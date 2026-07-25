"""Static gates for K1_VIVID_PRECOMP_V1.

The vivid pre-comp slice is an output-stage A/B control. It must stay
render-only, default-on for the accepted K1 posture, split chroma from black-depth, and reversible without
touching the K1 palette datasets or re-enabling output gamma.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

LED_UTILS_PATH = FW / "visual" / "led_utilities.h"
CONSTANTS_PATH = FW / "system" / "constants.h"
GLOBALS_PATH = FW / "system" / "globals.h"
SERIAL_PATH = FW / "serial" / "serial_menu.h"
SERIAL_MENU_CPP_PATH = FW / "serial" / "serial_menu.cpp"
SERIAL_CMD_HANDLERS_PATH = FW / "serial" / "serial_cmd_handlers.cpp"
PALETTES_PATH = FW / "visual" / "Palettes.cpp"
PIO_PATH = ROOT / "platformio.ini"

LED_UTILS = LED_UTILS_PATH.read_text()
CONSTANTS = CONSTANTS_PATH.read_text()
GLOBALS = GLOBALS_PATH.read_text()
SERIAL = SERIAL_PATH.read_text()
SERIAL_MENU_CPP = SERIAL_MENU_CPP_PATH.read_text()
SERIAL_CMD_HANDLERS = SERIAL_CMD_HANDLERS_PATH.read_text()
PALETTES = PALETTES_PATH.read_text()
PIO = PIO_PATH.read_text()


def _function_body(source: str, name: str) -> str:
    match = re.search(
        rf"\b(?:static\s+)?(?:inline\s+)?[A-Za-z_][A-Za-z0-9_:<>]*\s+{name}\s*\([^)]*\)\s*\{{",
        source,
    )
    assert match is not None, f"{name}() must exist"
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth:
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"{name}() body must be balanced"
    return source[start:index - 1]


class VividPrecompStaticTest(unittest.TestCase):
    def test_production_flag_and_default_on_runtime_state_exist(self):
        self.assertIn("-DK1_VIVID_PRECOMP_V1", PIO)
        self.assertRegex(GLOBALS, r"inline\s+bool\s+VP_VIVID_PRECOMP\s*=\s*true;")
        self.assertRegex(GLOBALS, r"inline\s+float\s+VP_VIVID_CHROMA_LEVEL\s*=\s*1\.0f;")
        self.assertRegex(GLOBALS, r"inline\s+float\s+VP_VIVID_BLACK_LEVEL\s*=\s*VIVID_BLACK_LEVEL_DEFAULT;")
        self.assertIn("#ifndef VIVID_CHROMA_GAIN_MAX", CONSTANTS)
        self.assertRegex(CONSTANTS, r"#define\s+VIVID_CHROMA_GAIN_MAX\s+0\.70f")
        self.assertIn("#ifndef VIVID_LUMA_CUT_MAX", CONSTANTS)
        self.assertRegex(CONSTANTS, r"#define\s+VIVID_LUMA_CUT_MAX\s+0\.12f")
        self.assertIn("#ifndef VIVID_BLACK_LEVEL_DEFAULT", CONSTANTS)
        self.assertRegex(CONSTANTS, r"#define\s+VIVID_BLACK_LEVEL_DEFAULT\s+0\.45f")

    def test_vivid_does_not_reenable_output_gamma_or_touch_palette_data(self):
        self.assertRegex(CONSTANTS, r"#define\s+ENABLE_OUTPUT_GAMMA\s+0\b")
        gamma_body = _function_body(CONSTANTS, "apply_gamma8")
        self.assertNotIn("VIVID", gamma_body)
        self.assertNotIn("K1_VIVID_PRECOMP_V1", PALETTES)
        self.assertNotIn("VIVID_CHROMA_GAIN_MAX", PALETTES)
        self.assertNotIn("VIVID_LUMA_CUT_MAX", PALETTES)
        self.assertNotIn("VIVID_BLACK_LEVEL_DEFAULT", PALETTES)
        self.assertNotIn("VP_VIVID_PRECOMP", PALETTES)

    def test_render_helper_is_flag_gated_split_levelled_and_hot_path_safe(self):
        self.assertIn("#ifdef K1_VIVID_PRECOMP_V1", LED_UTILS)
        body = _function_body(LED_UTILS, "apply_vivid_precomp_count")
        self.assertIn("if (!VP_VIVID_PRECOMP) return;", body)
        self.assertIn("VP_VIVID_CHROMA_LEVEL", body)
        self.assertIn("VP_VIVID_BLACK_LEVEL", body)
        self.assertIn("VIVID_CHROMA_GAIN_MAX", body)
        self.assertIn("VIVID_LUMA_CUT_MAX", body)
        self.assertIn("const SQ15x16 chroma_gain", body)
        self.assertIn("const SQ15x16 luma_cut", body)
        self.assertNotIn("VP_VIVID_PRECOMP_LEVEL", body)
        self.assertIn("desaturate(buffer[i], -chroma_gain)", body)
        self.assertIn("vivid_luminance", body)
        self.assertIn("common_cut", body)
        self.assertNotIn("apply_gamma8", body)
        self.assertNotIn("gamma8_lut", body)
        for forbidden in (
            "malloc",
            "calloc",
            "realloc",
            "new ",
            "delete",
            "String",
            "USBSerial",
            "Serial.",
            "printf",
        ):
            self.assertNotIn(forbidden, body)

    def test_clip_helper_accepts_count_and_existing_wrapper_stays_native(self):
        count_body = _function_body(LED_UTILS, "clip_led_values_count")
        self.assertIn("for (uint16_t i = 0; i < count; i++)", count_body)
        wrapper = _function_body(LED_UTILS, "clip_led_values")
        self.assertIn("clip_led_values_count(buffer, NATIVE_RESOLUTION);", wrapper)

    def test_vivid_runs_before_clip_on_primary_and_before_scale_on_secondary(self):
        primary = _function_body(LED_UTILS, "show_leds")
        self.assertLess(primary.index("render_ui();"), primary.index("apply_vivid_precomp_count(leds_16, NATIVE_RESOLUTION);"))
        self.assertLess(primary.index("apply_vivid_precomp_count(leds_16, NATIVE_RESOLUTION);"),
                        primary.index("clip_led_values(leds_16);"))

        secondary = _function_body(LED_UTILS, "show_secondary_leds")
        self.assertLess(secondary.index("apply_vivid_precomp_count(leds_16_secondary, NATIVE_RESOLUTION);"),
                        secondary.index("clip_led_values_count(leds_16_secondary, NATIVE_RESOLUTION);"))
        self.assertLess(secondary.index("clip_led_values_count(leds_16_secondary, NATIVE_RESOLUTION);"),
                        secondary.index("scale_to_secondary_strip();"))

    def test_serial_control_is_typed_and_hotkey_is_not_motion_probe_collision(self):
        # Help-text strings remain in serial_menu.h
        self.assertIn('vivid=[on/off] | Runtime output-stage chroma pre-comp', SERIAL)
        self.assertIn('vivid_level=[0.00-1.00] | Runtime vivid shortcut strength', SERIAL)
        self.assertIn('vivid_chroma=[0.00-1.00] | Runtime vivid chroma strength', SERIAL)
        self.assertIn('vivid_black=[0.00-1.00] | Runtime vivid black-depth strength', SERIAL)

        # Handler bodies were extracted to serial_cmd_handlers.cpp (Lane 2, S4.3).
        # The call-site in serial_menu.h now invokes serial_cmd_dispatch_vivid().
        self.assertIn('serial_cmd_dispatch_vivid(command_type, command_data)', SERIAL)
        self.assertIn('#ifdef K1_VIVID_PRECOMP_V1', SERIAL)

        # Verify handler bodies are in serial_cmd_handlers.cpp
        self.assertIn('strcmp(command_type, "vivid") == 0', SERIAL_CMD_HANDLERS)
        vivid_branch = SERIAL_CMD_HANDLERS.split('strcmp(command_type, "vivid") == 0', 1)[1].split("else if", 1)[0]
        self.assertIn("vp_parse_bool(command_data, &value)", vivid_branch)
        self.assertIn("VP_VIVID_PRECOMP = value;", vivid_branch)
        self.assertIn("serial_ensure_vivid_defaults();", vivid_branch)
        self.assertIn("serial_print_vivid_precomp_status();", vivid_branch)

        # Helper function bodies moved to serial_menu.cpp (M2.1 R1 batch 3); the
        # declarations remain gated in serial_menu.h. Same body teeth, correct file.
        print_body = _function_body(SERIAL_MENU_CPP, "serial_print_vivid_precomp_status")
        self.assertIn('USBSerial.print("VIVID_PRECOMP: ");', print_body)
        self.assertIn('USBSerial.print("VIVID_CHROMA_LEVEL: ");', print_body)
        self.assertIn('USBSerial.print("VIVID_BLACK_LEVEL: ");', print_body)

        self.assertIn('strcmp(command_type, "vivid_level") == 0', SERIAL_CMD_HANDLERS)
        level_branch = SERIAL_CMD_HANDLERS.split('strcmp(command_type, "vivid_level") == 0', 1)[1].split("else if", 1)[0]
        self.assertIn("vp_parse_float(command_data, &value)", level_branch)
        self.assertIn("serial_set_vivid_level(value);", level_branch)

        self.assertIn('strcmp(command_type, "vivid_chroma") == 0', SERIAL_CMD_HANDLERS)
        chroma_branch = SERIAL_CMD_HANDLERS.split('strcmp(command_type, "vivid_chroma") == 0', 1)[1].split("else if", 1)[0]
        self.assertIn("vp_parse_float(command_data, &value)", chroma_branch)
        self.assertIn("VP_VIVID_CHROMA_LEVEL = constrain(value, 0.0f, 1.0f);", chroma_branch)
        self.assertIn("serial_update_vivid_enabled_from_levels();", chroma_branch)

        self.assertIn('strcmp(command_type, "vivid_black") == 0', SERIAL_CMD_HANDLERS)
        black_branch = SERIAL_CMD_HANDLERS.split('strcmp(command_type, "vivid_black") == 0', 1)[1].split("else if", 1)[0]
        self.assertIn("vp_parse_float(command_data, &value)", black_branch)
        self.assertIn("VP_VIVID_BLACK_LEVEL = constrain(value, 0.0f, 1.0f);", black_branch)
        self.assertIn("serial_update_vivid_enabled_from_levels();", black_branch)

        hotkeys = _function_body(SERIAL, "serial_hotkey_is_immediate")
        self.assertIn("#if defined(K1_VIVID_PRECOMP_V1) && !defined(ENABLE_MOTION_PROBE)", hotkeys)
        self.assertIn("case 'v':", hotkeys)

        dispatcher = _function_body(SERIAL, "serial_handle_hotkey")
        shipping_v = dispatcher.split("#if defined(K1_VIVID_PRECOMP_V1) && !defined(ENABLE_MOTION_PROBE)", 1)[1]
        shipping_v = shipping_v.split("#endif", 1)[0]
        self.assertIn("case 'v':", shipping_v)
        self.assertIn("serial_toggle_vivid_precomp();", shipping_v)


if __name__ == "__main__":
    unittest.main()
