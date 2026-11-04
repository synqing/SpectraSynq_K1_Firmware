"""Execute the actual normal-primary branch with real params and palette maths."""
import copy
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT/'SPECTRASYNQ_K1_FIRMWARE'


def normal_branch(source):
    # Anchor on the unchanged normal dispatch, then extract its enclosing else body.
    anchor = source.index('render_channel_via_framework(CONFIG.LIGHTSHOW_MODE, primary_channel);')
    start = source.rfind('} else {', 0, anchor)+len('} else {')
    end = source.index('\n      }', anchor)
    assert start >= len('} else {') and end > start
    return source[start:end]


@pytest.fixture(scope='module', params=['legacy','framework'])
def binary(request, tmp_path_factory):
    work=tmp_path_factory.mktemp('primary_snapshot_'+request.param)
    spec=importlib.util.spec_from_file_location('snapshot_render_harness',ROOT/'scripts/regression-harness/render_replay.py')
    replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
    replay.MODES=copy.deepcopy(replay.ALL_MODES)
    params_source=(FW/'visual/render_params.cpp').read_text()
    fields=re.findall(r'p\.(\w+)\s*=\s*(?:CONFIG\.\w+|hue_position|chroma_val|chromatic_mode|hue_shifting_mix);',params_source.split('RenderParams build_secondary')[0])
    assert len(fields)==19
    counter_source=work/'render_params_counted.cpp'
    counter_source.write_text(params_source.replace('RenderParams build_primary_render_params() {',
        'unsigned long snapshot_builds=0;\nRenderParams build_primary_render_params() {\n ++snapshot_builds;'))
    replay.COMMON_SOURCES=[str(counter_source) if s=='visual/render_params.cpp' else s for s in replay.COMMON_SOURCES]
    ino=Path(os.environ.get('K1_PRIMARY_SNAPSHOT_TEST_INO',str(FW/'SPECTRASYNQ_K1_FIRMWARE.ino')))
    branch=normal_branch(ino.read_text())
    equal=' && '.join(f'a.{f}==b.{f}'for f in fields)
    source=r'''
#include <cstdio>
#include <cstdlib>
#include "lightshow_modes.h"
extern unsigned long snapshot_builds;
static bool same(const RenderParams&a,const RenderParams&b) { return EQUAL; }
static void require(bool yes,const char*why) { if(!yes){std::fprintf(stderr,"%s\n",why);std::exit(1);} }
static RenderParams expected;
static CRGB16 reference[80];
static bool mutate=false;
static unsigned route=0;
static void query_colours() {
 const auto& pal=cached_gradient_palette(3,false);
 for(unsigned i=0;i<80;i++) {
  if(mutate && i==40) { CONFIG.MOOD=0.731f;CONFIG.AUTO_COLOR_SHIFT=!expected.AUTO_COLOR_SHIFT; }
  require(same(*active_render_params(),expected),"19 fields changed within dispatch");
  CRGB16 got=palette_manual_colour(pal,SQ15x16::fromInternal(i*811),SQ15x16::fromInternal(i*829));
  require(got.r==reference[i].r && got.g==reference[i].g && got.b==reference[i].b,"Q16 palette mismatch");
 }
}
static void render_lightshow_for_channel(uint8_t,int&) { route=1;query_colours(); }
static void render_channel_via_framework(uint8_t,int&) { route=2;query_colours(); }
FRAMEWORK_DEFINE
static void dispatch_normal() {
 int primary_channel=0;
ACTUAL_BRANCH
}
static void establish_reference() {
 expected=build_primary_render_params();const auto& pal=cached_gradient_palette(3,false);
 for(unsigned i=0;i<80;i++) reference[i]=palette_manual_colour(pal,SQ15x16::fromInternal(i*811),SQ15x16::fromInternal(i*829));
}
int main() {
 CONFIG.MOOD=0.25f;CONFIG.AUTO_COLOR_SHIFT=true;CONFIG.PALETTE_MODE_ENABLED=true;CONFIG.PALETTE_INDEX=3;
 hue_position=SQ15x16(0.375f);vp_render_secondary_channel=false;
 require(active_render_params_depth()==-1,"initial stack not empty");
 establish_reference();snapshot_builds=0;dispatch_normal();
 require(snapshot_builds==1,"normal dispatch rebuilt params more than once");
 require(route==EXPECTED_ROUTE,"wrong dispatch route");
 require(active_render_params_depth()==-1,"unbalanced normal stack");
 mutate=true;snapshot_builds=0;dispatch_normal();
 require(snapshot_builds==1,"mutating dispatch rebuilt params");
 require(active_render_params_depth()==-1,"unbalanced mutation stack");
 require(CONFIG.MOOD==0.731f,"mutation stimulus absent");
 mutate=false;establish_reference();
 require(expected.MOOD==0.731f && !expected.AUTO_COLOR_SHIFT,"next scope missed mutation");
 snapshot_builds=0;dispatch_normal();
 require(snapshot_builds==1 && active_render_params_depth()==-1,"next scope imbalance");
 std::puts("exact_q16_samples=240 fields=19 builds_per_scope=1 balanced=1 frozen_then_visible=1");
}
'''.replace('EQUAL',equal).replace('ACTUAL_BRANCH',branch).replace('FRAMEWORK_DEFINE','#define K1_EFFECT_FRAMEWORK_V1 1' if request.param=='framework' else '').replace('EXPECTED_ROUTE','2' if request.param=='framework' else '1')
    replay._render_cpp=lambda *args,**kwargs: source
    ok,exe,meta=replay.build_binary(work,mode='bloom')
    assert ok,meta['stderr']
    return exe


def test_actual_normal_primary_scope_is_exact_balanced_and_bounded(binary):
    result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert 'exact_q16_samples=240 fields=19 builds_per_scope=1 balanced=1 frozen_then_visible=1' in result.stdout
