"""8-bit-grid incandescent equivalence: legacy *255 vs Lever-2 high byte of *65535.

Rounding law (frozen): legacy truncates (ch * factor * 255) toward 0 to uint8;
Lever-2 takes the high byte of trunc(ch * factor * 65535). Inputs are exactly
representable in 8 bits (ch = k/255). Lookup is firmware constants.h
incandescent_lookup = {1.0000, 0.4453, 0.1562} — not invented.

Accepted delta is 0 or ±1. Cells that need ±1 are listed in
ACCEPTED_PLUSMINUS_ONE below — that is the law, not a later fudge.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from lever2_host import (  # noqa: E402
    INCANDESCENT_LOOKUP,
    legacy_quantize_8,
    lever2_prepack_u16,
    requantize_u8,
)

K_VALUES = (0, 1, 2, 127, 128, 254, 255)
MIX_VALUES = (0.0, 0.10, 0.25)
CHANNELS = ("r", "g", "b")

# High byte of *65535 vs trunc(*255): these 8-bit-grid cells differ by ±1.
# That is the accepted rounding law, not a later fudge.
ACCEPTED_PLUSMINUS_ONE = {
    (127, 0.1, "g"),
    (128, 0.1, "g"),
    (128, 0.25, "b"),
    (254, 0.1, "b"),
    (254, 0.1, "g"),
    (254, 0.25, "b"),
    (254, 0.25, "g"),
    (255, 0.1, "b"),
    (255, 0.1, "g"),
    (255, 0.25, "g"),
}


def _cells():
    for k in K_VALUES:
        ch_f = k / 255.0
        for mix in MIX_VALUES:
            for name, lookup in zip(CHANNELS, INCANDESCENT_LOOKUP):
                yield k, mix, name, ch_f, lookup


def test_firmware_lookup_constants_not_invented():
    src = (
        ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
    ).read_text(encoding="utf-8")
    assert "1.0000" in src and "0.4453" in src and "0.1562" in src
    assert INCANDESCENT_LOOKUP == (1.0000, 0.4453, 0.1562)


def test_8bit_grid_lever2_matches_legacy_within_rounding_law():
    """High byte after *65535 vs legacy *255. Delta 0 or the listed ±1 cells."""
    mismatches = []
    plusminus = set()
    for k, mix, name, ch_f, lookup in _cells():
        legacy = legacy_quantize_8(ch_f, mix, lookup)
        lever = requantize_u8(lever2_prepack_u16(ch_f, mix, lookup))
        delta = lever - legacy
        cell = (k, mix, name)
        if delta == 0:
            continue
        if abs(delta) == 1:
            plusminus.add(cell)
            continue
        mismatches.append((cell, legacy, lever, delta))
    assert mismatches == [], f"deltas outside ±1: {mismatches}"
    unexpected = plusminus - ACCEPTED_PLUSMINUS_ONE
    missing = ACCEPTED_PLUSMINUS_ONE - plusminus
    assert unexpected == set() and missing == set(), (
        f"±1 cells changed. got={sorted(plusminus)!r} "
        f"accepted={sorted(ACCEPTED_PLUSMINUS_ONE)!r}"
    )
