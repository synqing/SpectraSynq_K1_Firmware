#!/usr/bin/env python3
"""P4 alignment fixtures: jittered transient trains.

Why jittered and not a metronome
--------------------------------
A strictly periodic transient train autocorrelates almost as strongly one period
away as it does at zero lag. The alignment estimator then reports a confident but
period-ALIASED lag. `p4_align.py --selftest` measures this directly: peak-to-
sidelobe 1.06 for a periodic train against 3.23 for a jittered one, with the
periodic case correctly flagged `ambiguous=True`.

So the spacing is randomised from a fixed seed: reproducible, deterministic, and
unambiguous under cross-correlation.

Both channels carry the same train, because P4 compares the LINE path against the
MIC path, not left against right. LEFT/RIGHT/MID is a P6 question.
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures"
FS = 48000
AMP = 0.125          # -18 dBFS, matching the existing fixture family
SECS = 8.0           # long enough for a head/tail drift estimate
SEED = 20260908
JITTER = 0.35        # +/- 35 % of the nominal spacing
NOMINAL_GAP_S = 0.25
BURST_S = 0.020
BURST_HZ = 1200.0    # inside the shared LINE/MIC band
GUARD_S = 1.0        # leading and trailing silence for the quiet guards


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


def jittered_train(n: int, seed: int = SEED, jitter: float = JITTER) -> list[float]:
    rnd = random.Random(seed)
    x = [0.0] * n
    nominal = int(FS * NOMINAL_GAP_S)
    length = int(FS * BURST_S)
    pos = int(FS * GUARD_S)
    end = n - int(FS * GUARD_S)
    while pos < end:
        amp = 0.7 + 0.3 * rnd.random()
        for i in range(length):
            if pos + i >= n:
                break
            env = math.exp(-6.0 * i / length)
            x[pos + i] += AMP * amp * env * math.sin(2.0 * math.pi * BURST_HZ * i / FS)
        step = int(nominal * (1.0 + jitter * (rnd.random() * 2.0 - 1.0)))
        pos += max(step, int(FS * 0.05))
    return x


def main() -> None:
    n = int(FS * SECS)
    train = jittered_train(n)
    write_wav("p4_align_transients_jittered.wav", [(v, v) for v in train])

    # A strictly periodic sibling, kept ONLY as the negative control that
    # demonstrates the aliasing the jittered fixture avoids. Do not use it to
    # close P4 alignment.
    periodic = jittered_train(n, jitter=0.0)
    write_wav("p4_align_transients_periodic_CONTROL.wav", [(v, v) for v in periodic])


if __name__ == "__main__":
    main()
