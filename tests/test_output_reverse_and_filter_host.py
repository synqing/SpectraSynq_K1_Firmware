"""Execute production packed reversal and secondary filter arithmetic on host."""
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VISUAL = ROOT / "SPECTRASYNQ_K1_FIRMWARE/visual"


def test_packed_reverse_and_filter(tmp_path):
    (tmp_path / "FastLED.h").write_text("""
#pragma once
#include <stdint.h>
struct CRGB {
 uint8_t r,g,b;
 CRGB():r(0),g(0),b(0){}
 CRGB(uint8_t a,uint8_t c,uint8_t d):r(a),g(c),b(d){}
 void nscale8_video(uint8_t){}
};
""")
    source = (VISUAL / "led_utilities.h").read_text()
    # Extract the actual product expressions; a narrowing regression must fail.
    product = re.search(r"(uint\d+_t green_reduction_fp = [^;]+;).*?(uint8_t green_reduction = [^;]+;)", source, re.S)
    assert product
    arithmetic = "\n".join(product.groups()).replace("uint32_t((filter_strength * 255).getInteger())", "uint32_t(strength)").replace("uint16_t((filter_strength * 255).getInteger())", "uint16_t(strength)")
    code = """
#include <cassert>
#include <cstring>
#include "ws2816_pack.h"
int main() {
 for (uint16_t n=0;n<=160;++n) {
  CRGB wire[320] = {}, original[320] = {};
  for(uint16_t i=0;i<n;++i)
   ws2816_pack_pixel(wire,i,0x1000+i,0x4500+2*i,0xAB00+3*i);
  memcpy(original,wire,sizeof(wire));
  ws2816_reverse_packed_pixels(wire,n);
  for(uint16_t i=0;i<n;++i)
   assert(memcmp(&wire[2*i],&original[2*(n-1-i)],2*sizeof(CRGB))==0);
  ws2816_reverse_packed_pixels(wire,n);
  assert(memcmp(wire,original,sizeof(wire))==0);
 }
 for(unsigned g=0;g<256;++g) for(unsigned b=0;b<256;++b)
 for(unsigned strength: {0u,1u,64u,128u,254u,255u}) {
  const uint8_t g_raw=g, blue_reduction=b;
""" + arithmetic + """
  assert(green_reduction == (uint64_t(g)*b*strength/65536));
 }
}
"""
    code = "#include <initializer_list>\n" + code
    (tmp_path / "check.cpp").write_text(code)
    exe = tmp_path / "check"
    compiler = shutil.which("clang++") or shutil.which("g++")
    subprocess.run([compiler,"-std=c++17","-O1","-fsanitize=address,undefined",f"-I{tmp_path}",f"-I{VISUAL}",str(tmp_path/"check.cpp"),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)


def test_reverse_reaches_both_product_packed_buffers():
    source = (VISUAL / "led_utilities.h").read_text()
    assert "CONFIG.REVERSE_ORDER == false" not in source
    assert "ws2816_reverse_packed_pixels(ws2816_wire, CONFIG.LED_COUNT)" in source
    assert "ws2816_reverse_packed_pixels(ws2816_wire_secondary, SECONDARY_LED_COUNT)" in source
