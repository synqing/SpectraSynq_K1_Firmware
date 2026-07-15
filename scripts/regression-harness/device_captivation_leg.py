#!/usr/bin/env python3
"""Run one identity-gated K1 captivation eyes-on leg and restore the prior mode."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import serial


CRASH_RE = re.compile(
    r"Guru Meditation|Backtrace:|watchdog|abort\(\) was called|assert failed|panic(?:'ed|:)",
    re.IGNORECASE,
)
MODE_NAMES = {32: "WAVEFORM HYBRID K1", 35: "SHOCKWAVE", 36: "IRIS"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_for(ser: serial.Serial, seconds: float, log: list[str]) -> list[str]:
    deadline = time.time() + seconds
    lines: list[str] = []
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace").rstrip()
        lines.append(line)
        log.append(f"[{time.time():.3f}] {line}")
    return lines


def send(ser: serial.Serial, body: str, settle: float, log: list[str]) -> list[str]:
    log.append(f"[{time.time():.3f}] >>> :{body}")
    ser.write((f":{body}\n").encode("ascii"))
    ser.flush()
    return read_for(ser, settle, log)


def extract_mode(lines: list[str]) -> int | None:
    for line in lines:
        match = re.fullmatch(r"MODE:\s*(\d+)", line.strip())
        if match:
            return int(match.group(1))
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--expected-chip-id", required=True)
    parser.add_argument("--expected-build-env", required=True)
    parser.add_argument("--expected-git", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--expected-track-sha256", required=True)
    parser.add_argument("--mode", type=int, choices=sorted(MODE_NAMES), required=True)
    parser.add_argument("--duration-s", type=float, default=30.0)
    parser.add_argument("--countdown-s", type=float, default=5.0)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    track = Path(args.track).resolve()
    out_dir = Path(args.out_dir).resolve()
    sys.path.insert(0, str(repo / "scripts/platformio"))
    from k1_session_target import validate_session_pin

    pin_ok, pin_message = validate_session_pin(args.expected_build_env, args.port)
    if not pin_ok:
        raise RuntimeError(pin_message)
    observed_track_sha = sha256(track)
    if observed_track_sha != args.expected_track_sha256:
        raise RuntimeError(
            f"track SHA256 mismatch: expected {args.expected_track_sha256}, observed {observed_track_sha}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    stem = f"mode_{args.mode}_{stamp}"
    raw_path = out_dir / f"{stem}.log"
    summary_path = out_dir / f"{stem}.json"
    log = [
        f"# session_pin={pin_message}",
        f"# track={track}",
        f"# track_sha256={observed_track_sha}",
        f"# mode={args.mode} expected_name={MODE_NAMES[args.mode]}",
    ]
    initial_mode: int | None = None
    restored_mode: int | None = None
    observed_mode: int | None = None
    build_line = ""
    chip_id = ""
    mode_name = ""
    playback_returncode: int | None = None
    failure: str | None = None
    ser: serial.Serial | None = None
    player: subprocess.Popen[bytes] | None = None
    try:
        ser = serial.Serial(args.port, 115200, timeout=0.05, write_timeout=1.0, dsrdtr=False, rtscts=False)
        ser.dtr = True
        ser.rts = True
        read_for(ser, 5.0, log)
        send(ser, "get_mode", 0.8, log)  # warm-up after CDC reset
        build_lines = send(ser, "build", 1.2, log)
        build_line = next((line for line in build_lines if line.startswith("BUILD:")), "")
        if f"git={args.expected_git}" not in build_line or f"env={args.expected_build_env}" not in build_line:
            raise RuntimeError(f"runtime BUILD mismatch: {build_line or 'missing'}")
        chip_lines = send(ser, "chip_id", 1.2, log)
        chip_id = next((line.strip() for line in chip_lines if re.fullmatch(r"[0-9A-Fa-f]{8}", line.strip())), "").upper()
        if chip_id != args.expected_chip_id.upper():
            raise RuntimeError(f"runtime chip mismatch: expected {args.expected_chip_id}, observed {chip_id or 'missing'}")
        initial_mode = extract_mode(send(ser, "get_mode", 1.2, log))
        if initial_mode is None:
            raise RuntimeError("initial mode readback missing")
        send(ser, f"set_mode={args.mode}", 1.0, log)
        time.sleep(1.5)
        observed_mode = extract_mode(send(ser, "get_mode", 1.2, log))
        if observed_mode != args.mode:
            raise RuntimeError(f"mode readback mismatch: expected {args.mode}, observed {observed_mode}")
        name_lines = send(ser, f"get_mode_name={args.mode}", 1.2, log)
        mode_name = next((line.split(":", 1)[1].strip() for line in name_lines if line.startswith("MODE_NAME:")), "")
        if mode_name != MODE_NAMES[args.mode]:
            raise RuntimeError(f"mode-name mismatch: expected {MODE_NAMES[args.mode]}, observed {mode_name or 'missing'}")

        print(
            f"EYES_ON_ARMED mode={args.mode} name={mode_name} playback_in_s={args.countdown_s:g}",
            flush=True,
        )
        time.sleep(args.countdown_s)
        log.append(f"[{time.time():.3f}] EYES_ON_START mode={args.mode} name={mode_name}")
        print(f"EYES_ON_START mode={args.mode} name={mode_name}", flush=True)
        player = subprocess.Popen(
            ["/usr/bin/afplay", "-v", "1.0", str(track)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        read_for(ser, args.duration_s, log)
        if player.poll() is None:
            player.terminate()
            try:
                player.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                player.kill()
                player.wait(timeout=2.0)
        playback_returncode = player.returncode
        player = None
        post_mode = extract_mode(send(ser, "get_mode", 1.2, log))
        if post_mode != args.mode:
            raise RuntimeError(f"post-playback mode changed: expected {args.mode}, observed {post_mode}")
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        if player is not None and player.poll() is None:
            player.terminate()
            player.wait(timeout=2.0)
        if ser is not None:
            if initial_mode is not None:
                try:
                    send(ser, f"set_mode={initial_mode}", 1.0, log)
                    time.sleep(2.0)
                    restored_mode = extract_mode(send(ser, "get_mode", 1.2, log))
                    if restored_mode != initial_mode and failure is None:
                        failure = f"RuntimeError: restore mismatch: expected {initial_mode}, observed {restored_mode}"
                except Exception as exc:
                    if failure is None:
                        failure = f"{type(exc).__name__}: restore failed: {exc}"
            ser.close()

    crash_lines = [line for line in log if CRASH_RE.search(line)]
    if crash_lines and failure is None:
        failure = f"RuntimeError: {len(crash_lines)} crash signatures observed"
    verdict = "PASS" if failure is None else "FAIL"
    rerun = (
        f"python3 scripts/regression-harness/device_captivation_leg.py --repo {repo} --port {args.port} "
        f"--expected-chip-id {args.expected_chip_id} --expected-build-env {args.expected_build_env} "
        f"--expected-git {args.expected_git} --track {track} "
        f"--expected-track-sha256 {args.expected_track_sha256} --mode {args.mode} "
        f"--duration-s {args.duration_s:g} --countdown-s {args.countdown_s:g} --out-dir {out_dir}"
    )
    summary = {
        "verdict": verdict,
        "failure": failure,
        "mode": args.mode,
        "mode_name": mode_name,
        "initial_mode": initial_mode,
        "observed_mode": observed_mode,
        "restored_mode": restored_mode,
        "build_line": build_line,
        "chip_id": chip_id,
        "track": str(track),
        "track_sha256": observed_track_sha,
        "duration_s": args.duration_s,
        "playback_returncode": playback_returncode,
        "crash_signature_count": len(crash_lines),
        "raw_log": str(raw_path),
        "rerun_command": rerun,
    }
    raw_path.write_text("\n".join(log) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
