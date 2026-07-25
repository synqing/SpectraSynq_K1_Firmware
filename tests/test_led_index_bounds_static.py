"""Audit M1.3 — LED-index out-of-bounds hardening in the render path.

Four shared render helpers in visual/led_utilities.h index / size 160-element
(NATIVE_RESOLUTION) CRGB/CRGB16 buffers with no bounds guard:

  * lerp_led_16()  — index_right = index_whole + 1 could reach NATIVE_RESOLUTION
                     (1-past-end read) at the top pixel.
  * unmirror()     — identical index_right = index_whole + 1 OOB pattern.
  * shift_leds_up() / shift_leds_down() — offset > NATIVE_RESOLUTION makes the
                     unsigned (NATIVE_RESOLUTION - offset) wrap to a huge size →
                     catastrophic OOB memcpy.

REACHABILITY (honest, verified 2026-07-25 by adversarial review): these are
LATENT in ALL current build configs, not "reachable under 61/91/224":
  - lerp_led_16's only caller (scale_to_secondary_strip) sits behind
    `if (SECONDARY_LED_COUNT == NATIVE_RESOLUTION) {memcpy} else {lerp}`, and
    SECONDARY_LED_COUNT is hardcoded == NATIVE_RESOLUTION (globals.h), so the lerp
    branch is dead in every env; the custom-224 build drops the secondary channel.
  - every shift_leds_up caller passes offset <= NATIVE_RESOLUTION/2; shift_leds_down
    and unmirror have zero callers.
This is DEFENSIVE hardening of a real OOB class the audit flagged (M1.3); it
becomes live only if a secondary strip with SECONDARY_LED_COUNT > NATIVE_RESOLUTION
or a new out-of-range caller is added. The guards are exact no-ops across the
valid range, so shipping output is byte-identical.

This test proves (a) the guards are present AND uncommented in source and (b) the
clamp arithmetic keeps every index / offset in-bounds while remaining a no-op
across the valid range. Pattern mirrors test_gdft_int64_*: numeric replica of the
exact firmware expression + regex tying the replica to the source. The source
regexes are statement-anchored (^\\s*if) so a commented-out clamp cannot satisfy
them (line-comment resistant; a /* */ block comment is not detected — regex, not
a parser).
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
    """Replica of the lerp_led_16 / unmirror index_left/index_right guard."""
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

    # --- 1: index clamp present + UNCOMMENTED in BOTH interpolators ----------
    # ^\s*if anchors to a real statement (a leading // breaks the match), and
    # count >= 2 requires it in both lerp_led_16 AND unmirror.
    def test_index_clamp_present_in_both_interpolators(self):
        clamps = [
            r"^\s*if\s*\(index_left\s+<\s*0\)\s*index_left\s*=\s*0;",
            r"^\s*if\s*\(index_right\s+<\s*0\)\s*index_right\s*=\s*0;",
            r"^\s*if\s*\(index_left\s+>\s*NATIVE_RESOLUTION\s*-\s*1\)\s*index_left\s*=\s*NATIVE_RESOLUTION\s*-\s*1;",
            r"^\s*if\s*\(index_right\s+>\s*NATIVE_RESOLUTION\s*-\s*1\)\s*index_right\s*=\s*NATIVE_RESOLUTION\s*-\s*1;",
        ]
        for expr in clamps:
            n = len(re.findall(expr, LED_UTILS, re.M))
            self.assertGreaterEqual(
                n, 2, f"uncommented clamp must appear in BOTH lerp_led_16 and unmirror: {expr!r} (found {n})")

    # --- 2: shift underflow guard present + UNCOMMENTED in both helpers ------
    def test_shift_underflow_guard_present_in_both(self):
        n = len(re.findall(
            r"^\s*if\s*\(offset\s*>\s*NATIVE_RESOLUTION\)\s*offset\s*=\s*NATIVE_RESOLUTION;", LED_UTILS, re.M))
        self.assertGreaterEqual(
            n, 2, f"uncommented offset clamp must appear in both shift_leds_up and shift_leds_down (found {n})")

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
