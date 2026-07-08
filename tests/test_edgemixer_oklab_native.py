"""EdgeMixer SB_EDGE_ROTATION_OKLAB perceptual-rotation acceptance gate.

Compiles the REAL firmware colour module
SPECTRASYNQ_K1_FIRMWARE/director/sb_edgemixer_lite.cpp on the host (via the probe
scripts/regression-harness/edgemixer_oklab_probe.cpp) and drives its actual
sb_edgemixer_lite_apply() in the OKLAB rotation space against an INDEPENDENT
double-precision, textbook-OKLab oracle (Ottosson 2020) re-implemented in the
probe. The engine and the oracle share no code, so agreement is real
cross-validation.

Acceptance is a PERCEPTUAL band, NOT the +/-1 LSB gate used for SUM_PRESERVING:
OKLab is a different, non-linear transform, so bit parity is neither expected nor
meaningful. The documented bands below are genuinely small perceptual bounds; an
implementation regression (weaker cbrt/gamma polynomials, a wrong constant) will
exceed them rather than silently pass. Mirrors the test_edgemixer_parity_native.py
host-probe convention (real g++, not Apple clang, because FixedPoints needs GCC).
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
MODULE_CPP = FW / "director" / "sb_edgemixer_lite.cpp"
PROBE = ROOT / "scripts" / "regression-harness" / "edgemixer_oklab_probe.cpp"
SHIM_DIR = ROOT / "scripts" / "regression-harness" / "edgemixer_host_shim"
FIXEDPOINTS_SRC = ROOT / "libraries" / "FixedPoints" / "src"

# --- Documented perceptual tolerance bands (see probe header for the metrics). --
# Values are integer milli-units emitted by the probe (dL/dC * 1000; degrees * 1000).
# These are small, principled PERCEPTUAL bounds (not +/-1 LSB — OKLab is a
# different transform). Measured actuals on the reference build (g++-15, -O2, host
# fixed-point path, which is bit-deterministic and representative of the device
# render path) sit far inside every band, proving margin, and the fault-evidence
# case gives the metric its teeth:
# Measured actuals on the reference build after the LUT (Task 1) + constant-L
# gamut clip (Task 2): OK_MAX_DL_M 0 | OK_MAX_DC_M 0 | OK_MAX_HUE_MDEG 94 (0.09 deg)
# RT_MAX_DIFF_M 1 (0.001) | NONTRIV 179238 (179.2 deg) | FAULT_PERTURBED 12294 (12.3 deg)
# GAMUT: OOG 29 | DL_NEW 4 (0.004) | DL_CLAMP 36 (0.036) -> chroma clip holds L ~9x
# better than the old hard clamp.
BAND_MAX_DL_M = 15        # |dL|        <= 0.015 perceptual-lightness units
BAND_MAX_DC_M = 15        # |dChroma|   <= 0.015
BAND_MAX_HUE_MDEG = 2500  # hue error   <= 2.5 degrees
BAND_RT_DIFF_M = 10       # round-trip  <= 0.010 per channel at theta = 0
MIN_NONTRIV_HUE_MDEG = 150000   # complementary must swing >= 150 degrees
MIN_FAULT_HUE_MDEG = 8000       # an injected M2 fault must exceed 8.0 degrees
# Task 2 gamut-clip quality bands.
MIN_GAMUT_OOG = 8         # enough out-of-gamut samples for the metric to mean anything
BAND_GAMUT_DL_NEW_M = 12  # chroma-reduction clip holds output L within 0.012 of ideal
GAMUT_IMPROVE_FACTOR = 2  # ...and at least 2x better than the old per-channel clamp

EXPECTED_OK_SAMPLES = 6 * 4 * 4 * 4   # 6 modes x 4^3 colour grid
EXPECTED_RT_SAMPLES = 4 * 4 * 4

# FixedPoints' in-class `static constexpr SFixed` members are rejected by Apple
# clang under -std=c++17 but accepted by real GCC (the firmware's xtensa-gcc
# lineage), exactly as in render_replay.py / test_edgemixer_parity_native.py.
GPP_CANDIDATES = ["g++-15", "g++-14", "g++-13", "g++-12", "g++"]


def _gnu_compiler():
    for cand in GPP_CANDIDATES:
        if not shutil.which(cand):
            continue
        try:
            ver = subprocess.run([cand, "--version"], capture_output=True, text=True)
        except OSError:
            continue
        if "clang" in (ver.stdout + ver.stderr).lower():
            continue  # Apple clang aliased as g++ cannot build FixedPoints
        return cand
    return None


def _build_and_run():
    cc = _gnu_compiler()
    if cc is None:
        raise unittest.SkipTest(
            "no real GNU g++ found; FixedPoints host build needs GCC, not clang "
            "(see render_replay.py)"
        )
    with tempfile.TemporaryDirectory() as td:
        exe = Path(td) / "edgemixer_oklab_probe"
        compile_cmd = [
            cc, "-std=c++17", "-O2",
            f"-I{SHIM_DIR}",
            f"-I{FIXEDPOINTS_SRC}",
            f"-I{FW / 'director'}",
            str(PROBE), str(MODULE_CPP),
            "-o", str(exe),
        ]
        subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
        proc = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
    out = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[0]] = int(parts[1])
    return out


class EdgeMixerOklabNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = _build_and_run()

    def test_probe_ran_full_battery(self):
        self.assertEqual(self.v["OK_SAMPLES"], EXPECTED_OK_SAMPLES)
        self.assertEqual(self.v["RT_SAMPLES"], EXPECTED_RT_SAMPLES)

    def test_perceptual_lightness_within_band(self):
        self.assertLessEqual(
            self.v["OK_MAX_DL_M"], BAND_MAX_DL_M,
            f"OKLab |dL| {self.v['OK_MAX_DL_M']} m-units exceeds band {BAND_MAX_DL_M}",
        )

    def test_hue_angle_within_band(self):
        self.assertLessEqual(
            self.v["OK_MAX_HUE_MDEG"], BAND_MAX_HUE_MDEG,
            f"OKLab hue error {self.v['OK_MAX_HUE_MDEG']} m-deg exceeds band "
            f"{BAND_MAX_HUE_MDEG}",
        )

    def test_chroma_within_band(self):
        self.assertLessEqual(
            self.v["OK_MAX_DC_M"], BAND_MAX_DC_M,
            f"OKLab |dChroma| {self.v['OK_MAX_DC_M']} m-units exceeds band "
            f"{BAND_MAX_DC_M}",
        )

    def test_round_trip_identity_at_theta_zero(self):
        self.assertLessEqual(
            self.v["RT_MAX_DIFF_M"], BAND_RT_DIFF_M,
            f"theta=0 round trip drifts {self.v['RT_MAX_DIFF_M']} m-units, band "
            f"{BAND_RT_DIFF_M}",
        )

    def test_rotation_is_non_trivial(self):
        # COMPLEMENTARY must actually swing the hue ~180 degrees.
        self.assertGreaterEqual(
            self.v["NONTRIV_HUE_MDEG"], MIN_NONTRIV_HUE_MDEG,
            "COMPLEMENTARY hue swing too small — the OKLab rotation is not running",
        )

    def test_fault_evidence_perturbed_constant_breaks_metric(self):
        # The correct engine sits inside the nominal band...
        self.assertLessEqual(self.v["FAULT_NOMINAL_HUE_MDEG"], BAND_MAX_HUE_MDEG)
        # ...and comparing it against a target with one M2 coefficient perturbed
        # provably blows past the band, so a wrong engine constant would be caught.
        self.assertGreaterEqual(
            self.v["FAULT_PERTURBED_HUE_MDEG"], MIN_FAULT_HUE_MDEG,
            "injected M2 coefficient fault MUST break the hue metric",
        )

    def test_gamut_clip_holds_lightness_better_than_hard_clamp(self):
        # Task 2: enough out-of-gamut COMPLEMENTARY pixels to be meaningful...
        self.assertGreaterEqual(
            self.v["GAMUT_OOG_COUNT"], MIN_GAMUT_OOG,
            "too few out-of-gamut samples to validate the gamut clip",
        )
        # ...the constant-L chroma-reduction clip holds output lightness tight...
        self.assertLessEqual(
            self.v["GAMUT_DL_NEW_M"], BAND_GAMUT_DL_NEW_M,
            f"chroma-clip |dL| {self.v['GAMUT_DL_NEW_M']} m-units exceeds band "
            f"{BAND_GAMUT_DL_NEW_M}",
        )
        # ...and is materially better than the OLD per-channel hard clamp, which
        # is the whole point of Task 2 (hard clamp shifts lightness AND hue).
        self.assertLessEqual(
            self.v["GAMUT_DL_NEW_M"] * GAMUT_IMPROVE_FACTOR,
            self.v["GAMUT_DL_CLAMP_M"],
            f"chroma clip (dL {self.v['GAMUT_DL_NEW_M']}) must beat hard clamp "
            f"(dL {self.v['GAMUT_DL_CLAMP_M']}) by >= {GAMUT_IMPROVE_FACTOR}x",
        )


if __name__ == "__main__":
    unittest.main()
