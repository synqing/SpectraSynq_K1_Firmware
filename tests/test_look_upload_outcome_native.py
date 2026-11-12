"""Look upload outcome (Modernes C++ follow-on W2, 11 Nov 2026).

A serial look upload (":look_load=<slot>,<bytes>" then the raw K1LT bytes)
installs the table first and saves it to LittleFS second. When the save
failed, the upload used to answer "LOOK_LOAD: fail" although the new table was
already live. This test compiles the PRODUCT upload path
(visual/k1_look_file.h: k1_look_rx_arm -> k1_look_rx_push -> install -> save,
and k1_look_rx_reply, the word check_serial() prints after "LOOK_LOAD: ")
against the in-memory LittleFS stub and checks all three finished outcomes:

* saved:            reply "ok"; table live; file on flash equals the upload;
* save failed:      reply "installed, not saved"; new table live; the slot's
                    previously saved file is untouched (this test fails the
                    temporary-file open; boot reloads only slot 15 from flash);
* refused (bad CRC): reply "fail"; old table still live; nothing written.

The save failure is a real one: the stub's file table is full, so opening the
temporary file fails exactly as a full LittleFS would. No firmware code is
altered. One tracking allocator stands in for heap_caps_malloc/heap_caps_free
and the look allocator, so the receive buffer and every table bundle are
counted: nothing may be left behind after each upload and after the slots are
cleared.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
STUBS = ROOT / "scripts" / "regression-harness" / "stubs"

SOURCE = r"""
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "esp_heap_caps.h"  // host stub; #pragma once, so the product includes below reuse it

// One tracking allocator for the receive buffer (heap_caps_malloc/free in the
// product code) and the table bundles (the header's K1_LOOK_ALLOC seam).
static std::map<void *, size_t> g_live;
static void *t_alloc(size_t n, unsigned) {
  void *p = std::malloc(n);
  if (p) g_live[p] = n;
  return p;
}
static void t_free(void *p) {
  if (!p) return;
  auto it = g_live.find(p);
  if (it == g_live.end()) { std::printf("FAIL double_or_foreign_free\n"); std::exit(3); }
  g_live.erase(it);
  std::free(p);
}
#define heap_caps_malloc(n, caps) t_alloc((n), (caps))
#define heap_caps_free(p) t_free(p)
#define K1_LOOK_ALLOC(n) t_alloc((n), 0u)
#define K1_LOOK_FREE(p) t_free(p)
#define K1_LOOK_NOW_US() 0u
#define K1_LOOK_LIB_V1 1
#define USBSerial Serial
#include "k1_look_file.h"
HostSerial Serial;

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
static uint16_t live_level(uint8_t slot, uint16_t v) {
  K1LookFrame f(slot);
  uint16_t r = v, g = v, b = v;
  f.apply(&r, &g, &b);
  if (r != g || g != b) return 1;
  return r;
}
static std::vector<uint8_t> flash_file(uint8_t slot) {
  char path[24];
  k1_look_slot_path(slot, path, sizeof(path));
  K1HostFsEntry *e = k1_host_fs_find(path);
  return e ? std::vector<uint8_t>(e->data, e->data + e->len) : std::vector<uint8_t>();
}
// Arm and stream one upload byte by byte, exactly as check_serial() feeds it.
// Returns the reply printed after "LOOK_LOAD: " ("" if none was due).
static std::string upload(uint8_t slot, const std::vector<uint8_t> &bytes, int *pending, int *idle) {
  *pending = *idle = 0;
  if (!k1_look_rx_arm(slot, (uint32_t)bytes.size())) return "ARM_REFUSED";
  std::string reply;
  for (size_t i = 0; i < bytes.size(); i++) {
    const K1LookRxOutcome o = k1_look_rx_push(bytes[i]);
    const char *word = k1_look_rx_reply(o);
    if (o == K1LookRxOutcome::Pending) (*pending)++;
    if (o == K1LookRxOutcome::Idle) (*idle)++;
    if (word != nullptr) {
      if (i + 1 != bytes.size() || !reply.empty()) return "REPLY_BEFORE_LAST_BYTE";
      reply = word;
    }
  }
  return reply;
}
static bool rx_idle() { return k1_look_rx_buf == nullptr && k1_look_rx_need == 0 && k1_look_rx_got == 0; }
#define CHECK(cond, tag) do { if (!(cond)) { std::printf("FAIL %s line %d\n", tag, __LINE__); return 1; } } while (0)

int main() {
  k1_host_fs_reset();
  const auto A = matrix_file(2 * 65536);  // 1000 -> 2000
  const auto B = matrix_file(3 * 65536);  // 1000 -> 3000
  int pending = 0, idle = 0;

  // No upload armed: a byte is not taken and nothing is reported.
  CHECK(k1_look_rx_push(0x55) == K1LookRxOutcome::Idle, "idle_not_armed");
  CHECK(k1_look_rx_reply(K1LookRxOutcome::Idle) == nullptr &&
        k1_look_rx_reply(K1LookRxOutcome::Pending) == nullptr, "no_reply_while_open");

  // 1. Full success: live, saved, reply "ok".
  CHECK(upload(10, A, &pending, &idle) == "ok", "ok_reply");
  CHECK(pending == (int)A.size() - 1 && idle == 0, "ok_pending_count");
  CHECK(live_level(10, 1000) == 2000, "ok_live");
  CHECK(flash_file(10) == A, "ok_saved_bytes");
  CHECK(rx_idle() && g_live.size() == 1, "ok_rx_freed_one_bundle");

  // 2. Save failure: LittleFS full (every stub file entry in use), so the
  //    temporary file cannot be created. B goes live; the slot's saved file
  //    stays A; the reply says so.
  for (int i = 0; k1_host_fs_create(("/fill/" + std::to_string(i)).c_str()) != nullptr; i++) {
  }
  const unsigned writes_before_fail = k1_host_fs_writes;
  CHECK(upload(10, B, &pending, &idle) == "installed, not saved", "notsaved_reply");
  CHECK(live_level(10, 1000) == 3000, "notsaved_new_table_live");
  CHECK(flash_file(10) == A, "notsaved_old_file_untouched");
  CHECK(k1_host_fs_writes == writes_before_fail, "notsaved_nothing_written");
  CHECK(rx_idle(), "notsaved_rx_freed");
  CHECK(k1_look_reclaim() == 0 && g_live.size() == 1, "notsaved_old_bundle_reclaimed");

  // 3. Refused upload (CRC broken): old table (B) still live, nothing saved.
  k1_host_fs_reset();
  auto bad = A;
  bad[bad.size() - 1] ^= 0xFF;
  CHECK(upload(10, bad, &pending, &idle) == "fail", "fail_reply");
  CHECK(live_level(10, 1000) == 3000, "fail_old_table_kept");
  CHECK(flash_file(10).empty() && k1_host_fs_writes == 0, "fail_nothing_saved");
  CHECK(rx_idle() && g_live.size() == 1, "fail_rx_freed");

  // Nothing left behind once the slot is cleared.
  CHECK(k1_look_ram_clear(10) == K1_LOOK_OK && k1_look_reclaim() == 0, "clear");
  CHECK(g_live.empty() && k1_look_retired_n == 0, "no_leak_end");
  std::printf("ok\n");
  return 0;
}
"""


def _compiler() -> str | None:
    import shutil

    return shutil.which("clang++") or shutil.which("g++")


def test_look_upload_reports_live_and_saved_separately():
    cxx = _compiler()
    assert cxx, "no host C++ compiler (clang++ or g++) on PATH"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "look_upload.cpp"
        src.write_text(SOURCE, encoding="utf-8")
        exe = td / "look_upload"
        cmd = [cxx, "-std=c++17", "-O1", "-g", "-DARDUINO", "-fsanitize=address,undefined",
               "-I", str(STUBS), "-I", str(FW / "visual"), "-I", str(FW / "persistence"),
               str(src), "-o", str(exe)]
        build = subprocess.run(cmd, text=True, capture_output=True)
        assert build.returncode == 0, build.stderr[-4000:]
        run = subprocess.run([str(exe)], text=True, capture_output=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr[-4000:]
    assert run.stdout.strip() == "ok", run.stdout
