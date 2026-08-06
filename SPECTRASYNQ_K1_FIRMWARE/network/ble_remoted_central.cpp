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
// them from the main-loop poll via k1_control_apply().
#ifdef K1_BLE_REMOTED

#include "ble_remoted_central.h"

#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_heap_caps.h> // internal-RAM budget telemetry (bench-only, non-shippable)
#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "k1_ble_midi_decoder.h"
#include "k1_control_facade.h"

// Runtime gate for the 1 Hz [ble_remoted] counters + heap telemetry below
// (defined in globals.h, default false). Toggle live via serial :ble_stream=on/off
// so the monitor isn't spammed unless a session is actively watching.
extern bool BLE_STREAM_ENABLED;

extern uint8_t k1_confirmed_mode(bool);       // feedback-only committed mode per channel

namespace {

constexpr char BLEMIDI_SERVICE_UUID[] = "03B80E5A-EDE8-4B33-A751-6CE34EC4C700";
constexpr char BLEMIDI_CHAR_UUID[]    = "7772E5DB-3868-4112-A1A9-F2669D106BF3";
constexpr char KNOB_NAME[]            = "SpectraSynq Remoted";

constexpr uint8_t CC_CONFIRM_PRIMARY   = 0x20;   // K1 -> knob: confirmed primary mode ordinal
constexpr uint8_t CC_CONFIRM_SECONDARY = 0x21;   // K1 -> knob: confirmed secondary mode ordinal
constexpr UBaseType_t CMD_QUEUE_CAPACITY = 16;

enum class ConfirmCause : uint8_t {
  Initial = 0,
  DialMode,
  Other,
};

struct DialModeTarget {
  bool valid;
  bool secondary;
  uint32_t record_id;
  uint32_t generation;
  uint8_t accepted;
};

struct QueuedControlRecord {
  K1WirelessControlRecord record;
  uint32_t generation;
};

struct StateSnapshot {
  bool linked;
  uint32_t generation;
  bool scan_active;
  uint32_t scan_start_ok;
  uint32_t scan_start_fail;
  uint32_t notify;
  uint32_t decoded;
  uint32_t enqueued;
  uint32_t apply_ok;
  uint32_t apply_fail;
  uint32_t queue_drops;
  uint32_t decode_errors;
  uint32_t stale_generation_drops;
  uint32_t link_up;
  uint32_t link_down;
  uint32_t connect_fail;
  uint32_t dial_mode_apply_ok;
  uint32_t confirm_write_ok;
  uint32_t confirm_write_fail;
  uint32_t dial_confirm_write_ok;
  uint8_t last_confirm_pm;
  uint8_t last_confirm_sm;
};

QueueHandle_t s_cmd_queue = nullptr;
StaticQueue_t s_cmd_queue_struct;
uint8_t s_cmd_queue_storage[CMD_QUEUE_CAPACITY * sizeof(QueuedControlRecord)];

TaskHandle_t s_task = nullptr;
NimBLEClient* s_client = nullptr;
NimBLERemoteCharacteristic* s_rx_char = nullptr; // subscribed + writable characteristic
volatile bool s_connected = false;
volatile bool s_linked = false;
volatile uint32_t s_connection_generation = 0;
bool s_scan_active = false;
uint32_t s_scan_start_ok = 0;
uint32_t s_scan_start_fail = 0;
volatile bool s_force_confirm = false;
uint8_t s_last_pm = 255;
uint8_t s_last_sm = 255;
bool s_confirmation_pending = false;
bool s_confirmation_inflight = false;
uint8_t s_confirmation_pm = 0;
uint8_t s_confirmation_sm = 0;
ConfirmCause s_confirmation_cause = ConfirmCause::Other;
uint32_t s_confirmation_record_id = 0;
uint32_t s_confirmation_generation = 0;
DialModeTarget s_dial_mode_target = {};
bool s_link_down_log_pending = false;
uint32_t s_link_down_log_generation = 0;
int s_link_down_log_reason = 0;
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
uint32_t s_stale_generation_drops = 0;
uint32_t s_apply_ok = 0;
uint32_t s_apply_fail = 0;
uint32_t s_link_up = 0;
uint32_t s_link_down = 0;
uint32_t s_connect_fail = 0;
uint32_t s_dial_mode_apply_ok = 0;
uint32_t s_confirm_write_ok = 0;
uint32_t s_confirm_write_fail = 0;
uint32_t s_dial_confirm_write_ok = 0;
uint8_t s_last_confirm_pm = 255;
uint8_t s_last_confirm_sm = 255;
uint32_t s_last_counter_ms = 0;

const char* confirm_cause_name(ConfirmCause cause) {
  switch (cause) {
    case ConfirmCause::Initial:
      return "initial";
    case ConfirmCause::DialMode:
      return "dial_mode";
    case ConfirmCause::Other:
    default:
      return "other";
  }
}

template <size_t N>
void serial_print_formatted(char (&line)[N], int written) {
  if (written > 0 && static_cast<size_t>(written) < N) {
    Serial.print(line);
    return;
  }
  Serial.println("[ble_remoted_diag] format_overflow");
}

StateSnapshot state_snapshot() {
  portENTER_CRITICAL(&s_state_mux);
  const StateSnapshot snapshot = {
      s_linked,
      s_connection_generation,
      s_scan_active,
      s_scan_start_ok,
      s_scan_start_fail,
      s_notify_packets,
      s_decoded_records,
      s_enqueued_records,
      s_apply_ok,
      s_apply_fail,
      s_queue_drops,
      s_decode_errors,
      s_stale_generation_drops,
      s_link_up,
      s_link_down,
      s_connect_fail,
      s_dial_mode_apply_ok,
      s_confirm_write_ok,
      s_confirm_write_fail,
      s_dial_confirm_write_ok,
      s_last_confirm_pm,
      s_last_confirm_sm,
  };
  portEXIT_CRITICAL(&s_state_mux);
  return snapshot;
}

void record_connect_failure() {
  portENTER_CRITICAL(&s_state_mux);
  ++s_connect_fail;
  portEXIT_CRITICAL(&s_state_mux);
}

void emit_pending_link_down() {
  portENTER_CRITICAL(&s_state_mux);
  const bool pending = s_link_down_log_pending;
  const uint32_t generation = s_link_down_log_generation;
  const int reason = s_link_down_log_reason;
  s_link_down_log_pending = false;
  portEXIT_CRITICAL(&s_state_mux);
  if (!pending) {
    return;
  }
  char line[96];
  const int written = snprintf(
      line, sizeof(line),
      "[ble_remoted] link down generation=%lu reason=%d\n",
      static_cast<unsigned long>(generation), reason);
  serial_print_formatted(line, written);
}

void decode_and_enqueue(
    const uint8_t* p, size_t len, uint32_t generation) {
  if (!s_cmd_queue || p == nullptr) {
    return;
  }

  portENTER_CRITICAL(&s_state_mux);
  ++s_notify_packets;
  portEXIT_CRITICAL(&s_state_mux);
  K1WirelessControlRecord records[K1_BLE_MIDI_MAX_RECORDS_PER_PACKET];
  size_t count = 0;
  const K1BleMidiDecodeStatus status =
      k1_ble_midi_decode_packet(&s_decoder, p, len, records,
                                K1_BLE_MIDI_MAX_RECORDS_PER_PACKET, &count);
  if (status != K1_BLE_MIDI_DECODE_OK && status != K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW) {
    portENTER_CRITICAL(&s_state_mux);
    ++s_decode_errors;
    portEXIT_CRITICAL(&s_state_mux);
    return;
  }
  portENTER_CRITICAL(&s_state_mux);
  if (status == K1_BLE_MIDI_DECODE_OUTPUT_OVERFLOW) {
    ++s_decode_errors;
  }
  s_decoded_records += static_cast<uint32_t>(count);
  portEXIT_CRITICAL(&s_state_mux);

  for (size_t i = 0; i < count; ++i) {
    const QueuedControlRecord queued = {records[i], generation};
    const bool enqueued =
        xQueueSend(s_cmd_queue, &queued, 0) == pdTRUE;
    portENTER_CRITICAL(&s_state_mux);
    if (!enqueued) {
      ++s_queue_drops;
    } else {
      ++s_enqueued_records;
    }
    portEXIT_CRITICAL(&s_state_mux);
  }
}

void on_notify(
    NimBLERemoteCharacteristic* characteristic,
    uint8_t* data,
    size_t len,
    bool) {
  portENTER_CRITICAL(&s_state_mux);
  const uint32_t generation = s_connection_generation;
  const bool usable =
      s_connected && s_linked && characteristic == s_rx_char;
  if (!usable) {
    ++s_stale_generation_drops;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!usable) {
    return;
  }
  decode_and_enqueue(data, len, generation);
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
    // A new generation must not inherit a partial CC14/NRPN transaction.
    k1_ble_midi_decoder_reset_partial(&s_decoder);
    portENTER_CRITICAL(&s_state_mux);
    ++s_connection_generation;
    s_connected = true;
    s_linked = false;
    portEXIT_CRITICAL(&s_state_mux);
  }

  void onDisconnect(NimBLEClient*, int reason) override {
    portENTER_CRITICAL(&s_state_mux);
    const bool was_linked = s_linked;
    const uint32_t generation = ++s_connection_generation;
    if (was_linked) {
      ++s_link_down;
      s_link_down_log_pending = true;
      s_link_down_log_generation = generation;
      s_link_down_log_reason = reason;
    }
    s_connected = false;
    s_linked = false;
    s_rx_char = nullptr;
    s_confirmation_pending = false;
    s_confirmation_inflight = false;
    s_dial_mode_target = {};
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
    s_confirmation_inflight = false;
    s_dial_mode_target = {};
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

void publish_scan_active(bool active) {
  portENTER_CRITICAL(&s_state_mux);
  s_scan_active = active;
  portEXIT_CRITICAL(&s_state_mux);
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
    char line[96];
    const int written = snprintf(
        line, sizeof(line),
        "[ble_remoted_diag] connect_fail last_error=%d\n",
        s_client->getLastError());
    serial_print_formatted(line, written);
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
    ++s_link_up;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!publish) {
    return false;
  }
  char line[80];
  const int written = snprintf(
      line, sizeof(line), "[ble_remoted] link up generation=%lu\n",
      static_cast<unsigned long>(generation));
  serial_print_formatted(line, written);
  Serial.println("[ble_remoted] linked + subscribed to Remoted dial");
  return true;
}

void queue_confirmed_modes(bool force) {
  const uint8_t pm = k1_confirmed_mode(false);
  const uint8_t sm = k1_confirmed_mode(true);

  portENTER_CRITICAL(&s_state_mux);
  if (s_connected && s_linked &&
      !s_confirmation_pending && !s_confirmation_inflight) {
    ConfirmCause cause = ConfirmCause::Other;
    uint32_t record_id = 0;
    bool should_queue = false;

    if (force) {
      cause = ConfirmCause::Initial;
      should_queue = true;
    } else if (
        s_dial_mode_target.valid &&
        s_dial_mode_target.generation == s_connection_generation &&
        (s_dial_mode_target.secondary ? sm : pm) ==
            s_dial_mode_target.accepted) {
      cause = ConfirmCause::DialMode;
      record_id = s_dial_mode_target.record_id;
      should_queue = true;
    } else if (pm != s_last_pm || sm != s_last_sm) {
      should_queue = true;
    }

    if (should_queue) {
      s_confirmation_pm = pm;
      s_confirmation_sm = sm;
      s_confirmation_cause = cause;
      s_confirmation_record_id = record_id;
      s_confirmation_generation = s_connection_generation;
      s_confirmation_pending = true;
    }
  }
  portEXIT_CRITICAL(&s_state_mux);
}

void send_pending_confirmation() {
  portENTER_CRITICAL(&s_state_mux);
  NimBLERemoteCharacteristic* const rx_char = s_rx_char;
  const uint32_t generation = s_connection_generation;
  const bool usable = s_connected && s_linked && rx_char != nullptr;
  const bool pending =
      s_confirmation_pending && !s_confirmation_inflight;
  const uint8_t pm = s_confirmation_pm;
  const uint8_t sm = s_confirmation_sm;
  const ConfirmCause cause = s_confirmation_cause;
  const uint32_t record_id = s_confirmation_record_id;
  const uint32_t queued_generation = s_confirmation_generation;
  const bool current_pending =
      pending && queued_generation == generation;
  if (usable && current_pending) {
    s_confirmation_pending = false;
    s_confirmation_inflight = true;
  }
  portEXIT_CRITICAL(&s_state_mux);
  if (!usable || !current_pending) {
    return;
  }
  const uint16_t ts = static_cast<uint16_t>(millis() & 0x1FFF);
  uint8_t pkt[8] = {
      static_cast<uint8_t>(0x80 | ((ts >> 7) & 0x3F)),
      static_cast<uint8_t>(0x80 | (ts & 0x7F)),
      0xB0, CC_CONFIRM_PRIMARY, pm,
      0xB0, CC_CONFIRM_SECONDARY, sm,
  };
  const bool write_ok = rx_char->writeValue(pkt, sizeof(pkt), false);
  portENTER_CRITICAL(&s_state_mux);
  const bool current =
      s_connected && s_linked &&
      s_connection_generation == generation && s_rx_char == rx_char;
  const bool confirmed = write_ok && current;
  s_confirmation_inflight = false;
  if (confirmed) {
    ++s_confirm_write_ok;
    s_last_confirm_pm = pm;
    s_last_confirm_sm = sm;
    s_last_pm = pm;
    s_last_sm = sm;
    if (cause == ConfirmCause::DialMode) {
      ++s_dial_confirm_write_ok;
      if (s_dial_mode_target.valid &&
          s_dial_mode_target.record_id == record_id &&
          s_dial_mode_target.generation == generation) {
        s_dial_mode_target = {};
      }
    }
  } else {
    ++s_confirm_write_fail;
    if (current) {
      s_confirmation_pm = pm;
      s_confirmation_sm = sm;
      s_confirmation_cause = cause;
      s_confirmation_record_id = record_id;
      s_confirmation_generation = queued_generation;
      s_confirmation_pending = true;
    }
  }
  portEXIT_CRITICAL(&s_state_mux);

  if (!confirmed) {
    Serial.println("[ble_remoted_diag] confirmation_write_fail");
  }
  char line[224];
  const int written = snprintf(
      line, sizeof(line),
      "[ble_remoted] confirm_write ok=%u cause=%s record_id=%lu "
      "generation=%lu pm=%u sm=%u\n",
      confirmed ? 1U : 0U,
      confirm_cause_name(cause),
      static_cast<unsigned long>(record_id),
      static_cast<unsigned long>(queued_generation),
      static_cast<unsigned>(pm),
      static_cast<unsigned>(sm));
  serial_print_formatted(line, written);
}

void ble_task(void*) {
  NimBLEScan* scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&s_scan_cb, false);
  scan->setActiveScan(true);
  for (;;) {
    // This Core-1 task owns every remote characteristic operation. The audio
    // loop only publishes the next confirmation payload.
    emit_pending_link_down();
    send_pending_confirmation();
    publish_scan_active(scan->isScanning());
    if (!s_linked && !s_connected) {
      if (!s_have_target) {
        if (!scan->isScanning()) {
          const bool started = scan->start(0, false);
          const bool active = scan->isScanning();
          portENTER_CRITICAL(&s_state_mux);
          s_scan_active = active;
          if (started) {
            ++s_scan_start_ok;
          } else {
            ++s_scan_start_fail;
          }
          portEXIT_CRITICAL(&s_state_mux);
          char line[96];
          const int written = snprintf(
              line, sizeof(line),
              "[ble_remoted_diag] scan_start ok=%u active=%u\n",
              started ? 1U : 0U, active ? 1U : 0U);
          serial_print_formatted(line, written);
          if (!started) {
            vTaskDelay(pdMS_TO_TICKS(500));
          }
        }
      } else if (!connect_and_subscribe()) {
        record_connect_failure();
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
                                   sizeof(QueuedControlRecord),
                                   s_cmd_queue_storage,
                                   &s_cmd_queue_struct);
  const bool init_ok =
      NimBLEDevice::isInitialized() || NimBLEDevice::init("K1-Remoted-RX");
  const BaseType_t task_result =
      init_ok ? xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr,
                                       1, &s_task, 1)
              : pdFAIL;
  char line[96];
  int written = snprintf(
      line, sizeof(line),
      "[ble_remoted_diag] init ok=%u task_ok=%u core=1\n",
      init_ok ? 1U : 0U, task_result == pdPASS ? 1U : 0U);
  serial_print_formatted(line, written);
  if (!init_ok || task_result != pdPASS) {
    return;
  }
  written = snprintf(
      line, sizeof(line),
      "[ble_remoted] begin (gated A/B build) - free heap=%u\n",
      static_cast<unsigned>(ESP.getFreeHeap()));
  serial_print_formatted(line, written);
}

void k1_ble_remoted_poll(uint32_t /*now_ms*/) {
  if (!s_cmd_queue) {
    return;
  }

  QueuedControlRecord queued;
  while (xQueueReceive(s_cmd_queue, &queued, 0) == pdTRUE) {
    portENTER_CRITICAL(&s_state_mux);
    const bool current_generation =
        s_connected && s_linked &&
        queued.generation == s_connection_generation;
    if (!current_generation) {
      ++s_stale_generation_drops;
    }
    portEXIT_CRITICAL(&s_state_mux);
    if (!current_generation) {
      continue;
    }
    const K1WirelessControlRecord& record = queued.record;
    const bool is_primary_mode =
        strcmp(record.control, "primary.mode") == 0;
    const bool is_secondary_mode =
        strcmp(record.control, "secondary.mode") == 0;
    const uint8_t committed_before =
        (is_primary_mode || is_secondary_mode)
            ? k1_confirmed_mode(is_secondary_mode)
            : 0;
    const K1WirelessControlResult result = k1_control_apply(record);
    uint32_t apply_ok_count = 0;
    uint8_t accepted = 0;
    bool meaningful_mode_change = false;

    portENTER_CRITICAL(&s_state_mux);
    const bool still_current =
        s_connected && s_linked &&
        queued.generation == s_connection_generation;
    if (!still_current) {
      ++s_stale_generation_drops;
    } else if (!result.ok) {
      ++s_apply_fail;
    } else {
      ++s_apply_ok;
      apply_ok_count = s_apply_ok;
      if (is_primary_mode || is_secondary_mode) {
        accepted = static_cast<uint8_t>(result.number_value);
        meaningful_mode_change = accepted != committed_before;
        if (meaningful_mode_change) {
          ++s_dial_mode_apply_ok;
          s_dial_mode_target.valid = true;
          s_dial_mode_target.secondary = is_secondary_mode;
          s_dial_mode_target.record_id = record.id;
          s_dial_mode_target.generation = queued.generation;
          s_dial_mode_target.accepted = accepted;
        }
      }
    }
    portEXIT_CRITICAL(&s_state_mux);

    if (!still_current) {
      continue;
    }
    if (!result.ok) {
      char line[192];
      const int written = snprintf(
          line, sizeof(line),
          "[ble_remoted] apply failed control=%s code=%s\n",
          record.control, result.error_code);
      serial_print_formatted(line, written);
    } else if (meaningful_mode_change) {
      char line[192];
      const int written = snprintf(
          line, sizeof(line),
          "[ble_remoted] mode_apply record_id=%lu control=%s "
          "accepted=%u apply_ok=%lu\n",
          static_cast<unsigned long>(record.id),
          record.control,
          static_cast<unsigned>(accepted),
          static_cast<unsigned long>(apply_ok_count));
      serial_print_formatted(line, written);
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
    const StateSnapshot snapshot = state_snapshot();
    char line[512];
    int written = snprintf(
        line, sizeof(line),
        "[ble_remoted] counters linked=%u scan_active=%u "
        "scan_start_ok=%lu scan_start_fail=%lu "
        "notify=%lu decoded=%lu "
        "enqueued=%lu queue_drops=%lu decode_errors=%lu "
        "stale_generation_drops=%lu apply_ok=%lu "
        "apply_fail=%lu link_up=%lu link_down=%lu connect_fail=%lu "
        "confirm_ok=%lu confirm_fail=%lu confirm_pm=%u confirm_sm=%u\n",
        snapshot.linked ? 1U : 0U,
        snapshot.scan_active ? 1U : 0U,
        static_cast<unsigned long>(snapshot.scan_start_ok),
        static_cast<unsigned long>(snapshot.scan_start_fail),
        static_cast<unsigned long>(snapshot.notify),
        static_cast<unsigned long>(snapshot.decoded),
        static_cast<unsigned long>(snapshot.enqueued),
        static_cast<unsigned long>(snapshot.queue_drops),
        static_cast<unsigned long>(snapshot.decode_errors),
        static_cast<unsigned long>(snapshot.stale_generation_drops),
        static_cast<unsigned long>(snapshot.apply_ok),
        static_cast<unsigned long>(snapshot.apply_fail),
        static_cast<unsigned long>(snapshot.link_up),
        static_cast<unsigned long>(snapshot.link_down),
        static_cast<unsigned long>(snapshot.connect_fail),
        static_cast<unsigned long>(snapshot.confirm_write_ok),
        static_cast<unsigned long>(snapshot.confirm_write_fail),
        static_cast<unsigned>(snapshot.last_confirm_pm),
        static_cast<unsigned>(snapshot.last_confirm_sm));
    serial_print_formatted(line, written);
    // Internal-RAM budget telemetry (bench-only). largest = the exact quantity
    // bridge_fs_internal_heap_ok() gates on (< SB_FS_MIN_INTERNAL_BLOCK = 8192
    // -> LittleFS write defers instead of aborting inside fopen). free vs largest
    // separates exhaustion from fragmentation; watching it across time exposes leak.
    // internal_min_ever = lowest internal free EVER since boot (heap watermark).
    // This is the one that catches a TRANSIENT dip between 1Hz samples — e.g. the
    // load-conditional spike (BLE link + notify stream + WiFi-AP client + cal-complete
    // fopen) that drove the original abort while idle headroom stays ~76KB.
    written = snprintf(
        line, sizeof(line),
        "[ble_remoted] heap internal_free=%u internal_largest=%u "
        "internal_min_ever=%u total_free=%u psram_free=%u\n",
        static_cast<unsigned>(
            heap_caps_get_free_size(MALLOC_CAP_INTERNAL)),
        static_cast<unsigned>(
            heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL)),
        static_cast<unsigned>(
            heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL)),
        static_cast<unsigned>(ESP.getFreeHeap()),
        static_cast<unsigned>(ESP.getFreePsram()));
    serial_print_formatted(line, written);
  }
}

bool k1_ble_remoted_is_linked() {
  return state_snapshot().linked;
}

void k1_ble_remoted_status() {
  const StateSnapshot snapshot = state_snapshot();
  char line[512];
  const int written = snprintf(
      line, sizeof(line),
      "DIAL_STATUS: linked=%u generation=%lu scan_active=%u "
      "scan_start_ok=%lu scan_start_fail=%lu notify=%lu decoded=%lu "
      "enqueued=%lu apply_ok=%lu apply_fail=%lu queue_drops=%lu "
      "decode_errors=%lu stale_generation_drops=%lu "
      "dial_mode_apply_ok=%lu confirm_write_ok=%lu "
      "confirm_write_fail=%lu dial_confirm_write_ok=%lu "
      "last_confirm_pm=%u last_confirm_sm=%u\n",
      snapshot.linked ? 1U : 0U,
      static_cast<unsigned long>(snapshot.generation),
      snapshot.scan_active ? 1U : 0U,
      static_cast<unsigned long>(snapshot.scan_start_ok),
      static_cast<unsigned long>(snapshot.scan_start_fail),
      static_cast<unsigned long>(snapshot.notify),
      static_cast<unsigned long>(snapshot.decoded),
      static_cast<unsigned long>(snapshot.enqueued),
      static_cast<unsigned long>(snapshot.apply_ok),
      static_cast<unsigned long>(snapshot.apply_fail),
      static_cast<unsigned long>(snapshot.queue_drops),
      static_cast<unsigned long>(snapshot.decode_errors),
      static_cast<unsigned long>(snapshot.stale_generation_drops),
      static_cast<unsigned long>(snapshot.dial_mode_apply_ok),
      static_cast<unsigned long>(snapshot.confirm_write_ok),
      static_cast<unsigned long>(snapshot.confirm_write_fail),
      static_cast<unsigned long>(snapshot.dial_confirm_write_ok),
      static_cast<unsigned>(snapshot.last_confirm_pm),
      static_cast<unsigned>(snapshot.last_confirm_sm));
  serial_print_formatted(line, written);
}

#endif // K1_BLE_REMOTED
