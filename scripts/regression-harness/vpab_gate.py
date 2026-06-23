#!/usr/bin/env python3
"""vpab_gate.py - parse and gate VPAB final-byte A/B probe packets.

Parses log lines shaped like:

  VPAB,ver=1,mode=7,channel=primary,scenario=self_shadow,frame=42,...

The gate is intentionally offline-only: it consumes captured text, emits JSON,
and has no serial, upload, or network dependency.

Exit: 0 = parsed and passed | 2 = parsed but invalid/failed | 1 = usage/I/O error
"""
import argparse
import json
import sys


MANDATORY_FIELDS = (
    "ver",
    "mode",
    "channel",
    "scenario",
    "frame",
    "mae8",
    "p95_abs8",
    "max_abs8",
    "changed_led_pct",
    "energy_a",
    "energy_b",
    "energy_delta_pct",
    "com_a",
    "com_b",
    "com_delta_leds",
    "com_slope_delta_pct",
)

INT_FIELDS = {
    "ver",
    "mode",
    "frame",
    "seed",
    "event_id",
    "heap",
    "leds",
    "truncated",
    "dither_step",
    "fastled_dither",
    "over",
    "dropped",
}

NUMERIC_FIELDS = {
    "mae8",
    "p95_abs8",
    "max_abs8",
    "changed_led_pct",
    "changed_channel_pct",
    "energy_a",
    "energy_b",
    "energy_delta_pct",
    "com_a",
    "com_b",
    "com_delta_leds",
    "com_slope_delta_pct",
    "trail_half_a",
    "trail_half_b",
    "trail_half_life_delta_frames",
    "tail_integral_delta_pct",
    "hue_delta_p95",
    "sat_delta_p95",
    "white_bias_score",
    "flicker_score",
    "t_ms",
    "dt_ms",
    "render_us",
    "quant_us",
    "show_us",
    "frame_us",
}

OPTIONAL_NUMERIC_FIELDS = NUMERIC_FIELDS | INT_FIELDS

LEVEL1_THRESHOLDS = {
    "mae8": 0.5,
    "p95_abs8": 1.0,
    "max_abs8": 8.0,
    "changed_led_pct": 2.0,
    "changed_channel_pct": 2.0,
    "com_delta_leds": 1.0,
    "trail_delta_frames": 2.0,
    "tail_integral_delta_pct_abs": 10.0,
    # Project runtime safety ceilings supplied with the K1 operating rules.
    "render_us": 2000.0,
    "frame_us": 8333.33,
    "over": 0,
    "dropped": 0,
}

VALID_CHANNELS = {"primary", "secondary"}
DIAG_SUMMARY_PREFIXES = ("VPAB_RECORDS:", "VPAB_DUMP:")


def _num(value):
    text = str(value).strip()
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        if any(ch in text for ch in (".", "e", "E")):
            return float(text)
        return int(text)
    except ValueError:
        return value


def _issue(line, field, message, value=None):
    out = {"line": line, "field": field, "message": message}
    if value is not None:
        out["value"] = value
    return out


def parse_vpab_line(line, line_no=0):
    raw = line.strip()
    parts = [part.strip() for part in raw.split(",")]
    if not parts or parts[0] != "VPAB":
        raise ValueError("not a VPAB line")

    fields = {}
    issues = []
    for part in parts[1:]:
        if not part:
            continue
        if "=" not in part:
            issues.append(_issue(line_no, None, "token without key=value", part))
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in fields:
            issues.append(_issue(line_no, key, "duplicate field", value))
            continue
        fields[key] = _num(value)

    return {"tag": "VPAB", "line": line_no, "raw": raw, "fields": fields, "issues": issues}


def parse_diag_summary_line(line, line_no=0):
    raw = line.strip()
    if raw.startswith("VPAB_RECORDS:"):
        tag = "VPAB_RECORDS"
        body = raw[len("VPAB_RECORDS:"):].strip()
    elif raw.startswith("VPAB_DUMP:"):
        tag = "VPAB_DUMP"
        body = raw[len("VPAB_DUMP:"):].strip()
    else:
        raise ValueError("not a VPAB diagnostic summary")

    fields = {}
    issues = []
    for part in body.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in fields:
            issues.append(_issue(line_no, key, "duplicate diagnostic summary field", value))
            continue
        fields[key] = _num(value)
    return {"tag": tag, "line": line_no, "raw": raw, "fields": fields, "issues": issues}


def parse_text(text):
    records = []
    diag_summaries = []
    ignored = 0
    issues = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(DIAG_SUMMARY_PREFIXES):
            try:
                summary = parse_diag_summary_line(line, line_no)
            except ValueError as exc:
                issues.append(_issue(line_no, None, str(exc), line))
                continue
            diag_summaries.append(summary)
            issues.extend(summary["issues"])
            continue
        if not line.startswith("VPAB,"):
            ignored += 1
            continue
        try:
            record = parse_vpab_line(line, line_no)
        except ValueError as exc:
            issues.append(_issue(line_no, None, str(exc), line))
            continue
        records.append(record)
        issues.extend(record["issues"])
    return records, diag_summaries, ignored, issues


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_record(record, strict_memory=False, allow_self_shadow_smoke=False):
    fields = record["fields"]
    issues = []
    warnings = []
    line = record["line"]

    for field in MANDATORY_FIELDS:
        if field not in fields:
            issues.append(_issue(line, field, "missing mandatory field %s" % field))

    for field, value in fields.items():
        if field in OPTIONAL_NUMERIC_FIELDS and not _is_number(value):
            issues.append(_issue(line, field, "field must be numeric", value))

    if fields.get("ver") != 1:
        issues.append(_issue(line, "ver", "unsupported VPAB version; expected 1", fields.get("ver")))

    if "channel" in fields and fields["channel"] not in VALID_CHANNELS:
        issues.append(_issue(line, "channel", "channel must be primary or secondary", fields["channel"]))

    for pct_field in ("changed_led_pct", "changed_channel_pct"):
        if pct_field in fields and _is_number(fields[pct_field]):
            if fields[pct_field] < 0 or fields[pct_field] > 100:
                issues.append(_issue(line, pct_field, "percentage must be within 0..100", fields[pct_field]))

    if "trail_half_a" in fields or "trail_half_b" in fields:
        if "trail_half_a" not in fields or "trail_half_b" not in fields:
            issues.append(_issue(line, "trail_half", "trail_half_a and trail_half_b must be paired"))

    has_trail = (
        "trail_half_life_delta_frames" in fields
        or ("trail_half_a" in fields and "trail_half_b" in fields)
    )
    has_tail = "tail_integral_delta_pct" in fields
    memory_marker = str(fields.get("memory_metrics", "")).lower()
    is_self_shadow = (
        str(fields.get("shadow", "")).lower() == "self"
        or str(fields.get("scenario", "")).lower() == "self_shadow"
    )
    if not allow_self_shadow_smoke and (is_self_shadow or memory_marker in {"absent", "placeholder"}):
        issues.append(_issue(line, "memory_metrics", "self-shadow or absent memory metrics are instrumentation smoke, not visual-memory proof", fields.get("memory_metrics")))
    if strict_memory and memory_marker in {"absent", "placeholder"}:
        issues.append(_issue(line, "memory_metrics", "strict memory gate rejects absent/placeholder memory metrics", fields.get("memory_metrics")))
    if strict_memory and not has_trail:
        issues.append(_issue(line, "trail_half_life_delta_frames", "strict memory gate requires trail delta"))
    elif not has_trail:
        warnings.append(_issue(line, "trail_half_life_delta_frames", "trail delta absent; memory threshold not evaluated"))

    if strict_memory and not has_tail:
        issues.append(_issue(line, "tail_integral_delta_pct", "strict memory gate requires tail integral delta"))
    elif not has_tail:
        warnings.append(_issue(line, "tail_integral_delta_pct", "tail integral delta absent; memory threshold not evaluated"))

    return issues, warnings


def _failure(record, metric, observed, threshold, message):
    return {
        "line": record["line"],
        "frame": record["fields"].get("frame"),
        "mode": record["fields"].get("mode"),
        "channel": record["fields"].get("channel"),
        "scenario": record["fields"].get("scenario"),
        "metric": metric,
        "observed": observed,
        "threshold": threshold,
        "message": message,
    }


def _derived_metrics(fields):
    derived = {}
    if "trail_half_life_delta_frames" in fields:
        derived["trail_delta_frames"] = abs(fields["trail_half_life_delta_frames"])
    elif "trail_half_a" in fields and "trail_half_b" in fields:
        if _is_number(fields["trail_half_a"]) and _is_number(fields["trail_half_b"]):
            derived["trail_delta_frames"] = abs(fields["trail_half_a"] - fields["trail_half_b"])
    return derived


def _gate_record(record):
    fields = record["fields"]
    failures = []
    derived = _derived_metrics(fields)

    for metric in ("mae8", "p95_abs8", "max_abs8", "changed_led_pct", "changed_channel_pct", "com_delta_leds"):
        if metric in fields and _is_number(fields[metric]):
            threshold = LEVEL1_THRESHOLDS[metric]
            if abs(fields[metric]) > threshold:
                failures.append(
                    _failure(
                        record,
                        metric,
                        fields[metric],
                        "<= %s" % threshold,
                        "%s exceeds Level 1 threshold" % metric,
                    )
                )

    if "trail_delta_frames" in derived:
        threshold = LEVEL1_THRESHOLDS["trail_delta_frames"]
        if derived["trail_delta_frames"] > threshold:
            failures.append(
                _failure(
                    record,
                    "trail_delta_frames",
                    derived["trail_delta_frames"],
                    "<= %s" % threshold,
                    "trail half-life delta exceeds Level 1 threshold",
                )
            )

    if "tail_integral_delta_pct" in fields and _is_number(fields["tail_integral_delta_pct"]):
        threshold = LEVEL1_THRESHOLDS["tail_integral_delta_pct_abs"]
        observed = abs(fields["tail_integral_delta_pct"])
        if observed > threshold:
            failures.append(
                _failure(
                    record,
                    "tail_integral_delta_pct",
                    fields["tail_integral_delta_pct"],
                    "abs <= %s" % threshold,
                    "tail integral delta exceeds Level 1 threshold",
                )
            )

    for metric in ("frame_us",):
        if metric in fields and _is_number(fields[metric]):
            threshold = LEVEL1_THRESHOLDS[metric]
            if fields[metric] > threshold:
                failures.append(
                    _failure(
                        record,
                        metric,
                        fields[metric],
                        "<= %s" % threshold,
                        "%s exceeds K1 runtime ceiling" % metric,
                    )
                )

    for metric in ("over", "dropped"):
        if metric in fields and _is_number(fields[metric]):
            threshold = LEVEL1_THRESHOLDS[metric]
            if fields[metric] != threshold:
                failures.append(
                    _failure(
                        record,
                        metric,
                        fields[metric],
                        "== %s" % threshold,
                        "%s must remain zero" % metric,
                    )
                )

    return failures, derived


def _gate_render_budget_record(record):
    fields = record["fields"]
    failures = []
    metric = "render_us"
    if metric in fields and _is_number(fields[metric]):
        threshold = LEVEL1_THRESHOLDS[metric]
        if fields[metric] > threshold:
            failures.append(
                _failure(
                    record,
                    metric,
                    fields[metric],
                    "<= %s" % threshold,
                    "%s exceeds K1 render-budget ceiling" % metric,
                )
            )
    return failures


def _gate_diag_summaries(diag_summaries):
    failures = []
    for summary in diag_summaries:
        fields = summary["fields"]
        for metric in ("dropped", "corrupt", "overflowed"):
            if metric in fields and _is_number(fields[metric]) and fields[metric] != 0:
                failures.append(
                    {
                        "line": summary["line"],
                        "frame": None,
                        "mode": None,
                        "channel": None,
                        "scenario": summary["tag"],
                        "metric": "diag_%s" % metric,
                        "observed": fields[metric],
                        "threshold": "== 0",
                        "message": "%s must remain zero in diagnostic capture summary" % metric,
                    }
                )
    return failures


def evaluate_records(records, diag_summaries=None, ignored_lines=0, parse_issues=None,
                     strict_memory=False, allow_self_shadow_smoke=False,
                     strict_render_budget=False):
    diag_summaries = diag_summaries or []
    parse_issues = parse_issues or []
    issues = list(parse_issues)
    warnings = []
    diag_failures = _gate_diag_summaries(diag_summaries)
    failures = list(diag_failures)
    visual_failures = []
    render_budget_failures = []
    out_records = []
    passed_records = 0
    visual_passed_records = 0

    if not records:
        issues.append(_issue(0, None, "no VPAB records found"))

    for record in records:
        validation_issues, validation_warnings = _validate_record(
            record,
            strict_memory=strict_memory,
            allow_self_shadow_smoke=allow_self_shadow_smoke,
        )
        issues.extend(validation_issues)
        warnings.extend(validation_warnings)
        record_failures, derived = _gate_record(record)
        record_render_failures = _gate_render_budget_record(record)
        failures.extend(record_failures)
        visual_failures.extend(record_failures)
        render_budget_failures.extend(record_render_failures)
        if strict_render_budget:
            failures.extend(record_render_failures)
        visual_passed = not validation_issues and not record_failures
        passed = visual_passed and (not strict_render_budget or not record_render_failures)
        if visual_passed:
            visual_passed_records += 1
        if passed:
            passed_records += 1
        out_records.append(
            {
                "line": record["line"],
                "fields": record["fields"],
                "derived": derived,
                "status": "PASS" if passed else "FAIL",
                "visual_status": "PASS" if visual_passed else "FAIL",
                "issues": validation_issues,
                "warnings": validation_warnings,
                "failures": record_failures,
                "render_budget_failures": record_render_failures,
            }
        )

    valid = len(issues) == 0
    passed = valid and len(failures) == 0
    result = "PASS" if passed else "FAIL"
    summary = (
        "VPAB gate %s: %d/%d records passed; %d issue(s); %d failure(s); %d warning(s)"
        % (result, passed_records, len(records), len(issues), len(failures), len(warnings))
    )
    render_budget_passed = len(render_budget_failures) == 0
    render_budget_status = "PASS" if render_budget_passed else ("FAIL" if strict_render_budget else "WARN")

    return {
        "schema": "vpab_gate.v1",
        "result": result,
        "valid": valid,
        "passed": passed,
        "summary": summary,
        "thresholds": LEVEL1_THRESHOLDS,
        "visual_gate": {
            "passed": valid and len(visual_failures) == 0,
            "passed_records": visual_passed_records,
            "total_records": len(records),
            "failures": visual_failures,
        },
        "diagnostic_capture": {
            "passed": len(diag_failures) == 0,
            "failures": diag_failures,
        },
        "render_budget": {
            "status": render_budget_status,
            "passed": render_budget_passed,
            "strict": strict_render_budget,
            "failures": render_budget_failures,
        },
        "counts": {
            "vpab_records": len(records),
            "passed_records": passed_records,
            "visual_passed_records": visual_passed_records,
            "ignored_lines": ignored_lines,
            "issues": len(issues),
            "failures": len(failures),
            "warnings": len(warnings),
            "diag_summaries": len(diag_summaries),
            "render_budget_failures": len(render_budget_failures),
        },
        "issues": issues,
        "failures": failures,
        "warnings": warnings,
        "diag_summaries": diag_summaries,
        "records": out_records,
    }


def evaluate_text(text, strict_memory=False, allow_self_shadow_smoke=False,
                  strict_render_budget=False):
    records, diag_summaries, ignored, issues = parse_text(text)
    return evaluate_records(
        records,
        diag_summaries=diag_summaries,
        ignored_lines=ignored,
        parse_issues=issues,
        strict_memory=strict_memory,
        allow_self_shadow_smoke=allow_self_shadow_smoke,
        strict_render_budget=strict_render_budget,
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("log", help="VPAB log path, or - for stdin")
    parser.add_argument("--out", help="write JSON result to this path")
    parser.add_argument("--summary", action="store_true", help="also print one-line summary to stderr")
    parser.add_argument("--strict-memory", action="store_true", help="require trail and tail metrics on every row")
    parser.add_argument("--strict-render-budget", action="store_true",
                        help="make render_us budget breaches fail the overall gate instead of reporting WARN")
    parser.add_argument("--allow-self-shadow-smoke", action="store_true",
                        help="allow self-shadow/absent-memory rows to pass as instrumentation smoke only")
    args = parser.parse_args(argv)

    try:
        if args.log == "-":
            text = sys.stdin.read()
        else:
            with open(args.log, "r", errors="replace") as handle:
                text = handle.read()
    except OSError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    result = evaluate_text(
        text,
        strict_memory=args.strict_memory,
        allow_self_shadow_smoke=args.allow_self_shadow_smoke,
        strict_render_budget=args.strict_render_budget,
    )
    output = json.dumps(result, indent=2, sort_keys=True)

    if args.out:
        try:
            with open(args.out, "w") as handle:
                handle.write(output)
                handle.write("\n")
        except OSError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
        print("wrote %s" % args.out, file=sys.stderr)
    else:
        print(output)

    if args.summary:
        print(result["summary"], file=sys.stderr)
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
