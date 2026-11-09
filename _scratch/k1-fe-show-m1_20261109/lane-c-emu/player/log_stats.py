#!/usr/bin/env python3
"""Send-error statistics from a show_player JSONL log (dry-run or serial)."""
import json, sys
import numpy as np
recs = [json.loads(l) for l in open(sys.argv[1])]
fr = [r for r in recs if "idx" in r]
err = np.array([r["err_us"] for r in fr], float)
sched = np.array([r["sched_us"] for r in fr], float); send = np.array([r["send_us"] for r in fr], float)
foot = next((r for r in recs if r.get("kind") == "footer"), {})
print(json.dumps({"log": sys.argv[1], "frames": len(fr), "frames_skipped_late": foot.get("frames_skipped_late"),
    "send_err_us": {q: float(np.percentile(err, p)) for q, p in (("p50", 50), ("p95", 95), ("p99", 99))} | {"max": float(err.max())},
    "late_counts": {"over_4ms": int((err > 4000).sum()), "over_10ms": int((err > 10000).sum()), "over_25ms": int((err > 25000).sum())},
    "cumulative_drift_us_end": float(np.mean(err[-120:]) - np.mean(err[:120])),
    "duration_s": float((send[-1] - send[0]) / 1e6),
    "linear_fit_slope_ppm": float((np.polyfit(sched, send, 1)[0] - 1) * 1e6),
    "pacing": next((r.get("pacing") for r in recs if r.get("kind") == "header"), None),
    "audio_align_us": ({q: float(np.percentile(al, p)) for q, p in (("p5", 5), ("p50", 50), ("p95", 95))} |
                       {"min": float(al.min()), "max": float(al.max()), "first_120_mean": float(al[:120].mean()),
                        "last_120_mean": float(al[-120:].mean())}) if len(al := np.array([r["audio_align_us"] for r in fr if "audio_align_us" in r], float)) else None,
    "audio_output_underflows": foot.get("audio_output_underflows")}, indent=1))
