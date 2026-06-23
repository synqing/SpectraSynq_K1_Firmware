"""feat/gdft-int64-magnitude-ab: default-OFF int64 magnitude-squared path in
process_GDFT(), so sustained near-resonance Goertzel bins do not overflow int32
and clamp to zero.

Measurement/parity-only. Validates:
  1. K1_GDFT_INT64_MAGNITUDE_V1 flag exists and defaults OFF.
  2. OFF (#else) path preserves the legacy int32 magnitude formula verbatim.
  3. ON (#if) path uses int64 casts before q1*q1 and q2*q2.
  4. Synthetic resonance: legacy int32 wraps/clamps to 0 (wrong); int64 stays
     positive and equals the full-precision truth; and for small q (no overflow)
     the two paths AGREE (int64 changes nothing when there is no overflow).
  5. K1_GDFT_TRUE_CENTER_V1 remains default-OFF (no coupled flip).
  (6. The full 574-test suite staying green is checked by the suite itself.)

The numeric replicas live in scripts/regression-harness/gdft_true_center_scalloping.py
and mirror the firmware integer semantics (int32/int64 wrapping) exactly.
"""

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
GDFT_H = (FW / "audio" / "GDFT.h").read_text(encoding="utf-8")
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text(encoding="utf-8")
SIM_PATH = ROOT / "scripts" / "regression-harness" / "gdft_true_center_scalloping.py"

spec = importlib.util.spec_from_file_location("gdft_true_center_scalloping", SIM_PATH)
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)


class GdftInt64MagnitudeTest(unittest.TestCase):
    # --- 1: flag exists, default OFF -----------------------------------------
    def test_flag_defined_default_off(self):
        self.assertRegex(
            CONFIG_TYPES,
            r"#ifndef\s+K1_GDFT_INT64_MAGNITUDE_V1\s*\n\s*#define\s+K1_GDFT_INT64_MAGNITUDE_V1\s+0")

    # --- 2: OFF (#else) preserves the legacy int32 formula verbatim ----------
    def test_off_path_formula_verbatim(self):
        self.assertRegex(GDFT_H, r"#if\s+K1_GDFT_INT64_MAGNITUDE_V1")
        self.assertRegex(GDFT_H, r"#else")
        self.assertRegex(GDFT_H, r"mult\s*=\s*coeff_q14\s*\*\s*\(int32_t\)q1;")
        self.assertRegex(
            GDFT_H,
            r"magnitudes\[i\]\s*=\s*q2\s*\*\s*q2\s*\+\s*q1\s*\*\s*q1\s*-\s*"
            r"\(\(int32_t\)\(mult\s*>>\s*14\)\)\s*\*\s*q2;")
        self.assertRegex(GDFT_H, r"magnitudes\[i\]\s*=\s*sqrtf\(\(float\)magnitudes\[i\]\);")

    # --- 3: ON (#if) uses int64 casts before the squares ---------------------
    def test_on_path_uses_int64(self):
        self.assertRegex(GDFT_H, r"\(int64_t\)q2\s*\*\s*\(int64_t\)q2")
        self.assertRegex(GDFT_H, r"\(int64_t\)q1\s*\*\s*\(int64_t\)q1")
        self.assertRegex(GDFT_H, r"\(int64_t\)coeff_q14\s*\*\s*\(int64_t\)q1")
        self.assertRegex(GDFT_H, r"magnitudes\[i\]\s*=\s*sqrtf\(\(float\)mag2\);")

    # --- 4: resonance overflow vs int64 correctness --------------------------
    def test_resonance_legacy_clamps_int64_stays_correct(self):
        # Device-scale resonance values (q ~ 160k, bin23/24 coeff_q14).
        cases = [(160000, 160000, 32152), (150000, 158000, 32152), (130000, 140000, 32075)]
        for q1, q2, c in cases:
            legacy = sim.magnitude2_int32_legacy(q1, q2, c)
            i64 = sim.magnitude2_int64(q1, q2, c)
            true = sim.magnitude2_true(q1, q2, c)
            self.assertEqual(legacy, 0, f"legacy should overflow->clamp to 0 for {q1,q2,c}")
            self.assertGreater(i64, 0, "int64 magnitude must be positive at resonance")
            self.assertEqual(i64, true, "int64 path must equal the full-precision truth")
            self.assertNotEqual(legacy, true, "legacy must differ (it lost the real magnitude)")

    def test_no_overflow_paths_agree(self):
        # Where q is small enough that int32 does not overflow, the int64 path must
        # produce byte-identical results -> it changes nothing for correct cases.
        for q1, q2, c in [(0, 0, 32152), (1000, 900, 32152), (5000, 4800, 32075), (-3000, 2500, 31988)]:
            self.assertEqual(sim.magnitude2_int32_legacy(q1, q2, c),
                             sim.magnitude2_int64(q1, q2, c),
                             f"paths must agree (no overflow) for {q1,q2,c}")

    # --- 5: true-center stays default-OFF (no coupled flip) ------------------
    def test_true_center_remains_default_off(self):
        self.assertRegex(
            CONFIG_TYPES,
            r"#ifndef\s+K1_GDFT_TRUE_CENTER_V1\s*\n\s*#define\s+K1_GDFT_TRUE_CENTER_V1\s+0")


if __name__ == "__main__":
    unittest.main()
