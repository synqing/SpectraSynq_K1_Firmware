"""ODR smoke: a second TU may #include serial_menu.h and link against serial_menu.cpp."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
HARNESS = ROOT / "scripts" / "regression-harness"
GOLDEN = HARNESS / "golden"
STUBS = HARNESS / "stubs"
SMOKE = HARNESS / "serial_menu_second_tu_smoke.cpp"
DRIVER = HARNESS / "serial_menu_odr_driver.cpp"
HOST_GLOBALS = HARNESS / "render_host_globals.cpp"
FIXEDPOINTS = ROOT / "libraries" / "FixedPoints" / "src"
FW_SUBDIRS = [
    "serial", "system", "control", "director", "visual", "audio",
    "effects", "diag", "calibration", "persistence", "network", "platform",
]

DEFINES = [
    "K1_HARDWARE",
    "K1_RENDER_HOST_TEST",
    "K1_SERIAL_REPLAY_HOST",
    "K1_TEMPO_CONF_V2",
    "K1_TEMPO_FLYWHEEL_V2",
    "K1_ONSET_V2",
    "K1_CHORD_V2",
    "K1_SEMANTIC_STATE",
    "K1_LOUD_GUARD_V1",
    "SB_K1_HARDWARE=1",
]

MODULE_CPPS = [
    "serial/serial_tx.cpp",
    "serial/serial_parse_helpers.cpp",
    "serial/serial_cmd_handlers.cpp",
    "serial/serial_menu.cpp",
    "serial/serial_typed_dispatch.cpp",
    "audio/k1_prsm.cpp",
    "audio/k1_authored_source.cpp",
    "director/k1_smart_director.cpp",
    "director/k1_edgemixer.cpp",
    "director/k1_visual_hooks.cpp",
    "director/k1_mode_selection.cpp",
]

COMMON_SOURCES = [
    "system/globals.cpp",
    "visual/Palettes.cpp",
    "visual/render_params.cpp",
]


class SerialMenuOdrSmokeTest(unittest.TestCase):
    def test_second_tu_links_without_duplicate_symbols(self):
        cc = shutil.which("g++-15") or shutil.which("g++-14") or shutil.which("g++")
        self.assertIsNotNone(cc, "need g++ for ODR smoke compile")
        binary = ROOT / ".pytest_cache" / "serial_menu_odr_smoke_bin"
        binary.parent.mkdir(parents=True, exist_ok=True)
        sources = [str(FW / s) for s in COMMON_SOURCES]
        sources.append(str(HOST_GLOBALS))
        sources += [str(FW / s) for s in MODULE_CPPS]
        sources += [str(DRIVER), str(SMOKE)]
        cmd = [
            cc, "-std=c++17", "-O0", "-fno-fast-math",
            "-Wno-unused-parameter", "-Wno-unused-variable", "-Wno-unused-function",
            *[f"-D{d}" for d in DEFINES],
            "-I", str(STUBS),
            "-I", str(GOLDEN),
            "-I", str(FW),
            *[arg for d in FW_SUBDIRS for arg in ("-I", str(FW / d))],
            "-I", str(FIXEDPOINTS),
            *sources,
            "-o", str(binary),
        ]
        r = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
        self.assertEqual(r.returncode, 0,
                         f"ODR smoke link failed:\nSTDERR:\n{r.stderr}\nSTDOUT:\n{r.stdout}")
        run = subprocess.run([str(binary)], cwd=str(ROOT), text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()
