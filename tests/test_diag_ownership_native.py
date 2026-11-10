"""Stage E (Modernes C++ next phase, 10 Nov 2026): diagnostic ownership.

Compiles the PRODUCT header visual/k1_diag_ownership.h on the host and drives:

* :identify as a render-owned request — the serial side posts and returns at
  once; the render side draws the two flashes on its own frames (same 150 ms
  phases and centre span as the old blocking_flash), publishes completion once,
  refuses a second request while busy, and accepts the next one afterwards;
* the render park self-heal policy — an ordinary park is force-resumed after
  1 s (unchanged), a diagnostic hold is not resumed before its 10 s ceiling,
  and every forced resume is counted so the probe can report itself invalid.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

DRIVER = r"""
#include "k1_diag_ownership.h"
#include <cstdio>
struct Px { int v; bool operator==(const Px& o) const { return v == o.v; } };
#define CHECK(c, t) do { if (!(c)) { std::printf("FAIL %s line %d\n", t, __LINE__); return 1; } } while (0)
int main() {
  const uint16_t N = 160;
  Px leds[N];
  const Px on{7}, off{0};
  // Idle: render keeps normal ownership.
  CHECK(!k1_identify_render_frame(0u, leds, N, on, off), "idle");
  CHECK(!k1_identify_take_completion(), "no_completion");
  // Post returns immediately; the render task owns the flash.
  CHECK(k1_identify_post(), "post");
  CHECK(!k1_identify_post(), "busy_refused");
  uint32_t t = 1000;
  int lit_frames = 0, dark_frames = 0, frames = 0;
  int pattern[4] = {0, 0, 0, 0};
  while (k1_identify_render_frame(t, leds, N, on, off)) {
    const uint32_t phase = (uint32_t)(t - 1000) / 150u;
    bool all_ok = true;
    for (uint16_t i = 0; i < N; i++) {
      const bool centre = i >= 48 && i < N - 48;
      const Px want = (phase % 2 == 0 && centre) ? on : off;
      if (!(leds[i] == want)) all_ok = false;
    }
    CHECK(all_ok, "pattern");
    pattern[phase]++;
    (phase % 2 == 0) ? lit_frames++ : dark_frames++;
    frames++;
    CHECK(!k1_identify_take_completion(), "not_done_early");
    t += 10;  // 100 FPS render frames
    CHECK(frames < 1000, "terminates");
  }
  CHECK(t - 1000 == 600, "runs_600ms");
  CHECK(pattern[0] == 15 && pattern[1] == 15 && pattern[2] == 15 && pattern[3] == 15, "phases");
  CHECK(k1_identify_take_completion(), "completion_reported");
  CHECK(!k1_identify_take_completion(), "completion_once");
  CHECK(!k1_identify_render_frame(t, leds, N, on, off), "back_to_normal");
  CHECK(k1_identify_post(), "next_accepted");
  CHECK(k1_identify_render_frame(t, leds, N, on, off), "second_runs");

  // Park self-heal policy.
  const uint32_t b0 = k1_render_park_breaks.load();
  CHECK(!k1_render_park_should_self_heal(900000), "ordinary_within_1s");
  CHECK(k1_render_park_should_self_heal(1000001), "ordinary_after_1s");
  CHECK(k1_render_park_breaks.load() == b0 + 1, "break_counted");
  k1_render_diag_hold.store(true);
  CHECK(!k1_render_park_should_self_heal(5000000), "hold_not_broken_at_5s");
  CHECK(k1_render_park_should_self_heal(10000001), "hold_ceiling");
  CHECK(k1_render_park_breaks.load() == b0 + 2, "ceiling_counted");
  std::printf("ok frames=%d lit=%d dark=%d\n", frames, lit_frames, dark_frames);
  return 0;
}
"""


def test_identify_is_render_owned_and_park_hold_policy():
    cxx = shutil.which("clang++") or shutil.which("g++")
    assert cxx
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "d.cpp"
        src.write_text(DRIVER, encoding="utf-8")
        exe = Path(td) / "d"
        r = subprocess.run([cxx, "-std=c++17", "-fsanitize=address,undefined", "-I", str(FW / "visual"),
                            str(src), "-o", str(exe)], text=True, capture_output=True)
        assert r.returncode == 0, r.stderr[-3000:]
        run = subprocess.run([str(exe)], text=True, capture_output=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.startswith("ok"), run.stdout
