#!/usr/bin/env python3
"""Fixed native-FE novelty replay against independent annotated beat seconds.

No phase alignment, octave correction, model fitting or onset labels. Strict
70 ms beat matching and 5 s warm-up follow mir_eval.beat conventions:
https://mir-eval.readthedocs.io/latest/api/beat.html
"""
import argparse,bisect,hashlib,json,math,re,subprocess,wave
from pathlib import Path
import numpy as np
import tempo_lane_replay as lane
import tempo_lane_emu as emu
import s3_audio_qualification_recover as recovery
ROOT=Path(__file__).resolve().parents[2]
TOLERANCE=.070
WARMUP=5.0

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def beat_metrics(reference,predictions):
    ref=sorted(reference);pred=sorted(predictions)
    if any(not math.isfinite(x) for x in ref+pred):raise ValueError('non-finite beat time')
    if any(b<=a for a,b in zip(ref,ref[1:])):raise ValueError('reference beats not unique')
    i=j=0;matches=0
    while i<len(ref) and j<len(pred):
        if pred[j]<ref[i]-TOLERANCE:j+=1
        elif pred[j]>ref[i]+TOLERANCE:i+=1
        else:matches+=1;i+=1;j+=1
    precision=matches/len(pred) if pred else 0.;recall=matches/len(ref) if ref else 0.
    errors=[t-min(ref,key=lambda r:abs(t-r)) for t in pred] if ref else []
    return {'reference_beats':len(ref),'predicted_beats':len(pred),'matched':matches,
            'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0.,
            'nearest_reference_signed_error_s':distribution(errors)}

def distribution(values):
    return {'count':len(values),'p05':float(np.quantile(values,.05)),
            'median':float(np.median(values)),'p95':float(np.quantile(values,.95)),
            'mean':float(np.mean(values))} if values else {'count':0,'p05':None,'median':None,'p95':None,'mean':None}

def phase_errors(reference,frames):
    errors=[]
    for t,phase,locked in frames:
        i=bisect.bisect_right(reference,t)-1
        if not locked or i<0 or i+1>=len(reference):continue
        truth=(t-reference[i])/(reference[i+1]-reference[i])
        errors.append((phase-truth+.5)%1.-.5)
    return {'signed_cycles':distribution(errors),'absolute_cycles':distribution([abs(x)for x in errors])}

def native_rows(uart):
    rows=[];native=[];epochs=[]
    for line in uart.splitlines():
        a=line.split(',')
        if a[0]=='N':rows.append((int(a[1]),float(a[2]),int(a[4])))
        elif a[0]=='V':native.append((int(a[2]),float(a[6]),float(a[7]),float(a[8]),int(a[9]),int(a[10])))
        elif line.startswith('EMU_EPOCH '):epochs.append(int(re.search(r'epoch_us=(\d+)',line)[1]))
    if not rows or [r[0]for r in rows]!=list(range(1,len(rows)+1)):raise ValueError('incomplete/duplicate N generations')
    if epochs!=[1000000]:raise ValueError('epoch differs from fixed 1 s replay convention')
    if not native:raise ValueError('no native V samples for parity')
    if any(not all(math.isfinite(v)for v in r[1:4]) or r[4]not in(0,1) or r[5]not in(0,1) for r in native):raise ValueError('invalid native V values')
    return rows,native

def validate_host_generations(gens,expected):
    if gens!=list(range(1,expected+1)):raise ValueError('host generation gap/duplicate/order')

def score_case(row,capture,binary,out,runtime,elf_hash,app_hash):
    if int((capture/'exit_code.txt').read_text())!=0:raise ValueError('capture not complete/exit nonzero')
    if sha(capture/'firmware.elf')!=elf_hash:raise ValueError('capture ELF differs from frozen runtime')
    if sha(row['path'])!=row['sha256']:raise ValueError('source audio hash mismatch')
    if row['excerpt']['start_ms']!=0 or row['excerpt']['duration_ms'] is not None:raise ValueError('only frozen full clips supported')
    with wave.open(row['path']) as w:duration=w.getnframes()/w.getframerate()
    out.mkdir()
    if sha(runtime/'firmware.bin')!=app_hash:raise ValueError('frozen app mismatch')
    app=(runtime/'firmware.bin').read_bytes()
    with (capture/'flash-run.bin').open('rb') as f:
        f.seek(0x10000)
        if f.read(len(app))!=app:raise ValueError('executed app differs from frozen app')
    uart=capture/'uart.txt';uart_text=uart.read_text();rows,native=native_rows(uart_text)
    streams=out/'streams.json';streams.write_text(json.dumps(emu.extract(uart_text)))
    _,integrity,error=recovery.recover((row,out,out,capture,streams))
    if error or integrity is None:raise ValueError('capture/source identity: '+str(error))
    if len(rows)*.0075<duration or len(rows)*.0075-duration>.020:raise ValueError('capture duration mismatch')
    ann=ROOT/'_scratch/esp-emulator/tempo-lock-r1/validation/raw/gtzan_tempo_beat-main/beats'/('gtzan_'+row['id'].split(':')[1]+'.beats')
    reference=[float(x.split()[0]) for x in ann.read_text().splitlines() if x.strip()]
    if len(reference)<2 or any(not math.isfinite(t)or t<0 for t in reference) or any(b<=a for a,b in zip(reference,reference[1:])):raise ValueError('empty/nonfinite/unordered annotation')
    feed=out/'input.txt';raw=out/'trajectory.txt'
    feed.write_text(''.join(f'{g} {lane.frame_ms(g)} {nov:.9g} {silent}\n'for g,nov,silent in rows))
    with feed.open() as f,raw.open('w') as o:subprocess.run([str(binary)],stdin=f,stdout=o,check=True,timeout=90)
    frames=[];allframes={};ticks=[];host_generations=[]
    for line in raw.read_text().splitlines():
        a=line.split();g=int(a[1]);bpm,conf=float(a[2]),float(a[3]);locked,tick=int(a[4]),int(a[5]);phase=float(a[6]);t=g*.0075
        if not all(math.isfinite(x)for x in (bpm,conf,phase)) or locked not in(0,1) or tick not in(0,1):raise ValueError('invalid host values')
        host_generations.append(g)
        allframes[g]=(bpm,phase,conf,locked,tick)
        if WARMUP<=t<=duration:
            frames.append((t,phase,locked))
            if tick:ticks.append(t)
    validate_host_generations(host_generations,len(rows))
    differences=[]
    for g,bpm,phase,conf,locked,tick in native:
        b,p,c,l,k=allframes[g]
        if abs(b-bpm)>.051 or abs(p-phase)>.00011 or abs(c-conf)>.00011 or l!=locked or k!=tick:
            differences.append({'gen':g,'native':[bpm,phase,conf,locked,tick],'host':[b,p,c,l,k]})
    refs=[t for t in reference if WARMUP<=t<=duration]
    result={'id':row['id'],'genre':row['genre'],'duration_s':duration,'uart_sha256':sha(uart),
            'source_audio_sha256':row['sha256'],'annotation':str(ann),'annotation_sha256':sha(ann),
            'capture_integrity':integrity,'annotation_count':len(reference),'metrics':beat_metrics(refs,ticks),
            'locked_phase_error':phase_errors(reference,frames),'locked_fraction':sum(f[2]for f in frames)/len(frames),
            'native_comparison_frames':len(native),'native_host_mismatches':differences,
            'predicted_seconds':ticks,'scored_reference_seconds':refs}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--preregistration',type=Path,required=True);p.add_argument('--captures',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--flags-receipt',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);a=p.parse_args()
    frozen=json.loads(a.preregistration.read_text());rows=frozen['rows']
    receipt=json.loads(a.flags_receipt.read_text())
    if receipt['env']!='k1_fe_emu' or receipt['elf_sha256']!=frozen['runtime']['sha256']['firmware.elf'] or receipt['app_sha256']!=frozen['runtime_app_sha256']:raise ValueError('FE runtime receipt mismatch')
    flags=receipt['effective_env']['build_flags']
    required={'-D'+d for d in lane.PROD}
    if not required.issubset(flags):raise ValueError('shipping tempo flags missing')
    allowed={f.split('=')[0]for f in required}|{'-DK1_TEMPO_CONSUMER_BANDS_V1'}
    if any(f.startswith('-DK1_TEMPO_') and f.split('=')[0] not in allowed for f in flags):raise ValueError('experimental tempo flags are not shipping FE')
    manifest=ROOT/'tests/fixtures/tempo_corpus/validation_gtzan_v1.json'
    if sha(manifest)!=frozen['manifest_sha256']:raise ValueError('frozen V1 manifest mismatch')
    selected={}
    for row in sorted(json.loads(manifest.read_text())['rows'],key=lambda r:r['id']):selected.setdefault(row['genre'],row)
    if rows!=list(selected.values()):raise ValueError('selection is not the fixed first V1 clip per genre')
    if len(rows)!=10 or len({r['genre']for r in rows})!=10:raise ValueError('fixed ten-genre set required')
    a.output.mkdir(parents=True,exist_ok=False);binary=lane.build(a.output,[],False)
    result={'schema':'k1-s3-annotated-beat/1','preregistration_sha256':sha(a.preregistration),'effective_flags_receipt_sha256':sha(a.flags_receipt),
            'scope':'Current shipping tempo C++ on native FE sqrt novelty; original annotated beat level, no octave folding or phase alignment',
            'metric_reference':'https://mir-eval.readthedocs.io/latest/api/beat.html','tolerance_s':TOLERANCE,'warmup_s':WARMUP,
            'source_sha256':sha(lane.FIRMWARE/'audio/k1_tempo.cpp'),
            'source_dependencies':{str(p.relative_to(ROOT)):sha(p)for p in sorted((lane.FIRMWARE/'audio').glob('*.h'))},
            'driver_sha256':hashlib.sha256(lane.DRIVER.encode()).hexdigest(),'complete':False,'cases':[]}
    for row in rows:
        rid=row['id'].replace(':','_');capture=a.captures/rid/('phase-'+rid)
        result['cases'].append(score_case(row,capture,binary,a.output/rid,a.runtime,frozen['runtime']['sha256']['firmware.elf'],frozen['runtime_app_sha256']))
        (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(row['id'],result['cases'][-1]['metrics'],flush=True)
    tp=sum(c['metrics']['matched']for c in result['cases']);nr=sum(c['metrics']['reference_beats']for c in result['cases']);npred=sum(c['metrics']['predicted_beats']for c in result['cases'])
    result['aggregate']={'matched':tp,'reference_beats':nr,'predicted_beats':npred,'precision':tp/npred if npred else 0.,'recall':tp/nr if nr else 0.,'f1':2*tp/(nr+npred) if nr+npred else 0.}
    result['complete']=True
    result['native_host_parity']=all(not c['native_host_mismatches']for c in result['cases'])
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');return int(not result['native_host_parity'])
if __name__=='__main__':raise SystemExit(main())
