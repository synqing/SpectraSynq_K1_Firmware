#!/usr/bin/env python3
"""Summarise [AP] telemetry for the CHAIN-MAP reconciliation (section 5).

Reads JSON-lines files whose "line" field carries the firmware's 1 Hz [AP]
line (i2s_audio.h:1545 + :1559 + :1676 in a6bad318). Only complete lines
(start "[AP]" and contain "lightshow=") are used; split fragments are counted
and skipped. Prints percentiles per file and a few source-model checks.

Usage: python3.13 -I ap_stats.py <file.jsonl> [...]
"""
import json
import re
import sys

FIELDS = [
    "SSL", "DC", "max_raw", "follower", "peak_scaled", "silence", "sil_pk",
    "rms_raw", "pky", "raw_i16_abs_peak", "raw_i16_rms", "input_trim",
    "gdft_trim", "agc_gain", "agc_env", "clip_pct", "near_pct", "peak_pin",
    "spec_pin", "spec_sat", "lg_mode", "lightshow",
]
KV = re.compile(r"(?:^|[\s|])([A-Za-z_0-9]+)=(-?[0-9.]+)")


def parse(path):
    rows, frags = [], 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                line = json.loads(raw).get("line", "")
            except json.JSONDecodeError:
                continue
            if not isinstance(line, str) or "SSL=" not in line:
                continue
            if not (line.startswith("[AP]") and "lightshow=" in line):
                frags += 1
                continue
            kv = {k: float(v) for k, v in KV.findall(line)}
            if all(f in kv for f in ("max_raw", "follower", "peak_scaled", "gdft_trim")):
                rows.append(kv)
    return rows, frags


def pct(vals, p):
    if not vals:
        return float("nan")
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def summarise(path):
    rows, frags = parse(path)
    print(f"\n=== {path}")
    print(f"complete [AP] lines={len(rows)} fragments_skipped={frags}")
    if not rows:
        return
    modes = sorted({int(r.get('lightshow', -1)) for r in rows})
    lg = sorted({int(r.get('lg_mode', -1)) for r in rows})
    sens = sorted({(int(r.get('SSL', -1)), int(r.get('DC', 0))) for r in rows})
    print(f"lightshow={modes} lg_mode={lg} (SSL,DC)={sens}")
    music = [r for r in rows if r.get("silence", 0) == 0]
    print(f"silence=0 lines={len(music)}  silence=1 lines={len(rows) - len(music)}")
    hdr = f"{'field':18s} {'min':>9s} {'p10':>9s} {'p50':>9s} {'p90':>9s} {'max':>9s}   (silence=0 lines)"
    print(hdr)
    for f in ["raw_i16_abs_peak", "raw_i16_rms", "max_raw", "sil_pk", "follower",
              "peak_scaled", "peak_pin", "spec_pin", "spec_sat", "gdft_trim",
              "input_trim", "agc_gain", "agc_env", "clip_pct", "near_pct", "rms_raw", "pky"]:
        v = [r[f] for r in music if f in r]
        if not v:
            continue
        print(f"{f:18s} {min(v):9.3f} {pct(v,10):9.3f} {pct(v,50):9.3f} {pct(v,90):9.3f} {max(v):9.3f}")

    # Model checks -------------------------------------------------------
    n = len(music)
    if n == 0:
        return
    # 1. Gain chain: max_raw ~= raw_i16_abs_peak * 8 * SENS (+/- |DC|); infer SENS.
    ratios = [(r["max_raw"]) / r["raw_i16_abs_peak"] for r in music
              if r.get("raw_i16_abs_peak", 0) >= 40]
    if ratios:
        print(f"max_raw/raw_i16_abs_peak (raw>=40): p10={pct(ratios,10):.2f} p50={pct(ratios,50):.2f} p90={pct(ratios,90):.2f}"
              f"  [8*2.7=21.6 before DC shift]")
    # 2. Follower floor: fraction of lines with follower == SSL (floor clamp active).
    fl = sum(1 for r in music if abs(r["follower"] - r["SSL"]) < 0.5)
    print(f"follower at SSL floor: {fl}/{n} = {fl/n:.3f}")
    # 3. Loud-guard ladder consistency: gdft target implied by peak_pin / spec_pin duties.
    def target(r):
        pp, ss = r["peak_pin"], r["spec_pin"]
        if ss > 0.35 or pp > 0.60:
            return 0.32
        if ss > 0.12 or pp > 0.30:
            return 0.70
        if ss > 0.04 or pp > 0.12:
            return 0.85
        return 1.0
    tcount = {}
    for r in music:
        t = target(r)
        tcount[t] = tcount.get(t, 0) + 1
    print("implied gdft_target share: " + ", ".join(f"{k:.2f}:{v/n:.3f}" for k, v in sorted(tcount.items())))
    below = sum(1 for r in music if r["gdft_trim"] < 0.999)
    print(f"gdft_trim<0.999 (floor-cut + ceiling knee ACTIVE): {below}/{n} = {below/n:.3f}")
    b92 = sum(1 for r in music if r["gdft_trim"] < 0.92)
    print(f"gdft_trim<0.92 (chroma unpin eligible): {b92}/{n} = {b92/n:.3f}")
    pp12 = sum(1 for r in music if r["peak_pin"] > 0.12)
    print(f"peak_pin duty>0.12: {pp12}/{n} = {pp12/n:.3f}; spec_pin>0.04: "
          f"{sum(1 for r in music if r['spec_pin'] > 0.04)}/{n}")
    # 4. AGC floor implied by gdft_trim, and how close agc_gain sits to it.
    def floor_of(trim):
        t = min(max(trim, 0.32), 1.0)
        return 0.020 + (0.1 - 0.020) * (t - 0.32) / (1.0 - 0.32)
    near_floor = [r for r in music if r["agc_gain"] <= 1.05 * floor_of(r["gdft_trim"])]
    print(f"agc_gain (bass band) within 5% of loud-guard floor: {len(near_floor)}/{n}")
    lo = sorted(music, key=lambda r: r["agc_gain"])[:3]
    for r in lo:
        print(f"  lowest agc_gain={r['agc_gain']:.3f} at gdft_trim={r['gdft_trim']:.3f} floor={floor_of(r['gdft_trim']):.4f}"
              f" target_cap=0.25*trim/(env+0.001)")
    # 5. peak_scaled vs (max_raw-SSL)/follower (instantaneous, unsmoothed).
    inst = [max(r["max_raw"] - r["SSL"], 0.0) / max(r["follower"], 1.0) for r in music]
    print(f"(max_raw-SSL)/follower instant: p50={pct(inst,50):.3f} p90={pct(inst,90):.3f} max={max(inst):.3f}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        summarise(p)
