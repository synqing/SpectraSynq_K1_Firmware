#!/usr/bin/env python3
"""Rebuild an im73d_audio_eval summary.json from a run directory's serial logs.

im73d_audio_eval writes summary.json only after every leg finishes, so a run that
is interrupted late still has all its per-leg .log files on disk but no summary --
and every downstream analysis consumes the summary. Re-running a bench capture to
recover data that was already collected costs device time and, when the stimulus is
played through a speaker, costs the operator peace and quiet. This tool reconstructs
the summary from the logs instead.

It deliberately imports the harness and reuses parse_ap_line / summarise_numeric /
assess_quality / assess_capture_integrity rather than reimplementing them. A second
implementation of the same parse would be free to disagree with the first, and the
recovered summary would silently stop meaning what a live summary means.

Legs are discovered from filenames written by run_capture:
    {label}_vol{volume:03d}_r{repeat}_{role}.log
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


HARNESS_PATH = Path(__file__).resolve().parent / "im73d_audio_eval.py"
LEG_RE = re.compile(r"^(?P<label>[a-z_]+)_vol(?P<volume>\d{3})_r(?P<repeat>\d+)_(?P<role>.+)\.log$")
# write_serial_log emits "<unix_ts> <line>"; the timestamp is not part of the payload.
LOG_LINE_RE = re.compile(r"^\d+\.\d+\s(?P<line>.*)$")


def load_harness():
    spec = importlib.util.spec_from_file_location("im73d_audio_eval", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def strip_timestamp(raw: str) -> str:
    match = LOG_LINE_RE.match(raw)
    return match.group("line") if match else raw


def discover_legs(run_dir: Path) -> dict[tuple[str, int, int], dict[str, Path]]:
    legs: dict[tuple[str, int, int], dict[str, Path]] = {}
    for path in sorted(run_dir.glob("*.log")):
        match = LEG_RE.match(path.name)
        if not match:
            continue  # preflight_*.log and runtime_ready_*.log are not legs
        key = (match.group("label"), int(match.group("volume")), int(match.group("repeat")))
        legs.setdefault(key, {})[match.group("role")] = path
    return legs


def rebuild(run_dir: Path, duration: float, label: str | None) -> dict[str, Any]:
    harness = load_harness()
    legs = discover_legs(run_dir)
    if not legs:
        raise SystemExit(f"no leg logs found in {run_dir}")

    min_rows = max(3, int(duration * 0.50))
    runs: list[dict[str, Any]] = []
    roles: set[str] = set()

    for (leg_label, volume, repeat), role_paths in sorted(legs.items()):
        run_report: dict[str, Any] = {
            "label": leg_label,
            "volume": volume,
            "repeat": repeat,
            "duration_sec": duration,
            "recovered_from_logs": True,
            "devices": {},
        }
        for role, path in sorted(role_paths.items()):
            roles.add(role)
            raw_lines = path.read_text(errors="replace").splitlines()
            lines = [strip_timestamp(line) for line in raw_lines]
            ap_rows = [row for row in (harness.parse_ap_line(l) for l in lines) if row is not None]
            summary = harness.summarise_numeric(ap_rows)
            run_report["devices"][role] = {
                "usb_serial": getattr(harness.DEVICE_BY_ROLE.get(role), "usb_serial", None),
                "error": None,
                "log": str(path),
                "total_lines": len(lines),
                "ap_rows": len(ap_rows),
                "summary": summary,
                "quality": harness.assess_quality(summary, min_rows),
                "capture": harness.assess_capture_integrity(None, len(ap_rows), min_rows),
            }
        runs.append(run_report)

    return {
        "created_at": run_dir.name,
        "label": label or run_dir.name,
        "recovered": True,
        "recovery_note": (
            "Rebuilt from per-leg serial logs by recover_eval_summary.py because the "
            "originating run was interrupted before it wrote summary.json. Leg contents "
            "are the bytes the devices actually emitted; only the run-level metadata "
            "(track, volumes, original_volume) is absent."
        ),
        "duration_sec": duration,
        "devices": {
            role: getattr(harness.DEVICE_BY_ROLE.get(role), "usb_serial", None) for role in sorted(roles)
        },
        "runs": runs,
    }


def run_self_test(tmp_root: Path) -> None:
    harness = load_harness()
    run_dir = tmp_root / "20260101T000000_selftest"
    run_dir.mkdir(parents=True, exist_ok=True)
    ap = (
        "[AP] SSL=253 DC=230 max_raw=4032 follower=12057 peak_scaled=0.454 "
        "silence=0 cal_source=persisted_profile cal_valid=1 | bpm=120.0 conf=0.96 lock=1 "
        "| onset=1 bass=0 ostr=0.00 "
        "| raw_i16_abs_peak=111 raw_i16_rms=39.0 raw_i16_near_pct=0.000 "
        "| k1_loud=1 input_trim=1.000 agc_gain=0.084 clip_pct=0.000 near_pct=0.000"
    )
    body = "\n".join(f"{1785932070.0 + i:.3f} {ap}" for i in range(20)) + "\n"
    (run_dir / "music_vol045_r1_bench_im69d.log").write_text(body)
    (run_dir / "music_vol045_r1_main_sph.log").write_text(body)
    (run_dir / "preflight_bench_im69d.log").write_text("noise\n")

    doc = rebuild(run_dir, duration=30.0, label="selftest")
    assert len(doc["runs"]) == 1, doc["runs"]
    device = doc["runs"][0]["devices"]["bench_im69d"]
    assert device["ap_rows"] == 20, device["ap_rows"]
    assert device["summary"]["raw_i16_rms"]["p90"] == 39.0
    assert device["quality"]["usable"] is True
    # preflight logs must never be mistaken for a capture leg
    assert set(doc["runs"][0]["devices"]) == {"bench_im69d", "main_sph"}

    # A timestamped line must parse identically to the raw AP line the device sent.
    assert harness.parse_ap_line(strip_timestamp(f"1785932070.916 {ap}")) == harness.parse_ap_line(ap)
    print("recover_eval_summary self-test: PASS")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--label")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            run_self_test(Path(tmp))
        return 0

    if args.run_dir is None:
        raise SystemExit("--run-dir is required unless --self-test is given")

    doc = rebuild(args.run_dir, args.duration, args.label)
    output = args.output or (args.run_dir / "summary.json")
    output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    legs = len(doc["runs"])
    print(f"recovered {legs} legs -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
