#!/usr/bin/env python3
"""Replay captured device NOV telemetry through the host sb_tempo.cpp harness.

This is an adapter, not a DSP implementation. It parses non-shippable firmware
`NOV,` rows, expands each accepted tempo novelty sample back into three AP-frame
updates, then feeds the resulting `ms novelty silence` stream to
tempo_replay.py's existing host C++ replay binary.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path

import tempo_replay as trp


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEFINES = ["SB_TEMPO_CONF_V2", "SB_TEMPO_FLYWHEEL_V2"]
DEFAULT_ACCEPTED_NOVELTY_RATE_HZ = (12800.0 / 96.0) / 3.0
SB_TEMPO_SOURCE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "sb_tempo.cpp"


def c_float_literal(value: float) -> str:
    """Return a C++ float literal that is valid for integer and fractional rates."""
    text = f"{float(value):.9g}"
    if "." not in text and "e" not in text and "E" not in text:
        text += ".0"
    return f"{text}f"


def _to_number(raw: str):
    try:
        if any(ch in raw for ch in ".eE"):
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _to_number_if_numeric(raw):
    try:
        if any(ch in raw for ch in ".eE"):
            return float(raw)
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return None


def _to_float_or_zero(raw) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def parse_nov_rows(path: Path) -> tuple[list[dict], list[str], dict]:
    parsed_rows: list[dict] = []
    has_buffer_rows = False
    for line_no, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        marker = line.find("NOV,")
        if marker < 0:
            continue
        payload = line[marker + len("NOV,") :]
        row = {"line_no": line_no}
        for part in payload.split(","):
            if "=" not in part:
                continue
            key, raw = part.split("=", 1)
            row[key.strip()] = _to_number(raw.strip())
        if str(row.get("src", "")) == "buf":
            has_buffer_rows = True
        parsed_rows.append(row)

    by_emit: dict[int, dict] = {}
    warnings: list[str] = []
    source_mode = "buffer" if has_buffer_rows else "live_or_legacy"
    ignored_non_buffer_rows = 0
    for row in parsed_rows:
        line_no = int(row["line_no"])
        src = str(row.get("src", ""))
        if has_buffer_rows and src != "buf":
            ignored_non_buffer_rows += 1
            continue
        if src and src not in {"buf", "live"}:
            continue

        t_val = _to_number_if_numeric(str(row.get("t", "")))
        emit_val = _to_number_if_numeric(str(row.get("emit", "")))
        nov_val = _to_number_if_numeric(str(row.get("nov", "")))
        if t_val is None or emit_val is None or nov_val is None:
            warnings.append(f"line {line_no}: NOV row missing t, emit, or nov")
            continue
        row["t"] = t_val
        row["emit"] = int(emit_val)
        row["nov"] = nov_val
        emit = int(row["emit"])
        if emit not in by_emit:
            by_emit[emit] = row
            continue
        existing = by_emit[emit]
        existing_src = str(existing.get("src", ""))
        if existing_src != "buf" and src == "buf":
            by_emit[emit] = row
        else:
            warnings.append(f"duplicate emit {emit} at line {line_no} ignored")

    rows = sorted(by_emit.values(), key=lambda r: (int(r["emit"]), int(r["t"])))
    deduped: list[dict] = []
    seen_emit: set[int] = set()
    for row in rows:
        emit = int(row["emit"])
        if emit in seen_emit:
            warnings.append(f"duplicate emit {emit} at line {row['line_no']} ignored")
            continue
        seen_emit.add(emit)
        deduped.append(row)
    metadata = {
        "source_mode": source_mode,
        "ignored_non_buffer_rows": ignored_non_buffer_rows,
    }
    return deduped, warnings, metadata


def audit_nov_rows(rows: list[dict]) -> dict:
    if not rows:
        return {
            "row_count": 0,
            "emit_gap_count": 0,
            "timestamp_regression_count": 0,
            "large_dt_count": 0,
            "warnings": ["no NOV rows parsed"],
        }

    emits = [int(r["emit"]) for r in rows]
    times = [int(r["t"]) for r in rows]
    gaps = []
    regressions = []
    large_dt = []
    for idx in range(1, len(rows)):
        emit_delta = emits[idx] - emits[idx - 1]
        dt = times[idx] - times[idx - 1]
        if emit_delta != 1:
            gaps.append({"at_index": idx, "prev_emit": emits[idx - 1], "emit": emits[idx]})
        if dt <= 0:
            regressions.append({"at_index": idx, "prev_t": times[idx - 1], "t": times[idx]})
        if dt > 60:
            large_dt.append({"at_index": idx, "prev_t": times[idx - 1], "t": times[idx], "dt": dt})

    duration_ms = times[-1] - times[0] if len(times) > 1 else 0
    cadence = [times[i] - times[i - 1] for i in range(1, len(times)) if times[i] > times[i - 1]]
    return {
        "row_count": len(rows),
        "first_emit": emits[0],
        "last_emit": emits[-1],
        "first_t_ms": times[0],
        "last_t_ms": times[-1],
        "duration_ms": duration_ms,
        "accepted_nov_rate_hz_measured": ((len(rows) - 1) * 1000.0 / duration_ms) if duration_ms > 0 else None,
        "cadence_ms_median": statistics.median(cadence) if cadence else None,
        "cadence_ms_p5": _percentile(cadence, 0.05),
        "cadence_ms_p95": _percentile(cadence, 0.95),
        "cadence_ms_min": min(cadence) if cadence else None,
        "cadence_ms_max": max(cadence) if cadence else None,
        "emit_gap_count": len(gaps),
        "emit_gaps_first10": gaps[:10],
        "timestamp_regression_count": len(regressions),
        "timestamp_regressions_first10": regressions[:10],
        "large_dt_count": len(large_dt),
        "large_dt_first10": large_dt[:10],
    }


def rows_to_ap_frame_stdin(
    rows: list[dict],
    novelty_field: str = "nov",
    ap_frame_hz: float = 12800.0 / 96.0,
    decimation: int = 3,
) -> str:
    if not rows:
        return ""

    lines: list[str] = []
    ap_frame_ms = 1000.0 / ap_frame_hz
    first_t = int(rows[0]["t"])
    prime_t = max(0, int(round(first_t - decimation * ap_frame_ms)))
    lines.append(f"{prime_t} 0.000000 0")
    last_ms = prime_t

    def monotonic_ms(value: float) -> int:
        nonlocal last_ms
        ms = int(round(value))
        if ms <= last_ms:
            ms = last_ms + 1
        last_ms = ms
        return ms

    for row in rows:
        emit_ms = int(row["t"])
        novelty = _to_float_or_zero(row.get(novelty_field, row["nov"]))
        silence = int(row.get("sil", 0))
        # Quiet AP frames followed by the captured accepted sample make the host
        # decimator accept exactly one peak-held sample per NOV row.
        for remaining in range(decimation - 1, -1, -1):
            offset = remaining * ap_frame_ms
            value = 0.0 if remaining else novelty
            ms = monotonic_ms(emit_ms - offset)
            lines.append(f"{ms} {value:.6f} {silence if offset == 0.0 else 0}")
    return "\n".join(lines) + "\n"


def parse_replay_stdout(stdout: str) -> list[dict]:
    frames = []
    for line in stdout.splitlines():
        if not line.startswith("T "):
            continue
        parts = line.split()
        if len(parts) < 7:
            continue
        frames.append(
            {
                "t_ms": int(float(parts[1])),
                "bpm": float(parts[2]),
                "conf": float(parts[3]),
                "lock": int(parts[4]),
                "phase": float(parts[5]),
                "beat": int(parts[6]),
            }
        )
    return frames


def _rounded_counts(values, limit: int = 12) -> dict[str, int]:
    counts = Counter(int(round(v)) for v in values if math.isfinite(v))
    return {str(k): v for k, v in counts.most_common(limit)}


def _percentile(values: list[int], pct: float):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * pct
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(ordered[lo])
    frac = pos - lo
    return float(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)


def _near_bpm(value: float, expected_bpm: int, tolerance_bpm: int) -> bool:
    return abs(int(round(value)) - int(expected_bpm)) <= int(tolerance_bpm)


def summarise_frames(
    frames: list[dict],
    warm_ms: int,
    high_conf: float,
    expected_bpm: int,
    near_bpm_tolerance: int,
) -> dict:
    if not frames:
        return {"frame_count": 0}
    t0 = frames[0]["t_ms"]
    warm = [f for f in frames if f["t_ms"] - t0 >= warm_ms]
    locked = [f for f in warm if f["lock"]]
    high = [f for f in warm if f["conf"] >= high_conf]
    high_or_locked = [f for f in warm if f["lock"] or f["conf"] >= high_conf]
    near_target = lambda seq: sum(
        1 for f in seq if _near_bpm(float(f["bpm"]), expected_bpm, near_bpm_tolerance)
    )
    near_127 = lambda seq: sum(1 for f in seq if _near_bpm(float(f["bpm"]), 127, 3))
    bpms = [f["bpm"] for f in frames]
    warm_bpms = [f["bpm"] for f in warm]
    return {
        "frame_count": len(frames),
        "warm_frame_count": len(warm),
        "expected_bpm": expected_bpm,
        "near_bpm_tolerance": near_bpm_tolerance,
        "bpm_min_median_max": [min(bpms), statistics.median(bpms), max(bpms)],
        "warm_bpm_min_median_max": [min(warm_bpms), statistics.median(warm_bpms), max(warm_bpms)] if warm_bpms else None,
        "warm_bpm_counts": _rounded_counts(warm_bpms),
        "warm_locked_count": len(locked),
        "warm_high_conf_count": len(high),
        "warm_high_or_locked_count": len(high_or_locked),
        "warm_near_target_rows": near_target(warm),
        "warm_locked_near_target_rows": near_target(locked),
        "warm_high_conf_near_target_rows": near_target(high),
        "warm_high_or_locked_near_target_rows": near_target(high_or_locked),
        "warm_near_127_rows": near_127(warm),
        "warm_locked_near_127_rows": near_127(locked),
        "warm_high_conf_near_127_rows": near_127(high),
        "warm_high_or_locked_near_127_rows": near_127(high_or_locked),
        "warm_beat_ticks": sum(f["beat"] for f in warm),
    }


def classify(audit: dict, replay: dict, expected_bpm: int, near_bpm_tolerance: int) -> str:
    if audit.get("row_count", 0) == 0:
        return "invalid_no_nov"
    if audit.get("emit_gap_count", 0) or audit.get("timestamp_regression_count", 0):
        return "partial_capture_parser_gaps"
    warm = replay.get("warm_frame_count", 0) or 0
    if warm == 0:
        return "invalid_no_warm_replay"
    near = replay.get("warm_high_or_locked_near_target_rows", 0)
    high_or_locked = replay.get("warm_high_or_locked_count", 0)
    if high_or_locked and (near / high_or_locked) >= 0.60:
        return "declared_rate_device_nov_replay_locks_near_target"
    counts = replay.get("warm_bpm_counts", {})
    if counts:
        dominant = int(next(iter(counts.keys())))
        if _near_bpm(float(dominant), expected_bpm, near_bpm_tolerance):
            return "declared_rate_device_nov_replay_timing_but_weak_lock"
        if not _near_bpm(float(dominant), expected_bpm, near_bpm_tolerance):
            return "host_replay_of_device_nov_reproduces_wrong_lane_frontend_novelty_suspect"
    return "unclassified"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_log", type=Path)
    parser.add_argument("--out", type=Path, help="write JSON summary")
    parser.add_argument("--trajectory-out", type=Path, help="write raw host replay stdout")
    parser.add_argument("--stdin-out", type=Path, help="write generated ms novelty silence replay input")
    parser.add_argument("--novelty-field", default="nov", choices=["nov", "nov_scaled"])
    parser.add_argument("--compiler", default="clang++")
    parser.add_argument("--define", action="append", default=[], help="extra tempo harness -D define")
    parser.add_argument("--ap-frame-hz", type=float, default=12800.0 / 96.0)
    parser.add_argument("--decimation", type=int, default=3)
    parser.add_argument(
        "--novelty-rate-hz",
        type=float,
        default=DEFAULT_ACCEPTED_NOVELTY_RATE_HZ,
        help=(
            "accepted NOV rate used by the host tempo coefficients. Default is the "
            "firmware contract, 44.444 Hz. Non-default values compile a temporary "
            "harness-only copy of sb_tempo.cpp; production source is not modified."
        ),
    )
    parser.add_argument("--warm-ms", type=int, default=15000)
    parser.add_argument("--high-conf", type=float, default=0.60)
    parser.add_argument("--expected-bpm", type=int, default=127)
    parser.add_argument("--near-bpm-tolerance", type=int, default=3)
    args = parser.parse_args(argv)

    rows, warnings, parse_meta = parse_nov_rows(args.capture_log)
    audit = audit_nov_rows(rows)
    audit.update(parse_meta)
    if warnings:
        audit["parse_warnings"] = warnings[:20]

    replay_stdin = rows_to_ap_frame_stdin(rows, args.novelty_field, args.ap_frame_hz, args.decimation)
    if args.stdin_out:
        args.stdin_out.parent.mkdir(parents=True, exist_ok=True)
        args.stdin_out.write_text(replay_stdin)

    defines = list(DEFAULT_DEFINES)
    for define in args.define:
        if define not in defines:
            defines.append(define)
    rate_defines = [
        f"SB_TEMPO_AP_FRAME_HZ={c_float_literal(args.ap_frame_hz)}",
        f"SB_TEMPO_NOVELTY_DECIMATION={args.decimation}U",
    ]
    for define in rate_defines:
        if define not in defines:
            defines.append(define)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ok, binary, comp = trp.build_binary(
            tmp_path,
            compiler=args.compiler,
            defines=defines,
        )
        if not ok:
            result = {
                "ok": False,
                "stage": "compile",
                "capture_log": str(args.capture_log),
                "defines": defines,
                "accepted_novelty_rate_hz_used": args.novelty_rate_hz,
                "replay_injection_mode": "B_AP_FRAME_RECONSTRUCTION",
                "nov_audit": audit,
                "compile": comp,
            }
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1
        run = trp.replay_stdin(binary, replay_stdin)

    frames = parse_replay_stdout(run.get("stdout", ""))
    replay_summary = summarise_frames(
        frames,
        args.warm_ms,
        args.high_conf,
        args.expected_bpm,
        args.near_bpm_tolerance,
    )
    result = {
        "ok": run["ok"],
        "capture_log": str(args.capture_log),
        "defines": defines,
        "novelty_field": args.novelty_field,
        "accepted_novelty_rate_hz_used": args.novelty_rate_hz,
        "ap_frame_hz_used_for_reconstruction": args.ap_frame_hz,
        "ap_frame_ms_used_for_reconstruction": 1000.0 / args.ap_frame_hz,
        "decimation_used_for_reconstruction": args.decimation,
        "replay_injection_mode": "B_AP_FRAME_RECONSTRUCTION",
        "nov_audit": audit,
        "replay_summary": replay_summary,
        "classification": classify(audit, replay_summary, args.expected_bpm, args.near_bpm_tolerance),
        "run_returncode": run["returncode"],
        "stderr": run.get("stderr", ""),
    }

    if args.trajectory_out:
        args.trajectory_out.parent.mkdir(parents=True, exist_ok=True)
        args.trajectory_out.write_text(run.get("stdout", ""))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if run["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
