// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// ble_remoted_central.cpp - K1 BLE-MIDI CENTRAL receiver for the Remoted dial.
//
// GATED / NON-SHIPPABLE. Compiled only under -DSB_K1_BLE_REMOTED
// (env k1_ble_remoted_probe). Production (k1_hardware) never sees this TU nor
// the .ino hooks, so the shipping firmware stays radio-free.
//
// The Remoted knob is a standard Apple BLE-MIDI peripheral ("SpectraSynq
// Remoted"). This central scans, connects, subscribes to notifications, decodes
// the generated 71-control map into K1WirelessControlRecord values, and applies
// them from the main-loop poll via sb_k1_control_apply().
#ifdef SB_K1_BLE_REMOTED

#include "ble_remoted_central.h"

#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_heap_caps.h> // internal-RAM budget telemetry (bench-only, non-shippable)

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "k1_ble_midi_decoder.h"
#include "sb_k1_control_facade.h"

// Runtime gate for the 1 Hz [ble_remoted] counters + heap telemetry below
// (defined in globals.h, default false). Toggle live via serial :ble_stream=on/off
// so the monitor isn't spammed unless a session is actively watching.
extern bool BLE_STREAM_ENABLED;

extern uint8_t sb_k1_confirmed_mode(bool);       // feedback-only committed mode per channel

namespace {

constexpr char BLEMIDI_SERVICE_UUID[] = "03B80E5A-EDE8-4B33-A751-6CE34EC4C700";
constexpr char BLEMIDI_CHAR_UUID[]    = "7772E5DB-3868-4112-A1A9-F2669D106BF3";
constexpr char KNOB_NAME[]            = "SpectraSynq Remoted";

constexpr uint8_t CC_CONFIRM_PRIMARY   = 0x20;   // K1 -> knob: confirmed primary mode ordinal
constexpr uint8_t CC_CONFIRM_SECONDARY = 0x21;   // K1 -> knob: confirmed secondary mode ordinal
constexpr UBaseType_t CMD_QUEUE_CAPACITY = 16;

QueueHandle_t s_cmd_queue = nullptr;
StaticQueue_t s_cmd_queue_struct;
uint8_t s_cmd_queue_storage[CMD_QUEUE_CAPACITY * sizeof(K1WirelessControlRecord)];

TaskHandle_t s_task = nullptr;
NimBLEClient* s_client = nullptr;
NimBLERemoteCharacteristic* s_rx_char = nullptr; // subscribed + writable characteristic
volatile bool s_connected = false;
volatile bool s_linked = false;
volatile uint32_t s_connection_generation = 0;
volatile bool s_force_confirm = false;
uint8_t s_last_pm = 255;
uint8_t s_last_sm = 255;
bool s_confirmation_pending = false;
uint8_t s_confirmation_pm = 0;
uint8_t s_confirmation_sm = 0;
volatile bool s_have_target = false;
NimBLEAddress s_target_addr;
portMUX_TYPE s_target_mux = portMUX_INITIALIZER_UNLOCKED;
portMUX_TYPE s_state_mux = portMUX_INITIALIZER_UNLOCKED;

K1BleMidiDecoderState s_decoder;
uint32_t s_decode_errors = 0;
uint32_t s_queue_drops = 0;
uint32_t s_notify_packets = 0;
uint32_t s_decoded_records = 0;
uint32_t s_enqueued_records = 0;
uint32_t s_apply_ok = 0;
uint32_t s_apply_fail = 0;
uint32_t s_last_counter_ms = 0;

void decode_and_enqueue(const uint8_t* p, size_t len) {
  if (!s_cmd_queue || p == nullptr) {
    return;
  }

  ++s_notify_packets;
  K1WirelessControlRecord records[K1_BLE_MIDI_MAX_RECORDS_PER_PACKET];
  size_t count = 0;
  const K1BleMidiDecodeStatus status =
      k1_ble_midi_decode_packet(&s_decoder, p, len, records,
                                K1_BLE_MIDI_MAX_RECORDS_PER_PACKET, &count);
  if (status != K1_BLE_MIDI_DECODE_OK && status != K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW) {
    ++s_decode_errors;
    return;
  }
  if (status == K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW) {
    ++s_decode_errors;
  }
  s_decoded_records += static_cast<uint32_t>(count);

  for (size_t i = 0; i < count; ++i) {
    if (xQueueSend(s_cmd_queue, &records[i], 0) != pdTRUE) {
      ++s_queue_drops;
    } else {
      ++s_enqueued_records;
    }
  }
}

void on_notify(NimBLERemoteCharacteristic*, uint8_t* data, size_t len, bool) {
  decode_and_enqueue(data, len);
}

class ScanCB : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice* dev) override {
    if (s_have_target || s_connected || s_linked) {
      return;
    }
    const bool match = (dev->getName() == KNOB_NAME) ||
                       (dev->haveServiceUUID() &&
                        dev->isAdvertisingService(NimBLEUUID(BLEMIDI_SERVICE_UUID)));
    if (!match) {
      return;
    }
    portENTER_CRITICAL(&s_target_mux);
    s_target_addr = dev->getAddress();
    s_have_target = true;
    portEXIT_CRITICAL(&s_target_mux);
    NimBLEDevice::getScan()->stop();
  }
};
ScanCB s_scan_cb;

class ClientCB : public NimBLEClientCallbacks {
  void onConnect(NimBLEClient*) override {
    // Raw GAP connection is not a usable dial link until subscribe() succeeds.
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = true;
    s_linked = false;
    portEXIT_CRITICAL(&s_state_mux);
  }

  void onDisconnect(NimBLEClient*, int) override {
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = false;
    s_linked = false;
    s_rx_char = nullptr;
    s_confirmation_pending = false;
    portEXIT_CRITICAL(&s_state_mux);
    portENTER_CRITICAL(&s_target_mux);
    s_have_target = false;
    portEXIT_CRITICAL(&s_target_mux);
  }

  void onConnectFail(NimBLEClient*, int) override {
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = false;
    s_linked = false;
    s_rx_char = nullptr;
    s_confirmation_pending = false;
    portEXIT_CRITICAL(&s_state_mux);
    portENTER_CRITICAL(&s_target_mux);
    s_have_target = false;
    portEXIT_CRITICAL(&s_target_mux);
  }
};
ClientCB s_client_cb;

bool connection_is_current(uint32_t generation) {
  portENTER_CRITICAL(&s_state_mux);
  const bool current =
      s_connected && s_connection_generation == generation;
  portEXIT_CRITICAL(&s_state_mux);
  return current && s_client && s_client->isConnected();
}

bool connect_and_subscribe() {
  NimBLEAddress addr;
  portENTER_CRITICAL(&s_target_mux);
  addr = s_target_addr;
  portEXIT_CRITICAL(&s_target_mux);

  if (!s_client) {
    s_client = NimBLEDevice::createClient();
    if (!s_client) {
      Serial.println("[ble_remoted_diag] connect_setup_fail step=create_client");
      return false;
    }
    s_client->setClientCallbacks(&s_client_cb, false);
  }
  // Preserve discovered attribute objects across reconnects so the main-loop
  // writer cannot race deletion of a locally snapshotted characteristic.
  if (!s_client->connect(addr, false)) {
    Serial.printf("[ble_remoted_diag] connect_fail last_error=%d\n",
                  s_client->getLastError());
    return false;
  }
  portENTER_CRITICAL(&s_state_mux);
  const uint32_t generation = s_connection_generation;
  portEXIT_CRITICAL(&s_state_mux);
  if (!connection_is_current(generation)) {
    return false;
  }

  NimBLERemoteService* svc = s_client->getService(BLEMIDI_SERVICE_UUID);
  if (!svc) {
    s_client->disconnect();
    return false;
  }
  NimBLERemoteCharacteristic* chr = svc->getCharacteristic(BLEMIDI_CHAR_UUID);
  if (!chr) {
    s_client->disconnect();
    return false;
  }
  if (!connection_is_current(generation) ||
      !chr->subscribe(true, on_notify)) {
    s_client->disconnect();
    return false;
  }
  portENTER_CRITICAL(&s_state_mux);
  const bool publish =
      s_connected && s_connection_generation == generation;
  if (publish) {
    s_rx_char = chr;
    s_force_confirm = true;
    s_linked = true;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!publish) {
    return false;
  }
  Serial.println("[ble_remoted] linked + subscribed to Remoted dial");
  return true;
}

void queue_confirmed_modes(bool force) {
  const uint8_t pm = sb_k1_confirmed_mode(false);
  const uint8_t sm = sb_k1_confirmed_mode(true);
  if (!force && pm == s_last_pm && sm == s_last_sm) {
    return;
  }
  s_last_pm = pm;
  s_last_sm = sm;
  portENTER_CRITICAL(&s_state_mux);
  s_confirmation_pm = pm;
  s_confirmation_sm = sm;
  s_confirmation_pending = true;
  portEXIT_CRITICAL(&s_state_mux);
}

void send_pending_confirmation() {
  portENTER_CRITICAL(&s_state_mux);
  NimBLERemoteCharacteristic* const rx_char = s_rx_char;
  const uint32_t generation = s_connection_generation;
  const bool usable = s_connected && s_linked && rx_char != nullptr;
  const bool pending = s_confirmation_pending;
  const uint8_t pm = s_confirmation_pm;
  const uint8_t sm = s_confirmation_sm;
  if (usable && pending) {
    s_confirmation_pending = false;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!usable || !pending) {
    return;
  }
  const uint16_t ts = static_cast<uint16_t>(millis() & 0x1FFF);
  uint8_t pkt[8] = {
      static_cast<uint8_t>(0x80 | ((ts >> 7) & 0x3F)),
      static_cast<uint8_t>(0x80 | (ts & 0x7F)),
      0xB0, CC_CONFIRM_PRIMARY, pm,
      0xB0, CC_CONFIRM_SECONDARY, sm,
  };
  if (!rx_char->writeValue(pkt, sizeof(pkt), false)) {
    Serial.println("[ble_remoted_diag] confirmation_write_fail");
    portENTER_CRITICAL(&s_state_mux);
    if (s_connected && s_linked &&
        s_connection_generation == generation && s_rx_char == rx_char) {
      s_confirmation_pending = true;
    }
    portEXIT_CRITICAL(&s_state_mux);
  }
}

void ble_task(void*) {
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&s_scan_cb, false);
  scan->setActiveScan(true);
  for (;;) {
    // This Core-1 task owns every remote characteristic operation. The audio
    // loop only publishes the next confirmation payload.
    send_pending_confirmation();
    if (!s_linked && !s_connected) {
      if (!s_have_target) {
        if (!scan->isScanning()) {
          const bool started = scan->start(0, false);
          Serial.printf("[ble_remoted_diag] scan_start ok=%u active=%u\n",
                        started ? 1U : 0U,
                        scan->isScanning() ? 1U : 0U);
          if (!started) {
            vTaskDelay(pdMS_TO_TICKS(500));
          }
        }
      } else if (!connect_and_subscribe()) {
        s_have_target = false;
        vTaskDelay(pdMS_TO_TICKS(800));
      }
    }
    vTaskDelay(pdMS_TO_TICKS(150));
  }
}

} // namespace

void sb_k1_ble_remoted_begin() {
  k1_ble_midi_decoder_reset(&s_decoder);
  s_cmd_queue = xQueueCreateStatic(CMD_QUEUE_CAPACITY,
                                   sizeof(K1WirelessControlRecord),
                                   s_cmd_queue_storage,
                                   &s_cmd_queue_struct);
  const bool init_ok =
      NimBLEDevice::isInitialized() || NimBLEDevice::init("K1-Remoted-RX");
  const BaseType_t task_result =
      init_ok ? xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr,
                                       1, &s_task, 1)
              : pdFAIL;
  Serial.printf("[ble_remoted_diag] init ok=%u task_ok=%u core=1\n",
                init_ok ? 1U : 0U, task_result == pdPASS ? 1U : 0U);
  if (!init_ok || task_result != pdPASS) {
    return;
  }
  Serial.printf("[ble_remoted] begin (gated A/B build) - free heap=%u\n", ESP.getFreeHeap());
}

void sb_k1_ble_remoted_poll(uint32_t /*now_ms*/) {
  if (!s_cmd_queue) {
    return;
  }

  K1WirelessControlRecord record;
  while (xQueueReceive(s_cmd_queue, &record, 0) == pdTRUE) {
    const K1WirelessControlResult result = sb_k1_control_apply(record);
    if (!result.ok) {
      ++s_apply_fail;
      Serial.printf("[ble_remoted] apply failed control=%s code=%s\n",
                    record.control, result.error_code);
    } else {
      ++s_apply_ok;
    }
  }

  portENTER_CRITICAL(&s_state_mux);
  const bool force = s_force_confirm;
  s_force_confirm = false;
  portEXIT_CRITICAL(&s_state_mux);
  queue_confirmed_modes(force);

  const uint32_t now_ms = millis();
  if (BLE_STREAM_ENABLED && now_ms - s_last_counter_ms >= 1000U) {
    s_last_counter_ms = now_ms;
    Serial.printf("[ble_remoted] counters linked=%u notify=%lu decoded=%lu enqueued=%lu queue_drops=%lu decode_errors=%lu apply_ok=%lu apply_fail=%lu\n",
                  s_linked ? 1U : 0U,
                  (unsigned long)s_notify_packets,
                  (unsigned long)s_decoded_records,
                  (unsigned long)s_enqueued_records,
                  (unsigned long)s_queue_drops,
                  (unsigned long)s_decode_errors,
                  (unsigned long)s_apply_ok,
                  (unsigned long)s_apply_fail);
    // Internal-RAM budget telemetry (bench-only). largest = the exact quantity
    // bridge_fs_internal_heap_ok() gates on (< SB_FS_MIN_INTERNAL_BLOCK = 8192
    // -> LittleFS write defers instead of aborting inside fopen). free vs largest
    // separates exhaustion from fragmentation; watching it across time exposes leak.
    // internal_min_ever = lowest internal free EVER since boot (heap watermark).
    // This is the one that catches a TRANSIENT dip between 1Hz samples — e.g. the
    // load-conditional spike (BLE link + notify stream + WiFi-AP client + cal-complete
    // fopen) that drove the original abort while idle headroom stays ~76KB.
    Serial.printf("[ble_remoted] heap internal_free=%u internal_largest=%u internal_min_ever=%u total_free=%u psram_free=%u\n",
                  (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
                  (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL),
                  (unsigned)heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL),
                  (unsigned)ESP.getFreeHeap(),
                  (unsigned)ESP.getFreePsram());
  }
}

bool sb_k1_ble_remoted_is_linked() {
  return s_linked;
}

#endif // SB_K1_BLE_REMOTED
