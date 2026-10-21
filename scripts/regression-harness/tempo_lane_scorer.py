#!/usr/bin/env python3
"""Frozen tempo-lane scorer (lane R1, DEF-001 / DEF-002). Compares; never regenerates.

The scorer reads ONLY the corpus manifest (tests/fixtures/tempo_corpus/manifest.json) for gold
tempo and role, plus trajectory files produced by another tool (host replay or emulator V lines).
A clip that is not in the manifest is not scored.

Frozen definitions (lane R1 brief, 2026-10-21; change only with a dated changelog line here):
  scored window   generations >= SCORE_FROM_GEN (hop >= 1600 = 12 s warm-up at 7.5 ms/hop)
  detected        mode of integer BPM over the last 50 % of the clip (by generation)
  CORRECT         detected within +/-4 % of gold x {1/2, 1, 2}
  LOCKED          published lock fraction over the scored window >= 0.5
  WRONG LOCK      LOCKED and not CORRECT
  3:2             detected/gold within +/-6 % of 2/3 or 4/3

Exit codes: 0 ok / criterion met, 1 criterion not met (or self-test failure), 2 malformed or
incomplete input, 3 an acceptance verdict was requested over a dev-role clip (refused).

Usage:
  tempo_lane_scorer.py score   --manifest M --traj T.json [--role dev|heldout|all] [--out R.json]
  tempo_lane_scorer.py compare --manifest M --baseline A.json --candidate B.json
                               [--role ...] [--acceptance] [--out R.json]
  tempo_lane_scorer.py self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

SCORE_FROM_HOP = 1600
SCORE_FROM_GEN = SCORE_FROM_HOP + 1   # generation g carries hop g-1
DETECT_TAIL_FRACTION = 0.5
TOL_CORRECT = 0.04
CORRECT_MULTS = (0.5, 1.0, 2.0)
LOCKED_FRACTION = 0.5
TOL_32 = 0.06
RATIOS_32 = (2.0 / 3.0, 4.0 / 3.0)

EXIT_OK, EXIT_FAIL, EXIT_INPUT, EXIT_DEV_REFUSED = 0, 1, 2, 3


class InputError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict[str, dict]:
    doc = json.loads(Path(path).read_text())
    rows = doc["rows"] if isinstance(doc, dict) else doc
    out = {}
    for r in rows:
        for k in ("id", "path", "sha256", "gold_bpm", "role", "source"):
            if k not in r:
                raise InputError(f"manifest row {r.get('id')!r} lacks {k!r}")
        if r["role"] not in ("dev", "heldout"):
            raise InputError(f"manifest row {r['id']!r} has role {r['role']!r}")
        if r["id"] in out:
            raise InputError(f"manifest row {r['id']!r} duplicated")
        out[r["id"]] = r
    return out


def load_traj(path: Path) -> dict:
    doc = json.loads(Path(path).read_text())
    if "clips" not in doc:
        raise InputError(f"{path}: no 'clips'")
    for cid, c in doc["clips"].items():
        n = len(c.get("gen", []))
        if n == 0 or any(len(c.get(k, [])) != n for k in ("bpm", "lock")):
            raise InputError(f"{path}: clip {cid!r} arrays missing or unequal")
    return doc


def score_clip(c: dict, gold: float) -> dict:
    gen, bpm, lock = c["gen"], c["bpm"], c["lock"]
    gmax = max(gen)
    tail = [round(b) for g, b in zip(gen, bpm) if g >= gmax * DETECT_TAIL_FRACTION]
    if len(tail) < 5:
        tail = [round(b) for b in bpm]
    detected = float(Counter(int(x) for x in tail).most_common(1)[0][0])
    scored = [l for g, l in zip(gen, lock) if g >= SCORE_FROM_GEN]
    if not scored:
        raise InputError("no generations in the scored window")
    lock_frac = sum(1 for l in scored if l) / len(scored)
    correct = any(abs(detected - m * gold) <= TOL_CORRECT * m * gold for m in CORRECT_MULTS)
    ratio = detected / gold
    is_32 = any(abs(ratio - r) <= TOL_32 * r for r in RATIOS_32)
    locked = lock_frac >= LOCKED_FRACTION
    return {"detected_bpm": detected, "gold_bpm": gold, "ratio": round(ratio, 4),
            "correct": bool(correct), "lock_frac": round(lock_frac, 4), "locked": bool(locked),
            "wrong_lock": bool(locked and not correct), "is_32": bool(is_32),
            "scored_gens": len(scored)}


def summarise(per: dict[str, dict]) -> dict:
    v = list(per.values())
    return {
        "n": len(v),
        "correct": sum(r["correct"] for r in v),
        "locked": sum(r["locked"] for r in v),
        "locked_correct": sum(r["locked"] and r["correct"] for r in v),
        "locked_wrong": sum(r["wrong_lock"] for r in v),
        "locked_wrong_32": sum(r["wrong_lock"] and r["is_32"] for r in v),
        "detected_32": sum(r["is_32"] for r in v),
        "mean_lock_frac": round(sum(r["lock_frac"] for r in v) / len(v), 4) if v else None,
    }


def score(manifest: dict[str, dict], traj: dict, role: str) -> dict:
    per, unscored, missing = {}, [], []
    for cid, c in traj["clips"].items():
        row = manifest.get(cid)
        if row is None:
            unscored.append(cid)
            continue
        if role != "all" and row["role"] != role:
            continue
        per[cid] = {**score_clip(c, float(row["gold_bpm"])), "role": row["role"]}
    for cid, row in manifest.items():
        if (role == "all" or row["role"] == role) and cid not in traj["clips"]:
            missing.append(cid)
    roles = sorted({r["role"] for r in per.values()})
    return {"role_filter": role, "roles_scored": roles, "summary": summarise(per), "per_clip": per,
            "unscored_not_in_manifest": sorted(unscored), "missing_from_traj": sorted(missing),
            "variant": traj.get("variant"), "producer": traj.get("producer")}


def acceptance(base: dict, cand: dict) -> dict:
    b, c = base["summary"], cand["summary"]
    ok = c["locked_wrong"] <= b["locked_wrong"] and c["locked_correct"] > b["locked_correct"]
    return {"criterion": "candidate locked_wrong <= baseline AND candidate locked_correct > baseline",
            "baseline": {k: b[k] for k in ("locked_correct", "locked_wrong")},
            "candidate": {k: c[k] for k in ("locked_correct", "locked_wrong")}, "met": bool(ok)}


def _write(out: Path | None, doc: dict) -> None:
    text = json.dumps(doc, indent=1, sort_keys=True)
    if out:
        Path(out).write_text(text + "\n")
    print(json.dumps({k: doc[k] for k in doc if k not in ("per_clip", "baseline_report", "candidate_report")},
                     indent=1, sort_keys=True))


def cmd_score(a) -> int:
    manifest = load_manifest(a.manifest)
    rep = score(manifest, load_traj(a.traj), a.role)
    rep["manifest_sha256"] = sha256_file(Path(a.manifest))
    rep["traj_sha256"] = sha256_file(Path(a.traj))
    _write(a.out, rep)
    return EXIT_INPUT if rep["missing_from_traj"] else EXIT_OK


def cmd_compare(a) -> int:
    manifest = load_manifest(a.manifest)
    base = score(manifest, load_traj(a.baseline), a.role)
    cand = score(manifest, load_traj(a.candidate), a.role)
    doc = {"role_filter": a.role, "manifest_sha256": sha256_file(Path(a.manifest)),
           "baseline_sha256": sha256_file(Path(a.baseline)), "candidate_sha256": sha256_file(Path(a.candidate)),
           "baseline": base["summary"], "candidate": cand["summary"],
           "baseline_report": base, "candidate_report": cand}
    if set(base["per_clip"]) != set(cand["per_clip"]) or base["missing_from_traj"] or cand["missing_from_traj"]:
        doc["error"] = "baseline and candidate do not cover the same manifest clips"
        _write(a.out, doc)
        return EXIT_INPUT
    if a.acceptance:
        dev = sorted(cid for cid, r in cand["per_clip"].items() if r["role"] == "dev")
        if dev:
            doc["refused"] = f"acceptance verdict requested over {len(dev)} dev-role clip(s), e.g. {dev[:3]}"
            _write(a.out, doc)
            return EXIT_DEV_REFUSED
        doc["acceptance"] = acceptance(base, cand)
        _write(a.out, doc)
        return EXIT_OK if doc["acceptance"]["met"] else EXIT_FAIL
    _write(a.out, doc)
    return EXIT_OK


# ---------------------------------------------------------------- self-test (both truth values)
def _synthetic(bpm: float, lock: int, n: int = 3334) -> dict:
    return {"gen": list(range(1, n + 1)), "bpm": [bpm] * n, "conf": [0.9 if lock else 0.1] * n, "lock": [lock] * n}


def self_test() -> int:
    fails = []
    def check(cond, msg):
        if not cond:
            fails.append(msg)
    m = {"dev:a": {"id": "dev:a", "path": "-", "sha256": "-", "gold_bpm": 120.0, "role": "dev", "source": "synthetic"},
         "ho:b": {"id": "ho:b", "path": "-", "sha256": "-", "gold_bpm": 120.0, "role": "heldout", "source": "synthetic"}}
    r = score_clip(_synthetic(80.0, 1), 120.0)          # 3:2 locked
    check(r["wrong_lock"] and r["is_32"] and not r["correct"], "3:2 lock must be WRONG and flagged 3:2")
    r = score_clip(_synthetic(160.0, 1), 120.0)         # 4:3 locked
    check(r["wrong_lock"] and r["is_32"], "4:3 lock must be WRONG and flagged 3:2")
    r = score_clip(_synthetic(60.0, 1), 120.0)          # half time
    check(r["correct"] and not r["wrong_lock"] and not r["is_32"], "octave (1/2) must be CORRECT")
    r = score_clip(_synthetic(240.0, 1), 120.0)         # double time
    check(r["correct"], "octave (x2) must be CORRECT")
    r = score_clip(_synthetic(124.0, 1), 120.0)         # +3.3 %
    check(r["correct"], "within 4 % must be CORRECT")
    r = score_clip(_synthetic(126.0, 1), 120.0)         # +5 %
    check(not r["correct"] and r["wrong_lock"], "5 % off must be WRONG")
    r = score_clip(_synthetic(80.0, 0), 120.0)          # no lock
    check(not r["locked"] and not r["wrong_lock"], "no-lock must not count as a lock")
    # warm-up excluded: locked only before hop 1600 -> not LOCKED
    c = _synthetic(120.0, 0); c["lock"] = [1 if g < SCORE_FROM_GEN else 0 for g in c["gen"]]
    check(not score_clip(c, 120.0)["locked"], "lock inside the warm-up must not count")
    # acceptance over dev must refuse (exit 3); over heldout it must evaluate
    base = score(m, {"clips": {"dev:a": _synthetic(80.0, 0)}}, "all")
    cand = score(m, {"clips": {"dev:a": _synthetic(120.0, 1)}}, "all")
    check(any(r["role"] == "dev" for r in cand["per_clip"].values()), "dev clip must be visible to the refusal check")
    hb = score(m, {"clips": {"ho:b": _synthetic(80.0, 0)}}, "heldout")
    hc = score(m, {"clips": {"ho:b": _synthetic(120.0, 1)}}, "heldout")
    check(acceptance(hb, hc)["met"], "a correct new lock on held-out must meet acceptance")
    check(not acceptance(hc, hb)["met"], "losing the correct lock must fail acceptance")
    # clip not in the manifest is not scored
    rep = score(m, {"clips": {"zz:x": _synthetic(120.0, 1)}}, "all")
    check(rep["summary"]["n"] == 0 and rep["unscored_not_in_manifest"] == ["zz:x"], "unknown clip must be unscored")
    for f in fails:
        print("SELFTEST_FAIL:", f)
    print(f"selftest cases_failed={len(fails)}")
    return EXIT_OK if not fails else EXIT_FAIL


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--manifest", required=True, type=Path)
    s.add_argument("--traj", required=True, type=Path)
    s.add_argument("--role", default="all", choices=("dev", "heldout", "all"))
    s.add_argument("--out", type=Path)
    c = sub.add_parser("compare")
    c.add_argument("--manifest", required=True, type=Path)
    c.add_argument("--baseline", required=True, type=Path)
    c.add_argument("--candidate", required=True, type=Path)
    c.add_argument("--role", default="all", choices=("dev", "heldout", "all"))
    c.add_argument("--acceptance", action="store_true")
    c.add_argument("--out", type=Path)
    sub.add_parser("self-test")
    a = p.parse_args(argv)
    try:
        if a.cmd == "score":
            return cmd_score(a)
        if a.cmd == "compare":
            return cmd_compare(a)
        return self_test()
    except (InputError, KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    sys.exit(main())
