#!/usr/bin/env python3
"""Lane 1: quantify alias / high-bin contamination at 12.8 kHz (bins 70–79).

Offline host audit — no device required. Two parts:
  A) Synthetic pure-tone fold map (which semitone bins light up above Nyquist).
  B) HarmonixSet corpus: bright vs dark tracks; compare labelled hi-hat band energy
     at 12.8 kHz vs true HF energy on a 32 kHz reference resample.

Outputs JSON summary to --out (default: evidence/sample-rate-lanes/).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = (
    ROOT
    / "Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8"
)

SAMPLE_RATE = 12800
REF_SR = 32000
HOP = 96
NFFT = 512
NOTE_OFFSET = 12
NUM_FREQS = 80
HIHAT_LO, HIHAT_HI = 70, 80  # sb_onset_beat.cpp SBV2_HIHAT_LO/HI
NYQUIST = SAMPLE_RATE / 2.0

# constants.h notes[] (A1 = 55 Hz, semitone-spaced)
NOTES = np.array(
    [
        55.00000, 58.27047, 61.73541, 65.40639, 69.29566, 73.41619, 77.78175,
        82.40689, 87.30706, 92.49861, 97.99886, 103.8262, 110.0000, 116.5409,
        123.4708, 130.8128, 138.5913, 146.8324, 155.5635, 164.8138, 174.6141,
        184.9972, 195.9977, 207.6523, 220.0000, 233.0819, 246.9417, 261.6256,
        277.1826, 293.6648, 311.1270, 329.6276, 349.2282, 369.9944, 391.9954,
        415.3047, 440.0000, 466.1638, 493.8833, 523.2511, 554.3653, 587.3295,
        622.2540, 659.2551, 698.4565, 739.9888, 783.9909, 830.6094, 880.0000,
        932.3275, 987.7666, 1046.502, 1108.731, 1174.659, 1244.508, 1318.510,
        1396.913, 1479.978, 1567.982, 1661.219, 1760.000, 1864.655, 1975.533,
        2093.005, 2217.461, 2349.318, 2489.016, 2637.020, 2793.825, 2959.956,
        3135.964, 3322.437, 3520.000, 3729.310, 3951.065, 4186.009, 4434.922,
        4698.636, 4978.032, 5274.041, 5587.652, 5919.911, 6271.927, 6644.875,
        7040.000, 7458.620, 7902.130, 8372.018, 8869.844, 9397.272, 9956.064,
        10548.08, 11175.30, 11839.82, 12543.85, 13289.75,
    ],
    dtype=np.float64,
)


def bin_target_freq(bin_idx: int, note_offset: int = NOTE_OFFSET) -> float:
    return float(NOTES[note_offset + bin_idx])


def _target_freqs() -> np.ndarray:
    return np.array([bin_target_freq(b) for b in range(NUM_FREQS)], dtype=np.float64)


def frame_semitone_spectrum(
    x: np.ndarray, sr: int, hop: int = HOP, nfft: int = NFFT
) -> np.ndarray:
    """FFT-derived narrowband energy per semitone bin (fast host proxy for GDFT)."""
    nframes = 1 + (len(x) - nfft) // hop
    starts = np.arange(nframes) * hop
    win = np.hanning(nfft)
    frames = np.lib.stride_tricks.sliding_window_view(x, nfft)[starts] * win
    mag = np.abs(np.fft.rfft(frames, axis=1))  # [nframes, nfft//2+1]
    fft_freqs = np.fft.rfftfreq(nfft, 1.0 / sr)
    targets = _target_freqs()
    out = np.zeros((nframes, NUM_FREQS), dtype=np.float64)
    # Half semitone bandwidth (~3% frequency) for each target note.
    for b, f0 in enumerate(targets):
        lo = f0 * (2.0 ** (-1.0 / 24.0))
        hi = f0 * (2.0 ** (1.0 / 24.0))
        mask = (fft_freqs >= lo) & (fft_freqs <= hi)
        out[:, b] = mag[:, mask].sum(axis=1)
    return out


def _to_mono_float(data: np.ndarray) -> np.ndarray:
    x = data.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        x /= float(np.iinfo(data.dtype).max)
    return x


def synthetic_alias_map() -> dict:
    """Pure tones above Nyquist: where energy lands in semitone bins."""
    duration = 1.0
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n) / SAMPLE_RATE
    tones = [300.0, 2000.0, 5500.0, 7000.0, 9000.0, 11000.0, 13000.0]
    rows = []
    for f in tones:
        x = 0.5 * np.sin(2 * math.pi * f * t)
        g = frame_semitone_spectrum(x, SAMPLE_RATE)
        mean_mag = g.mean(axis=0)
        peak_bin = int(mean_mag.argmax())
        hihat_sum = float(mean_mag[HIHAT_LO:HIHAT_HI].sum())
        below_nyq_sum = float(
            mean_mag[[i for i in range(NUM_FREQS) if bin_target_freq(i) <= NYQUIST]].sum()
        )
        rows.append(
            {
                "tone_hz": f,
                "above_nyquist": f > NYQUIST,
                "alias_of_hz": round(f - SAMPLE_RATE, 1) if f > NYQUIST else None,
                "peak_bin": peak_bin,
                "peak_bin_label_hz": round(bin_target_freq(peak_bin), 1),
                "peak_mag": round(float(mean_mag[peak_bin]), 6),
                "hihat_band_sum_bins_70_79": round(hihat_sum, 6),
                "below_nyq_bin_sum": round(below_nyq_sum, 6),
                "hihat_fraction_of_total": round(
                    hihat_sum / max(mean_mag.sum(), 1e-12), 4
                ),
            }
        )
    return {"synthetic_tones": rows, "nyquist_hz": NYQUIST}


def corpus_track_metrics(path: Path) -> dict:
    sr, data = wavfile.read(str(path))
    x = _to_mono_float(data)
    if sr != SAMPLE_RATE:
        x = signal.resample(x, int(len(x) * SAMPLE_RATE / sr))

    # 32 kHz reference for "true" HF content (6.4–12 kHz band).
    x_ref = signal.resample(x, int(len(x) * REF_SR / SAMPLE_RATE))
    nframes = 1 + (len(x_ref) - NFFT) // HOP
    hf_ref_energy = []
    lf_ref_energy = []
    win = np.hanning(NFFT)
    for fi in range(nframes):
        start = fi * HOP
        frame = x_ref[start : start + NFFT] * win
        spec = np.abs(np.fft.rfft(frame))
        freqs = np.fft.rfftfreq(NFFT, 1.0 / REF_SR)
        hf_ref_energy.append(float(spec[(freqs >= 6400) & (freqs < 12000)].sum()))
        lf_ref_energy.append(float(spec[freqs < 500].sum()))

    hf_ref_mean = float(np.mean(hf_ref_energy))
    lf_ref_mean = float(np.mean(lf_ref_energy))
    bright_score = hf_ref_mean / max(hf_ref_mean + lf_ref_mean, 1e-12)

    g = frame_semitone_spectrum(x, SAMPLE_RATE)
    mean_mag = g.mean(axis=0)

    def band_sum(lo: int, hi: int) -> float:
        return float(mean_mag[lo:hi].sum())

    hihat = band_sum(HIHAT_LO, HIHAT_HI)
    trans = band_sum(1, 76)
    kick = band_sum(1, 25)
    total = float(mean_mag.sum())

    # Bins whose *label* exceeds Nyquist (misleading targets)
    above_label = [
        i
        for i in range(NUM_FREQS)
        if bin_target_freq(i) > NYQUIST
    ]
    above_label_energy = float(mean_mag[above_label].sum()) if above_label else 0.0

    return {
        "file": path.name,
        "bright_score": round(bright_score, 4),
        "hf_ref_6p4_12k": round(hf_ref_mean, 6),
        "lf_ref_below_500": round(lf_ref_mean, 6),
        "hihat_bins_70_79": round(hihat, 6),
        "transient_bins_1_75": round(trans, 6),
        "kick_bins_1_24": round(kick, 6),
        "above_nyq_label_bin_energy": round(above_label_energy, 6),
        "hihat_over_transient": round(hihat / max(trans, 1e-12), 4),
        "alias_contamination_index": round(
            hihat / max(hf_ref_mean, 1e-12), 4
        ),
        "hihat_fraction_of_total": round(hihat / max(total, 1e-12), 4),
    }


def run_corpus(corpus: Path, limit: int | None) -> dict:
    wavs = sorted(corpus.glob("*.wav"))
    if limit:
        wavs = wavs[:limit]
    tracks = [corpus_track_metrics(p) for p in wavs]
    if not tracks:
        return {"tracks": [], "summary": {}}

    bright = sorted(tracks, key=lambda t: t["bright_score"], reverse=True)
    dark = sorted(tracks, key=lambda t: t["bright_score"])
    n = len(tracks)
    top_b = bright[: max(1, n // 4)]
    bot_d = dark[: max(1, n // 4)]

    def avg(key: str, items: list) -> float:
        return float(np.mean([t[key] for t in items]))

    summary = {
        "n_tracks": n,
        "nyquist_hz": NYQUIST,
        "hihat_bin_range": [HIHAT_LO, HIHAT_HI - 1],
        "hihat_label_hz_range": [
            round(bin_target_freq(HIHAT_LO), 1),
            round(bin_target_freq(HIHAT_HI - 1), 1),
        ],
        "all_tracks_mean_hihat_70_79": round(avg("hihat_bins_70_79", tracks), 6),
        "all_tracks_mean_alias_index": round(avg("alias_contamination_index", tracks), 4),
        "bright_quartile_mean_bright_score": round(avg("bright_score", top_b), 4),
        "dark_quartile_mean_bright_score": round(avg("bright_score", bot_d), 4),
        "bright_quartile_mean_hihat_70_79": round(avg("hihat_bins_70_79", top_b), 6),
        "dark_quartile_mean_hihat_70_79": round(avg("hihat_bins_70_79", bot_d), 6),
        "bright_quartile_mean_alias_index": round(
            avg("alias_contamination_index", top_b), 4
        ),
        "dark_quartile_mean_alias_index": round(
            avg("alias_contamination_index", bot_d), 4
        ),
        "bright_dark_hihat_ratio": round(
            avg("hihat_bins_70_79", top_b) / max(avg("hihat_bins_70_79", bot_d), 1e-12),
            3,
        ),
        "bright_quartile_top5": [t["file"] for t in top_b[:5]],
        "dark_quartile_bottom5": [t["file"] for t in bot_d[:5]],
    }
    return {"tracks": tracks, "summary": summary}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "evidence/sample-rate-lanes/20260609-lane1-alias-audit.json",
    )
    args = p.parse_args()

    report = {
        "lane": 1,
        "title": "High-bin alias contamination audit @ 12.8 kHz",
        "sample_rate_hz": SAMPLE_RATE,
        "reference_sr_hz": REF_SR,
        "synthetic": synthetic_alias_map(),
    }

    if args.corpus.is_dir():
        report["corpus"] = run_corpus(args.corpus, args.limit)
        report["corpus_path"] = str(args.corpus)
    else:
        report["corpus"] = {"error": f"corpus not found: {args.corpus}"}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["corpus"].get("summary", report.get("corpus")), indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
