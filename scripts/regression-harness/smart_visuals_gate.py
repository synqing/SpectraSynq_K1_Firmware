#!/usr/bin/env python3
"""Parse Smart Visual Engine runtime logs without touching hardware.

The parser consumes Captain-provided text logs and emits JSON summaries for
Smart Assist, EdgeMixer, and VPABB evidence. It does not open serial ports.
"""

import argparse
import json
import statistics
import sys


NUMERIC_KEYS = {
    "SMART_APPLIED_MODE",
    "SMART_LAST_REQUESTED_MODE",
    "SMART_SWITCHES_IN_WINDOW",
    "SMART_LAST_REASON",
    "SMART_STATE",
    "SMART_INTENT_MODE",
    "SMART_INTENT_CONFIDENCE",
    "SMART_INTENT_WANTS_SWITCH",
    "SMART_SCALAR_PHOTONS",
    "SMART_SCALAR_CHROMA",
    "SMART_SCALAR_MOOD",
    "SMART_SCALAR_SATURATION",
    "SMART_PALETTE_OVERLAY",
    "SMART_PALETTE_INDEX",
    "SMART_AUTO_COLOUR_SHIFT",
    "SMART_MIN_DWELL_MS",
    "SMART_COOLDOWN_MS",
    "SMART_SWITCH_WINDOW_MS",
    "SMART_MAX_SWITCHES",
    "SMART_AUDIO_NOVELTY",
    "SMART_AUDIO_ENERGY",
    "SMART_EVENT_ID",
    "SMART_EVENT_AGE_MS",
    "SMART_ONSET",
    "SMART_BASS_ONSET",
    "SMART_BEAT_CONFIDENCE",
    "EDGE_STRENGTH",
}


def _num(value):
    text = str(value).strip()
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        if any(ch in text for ch in (".", "e", "E")):
            return float(text)
        return int(text)
    except ValueError:
        return text


def _parse_key_values(parts):
    fields = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key.strip()] = _num(value.strip())
    return fields


def _summarise_values(values):
    clean = [value for value in values if isinstance(value, (int, float))]
    if not clean:
        return None
    return {
        "min": min(clean),
        "max": max(clean),
        "mean": statistics.fmean(clean),
    }


def _percent_delta(before, after):
    if before is None or after is None:
        return None
    if abs(before) < 0.000001:
        return 0.0 if abs(after) < 0.000001 else 100.0
    return ((after - before) / before) * 100.0


def _status_value(value):
    value = value.strip()
    if value in {"on", "off"}:
        return value
    if value in {"true", "false"}:
        return value == "true"
    return _num(value)


def parse_text(text):
    current_leg = "unlabelled"
    records = []
    smart_status = []
    edge_status = []
    vpab_record_status = []
    ignored = 0

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#LEG "):
            current_leg = line.split(" ", 1)[1].strip()
            continue
        if line.startswith("SMART_") and ":" in line:
            key, value = line.split(":", 1)
            smart_status.append({"line": line_no, key.strip(): _status_value(value)})
            continue
        if line.startswith("EDGE_") and ":" in line:
            key, value = line.split(":", 1)
            edge_status.append({"line": line_no, key.strip(): _status_value(value)})
            continue
        if line.startswith("VPAB_RECORDS:"):
            fields = _parse_key_values(line[len("VPAB_RECORDS:"):].strip().split())
            fields["line"] = line_no
            vpab_record_status.append(fields)
            continue
        if line.startswith("VPABB,"):
            fields = _parse_key_values(line.split(",")[1:])
            fields["line"] = line_no
            fields["leg"] = current_leg
            records.append(fields)
            continue
        ignored += 1

    return {
        "records": records,
        "smart_status": smart_status,
        "edge_status": edge_status,
        "vpab_record_status": vpab_record_status,
        "ignored_lines": ignored,
    }


def _merge_status_tail(rows, prefix, limit):
    merged = []
    current = {}
    for row in rows:
        for key, value in row.items():
            if key == "line":
                continue
            if key.startswith(prefix):
                current[key] = value
                if key in {"SMART_BEAT_CONFIDENCE", "EDGE_STRENGTH"}:
                    merged.append(dict(current))
    if not merged and current:
        merged.append(current)
    return merged[-limit:]


def _group_records(records):
    groups = {}
    for row in records:
        key = "%s/%s" % (row.get("leg", "unlabelled"), row.get("channel", "unknown"))
        groups.setdefault(key, []).append(row)

    summary = {}
    for key, rows in sorted(groups.items()):
        rgb_sums = []
        for row in rows:
            r_sum = row.get("r_sum", 0)
            g_sum = row.get("g_sum", 0)
            b_sum = row.get("b_sum", 0)
            if all(isinstance(value, (int, float)) for value in (r_sum, g_sum, b_sum)):
                rgb_sums.append(r_sum + g_sum + b_sum)
        summary[key] = {
            "rows": len(rows),
            "modes": sorted({str(row.get("mode")) for row in rows if "mode" in row}),
            "energy": _summarise_values(row.get("energy") for row in rows),
            "rgb_sum": _summarise_values(rgb_sums),
            "nonzero_led_pct": _summarise_values(row.get("nonzero_led_pct") for row in rows),
            "com": _summarise_values(row.get("com") for row in rows),
            "over_max": max((row.get("over", 0) for row in rows), default=0),
            "dropped_max": max((row.get("dropped", 0) for row in rows), default=0),
        }
    return summary


def _mean(summary, group, metric):
    payload = summary.get(group, {}).get(metric)
    if not payload:
        return None
    return payload.get("mean")


def _edge_materiality(groups):
    baseline_secondary = "baseline_features_off/secondary"
    edge_secondary = "edge_complementary_strength_1/secondary"
    baseline_primary = "baseline_features_off/primary"
    edge_primary = "edge_complementary_strength_1/primary"

    base_secondary_energy = _mean(groups, baseline_secondary, "energy")
    edge_secondary_energy = _mean(groups, edge_secondary, "energy")
    base_secondary_rgb = _mean(groups, baseline_secondary, "rgb_sum")
    edge_secondary_rgb = _mean(groups, edge_secondary, "rgb_sum")
    base_primary_rgb = _mean(groups, baseline_primary, "rgb_sum")
    edge_primary_rgb = _mean(groups, edge_primary, "rgb_sum")

    return {
        "baseline_found": baseline_secondary in groups,
        "edge_found": edge_secondary in groups,
        "secondary_energy_delta_pct": _percent_delta(base_secondary_energy, edge_secondary_energy),
        "secondary_rgb_sum_delta_pct": _percent_delta(base_secondary_rgb, edge_secondary_rgb),
        "primary_rgb_sum_delta_pct": _percent_delta(base_primary_rgb, edge_primary_rgb),
    }


def summarise_text(text):
    parsed = parse_text(text)
    groups = _group_records(parsed["records"])
    return {
        "records_total": len(parsed["records"]),
        "ignored_lines": parsed["ignored_lines"],
        "vpabb_groups": groups,
        "smart_status_tail": _merge_status_tail(parsed["smart_status"], "SMART_", 32),
        "edge_status_tail": _merge_status_tail(parsed["edge_status"], "EDGE_", 16),
        "vpab_record_status": parsed["vpab_record_status"],
        "edge_materiality": _edge_materiality(groups),
    }


def gate_summary(summary, strict=False):
    issues = []
    if summary["records_total"] == 0:
        issues.append({"severity": "fail", "message": "no VPABB records parsed"})
    if strict:
        for row in summary["vpab_record_status"]:
            if row.get("dropped", 0):
                issues.append({"severity": "fail", "message": "VPAB_RECORDS dropped rows", "line": row.get("line")})
            if row.get("overflowed", 0):
                issues.append({"severity": "fail", "message": "VPAB_RECORDS overflowed", "line": row.get("line")})
        materiality = summary["edge_materiality"]
        if not materiality["baseline_found"] or not materiality["edge_found"]:
            issues.append({"severity": "fail", "message": "missing baseline or edge leg for materiality"})
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("log_path")
    parser.add_argument("--out")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    try:
        with open(args.log_path, "r", encoding="utf-8", errors="replace") as handle:
            summary = summarise_text(handle.read())
    except OSError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    summary["issues"] = gate_summary(summary, strict=args.strict)
    payload = json.dumps(summary, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
    print(payload)
    return 2 if any(issue["severity"] == "fail" for issue in summary["issues"]) else 0


if __name__ == "__main__":
    sys.exit(main())
