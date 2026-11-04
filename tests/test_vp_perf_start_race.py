"""Execute actual render timing guards across asynchronous diagnostic start."""
from pathlib import Path
import re
import subprocess
import pytest

FW = Path(__file__).resolve().parents[1] / "SPECTRASYNQ_K1_FIRMWARE"

@pytest.mark.parametrize("stat,start", [
    ("primary_render", "vp_perf_stage_start_us"),
    ("secondary_render", "vp_perf_secondary_start_us"),
])
def test_render_start_midstage_does_not_record_uptime(tmp_path, stat, start):
    ino = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text()
    block = re.search(
        r"if \(vp_perf.running[^\n]*\) \{\s*"
        r"vp_perf_record\(vp_perf\." + stat + r",[^;]+;\s*\}", ino
    )
    assert block, "production render timing block missing"
    source = r"""
#include <stdint.h>
#include <assert.h>
struct Stat { unsigned count = 0; uint32_t elapsed = 0; };
struct State { bool running = false; Stat primary_render, secondary_render; } vp_perf;
int64_t now_us;
int64_t esp_timer_get_time() { return now_us; }
void vp_perf_record(Stat& s, uint32_t elapsed) {
  if (vp_perf.running) { ++s.count; s.elapsed = elapsed; }
}
void finish(int64_t START) { BLOCK }
int main() {
  // Begin while stopped; command starts recording before the stage ends.
  now_us = 264205033; vp_perf.running = true;
  finish(0);
  assert(vp_perf.STAT.count == 0);
  // A complete active stage retains its actual elapsed time.
  finish(now_us - 1795);
  assert(vp_perf.STAT.count == 1 && vp_perf.STAT.elapsed == 1795);
  // Stop before stage end discards it.
  vp_perf.running = false; finish(now_us - 1000);
  assert(vp_perf.STAT.count == 1);
  // High uptime does not affect a valid 64-bit timer difference.
  vp_perf.running = true; now_us = 4294967296LL + 2000000;
  finish(now_us - 2528);
  assert(vp_perf.STAT.count == 2 && vp_perf.STAT.elapsed == 2528);
}
""".replace("START", start).replace("BLOCK", block.group()).replace("STAT", stat)
    cpp = tmp_path / "guard.cpp"
    exe = tmp_path / "guard"
    cpp.write_text(source)
    subprocess.run(["c++", "-std=c++17", "-O2", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True, timeout=10)
