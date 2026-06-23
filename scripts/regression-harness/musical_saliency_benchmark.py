#!/usr/bin/env python3
"""Evaluate sb_musical_saliency on HarmonixSet using host-side replay.

The benchmark compiles a small harness that runs the real `sb_musical_saliency.cpp`
with host-provided `frame_ms novelty silence` novelty from `novelty_from_wav`.
It emits salient-event times as `S` rows and derives precision / recall / rate
metrics against HarmonixSet beat annotations.
"""

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

import novelty_from_wav as nfw


ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
DEFAULT_CORPUS = ROOT / "Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8"
DEFAULT_GT = Path("/Users/spectrasynq/Workspace_Management/Software/K1.reinvented/Implementation.plans/harmonixset-main/dataset")


ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""


CPP_REPLAY = r"""
#include "sb_musical_saliency.h"
#include "sb_onset_beat.h"

#include <cmath>
#include <cstdio>

int main() {
  sb_onset_beat_reset();
  char line[160];
  unsigned int last_ms = 0;
  unsigned long frames = 0;
  while (std::fgets(line, sizeof(line), stdin)) {
    unsigned int ms = 0;
    float novelty = 0.0f, spectral_energy = 0.0f, chroma_strength = 0.0f;
    int silence = 0;
    int got = std::sscanf(line, "%u %f %d %f %f", &ms, &novelty, &silence, &spectral_energy, &chroma_strength);
    if (got < 2) continue;
    if (got < 5) { spectral_energy = novelty; chroma_strength = novelty; }  // back-compat broadcast

    SBAudioSnapshot audio = {};
    audio.frame_ms = ms;
    audio.peak_scaled = novelty;
    audio.vu_level = novelty;
    audio.novelty = novelty;
    audio.spectral_energy = spectral_energy;
    audio.low_energy = spectral_energy;
    audio.mid_energy = spectral_energy;
    audio.high_energy = spectral_energy;
    audio.chroma_strength = chroma_strength;
    audio.silence = silence != 0;

    sb_onset_beat_update(audio);
    SBOnsetBeatEvent onset = sb_onset_beat_read();
    sb_musical_saliency_update(audio, &onset);

    SBSaliencyEvent ev = {};
    if (sb_musical_saliency_read_event(&ev, true)) {
      if (ev.salient) {
        std::printf("S %u %.6f %.6f %u\n", ms, ev.overallSaliency, ev.adaptiveThreshold, (unsigned)ev.ageMs);
      }
    }
    SBSaliencyAxisFrame ax = sb_musical_saliency_read();
    std::printf("O %u %.6f %d\n", ms, ax.overallSaliency, silence);
    last_ms = ms;
    frames++;
  }
  std::printf("FILE_DONE frames=%lu last_ms=%u\n", frames, last_ms);
  return 0;
}
"""


def build_binary(compiler="clang++", keep_dir=None):
    workdir = None
    if keep_dir:
        workdir = Path(keep_dir)
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        workdir = Path(tempfile.mkdtemp(prefix="sb_saliency_bench_"))

    stub_dir = workdir / "stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")

    main_cpp = workdir / "musical_saliency_benchmark_main.cpp"
    main_cpp.write_text(CPP_REPLAY, encoding="utf-8")

    binary = workdir / "musical_saliency_benchmark"
    compile_cmd = [
        compiler,
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-I",
        str(stub_dir),
        "-I",
        str(FIRMWARE),
        "-I",
        str(FIRMWARE / "audio"),
        str(FIRMWARE / "audio" / "sb_musical_saliency.cpp"),
        str(FIRMWARE / "audio" / "sb_onset_beat.cpp"),
        str(main_cpp),
        "-o",
        str(binary),
    ]

    r = subprocess.run(compile_cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        return {
            "ok": False,
            "stage": "compile",
            "returncode": r.returncode,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "workdir": str(workdir),
        }
    return {
        "ok": True,
        "stage": "compile",
        "binary": str(binary),
        "workdir": str(workdir),
    }


def run_replay(binary, lines):
    payload = "\n".join(lines)
    if payload:
        payload += "\n"
    r = subprocess.run([binary, "--replay-stdin"], cwd=ROOT, text=True, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    events = []
    oa_series = []
    frames = 0
    last_ms = None
    for row in r.stdout.splitlines():
        parts = row.strip().split()
        if not parts:
            continue
        if parts[0] == "S" and len(parts) >= 5:
            events.append(int(parts[1]))
        elif parts[0] == "O" and len(parts) >= 4:
            oa_series.append((int(parts[1]), float(parts[2]), int(parts[3])))
        elif parts[0] == "FILE_DONE":
            for tok in parts[1:]:
                if tok.startswith("frames="):
                    frames = int(tok.split("=", 1)[1])
                elif tok.startswith("last_ms="):
                    last_ms = int(tok.split("=", 1)[1])
    return {
        "ok": r.returncode == 0,
        "events_ms": events,
        "oa_series": oa_series,
        "frames": frames,
        "last_ms": last_ms,
        "stdout": r.stdout,
        "stderr": r.stderr,
        "returncode": r.returncode,
    }


def load_gt(gt_dir):
    gt_dir = Path(gt_dir)
    yt2key = {}
    with open(gt_dir / "index.jsonl", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("youtube_id") and row.get("file_key"):
                yt2key[row["youtube_id"]] = row["file_key"]

    key2bpm = {}
    with open(gt_dir / "metadata.csv", encoding="utf-8") as handle:
        import csv
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                key2bpm[row["File"]] = float(row["BPM"])
            except (KeyError, ValueError, TypeError):
                continue

    out = {}
    for yt, key in yt2key.items():
        if key not in key2bpm:
            continue
        beats = []
        beat_file = gt_dir / "beats_and_downbeats" / f"{key}.txt"
        if not beat_file.exists():
            continue
        with open(beat_file, encoding="utf-8") as handle:
            for line in handle:
                parts = line.strip().split()
                if not parts:
                    continue
                try:
                    beats.append(float(parts[0]) * 1000.0)
                except ValueError:
                    continue
        segments = []
        seg_file = gt_dir / "segments" / f"{key}.txt"
        if seg_file.exists():
            with open(seg_file, encoding="utf-8") as handle:
                for line in handle:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    try:
                        segments.append(float(parts[0]) * 1000.0)
                    except ValueError:
                        continue
        if beats:
            out[yt] = {"file_key": key, "bpm": key2bpm[key], "beats_ms": beats, "segments_ms": segments}
    return out


def _read_novelty_frames(path):
    frame_ms, nov, silence, spec, chroma = nfw.wav_to_features(path)
    lines = [f"{int(m)} {float(v):.6f} {int(s)} {float(e):.6f} {float(c):.6f}"
             for m, v, s, e, c in zip(frame_ms, nov, silence, spec, chroma)]
    total_ms = float(frame_ms[-1] - frame_ms[0]) if frame_ms.size else 0.0
    feats = {"novelty": nov, "spectral_energy": spec, "chroma_strength": chroma}
    return frame_ms, silence, lines, total_ms, feats


def _match_one_way(events, reference, tolerance_ms):
    if not events or not reference:
        return 0
    i = 0
    matched = 0
    for e in events:
        while i < len(reference) and reference[i] < e - tolerance_ms:
            i += 1
        if i >= len(reference):
            break
        if abs(reference[i] - e) <= tolerance_ms:
            matched += 1
            i += 1
    return matched


def _window_sums(frame_ms, silence, events_ms):
    if frame_ms.size == 0:
        return 0.0, 0.0, 0, 0
    if frame_ms.size != silence.size:
        raise ValueError("frame_ms and silence arrays out of sync")

    music_ms = 0.0
    silence_ms = 0.0
    for i in range(len(frame_ms) - 1):
        dt = float(frame_ms[i + 1] - frame_ms[i])
        if silence[i]:
            silence_ms += dt
        else:
            music_ms += dt

    # classify each salient event by the nearest frame timestamp.
    frame_idx = 0
    event_in_silence = 0
    for ev in events_ms:
        while frame_idx + 1 < frame_ms.size and frame_ms[frame_idx + 1] <= ev:
            frame_idx += 1
        if frame_idx < frame_ms.size and silence[frame_idx]:
            event_in_silence += 1

    return music_ms / 1000.0, silence_ms / 1000.0, event_in_silence, len(events_ms)


def _boundary_lift_sums(oa_series, segs_ms, win_ms):
    """Threshold-free, rate-free structure probe: mean overallSaliency within +/-win of a
    section boundary vs elsewhere (music frames only; silence excluded so far-baseline isn't
    deflated by silence zeros). Pooled lift = mean(near)/mean(far). Lift >> 1 => the detector
    tracks musical structure; lift ~ 1 => mis-scaled/dead. Decouples the structure verdict from
    the event firing rate, which segment-precision is structurally coupled to."""
    if not oa_series or not segs_ms:
        return 0.0, 0, 0.0, 0
    import bisect
    segs = sorted(segs_ms)
    near_sum = 0.0
    near_n = 0
    far_sum = 0.0
    far_n = 0
    for ms, oa, sil in oa_series:
        if sil:
            continue
        idx = bisect.bisect_left(segs, ms)
        near = False
        for cand_i in (idx - 1, idx):
            if 0 <= cand_i < len(segs) and abs(segs[cand_i] - ms) <= win_ms:
                near = True
                break
        if near:
            near_sum += oa
            near_n += 1
        else:
            far_sum += oa
            far_n += 1
    return near_sum, near_n, far_sum, far_n


def evaluate(corpus, gt_dir, limit=None, tolerance_ms=70):
    gt = load_gt(gt_dir)
    wavs = sorted(Path(corpus).glob("*.wav"))
    if limit:
        wavs = wavs[:limit]

    build = build_binary()
    if not build["ok"]:
        return {
            "ok": False,
            "stage": "compile",
            "build": build,
        }
    binary = build["binary"]

    total_events = 0
    total_beats = 0
    total_segments = 0
    precision_hits = 0
    recall_hits = 0
    precision_seg_hits = 0
    recall_seg_hits = 0
    total_music_s = 0.0
    total_silence_s = 0.0
    total_silence_events = 0
    near_oa_sum = 0.0
    near_oa_n = 0
    far_oa_sum = 0.0
    far_oa_n = 0
    seg_tolerance_ms = 1500
    lift_window_ms = 1500
    delta_lift_window_ms = 250  # raw deltas are TRANSIENT (spike at the transition, not across
                                # the whole section) -> use a TIGHT window; a 1.5s window would
                                # dilute a real boundary spike across ~400 frames -> false ~1.0.
    feat_keys = ("novelty", "spectral_energy", "chroma_strength")
    feat_near_sum = {k: 0.0 for k in feat_keys}
    feat_near_n = {k: 0 for k in feat_keys}
    feat_far_sum = {k: 0.0 for k in feat_keys}
    feat_far_n = {k: 0 for k in feat_keys}

    track_results = []
    for wav in wavs:
        yt = wav.stem.replace("_12k8", "")
        gt_row = gt.get(yt)
        if not gt_row:
            continue
        frame_ms, silence, lines, track_ms, feats = _read_novelty_frames(wav)
        if len(lines) == 0:
            continue
        replay = run_replay(binary, lines)
        if not replay["ok"]:
            return {
                "ok": False,
                "stage": "run",
                "binary": binary,
                "track": str(wav),
                "replay": replay,
            }

        events_ms = replay["events_ms"]
        beats_ms = gt_row["beats_ms"]
        segs_ms = gt_row.get("segments_ms", [])
        music_s, silence_s, silence_events, event_count = _window_sums(frame_ms, silence, events_ms)
        p_hits = _match_one_way(events_ms, beats_ms, tolerance_ms)
        r_hits = _match_one_way(list(beats_ms), events_ms, tolerance_ms)
        ps_hits = _match_one_way(events_ms, segs_ms, seg_tolerance_ms)
        rs_hits = _match_one_way(list(segs_ms), events_ms, seg_tolerance_ms)
        ns, nn, fs, fn = _boundary_lift_sums(replay.get("oa_series", []), segs_ms, lift_window_ms)

        total_events += event_count
        total_beats += len(beats_ms)
        total_segments += len(segs_ms)
        precision_hits += p_hits
        recall_hits += r_hits
        precision_seg_hits += ps_hits
        recall_seg_hits += rs_hits
        total_music_s += music_s
        total_silence_s += silence_s
        total_silence_events += silence_events
        near_oa_sum += ns
        near_oa_n += nn
        far_oa_sum += fs
        far_oa_n += fn

        # RC-4 decider: boundary-lift of each RAW per-feature delta (pre-threshold), so the
        # engine's (possibly mis-scaled) thresholds cannot mask whether the signal exists.
        for fk in feat_keys:
            fser = feats.get(fk)
            if fser is None or len(fser) == 0:
                continue
            dser = np.abs(np.diff(fser, prepend=fser[:1]))
            foa = list(zip((int(m) for m in frame_ms), (float(x) for x in dser), (int(s) for s in silence)))
            fns, fnn, ffs, ffn = _boundary_lift_sums(foa, segs_ms, delta_lift_window_ms)
            feat_near_sum[fk] += fns
            feat_near_n[fk] += fnn
            feat_far_sum[fk] += ffs
            feat_far_n[fk] += ffn

        track_lift = (ns / nn) / (fs / fn) if (nn and fn and fs > 0.0) else None
        track_results.append({
            "track": str(wav),
            "events": event_count,
            "beats": len(beats_ms),
            "segments": len(segs_ms),
            "precision_hits": p_hits,
            "recall_hits": r_hits,
            "precision_seg_hits": ps_hits,
            "recall_seg_hits": rs_hits,
            "boundary_lift": track_lift,
            "music_s": music_s,
            "silence_s": silence_s,
        })

    precision = precision_hits / total_events if total_events else 0.0
    recall = recall_hits / total_beats if total_beats else 0.0
    precision_seg = precision_seg_hits / total_events if total_events else 0.0
    recall_seg = recall_seg_hits / total_segments if total_segments else 0.0
    music_epm = (total_events * 60.0 / total_music_s) if total_music_s > 0.0 else math.inf
    silence_epm = (total_silence_events * 60.0 / total_silence_s) if total_silence_s > 0.0 else 0.0
    near_oa_mean = (near_oa_sum / near_oa_n) if near_oa_n else 0.0
    far_oa_mean = (far_oa_sum / far_oa_n) if far_oa_n else 0.0
    boundary_lift = (near_oa_mean / far_oa_mean) if far_oa_mean > 0.0 else 0.0

    raw_delta_lift = {}
    for fk in feat_keys:
        nm = (feat_near_sum[fk] / feat_near_n[fk]) if feat_near_n[fk] else 0.0
        fm = (feat_far_sum[fk] / feat_far_n[fk]) if feat_far_n[fk] else 0.0
        raw_delta_lift[fk] = {"lift": (nm / fm) if fm > 0.0 else 0.0, "near_mean": nm, "far_mean": fm}
    _max_lift = max((v["lift"] for v in raw_delta_lift.values()), default=0.0)

    # GATED criteria drive `ok` (the structure verdict):
    #  - music/silence epm : RC-1 gate-fix proof (event rate sane; no silence misfire)
    #  - recall_segments    : did salient events land on section boundaries (sparse, achievable)
    #  - boundary_lift       : rate-free structure tracking -- the decisive discriminator
    # REPORTED-ONLY (not gated): precision_beats / recall_beats (dense beats are the wrong
    # reference) and precision_segments (coupled to firing rate -- a dense gate caps it ~0.2
    # regardless of detector quality, so it is NOT a clean detector verdict; boundary_lift
    # replaces it as the structure measure).
    criteria = {
        "precision_beats": {
            "value": precision, "pass": precision >= 0.65, "threshold": 0.65,
            "matched": precision_hits, "denominator": total_events, "gated": False,
        },
        "recall_beats": {
            "value": recall, "pass": recall >= 0.45, "threshold": 0.45,
            "matched": recall_hits, "denominator": total_beats, "gated": False,
        },
        "precision_segments": {
            "value": precision_seg, "pass": precision_seg >= 0.40, "threshold": 0.40,
            "matched": precision_seg_hits, "denominator": total_events,
            "tolerance_ms": seg_tolerance_ms, "gated": False,
            "note": "rate-coupled; informational, not a detector verdict",
        },
        "recall_segments": {
            "value": recall_seg, "pass": recall_seg >= 0.45, "threshold": 0.45,
            "matched": recall_seg_hits, "denominator": total_segments,
            "tolerance_ms": seg_tolerance_ms, "gated": True,
        },
        "boundary_lift": {
            "value": boundary_lift, "pass": boundary_lift >= 1.5, "threshold": 1.5,
            "near_oa_mean": near_oa_mean, "far_oa_mean": far_oa_mean,
            "near_frames": near_oa_n, "far_frames": far_oa_n,
            "window_ms": lift_window_ms, "gated": True,
        },
        "music_events_per_min": {
            "value": music_epm, "pass": 40.0 <= music_epm <= 180.0,
            "lower": 40.0, "upper": 180.0, "gated": True,
        },
        "silence_events_per_min": {
            "value": silence_epm, "pass": silence_epm < 12.0, "threshold": 12.0, "gated": True,
        },
        "raw_delta_lift": {
            "value": _max_lift, "per_feature": raw_delta_lift,
            "pass": _max_lift >= 1.2, "threshold": 1.2, "gated": False,
            "window_ms": delta_lift_window_ms,
            "note": "RC-4 decider: does ANY raw per-feature delta lift at a section boundary? "
                    ">=1.2 => instantaneous signal EXISTS => RC-2 (recoverable by conditioning); "
                    "all ~1.0 => RC-4 (no instantaneous structure) => pivot to periodicity",
        },
    }

    gated_ok = all(v["pass"] for v in criteria.values() if v.get("gated"))
    return {
        "ok": gated_ok,
        "n_tracks_scored": len(track_results),
        "track_results": track_results,
        "criteria": criteria,
        "totals": {
            "events": total_events,
            "beats": total_beats,
            "segments": total_segments,
            "precision_hits": precision_hits,
            "recall_hits": recall_hits,
            "precision_seg_hits": precision_seg_hits,
            "recall_seg_hits": recall_seg_hits,
            "music_s": total_music_s,
            "silence_s": total_silence_s,
            "silence_events": total_silence_events,
            "near_oa_n": near_oa_n,
            "far_oa_n": far_oa_n,
        },
        "build": build,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--gt-dataset", default=str(DEFAULT_GT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tolerance-ms", type=int, default=70)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    result = evaluate(Path(args.corpus), args.gt_dataset, limit=args.limit, tolerance_ms=args.tolerance_ms)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok", False) else 1

    if not result.get("ok", False) and result.get("stage") in {"compile", "run"}:
        print(f"FAIL: {result['stage']} stage failed", file=sys.stderr)
        if "build" in result and result["build"].get("stderr"):
            print(result["build"]["stderr"], file=sys.stderr)
        if "replay" in result:
            print(result["replay"]["stderr"], file=sys.stderr)
        return 2

    print(f"tracks_scored={result['n_tracks_scored']}")
    c = result["criteria"]
    print(f"precision_beats={c['precision_beats']['value']:.3f} matched={c['precision_beats']['matched']}/{c['precision_beats']['denominator']} pass={c['precision_beats']['pass']} (reported)")
    print(f"recall_beats={c['recall_beats']['value']:.4f} matched={c['recall_beats']['matched']}/{c['recall_beats']['denominator']} (reported)")
    print(f"precision_segments={c['precision_segments']['value']:.3f} (informational, rate-coupled)")
    print(f"recall_segments={c['recall_segments']['value']:.3f} matched={c['recall_segments']['matched']}/{c['recall_segments']['denominator']} pass={c['recall_segments']['pass']} [GATED]")
    print(f"boundary_lift={c['boundary_lift']['value']:.3f} (near={c['boundary_lift']['near_oa_mean']:.4f} far={c['boundary_lift']['far_oa_mean']:.4f}) pass={c['boundary_lift']['pass']} [GATED]")
    print(f"music_events_per_min={c['music_events_per_min']['value']:.3f} pass={c['music_events_per_min']['pass']} [GATED]")
    print(f"silence_events_per_min={c['silence_events_per_min']['value']:.3f} pass={c['silence_events_per_min']['pass']} [GATED]")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
