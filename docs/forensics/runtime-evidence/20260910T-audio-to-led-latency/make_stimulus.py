#!/usr/bin/env python3
"""Regenerate the acoustic stimulus used for the 2026-09-10 latency captures.

Deterministic (seeded), so the same file comes back byte-for-byte. 120 BPM kick
transient + 1/8 hats + moving bass and mid tones, so the AP frontend sees real
onsets and a non-static spectrum rather than a single steady tone.

    python3 make_stimulus.py            # -> k1_latency_stimulus.wav

The WAV itself is deliberately not committed: 90 s of 44.1 kHz mono is ~7.9 MB,
over the commit gate's blob ceiling.
"""
import math
import random
import struct
import wave

SAMPLE_RATE = 44100
DURATION_S = 90
BPM = 120
OUT = "k1_latency_stimulus.wav"


def main() -> None:
    total = SAMPLE_RATE * DURATION_S
    beat = int(SAMPLE_RATE * 60 / BPM)
    random.seed(7)
    frames = bytearray()
    for i in range(total):
        t = i / SAMPLE_RATE
        phase = i % beat
        # sharp kick transient on every beat — the onset the AP should catch
        kick = math.sin(2 * math.pi * 55 * (phase / SAMPLE_RATE)) * math.exp(
            -phase / (SAMPLE_RATE * 0.045)
        ) * 0.85
        # hats on the 1/8 for high-band transients
        phase8 = i % (beat // 2)
        hat = (random.random() * 2 - 1) * math.exp(-phase8 / (SAMPLE_RATE * 0.012)) * 0.18
        # sweeping bass and mid so the spectrum is never static
        bass = math.sin(2 * math.pi * (80 + 30 * math.sin(2 * math.pi * t / 8)) * t) * 0.28
        mid = math.sin(2 * math.pi * (440 + 180 * math.sin(2 * math.pi * t / 5)) * t) * 0.16
        v = max(-1.0, min(1.0, kick + hat + bass + mid))
        frames += struct.pack("<h", int(v * 30000))

    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(frames))
    print("wrote %s  %ds  %d BPM" % (OUT, DURATION_S, BPM))


if __name__ == "__main__":
    main()
