#!/usr/bin/env python3
"""Capture frozen validation PCM through a checksum-verified historical emulator image.
No builds, model fitting, device access, manifest edits or scoring-policy changes.
"""
import argparse,concurrent.futures,copy,hashlib,json,sys
from pathlib import Path
import tempo_lane_emu as lane
import s3_audio_qualification_recover as recovery
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/esp_emulator'))
import run as replay

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate_record(row,rec,runtime,checks):
    if rec.get('status')!='PASS' or rec.get('source_sha256')!=row['sha256']:raise ValueError('record source/status mismatch')
    folder=Path(rec['capture']);stream=Path(rec['streams'])
    if sha(folder/'firmware.elf')!=sha(runtime/'firmware.elf'):raise ValueError('retained runtime ELF mismatch')
    app=(runtime/'firmware.bin').read_bytes()
    with (folder/'flash-run.bin').open('rb')as f:f.seek(0x10000);actual=f.read(len(app))
    if actual!=app:raise ValueError('retained executed app mismatch')
    checks.mkdir(parents=True,exist_ok=True)
    cid,meta,error=recovery.recover((row,checks,checks,folder,stream))
    if error or meta is None:raise ValueError('audio stream verification: '+str(error))
    return meta


def capture(row,out,runtime,capture_every=1):
    rid=row['id'];dest=out/rid.replace(':','_');dest.mkdir()
    try:
        if sha(row['path'])!=row['sha256']:raise ValueError('source audio hash mismatch')
        case= {'id':rid,'source':{'kind':'wav','path':row['path'],'start_ms':(row.get('excerpt')or{}).get('start_ms')or 0,'duration_ms':(row.get('excerpt')or{}).get('duration_ms')}}
        pcm,meta=lane.case_pcm(case,dest)
        sc=replay.load_scenario(ROOT/'tools/esp_emulator/s3_music_regression.json');cid='validation-'+rid.replace(':','_');aid='pcm'
        sc['assets'][aid]={'kind':'c_array_inc','qualification':'real_music','path':'-'}
        hops=-(-(len(pcm)//2)//96)
        sc['cases'][cid]={'purpose':'Frozen V2 validation capture, no tuning','pcm':aid,'epoch':{'policy':'declared','us':1000000},'capture':{'start_hop':1600,'end_hop':min(3600,hops),'every':capture_every},'partial_hop':'zero_pad','trace_novelty':True}
        assets={aid:(pcm,{'id':aid,'samples':len(pcm)//2,'sha256':hashlib.sha256(pcm).hexdigest(),**meta})}
        lock=json.loads((replay.HERE/'tool-lock.json').read_text());emu,_=replay.resolve_esp_emu(lock)
        if emu is None:raise RuntimeError('pinned emulator unavailable')
        rec=replay.run_case(sc,cid,dest,emu,runtime,assets,{})
        streams=lane.extract(rec.get('_uart',''));(dest/'streams.json').write_text(json.dumps(streams,separators=(',',':')))
        result={'id':rid,'status':rec['status'],'reasons':rec.get('reasons',[]),'source_sha256':row['sha256'],'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'streams':str(dest/'streams.json'),'capture':str(dest/cid),'counts':{k:len(v)for k,v in streams.items()},'pixel_capture_every_hops':capture_every}
        result['audio_integrity']=validate_record(row,result,runtime,dest/'verified')
        return result
    except Exception as e:return {'id':rid,'status':'FAIL','reasons':[repr(e)]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--preregistration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pilot',action='store_true');p.add_argument('--parallel',type=int,default=3);p.add_argument('--reuse',type=Path);p.add_argument('--pixel-every',type=int,choices=(1,100),default=1,help='Pixel diagnostics only; complete N/P audio traces and processing remain enabled.');a=p.parse_args()
    frozen=json.loads(a.preregistration.read_text());assert sha(a.manifest)==frozen['validation_manifest_sha256'];assert sha(a.runtime/'firmware.bin')==frozen['runtime_app_sha256'];assert sha(a.runtime/'firmware.elf')==frozen['runtime_elf_sha256'];assert sha(frozen['model_path'])==frozen['model_sha256']
    rows=json.loads(a.manifest.read_text())['rows'];assert len(rows)==483;assert all(r['role']=='validation'and r['split']=='V2'for r in rows)
    if a.pilot:rows=rows[:1]
    a.output.mkdir(parents=True,exist_ok=False);result={'schema':'k1-s3-validation-capture/1','preregistration_sha256':sha(a.preregistration),'runtime':json.loads((a.runtime/'identity.json').read_text()),'expected':len(rows),'pilot':a.pilot,'cases':[]}
    reused=[]
    if a.reuse:
        prior=json.loads(a.reuse.read_text());assert prior['preregistration_sha256']==sha(a.preregistration)
        lookup={r['id']:r for r in rows}
        for rec in prior['cases']:
            assert rec['status']=='PASS' and rec['source_sha256']==lookup[rec['id']]['sha256']
            rec['audio_integrity']=validate_record(lookup[rec['id']],rec,a.runtime,a.output/'verified')
            reused.append(rec)
        result['cases'].extend(reused)
    seen={r['id']for r in reused}
    if len(seen)!=len(reused):raise ValueError('duplicate reused case')
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.parallel)as pool:
        jobs=[pool.submit(capture,r,a.output,a.runtime,a.pixel_every)for r in rows if r['id']not in seen]
        for f in concurrent.futures.as_completed(jobs):
            rec=f.result();result['cases'].append(rec);(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(rec['id'],rec['status'],rec.get('reasons'),flush=True)
    return int(any(r['status']!='PASS'for r in result['cases'])or len(result['cases'])!=len(rows))
if __name__=='__main__':raise SystemExit(main())
