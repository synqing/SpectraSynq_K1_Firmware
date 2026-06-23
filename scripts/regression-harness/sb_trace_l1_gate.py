#!/usr/bin/env python3
"""Summarise L1 Accent trace-dev timing evidence."""

import argparse
import json
import statistics
import sys


TRACE_SCOPE_NAMES = (
    "vp_bus_read",
    "vp_visual_hooks_tick",
)

COUNTER_NAMES = (
    "vp_primary_render_us",
    "vp_secondary_render_us",
)


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    idx = max(0, min(idx, len(ordered) - 1))
    return ordered[idx]


def summarise(values):
    if not values:
        return {
            "count": 0,
            "min": None,
            "mean": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    return {
        "count": len(values),
        "min": min(values),
        "mean": statistics.fmean(values),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": max(values),
    }


def analyse(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    events = payload.get("traceEvents", [])
    scopes = {name: [] for name in TRACE_SCOPE_NAMES}
    counters = {name: [] for name in COUNTER_NAMES}

    for event in events:
        name = event.get("name")
        phase = event.get("ph")
        if name in scopes and phase == "X":
            dur = event.get("dur")
            if isinstance(dur, (int, float)):
                scopes[name].append(float(dur))
        elif name in counters and phase == "C":
            value = event.get("args", {}).get("value")
            if isinstance(value, (int, float)):
                counters[name].append(float(value))

    summary = {
        "trace_events": len(events),
        "scopes_us": {name: summarise(values) for name, values in scopes.items()},
        "counters_us": {name: summarise(values) for name, values in counters.items()},
        "pass": True,
        "issues": [],
    }

    bus = summary["scopes_us"]["vp_bus_read"]
    hooks = summary["scopes_us"]["vp_visual_hooks_tick"]
    if bus["count"] == 0:
        summary["pass"] = False
        summary["issues"].append("missing vp_bus_read trace scope")
    elif bus["p99"] is not None and bus["p99"] > 100.0:
        summary["pass"] = False
        summary["issues"].append("vp_bus_read p99 exceeds 100us")

    if hooks["count"] == 0:
        summary["pass"] = False
        summary["issues"].append("missing vp_visual_hooks_tick trace scope")
    elif hooks["p99"] is not None and hooks["p99"] > 50.0:
        summary["pass"] = False
        summary["issues"].append("vp_visual_hooks_tick p99 exceeds 50us")

    return summary


def compare_against_baseline(summary, baseline, hook_p99_widening_threshold):
    summary["baseline_scopes_us"] = baseline.get("scopes_us", {})
    summary["comparisons"] = {}

    hooks = summary["scopes_us"]["vp_visual_hooks_tick"]
    baseline_hooks = baseline["scopes_us"]["vp_visual_hooks_tick"]
    hooks_p99 = hooks["p99"]
    baseline_hooks_p99 = baseline_hooks["p99"]

    if baseline_hooks["count"] == 0:
        summary["pass"] = False
        summary["issues"].append("baseline missing vp_visual_hooks_tick trace scope")
        return summary

    if hooks_p99 is None or baseline_hooks_p99 in (None, 0):
        summary["pass"] = False
        summary["issues"].append("cannot compare vp_visual_hooks_tick p99 against baseline")
        return summary

    widening_pct = ((hooks_p99 - baseline_hooks_p99) / baseline_hooks_p99) * 100.0
    summary["comparisons"]["vp_visual_hooks_tick_p99_widening_pct"] = widening_pct
    summary["comparisons"]["vp_visual_hooks_tick_p99_widening_threshold_pct"] = hook_p99_widening_threshold
    if widening_pct > hook_p99_widening_threshold:
        summary["pass"] = False
        summary["issues"].append(
            "vp_visual_hooks_tick p99 widened %.2f%% vs baseline (threshold %.2f%%)"
            % (widening_pct, hook_p99_widening_threshold)
        )
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_json")
    parser.add_argument("--baseline")
    parser.add_argument("--hook-p99-widening-threshold", type=float, default=10.0)
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    summary = analyse(args.trace_json)
    if args.baseline:
        baseline = analyse(args.baseline)
        before = list(summary["issues"])
        summary["issues"] = [
            issue for issue in summary["issues"]
            if issue != "vp_visual_hooks_tick p99 exceeds 50us"
        ]
        summary["pass"] = not summary["issues"]
        summary = compare_against_baseline(summary, baseline, args.hook_p99_widening_threshold)
        if before != summary["issues"]:
            summary["comparisons"]["absolute_hook_p99_gate_replaced_by_baseline"] = True
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    print(text)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
