"""Independent integer oracles against actual product quantisers and look headers."""
from pathlib import Path
import importlib.util
import shutil
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
VISUAL=ROOT/"SPECTRASYNQ_K1_FIRMWARE/visual"

def function(src,name):
    start=src.index("inline void "+name+"(")
    brace=src.index("{",start); depth=0
    for i in range(brace,len(src)):
        depth+=(src[i]=="{")-(src[i]=="}")
        if depth==0:return src[start:i+1]
    raise AssertionError(name)

def test_actual_rgb8_quantisers_and_u16_look(tmp_path):
    (tmp_path/"Arduino.h").write_text("#pragma once\n#include <stdint.h>\n")
    source=(VISUAL/"led_utilities.h").read_text()
    constants=(ROOT/"SPECTRASYNQ_K1_FIRMWARE/system/constants.h").read_text()
    assert re.search(r"#define ENABLE_OUTPUT_GAMMA\s+0\b",constants)
    dither=re.search(r"const SQ15x16 dither_table\[4\] = \{.*?\};",constants,re.S).group(0)
    funcs="\n".join(function(source,n) for n in ("quantize_color","quantize_color_secondary"))
    code=r'''#include <cassert>
#include <cmath>
#include <cstdint>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
#define K1_LOOK_LIB_V1
#include "k1_look.h"
struct CRGB16 {SQ15x16 r,g,b;};
struct CRGB {uint8_t r,g,b;};
struct Config {uint16_t LED_COUNT=1;} CONFIG;
constexpr uint16_t SECONDARY_LED_COUNT=1;
CRGB16 leds_scaled[1],leds_scaled_secondary[1];
CRGB leds_out[1],leds_out_secondary[1];
uint8_t dither_step=0;
const SQ15x16 dither_table[4]={0.25,0.5,0.75,1.0};
uint8_t apply_gamma8(uint8_t v){return v;} // shipping ENABLE_OUTPUT_GAMMA=0
''' + funcs + r'''
int main(){
 for(int raw=0;raw<=65536;raw+=16){
  SQ15x16 c=SQ15x16::fromInternal(raw);
  leds_scaled[0]={c,c,c};leds_scaled_secondary[0]={c,c,c};
  quantize_color(false);quantize_color_secondary(false);
  const unsigned exact=(uint64_t(raw)*255)/65536;
  assert(leds_out[0].r==exact && leds_out_secondary[0].r==exact);
  unsigned sum=0,second=0;
  for(int phase=0;phase<4;++phase){
   quantize_color(true);quantize_color_secondary(true);
   assert(leds_out[0].r==leds_out[0].g && leds_out[0].g==leds_out[0].b);
   assert(leds_out_secondary[0].r==leds_out_secondary[0].b);
   sum+=leds_out[0].r;second+=leds_out_secondary[0].r;
  }
  unsigned expected=4*((uint64_t(raw)*254)/65536)+((uint64_t(raw)*254)%65536)/16384;
  assert(sum==expected && second==expected);
 }
 for(unsigned v=0;v<=65535;++v){
  uint16_t r=v,g=65535-v,b=v/2;
  k1_look_apply_u16(&r,&g,&b,0);
  assert(r==v && g==65535-v && b==v/2);
  r=g=b=v;k1_look_apply_u16(&r,&g,&b,1);
  assert(r==g && g==b);
  if(v==0) assert(r==0);
  if(v==65535) assert(r==65535);
  // LUT approximates inverse gamma; tolerance is the existing generator's
  // 16-bit interpolation bound, tested separately by test_lever2_degamma_curve.
  const long oracle=std::lround(65535.0*std::pow(double(v)/65535.0,1.0/2.2));
  assert(std::abs(long(r)-oracle)<=4);
  static uint16_t last=0;assert(r>=last);last=r;
 }
}
'''
    code=code.replace("const SQ15x16 dither_table[4]={0.25,0.5,0.75,1.0};",dither)
    (tmp_path/"check.cpp").write_text(code)
    compiler=shutil.which("g++-16") or shutil.which("g++")
    cmd=[compiler,"-std=c++17","-O1","-fsanitize=address,undefined","-fno-sanitize-recover=all",f"-I{tmp_path}",f"-I{VISUAL}",f"-I{ROOT/'.pio/libdeps/k1_fe/FixedPoints/src'}",str(tmp_path/"check.cpp"),"-o",str(tmp_path/"check")]
    subprocess.run(cmd,check=True)
    subprocess.run([str(tmp_path/"check")],check=True)

def load_runner():
    sys.path.insert(0,str(ROOT/"tools/esp_emulator"))
    import s3_visual_qualification as runner
    return runner

def test_roster_and_scenario_obey_existing_blob_limits(tmp_path):
    runner=load_runner();roster=runner.compiled_roster(tmp_path)
    assert len(roster)==38
    assert {r["mode"] for r in roster if not r["enabled"]}=={0,1,2,4,5,6,10,17,30,31}
    sc=runner.scenario(roster)
    assert len(sc["cases"]["all_modes"]["commands"])<=64
    assert all(isinstance(a["segments"][0]["to_ms"],int) for key,a in sc["assets"].items() if key in ("visual_music","modifier_music"))

def test_output_checker_rejects_malformed_width():
    import pytest
    from types import SimpleNamespace
    runner=load_runner()
    with pytest.raises(ValueError): runner.frame_metrics([SimpleNamespace(A=b"bad")],"A")


def test_no_frames_never_counts_as_mode_coverage():
    from types import SimpleNamespace
    runner=load_runner()
    cap=SimpleNamespace(frames=[],show_states=[])
    rows=runner.sweep_metrics(cap,[{"mode":3,"name":"BLOOM","enabled":True}])
    assert not rows[0]["dispatch_match"]
    assert not rows[0]["secondary_readback_match"]
    assert rows[0]["coverage"]!="OUTPUT_OBSERVED"


def test_disabled_checker_rejects_stuck_enabled_primary(monkeypatch):
    from types import SimpleNamespace
    runner=load_runner()
    roster=[{"mode":i,"enabled":i in (3,7)} for i in range(8)]
    disabled=[i for i in range(8) if i not in (3,7)]
    states=[{"when":"cmd","hop":i*24,"hex":str(next((m+j)%8 for j in range(8) if (m+j)%8 in (3,7)))} for i,m in enumerate(disabled)]
    monkeypatch.setattr(runner.replay,"_decode_show_state",lambda v:{"secondary":{"lightshow_mode":int(v)}})
    frames={i*24+23:SimpleNamespace(mode=int(st["hex"])) for i,st in enumerate(states)}
    monkeypatch.setattr(runner.replay,"_by_hop",lambda cap,hop:frames)
    cap=SimpleNamespace(show_states=states,frames=list(frames.values()))
    assert all(r["status"]=="PASS" for r in runner.disabled_checks(cap,roster))
    for f in frames.values(): f.mode=3
    assert any(r["status"]=="FAIL" for r in runner.disabled_checks(cap,roster))


def test_long_checker_rejects_quiet_light_missing_return_and_asymmetry(monkeypatch):
    from types import SimpleNamespace
    runner=load_runner()
    state={"primary":{"mirror_enabled":1},"secondary":{"lightshow_mode":3,"mirror_enabled":1}}
    monkeypatch.setattr(runner.replay,"_decode_show_state",lambda value:state)
    lit=b'\x00\x01'*480
    frames={h:SimpleNamespace(index=h,mode=3,A=lit if h<800 or h>=1600 else bytes(960),B=lit if h<800 or h>=1600 else bytes(960)) for h in range(1867)}
    cap=SimpleNamespace(show_states=[{"hex":"fixture"}],render_state={})
    monkeypatch.setattr(runner.replay,"_by_hop",lambda cap,hop:frames)
    assert runner.long_metrics(cap,3)["status"]=="PASS"
    frames[1500].A=lit
    assert any("nonzero output" in r for r in runner.long_metrics(cap,3)["reasons"])
    frames[1500].A=bytes(960)
    for h in range(1600,1867):frames[h].B=bytes(960)
    assert any("did not relight" in r for r in runner.long_metrics(cap,3)["reasons"])
    frames[10].A=b'\x00\x02'+lit[2:]
    assert any("asymmetric" in r for r in runner.long_metrics(cap,3)["reasons"])


def test_mode18_quiet_drain_preserves_requested_mirror(tmp_path):
    source=(ROOT/'SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp').read_text()
    start=source.index('  if (dark_gate) {\n#ifdef M18_DARK_DIAG')
    branch=source[start:source.index('  // MAPPING',start)]
    mirror=function((VISUAL/'led_utilities.h').read_text(),'mirror_image_downwards')
    code='''#include <cstdint>
#include <cstring>
#include <cassert>
constexpr int NATIVE_RESOLUTION=160;
struct CRGB16 {uint16_t r,g,b;};
CRGB16 leds_16[160],leds_16_temp[160];
struct Params {bool MIRROR_ENABLED;};
'''+mirror+'\nvoid drain(bool dark_gate,Params* rp){\n'+branch+'\n}\n'+'''
int main(){
 for(bool mirror : {false,true}){
  for(unsigned i=0;i<160;++i) leds_16[i]={uint16_t(i+1),uint16_t(i+100),uint16_t(600-i)};
  Params p{mirror};drain(true,&p);
  for(unsigned i=0;i<160;++i){
   unsigned src=mirror && i<80 ?159-i:i;
   assert(leds_16[i].r==src+1);
   assert(leds_16[i].g==src+100);
   assert(leds_16[i].b==600-src);
  }
 }
}
'''
    code='#include <initializer_list>\n'+code
    (tmp_path/'check.cpp').write_text(code)
    compiler=shutil.which('g++-16') or shutil.which('g++')
    subprocess.run([compiler,'-std=c++17','-fsanitize=address,undefined',str(tmp_path/'check.cpp'),'-o',str(tmp_path/'check')],check=True)
    subprocess.run([str(tmp_path/'check')],check=True)


def test_actual_tempo_consumers_bands_counterfactual(tmp_path):
    """Actual complete effects, actual fixed arithmetic and state declarations.
    Fake clock/event inputs and fixed palette isolate cue admission, not appeal.
    """
    (tmp_path/"Arduino.h").write_text("#pragma once\n#include <stdint.h>\n")
    state=(VISUAL/'channel_effect_state.h').read_text()
    fields='\n'.join(l for l in state.splitlines() if re.match(r'\s*(float|uint32_t|uint16_t|uint8_t)\s+(tcomet_|tcanta_)',l))
    sources=[]
    for name in ('tempo_comet','tempo_comet_anticipate'):
        source=(ROOT/f'SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_{name}.cpp').read_text()
        sources.append(re.sub(r'^#include .*\n','',source,flags=re.M))
    mirror=function((VISUAL/'led_utilities.h').read_text(),'mirror_image_downwards')
    code=r'''#include <cstdint>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
constexpr int COMET_MAX=6,NATIVE_RESOLUTION=160;
struct CRGB16 {SQ15x16 r,g,b;};
struct RenderParams {bool MIRROR_ENABLED=true;};
struct K1TempoEvent {float bpm=120,phase01=0,confidence=0,beat_strength=0.8f;bool beat_tick=false,locked=false;};
struct K1OnsetBeatEvent {uint32_t event_id=0;bool bass_onset=false;float bass_onset_strength=0.8f;};
RenderParams params;K1TempoEvent tempo;K1OnsetBeatEvent onset;
uint32_t clock_ms=1000;
uint32_t millis(){return clock_ms;}
bool vp_render_secondary_channel=false,led_thread_halt=false;
const RenderParams* active_render_params(){return &params;}
K1TempoEvent k1_vp_tempo_read(){return tempo;}
K1OnsetBeatEvent k1_vp_onset_beat_read(){return onset;}
CRGB16 leds_16[160],leds_16_temp[160];
CRGB16 effect_particle_colour(const RenderParams*,bool,float,SQ15x16){return {SQ15x16(.2f),SQ15x16(.4f),SQ15x16(.7f)};}
CRGB16 clamp_crgb16_preserve_sat(CRGB16 c){float m=fmaxf(float(c.r),fmaxf(float(c.g),float(c.b)));if(m>1){c.r/=m;c.g/=m;c.b/=m;}return c;}
struct ChannelEffectState {
'''+fields+'\n};\n'+mirror+'\n'+'\n'.join(sources)+r'''
using Render=void(*)(ChannelEffectState&);
void clear(ChannelEffectState& fx){fx={};for(auto& p:leds_16)p={};clock_ms=1000;tempo={};onset={};}
int live(ChannelEffectState& fx,bool anticipate){int n=0;for(int i=0;i<COMET_MAX;++i)n+=(anticipate?fx.tcanta_life[i]:fx.tcomet_life[i])>.01f;return n;}
float learned(ChannelEffectState& fx,bool a){return a?fx.tcanta_locked_bpm:fx.tcomet_locked_bpm;}
int main(){
 for(int a=0;a<2;++a){
  Render render=a?light_mode_tempo_comet_anticipate:light_mode_tempo_comet;
  ChannelEffectState fx{};clear(fx);
  // Fresh measured bass onset while tentative: only repaired branch may launch.
  tempo.confidence=.35f;onset.event_id=1;onset.bass_onset=true;
  render(fx);
#ifdef K1_TEMPO_CONSUMER_BANDS_V1
  assert(live(fx,a)==1);assert(learned(fx,a)==0);
  if(a)assert(fx.tcanta_free[0]==1);
  // Same event is never admitted twice, even though bass_onset remains true.
  for(int k=0;k<10;++k){clock_ms+=8;render(fx);assert(live(fx,a)==1);}
#else
  assert(live(fx,a)==0);
#endif
  // Confidence alone must not manufacture a validated beat grid.
  clear(fx);tempo.confidence=.9f;bool seen=false;
  for(int k=0;k<250;++k){clock_ms+=8;tempo.phase01=fmodf(k*.016f,1.0f);render(fx);seen|=live(fx,a)>0;}
#ifdef K1_TEMPO_CONSUMER_BANDS_V1
  assert(!seen);assert(learned(fx,a)==0);
#else
  assert(seen);assert(learned(fx,a)>0);
#endif
  // A genuinely published lock and its subsequent bounded coast retain bytes.
  clear(fx);uint64_t hash=1469598103934665603ull;seen=false;
  for(int k=0;k<750;++k){clock_ms+=8;tempo.locked=k<250;tempo.confidence=k<250?.9f:0.0f;tempo.phase01=fmodf(k*.016f,1.0f);render(fx);if(k>=250)seen|=live(fx,a)>0;
   for(auto p:leds_16)for(auto ch:{p.r,p.g,p.b}){hash^=uint32_t(ch.getInternal());hash*=1099511628211ull;}
  }
  assert(seen);printf("%d %llu\n",a,(unsigned long long)hash);
 }
}
'''
    code='#include <initializer_list>\n'+code
    (tmp_path/'consumers.cpp').write_text(code)
    compiler=shutil.which('g++-16') or shutil.which('g++')
    outputs=[]
    for enabled in (False,True):
        exe=tmp_path/('bands' if enabled else 'baseline')
        cmd=[compiler,'-std=c++17','-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all',f'-I{tmp_path}',f"-I{ROOT/'.pio/libdeps/k1_fe/FixedPoints/src'}",str(tmp_path/'consumers.cpp'),'-o',str(exe)]
        if enabled:cmd.append('-DK1_TEMPO_CONSUMER_BANDS_V1')
        subprocess.run(cmd,check=True)
        outputs.append(subprocess.check_output([str(exe)],text=True))
    assert outputs[0]==outputs[1], 'Published-lock/coast output changed under consumer repair'


def test_modifier_selection_repairs_omitted_or_reordered_baseline():
    import pytest
    runner=load_runner()
    sc={"cases":{"all_modes":{},"modifier_base":{},"a_reverse":{},"b_zero":{}}}
    for selection in ('a_reverse','a_reverse,modifier_base','a_reverse,b_zero,modifier_base'):
        cases,required=runner.select_cases(sc,selection)
        assert cases[0]=='modifier_base'
        assert cases.count('modifier_base')==1
        assert required==[c for c in cases if c!='modifier_base']
        # Transport success alone, or only one of two requested comparisons, fails.
        assert runner.modifier_comparison_errors([],required)
        passed=[{'name':c,'status':'PASS'} for c in required]
        assert not runner.modifier_comparison_errors(passed,required)
        assert runner.modifier_comparison_errors(passed[:-1],required)
    for invalid in ('','typo','a_reverse,a_reverse'):
        with pytest.raises(ValueError): runner.select_cases(sc,invalid)


def test_modifier_main_rejects_transport_only_and_orders_baseline(tmp_path,monkeypatch):
    import json
    runner=load_runner()
    sc={"cases":{"modifier_base":{},"a_reverse":{}}}
    monkeypatch.setattr(runner,'compiled_roster',lambda out:[])
    monkeypatch.setattr(runner,'scenario',lambda roster:sc)
    monkeypatch.setattr(runner.replay,'resolve_esp_emu',lambda lock:('fake',[]))
    monkeypatch.setattr(runner.replay,'source_identity',lambda:{})
    monkeypatch.setattr(runner.replay,'sha256_file',lambda path:'test')
    monkeypatch.setattr(runner,'compare',lambda base,changed,name:{'name':name,'status':'PASS'})
    for i,(selection,capture) in enumerate([('a_reverse',False),('a_reverse,modifier_base',False),('a_reverse',True)]):
        calls=[]
        def fake_case(sc,cid,*args):
            calls.append(cid)
            return {'status':'PASS',**({'_capture':object()} if capture else {})}
        monkeypatch.setattr(runner.replay,'run_case',fake_case)
        out=tmp_path/str(i)
        monkeypatch.setattr(sys,'argv',['visual','--output',str(out),'--build-dir',str(tmp_path),'--cases',selection])
        assert runner.main()==(0 if capture else 1)
        assert calls==['modifier_base','a_reverse']
        report=json.loads((out/'result.json').read_text())
        assert report['required_comparisons']==['a_reverse']
        assert bool(report['comparison_errors'])== (not capture)
