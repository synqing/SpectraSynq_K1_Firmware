#!/usr/bin/env python3
"""Deterministic 12.8 kHz mono S16LE WAV fixture for K1 USB-audio ingress."""

from __future__ import annotations

import argparse
import hashlib
import math
import struct
import wave
from pathlib import Path

RATE = 12800
CHANNELS = 1
SAMPLE_WIDTH = 2
AMP = 0.25
CLICK_BPM = 120


def _sine(freq_hz: float, seconds: float) -> list[int]:
    n = int(RATE * seconds)
    out = []
    peak = AMP * 32767.0
    for i in range(n):
        v = peak * math.sin(2.0 * math.pi * freq_hz * i / RATE)
        out.append(int(round(v)))
    return out


def _silence(seconds: float) -> list[int]:
    return [0] * int(RATE * seconds)


def _windowed_clicks(seconds: float, bpm: int) -> list[int]:
    n = int(RATE * seconds)
    period = int(round(RATE * 60.0 / bpm))
    width = max(8, RATE // 400)  # ~2.5 ms raised-cosine burst, not a one-sample impulse
    out = [0] * n
    peak = AMP * 32767.0
    t = 0
    while t < n:
        for k in range(width):
            idx = t + k
            if idx >= n:
                break
            w = 0.5 - 0.5 * math.cos(2.0 * math.pi * k / max(width - 1, 1))
            out[idx] = int(round(peak * w))
        t += period
    return out


def build_samples() -> list[int]:
    parts: list[int] = []
    parts += _silence(2)
    parts += _sine(110, 3)
    parts += _silence(1)
    parts += _sine(440, 3)
    parts += _silence(1)
    parts += _sine(1000, 3)
    parts += _silence(1)
    parts += _sine(3000, 3)
    parts += _silence(1)
    parts += _sine(5000, 3)
    parts += _silence(1)
    parts += _windowed_clicks(20, CLICK_BPM)
    parts += _silence(2)
    return parts


def write_wav(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(RATE)
        wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    samples = build_samples()
    peak = max(abs(s) for s in samples)
    write_wav(out, samples)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    duration = len(samples) / RATE
    print(f"path={out.resolve()}")
    print(f"rate={RATE}")
    print(f"channels={CHANNELS}")
    print(f"sample_width={SAMPLE_WIDTH}")
    print(f"count={len(samples)}")
    print(f"duration_s={duration:.3f}")
    print(f"peak={peak}")
    print(f"sha256={digest}")
    if peak >= 32767:
        raise SystemExit("fixture clipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
