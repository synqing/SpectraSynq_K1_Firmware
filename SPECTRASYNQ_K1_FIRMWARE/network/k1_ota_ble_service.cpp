// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// network/k1_ota_ble_service.cpp — Component B: the NimBLE PERIPHERAL that
// exposes the K1-OTA GATT service. Core-0 producer.
//
// The ENTIRE translation unit is behind #if SB_ENABLE_OTA. With the flag OFF
// (every shipping build) this compiles to an empty object: byte-identical to a
// build that never listed the file. It is added unconditionally to
// build_src_filter, exactly like system/k1_ota.cpp.
//
// ROLE (per the locked system/k1_ota_mode.h contract):
//   - Advertise "Lightwave-Update" for service b4d8bc3c-… with a control
//     characteristic (write+notify) and a data characteristic (write-no-resp).
//   - Map wire opcodes BEGIN/SIG/END/ABORT onto the on-silicon-proven OTA engine
//     (k1_ota_begin / k1_ota_append_signature / k1_ota_end / k1_ota_abort) and
//     the raw image stream onto k1_ota_write().
//   - Emit PROGRESS/VERIFYING/INSTALLING/ACCEPT/REJECT notifies byte-for-byte per
//     docs/protocol/k1-ble-ota-contract.yaml.
//   - Publish the UI state to the Core-1 Reactor renderer via the coordinator
//     publishers (k1_ota_mode_publish_*) — never touching the atomics directly.
//   - Use the shared idempotent NimBLE-init seam (k1_ota_nimble_ensure_inited)
//     so the OTA peripheral co-exists with the Remoted BLE-MIDI central without a
//     double NimBLEDevice::init() crash.
//   - On ACCEPT: publish INSTALLING → send the ACCEPT notify → let it flush →
//     ESP.restart(). REJECT paths never reboot (the running image is untouched).
//
// CROSS-CORE MODEL: all NimBLE server callbacks here run on the Core-0 NimBLE
// host task. State transfer to the Core-1 renderer is lock-free via the
// coordinator's atomic holder (release stores here, acquire loads in the
// renderer). We hold NO renderer lock.

#include "constants.h"  // SB_ENABLE_OTA

#if SB_ENABLE_OTA

#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_heap_caps.h>  // internal-RAM budget guard at service creation
#include <esp_system.h>     // esp_restart() — deferred reboot from the timer callback
#include <freertos/FreeRTOS.h>
#include <freertos/timers.h> // xTimerCreate — deferred ACCEPT-flush reboot (FIX C)
#include <string.h>
#include <stdint.h>

#include "globals.h"        // USBSerial
#include "k1_ota.h"         // k1_ota_begin/write/append_signature/end/abort/active
#include "k1_ota_mode.h"    // locked contract: publishers + NimBLE init seam + service API

#ifdef SB_K1_BLE_REMOTED
#include "ble_remoted_central.h"  // sb_k1_ble_remoted_is_linked() — RF-contention hint
#endif

namespace {

// ─────────────────────────────────────────────────────────────────────────────
// Wire constants — VERBATIM from docs/protocol/k1-ble-ota-contract.yaml.
// ─────────────────────────────────────────────────────────────────────────────
constexpr char K1_OTA_SERVICE_UUID[]  = "b4d8bc3c-f0cf-4f2b-b4e1-b4c3c570e606";
constexpr char K1_OTA_CONTROL_UUID[]  = "3a058b4a-3adc-46e4-85f2-2c57f3d157bd";
constexpr char K1_OTA_DATA_UUID[]     = "6cc82419-4149-4601-a6c1-a255b05b921d";
constexpr char K1_OTA_ADV_NAME[]      = "Lightwave-Update";

// control write opcodes (byte 0 of a control write)
constexpr uint8_t OP_BEGIN = 0x01;  // + u32 image_size (LE)
constexpr uint8_t OP_SIG   = 0x02;  // + u16 offset (LE) + signature fragment bytes
constexpr uint8_t OP_END   = 0x03;  // no args
constexpr uint8_t OP_ABORT = 0x04;  // no args

// control notify status codes (byte 0 of a control notify)
constexpr uint8_t ST_PROGRESS   = 0x10;  // + u8 percent
constexpr uint8_t ST_VERIFYING  = 0x11;
constexpr uint8_t ST_INSTALLING = 0x12;
constexpr uint8_t ST_ACCEPT     = 0x13;
constexpr uint8_t ST_REJECT     = 0x14;  // + u8 reason

// REJECT reason codes — byte-identical to the contract AND to OtaRejectReason.
constexpr uint8_t RJ_NO_SIGNATURE  = 1;
constexpr uint8_t RJ_BAD_SIGNATURE = 2;
constexpr uint8_t RJ_INTEGRITY     = 3;  // reserved; k1_ota_end() collapses to bad-sig/size
constexpr uint8_t RJ_NO_SLOT       = 4;
constexpr uint8_t RJ_SIZE_MISMATCH = 5;

// Minimum internal-SRAM headroom (bytes) required to stand the GATT server up.
// Below this we refuse cleanly rather than fragment the heap into an abort. This
// is the risk-register HEAP mitigation threshold.
constexpr size_t K1_OTA_MIN_INTERNAL_FREE = 16 * 1024;

// Preferred BLE data-length (octets) for Data Length Extension. MTU target = 517.
constexpr uint16_t K1_OTA_DLE_TX_OCTETS = 251;  // BLE 4.2 DLE max PDU payload

// ─────────────────────────────────────────────────────────────────────────────
// File-scope service state (Core-0 only; never read from Core-1).
// ─────────────────────────────────────────────────────────────────────────────
NimBLEServer*         s_server   = nullptr;
NimBLEService*        s_service  = nullptr;
NimBLECharacteristic* s_control  = nullptr;  // write + notify
NimBLECharacteristic* s_data     = nullptr;  // write-without-response
bool                  s_running  = false;    // server exists + advertising/connected
uint16_t              s_conn     = BLE_HS_CONN_HANDLE_NONE;

// Reported image size from BEGIN and running byte count, for the END size check.
uint32_t s_expected_size = 0;
uint32_t s_written       = 0;

// Last percent notified, so PROGRESS is emitted only on a change (throughput).
int16_t  s_last_percent  = -1;

// ─────────────────────────────────────────────────────────────────────────────
// Notify helpers — every wire frame is built on a tiny stack buffer (no heap).
// ─────────────────────────────────────────────────────────────────────────────
void notify_control(const uint8_t* frame, size_t len) {
  if (s_control == nullptr) {
    return;
  }
  // Explicit connHandle keeps the notify targeted at the active OTA client.
  if (s_conn != BLE_HS_CONN_HANDLE_NONE) {
    s_control->notify(frame, len, s_conn);
  } else {
    s_control->notify(frame, len);
  }
}

void notify_progress(uint8_t percent) {
  const uint8_t frame[2] = {ST_PROGRESS, percent};
  notify_control(frame, sizeof(frame));
}

void notify_status(uint8_t status_code) {
  const uint8_t frame[1] = {status_code};
  notify_control(frame, sizeof(frame));
}

void notify_reject(uint8_t reason) {
  const uint8_t frame[2] = {ST_REJECT, reason};
  notify_control(frame, sizeof(frame));
}

// Map a wire reject reason onto the coordinator's OtaRejectReason and publish
// FAIL to the renderer, then notify the client. Never reboots.
void publish_and_notify_reject(uint8_t reason) {
  OtaRejectReason r = OtaRejectReason::NONE;
  switch (reason) {
    case RJ_NO_SIGNATURE:  r = OtaRejectReason::NO_SIGNATURE;  break;
    case RJ_BAD_SIGNATURE: r = OtaRejectReason::BAD_SIGNATURE; break;
    case RJ_INTEGRITY:     r = OtaRejectReason::INTEGRITY_FAIL;break;
    case RJ_NO_SLOT:       r = OtaRejectReason::NO_SLOT;       break;
    case RJ_SIZE_MISMATCH: r = OtaRejectReason::SIZE_MISMATCH; break;
    default:               r = OtaRejectReason::BAD_SIGNATURE; break;
  }
  // publish_fail() sets rejectReason BEFORE state=FAIL, so a renderer that sees
  // FAIL always sees the reason (risk-register CROSS-CORE mitigation).
  k1_ota_mode_publish_fail(r);
  notify_reject(reason);
  USBSerial.printf("[ota_ble] REJECT reason=%u\n", (unsigned)reason);
}

void reset_session_counters() {
  s_expected_size = 0;
  s_written       = 0;
  s_last_percent  = -1;
}

// ─────────────────────────────────────────────────────────────────────────────
// Deferred reboot (FIX C — adversarial review).
// ─────────────────────────────────────────────────────────────────────────────
// On ACCEPT we must NOT busy-delay-then-restart on the NimBLE host task: that
// same task has to transmit the ACCEPT notification PDU, and a busy delay can
// starve it so the client never receives ACCEPT. Instead we arm a one-shot
// FreeRTOS software timer and return immediately, letting the host task flush the
// notify; the timer callback (which runs on the FreeRTOS timer-service task, not
// the host task) then performs esp_restart(). ~700 ms gives ample flush margin.
constexpr uint32_t K1_OTA_REBOOT_DELAY_MS = 700;
TimerHandle_t s_reboot_timer = nullptr;

void reboot_timer_cb(TimerHandle_t /*t*/) {
  // Runs on the timer-service task after the ACCEPT notify has flushed.
  esp_restart();
}

void schedule_deferred_reboot() {
  if (s_reboot_timer == nullptr) {
    s_reboot_timer = xTimerCreate(
        "k1_ota_reboot",
        pdMS_TO_TICKS(K1_OTA_REBOOT_DELAY_MS),
        pdFALSE,      // one-shot (no auto-reload)
        nullptr,
        reboot_timer_cb);
  }
  if (s_reboot_timer != nullptr) {
    // Restart from zero so the full delay applies from this call.
    xTimerStart(s_reboot_timer, 0);
  } else {
    // Timer allocation failed — fall back to an immediate restart rather than
    // hang mid-install. The client may miss the ACCEPT, but the image is flipped.
    esp_restart();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Opcode handlers (called from the control onWrite callback, Core-0).
// ─────────────────────────────────────────────────────────────────────────────
void handle_begin(const uint8_t* args, size_t arglen) {
  // BEGIN carries u32 image_size (LE). Tolerate a short/absent size (0 = unknown).
  uint32_t size = 0;
  if (arglen >= 4) {
    size = (uint32_t)args[0] | ((uint32_t)args[1] << 8) |
           ((uint32_t)args[2] << 16) | ((uint32_t)args[3] << 24);
  }

  if (k1_ota_active()) {
    k1_ota_abort();  // supersede any stale session before starting fresh
  }
  reset_session_counters();

  if (!k1_ota_begin((size_t)size)) {
    // Most common cause at bench: no ota_0/ota_1 slot in the partition table.
    publish_and_notify_reject(RJ_NO_SLOT);
    return;
  }
  s_expected_size = size;
  k1_ota_mode_publish_state(OtaUiState::DOWNLOADING);
  k1_ota_mode_publish_progress(0.0f);
  notify_progress(0);
  s_last_percent = 0;
  USBSerial.printf("[ota_ble] BEGIN size=%u\n", (unsigned)size);
}

void handle_sig(const uint8_t* args, size_t arglen) {
  // SIG carries u16 offset (LE) + signature fragment. The engine concatenates
  // fragments in order via k1_ota_append_signature(); the explicit wire offset is
  // an ordering/debug aid — we forward the fragment bytes as-is (in-order writes
  // are BLE-guaranteed on the control characteristic).
  if (arglen < 2) {
    return;  // malformed — no fragment
  }
  const uint8_t* frag = args + 2;
  const size_t   flen = arglen - 2;
  if (flen == 0) {
    return;
  }
  if (!k1_ota_append_signature(frag, flen)) {
    // Buffer overflow or no open session — treat as a bad signature outright.
    publish_and_notify_reject(RJ_BAD_SIGNATURE);
  }
}

void handle_end() {
  // END: verify-or-reject. Producer publishes VERIFYING, runs the on-silicon
  // RSA-3072 verify, then maps the result to INSTALLING+ACCEPT (reboot) or FAIL.
  if (!k1_ota_active()) {
    publish_and_notify_reject(RJ_NO_SIGNATURE);  // nothing was ever begun/streamed
    return;
  }

  // Size reconciliation (contract: a short/over count -> REJECT size_mismatch).
  // Only enforced when the client declared a non-zero size at BEGIN.
  if (s_expected_size != 0 && s_written != s_expected_size) {
    k1_ota_abort();
    publish_and_notify_reject(RJ_SIZE_MISMATCH);
    reset_session_counters();
    return;
  }

  k1_ota_mode_publish_state(OtaUiState::VERIFYING);
  notify_status(ST_VERIFYING);

  // k1_ota_end() runs the IDF integrity check + the application RSA-3072 verify.
  // true  => signature verified + boot partition flipped (takes effect on reboot).
  // false => unsigned / mis-signed / tampered / integrity fail — running image safe.
  const bool accepted = k1_ota_end();
  reset_session_counters();

  if (!accepted) {
    // The engine collapses no-signature / bad-signature / integrity into one
    // false. Report BAD_SIGNATURE — the most actionable reason for the operator.
    publish_and_notify_reject(RJ_BAD_SIGNATURE);
    return;
  }

  // ACCEPT path: boot partition already flipped. Announce INSTALLING, then ACCEPT,
  // let the notify flush, then reboot. (risk-register REBOOT SAFETY mitigation.)
  k1_ota_mode_publish_state(OtaUiState::INSTALLING);
  notify_status(ST_INSTALLING);

  k1_ota_mode_publish_state(OtaUiState::SUCCESS);
  notify_status(ST_ACCEPT);
  USBSerial.println("[ota_ble] ACCEPT — image verified, rebooting into new slot");

  // Defer the reboot off the NimBLE host task so it can flush the ACCEPT notify
  // PDU first (FIX C). A busy delay here would starve the very task that must
  // transmit the notification, leaving the client hung on VERIFYING. Arm a
  // one-shot software timer and return; the timer-service task reboots after the
  // flush. The device reboots into the new slot (rollback armed, self-validates).
  schedule_deferred_reboot();
  return;
}

void handle_abort() {
  if (k1_ota_active()) {
    k1_ota_abort();
  }
  reset_session_counters();
  // Return to the waiting screen; the service stays up and keeps advertising.
  // No status frame is emitted: the contract's 0x14 REJECT carries a reason byte
  // and ABORT has no defined ACK, so teardown + return to ADVERTISING is the whole
  // response (adversarial-review FIX B).
  k1_ota_mode_publish_state(OtaUiState::ADVERTISING);
  USBSerial.println("[ota_ble] ABORT — session torn down, image untouched");
}

// ─────────────────────────────────────────────────────────────────────────────
// GATT callbacks.
// ─────────────────────────────────────────────────────────────────────────────
class ControlCB : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* chr, NimBLEConnInfo& info) override {
    const NimBLEAttValue& v = chr->getValue();
    const uint8_t* p   = v.data();
    const size_t   len = v.size();
    if (p == nullptr || len == 0) {
      return;  // empty write — ignore
    }
    s_conn = info.getConnHandle();
    const uint8_t opcode = p[0];
    const uint8_t* args  = p + 1;
    const size_t   arglen = len - 1;
    switch (opcode) {
      case OP_BEGIN: handle_begin(args, arglen); break;
      case OP_SIG:   handle_sig(args, arglen);   break;
      case OP_END:   handle_end();               break;
      case OP_ABORT: handle_abort();             break;
      default:
        USBSerial.printf("[ota_ble] unknown control opcode 0x%02X\n", opcode);
        break;
    }
  }
};

class DataCB : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* chr, NimBLEConnInfo& /*info*/) override {
    // Raw image bytes, in order. write-without-response: no ack, throughput path.
    const NimBLEAttValue& v = chr->getValue();
    const uint8_t* p   = v.data();
    const size_t   len = v.size();
    if (p == nullptr || len == 0) {
      return;
    }
    if (!k1_ota_active()) {
      return;  // stray data outside a session — drop silently
    }
    if (!k1_ota_write(p, len)) {
      // esp_ota_write failure aborts the engine session; report integrity fail.
      publish_and_notify_reject(RJ_INTEGRITY);
      reset_session_counters();
      return;
    }
    s_written += (uint32_t)len;

    // PROGRESS: only when a whole percent lands, and only if we know the size.
    if (s_expected_size != 0) {
      const int16_t pct =
          (int16_t)(((uint64_t)s_written * 100ULL) / (uint64_t)s_expected_size);
      const int16_t clamped = pct > 100 ? 100 : pct;
      if (clamped != s_last_percent) {
        s_last_percent = clamped;
        k1_ota_mode_publish_progress((float)clamped / 100.0f);
        notify_progress((uint8_t)clamped);
      }
    }
  }
};

class ServerCB : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* server, NimBLEConnInfo& info) override {
    s_conn = info.getConnHandle();
    // Negotiate throughput: request Data Length Extension for the link. MTU is
    // driven client-side (default MTU cap is set device-wide at start()); DLE +
    // 2M PHY carry the 517-byte MTU efficiently. (contract flow step 1.)
    server->setDataLen(s_conn, K1_OTA_DLE_TX_OCTETS);
#if defined(BLE_GAP_LE_PHY_2M_MASK)
    NimBLEDevice::setDefaultPhy(BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK);
#endif
#ifdef SB_K1_BLE_REMOTED
    // If the Remoted central is compiled in, reduce 2.4 GHz contention while the
    // image streams by stopping its scan for the duration of the connection.
    NimBLEScan* scan = NimBLEDevice::getScan();
    if (scan != nullptr) {
      scan->stop();
    }
#endif
    USBSerial.printf("[ota_ble] client connected (conn=%u)\n", (unsigned)s_conn);
  }

  void onDisconnect(NimBLEServer* server, NimBLEConnInfo& /*info*/, int reason) override {
    s_conn = BLE_HS_CONN_HANDLE_NONE;
    // If a session was mid-flight, abort it — a dropped link must not leave the
    // engine half-open holding an esp_ota handle.
    if (k1_ota_active()) {
      k1_ota_abort();
      k1_ota_mode_publish_state(OtaUiState::ADVERTISING);
    }
    reset_session_counters();
    // Resume advertising so a fresh client (or a reconnect) can pick the service
    // back up. Never called on the ACCEPT/reboot path (that supersedes teardown).
    if (s_running && server != nullptr) {
      server->getAdvertising()->start();
    }
    USBSerial.printf("[ota_ble] client disconnected (reason=%d) — advertising resumed\n",
                     reason);
  }

  void onMTUChange(uint16_t mtu, NimBLEConnInfo& /*info*/) override {
    USBSerial.printf("[ota_ble] MTU negotiated: %u\n", (unsigned)mtu);
  }
};

ControlCB s_control_cb;
DataCB    s_data_cb;
ServerCB  s_server_cb;

}  // namespace

// ─────────────────────────────────────────────────────────────────────────────
// Public API (locked contract).
// ─────────────────────────────────────────────────────────────────────────────
bool k1_ota_ble_service_start() {
  if (s_running) {
    return true;  // idempotent — already advertising
  }

  // HEAP guard: refuse to stand the server up below the internal-SRAM floor,
  // rather than fragment the heap into a later abort (risk-register HEAP).
  const size_t internal_free = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  USBSerial.printf("[ota_ble] start — internal_free=%u total_free=%u\n",
                   (unsigned)internal_free, (unsigned)ESP.getFreeHeap());
  if (internal_free < K1_OTA_MIN_INTERNAL_FREE) {
    USBSerial.printf("[ota_ble] start FAILED — internal free %u < floor %u\n",
                     (unsigned)internal_free, (unsigned)K1_OTA_MIN_INTERNAL_FREE);
    return false;
  }

  // Shared idempotent NimBLE init — co-exists with the Remoted central. NEVER call
  // NimBLEDevice::init() directly (double-init crash mitigation).
  if (!k1_ota_nimble_ensure_inited()) {
    USBSerial.println("[ota_ble] start FAILED — NimBLE init");
    return false;
  }

  // Request the target ATT MTU device-wide before the server comes up so the
  // negotiated MTU can reach the 517-byte contract target.
  NimBLEDevice::setMTU(517);

  // NO pairing / NO bonding. The OTA image is authenticated on-device by its
  // RSA-3072 signature (k1_ota_end), NOT by the BLE link — so the peripheral never
  // requires pairing (no characteristic carries an ENC/AUTH flag). These two calls
  // re-assert NimBLE's init defaults (no-op, kept for explicitness — NOT a fix).
  NimBLEDevice::setSecurityAuth(false, false, false);
  NimBLEDevice::setSecurityIOCap(BLE_HS_IO_NO_INPUT_OUTPUT);

  // Advertise from a fresh RANDOM address, not the fixed public MAC. A central
  // that previously bonded the K1's public identity (e.g. macOS caching an LTK
  // from an earlier BLE build) keys its stale bond to that public address; on
  // reconnect it attempts encryption with a key the reflashed K1 no longer holds
  // and CoreBluetooth aborts with "Peer removed pairing information" (Code 14).
  // Using a random address makes every central see a brand-new, bondless peer, so
  // the connection is always fresh. deleteAllBonds() clears any residual K1-side
  // bond store as well. (Address auth: our signature, not the BLE link.)
  NimBLEDevice::deleteAllBonds();
  NimBLEDevice::setOwnAddrType(BLE_OWN_ADDR_RANDOM);

  s_server = NimBLEDevice::createServer();
  if (s_server == nullptr) {
    USBSerial.println("[ota_ble] start FAILED — createServer");
    return false;
  }
  s_server->setCallbacks(&s_server_cb, false);
  s_server->advertiseOnDisconnect(false);  // we resume advertising explicitly

  s_service = s_server->createService(K1_OTA_SERVICE_UUID);
  if (s_service == nullptr) {
    USBSerial.println("[ota_ble] start FAILED — createService");
    return false;
  }

  s_control = s_service->createCharacteristic(
      K1_OTA_CONTROL_UUID,
      NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::NOTIFY);
  s_data = s_service->createCharacteristic(
      K1_OTA_DATA_UUID,
      NIMBLE_PROPERTY::WRITE_NR);
  if (s_control == nullptr || s_data == nullptr) {
    USBSerial.println("[ota_ble] start FAILED — createCharacteristic");
    return false;
  }
  s_control->setCallbacks(&s_control_cb);
  s_data->setCallbacks(&s_data_cb);

  s_service->start();

  NimBLEAdvertising* adv = s_server->getAdvertising();
  adv->setName(K1_OTA_ADV_NAME);
  adv->addServiceUUID(K1_OTA_SERVICE_UUID);
  adv->enableScanResponse(true);
  if (!adv->start()) {
    USBSerial.println("[ota_ble] start FAILED — advertising");
    return false;
  }

  s_running = true;
  reset_session_counters();
  // Waiting screen: service up, no session yet.
  k1_ota_mode_publish_state(OtaUiState::ADVERTISING);
  USBSerial.printf("[ota_ble] advertising '%s' svc=%s — post-create internal_free=%u\n",
                   K1_OTA_ADV_NAME, K1_OTA_SERVICE_UUID,
                   (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
  return true;
}

void k1_ota_ble_service_stop() {
  if (!s_running) {
    return;
  }
  if (k1_ota_active()) {
    k1_ota_abort();
  }
  NimBLEAdvertising* adv = (s_server != nullptr) ? s_server->getAdvertising() : nullptr;
  if (adv != nullptr) {
    adv->stop();
  }
  if (s_server != nullptr && s_service != nullptr) {
    s_server->removeService(s_service, true);  // delete the OTA GATT server tree
  }
  s_service = nullptr;
  s_control = nullptr;
  s_data    = nullptr;
  s_conn    = BLE_HS_CONN_HANDLE_NONE;
  s_running = false;
  reset_session_counters();
  // Do NOT de-init NimBLEDevice — the Remoted central may still own it.
  k1_ota_mode_publish_state(OtaUiState::IDLE);
  USBSerial.println("[ota_ble] stopped — GATT torn down, NimBLE left inited");
}

bool k1_ota_ble_service_running() {
  return s_running;
}

#endif  // SB_ENABLE_OTA
