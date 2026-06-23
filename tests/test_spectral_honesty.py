"""Tasks A-D: DFT/STFT measurement-honesty for the K1 Goertzel AP path.

Compiles the REAL firmware header
SPECTRASYNQ_K1_FIRMWARE/audio/k1_spectral_honesty.h (via the host probe
scripts/regression-harness/spectral_honesty_probe.cpp) and asserts the
metadata/leakage/windowing contract. No Python re-implementation of the math,
so the test cannot drift from the firmware. Also parity-checks that the
sample-rate constant the metadata is computed against matches the firmware
#define (the noise_cal_quality_model pattern).
"""

import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
HEADER_DIR = FW / "audio"
PROBE = ROOT / "scripts" / "regression-harness" / "spectral_honesty_probe.cpp"
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text(encoding="utf-8")
SYSTEM_H = (FW / "system" / "system.h").read_text(encoding="utf-8")


def _define_number(text, name):
    match = re.search(rf"#define\s+{re.escape(name)}\s+([^\s/]+)", text)
    assert match, f"missing #define {name}"
    raw = re.sub(r"[fFuUlL]+$", "", match.group(1))
    return float(raw) if "." in raw else int(raw)


def _compiler():
    for cc in ("c++", "clang++", "g++"):
        if shutil.which(cc):
            return cc
    return None


def _build_and_run():
    cc = _compiler()
    assert cc, "no host C++ compiler (c++/clang++/g++) found"
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        exe = Path(td) / "spectral_honesty_probe"
        compile_cmd = [
            cc, "-std=c++17", "-O2",
            f"-I{HEADER_DIR}",
            str(PROBE), "-o", str(exe),
        ]
        subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
        proc = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
    out = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[0]] = float(parts[1])
    return out


class SpectralHonestyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = _build_and_run()

    # --- parity: metadata computed against the real firmware sample rate ----
    def test_sample_rate_matches_firmware_define(self):
        fs = _define_number(CONFIG_TYPES, "DEFAULT_SAMPLE_RATE")
        # true_resolution(512) = fs/512; reverse it out of the probe value.
        self.assertAlmostEqual(self.v["A_true_res_512"] * 512.0, fs, places=2)

    # --- Task A: DFT metadata -----------------------------------------------
    def test_true_resolution_is_rate_over_window(self):
        self.assertAlmostEqual(self.v["A_true_res_512"], 12800.0 / 512.0, places=3)
        self.assertAlmostEqual(self.v["A_true_res_2000"], 12800.0 / 2000.0, places=3)

    def test_bin_spacing_equals_rate_over_fft_n(self):
        self.assertAlmostEqual(self.v["A_bin_spacing_512"], 12800.0 / 512.0, places=3)

    def test_resolution_and_spacing_equal_when_no_padding(self):
        # fft_n == window_n => the two are identical (no zero-padding).
        self.assertAlmostEqual(self.v["A_true_res_512"], self.v["A_bin_spacing_512"], places=4)

    # --- Task B: zero-padding cannot inflate confidence ---------------------
    def test_padding_shrinks_bin_spacing_but_not_resolution(self):
        # bin spacing halves/quarters with fft_n...
        self.assertAlmostEqual(self.v["B_bin_spacing_pad2"], self.v["B_bin_spacing_pad1"] / 2.0, places=3)
        self.assertAlmostEqual(self.v["B_bin_spacing_pad4"], self.v["B_bin_spacing_pad1"] / 4.0, places=3)
        # ...while true resolution is INVARIANT (tied to the real window length).
        self.assertEqual(self.v["B_true_res_pad1"], self.v["B_true_res_pad2"])
        self.assertEqual(self.v["B_true_res_pad1"], self.v["B_true_res_pad4"])
        self.assertNotAlmostEqual(self.v["B_true_res_pad2"], self.v["B_bin_spacing_pad2"], places=3)

    def test_zero_padding_factor(self):
        self.assertAlmostEqual(self.v["B_zpf_pad1"], 1.0, places=4)
        self.assertAlmostEqual(self.v["B_zpf_pad2"], 2.0, places=4)
        self.assertAlmostEqual(self.v["B_zpf_pad4"], 4.0, places=4)

    # --- Task C: endpoint leakage risk --------------------------------------
    def test_matched_frame_has_lower_leakage_than_mismatched(self):
        self.assertLess(self.v["C_risk_matched"], self.v["C_risk_mismatched"])
        # periodic-in-window frame is near zero; aperiodic frame is clearly raised.
        self.assertLess(self.v["C_risk_matched"], 0.05)
        self.assertGreater(self.v["C_risk_mismatched"], 0.2)
        self.assertGreaterEqual(self.v["C_risk_matched"], 0.0)
        self.assertLessEqual(self.v["C_risk_mismatched"], 1.0)

    def test_leakage_risk_independent_of_fft_n(self):
        # Same window re-evaluated is identical: leakage depends only on the real
        # window, there is no fft_n knob that could inflate it.
        self.assertEqual(self.v["C_risk_matched"], self.v["C_risk_matched_again"])

    # --- Task D: windowing path ---------------------------------------------
    def test_hann_window_shape(self):
        self.assertAlmostEqual(self.v["D_w_first"], 0.0, places=4)
        self.assertAlmostEqual(self.v["D_w_last"], 0.0, places=4)
        self.assertGreater(self.v["D_w_centre"], 0.99)

    def test_hann_coherent_gain_is_explicit_half(self):
        # Discrete-window mean approaches the continuous coherent gain 0.5 as
        # N grows (off by ~1/N for finite N); K1_HANN_COHERENT_GAIN = 0.5 is the
        # theoretical compensation factor used in the gated GDFT path.
        self.assertAlmostEqual(self.v["D_coherent_gain"], 0.5, delta=0.02)
        self.assertEqual(self.v["D_declared_coherent_gain"], 0.5)
        # power gain of a Hann window ~= 0.375 (3/8).
        self.assertAlmostEqual(self.v["D_power_gain"], 0.375, delta=0.01)

    # --- Task (Captain follow-up): per-bin block -> Hann index mapping -------
    # Proves the ACTUAL firmware mapping (k1_hann_window_mult +
    # k1_hann_lookup_index, used by precompute_goertzel_constants() and the GDFT
    # loop) lands the first/last samples of each block on both Hann zero
    # endpoints (index 0 and 4095) — not just that k1_hann_window_gain() is a
    # correct Hann.
    def test_block_endpoints_map_to_hann_zero_indices(self):
        for bs in (32, 512, 2000):  # small/high-freq, medium, capped
            self.assertEqual(self.v[f"E_map_{bs}_first"], 0,
                             f"block_size={bs}: first sample must map to index 0")
            self.assertEqual(self.v[f"E_map_{bs}_last"], 4095,
                             f"block_size={bs}: last sample must map to index 4095")

    def test_mapped_endpoint_indices_are_hann_zeros(self):
        # The indices the mapping targets are the window's zero endpoints.
        self.assertAlmostEqual(self.v["E_w_at_0"], 0.0, places=5)
        self.assertAlmostEqual(self.v["E_w_at_4095"], 0.0, places=5)

    def test_every_block_size_hits_far_endpoint(self):
        # Full sweep [2, 2000]: 0 failures. Pure truncation failed on 287 sizes
        # (the latent bug the 3-size sample alone would miss); the rounded
        # mapping must hit index 4095 for every block_size.
        self.assertEqual(self.v["E_sweep_fail_count"], 0)

    # --- Goertzel bin frequency honesty (target vs actual vs error) ---------
    def test_bin_k_rounds_target_to_integer_dft_index(self):
        # block_size=128 @ 12.8kHz: 128*440/12800 = 4.4 -> k = round = 4.
        self.assertEqual(self.v["F_k_128_440"], 4)

    def test_actual_center_differs_from_target_by_rounding(self):
        # k=4 -> actual centre = 4*12800/128 = 400 Hz (not the 440 Hz label).
        self.assertAlmostEqual(self.v["F_actual_128_440"], 400.0, places=3)
        self.assertAlmostEqual(self.v["F_err_128_440"], -40.0, places=3)
        # error == actual - target (definitional consistency).
        self.assertAlmostEqual(
            self.v["F_err_128_440"], self.v["F_actual_128_440"] - 440.0, places=4)

    def test_on_bin_target_has_zero_error(self):
        # 128*400/12800 = 4.0 exactly -> k=4 -> actual 400 -> error 0.
        self.assertAlmostEqual(self.v["F_err_128_400"], 0.0, places=4)

    def test_larger_window_has_smaller_error_bound(self):
        # block_size 2000 -> cell 6.4 Hz -> |error| <= 3.2 Hz (vs 50 Hz at 128).
        self.assertLessEqual(abs(self.v["F_err_2000_440"]), 0.5 * (12800.0 / 2000.0) + 1e-3)

    def test_error_is_bounded_by_half_resolution_cell_for_all_bins(self):
        # |error| <= 0.5 * (fs/block_size) for every swept bin; the worst case
        # actually reaches the bound (tight, not vacuous).
        self.assertEqual(self.v["F_bound_fail_count"], 0)
        self.assertLessEqual(self.v["F_max_error_cell_ratio"], 1.001)
        self.assertGreater(self.v["F_max_error_cell_ratio"], 0.9)

    def test_helper_k_formula_matches_firmware(self):
        # Static parity: the helper mirrors precompute_goertzel_constants()'s k.
        self.assertRegex(
            SYSTEM_H,
            r"\(int\)\(0\.5\s*\+\s*\(\(frequencies\[i\]\.block_size\s*\*\s*"
            r"frequencies\[i\]\.target_freq\)\s*/\s*CONFIG\.SAMPLE_RATE\)\)",
        )


if __name__ == "__main__":
    unittest.main()
