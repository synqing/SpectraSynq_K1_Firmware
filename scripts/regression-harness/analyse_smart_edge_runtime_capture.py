#!/usr/bin/env python3
"""Summarise Smart/Edge K1 runtime capture logs."""

import argparse
import json
import re
import statistics
import sys


AP_RE = re.compile(
    r"\[AP\]\s+SSL=(?P<ssl>-?\d+)\s+DC=(?P<dc>-?\d+)\s+"
    r"max_raw=(?P<max_raw>-?[0-9.]+)\s+follower=(?P<follower>-?[0-9.]+)\s+"
    r"peak_scaled=(?P<peak_scaled>-?[0-9.]+)\s+silent_scale=(?P<silent_scale>-?[0-9.]+)\s+"
    r"silence=(?P<silence>[01])"
)

WHITE_FLOOD_WHITE_BIAS_MIN = 220.0
WHITE_FLOOD_SAT_AVG_MAX = 16.0
WHITE_FLOOD_NONZERO_PCT_MIN = 95.0
WHITE_FLOOD_ENERGY_MIN = 10000.0


def parse_fields(line):
    fields = {}
    for token in line.split(",")[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = value
    return fields


def as_float(fields, key):
    try:
        return float(fields[key])
    except (KeyError, ValueError):
        return None


def as_int(fields, key):
    try:
        return int(float(fields[key]))
    except (KeyError, ValueError):
        return None


def summarise_values(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def summarise_mode_counts(rows):
    counts = {}
    for row in rows:
        mode = row.get("mode")
        if not mode:
            continue
        counts[mode] = counts.get(mode, 0) + 1
    return dict(sorted(counts.items()))


def summary_mean(group, metric):
    values = group.get(metric)
    if not isinstance(values, dict):
        return None
    value = values.get("mean")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def evaluate_visual_safety(groups):
    failures = []
    for group_name, group in sorted(groups.items()):
        white_bias = summary_mean(group, "white_bias_avg")
        sat_avg = summary_mean(group, "sat_avg")
        nonzero = summary_mean(group, "nonzero_led_pct")
        energy = summary_mean(group, "energy")

        if (
            white_bias is not None and white_bias >= WHITE_FLOOD_WHITE_BIAS_MIN and
            sat_avg is not None and sat_avg <= WHITE_FLOOD_SAT_AVG_MAX and
            nonzero is not None and nonzero >= WHITE_FLOOD_NONZERO_PCT_MIN and
            energy is not None and energy >= WHITE_FLOOD_ENERGY_MIN
        ):
            failures.append({
                "group": group_name,
                "metric": "white_flood",
                "white_bias_avg_mean": white_bias,
                "sat_avg_mean": sat_avg,
                "nonzero_led_pct_mean": nonzero,
                "energy_mean": energy,
                "thresholds": {
                    "white_bias_avg_min": WHITE_FLOOD_WHITE_BIAS_MIN,
                    "sat_avg_max": WHITE_FLOOD_SAT_AVG_MAX,
                    "nonzero_led_pct_min": WHITE_FLOOD_NONZERO_PCT_MIN,
                    "energy_min": WHITE_FLOOD_ENERGY_MIN,
                },
            })
    return failures


def evaluate_smart_switch_path(groups):
    group_name = "smart_assist_low_floor_edge_on/primary"
    group = groups.get(group_name)
    if not group:
        return {
            "checked": False,
            "group": group_name,
            "switched": False,
            "reason": "missing_group",
        }

    modes = group.get("modes", [])
    mode_counts = group.get("mode_counts", {})
    switched_modes = [mode for mode in modes if mode != "3"]
    return {
        "checked": True,
        "group": group_name,
        "switched": bool(switched_modes),
        "modes": modes,
        "mode_counts": mode_counts,
        "switched_modes": switched_modes,
    }


def summarise_vpabb(path):
    current_leg = "unlabelled"
    groups = {}
    smart_status = []
    edge_status = []
    context_status = []
    diag_status = []

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("#LEG "):
                current_leg = line.split(" ", 1)[1]
                continue
            if line.startswith("SMART_"):
                smart_status.append(line)
                continue
            if line.startswith("EDGE_"):
                edge_status.append(line)
                continue
            if line.startswith("VPABC,"):
                context_status.append(parse_fields(line))
                continue
            if line.startswith("VPAB_RECORDS:"):
                diag_status.append(line)
                continue
            if not line.startswith("VPABB,"):
                continue

            fields = parse_fields(line)
            channel = fields.get("channel", "unknown")
            key = "%s/%s" % (current_leg, channel)
            groups.setdefault(key, []).append(fields)

    summary = {}
    for key, rows in sorted(groups.items()):
        hashes = [row.get("hash") for row in rows if row.get("hash")]
        modes = sorted(set(row.get("mode") for row in rows if row.get("mode")))
        summary[key] = {
            "rows": len(rows),
            "modes": modes,
            "mode_counts": summarise_mode_counts(rows),
            "unique_hashes": len(set(hashes)),
            "energy": summarise_values(as_float(row, "energy") for row in rows),
            "r_sum": summarise_values(as_float(row, "r_sum") for row in rows),
            "g_sum": summarise_values(as_float(row, "g_sum") for row in rows),
            "b_sum": summarise_values(as_float(row, "b_sum") for row in rows),
            "nonzero_led_pct": summarise_values(as_float(row, "nonzero_led_pct") for row in rows),
            "com": summarise_values(as_float(row, "com") for row in rows),
            "sat_avg": summarise_values(as_float(row, "sat_avg") for row in rows),
            "white_bias_avg": summarise_values(as_float(row, "white_bias_avg") for row in rows),
            "over_max": max(as_int(row, "over") or 0 for row in rows),
            "dropped_max": max(as_int(row, "dropped") or 0 for row in rows),
        }

    return {
        "vpabb_groups": summary,
        "smart_status_tail": smart_status[-32:],
        "edge_status_tail": edge_status[-16:],
        "vpab_context_tail": context_status[-8:],
        "vpab_record_status": diag_status,
    }


def summarise_production(path):
    ap_rows = []
    smart_status = []
    edge_status = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            match = AP_RE.search(line)
            if match:
                fields = match.groupdict()
                ap_rows.append({key: float(value) for key, value in fields.items()})
            elif line.startswith("SMART_"):
                smart_status.append(line)
            elif line.startswith("EDGE_"):
                edge_status.append(line)

    return {
        "ap_rows": len(ap_rows),
        "ap_max_raw": summarise_values(row["max_raw"] for row in ap_rows),
        "ap_follower": summarise_values(row["follower"] for row in ap_rows),
        "ap_peak_scaled": summarise_values(row["peak_scaled"] for row in ap_rows),
        "ap_silence_rows": int(sum(1 for row in ap_rows if row["silence"] >= 1.0)),
        "smart_status_tail": smart_status[-32:],
        "edge_status_tail": edge_status[-16:],
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("harness_log")
    parser.add_argument("production_log")
    parser.add_argument("out_json")
    args = parser.parse_args(argv)

    harness = summarise_vpabb(args.harness_log)
    harness["visual_safety_failures"] = evaluate_visual_safety(harness["vpabb_groups"])
    harness["smart_switch_path"] = evaluate_smart_switch_path(harness["vpabb_groups"])

    result = {
        "harness": harness,
        "production": summarise_production(args.production_log),
    }

    with open(args.out_json, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if harness["visual_safety_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
