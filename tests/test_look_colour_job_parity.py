"""
Colour-job parity: WS2812 sibling look library vs WS2816 RPL look library.

Both libraries must perform the same conceptual jobs on shared paint samples:
  - Slot 0: identity (both libraries)
  - Slot 1 (shared 1D inv-γ): G lifts on Naberius gold, greys stay grey
  - Slot 2 (tungsten RGB): grey channel-splits, R up / B down

This module proves the HOST REPLICAS of both libraries agree on job direction
(lift vs cut, grey-preserving vs channel-split) for the K1 paint samples.
It does NOT prove photon accuracy on hardware. The separation of
"job correctness" from "photons on the plate" is deliberate: host tests
own the job; device rtrace dumps (if present) own the buffer.

Paint samples used:
  - Naberius gold  (255, 140, 0)   — stop 212 in K1_Naberius_Gold_gp
  - Mid grey       (128, 128, 128)
  - White          (255, 255, 255)
  - Black          (  0,   0,   0)
  - Vepar magenta  (255,  70, 150) — exercises non-gold non-grey chromatic path

WS2812 domain: u8 (0-255), direct LUT lookup.
RPL domain:    u16 (0-65535), interpolated from cube-spaced / identity-abscissa nodes.
Bridge:        u8_to_u16(v) = v * 257.  sign() checks are domain-independent.

Rtrace dump scorer (tests test_rtrace_*): scores the hex dumps in
docs/forensics/look-parity-rtrace-20260826/ (or the working _scratch copy).
Missing pack → skip with a truthful reason. Malformed/incomplete pack → fail.
Never synthesise replacement dump data. Ceiling is JOB_ONLY, not photon parity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Tuple

import pytest

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Import host replicas
# ---------------------------------------------------------------------------
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))

from look_ws2812_lut import (  # noqa: E402
    NABERIUS_GOLD,
    apply_u8,
    slot_channels,
)
from ws2816_degamma_lut import apply_u16 as degamma_u16  # noqa: E402
from look_tungsten_lut import apply_rgb as tungsten_rgb  # noqa: E402

WS_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look_ws2812.h"

RTRACE_SCRATCH = ROOT / "_scratch" / "look-parity-rtrace-20260826"
RTRACE_TRACKED = ROOT / "docs" / "forensics" / "look-parity-rtrace-20260826"
REQUIRED_DUMPS = (
    "rpl_slot0_dump.txt",
    "rpl_slot1_dump.txt",
    "rpl_slot2_dump.txt",
    "bench_slot0_dump.txt",
    "bench_slot1_dump.txt",
    "bench_slot2_dump.txt",
)


def rtrace_pack_dir():
    """Prefer the tracked evidence pack; fall back to the working scratch copy."""
    for candidate in (RTRACE_TRACKED, RTRACE_SCRATCH):
        if candidate.is_dir():
            return candidate
    return None


RTRACE_DIR = rtrace_pack_dir()

# ---------------------------------------------------------------------------
# Paint samples
# ---------------------------------------------------------------------------
GOLD = NABERIUS_GOLD            # (255, 140, 0) — Naberius Gold stop 212
MID_GREY = (128, 128, 128)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
VEPAR_MAGENTA = (255, 70, 150)  # Vepar-ish, exercises non-grey chromatic path

ALL_SAMPLES = (GOLD, MID_GREY, WHITE, BLACK, VEPAR_MAGENTA)


# ---------------------------------------------------------------------------
# Host replica of RPL (WS2816) look-apply for jobs-only comparison
# ---------------------------------------------------------------------------

def rpl_apply_u16(slot: int, r_u8: int, g_u8: int, b_u8: int) -> Tuple[int, int, int]:
    """Apply RPL look library, input u8 paint → output u16.

    Converts u8 paint into u16 via * 257, then applies the RPL slot.
    Slots beyond 2 are identity (not yet populated in Phase A).
    """
    r16, g16, b16 = r_u8 * 257, g_u8 * 257, b_u8 * 257
    if slot == 0:
        return r16, g16, b16
    if slot == 1:
        # RPL slot 1 = cube-spaced k1_ws2816_degamma_u16 (shared 1D).
        return degamma_u16(r16), degamma_u16(g16), degamma_u16(b16)
    if slot == 2:
        # RPL slot 2 = tungsten RGB 1D, gains R 1.18 / G 1.00 / B 0.78.
        return tungsten_rgb(r16, g16, b16)
    return r16, g16, b16


def rpl_apply_u8(slot: int, r_u8: int, g_u8: int, b_u8: int) -> Tuple[int, int, int]:
    """RPL output rounded back to u8 for direction comparisons."""
    r16, g16, b16 = rpl_apply_u16(slot, r_u8, g_u8, b_u8)
    return r16 // 257, g16 // 257, b16 // 257


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sign(x: int) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


# ===========================================================================
# 1. Slot 1 lifts G on Naberius gold — both libraries, same sign
# ===========================================================================

def test_slot1_gold_g_lifts_ws2812():
    """WS2812 slot 1 must increase G on Naberius gold (not cut it)."""
    gold0 = apply_u8(0, *GOLD)
    gold1 = apply_u8(1, *GOLD)
    delta_g = gold1[1] - gold0[1]
    assert delta_g > 0, (
        f"WS2812 slot 1 cut G on gold: delta_g={delta_g} "
        f"(slot0={gold0}, slot1={gold1})"
    )


def test_slot1_gold_g_lifts_rpl():
    """RPL (WS2816) slot 1 must increase G on Naberius gold (same job)."""
    gold0 = rpl_apply_u16(0, *GOLD)
    gold1 = rpl_apply_u16(1, *GOLD)
    delta_g_u16 = gold1[1] - gold0[1]
    assert delta_g_u16 > 0, (
        f"RPL slot 1 cut G on gold (u16): delta_g={delta_g_u16} "
        f"(slot0_G={gold0[1]}, slot1_G={gold1[1]})"
    )


def test_slot1_gold_g_sign_is_same_on_both_libraries():
    """RPL and WS2812 slot-1 must agree on the SIGN of ΔG for Naberius gold.

    Both are inverse-γ 2.2 shared-1D functions; both must LIFT G.
    Exact values differ (u8 vs u16 domain) but direction must match.
    """
    ws2_delta = apply_u8(1, *GOLD)[1] - apply_u8(0, *GOLD)[1]
    rpl_delta = rpl_apply_u16(1, *GOLD)[1] - rpl_apply_u16(0, *GOLD)[1]
    assert _sign(ws2_delta) == _sign(rpl_delta) == 1, (
        f"Library sign mismatch on gold G: ws2812 delta={ws2_delta}, rpl delta={rpl_delta}"
    )


# ===========================================================================
# 2. Slot 1 exact value — not the old green-cut stub
# ===========================================================================

def test_ws2812_gold_lift_exact_g_value():
    """WS2812 GOLD_LIFT table: G[140] must equal 194.

    This is the known value for inv-γ 2.2 applied to 140/255.
    """
    g_table = slot_channels(1)[1]
    assert g_table[140] == 194, (
        f"G[140]={g_table[140]}, expected 194"
    )


def test_ws2812_g140_not_old_green_cut_stub():
    """G[140] must NOT equal the old green-cut value (140 * 220) // 255 = 120.

    The 220/255 multiplier was the stub that actively cut G on gold. Any
    table that reproduces it has regressed.
    """
    g_table = slot_channels(1)[1]
    old_cut = (140 * 220) // 255  # = 120
    assert g_table[140] != old_cut, (
        f"G[140]={g_table[140]} equals the old cut stub {old_cut}; "
        "green-cut regression detected"
    )


# ===========================================================================
# 3. Slot 1 must not be a naive WS2816-to-u8 downscale
# ===========================================================================

def test_ws2812_g_table_is_not_naive_ws2816_downsample():
    """WS2812 GOLD_LIFT G table must NOT be identical to naively downscaling
    the WS2816 cube-spaced degamma table into u8.

    If someone copied WS2816 degamma_u16(i*257)//257 into the WS2812 table,
    the tables would differ at dark values where cube-spacing and uniform-256
    spacing diverge. This test rejects that path.
    """
    ws2812_g = slot_channels(1)[1]
    naive_copy = bytes(degamma_u16(i * 257) // 257 for i in range(256))
    assert ws2812_g != naive_copy, (
        "WS2812 G table is bit-identical to naive WS2816-to-u8 downscale; "
        "the table must be generated from shared_inv_gamma() on a uniform-256 grid, "
        "not copied from the cube-spaced WS2816 LUT."
    )
    # The first few dark entries must differ (this is where cube vs uniform diverges).
    diffs = [(i, ws2812_g[i], naive_copy[i]) for i in range(1, 20) if ws2812_g[i] != naive_copy[i]]
    assert len(diffs) >= 1, (
        "No dark-value differences found between WS2812 G table and naive copy; "
        "expected at least one divergent entry in indices 1-19"
    )


# ===========================================================================
# 4. WS2812 header must not include the WS2816 degamma header
# ===========================================================================

def test_ws2812_header_excludes_ws2816_degamma():
    """k1_look_ws2812.h must not #include k1_ws2816_degamma.h.

    The libraries are isolated by construction; sharing the header would
    contaminate the ABI boundary and could re-introduce u16 degamma tables
    into the u8 loom path.
    """
    src = WS_H.read_text(encoding="utf-8")
    assert '#include "k1_ws2816_degamma.h"' not in src, (
        "k1_look_ws2812.h must not include k1_ws2816_degamma.h"
    )


# ===========================================================================
# 5. Shared-1D greys stay grey — both libraries
# ===========================================================================

@pytest.mark.parametrize("grey_val", [64, 128, 192])
def test_slot1_grey_stays_grey_ws2812(grey_val):
    """WS2812 slot 1 (shared 1D) must map grey to grey."""
    r, g, b = apply_u8(1, grey_val, grey_val, grey_val)
    assert r == g == b, (
        f"WS2812 slot 1 broke grey({grey_val}): got ({r},{g},{b})"
    )


@pytest.mark.parametrize("grey_val", [64, 128, 192])
def test_slot1_grey_stays_grey_rpl(grey_val):
    """RPL slot 1 (shared 1D) must map grey to grey in u16 domain."""
    r16, g16, b16 = rpl_apply_u16(1, grey_val, grey_val, grey_val)
    # RPL uses the same 1D function per channel, so iso-grey input → iso-grey output.
    assert r16 == g16 == b16, (
        f"RPL slot 1 broke grey({grey_val}): got ({r16},{g16},{b16})"
    )


# ===========================================================================
# 6. Slot 2 (tungsten) breaks grey — both libraries
# ===========================================================================

def test_slot2_tungsten_splits_grey_ws2812():
    """WS2812 slot 2 must channel-split mid grey (R high, B low)."""
    r, g, b = apply_u8(2, *MID_GREY)
    assert r != b, f"WS2812 slot 2 did not split grey: ({r},{g},{b})"
    assert r > g, f"WS2812 slot 2: R should be > G for tungsten grey: ({r},{g},{b})"
    assert g > b, f"WS2812 slot 2: G should be > B for tungsten grey: ({r},{g},{b})"


def test_slot2_tungsten_splits_grey_rpl():
    """RPL slot 2 must channel-split mid grey in u16 domain."""
    r16, g16, b16 = rpl_apply_u16(2, *MID_GREY)
    assert r16 != b16, f"RPL slot 2 did not split grey: ({r16},{g16},{b16})"
    assert r16 > g16, f"RPL slot 2: R should be > G for tungsten grey: ({r16},{g16},{b16})"
    assert g16 > b16, f"RPL slot 2: G should be > B for tungsten grey: ({r16},{g16},{b16})"


def test_slot2_tungsten_sign_is_same_on_both_libraries():
    """Both libraries' slot-2 must agree: tungsten warms (R up, B down) on grey."""
    r_ws, g_ws, b_ws = apply_u8(2, *MID_GREY)
    r_rpl, g_rpl, b_rpl = rpl_apply_u8(2, *MID_GREY)
    # R should be greater than G in both
    assert r_ws > g_ws and r_rpl > g_rpl, (
        f"Tungsten R-vs-G sign mismatch: ws2812=({r_ws},{g_ws},{b_ws}), rpl=({r_rpl},{g_rpl},{b_rpl})"
    )
    # B should be less than G in both
    assert b_ws < g_ws and b_rpl < g_rpl, (
        f"Tungsten B-vs-G sign mismatch: ws2812=({r_ws},{g_ws},{b_ws}), rpl=({r_rpl},{g_rpl},{b_rpl})"
    )


# ===========================================================================
# 7. Black and white lock — both libraries, both slots
# ===========================================================================

@pytest.mark.parametrize("slot", [0, 1, 2])
def test_black_locks_ws2812(slot):
    assert apply_u8(slot, 0, 0, 0) == (0, 0, 0), f"WS2812 slot {slot} broke black"


@pytest.mark.parametrize("slot", [0, 1, 2])
def test_white_locks_ws2812(slot):
    assert apply_u8(slot, 255, 255, 255) == (255, 255, 255), f"WS2812 slot {slot} broke white"


@pytest.mark.parametrize("slot", [0, 1, 2])
def test_black_locks_rpl(slot):
    r16, g16, b16 = rpl_apply_u16(slot, 0, 0, 0)
    assert (r16, g16, b16) == (0, 0, 0), f"RPL slot {slot} broke black"


@pytest.mark.parametrize("slot", [0, 1, 2])
def test_white_locks_rpl(slot):
    r16, g16, b16 = rpl_apply_u16(slot, 255, 255, 255)
    assert (r16, g16, b16) == (65535, 65535, 65535), f"RPL slot {slot} broke white"


# ===========================================================================
# 8. All paint samples — slot 1 lifts all channels vs identity on both libraries
# ===========================================================================

@pytest.mark.parametrize("sample", [GOLD, VEPAR_MAGENTA], ids=["gold", "vepar_magenta"])
def test_slot1_lifts_nonblack_channels_ws2812(sample):
    """WS2812 slot 1 must lift every non-zero channel on chromatic samples."""
    s0 = apply_u8(0, *sample)
    s1 = apply_u8(1, *sample)
    for i, ch in enumerate("RGB"):
        if s0[i] > 0 and s0[i] < 255:
            assert s1[i] > s0[i], (
                f"WS2812 slot 1 did not lift {ch} for {sample}: "
                f"slot0={s0}, slot1={s1}"
            )


@pytest.mark.parametrize("sample", [GOLD, VEPAR_MAGENTA], ids=["gold", "vepar_magenta"])
def test_slot1_lifts_nonblack_channels_rpl(sample):
    """RPL slot 1 must lift every non-zero channel on chromatic samples (u16 domain)."""
    s0 = rpl_apply_u16(0, *sample)
    s1 = rpl_apply_u16(1, *sample)
    for i, ch in enumerate("RGB"):
        if s0[i] > 0 and s0[i] < 65535:
            assert s1[i] > s0[i], (
                f"RPL slot 1 did not lift {ch} for {sample}: "
                f"slot0_u16={s0}, slot1_u16={s1}"
            )


# ===========================================================================
# 9. Rtrace dump scorer — score the real hex dumps (JOB_ONLY ceiling)
# ===========================================================================

from look_parity_rtrace import parity_verdict, score_device  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts" / "regression-harness"))
from score_rtrace_occupancy import (  # noqa: E402
    parse_rtrace_occupancy,
    score_occupancy,
)


def _require_pack() -> Path:
    pack = rtrace_pack_dir()
    if pack is None:
        pytest.skip(
            "rtrace dump pack absent "
            f"(looked in {RTRACE_TRACKED} and {RTRACE_SCRATCH})"
        )
    missing = [name for name in REQUIRED_DUMPS if not (pack / name).is_file()]
    if missing:
        pytest.fail(
            f"rtrace pack at {pack} is incomplete; missing {missing}. "
            "Do not synthesise replacement dumps."
        )
    return pack


@pytest.mark.skipif(
    rtrace_pack_dir() is None,
    reason="rtrace dump pack absent "
    f"(looked in {RTRACE_TRACKED} and {RTRACE_SCRATCH})",
)
def test_rtrace_pack_has_required_hex_dumps():
    """The pack must contain all six named hex dumps. Incomplete = fail."""
    pack = _require_pack()
    for name in REQUIRED_DUMPS:
        path = pack / name
        assert path.stat().st_size > 0, f"{path} is empty"
        head = path.read_text(encoding="utf-8", errors="replace")[:80]
        assert "RTRACE-BEGIN" in head, f"{path} is not an rtrace hex dump"


@pytest.mark.skipif(
    rtrace_pack_dir() is None,
    reason="rtrace dump pack absent "
    f"(looked in {RTRACE_TRACKED} and {RTRACE_SCRATCH})",
)
def test_rtrace_slot1_gold_job_is_job_only():
    """Score the real dumps with the production scorer. Ceiling is JOB_ONLY.

    Both lanes must LIFT green on gold-region pixels and move R/G toward
    MORE_GOLDEN. Photon-level / FULL parity is not a pass condition.
    """
    pack = _require_pack()
    rpl = score_device(
        "RPL_9087A500_WS2816",
        {
            0: pack / "rpl_slot0_dump.txt",
            1: pack / "rpl_slot1_dump.txt",
            2: pack / "rpl_slot2_dump.txt",
        },
    )
    bench = score_device(
        "BENCH_B489A500_WS2812",
        {
            0: pack / "bench_slot0_dump.txt",
            1: pack / "bench_slot1_dump.txt",
            2: pack / "bench_slot2_dump.txt",
        },
    )
    verdict = parity_verdict(rpl, bench)

    assert rpl.get("gold_direction") == "LIFT", rpl
    assert bench.get("gold_direction") == "LIFT", bench
    assert rpl.get("gold_rg_direction") == "MORE_GOLDEN", rpl
    assert bench.get("gold_rg_direction") == "MORE_GOLDEN", bench
    assert verdict["verdict"] == "JOB_ONLY", verdict
    assert verdict["verdict"] != "FULL"
    assert "Cannot claim FULL" in verdict["reason"] or "not comparable" in verdict["reason"]

    measured = pack / "MEASURED.json"
    if measured.is_file():
        recorded = json.loads(measured.read_text(encoding="utf-8"))
        assert recorded.get("parity", {}).get("verdict") == "JOB_ONLY"


@pytest.mark.skipif(
    rtrace_pack_dir() is None,
    reason="rtrace dump pack absent "
    f"(looked in {RTRACE_TRACKED} and {RTRACE_SCRATCH})",
)
def test_rtrace_rpl_occupancy_is_true16():
    """RPL rgb16hex dump must score PASS_TRUE16 on the occupancy scorer."""
    pack = _require_pack()
    path = pack / "rpl_slot1_dump.txt"
    fmt, frames, _dropped = parse_rtrace_occupancy(str(path))
    assert fmt == "rgb16hex", f"RPL dump fmt={fmt}, expected rgb16hex"
    assert frames, f"{path} produced no rgb16hex frames"
    rec = score_occupancy(frames)
    assert rec["verdict"] == "PASS_TRUE16", rec
