"""Stage D (Modernes C++ next phase, 10 Nov 2026): mode and preset requests are
transferred complete, consumed and cleared coherently, and never lost.

Drives the REAL production code on the host, built with ThreadSanitizer where
available:

* mode requests: system/globals.h k1_mode_request_post() (what serial set_mode,
  the mode button and the control facade call) against k1_mode_request_land()
  (what run_transition_fade() calls at black on the render task);
* preset requests: control/k1_effect_queue.cpp — k1_queue_arm_begin() /
  k1_queue_request_commit() from two producer threads acting as the two cores
  (serial loop + beat-aware director) against k1_effect_queue_frame_tick() on
  a render thread, with real DIP transitions landing fields in CONFIG.

Every published preset carries one token in all of its float fields, so a
mixed (torn) preset is detectable in the live state and in seeds.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))

import oracle_serial_replay as osr  # noqa: E402

FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

DRIVER = r"""
#include <atomic>
#include <thread>
#include <LittleFS.h>
#include "globals.h"
#include "serial_replay_host_stubs.h"
#include "bridge_fs.h"
#include "k1_effect_queue.h"
#include "k1_tempo.h"
#include <stdio.h>

K1TempoEvent k1_tempo_read() { K1TempoEvent e = {}; return e; }
bool k1_persist_request_push(const K1PersistRequest&) { return true; }
void reboot() {}

#define CHECK(c, tag) do { if (!(c)) { printf("FAIL %s line %d\n", tag, __LINE__); return 1; } } while (0)

static void fill(K1ChannelPreset* p, float token) {
  p->photons = token; p->chroma = token; p->mood = token; p->saturation = token;
  p->prism_count = token; p->incandescent_filter = token; p->base_coat_intensity = token;
}
static bool coherent(const K1ChannelPreset& p) {
  return p.chroma == p.photons && p.mood == p.photons && p.saturation == p.photons &&
         p.prism_count == p.photons && p.incandescent_filter == p.photons &&
         p.base_coat_intensity == p.photons;
}

static int mode_requests() {
  // Deterministic: latest wins, button = next, cancel, flag/request agree.
  CONFIG.LIGHTSHOW_MODE = 0;
  k1_mode_request_post(5);
  CHECK(mode_transition_queued && k1_mode_request_peek() == 5, "posted");
  CHECK(k1_mode_request_land() == 5 && CONFIG.LIGHTSHOW_MODE == 5, "land5");
  CHECK(!mode_transition_queued && k1_mode_request_peek() == K1_MODE_REQUEST_NONE, "cleared");
  k1_mode_request_post(7); k1_mode_request_post(9);
  CHECK(k1_mode_request_land() == 9 && CONFIG.LIGHTSHOW_MODE == 9, "latest_wins");
  k1_mode_request_post(-1);
  CHECK(k1_mode_request_land() == -1 && CONFIG.LIGHTSHOW_MODE == 10, "button_next");
  k1_mode_request_post(3); k1_mode_request_cancel();
  CHECK(k1_mode_request_land() == K1_MODE_REQUEST_NONE && CONFIG.LIGHTSHOW_MODE == 10, "cancel");
  // A spurious flag with no request never acts like a button press.
  mode_transition_queued = true;
  CHECK(k1_mode_request_land() == K1_MODE_REQUEST_NONE && CONFIG.LIGHTSHOW_MODE == 10, "no_phantom");

  // Concurrent: producer posts ascending destinations while the render
  // thread lands whenever the flag is up. Nothing lost at the end, never a
  // step backwards, never a value that was not posted.
  const int M = NUM_MODES;
  long bad = 0;
  for (int trial = 0; trial < 300; trial++) {
    CONFIG.LIGHTSHOW_MODE = 0;
    k1_mode_request_cancel();
    std::atomic<bool> done{false};
    std::thread render([&] {
      int last = 0;
      while (!done.load() || mode_transition_queued) {
        if (mode_transition_queued) {
          const int32_t r = k1_mode_request_land();
          if (r != K1_MODE_REQUEST_NONE) {
            if (r < 0 || r >= M || r < last) bad++;
            last = r;
          }
        }
      }
    });
    for (int d = 1; d < M; d++) k1_mode_request_post((int16_t)d);
    done = true;
    render.join();
    if (CONFIG.LIGHTSHOW_MODE != M - 1) bad++;
  }
  CHECK(bad == 0, "mode_concurrent");
  printf("mode ok\n");
  return 0;
}

static uint32_t g_now = 1000;
static void ticks(int n) { for (int i = 0; i < n; i++) { g_now += 10; k1_effect_queue_frame_tick(g_now); } }

static int preset_requests() {
  k1_queue_set_dip_ms(K1_QUEUE_DIP_MS_MIN);
  // Deterministic: arm+commit lands one complete preset on the right channel.
  k1_queue_host_set_producer(0);
  K1ChannelPreset* p = k1_queue_arm_begin(false);
  fill(p, 0.25f);
  p->lightshow_mode = CONFIG.LIGHTSHOW_MODE;
  k1_queue_request_commit(false, g_now);
  CHECK(k1_queue_commit_pending() && k1_queue_channel_armed(false), "pending");
  // An edit by the producer after publishing cannot reach the consumer.
  fill(p, 9.0f);
  ticks(60);
  K1ChannelPreset live = k1_queue_capture_live(false);
  CHECK(live.photons == 0.25f && coherent(live), "landed_complete");
  CHECK(!k1_queue_commit_pending(), "consumed");
  // Seeding during an in-flight transition uses the target, not live.
  p = k1_queue_arm_begin(true);
  fill(p, 0.5f);
  k1_queue_request_commit(false, g_now);
  ticks(1);  // taken, DIP in flight on the secondary
  K1ChannelPreset* seed = k1_queue_arm_begin(true);
  CHECK(seed->photons == 0.5f && coherent(*seed), "seed_from_target");
  fill(seed, 0.75f);
  k1_queue_request_commit(false, g_now);
  ticks(60);
  live = k1_queue_capture_live(true);
  CHECK(live.photons == 0.75f && coherent(live), "secondary_latest");
  // Both channels armed by one commit land together; a later single-channel
  // commit before consumption does not drop the other channel.
  p = k1_queue_arm_begin(false); fill(p, 0.1f); k1_queue_request_commit(false, g_now);
  p = k1_queue_arm_begin(true);  fill(p, 0.2f); k1_queue_request_commit(false, g_now);
  ticks(60);
  CHECK(k1_queue_capture_live(false).photons == 0.1f, "prim_kept");
  CHECK(k1_queue_capture_live(true).photons == 0.2f, "sec_kept");
  // Disarm discards an untaken commit (existing queue-mode-off semantics).
  p = k1_queue_arm_begin(false); fill(p, 0.3f); k1_queue_request_commit(false, g_now);
  k1_queue_disarm_all();
  ticks(60);
  CHECK(k1_queue_capture_live(false).photons == 0.1f && !k1_queue_any_armed(), "disarm");

  // Concurrent: core-0 producer (tokens 1000+i) and core-1 producer (tokens
  // 5000+i) arm/step/commit while the render thread ticks. Every seed and
  // every landed state is one complete submitted preset; the core-0
  // producer's final request is not lost.
  std::atomic<bool> stop{false};
  std::atomic<long> torn{0}, frames{0};
  std::thread render([&] {
    uint32_t now = 100000;
    while (!stop.load()) {
      now += 10;
      k1_effect_queue_frame_tick(now);
      const K1ChannelPreset a = k1_queue_capture_live(false);
      const K1ChannelPreset b = k1_queue_capture_live(true);
      if (!coherent(a) || !coherent(b)) torn++;
      frames++;
    }
    for (int i = 0; i < 200; i++) { now += 10; k1_effect_queue_frame_tick(now); }
  });
  std::thread director([&] {
    k1_queue_host_set_producer(1);
    for (int i = 0; i < 3000; i++) {
      K1ChannelPreset* d = k1_queue_arm_begin(false);
      if (!coherent(*d)) torn++;
      fill(d, 5000.0f + i);
      k1_queue_request_commit(true, 0);
    }
  });
  k1_queue_host_set_producer(0);
  const int N = 3000;
  for (int i = 1; i <= N; i++) {
    K1ChannelPreset* s = k1_queue_arm_begin(i & 1);
    if (!coherent(*s)) torn++;
    fill(s, 1000.0f + i);
    k1_queue_request_commit(false, 0);
  }
  director.join();
  // Final known request from core 0 on both channels after the director stopped.
  K1ChannelPreset* f = k1_queue_arm_begin(false); fill(f, 77.0f);
  f = k1_queue_arm_begin(true); fill(f, 88.0f);
  k1_queue_request_commit(false, 0);
  while (k1_queue_commit_pending()) { std::this_thread::yield(); }
  stop = true;
  render.join();
  CHECK(torn.load() == 0, "torn_preset");
  CHECK(frames.load() > 0, "render_ran");
  CHECK(k1_queue_capture_live(false).photons == 77.0f, "final_primary_not_lost");
  CHECK(k1_queue_capture_live(true).photons == 88.0f, "final_secondary_not_lost");
  printf("preset ok frames=%ld\n", frames.load());
  return 0;
}

int main() {
  update_config_filename(FIRMWARE_VERSION);
  memcpy(&CONFIG, &CONFIG_DEFAULTS, sizeof(CONFIG));
  if (mode_requests() != 0) return 1;
  if (preset_requests() != 0) return 1;
  return 0;
}
"""


def _tsan_ok(cc: str, tmp: Path) -> bool:
    r = subprocess.run([cc, "-fsanitize=thread", "-x", "c++", "-", "-o", str(tmp / "p")],
                       input="int main(){}", text=True, capture_output=True)
    return r.returncode == 0


def test_mode_and_preset_requests_transfer_complete_and_are_never_lost(tmp_path):
    cc = osr._detect_compiler()
    tsan = _tsan_ok(cc, tmp_path)
    drv = tmp_path / "handoff_drv.cpp"
    drv.write_text(DRIVER, encoding="utf-8")
    exe = tmp_path / "handoff_drv"
    srcs = [FW / s for s in osr.COMMON_SOURCES] + [osr.HOST_GLOBALS] + [
        FW / "control" / "k1_show_state.cpp",
        FW / "control" / "k1_effect_queue.cpp",
        FW / "director" / "k1_edgemixer.cpp",
    ]
    cmd = [cc, "-std=c++17", "-O1", "-g", "-fno-fast-math", "-w", "-pthread",
           *(["-fsanitize=thread"] if tsan else []),
           *[f"-D{d}" for d in osr.DEFINES if d != "K1_SERIAL_REPLAY_HOST"],
           "-I", str(osr.STUBS), "-I", str(ROOT / "scripts" / "regression-harness" / "golden"),
           "-I", str(osr.FIXEDPOINTS), "-I", str(FW),
           *[a for d in osr.FW_SUBDIRS for a in ("-I", str(FW / d))],
           str(drv), *map(str, srcs), "-o", str(exe)]
    r = subprocess.run(cmd, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr[-6000:]
    run = subprocess.run([str(exe)], text=True, capture_output=True, timeout=600)
    assert run.returncode == 0, run.stdout[-3000:] + run.stderr[-6000:]
    assert "mode ok" in run.stdout and "preset ok" in run.stdout, run.stdout
    assert "WARNING: ThreadSanitizer" not in run.stderr, run.stderr[-6000:]
