#!/usr/bin/env python3
"""Hear exactly what a tempo-lane test fed the emulated firmware (lane R1).

The emulator never plays sound: tempo_lane_emu.py decodes each clip and copies the samples straight into the
firmware's microphone buffer (im69d_samples_i16, in place of the I2S read), so runs are silent, parallel and
bit-exact. This tool rebuilds the SAME samples with the same code (tempo_lane_emu.case_pcm: ffmpeg to mono
12.8 kHz, one gain to peak 4096) and plays them, so what you hear is what the firmware heard. It checks the
sha256 of the rebuilt PCM against the run's cases.json when you pass --run.

  tempo_audition.py clip --manifest M --id gz:blues_00002 [--run RUN_DIR] [--seconds 10] [--no-play]
  tempo_audition.py suite --suite p15|neg|consumer|music --id music-a [--run RUN_DIR] [--seconds 10] [--no-play]
  tempo_audition.py list --manifest M | --suite NAME
WAV files go to _scratch/esp-emulator/tempo-lock-r1/audition/. Playback uses macOS afplay.
Exit: 0 played or written, 1 the rebuilt PCM does not match the run's recorded sha256, 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import tempo_lane_emu as tle  # noqa: E402

OUT = ROOT / "_scratch/esp-emulator/tempo-lock-r1/audition"


def cases_for(a) -> list[dict]:
    if getattr(a, "suite", None):
        return tle.suite(a.suite)
    return tle.manifest_cases(Path(a.manifest), "all", None)


def recorded_sha(run_dir: Path, cid: str) -> str | None:
    doc = json.loads((run_dir / "cases.json").read_text())
    return next((c.get("pcm_sha256") for c in doc["cases"] if c["id"] == cid), None)


def build(case: dict) -> tuple[bytes, dict]:
    with tempfile.TemporaryDirectory() as td:
        return tle.case_pcm(case, Path(td))


def cmd_play(a) -> int:
    case = next((c for c in cases_for(a) if c["id"] == a.id), None)
    if case is None:
        print(f"no case {a.id!r}; try the list command", file=sys.stderr)
        return 2
    pcm, meta = build(case)
    sha = hashlib.sha256(pcm).hexdigest()
    status = 0
    if getattr(a, "run", None):
        want = recorded_sha(Path(a.run), a.id)
        if want is None:
            print(f"{a.run}/cases.json has no pcm_sha256 for {a.id}", file=sys.stderr)
            return 2
        status = 0 if want == sha else 1
        print(f"pcm sha256 {sha} {'MATCHES' if status == 0 else 'DIFFERS FROM'} the run's recorded {want}")
    OUT.mkdir(parents=True, exist_ok=True)
    wav = OUT / (a.id.replace(":", "_") + ".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(tle.RATE); w.writeframes(pcm)
    secs = len(pcm) / 2 / tle.RATE
    gold = case.get("gold_bpm") or case.get("expected_bpm")
    print(f"{a.id}: {secs:.1f} s at {tle.RATE} Hz, gold {gold} BPM, {meta.get('source', meta.get('argv', ''))}")
    print(f"wrote {wav}")
    if not a.no_play:
        if shutil.which("afplay") is None:
            print("afplay not found; open the WAV instead", file=sys.stderr)
            return 2
        cmd = ["afplay", str(wav)] + (["-t", str(a.seconds)] if a.seconds else [])
        subprocess.run(cmd, check=False)
    return status


def cmd_list(a) -> int:
    for c in cases_for(a):
        print(c["id"], c.get("gold_bpm") or c.get("expected_bpm") or "", c["source"].get("path", c["source"].get("kind")))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("clip", "suite"):
        s = sub.add_parser(name)
        if name == "clip":
            s.add_argument("--manifest", required=True)
        else:
            s.add_argument("--suite", required=True)
        s.add_argument("--run", help="run directory with cases.json, to check the PCM hash")
        s.add_argument("--id", required=True)
        s.add_argument("--seconds", type=float, default=0.0, help="play only the first N seconds")
        s.add_argument("--no-play", action="store_true")
    ls = sub.add_parser("list")
    g = ls.add_mutually_exclusive_group(required=True)
    g.add_argument("--manifest")
    g.add_argument("--suite")
    a = p.parse_args(argv)
    return cmd_list(a) if a.cmd == "list" else cmd_play(a)


if __name__ == "__main__":
    sys.exit(main())
