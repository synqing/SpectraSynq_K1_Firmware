#!/usr/bin/env python3
"""Capture harness-only VPAB rows tied to a labelled AV regression fixture."""

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


DEFAULT_OUT = ROOT / "build/audio-semantic-metrics/k1-vpab-visual-sync"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/cu.usbmodem1401")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--fixtures-json", default=str(manifest_mod.DEFAULT_FIXTURES))
    parser.add_argument("--fixture-id", required=True)
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--palette-mode", choices=("on", "off"), default="on")
    parser.add_argument("--duration-ms", type=int, default=20000)
    parser.add_argument("--every-n", type=int, default=150)
    parser.add_argument("--capture-mode", choices=("metrics", "bytes", "both"), default="both")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--label", default="k1_vpab_visual_sync")
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
    return [f"# cmd=:{command}", *read_lines(ser, wait_s)]


def dump_vpab(ser: Any, read_s: float = 12.0) -> list[str]:
    ser.write(b":vpab=dump\n")
    ser.flush()
    lines: list[str] = ["# cmd=:vpab=dump"]
    deadline = time.time() + read_s
    while time.time() < deadline:
        new_lines = read_lines(ser, 0.25)
        lines.extend(new_lines)
        if any("VPAB_DUMP:" in line for line in new_lines):
            break
    return lines


def find_fixture(manifest: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    for fixture in manifest.get("fixtures", []):
        if fixture.get("id") == fixture_id:
            return fixture
    raise SystemExit(f"fixture not found: {fixture_id}")


def build_playback_command(fixture: dict[str, Any], manifest: dict[str, Any], duration_ms: int) -> list[str]:
    start_ms, _manifest_duration = manifest_mod.resolve_playback_window(fixture)
    gain_db, _gain_meta = manifest_mod.resolve_playback_gain_db(
        {**fixture, "duration_ms": duration_ms},
        manifest,
    )
    return manifest_mod.build_ffplay_command(
        fixture["resolved_path"],
        start_ms=start_ms,
        duration_ms=duration_ms,
        gain_db=gain_db,
        playback_settings=manifest_mod.playback_settings(manifest),
    )


def parse_kv_row(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for token in line.split(","):
        if "=" not in token:
            fields.setdefault("kind", token)
            continue
        key, value = token.split("=", 1)
        fields[key] = value
    return fields


def summarize(lines: list[str]) -> dict[str, Any]:
    vpab = [line for line in lines if line.startswith("VPAB,")]
    vpabb = [line for line in lines if line.startswith("VPABB,")]
    vpabc = [line for line in lines if line.startswith("VPABC,")]
    rows = [parse_kv_row(line) for line in vpab]
    byte_rows = [parse_kv_row(line) for line in vpabb]
    channels = sorted({row.get("channel", "") for row in rows + byte_rows if row.get("channel")})
    modes = sorted({row.get("mode", "") for row in rows + byte_rows if row.get("mode")})
    max_white_bias = max((float(row.get("white_bias_score", "0") or 0) for row in rows), default=0.0)
    max_render_us = max((int(row.get("render_us", "0") or 0) for row in rows + byte_rows), default=0)
    max_frame_us = max((int(row.get("frame_us", "0") or 0) for row in rows + byte_rows), default=0)
    max_show_us = max((int(row.get("show_us", "0") or 0) for row in rows + byte_rows), default=0)
    dropped = max((int(row.get("dropped", "0") or 0) for row in rows + byte_rows), default=0)
    return {
        "vpab_rows": len(vpab),
        "vpabb_rows": len(vpabb),
        "vpabc_rows": len(vpabc),
        "channels": channels,
        "modes": modes,
        "max_white_bias_score": max_white_bias,
        "max_render_us_wall_envelope": max_render_us,
        "max_frame_us": max_frame_us,
        "max_show_us": max_show_us,
        "max_dropped": dropped,
        "context": parse_kv_row(vpabc[-1]) if vpabc else None,
    }


def main() -> int:
    import serial

    args = parse_args()
    manifest = manifest_mod.load_manifest(Path(args.fixtures_json).expanduser())
    fixture = find_fixture(manifest, args.fixture_id)
    available, reason = manifest_mod.fixture_availability(fixture)
    if not available:
        raise SystemExit(f"fixture unavailable: {args.fixture_id}: {reason}")

    stamp = now_stamp()
    out_dir = Path(args.out_dir).expanduser() / f"{args.label}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{args.label}_{stamp}__{args.fixture_id}__vpab.log"
    summary_path = out_dir / f"{args.label}_{stamp}__{args.fixture_id}__summary.json"

    playback_cmd = build_playback_command(fixture, manifest, args.duration_ms)
    lines = [
        f"# label={args.label}",
        f"# fixture_id={args.fixture_id}",
        f"# mode={args.mode}",
        f"# palette_mode={args.palette_mode}",
        f"# duration_ms={args.duration_ms}",
        f"# every_n={args.every_n}",
        f"# capture_mode={args.capture_mode}",
        f"# git_head={git_head()}",
        f"# serial_identity={json.dumps(serial_identity(args.port), sort_keys=True)}",
        f"# ffplay_cmd={' '.join(playback_cmd)}",
    ]

    with serial.Serial(args.port, args.baud, timeout=0.05, write_timeout=1.0) as ser:
        ser.dtr = False
        ser.rts = False
        for command in (
            "stop",
            "vpab=reset",
            f"set_mode={args.mode}",
            f"palette_mode={args.palette_mode}",
            f"vpab=start,{args.every_n},{args.capture_mode}",
        ):
            lines.extend(send_command(ser, command))
        playback = subprocess.Popen(playback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + (args.duration_ms / 1000.0) + 5.0
        while playback.poll() is None and time.time() < deadline:
            lines.extend(read_lines(ser, 0.25))
        playback.wait(timeout=max(5, args.duration_ms / 1000.0 + 5))
        lines.extend(send_command(ser, "vpab=stop", wait_s=0.75))
        lines.extend(dump_vpab(ser))
        lines.extend(send_command(ser, "vpab=status", wait_s=0.75))

    raw_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "label": args.label,
        "timestamp": stamp,
        "fixture_id": args.fixture_id,
        "mode": args.mode,
        "palette_mode": args.palette_mode,
        "duration_ms": args.duration_ms,
        "every_n": args.every_n,
        "capture_mode": args.capture_mode,
        "port": args.port,
        "serial_identity": serial_identity(args.port),
        "git_head": git_head(),
        "raw_log": str(raw_path),
        "summary": summarize(lines),
        "render_budget_semantics": {
            "render_us": "VPAB wall-envelope/max-accumulator diagnostic; not effect-code causality proof",
            "quant_us": "final-byte quantization/LED byte conversion timing",
            "frame_us": "visual frame envelope diagnostic",
            "show_us": "FastLED.show/RMT output diagnostic",
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary_json": str(summary_path), "raw_log": str(raw_path), **summary["summary"]}, indent=2))
    return 0 if summary["summary"]["vpab_rows"] or summary["summary"]["vpabb_rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
