#!/usr/bin/env python3
"""Gate paired on-device final-buffer twitch summaries.

The firmware computes lit-count and adjacent-frame delta histograms over every
post-gamma frame before FastLED transmission. This host gate compares only the
completed aggregates; it never reconstructs adjacency from serial traffic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PREFIX = "TWITCH_RESULT "


def parse_row(text: str) -> dict:
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(PREFIX):
            continue
        fields = {}
        for token in line[len(PREFIX):].split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            fields[key] = value
        if fields.get("complete") == "1" and fields.get("active") == "0":
            rows.append(fields)
    if len(rows) != 1:
        raise ValueError(f"expected exactly one completed TWITCH_RESULT, got {len(rows)}")
    row = rows[0]
    integer_fields = {
        "requested_ms", "start_ms", "end_ms", "warmup_frames", "frames",
        "delta_frames", "lit_threshold", "p_lit_p50", "p_lit_p95",
        "p_delta_p95", "s_lit_p50", "s_lit_p95", "s_delta_p95", "tick_max_us",
    }
    for field in integer_fields:
        if field not in row:
            raise ValueError(f"missing {field} in TWITCH_RESULT")
        row[field] = int(row[field])
    if row.get("delta") != "mean_abs_rgb_channel":
        raise ValueError("unexpected frame-delta definition")
    return row


def evaluate(
    silence: dict,
    music: dict,
    *,
    silence_lit_p50_max: int = 4,
    silence_lit_p95_max: int = 8,
    silence_delta_p95_max: int = 1,
    music_lit_p50_min: int = 16,
    separation_min: int = 12,
    tick_max_us_max: int = 500,
) -> dict:
    failures = []
    if silence["requested_ms"] != music["requested_ms"]:
        failures.append("integration windows differ")
    if silence["warmup_frames"] != music["warmup_frames"]:
        failures.append("warm-up windows differ")
    if silence["lit_threshold"] != music["lit_threshold"]:
        failures.append("lit thresholds differ")
    if silence["frames"] <= 0 or music["frames"] <= 0:
        failures.append("empty measurement window")
    elif abs(silence["frames"] - music["frames"]) / max(silence["frames"], music["frames"]) > 0.05:
        failures.append("effective frame-count windows differ by more than 5%")
    if silence["delta_frames"] != max(0, silence["frames"]):
        failures.append("silence adjacency coverage is incomplete")
    if music["delta_frames"] != max(0, music["frames"]):
        failures.append("music adjacency coverage is incomplete")

    channel_results = {}
    for prefix in ("p", "s"):
        sil_p50 = silence[f"{prefix}_lit_p50"]
        sil_p95 = silence[f"{prefix}_lit_p95"]
        sil_delta = silence[f"{prefix}_delta_p95"]
        mus_p50 = music[f"{prefix}_lit_p50"]
        separation = mus_p50 - sil_p95
        channel_results[prefix] = {
            "silence_lit_p50": sil_p50,
            "silence_lit_p95": sil_p95,
            "silence_delta_p95": sil_delta,
            "music_lit_p50": mus_p50,
            "music_vs_silence_separation": separation,
        }
        if sil_p50 > silence_lit_p50_max:
            failures.append(f"{prefix}: silence lit p50 above limit")
        if sil_p95 > silence_lit_p95_max:
            failures.append(f"{prefix}: silence lit p95 above limit")
        if sil_delta > silence_delta_p95_max:
            failures.append(f"{prefix}: silence frame delta p95 above limit")
        if mus_p50 < music_lit_p50_min:
            failures.append(f"{prefix}: music lit p50 below minimum")
        if separation < separation_min:
            failures.append(f"{prefix}: music/silence separation below minimum")

    if silence["tick_max_us"] > tick_max_us_max or music["tick_max_us"] > tick_max_us_max:
        failures.append("oracle hot-path time exceeds diagnostic ceiling")

    return {
        "result": "PASS" if not failures else "RED",
        "failures": failures,
        "contract": {
            "capture_point": "final_post_gamma_pre_FastLED_show",
            "lit_definition": f"max_rgb>{silence['lit_threshold']}",
            "frame_delta": "mean_abs_rgb_channel_on_consecutive_frames",
            "requested_ms": silence["requested_ms"],
            "warmup_frames": silence["warmup_frames"],
            "limits": {
                "silence_lit_p50_max": silence_lit_p50_max,
                "silence_lit_p95_max": silence_lit_p95_max,
                "silence_delta_p95_max": silence_delta_p95_max,
                "music_lit_p50_min": music_lit_p50_min,
                "separation_min": separation_min,
                "tick_max_us_max": tick_max_us_max,
            },
        },
        "channels": channel_results,
        "silence": silence,
        "music": music,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silence", required=True)
    parser.add_argument("--music", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        silence = parse_row(Path(args.silence).read_text(encoding="utf-8"))
        music = parse_row(Path(args.music).read_text(encoding="utf-8"))
        result = evaluate(silence, music)
    except (OSError, ValueError) as exc:
        result = {"result": "RED", "failures": [str(exc)]}
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
