#!/usr/bin/env python3
"""Evaluate gate0 `feature_latency_contracts` against a real device capture.

Why this exists
---------------
`docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json` carries
seven `budget_us: 25000` entries and one at `35000`. Before 2026-09-10 the Gate 0
runner referenced `ap_service_p99` eight times and `feature_latency_contracts`,
`budget_us`, `budget_formula`, `25000` and `35000` **zero** times. The budgets
were inert text: the RPL exceeded 25,000 us on its worst measured frame and
nothing noticed.

This gate reads the contract and measures against it. Three verdicts, never two:

    PASS            measured, inside budget
    FAIL            measured, over budget
    NOT_MEASURABLE  the capture does not contain the fields this budget needs

NOT_MEASURABLE is reported as loudly as FAIL and is non-zero exit by default.
A budget nothing can evaluate is the defect, not a pass. Every summary line
states the denominator: how many of the contract's budgets were actually
evaluated, not just how many passed.

Usage
-----
    python3 k1_feature_latency_gate.py --contract <contract.json> \
                                       --capture-dir <dir with apcad/k1rmt dumps>
    python3 k1_feature_latency_gate.py --self-test

Exit codes: 0 all evaluated budgets pass and none are unmeasurable;
1 at least one FAIL; 2 no FAIL but at least one NOT_MEASURABLE
(suppress with --allow-unmeasurable, which downgrades 2 to 0).
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import sys
import tempfile

# Contract origin/endpoint tokens this gate knows how to measure from a capture.
# Anything outside this map is honestly reported NOT_MEASURABLE rather than
# quietly skipped.
MEASURABLE = {
    ("newest_sample_estimate_us", "ap_publish_us"): "ap_leg",
    ("newest_sample_estimate_us", "rmt_complete_us_of_first_intended_visible_change"): "newest_to_complete",
    ("rmt_submit_us", "rmt_complete_us"): "wire",
}


def fields(line: str) -> dict:
    out = {}
    for kv in line.split(","):
        if "=" in kv:
            key, value = kv.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


def load_capture(capture_dir: str):
    """Return joined per-frame intervals from an apcad + k1rmt dump pair."""
    ap, rmt = [], []
    ap_path = os.path.join(capture_dir, "apcad_dump.txt")
    rmt_path = os.path.join(capture_dir, "k1rmt_dump.txt")
    if os.path.isfile(ap_path):
        with open(ap_path, errors="ignore") as handle:
            for line in handle:
                if line.startswith("APCAD,"):
                    f = fields(line)
                    if "newest_sample_estimate_us" in f and "ap_publish_us" in f:
                        ap.append((int(f["ap_publish_us"]),
                                   int(f["newest_sample_estimate_us"])))
    if os.path.isfile(rmt_path):
        with open(rmt_path, errors="ignore") as handle:
            for line in handle:
                if line.startswith("K1RMT,"):
                    f = fields(line)
                    if f.get("channel") == "0" and f.get("flags") == "1":
                        rmt.append((int(f["submit_us"]), int(f["complete_us"])))
    ap.sort()
    rmt.sort()

    series = {"ap_leg": [], "newest_to_complete": [], "wire": []}
    series["wire"] = [c - s for s, c in rmt]
    if ap and rmt:
        submits = [r[0] for r in rmt]
        lo, hi = rmt[0][0], rmt[-1][0]
        for publish, newest in ap:
            series["ap_leg"].append(publish - newest)
            if not lo <= publish <= hi:
                continue
            i = bisect.bisect_left(submits, publish)
            if i < len(rmt):
                series["newest_to_complete"].append(rmt[i][1] - newest)
    elif ap:
        series["ap_leg"] = [p - n for p, n in ap]
    return series


def evaluate(contract: dict, series: dict):
    """Return (rows, n_fail, n_unmeasurable). One row per contract budget."""
    rows = []
    for entry in contract.get("feature_latency_contracts", []):
        feature = entry.get("feature", "?")
        origin = entry.get("origin", "")
        endpoint = entry.get("endpoint", "")
        budget = entry.get("budget_us", entry.get("budget_p99_us"))
        key = MEASURABLE.get((origin, endpoint))

        if budget is None:
            rows.append((feature, entry.get("budget_formula", "formula"), None,
                         "NOT_MEASURABLE", "budget is a formula, not a fixed value"))
            continue
        if key is None:
            rows.append((feature, budget, None, "NOT_MEASURABLE",
                         "capture has no %s -> %s pair" % (origin or "?", endpoint or "?")))
            continue
        values = series.get(key) or []
        if not values:
            rows.append((feature, budget, None, "NOT_MEASURABLE",
                         "no samples for %s in this capture" % key))
            continue
        measured = pct(values, 0.99)
        verdict = "PASS" if measured <= budget else "FAIL"
        rows.append((feature, budget, measured, verdict,
                     "p99 over %d samples" % len(values)))

    n_fail = sum(1 for r in rows if r[3] == "FAIL")
    n_unmeasurable = sum(1 for r in rows if r[3] == "NOT_MEASURABLE")
    return rows, n_fail, n_unmeasurable


def report(rows, n_fail, n_unmeasurable) -> None:
    total = len(rows)
    evaluated = total - n_unmeasurable
    print("%-38s %10s %10s  %-15s %s"
          % ("FEATURE", "BUDGET", "p99", "VERDICT", "NOTE"))
    for feature, budget, measured, verdict, note in rows:
        print("%-38s %10s %10s  %-15s %s"
              % (feature[:38], budget, "-" if measured is None else measured,
                 verdict, note))
    print()
    print("COVERAGE: %d of %d contract budgets evaluated (%d not measurable)"
          % (evaluated, total, n_unmeasurable))
    print("RESULT:   %d pass, %d fail, %d not measurable"
          % (evaluated - n_fail, n_fail, n_unmeasurable))


# --------------------------------------------------------------------------
# Self-test: prove this gate can go RED, and go red for the RIGHT budget.
# A checker never seen to fail is not a checker.
# --------------------------------------------------------------------------
SELFTEST_CONTRACT = {
    "feature_latency_contracts": [
        {"feature": "ap_publication_freshness",
         "origin": "newest_sample_estimate_us",
         "endpoint": "ap_publish_us", "budget_p99_us": 8000},
        {"feature": "raw_peak_vu",
         "origin": "newest_sample_estimate_us",
         "endpoint": "rmt_complete_us_of_first_intended_visible_change",
         "budget_us": 25000},
        {"feature": "rmt_output",
         "origin": "rmt_submit_us", "endpoint": "rmt_complete_us",
         "budget_formula": "physical_wire_time_us+500"},
        {"feature": "tempo_beat_phase",
         "origin": "accepted_beat_or_phase_event_us",
         "endpoint": "rmt_complete_us_of_phase_aligned_output",
         "budget_us": 25000},
    ]
}


def _synth(tmp: str, ap_leg_us: int, wire_us: int, n: int = 40) -> str:
    """Write a synthetic capture with a chosen ap_leg and wire time."""
    os.makedirs(tmp, exist_ok=True)
    base = 1_000_000
    period = 7500
    with open(os.path.join(tmp, "apcad_dump.txt"), "w") as ap:
        for i in range(n):
            newest = base + i * period
            ap.write("APCAD,frame=%d,newest_sample_estimate_us=%d,"
                     "oldest_sample_estimate_us=%d,ap_publish_us=%d\n"
                     % (i, newest, newest - 7421, newest + ap_leg_us))
    with open(os.path.join(tmp, "k1rmt_dump.txt"), "w") as rmt:
        for i in range(n):
            submit = base + i * period + ap_leg_us + 200
            rmt.write("K1RMT,channel=0,seq=%d,vp_seq=%d,submit_us=%d,"
                      "complete_us=%d,duration_us=%d,payload_bytes=450,"
                      "num_symbols=3602,flags=1\n"
                      % (i + 1, i + 1, submit, submit + wire_us, wire_us))
    return tmp


def self_test() -> int:
    failures = []
    root = tempfile.mkdtemp(prefix="k1_flg_")

    # Case 1 — POSITIVE CONTROL. Healthy numbers: the two measurable fixed
    # budgets must both pass. If this goes red the harness is broken, not the
    # firmware.
    good = _synth(os.path.join(root, "good"), ap_leg_us=4700, wire_us=4600)
    rows, n_fail, n_unmeas = evaluate(SELFTEST_CONTRACT, load_capture(good))
    verdicts = {r[0]: r[3] for r in rows}
    if verdicts.get("ap_publication_freshness") != "PASS":
        failures.append("positive control: ap_publication_freshness not PASS")
    if verdicts.get("raw_peak_vu") != "PASS":
        failures.append("positive control: raw_peak_vu not PASS")
    if n_fail:
        failures.append("positive control produced %d FAIL" % n_fail)

    # Case 2 — MUTATION. Blow ONLY the AP leg past 8000 us. The AP budget must
    # go red and raw_peak_vu (still inside 25000) must stay green. A gate that
    # reddens everything is as useless as one that reddens nothing.
    bad_ap = _synth(os.path.join(root, "bad_ap"), ap_leg_us=9200, wire_us=4600)
    rows, n_fail, _ = evaluate(SELFTEST_CONTRACT, load_capture(bad_ap))
    verdicts = {r[0]: r[3] for r in rows}
    if verdicts.get("ap_publication_freshness") != "FAIL":
        failures.append("mutation: blown AP leg did not FAIL")
    if verdicts.get("raw_peak_vu") != "PASS":
        failures.append("mutation: raw_peak_vu should have stayed PASS")

    # Case 3 — MUTATION. Blow the end-to-end path past 25000 us via wire time,
    # leaving the AP leg healthy.
    bad_e2e = _synth(os.path.join(root, "bad_e2e"), ap_leg_us=4700, wire_us=21000)
    rows, _, _ = evaluate(SELFTEST_CONTRACT, load_capture(bad_e2e))
    verdicts = {r[0]: r[3] for r in rows}
    if verdicts.get("raw_peak_vu") != "FAIL":
        failures.append("mutation: blown end-to-end did not FAIL")
    if verdicts.get("ap_publication_freshness") != "PASS":
        failures.append("mutation: AP leg should have stayed PASS")

    # Case 4 — HONESTY. A formula budget and an event-origin budget cannot be
    # measured from this capture and must say so, not silently pass.
    rows, _, n_unmeas = evaluate(SELFTEST_CONTRACT, load_capture(good))
    verdicts = {r[0]: r[3] for r in rows}
    if verdicts.get("rmt_output") != "NOT_MEASURABLE":
        failures.append("honesty: formula budget should be NOT_MEASURABLE")
    if verdicts.get("tempo_beat_phase") != "NOT_MEASURABLE":
        failures.append("honesty: event-origin budget should be NOT_MEASURABLE")
    if n_unmeas != 2:
        failures.append("honesty: expected 2 NOT_MEASURABLE, got %d" % n_unmeas)

    # Case 5 — EMPTY. An empty capture must never read as a pass.
    empty = os.path.join(root, "empty")
    os.makedirs(empty, exist_ok=True)
    rows, _, n_unmeas = evaluate(SELFTEST_CONTRACT, load_capture(empty))
    if n_unmeas != len(SELFTEST_CONTRACT["feature_latency_contracts"]):
        failures.append("empty capture did not report every budget unmeasurable")

    for f in failures:
        print("SELF-TEST FAIL: %s" % f)
    if failures:
        print("\nSELF-TEST: %d failure(s)" % len(failures))
        return 1
    print("SELF-TEST: 5/5 cases pass "
          "(1 positive control, 2 mutations, 1 honesty, 1 empty)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--contract")
    parser.add_argument("--capture-dir")
    parser.add_argument("--allow-unmeasurable", action="store_true",
                        help="downgrade the NOT_MEASURABLE exit code to 0; the "
                             "coverage line still reports the gap")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.contract or not args.capture_dir:
        parser.error("--contract and --capture-dir are required "
                     "(or use --self-test)")

    with open(args.contract) as handle:
        contract = json.load(handle)
    series = load_capture(args.capture_dir)
    rows, n_fail, n_unmeasurable = evaluate(contract, series)
    report(rows, n_fail, n_unmeasurable)

    if n_fail:
        return 1
    if n_unmeasurable and not args.allow_unmeasurable:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
