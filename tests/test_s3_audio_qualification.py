"""Actual-code reproduction of the hidden silence veto, without admitting a fix."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts/regression-harness"))
import s3_audio_qualification as q

@pytest.fixture(scope="module")
def paired(tmp_path_factory):
    root=tmp_path_factory.mktemp("s3_audio_qualification")
    index=ROOT/"tests/fixtures/tempo_corpus/streams/index.json"
    meta=json.loads(index.read_text())["clips"]["r3:r3_music_sqrt"]
    rows=q.replay.load_fixture(index,"r3:r3_music_sqrt",meta)
    results={}
    for variant in ("shipped","silence_only"):
        out=root/variant;out.mkdir()
        binary=q.replay.build(out,q.replay.VARIANTS[variant]+["K1_ONSET_V2"],True)
        results[variant]=q.run_rows(binary,rows,out/"replay.raw")
    return results

def test_actual_shipped_music_is_internally_locked_but_silence_vetoed(paired):
    s=q.summary(paired["shipped"])
    assert s["settled_bpm"]==127
    assert s["internal_lock_frames"]==s["false_silence_frames"]==s["scored_frames"]
    assert s["published_lock_frames"]==s["beat_ticks"]==0

def test_producer_silence_changes_output_not_tempo_and_is_not_admission(paired):
    old,new=paired["shipped"],paired["silence_only"]
    assert old["bpm"]==new["bpm"]
    s=q.summary(new)
    assert s["false_silence_frames"]==0 and s["beat_ticks"]>0
    assert s["published_lock_frames"]==s["scored_frames"]
    assert all(0<=x<=1 for x in new["conf"])
    assert all(0<=x<1 for x in new["phase"])

def test_increased_wrong_locks_remain_rejected():
    result=q.scorer.acceptance({"summary":{"locked_correct":1,"locked_wrong":1}},
                              {"summary":{"locked_correct":11,"locked_wrong":7}})
    assert not result["met"]

@pytest.mark.parametrize("fault", [None,"audio_hash","payload","generation_gap","cached_stream"])
def test_capture_recovery_checks_identity_and_total_hops(tmp_path, fault):
    import hashlib
    import struct
    import wave
    import s3_audio_qualification_recover as recover
    sys.path.insert(0,str(ROOT/"tools/esp_emulator"))
    from emu_blob import BlobSpec, build_blob
    # Synthetic infrastructure fixture, not a music or tempo reference.
    pcm=struct.pack("<192h",*([4096,-4096]*96))
    audio=tmp_path/"synthetic.wav"
    with wave.open(str(audio),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(12800);w.writeframes(pcm)
    folder=tmp_path/"runs/lane-gz_fixture";folder.mkdir(parents=True)
    blob,_=build_blob(BlobSpec("fixture",12800,96,pcm,0,0,1,1,False,[],20000))
    if fault=="payload": blob=blob[:-1]+bytes([blob[-1]^1])
    (folder/"scenario-blob.bin").write_bytes(blob)
    (folder/"exit_code.txt").write_text("0")
    (folder/"firmware.elf").write_bytes(b"synthetic infrastructure fixture")
    rows=[[1,"0.0",0],[2,"0.0",0]]
    if fault=="generation_gap": rows[1][0]=3
    (folder/"streams.json").write_text(json.dumps({"N":rows,"P":[[r[0],"0000"*80] for r in rows]}))
    (folder/"uart.txt").write_text("".join(f"N,{g},{n},0,{sil},unused\nP,{g},{'0000'*80}\n" for g,n,sil in rows))
    if fault=="cached_stream":
        cached=json.loads((folder/"streams.json").read_text());cached["N"][0][1]="0.9"
        (folder/"streams.json").write_text(json.dumps(cached))
    row={"id":"gz:fixture","path":str(audio),"sha256":hashlib.sha256(audio.read_bytes()).hexdigest()}
    if fault=="audio_hash": row["sha256"]="0"*64
    out=tmp_path/"out";out.mkdir()
    cid,meta,error=recover.recover((row,tmp_path/"runs",out))
    assert cid==row["id"]
    if fault is None: assert meta["gens"]==2 and error is None
    else: assert meta is None and error


def test_intersection_is_only_and_and_rejects_alignment_errors():
    from s3_audio_qualification_intersection import intersect
    a={"clips":{"x":{"gen":[1,2,3,4],"bpm":[127]*4,"lock":[0,0,1,1]}}}
    b={"clips":{"x":{"gen":[1,2,3,4],"bpm":[127]*4,"lock":[0,1,0,1]}}}
    assert intersect(a,b)["clips"]["x"]["lock"]==[0,0,0,1]
    b["clips"]["x"]["gen"][0]=0
    with pytest.raises(ValueError,match="mismatch"): intersect(a,b)


@pytest.mark.parametrize('fault',[None,'missing_n','missing_p','gap_p','width_p'])
def test_validation_projection_is_fail_closed(fault):
    import copy
    from s3_audio_qualification_recover import validate_streams
    d={'N':[[1,'0.0',0],[2,'0.1',0]],'P':[[1,'0000'*80],[2,'0001'*80]]}
    if fault=='missing_n':d['N'].pop()
    if fault=='missing_p':d['P'].pop()
    if fault=='gap_p':d['P'][1][0]=3
    if fault=='width_p':d['P'][1][1]='0000'*79
    if fault is None:validate_streams(d,2)
    else:
        with pytest.raises(ValueError):validate_streams(d,2)


def test_e1_stops_on_failed_dependency_instead_of_reading_stale_outputs(tmp_path,monkeypatch):
    import types
    import s3_audio_qualification_e1 as e1
    idx=tmp_path/'fixtures.json';idx.write_text('{"clips":{},"complete":true}')
    out=tmp_path/'out';out.mkdir();(out/'gated.json').write_text('stale');(out/'score.json').write_text('stale')
    def fake_build(where,*args):
        (where/'build_cmd.txt').write_text('synthetic infrastructure test; no DSP run')
        return where/'unused'
    monkeypatch.setattr(e1.q.replay,'build',fake_build)
    calls=[]
    def fail_first(cmd,**kw):
        calls.append(cmd);return types.SimpleNamespace(returncode=7 if len(calls)==1 else 0)
    monkeypatch.setattr(e1.subprocess,'run',fail_first)
    monkeypatch.setattr(sys,'argv',['e1','--fixtures',str(idx),'--out',str(out),'--manifest',str(tmp_path/'unused')])
    assert e1.main()==7 and len(calls)==1
    assert json.loads((out/'commands.json').read_text())[0]['exit_code']==7
    assert (out/'gated.json').read_text()=='stale'
