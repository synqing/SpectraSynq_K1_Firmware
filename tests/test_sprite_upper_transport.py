"""Exact upper-half transport against the unchanged full transport and caller discard.
No palette/effect retuning or target-timing claims. Both complete product bodies
are compiled with the real FixedPoints library; no numerical expected formula.
"""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LED=ROOT/"SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h"
CALLERS={"spectrum_river","spectrum_river_v2","ember","tempo_river","dense_forge","dense_forge_chord","chroma_constellation","river_surge","tempo_river_walk"}
ORIGINAL_SHA256="bec1a3d8327776069af0985930e733289b5121fd8c77dc487e5e50c072b78f44"  # unchanged668f9151 body


def block(text,start):
    brace=text.index("{",start);depth=0
    for i in range(brace,len(text)):
        depth+=(text[i]=="{")-(text[i]=="}")
        if depth==0:return text[start:i+1]
    raise AssertionError("unterminated source block")


def test_only_approved_callers_and_unchanged_original():
    source=LED.read_text()
    original=block(source,source.index("inline void draw_sprite("))
    assert hashlib.sha256(original.encode()).hexdigest()==ORIGINAL_SHA256
    users={}
    for path in (ROOT/"SPECTRASYNQ_K1_FIRMWARE/effects").glob("light_mode_*.cpp"):
        count=path.read_text().count("draw_sprite_upper(")
        if count:users[path.stem.removeprefix("light_mode_")]=count
    assert users=={name:1 for name in CALLERS}
    candidate=block(source,source.index("inline void draw_sprite_upper("))
    assert not re.search(r"\b(new|delete|malloc|calloc|realloc|free|String)\b",candidate)


MAIN=r'''int main() {
 std::mt19937 rng(0x16080); uint64_t cases=0;
 auto test=[&](float pos, int32_t aq, bool boundary) {
   CRGB16 src[160],saved[160],ref[160]={},got[160]={};
   for(int i=0;i<160;i++) {
     src[i]={SQ15x16::fromInternal(rng()%65537),SQ15x16::fromInternal(rng()%65537),SQ15x16::fromInternal(rng()%65537)};
     if(boundary) src[i]={};
   }
   if(boundary) src[79]={SQ15x16(1),SQ15x16::fromInternal(32769),SQ15x16::fromInternal(1)};
   memcpy(saved,src,sizeof src);
   draw_sprite(ref,src,160,160,pos,SQ15x16::fromInternal(aq));
   discard_lower(ref);
   draw_sprite_upper(got,src,160,160,pos,SQ15x16::fromInternal(aq));
   discard_lower(got);
   for(int i=0;i<160;i++) if(ref[i].r.getInternal()!=got[i].r.getInternal() || ref[i].g.getInternal()!=got[i].g.getInternal() || ref[i].b.getInternal()!=got[i].b.getInternal()) {
     std::fprintf(stderr,"mismatch pos=%a alpha=%d index=%d boundary=%d\n",pos,aq,i,boundary);return false;
   }
   if(memcmp(saved,src,sizeof src)) return false;
   cases++;return true;
 };
 if(!test(0.5f,65536,true))return 1; // Source79 contributes across centre to80.
 // Every 1/256-pixel offset over [-161,161], representative fixed alpha endpoints.
 for(int p=-161*256;p<=161*256;p++) for(int a: {0,1,32767,32768,53739,58982,65535,65536})
   if(!test(p/256.0f,a,false))return 1;
 // Independent random positions/alpha; includes negative fractional truncation.
 for(int i=0;i<100000;i++) if(!test(std::uniform_real_distribution<float>(-200,200)(rng),rng()%65537,false))return 1;
 for(float p: {-80.5f,-1.999f,-1.0f,-0.999f,-0.5f,0.0f,0.00001f,0.5f,0.99999f,1.0f,1.5f,80.5f})
   for(int a:{0,1,32768,65535,65536}) if(!test(p,a,true))return 1;
 std::printf("exact_fixed_channel_comparisons=%llu cases=%llu source_unchanged=1\n",(unsigned long long)(cases*480),(unsigned long long)cases);
}
'''


def test_actual_sprite_transport_exact_and_fault_sensitive(tmp_path):
    source=LED.read_text()
    original=block(source,source.index("inline void draw_sprite("))
    candidate=block(source,source.index("inline void draw_sprite_upper("))
    # This is the existing real caller's discard, not an independent formula
    # that happens to duplicate the new helper's guards.
    river=(ROOT/"SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_spectrum_river.cpp").read_text()
    start=river.index("for (uint16_t i = 0; i < HALF; i++)")
    discard=block(river,start)
    preamble="""#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
struct CRGB16 {SQ15x16 r,g,b;};
"""
    discard="void discard_lower(CRGB16* leds_16){constexpr unsigned HALF=80;"+discard+"}\n"
    compiler=shutil.which("g++-16") or shutil.which("g++")
    assert compiler,"a real C++ compiler is required"
    variants={"actual":candidate,"lost_centre_destination":candidate.replace(">= 80",">= 81"),"lost_source79":candidate.replace("uint16_t i = 0","uint16_t i = 80")}
    for label,body in variants.items():
        cpp=tmp_path/(label+".cpp");exe=tmp_path/label
        cpp.write_text(preamble+original+"\n"+body+"\n"+discard+MAIN)
        subprocess.run([compiler,"-std=c++17","-O2","-ffp-contract=off","-fsanitize=address,undefined","-fno-sanitize-recover=all","-I",str(ROOT/"scripts/regression-harness/stubs"),"-I",str(ROOT/"libraries/FixedPoints/src"),str(cpp),"-o",str(exe)],check=True,capture_output=True,text=True)
        run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=180)
        (tmp_path/(label+".stdout")).write_text(run.stdout)
        (tmp_path/(label+".stderr")).write_text(run.stderr)
        if label=="actual":
            assert run.returncode==0,run.stderr
            assert "cases=759525 source_unchanged=1" in run.stdout
        else:
            assert run.returncode!=0 and "mismatch" in run.stderr,(label,run.stdout,run.stderr)
