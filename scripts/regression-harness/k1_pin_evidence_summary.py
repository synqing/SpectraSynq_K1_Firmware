#!/usr/bin/env python3
"""Summarise K1 loud-pinning evidence captures.

This host tool joins manual dBA labels with framed K1 diagnostic records. It is
deliberately fail-closed: corrupt frame transport, missing labels, or missing
K1 pin evidence records produce an invalid result rather than a best-effort
claim.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FRAME_GATE_PATH = ROOT / "scripts" / "regression-harness" / "vpab_frame_gate.py"

KIND_K1_PIN_EVIDENCE = 4
PAYLOAD_STRUCT = struct.Struct("<BBHIIIHHHHHHHHHHH?B?HHBBHHHHHHHHHBHHHHHHHH")
DBA_BUCKETS = {
    "unknown": 0,
    "normal_52_62": 1,
    "threshold_63_66": 2,
    "loud_67_72": 3,
    "extreme_73_plus": 4,
}
DBA_BUCKET_NAMES = {value: key for key, value in DBA_BUCKETS.items()}


def _load_frame_gate():
    spec = importlib.util.spec_from_file_location("vpab_frame_gate", FRAME_GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {FRAME_GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpab_frame_gate = _load_frame_gate()


def _q16(value: int) -> float:
    return float(value) / 65535.0


def _q8_8(value: int) -> float:
    return float(value) / 256.0


def _manifest_bucket(manifest: dict[str, Any]) -> tuple[str | None, list[str]]:
    issues: list[str] = []
    if "legs" in manifest:
        legs = manifest.get("legs")
        if not isinstance(legs, list) or not legs:
            return None, ["manifest requires at least one leg"]
        buckets = {leg.get("dBA_bucket") for leg in legs if isinstance(leg, dict)}
        if len(buckets) != 1:
            return None, ["manifest legs must share exactly one dBA_bucket for this summary"]
        bucket = next(iter(buckets))
    else:
        bucket = manifest.get("dBA_bucket")

    if not isinstance(bucket, str) or bucket not in DBA_BUCKETS or bucket == "unknown":
        issues.append("manifest requires a valid non-unknown dBA_bucket")
        return None, issues
    return bucket, issues


def _assemble_payloads(frames_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    gate = vpab_frame_gate.evaluate_text(frames_text)
    begin, end, records, record_order, issues = vpab_frame_gate._parse_stream(frames_text)
    if issues:
        return gate, []

    assembled: list[dict[str, Any]] = []
    for seq in record_order:
        record = records[seq]
        if record["kind"] != KIND_K1_PIN_EVIDENCE:
            continue
        payload = bytearray(record["len"] or 0)
        for idx in range(record["chunks"] or 0):
            chunk = record["chunk_items"][idx]
            off = chunk["off"]
            payload[off:off + len(chunk["payload"])] = chunk["payload"]
        assembled.append(
            {
                "seq": record["seq"],
                "frame": record["frame"],
                "t_us": record["t_us"],
                "payload": bytes(payload),
            }
        )
    return gate, assembled


def decode_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = record["payload"]
    if len(payload) != PAYLOAD_STRUCT.size:
        raise ValueError(f"k1_pin payload seq={record['seq']} length {len(payload)} != {PAYLOAD_STRUCT.size}")
    values = PAYLOAD_STRUCT.unpack(payload)
    keys = (
        "version",
        "channel_id",
        "mode",
        "ap_ms",
        "chroma_seq",
        "state_bits",
        "raw_peak_q",
        "post_sensitivity_peak_q",
        "clip_count",
        "near_rail_count",
        "sample_count",
        "agc_gain_q",
        "agc_envelope_q",
        "spectral_saturation_q",
        "chroma_pre_max_q",
        "chroma_pre_mean_q",
        "chroma_gate_q",
        "agc_gated",
        "dba_bucket_id",
        "held_hue_valid",
        "held_hue_q",
        "centroid_strength_q",
        "dominant_bin",
        "palette_index",
        "chroma_norm_max_q",
        "chroma_norm_mean_q",
        "chroma_final_max_q",
        "chroma_final_mean_q",
        "chroma_flatness_q",
        "loud_input_trim_q",
        "loud_gdft_trim_q",
        "vivid_chroma_q",
        "vivid_black_q",
        "chroma_profile",
        "colour_entropy_q",
        "top_colour_dwell_q",
        "top_hue_q",
        "active_led_pct_q",
        "saturation_avg_q",
        "white_bias_avg_q",
        "com_q",
        "motion_delta_q",
    )
    row = dict(zip(keys, values))
    row.update(
        {
            "seq": record["seq"],
            "frame": record["frame"],
            "t_us": record["t_us"],
            "channel": "secondary" if row["channel_id"] == 1 else "primary",
            "dba_bucket": DBA_BUCKET_NAMES.get(row["dba_bucket_id"], "unknown"),
            "raw_peak": _q16(row["raw_peak_q"]),
            "post_sensitivity_peak": _q16(row["post_sensitivity_peak_q"]),
            "agc_gain": _q16(row["agc_gain_q"]),
            "agc_envelope": _q16(row["agc_envelope_q"]),
            "spectral_saturation": _q16(row["spectral_saturation_q"]),
            "chroma_pre_max": _q16(row["chroma_pre_max_q"]),
            "chroma_pre_mean": _q16(row["chroma_pre_mean_q"]),
            "chroma_gate": _q16(row["chroma_gate_q"]),
            "held_hue": _q16(row["held_hue_q"]),
            "centroid_strength": _q16(row["centroid_strength_q"]),
            "chroma_norm_max": _q16(row["chroma_norm_max_q"]),
            "chroma_norm_mean": _q16(row["chroma_norm_mean_q"]),
            "chroma_final_max": _q16(row["chroma_final_max_q"]),
            "chroma_final_mean": _q16(row["chroma_final_mean_q"]),
            "chroma_flatness": _q16(row["chroma_flatness_q"]),
            "loud_input_trim": _q16(row["loud_input_trim_q"]),
            "loud_gdft_trim": _q16(row["loud_gdft_trim_q"]),
            "vivid_chroma": _q16(row["vivid_chroma_q"]),
            "vivid_black": _q16(row["vivid_black_q"]),
            "colour_entropy": _q16(row["colour_entropy_q"]),
            "top_colour_dwell": _q16(row["top_colour_dwell_q"]),
            "top_hue": _q16(row["top_hue_q"]),
            "active_led_pct": _q16(row["active_led_pct_q"]),
            "saturation_avg": _q16(row["saturation_avg_q"]),
            "white_bias_avg": _q16(row["white_bias_avg_q"]),
            "com": _q8_8(row["com_q"]),
            "motion_delta": _q8_8(row["motion_delta_q"]),
        }
    )
    return row


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return statistics.fmean(values) if values else 0.0


def _classify(metrics: dict[str, float]) -> str:
    spectral_high = metrics["spectral_saturation_mean"] >= 0.15
    chroma_collapsed = metrics["chroma_gate_mean"] <= 0.20 or metrics["chroma_final_max_mean"] <= 0.08
    final_pinned = metrics["top_colour_dwell_mean"] >= 0.55 and metrics["colour_entropy_mean"] <= 0.90
    if spectral_high and chroma_collapsed and final_pinned:
        return "MIXED_BY_CONSUMER"
    if spectral_high and final_pinned:
        return "AP_DOMINANT"
    if chroma_collapsed and final_pinned:
        return "VP_DOMINANT"
    if final_pinned:
        return "OUTPUT_STAGE"
    return "INCONCLUSIVE"


def evaluate_capture(frames_text: str, manifest: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    dba_bucket, manifest_issues = _manifest_bucket(manifest)
    issues.extend(manifest_issues)

    gate, payload_records = _assemble_payloads(frames_text)
    if not gate.get("passed"):
        issues.append("framed diagnostic gate failed")

    rows: list[dict[str, Any]] = []
    for record in payload_records:
        try:
            rows.append(decode_payload(record))
        except ValueError as exc:
            issues.append(str(exc))

    if not rows:
        issues.append("no k1_pin_evidence records found")

    metrics = {
        "spectral_saturation_mean": _mean(rows, "spectral_saturation"),
        "chroma_gate_mean": _mean(rows, "chroma_gate"),
        "chroma_final_max_mean": _mean(rows, "chroma_final_max"),
        "colour_entropy_mean": _mean(rows, "colour_entropy"),
        "top_colour_dwell_mean": _mean(rows, "top_colour_dwell"),
        "active_led_pct_mean": _mean(rows, "active_led_pct"),
        "motion_delta_mean": _mean(rows, "motion_delta"),
    }
    classification = _classify(metrics) if not issues else "INVALID"

    return {
        "schema": "k1_pin_evidence_summary.v1",
        "result": "PASS" if not issues else "FAIL",
        "classification": classification,
        "dBA_bucket": dba_bucket,
        "records": len(rows),
        "metrics": metrics,
        "gate": gate,
        "issues": issues,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="K1DF framed diagnostic log")
    parser.add_argument("--manifest", required=True, help="manual dBA/capture manifest JSON")
    parser.add_argument("--output", required=True, help="write JSON summary here")
    args = parser.parse_args(argv)

    frames_text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = evaluate_capture(frames_text, manifest)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
