#!/usr/bin/env python3
"""Guarded 48 kHz stereo 24-bit WAV fixtures for P3 Line-In characterisation.

Each file is 2 s silence + stimulus + 2 s silence. Deterministic. No numpy.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures" / "guarded"
FS = 48000
GUARD = 2.0
AMP = 0.125  # -18 dBFS
STIM = 4.0


def q24(x: float) -> int:
    v = int(round(max(-1.0, min(1.0, x)) * 8388607.0))
    return max(-8388608, min(8388607, v))


def pack24(v: int) -> bytes:
    u = v & 0xFFFFFF
    return bytes((u & 0xFF, (u >> 8) & 0xFF, (u >> 16) & 0xFF))


def write_wav(name: str, frames: list[tuple[float, float]]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with wave.open(str(path), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(FS)
        buf = bytearray()
        for l, r in frames:
            buf += pack24(q24(l))
            buf += pack24(q24(r))
        w.writeframes(bytes(buf))
    return path


def tone(n: int, hz: float, amp: float = AMP) -> float:
    return amp * math.sin(2 * math.pi * hz * n / FS)


def guarded(stim: list[tuple[float, float]]) -> list[tuple[float, float]]:
    z = [(0.0, 0.0)] * int(FS * GUARD)
    return z + stim + z


def main() -> None:
    ng = int(FS * GUARD)
    ns = int(FS * STIM)
    files: dict[str, str] = {}

    def rec(path: Path) -> None:
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        files[path.name] = h
        print(f"{h}  {path.name}")

    rec(write_wav("00_silence_guarded.wav", [(0.0, 0.0)] * (ng * 2 + ns)))
    rec(
        write_wav(
            "01_both_997hz_guarded.wav",
            guarded([(tone(n, 997.0), tone(n, 997.0)) for n in range(ns)]),
        )
    )
    rec(
        write_wav(
            "02_left_997hz_guarded.wav",
            guarded([(tone(n, 997.0), 0.0) for n in range(ns)]),
        )
    )
    rec(
        write_wav(
            "03_right_1499hz_guarded.wav",
            guarded([(0.0, tone(n, 1499.0)) for n in range(ns)]),
        )
    )
    rec(
        write_wav(
            "04_lr_997_1499_guarded.wav",
            guarded([(tone(n, 997.0), tone(n, 1499.0)) for n in range(ns)]),
        )
    )
    steps = []
    for n in range(ns):
        a = AMP * (0.05 + 0.95 * (n / max(1, ns - 1)))
        s = a * math.sin(2 * math.pi * 997.0 * n / FS)
        steps.append((s, s))
    rec(write_wav("05_amplitude_staircase_997hz.wav", guarded(steps)))

    sweep = []
    f0, f1 = 20.0, 20000.0
    for n in range(ns):
        t = n / FS
        # log sweep phase
        k = ns / FS
        frac = n / max(1, ns - 1)
        hz = f0 * ((f1 / f0) ** frac)
        ph = 2 * math.pi * f0 * k * ((pow(f1 / f0, frac) - 1.0) / math.log(f1 / f0))
        s = AMP * math.sin(ph)
        sweep.append((s, s))
        (void := hz)
    rec(write_wav("06_log_sweep_20hz_20khz.wav", guarded(sweep)))

    mt = []
    tones = (97.0, 997.0, 2999.0, 7993.0)
    for n in range(ns):
        s = sum(tone(n, hz, AMP / len(tones)) for hz in tones)
        mt.append((s, s))
    rec(write_wav("07_multitone.wav", guarded(mt)))

    imp = []
    period = int(FS * 0.25)
    for n in range(ns):
        v = AMP if (n % period) == 0 else 0.0
        imp.append((v, v))
    rec(write_wav("08_impulse_transient_train.wav", guarded(imp)))

    # Deterministic synthetic "programme-like" excerpt — not commercial music.
    mus = []
    for n in range(ns):
        kick = AMP * math.exp(-((n % int(FS * 0.5)) / (FS * 0.04))) * math.sin(
            2 * math.pi * 60.0 * n / FS
        )
        hat = (AMP * 0.25 if (n % int(FS * 0.125)) < 40 else 0.0) * (
            1.0 if ((n * 1103515245 + 12345) & 0xFFFF) > 20000 else -1.0
        )
        mid = tone(n, 440.0, AMP * 0.2) + tone(n, 659.25, AMP * 0.15)
        l = kick + hat + mid
        r = kick * 0.9 + hat * 1.1 + tone(n, 440.0, AMP * 0.18)
        mus.append((l, r))
    rec(write_wav("09_reference_music_excerpt.wav", guarded(mus)))

    man = {
        "fs": FS,
        "sampwidth_bytes": 3,
        "channels": 2,
        "guard_s": GUARD,
        "stim_s": STIM,
        "amp": AMP,
        "label": "END_TO_END_LINE_LANE_FIXTURE",
        "music_excerpt": "SYNTHETIC_DETERMINISTIC_NOT_COMMERCIAL",
        "sha256": files,
    }
    mp = OUT / "P3_LINE_FIXTURE_MANIFEST.json"
    mp.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print(mp)


if __name__ == "__main__":
    main()
