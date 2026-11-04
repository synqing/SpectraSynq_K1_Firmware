"""Exact saturation scaling versus the pinned original body, with real FixedPoints.
The old arithmetic is correct: this is equivalence and fault-detection evidence,
not a claim that the original implementation should fail numerical tests.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h"

# Original 5dacc3e9 body, retained independently of the candidate and git history.
REFERENCE=r'''inline CRGB16 clamp_reference(CRGB16 color) {
  if (color.r < SQ15x16(0.0)) color.r = SQ15x16(0.0);
  if (color.g < SQ15x16(0.0)) color.g = SQ15x16(0.0);
  if (color.b < SQ15x16(0.0)) color.b = SQ15x16(0.0);

  SQ15x16 max_channel = color.r;
  if (color.g > max_channel) max_channel = color.g;
  if (color.b > max_channel) max_channel = color.b;

  if (max_channel > SQ15x16(1.0)) {
    const SQ15x16 scale = SQ15x16(1.0) / max_channel;
    color.r *= scale;
    color.g *= scale;
    color.b *= scale;
  }
  return color;
}'''
MAIN=r'''#include <cassert>
#include <cstdio>
#include <random>
#include <climits>
uint64_t denominators=0,colours=0;
void denominator(uint32_t d){
 if(d<=65536 || d>INT32_MAX)return;
 const auto original=SQ15x16(1.0)/SQ15x16::fromInternal(int32_t(d));
 const auto expected=original.getInternal();const auto got=production_scale(SQ15x16::fromInternal(int32_t(d))).getInternal();
 if(expected!=got){fprintf(stderr,"quotient mismatch d=%u expected=%d got=%u\n",d,expected,got);std::exit(1);}
 ++denominators;
}
void colour(int32_t r,int32_t g,int32_t b){
 CRGB16 src={SQ15x16::fromInternal(r),SQ15x16::fromInternal(g),SQ15x16::fromInternal(b)};
 #if FEATURE_MABUTRACE && FEATURE_TRACE_RENDER
 const uint32_t before=k1_trace_saturated_pixels;
#endif
 const auto ref=clamp_reference(src),got=clamp_crgb16_preserve_sat(src);
#if FEATURE_MABUTRACE && FEATURE_TRACE_RENDER
 const uint32_t expected_count=(r>65536 || g>65536 || b>65536)?1u:0u;
 assert(k1_trace_saturated_pixels-before==expected_count);
#endif
 assert(ref.r.getInternal()==got.r.getInternal());assert(ref.g.getInternal()==got.g.getInternal());assert(ref.b.getInternal()==got.b.getInternal());++colours;
}
int main(){
 colour(131072,65536,-1);
 // Exercise the power-of-two correction first so a missing-correction fault fails.
 denominator(131072);
 for(uint32_t d=65537;d<=4194304;++d){denominator(d);if((d&31)==0)colour(d,d/2,1);}
 for(uint64_t q=2;q<=65535;++q){uint64_t boundary=(uint64_t(1)<<32)/q;for(int j=-2;j<=2;++j){denominator(uint32_t(boundary+j));if(boundary+j<=INT32_MAX)colour(int32_t(boundary+j),int32_t(boundary/3),-1);}}
 for(int p=17;p<=30;++p)for(int delta=-3;delta<=3;++delta)denominator((1u<<p)+delta);
 std::mt19937 rng(0x32514650);
 for(unsigned i=0;i<2000000;++i){uint32_t d=65537u+rng()%(uint32_t(INT32_MAX)-65536u);denominator(d);colour(int32_t(rng()),int32_t(rng()),int32_t(rng()));}
 for(int32_t r:{INT32_MIN,-65537,-65536,-1,0,1,65535,65536,65537,131072,INT32_MAX})
 for(int32_t g:{INT32_MIN,-1,0,1,65536,INT32_MAX})
 for(int32_t b:{INT32_MIN,-1,0,1,65536,INT32_MAX})colour(r,g,b);
 printf("PASS denominators=%llu colours=%llu channels=%llu\n",(unsigned long long)denominators,(unsigned long long)colours,(unsigned long long)(colours*3));
}
'''


def actual_body():
    source=SOURCE.read_text();start=source.index("inline CRGB16 clamp_crgb16_preserve_sat(")
    brace=source.index("{",start);depth=0
    for i in range(brace,len(source)):
        depth+=(source[i]=="{")-(source[i]=="}")
        if depth==0:return source[start:i+1]
    raise AssertionError("unterminated product function")


def build_run(tmp_path, body, flags=(0,0), label="check"):
    (tmp_path/"Arduino.h").write_text("#pragma once\n#include <stdint.h>\n")
    # Extract the product's exact scale statements, not a second copy of its
    # formula, so the denominator sweep exercises the implementation being built.
    scale=body[body.index("    const uint32_t d ="):body.index("    color.r *= scale;")]
    code="""#include <cstdint>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
static_assert(sizeof(SQ15x16::InternalType)==4,"32-bit raw contract");
struct CRGB16 {SQ15x16 r,g,b;};
#if FEATURE_MABUTRACE && FEATURE_TRACE_RENDER
uint32_t k1_trace_saturated_pixels=0;
#endif
"""+REFERENCE+"\n"+body+"\nSQ15x16 production_scale(SQ15x16 max_channel){\n"+scale+"return scale;}\n"+MAIN
    cpp=tmp_path/(label+".cpp");exe=tmp_path/label;cpp.write_text(code)
    compiler=shutil.which("g++-16") or shutil.which("g++")
    assert compiler,"real C++ compiler required"
    subprocess.run([compiler,"-std=c++17","-O2","-ffp-contract=off","-fsanitize=address,undefined","-fno-sanitize-recover=all",f"-DFEATURE_MABUTRACE={flags[0]}",f"-DFEATURE_TRACE_RENDER={flags[1]}",f"-I{tmp_path}",f"-I{ROOT/'libraries/FixedPoints/src'}",str(cpp),"-o",str(exe)],check=True,capture_output=True,text=True)
    result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=180)
    (tmp_path/(label+".stdout")).write_text(result.stdout)
    (tmp_path/(label+".stderr")).write_text(result.stderr)
    return result,exe


def test_actual_exact_reciprocal_and_private_counter(tmp_path):
    assert hashlib.sha256(REFERENCE.encode()).hexdigest()=="137d7b149c60bbb1f9451a0ee9164fba5c1c44109764f475bcd3ecb1ac950bcc"
    body=actual_body()
    for flags in ((0,0),(0,1),(1,0),(1,1)):
        label=f"actual-{flags[0]}{flags[1]}"
        result,exe=build_run(tmp_path,body,flags,label)
        assert result.returncode==0,result.stderr
        assert "denominators=6456531 colours=2457088 channels=7371264" in result.stdout
        symbols=subprocess.check_output([shutil.which("nm"),str(exe)],text=True)
        assert ("k1_trace_saturated_pixels" in symbols)==(flags==(1,1))


def test_faults_in_actual_body_are_rejected(tmp_path):
    body=actual_body()
    mutations={"missing-correction":body.replace(" + ((d & (d - 1u)) == 0u)",""),"extra-unit":body.replace("UINT32_MAX / d +","UINT32_MAX / d + 1u +")}
    for label,mutant in mutations.items():
        assert mutant!=body
        result,_=build_run(tmp_path,mutant,label=label)
        assert result.returncode!=0 and "ref.r.getInternal()==got.r.getInternal()" in result.stderr,result.stderr
