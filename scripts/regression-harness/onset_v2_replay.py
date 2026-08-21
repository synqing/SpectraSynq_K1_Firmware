#!/usr/bin/env python3
"""WAV -> 80-bin spectrogram -> REAL k1_onset_beat.cpp -> per-frame onset/band events.

This is the onset analogue of tempo_accuracy.py. It drives the UNMODIFIED
(compiled) `k1_onset_beat.cpp` -- either the incumbent dual-EMA path (no flag) or
the donor-shaped V2 path (`-DK1_ONSET_V2`) -- with a real-music per-note
spectrogram synthesised from the 12.8 kHz corpus, and scores:

  * onset precision/recall vs GT *beats* (PROXY -- GT is beats, not onsets; we
    label it a proxy: percussive beats SHOULD carry an onset, so onset-vs-beat
    P/R is a directional indicator, not a labelled-onset score),
  * per-band kick/snare/hihat event counts + band separation sanity,
  * refractory adherence (min inter-event gap per channel >= configured refractory),
  * an AGC-CLAMP regression: scale the spectrogram hard into the [0,1] clamp and
    confirm the V2 onset density survives where the incumbent flatlines (ON-02).

Spectrogram synthesis (mirrors the fork's per-note GDFT + broadband AGC):
  - rfft magnitude per 96-sample hop (133.333 Hz AP frame rate, NFFT=512),
  - fold linear rfft bins into the 80 chromatic note bins of constants.h `notes[]`
    by nearest-note assignment (each note bin = sum of rfft bins closest to it),
  - broadband AGC: divide by a slow envelope so the mean bin level tracks a
    target, then HARD-CLAMP to [0,1] -- the exact behaviour of GDFT.h:269-279 that
    causes ON-02. `--agc-clamp-hard` pushes the AGC target up so most bins pin at
    1.0 (the loud/clamped regime).

The spectrogram is fed to the firmware as one `S <ms> <silence> <b0..b79>` line
per frame; the generated replay main parses it, fills K1AudioSnapshot.spectrum[]
(+ the legacy scalar band means, identically to k1_audio_snapshot.cpp), calls the
real k1_onset_beat_update, and prints one event line per frame.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wavfile

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parents[1]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

SAMPLE_RATE = 12800
HOP = 96            # one AP frame per hop -> 133.333 Hz
NFFT = 512
NUM_FREQS = 80

# constants.h `notes[]` -- bin i centre frequency (Hz). A1=55, chromatic. The
# full table is 96 long; NUM_FREQS=80 uses the first 80 (55 Hz .. 11.18 kHz).
NOTES = np.array([
    55.00000, 58.27047, 61.73541, 65.40639, 69.29566, 73.41619, 77.78175, 82.40689, 87.30706, 92.49861, 97.99886, 103.8262,
    110.0000, 116.5409, 123.4708, 130.8128, 138.5913, 146.8324, 155.5635, 164.8138, 174.6141, 184.9972, 195.9977, 207.6523,
    220.0000, 233.0819, 246.9417, 261.6256, 277.1826, 293.6648, 311.1270, 329.6276, 349.2282, 369.9944, 391.9954, 415.3047,
    440.0000, 466.1638, 493.8833, 523.2511, 554.3653, 587.3295, 622.2540, 659.2551, 698.4565, 739.9888, 783.9909, 830.6094,
    880.0000, 932.3275, 987.7666, 1046.502, 1108.731, 1174.659, 1244.508, 1318.510, 1396.913, 1479.978, 1567.982, 1661.219,
    1760.000, 1864.655, 1975.533, 2093.005, 2217.461, 2349.318, 2489.016, 2637.020, 2793.825, 2959.956, 3135.964, 3322.437,
    3520.000, 3729.310, 3951.065, 4186.009, 4434.922, 4698.636, 4978.032, 5274.041, 5587.652, 5919.911, 6271.927, 6644.875,
    7040.000, 7458.620, 7902.130, 8372.018, 8869.844, 9397.272, 9956.064, 10548.08, 11175.30, 11839.82, 12543.85, 13289.75,
], dtype=np.float64)
NOTES = NOTES[:NUM_FREQS]


# --------------------------------------------------------------------------- features
def _to_mono_float(sr, data):
    x = data.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        x /= float(np.iinfo(data.dtype).max)
    return x, sr


def wav_to_spectrogram(path, agc_target=0.4, agc_clamp_hard=False):
    """Return (frame_ms[N], spec[N,80] in [0,1], silence[N]).

    Mirrors the fork: per-note magnitude -> broadband AGC (slow envelope, gain =
    target/envelope) -> HARD clamp to [0,1]. agc_clamp_hard raises the effective
    target so most bins saturate at 1.0 (the loud/clamped ON-02 regime).
    """
    sr, data = wavfile.read(str(path))
    x, sr = _to_mono_float(sr, data)
    if sr != SAMPLE_RATE:
        raise ValueError(f"{path}: sample rate {sr} != {SAMPLE_RATE}")
    n = x.shape[0]
    if n < NFFT:
        raise ValueError(f"{path}: only {n} samples")

    nframes = 1 + (n - NFFT) // HOP
    starts = np.arange(nframes) * HOP
    frames = np.lib.stride_tricks.sliding_window_view(x, NFFT)[starts]
    win = np.hanning(NFFT)
    mag = np.abs(np.fft.rfft(frames * win, axis=1))      # [N, NFFT/2+1]
    freqs = np.fft.rfftfreq(NFFT, d=1.0 / SAMPLE_RATE)

    # Nearest-note fold: assign each rfft bin to its closest note bin, sum.
    # (log-spaced note edges; argmin over |log f - log note|.)
    valid = freqs > 20.0
    note_of = np.full(freqs.shape, -1, dtype=np.int64)
    lf = np.log(np.maximum(freqs[valid], 1e-9))
    ln = np.log(NOTES)
    note_of[valid] = np.argmin(np.abs(lf[:, None] - ln[None, :]), axis=1)
    spec = np.zeros((nframes, NUM_FREQS), dtype=np.float64)
    for k in range(NUM_FREQS):
        cols = np.where(note_of == k)[0]
        if cols.size:
            spec[:, k] = mag[:, cols].sum(axis=1)

    # Per-frame broadband signal level + slow envelope follower (asymmetric),
    # echoing GDFT.h broadband AGC v2 (attack 0.28, release 0.02 @ ~100 Hz).
    sig = spec.mean(axis=1)
    env = np.zeros_like(sig)
    e = sig[0] if sig.size else 0.0
    A, R = 0.28, 0.02
    for i in range(sig.size):
        e += (sig[i] - e) * (A if sig[i] > e else R)
        env[i] = max(e, 1e-6)
    target = agc_target * (3.0 if agc_clamp_hard else 1.0)
    gain = np.clip(target / env, 0.1, 10.0)
    spec = spec * gain[:, None]
    spec = np.clip(spec, 0.0, 1.0)         # the ON-02 hard clamp

    rms = np.sqrt((frames ** 2).mean(axis=1))
    med = float(np.median(rms))
    floor = max(0.005, 0.05 * med)
    silence = (rms < floor).astype(np.int8)

    frame_ms = np.round(starts * 1000.0 / SAMPLE_RATE).astype(np.int64)
    return frame_ms, spec, silence


# --------------------------------------------------------------------------- replay main
ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""

# Reads 'S <ms> <silence> b0..b79' lines on stdin, fills K1AudioSnapshot
# (spectrum[] + legacy scalar band means EXACTLY as k1_audio_snapshot.cpp does),
# runs the real k1_onset_beat_update, prints per-frame events.
CPP_REPLAY = r"""
#include "k1_onset_beat.h"
#include <cstdio>
#include <cmath>

static float clampnn(float v){ return (!std::isfinite(v)||v<0.0f)?0.0f:v; }

int main(){
  k1_onset_beat_reset();
  char tag; long ms; int sil;
  static float spec[80];
  while (std::scanf(" %c", &tag) == 1) {
    if (tag != 'S') { /* skip line */ int c; while((c=getchar())!='\n'&&c!=EOF){} continue; }
    if (std::scanf("%ld %d", &ms, &sil) != 2) break;
    for (int i=0;i<80;i++){ if (std::scanf("%f",&spec[i])!=1){ spec[i]=0.0f; } }

    K1AudioSnapshot a = {};
    a.frame_ms = (uint32_t)ms;
    a.silence = sil != 0;
#ifdef K1_ONSET_V2
    for (int i=0;i<80;i++) a.spectrum[i] = clampnn(spec[i]);
#endif
    // Legacy scalar band means -- identical thirds split to k1_audio_snapshot.cpp.
    float low=0,mid=0,hi=0;
    for (int i=0;i<80;i++){ float v=clampnn(spec[i]);
      if (i<80/3) low+=v; else if (i<(80*2)/3) mid+=v; else hi+=v; }
    a.low_energy  = low/float(80/3);
    a.mid_energy  = mid/float((80*2)/3 - 80/3);
    a.high_energy = hi/float(80 - (80*2)/3);
    a.spectral_energy = (low+mid+hi)/80.0f;
    // novelty/peak proxies for the incumbent path: use spectral_energy delta-free
    // surrogates so the incumbent has a fair shot (it keys on novelty+peak+low).
    a.novelty = a.spectral_energy;
    a.peak_scaled = a.spectral_energy;

    k1_onset_beat_update(a);
    K1OnsetBeatEvent e = k1_onset_beat_read();

    int onset = (e.event_age_ms == 0 && (e.onset || e.bass_onset)) ? 1 : 0;
#ifdef K1_ONSET_V2
    std::printf("E %ld %d %d %d %d %d %.4f %.4f %.4f %.4f\n",
      ms, onset, e.kick?1:0, e.snare?1:0, e.hihat?1:0, e.transient?1:0,
      e.onset_strength, e.kick_strength, e.snare_strength, e.hihat_strength);
#else
    std::printf("E %ld %d 0 0 0 0 %.4f 0 0 0\n", ms, onset, e.onset_strength);
#endif
  }
  std::printf("ONSET_V2_REPLAY_DONE\n");
  return 0;
}
"""


def build_replay(defines, workdir, compiler="clang++"):
    workdir = Path(workdir)
    stub = workdir / "stub"
    stub.mkdir(parents=True, exist_ok=True)
    (stub / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
    main_cpp = workdir / "onset_v2_main.cpp"
    main_cpp.write_text(CPP_REPLAY, encoding="utf-8")
    binary = workdir / "onset_v2_replay"
    cmd = [compiler, "-std=c++17", "-O2", "-I", str(stub), "-I", str(FIRMWARE)]
    for d in ("audio", "visual", "effects", "director", "serial", "system",
              "persistence", "calibration", "diag", "platform"):
        cmd += ["-I", str(FIRMWARE / d)]
    for d in defines:
        cmd += [f"-D{d}"]
    cmd += [str(next(FIRMWARE.rglob("k1_onset_beat.cpp"))), str(main_cpp), "-o", str(binary)]
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"compile failed:\n{r.stderr}")
    return binary


def run_replay(binary, frame_ms, spec, silence):
    lines = []
    for m, row, s in zip(frame_ms, spec, silence):
        lines.append(f"S {int(m)} {int(s)} " + " ".join(f"{v:.4f}" for v in row))
    stdin = "\n".join(lines) + "\n"
    r = subprocess.run([str(binary)], input=stdin, text=True, capture_output=True)
    events = []
    for ln in r.stdout.splitlines():
        if not ln.startswith("E "):
            continue
        p = ln.split()
        events.append({
            "ms": int(p[1]), "onset": int(p[2]), "kick": int(p[3]),
            "snare": int(p[4]), "hihat": int(p[5]), "transient": int(p[6]),
            "onset_str": float(p[7]), "kick_str": float(p[8]),
            "snare_str": float(p[9]), "hihat_str": float(p[10]),
        })
    return events


# --------------------------------------------------------------------------- GT join + scoring
def load_yt2key(gt_dir):
    yt2key = {}
    idx = Path(gt_dir) / "index.jsonl"
    if idx.exists():
        for line in idx.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("youtube_id") and r.get("file_key"):
                yt2key[r["youtube_id"]] = r["file_key"]
    return yt2key


def load_gt_beats(gt_dir, file_key):
    p = Path(gt_dir) / "beats_and_downbeats" / f"{file_key}.txt"
    if not p.exists():
        return None
    times = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if parts:
            try:
                times.append(float(parts[0]))
            except ValueError:
                pass
    return np.array(times) if times else None


def onset_pr_vs_beats(event_ms_onsets, gt_beats_s, tol_ms=70.0):
    """PROXY P/R: each GT beat matched to nearest onset within tol; precision =
    matched onsets / total onsets, recall = matched beats / total beats."""
    if gt_beats_s is None or gt_beats_s.size == 0:
        return None
    onsets = np.array(sorted(event_ms_onsets), dtype=float)
    beats = gt_beats_s * 1000.0
    if onsets.size == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0,
                "n_onset": 0, "n_beat": int(beats.size), "tp": 0}
    matched_beats = 0
    used = np.zeros(onsets.size, dtype=bool)
    for b in beats:
        d = np.abs(onsets - b)
        j = int(np.argmin(d))
        if d[j] <= tol_ms and not used[j]:
            used[j] = True
            matched_beats += 1
    tp = matched_beats
    precision = tp / onsets.size
    recall = tp / beats.size
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1,
            "n_onset": int(onsets.size), "n_beat": int(beats.size), "tp": int(tp)}


def min_gap_ms(times):
    if len(times) < 2:
        return None
    d = np.diff(np.array(sorted(times)))
    return float(d.min())


def score_events(events):
    onset_ms = [e["ms"] for e in events if e["onset"]]
    kick_ms = [e["ms"] for e in events if e["kick"]]
    snare_ms = [e["ms"] for e in events if e["snare"]]
    hihat_ms = [e["ms"] for e in events if e["hihat"]]
    trans_ms = [e["ms"] for e in events if e["transient"]]
    return {
        "onset_ms": onset_ms, "kick_ms": kick_ms, "snare_ms": snare_ms,
        "hihat_ms": hihat_ms, "trans_ms": trans_ms,
        "n_onset": len(onset_ms), "n_kick": len(kick_ms),
        "n_snare": len(snare_ms), "n_hihat": len(hihat_ms), "n_trans": len(trans_ms),
        "min_gap_kick": min_gap_ms(kick_ms), "min_gap_snare": min_gap_ms(snare_ms),
        "min_gap_hihat": min_gap_ms(hihat_ms),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default=str(
        ROOT / "Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8"))
    ap.add_argument("--gt", default="/Users/spectrasynq/Workspace_Management/Software/K1.reinvented/Implementation.plans/harmonixset-main/dataset")
    ap.add_argument("--limit", type=int, default=12, help="max tracks")
    ap.add_argument("--out", default=str(ROOT / "build/audio-semantic-metrics/onset_v2_ab.json"))
    ap.add_argument("--compiler", default="clang++")
    args = ap.parse_args(argv)

    corpus = Path(args.corpus)
    wavs = sorted(corpus.glob("*.wav"))[: args.limit]
    yt2key = load_yt2key(args.gt)

    tmp = tempfile.TemporaryDirectory()
    bin_incumbent = build_replay([], tmp.name + "/inc", args.compiler)
    bin_v2 = build_replay(["K1_ONSET_V2"], tmp.name + "/v2", args.compiler)

    results = {"tracks": [], "agc_clamp": {}}
    agg = {"inc": [], "v2": []}
    for wav in wavs:
        yt = wav.stem.replace("_12k8", "")
        file_key = yt2key.get(yt)
        gt_beats = load_gt_beats(args.gt, file_key) if file_key else None

        fm, spec, sil = wav_to_spectrogram(wav)
        ev_inc = run_replay(bin_incumbent, fm, spec, sil)
        ev_v2 = run_replay(bin_v2, fm, spec, sil)
        s_inc = score_events(ev_inc)
        s_v2 = score_events(ev_v2)
        pr_inc = onset_pr_vs_beats(s_inc["onset_ms"], gt_beats)
        pr_v2 = onset_pr_vs_beats(s_v2["onset_ms"], gt_beats)
        if pr_inc:
            agg["inc"].append(pr_inc)
        if pr_v2:
            agg["v2"].append(pr_v2)
        results["tracks"].append({
            "wav": wav.name, "file_key": file_key,
            "dur_s": float(fm[-1] / 1000.0),
            "incumbent": {"n_onset": s_inc["n_onset"], "pr": pr_inc},
            "v2": {"n_onset": s_v2["n_onset"], "n_kick": s_v2["n_kick"],
                   "n_snare": s_v2["n_snare"], "n_hihat": s_v2["n_hihat"],
                   "min_gap_kick": s_v2["min_gap_kick"],
                   "min_gap_snare": s_v2["min_gap_snare"],
                   "min_gap_hihat": s_v2["min_gap_hihat"], "pr": pr_v2},
        })

    # ---- AGC-clamp regression: first track, hard-clamped spectrogram ----
    if wavs:
        fm, spec_hard, sil = wav_to_spectrogram(wavs[0], agc_clamp_hard=True)
        clamp_frac = float((spec_hard >= 0.999).mean())
        ev_inc = run_replay(bin_incumbent, fm, spec_hard, sil)
        ev_v2 = run_replay(bin_v2, fm, spec_hard, sil)
        s_inc = score_events(ev_inc)
        s_v2 = score_events(ev_v2)
        dur_min = max(fm[-1] / 60000.0, 1e-6)
        results["agc_clamp"] = {
            "wav": wavs[0].name, "clamp_frac": clamp_frac,
            "incumbent_onsets_per_min": s_inc["n_onset"] / dur_min,
            "v2_onsets_per_min": s_v2["n_onset"] / dur_min,
            "v2_kick_per_min": s_v2["n_kick"] / dur_min,
            "incumbent_n_onset": s_inc["n_onset"], "v2_n_onset": s_v2["n_onset"],
            "v2_n_kick": s_v2["n_kick"],
        }

    def mean_pr(lst):
        if not lst:
            return None
        return {"precision": float(np.mean([x["precision"] for x in lst])),
                "recall": float(np.mean([x["recall"] for x in lst])),
                "f1": float(np.mean([x["f1"] for x in lst])),
                "n_tracks": len(lst)}
    results["summary"] = {
        "incumbent_pr_proxy": mean_pr(agg["inc"]),
        "v2_pr_proxy": mean_pr(agg["v2"]),
        "n_tracks_scored": len(results["tracks"]),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    s = results["summary"]
    print("INCUMBENT pr-proxy:", s["incumbent_pr_proxy"])
    print("V2        pr-proxy:", s["v2_pr_proxy"])
    print("AGC-CLAMP:", json.dumps(results["agc_clamp"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
