#!/usr/bin/env python3
"""Resume the frozen E1 tracker/estimator on hash-verified captured inputs.
No new estimator, threshold, label or firmware algorithm. Per-clip checkpoints.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time
import s3_audio_qualification as q
import tempo_joint_estimator as joint

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixtures",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True);p.add_argument("--role",choices=("validation","dev"),default="validation");a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    idx=json.loads(a.fixtures.read_text());params={**joint.DEFAULTS,"kappa":8.0,"lam":8.0,"tempo_q":0.02}
    binary=q.replay.build(a.out,q.replay.VARIANTS["l1sp"],True)
    headers = {str(p.relative_to(q.replay.FIRMWARE)):q.replay.sha256_bytes(p.read_bytes())
               for directory in ("audio", "system") for p in (q.replay.FIRMWARE/directory).glob("*.h")}
    driver_hash=q.replay.sha256_bytes(q.replay.DRIVER.encode())
    tracker={};estimator={};start=time.monotonic()
    for i,(cid,meta) in enumerate(sorted(idx["clips"].items())):
        name=cid.replace(":","_"); cache=a.out/(name+".json")
        rows=q.replay.load_fixture(a.fixtures,cid,meta)
        # Cache identity includes source, fixture and frozen estimator parameters.
        identity={"fixture":meta["sha256"],"tempo":q.replay.sha256_bytes((q.replay.FIRMWARE/"audio/k1_tempo.cpp").read_bytes()),
                  "joint":q.replay.sha256_bytes(Path(joint.__file__).read_bytes()),"params":params,
                  "headers":headers,"driver":driver_hash,"defines":q.replay.PROD+q.replay.VARIANTS["l1sp"]}
        old=json.loads(cache.read_text()) if cache.exists() else None
        if old and old.get("identity")==identity: t,e=old["tracker"],old["estimator"]
        else:
            t=q.run_rows(binary,rows,a.out/(name+".raw"));e,_=joint.run_clip(rows,params)
            cache.write_text(json.dumps({"identity":identity,"tracker":t,"estimator":e}))
        tracker[cid]=t;estimator[cid]=e
        if (i+1)%25==0: print(f"{i+1}/{len(idx['clips'])} clips {time.monotonic()-start:.1f}s",flush=True)
    td={"variant":"l1sp","clips":tracker,"producer":{"build_cmd":(a.out/"build_cmd.txt").read_text(),"fixtures":str(a.fixtures)}}
    ed={"variant":"frozen-E1-pointer","clips":estimator,"producer":{"params":params,"fixtures":str(a.fixtures)}}
    (a.out/"tracker.json").write_text(json.dumps(td));(a.out/"joint.json").write_text(json.dumps(ed))
    import sys
    here=Path(__file__).resolve().parent
    commands=[
      ["tempo_joint_estimator.py","gate","--tracker-traj",str(a.out/"tracker.json"),"--estimator-traj",str(a.out/"joint.json"),"--hold-s","4","--out",str(a.out/"gated.json")],
      ["tempo_lane_scorer.py","compare","--manifest",str(a.manifest),"--role",a.role,"--baseline",str(a.out/"tracker.json"),"--candidate",str(a.out/"gated.json"),"--out",str(a.out/"score.json")],
      ["tempo_lock_verdict.py","--report",str(a.out/"score.json"),"--baseline-traj",str(a.out/"tracker.json"),"--candidate-traj",str(a.out/"gated.json"),"--out",str(a.out/"verdict.json")]]
    receipts=[]
    for cmd in commands:
        command=[sys.executable,str(here/cmd[0]),*cmd[1:]]
        with (a.out/(cmd[0]+".log")).open("w") as log: r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        receipts.append({"command":command,"exit_code":r.returncode})
        (a.out/"commands.json").write_text(json.dumps(receipts,indent=2))
        if r.returncode: return r.returncode
    (a.out/"commands.json").write_text(json.dumps(receipts,indent=2))
    complete=idx.get("complete",True);print(json.dumps({"complete_corpus":complete,"clips":len(tracker),"verdict_exit":receipts[-1]["exit_code"]}))
    return 2 if not complete else receipts[-1]["exit_code"]
if __name__=="__main__":raise SystemExit(main())
