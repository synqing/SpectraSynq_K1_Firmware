import re
import unittest
from pathlib import Path

from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
FIRMWARE = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
INO = FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino"
LED_UTILITIES_H = FIRMWARE / "led_utilities.h"
SERIAL_MENU_H = FIRMWARE / "serial_menu.h"
VPML_H = FIRMWARE / "vp_motion_lab.h"


def read(path):
    return path.read_text(encoding="utf-8")


def strip_ini_comments(text):
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(";"))


def platformio_sections():
    text = read(PLATFORMIO)
    matches = list(re.finditer(r"^\[(?P<name>[^\]]+)\]\s*$", text, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("name")] = text[start:end]
    return sections


def resolved_section(name, sections, seen=None):
    if seen is None:
        seen = set()
    if name in seen:
        raise AssertionError("cyclic PlatformIO extends chain at %s" % name)
    seen.add(name)
    body = sections.get(name, "")
    match = re.search(r"(?m)^\s*extends\s*=\s*(?P<env>[^\s;]+)", body)
    if not match:
        return body
    parent = match.group("env").strip()
    return resolved_section(parent, sections, seen) + "\n" + body


def extract_function_body(source, name):
    pattern = rf"\b(?:inline\s+)?(?:constexpr\s+)?(?:bool|void|const\s+char\s*\*)\s+{name}\s*\([^)]*\)\s*\{{"
    match = re.search(pattern, source)
    if not match:
        raise AssertionError("%s() must exist" % name)
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
    if depth != 0:
        raise AssertionError("%s() body must be balanced" % name)
    return source[start:index - 1]


def strip_cpp_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


RENDER_FORBIDDEN = (
    r"\bshow_leds\s*\(",
    r"\bFastLED\.delay\s*\(",
    r"(?<!FastLED\.)\bdelay\s*\(",
    r"\bvTaskDelay\s*\(",
    r"\bUSBSerial\.",
    r"\bSerial\.",
    r"\bString\b",
    r"\bnew\s*(?:\(|[A-Za-z_])",
    r"\bdelete\b",
    r"\bmalloc\s*\(",
    r"\bcalloc\s*\(",
    r"\brealloc\s*\(",
    r"\bfree\s*\(",
    r"\bFile\b",
    r"\bLittleFS\b",
    r"\bSPIFFS\b",
    r"\bPreferences\b",
    r"\bWiFi\b",
    r"\bWebSockets\b",
)


class VPMotionLabStaticTest(unittest.TestCase):
    def test_platformio_declares_non_shippable_vp_motion_lab_env(self):
        sections = platformio_sections()
        self.assertIn("env:k1_vp_motion_lab", sections)
        raw = sections["env:k1_vp_motion_lab"].lower()
        resolved = strip_ini_comments(resolved_section("env:k1_vp_motion_lab", sections)).lower()
        self.assertIn("non-shippable", raw)
        self.assertIn("extends = env:k1_hardware_harness", raw)
        self.assertIn("-denable_vp_motion_lab=1", resolved)
        for inherited in (
            "diagnostic_capture.cpp",
            "vpab_capture.cpp",
            "enable_diag_capture=1",
            "enable_vpab_probe=1",
            "enable_vp_perf_audit=1",
        ):
            self.assertIn(inherited, resolved)

    def test_production_envs_exclude_vp_motion_lab_flag(self):
        sections = platformio_sections()
        for env in ("env:k1_hardware", "env:k1_bench_reference"):
            with self.subTest(env=env):
                resolved = strip_ini_comments(resolved_section(env, sections)).lower()
                self.assertNotIn("enable_vp_motion_lab", resolved)
                self.assertNotIn("vp_motion_lab.cpp", resolved)

    def test_intro_per_frame_renderer_exists_and_is_render_safe(self):
        source = read(LED_UTILITIES_H)
        body = extract_function_body(source, "vp_intro_render_frame")
        hits = [pattern for pattern in RENDER_FORBIDDEN if re.search(pattern, body)]
        self.assertEqual(hits, [])
        self.assertIn("clear_intro_led_buffers()", body)
        self.assertIn("leds_16", body)
        self.assertIn("leds_16_secondary", body)
        self.assertIn("clip_led_values(leds_16)", body)
        self.assertIn("clip_led_values(leds_16_secondary)", body)

    def test_intro_loop_renderer_exists_and_is_render_safe(self):
        source = read(LED_UTILITIES_H)
        body = extract_function_body(source, "vp_intro_render_loop_frame")
        hits = [pattern for pattern in RENDER_FORBIDDEN if re.search(pattern, body)]
        self.assertEqual(hits, [])
        self.assertIn("intro_triangle01", body)
        self.assertIn("leds_16", body)
        self.assertIn("leds_16_secondary", body)
        self.assertIn("clip_led_values(leds_16)", body)
        self.assertIn("clip_led_values(leds_16_secondary)", body)

    def test_intro_animation_keeps_boot_wrapper_behaviour(self):
        body = extract_function_body(read(LED_UTILITIES_H), "intro_animation")
        self.assertIn("const uint16_t frame_count = 112;", body)
        self.assertIn("for (uint16_t frame = 0; frame < frame_count; frame++)", body)
        render_pos = body.index("vp_intro_render_frame(frame, frame_count);")
        show_pos = body.index("show_leds();", render_pos)
        delay_pos = body.index("FastLED.delay(2);", show_pos)
        self.assertLess(render_pos, show_pos)
        self.assertLess(show_pos, delay_pos)
        self.assertIn("clear_intro_history_buffers();", body)

    def test_vpml_header_is_non_shippable_and_render_safe(self):
        source = read(VPML_H)
        self.assertIn("NON-SHIPPABLE", source)
        body = extract_function_body(source, "vpml_render_frame")
        hits = [pattern for pattern in RENDER_FORBIDDEN if re.search(pattern, body)]
        self.assertEqual(hits, [])
        self.assertIn("frame_count = vpml_frame_count_for_program(vpml_program)", body)
        self.assertIn("vp_intro_render_frame(vpml_frame, frame_count)", body)
        self.assertIn("vp_intro_render_loop_frame(vpml_frame, frame_count)", body)

    def test_vpml_frame_owner_sets_context_before_show_leds(self):
        source = read(INO)
        led_thread_start = source.index("void led_thread")
        start = source.index("#ifdef ENABLE_VP_MOTION_LAB", led_thread_start)
        end = source.index("      if (mode_transition_queued", start)
        block = source[start:end]
        self.assertIn("vpml_is_active()", block)
        render_pos = block.index("vpml_render_frame();")
        context_pos = block.index("vpml_set_vpab_context();")
        show_pos = block.index("show_leds();", context_pos)
        continue_pos = block.index("continue;", show_pos)
        self.assertLess(render_pos, context_pos)
        self.assertLess(context_pos, show_pos)
        self.assertLess(show_pos, continue_pos)

    def test_vpml_vpab_context_marks_both_channels(self):
        body = extract_function_body(read(VPML_H), "vpml_set_vpab_context")
        self.assertIn("VPABRenderContext context", body)
        self.assertGreaterEqual(body.count("VPML_VPAB_MODE_ID"), 2)
        self.assertIn("vpab_capture_set_render_context(context)", body)

    def test_vpml_serial_surface_is_compile_guarded_and_typed_only(self):
        serial = read(SERIAL_MENU_H)
        self.assertRegex(
            serial,
            r'(?s)#ifdef\s+ENABLE_VP_MOTION_LAB\s*\n\s*else if \(strcmp\(command_type, "vpml"\) == 0\).*?#endif',
        )
        command_body = extract_function_body(read(VPML_H), "vpml_command")
        self.assertIn('"play_builtin,intro_bounce"', command_body)
        self.assertIn('"play_builtin,intro_bounce_loop"', command_body)
        forbidden = (
            "chunk",
            "upload",
            "raw",
            "compiler",
            "compile",
            "eval",
            "exec",
            "commit",
            "persist",
            "LittleFS",
            "Preferences",
        )
        hits = [token for token in forbidden if token in command_body]
        self.assertEqual(hits, [])

        hotkeys = extract_function_body(serial, "serial_hotkey_is_immediate")
        self.assertNotIn("vpml", hotkeys)
        self.assertIn("vpml=play_builtin,intro_bounce_loop", serial)

    def test_vpml_code_excludes_wireless_audio_persistence_and_smart_director(self):
        code = strip_cpp_comments(read(VPML_H))
        forbidden = (
            "k1_wireless",
            "WebSockets",
            "WiFi",
            "K1_CONTROL_TOKEN",
            "k1_smart_director",
            "k1_audio_snapshot_read",
            "K1OnsetBeatEvent",
            "GDFT",
            "noise_cal",
            "save_config",
            "LittleFS",
            "Preferences",
        )
        hits = [token for token in forbidden if token in code]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
