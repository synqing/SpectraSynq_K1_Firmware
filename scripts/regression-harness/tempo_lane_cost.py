#!/usr/bin/env python3
"""Per-emit tempo stage cost from G lines (ENABLE_TEMPO_STREAM timers; emulated time, not silicon).
usage: tempo_lane_cost.py UART [UART...] -> JSON on stdout
       tempo_lane_cost.py --baseline BASE_UART [--max-ratio 2.0] CANDIDATE_UART
         A7 gate: exit 1 unless the candidate's total p50 AND max are <= max-ratio x the baseline's.

A 17th G field (K1_TEMPO_SPECTRAL_PRESENCE_V1 probe builds) is the per-frame presence cost summed
over the emit window; that work runs outside the emit timer, so `emit_plus_presence` is the like-for-
like total for A7. Builds without the field report the six emit stages only (the Phase 0.2 method)."""
import json, sys
args = sys.argv[1:]
baseline, max_ratio = None, 2.0
if "--baseline" in args:
    i = args.index("--baseline"); baseline = args[i + 1]; del args[i:i + 2]
if "--max-ratio" in args:
    i = args.index("--max-ratio"); max_ratio = float(args[i + 1]); del args[i:i + 2]
STAGES = ["silence", "acf", "update", "phase", "publish", "emit_total"]
def pct(v, q):
    s = sorted(v); return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]
def summ(v):
    return {"p50": pct(v, .5), "p95": pct(v, .95), "p99": pct(v, .99), "max": max(v), "mean": round(sum(v) / len(v), 1)}
def load(u):
    seen, rows = set(), []
    for ln in open(u, errors="replace"):
        if ln.startswith("G,"):
            p = ln.strip().split(","); emit = int(p[6])
            if emit and emit not in seen:
                seen.add(emit); rows.append([int(x) for x in p[10:17]])
    if not rows:
        raise SystemExit(f"{u}: no G lines")
    d = {"emits": len(rows)}
    for i, st in enumerate(STAGES):
        d[st] = summ([r[i] for r in rows])
    if all(len(r) == 7 for r in rows):
        d["presence_window"] = summ([r[6] for r in rows])
        d["emit_plus_presence"] = summ([r[5] + r[6] for r in rows])
    return d
total = lambda d: d.get("emit_plus_presence", d["emit_total"])
out = {u: load(u) for u in ([baseline] if baseline else []) + args}
if baseline:
    b, c = total(out[baseline]), total(out[args[0]])
    verdict = {"baseline_p50": b["p50"], "baseline_max": b["max"], "candidate_p50": c["p50"], "candidate_max": c["max"],
               "ratio_p50": round(c["p50"] / b["p50"], 3), "ratio_max": round(c["max"] / b["max"], 3), "max_ratio": max_ratio}
    verdict["within"] = verdict["ratio_p50"] <= max_ratio and verdict["ratio_max"] <= max_ratio
    out["a7"] = verdict
print(json.dumps(out, indent=1))
if baseline and not out["a7"]["within"]:
    sys.exit(1)

