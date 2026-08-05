#!/usr/bin/env python3
"""Device STM telemetry soak: serial poll during approved playback."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import serial
except ImportError:
    print("pip install pyserial", file=sys.stderr)
    raise

STM_RE = re.compile(
    r"STM_TELEM: ready=(\d+) temporal=([0-9.]+) spectral=([0-9.]+) "
    r"spec_max=([0-9.]+) spec_mean=([0-9.]+)"
)

@dataclass
class StmSample:
    t_wall: float
    ready: int
    temporal: float
    spectral: float
    spec_max: float
    spec_mean: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--port", default="/dev/cu.usbmodem112401")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument(
        "--wav",
        type=Path,
        default=Path(
            "/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/"
            "firmware-v3/tools/mic_ab_scorer/stimuli/cal_tone_1khz.wav"
        ),
    )
    p.add_argument("--soak-seconds", type=float, default=60.0)
    p.add_argument("--pre-silence-s", type=float, default=8.0)
    p.add_argument("--post-silence-s", type=float, default=8.0)
    p.add_argument("--poll-interval-s", type=float, default=0.5)
    p.add_argument("--edge-strength", type=float, default=0.75)
    p.add_argument("--out-dir", type=Path, required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.wav.is_file():
        print(f"missing wav: {args.wav}", file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = args.out_dir / f"device_stm_telem_soak_{ts}.log"
    json_path = args.out_dir / f"device_stm_telem_soak_{ts}.json"

    lines: list[str] = []
    samples: list[StmSample] = []
    t0 = time.monotonic()

    ser = serial.Serial(args.port, args.baud, timeout=0.25)
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            try:
                raw = ser.readline()
            except Exception:
                break
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").rstrip()
            lines.append(line)
            m = STM_RE.search(line)
            if m:
                samples.append(
                    StmSample(
                        t_wall=time.monotonic() - t0,
                        ready=int(m.group(1)),
                        temporal=float(m.group(2)),
                        spectral=float(m.group(3)),
                        spec_max=float(m.group(4)),
                        spec_mean=float(m.group(5)),
                    )
                )

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    time.sleep(2.5)

    def cmd(c: str) -> None:
        lines.append(f">>> {c}")
        ser.write((c + "\n").encode())
        ser.flush()
        time.sleep(0.3)

    cmd(":edge_enabled=on")
    cmd(":edge_mode=stm_dual")
    cmd(f":edge_strength={args.edge_strength:.2f}")
    cmd(":stm_telem=reset")

    lines.append(f"[SOAK] pre_silence_s={args.pre_silence_s}")
    pre_end = time.monotonic() + args.pre_silence_s
    while time.monotonic() < pre_end:
        cmd(":stm_telem=report")
        time.sleep(max(0.0, args.poll_interval_s - 0.3))

    audio_budget = max(
        5.0,
        args.soak_seconds - args.pre_silence_s - args.post_silence_s,
    )
    lines.append(
        f"[PLAYBACK START] file={args.wav} tool=afplay "
        f"budget_s={audio_budget:.1f} loop_until_budget"
    )
    af_proc: subprocess.Popen | None = None
    playback_start = time.monotonic()
    while time.monotonic() - playback_start < audio_budget:
        if af_proc is None or af_proc.poll() is not None:
            af_proc = subprocess.Popen(["afplay", str(args.wav)])
        cmd(":stm_telem=report")
        time.sleep(max(0.0, args.poll_interval_s - 0.3))
    if af_proc and af_proc.poll() is None:
        af_proc.terminate()
        try:
            af_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            af_proc.kill()
    lines.append("[PLAYBACK END]")

    lines.append(f"[SOAK] post_silence_s={args.post_silence_s}")
    post_end = time.monotonic() + args.post_silence_s
    while time.monotonic() < post_end:
        cmd(":stm_telem=report")
        time.sleep(max(0.0, args.poll_interval_s - 0.3))

    cmd(":stm_telem=report")
    time.sleep(0.5)
    stop.set()
    th.join(timeout=2)
    ser.close()

    wall_s = time.monotonic() - t0
    ready = [s for s in samples if s.ready == 1]
    bad = [l for l in lines if "Bad command" in l or "sberr" in l]

    def stats(vals: list[float]) -> dict:
        if not vals:
            return {"n": 0}
        return {
            "n": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": statistics.fmean(vals),
            "p50": statistics.median(vals),
        }

    summary = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "device_port": args.port,
        "wav": str(args.wav),
        "edge_mode": "stm_dual",
        "edge_strength": args.edge_strength,
        "wall_seconds": round(wall_s, 2),
        "stm_samples_total": len(samples),
        "stm_samples_ready": len(ready),
        "ready_fraction": round(len(ready) / len(samples), 4) if samples else 0.0,
        "bad_command_lines": len(bad),
        "temporal_energy": stats([s.temporal for s in ready]),
        "spectral_energy": stats([s.spectral for s in ready]),
        "spec_max": stats([s.spec_max for s in ready]),
        "verdict": "PASS"
        if samples
        and len(ready) >= max(10, int(0.5 * len(samples)))
        and not bad
        and stats([s.temporal for s in ready]).get("max", 0) > 0.05
        else "FAIL",
        "log_path": str(log_path),
    }

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "device_stm_telem_soak_latest.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "device_stm_telem_soak_latest.log").write_text(
        log_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
