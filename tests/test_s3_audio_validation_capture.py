"""Synthetic transport/integrity tests only; these fixtures establish no music quality."""
import copy
import json
import struct
import sys
import wave
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/regression-harness'))
import s3_audio_validation_capture as capture
import s3_audio_validation_verify as verify
from emu_blob import BlobSpec, build_blob


@pytest.fixture
def record(tmp_path):
    runtime = tmp_path/'runtime'; runtime.mkdir()
    folder = tmp_path/'capture'; folder.mkdir()
    pcm = struct.pack('<192h', *([4096, -4096]*96))
    audio = tmp_path/'synthetic.wav'
    with wave.open(str(audio), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(12800); w.writeframes(pcm)
    for name, data in [('firmware.elf', b'synthetic ELF'), ('firmware.bin', b'synthetic app')]:
        (runtime/name).write_bytes(data)
    (folder/'firmware.elf').write_bytes((runtime/'firmware.elf').read_bytes())
    (folder/'flash-run.bin').write_bytes(bytes(0x10000)+(runtime/'firmware.bin').read_bytes())
    blob, _ = build_blob(BlobSpec('fixture',12800,96,pcm,0,0,1,1,False,[],20000))
    (folder/'scenario-blob.bin').write_bytes(blob)
    (folder/'exit_code.txt').write_text('0')
    streams = {'N': [[1,'0.0',0],[2,'0.0',0]], 'P': [[g,'0000'*80] for g in (1,2)]}
    (folder/'streams.json').write_text(json.dumps(streams))
    (folder/'uart.txt').write_text(''.join(f'N,{g},0.0,0,0,unused\nP,{g},{"0000"*80}\n' for g in (1,2)))
    row = {'id':'fixture', 'path':str(audio), 'sha256':capture.sha(audio)}
    rec = {'id':'fixture','status':'PASS','source_sha256':row['sha256'], 'capture':str(folder), 'streams':str(folder/'streams.json')}
    return row, rec, runtime


@pytest.mark.parametrize('fault', [None,'elf','app','raw','cache','missing_n','missing_p','blob','pcm'])
def test_record_verifies_retained_bytes_and_independent_audio(record, tmp_path, fault):
    row, rec, runtime = record
    folder = Path(rec['capture'])
    if fault in ('elf','app','blob'):
        path = folder/{'elf':'firmware.elf','app':'flash-run.bin','blob':'scenario-blob.bin'}[fault]
        b = path.read_bytes(); path.write_bytes(b[:-1]+bytes([b[-1]^1]))
    if fault == 'raw':
        p = folder/'uart.txt'; p.write_text(p.read_text().replace('N,1,0.0','N,1,0.1'))
    if fault in ('cache','missing_n','missing_p'):
        p = Path(rec['streams']); d=json.loads(p.read_text())
        if fault == 'cache': d['N'][0][1]='0.2'
        else:
            key = 'N' if fault == 'missing_n' else 'P'; d[key].pop()
            # Remove the corresponding raw row too: matching projections alone cannot pass.
            uart=folder/'uart.txt'; uart.write_text('\n'.join(x for x in uart.read_text().splitlines() if not x.startswith(key+',2,'))+'\n')
        p.write_text(json.dumps(d))
    if fault == 'pcm':
        pcm=bytes(384)
        blob,_=build_blob(BlobSpec('fixture',12800,96,pcm,0,0,1,1,False,[],20000))
        (folder/'scenario-blob.bin').write_bytes(blob)
    if fault:
        with pytest.raises(ValueError): capture.validate_record(row,rec,runtime,tmp_path/'checks')
    else:
        assert capture.validate_record(row,rec,runtime,tmp_path/'checks')['gens']==2


@pytest.fixture
def frozen(tmp_path, record):
    row, rec, runtime=record
    rows=[dict(row,id=f'f{i}',role='validation',split='V2') for i in range(483)]
    manifest=tmp_path/'manifest.json'; manifest.write_text(json.dumps({'rows':rows}))
    model=tmp_path/'model'; model.write_text('synthetic orchestration fixture')
    identity={'app_sha256':capture.sha(runtime/'firmware.bin'),'elf_sha256':capture.sha(runtime/'firmware.elf')}
    (runtime/'identity.json').write_text(json.dumps(identity))
    pre=tmp_path/'pre.json'; pre.write_text(json.dumps({'validation_manifest_sha256':capture.sha(manifest), 'runtime_app_sha256':identity['app_sha256'],'runtime_elf_sha256':identity['elf_sha256'],'model_path':str(model),'model_sha256':capture.sha(model)}))
    source=tmp_path/'result.json'; source.write_text(json.dumps({'preregistration_sha256':capture.sha(pre),'runtime':identity,'expected':483,'pilot':False,'cases':[dict(rec,id=r['id']) for r in rows]}))
    return manifest,runtime,pre,source


@pytest.mark.parametrize('fault',[None,'duplicate','prereg'])
def test_all_reuse_main_writes_result_or_rejects_invalid_input(frozen,tmp_path,monkeypatch,fault):
    manifest,runtime,pre,source=frozen
    prior=json.loads(source.read_text())
    if fault=='duplicate': prior['cases'].append(copy.deepcopy(prior['cases'][0]))
    if fault=='prereg': prior['preregistration_sha256']='wrong'
    source.write_text(json.dumps(prior))
    # Integrity is independently exercised above; here isolate reuse scheduling and publication.
    monkeypatch.setattr(capture,'validate_record',lambda *a: {'gens':2})
    monkeypatch.setattr(capture,'capture',lambda *a: pytest.fail('all-reuse must not capture'))
    output=tmp_path/'out'
    monkeypatch.setattr(sys,'argv',['capture','--manifest',str(manifest),'--runtime',str(runtime),'--preregistration',str(pre),'--reuse',str(source),'--output',str(output)])
    if fault:
        with pytest.raises((ValueError,AssertionError)): capture.main()
    else:
        assert capture.main()==0
        assert len(json.loads((output/'result.json').read_text())['cases'])==483


@pytest.mark.parametrize('fault',[None,'duplicate','partial','extra','prereg','runtime','manifest','record'])
def test_post_validation_publishes_only_complete_exact_verified_coverage(frozen,tmp_path,monkeypatch,fault):
    manifest,runtime,pre,source=frozen
    prior=json.loads(source.read_text())
    if fault=='duplicate': prior['cases'][-1]=copy.deepcopy(prior['cases'][0])
    if fault=='partial': prior['cases'].pop()
    if fault=='extra': prior['cases'][0]['id']='unlisted'
    if fault=='prereg': prior['preregistration_sha256']='wrong'
    if fault=='runtime': prior['runtime']['app_sha256']='wrong'
    if fault=='manifest': manifest.write_text(manifest.read_text()+' ')
    source.write_text(json.dumps(prior))
    calls=[]
    def validate(row,*args):
        calls.append(row['id'])
        if fault=='record' and row['id']=='f1': raise ValueError('retained corruption')
        return {'gens':2}
    monkeypatch.setattr(capture,'validate_record',validate)
    output=tmp_path/'out'
    result=verify.verify(manifest,runtime,pre,source,output)
    assert result['complete'] is (fault is None)
    assert (output/'index.json').exists() is (fault is None)
    assert (output/'verification.json').exists()
    if fault in (None,'record'): assert len(calls)==483
    if fault: assert result['errors']
