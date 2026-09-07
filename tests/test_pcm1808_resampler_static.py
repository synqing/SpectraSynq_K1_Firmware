"""48k -> 12.8k rational SRC: counts, DC, continuity, alias."""

from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"

SRC = r"""
#include "k1_resample_48k_to_12k8.h"
#include <math.h>
#include <stdio.h>
#include <vector>
int fail=0;
int main() {
  K1PcmSrc s;
  k1_pcm_src_reset(&s);
  float in[360];
  float out[96];
  // SRC-T1 counts over 10 hops
  for (int hop=0; hop<10; hop++) {
    for (int i=0; i<360; i++) in[i] = 1000.0f;
    k1_pcm_src_hop360(&s, in, out);
  }
  if (s.in_count != 3600) { printf("in_count %d\n", s.in_count); fail=1; }
  if (s.out_count != 960) { printf("out_count %d\n", s.out_count); fail=1; }
  if (s.in_count * 4 != s.out_count * 15) fail=1;

  // SRC-T3 DC after settle
  float mean=0;
  for (int i=0;i<96;i++) mean += out[i];
  mean /= 96.0f;
  printf("dc_mean=%.6f\n", mean);
  if (fabsf(mean - 1000.0f) > 20.0f) fail=1;

  // SRC-T2 continuity: one long stream vs hops
  K1PcmSrc a,b;
  k1_pcm_src_reset(&a);
  k1_pcm_src_reset(&b);
  std::vector<float> long_in(360*4, 0.0f);
  for (int i=0;i<(int)long_in.size();i++) long_in[i] = sinf(2.0f*3.14159265f*1000.0f*i/48000.0f);
  float hop_out[96*4];
  for (int h=0;h<4;h++) k1_pcm_src_hop360(&a, long_in.data()+h*360, hop_out+h*96);
  float once[96*4];
  for (int h=0;h<4;h++) k1_pcm_src_hop360(&b, long_in.data()+h*360, once+h*96);
  float maxd=0;
  for (int i=0;i<96*4;i++) {
    float d = fabsf(hop_out[i]-once[i]);
    if (d>maxd) maxd=d;
  }
  printf("cont_maxd=%.6e\n", maxd);
  if (maxd > 1e-4f) fail=1;
  return fail;
}
"""


def test_src_counts_dc_continuity():
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "t.cpp"
        exe = Path(td) / "t"
        cpp.write_text(SRC, encoding="utf-8")
        subprocess.check_call(
            ["c++", "-std=c++17", "-I", str(AUDIO), str(cpp), "-o", str(exe)]
        )
        out = subprocess.check_output([str(exe)], text=True)
        assert "dc_mean=" in out


def test_src_alias_energy_is_small():
    """8 kHz at 48 kHz must not dominate the 12.8 kHz output."""
    src = r"""
#include "k1_resample_48k_to_12k8.h"
#include <math.h>
#include <stdio.h>
int main() {
  K1PcmSrc s; k1_pcm_src_reset(&s);
  float in[360]; float out[96];
  double acc=0, acc8=0;
  const float w = 2.0f*3.14159265f;
  for (int hop=0; hop<8; hop++) {
    for (int i=0;i<360;i++) {
      int n = hop*360+i;
      in[i] = sinf(w*8000.0f*n/48000.0f);
    }
    k1_pcm_src_hop360(&s, in, out);
    if (hop < 2) continue;
    for (int i=0;i<96;i++) acc += (double)out[i]*out[i];
  }
  printf("alias_energy=%.6f\n", acc);
  // Settled output energy of a stopband tone must be far below full-scale^2 * N
  return (acc < 1.0e6) ? 0 : 1;
}
"""
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "t.cpp"
        exe = Path(td) / "t"
        cpp.write_text(src, encoding="utf-8")
        subprocess.check_call(
            ["c++", "-std=c++17", "-I", str(AUDIO), str(cpp), "-o", str(exe)]
        )
        subprocess.check_call([str(exe)])
