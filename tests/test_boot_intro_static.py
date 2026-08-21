import re
import unittest
from pathlib import Path

from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
INO = FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino"
SYSTEM_H = FIRMWARE / "system.h"
LED_UTILITIES_H = FIRMWARE / "led_utilities.h"


def read(path):
    return path.read_text(encoding="utf-8")


def intro_region():
    source = read(LED_UTILITIES_H)
    start = source.index("inline float intro_clamp01")
    end = source.index("inline void run_transition_fade")
    return source[start:end]


class TestBootIntroStatic(unittest.TestCase):
    def test_intro_runs_after_secondary_registration_and_before_led_task(self):
        system_h = read(SYSTEM_H)
        self.assertNotIn("intro_animation();", system_h)

        setup = read(INO)
        setup_start = setup.index("void setup()")
        setup_end = setup.index("void led_thread")
        setup = setup[setup_start:setup_end]
        intro_pos = setup.index("intro_animation();")
        self.assertLess(setup.index("init_secondary_leds();"), intro_pos)
        self.assertLess(setup.index("ENABLE_SECONDARY_LEDS = true;"), intro_pos)
        self.assertLess(setup.index("FastLED.setCorrection(TypicalLEDStrip);"), intro_pos)
        self.assertLess(intro_pos, setup.index("xTaskCreatePinnedToCore"))
        self.assertIn("#if K1_RMT_ALLOC_ON_VP_CORE_V1", setup)
        self.assertLess(setup.index("#if K1_RMT_ALLOC_ON_VP_CORE_V1"), intro_pos)
        self.assertLess(setup.index("#else"), intro_pos)

    def test_rmt_vp_intro_runs_on_led_thread_before_wdt(self):
        """Main RPL (K1_RMT_ALLOC_ON_VP_CORE_V1) plays intro on Core 1, not setup."""
        source = read(INO)
        led_start = source.index("void led_thread")
        loop_start = source.index("while (true) {", led_start)
        led_head = source[led_start:loop_start]
        self.assertIn("#if K1_RMT_ALLOC_ON_VP_CORE_V1", led_head)
        self.assertIn("intro_animation();", led_head)
        self.assertIn('USBSerial.println("INTRO: vp_core");', led_head)
        self.assertIn("CONFIG.BOOT_ANIMATION == true", led_head)
        intro_pos = led_head.index("intro_animation();")
        wdt_pos = source.index("esp_task_wdt_add", led_start)
        self.assertLess(led_start + intro_pos, wdt_pos)
        self.assertLess(wdt_pos, source.index("while (true) {", led_start))

    def test_intro_writes_and_clears_both_channels(self):
        region = intro_region()
        self.assertIn("leds_16_secondary", region)
        self.assertIn("clear_intro_led_buffers()", region)
        self.assertIn("show_leds();", region)
        self.assertRegex(region, r"intro_draw_centre_band\s*\(\s*leds_16\s*,")
        self.assertRegex(region, r"intro_draw_centre_band\s*\(\s*leds_16_secondary\s*,")

    def test_intro_is_centre_origin_not_linear_sweep(self):
        region = intro_region()
        self.assertIn("const uint16_t centre_left = (NATIVE_RESOLUTION / 2) - 1;", region)
        self.assertIn("const uint16_t centre_right = NATIVE_RESOLUTION / 2;", region)
        self.assertIn("centre_left - offset", region)
        self.assertIn("centre_right + offset", region)
        self.assertNotIn("pos * NATIVE_RESOLUTION", region)
        self.assertNotIn("(cos(", region)
        self.assertNotIn("(sin(", region)

    def test_intro_does_not_reintroduce_hue_wheel_particles(self):
        region = intro_region()
        forbidden = (
            r"\bhsv\s*\(\s*prog\b",
            r"\bhsv\s*\(\s*progress\b",
            r"\bCHSV\s*\(",
            r"particle_count",
            r"i\s*/\s*float\s*\(",
            r"fill_rainbow",
        )
        hits = [pattern for pattern in forbidden if re.search(pattern, region)]
        self.assertEqual(hits, [])

    def test_intro_has_warm_centre_origin_bounce(self):
        region = intro_region()
        self.assertIn("inline float intro_bounce_radius", region)
        self.assertIn("launch - retreat", region)
        self.assertIn("primary_radius = intro_bounce_radius(t, half_extent", region)
        self.assertIn("secondary_radius = intro_bounce_radius(t - (params.secondary_phase", region)
        # Warm centre-origin palette is now centralised in VPMLRenderParams defaults
        # (primary 1.00/0.38/0.04, secondary 1.00/0.76/0.10) and applied via params.
        self.assertIn("intro_make_colour(params.primary_red, params.primary_green, params.primary_blue", region)
        self.assertIn("intro_make_colour(params.secondary_red, params.secondary_green, params.secondary_blue", region)
        self.assertIn("    1.00f,\n    0.38f,\n    0.04f,", region)
        self.assertIn("    1.00f,\n    0.76f,\n    0.10f,", region)
        self.assertIn("edge_hit", region)
        self.assertIn("centre_catch", region)

    def test_intro_helpers_are_boot_bounded_and_heap_free(self):
        region = intro_region()
        forbidden = (
            r"\bnew\s*(?:\(|[A-Za-z_])",
            r"\bmalloc\s*\(",
            r"\bcalloc\s*\(",
            r"\brealloc\s*\(",
            r"\bfree\s*\(",
            r"\bString\b",
            r"#\s*include\s*[<\"].*WiFi",
            r"\bUSBSerial\.",
        )
        hits = [pattern for pattern in forbidden if re.search(pattern, region)]
        self.assertEqual(hits, [])
        self.assertIn("const uint16_t frame_count = 112;", region)


if __name__ == "__main__":
    unittest.main()
