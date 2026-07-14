#!/usr/bin/env python3
"""Pair clean spectral-flux and production-reference IM73D novelty replays.

The tool is offline-only. It verifies the immutable source corpus and existing
buffered device captures, compiles one k1_tempo binary, replays both novelty
sources through that binary, and emits bounded H2/H4/H5 evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

import device_novelty_corpus_score as corpus_score
import device_novelty_replay as device_replay
import novelty_from_wav as clean_novelty
import tempo_replay


ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_REFERENCE_ENV = "k1_bench_ap_frontend_probe"
PRODUCTION_REFERENCE_CHIP = "B489A500"
PRODUCTION_REFERENCE_FLAG = "-DK1_MIC_IM73D_PDM_V1"
AP_FRAME_HZ = 12800.0 / 96.0
DECIMATION = 3
DURATION_MS = 120000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("--device-manifest", type=Path, required=True)
    parser.add_argument("--preflight-report", type=Path, required=True)
    parser.add_argument("--duration-ms", type=int, default=DURATION_MS)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--commands-out", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def display_command(argv: list[str]) -> str:
    rendered = ["python3" if index == 0 and value == sys.executable else value for index, value in enumerate(argv)]
    return shlex.join(rendered)


def git_value(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def platformio_sections() -> dict[str, str]:
    text = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    matches = list(re.finditer(r"^\[(?P<name>[^\]]+)\]\s*$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("name")] = text[match.end() : end]
    return sections


def resolved_platformio_env(env: str) -> str:
    sections = platformio_sections()

    def visit(name: str, seen: set[str]) -> str:
        if name in seen:
            raise RuntimeError(f"cyclic PlatformIO inheritance at {name}")
        body = sections.get(name)
        if body is None:
            raise RuntimeError(f"PlatformIO environment missing: {name}")
        match = re.search(r"(?m)^\s*extends\s*=\s*(?P<parent>[^\s;]+)", body)
        if not match:
            return body
        parent = match.group("parent")
        return visit(parent, {*seen, name}) + "\n" + body

    return visit(f"env:{env}", set())


def score_stdout(stdout: str, gt_bpm: float) -> dict[str, object]:
    ms, bpm, conf, lock = corpus_score.accuracy.parse_trajectory(stdout)
    detected, settled_median, locked_fraction, final_confidence = corpus_score.accuracy.detected_bpm(
        ms, bpm, conf, lock
    )
    if detected is None:
        raise RuntimeError("trajectory has no scoreable rows")
    cutoff = ms.min() + (ms.max() - ms.min()) * 0.5
    settled = ms >= cutoff
    exact_near = np.abs(bpm - gt_bpm) / gt_bpm <= corpus_score.accuracy.TOL
    metrical_near = np.zeros_like(exact_near, dtype=bool)
    for multiple in corpus_score.accuracy.OCTAVES:
        target = multiple * gt_bpm
        metrical_near |= np.abs(bpm - target) / target <= corpus_score.accuracy.TOL
    locked_mask = lock.astype(bool)
    locked_acc1_fraction = float(np.mean(locked_mask[settled] & exact_near[settled]))
    locked_acc2_fraction = float(np.mean(locked_mask[settled] & metrical_near[settled]))
    acc1, acc2, best_k, best_error = corpus_score.accuracy.octave_eval(detected, gt_bpm)
    return {
        "det_bpm": detected,
        "settled_median": settled_median,
        "locked_frac": locked_fraction,
        "locked_acc1_frac": locked_acc1_fraction,
        "locked_acc2_frac": locked_acc2_fraction,
        "locked_wrong_lane_frac": float(locked_fraction) - locked_acc2_fraction,
        "final_conf": final_confidence,
        "acc1": acc1,
        "acc2": acc2,
        "octave": corpus_score.accuracy.octave_label(best_k, best_error),
        "rel_err": best_error,
        "in_range": corpus_score.accuracy.BPM_LO <= gt_bpm <= corpus_score.accuracy.BPM_HI,
        "bucket": corpus_score.accuracy.bucket(gt_bpm),
        "n_frames": int(ms.size),
        "first_ms": int(ms.min()),
        "last_ms": int(ms.max()),
    }


def correctness_verdict(clean: dict[str, object], device: dict[str, object]) -> str:
    clean_acc1 = float(clean["acc1"])
    clean_acc2 = float(clean["acc2"])
    device_acc1 = float(device["acc1"])
    device_acc2 = float(device["acc2"])
    delta1 = clean_acc1 - device_acc1
    delta2 = clean_acc2 - device_acc2
    if delta1 > 0.0 and delta2 >= 0.0:
        return "SUPPORTED"
    if delta1 == 0.0 and delta2 > 0.0:
        return "SUPPORTED"
    if delta1 * delta2 < 0.0:
        return "MIXED"
    return "NOT_SUPPORTED"


def lock_verdict(differences: list[float]) -> str:
    if not differences:
        return "NOT_VERIFIED"
    positive = sum(value > 0.0 for value in differences)
    non_positive = len(differences) - positive
    median = float(np.median(np.asarray(differences, dtype=float)))
    if positive >= 4 and median > 0.0:
        return "SUPPORTED"
    if non_positive >= 4 and median <= 0.0:
        return "NOT_SUPPORTED"
    return "MIXED"


def add_lock_quality(aggregate: dict[str, object], rows: list[dict[str, object]], arm: str) -> None:
    scopes: dict[str, list[dict[str, object]]] = {
        "all": rows,
        "in_range": [row for row in rows if bool(row[arm]["in_range"])],
    }
    for name, selected in scopes.items():
        aggregate[name]["locked_acc1_fraction"] = float(
            np.mean([float(row[arm]["locked_acc1_frac"]) for row in selected])
        )
        aggregate[name]["locked_acc2_fraction"] = float(
            np.mean([float(row[arm]["locked_acc2_frac"]) for row in selected])
        )
        aggregate[name]["locked_wrong_lane_fraction"] = float(
            np.mean([float(row[arm]["locked_wrong_lane_frac"]) for row in selected])
        )
    for bucket, bucket_aggregate in aggregate["buckets"].items():
        selected = [row for row in rows if row[arm]["bucket"] == bucket]
        for metric in ("locked_acc1_frac", "locked_acc2_frac", "locked_wrong_lane_frac"):
            key = metric.replace("_frac", "_fraction")
            bucket_aggregate[key] = (
                float(np.mean([float(row[arm][metric]) for row in selected])) if selected else None
            )


def capture_timing(summary: dict[str, object]) -> dict[str, object]:
    soak = summary.get("apcad_soak")
    if not isinstance(soak, dict):
        raise RuntimeError("capture has no AP cadence soak")
    compact = soak.get("compact_soak")
    if not isinstance(compact, dict):
        raise RuntimeError("capture has no compact AP cadence summary")
    worst = soak.get("compact_soak_worst") or []
    return {
        "classification": soak.get("classification"),
        "classification_reason": soak.get("classification_reason"),
        "active_p95_us": int(compact["active_p95_us"]),
        "active_max_us": int(compact["active_max_us"]),
        "active_over_7500": int(compact["active_over_7500"]),
        "total_max_us": max((int(row.get("total_us", 0)) for row in worst), default=0),
        "frame_gap": int(compact["frame_gap"]),
        "i2s_not_ok": int(compact["i2s_not_ok"]),
        "timestamp_regression": int(compact["timestamp_regression"]),
        "measured_ap_hz": float(compact["meas_ap_hz"]),
        "measured_novelty_hz": float(compact["meas_nov_hz"]),
    }


def aggregate_h4(rows: list[dict[str, object]]) -> dict[str, object]:
    clean_integrity = all(
        int(row[key]) == 0
        for row in rows
        for key in ("frame_gap", "i2s_not_ok", "timestamp_regression")
    )
    p95_below_budget = all(int(row["active_p95_us"]) < 7500 for row in rows)
    return {
        "verdict": "PROXY_PASS" if clean_integrity and p95_below_budget else "PROXY_FAIL",
        "method_boundary": "IM73D production-reference path with non-shippable capture instrumentation",
        "tracks": len(rows),
        "worst_active_p95_us": max(int(row["active_p95_us"]) for row in rows),
        "worst_active_max_us": max(int(row["active_max_us"]) for row in rows),
        "active_over_7500_total": sum(int(row["active_over_7500"]) for row in rows),
        "worst_total_max_us": max(int(row["total_max_us"]) for row in rows),
        "frame_gap_total": sum(int(row["frame_gap"]) for row in rows),
        "i2s_fault_total": sum(int(row["i2s_not_ok"]) for row in rows),
        "timestamp_regression_total": sum(int(row["timestamp_regression"]) for row in rows),
        "ap_hz_range": [min(float(row["measured_ap_hz"]) for row in rows), max(float(row["measured_ap_hz"]) for row in rows)],
        "novelty_hz_range": [min(float(row["measured_novelty_hz"]) for row in rows), max(float(row["measured_novelty_hz"]) for row in rows)],
        "capture_classifications": sorted({str(row["classification"]) for row in rows}),
    }


def percent(value: object) -> str:
    return "N/A" if value is None else f"{float(value) * 100.0:.1f}%"


def validate_manifests(
    args: argparse.Namespace,
    source: dict[str, object],
    device: dict[str, object],
    preflight: dict[str, object],
) -> None:
    if args.duration_ms != DURATION_MS:
        raise RuntimeError(f"duration-ms must be exactly {DURATION_MS}")
    if preflight.get("verdict") != "PASS":
        raise RuntimeError("corpus preflight is not PASS")
    if resolve_path(str(preflight.get("manifest", ""))).resolve() != args.source_manifest.resolve():
        raise RuntimeError("preflight report names a different source manifest")
    if preflight.get("manifest_sha256") != sha256(args.source_manifest):
        raise RuntimeError("corpus preflight is stale")
    if source.get("corpus_id") != device.get("corpus_id"):
        raise RuntimeError("source and device manifests have different corpus IDs")
    if len(source.get("tracks", [])) != 6 or len(device.get("tracks", [])) != 6:
        raise RuntimeError("paired production-reference gate requires exactly six tracks")


def main() -> int:
    args = parse_args()
    for field in (
        "source_manifest",
        "device_manifest",
        "preflight_report",
        "out_dir",
        "commands_out",
        "out_json",
        "out_md",
    ):
        setattr(args, field, resolve_path(getattr(args, field)))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.commands_out.parent.mkdir(parents=True, exist_ok=True)

    source = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    device = json.loads(args.device_manifest.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight_report.read_text(encoding="utf-8"))
    validate_manifests(args, source, device, preflight)
    device_by_id = {str(row["id"]): row for row in device["tracks"]}
    preflight_by_id = {str(row["id"]): row for row in preflight["tracks"]}

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")

    defines = list(device_replay.DEFAULT_DEFINES)
    defines.extend(
        [
            f"K1_TEMPO_AP_FRAME_HZ={device_replay.c_float_literal(AP_FRAME_HZ)}",
            f"K1_TEMPO_NOVELTY_DECIMATION={DECIMATION}U",
        ]
    )
    entry_command = display_command([sys.executable, *sys.argv])
    commands: list[dict[str, str]] = []
    paired_rows: list[dict[str, object]] = []
    h4_rows: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="k1-paired-novelty-") as temporary:
        temp = Path(temporary)
        ok, binary, compile_result = tempo_replay.build_binary(temp / "build", defines=defines)
        if not ok:
            raise RuntimeError("tempo replay compile failed: " + compile_result.get("stderr", ""))
        binary_path = Path(binary)
        binary_hash = sha256(binary_path)

        for track in source["tracks"]:
            track_id = str(track["id"])
            track_path = resolve_path(str(track["track_file"]))
            if not track_path.is_file() or sha256(track_path) != track["track_sha256"]:
                raise RuntimeError(f"{track_id}: source track hash mismatch")
            preflight_row = preflight_by_id.get(track_id)
            if not preflight_row or preflight_row.get("verdict") != "PASS":
                raise RuntimeError(f"{track_id}: no matching PASS preflight row")
            device_row = device_by_id.get(track_id)
            if not device_row:
                raise RuntimeError(f"{track_id}: missing device manifest row")
            summary_path = resolve_path(str(device_row["capture_summary"]))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            capture_checks = (
                summary.get("validation", {}).get("verdict") == "PASS",
                summary.get("track_sha256") == track["track_sha256"],
                summary.get("expected_chip_id") == PRODUCTION_REFERENCE_CHIP,
                summary.get("expected_build_env") == PRODUCTION_REFERENCE_ENV,
                int(summary.get("duration_ms_requested", 0)) == args.duration_ms,
            )
            if not all(capture_checks):
                raise RuntimeError(f"{track_id}: capture identity or integrity mismatch")

            clean_wav = temp / f"{track_id}.wav"
            ffmpeg_command = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-t",
                f"{args.duration_ms / 1000.0:.3f}",
                "-i",
                str(track_path),
                "-ac",
                "1",
                "-ar",
                str(clean_novelty.SAMPLE_RATE),
                str(clean_wav),
            ]
            subprocess.run(ffmpeg_command, check=True)
            commands.append({"track": track_id, "stage": "clean_decode", "command": shlex.join(ffmpeg_command)})
            frame_ms, novelty, silence = clean_novelty.wav_to_novelty(clean_wav)
            clean_stdin = "\n".join(
                f"{int(ms)} {value:.6f} {int(silent)}"
                for ms, value, silent in zip(frame_ms, novelty, silence)
            ) + "\n"

            nov_dump = resolve_path(str(summary["nov_dump_log"]))
            nov_rows, warnings, parse_meta = device_replay.parse_nov_rows(nov_dump)
            audit = device_replay.audit_nov_rows(nov_rows)
            audit.update(parse_meta)
            if warnings or audit["emit_gap_count"] or audit["timestamp_regression_count"]:
                raise RuntimeError(f"{track_id}: device NOV audit failed")
            device_stdin = device_replay.rows_to_ap_frame_stdin(
                nov_rows, ap_frame_hz=AP_FRAME_HZ, decimation=DECIMATION
            )

            clean_run = tempo_replay.replay_stdin(str(binary_path), clean_stdin)
            device_run = tempo_replay.replay_stdin(str(binary_path), device_stdin)
            if not clean_run["ok"] or not device_run["ok"]:
                raise RuntimeError(f"{track_id}: shared-binary replay failed")

            clean_trajectory = args.out_dir / f"{track_id}__clean_trajectory.log"
            device_trajectory = args.out_dir / f"{track_id}__device_trajectory.log"
            clean_input = args.out_dir / f"{track_id}__clean_replay_input.txt"
            device_input = args.out_dir / f"{track_id}__device_replay_input.txt"
            clean_trajectory.write_text(clean_run["stdout"], encoding="utf-8")
            device_trajectory.write_text(device_run["stdout"], encoding="utf-8")
            clean_input.write_text(clean_stdin, encoding="utf-8")
            device_input.write_text(device_stdin, encoding="utf-8")

            gt_bpm = float(track["gt_bpm"])
            clean_score = score_stdout(clean_run["stdout"], gt_bpm)
            device_score = score_stdout(device_run["stdout"], gt_bpm)
            timing = capture_timing(summary)
            h4_rows.append({"id": track_id, **timing})
            paired_rows.append(
                {
                    "id": track_id,
                    "title": track["title"],
                    "genre": track["genre"],
                    "gt_bpm": gt_bpm,
                    "gt_source": track["gt_source"],
                    "track_sha256": track["track_sha256"],
                    "capture_summary": str(summary_path.relative_to(ROOT)),
                    "nov_dump": str(nov_dump.relative_to(ROOT)),
                    "clean_trajectory": str(clean_trajectory.relative_to(ROOT)),
                    "device_trajectory": str(device_trajectory.relative_to(ROOT)),
                    "clean": clean_score,
                    "device": device_score,
                    "lock_delta_clean_minus_device": float(clean_score["locked_frac"]) - float(device_score["locked_frac"]),
                    "accuracy_transition": (
                        f"{'PASS' if clean_score['acc1'] else 'FAIL'}->"
                        f"{'PASS' if device_score['acc1'] else 'FAIL'}"
                    ),
                    "device_nov_audit": audit,
                    "h4": timing,
                    "decoded_wav_sha256": sha256(clean_wav),
                }
            )

    clean_aggregate = corpus_score.aggregate_set(
        [{**row["clean"], "locked_frac": row["clean"]["locked_frac"]} for row in paired_rows]
    )
    device_aggregate = corpus_score.aggregate_set(
        [{**row["device"], "locked_frac": row["device"]["locked_frac"]} for row in paired_rows]
    )
    add_lock_quality(clean_aggregate, paired_rows, "clean")
    add_lock_quality(device_aggregate, paired_rows, "device")
    lock_differences = [float(row["lock_delta_clean_minus_device"]) for row in paired_rows]
    acc1_lock_differences = [
        float(row["clean"]["locked_acc1_frac"]) - float(row["device"]["locked_acc1_frac"])
        for row in paired_rows
    ]
    acc2_lock_differences = [
        float(row["clean"]["locked_acc2_frac"]) - float(row["device"]["locked_acc2_frac"])
        for row in paired_rows
    ]
    h2 = {
        "correctness": {
            "verdict": correctness_verdict(clean_aggregate["all"], device_aggregate["all"]),
            "acc1_delta_clean_minus_device": float(clean_aggregate["all"]["acc1"]) - float(device_aggregate["all"]["acc1"]),
            "acc2_delta_clean_minus_device": float(clean_aggregate["all"]["acc2"]) - float(device_aggregate["all"]["acc2"]),
        },
        "lock_occupancy": {
            "verdict": lock_verdict(lock_differences),
            "mean_delta_clean_minus_device": float(np.mean(lock_differences)),
            "median_delta_clean_minus_device": float(np.median(lock_differences)),
            "clean_higher_tracks": sum(value > 0.0 for value in lock_differences),
            "device_equal_or_higher_tracks": sum(value <= 0.0 for value in lock_differences),
        },
        "acc1_correct_lock_occupancy": {
            "verdict": lock_verdict(acc1_lock_differences),
            "mean_delta_clean_minus_device": float(np.mean(acc1_lock_differences)),
            "median_delta_clean_minus_device": float(np.median(acc1_lock_differences)),
            "clean_higher_tracks": sum(value > 0.0 for value in acc1_lock_differences),
            "device_equal_or_higher_tracks": sum(value <= 0.0 for value in acc1_lock_differences),
        },
        "acc2_correct_lock_occupancy": {
            "verdict": lock_verdict(acc2_lock_differences),
            "mean_delta_clean_minus_device": float(np.mean(acc2_lock_differences)),
            "median_delta_clean_minus_device": float(np.median(acc2_lock_differences)),
            "clean_higher_tracks": sum(value > 0.0 for value in acc2_lock_differences),
            "device_equal_or_higher_tracks": sum(value <= 0.0 for value in acc2_lock_differences),
        },
        "attribution_boundary": "combined playback, room, microphone, GDFT, AGC, clamp, and novelty path; not AGC alone",
    }
    resolved_env = resolved_platformio_env(PRODUCTION_REFERENCE_ENV)
    h5 = {
        "verdict": "VERIFIED" if PRODUCTION_REFERENCE_FLAG in resolved_env else "CONTRADICTORY",
        "authority": "Captain decision 2026-07-15: IM73D is the K1 reference and production microphone",
        "environment": PRODUCTION_REFERENCE_ENV,
        "chip_id": PRODUCTION_REFERENCE_CHIP,
        "required_flag": PRODUCTION_REFERENCE_FLAG,
        "flag_present_in_resolved_environment": PRODUCTION_REFERENCE_FLAG in resolved_env,
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "tempo_decimation": 3,
    }
    h4 = aggregate_h4(h4_rows)

    tracked_sources = [
        ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp",
        ROOT / "scripts/regression-harness/novelty_from_wav.py",
        ROOT / "scripts/regression-harness/device_novelty_replay.py",
        ROOT / "scripts/regression-harness/tempo_accuracy.py",
        Path(__file__),
    ]
    result = {
        "verdict": "MEASURED",
        "corpus_id": source["corpus_id"],
        "hardware_authority": "IM73D production/reference, Captain decision 2026-07-15",
        "metric_contract": {
            "settled_window": "final 50% relative to each trajectory start timestamp",
            "acc1": "relative error <=4% at exact GT tempo",
            "acc2": "relative error <=4% at GT multiples 1/3, 1/2, 1, 2, 3",
            "octave_error": "Acc2 minus Acc1",
        },
        "git_head": git_value("rev-parse", "HEAD"),
        "git_dirty": bool(git_value("status", "--porcelain")),
        "source_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in tracked_sources},
        "detector_defines": defines,
        "detector_binary_sha256": binary_hash,
        "source_manifest": str(args.source_manifest),
        "source_manifest_sha256": sha256(args.source_manifest),
        "device_manifest": str(args.device_manifest),
        "device_manifest_sha256": sha256(args.device_manifest),
        "preflight_report": str(args.preflight_report),
        "clean": clean_aggregate,
        "device": device_aggregate,
        "h2": h2,
        "h4": h4,
        "h5": h5,
        "tracks": paired_rows,
        "rerun_command": entry_command,
        "limitations": [
            "existing captures do not record arming-to-afplay latency, so the arms share source start and nominal duration but are not sample-synchronous",
            "six EDM tracks do not establish performance on human-phrased 120-140 BPM music",
            "AGC-specific causality is not isolated",
            "H4 uses a non-shippable capture probe and is proxy evidence",
        ],
    }

    command_ledger = {
        "verdict": "COMPLETE",
        "entry_command": entry_command,
        "detector_binary_sha256": binary_hash,
        "commands": commands,
    }
    args.commands_out.write_text(json.dumps(command_ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    clean_all = clean_aggregate["all"]
    device_all = device_aggregate["all"]
    lines = [
        "# Paired Clean vs IM73D Device Novelty",
        "",
        "[FACT] IM73D is the K1 production/reference microphone by Captain decision on 2026-07-15.",
        "",
        "[FACT] Both novelty arms below use the same six SHA-pinned tracks, Beatport GT, detector binary, defines, and corrected relative final-half scoring window.",
        "",
        f"[FACT] H2 correctness verdict: **{h2['correctness']['verdict']}**.",
        "",
        f"[FACT] H2 lock-occupancy verdict: **{h2['lock_occupancy']['verdict']}**.",
        "",
        f"[FACT] H2 Acc1-correct lock-occupancy verdict: **{h2['acc1_correct_lock_occupancy']['verdict']}**.",
        "",
        f"[FACT] H2 Acc2-correct lock-occupancy verdict: **{h2['acc2_correct_lock_occupancy']['verdict']}**.",
        "",
        "[INFERENCE] Any difference belongs to the combined device input chain; this experiment does not isolate AGC.",
        "",
        "## Paired Headline",
        "",
        "| Scope | n | Clean Acc1 | Device Acc1 | Delta | Clean Acc2 | Device Acc2 | Delta | Clean locked | Device locked | Clean Acc1-correct lock | Device Acc1-correct lock | Clean Acc2-correct lock | Device Acc2-correct lock |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| **120-140 BPM** | {clean_all['n']} | {percent(clean_all['acc1'])} | {percent(device_all['acc1'])} | "
            f"{(float(clean_all['acc1']) - float(device_all['acc1'])) * 100:+.1f} pp | "
            f"{percent(clean_all['acc2'])} | {percent(device_all['acc2'])} | "
            f"{(float(clean_all['acc2']) - float(device_all['acc2'])) * 100:+.1f} pp | "
            f"{percent(clean_all['locked_fraction'])} | {percent(device_all['locked_fraction'])} | "
            f"{percent(clean_all['locked_acc1_fraction'])} | {percent(device_all['locked_acc1_fraction'])} | "
            f"{percent(clean_all['locked_acc2_fraction'])} | {percent(device_all['locked_acc2_fraction'])} |"
        ),
        "",
        "## Tracks",
        "",
        "| Track | GT | Clean BPM | Device BPM | Clean Acc1 | Device Acc1 | Clean locked | Device locked | Clean Acc1-correct lock | Device Acc1-correct lock | Clean Acc2-correct lock | Device Acc2-correct lock |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in paired_rows:
        lines.append(
            f"| {row['title']} | {row['gt_bpm']:.1f} | {row['clean']['det_bpm']:.1f} | {row['device']['det_bpm']:.1f} | "
            f"{'PASS' if row['clean']['acc1'] else 'FAIL'} | {'PASS' if row['device']['acc1'] else 'FAIL'} | "
            f"{percent(row['clean']['locked_frac'])} | {percent(row['device']['locked_frac'])} | "
            f"{percent(row['clean']['locked_acc1_frac'])} | {percent(row['device']['locked_acc1_frac'])} | "
            f"{percent(row['clean']['locked_acc2_frac'])} | {percent(row['device']['locked_acc2_frac'])} |"
        )
    lines.extend(
        [
            "",
            "## H4 Timing Proxy",
            "",
            f"[FACT] Verdict: **{h4['verdict']}**. Worst active p95 **{h4['worst_active_p95_us'] / 1000.0:.3f} ms**; "
            f"worst active maximum **{h4['worst_active_max_us'] / 1000.0:.3f} ms**; "
            f"over-budget frames **{h4['active_over_7500_total']}**; frame gaps **{h4['frame_gap_total']}**; "
            f"I2S faults **{h4['i2s_fault_total']}**.",
            "",
            "[FACT] This is IM73D production-path proxy evidence from a non-shippable capture build, not byte-identical production timing.",
            "",
            "## H5 Front-End Identity",
            "",
            f"[FACT] Verdict: **{h5['verdict']}**. `{PRODUCTION_REFERENCE_ENV}` resolves through `k1_bench_im73d` and includes `{PRODUCTION_REFERENCE_FLAG}` at 12.8 kHz / 96 / decimation 3.",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- [FACT] {limitation}." for limitation in result["limitations"])
    lines.extend(
        [
            "",
            "## Exact Re-run",
            "",
            "```bash",
            entry_command,
            "```",
            "",
            f"[FACT] Per-track decode commands are preserved in `{args.commands_out}`.",
        ]
    )
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": "MEASURED", "h2": h2, "h4": h4["verdict"], "h5": h5["verdict"], "out_json": str(args.out_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
