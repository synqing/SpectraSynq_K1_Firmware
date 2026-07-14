#!/usr/bin/env python3
"""Score same-device V1-off/V2 tempo and onset telemetry without grading eyes-on chord behaviour."""

from __future__ import annotations

import argparse
import collections
import json
import re
import shlex
import statistics
import sys
from pathlib import Path


TEMPO_RE = re.compile(
    r"^TEMPO,t=(\d+),bpm=([0-9.]+),phase=([0-9.]+),conf=([0-9.]+),"
    r"beat=(\d),lock=(\d),str=([0-9.]+)$"
)
AP_RE = re.compile(
    r"^\[AP\].*\| bpm=([0-9.]+) conf=([0-9.]+) lock=(\d).*"
    r"\| onset=(\d) bass=(\d) ostr=([0-9.]+)"
)
CRASH_RE = re.compile(
    r"Guru Meditation|Backtrace:|rst:0x|watchdog|abort\(\) was called|assert failed|panic(?:'ed|:)",
    re.IGNORECASE,
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-summary", required=True)
    parser.add_argument("--v2-summary", required=True)
    parser.add_argument("--expected-bpm", type=float, required=True)
    parser.add_argument("--captain-eyes-on", choices=("PASS", "FAIL", "NOT_VERIFIED"), default="NOT_VERIFIED")
    parser.add_argument("--eyes-on-evidence")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    return parser.parse_args()


def analyse(summary_path: Path, expected_bpm: float) -> dict[str, object]:
    summary = json.loads(summary_path.read_text())
    raw_path = Path(summary["raw_log"])
    lines = raw_path.read_text(errors="replace").splitlines()
    tempo_rows = []
    ap_rows = []
    for line in lines:
        match = TEMPO_RE.match(line)
        if match:
            tempo_rows.append(tuple(float(value) for value in match.groups()))
        match = AP_RE.match(line)
        if match:
            ap_rows.append(tuple(float(value) for value in match.groups()))
    if not tempo_rows or not ap_rows:
        raise ValueError(f"missing structured TEMPO/AP rows in {raw_path}")

    final_tempo = tempo_rows[len(tempo_rows) // 2 :]
    mode_bpm = collections.Counter(round(row[1]) for row in final_tempo).most_common(1)[0][0]
    apcad = summary.get("apcad_soak") or {}
    timing = ((apcad.get("timing_us") or {}).get("active_ap_work_elapsed_us") or {})
    worst_rows = (apcad.get("compact_soak_worst") or [])
    crash_lines = [line for line in lines if CRASH_RE.search(line)]
    rel_error = abs(mode_bpm - expected_bpm) / expected_bpm
    mechanical_errors = list((summary.get("validation") or {}).get("errors") or [])
    for key in ("frame_gap_count", "timestamp_regression_count", "i2s_not_ok_count", "bytes_mismatch_count"):
        if int(apcad.get(key, 0) or 0):
            mechanical_errors.append(f"{key}={apcad[key]}")
    if crash_lines:
        mechanical_errors.append(f"crash_signatures={len(crash_lines)}")

    return {
        "summary": str(summary_path),
        "raw_log": str(raw_path),
        "build_env": (summary.get("runtime_identity") or {}).get("build_env"),
        "chip_id": (summary.get("runtime_identity") or {}).get("chip_id"),
        "capture_validation": (summary.get("validation") or {}).get("verdict"),
        "mechanical_verdict": "PASS" if not mechanical_errors else "FAIL",
        "mechanical_errors": mechanical_errors,
        "tempo": {
            "rows": len(tempo_rows),
            "final_half_rows": len(final_tempo),
            "final_half_mode_bpm": mode_bpm,
            "final_half_median_bpm": statistics.median(row[1] for row in final_tempo),
            "final_half_relative_error": rel_error,
            "final_half_acc1": rel_error <= 0.04,
            "final_half_locked_fraction": sum(row[5] for row in final_tempo) / len(final_tempo),
            "final_half_median_confidence": statistics.median(row[3] for row in final_tempo),
            "sampled_beat_tick_count": int(sum(row[4] for row in final_tempo)),
        },
        "ap_sampled": {
            "rows": len(ap_rows),
            "onset_positive_rows": int(sum(row[3] for row in ap_rows)),
            "bass_onset_positive_rows": int(sum(row[4] for row in ap_rows)),
            "locked_fraction": sum(row[2] for row in ap_rows) / len(ap_rows),
        },
        "capture_integrity": {
            "novelty_rows": summary.get("nov_rows"),
            "novelty_dropped": (summary.get("novelty_integrity") or {}).get("dropped"),
            "frame_gap_count": apcad.get("frame_gap_count"),
            "timestamp_regression_count": apcad.get("timestamp_regression_count"),
            "i2s_not_ok_count": apcad.get("i2s_not_ok_count"),
            "bytes_mismatch_count": apcad.get("bytes_mismatch_count"),
            "active_p95_us": timing.get("p95"),
            "active_max_us": timing.get("max"),
            "total_max_us": max((row.get("total_us", 0) for row in worst_rows), default=None),
            "active_over_7500_count": apcad.get("active_ap_work_over_7500_count"),
            "crash_signature_count": len(crash_lines),
        },
    }


def pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def render_markdown(payload: dict[str, object]) -> str:
    v1 = payload["v1_off"]
    v2 = payload["v2"]
    lines = [
        "# Device Audio-Semantic V1-Off / V2 Comparison",
        "",
        "[FACT] Both rows use the same bench K1, track, duration, playback path, calibration profile, and diagnostic surfaces.",
        "",
        "| Metric | V1 off-path | V2 |",
        "|---|---:|---:|",
        f"| Runtime environment | `{v1['build_env']}` | `{v2['build_env']}` |",
        f"| Tempo mode, final half | {v1['tempo']['final_half_mode_bpm']} BPM | {v2['tempo']['final_half_mode_bpm']} BPM |",
        f"| Tempo Acc1 at {payload['expected_bpm']:.1f} BPM | {'PASS' if v1['tempo']['final_half_acc1'] else 'FAIL'} | {'PASS' if v2['tempo']['final_half_acc1'] else 'FAIL'} |",
        f"| Locked fraction, final half | {pct(v1['tempo']['final_half_locked_fraction'])} | {pct(v2['tempo']['final_half_locked_fraction'])} |",
        f"| Median confidence, final half | {v1['tempo']['final_half_median_confidence']:.3f} | {v2['tempo']['final_half_median_confidence']:.3f} |",
        f"| AP onset-positive samples / {v1['ap_sampled']['rows']} | {v1['ap_sampled']['onset_positive_rows']} | {v2['ap_sampled']['onset_positive_rows']} |",
        f"| AP bass-onset-positive samples / {v1['ap_sampled']['rows']} | {v1['ap_sampled']['bass_onset_positive_rows']} | {v2['ap_sampled']['bass_onset_positive_rows']} |",
        f"| Frame gaps | {v1['capture_integrity']['frame_gap_count']} | {v2['capture_integrity']['frame_gap_count']} |",
        f"| I2S faults | {v1['capture_integrity']['i2s_not_ok_count']} | {v2['capture_integrity']['i2s_not_ok_count']} |",
        f"| Crash signatures | {v1['capture_integrity']['crash_signature_count']} | {v2['capture_integrity']['crash_signature_count']} |",
        f"| Active AP p95 / max | {v1['capture_integrity']['active_p95_us']:.0f} / {v1['capture_integrity']['active_max_us']:.0f} us | {v2['capture_integrity']['active_p95_us']:.0f} / {v2['capture_integrity']['active_max_us']:.0f} us |",
        f"| Mechanical verdict | {v1['mechanical_verdict']} | {v2['mechanical_verdict']} |",
        "",
        "[FACT] `onset-positive` values are 1 Hz sampled-positive rows, not complete event counts; sampled beat ticks are excluded from the verdict because the 20 Hz stream can alias frame-local ticks.",
        "",
        "[FACT] Production AP telemetry intentionally exposes no chord field. Chord colour and perceptual regression therefore remain Captain eyes-on evidence, not a fabricated host metric.",
        "",
        f"[FACT] Captain eyes-on verdict: **{payload['captain_eyes_on']}**.",
        "",
        (
            f"[FACT] Corrected eyes-on evidence: `{payload['eyes_on_evidence']}`."
            if payload.get("eyes_on_evidence")
            else "[FACT] Corrected eyes-on evidence: none."
        ),
        "",
        f"[FACT] DEVICE five-flag comparison verdict: **{payload['gate_verdict']}**.",
        "",
        "## Exact Re-run",
        "",
        "```bash",
        payload["rerun_command"],
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    rerun_command = shlex.join(["python3", "scripts/regression-harness/device_semantic_ab_score.py", *sys.argv[1:]])
    eyes_on_evidence = None
    eyes_on_evidence_pass = False
    if args.eyes_on_evidence:
        eyes_on_path = Path(args.eyes_on_evidence)
        eyes_on_evidence = json.loads(eyes_on_path.read_text())
        eyes_on_evidence_pass = eyes_on_evidence.get("gate_verdict") == "PASS"
    if args.captain_eyes_on == "PASS" and not eyes_on_evidence_pass:
        raise SystemExit("Captain PASS requires --eyes-on-evidence with gate_verdict PASS")
    payload = {
        "verdict": "MEASURED",
        "expected_bpm": args.expected_bpm,
        "captain_eyes_on": args.captain_eyes_on,
        "eyes_on_evidence": args.eyes_on_evidence,
        "eyes_on_evidence_pass": eyes_on_evidence_pass,
        "v1_off": analyse(Path(args.v1_summary), args.expected_bpm),
        "v2": analyse(Path(args.v2_summary), args.expected_bpm),
        "rerun_command": rerun_command,
    }
    mechanical_pass = payload["v1_off"]["mechanical_verdict"] == "PASS" and payload["v2"]["mechanical_verdict"] == "PASS"
    payload["gate_verdict"] = (
        "PASS" if mechanical_pass and args.captain_eyes_on == "PASS" and eyes_on_evidence_pass else "NOT_VERIFIED"
    )
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    Path(args.out_md).write_text(render_markdown(payload))
    print(json.dumps({"verdict": payload["gate_verdict"], "out_json": args.out_json, "out_md": args.out_md}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
