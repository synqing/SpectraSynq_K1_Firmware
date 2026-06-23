#!/usr/bin/env python3
"""Summarise SMART onset/beat event evidence from captured logs.

The parser is intentionally file-only. It never opens serial ports; Captain or
another capture tool supplies the log, then this script validates the SMART
event surface used by the OnsetDetector/BeatTracker-lite lane.
"""

import argparse
import json
import math
import statistics
import sys


REQUIRED_FIELDS = (
    "SMART_EVENT_ID",
    "SMART_EVENT_AGE_MS",
    "SMART_ONSET",
    "SMART_BASS_ONSET",
    "SMART_BEAT_CONFIDENCE",
)

EVENT_STORM_THRESHOLD_EVENTS_PER_MIN = 240.0


def _parse_number(text):
    value = text.strip()
    try:
        if any(ch in value for ch in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_vpabb_time_ms(line):
    if not line.startswith("VPABB,"):
        return None
    for part in line.split(",")[1:]:
        if part.startswith("t_ms="):
            try:
                return int(float(part.split("=", 1)[1]))
            except ValueError:
                return None
    return None


def _parse_capture_time_ms(line):
    if not line.startswith("#TS_MS "):
        return None
    try:
        return int(float(line.split(" ", 1)[1]))
    except ValueError:
        return None


def _percentile(values, percentile):
    if not values:
        return None
    ordered = sorted(values)
    index = int(math.ceil((percentile / 100.0) * len(ordered))) - 1
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def _summarise_values(values):
    clean = [value for value in values if isinstance(value, (int, float))]
    if not clean:
        return None
    return {
        "min": min(clean),
        "max": max(clean),
        "mean": statistics.fmean(clean),
        "p50": _percentile(clean, 50),
        "p95": _percentile(clean, 95),
    }


def _complete_snapshot(snapshot):
    return all(field in snapshot for field in REQUIRED_FIELDS)


def _missing_fields(snapshot):
    return [field for field in REQUIRED_FIELDS if field not in snapshot]


def _finalise_snapshot(snapshot, snapshots, missing_snapshots):
    if not snapshot:
        return
    missing = _missing_fields(snapshot)
    if missing:
        missing_snapshots.append({
            "line": snapshot.get("line"),
            "leg": snapshot.get("leg", "unlabelled"),
            "missing": missing,
        })
        return
    snapshots.append(dict(snapshot))


def parse_text(text):
    snapshots = []
    missing_snapshots = []
    vpabb_times = []
    current_leg = "unlabelled"
    current = {}
    smart_seen = False

    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#LEG "):
            _finalise_snapshot(current, snapshots, missing_snapshots)
            current = {}
            smart_seen = False
            current_leg = line.split(" ", 1)[1].strip()
            continue

        t_ms = _parse_capture_time_ms(line)
        if t_ms is None:
            t_ms = _parse_vpabb_time_ms(line)
        if t_ms is not None:
            vpabb_times.append(t_ms)
            continue

        if line in {"sbr{{", "{{"}:
            _finalise_snapshot(current, snapshots, missing_snapshots)
            current = {}
            smart_seen = False
            continue
        if line == "}}":
            _finalise_snapshot(current, snapshots, missing_snapshots)
            current = {}
            smart_seen = False
            continue

        if not line.startswith("SMART_") or ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        if key in REQUIRED_FIELDS and key in current:
            _finalise_snapshot(current, snapshots, missing_snapshots)
            current = {}
            smart_seen = False

        if not smart_seen:
            current = {"line": line_no, "leg": current_leg}
            smart_seen = True
        current[key] = _parse_number(value)

        if _complete_snapshot(current):
            _finalise_snapshot(current, snapshots, missing_snapshots)
            current = {}
            smart_seen = False

    _finalise_snapshot(current, snapshots, missing_snapshots)
    return {
        "snapshots": snapshots,
        "snapshots_with_missing_required_fields": missing_snapshots,
        "vpabb_times_ms": vpabb_times,
    }


def summarise_text(text):
    parsed = parse_text(text)
    snapshots = parsed["snapshots"]
    missing_snapshots = parsed["snapshots_with_missing_required_fields"]
    ids = [row["SMART_EVENT_ID"] for row in snapshots if isinstance(row.get("SMART_EVENT_ID"), int)]
    event_count_delta = max(ids) - min(ids) if ids else 0
    observed_event_snapshots = [row for row in snapshots if row.get("SMART_EVENT_ID", 0) > 0]

    times = parsed["vpabb_times_ms"]
    duration_ms = (max(times) - min(times)) if len(times) >= 2 else None
    events_per_min = None
    if duration_ms and duration_ms > 0:
        events_per_min = (event_count_delta * 60000.0) / duration_ms

    silence_or_control = [
        row for row in observed_event_snapshots
        if "silence" in row.get("leg", "") or "control" in row.get("leg", "")
    ]
    false_by_window = {}
    for row in silence_or_control:
        leg = row.get("leg", "unlabelled")
        false_by_window[leg] = false_by_window.get(leg, 0) + 1

    missing_required = []
    for row in missing_snapshots:
        for field in row["missing"]:
            if field not in missing_required:
                missing_required.append(field)

    invalidation_reasons = []
    if missing_snapshots:
        invalidation_reasons.append("missing required SMART fields")

    event_storm_triggered = (
        events_per_min is not None and
        events_per_min > EVENT_STORM_THRESHOLD_EVENTS_PER_MIN
    )

    return {
        "capture_valid": not invalidation_reasons,
        "invalidation_reasons": invalidation_reasons,
        "snapshot_count": len(snapshots),
        "event_count_delta": event_count_delta,
        "observed_event_snapshots": len(observed_event_snapshots),
        "events_per_min": events_per_min,
        "event_age_ms": _summarise_values(row.get("SMART_EVENT_AGE_MS") for row in observed_event_snapshots),
        "beat_confidence": _summarise_values(row.get("SMART_BEAT_CONFIDENCE") for row in observed_event_snapshots),
        "false_events": {
            "windows_present": bool(silence_or_control),
            "count": len(silence_or_control),
            "by_window": false_by_window,
        },
        "event_storm": {
            "triggered": event_storm_triggered,
            "threshold_events_per_min": EVENT_STORM_THRESHOLD_EVENTS_PER_MIN,
        },
        "missing_required_fields": missing_required,
        "snapshots_with_missing_required_fields": missing_snapshots,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", help="Captured SMART/runtime log to analyse")
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args(argv)

    with open(args.log, "r", encoding="utf-8", errors="replace") as handle:
        summary = summarise_text(handle.read())

    payload = json.dumps(summary, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
    else:
        print(payload)

    return 0 if summary["capture_valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
