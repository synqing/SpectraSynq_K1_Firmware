"""Full actual Comet render: V2 event units, legacy floor and byte parity."""
import importlib.util
import subprocess
import json
import hashlib
import sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/regression-harness'))
import render_replay as render

def build_comet(work,v2,source=None):
    mode=dict(render.ALL_MODES['comet'])
    # Comet does not consume waveform input. Use that existing driver slot to
    # carry explicit event IDs, rather than inventing a new production interface.
    mode['frame_apply']=mode['frame_apply'].replace('g_host_onset_event.event_id += 1u;', 'g_host_onset_event.event_id = uint32_t(fr.max_waveform_val_raw);')
    if source is not None:mode['sources']=[str(Path(source).resolve())]
    original=subprocess.run
    def run(argv,*args,**kwargs):
        if v2 and '-DK1_RENDER_HOST_TEST' in argv:argv=[*argv,'-DK1_ONSET_V2']
        return original(argv,*args,**kwargs)
    with patch.dict(render.MODES,{'comet':mode}),patch.object(render.subprocess,'run',run):
        ok,binary,details=render.build_binary(work,mode='comet')
    assert ok,details['stderr']
    return binary

def frames(strength=None):
    return [{'ms':1000+i*8,'chromagram':[1.]+[0.]*11,
             'bass_onset':int(i==5 and strength is not None),
             'bass_onset_strength':strength or 0.,'event_id':int(i>=5)} for i in range(60)]

def replay(binary,stimulus,work,label):
    feed=work/(label+'.input');raw=work/(label+'.raw')
    (work/(label+'.frames.json')).write_text(json.dumps(stimulus,indent=2)+'\n')
    encoded=[{**f,'max_waveform_val_raw':f['event_id']}for f in stimulus]
    feed.write_text(render._params_line(None)+render._frames_to_stdin(encoded))
    with feed.open()as f,raw.open('w')as o:subprocess.run([str(binary)],stdin=f,stdout=o,check=True)
    images=[bytes.fromhex(l[2:])for l in raw.read_text().splitlines()if l.startswith('R ')]
    assert len(images)==len(stimulus)
    return images

def verify_comet(work,source=None):
    legacy=build_comet(work/'legacy',False,source)
    v2=build_comet(work/'v2',True,source)
    strong=frames(.5)
    original=replay(legacy,strong,work,'legacy-strong')
    repaired=replay(v2,strong,work,'v2-strong')
    assert original==repaired
    held=[{**f,'bass_onset':int(i>=5)}for i,f in enumerate(strong)]
    assert replay(v2,held,work,'v2-held-same-id')==repaired
    (work/'green.json').write_text(json.dumps({'strong_frames_byte_identical':len(repaired),
        'strong_bytes_sha256':hashlib.sha256(b''.join(repaired)).hexdigest(),
        'held_same_id_frames_byte_identical':len(repaired)},indent=2)+'\n')
    low=frames(.00002055) # actual captured qualified V2 kick, generation1672
    assert not any(any(x)for x in replay(legacy,low,work,'legacy-low'))
    assert any(any(x)for x in replay(v2,low,work,'v2-low'))
    for name,stimulus in [('no-event',frames()),('zero-strength',frames(0.))]:
        assert not any(any(x)for x in replay(v2,stimulus,work,name))

def test_actual_comet_admits_v2_kicks_without_changing_strong_frames(tmp_path):
    verify_comet(tmp_path)
