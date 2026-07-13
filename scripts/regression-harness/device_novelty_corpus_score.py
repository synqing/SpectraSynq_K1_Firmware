#!/usr/bin/env python3
"""Score device-novelty replay trajectories using the frozen baseline metrics.

The input manifest names each track's trustworthy ground truth, capture summary,
and host replay trajectory. Captures fail closed unless their integrity verdict
is PASS. The reference metrics are recomputed from the committed baseline CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import tempo_accuracy as accuracy


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = ROOT / "docs/measurements/tempo-octave-baseline.tracks.csv"
BUCKETS = ["<060", "060-080", "080-100", "100-120", "120-140", "140-156", ">156"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON manifest containing a tracks array")
    parser.add_argument("--baseline-csv", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    return parser.parse_args()


def load_baseline(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    "acc1": raw["acc1"] == "True",
                    "acc2": raw["acc2"] == "True",
                    "locked_frac": float(raw["locked_frac"]),
                    "in_range": raw["in_range"] == "True",
                    "bucket": raw["bucket"],
                }
            )
    return rows


def score_trajectory(path: Path, gt_bpm: float) -> dict[str, object]:
    ms, bpm, conf, lock = accuracy.parse_trajectory(path.read_text(errors="replace"))
    detected, settled_median, locked_fraction, final_confidence = accuracy.detected_bpm(ms, bpm, conf, lock)
    if detected is None:
        raise RuntimeError(f"trajectory has no scoreable rows: {path}")
    acc1, acc2, best_k, best_error = accuracy.octave_eval(detected, gt_bpm)
    return {
        "det_bpm": detected,
        "settled_median": settled_median,
        "locked_frac": locked_fraction,
        "final_conf": final_confidence,
        "acc1": acc1,
        "acc2": acc2,
        "octave": accuracy.octave_label(best_k, best_error),
        "rel_err": best_error,
        "in_range": accuracy.BPM_LO <= gt_bpm <= accuracy.BPM_HI,
        "bucket": accuracy.bucket(gt_bpm),
        "n_frames": int(ms.size),
    }


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    count = len(rows)
    if not count:
        return {"n": 0, "acc1": None, "acc2": None, "octave_error": None, "locked_fraction": None}
    acc1 = sum(bool(row["acc1"]) for row in rows) / count
    acc2 = sum(bool(row["acc2"]) for row in rows) / count
    return {
        "n": count,
        "acc1": acc1,
        "acc2": acc2,
        "octave_error": acc2 - acc1,
        "locked_fraction": sum(float(row["locked_frac"]) for row in rows) / count,
    }


def aggregate_set(rows: list[dict[str, object]]) -> dict[str, object]:
    result = {
        "all": aggregate(rows),
        "in_range": aggregate([row for row in rows if bool(row["in_range"])]),
        "buckets": {},
    }
    for name in BUCKETS:
        result["buckets"][name] = aggregate([row for row in rows if row["bucket"] == name])
    return result


def percent(value: object) -> str:
    return "N/A" if value is None else f"{float(value) * 100.0:.1f}%"


def delta(device: object, baseline: object) -> str:
    if device is None or baseline is None:
        return "N/A"
    return f"{(float(device) - float(baseline)) * 100.0:+.1f} pp"


def table_row(label: str, device: dict[str, object], baseline: dict[str, object]) -> str:
    return (
        f"| {label} | {device['n']} | {baseline['n']} | "
        f"{percent(device['acc1'])} | {percent(baseline['acc1'])} | {delta(device['acc1'], baseline['acc1'])} | "
        f"{percent(device['acc2'])} | {percent(baseline['acc2'])} | {delta(device['acc2'], baseline['acc2'])} | "
        f"{percent(device['octave_error'])} | {percent(device['locked_fraction'])} | "
        f"{percent(baseline['locked_fraction'])} |"
    )


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    device_rows: list[dict[str, object]] = []
    validation_errors: list[str] = []
    for track in manifest.get("tracks", []):
        track_id = str(track["id"])
        capture_path = Path(track["capture_summary"]).expanduser()
        trajectory_path = Path(track["replay_trajectory"]).expanduser()
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        verdict = capture.get("validation", {}).get("verdict")
        if verdict != "PASS":
            validation_errors.append(f"{track_id}: capture verdict is {verdict!r}, not PASS")
            continue
        if str(capture.get("track_sha256")) != str(track.get("track_sha256")):
            validation_errors.append(f"{track_id}: capture track SHA-256 does not match manifest")
            continue
        scored = score_trajectory(trajectory_path, float(track["gt_bpm"]))
        scored.update(
            {
                "id": track_id,
                "title": track["title"],
                "genre": track["genre"],
                "gt_bpm": float(track["gt_bpm"]),
                "gt_source": track["gt_source"],
                "track_sha256": track["track_sha256"],
                "capture_summary": str(capture_path),
                "replay_trajectory": str(trajectory_path),
            }
        )
        device_rows.append(scored)

    if validation_errors:
        raise RuntimeError("invalid corpus inputs: " + "; ".join(validation_errors))
    if not device_rows:
        raise RuntimeError("manifest contains no scoreable tracks")

    baseline_rows = load_baseline(args.baseline_csv)
    device = aggregate_set(device_rows)
    baseline = aggregate_set(baseline_rows)
    result = {
        "verdict": "MEASURED",
        "metric_contract": {
            "acc1": "relative error <=4% at exact GT tempo",
            "acc2": "relative error <=4% at GT multiples 1/3, 1/2, 1, 2, 3",
            "detected_bpm": "mode of rounded BPM over final 50% of trajectory",
            "locked_fraction": "mean lock state over final 50% of trajectory",
            "octave_error": "Acc2 minus Acc1",
        },
        "manifest": str(args.manifest),
        "baseline_csv": str(args.baseline_csv),
        "device": device,
        "baseline": baseline,
        "tracks": device_rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Device-Novelty Tempo Delta",
        "",
        "[FACT] Device rows use buffered on-device GDFT novelty replayed through the current host tempo detector.",
        "",
        "[FACT] Baseline rows are recomputed from `docs/measurements/tempo-octave-baseline.tracks.csv`.",
        "",
        "[INFERENCE] Deltas are cross-corpus reference differences, not a paired estimate of novelty-front-end causality.",
        "",
        "| Scope | Device n | Baseline n | Device Acc1 | Baseline Acc1 | Delta Acc1 | Device Acc2 | Baseline Acc2 | Delta Acc2 | Device octave-error | Device locked | Baseline locked |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        table_row("All", device["all"], baseline["all"]),
        table_row("In-range 60-155", device["in_range"], baseline["in_range"]),
        "",
        "## Per-Bucket",
        "",
        "| Bucket | Device n | Baseline n | Device Acc1 | Baseline Acc1 | Delta Acc1 | Device Acc2 | Baseline Acc2 | Delta Acc2 | Device octave-error | Device locked | Baseline locked |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(table_row(f"**{name}**" if name == "120-140" else name, device["buckets"][name], baseline["buckets"][name]) for name in BUCKETS)
    lines.extend(
        [
            "",
            "## Tracks",
            "",
            "| Track | Genre | GT BPM | Detected BPM | Acc1 | Acc2 | Octave | Locked fraction | GT source |",
            "|---|---|---:|---:|---:|---:|---|---:|---|",
        ]
    )
    for row in device_rows:
        lines.append(
            f"| {row['title']} | {row['genre']} | {row['gt_bpm']:.1f} | {row['det_bpm']:.1f} | "
            f"{'PASS' if row['acc1'] else 'FAIL'} | {'PASS' if row['acc2'] else 'FAIL'} | "
            f"{row['octave']} | {percent(row['locked_frac'])} | {row['gt_source']} |"
        )
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": "MEASURED", "tracks": len(device_rows), "out_json": str(args.out_json), "out_md": str(args.out_md)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
