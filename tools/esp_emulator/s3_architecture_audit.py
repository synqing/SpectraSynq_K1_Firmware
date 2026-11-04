#!/usr/bin/env python3
"""Inspect the actual S3 image and existing target traces; never flash hardware.

Direct-call reachability is an inventory, not proof about indirect callbacks.
Timing windows retain their original image identity and workload.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re,statistics,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def calls(text):
    graph={}; indirect={}; current=None
    for line in text.splitlines():
        m=re.match(r'^[0-9a-fA-F]+ <(.+)>:$',line)
        if m:
            current=None if re.search(r'[+-]0x[0-9a-fA-F]+$',m[1]) else m[1]
            if current is not None: graph.setdefault(current,set())
            continue
        if current is None: continue
        m=re.search(r'\bcall(?:0|4|8|12)\s+[0-9a-fA-F]+ <(.+)>',line)
        if m:graph[current].add(m[1])
        if re.search(r'\bcallx(?:0|4|8|12)\b',line):indirect[current]=indirect.get(current,0)+1
    return graph,indirect

def reachable(graph,root):
    seen=set();todo=[root]
    while todo:
        f=todo.pop()
        if f in seen:continue
        seen.add(f);todo.extend(graph.get(f,()))
    return seen

def trace_summary(path):
    rows=collections.defaultdict(list);windows=[]
    for p in sorted(path.glob('window-*.json')):
        data=json.loads(p.read_text())['traceEvents'];local=[]
        for e in data:
            if e.get('ph')=='X' and e.get('name','').startswith('vp_'):
                rows[e['name']].append(e['dur']);local.append(e)
        if not local:raise ValueError(f'no duration events: {p}')
        windows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'start_us':min(e['ts'] for e in local),'end_us':max(e['ts']+e['dur'] for e in local)})
    if not windows:raise ValueError('No target trace windows supplied')
    return {'identity':json.loads((path/'identity.json').read_text()),'windows':windows,'durations':{k:{'samples':len(v),'mean_us':statistics.mean(v),'max_us':max(v)}for k,v in rows.items()},'scope':'Recorded primary32 / secondary18. Do not add independent maxima or transfer timings to other effects/images.'}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--elf',type=Path,required=True);ap.add_argument('--trace',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    candidates=sorted((Path.home()/'.platformio/packages').glob('toolchain-xtensa-esp-elf/bin/xtensa-esp32s3-elf-objdump'))
    if not candidates:raise SystemExit('Installed S3 objdump unavailable')
    tool=candidates[0];dis=subprocess.check_output([str(tool),'-d','-C',str(a.elf)],text=True);graph,indirect=calls(dis)
    roots=['loop()','led_thread(void*)','calculate_GDFT()'];roots=[r for r in roots if r in graph]
    if 'loop()'not in roots or 'led_thread(void*)'not in roots:raise SystemExit('Missing actual audio/render roots')
    branches={r:sorted(reachable(graph,r))for r in roots}
    nm=tool.with_name('xtensa-esp32s3-elf-nm');symbols=subprocess.check_output([str(nm),'-S','--size-sort','-C',str(a.elf)],text=True)
    buffers=[]
    for l in symbols.splitlines():
        m=re.match(r'([0-9a-f]+) ([0-9a-f]+) \w (.+)',l)
        if m and m[3] in ('leds_16','leds_16_secondary','leds_16_primary_snapshot','s_published','s_pub_spectrogram','waveform_history'):
            buffers.append({'name':m[3],'address':'0x'+m[1],'bytes':int(m[2],16),'note':'waveform_history is a pointer; its allocation is not the pointer size'if m[3]=='waveform_history'else'actual linked symbol'})
    out={'schema':'k1-s3-architecture/1','elf':{'path':str(a.elf),'sha256':hashlib.sha256(a.elf.read_bytes()).hexdigest()},'toolchain':subprocess.check_output([str(tool),'--version'],text=True).splitlines()[0],'direct_calls':{k:sorted(v)for k,v in graph.items()},'reachable':branches,'indirect_calls':indirect,'linked_buffers':buffers,'trace':trace_summary(a.trace),'limitations':['Indirect callbacks, virtual calls, inlined code and conditional runtime branches require source/actual-output review; graph is not a complete behavioural proof.','Prior trace timings retain original image and mode identity.','No device, DMA wire timing or optical access performed.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'functions':len(graph),'linked_buffers':buffers,'durations':out['trace']['durations']},indent=2))
if __name__=='__main__':main()
