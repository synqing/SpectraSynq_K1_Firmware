#!/usr/bin/env python3
"""Capture, replay, and score a ground-truthed device-novelty corpus.

The runner is intentionally narrow: it accepts only the corrected IM73D bench
probe, requires a passing corpus preflight, preserves every exact child command,
and checkpoints the scoring manifest after each track so an interrupted physical
run can resume without repeating valid 120-second captures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = Path(__file__).resolve().parent
CORRECT_ENV = "k1_bench_ap_frontend_probe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--preflight-report", type=Path, required=True)
    parser.add_argument("--port", required=True, help="Explicit capture port; auto-detection is forbidden")
    parser.add_argument("--expected-chip-id", required=True)
    parser.add_argument("--expected-build-env", required=True)
    parser.add_argument("--duration-ms", type=int, default=120000)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--score-manifest", type=Path, required=True)
    parser.add_argument("--commands-out", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--baseline-csv", type=Path, default=ROOT / "docs/measurements/tempo-octave-baseline.tracks.csv")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def display_command(argv: list[str]) -> str:
    rendered = ["python3" if index == 0 and value == sys.executable else value for index, value in enumerate(argv)]
    return shlex.join(rendered)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    print(f"+ {display_command(argv)}", flush=True)
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        lines.append(line)
        print(line, end="", flush=True)
    return_code = process.wait()
    stdout = "".join(lines)
    if return_code:
        raise subprocess.CalledProcessError(return_code, argv, output=stdout)
    return subprocess.CompletedProcess(argv, return_code, stdout, "")


def parse_written_path(stdout: str, key: str) -> Path:
    marker = f"wrote {key}="
    matches = [line[len(marker) :] for line in stdout.splitlines() if line.startswith(marker)]
    if len(matches) != 1:
        raise RuntimeError(f"capture did not report exactly one {key} path")
    return Path(matches[0])


def capture_command(args: argparse.Namespace, track: dict[str, object]) -> list[str]:
    return [
        sys.executable,
        str(HARNESS / "device_novelty_buffer_capture.py"),
        "--track",
        str(Path(str(track["track_file"])).expanduser()),
        "--port",
        args.port,
        "--expected-chip-id",
        args.expected_chip_id,
        "--expected-build-env",
        args.expected_build_env,
        "--duration-ms",
        str(args.duration_ms),
        "--capture-apcad-soak",
        "--out-dir",
        str(args.out_dir),
        "--label",
        str(track["id"]),
    ]


def replay_command(track: dict[str, object], capture: dict[str, object]) -> list[str]:
    return [
        sys.executable,
        str(HARNESS / "device_novelty_replay.py"),
        str(capture["nov_dump_log"]),
        "--expected-bpm",
        str(float(track["gt_bpm"])),
        "--out",
        str(capture["replay_summary"]),
        "--trajectory-out",
        str(capture["trajectory"]),
        "--stdin-out",
        str(capture["replay_input"]),
    ]


def capture_is_reusable(summary: Path, args: argparse.Namespace, track: dict[str, object]) -> bool:
    try:
        capture = json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return all(
        (
            capture.get("validation", {}).get("verdict") == "PASS",
            capture.get("track_sha256") == track.get("track_sha256"),
            capture.get("expected_chip_id") == args.expected_chip_id,
            capture.get("expected_build_env") == args.expected_build_env,
            capture.get("port") == args.port,
            int(capture.get("duration_ms_requested", 0)) == args.duration_ms,
        )
    )


def reusable_capture(args: argparse.Namespace, track: dict[str, object]) -> Path | None:
    candidates = sorted(args.out_dir.glob(f"{track['id']}_nov_buffered_*__summary.json"), reverse=True)
    return next((path for path in candidates if capture_is_reusable(path, args, track)), None)


def write_checkpoints(
    args: argparse.Namespace,
    source_manifest: dict[str, object],
    rows: list[dict[str, object]],
    commands: list[dict[str, str]],
) -> None:
    args.score_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.commands_out.parent.mkdir(parents=True, exist_ok=True)
    score_manifest = {
        "corpus_id": source_manifest.get("corpus_id"),
        "source_manifest": str(args.manifest.resolve()),
        "preflight_report": str(args.preflight_report.resolve()),
        "tracks": rows,
    }
    args.score_manifest.write_text(json.dumps(score_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command_report = {
        "verdict": "IN_PROGRESS",
        "entry_command": display_command([sys.executable, *sys.argv]),
        "commands": commands,
    }
    args.commands_out.write_text(json.dumps(command_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_inputs(args: argparse.Namespace, manifest: dict[str, object], preflight: dict[str, object]) -> None:
    if args.expected_build_env != CORRECT_ENV:
        raise RuntimeError(f"expected-build-env must be {CORRECT_ENV}, got {args.expected_build_env}")
    if args.duration_ms != 120000:
        raise RuntimeError("gate corpus duration-ms must be exactly 120000")
    if preflight.get("verdict") != "PASS":
        raise RuntimeError("corpus preflight verdict is not PASS")
    if Path(str(preflight.get("manifest", ""))).resolve() != args.manifest.resolve():
        raise RuntimeError("preflight report does not name this source manifest")
    if preflight.get("manifest_sha256") != sha256(args.manifest):
        raise RuntimeError("preflight report is stale: source manifest SHA-256 changed")
    if not manifest.get("tracks"):
        raise RuntimeError("source manifest has no tracks")
    preflight_rows = {str(row.get("id")): row for row in preflight.get("tracks", [])}
    for track in manifest["tracks"]:
        path = Path(str(track["track_file"])).expanduser()
        row = preflight_rows.get(str(track["id"]))
        if row is None or row.get("verdict") != "PASS":
            raise RuntimeError(f"{track['id']}: no matching PASS preflight row")
        if not path.is_file() or sha256(path) != track.get("track_sha256"):
            raise RuntimeError(f"{track['id']}: local track SHA-256 changed after preflight")
        if row.get("track_sha256") != track.get("track_sha256"):
            raise RuntimeError(f"{track['id']}: preflight track SHA-256 does not match manifest")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight_report.read_text(encoding="utf-8"))
    validate_inputs(args, manifest, preflight)

    rows: list[dict[str, object]] = []
    commands: list[dict[str, str]] = []
    write_checkpoints(args, manifest, rows, commands)
    for track in manifest["tracks"]:
        summary_path = reusable_capture(args, track) if args.resume else None
        if summary_path is None:
            capture_argv = capture_command(args, track)
            commands.append({"track": str(track["id"]), "stage": "capture", "command": display_command(capture_argv)})
            write_checkpoints(args, manifest, rows, commands)
            result = run_command(capture_argv)
            summary_path = parse_written_path(result.stdout, "summary")
        else:
            commands.append({"track": str(track["id"]), "stage": "capture", "command": "REUSED PASS capture: " + str(summary_path)})

        capture = json.loads(summary_path.read_text(encoding="utf-8"))
        if not capture_is_reusable(summary_path, args, track):
            raise RuntimeError(f"capture failed reuse validation after execution: {summary_path}")
        replay_argv = replay_command(track, capture)
        commands.append({"track": str(track["id"]), "stage": "replay", "command": display_command(replay_argv)})
        write_checkpoints(args, manifest, rows, commands)
        run_command(replay_argv)
        rows.append(
            {
                "id": track["id"],
                "title": track["title"],
                "genre": track["genre"],
                "gt_bpm": track["gt_bpm"],
                "gt_source": track["gt_source"],
                "track_sha256": track["track_sha256"],
                "capture_summary": str(summary_path),
                "replay_trajectory": str(capture["trajectory"]),
            }
        )
        write_checkpoints(args, manifest, rows, commands)

    score_argv = [
        sys.executable,
        str(HARNESS / "device_novelty_corpus_score.py"),
        str(args.score_manifest),
        "--baseline-csv",
        str(args.baseline_csv),
        "--commands-json",
        str(args.commands_out),
        "--out-json",
        str(args.out_json),
        "--out-md",
        str(args.out_md),
    ]
    commands.append({"track": "ALL", "stage": "score", "command": display_command(score_argv)})
    write_checkpoints(args, manifest, rows, commands)
    run_command(score_argv)
    command_report = json.loads(args.commands_out.read_text(encoding="utf-8"))
    command_report["verdict"] = "COMPLETE"
    args.commands_out.write_text(json.dumps(command_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
