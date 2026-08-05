#!/usr/bin/env python3
"""Independent 512-pt STM reference (TB-1). Does NOT import or call k1_stm."""
from __future__ import annotations

import hashlib
import json
import math
import wave
from pathlib import Path
from typing import Iterator, List

import numpy as np

SR = 12800.0
HOP = 96
NFFT = 512
STM_BINS = 42
ENV_BANDS = 128
ALGO_ID = "wb3-ref-512-v1"

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def self_executable_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def load_pcm_mono(path: Path, max_seconds: float | None = 30.0) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        ch = w.getnchannels()
        sw = w.getsampwidth()
        fr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError("expected 16-bit PCM")
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if fr != int(SR):
        # simple resample for fixture hygiene
        t_old = np.arange(len(x)) / fr
        t_new = np.arange(0, t_old[-1], 1.0 / SR)
        x = np.interp(t_new, t_old, x)
    if max_seconds is not None:
        x = x[: int(max_seconds * SR)]
    return x / 32768.0

def hann(n: int) -> np.ndarray:
    if n <= 1:
        return np.ones(n, dtype=np.float64)
    i = np.arange(n, dtype=np.float64)
    return 0.5 * (1.0 - np.cos(2.0 * math.pi * i / (n - 1)))

def frame_energies(pcm: np.ndarray) -> Iterator[tuple[int, float, List[float]]]:
    win = hann(NFFT)
    pos = 0
    t_ms = 0
    dt_ms = int(round(1000.0 * HOP / SR))
    hist: List[np.ndarray] = []
    while pos + NFFT <= len(pcm):
        seg = pcm[pos : pos + NFFT] * win
        spec = np.fft.rfft(seg)
        mag = np.abs(spec)
        # 128-band envelope
        env = np.zeros(ENV_BANDS, dtype=np.float64)
        for b in range(ENV_BANDS):
            lo = (b * (len(mag) - 1)) // ENV_BANDS
            hi = ((b + 1) * (len(mag) - 1)) // ENV_BANDS
            env[b] = mag[lo : hi + 1].mean()
        # 42 STM bins
        stm = np.zeros(STM_BINS, dtype=np.float64)
        for i in range(STM_BINS):
            lo = (i * ENV_BANDS) // STM_BINS
            hi = ((i + 1) * ENV_BANDS) // STM_BINS
            stm[i] = env[lo:hi].mean()
        peak = float(stm.max())
        if peak > 1e-9:
            stm = stm / peak
        hist.append(stm)
        if len(hist) > 17:
            hist.pop(0)
        ready = len(hist) >= 17
        temporal = float(np.std(np.stack(hist, axis=0), axis=0).mean()) if ready else 0.0
        spectral = float(stm.mean()) if ready else 0.0
        energy = temporal + spectral
        yield t_ms, energy, stm.astype(float).tolist()
        pos += HOP
        t_ms += dt_ms

def emit_ndjson(pcm: np.ndarray, out: Path) -> dict:
    frames = []
    for t_ms, energy, stm in frame_energies(pcm):
        ready = t_ms >= 17 * int(round(1000.0 * HOP / SR))
        frames.append({
            "t_ms": t_ms,
            "ready": ready,
            "temporal_energy": energy * 0.5,
            "spectral_energy": energy * 0.5,
            "spectral": stm,
            "energy": energy,
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for fr in frames:
            f.write(json.dumps(fr) + chr(10))
    return {"frames": len(frames), "mean_energy": float(np.mean([f["energy"] for f in frames])) if frames else 0.0}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("wav")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--max-seconds", type=float, default=20.0)
    a = p.parse_args()
    pcm = load_pcm_mono(Path(a.wav), a.max_seconds)
    stats = emit_ndjson(pcm, Path(a.out))
    print(json.dumps({"algorithm_id": ALGO_ID, "executable_hash": self_executable_hash(), **stats}))
