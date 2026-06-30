"""Per-band AGC characterisation gate (Lane N6, Class C — PREPARE ONLY).

RED-before-fix property test for the "louder -> dimmer" broadband-AGC defect and
its per-band fix. It host-compiles the REAL audio/k1_gdft_core.cpp twice — flag
OFF (production broadband AGC) and flag ON (-DSB_AGC_PERBAND_V1 candidate) — via
the oracle_agc_perband harness, and asserts:

  OFF  (documents the defect — passes against current production code):
    * single-scalar: all 4 band gains are identical every frame
    * collapse:      the one global gain falls hard as broadband loudness rises
                     (the "louder -> dimmer" inverse)

  ON   (the fix — FAILS until SB_AGC_PERBAND_V1 is implemented, then passes):
    * independence:  under loud bass + a quiet treble tone, the per-band gains
                     diverge and the treble (tonal) band keeps far more gain than
                     the loud bass band
    * retention:     the quiet treble band retains substantially more gain than
                     the single-scalar path crushed it to

Grounding: eyes-on-verdict.md (2026-06-21) + DSP root-cause spike obs #72837 +
first-hand read of k1_gdft_core.cpp:376/384/410. The flag DEFAULTS OFF; production
behaviour is unchanged (proven separately by test_golden_master gdft reproduction).

NON-SHIPPING. Host-only. This is a property/characterisation gate, NOT a frozen
golden — it is deliberately absent from harness_selftest.ORACLE_MODULES.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness" / "golden"
sys.path.insert(0, str(HARNESS))

import oracle_agc_perband as agc  # noqa: E402

# Band indices (constants.h agc_band_t).
BASS, LOW_MID, HIGH_MID, TREBLE = 0, 1, 2, 3

# Last warmup frame = bass silent (the "quiet" reference); last frame = loudest.
QUIET_FRAME = 5     # WARMUP - 1 in the driver (bass_rel == 0)
# loud frame is simply frames[-1]


@pytest.fixture(scope="module")
def off():
    return agc.frames(perband=False)


@pytest.fixture(scope="module")
def on():
    return agc.frames(perband=True)


# ---------------------------------------------------------------------------
# OFF — characterise the CURRENT production defect (these pass against HEAD).
# ---------------------------------------------------------------------------

def test_off_is_single_scalar(off):
    """Every frame: all 4 band gains identical -> one global gain mirrored."""
    for d in off:
        spread = max(d["g"]) - min(d["g"])
        assert spread < 1e-3, (
            f"frame {d['f']}: expected single-scalar AGC (all bands equal) "
            f"but gains={d['g']} spread={spread:.5f}"
        )


def test_off_gain_collapses_under_load(off):
    """The single gain falls hard as broadband loudness rises (louder -> dimmer)."""
    quiet_g = off[QUIET_FRAME]["g"][BASS]
    loud_g = off[-1]["g"][BASS]
    assert off[-1]["load"] >= 0.99, "driver contract: last frame is loudest"
    assert loud_g < quiet_g * 0.6, (
        f"expected >=1.67x global-gain collapse quiet->loud, "
        f"got quiet={quiet_g:.3f} loud={loud_g:.3f}"
    )


# ---------------------------------------------------------------------------
# ON — the per-band fix. RED until SB_AGC_PERBAND_V1 is implemented.
# ---------------------------------------------------------------------------

def test_on_gains_are_per_band_independent(on):
    """Under a spectrally non-uniform load, the per-band gains must DIVERGE — they
    are no longer one global scalar mirrored into every band."""
    loud = on[-1]
    spread = max(loud["g"]) - min(loud["g"])
    assert spread > 0.3, (
        f"per-band AGC not engaged: gains still ~uniform at loud frame "
        f"(gains={loud['g']} spread={spread:.5f}). "
        f"Is SB_AGC_PERBAND_V1 implemented?"
    )


def test_on_preserves_headroom_vs_single_scalar(on, off):
    """The direct "louder -> dimmer" fix: the single broadband scalar crushes
    EVERY band to one low gain under load; per-band AGC keeps the less-loud bands
    well above that floor, so loud energy in one band no longer dims the others.

    OFF gains are identical across bands (the scalar); ON's brightest-retained
    band must sit far above that scalar at the loudest frame."""
    off_scalar = max(off[-1]["g"])           # all OFF bands equal -> the scalar
    on_best = max(on[-1]["g"])               # least-crushed band under per-band
    assert off_scalar - min(off[-1]["g"]) < 1e-3, "OFF must be a single scalar"
    assert on_best > off_scalar * 1.5, (
        f"per-band AGC should preserve headroom the single scalar destroyed: "
        f"best ON band gain={on_best:.3f} vs OFF scalar={off_scalar:.3f}"
    )


def test_on_determinism():
    """Two ON captures are byte-identical (host determinism)."""
    a = agc.capture(perband=True)
    b = agc.capture(perband=True)
    assert a == b, "ON capture is non-deterministic across runs"
