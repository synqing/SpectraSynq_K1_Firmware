#!/usr/bin/env python3
"""Prepare and render the dual-edge Raw Motion explainer.

The capture and the output directory are explicit arguments. Nothing in the
scene hard-codes the emulator workspace.
"""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EMU = HERE.parents[1]
sys.path.insert(0, str(EMU))

import adapter  # noqa: E402

ENGINE_PIN = "2e96bc3e5b1a3d214578d32338a0c49f73c1311a"
SKILL_PIN = "30bd029e63b1e5173a97edff53400d224deaa16c"
DEFAULT_ENGINE = Path(
    "/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/raw-motion-toolchain/raw-motion"
)


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["/usr/bin/git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def _rms(samples: array.array, lo: int, hi: int) -> float:
    acc = 0
    n = hi - lo
    for i in range(lo, hi):
        s = samples[i]
        acc += s * s
    return (acc / n) ** 0.5


def prepare(run: Path, output: Path, case_id: str) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    doc, pcm, checks = adapter.scene_document(run, case_id)
    samples = array.array("h")
    samples.frombytes(pcm)
    zero_lo, zero_hi = 7 * adapter.RATE, 10 * adapter.RATE
    if any(samples[i] != 0 for i in range(zero_lo, zero_hi)):
        raise adapter.AdapterError("the declared 7–10 s section is not digital zero")
    checks["rms"] = {
        "music_0_7": round(_rms(samples, 0, zero_lo), 2),
        "zeros_7_10": _rms(samples, zero_lo, zero_hi),
        "return_10_16": round(_rms(samples, zero_hi, len(samples)), 2),
    }
    checks["boundaries"] = adapter.boundary_agreement(run, case_id, doc)
    if not all(row["agree"] for row in checks["boundaries"]):
        raise adapter.AdapterError(f"boundary rows disagree: {checks['boundaries']}")
    data_path = output / "scene-data.json"
    data_path.write_text(json.dumps(doc, separators=(",", ":")))
    (output / "reference.pcm").write_bytes(pcm)
    adapter.write_wav(pcm, output / "reference.wav")
    checks["scene_data_sha256"] = _sha_file(data_path)
    checks["reference_pcm_sha256"] = _sha_file(output / "reference.pcm")
    checks["reference_wav_sha256"] = _sha_file(output / "reference.wav")
    manifest = {
        "schema": "k1-dual-edge-replay-manifest/1",
        "case_id": case_id,
        "run_dir": str(run.resolve()),
        "output": str(output.resolve()),
        "duration_s": doc["duration_s"],
        "fps": doc["fps"],
        "sample_start": 0,
        "sample_end": doc["sample_end"],
        "audio_delta_s": 0,
        "pins": {"raw-motion": ENGINE_PIN, "raw-motion-skill": SKILL_PIN},
        "checks": checks,
        "capture_source": doc["capture_source"],
        "header_every_recorded": doc["header"]["every"],
        "capture_every": doc["capture"]["every"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def stage(output: Path, job: str) -> Path:
    src = HERE / "scene"
    dest = output / "jobs" / job
    if dest.exists():
        raise SystemExit(f"job already exists: {dest}")
    dest.mkdir(parents=True)
    for name in ("index.html", "comp.js", "annotations.json", "motion.js", "LICENSE-raw-motion.txt"):
        shutil.copy2(src / name, dest / name)
    shutil.copy2(output / "scene-data.json", dest / "scene-data.json")
    return dest


def render(engine: Path, project: Path, *, dur: int, stills: str | None, timeout: int) -> None:
    head = _git_head(engine)
    if head != ENGINE_PIN:
        raise SystemExit(f"engine {engine} is {head}, pin is {ENGINE_PIN}")
    cmd = [
        "node", str(engine / "engine" / "render.mjs"),
        "--project", str(project),
        "--w", "1920", "--h", "1080",
        "--fps", "60", "--dur", str(dur),
        "--sub", "1", "--shutter", "0", "--workers", "1",
    ]
    if stills:
        cmd.extend(["--stills", stills])
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, timeout=timeout)


def mux(frames: Path, wav: Path, mp4: Path) -> None:
    pngs = sorted(frames.glob("*.png"))
    if len(pngs) != 960:
        raise SystemExit(f"{frames} has {len(pngs)} pngs, expected 960")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", "60", "-start_number", "0", "-i", str(frames / "%05d.png"),
        "-i", str(wav),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-r", "60",
        "-c:a", "pcm_s16le",
        "-frames:v", "960",
        "-muxpreload", "0", "-muxdelay", "0",
        str(mp4),
    ]
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, timeout=180)
    probe = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,width,height,sample_rate,r_frame_rate,nb_frames,duration",
        "-show_entries", "format=duration",
        "-of", "json", str(mp4),
    ], text=True)
    (mp4.with_suffix(".ffprobe.json")).write_text(probe)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    prep = sub.add_parser("prepare")
    prep.add_argument("--run", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--case", default="startup-sqr")

    rnd = sub.add_parser("render")
    rnd.add_argument("--output", type=Path, required=True)
    rnd.add_argument("--job", required=True)
    rnd.add_argument("--engine", type=Path, default=DEFAULT_ENGINE)
    rnd.add_argument("--stills", default=None)
    rnd.add_argument("--timeout", type=int, default=1200)

    mx = sub.add_parser("mux")
    mx.add_argument("--frames", type=Path, required=True)
    mx.add_argument("--wav", type=Path, required=True)
    mx.add_argument("--mp4", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.cmd == "prepare":
        manifest = prepare(args.run, args.output, args.case)
        print(json.dumps({
            "output": str(args.output),
            "pcm_sha256": manifest["checks"]["pcm_sha256"],
            "frames": manifest["checks"]["frame_count"],
            "missing_hops": manifest["checks"]["missing_hops"],
            "boundaries": manifest["checks"]["boundaries"],
            "rms": manifest["checks"]["rms"],
        }, indent=2))
        return 0
    if args.cmd == "render":
        manifest = json.loads((args.output / "manifest.json").read_text())
        project = stage(args.output, args.job)
        render(
            args.engine, project, dur=int(manifest["duration_s"]),
            stills=args.stills, timeout=args.timeout,
        )
        return 0
    mux(args.frames, args.wav, args.mp4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
