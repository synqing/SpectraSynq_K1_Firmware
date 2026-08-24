"""Host compile-and-run of the USB PCM assembler (header-only, no Arduino)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"
PROBE = ROOT / "tests" / "host" / "k1_usb_audio_host_probe.cpp"


def _compiler() -> str | None:
    for cc in ("c++", "clang++", "g++"):
        if shutil.which(cc):
            return cc
    return None


class UsbAudioAssemblerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc = _compiler()
        if cc is None:
            raise unittest.SkipTest("no host C++ compiler")
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "k1_usb_audio_host_probe"
            cmd = [
                cc,
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-Werror",
                f"-I{AUDIO}",
                str(PROBE),
                "-o",
                str(exe),
            ]
            built = subprocess.run(cmd, capture_output=True, text=True)
            if built.returncode != 0:
                raise AssertionError(f"host probe compile failed:\n{built.stderr}\n{built.stdout}")
            ran = subprocess.run([str(exe)], capture_output=True, text=True)
            cls.stdout = ran.stdout
            cls.stderr = ran.stderr
            cls.rc = ran.returncode

    def test_probe_pass(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        self.assertIn("PASS k1_usb_audio_host_probe", self.stdout)

    def test_assembler_api_is_header_only(self):
        text = (AUDIO / "k1_usb_pcm_assembler.h").read_text(encoding="utf-8")
        self.assertIn("k1_usb_pcm_assembler_feed", text)
        self.assertIn("#define K1_USB_PCM_FRAME_BYTES 192u", text)
        self.assertNotIn("Arduino.h", text)
        self.assertNotIn("malloc", text)
        self.assertNotIn("printf", text)
