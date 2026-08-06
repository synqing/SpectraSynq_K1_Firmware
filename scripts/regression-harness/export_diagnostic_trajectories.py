#!/usr/bin/env python3
"""Export unified per-track diagnostic TRAJECTORIES for the audio forward-graft notebook.

DISPLAY-PRODUCING, NOT DSP. This script runs the EXISTING host harness binaries
(tempo_replay, onset_v2_replay) on the corpus and dumps their per-frame output
verbatim into a single JSON per (track, run). It reimplements NO tempo / beat /
onset / saliency / AP DSP — every numeric field is produced by the compiled,
UNMODIFIED firmware C++ (k1_tempo.cpp / k1_onset_beat.cpp) replayed through the
canonical harness modules:

  novelty_from_wav.wav_to_novelty   -> 'ms novelty silence' lines      (front-end)
  tempo_replay.build_binary/replay_stdin
      run=baseline : no defines                 -> incumbent k1_tempo
      run=final    : K1_TEMPO_CONF_V2 +
                     K1_TEMPO_FLYWHEEL_V2        -> the graft confidence/lock/beat path
      -> 'T <ms> <bpm> <conf> <locked> <phase01> <beat_tick>' + final 'RAWSPEC ...'
  onset_v2_replay (FINAL only, K1_ONSET_V2)
      -> per-frame transient/kick/snare/hihat events

The two run flavours mirror exactly how baseline.json / final.json were produced
(beat_semantic_metrics.py: baseline = no defines; final = CONF_V2 + FLYWHEEL_V2).
ONSET_V2 per-band channels exist ONLY in the V2 onset binary, so they are filled
for the `final` run and left EMPTY for `baseline` (documented in SCHEMA.md).

chord_events are NOT exported per-track: the chord harness (chord_saliency_replay)
is a SYNTHETIC labelled-fixture A/B, not a per-music-track chord stream, and
re-deriving chroma->chord on the corpus would be DSP reimplementation (forbidden).
The notebook reads the synthetic harmonic-axis state from chord_v2_ab.json instead;
chord_events here is an empty list with a documented null reason.

Output: build/audio-semantic-metrics/trajectories/<track_id>__<run>.json  (+ SCHEMA.md)

Run:
  python3 scripts/regression-harness/export_diagnostic_trajectories.py            # full subset, both runs
  python3 scripts/regression-harness/export_diagnostic_trajectories.py --track 7vevOMWY6MY --run final
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import novelty_from_wav as nfw          # noqa: E402
import tempo_replay as trp              # noqa: E402
import tempo_accuracy as tac            # noqa: E402
import onset_v2_replay as ov2           # noqa: E402

ROOT = _HERE.parents[1]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
OUT_DIR = ROOT / "build" / "audio-semantic-metrics" / "trajectories"

AP_FRAME_HZ = nfw.SAMPLE_RATE / nfw.HOP          # 133.333 Hz
NOVELTY_RATE_HZ = AP_FRAME_HZ / 3.0              # k1_tempo internally /3-decimates the novelty
DEFAULT_GT = tac.DEFAULT_GT
DEFAULT_CORPUS = tac.DEFAULT_CORPUS

# run -> tempo defines (must match how baseline.json / final.json were produced)
RUN_TEMPO_DEFINES = {
    "baseline": [],
    "final": ["K1_TEMPO_CONF_V2", "K1_TEMPO_FLYWHEEL_V2"],
}
# onset per-band channels only come from the V2 onset binary; only the final run gets them
RUN_HAS_ONSET_CHANNELS = {"baseline": False, "final": True}

# ---------------------------------------------------------------------------
# CURATED REPRESENTATIVE SUBSET  (youtube_id -> why this track is in the set)
# Chosen from the 36 HarmonixSet corpus tracks by gold metadata (genre / BPM /
# time-signature) + the half-tempo-suspect flag used by beat_semantic_metrics.
# ---------------------------------------------------------------------------
CURATED_SUBSET = {
    # clean mid-tempo pop, textbook 4/4 backbeat — the "should-just-work" control
    "7vevOMWY6MY": "clean mid-tempo Pop 128 BPM 4/4 (0877 Whatchamacallit) — clean-control",
    # four-on-the-floor dance/electronic, steady kick grid — the easy lock case
    "T-sxSd1uwoU": "four-on-the-floor Dance/Electronic 130 BPM 4/4 (0423 I Wanna Go)",
    # syncopated hip-hop, off-grid accents — stresses onset/phase against syncopation
    "c7tOAGY59uQ": "syncopated Hip-Hop 84 BPM 4/4 (0003 6 Foot 7 Foot) — syncopation stress",
    # half-tempo-suspect + below representable range (gt 58 < 60) — octave/range edge
    "Qa1AqKxakRM": "half-tempo-suspect 0331 Pop 58 BPM (Against All Odds) — sub-range/octave edge",
    # half-tempo-suspect 0680 + compound 6/8 meter — half-tempo + non-4/4 stress
    "r9DBFTZTKPI": "half-tempo-suspect 0680 Pop 80 BPM 6/8 (Fix a Heart) — half-tempo + 6/8",
    # loud metal at 200 BPM (out of 60–155 range) — clamp-stress + super-octave
    "WxnN05vOuSM": "loud Metal 200 BPM 4/4 (0199 Number of the Beast) — clamp-stress / super-octave",
}


# --------------------------------------------------------------------------- GT join
def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, text=True,
                              capture_output=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def load_gt_beats(gt_dir, file_key):
    """Gold per-track beat times (seconds) from beats_and_downbeats/<file_key>.txt col0."""
    p = Path(gt_dir) / "beats_and_downbeats" / f"{file_key}.txt"
    if not p.exists():
        return []
    times = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if parts:
            try:
                times.append(float(parts[0]))
            except ValueError:
                pass
    return times


# --------------------------------------------------------------------------- parsers
def parse_tempo_trajectory(stdout):
    """Parse the 'T ...' lines + final 'RAWSPEC ...' from a tempo replay.

    Returns (frames_dict, tempogram_or_None). Columns (display-only, verbatim from
    the firmware): T <ms> <bpm> <conf> <locked> <phase01> <beat_tick>. The trailing
    V2-dump columns (if present under CONF_DUMP) are ignored here — they are not
    needed for the diagnostic surface. beat_tick_dedup collapses the known 133 Hz
    stale-republish (a tick that stays 1 across consecutive frames) to its leading
    edge — the harness's own documented dedup view (see tempo_replay fw_train).
    """
    t_ms, bpm, conf, locked, phase, tick_raw = [], [], [], [], [], []
    rawspec = None
    for ln in stdout.splitlines():
        if ln.startswith("T "):
            p = ln.split()
            if len(p) >= 7:
                t_ms.append(int(p[1]))
                bpm.append(float(p[2]))
                conf.append(float(p[3]))
                locked.append(int(p[4]))
                phase.append(float(p[5]))
                tick_raw.append(int(p[6]))
        elif ln.startswith("RAWSPEC"):
            vals = ln.split()[1:]
            try:
                rawspec = [float(v) for v in vals]
            except ValueError:
                rawspec = None
    # leading-edge dedup of the republished tick
    tick_dedup = []
    prev = 0
    for t in tick_raw:
        tick_dedup.append(1 if (t and not prev) else 0)
        prev = t
    frames = {
        "t_ms": t_ms,
        "bpm": bpm,
        "conf": conf,
        "locked": locked,
        "phase01": phase,
        "beat_tick_raw": tick_raw,
        "beat_tick_dedup": tick_dedup,
    }
    tempogram = None
    if rawspec is not None:
        # k1_tempo raw Goertzel spectrum: 96 bins, bin i == (60 + i) BPM (TEMPO_LOW=60,
        # 96 integer bins). This is the device's own tempo periodicity surface (the
        # "ACF/comb" heatmap the notebook shows) — taken verbatim, no recompute.
        bpm_axis = [60.0 + i for i in range(len(rawspec))]
        tempogram = {"bpm_axis": bpm_axis, "magnitude": rawspec,
                     "source": "k1_tempo RAWSPEC (final raw Goertzel-over-novelty spectrum, bin i = 60+i BPM)"}
    return frames, tempogram


def extract_novelty_aligned(frame_ms_nov, nov, t_ms_traj):
    """Map the front-end novelty (one value per AP frame, from novelty_from_wav) onto
    the trajectory's frame timeline. The trajectory is produced from the SAME novelty
    lines, so the frame count matches 1:1 in practice; we align defensively by index
    and pad/truncate to the trajectory length so the notebook can plot them together."""
    nov = list(map(float, nov))
    n = len(t_ms_traj)
    if len(nov) == n:
        return nov
    if len(nov) > n:
        return nov[:n]
    return nov + [0.0] * (n - len(nov))


# --------------------------------------------------------------------------- onset channels (final only)
def onset_channels_for(wav, frame_ms_nov):
    """Run the REAL k1_onset_beat.cpp V2 binary on the per-note spectrogram of this WAV
    and return {transient_ms, kick_ms, snare_ms, hihat_ms} event-time lists. Uses
    onset_v2_replay's own spectrogram synth + V2 build + run — NO reimplementation."""
    tmp = tempfile.TemporaryDirectory()
    try:
        binary = ov2.build_replay(["K1_ONSET_V2"], tmp.name)
        fm, spec, sil = ov2.wav_to_spectrogram(wav)
        events = ov2.run_replay(binary, fm, spec, sil)
    finally:
        tmp.cleanup()
    return {
        "transient_ms": [e["ms"] for e in events if e["transient"]],
        "kick_ms": [e["ms"] for e in events if e["kick"]],
        "snare_ms": [e["ms"] for e in events if e["snare"]],
        "hihat_ms": [e["ms"] for e in events if e["hihat"]],
    }


# --------------------------------------------------------------------------- one export
def export_one(track_id, run, wav, gt, binary, head, branch):
    """Build + write one trajectory JSON. `binary` is a pre-compiled tempo replay
    binary for `run` (compile once, reuse across tracks)."""
    frame_ms_nov, nov, sil = nfw.wav_to_novelty(wav)
    lines = [f"{int(m)} {v:.6f} {int(s)}" for m, v, s in zip(frame_ms_nov, nov, sil)]
    res = trp.replay_stdin(binary, "\n".join(lines) + "\n")
    frames, tempogram = parse_tempo_trajectory(res["stdout"])
    frames["novelty"] = extract_novelty_aligned(frame_ms_nov, nov, frames["t_ms"])

    onset_channels = {"transient_ms": [], "kick_ms": [], "snare_ms": [], "hihat_ms": []}
    onset_note = "baseline run: per-band onset channels are V2-only; left empty by design"
    if RUN_HAS_ONSET_CHANNELS[run]:
        onset_channels = onset_channels_for(wav, frame_ms_nov)
        onset_note = ("final run: from k1_onset_beat.cpp compiled with K1_ONSET_V2, "
                      "driven by onset_v2_replay per-note spectrogram (real firmware C++)")

    g = gt.get(track_id, {})
    harness_cmd = (
        "novelty_from_wav.wav_to_novelty -> tempo_replay.build_binary("
        f"defines={RUN_TEMPO_DEFINES[run]}).replay_stdin"
        + ("  ||  onset: onset_v2_replay.build_replay(['K1_ONSET_V2']).run_replay" if RUN_HAS_ONSET_CHANNELS[run] else "")
    )
    out = {
        "track_id": track_id,
        "run": run,
        "provenance": {
            "branch": branch,
            "head": head,
            "flags": RUN_TEMPO_DEFINES[run],
            "sample_rate_hz": nfw.SAMPLE_RATE,
            "hop": nfw.HOP,
            "ap_frame_hz": AP_FRAME_HZ,
            "novelty_rate_hz": NOVELTY_RATE_HZ,
            "corpus_path": str(wav),
            "gt_source": str(DEFAULT_GT),
            "harness_cmd": harness_cmd,
            "curated_reason": CURATED_SUBSET.get(track_id, "(ad-hoc track, not in curated subset)"),
        },
        "frames": frames,
        "onset_channels": onset_channels,
        "onset_channels_note": onset_note,
        "chord_events": [],
        "chord_events_note": (
            "null by design: the chord harness (chord_saliency_replay.py) is a SYNTHETIC "
            "labelled-fixture A/B, not a per-track chord stream over real music; deriving "
            "per-track chord events would be DSP reimplementation (forbidden). The notebook "
            "reads harmonic/chord state from build/audio-semantic-metrics/chord_v2_ab.json."
        ),
        "tempogram": tempogram,
        "gt": {
            "bpm": g.get("bpm"),
            "beat_times_s": load_gt_beats(DEFAULT_GT, g["file_key"]) if g.get("file_key") else [],
            "file_key": g.get("file_key"),
            "genre": g.get("genre"),
            "title": g.get("title"),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{track_id}__{run}.json"
    out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    n_tick = sum(frames["beat_tick_dedup"])
    return out_path, len(frames["t_ms"]), n_tick


# --------------------------------------------------------------------------- SCHEMA.md
SCHEMA_MD = """---
abstract: "Schema + provenance for build/audio-semantic-metrics/trajectories/<track_id>__<run>.json, the unified per-track diagnostic trajectories consumed by notebooks/audio_semantic_diagnostics.ipynb. DISPLAY-ONLY artifacts: every numeric field is produced verbatim by the UNMODIFIED firmware C++ replayed through the canonical host harness (tempo_replay / onset_v2_replay / novelty_from_wav) — NO DSP is reimplemented. Documents which harness command produces each field, the baseline-vs-final run flags, and why chord_events is empty. Read before consuming a trajectory JSON or changing export_diagnostic_trajectories.py."
---

# Diagnostic trajectory schema

`build/audio-semantic-metrics/trajectories/<track_id>__<run>.json`

Produced by `scripts/regression-harness/export_diagnostic_trajectories.py`. These are
DISPLAY artifacts: every numeric value is emitted verbatim by the compiled, UNMODIFIED
firmware (`k1_tempo.cpp`, `k1_onset_beat.cpp`) replayed through the existing host harness.
The exporter reimplements no tempo/beat/onset/saliency DSP.

## Runs

| `run` | tempo defines | onset channels | meaning |
|---|---|---|---|
| `baseline` | *(none)* | empty (V2-only) | incumbent k1_tempo (matches baseline.json) |
| `final` | `K1_TEMPO_CONF_V2`, `K1_TEMPO_FLYWHEEL_V2` | from `K1_ONSET_V2` | the graft confidence/lock/flywheel + V2 onset path (matches final.json) |

## Top-level fields

| field | producer |
|---|---|
| `track_id` | youtube_id (corpus WAV stem minus `_12k8`) |
| `run` | `baseline` \\| `final` |
| `provenance.branch` / `.head` | `git rev-parse` at export time |
| `provenance.flags` | tempo `-D` defines for this run |
| `provenance.sample_rate_hz` | 12800 (`novelty_from_wav.SAMPLE_RATE`) |
| `provenance.hop` | 96 (`SAMPLES_PER_CHUNK`) |
| `provenance.ap_frame_hz` | 12800/96 = 133.333 Hz |
| `provenance.novelty_rate_hz` | 133.333/3 = 44.44 Hz (k1_tempo's internal /3 decimation) |
| `provenance.corpus_path` | absolute WAV path |
| `provenance.gt_source` | HarmonixSet dataset dir |
| `provenance.harness_cmd` | the exact harness call chain |
| `provenance.curated_reason` | why this track is in the curated subset |

## `frames.*` — per-AP-frame arrays (all same length, index-aligned)

| field | producer / column |
|---|---|
| `t_ms` | `tempo_replay --replay-stdin` → `T <ms> ...` col 1 (ms, ~7.5 ms apart) |
| `novelty` | `novelty_from_wav.wav_to_novelty` (spectral-flux onset @ 133.33 Hz) — the front-end fed to k1_tempo, aligned 1:1 to the trajectory |
| `bpm` | `T` col 2 — k1_tempo detected BPM |
| `conf` | `T` col 3 — k1_tempo confidence (incumbent or CONF_V2 metric per run) |
| `locked` | `T` col 4 — k1_tempo lock state (0/1) |
| `beat_tick_raw` | `T` col 6 — raw emitted beat_tick (carries the known 133 Hz stale-republish) |
| `beat_tick_dedup` | DISPLAY-derived leading-edge collapse of `beat_tick_raw` (the harness's own dedup view, `tempo_replay.fw_train`); NOT a DSP change |
| `phase01` | `T` col 5 — k1_tempo beat-phase in [0,1] (carried for completeness) |

## `onset_channels.*` — event-time lists (ms), `final` run only

`transient_ms`, `kick_ms`, `snare_ms`, `hihat_ms`: frames where the V2
`k1_onset_beat.cpp` fired that channel, via `onset_v2_replay.build_replay(['K1_ONSET_V2'])`
on the per-note spectrogram of this WAV. Empty `[]` for the `baseline` run (these channels
do not exist without `K1_ONSET_V2`) — see `onset_channels_note`. Beat / downbeat are
k1_tempo-owned (see `frames.beat_tick_*`); downbeat is not available from any harness.

## `chord_events` — always `[]`

The chord harness (`chord_saliency_replay.py`) is a SYNTHETIC labelled-fixture A/B, not a
per-music-track chord stream; deriving per-track chord events from real audio would be DSP
reimplementation (forbidden). Harmonic/chord state for the notebook comes from
`build/audio-semantic-metrics/chord_v2_ab.json`. See `chord_events_note`.

## `tempogram` — `{bpm_axis[], magnitude[], source}` or `null`

From the `RAWSPEC` line of the tempo replay: k1_tempo's final raw Goertzel-over-novelty
spectrum, 96 bins, bin *i* = (60 + *i*) BPM. The device's own tempo-periodicity surface
(the notebook's "ACF/comb heatmap"), verbatim — not recomputed. `null` if the binary
emitted no RAWSPEC.

## `gt.*`

`bpm` (gold metadata BPM), `beat_times_s` (gold beat times, `beats_and_downbeats/<file_key>.txt`
col 0, seconds), `file_key`, `genre`, `title`. Ground truth is corpus-supplied, not invented.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| {DATE} | agent:claude-opus | Created — schema for the diagnostic trajectory exporter (audio forward-graft notebook package). |
"""


def write_schema():
    import datetime
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "SCHEMA.md").write_text(
        SCHEMA_MD.replace("{DATE}", datetime.date.today().isoformat()), encoding="utf-8")


# --------------------------------------------------------------------------- driver
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    ap.add_argument("--gt-dataset", default=str(DEFAULT_GT))
    ap.add_argument("--track", action="append", default=[],
                    help="youtube_id(s) to export; default = the curated subset")
    ap.add_argument("--run", action="append", default=[],
                    choices=["baseline", "final"],
                    help="run(s) to export; default = both")
    ap.add_argument("--compiler", default="clang++")
    args = ap.parse_args(argv)

    corpus = Path(args.corpus)
    if not corpus.is_dir():
        print(f"corpus not found: {corpus}", file=sys.stderr)
        return 2
    gt = tac.load_gt(args.gt_dataset)

    tracks = args.track or list(CURATED_SUBSET.keys())
    runs = args.run or ["baseline", "final"]
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    head = _git("rev-parse", "HEAD")

    # resolve each track_id -> wav
    wav_for = {}
    for tid in tracks:
        cands = list(corpus.glob(f"{tid}*.wav"))
        if cands:
            wav_for[tid] = cands[0]
        else:
            print(f"  WARN: no WAV for track {tid} in {corpus}", file=sys.stderr)

    write_schema()
    produced = []
    for run in runs:
        # compile the tempo binary once per run, reuse across all tracks
        tmp = tempfile.TemporaryDirectory()
        ok, binary, comp = trp.build_binary(tmp.name, args.compiler,
                                            defines=RUN_TEMPO_DEFINES[run])
        if not ok:
            print(f"COMPILE FAILED (run={run}):\n{comp['stderr']}", file=sys.stderr)
            tmp.cleanup()
            return 1
        for tid, wav in wav_for.items():
            try:
                path, nframes, nticks = export_one(tid, run, wav, gt, binary, head, branch)
                produced.append(str(path))
                print(f"  [{run:8}] {tid:12} -> {path.name}  frames={nframes} dedup_ticks={nticks}")
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR {tid} {run}: {e}", file=sys.stderr)
        tmp.cleanup()

    print(f"\nEXPORTED {len(produced)} trajectory file(s) -> {OUT_DIR}")
    print(f"  schema -> {OUT_DIR / 'SCHEMA.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
