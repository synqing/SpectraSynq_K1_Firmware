#!/usr/bin/env python3
"""Recover interrupted E1 captures after checking audio/blob identity; no hardware."""
import argparse
import hashlib
import json
import struct
import zlib
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import tempo_lane_emu as emu

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def validate_streams(d,expected):
    n,p=d.get("N",[]),d.get("P",[])
    gens=list(range(1,expected+1))
    if len(n)!=expected or len(p)!=expected: raise ValueError("truncated N/P stream")
    if [r[0]for r in n]!=gens or [r[0]for r in p]!=gens: raise ValueError("N/P generation gap/duplicate/alignment")
    for row in n:
        if len(row)!=3 or not math.isfinite(float(row[1])) or row[2]not in(0,1):raise ValueError("invalid novelty/silence record")
    for row in p:
        if len(row)!=2 or len(row[1])!=320 or len(bytes.fromhex(row[1]))!=160:raise ValueError("spectrum width/encoding")


def recover(args):
    row,runs,out=args[:3]; cid=row["id"]; folder=Path(args[3]) if len(args)>3 else runs/("lane-"+cid.replace(":","_")); stream_file=Path(args[4]) if len(args)>4 else folder/"streams.json"
    if not stream_file.exists(): return cid,None,"capture missing"
    try:
        assert (folder/"exit_code.txt").read_text().strip()=="0", "emulator exit"
        assert sha(Path(row["path"]))==row["sha256"], "source audio hash"
        blob=(folder/"scenario-blob.bin").read_bytes();h=struct.unpack("<8sII48s14IQ124sI",blob[:256])
        assert h[0]==b"K1EMUSC2" and h[1:3]==(2,256) and h[4:6]==(12800,96), "blob schema/rate/hop"
        assert len(blob)==h[16], "blob length"
        assert zlib.crc32(blob[:252]) & 0xffffffff == h[-1], "header CRC"
        assert zlib.crc32(blob[256:]) & 0xffffffff == h[17], "payload CRC"
        work=out/("decode-"+cid.replace(":","_"));work.mkdir(exist_ok=True)
        ex=row.get("excerpt") or {}
        pcm,decode=emu.decode_like_run(row["path"],ex.get("start_ms") or 0,ex.get("duration_ms"),work)
        assert pcm==blob[h[14]:h[14]+2*h[6]], "PCM differs from independent audio decode"
        d=json.loads(stream_file.read_text()); specs={x[0]:x[1] for x in d["P"]}
        # The cached JSON is not authority: compare both projections to raw UART.
        uart_hash=hashlib.sha256(); uart_n=[]; uart_p=[]
        with (folder/"uart.txt").open("rb") as raw:
            for line in raw:
                uart_hash.update(line)
                if line.startswith(b"N,"):
                    parts=line.decode().strip().split(",")
                    uart_n.append([int(parts[1]),parts[2],int(parts[4])])
                elif line.startswith(b"P,"):
                    parts=line.decode().strip().split(",")
                    uart_p.append([int(parts[1]),parts[2]])
        assert uart_n==d["N"] and uart_p==d["P"], "cached stream differs from raw UART"
        validate_streams(d,(h[6]+h[7]+h[5]-1)//h[5])
        assert [r[0] for r in d["N"]]==list(range(1,len(d["N"])+1)), "generation gap"
        body="".join(f"{g} {nov} {sil} {specs[g]}\n" for g,nov,sil in d["N"])
        path=out/(cid.replace(":","_")+".tsv");path.write_text(body)
        meta={"file":path.name,"sha256":sha(path),"gens":len(d["N"]),"source_audio_sha256":row["sha256"],
            "pcm_sha256":hashlib.sha256(pcm).hexdigest(),"source_uart":str(folder/"uart.txt"),
            "source_uart_sha256":uart_hash.hexdigest(),"elf_sha256":sha(folder/"firmware.elf"),
            "blob_sha256":sha(folder/"scenario-blob.bin"),"streams_sha256":sha(stream_file),"decode":decode}
        return cid,meta,None
    except Exception as e: return cid,None,str(e)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--runs",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--workers",type=int,default=4);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    rows=json.loads(a.manifest.read_text())["rows"]
    with ProcessPoolExecutor(a.workers) as pool: results=list(pool.map(recover,[(r,a.runs,a.out) for r in rows]))
    clips={cid:meta for cid,meta,err in results if meta};errors={cid:err for cid,meta,err in results if err}
    d={"schema":"k1-tempo-fixture-set/1","source_manifest":str(a.manifest),"source_manifest_sha256":sha(a.manifest),
       "clips":clips,"errors":errors,"complete":not errors,"expected":len(rows)}
    (a.out/"index.json").write_text(json.dumps(d,indent=1)+"\n")
    print(json.dumps({"verified":len(clips),"errors":errors}));return int(bool(errors))
if __name__=="__main__":raise SystemExit(main())
