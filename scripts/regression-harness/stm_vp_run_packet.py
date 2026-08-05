#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RH = Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_ndjson(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def run(mod, wav, out, sec):
    cmd=[sys.executable,str(RH/mod),str(wav),"-o",str(out),"--max-seconds",str(sec)]
    p=subprocess.run(cmd,capture_output=True,text=True,check=True)
    return json.loads(p.stdout.strip().splitlines()[-1])
def gate(mpath):
    p=subprocess.run([sys.executable,str(RH/"stm_vp_compare.py"),str(mpath),"--json"],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)
def align(a,b):
    n=min(len(a),len(b)); s=[]
    for i in range(n):
        s.append({"reference_energy":float(a[i].get("energy",0)),"candidate_energy":float(b[i].get("energy",0))})
    return s

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--wav",required=True); ap.add_argument("--run-id",default="wb3_vp_host_2026-07-30"); ap.add_argument("--max-seconds",type=float,default=15)
    args=ap.parse_args(); wav=Path(args.wav); run_dir=ROOT/"artifacts/stm-vp"/args.run_id; run_dir.mkdir(parents=True,exist_ok=True)
    fh=sha(wav)
    ref=run("stm_reference_512.py",wav,run_dir/"reference.ndjson",args.max_seconds)
    ref_exe=ref["executable_hash"]
    hashes=[]
    for i in range(3):
        outp=run_dir/f"reference_repeat_{i}.ndjson"
        run("stm_reference_512.py",wav,outp,args.max_seconds)
        rows=load_ndjson(outp)
        hashes.append(hashlib.sha256(json.dumps([r["energy"] for r in rows]).encode()).hexdigest())
    cand=run("stm_k1_native_host.py",wav,run_dir/"candidate.ndjson",args.max_seconds)
    streams=align(load_ndjson(run_dir/"reference.ndjson"),load_ndjson(run_dir/"candidate.ndjson"))
    diffs=[abs(s["reference_energy"]-s["candidate_energy"])/max(s["reference_energy"],s["candidate_energy"],1e-6) for s in streams]
    mean_rel=sum(diffs)/len(diffs) if diffs else 1.0
    within=mean_rel<=0.35
    manifest={"experiment_version":"wb3-vp-host-1","threshold_set_hash":"sha256:provisional-v1","fixture_hash":fh,"claim":"parity",
        "reference":{"algorithm_id":ref["algorithm_id"],"executable_hash":ref_exe,"source_hash":fh,"fft_size":512,"stm_bins":42},
        "candidate":{"algorithm_id":cand["algorithm_id"],"executable_hash":cand["executable_hash"],"source_hash":fh,"stm_bins":40},
        "streams":streams,"metrics_within_threshold":within,
        "controls":{"fixture":wav.name,"mean_relative_error":mean_rel}}
    (run_dir/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    verdict=gate(run_dir/"manifest.json")
    (run_dir/"verdict.json").write_text(json.dumps(verdict,indent=2)+"\n")
    (run_dir/"ref_ref_repeatability.json").write_text(json.dumps({"energy_series_hashes":hashes,"all_identical":len(set(hashes))==1},indent=2)+"\n")
    summary={"run_id":args.run_id,"finished_at":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"fixture":str(wav),
        "tb5_all_identical":len(set(hashes))==1,"mean_relative_error":mean_rel,"verdict":verdict}
    (run_dir/"packet_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
