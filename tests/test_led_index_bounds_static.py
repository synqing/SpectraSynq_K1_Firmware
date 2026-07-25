"""Audit M1.3 — LED-index out-of-bounds hardening in the render path.

Three shared render helpers in visual/led_utilities.h indexed / sized 160-element
(NATIVE_RESOLUTION) CRGB/CRGB16 buffers with no bounds guard:

  * lerp_led_16()   — index_right = index_whole + 1 could reach NATIVE_RESOLUTION
                      (1-past-end read) at the top pixel of a secondary strip
                      where SECONDARY_LED_COUNT != NATIVE_RESOLUTION.
  * shift_leds_up() / shift_leds_down() — an offset > NATIVE_RESOLUTION makes the
                      unsigned (NATIVE_RESOLUTION - offset) wrap to a huge size →
                      catastrophic OOB memcpy.

Under the shipping 160/160 config these are LATENT (index_right stays <=159;
callers pass offset <= NATIVE_RESOLUTION/2), but they are reachable under the
custom 61/91/224 strip configs and any future caller. This test proves (a) the
guards are present in source and (b) the clamp arithmetic keeps every index /
offset in-bounds while remaining a no-op across the valid range (so the shipping
config's output is unchanged). Pattern mirrors test_gdft_int64_*: numeric replica
of the exact firmware expression + regex tying the replica to the source.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
LED_UTILS = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
CONSTANTS = (FW / "system" / "constants.h").read_text(encoding="utf-8")

NR = 160  # NATIVE_RESOLUTION; re-asserted against source below.


# --- exact replicas of the firmware clamp expressions -----------------------
def lerp_clamp(index_whole):
    """Replica of lerp_led_16's index_left/index_right guard."""
    index_left = index_whole
    index_right = index_whole + 1
    if index_left < 0:
        index_left = 0
    if index_right < 0:
        index_right = 0
    if index_left > NR - 1:
        index_left = NR - 1
    if index_right > NR - 1:
        index_right = NR - 1
    return index_left, index_right


def shift_clamp(offset):
    """Replica of shift_leds_up/down's underflow guard (uint16 offset)."""
    if offset > NR:
        offset = NR
    return offset


class LedIndexBoundsTest(unittest.TestCase):
    # --- 0: the constant the guards depend on -------------------------------
    def test_native_resolution_is_160(self):
        self.assertRegex(CONSTANTS, r"#define\s+NATIVE_RESOLUTION\s+160")

    # --- 1: source carries the lerp_led_16 bounds guard ---------------------
    def test_lerp_led_16_source_has_bounds_guard(self):
        self.assertRegex(LED_UTILS, r"if\s*\(index_left\s*<\s*0\)\s*index_left\s*=\s*0;")
        self.assertRegex(LED_UTILS, r"if\s*\(index_right\s*<\s*0\)\s*index_right\s*=\s*0;")
        self.assertRegex(
            LED_UTILS,
            r"if\s*\(index_left\s*>\s*NATIVE_RESOLUTION\s*-\s*1\)\s*index_left\s*=\s*NATIVE_RESOLUTION\s*-\s*1;")
        self.assertRegex(
            LED_UTILS,
            r"if\s*\(index_right\s*>\s*NATIVE_RESOLUTION\s*-\s*1\)\s*index_right\s*=\s*NATIVE_RESOLUTION\s*-\s*1;")

    # --- 2: source carries the shift underflow guard (both helpers) ---------
    def test_shift_leds_source_has_underflow_guard(self):
        guard = "if (offset > NATIVE_RESOLUTION) offset = NATIVE_RESOLUTION;"
        self.assertGreaterEqual(
            LED_UTILS.count(guard), 2,
            "both shift_leds_up and shift_leds_down must clamp offset")

    # --- 3: clamp keeps every lerp index in [0, NR-1] -----------------------
    def test_lerp_clamp_never_out_of_bounds(self):
        for iw in range(-300, 400):
            left, right = lerp_clamp(iw)
            self.assertTrue(0 <= left <= NR - 1, f"index_left OOB for index_whole={iw}")
            self.assertTrue(0 <= right <= NR - 1, f"index_right OOB for index_whole={iw}")

    # --- 4: clamp is a no-op across the valid interior (output unchanged) ---
    def test_lerp_clamp_noop_in_valid_range(self):
        for iw in range(0, NR - 1):  # index_right = iw+1 stays <= NR-1
            left, right = lerp_clamp(iw)
            self.assertEqual((left, right), (iw, iw + 1),
                             f"clamp must not alter valid interior index {iw}")

    # --- 5: shift clamp never underflows (NR - offset) across uint16 -------
    def test_shift_clamp_never_underflows(self):
        for off in range(0, 65536):
            c = shift_clamp(off)
            self.assertLessEqual(c, NR)
            self.assertGreaterEqual(NR - c, 0, f"(NR - offset) underflows for offset={off}")

    # --- 6: shift clamp is a no-op for the valid offset range --------------
    def test_shift_clamp_noop_in_valid_range(self):
        for off in range(0, NR + 1):
            self.assertEqual(shift_clamp(off), off, f"clamp must not alter valid offset {off}")


if __name__ == "__main__":
    unittest.main()
