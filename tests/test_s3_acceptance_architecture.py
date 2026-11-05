"""Acceptance authority pins and actual-disassembly inventory controls."""
import copy,importlib.util,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/esp_emulator'))
import run as runner
import s3_architecture_audit as arch


def test_acceptance_has_all_independent_requirements_and_current_sources():
    import hashlib
    j=json.loads((ROOT/'tools/esp_emulator/k1_lightshow_acceptance.json').read_text())
    assert [r['id']for r in j['requirements']]==[f'LS{i:02}'for i in range(1,9)]
    for r in j['references']:
        assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
    assert j['geometry']=={'edges':2,'pixels_per_edge':160,'centre_indices':[79,80]}


@pytest.mark.parametrize('name',['temporal_dithering','incandescent_mode','secondary_incandescent_mode','look','secondary_look'])
def test_visual_replay_controls_exist_in_production_table(name,tmp_path):
    table=(ROOT/'SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def').read_text()
    assert f'SERIAL_TYPED_CMD("{name}"' in table
    j=json.loads((ROOT/'tools/esp_emulator/s3_music_regression.json').read_text())
    cid=next(iter(j['cases']));j['cases'][cid]['commands']=[{'hop':0,'text':name+'=0'}]
    p=tmp_path/'scenario.json';p.write_text(json.dumps(j));runner.load_scenario(p)
    j['cases'][cid]['commands'][0]['text']='not_a_product_control=1';p.write_text(json.dumps(j))
    with pytest.raises(runner.ScenarioError,match='unsupported command'):runner.load_scenario(p)


def test_disassembly_inventory_separates_direct_and_indirect_calls():
    s='''00000010 <loop()>:
 10: abcd call8 20 <stage()>\n 13: abcd callx8 a8
00000020 <stage()>:
 20: abcd call8 30 <worker()>\n00000030 <worker()>:
 30: abcd retw.n
00000040 <unused()>:
 40: abcd call8 30 <worker()>\n'''
    g,i=arch.calls(s)
    assert arch.reachable(g,'loop()')=={'loop()','stage()','worker()'}
    assert i=={'loop()':1}
    assert 'unused()'not in arch.reachable(g,'loop()')


def test_missing_target_trace_cannot_be_accepted(tmp_path):
    with pytest.raises(ValueError,match='No target trace'):arch.trace_summary(tmp_path)
    (tmp_path/'window-0.json').write_text('{"traceEvents":[]}')
    with pytest.raises(ValueError,match='no duration'):arch.trace_summary(tmp_path)


def test_independent_spectral_dft_qualification(tmp_path):
    import subprocess
    result=subprocess.run([sys.executable,str(ROOT/'scripts/regression-harness/s3_spectral_qualification.py'),'--output',str(tmp_path/'spectral')],cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    j=json.loads((tmp_path/'spectral/result.json').read_text())
    assert len(j['cases'])==23 and j['bins_compared']==71 and j['above_nyquist_zero_bins']==9
    assert j['negative_zeroed_strong_tone_rejected']


def test_acceptance_budgets_match_current_constants():
    j=json.loads((ROOT/'tools/esp_emulator/k1_lightshow_acceptance.json').read_text())
    text=(ROOT/'SPECTRASYNQ_K1_FIRMWARE/system/constants.h').read_text()
    assert '#define VP_PERF_FRAME_BUDGET_US 8333UL'in text
    assert '#define VP_PERF_RENDER_BUDGET_US 2000UL'in text
    assert j['budgets']['frame_us']==8333 and j['budgets']['effect_us']==2000
    assert j['budgets']['audio_service_p99_us']==8000


def test_consumer_repair_stays_on_bench_and_emu_onset_trace_stays_private():
    flags=runner.flag_names(runner.effective_env('k1_fe').get('build_flags',[]))
    assert 'K1_TEMPO_CONSUMER_BANDS_V1'not in flags
    bench_flags=runner.flag_names(runner.effective_env('k1_fe_bench_b489').get('build_flags',[]))
    assert 'K1_TEMPO_CONSUMER_BANDS_V1'in bench_flags
    assert 'K1_EMU_ONSET_TRACE'not in flags
    assert 'K1_TEMPO_LOCK_OFF_V1'not in flags
    assert 'K1_TEMPO_SILENCE_FROM_PRODUCER_V1'not in flags
    sc=runner.select_profile(runner.load_scenario(ROOT/'tools/esp_emulator/s3_music_regression.json'),'fe')
    assert 'K1_EMU_ONSET_TRACE'in sc['profile']['adapter_flags']
    assert 'K1_EMU_ONSET_TRACE'in sc['profile']['forbidden_in_product']
