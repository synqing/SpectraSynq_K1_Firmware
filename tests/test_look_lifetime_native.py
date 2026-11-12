"""Stage B (Modernes C++ next phase, 10 Nov 2026): loadable look-table lifetime.

Compiles the PRODUCT headers (visual/k1_look.h + visual/k1_look_file.h, the
same code the k1_fe build uses for K1_LOOK_LIB_V1) on the host with a tracking
allocator, then drives reader/writer interleavings:

* deterministic: a render reader (K1LookFrame, as the packers use it) holds the
  old table while a replacement / clear / failed replacement arrives; nothing
  it can still read is freed, it keeps the complete old table, and the retired
  storage is freed once no reader is registered (no leak);
* stress: one thread renders continuously while another replaces and clears
  the slot; freed memory is poisoned, so a reader touching freed storage or a
  torn type/payload pair produces a value outside the valid set. Built with
  ThreadSanitizer where the host compiler supports it.

The allocator, wait budget and clock are the header's own seams
(K1_LOOK_ALLOC / K1_LOOK_FREE / K1_LOOK_RECLAIM_WAIT_US); the lifetime logic
under test is unmodified product code.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))

from oracle_bridge_fs_codec import _find_compiler  # noqa: E402

FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

PRELUDE = r"""
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <mutex>
#include <vector>

// Tracking allocator: freed blocks are poisoned and parked (not returned to
// the C heap) so any later read of them is visible as a wrong value.
static std::mutex g_mu;
static std::map<void *, size_t> g_live;
static std::vector<std::pair<void *, size_t>> g_parked;
static int g_fail_next_alloc = 0;
static int g_frees = 0;
static void *t_alloc(size_t n) {
  std::lock_guard<std::mutex> l(g_mu);
  if (g_fail_next_alloc > 0) { g_fail_next_alloc--; return nullptr; }
  void *p = std::malloc(n);
  g_live[p] = n;
  return p;
}
static void t_free(void *p) {
  if (!p) return;
  size_t n;
  {
    std::lock_guard<std::mutex> l(g_mu);
    auto it = g_live.find(p);
    if (it == g_live.end()) { std::printf("FAIL double_or_foreign_free\n"); std::exit(3); }
    n = it->second;
    g_live.erase(it);
    g_frees++;
    g_parked.push_back({p, n});
  }
  std::memset(p, 0xA5, n);
}
static size_t live_blocks() { std::lock_guard<std::mutex> l(g_mu); return g_live.size(); }
#define K1_LOOK_ALLOC(n) t_alloc(n)
#define K1_LOOK_FREE(p) t_free(p)
#define K1_LOOK_LIB_V1 1
#include "k1_look_file.h"

// K1LT matrix file: diagonal gain `q16` on all three channels.
static std::vector<uint8_t> matrix_file(int32_t q16) {
  int32_t m[12] = {q16, 0, 0, 0, 0, q16, 0, 0, 0, 0, q16, 0};
  std::vector<uint8_t> out(16 + 48 + 4);
  size_t n = 0;
  if (!k1_look_build_k1lt(K1_LOOK_MATRIX_3X4, 0, (const uint8_t *)m, 48, out.data(), out.size(), &n)) {
    std::printf("FAIL build\n"); std::exit(3);
  }
  out.resize(n);
  return out;
}
static uint16_t apply_frame(uint8_t slot, uint16_t v) {
  K1LookFrame f(slot);
  uint16_t r = v, g = v, b = v;
  f.apply(&r, &g, &b);
  if (r != g || g != b) return 1;  // torn / poisoned
  return r;
}
#define CHECK(cond, tag) do { if (!(cond)) { std::printf("FAIL %s line %d\n", tag, __LINE__); return 1; } } while (0)
"""

DETERMINISTIC = PRELUDE + r"""
int main() {
  const auto A = matrix_file(2 * 65536);  // 1000 -> 2000
  const auto B = matrix_file(3 * 65536);  // 1000 -> 3000
  const auto C = matrix_file(4 * 65536);  // 1000 -> 4000

  // --- install, select on both edges (secondary inherits primary) ---
  CHECK(k1_look_install_parsed_ex(12, A.data(), A.size()) == K1_LOOK_OK, "install_A");
  CHECK(k1_look_publish(12) && k1_look_publish_sec(255), "select");
  CHECK(apply_frame(k1_look_slot, 1000) == 2000, "A_live");
  CHECK(apply_frame(k1_look_effective_sec(), 1000) == 2000, "A_inherited");
  CHECK(live_blocks() == 1, "one_block");

  // --- replacement while a primary AND an inheriting secondary reader hold A ---
  {
    K1LookFrame prim(k1_look_slot);
    K1LookFrame sec(k1_look_effective_sec());
    CHECK(k1_look_install_parsed_ex(12, B.data(), B.size()) == K1_LOOK_OK, "install_B");
    CHECK(g_frees == 0 && k1_look_retired_n == 1, "A_retired_not_freed");
    uint16_t r = 1000, g = 1000, b = 1000;
    prim.apply(&r, &g, &b);
    CHECK(r == 2000 && g == 2000 && b == 2000, "prim_still_complete_A");
    r = g = b = 1000;
    sec.apply(&r, &g, &b);
    CHECK(r == 2000, "sec_still_complete_A");
    CHECK(apply_frame(12, 1000) == 3000, "new_reader_sees_B");
    // A later look operation while readers remain: still nothing freed.
    CHECK(k1_look_reclaim() == 1 && g_frees == 0, "reclaim_deferred_while_reading");
  }
  CHECK(k1_look_reclaim() == 0 && g_frees == 1, "A_freed_after_readers_left");
  CHECK(live_blocks() == 1 && k1_look_slot == 12, "B_live_selection_kept");

  // --- clear while a reader holds B; repeated clear ---
  {
    K1LookFrame prim(k1_look_slot);
    CHECK(k1_look_ram_clear(12) == K1_LOOK_OK, "clear");
    CHECK(k1_look_slot == 0 && k1_look_slot_sec == 255, "selection_fallback");
    CHECK(g_frees == 1, "B_not_freed_under_reader");
    uint16_t r = 1000, g = 1000, b = 1000;
    prim.apply(&r, &g, &b);
    CHECK(r == 3000, "reader_keeps_B");
    CHECK(apply_frame(12, 1000) == 1000, "cleared_slot_is_identity");
    CHECK(k1_look_ram_clear(12) == K1_LOOK_OK, "repeat_clear_while_reading");
  }
  CHECK(k1_look_ram_clear(12) == K1_LOOK_OK, "repeat_clear");
  CHECK(g_frees == 2 && live_blocks() == 0 && k1_look_retired_n == 0, "no_leak_after_clear");

  // --- explicit secondary on its own slot; clearing it re-inherits ---
  CHECK(k1_look_install_parsed_ex(13, A.data(), A.size()) == K1_LOOK_OK, "install_13");
  CHECK(k1_look_install_parsed_ex(14, C.data(), C.size()) == K1_LOOK_OK, "install_14");
  CHECK(k1_look_publish(13) && k1_look_publish_sec(14), "select_13_14");
  CHECK(apply_frame(k1_look_effective_sec(), 1000) == 4000, "sec_14");
  CHECK(k1_look_ram_clear(14) == K1_LOOK_OK && k1_look_slot_sec == 255, "sec_clear");
  CHECK(apply_frame(k1_look_effective_sec(), 1000) == 2000, "sec_inherits_13");

  // --- failed replacements keep the old table published and owned ---
  const size_t live_before = live_blocks();
  auto bad = A;
  bad[bad.size() - 1] ^= 0xFF;  // CRC
  CHECK(k1_look_install_parsed_ex(13, bad.data(), bad.size()) == K1_LOOK_ERR_FILE, "bad_crc");
  auto huge = A;  // payload_bytes that would wrap HEADER + 4 + n on 32-bit
  const uint32_t wrap = 0xFFFFFFF0u;
  std::memcpy(huge.data() + 12, &wrap, 4);
  CHECK(k1_look_install_parsed_ex(13, huge.data(), huge.size()) == K1_LOOK_ERR_FILE, "wrap_len");
  {
    // Valid file, table type this build does not render (CUBE_33).
    std::vector<uint8_t> cube33(16 + 64 + 4);
    uint8_t pay[64] = {};
    size_t n = 0;
    CHECK(k1_look_build_k1lt(K1_LOOK_CUBE_33, 33, pay, 64, cube33.data(), cube33.size(), &n), "b33");
    CHECK(k1_look_install_parsed_ex(13, cube33.data(), n) == K1_LOOK_ERR_FILE, "unsupported");
  }
  g_fail_next_alloc = 1;
  CHECK(k1_look_install_parsed_ex(13, B.data(), B.size()) == K1_LOOK_ERR_NO_MEMORY, "oom");
  CHECK(k1_look_install_parsed_ex(7, B.data(), B.size()) == K1_LOOK_ERR_SLOT, "slot7");
  CHECK(k1_look_ram_clear(3) == K1_LOOK_ERR_SLOT, "clear_compiled");
  CHECK(live_blocks() == live_before && apply_frame(13, 1000) == 2000 && k1_look_slot == 13,
        "old_kept_after_failures");

  // --- retire list full while a reader is stuck: refuse, keep latest ---
  {
    K1LookFrame stuck(13);
    for (int i = 0; i < K1_LOOK_RETIRE_MAX; i++) {
      const auto &f = (i & 1) ? A : B;
      CHECK(k1_look_install_parsed_ex(13, f.data(), f.size()) == K1_LOOK_OK, "fill");
    }
    CHECK(k1_look_retired_n == K1_LOOK_RETIRE_MAX, "retire_full");
    const uint16_t latest = apply_frame(13, 1000);
    CHECK(k1_look_install_parsed_ex(13, C.data(), C.size()) == K1_LOOK_ERR_BUSY, "busy_install");
    CHECK(k1_look_ram_clear(13) == K1_LOOK_ERR_BUSY, "busy_clear");
    CHECK(apply_frame(13, 1000) == latest && k1_look_slot == 13, "latest_kept_when_busy");
    uint16_t r = 1000, g = 1000, b = 1000;
    stuck.apply(&r, &g, &b);
    CHECK(r == 2000, "stuck_reader_intact");
  }
  // The reader finished after its writer stopped waiting: the next look
  // operation completes the reclaim.
  CHECK(k1_look_install_parsed_ex(13, C.data(), C.size()) == K1_LOOK_OK, "after_stuck");
  CHECK(k1_look_retired_n == 0, "all_reclaimed");
  CHECK(k1_look_ram_clear(13) == K1_LOOK_OK, "final_clear_13");
  CHECK(live_blocks() == 0 && k1_look_retired_n == 0, "no_leak_end");
  std::printf("ok frees=%d\n", g_frees);
  return 0;
}
"""

STRESS = PRELUDE + r"""
#include <atomic>
#include <thread>
int main() {
  const auto A = matrix_file(2 * 65536);
  const auto B = matrix_file(3 * 65536);
  CHECK(k1_look_install_parsed_ex(9, A.data(), A.size()) == K1_LOOK_OK, "seed");
  CHECK(k1_look_publish(9), "sel");
  std::atomic<bool> stop{false};
  std::atomic<long> bad{0}, frames{0};
  std::thread render([&] {
    while (!stop.load(std::memory_order_relaxed)) {
      K1LookFrame f(9);  // as the packers: one snapshot per edge
      for (int px = 0; px < 160; px++) {
        uint16_t r = 1000, g = 1000, b = 1000;
        f.apply(&r, &g, &b);
        // Valid: A (2000), B (3000) or cleared slot (identity, 1000).
        if (!(r == g && g == b && (r == 2000 || r == 3000 || r == 1000))) bad++;
      }
      frames++;
    }
  });
  long ops = 0;
  for (int i = 0; i < 20000; i++) {
    const int k = i % 3;
    if (k == 0) (void)k1_look_install_parsed_ex(9, A.data(), A.size());
    else if (k == 1) (void)k1_look_install_parsed_ex(9, B.data(), B.size());
    else (void)k1_look_ram_clear(9);
    ops++;
  }
  stop = true;
  render.join();
  (void)k1_look_ram_clear(9);
  (void)k1_look_reclaim();
  CHECK(bad.load() == 0, "reader_saw_freed_or_torn_table");
  CHECK(live_blocks() == 0 && k1_look_retired_n == 0, "leak");
  CHECK(frames.load() > 0, "renderer_ran");
  std::printf("ok ops=%ld frames=%ld frees=%d\n", ops, frames.load(), g_frees);
  return 0;
}
"""


def _build_and_run(td: Path, name: str, src_text: str, extra: list[str]) -> subprocess.CompletedProcess:
    cxx = _find_compiler()
    if not cxx:
        pytest.skip("no host C++ compiler")
    src = td / f"{name}.cpp"
    src.write_text(src_text, encoding="utf-8")
    exe = td / name
    cmd = [cxx, "-std=c++17", "-O1", "-g", "-I", str(FW / "visual"), "-I", str(FW / "persistence"),
           *extra, str(src), "-o", str(exe)]
    r = subprocess.run(cmd, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr[-4000:]
    return subprocess.run([str(exe)], text=True, capture_output=True, timeout=300)


def test_reader_holds_old_table_across_replace_clear_and_failures():
    with tempfile.TemporaryDirectory() as td:
        run = _build_and_run(Path(td), "look_lifetime", DETERMINISTIC, ["-fsanitize=address,undefined"])
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.startswith("ok"), run.stdout


def test_concurrent_render_and_writer_never_reads_freed_or_torn_table():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cxx = _find_compiler()
        probe = subprocess.run([cxx, "-fsanitize=thread", "-x", "c++", "-", "-o", str(td / "p")],
                               input="int main(){}", text=True, capture_output=True) if cxx else None
        tsan = probe is not None and probe.returncode == 0
        run = _build_and_run(td, "look_stress", STRESS, ["-pthread"] + (["-fsanitize=thread"] if tsan else []))
    assert run.returncode == 0, run.stdout + run.stderr[-4000:]
    assert run.stdout.startswith("ok"), run.stdout
    assert "WARNING: ThreadSanitizer" not in run.stderr, run.stderr[-4000:]
