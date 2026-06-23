"""feat/gdft-int64-recurrence-ab: default-OFF int64 recurrence-multiply for the
Goertzel inner loop, so `coeff_q14 * q1` cannot overflow int32 before the int64
store. Companion to K1_GDFT_INT64_MAGNITUDE_V1 (separate flag).

Validates:
  1. K1_GDFT_INT64_RECURRENCE_V1 exists and defaults OFF.
  2. OFF (#else) recurrence preserves the legacy formula verbatim.
  3. ON (#if) recurrence casts coeff_q14 and q1 to int64 before the multiply.
  4. Synthetic resonance: the legacy int32 recurrence multiply OVERFLOWS (wraps).
  5. Synthetic resonance: the int64 recurrence multiply does NOT overflow.
  6. q0 (q-state) stays inside int32 for the harness tones -> the proven bug is the
     MULTIPLY width, not the q range. (A failure here would demand a wider-q pass.)
  (7. The full suite staying green is checked by the suite itself.)

Numeric replicas live in scripts/regression-harness/gdft_true_center_scalloping.py.
"""

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
# GDFT.h bodies were lifted WHOLE & VERBATIM into k1_gdft_core.cpp (2026-06-23
# Phase A Lane 1); the recurrence arithmetic asserted here now lives in the .cpp TU.
GDFT_H = (FW / "audio" / "k1_gdft_core.cpp").read_text(encoding="utf-8")
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text(encoding="utf-8")
SIM_PATH = ROOT / "scripts" / "regression-harness" / "gdft_true_center_scalloping.py"

spec = importlib.util.spec_from_file_location("gdft_true_center_scalloping", SIM_PATH)
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

INT32_MAX = 0x7FFFFFFF


class GdftInt64RecurrenceTest(unittest.TestCase):
    # --- 1: flag exists, default OFF -----------------------------------------
    def test_flag_defined_default_off(self):
        self.assertRegex(
            CONFIG_TYPES,
            r"#ifndef\s+K1_GDFT_INT64_RECURRENCE_V1\s*\n\s*#define\s+K1_GDFT_INT64_RECURRENCE_V1\s+0")

    # --- 2: OFF (#else) preserves the legacy recurrence verbatim -------------
    def test_off_recurrence_verbatim(self):
        self.assertRegex(GDFT_H, r"#if\s+K1_GDFT_INT64_RECURRENCE_V1")
        self.assertRegex(GDFT_H, r"mult\s*=\s*coeff_q14\s*\*\s*\(int32_t\)q1;")
        self.assertRegex(
            GDFT_H,
            r"q0\s*=\s*\(sample\s*>>\s*6\)\s*\+\s*\(mult\s*>>\s*14\)\s*-\s*q2;")

    # --- 3: ON (#if) casts to int64 before the multiply ----------------------
    def test_on_recurrence_int64(self):
        self.assertRegex(GDFT_H, r"mult\s*=\s*\(int64_t\)coeff_q14\s*\*\s*\(int64_t\)q1;")
        self.assertRegex(GDFT_H, r"int64_t\s+q0_64\s*=")
        self.assertRegex(GDFT_H, r"q0\s*=\s*\(int32_t\)q0_64;")
        # post-loop coeff term stays int64 when the magnitude flag is on
        self.assertRegex(GDFT_H, r"\(int64_t\)coeff_q14\s*\*\s*\(int64_t\)q1\)\s*>>\s*14")

    # --- 4 + 5: legacy multiply overflows; int64 multiply does not -----------
    def test_recurrence_multiply_overflow_vs_int64(self):
        # Device-scale resonance: q1 ~ 160k, coeff_q14 ~ 32k -> product ~5.1e9 > INT32_MAX.
        for coeff_q14, q1 in [(32152, 160000), (32075, 140000), (31988, 158000)]:
            legacy = sim.recurrence_mult_int32_legacy(coeff_q14, q1)
            i64 = sim.recurrence_mult_int64(coeff_q14, q1)
            true = sim.recurrence_mult_true(coeff_q14, q1)
            self.assertGreater(true, INT32_MAX, "test premise: product must exceed int32")
            self.assertNotEqual(legacy, true, "legacy int32 multiply must overflow/wrap")  # #4
            self.assertEqual(i64, true, "int64 multiply must equal the true product")       # #5

    def test_no_overflow_multiply_agrees(self):
        # Small q1: no overflow -> legacy and int64 agree (int64 changes nothing).
        for coeff_q14, q1 in [(32152, 1000), (32075, -2000), (31988, 0)]:
            self.assertEqual(sim.recurrence_mult_int32_legacy(coeff_q14, q1),
                             sim.recurrence_mult_int64(coeff_q14, q1))

    # --- 6: q-state stays inside int32 for the harness tones ----------------
    def test_q0_state_stays_in_int32(self):
        # If ANY of these exceeds int32, q-STATE itself overflows and a separate
        # wider-q (q0/q1/q2) pass is required -- this test would then HARD-FAIL.
        cases = [
            ("off", 415.3, 23), ("off", 440.0, 25), ("off", 466.16, 26),
            ("on", 415.3, 23), ("on", 440.0, 24), ("on", 466.16, 25),
        ]
        worst = 0
        for mode, f, b in cases:
            mq = sim.recurrence_max_abs_q0(f, b, mode)
            worst = max(worst, mq)
            self.assertLess(mq, INT32_MAX,
                            f"q0 exceeds int32 for {mode} {f}Hz bin{b} -> needs a wider-q pass")
        # Sanity: the proven failure is the MULTIPLY (q1*coeff ~5e9), not q-state (~1.6e5).
        self.assertLess(worst, 1_000_000, "q-state should be ~1e5, far below int32")


if __name__ == "__main__":
    unittest.main()
