"""Mailbox depth-4 drop-oldest contract (same host probe as assembler)."""

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


class UsbAudioQueueTest(unittest.TestCase):
    def test_mailbox_depth_and_drop_oldest(self):
        text = (AUDIO / "k1_usb_frame_mailbox.h").read_text(encoding="utf-8")
        self.assertIn("#define K1_USB_FRAME_QUEUE_DEPTH 4u", text)
        self.assertIn("k1_usb_mailbox_push_drop_oldest", text)
        self.assertIn("dropped_oldest", text)
        self.assertNotIn("xQueueCreate", text)
        self.assertNotIn("malloc", text)

    def test_host_probe_covers_drop_oldest_and_underflow(self):
        cc = _compiler()
        if cc is None:
            self.skipTest("no host C++ compiler")
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "k1_usb_audio_host_probe"
            built = subprocess.run(
                [cc, "-std=c++17", "-Wall", "-Wextra", "-Werror", f"-I{AUDIO}", str(PROBE), "-o", str(exe)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr + ran.stdout)
