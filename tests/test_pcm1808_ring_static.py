"""SPSC PCM ring: wrap, drop, whole-frame copies, producer/consumer counts."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HDR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_ring.h"

SRC = r"""
#include "k1_pcm1808_ring.h"
#include <stdio.h>
#include <stdint.h>
static int fail = 0;
static void expect_u32(const char *n, uint32_t got, uint32_t want) {
  if (got != want) { printf("FAIL %s got=%u want=%u\n", n, got, want); fail = 1; }
}
int main() {
  uint8_t store[8 * 6];
  K1PcmRing q = {};
  q.buf = store;
  q.cap_frames = 8;
  k1_pcm_ring_reset(&q);

  uint8_t a[2 * 6];
  for (int i = 0; i < 12; i++) a[i] = (uint8_t)(i + 1);
  expect_u32("push2", k1_pcm_ring_push(&q, a, 2), 2);
  expect_u32("used2", k1_pcm_ring_used(&q), 2);

  uint8_t b[8 * 6];
  expect_u32("push_overflow", k1_pcm_ring_push(&q, b, 8), 0);
  expect_u32("dropped", q.dropped_frames, 8);
  expect_u32("used_unchanged", k1_pcm_ring_used(&q), 2);

  uint8_t out[2 * 6];
  expect_u32("pop2", k1_pcm_ring_pop(&q, out, 2), 2);
  expect_u32("empty", k1_pcm_ring_used(&q), 0);
  if (out[0] != 1 || out[11] != 12) { printf("FAIL payload\n"); fail = 1; }

  // wrap: fill 7, pop 5, push 4 (wraps)
  uint8_t c[7 * 6];
  for (int i = 0; i < 42; i++) c[i] = (uint8_t)(100 + i);
  expect_u32("push7", k1_pcm_ring_push(&q, c, 7), 7);
  uint8_t junk[5 * 6];
  expect_u32("pop5", k1_pcm_ring_pop(&q, junk, 5), 5);
  uint8_t d[4 * 6];
  for (int i = 0; i < 24; i++) d[i] = (uint8_t)(200 + i);
  expect_u32("push4_wrap", k1_pcm_ring_push(&q, d, 4), 4);
  expect_u32("used6", k1_pcm_ring_used(&q), 6);
  uint8_t e[6 * 6];
  expect_u32("pop6", k1_pcm_ring_pop(&q, e, 6), 6);
  if (e[0] != 100 + 5 * 6) { printf("FAIL wrap head %u\n", e[0]); fail = 1; }
  if (e[2 * 6] != 200) { printf("FAIL wrap seam %u\n", e[12]); fail = 1; }
  expect_u32("high_water", q.high_water, 7);
  expect_u32("no_partial", (uint32_t)K1_PCM_STEREO_FRAME_BYTES, 6);

  k1_pcm_ring_reset(&q);
  expect_u32("push7b", k1_pcm_ring_push(&q, c, 7), 7);
  expect_u32("discard3", k1_pcm_ring_discard(&q, 3), 3);
  expect_u32("used_after_discard", k1_pcm_ring_used(&q), 4);
  expect_u32("discard_all", k1_pcm_ring_discard(&q, 99), 4);
  expect_u32("empty_after_discard", k1_pcm_ring_used(&q), 0);
  return fail;
}
"""


def test_ring_wrap_drop_and_counts():
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "t.cpp"
        exe = Path(td) / "t"
        cpp.write_text(SRC, encoding="utf-8")
        subprocess.check_call(["c++", "-std=c++17", "-I", str(HDR.parent), str(cpp), "-o", str(exe)])
        subprocess.check_call([str(exe)])
