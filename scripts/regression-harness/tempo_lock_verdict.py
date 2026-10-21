#!/usr/bin/env python3
"""Pre-registered verdict for a lock candidate on validation material (lane R1, DEF-002).

Reads a frozen-scorer `compare` report (tempo_lane_scorer.py compare --out R.json; baseline = the lane tracker,
candidate = the gated trajectory) and the two trajectories, and applies the criteria pre-registered in
docs/architecture/tempo-lock-hardening-plan.md before the run:
  C1  wrong locks <= 10 % of locked tracks at the upper two-sided 95 % Wilson bound
  C2  right locks >= 25 % of scored tracks
  C3  no new trap attractor: the candidate publishes the baseline's BPM unchanged on every generation
      (a lock gate cannot move the settled tempo; checked, not assumed)
Exit 0 all met, 1 any not met, 2 malformed input. The verdict compares; it never re-scores.

  tempo_lock_verdict.py --report R.json --baseline-traj T.json --candidate-traj G.json [--out V.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

WRONG_MAX, COVER_MIN = 0.10, 0.25


def wilson_upper(x: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 1.0
    p = x / n
    return (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def verdict(rep: dict, base: dict, cand: dict) -> dict:
    c = rep["candidate"]
    locked, right, wrong, n = c["locked"], c["locked_correct"], c["locked_wrong"], c["n"]
    wu = wilson_upper(wrong, locked)
    moved = [cid for cid, t in cand["clips"].items() if t["bpm"] != base["clips"][cid]["bpm"]]
    crit = {
        "C1_wrong_wilson_upper": {"value": round(wu, 4), "limit": WRONG_MAX, "wrong": wrong, "locked": locked,
                                  "met": bool(locked > 0 and wu <= WRONG_MAX)},
        "C2_right_lock_coverage": {"value": round(right / n, 4) if n else 0.0, "limit": COVER_MIN, "right": right,
                                   "n": n, "met": bool(n and right / n >= COVER_MIN)},
        "C3_bpm_passthrough": {"clips_with_bpm_changed": len(moved), "examples": moved[:5], "met": not moved},
    }
    return {"criteria": crit, "met": all(v["met"] for v in crit.values()),
            "baseline_summary": rep["baseline"], "candidate_summary": c, "role_filter": rep.get("role_filter"),
            "manifest_sha256": rep.get("manifest_sha256"), "candidate_sha256": rep.get("candidate_sha256")}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--report", required=True)
    p.add_argument("--baseline-traj", required=True)
    p.add_argument("--candidate-traj", required=True)
    p.add_argument("--out")
    a = p.parse_args(argv)
    try:
        rep = json.loads(Path(a.report).read_text())
        base = json.loads(Path(a.baseline_traj).read_text())
        cand = json.loads(Path(a.candidate_traj).read_text())
        if "error" in rep or set(base["clips"]) != set(cand["clips"]):
            raise ValueError("report error or trajectories cover different clips")
        doc = verdict(rep, base, cand)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    if a.out:
        Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"met": doc["met"], **{k: v for k, v in doc["criteria"].items()}}, indent=1))
    return 0 if doc["met"] else 1


if __name__ == "__main__":
    sys.exit(main())
