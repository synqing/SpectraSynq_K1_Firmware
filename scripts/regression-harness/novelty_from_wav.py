#!/usr/bin/env python3
"""Convert a 12.8 kHz mono WAV into a SensoryBridge-rate novelty curve.

This is the front half of the DIGITAL real-music tempo validation pipe (Lane A,
docs/architecture/tempo-lock-hardening-plan.md). It is 100% offline: no mic, no
speaker, no sound played, no K1/bench. The WAV's *samples* are processed on the
dev machine into a spectral-flux onset-strength curve at the SensoryBridge AP
frame rate, which is then replayed through the UNMODIFIED sb_tempo.cpp by
tempo_replay.py / tempo_accuracy.py.

Why this is valid (per the algo-design swarm, SW5): sb_tempo consumes only the
*temporal shape* of novelty (it normalises and [0,1]-clamps internally), so the
host novelty just needs to be REPRESENTATIVE, not a bit-exact GDFT replica.
Octave aliasing — the thing the octave fix targets — lives in onset periodicity,
which spectral flux preserves.

Frame rate: SensoryBridge runs the audio pipeline at
    CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK = 12800 / 96 = 133.333 Hz.
sb_tempo_update() is called once per AP frame; the detector does its OWN /3
decimation internally (to ~44.4 Hz). So we emit ONE novelty value per 96-sample
hop = the native 133.333 Hz AP frame rate, and we DO NOT pre-decimate.

Output CSV columns: frame_ms,novelty,silence
  frame_ms : int, monotonic, ~7.5 ms apart (one AP frame).
  novelty  : float in [0,1] (sb_tempo clamps to [0,1] anyway — pre-scaling here
             mirrors the device's own clamp, so the baseline is faithful to the
             CURRENT system; log-domain pre-clamp novelty is the SW3 Step-4 fix,
             out of scope for the baseline).
  silence  : 0/1, 1 when the frame RMS is below a conservative floor.

No librosa / soundfile dependency (absent on this machine) — scipy.io.wavfile +
hand-rolled spectral flux only, exactly as the plan's fallback specifies.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
from scipy.ndimage import uniform_filter1d

# SensoryBridge audio config (config_types.h DEFAULT_SAMPLE_RATE, i2s_audio.h SAMPLES_PER_CHUNK).
SAMPLE_RATE = 12800
HOP = 96            # SAMPLES_PER_CHUNK -> one AP frame per hop -> 133.333 Hz
NFFT = 512          # ~40 ms analysis window
TOP_DB = 80.0       # dB floor below per-file peak for the log-magnitude spectrogram


def _to_mono_float(sr, data):
    """int/float WAV -> mono float32 in roughly [-1, 1]."""
    x = data.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        x /= float(np.iinfo(data.dtype).max)
    return x, sr


def wav_to_novelty(path):
    """Return (frame_ms, novelty, silence) numpy arrays for a WAV file.

    novelty is dB-spectral-flux: log-magnitude spectrogram, half-wave-rectified
    first difference summed over frequency, sqrt-compressed, then scaled by its
    99th percentile and clipped to [0,1] (robust to single-frame outliers).
    """
    sr, data = wavfile.read(str(path))
    x, sr = _to_mono_float(sr, data)
    if sr != SAMPLE_RATE:
        # We expect the corpus to already be 12.8 kHz; resampling would change the
        # hop->frame-rate relationship sb_tempo assumes. Refuse rather than lie.
        raise ValueError(f"{path}: sample rate {sr} != {SAMPLE_RATE}; decode to 12.8 kHz first")

    n = x.shape[0]
    if n < NFFT:
        raise ValueError(f"{path}: only {n} samples (< {NFFT})")

    nframes = 1 + (n - NFFT) // HOP
    starts = np.arange(nframes) * HOP
    # [nframes, NFFT] windowed frames via stride view (no copy until *win).
    frames = np.lib.stride_tricks.sliding_window_view(x, NFFT)[starts]
    win = np.hanning(NFFT)
    mag = np.abs(np.fft.rfft(frames * win, axis=1))  # [nframes, NFFT/2+1]

    # Per-file dB spectrogram, floored TOP_DB below the peak (librosa-style ref=max).
    ref = max(mag.max(), 1e-10)
    sdb = 20.0 * np.log10(np.maximum(mag, ref * (10.0 ** (-TOP_DB / 20.0))) / ref)

    # Spectral flux: positive first difference summed across frequency.
    diff = np.diff(sdb, axis=0, prepend=sdb[:1])
    flux = np.maximum(diff, 0.0).sum(axis=1)

    # Remove slow song-dynamics drift (verse/chorus swells) that otherwise piles a DC
    # pedestal onto the curve. Left in, that drift dominates the lowest tempo Goertzel
    # bins and — with sb_tempo's quartic winner exaggeration — pins the winner to its
    # bottom bin (60 BPM). Subtract a LONG (~3 s) moving mean: high-pass cutoff ~0.3 Hz,
    # well below the 60 BPM (1 Hz) tempo floor, so 60–200 BPM periodicity is fully
    # preserved while only sub-tempo drift is removed; then half-wave rectify to an
    # onset-like envelope (standard adaptive-threshold onset strength, SW3's
    # "sliding-window-mean threshold (not EMA)"). This is host-novelty *quality*, not a
    # detector change — it gives the winner-selection logic a fair input to be measured.
    w = max(3, int(round(3.0 * SAMPLE_RATE / HOP)))
    local_mean = uniform_filter1d(flux, size=w, mode="nearest")
    onset = np.maximum(flux - local_mean, 0.0)
    nov = np.sqrt(onset)

    p99 = float(np.percentile(nov, 99))
    if p99 < 1e-9:
        p99 = 1e-9
    nov = np.clip(nov / p99, 0.0, 1.0)

    # Silence: frame RMS below a conservative floor (rarely fires on loud pop, but
    # protects quiet ballad intros). Both absolute (~-46 dBFS) and relative guards.
    rms = np.sqrt((frames ** 2).mean(axis=1))
    med = float(np.median(rms))
    floor = max(0.005, 0.05 * med)
    silence = (rms < floor).astype(np.int8)

    frame_ms = np.round(starts * 1000.0 / SAMPLE_RATE).astype(np.int64)
    return frame_ms, nov.astype(np.float64), silence


def wav_to_features(path):
    """Return (frame_ms, novelty, silence, spectral_energy, chroma_strength) for a WAV.

    Adds the two REAL per-axis input signals the 4-axis saliency engine needs and that the
    novelty-only replay was broadcasting away (RC-3):
      spectral_energy : per-frame energy LEVEL (mean linear magnitude), p99-normalised to [0,1]
                        -- distinct from novelty (flux); the dynamic axis keys on |d energy|.
      chroma_strength : 12-bin chroma concentration max/sum in [1/12, 1] (mirrors the fork's
                        chroma_max/chroma_sum); the harmonic axis keys on |d chroma_strength|.
    novelty + silence are computed identically to wav_to_novelty so the timbral/rhythmic axes
    are unchanged. Self-contained (does not touch wav_to_novelty, which the tempo baseline pins).
    """
    sr, data = wavfile.read(str(path))
    x, sr = _to_mono_float(sr, data)
    if sr != SAMPLE_RATE:
        raise ValueError(f"{path}: sample rate {sr} != {SAMPLE_RATE}; decode to 12.8 kHz first")
    n = x.shape[0]
    if n < NFFT:
        raise ValueError(f"{path}: only {n} samples (< {NFFT})")

    nframes = 1 + (n - NFFT) // HOP
    starts = np.arange(nframes) * HOP
    frames = np.lib.stride_tricks.sliding_window_view(x, NFFT)[starts]
    win = np.hanning(NFFT)
    mag = np.abs(np.fft.rfft(frames * win, axis=1))  # [nframes, NFFT/2+1]

    # novelty: identical pipeline to wav_to_novelty (dB flux, drift-removed, sqrt, p99-clip).
    ref = max(mag.max(), 1e-10)
    sdb = 20.0 * np.log10(np.maximum(mag, ref * (10.0 ** (-TOP_DB / 20.0))) / ref)
    diff = np.diff(sdb, axis=0, prepend=sdb[:1])
    flux = np.maximum(diff, 0.0).sum(axis=1)
    w = max(3, int(round(3.0 * SAMPLE_RATE / HOP)))
    local_mean = uniform_filter1d(flux, size=w, mode="nearest")
    onset = np.maximum(flux - local_mean, 0.0)
    nov = np.sqrt(onset)
    p99 = float(np.percentile(nov, 99))
    if p99 < 1e-9:
        p99 = 1e-9
    nov = np.clip(nov / p99, 0.0, 1.0)

    # spectral_energy: energy LEVEL, not flux. p99-normalised to [0,1].
    energy = mag.mean(axis=1)
    e99 = float(np.percentile(energy, 99))
    if e99 < 1e-9:
        e99 = 1e-9
    spectral_energy = np.clip(energy / e99, 0.0, 1.0)

    # chroma_strength: fold rfft bins into 12 pitch classes (A4=440), concentration = max/sum.
    freqs = np.fft.rfftfreq(NFFT, d=1.0 / SAMPLE_RATE)
    pc = np.full(freqs.shape, -1, dtype=np.int64)
    valid = freqs > 20.0
    pc[valid] = np.mod(np.round(12.0 * np.log2(freqs[valid] / 440.0)).astype(np.int64), 12)
    chroma = np.zeros((nframes, 12), dtype=np.float64)
    for k in range(12):
        cols = np.where(pc == k)[0]
        if cols.size:
            chroma[:, k] = mag[:, cols].sum(axis=1)
    csum = chroma.sum(axis=1)
    csum = np.where(csum < 1e-12, 1e-12, csum)
    chroma_strength = chroma.max(axis=1) / csum

    rms = np.sqrt((frames ** 2).mean(axis=1))
    med = float(np.median(rms))
    floor = max(0.005, 0.05 * med)
    silence = (rms < floor).astype(np.int8)

    frame_ms = np.round(starts * 1000.0 / SAMPLE_RATE).astype(np.int64)
    return (frame_ms, nov.astype(np.float64), silence,
            spectral_energy.astype(np.float64), chroma_strength.astype(np.float64))


def novelty_lines(path):
    """Return a list of 'ms novelty silence' whitespace lines for stdin replay."""
    frame_ms, nov, silence = wav_to_novelty(path)
    return [f"{int(m)} {v:.6f} {int(s)}" for m, v, s in zip(frame_ms, nov, silence)]


def write_csv(path, out_csv):
    frame_ms, nov, silence = wav_to_novelty(path)
    lines = ["frame_ms,novelty,silence"]
    lines += [f"{int(m)},{v:.6f},{int(s)}" for m, v, s in zip(frame_ms, nov, silence)]
    Path(out_csv).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(frame_ms)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("wav")
    p.add_argument("out_csv", nargs="?", help="if omitted, prints summary stats only")
    args = p.parse_args(argv)
    frame_ms, nov, silence = wav_to_novelty(args.wav)
    if args.out_csv:
        n = write_csv(args.wav, args.out_csv)
        print(f"wrote {n} frames -> {args.out_csv}")
    else:
        print(f"frames={len(frame_ms)} dur={frame_ms[-1]/1000:.1f}s "
              f"nov[mean={nov.mean():.3f} max={nov.max():.3f}] "
              f"silence_frac={silence.mean():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
