"""24-bit LE DMA unpack and 24->16 mapping."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HDR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_unpack.h"

SRC = r"""
#include "k1_pcm1808_unpack.h"
#include <stdint.h>
#include <stdio.h>
static int fail = 0;
static void expect_i32(const char *n, int32_t got, int32_t want) {
  if (got != want) { printf("FAIL %s got=%d want=%d\n", n, got, want); fail=1; }
}
int main() {
  uint8_t z[3]={0,0,0};
  expect_i32("0", k1_pcm1808_unpack_le24(z), 0);
  uint8_t one[3]={1,0,0};
  expect_i32("+1", k1_pcm1808_unpack_le24(one), 1);
  uint8_t pmax[3]={0xFF,0xFF,0x7F};
  expect_i32("+max", k1_pcm1808_unpack_le24(pmax), 8388607);
  uint8_t nmin[3]={0x00,0x00,0x80};
  expect_i32("-min", k1_pcm1808_unpack_le24(nmin), -8388608);
  uint8_t neg1[3]={0xFF,0xFF,0xFF};
  expect_i32("-1", k1_pcm1808_unpack_le24(neg1), -1);
  if (k1_pcm1808_s24_to_s16(0) != 0) fail=1;
  if (k1_pcm1808_s24_to_s16(8388607) != 32767) fail=1;
  if (k1_pcm1808_s24_to_s16(-8388608) != -32768) fail=1;
  return fail;
}
"""


def test_le24_vectors_and_s16_sat():
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "t.cpp"
        exe = Path(td) / "t"
        cpp.write_text(SRC, encoding="utf-8")
        subprocess.check_call(
            ["c++", "-std=c++17", "-I", str(HDR.parent), str(cpp), "-o", str(exe)]
        )
        subprocess.check_call([str(exe)])
