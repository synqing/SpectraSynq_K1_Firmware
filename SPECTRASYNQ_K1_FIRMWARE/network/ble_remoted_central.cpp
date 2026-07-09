// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// ble_remoted_central.cpp - K1 BLE-MIDI CENTRAL receiver for the Remoted dial.
//
// GATED / NON-SHIPPABLE. Compiled only under -DK1_BLE_REMOTED
// (env k1_ble_remoted_probe). Production (k1_hardware) never sees this TU nor
// the .ino hooks, so the shipping firmware stays radio-free.
//
// The Remoted knob is a standard Apple BLE-MIDI peripheral ("SpectraSynq
// Remoted"). This central scans, connects, subscribes to notifications, decodes
// the generated 71-control map into K1WirelessControlRecord values, and applies
// them from the main-loop poll via k1_control_apply().
#ifdef K1_BLE_REMOTED

#include "ble_remoted_central.h"

#include <Arduino.h>
#include <NimBLEDevice.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "k1_ble_midi_decoder.h"
#include "k1_control_facade.h"

extern uint8_t k1_confirmed_mode(bool);       // feedback-only committed mode per channel

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
volatile bool s_linked = false;
volatile bool s_force_confirm = false;
uint8_t s_last_pm = 255;
uint8_t s_last_sm = 255;
volatile bool s_have_target = false;
volatile bool s_scanning = false;
NimBLEAddress s_target_addr;
portMUX_TYPE s_target_mux = portMUX_INITIALIZER_UNLOCKED;

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
    if (s_have_target || s_linked) {
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
    s_scanning = false;
  }

  void onScanEnd(const NimBLEScanResults&, int) override {
    s_scanning = false;
  }
};
ScanCB s_scan_cb;

class ClientCB : public NimBLEClientCallbacks {
  void onConnect(NimBLEClient*) override {
    s_linked = true;
  }

  void onDisconnect(NimBLEClient*, int) override {
    s_linked = false;
    s_have_target = false;
    s_rx_char = nullptr;
  }

  void onConnectFail(NimBLEClient*, int) override {
    s_linked = false;
    s_have_target = false;
    s_rx_char = nullptr;
  }
};
ClientCB s_client_cb;

bool connect_and_subscribe() {
  NimBLEAddress addr;
  portENTER_CRITICAL(&s_target_mux);
  addr = s_target_addr;
  portEXIT_CRITICAL(&s_target_mux);

  if (!s_client) {
    s_client = NimBLEDevice::createClient();
    s_client->setClientCallbacks(&s_client_cb, false);
  }
  if (!s_client->connect(addr)) {
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
  if (!chr->subscribe(true, on_notify)) {
    s_client->disconnect();
    return false;
  }
  s_rx_char = chr;
  s_force_confirm = true;
  Serial.println("[ble_remoted] linked + subscribed to Remoted dial");
  return true;
}

void send_confirmed_modes(bool force) {
  if (!s_rx_char) {
    return;
  }
  const uint8_t pm = k1_confirmed_mode(false);
  const uint8_t sm = k1_confirmed_mode(true);
  if (!force && pm == s_last_pm && sm == s_last_sm) {
    return;
  }
  s_last_pm = pm;
  s_last_sm = sm;
  const uint16_t ts = static_cast<uint16_t>(millis() & 0x1FFF);
  uint8_t pkt[8] = {
      static_cast<uint8_t>(0x80 | ((ts >> 7) & 0x3F)),
      static_cast<uint8_t>(0x80 | (ts & 0x7F)),
      0xB0, CC_CONFIRM_PRIMARY, pm,
      0xB0, CC_CONFIRM_SECONDARY, sm,
  };
  s_rx_char->writeValue(pkt, sizeof(pkt), false);
}

void ble_task(void*) {
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&s_scan_cb, false);
  scan->setActiveScan(true);
  for (;;) {
    if (!s_linked) {
      if (!s_have_target) {
        if (!s_scanning) {
          s_scanning = true;
          scan->start(0, false);
        }
      } else if (connect_and_subscribe()) {
        s_linked = true;
      } else {
        s_have_target = false;
        vTaskDelay(pdMS_TO_TICKS(800));
      }
    }
    vTaskDelay(pdMS_TO_TICKS(150));
  }
}

} // namespace

void k1_ble_remoted_begin() {
  k1_ble_midi_decoder_reset(&s_decoder);
  s_cmd_queue = xQueueCreateStatic(CMD_QUEUE_CAPACITY,
                                   sizeof(K1WirelessControlRecord),
                                   s_cmd_queue_storage,
                                   &s_cmd_queue_struct);
  NimBLEDevice::init("K1-Remoted-RX");
  xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr, 1, &s_task, 0);
  Serial.printf("[ble_remoted] begin (gated A/B build) - free heap=%u\n", ESP.getFreeHeap());
}

void k1_ble_remoted_poll(uint32_t /*now_ms*/) {
  if (!s_cmd_queue) {
    return;
  }

  K1WirelessControlRecord record;
  while (xQueueReceive(s_cmd_queue, &record, 0) == pdTRUE) {
    const K1WirelessControlResult result = k1_control_apply(record);
    if (!result.ok) {
      ++s_apply_fail;
      Serial.printf("[ble_remoted] apply failed control=%s code=%s\n",
                    record.control, result.error_code);
    } else {
      ++s_apply_ok;
    }
  }

  const bool force = s_force_confirm;
  s_force_confirm = false;
  send_confirmed_modes(force);

  const uint32_t now_ms = millis();
  if (now_ms - s_last_counter_ms >= 1000U) {
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
  }
}

bool k1_ble_remoted_is_linked() {
  return s_linked;
}

#endif // K1_BLE_REMOTED
