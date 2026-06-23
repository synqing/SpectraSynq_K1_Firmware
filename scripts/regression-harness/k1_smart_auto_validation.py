#!/usr/bin/env python3
"""Validate Smart Auto mode-selection behavior on labelled AV fixtures."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))

import k1_av_manifest as manifest_mod  # noqa: E402
from k1_audio_visual_regression import git_head, serial_identity  # noqa: E402


DEFAULT_OUT = ROOT / "build/audio-semantic-metrics/k1-smart-auto-validation"
DISABLED_MODES = {0, 1, 2, 4, 5, 6, 10, 17, 24, 25}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/cu.usbmodem1401")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--fixtures-json", default=str(manifest_mod.DEFAULT_FIXTURES))
    parser.add_argument(
        "--fixture-ids",
        default="acestep_kick_drop_heavy,acestep_steady_groove,acestep_sparse_breakdown_build,dense_clipped_edm",
    )
    parser.add_argument("--duration-ms", type=int, default=25000)
    parser.add_argument("--poll-s", type=float, default=5.0)
    parser.add_argument("--label", default="k1_smart_auto_validation")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    return parser.parse_args()


def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def read_lines(ser: Any, seconds: float) -> list[str]:
    deadline = time.time() + seconds
    lines: list[str] = []
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            time.sleep(0.01)
            continue
        text = carry + chunk.decode("utf-8", errors="replace")
        parts = text.splitlines()
        if text.endswith(("\n", "\r")):
            carry = ""
        elif parts:
            carry = parts.pop()
        else:
            carry = text
        lines.extend(line.strip() for line in parts if line.strip())
    if carry.strip():
        lines.append(carry.strip())
    return lines


def send_command(ser: Any, command: str, wait_s: float = 0.5) -> list[str]:
    ser.reset_input_buffer()
    ser.write((f":{command}\n").encode("utf-8"))
    ser.flush()
    return read_lines(ser, wait_s)


def parse_smart_status(lines: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in lines:
        if not line.startswith("SMART_"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        try:
            if "." in value:
                out[key] = float(value)
            else:
                out[key] = int(value)
        except ValueError:
            out[key] = value
    return out


def fixture_by_id(manifest: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    for fixture in manifest.get("fixtures", []):
        if fixture.get("id") == fixture_id:
            return fixture
    raise SystemExit(f"fixture not found: {fixture_id}")


def playback_command(fixture: dict[str, Any], manifest: dict[str, Any], duration_ms: int) -> list[str]:
    start_ms, _ = manifest_mod.resolve_playback_window(fixture)
    gain_db, _gain_meta = manifest_mod.resolve_playback_gain_db({**fixture, "duration_ms": duration_ms}, manifest)
    return manifest_mod.build_ffplay_command(
        fixture["resolved_path"],
        start_ms=start_ms,
        duration_ms=duration_ms,
        gain_db=gain_db,
        playback_settings=manifest_mod.playback_settings(manifest),
    )


def run_fixture(ser: Any, fixture: dict[str, Any], manifest: dict[str, Any], duration_ms: int, poll_s: float) -> dict[str, Any]:
    cmd = playback_command(fixture, manifest, duration_ms)
    raw_lines: list[str] = [f"# fixture_id={fixture['id']}", f"# ffplay_cmd={' '.join(cmd)}"]
    raw_lines.extend(send_command(ser, "smart_status", wait_s=0.75))
    playback = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start = time.time()
    polls: list[dict[str, Any]] = []
    next_poll = start
    while playback.poll() is None:
        now = time.time()
        if now >= next_poll:
            lines = send_command(ser, "smart_status", wait_s=0.75)
            raw_lines.extend(lines)
            status = parse_smart_status(lines)
            status["elapsed_s"] = round(now - start, 2)
            polls.append(status)
            next_poll = now + poll_s
        time.sleep(0.05)
    playback.wait(timeout=max(5, duration_ms / 1000.0 + 5))
    final_lines = send_command(ser, "smart_status", wait_s=0.75)
    raw_lines.extend(final_lines)
    final = parse_smart_status(final_lines)
    modes = []
    requested = []
    for row in polls + [final]:
        if "SMART_APPLIED_MODE" in row:
            modes.append(int(row["SMART_APPLIED_MODE"]))
        if "SMART_INTENT_MODE" in row:
            requested.append(int(row["SMART_INTENT_MODE"]))
    disabled_seen = sorted((set(modes) | set(requested)) & DISABLED_MODES)
    return {
        "id": fixture["id"],
        "source_clip_id": fixture.get("source_clip_id"),
        "purpose": fixture.get("purpose"),
        "duration_ms": duration_ms,
        "polls": polls,
        "final_status": final,
        "applied_modes": modes,
        "requested_modes": requested,
        "disabled_modes_seen": disabled_seen,
        "status": "PASS" if not disabled_seen else "FAIL_disabled_mode_selected",
        "raw_lines": raw_lines,
    }


def main() -> int:
    import serial

    args = parse_args()
    manifest = manifest_mod.load_manifest(Path(args.fixtures_json).expanduser())
    fixtures = [fixture_by_id(manifest, item.strip()) for item in args.fixture_ids.split(",") if item.strip()]
    for fixture in fixtures:
        available, reason = manifest_mod.fixture_availability(fixture)
        if not available:
            raise SystemExit(f"fixture unavailable: {fixture['id']}: {reason}")

    stamp = now_stamp()
    out_dir = Path(args.out_dir).expanduser() / f"{args.label}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{args.label}_{stamp}__raw.log"
    summary_path = out_dir / f"{args.label}_{stamp}__summary.json"

    all_raw: list[str] = []
    results: list[dict[str, Any]] = []
    with serial.Serial(args.port, args.baud, timeout=0.05, write_timeout=1.0) as ser:
        ser.dtr = False
        ser.rts = False
        all_raw.extend(send_command(ser, "stop", wait_s=0.5))
        all_raw.extend(send_command(ser, "smart_scene=auto", wait_s=1.0))
        for fixture in fixtures:
            result = run_fixture(ser, fixture, manifest, args.duration_ms, args.poll_s)
            all_raw.extend(result.pop("raw_lines"))
            results.append(result)
            all_raw.extend(send_command(ser, "stop", wait_s=0.5))
        all_raw.extend(send_command(ser, "smart_scene=off", wait_s=1.0))

    raw_path.write_text("\n".join(all_raw) + "\n", encoding="utf-8")
    disabled_seen = sorted({mode for item in results for mode in item["disabled_modes_seen"]})
    summary = {
        "label": args.label,
        "timestamp": stamp,
        "port": args.port,
        "serial_identity": serial_identity(args.port),
        "git_head": git_head(),
        "raw_log": str(raw_path),
        "duration_ms": args.duration_ms,
        "fixture_ids": [fixture["id"] for fixture in fixtures],
        "disabled_modes_seen": disabled_seen,
        "verdict": "PASS" if not disabled_seen else "FAIL",
        "results": results,
        "note": "Smart Auto product validation only; AP/tempo proof remains in AV regression matrix.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary_json": str(summary_path), "raw_log": str(raw_path), "verdict": summary["verdict"]}, indent=2))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
