#!/usr/bin/env python3
"""Deterministic 48 kHz stereo WAV fixtures for PCM1808 raw tests."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures"
FS = 48000
AMP = 0.125  # -18 dBFS
SECS = 4.0


def write_wav(name: str, frames: list[tuple[float, float]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with wave.open(str(path), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(FS)
        buf = bytearray()
        for l, r in frames:
            def q(x: float) -> int:
                v = int(round(x * 32767.0))
                return max(-32768, min(32767, v))

            buf += struct.pack("<hh", q(l), q(r))
        w.writeframes(bytes(buf))
    print(path)


def tone(n: int, hz: float) -> float:
    return AMP * math.sin(2 * math.pi * hz * n / FS)


def main() -> None:
    nframes = int(FS * SECS)
    write_wav("silence_48k_stereo.wav", [(0.0, 0.0)] * nframes)
    write_wav(
        "both_1khz_minus18db.wav",
        [(tone(n, 1000.0), tone(n, 1000.0)) for n in range(nframes)],
    )
    write_wav(
        "left_997hz_minus18db.wav",
        [(tone(n, 997.0), 0.0) for n in range(nframes)],
    )
    write_wav(
        "right_1499hz_minus18db.wav",
        [(0.0, tone(n, 1499.0)) for n in range(nframes)],
    )
    write_wav(
        "dual_lr_997_1499_minus18db.wav",
        [(tone(n, 997.0), tone(n, 1499.0)) for n in range(nframes)],
    )
    steps = []
    for n in range(nframes):
        a = AMP * (0.25 + 0.75 * (n / nframes))
        s = a * math.sin(2 * math.pi * 1000.0 * n / FS)
        steps.append((s, s))
    write_wav("amplitude_steps_1khz.wav", steps)


if __name__ == "__main__":
    main()
