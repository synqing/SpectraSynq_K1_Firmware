"""Tests for the VE-Auto-Loop MVP-0 driver (scripts/regression-harness/loop.py).

Two layers:
  * pure-logic unit tests (always run) — proxy math, DECIDE guards/vetoes,
    aggregation, candidate generation, weight invariants. No compilation.
  * a g++-gated integration smoke (skipped if no host compiler) that actually
    compiles light_mode_bloom via render_replay and proves the loop's
    score/determinism path on a real render. This is the first pytest coverage
    for the render_replay host harness too.
"""
import pathlib
import os
import shutil
import subprocess
import sys
import types

import pytest

HARNESS = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))
import loop  # noqa: E402
import render_replay as rr  # noqa: E402


# ---- frame helpers ---------------------------------------------------------
def _black():
    return [(0, 0, 0)] * loop.LED_COUNT


def _to_hex(leds):
    b = bytearray()
    for (r, g, bb) in leds:
        b += bytes([r, g, bb])
    return b.hex()


def _dot(pos, colour=(255, 255, 255)):
    f = _black()
    f[pos % loop.LED_COUNT] = colour
    return f


# ---- pure math -------------------------------------------------------------
def test_clamp01():
    assert loop.clamp01(-1) == 0.0
    assert loop.clamp01(2) == 1.0
    assert loop.clamp01(0.4) == 0.4


def test_band_score():
    assert loop.band_score(5, 1, 10) == 1.0       # inside
    assert loop.band_score(1, 1, 10) == 1.0       # on edge
    assert loop.band_score(19, 1, 10) == 0.0      # one full band above hi
    assert 0.0 < loop.band_score(14.5, 1, 10) < 1.0


def test_weights_normalised():
    assert abs(sum(loop.WEIGHTS.values()) - 1.0) < 1e-6


# ---- proxy panel -----------------------------------------------------------
def test_panel_all_black_is_dead():
    hexes = [_to_hex(_black()) for _ in range(10)]
    p = loop.compute_panel(hexes)
    assert p is not None
    assert p["liveness_fail"] is True
    assert p["motion_presence"] == 0.0


def test_panel_static_dot_is_dead():
    hexes = [_to_hex(_dot(80)) for _ in range(10)]   # same position every frame
    p = loop.compute_panel(hexes)
    assert p["liveness_fail"] is True


def test_panel_moving_dot_is_alive():
    hexes = [_to_hex(_dot(i)) for i in range(loop.LED_COUNT)]  # dot sweeps the strip
    p = loop.compute_panel(hexes)
    assert p["liveness_fail"] is False
    assert p["motion_presence"] > 0.0
    assert p["frames"] == loop.LED_COUNT


def test_panel_rejects_wrong_length():
    assert loop.compute_panel(["00"]) is None        # not 480 bytes
    assert loop.compute_panel([]) is None


# ---- aggregation -----------------------------------------------------------
def test_aggregate_mean_min_blend():
    def mk(v):
        d = {k: v for k in loop.SCORE_KEYS}
        d.update(white_bias_mean=0.0, half_life=10.0, liveness_fail=False)
        return d
    agg = loop.aggregate([mk(1.0), mk(0.0)])
    # 0.5*mean(1,0) + 0.5*min(1,0) = 0.5*0.5 + 0.5*0 = 0.25
    assert abs(agg["motion_presence"] - 0.25) < 1e-9
    assert agg["half_life"] == 10.0          # worst-case (min)
    assert agg["white_bias_mean"] == 0.0     # worst-case (max)


# ---- DECIDE ----------------------------------------------------------------
def _champ(rank=0.5, wb=0.10, hl=5.0):
    return {"rank_score": rank,
            "doctrine_floors": {"white_bias_max": wb, "energy_half_life_min": hl}}


def _cand(rank=0.5, wb=0.05, hl=10.0, dead=False):
    return {"rank_score": rank, "white_bias_mean": wb, "half_life": hl, "liveness_fail": dead}


def test_decide_dead_effect_rejected():
    v = loop.decide(_cand(dead=True), _champ())
    assert v["decision"] == "REJECT" and v["reason"] == "dead_effect"


def test_decide_colour_clarity_veto():
    v = loop.decide(_cand(rank=0.9, wb=0.5), _champ(wb=0.10))  # white-washed beyond floor
    assert v["decision"] == "REJECT" and v["reason"] == "colour_clarity"


def test_decide_motion_memory_veto():
    v = loop.decide(_cand(rank=0.9, hl=1.0), _champ(hl=5.0))   # persistence collapsed
    assert v["decision"] == "REJECT" and v["reason"] == "motion_memory"


def test_decide_keep_iterate_reject_ladder():
    assert loop.decide(_cand(rank=0.60), _champ(0.5))["decision"] == "KEEP"
    assert loop.decide(_cand(rank=0.40), _champ(0.5))["decision"] == "ITERATE"
    assert loop.decide(_cand(rank=0.10), _champ(0.5))["decision"] == "REJECT"


# ---- candidate generation --------------------------------------------------
def test_expand_space_rejects_unknown_field():
    with pytest.raises(ValueError):
        loop.expand_space({"params": {"speed": [1, 2]}})   # not a wired P-line key


def test_expand_space_accepts_wired_keys():
    keys, grids = loop.expand_space({"params": {"mood": [0.1, 0.2], "chroma": [1.0]}})
    assert set(keys) == {"mood", "chroma"}


def test_generate_grid_and_overflow():
    sp = {"params": {"mood": [0.1, 0.2], "chroma": [0.5, 1.0]}}  # 4-point grid
    assert len(loop.generate(sp, None, 42, 10)) == 4
    with pytest.raises(loop.GridOverflow):
        loop.generate(sp, "grid", 42, 2)          # forced grid over cap = hard error
    assert len(loop.generate(sp, "random", 42, 2)) == 2


def test_generate_random_is_seeded():
    sp = {"params": {"mood": [0.1, 0.2, 0.3, 0.4], "chroma": [0.5, 1.0]}}  # 8 points
    a = loop.generate(sp, "random", 7, 3)
    b = loop.generate(sp, "random", 7, 3)
    assert a == b                                  # deterministic under a fixed seed


def test_render_replay_keeps_parked_modes_opt_in():
    assert sorted(rr.MODES.keys()) == ["bloom"]

    env = os.environ.copy()
    env["SB_RENDER_REPLAY_ALL_MODES"] = "1"
    result = subprocess.run(
        [sys.executable, str(HARNESS / "render_replay.py"), "--help"],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    assert "comet" in result.stdout
    assert "spectrum_river" in result.stdout


# ---- integration smoke (real compile + render) -----------------------------
_HAVE_GPP = any(shutil.which(c) for c in rr.GPP_CANDIDATES)


@pytest.mark.skipif(not _HAVE_GPP, reason="no host g++ available")
def test_render_replay_integration_and_determinism(tmp_path):
    ok, binary, comp = rr.build_binary(str(tmp_path), mode="bloom")
    assert ok, (comp.get("stderr") or "")[:800]
    frames = rr.load_fixture(rr.FIXTURE_DIR / "beat-pulse.ndjson")
    ok1, h1, _ = rr.replay_frames(binary, frames, loop.CHAMPION_DEFAULT_PARAMS)
    ok2, h2, _ = rr.replay_frames(binary, frames, loop.CHAMPION_DEFAULT_PARAMS)
    assert ok1 and ok2
    assert h1 == h2                                # host is bit-identical (A2 invariant)
    assert len(h1) == len(frames)
    panel = loop.compute_panel(h1)
    assert panel is not None and panel["frames"] == len(frames)


# ---- plate contact sheet (the DEFAULT eye-gate) ----------------------------
_HAVE_PLATE_DEPS = True
try:
    import numpy  # noqa: F401
    import PIL  # noqa: F401

    sys.path.insert(0, str(HARNESS))
    import lgp_optics  # noqa: F401
except Exception:
    _HAVE_PLATE_DEPS = False


def _swelling_hexes(frames=12, colour=(255, 120, 40), dim=1.0):
    """Synthetic 'effect': a centred blob that grows and moves, so the peak frame is
    unambiguous and the plate render exercises non-trivial input. `dim` scales the
    LED amplitude DOWN to mimic the dim synthetic fixtures (which is exactly the
    near-black failure mode the auto-exposure must rescue). `colour` lets a test
    build two visibly different candidates."""
    out = []
    for t in range(frames):
        leds = _black()
        w = 4 + t  # widening blob
        c = tuple(int(round(min(255, v * dim))) for v in
                  (colour[0], colour[1] + t, colour[2]))
        for j in range(loop.LED_COUNT // 2 - w, loop.LED_COUNT // 2 + w):
            if 0 <= j < loop.LED_COUNT:
                leds[j] = c
        out.append(_to_hex(leds))
    return out


def _plate_luma(uri):
    """Decode a plate data-URI to (mean_luma, max_luma) in [0,1]."""
    import base64
    import io
    import numpy as np
    from PIL import Image
    raw = base64.b64decode(uri.split(",", 1)[1])
    arr = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB")).astype(np.float64) / 255.0
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    return float(lum.mean()), float(lum.max()), arr


@pytest.mark.skipif(not _HAVE_PLATE_DEPS, reason="numpy/PIL/lgp_optics unavailable")
def test_plate_data_uri_is_valid_png():
    hexes = _swelling_hexes()
    res = loop._plate_png_data_uri(hexes)
    assert res is not None
    uri, fi, mean_l, max_l = res
    assert uri.startswith("data:image/png;base64,")
    import base64
    raw = base64.b64decode(uri.split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
    assert 0 <= fi < len(hexes)
    assert 0.0 <= mean_l <= 1.0 and 0.0 <= max_l <= 1.0


@pytest.mark.skipif(not _HAVE_PLATE_DEPS, reason="numpy/PIL/lgp_optics unavailable")
def test_plate_auto_exposure_rescues_dim_input_from_black():
    """The whole bug: DIM synthetic content through K1_REAL_V1's bright-music
    exposure renders near-black. Per-plate auto-exposure MUST light it up."""
    dim = _swelling_hexes(dim=0.08)             # very dim blob (was rendering black)
    uri, _fi, mean_l, max_l = loop._plate_png_data_uri(dim)
    # NON-BLACK gates (the numeric proof we never ship a black plate again):
    assert max_l > 0.4, "dim plate max-luma %.3f <= 0.4 (still near-black)" % max_l
    assert mean_l > 0.05, "dim plate mean-luma %.3f <= 0.05 (still near-black)" % mean_l


@pytest.mark.skipif(not _HAVE_PLATE_DEPS, reason="numpy/PIL/lgp_optics unavailable")
def test_plate_columns_are_distinct():
    """Two visibly different candidates must produce visibly different plates
    (mean-abs pixel diff non-trivial) — the anti-'identical-columns' gate."""
    import numpy as np
    warm = _swelling_hexes(colour=(255, 90, 20), dim=0.1)
    cool = _swelling_hexes(colour=(20, 90, 255), dim=0.1)
    _u1, _f1, _m1, _x1 = loop._plate_png_data_uri(warm)
    _u2, _f2, _m2, _x2 = loop._plate_png_data_uri(cool)
    _ml1, _xl1, a1 = _plate_luma(_u1)
    _ml2, _xl2, a2 = _plate_luma(_u2)
    diff = float(np.abs(a1 - a2).mean())
    assert diff > 0.02, "plates not distinct (mean abs pixel diff %.4f)" % diff


def test_plate_data_uri_empty_is_none():
    assert loop._plate_png_data_uri([]) is None


@pytest.mark.skipif(not _HAVE_PLATE_DEPS, reason="numpy/PIL/lgp_optics unavailable")
def test_render_contact_sheet_plate_path(tmp_path):
    champion = {"champion_version": 0, "params": dict(loop.CHAMPION_DEFAULT_PARAMS),
                "rank_score": 0.5}
    champ_hexes = _swelling_hexes(colour=(255, 90, 20), dim=0.1)
    # two distinct dim candidates + a contrasting top edge => full, distinct, lit plates
    shortlist = [
        {"params": {**loop.CHAMPION_DEFAULT_PARAMS, "palette_mode": True, "palette_index": 5},
         "agg": {k: 0.5 for k in loop.SCORE_KEYS},
         "render_hexes": _swelling_hexes(colour=(40, 220, 60), dim=0.1), "rank_score": 0.55},
        {"params": {**loop.CHAMPION_DEFAULT_PARAMS, "palette_mode": True, "palette_index": 9},
         "agg": {k: 0.5 for k in loop.SCORE_KEYS},
         "render_hexes": _swelling_hexes(colour=(40, 60, 230), dim=0.1), "rank_score": 0.52},
    ]
    top = _swelling_hexes(colour=(220, 30, 200), dim=0.1)
    p = loop.render_contact_sheet(tmp_path, "bloom", "broadband-swell", champ_hexes,
                                  champion, shortlist, top_hexes=top)  # default = plate
    html = p.read_text(encoding="utf-8")
    assert p.exists()
    assert "data:image/png;base64," in html       # embedded PNG plate(s)
    assert html.count("<img class=plate") == 3     # champion + 2 shortlist
    assert "K1_REAL_V1" in html
    assert "auto-exposed for comparison" in html   # the viewing-transform label

    # numeric proof from the side-channel stats: every plate lit, shortlist distinct
    import base64
    import io
    import re
    import numpy as np
    from PIL import Image
    stats = loop.render_contact_sheet.last_plate_stats
    assert len(stats) == 3
    for title, ml, xl in stats:
        assert xl > 0.4 and ml > 0.05, "%s rendered near-black (μ=%.3f max=%.3f)" % (title, ml, xl)
    # decode the two shortlist plates and assert they differ
    uris = re.findall(r'<img class=plate src="data:image/png;base64,([^"]+)"', html)
    arrs = []
    for u in uris[1:]:  # skip champion column
        raw = base64.b64decode(u)
        arrs.append(np.asarray(Image.open(io.BytesIO(raw)).convert("RGB")).astype(np.float64) / 255.0)
    assert float(np.abs(arrs[0] - arrs[1]).mean()) > 0.02, "shortlist columns identical"


# ---- Layer-1 regression check ----------------------------------------------
def test_regress_without_champion_is_tooling_error(tmp_path):
    ns = types.SimpleNamespace(effect="bloom", corpus=None, out=str(tmp_path), compiler=None)
    assert loop.cmd_regress(ns) == loop.EXIT_TOOLING


@pytest.mark.skipif(not _HAVE_GPP, reason="no host g++ available")
def test_regress_clean_holds_floor(tmp_path):
    seed = types.SimpleNamespace(effect="bloom", corpus=None, params=None,
                                 out=str(tmp_path), compiler=None, json=False)
    assert loop.cmd_seed_champion(seed) == loop.EXIT_OK
    reg = types.SimpleNamespace(effect="bloom", corpus=None, out=str(tmp_path), compiler=None)
    # unchanged source must hold the champion's own floor
    assert loop.cmd_regress(reg) == loop.EXIT_OK
