#!/usr/bin/env python3
"""Actual shipping tempo C++ paired replay; preserves frozen scoring and admission gates.

Uses recorded novelty, never reconstructs the audio frontend. Synthetic traps are
explicitly labelled. File-backed IO avoids pipe deadlock on large trajectories.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempo_lane_replay as replay
import tempo_trap_suite as traps
import tempo_lane_scorer as scorer

ROOT = Path(__file__).resolve().parents[2]
KEYS = "gen bpm conf lock tick phase int_lock int_silence conf_ema emit_count veto comb_bpm point_bpm goertzel_bpm quality tooth".split()
FLOATS = set("bpm conf phase conf_ema comb_bpm point_bpm goertzel_bpm quality tooth".split())

def run_rows(binary, rows, path):
    feed = path.with_suffix(".input")
    feed.write_text("".join(f"{r[0]} {replay.frame_ms(r[0])} {float(r[1]):.9g} {r[2]}" +
        (f" {r[3]}" if len(r) > 3 else "") + "\n" for r in rows))
    with feed.open() as src, path.open("w") as dst:
        subprocess.run([str(binary)], stdin=src, stdout=dst, check=True, timeout=30)
    lines = [x.split()[1:] for x in path.read_text().splitlines() if x.startswith("F ")]
    if len(lines) != len(rows) or any(len(x) != len(KEYS) for x in lines):
        raise ValueError("incomplete actual-code trajectory")
    c = {k: [(float if k in FLOATS else int)(x[i]) for x in lines] for i,k in enumerate(KEYS)}
    c["producer_silence"] = [r[2] for r in rows]
    return c

def summary(c):
    ids = [i for i,g in enumerate(c["gen"]) if g >= 1601]
    if not ids: ids = list(range(len(c["gen"])))
    return {"frames":len(c["gen"]), "scored_frames":len(ids),
        "settled_bpm": traps.settled_bpm(c),
        "published_lock_frames":sum(c["lock"][i] for i in ids),
        "beat_ticks":sum(c["tick"][i] for i in ids),
        "internal_lock_frames":sum(c["int_lock"][i] for i in ids),
        "false_silence_frames":sum(c["int_silence"][i] and not c["producer_silence"][i] for i in ids),
        "max_conf":max(c["conf"][i] for i in ids)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fixtures", type=Path, action="append", default=[])
    ap.add_argument("--uart", type=Path, action="append", default=[])
    ap.add_argument("--traps", action="store_true")
    ap.add_argument("--candidate", choices=("silence_only", "retention"), default="silence_only")
    a=ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    if a.candidate == "retention" and "K1_TEMPO_SILENCE_RETENTION_V1" not in (replay.FIRMWARE / "audio/k1_tempo.cpp").read_text():
        raise ValueError("retention candidate was rejected and is not installed; see saved experiment patch")
    cases={}; provenance={}
    for index in a.fixtures:
        d=json.loads(index.read_text())
        for cid,meta in d["clips"].items():
            if cid in cases: raise ValueError("duplicate case " + cid)
            cases[cid]=replay.load_fixture(index,cid,meta)
            provenance[cid]={"kind":"recorded_producer", "index":str(index), **meta}
    for uart in a.uart:
        cid=uart.parent.name
        if cid in cases: raise ValueError("duplicate case " + cid)
        raw=uart.read_bytes(); cases[cid]=replay.parse_n_lines(raw.decode(),with_spectrum=True)
        provenance[cid]={"kind":"recorded_producer", "source_uart":str(uart),"sha256":hashlib.sha256(raw).hexdigest()}
    if a.traps:
        seed=7
        for pattern in traps.PATTERNS:
            for bpm in traps.BPMS:
                seed+=1; cid=f"synthetic-{pattern}-{bpm:g}"
                cases[cid],truth=traps.train(pattern,bpm,seed)
                provenance[cid]={"kind":"synthetic_novelty_not_music", "gold_bpm":truth,"seed":seed,"generator":"tempo_trap_suite.train"}
    if not cases: raise ValueError("no inputs")
    result={"source_sha256":hashlib.sha256((replay.FIRMWARE/"audio/k1_tempo.cpp").read_bytes()).hexdigest(),
        "provenance":provenance,"variants":{},"note":"Diagnostic qualification, not full audio frontend or heldout admission."}
    manifest=scorer.load_manifest(ROOT/"tests/fixtures/tempo_corpus/manifest.json")
    for variant in ("shipped", a.candidate):
        replay.VARIANTS["retention"] = ["K1_TEMPO_SILENCE_RETENTION_V1"]
        dest=a.out/variant; dest.mkdir(exist_ok=True)
        binary=replay.build(dest,replay.VARIANTS[variant]+["K1_ONSET_V2"],True)
        trajectories={}; summaries={}
        for cid,rows in cases.items():
            c=run_rows(binary,rows,dest/(cid.replace(":","_")+".raw")); trajectories[cid]=c
            s=summary(c)
            if "gold_bpm" in provenance[cid]:
                s["tempo_verdict"]=traps.verdict(s["settled_bpm"],provenance[cid]["gold_bpm"])
            summaries[cid]=s
        traj={"variant":variant,"clips":trajectories,"producer":{"build_cmd":(dest/"build_cmd.txt").read_text()}}
        (dest/"trajectories.json").write_text(json.dumps(traj))
        dev=scorer.score(manifest,traj,"dev")
        (dest/"dev-score.json").write_text(json.dumps(dev,indent=2))
        result["variants"][variant]={"cases":summaries,"dev":dev["summary"]}
    b=result["variants"]["shipped"]; c=result["variants"][a.candidate]
    result["dev_acceptance"]=scorer.acceptance({"summary":b["dev"]},{"summary":c["dev"]})
    result["new_false_positive_cases"]=[cid for cid in cases if any(x in cid for x in ("noise","drone","sweep","chord")) and c["cases"][cid]["published_lock_frames"]>b["cases"][cid]["published_lock_frames"]]
    result["new_trap_failures"] = [cid for cid in cases if provenance[cid]["kind"] == "synthetic_novelty_not_music" and b["cases"][cid]["tempo_verdict"] == "PASS" and c["cases"][cid]["tempo_verdict"] != "PASS"]
    (a.out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"cases":len(cases),"dev_acceptance":result["dev_acceptance"],"new_false_positive_cases":result["new_false_positive_cases"]}))
    return int(bool(result["new_false_positive_cases"]) or bool(result["new_trap_failures"]) or not result["dev_acceptance"]["met"])

if __name__ == "__main__": raise SystemExit(main())
