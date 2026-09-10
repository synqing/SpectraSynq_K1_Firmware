#!/usr/bin/env python3
"""Reproduce every latency figure in RESULT.md from the committed dumps.

Joins the APCAD audio ring to the RMT completion ring on the shared
esp_timer_get_time() clock. For each analysis publish it takes the FIRST LED
frame submitted after it, so the result is the earliest possible light for that
audio -- a floor, not a worst case.

    python3 join_latency.py
"""
import bisect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = [
    ("Bench B489A500  WS2812 150 px/lane  music via mic", "bench-B489A500"),
    ("RPL   9087A500  Lever-2 160 px/lane  LINE-IN SILENT", "rpl-9087A500"),
]
STAGES = [
    ("ap_leg", "audio frame -> analysis published"),
    ("wait_render", "published -> transmission starts"),
    ("wire", "LED wire (hardware confirmed)"),
    ("newest", "NEWEST sample -> LED frame complete"),
    ("oldest", "OLDEST sample -> LED frame complete"),
]


def fields(line):
    out = {}
    for kv in line.split(","):
        if "=" in kv:
            key, value = kv.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


def load(unit_dir):
    ap, rmt = [], []
    with open(os.path.join(unit_dir, "apcad_dump.txt"), errors="ignore") as handle:
        for line in handle:
            if line.startswith("APCAD,"):
                f = fields(line)
                if "newest_sample_estimate_us" in f:
                    ap.append((
                        int(f["ap_publish_us"]),
                        int(f["newest_sample_estimate_us"]),
                        int(f["oldest_sample_estimate_us"]),
                    ))
    with open(os.path.join(unit_dir, "k1rmt_dump.txt"), errors="ignore") as handle:
        for line in handle:
            if line.startswith("K1RMT,"):
                f = fields(line)
                # channel 0 only, and only hardware-confirmed records
                if f.get("channel") == "0" and f.get("flags") == "1":
                    rmt.append((int(f["submit_us"]), int(f["complete_us"])))
    ap.sort()
    rmt.sort()
    return ap, rmt


def main():
    for label, subdir in UNITS:
        path = os.path.join(HERE, subdir)
        if not os.path.isdir(path):
            print("missing: %s" % path, file=sys.stderr)
            continue
        ap, rmt = load(path)
        if not ap or not rmt:
            print("%s -- no joinable records" % label, file=sys.stderr)
            continue
        submits = [r[0] for r in rmt]
        lo, hi = rmt[0][0], rmt[-1][0]
        rows = []
        for publish, newest, oldest in ap:
            if not lo <= publish <= hi:
                continue                      # outside the LED capture window
            i = bisect.bisect_left(submits, publish)
            if i >= len(rmt):
                continue
            submit, complete = rmt[i]
            rows.append({
                "ap_leg": publish - newest,
                "wait_render": submit - publish,
                "wire": complete - submit,
                "newest": complete - newest,
                "oldest": complete - oldest,
            })
        print("\n%s" % label)
        print("  joined frames: %d   (all values microseconds)" % len(rows))
        for key, text in STAGES:
            v = [r[key] for r in rows]
            print("  %-38s min=%6d  p50=%6d  p99=%6d  max=%6d"
                  % (text, min(v), pct(v, 0.5), pct(v, 0.99), max(v)))


if __name__ == "__main__":
    main()
