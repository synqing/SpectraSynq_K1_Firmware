#!/usr/bin/env python3
"""Fixed intersection of independently recorded E1/E2 lock decisions; no tuning."""
import argparse
import json
from pathlib import Path
import tempo_lane_scorer as scorer

def intersect(first,second):
    if set(first["clips"])!=set(second["clips"]): raise ValueError("different clip sets")
    out={"variant":"E1-hold4s-AND-frozen-E2","clips":{}}
    for cid,a in first["clips"].items():
        b=second["clips"][cid]
        if a["gen"]!=b["gen"] or a["bpm"]!=b["bpm"]: raise ValueError("generation/BPM mismatch: "+cid)
        if len(a["lock"])!=len(a["gen"]) or len(b["lock"])!=len(b["gen"]): raise ValueError("incomplete lock: "+cid)
        out["clips"][cid]={**a,"lock":[int(bool(x) and bool(y)) for x,y in zip(a["lock"],b["lock"])]}
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--first",type=Path,required=True);p.add_argument("--second",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    out=intersect(json.loads(a.first.read_text()),json.loads(a.second.read_text()))
    out["producer"]={"first":str(a.first),"first_sha256":scorer.sha256_file(a.first),
                     "second":str(a.second),"second_sha256":scorer.sha256_file(a.second),
                     "scope":"diagnostic intersection; no new threshold or firmware admission"}
    a.out.write_text(json.dumps(out));print(f"intersected {len(out['clips'])} clips")
if __name__=="__main__":main()
