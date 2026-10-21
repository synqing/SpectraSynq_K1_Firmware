#!/usr/bin/env python3
"""Tempo-lock class gates for lane R1 (DEF-001 / DEF-002). Each gate compares captured streams
against a rule and exits non-zero on failure; none of them regenerates its input.

  m1   veto observability (I1): on every emit,
         (producer_silence == 0 AND internal_lock == 1) => (published_lock == 1 OR veto != NONE)
       --streams S.json   emulator K lines (real chain), or
       --traj T.json [--clip ID]   host replay with --debug (veto -1 = the build has no veto = NONE)
       exit 1 on the first violation and print its generation.
  m2   contrast invariance (I2): replay one captured tempo-input stream at x1, x1/2, x1/4, ^2, ^1/2
       through the host tracker; every transform must keep lock_frac within --tol of x1 and the same
       settled BPM (mode, last 50 %). --fixtures INDEX --clip ID --variant VAR [--tol 0.05]
       A clip captured with the per-note spectrum gets the same transform on every spectrum bin
       (the whole producer output moves). --transforms overrides the set; `speczero:1` (spectrum
       erased, novelty kept) is the broken-input control that must fail for a spectrum-reading build.
  p15  Phase 1.5 behaviour on emulator cases (tempo_lane_emu.py p15 suite): --cases DIR/cases.json
       silence: no lock and published confidence 0 throughout; noise / tone / drone / sweep:
       published confidence < 0.30 and 0 beat ticks; music then silence: lock released <= 3.0 s
       after the music ends; music-a: k1_av_layer_classifier PASS_timing_and_tempo.
Exit: 0 pass, 1 rule violated, 2 input lacks the fields the rule needs.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
HOP_MS = 7.5
SCORE_FROM_GEN = 1601
CONF_QUIET = 0.30
RELEASE_MAX_S = 3.0


# ------------------------------------------------------------------ M1
def m1_rows_from_streams(streams: dict):
    # K,gen,veto,internal_locked,producer_silence,locked,beat_tick,conf,bpm
    return [(k[0], k[3], k[2], k[4], k[1]) for k in streams.get("K", [])]


def m1_rows_from_traj(clip: dict):
    if "int_lock" not in clip:
        return []
    return list(zip(clip["gen"], clip["producer_silence"], clip["int_lock"], clip["lock"],
                    [max(v, 0) for v in clip["veto"]]))


def m1_check(rows) -> int | None:
    """rows: (gen, producer_silence, internal_lock, published_lock, veto). Returns first violating gen."""
    for gen, psil, ilock, plock, veto in rows:
        if psil == 0 and ilock == 1 and not (plock == 1 or veto != 0):
            return gen
    return None


def cmd_m1(a) -> int:
    if a.streams:
        for s in a.streams:
            rows = m1_rows_from_streams(json.loads(Path(s).read_text()))
            if not rows:
                print(f"M1 INPUT: {s} has no K lines")
                return 2
            first = m1_check(rows)
            if first is not None:
                print(f"M1 VIOLATION in {s} at generation {first}")
                return 1
        print(f"M1 holds on {len(a.streams)} emulator stream(s)")
        return 0
    else:
        doc = json.loads(Path(a.traj).read_text())
        clips = [a.clip] if a.clip else sorted(doc["clips"])
        rows = []
        for cid in clips:
            rows += m1_rows_from_traj(doc["clips"][cid])
    if not rows:
        print("M1 INPUT: no internal-lock / veto fields in this input")
        return 2
    first = m1_check(rows)
    n_int = sum(1 for r in rows if r[1] == 0 and r[2] == 1)
    if first is not None:
        print(f"M1 VIOLATION at generation {first}: producer_silence=0, internal_lock=1, published_lock=0, veto=NONE "
              f"(rows checked {len(rows)}, internally-locked non-silent rows {n_int})")
        return 1
    print(f"M1 holds on {len(rows)} rows ({n_int} internally-locked non-silent)")
    return 0


# ------------------------------------------------------------------ M2
TRANSFORMS = ["scale:0.5", "scale:0.25", "pow:2", "pow:0.5"]


def _settled(clip):
    gmax = max(clip["gen"])
    tail = [round(b) for g, b in zip(clip["gen"], clip["bpm"]) if g >= gmax * 0.5]
    return Counter(tail).most_common(1)[0][0]


def _lock_frac(clip):
    s = [l for g, l in zip(clip["gen"], clip["lock"]) if g >= SCORE_FROM_GEN]
    return sum(s) / len(s)


def cmd_m2(a) -> int:
    import tempo_lane_replay as tlr
    index_path = Path(a.fixtures)
    meta = json.loads(index_path.read_text())["clips"][a.clip]
    rows = tlr.load_fixture(index_path, a.clip, meta)
    with tempfile.TemporaryDirectory() as td:
        binary = tlr.build(Path(td), tlr.VARIANTS[a.variant], False)
        base = tlr.replay_rows(binary, rows, None, False)
        res = {"x1": {"lock_frac": round(_lock_frac(base), 4), "settled_bpm": _settled(base)}}
        bad = []
        for t in (a.transforms or TRANSFORMS):
            c = tlr.replay_rows(binary, rows, t, False)
            lf, bpm = _lock_frac(c), _settled(c)
            res[t] = {"lock_frac": round(lf, 4), "settled_bpm": bpm}
            if abs(lf - res["x1"]["lock_frac"]) > a.tol or bpm != res["x1"]["settled_bpm"]:
                bad.append(t)
    out = {"clip": a.clip, "variant": a.variant, "tolerance_lock_frac": a.tol, "results": res, "failing": bad,
           "fixture_sha256": meta["sha256"], "spectrum_transformed": len(rows[0]) > 3}
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 1 if bad else 0


# ------------------------------------------------------------------ P1.5
def _k(streams):
    K = streams.get("K", [])
    return {"gen": [k[0] for k in K], "veto": [k[1] for k in K], "int_lock": [k[2] for k in K],
            "psil": [k[3] for k in K], "lock": [k[4] for k in K], "tick": [k[5] for k in K],
            "conf": [k[6] for k in K], "bpm": [k[7] for k in K]}


def cmd_p15(a) -> int:
    doc = json.loads(Path(a.cases).read_text())
    rows, fails = [], []
    for c in doc["cases"]:
        s = json.loads(Path(c["streams"]).read_text())
        k = _k(s)
        if c["status"] != "PASS":
            fails.append(f"{c['id']}: emulator case {c['status']} {c['reasons']}")
            continue
        if not k["gen"]:
            print(f"P15 INPUT: {c['id']} has no K lines (build lacks the lane flags)")
            return 2
        r = {"id": c["id"], "max_conf": max(k["conf"]), "ticks": sum(k["tick"]),
             "lock_frac_all": round(sum(k["lock"]) / len(k["lock"]), 4),
             "producer_silence_frac": round(sum(k["psil"]) / len(k["psil"]), 4)}
        cid = c["id"]
        if cid == "music-a":
            tl = c.get("tempo_lane") or {}
            r["classification"] = tl.get("classification")
            r["ok"] = tl.get("classification") == "PASS_timing_and_tempo"
        elif cid == "silence-30s":
            r["ok"] = sum(k["lock"]) == 0 and r["max_conf"] == 0.0 and r["ticks"] == 0
        elif cid in ("white-noise-30s", "tone440-30s", "pink-drone-30s", "sweep-30s"):
            r["ok"] = r["max_conf"] < CONF_QUIET and r["ticks"] == 0 and sum(k["lock"]) == 0
        elif cid == "music-then-silence":
            end_gen = -(-c["music_samples"] // 96)
            locked_at_end = [g for g, l in zip(k["gen"], k["lock"]) if l and g <= end_gen]
            after = [(g, l) for g, l in zip(k["gen"], k["lock"]) if g > end_gen]
            last_locked = max((g for g, l in after if l), default=end_gen)
            release_s = (last_locked - end_gen) * HOP_MS / 1000.0
            psil_on = next((g for g, p in zip(k["gen"], k["psil"]) if g > end_gen and p), None)
            r.update(music_end_gen=end_gen, locked_before_end=bool(locked_at_end),
                     release_s_after_music=round(release_s, 3),
                     producer_silence_s_after_music=None if psil_on is None else round((psil_on - end_gen) * HOP_MS / 1000, 3),
                     unlocked_at_end=k["lock"][-1] == 0, conf_at_end=k["conf"][-1])
            r["ok"] = bool(locked_at_end) and release_s <= RELEASE_MAX_S and r["unlocked_at_end"]
        else:
            r["ok"] = None
        rows.append(r)
        if r["ok"] is False:
            fails.append(cid)
    out = {"cases": rows, "failing": fails, "env": doc.get("env"), "git_head": doc.get("git_head")}
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 1 if fails else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    m1 = sub.add_parser("m1")
    m1.add_argument("--streams", nargs="+")
    m1.add_argument("--traj")
    m1.add_argument("--clip")
    m2 = sub.add_parser("m2")
    m2.add_argument("--fixtures", required=True)
    m2.add_argument("--clip", required=True)
    m2.add_argument("--variant", default="l1")
    m2.add_argument("--tol", type=float, default=0.05)
    m2.add_argument("--transforms", nargs="+")
    m2.add_argument("--json")
    p15 = sub.add_parser("p15")
    p15.add_argument("--cases", required=True)
    p15.add_argument("--json")
    a = p.parse_args(argv)
    return {"m1": cmd_m1, "m2": cmd_m2, "p15": cmd_p15}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
