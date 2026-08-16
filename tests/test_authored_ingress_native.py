"""Host gate for authored PRSM ingress (parse, magic-before-hotkey, arbitration).

Compiles the real firmware units audio/k1_prsm.cpp and audio/k1_authored_source.cpp.
No second renderer. No Arduino. clang++ or g++ is fine (stdint-only).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
AUDIO = FW / "audio"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
SERIAL_CPP = FW / "serial" / "serial_menu.cpp"
PROBE = ROOT / "scripts" / "regression-harness" / "k1_authored_ingress_probe.cpp"


def _compiler():
    for cc in ("c++", "clang++", "g++"):
        if shutil.which(cc):
            return cc
    return None


class AuthoredIngressNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc = _compiler()
        if cc is None:
            raise unittest.SkipTest("no host C++ compiler")
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "k1_authored_ingress_probe"
            cmd = [
                cc, "-std=c++17", "-O2",
                f"-I{AUDIO}",
                str(PROBE),
                str(AUDIO / "k1_prsm.cpp"),
                str(AUDIO / "k1_authored_source.cpp"),
                "-o", str(exe),
            ]
            built = subprocess.run(cmd, capture_output=True, text=True)
            if built.returncode != 0:
                raise AssertionError(f"probe compile failed:\n{built.stderr}")
            ran = subprocess.run([str(exe)], capture_output=True, text=True)
            cls.stdout = ran.stdout
            cls.stderr = ran.stderr
            cls.rc = ran.returncode

    def test_probe_pass(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        self.assertIn("PASS authored_ingress", self.stdout)
        self.assertIn("freshness_ms 50", self.stdout)

    def test_check_serial_scans_before_hotkeys(self):
        text = SERIAL_CPP.read_text(encoding="utf-8")
        fn = text.split("void check_serial(uint32_t t_now)", 1)[1]
        body = fn.split("void stream_agc_data", 1)[0]
        scan_at = body.find("k1_prsm_scanner_push")
        hot_at = body.find("serial_hotkey_is_immediate")
        self.assertGreater(scan_at, 0, "check_serial must call k1_prsm_scanner_push")
        self.assertGreater(hot_at, 0, "check_serial must still dispatch hotkeys")
        self.assertLess(scan_at, hot_at, "PRSM scanner must run before hotkeys")

    def test_ino_one_writer(self):
        text = INO.read_text(encoding="utf-8")
        self.assertIn("k1_authored_suppresses_live_update", text)
        self.assertIn("k1_audio_snapshot_publish", text)
        self.assertIn("k1_audio_snapshot_update", text)
        # Live update only in the else branch of authored suppress.
        self.assertIsNotNone(
            re.search(
                r"k1_authored_suppresses_live_update\(\)[\s\S]+k1_audio_snapshot_publish"
                r"[\s\S]+else[\s\S]+k1_audio_snapshot_update",
                text,
            )
        )

    def test_no_second_renderer_symbols(self):
        for path in (AUDIO / "k1_prsm.cpp", AUDIO / "k1_authored_source.cpp"):
            src = path.read_text(encoding="utf-8")
            self.assertNotIn("FastLED", src)
            self.assertNotIn("CRGB", src)
            self.assertNotIn("wavefield", src.lower())
