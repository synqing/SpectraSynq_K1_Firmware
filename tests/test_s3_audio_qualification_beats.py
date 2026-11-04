"""Independent beat-time metric controls; no synthetic stimulus called music."""
import importlib.util
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/regression-harness'))
import s3_audio_qualification_beats as q

def test_exact_shifted_missing_and_false_beats():
    ref=[5.+i*.5 for i in range(20)]
    assert q.beat_metrics(ref,ref)['f1']==1
    assert q.beat_metrics(ref,[t+.125 for t in ref])['matched']==0
    half=q.beat_metrics(ref,ref[::2])
    assert half['precision']==1 and half['recall']==.5
    extra=q.beat_metrics(ref,sorted(ref+[t+.25 for t in ref]))
    assert extra['precision']==.5 and extra['recall']==1
    assert q.beat_metrics(ref,[])['recall']==0

def test_one_prediction_cannot_match_multiple_labels():
    m=q.beat_metrics([5.,5.1],[5.05])
    assert m['matched']==1 and m['recall']==.5

def test_phase_is_compared_without_optimising_shift():
    ref=[5.,5.5,6.]
    exact=q.phase_errors(ref,[(5.125,.25,True),(5.625,.25,True)])
    wrong=q.phase_errors(ref,[(5.125,.75,True),(5.625,.75,True)])
    assert exact['absolute_cycles']['mean']==0
    assert wrong['absolute_cycles']['mean']==.5
    assert q.phase_errors(ref,[(5.125,.25,False)])['absolute_cycles']['count']==0

def test_epoch_and_contiguous_generation_guards():
    good='EMU_EPOCH policy=declared epoch_us=1000000 boot_us=0\nN,1,0.1,0.2,0,00000000\nV,0,1,0,0,0,120,0,.5,1,0\n'
    assert q.native_rows(good)[0]==[(1,.1,0)]
    with pytest.raises(ValueError):q.native_rows(good.replace('N,1,','N,2,'))
    with pytest.raises(ValueError):q.native_rows(good.replace('epoch_us=1000000','epoch_us=0'))

def test_nonfinite_and_duplicate_reference_rejected():
    with pytest.raises(ValueError):q.beat_metrics([float('nan')],[1.])
    with pytest.raises(ValueError):q.beat_metrics([1.,1.],[1.])


def test_host_generation_identity_is_strict():
    q.validate_host_generations([1,2,3],3)
    for bad in ([2,3,4],[1,1,3],[1,3,2],[1,2]):
        with pytest.raises(ValueError):q.validate_host_generations(bad,3)

def test_native_parity_requires_actual_samples():
    with pytest.raises(ValueError):q.native_rows('EMU_EPOCH policy=declared epoch_us=1000000\nN,1,.1,.2,0,00000000\n')


def test_native_nonfinite_cannot_silently_pass_parity():
    text='EMU_EPOCH policy=declared epoch_us=1000000\nN,1,.1,.2,0,00000000\nV,0,1,0,0,0,nan,0,.5,1,0\n'
    with pytest.raises(ValueError):q.native_rows(text)
