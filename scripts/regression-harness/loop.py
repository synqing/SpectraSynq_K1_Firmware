#!/usr/bin/env python3
"""VE-Auto-Loop MVP-0 driver — the autonomous inner loop (Tier-1, host-only).

    edit (param sweep) -> render -> score -> regress vs champion -> rank -> shortlist

This is the driver PRD-03 (`docs/prd/ve-auto-loop/03-loop-driver-and-human-gate.md`)
specs and PRD-02 (`02-evaluation-and-scoring.md`) scores. It drives the real
firmware render path via `render_replay.py` (Tier-1 host harness), with ZERO
Captain involvement per iteration. The Captain's eye is the single TERMINAL
aesthetic gate, applied once per cycle over the <=5 shortlist via the generated
contact sheet — never per iteration, never on rejects (Founder Execution Boundary).

EPISTEMIC STATUS  [MECHANISM], NOT [MEASURED]
  Every proxy here is computed from `render_replay`'s pre-gamma/pre-dither LED
  byte dump (the host reproduces the effect MATHS + motion memory only, not the
  optics stack). Scores RANK candidates; they NEVER judge aesthetics and NEVER
  certify "ship". A real promotion still requires the Captain's eye + on-device
  [MEASURED] certification (Tier-2, deferred). The host champion is a regression
  FLOOR, not a ship decision.

BUILD-TO-REPO NOTES (the PRD assumed surfaces that don't exist on disk):
  * render_replay returns LED BYTES ONLY (no VPABMetricPayload) -> every proxy is
    recomputed from the 480-byte frame here. (D5 BLOCKER-1)
  * The sweepable surface is EXACTLY the 10 RenderParams keys wired into
    render_replay's stdin 'P' line (RENDER_REPLAY_PARAM_KEYS), not the full struct
    and not the PRD's fictional speed/persistence fields. (D5 DEVIATION-1)
  * beat-correlation, perf-budget, channel-independence, and all
    VPABMetricPayload-sourced proxies are DEFERRED (MVP-1 / Tier-2 device).
  * Aggregation = 0.5*mean + 0.5*min across fixtures (PRD-02 §1.10.3,
    Goodhart-resistant). Shortlist hard-capped at 5 (PRD-03 §6.2).

NO HARDWARE, NO BENCH, NO SOUND, NO FLASH. Write scope = results/<effect>/ only.
NON-SHIPPING: this is developer harness code (Developer Instrumentation Boundary).
"""

import argparse
import hashlib
import itertools
import json
import math
import random
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))
import render_replay as rr  # noqa: E402  (the Tier-1 renderer we drive)

RESULTS_ROOT = HARNESS / "results"
LED_COUNT = rr.LED_COUNT  # 160

# ---- exit-code contract (PRD-03 §1.5) -------------------------------------
EXIT_OK = 0            # ran the budget, >=1 survivor + shortlist + contact sheet
EXIT_TOOLING = 1       # compile/IO/usage error
EXIT_NO_SURVIVOR = 2   # ran clean, nothing cleared the floor (recorded negative)
EXIT_DETERMINISM = 3   # champion re-render not bit-identical

# ---- the ONLY sweepable surface (render_replay.py stdin 'P' line) ----------
RENDER_REPLAY_PARAM_KEYS = {
    "mood", "saturation", "square_iter", "chroma", "palette_mode",
    "palette_index", "auto_color_shift", "hue_position", "chroma_val", "chromatic_mode",
}

# render_replay.DEFAULT_PARAMS carries only 4 keys; the champion pins all 10.
CHAMPION_DEFAULT_PARAMS = {
    "mood": 0.5, "saturation": 0.9, "square_iter": 1.0, "chroma": 1.0,
    "palette_mode": False, "palette_index": 0, "auto_color_shift": False,
    "hue_position": 0.0, "chroma_val": 0.0, "chromatic_mode": True,
}

DEFAULT_CORPUS = ["beat-pulse", "broadband-swell", "chord-major"]

# ---- proxy weights: PRD-02 §3.3 with W_beat (0.25) dropped (MVP-1) and the
#      remaining six renormalised to sum 1.0. Version-stamped + frozen per run.
WEIGHTS_VERSION = "ve-eval-w0-mvp0"
_RAW_W = {"motion": 0.15, "am_velocity": 0.15, "am_coherence": 0.10,
          "colour": 0.15, "spatial": 0.10, "persistence": 0.10}
_WSUM = sum(_RAW_W.values())  # 0.75
WEIGHTS = {k: round(v / _WSUM, 6) for k, v in _RAW_W.items()}  # sum == 1.0

# ---- proxy normalisation scales [INFERENCE] — tunable. Relative-to-champion
#      ranking is the load-bearing property; absolute scales only set sensitivity.
SC = {"DELTA": 2.0, "ENERGY": 32.0, "TV": 48.0, "CD": 48.0, "EER": 0.8,
      "WIDTH_LO": 6.0, "WIDTH_HI": 50.0, "HL_LO": 1.5, "HL_HI": 30.0,
      "VEL_LO": 0.2, "VEL_HI": 8.0, "COH": 6.0}
LIVENESS_MIN = 0.005      # mean changed-LED fraction below which an effect is "dead"
DOCTRINE_MARGIN = 0.15    # how far a candidate may regress a doctrine floor before reject
KEEP_MARGIN = 0.02        # rank must be >= champion - this to KEEP (shortlist)
ITERATE_FRAC = 0.60       # rank >= this * champion -> ITERATE (recorded, not shortlisted)
SHORTLIST_HARD_CAP = 5    # PRD-03 §6.2

SCORE_KEYS = ["motion_presence", "am_velocity_score", "am_coherence",
              "colour_clarity", "spatial_shape", "persistence"]


# ============================================================================
# small math helpers
# ============================================================================
def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def band_score(x, lo, hi):
    """1.0 inside [lo,hi], linear falloff to 0 over one band-width outside."""
    if lo <= x <= hi:
        return 1.0
    span = max(hi - lo, 1e-6)
    d = (lo - x) / span if x < lo else (x - hi) / span
    return max(0.0, 1.0 - d)


# ============================================================================
# proxy panel — frame-buffer [MECHANISM] metrics from render_replay LED bytes
# ============================================================================
def _luma(frame, j):
    return 0.299 * frame[3 * j] + 0.587 * frame[3 * j + 1] + 0.114 * frame[3 * j + 2]


def compute_panel(hexes):
    """Score one fixture's render. `hexes` = list of per-frame hex strings (960
    chars = 480 bytes = 160 LEDs * RGB). Returns a panel dict of [0,1] scores plus
    the raw doctrine metrics, or None on empty/invalid input."""
    if not hexes:
        return None
    frames = []
    for h in hexes:
        b = bytes.fromhex(h)
        if len(b) != LED_COUNT * 3:
            return None
        frames.append(b)
    n = len(frames)

    lumas = [[_luma(f, j) for j in range(LED_COUNT)] for f in frames]
    energy = [sum(L) / LED_COUNT for L in lumas]

    # channel divergence (colour spread) — std of the three channel means, per frame
    chan_div = statistics.fmean(
        statistics.pstdev([sum(f[0::3]) / LED_COUNT,
                           sum(f[1::3]) / LED_COUNT,
                           sum(f[2::3]) / LED_COUNT]) for f in frames)

    # white-bias: mean over lit LEDs of min/max (1.0 == fully white-washed)
    def _wb(f):
        s, lit = 0.0, 0
        for j in range(LED_COUNT):
            r, g, b = f[3 * j], f[3 * j + 1], f[3 * j + 2]
            mx = max(r, g, b)
            if mx > 0:
                s += min(r, g, b) / mx
                lit += 1
        return s / lit if lit else 0.0
    white_bias_mean = statistics.fmean(_wb(f) for f in frames)

    # spatial shape — centre-of-mass, width, edge energy per frame
    coms, widths, eers = [], [], []
    for L in lumas:
        tot = sum(L)
        if tot <= 1e-9:
            coms.append((LED_COUNT - 1) / 2.0)
            widths.append(0.0)
            eers.append(0.0)
            continue
        com = sum(j * L[j] for j in range(LED_COUNT)) / tot
        width = math.sqrt(sum(L[j] * (j - com) ** 2 for j in range(LED_COUNT)) / tot)
        eer = sum(abs(L[j] - L[j - 1]) for j in range(1, LED_COUNT)) / tot
        coms.append(com)
        widths.append(width)
        eers.append(eer)

    # temporal proxies (need >= 2 frames)
    if n > 1:
        changed = [sum(1 for j in range(LED_COUNT)
                       if abs(lumas[t][j] - lumas[t - 1][j]) > SC["DELTA"]) / LED_COUNT
                   for t in range(1, n)]
        mean_changed = statistics.fmean(changed)
        mean_denergy = statistics.fmean(abs(energy[t] - energy[t - 1]) for t in range(1, n))
        tv = statistics.fmean(statistics.pstdev([lumas[t][j] for t in range(n)])
                              for j in range(LED_COUNT))
        com_delta = [abs(coms[t] - coms[t - 1]) for t in range(1, n)]
        am_velocity = statistics.median(com_delta) if com_delta else 0.0
        com_delta2 = [abs(com_delta[t] - com_delta[t - 1]) for t in range(1, len(com_delta))]
        coh_std = statistics.pstdev(com_delta2) if len(com_delta2) > 1 else 0.0
    else:
        mean_changed = mean_denergy = tv = am_velocity = coh_std = 0.0

    # energy half-life (motion-memory persistence): frames from peak to 50% decay
    peak_t = max(range(n), key=lambda t: energy[t])
    peak_e = energy[peak_t]
    half_life = float(n - peak_t)
    if peak_e > 1e-9:
        for t in range(peak_t, n):
            if energy[t] <= 0.5 * peak_e:
                half_life = float(t - peak_t)
                break

    motion_presence = clamp01(0.5 * mean_changed
                              + 0.2 * clamp01(mean_denergy / SC["ENERGY"])
                              + 0.3 * clamp01(tv / SC["TV"]))
    colour_clarity = clamp01(0.5 * (1.0 - clamp01(white_bias_mean))
                             + 0.5 * clamp01(chan_div / SC["CD"]))
    spatial_shape = clamp01(0.6 * band_score(statistics.fmean(widths), SC["WIDTH_LO"], SC["WIDTH_HI"])
                            + 0.4 * clamp01(statistics.fmean(eers) / SC["EER"]))
    persistence = band_score(half_life, SC["HL_LO"], SC["HL_HI"])
    am_velocity_score = band_score(am_velocity, SC["VEL_LO"], SC["VEL_HI"])
    am_coherence = clamp01(1.0 - clamp01(coh_std / SC["COH"]))

    return {
        "frames": n,
        "motion_presence": round(motion_presence, 6),
        "colour_clarity": round(colour_clarity, 6),
        "spatial_shape": round(spatial_shape, 6),
        "persistence": round(persistence, 6),
        "am_velocity_score": round(am_velocity_score, 6),
        "am_coherence": round(am_coherence, 6),
        # raw doctrine metrics (used for floors / vetoes)
        "white_bias_mean": round(white_bias_mean, 6),
        "half_life": round(half_life, 6),
        "mean_changed": round(mean_changed, 6),
        "liveness_fail": mean_changed < LIVENESS_MIN,
    }


def rank_from_scores(s):
    return clamp01(
        WEIGHTS["motion"] * s["motion_presence"]
        + WEIGHTS["am_velocity"] * s["am_velocity_score"]
        + WEIGHTS["am_coherence"] * s["am_coherence"]
        + WEIGHTS["colour"] * s["colour_clarity"]
        + WEIGHTS["spatial"] * s["spatial_shape"]
        + WEIGHTS["persistence"] * s["persistence"])


def aggregate(panels):
    """Corpus aggregation: 0.5*mean + 0.5*min per score (worst-scenario weighted),
    worst-case for raw doctrine metrics. `panels` = list of per-fixture panels."""
    agg = {}
    for k in SCORE_KEYS:
        vals = [p[k] for p in panels]
        agg[k] = round(0.5 * statistics.fmean(vals) + 0.5 * min(vals), 6)
    agg["white_bias_mean"] = round(max(p["white_bias_mean"] for p in panels), 6)
    agg["half_life"] = round(min(p["half_life"] for p in panels), 6)
    agg["liveness_fail"] = any(p["liveness_fail"] for p in panels)
    agg["rank_score"] = round(rank_from_scores(agg), 6)
    return agg


def decide(cand_agg, champion):
    """DECIDE (PRD-02 §3): hard guards + doctrine vetoes (relative to champion)
    short-circuit before the weighted rank. Vocabulary is frozen — only
    KEEP/ITERATE/REJECT (+ INCOMPARABLE upstream)."""
    if cand_agg["liveness_fail"]:
        return {"decision": "REJECT", "reason": "dead_effect", "rank_score": 0.0}
    floors = champion["doctrine_floors"]
    if cand_agg["white_bias_mean"] > floors["white_bias_max"] * (1.0 + DOCTRINE_MARGIN):
        return {"decision": "REJECT", "reason": "colour_clarity", "rank_score": 0.0}
    if cand_agg["half_life"] < floors["energy_half_life_min"] * (1.0 - DOCTRINE_MARGIN):
        return {"decision": "REJECT", "reason": "motion_memory", "rank_score": 0.0}
    rs, cr = cand_agg["rank_score"], champion["rank_score"]
    if rs >= cr - KEEP_MARGIN:
        return {"decision": "KEEP", "reason": None, "rank_score": rs}
    if rs >= ITERATE_FRAC * cr:
        return {"decision": "ITERATE", "reason": "below_keep", "rank_score": rs}
    return {"decision": "REJECT", "reason": "below_floor", "rank_score": rs}


# ============================================================================
# render_replay integration (compile ONCE, replay MANY)
# ============================================================================
class RenderError(Exception):
    pass


class GridOverflow(Exception):
    def __init__(self, size, cap):
        super().__init__("grid %d > cap %d (use --strategy random or raise --max-iterations)"
                         % (size, cap))


def load_corpus(names):
    corpus = {}
    for nm in names:
        fx = rr.FIXTURE_DIR / (nm + ".ndjson")
        if not fx.exists():
            raise FileNotFoundError("fixture not found: %s" % fx)
        corpus[nm] = rr.load_fixture(fx)
    return corpus


def render_corpus(binary, params, corpus):
    """Drive the compiled harness over each fixture. Returns {name: hexes}."""
    out = {}
    for nm, frames in corpus.items():
        ok, hexes, meta = rr.replay_frames(binary, frames, params)
        if not ok or len(hexes) != len(frames):
            raise RenderError("%s: rc=%s %s" % (nm, meta.get("returncode"),
                                                (meta.get("stderr") or "")[:200]))
        out[nm] = hexes
    return out


def frame_hash(hexes):
    return hashlib.sha256("".join(hexes).encode("ascii")).hexdigest()


def params_hash(params):
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()


def corpus_hash(names):
    h = hashlib.sha256()
    for nm in names:
        h.update((rr.FIXTURE_DIR / (nm + ".ndjson")).read_bytes())
    return h.hexdigest()


def score_corpus(rendered, names):
    panels = {nm: compute_panel(rendered[nm]) for nm in names}
    if any(p is None for p in panels.values()):
        raise RenderError("a fixture produced no/invalid frames")
    return panels, aggregate([panels[nm] for nm in names])


def _iso_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _git_ref(rel):
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             text=True, capture_output=True).stdout.strip() or "unknown"
    except Exception:
        sha = "unknown"
    return "git:%s@%s" % (rel, sha)


# ============================================================================
# candidate generation (MVP-0 "edit" = parameter sweep)
# ============================================================================
def expand_space(space):
    params = space.get("params") or {}
    if not params:
        raise ValueError("space has no 'params' grid")
    bad = [k for k in params if k not in RENDER_REPLAY_PARAM_KEYS]
    if bad:
        raise ValueError("unknown sweep field(s) %s — not in render_replay 'P'-line "
                         "surface %s" % (bad, sorted(RENDER_REPLAY_PARAM_KEYS)))
    keys = list(params.keys())
    return keys, [params[k] for k in keys]


def generate(space, strategy, seed, cap):
    """Returns list of candidate param-delta dicts (<= cap). `strategy` None means
    grid with auto-fallback to random when the grid exceeds the cap; explicit
    'grid' over the cap is a hard error (never silently truncate)."""
    keys, grids = expand_space(space)
    full = list(itertools.product(*grids))
    size = len(full)
    if strategy == "random":
        pts = full if size <= cap else random.Random(seed).sample(full, cap)
    elif strategy == "grid":
        if size > cap:
            raise GridOverflow(size, cap)
        pts = full
    else:  # None -> grid with auto-fallback
        pts = full if size <= cap else random.Random(seed).sample(full, cap)
    return [dict(zip(keys, p)) for p in pts]


# ============================================================================
# champion lifecycle
# ============================================================================
def champion_path(out_dir):
    return out_dir / "champion.json"


def load_champion(out_dir):
    p = champion_path(out_dir)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def build_champion(binary, params, corpus, names, promoted_by, out_dir,
                   version=0, supersedes=None):
    """Render+score `params`, assert host determinism, return a champion.json dict.
    Raises RenderError on render failure / DeterminismError surfaced by caller."""
    r1 = render_corpus(binary, params, {n: corpus[n] for n in names})
    r2 = render_corpus(binary, params, {n: corpus[n] for n in names})
    fh1 = {n: frame_hash(r1[n]) for n in names}
    fh2 = {n: frame_hash(r2[n]) for n in names}
    det = fh1 == fh2
    panels, agg = score_corpus(r1, names)
    try:
        evidence_ref = str((out_dir / "results.json").relative_to(ROOT))
    except ValueError:
        evidence_ref = str(out_dir / "results.json")  # out_dir outside the repo
    champ = {
        "champion_version": version,
        "promoted_utc": _iso_now(),
        "promoted_by": promoted_by,
        "effect": "bloom",
        "effect_id": None,  # firmware enum id not source-verified here; honest null
        "effect_source_ref": _git_ref("SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_bloom.cpp"),
        "params": params,
        "params_hash": params_hash(params),
        "weights_version": WEIGHTS_VERSION,
        "weights": WEIGHTS,
        "fixture_corpus": names,
        "fixture_corpus_hash": corpus_hash(names),
        "tier_of_record": "host",            # [MECHANISM] floor, NOT device [MEASURED]
        "panel": panels,
        "rank_score": agg["rank_score"],
        "doctrine_floors": {
            "white_bias_max": agg["white_bias_mean"],
            "energy_half_life_min": agg["half_life"],
        },
        "evidence_ref": evidence_ref,
        "supersedes": supersedes,
        "frame_hashes": fh1,
        "changelog": [{
            "version": version, "utc": _iso_now(), "by": promoted_by,
            "note": "host-bootstrap [MECHANISM] floor; weights=%s; corpus=%s"
                    % (WEIGHTS_VERSION, names),
        }],
    }
    return champ, det, r1


def _atomic_write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp.replace(path)


# ============================================================================
# contact sheet (dependency-free HTML; display-gamma applied for VIEWING only)
# ============================================================================
def _gamma_hex(r, g, b):
    # values are pre-gamma [MECHANISM]; apply a display gamma so the strip is
    # legible to the human eye. This is a VIEWING transform only.
    def g_(v):
        return int(round((min(255, max(0, v)) / 255.0) ** (1 / 2.2) * 255))
    return "#%02x%02x%02x" % (g_(r), g_(g), g_(b))


# ---- plate render (the DEFAULT contact-sheet eye-gate) ---------------------
# The Captain judges effects by eye, so the per-column image must be the REAL K1
# LGP plate (reality-calibrated K1_REAL_V1 optics, dual-channel, ~5.48:1 plate-face
# aspect) — NOT a flat LED ribbon. We feed one representative frame of the
# candidate's LED output through lgp_optics.plate_image() and embed the PNG.
#
# This is a RELATIVE eye-gate for comparing SHAPE + COLOUR across candidates, not an
# absolute-photometry render. So two viewing transforms are applied (both clearly
# labelled in the sheet) so every column is visibly lit and distinct:
#
#   (1) DUAL-CHANNEL like the good lgp_real_render samples (Captain rated 7.4/10):
#       the candidate drives the BOTTOM edge (warm/chromatic primary) and a
#       contrasting magenta/cool palette bloom drives the TOP edge — so the plate
#       reads full and rich, not a sparse bottom sliver. The top channel is scaled
#       (TOP_SCALE) so the candidate stays the dominant feature.
#   (2) PER-PLATE AUTO-EXPOSURE: the synthetic fixtures are DIM, and K1_REAL_V1's
#       exposure (2.8) was calibrated to BRIGHT real-music content, so a fixed
#       exposure renders dim input near-black. We auto-gain each plate's LED input
#       so its brightest region reaches a good target peak luma (PLATE_TARGET_LUMA),
#       making shape/colour legible for comparison. Absolute brightness is NOT the
#       sheet's job (that's the on-device [MEASURED] gate).
#
# Frame choice: the genuinely HIGHEST-ENERGY frame (max total LED luma), not a fixed
# index, so the swell peak is what gets shown.

# Top-channel contrast bloom (magenta palette), matching lgp_real_render's secondary
# edge. Rendered ONCE per run and reused; the per-column distinctness comes from each
# candidate's own bottom channel (palette-diverse sweep => visibly different plates).
CONTACT_TOP_PARAMS = {
    "mood": 0.7, "saturation": 1.0, "square_iter": 1.0, "chroma": 1.0,
    "palette_mode": True, "palette_index": 26, "auto_color_shift": False,
    "hue_position": 0.85, "chroma_val": 0.0, "chromatic_mode": False,
}
TOP_SCALE = 0.62           # keep the warm candidate edge dominant (lgp_real_render)
PLATE_TARGET_LUMA = 0.82   # auto-exposure target peak luma in the rendered plate
PLATE_MAX_AUTOGAIN = 64.0  # cap the auto-gain so pure-black input stays black


def _peak_frame_index(hexes):
    """Representative frame = the highest TOTAL LED energy (sum of luma), so the
    swell peak is shown even when no LED is fully on. Robust on dim content."""
    if not hexes:
        return 0
    def _energy(h):
        b = bytes.fromhex(h)
        return sum(_luma(b, j) for j in range(LED_COUNT))
    return max(range(len(hexes)), key=lambda i: _energy(hexes[i]))


def _decode_frame_rgb(hex_str):
    """Harness 'R' line hex -> (160,3) float in [0,1], render-index order."""
    import numpy as np
    b = bytes.fromhex(hex_str)
    return np.frombuffer(b, dtype=np.uint8).astype(np.float64).reshape(LED_COUNT, 3) / 255.0


def _auto_gain(bottom, top, optics, target=PLATE_TARGET_LUMA):
    """Find a linear input gain so the rendered plate's PEAK luma reaches `target`.
    The K1_REAL_V1 tonemap (extended Reinhard) is monotonic in input, so a bisection
    on the gain converges cleanly. Returns the gain (>=1 typically; capped)."""
    import numpy as np
    import lgp_optics as lo

    def peak_luma(g):
        img = lo.plate_image(bottom * g, top * g, optics=optics)
        f = img.astype(np.float64) / 255.0
        lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
        return float(lum.max())

    if peak_luma(1.0) <= 1e-6:          # input is black -> no gain can light it
        return 1.0
    lo_g, hi_g = 1.0, PLATE_MAX_AUTOGAIN
    # if even base gain already exceeds target, search below 1.0 too
    if peak_luma(1.0) >= target:
        lo_g, hi_g = 0.0, 1.0
    for _ in range(24):
        mid = 0.5 * (lo_g + hi_g)
        if peak_luma(mid) < target:
            lo_g = mid
        else:
            hi_g = mid
    return 0.5 * (lo_g + hi_g)


def _plate_png_data_uri(hexes, top_hexes=None):
    """Render the peak frame of `hexes` through the K1_REAL_V1 LGP optics, DUAL-channel
    and PER-PLATE AUTO-EXPOSED, and return a base64 PNG `data:` URI at the ~5.48:1
    plate-face aspect, plus (frame_index, mean_luma, max_luma) of the rendered plate.

    `hexes`     drives the BOTTOM edge (the candidate — warm/chromatic primary).
    `top_hexes` drives the TOP edge (a contrasting magenta palette bloom); when None
                the top edge is zeros (single-channel fallback). Auto-exposure scales
                the LED input so the plate's brightest region reaches PLATE_TARGET_LUMA
                — a relative comparison view, not absolute photometry.
    Returns None on empty input."""
    if not hexes:
        return None
    import io
    import base64
    import numpy as np
    import lgp_optics as lo  # lazy: keeps pure-math import path PIL/numpy-free
    from PIL import Image
    fi = _peak_frame_index(hexes)
    bottom = _decode_frame_rgb(hexes[fi])
    if top_hexes:
        ti = _peak_frame_index(top_hexes)
        top = _decode_frame_rgb(top_hexes[ti]) * TOP_SCALE
    else:
        top = np.zeros_like(bottom)
    gain = _auto_gain(bottom, top, lo.K1_REAL_V1)
    img = lo.plate_image(bottom * gain, top * gain, optics=lo.K1_REAL_V1)
    f = img.astype(np.float64) / 255.0
    lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    mean_luma, max_luma = float(lum.mean()), float(lum.max())
    buf = io.BytesIO()
    Image.fromarray(img, "RGB").save(buf, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return uri, fi, mean_luma, max_luma


def _strip_rows(hexes, sample=10):
    n = len(hexes)
    if n == 0:
        return ""
    idx = sorted(set(int(round(i * (n - 1) / max(1, sample - 1))) for i in range(min(sample, n))))
    rows = []
    for t in idx:
        f = bytes.fromhex(hexes[t])
        cells = "".join('<td style="background:%s"></td>'
                        % _gamma_hex(f[3 * j], f[3 * j + 1], f[3 * j + 2])
                        for j in range(LED_COUNT))
        rows.append("<tr>%s</tr>" % cells)
    return ("<table class=strip cellspacing=0 cellpadding=0>%s</table>"
            % "".join(rows))


def render_contact_sheet(out_dir, effect, fixture_name, champ_hexes, champion,
                         shortlist, strips=False, top_hexes=None):
    """One HTML page: champion column 0, then the <=5 shortlist columns. Each
    column shows — by DEFAULT — a faithful K1 LGP PLATE render (K1_REAL_V1 optics,
    ~5.48:1 plate-face aspect, DUAL-channel, PER-PLATE auto-exposed for comparison)
    of that candidate's highest-energy frame, plus the proxy panel with
    delta-vs-champion + the param diff. The Captain's terminal batch gate is the
    REAL plate, not a flat LED ribbon. Pass strips=True to fall back to the legacy
    raw spacetime-strip view (display-gamma cells). `top_hexes` is the shared
    contrasting magenta palette bloom rendered for the TOP edge (None => zeros)."""
    cols = [("CHAMPION v%s" % champion["champion_version"], champion["params"],
             {k: champion["rank_score"] if k == "rank_score" else None for k in []},
             champ_hexes, champion["rank_score"], 0.0, "—")]
    for i, c in enumerate(shortlist):
        diff = {k: c["params"][k] for k in c["params"]
                if champion["params"].get(k) != c["params"][k]}
        diff_s = ", ".join("%s=%s" % (k, diff[k]) for k in diff) or "(== champion)"
        cols.append(("rank %d" % (i + 1), c["params"], c["agg"], c["render_hexes"],
                     c["rank_score"], c["rank_score"] - champion["rank_score"], diff_s))

    col_html = []
    plate_stats = []  # (title, mean_luma, max_luma) — validation evidence
    for title, params, agg, hexes, rank, delta, diff_s in cols:
        rows = "".join(
            "<tr><td class=k>%s</td><td class=v>%.3f</td></tr>" % (k, (agg or {}).get(k, 0.0))
            for k in SCORE_KEYS) if agg else ""
        dcls = "pos" if delta > 0 else ("neg" if delta < 0 else "")
        if strips:
            visual = _strip_rows(hexes)
        else:
            res = _plate_png_data_uri(hexes, top_hexes=top_hexes)
            if res is None:
                visual = "<div class=noplate>(no frames)</div>"
            else:
                uri, fi, mean_l, max_l = res
                plate_stats.append((title, mean_l, max_l))
                visual = ('<img class=plate src="%s" alt="K1 LGP plate render">'
                          '<div class=fcap>K1_REAL_V1 plate · auto-exposed for '
                          'comparison · peak frame %d · luma μ=%.2f max=%.2f</div>'
                          % (uri, fi, mean_l, max_l))
        col_html.append(
            "<div class=col><h3>%s</h3>"
            "<div class=rank>rank_score <b>%.4f</b> "
            "<span class='%s'>(%+.4f)</span></div>"
            "<div class=diff>%s</div>%s"
            "<table class=panel>%s</table></div>"
            % (title, rank, dcls, delta, diff_s, visual, rows))

    if strips:
        note = ("<b>[MECHANISM], NOT [MEASURED].</b> Strips are render_replay's "
                "pre-gamma host bytes with a display-gamma applied for viewing only; "
                "values are NOT the on-device strip. Each row = a sampled frame of "
                "fixture <b>%s</b>; columns = the 160 LEDs." % fixture_name)
    else:
        note = ("<b>[MECHANISM], NOT [MEASURED].</b> Each column is the candidate's "
                "highest-energy frame on fixture <b>%s</b>, rendered through the "
                "reality-calibrated <b>K1_REAL_V1</b> LGP optics at the ~5.48:1 plate "
                "face — the candidate (warm/chromatic) on the BOTTOM edge + a "
                "contrasting magenta palette bloom on the TOP edge (dual-channel, like "
                "the rated samples). Each plate is <b>auto-exposed for comparison</b> "
                "(per-plate gain to a common target peak luma) because the synthetic "
                "fixture is dim and K1_REAL_V1's exposure is calibrated to bright "
                "real-music content — this is a RELATIVE shape/colour eye-gate, not "
                "absolute photometry (that is the on-device [MEASURED] gate). Proxies "
                "RANK; they do not judge." % fixture_name)
    render_contact_sheet.last_plate_stats = plate_stats  # exposed for tests/validation
    html = """<!doctype html><meta charset=utf-8>
<title>VE-Auto-Loop contact sheet — {effect}</title>
<style>
 body{{font:13px/1.4 -apple-system,Segoe UI,sans-serif;background:#111;color:#ddd;margin:16px}}
 h1{{font-size:16px}} .note{{color:#888;max-width:60em}}
 .row{{display:flex;gap:14px;overflow-x:auto;padding:8px 0}}
 .col{{background:#1b1b1b;border:1px solid #333;border-radius:8px;padding:10px;min-width:340px}}
 .col h3{{margin:0 0 6px;font-size:13px;color:#9cf}}
 .rank{{font-size:12px;margin-bottom:4px}} .rank b{{color:#fff}}
 .pos{{color:#6f6}} .neg{{color:#f77}}
 .diff{{color:#fc9;font-size:11px;margin-bottom:8px;min-height:1.4em}}
 img.plate{{display:block;width:320px;height:auto;image-rendering:auto;border:1px solid #000;
   border-radius:3px;background:#000;margin-bottom:2px}}
 .fcap{{color:#789;font-size:10px;margin-bottom:8px}} .noplate{{color:#a55;margin-bottom:8px}}
 table.strip{{border:1px solid #000;margin-bottom:8px}}
 table.strip td{{width:2px;height:7px;padding:0}}
 table.panel{{width:100%;border-collapse:collapse;font-size:11px}}
 table.panel td{{padding:1px 4px}} td.k{{color:#9ab}} td.v{{text-align:right;color:#fff}}
</style>
<h1>VE-Auto-Loop — {effect} — contact sheet</h1>
<p class=note>{note} This sheet is the single terminal aesthetic gate — pick a
winner by eye, then <code>loop.py promote</code> it. A real ship still needs
on-device certification.</p>
<div class=row>{cols}</div>
""".format(effect=effect, note=note, cols="".join(col_html))
    p = out_dir / "contact_sheet.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p


# ============================================================================
# subcommands
# ============================================================================
def _resolve_out(args, effect):
    return Path(args.out) if getattr(args, "out", None) else (RESULTS_ROOT / effect)


def cmd_seed_champion(args):
    effect = args.effect
    if effect != "bloom":
        print("only --effect bloom is wired for MVP-0 (render_replay mode registry)", file=sys.stderr)
        return EXIT_TOOLING
    out_dir = _resolve_out(args, effect)
    names = args.corpus or DEFAULT_CORPUS
    params = dict(CHAMPION_DEFAULT_PARAMS)
    if args.params:
        for kv in args.params.split(","):
            k, _, v = kv.partition("=")
            k = k.strip()
            if k not in RENDER_REPLAY_PARAM_KEYS:
                print("unknown param '%s'" % k, file=sys.stderr)
                return EXIT_TOOLING
            params[k] = _coerce(v.strip())
    try:
        corpus = load_corpus(names)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return EXIT_TOOLING
    with tempfile.TemporaryDirectory() as td:
        ok, binary, comp = rr.build_binary(td, mode=effect, compiler=args.compiler)
        if not ok:
            print("COMPILE FAILED:\n" + (comp.get("stderr") or "")[:1200], file=sys.stderr)
            return EXIT_TOOLING
        try:
            champ, det, _ = build_champion(binary, params, corpus, names,
                                           "host-bootstrap", out_dir)
        except RenderError as e:
            print("RENDER FAILED: %s" % e, file=sys.stderr)
            return EXIT_TOOLING
        if not det:
            print("DETERMINISM FAILED: champion re-render not bit-identical", file=sys.stderr)
            return EXIT_DETERMINISM
    _atomic_write_json(champion_path(out_dir), champ)
    print("seeded champion v0 [MECHANISM] -> %s" % champion_path(out_dir))
    print("  rank_score=%.4f  white_bias_max=%.4f  half_life_min=%.2f  corpus=%s"
          % (champ["rank_score"], champ["doctrine_floors"]["white_bias_max"],
             champ["doctrine_floors"]["energy_half_life_min"], names))
    if args.json:
        print(json.dumps(champ, indent=2))
    return EXIT_OK


def cmd_run(args):
    effect = args.effect
    if effect != "bloom":
        print("only --effect bloom is wired for MVP-0", file=sys.stderr)
        return EXIT_TOOLING
    out_dir = _resolve_out(args, effect)
    names = args.corpus or DEFAULT_CORPUS
    score_names = [n for n in names if n != "silence"]
    cap = int(args.max_iterations)
    K = min(int(args.shortlist), SHORTLIST_HARD_CAP)

    try:
        space = json.loads(Path(args.space).read_text(encoding="utf-8"))
        candidates = generate(space, args.strategy, int(args.seed), cap)
        corpus = load_corpus(names)
    except (FileNotFoundError, ValueError, GridOverflow, json.JSONDecodeError) as e:
        print("USAGE/INPUT ERROR: %s" % e, file=sys.stderr)
        return EXIT_TOOLING

    with tempfile.TemporaryDirectory() as td:
        ok, binary, comp = rr.build_binary(td, mode=effect, compiler=args.compiler)
        if not ok:
            print("COMPILE FAILED:\n" + (comp.get("stderr") or "")[:1200], file=sys.stderr)
            return EXIT_TOOLING

        champion = load_champion(out_dir)
        if champion is None:
            try:
                champion, det, _ = build_champion(binary, dict(CHAMPION_DEFAULT_PARAMS),
                                                  corpus, score_names, "host-bootstrap", out_dir)
            except RenderError as e:
                print("RENDER FAILED (champion bootstrap): %s" % e, file=sys.stderr)
                return EXIT_TOOLING
            if not det:
                print("DETERMINISM FAILED (champion bootstrap)", file=sys.stderr)
                return EXIT_DETERMINISM
            _atomic_write_json(champion_path(out_dir), champion)
            print("no champion found — bootstrapped v0 [MECHANISM]")

        # determinism self-check (PRD-02 §0.2): champion params must re-render identically
        c1 = render_corpus(binary, champion["params"], {n: corpus[n] for n in score_names})
        c2 = render_corpus(binary, champion["params"], {n: corpus[n] for n in score_names})
        if {n: frame_hash(c1[n]) for n in score_names} != {n: frame_hash(c2[n]) for n in score_names}:
            print("DETERMINISM SELF-CHECK FAILED — host not bit-identical", file=sys.stderr)
            return EXIT_DETERMINISM

        t0 = time.time()
        survivors, rej = [], Counter()
        for cand in candidates:
            params = {**champion["params"], **cand}
            try:
                rendered = render_corpus(binary, params, {n: corpus[n] for n in score_names})
            except RenderError:
                rej["render_fail"] += 1
                continue
            try:
                panels, agg = score_corpus(rendered, score_names)
            except RenderError:
                rej["render_fail"] += 1
                continue
            v = decide(agg, champion)
            if v["decision"] == "REJECT":
                rej[v["reason"]] += 1
                continue
            if v["decision"] == "ITERATE":
                rej["iterate"] += 1
                continue
            survivors.append({"params": params, "delta": cand, "panels": panels,
                              "agg": agg, "rank_score": agg["rank_score"],
                              "hash": params_hash(params)[:12]})

        survivors.sort(key=lambda c: c["rank_score"], reverse=True)
        shortlist = survivors[:K]
        wall = round(time.time() - t0, 2)

        # results.json (one canonical file, OVERWRITE)
        results = {
            "effect": effect,
            "run": {
                "seed": int(args.seed), "max_iterations": cap,
                "strategy": args.strategy or "grid+fallback", "shortlist_cap": K,
                "corpus": score_names, "rendered": len(candidates),
                "wall_seconds": wall, "aggregation": "0.5*mean+0.5*min",
                "weights_version": WEIGHTS_VERSION, "tier": "host",
                "epistemic": "[MECHANISM] — ranks only; not [MEASURED]; not a ship decision",
            },
            "champion": {"hash": champion["params_hash"][:12], "version": champion["champion_version"],
                         "params": champion["params"], "rank_score": champion["rank_score"]},
            "shortlist": [{
                "rank": i + 1, "hash": c["hash"], "rank_score": round(c["rank_score"], 6),
                "delta_vs_champion": round(c["rank_score"] - champion["rank_score"], 6),
                "param_diff": c["delta"], "params": c["params"], "agg": c["agg"],
                "per_fixture": c["panels"],
            } for i, c in enumerate(shortlist)],
            "rejection_histogram": dict(rej),
            "changelog": [{
                "date": time.strftime("%Y-%m-%d", time.gmtime()), "by": "loop.py",
                "note": "ran %d candidates; %d survivor(s); shortlist %d; champion v%s unchanged"
                        % (len(candidates), len(survivors), len(shortlist),
                           champion["champion_version"]),
            }],
        }
        _atomic_write_json(out_dir / "results.json", results)

        sheet = None
        if not args.no_contact_sheet and shortlist:
            # Render the plates on broadband-swell when available (the dim swell the
            # rated lgp_real_render samples used — clear peak frame); else fixture 0.
            fx0 = "broadband-swell" if "broadband-swell" in score_names else score_names[0]
            for c in shortlist:
                c["render_hexes"] = render_corpus(
                    binary, c["params"], {fx0: corpus[fx0]})[fx0]
            # Shared contrasting TOP edge (magenta palette bloom) for the dual-channel
            # plate look, rendered once on the same fixture. Plate path only (skipped
            # for the legacy --strips view).
            top_hexes = None
            if not getattr(args, "strips", False):
                top_hexes = render_corpus(
                    binary, CONTACT_TOP_PARAMS, {fx0: corpus[fx0]})[fx0]
            sheet = render_contact_sheet(out_dir, effect, fx0,
                                         c1[fx0], champion, shortlist,
                                         strips=getattr(args, "strips", False),
                                         top_hexes=top_hexes)

    print("ran %d candidates | %d survivor(s) | shortlist %d | %.1fs"
          % (len(candidates), len(survivors), len(shortlist), wall))
    print("  rejections: %s" % (dict(rej) or "none"))
    print("  results  -> %s" % (out_dir / "results.json"))
    if sheet:
        print("  contact  -> %s   (open in a browser — terminal aesthetic gate)" % sheet)
    for c in shortlist:
        print("  rank %d  %s  score=%.4f (%+.4f)  %s"
              % (shortlist.index(c) + 1, c["hash"], c["rank_score"],
                 c["rank_score"] - champion["rank_score"],
                 ", ".join("%s=%s" % (k, v) for k, v in c["delta"].items()) or "(==champion)"))
    if args.json:
        print(json.dumps(results, indent=2))
    return EXIT_OK if shortlist else EXIT_NO_SURVIVOR


def cmd_promote(args):
    effect = args.effect
    out_dir = _resolve_out(args, effect)
    champ = load_champion(out_dir)
    res_path = out_dir / "results.json"
    if champ is None or not res_path.exists():
        print("need an existing champion.json and results.json under %s" % out_dir, file=sys.stderr)
        return EXIT_TOOLING
    results = json.loads(res_path.read_text(encoding="utf-8"))
    chosen = None
    ref = args.candidate
    for c in results["shortlist"]:
        if str(c["rank"]) == str(ref) or c["hash"].startswith(str(ref)):
            chosen = c
            break
    if chosen is None:
        print("candidate '%s' not in shortlist (ranks 1..%d / hashes)"
              % (ref, len(results["shortlist"])), file=sys.stderr)
        return EXIT_TOOLING
    new_ver = champ["champion_version"] + 1
    agg = chosen["agg"]
    new = dict(champ)
    new.update({
        "champion_version": new_ver,
        "promoted_utc": _iso_now(),
        "promoted_by": "captain",
        "params": chosen["params"],
        "params_hash": params_hash(chosen["params"]),
        "panel": chosen["per_fixture"],
        "rank_score": chosen["rank_score"],
        "doctrine_floors": {"white_bias_max": agg["white_bias_mean"],
                            "energy_half_life_min": agg["half_life"]},
        "supersedes": champ["champion_version"],
    })
    new["changelog"] = champ.get("changelog", []) + [{
        "version": new_ver, "utc": _iso_now(), "by": "captain",
        "note": "promoted shortlist rank %d (%s) — host [MECHANISM] floor; "
                "device [MEASURED] certification still REQUIRED before ship"
                % (chosen["rank"], chosen["hash"]),
    }]
    _atomic_write_json(champion_path(out_dir), new)
    print("promoted rank %d (%s) -> champion v%d" % (chosen["rank"], chosen["hash"], new_ver))
    print("  WARNING: tier_of_record=host [MECHANISM]. This is a regression FLOOR, "
          "not a ship decision. On-device [MEASURED] certification still required.")
    return EXIT_OK


def cmd_list(args):
    try:
        space = json.loads(Path(args.space).read_text(encoding="utf-8"))
        cands = generate(space, "grid", 10 ** 9, 10 ** 9)  # full grid for listing
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print("USAGE/INPUT ERROR: %s" % e, file=sys.stderr)
        return EXIT_TOOLING
    print("space '%s' -> %d grid points over %s"
          % (args.space, len(cands), sorted((space.get("params") or {}).keys())))
    for c in cands[:50]:
        print("  " + ", ".join("%s=%s" % (k, v) for k, v in c.items()))
    if len(cands) > 50:
        print("  ... (%d more)" % (len(cands) - 50))
    return EXIT_OK


def cmd_show(args):
    out_dir = _resolve_out(args, args.effect or "bloom")
    res_path = out_dir / "results.json"
    if not res_path.exists():
        print("no results.json under %s" % out_dir, file=sys.stderr)
        return EXIT_TOOLING
    results = json.loads(res_path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(results, indent=2))
        return EXIT_OK
    r = results["run"]
    print("effect=%s  rendered=%d  shortlist=%d  %.1fs  weights=%s"
          % (results["effect"], r["rendered"], len(results["shortlist"]),
             r["wall_seconds"], r["weights_version"]))
    print("champion v%s rank=%.4f" % (results["champion"]["version"], results["champion"]["rank_score"]))
    for c in results["shortlist"]:
        print("  rank %d  %s  score=%.4f (%+.4f)  %s"
              % (c["rank"], c["hash"], c["rank_score"], c["delta_vs_champion"],
                 ", ".join("%s=%s" % (k, v) for k, v in c["param_diff"].items()) or "(==champion)"))
    print("rejections: %s" % (results["rejection_histogram"] or "none"))
    return EXIT_OK


def cmd_regress(args):
    """LAYER-1 commit-gate building block: render the CHAMPION's own params against
    the CURRENT effect source and verify it still holds the champion's doctrine
    floor. This is what the pre-commit gate calls when a light_mode_*/render source
    change is staged. Exit 0 = floor held; 2 = floor breached (BLOCK the commit);
    3 = determinism broke; 1 = tooling / no baseline. [MECHANISM] — objective
    regression only; never an aesthetic judgement."""
    effect = args.effect
    if effect != "bloom":
        print("only --effect bloom is wired for MVP-0", file=sys.stderr)
        return EXIT_TOOLING
    out_dir = _resolve_out(args, effect)
    champ = load_champion(out_dir)
    if champ is None:
        print("no champion baseline under %s — run 'loop.py seed-champion' first"
              % out_dir, file=sys.stderr)
        return EXIT_TOOLING
    names = args.corpus or champ.get("fixture_corpus") or DEFAULT_CORPUS
    score_names = [n for n in names if n != "silence"]
    try:
        corpus = load_corpus(score_names)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return EXIT_TOOLING

    with tempfile.TemporaryDirectory() as td:
        ok, binary, comp = rr.build_binary(td, mode=effect, compiler=args.compiler)
        if not ok:
            print("COMPILE FAILED:\n" + (comp.get("stderr") or "")[:1200], file=sys.stderr)
            return EXIT_TOOLING
        try:
            r1 = render_corpus(binary, champ["params"], {n: corpus[n] for n in score_names})
            r2 = render_corpus(binary, champ["params"], {n: corpus[n] for n in score_names})
        except RenderError as e:
            print("RENDER FAILED: %s" % e, file=sys.stderr)
            return EXIT_TOOLING
        fh = {n: frame_hash(r1[n]) for n in score_names}
        if fh != {n: frame_hash(r2[n]) for n in score_names}:
            print("DETERMINISM FAILED — host not bit-identical", file=sys.stderr)
            return EXIT_DETERMINISM
        _, agg = score_corpus(r1, score_names)

    floors = champ["doctrine_floors"]
    breaches = []
    if agg["liveness_fail"]:
        breaches.append("dead_effect")
    if agg["white_bias_mean"] > floors["white_bias_max"] * (1 + DOCTRINE_MARGIN):
        breaches.append("colour_clarity")
    if agg["half_life"] < floors["energy_half_life_min"] * (1 - DOCTRINE_MARGIN):
        breaches.append("motion_memory")
    if agg["rank_score"] < champ["rank_score"] - KEEP_MARGIN:
        breaches.append("rank_regression")

    comparable = (score_names == champ.get("fixture_corpus")
                  and WEIGHTS_VERSION == champ.get("weights_version"))
    drift = comparable and fh != champ.get("frame_hashes")

    print("regress %s vs champion v%s [MECHANISM]: rank %.4f (floor %.4f) | "
          "white_bias %.4f (max %.4f) | half_life %.2f (min %.2f)"
          % (effect, champ["champion_version"], agg["rank_score"], champ["rank_score"],
             agg["white_bias_mean"], floors["white_bias_max"],
             agg["half_life"], floors["energy_half_life_min"]))
    if not comparable:
        print("  INCOMPARABLE baseline (weights/corpus changed) — re-seed champion; not blocking.")
        return EXIT_OK
    if drift:
        print("  drift: champion params now render different bytes (source changed the "
              "render); floor still checked below — consider re-seeding if intentional.")
    if breaches:
        print("  REGRESSION — champion floor breached: %s  (commit should BLOCK)"
              % ", ".join(breaches))
        return EXIT_NO_SURVIVOR
    print("  champion floor held.")
    return EXIT_OK


def _coerce(v):
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="edit->render->score->regress->rank->shortlist")
    pr.add_argument("--effect", default="bloom")
    pr.add_argument("--space",
                    default=str(HARNESS / "spaces" / "bloom_palette.json"),
                    help="sweep-space JSON (default: spaces/bloom_palette.json — the "
                         "palette axis is the one that makes columns VISIBLY distinct; "
                         "mood/sat/chroma micro-tweaks cluster into near-identical looks)")
    pr.add_argument("--corpus", nargs="*", help="fixture names (default: %s)" % DEFAULT_CORPUS)
    pr.add_argument("--max-iterations", type=int, default=64)
    pr.add_argument("--shortlist", type=int, default=5)
    pr.add_argument("--strategy", choices=["grid", "random"], default=None)
    pr.add_argument("--seed", type=int, default=42)
    pr.add_argument("--out", default=None)
    pr.add_argument("--compiler", default=None)
    pr.add_argument("--no-contact-sheet", action="store_true")
    pr.add_argument("--strips", action="store_true",
                    help="legacy raw LED-strip contact sheet (default = K1 LGP plate render)")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_run)

    ps = sub.add_parser("seed-champion", help="render+score defaults -> champion.json v0")
    ps.add_argument("--effect", default="bloom")
    ps.add_argument("--corpus", nargs="*")
    ps.add_argument("--params", default=None, help="key=val,key=val overrides")
    ps.add_argument("--out", default=None)
    ps.add_argument("--compiler", default=None)
    ps.add_argument("--json", action="store_true")
    ps.set_defaults(func=cmd_seed_champion)

    pp = sub.add_parser("promote", help="promote a shortlist candidate to champion")
    pp.add_argument("--effect", default="bloom")
    pp.add_argument("--candidate", required=True, help="shortlist rank (int) or hash prefix")
    pp.add_argument("--out", default=None)
    pp.set_defaults(func=cmd_promote)

    pl = sub.add_parser("list", help="enumerate a sweep space's grid points")
    pl.add_argument("--effect", default="bloom")
    pl.add_argument("--space", required=True)
    pl.set_defaults(func=cmd_list)

    psh = sub.add_parser("show", help="print the last run's results")
    psh.add_argument("--effect", default="bloom")
    psh.add_argument("--out", default=None)
    psh.add_argument("--json", action="store_true")
    psh.set_defaults(func=cmd_show)

    prg = sub.add_parser("regress", help="check the current effect source vs the champion "
                                         "floor (Layer-1 commit-gate building block)")
    prg.add_argument("--effect", default="bloom")
    prg.add_argument("--corpus", nargs="*")
    prg.add_argument("--out", default=None)
    prg.add_argument("--compiler", default=None)
    prg.set_defaults(func=cmd_regress)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
