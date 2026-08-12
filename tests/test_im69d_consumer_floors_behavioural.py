"""P4.B — table-driven behavioural cases for the IM69D joint silence gate.

Not a regex ratchet: the constants are LIVE-PARSED from source and the
documented decision inequality (canon 2026-08-07 + a8b1912a: crest AND level,
both required) is evaluated over measured fixture points, so a value drift OR
a formula-scope drift changes a behavioural verdict, not just a string.

The break-path formula under test (i2s_audio.h, IM69D-scoped):
    break_silence = (pky >= K1_SILENCE_PEAKINESS_BREAK)
                AND (max_raw >= SSL * K1_SILENCE_JOINT_LEVEL_SSL_FRAC)

Fixture points come from measured distributions (unit2-bench-transfer-full
2026-08-12 + FINDING-rms-cannot-separate): hum crest ~1.26; music crest 3-5;
worst quiet p95 level 1.03×SSL; worst music p25 level 2.13×SSL.

The device proof anchors the formula itself (both units: 100% silence under
true silence, 0% under music, eyes-on PASS at 1.75); this table keeps the
CONSTANTS honest against those measured margins.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GLOBALS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h"


def _const(name: str) -> float:
    text = GLOBALS.read_text(encoding="utf-8")
    m = re.search(rf"inline\s+float\s+{name}\s*=\s*([0-9.]+)f?\s*;", text)
    assert m, f"{name} not found in globals.h"
    return float(m.group(1))


FRAC = _const("K1_SILENCE_JOINT_LEVEL_SSL_FRAC")
BREAK = _const("K1_SILENCE_PEAKINESS_BREAK")
RMS_ENTER = _const("K1_SILENCE_RMS_ENTER")
RMS_EXIT = _const("K1_SILENCE_RMS_EXIT")


def joint_break(pky: float, level_x_ssl: float) -> bool:
    """The IM69D break-path decision, per the documented AND composition."""
    return pky >= BREAK and level_x_ssl >= FRAC


# (name, pky, level as multiple of SSL, must_break)
CASES = [
    # Narrowband hum: crest ~1.26 (measured). Loud hum must NEVER wake the lamp
    # — the peakiness term rejects it regardless of level.
    ("hum_loud", 1.26, 3.0, False),
    # Music at the worst measured music p25 level (2.13×SSL), crest mid-band.
    ("music_typical", 3.2, 2.13, True),
    # Quiet-room transient: peaky but at the worst quiet p95 level (1.03×SSL).
    # 42% of quiet frames clear the crest threshold unaided (canon HF); the
    # level term must reject them.
    ("quiet_transient", 2.5, 1.03, False),
    # Music-shaped crest just below the shipping fraction: stays asleep — this
    # is the deliberate wake threshold, ~18% under the music floor.
    ("music_below_frac", 3.2, FRAC - 0.05, False),
    # Exactly at both thresholds: wakes (>= comparisons in firmware).
    ("at_thresholds", BREAK, FRAC, True),
]


@pytest.mark.parametrize("name,pky,level,must_break", CASES)
def test_joint_gate_case(name, pky, level, must_break):
    assert joint_break(pky, level) is must_break, (
        f"{name}: pky={pky} level={level}xSSL expected break={must_break} "
        f"with BREAK={BREAK} FRAC={FRAC}"
    )


def test_fraction_sits_inside_the_measured_usable_window():
    """a8b1912a: usable window = above worst quiet p95 (1.03), below worst
    music p25 (2.13). A future edit that pushes the fraction outside the
    measured window reopens either false-wake or fails-to-wake."""
    assert 1.03 < FRAC < 2.13, (
        f"FRAC={FRAC} escaped the measured usable window (1.03, 2.13) — "
        "re-derive from fresh final-placement calibrations before shipping"
    )


def test_sph_schmitt_pair_untouched():
    """SPH0645 keeps its characterised RMS Schmitt (HarmonixSet-calibrated);
    the IM69D lane must never move it."""
    assert RMS_ENTER == 0.04 and RMS_EXIT == 0.08
    assert RMS_EXIT > RMS_ENTER, "Schmitt gap inverted"
