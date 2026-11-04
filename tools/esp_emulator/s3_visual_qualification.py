"""Exercise enabled FE effects through the existing PCM-to-packed-output emulator.
No build, serial or hardware access. Requires a separately built k1_fe_emu.
Dark effects are coverage gaps, never an aesthetic failure or an automatic pass.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as replay
import emu_capture as ec


def compiled_roster(out: Path) -> list[dict]:
    src = (replay.REPO / "SPECTRASYNQ_K1_FIRMWARE/system/config_types.h").read_text()
    enum = src[src.index("enum lightshow_modes {"):src.index("// Modes removed from the product")]
    fn = src[src.index("inline bool light_mode_is_enabled"):src.index("// Return `mode` if enabled")]
    names = re.findall(r"^\s*(LIGHT_MODE_\w+)\s*,", enum, re.M)
    flags=replay.effective_env("k1_fe").get("build_flags",[])
    if isinstance(flags,str): flags=flags.split()
    variant=any(str(f).startswith("-DK1_WFHYB_M32_VARIANTS_V1") for f in flags)
    (out/"effective_flags.json").write_text(json.dumps(flags,indent=2)+"\n")
    code = "#include <cstdint>\n#include <cstdio>\n" + ("#define K1_WFHYB_M32_VARIANTS_V1\n" if variant else "") + enum + fn
    code += '\nint main(){ for(unsigned i=0;i<NUM_MODES;++i) printf("%u %u\\n",i,light_mode_is_enabled(i)); }\n'
    (out / "roster.cpp").write_text(code)
    compiler = shutil.which("clang++") or shutil.which("g++")
    subprocess.run([compiler, "-std=c++17", str(out / "roster.cpp"), "-o", str(out / "roster")], check=True)
    raw = subprocess.check_output([str(out / "roster")], text=True)
    (out / "roster.txt").write_text(raw)
    return [{"mode": int(i), "name": names[int(i)], "enabled": bool(int(v))} for i, v in (line.split() for line in raw.splitlines())]


def scenario(roster: list[dict]) -> dict:
    sc = replay.select_profile(replay.load_scenario(HERE / "s3_music_regression.json"), "fe")
    modes = [r["mode"] for r in roster if r["enabled"]]
    sc["assets"]["visual_music"] = {"kind": "concat", "qualification": "real_music", "segments": [{"asset": "loreen_src", "from_ms": 0, "to_ms": int(len(modes)*64*7.5), "label": "approved inventory Loreen excerpt; 64 hops per enabled effect"}]}
    base = ["secondary_enabled=true", "edge_enabled=false", "palette_mode=true", "secondary_palette_mode=true", "palette_index=12", "secondary_palette_index=27", "photons=0.70", "secondary_photons=0.55", "base_coat=false", "secondary_base_coat=false", "auto_color_shift=false", "secondary_auto_color_shift=false"]
    commands = [{"hop":0,"text":s} for s in base if not s.startswith(("photons=", "secondary_photons=", "auto_color_shift=", "secondary_auto_color_shift="))]
    for index, mode in enumerate(modes):
        commands += [{"hop":index*64,"text":f"set_mode={mode}"}, {"hop":index*64,"text":f"secondary_mode={mode}"}]
    sweep = {"purpose":"All enabled effects on BOTH edges; actual native paired output; no optical judgement.","pcm":"visual_music","epoch":{"policy":"declared","us":1000000},"capture":{"every":2},"commands":commands}
    sc["assets"]["modifier_music"] = {"kind":"concat","qualification":"real_music","segments":[{"asset":"loreen_src","from_ms":0,"to_ms":1920,"label":"same approved inventory excerpt, 256 hops"}]}
    sc["cases"] = {"all_modes": sweep}
    common = [{"hop":0,"text":s} for s in base + ["set_mode=32","secondary_mode=32","mirror_enabled=false","secondary_mirror_enabled=false"]]
    def case(extra):
        return {"purpose":"Mode32 modifier transfer at hop64 on identical real PCM; paired final buffers.","pcm":"modifier_music","epoch":{"policy":"declared","us":1000000},"capture":{"end_hop":256,"every":1},"commands":common+extra}
    sc["cases"]["modifier_base"] = case([])
    modifiers = {"a_zero":["photons=0"],"b_zero":["secondary_photons=0"],"a_reverse":["reverse_order=true"],"b_reverse":["secondary_reverse_order=true"],"a_filter":["incandescent_filter=1"],"a_palette":["palette_index=27"],"b_palette":["secondary_palette_index=12"],"dither":["temporal_dithering=false"],"a_incandescent":["incandescent_mode=true"],"b_incandescent":["secondary_incandescent_mode=true"],"a_look":["look=1"],"b_look":["secondary_look=1"],"edge":["edge_enabled=true","edge_mode=analogous","edge_strength=1","edge_spread=60"]}
    for name, texts in modifiers.items():
        sc["cases"][name] = case([{"hop":64,"text":s} for s in texts])
    disabled=[r["mode"] for r in roster if not r["enabled"]]
    sc["cases"]["disabled_modes"]=case([cmd for i,m in enumerate(disabled) for cmd in ({"hop":i*24,"text":f"set_mode={m}"},{"hop":i*24,"text":f"secondary_mode={m}"})])
    sc["comparisons"] = []
    sc["suites"] = {"visual":list(sc["cases"])}
    return sc


def frame_metrics(frames, edge):
    payloads = [getattr(f,edge) for f in frames]
    if any(len(p)!=960 for p in payloads):
        raise ValueError("not 160 complete 48-bit pixels")
    words = [int.from_bytes(p[i:i+2],"big") for p in payloads for i in range(0,len(p),2)]
    return {"frames":len(payloads),"nonzero_frames":sum(any(p) for p in payloads),"unique_frames":len(set(payloads)),"max_word":max(words,default=0),"sub8bit_words":sum((v&255)!=(v>>8) for v in words),"sha256":hashlib.sha256(b"".join(payloads)).hexdigest()}


def sweep_metrics(cap, roster):
    modes = [r for r in roster if r["enabled"]]
    by_hop = replay._by_hop(cap,96)
    rows=[]
    for index,row in enumerate(modes):
        selected=[f for h,f in by_hop.items() if index*64<=h<(index+1)*64]
        observed=sorted({f.mode for f in selected})
        transition_frames=sum(f.mode!=row["mode"] for f in selected)
        selected=[f for f in selected if f.mode==row["mode"]]
        edges={edge:frame_metrics(selected,edge) for edge in ("A","B")}
        snapshots=[s for s in cap.show_states if s.get("when")=="cmd" and int(s.get("hop",-1))==index*64]
        secondary_ok=bool(snapshots) and replay._decode_show_state(snapshots[-1]["hex"])["secondary"]["lightshow_mode"]==row["mode"]
        rows.append({**row,"observed_modes":observed,"secondary_readback_match":secondary_ok,"transition_frames":transition_frames,"dispatch_match":len(selected)>0,"edges":edges,"coverage":"OUTPUT_OBSERVED" if selected and all(m["nonzero_frames"] for m in edges.values()) else "DARK_OUTPUT_REQUIRES_LONGER_OR_EVENT_STIMULUS"})
    return rows


def compare(base, changed, name):
    a=replay._by_hop(base,96); b=replay._by_hop(changed,96)
    changed_edge="B" if name.startswith("b_") or name=="edge" else "A"
    other="A" if changed_edge=="B" else "B"
    rows=[(a[h],b[h]) for h in a.keys()&b.keys() if h>=64]
    diffs=sum(getattr(x,changed_edge)!=getattr(y,changed_edge) for x,y in rows)
    reasons=[]
    if not rows: reasons.append("no paired post-command frames")
    coupled=name in ("edge","a_look")
    other_diffs=sum(getattr(x,other)!=getattr(y,other) for x,y in rows)
    if not coupled and other_diffs: reasons.append("untargeted edge changed")
    if coupled and not other_diffs: reasons.append("declared dual-edge/follow-primary relation not exercised")
    if name=="a_zero":
        state=replay._decode_show_state(changed.show_states[-1]["hex"])
        if abs(state["primary"]["photons"]-0.05)>1e-6: reasons.append("primary zero request must clamp to product0.05 floor")
    if name=="b_zero" and any(any(getattr(y,changed_edge)) for x,y in rows): reasons.append("zero photons emitted nonzero pixels")
    if name.endswith("_reverse"):
        def reverse(p): return b"".join(p[i:i+6] for i in range(len(p)-6,-1,-6))
        if any(reverse(getattr(x,changed_edge))!=getattr(y,changed_edge) for x,y in rows): reasons.append("whole 48-bit pixel reversal mismatch")
    if name=="dither" and diffs!=0: reasons.append("WS2816 output changed under inapplicable RGB8 dither")
    if diffs==0 and name!="dither": reasons.append("modifier not exercised by captured content")
    return {"name":name,"paired_frames":len(rows),"changed_frames":diffs,"other_edge_changed_frames":other_diffs,"relation":"both edges by declared dual/follow setting" if coupled else "isolated edge","status":"PASS" if not reasons else "FAIL","reasons":reasons}


def disabled_checks(cap, roster):
    disabled=[r["mode"] for r in roster if not r["enabled"]]
    enabled={r["mode"] for r in roster if r["enabled"]}
    frames=replay._by_hop(cap,96)
    checks=[]
    for i,m in enumerate(disabled):
        state=[s for s in cap.show_states if s.get("when")=="cmd" and int(s.get("hop",-1))==i*24]
        want=next((m+j)%len(roster) for j in range(len(roster)) if (m+j)%len(roster) in enabled)
        got=replay._decode_show_state(state[-1]["hex"])["secondary"]["lightshow_mode"] if state else None
        settled=[(h,f) for h,f in frames.items() if i*24+5<=h<(i+1)*24]
        last=max(settled,key=lambda pair:pair[0]) if settled else None
        primary=last[1].mode if last else None
        checks.append({"requested":m,"expected_next_enabled":want,"secondary_readback":got,"settled_primary":primary,"settled_hop":last[0] if last else None,"status":"PASS" if got==want and primary==want else "FAIL"})
    if any(f.mode not in enabled for f in cap.frames): checks.append({"status":"FAIL","reason":"disabled primary mode reached capture"})
    return checks


def long_scenario(roster, extended=False):
    sc=scenario(roster)
    sc["assets"]["mode_quiet_return"]={"kind":"concat","qualification":"diagnostic_composite","segments":[{"asset":"loreen_src","from_ms":74000,"to_ms":80000,"label":"approved Loreen active"},{"zeros_ms":6000,"label":"declared diagnostic zeros; not natural quiet"},{"asset":"loreen_src","from_ms":74000,"to_ms":80000 if extended else 76000,"label":"same approved Loreen return"}]}
    sc["cases"]={f"long_{r['mode']}":{"purpose":"Full-cadence active 6s / declared zero 6s / return 2s; output arithmetic and motion observations, no aesthetic threshold.","pcm":"mode_quiet_return","partial_hop":"zero_pad","epoch":{"policy":"declared","us":1000000},"capture":{"every":1,"start_hop":400 if extended else 0,"end_hop":2400 if extended else 1867},"commands":[{"hop":0,"text":t} for t in ["secondary_enabled=true","edge_enabled=false","base_coat=false","secondary_base_coat=false",f"set_mode={r['mode']}",f"secondary_mode={r['mode']}"]]} for r in roster if r["enabled"]}
    sc["suites"]={"visual":list(sc["cases"])}
    if extended:
        for case in sc["cases"].values(): case["purpose"]="6s active /6s zero /6s return; fullcadence capture hops400..2399; beat-event eligibility recorded, no aesthetic threshold."
    return sc


def long_metrics(cap,mode, extended=False):
    import struct
    frames=replay._by_hop(cap,96)
    rows={}; reasons=[]
    state=replay._decode_show_state(cap.show_states[-1]["hex"]) if cap.show_states else {}
    expected=list(range(400,2400)) if extended else list(range(1867))
    if sorted(frames)!=expected: reasons.append("missing full-cadence frame(s)")
    if not frames or any(f.mode!=mode for h,f in frames.items() if h>=5): reasons.append("primary dispatch mismatch after transition")
    if state.get("secondary",{}).get("lightshow_mode")!=mode: reasons.append("secondary mode readback mismatch")
    for edge in ("A","B"):
        parts={"active":[f for h,f in frames.items() if 5<=h<800],"quiet_last_second":[f for h,f in frames.items() if 1467<=h<1600],"return":[f for h,f in frames.items() if 1600<=h<(2400 if extended else 1867)]}
        row={k:frame_metrics(v,edge) for k,v in parts.items()}
        payloads=[getattr(f,edge) for f in frames.values()]
        row["motion"]={"adjacent_changed_frames":sum(a!=b for a,b in zip(payloads,payloads[1:])),"max_adjacent_word_delta":max((abs(int.from_bytes(a[i:i+2],"big")-int.from_bytes(b[i:i+2],"big")) for a,b in zip(payloads,payloads[1:]) for i in range(0,960,2)),default=0),"full_cadence":True,"appeal_threshold":None}
        row["centre_mirror_mismatches"]=sum(any(p[i*6:i*6+6]!=p[(159-i)*6:(160-i)*6] for i in range(80)) for p in payloads)
        if state.get("primary" if edge=="A" else "secondary",{}).get("mirror_enabled") and row["centre_mirror_mismatches"]: reasons.append(edge+" mirror-enabled output is asymmetric; inspect effect-specific contract")
        if row["quiet_last_second"]["nonzero_frames"]: reasons.append(edge+" nonzero output in final quiet second; inspect persistence and silence producer")
        if not row["return"]["nonzero_frames"]: reasons.append(edge+" did not relight on return")
        rows[edge]=row
    quiet_states=[cap.render_state[f.index] for h,f in frames.items() if 1467<=h<1600 and f.index in cap.render_state]
    scales=[struct.unpack('<f',int(r[3],16).to_bytes(4,'little'))[0] for r in quiet_states]
    meaning=[cap.meanings[f.index] for h,f in frames.items() if h>=1600 and f.index in getattr(cap,"meanings",{})]
    eligibility={"confidence_max":max((float(m.p_confidence) for m in meaning),default=None),"locked_frames":sum(m.p_locked for m in meaning),"beat_tick_frames":sum(m.p_beat_tick for m in meaning),"source_confident_frames":sum(float(m.p_confidence)>=0.45 for m in meaning) if mode in (20,27) else None,"tentative_confidence_frames":sum(float(m.p_confidence)>=0.30 for m in meaning) if mode in (20,27) else None,"scope":"Observed confidence and published beat state only. Fresh onset admission and consumer policy require their own event comparison; confidence alone does not qualify a beat cue."}
    return {"mode":mode,"return_eligibility":eligibility,"extended":extended,"edges":rows,"quiet_silent_scale_min":min(scales,default=None),"quiet_silent_scale_max":max(scales,default=None),"status":"FAIL" if reasons else "PASS","reasons":reasons,"show_state":state,"mirror_note":"Mirror-enabled paired-pixel equality; any mismatch requires effect-specific source review before repair."}


def rescore_long(out):
    report=json.loads((out/"result.json").read_text())
    checks=[]
    for cid,result in report["cases"].items():
        if cid.startswith("long_") and result["status"]=="PASS":
            cap=ec.decode((out/cid/"uart.txt").read_text())
            checks.append(long_metrics(cap,int(cid[5:])))
    expected={r["mode"] for r in report["roster"] if r["enabled"]}
    observed={r["mode"] for r in checks}
    summary={"checks":checks,"expected_modes":sorted(expected),"observed_modes":sorted(observed),"missing_modes":sorted(expected-observed),"status":"PASS" if expected==observed and all(r["status"]=="PASS" for r in checks) else "FAIL_OR_INCOMPLETE"}
    (out/"strengthened-check.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


def select_cases(sc, requested):
    """Resolve the requested work and its modifier baseline before execution."""
    cases=list(sc["cases"]) if requested=="all" else requested.split(",")
    unknown=[cid for cid in cases if cid not in sc["cases"]]
    if unknown: raise ValueError(f"unknown or empty visual cases: {unknown}")
    if len(cases)!=len(set(cases)): raise ValueError("duplicate visual cases")
    modifiers=[cid for cid in cases if cid not in ("all_modes","disabled_modes","modifier_base") and not cid.startswith("long_")]
    if modifiers:
        if "modifier_base" not in sc["cases"]: raise ValueError("modifier scenario has no baseline")
        cases=["modifier_base"]+[cid for cid in cases if cid!="modifier_base"]
    return cases,modifiers


def modifier_comparison_errors(comparisons, required):
    errors=[]
    for cid in required:
        matches=[row for row in comparisons if row.get("name")==cid]
        if len(matches)!=1:
            errors.append(f"{cid}: expected one semantic comparison, found {len(matches)}")
        elif matches[0].get("status")!="PASS":
            errors.append(f"{cid}: semantic comparison did not pass")
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    parser.add_argument("--build-dir",required=True)
    parser.add_argument("--cases",default="all_modes")
    parser.add_argument("--long",action="store_true")
    parser.add_argument("--rescore",action="store_true")
    parser.add_argument("--extended",action="store_true")
    args=parser.parse_args(); out=Path(args.output).resolve()
    if args.rescore: return 0 if rescore_long(out)["status"]=="PASS" else 1
    out.mkdir(parents=True,exist_ok=False)
    build=Path(args.build_dir).resolve()
    roster=compiled_roster(out); sc=long_scenario(roster,args.extended) if args.long else scenario(roster)
    (out/"scenario.json").write_text(json.dumps(sc,indent=2)+"\n")
    lock=json.loads((HERE/"tool-lock.json").read_text()); emu,tried=replay.resolve_esp_emu(lock)
    if emu is None: raise RuntimeError(tried)
    report={"source":replay.source_identity(),"app_sha256":replay.sha256_file(build/"firmware.bin"),"roster":roster,"scope":"software PCM-to-packed-buffer only; no LED timing or optical judgement","cases":{},"comparisons":[]}
    results={}; assets={}
    cases,required_comparisons=select_cases(sc,args.cases)
    report["requested_cases"]=args.cases
    report["execution_cases"]=cases
    report["required_comparisons"]=required_comparisons
    for cid in cases:
        print("case",cid,flush=True)
        result=replay.run_case(sc,cid,out,emu,build,assets,results); results[cid]=result
        report["cases"][cid]={k:v for k,v in result.items() if not k.startswith("_")}
        if result.get("_capture"):
            if cid=="all_modes": report["mode_coverage"]=sweep_metrics(result["_capture"],roster)
            elif cid=="disabled_modes":
                report["disabled_mode_checks"]=disabled_checks(result["_capture"],roster)
            elif cid.startswith("long_"):
                report.setdefault("long_checks",[]).append(long_metrics(result["_capture"],int(cid[5:]),args.extended))
            elif cid in required_comparisons and results.get("modifier_base",{}).get("_capture"):
                report["comparisons"].append(compare(results["modifier_base"]["_capture"],result["_capture"],cid))
        report["comparison_errors"]=modifier_comparison_errors(report["comparisons"],required_comparisons)
        (out/"result.json").write_text(json.dumps(report,indent=2)+"\n")
        print(cid,"transport",result["status"],result.get("reasons"),flush=True)
        if cid.startswith("long_") and report.get("long_checks"):
            check=report["long_checks"][-1]
            print(cid,"semantic",check["status"],check["reasons"],flush=True)
    return 1 if report.get("comparison_errors") or any(c["status"]!="PASS" for c in report.get("long_checks",[])) or any(r["status"]!="PASS" for r in report["cases"].values()) or any(c["status"]!="PASS" for c in report["comparisons"]) or any(c["status"]!="PASS" for c in report.get("disabled_mode_checks",[])) or any(not c["dispatch_match"] or not c["secondary_readback_match"] or c["coverage"]!="OUTPUT_OBSERVED" for c in report.get("mode_coverage",[])) else 0

if __name__=="__main__": raise SystemExit(main())
