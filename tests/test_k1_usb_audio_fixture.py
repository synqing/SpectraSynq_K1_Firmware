"""WAV header / duration / peak gate for the K1 USB-audio fixture generator."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tools" / "usb_audio" / "generate_k1_usb_audio_fixture.py"


def test_fixture_header_duration_and_peak():
    with tempfile.TemporaryDirectory() as td:
        wav_path = Path(td) / "k1_usb_audio_fixture_12800_mono_s16.wav"
        proc = subprocess.run(
            [sys.executable, str(GEN), "--output", str(wav_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert wav_path.is_file()
        with wave.open(str(wav_path), "rb") as wf:
            assert wf.getframerate() == 12800
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            n = wf.getnframes()
            raw = wf.readframes(n)
        duration = n / 12800.0
        # 2+3+1+3+1+3+1+3+1+3+1+20+2 = 44 s
        assert abs(duration - 44.0) < 1e-6
        assert n == 12800 * 44
        peak = 0
        for i in range(0, len(raw), 2):
            v = int.from_bytes(raw[i : i + 2], "little", signed=True)
            peak = max(peak, abs(v))
        assert peak < 32767
        assert "rate=12800" in proc.stdout
        assert "channels=1" in proc.stdout
        digest = hashlib.sha256(wav_path.read_bytes()).hexdigest()
        assert f"sha256={digest}" in proc.stdout
