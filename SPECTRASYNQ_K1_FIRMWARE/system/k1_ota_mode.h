// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// system/k1_ota_mode.h — LOCKED shared interface for the BLE OTA mode subsystem.
//
// Three builders implement against THIS FILE verbatim:
//   (A) visual/k1_ota_reactor.cpp        — the Reactor renderer (Core-1 consumer)
//   (B) network/k1_ota_ble_service.cpp   — the NimBLE GATT peripheral (Core-0 producer)
//   (C) system/k1_ota_mode.cpp           — the coordinator + shared state holder
//
// EVERYTHING here is #if SB_ENABLE_OTA. When the flag is 0 this header is a no-op
// (it declares nothing) and the three .cpp files above compile to empty TUs, so
// flag-OFF builds are byte-identical.
//
// HARD CONSTRAINTS honoured by this contract:
//   - Renderer writes leds_16[] centre-origin from LED 79/80 outward; bounded
//     red->amber->green status arc (NOT a rainbow).
//   - The renderer and everything it calls perform ZERO heap allocation.
//   - Renderer frame budget <= 2.0 ms @ 120 FPS.
//   - British English throughout.
//
// CROSS-CORE MODEL (per the BLE surface map):
//   Producer = Core-0 NimBLE service callbacks (write BEGIN/SIG/END/ABORT +
//              per-chunk progress) AND the Core-0 coordinator on END verify.
//   Consumer = Core-1 led_thread() renderer, reads once per frame.
//   The two cores never share a lock. State transfer is lock-free via a small
//   holder of C11 atomics (std::atomic). Each field is independently atomic; the
//   renderer tolerates a torn read across fields for a single frame (visually
//   irrelevant at >=100 FPS). No struct-wide seqlock is required for v1.

#pragma once

#include "constants.h"  // SB_ENABLE_OTA
#include <stdint.h>

#if SB_ENABLE_OTA

#include <atomic>
#include "FixedPoints.h"  // CRGB16 (Q8.8) — the leds_16[] element type

// ─────────────────────────────────────────────────────────────────────────────
// 1. UI STATE MACHINE
// ─────────────────────────────────────────────────────────────────────────────
// Ordered to mirror the GATT contract flow. The wire status codes in
// k1-ble-ota-contract.yaml (0x10..0x14) map onto these; the enum itself is the
// firmware-internal render state and is NOT sent on the wire.
enum class OtaUiState : uint8_t {
  IDLE        = 0,  // OTA mode not active; render-hook returns false, music runs.
  ADVERTISING = 1,  // service up, no session (contract: waiting).            wire: (none)
  DOWNLOADING = 2,  // BEGIN received, image bytes streaming.                 wire: 0x10 PROGRESS
  VERIFYING   = 3,  // END received, RSA-3072 verify in flight.               wire: 0x11 VERIFYING
  INSTALLING  = 4,  // signature good, boot partition flipped, pre-reboot.    wire: 0x12 INSTALLING
  SUCCESS     = 5,  // ACCEPT latched; device about to reboot.                wire: 0x13 ACCEPT
  FAIL        = 6   // REJECT latched; running image untouched.               wire: 0x14 REJECT
};

// REJECT reason codes — byte-identical to k1-ble-ota-contract.yaml REJECT args.
// Carried in the holder so the renderer can tint FAIL and the service can notify
// the same value. 0 = none (not a rejection).
enum class OtaRejectReason : uint8_t {
  NONE          = 0,
  NO_SIGNATURE  = 1,  // contract reason 1
  BAD_SIGNATURE = 2,  // contract reason 2
  INTEGRITY_FAIL= 3,  // contract reason 3
  NO_SLOT       = 4,  // contract reason 4
  SIZE_MISMATCH = 5   // contract reason 5
};

// ─────────────────────────────────────────────────────────────────────────────
// 2. CROSS-CORE STATE HOLDER  (owned by the coordinator; defined in k1_ota_mode.cpp)
// ─────────────────────────────────────────────────────────────────────────────
// Producers (Core-0) write ONLY through k1_ota_mode_publish_*(). Consumer
// (Core-1) reads ONLY through k1_ota_mode_snapshot(). Do NOT touch the atomics
// directly from either side — go through the accessors so the memory-order
// contract (release on write, acquire on read) is centralised.
struct OtaUiSnapshot {
  OtaUiState      state;        // current UI state
  float           progress;     // 0.0f .. 1.0f (DOWNLOADING fill fraction)
  OtaRejectReason rejectReason; // valid only when state == FAIL, else NONE
};

// The live holder. Definition lives in k1_ota_mode.cpp. Producers/consumers use
// the accessor functions below — the struct is exposed only so both cores share
// one storage location. All three fields are lock-free atomics.
struct OtaUiHolder {
  std::atomic<uint8_t> state{static_cast<uint8_t>(OtaUiState::IDLE)};
  std::atomic<uint32_t> progress_milli{0};   // progress * 1000, 0..1000 (integer, avoids atomic<float> portability issues)
  std::atomic<uint8_t> rejectReason{static_cast<uint8_t>(OtaRejectReason::NONE)};
};

// Producer-side publishers (call from Core-0 only). Each is a release store.
// Publishing DOWNLOADING/progress is the per-chunk hot path — keep it O(1).
void k1_ota_mode_publish_state(OtaUiState s);
void k1_ota_mode_publish_progress(float fraction01);          // clamps to [0,1]
void k1_ota_mode_publish_fail(OtaRejectReason reason);        // sets state=FAIL + reason atomically-enough for the renderer

// Consumer-side snapshot (call from Core-1 renderer only). Acquire loads of all
// three fields into a plain struct. One call per frame.
OtaUiSnapshot k1_ota_mode_snapshot();

// True iff the current published state is anything other than IDLE. Cheap acquire
// load of the state field only — this is the render-hook fast path predicate.
bool k1_ota_mode_active();

// ─────────────────────────────────────────────────────────────────────────────
// 3. REACTOR RENDERER  (implemented in visual/k1_ota_reactor.cpp — Core-1)
// ─────────────────────────────────────────────────────────────────────────────
// Renders one Reactor frame into the global leds_16[NATIVE_RESOLUTION] buffer,
// centre-origin from indices 79/80 outward. MUST NOT allocate. MUST complete in
// < 2.0 ms. Receives the already-taken snapshot (renderer does not re-snapshot)
// and the real per-frame delta in seconds (from the led_thread frame timer).
// The function ONLY fills leds_16[]; the caller invokes show_leds() afterwards.
// Colour is a bounded red->amber->green arc plus a white-hot centre core; the arc
// radius/fill tracks snapshot.progress and snapshot.state. No secondary strip.
void k1_ota_reactor_render(const OtaUiSnapshot& snap, float dtSeconds);

// ─────────────────────────────────────────────────────────────────────────────
// 4. BLE GATT SERVICE  (implemented in network/k1_ota_ble_service.cpp — Core-0)
// ─────────────────────────────────────────────────────────────────────────────
// Lifecycle for the NimBLE peripheral advertising the K1-OTA service
// (b4d8bc3c-...). start() is idempotent: it performs the single shared
// NimBLEDevice::init() via the coordinator seam (co-exists with the Remoted
// central when SB_K1_BLE_REMOTED is also defined), creates the GATT server +
// control/data characteristics, and begins advertising "Lightwave-Update".
// On BEGIN it publishes DOWNLOADING; per chunk it publishes progress; on END it
// publishes VERIFYING then (via coordinator) INSTALLING/SUCCESS or FAIL, notifies
// the client per the contract, and on ACCEPT calls ESP.restart() AFTER the
// notify is flushed. Returns true if the service is up (or already up).
bool k1_ota_ble_service_start();

// Stop advertising, tear down the OTA GATT server, publish IDLE. Does NOT
// de-init NimBLEDevice (the Remoted central may still own it). Safe if not
// started. Called on ABORT-after-idle or explicit teardown; NOT called on the
// ACCEPT/reboot path (the reboot supersedes teardown).
void k1_ota_ble_service_stop();

// True while the OTA GATT server exists and is advertising/connected.
bool k1_ota_ble_service_running();

// ─────────────────────────────────────────────────────────────────────────────
// 5. COORDINATOR RENDER-HOOK  (implemented in system/k1_ota_mode.cpp — Core-1 call)
// ─────────────────────────────────────────────────────────────────────────────
// Called once per frame at the TOP of led_thread()'s work block, before any
// music/effect dispatch. If OTA mode is active it takes over the frame:
// snapshots state, calls k1_ota_reactor_render() into leds_16[], and returns
// true — signalling the caller to show_leds() and skip the entire music
// visualiser for this frame. If OTA mode is IDLE it returns false immediately
// (single acquire load) and the normal render path runs unchanged.
//
//   dtSeconds — real per-frame delta from the led_thread frame timer
//               (esp_timer_get_time() delta / 1e6), for animation pacing.
//
// The caller (led_thread) owns show_leds() and the LED_FPS/last_frame_us update.
bool k1_ota_mode_render_hook(float dtSeconds);

// ─────────────────────────────────────────────────────────────────────────────
// 6. SHARED NimBLE INIT SEAM  (implemented in system/k1_ota_mode.cpp — Core-0)
// ─────────────────────────────────────────────────────────────────────────────
// Idempotent single-init guard shared between the OTA peripheral and the Remoted
// central. Both subsystems MUST call this instead of NimBLEDevice::init()
// directly. First caller runs NimBLEDevice::init("K1"); subsequent callers are
// no-ops. Prevents the double-init crash when SB_ENABLE_OTA and SB_K1_BLE_REMOTED
// are both defined. Returns true once NimBLE is initialised.
bool k1_ota_nimble_ensure_inited();

#endif  // SB_ENABLE_OTA
