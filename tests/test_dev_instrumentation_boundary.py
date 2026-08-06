import re
import unittest
from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface, compile_guarded_typed_row


ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
AGENTS = ROOT / "AGENTS.md"
CLAUDE = ROOT / ".claude" / "CLAUDE.md"
SPEC = ROOT / "docs" / "superpowers" / "specs" / "2026-05-27-sb-trace-diagnostic-design.md"
FIRMWARE = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
DEFAULT_ENV_RE = re.compile(r"(?m)^\s*default_envs\s*=\s*(?P<env>[^\s;]+)")
EXTENDS_RE = re.compile(r"(?m)^\s*extends\s*=\s*(?P<env>[^\s;]+)")
MABUTRACE_INCLUDE_RE = re.compile(
    r'#\s*include\s*[<"](?:[^>"]*/)?mabutrace(?:\.h)?[>"]',
    re.IGNORECASE,
)
MABUTRACE_SYMBOL_RE = re.compile(
    r"\b(?:mabutrace_|MABUTRACE_|TRACE_(?:SCOPE|COUNTER|INSTANT|MARKER|BEGIN|END|EVENT))\b"
)
NON_SHIPPABLE_ENV_MARKERS = ("harness", "probe", "trace_dev", "motion_lab")
PRODUCTION_FORBIDDEN_TOKENS = (
    "mabutrace",
    "feature_mabutrace",
    "enable_mabutrace",
    "trace_dev",
    "k1_hardware_trace_dev",
    "enable_diag_capture",
    "enable_vpab_probe",
    "enable_vp_perf_audit",
    "enable_ap_stream",
    "enable_frame_dump",
    "enable_vp_probe_cmd",
    "enable_gdft_harness",
    "enable_vp_motion_lab",
    "enable_tempo_stream",
    "enable_ap_frontend_debug",
    "k1_acquisition_only_probe",
    "k1_ap_stage_probe_stop_stage",
    "diagnostic_capture.cpp",
    "vpab_capture.cpp",
)
INSTRUMENTATION_ENV_TOKENS = (
    "enable_diag_capture",
    "enable_vpab_probe",
    "enable_vp_perf_audit",
    "enable_ap_stream",
    "enable_frame_dump",
    "enable_vp_probe_cmd",
    "enable_gdft_harness",
    "enable_vp_motion_lab",
    "enable_tempo_stream",
    "enable_ap_frontend_debug",
    "k1_acquisition_only_probe",
    "k1_ap_stage_probe_stop_stage",
    "diagnostic_capture.cpp",
    "vpab_capture.cpp",
    "mabutrace",
    "trace_dev",
)


def read(path):
    return path.read_text(encoding="utf-8")


def strip_ini_comments(text):
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(";"):
            continue
        lines.append(line)
    return "\n".join(lines)


def platformio_sections():
    text = read(PLATFORMIO)
    matches = list(re.finditer(r"^\[(?P<name>[^\]]+)\]\s*$", text, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("name")] = text[start:end]
    return sections


def default_env_name():
    match = DEFAULT_ENV_RE.search(read(PLATFORMIO))
    if not match:
        return None
    return "env:" + match.group("env").strip()


def resolved_section(name, sections, seen=None):
    if seen is None:
        seen = set()
    if name in seen:
        raise AssertionError("cyclic PlatformIO extends chain at %s" % name)
    seen.add(name)
    body = sections.get(name, "")
    match = EXTENDS_RE.search(body)
    if not match:
        return body
    parent = match.group("env").strip()
    return resolved_section(parent, sections, seen) + "\n" + body


def is_non_shippable_env(name):
    lower = name.lower()
    return any(marker in lower for marker in NON_SHIPPABLE_ENV_MARKERS)


class DevInstrumentationBoundaryTest(unittest.TestCase):
    def test_governing_docs_encode_dev_code_never_ships_and_mabutrace_escalation(self):
        required_files = (AGENTS, CLAUDE, SPEC)
        for path in required_files:
            with self.subTest(path=path.relative_to(ROOT)):
                text = read(path).lower()
                self.assertIn("never ships with production firmware", text)
                self.assertIn("mabutrace", text)
                self.assertIn("mandatory", text)
                self.assertIn("developer-only", text)
                self.assertIn("timeline/causality", text)
                self.assertIn("non-shippable", text)
                self.assertIn("scalar diagnostics", text)
                self.assertIn("do not close causal attribution", text)
                self.assertNotIn("optional mabutrace dev env", text)
                self.assertNotIn("mabutrace support may exist only", text)

    def test_production_platformio_env_excludes_dev_instrumentation(self):
        sections = platformio_sections()
        default_env = default_env_name()
        self.assertEqual(default_env, "env:k1_hardware")
        production_envs = [name for name in sections if name.startswith("env:") and not is_non_shippable_env(name)]
        self.assertIn(default_env, production_envs)

        failures = []
        for name in production_envs:
            resolved = strip_ini_comments(resolved_section(name, sections)).lower()
            hits = [token for token in PRODUCTION_FORBIDDEN_TOKENS if token in resolved]
            if hits:
                failures.append("%s: %s" % (name, ", ".join(hits)))
        self.assertEqual(failures, [])

    def test_production_candidate_pins_ap_vp_split_and_declared_timing(self):
        sections = platformio_sections()
        resolved = strip_ini_comments(resolved_section("env:k1_hardware", sections)).lower()
        required = (
            "-darduino_running_core=0",
            "-dk1_led_task_core=1",
            "-dk1_i2s_dma_desc_num_value=3",
            "-ddefault_sample_rate=12800",
            "-ddefault_samples_per_chunk=96",
            "-dk1_tempo_novelty_decimation=3u",
        )
        missing = [token for token in required if token not in resolved]
        self.assertEqual(missing, [])

    def test_harness_env_owns_static_diagnostics_and_vp_perf_audit(self):
        sections = platformio_sections()
        self.assertIn("env:k1_hardware_harness", sections)
        harness_raw = sections["env:k1_hardware_harness"].lower()
        harness = strip_ini_comments(harness_raw)
        required = (
            "extends = env:k1_hardware",
            "diagnostic_capture.cpp",
            "vpab_capture.cpp",
            "enable_diag_capture=1",
            "enable_vpab_probe=1",
            "enable_vp_perf_audit=1",
        )
        missing = [token for token in required if token not in harness]
        self.assertEqual(missing, [])
        self.assertNotIn("mabutrace", harness)
        self.assertIn("non-shippable", harness_raw)

    def test_instrumentation_envs_are_non_shippable_labelled(self):
        offenders = []
        for name, body in platformio_sections().items():
            if not name.startswith("env:"):
                continue
            resolved = strip_ini_comments(resolved_section(name, platformio_sections())).lower()
            raw = body.lower()
            if any(token in resolved for token in INSTRUMENTATION_ENV_TOKENS):
                if not is_non_shippable_env(name):
                    offenders.append(f"{name}: instrumentation env name is not non-shippable")
                if "non-shippable" not in raw:
                    offenders.append(f"{name}: missing non-shippable label")
        self.assertEqual(offenders, [])

    def test_mabutrace_dependency_if_introduced_is_trace_dev_only_and_non_shippable(self):
        offenders = []
        sections = platformio_sections()
        for name, body in sections.items():
            lower = strip_ini_comments(resolved_section(name, sections)).lower()
            if "mabutrace" not in lower:
                continue
            if "trace_dev" not in name.lower():
                offenders.append(f"{name}: env name is not trace_dev")
            if "non-shippable" not in body.lower():
                offenders.append(f"{name}: missing non-shippable label")
            self.assertNotEqual(default_env_name(), name)
        self.assertEqual(offenders, [])

    def test_direct_mabutrace_include_is_forbidden_outside_sb_trace_wrapper(self):
        offenders = []
        for path in FIRMWARE.rglob("*"):
            if path.suffix not in {".h", ".hpp", ".c", ".cpp", ".ino"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if path.name == "k1_trace.h":
                continue
            if MABUTRACE_INCLUDE_RE.search(text):
                offenders.append(str(path.relative_to(ROOT)) + ": include")
            if MABUTRACE_SYMBOL_RE.search(text):
                offenders.append(str(path.relative_to(ROOT)) + ": symbol")
        self.assertEqual(offenders, [])

    def test_diagnostic_includes_are_compile_guarded(self):
        serial_menu = read(FIRMWARE / "serial_menu.h")
        led_utilities = read(FIRMWARE / "led_utilities.h")
        self.assertRegex(
            serial_menu,
            r'(?s)#if\s+ENABLE_DIAG_CAPTURE\s*\n\s*#include\s+"diagnostic_capture\.h"\s*\n#endif',
        )
        for text in (serial_menu, led_utilities):
            self.assertRegex(
                text,
                r'(?s)#if\s+ENABLE_VPAB_PROBE\s*\n\s*#include\s+"vpab_capture\.h"\s*\n#endif',
            )

    def test_diagnostic_command_surfaces_are_compile_guarded(self):
        serial_menu = read_serial_menu_surface(FIRMWARE)
        self.assertTrue(compile_guarded_typed_row(serial_menu, "ENABLE_DIAG_CAPTURE", "diag"))
        self.assertTrue(compile_guarded_typed_row(serial_menu, "ENABLE_VPAB_PROBE", "vpab"))


if __name__ == "__main__":
    unittest.main()
