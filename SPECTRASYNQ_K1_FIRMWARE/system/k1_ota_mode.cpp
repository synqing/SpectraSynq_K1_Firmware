// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// system/k1_ota_mode.cpp — Component C: the OTA-mode COORDINATOR + shared state.
//
// Owns the single OtaUiHolder cross-core atomic instance and the publish/snapshot
// accessors (release stores on the Core-0 producer side, acquire loads on the
// Core-1 consumer side). Implements the once-per-frame render-hook that hands the
// frame to the Reactor renderer whenever OTA mode is active, and the idempotent
// NimBLE single-init seam shared with the Remoted central.
//
// The ENTIRE translation unit is behind #if SB_ENABLE_OTA. With the flag OFF
// (every shipping build) this compiles to an empty object — zero behaviour
// change, byte-identical output. This mirrors the always-listed system/k1_ota.cpp
// pattern already on the k1_hardware build_src_filter line.

#include "k1_ota_mode.h"

#if SB_ENABLE_OTA

#include "globals.h"       // leds_16[], NATIVE_RESOLUTION (via constants.h), USBSerial
#include <NimBLEDevice.h>  // NimBLEDevice::init — the shared single-init seam
#include <algorithm>       // std::clamp

namespace {

// ─────────────────────────────────────────────────────────────────────────────
// Shared cross-core state holder. This is the SINGLE storage location both cores
// touch; all access is funnelled through the accessor functions below so the
// release/acquire memory-order contract lives in exactly one place.
// ─────────────────────────────────────────────────────────────────────────────
OtaUiHolder g_ota_ui;

// Idempotent NimBLE-init latch. Written once (first caller) and only ever read
// afterwards; the BLE bring-up path is not re-entrant across cores in practice
// (start() is called from a single control path), so a plain bool guarded by the
// init call is sufficient — but we make it atomic for defence in depth.
std::atomic<bool> g_nimble_inited{false};

}  // namespace

// ─────────────────────────────────────────────────────────────────────────────
// Producer-side publishers — Core-0 ONLY. Each store uses release ordering so a
// Core-1 acquire reader that observes a newer value also observes everything the
// producer wrote before it.
// ─────────────────────────────────────────────────────────────────────────────
void k1_ota_mode_publish_state(OtaUiState s) {
  g_ota_ui.state.store(static_cast<uint8_t>(s), std::memory_order_release);
}

void k1_ota_mode_publish_progress(float fraction01) {
  // Clamp to [0,1] then quantise to milli-units (0..1000). Integer atomic avoids
  // the portability caveats of std::atomic<float> on Xtensa.
  const float f = std::clamp(fraction01, 0.0f, 1.0f);
  const uint32_t milli = static_cast<uint32_t>(f * 1000.0f + 0.5f);
  g_ota_ui.progress_milli.store(milli, std::memory_order_release);
}

void k1_ota_mode_publish_fail(OtaRejectReason reason) {
  // Order matters: publish the reason FIRST (release), THEN the FAIL state
  // (release). Any Core-1 acquire reader that sees state == FAIL is therefore
  // guaranteed to also see the matching reason (never a stale NONE). A reader
  // that races and still sees a pre-FAIL state simply tints one more frame with
  // the previous state — visually irrelevant at >= 100 FPS.
  g_ota_ui.rejectReason.store(static_cast<uint8_t>(reason), std::memory_order_release);
  g_ota_ui.state.store(static_cast<uint8_t>(OtaUiState::FAIL), std::memory_order_release);
}

// ─────────────────────────────────────────────────────────────────────────────
// Consumer-side snapshot — Core-1 renderer ONLY. Acquire loads of all three
// fields into a plain struct so the renderer works from an immutable local copy
// for the whole frame. A single torn read across fields is tolerated (see the
// publish_fail ordering note); no seqlock for v1.
// ─────────────────────────────────────────────────────────────────────────────
OtaUiSnapshot k1_ota_mode_snapshot() {
  OtaUiSnapshot snap;
  snap.state        = static_cast<OtaUiState>(
      g_ota_ui.state.load(std::memory_order_acquire));
  const uint32_t milli = g_ota_ui.progress_milli.load(std::memory_order_acquire);
  snap.progress     = static_cast<float>(milli) / 1000.0f;
  snap.rejectReason = static_cast<OtaRejectReason>(
      g_ota_ui.rejectReason.load(std::memory_order_acquire));
  return snap;
}

// Cheap render-hook predicate: a single acquire load of the state field.
bool k1_ota_mode_active() {
  return g_ota_ui.state.load(std::memory_order_acquire) !=
         static_cast<uint8_t>(OtaUiState::IDLE);
}

// ─────────────────────────────────────────────────────────────────────────────
// Coordinator render-hook — called once per frame at the TOP of led_thread()'s
// work block, before any music/effect dispatch. When OTA mode is active it takes
// over the frame: snapshot once, fill leds_16[] via the Reactor renderer, and
// return true so the caller shows the frame and skips the visualiser. When IDLE
// it returns false after a single acquire load and the normal render path runs
// unchanged.
//
// The renderer performs ZERO heap allocation and must complete in < 2.0 ms; the
// hook itself adds only one snapshot + one function call, so the OTA-active frame
// budget is dominated by the renderer. show_leds() and the LED_FPS/last_frame_us
// bookkeeping remain the caller's responsibility.
// ─────────────────────────────────────────────────────────────────────────────
bool k1_ota_mode_render_hook(float dtSeconds) {
  if (!k1_ota_mode_active()) {
    return false;  // fast path: OTA idle, normal render proceeds
  }
  const OtaUiSnapshot snap = k1_ota_mode_snapshot();
  k1_ota_reactor_render(snap, dtSeconds);
  return true;  // OTA owns this frame
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared NimBLE single-init seam — Core-0. Both the OTA peripheral and the
// Remoted central call THIS instead of NimBLEDevice::init() directly, so the
// stack is initialised exactly once when SB_ENABLE_OTA and SB_K1_BLE_REMOTED are
// both defined (double init hard-faults the controller). First caller runs the
// init; every subsequent caller is a no-op that returns true.
// ─────────────────────────────────────────────────────────────────────────────
bool k1_ota_nimble_ensure_inited() {
  bool expected = false;
  if (g_nimble_inited.compare_exchange_strong(expected, true,
                                              std::memory_order_acq_rel)) {
    // We won the race to be the first initialiser.
    NimBLEDevice::init("K1");
  }
  // Whether we initialised or someone beat us to it, NimBLE is up now.
  return true;
}

#endif  // SB_ENABLE_OTA
