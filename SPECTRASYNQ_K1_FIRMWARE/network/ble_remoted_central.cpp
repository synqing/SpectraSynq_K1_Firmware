// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// ble_remoted_central.cpp — K1 BLE-MIDI CENTRAL receiver for the Remoted dial.
//
// GATED / NON-SHIPPABLE. Compiled only under -DSB_K1_BLE_REMOTED (env
// k1_ble_remoted_probe). Production (k1_hardware) never sees this TU nor the .ino
// hooks (all #ifdef-guarded), so the shipping firmware is byte-identical.
//
// This is the 2.4 GHz radio-interference A/B build: it adds a BLE central to the
// audio firmware so the Remoted dial drives the K1 with NO Mac bridge — then the
// A/B (scripts/regression-harness/{k1_audio_visual_regression,wireless_ab_bench})
// decides whether the radio degrades the audio->LED pipeline. STOP + surface if so.
//
// Design (mirrors the proven serial-hotkey + sb_k1_wireless seams):
//   * The Remoted knob is a standard Apple BLE-MIDI peripheral ("SpectraSynq
//     Remoted"); we are the CENTRAL (inverse of the knob's ble_midi_peripheral.cpp):
//     scan -> connect -> subscribe to its NOTIFY characteristic.
//   * Wire protocol is line-for-line from the proven host bridge
//     (scripts/ble_midi/remoted_k1_bridge.py): each notify = [hdr][ts][MIDI...];
//     CC 0x10 = mode step (val>=0x40 next / else prev), CC 0x11 = channel select;
//     MIDI channel 0 = primary, 1 = secondary.
//   * SAFETY / non-blocking: the NimBLE notify callback (NimBLE host task) does the
//     MINIMUM — decode + enqueue. sb_k1_ble_remoted_poll(), called from the main
//     loop in the SAME context as check_serial, drains the queue and applies control
//     through the exact serial-hotkey entry points:
//         secondaryMode = (ch == 1);  serial_adjust_target_mode(+/-1);
//     so BLE-applied control is identical in execution context to the proven serial
//     path — no new cross-core race on the effects queue. Connection orchestration
//     runs in a dedicated LOW-PRIORITY Core-0 task so connect() never stalls audio.
#ifdef SB_K1_BLE_REMOTED

#include "ble_remoted_central.h"

#include <Arduino.h>
#include <NimBLEDevice.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

// K1 control hooks — external linkage; applied ONLY from the main-loop poll.
extern bool secondaryMode;                       // system/globals.h:823 (inline global)
extern void serial_adjust_target_mode(int8_t);   // serial/serial_menu.h:1010 (routes by secondaryMode)
extern uint8_t sb_k1_confirmed_mode(bool);       // serial/serial_menu.h (gated): committed mode per channel

namespace {

// Standard Apple BLE-MIDI contract (identical to the knob peripheral).
constexpr char BLEMIDI_SERVICE_UUID[] = "03B80E5A-EDE8-4B33-A751-6CE34EC4C700";
constexpr char BLEMIDI_CHAR_UUID[]    = "7772E5DB-3868-4112-A1A9-F2669D106BF3";
constexpr char KNOB_NAME[]            = "SpectraSynq Remoted";

// Wire protocol (matches remoted_control.cpp / remoted_k1_bridge.py).
constexpr uint8_t CC_MODE_STEP = 0x10;           // value >= 0x40 = next, else prev
constexpr uint8_t CC_CHAN_SEL  = 0x11;
constexpr uint8_t CC_CONFIRM_PRIMARY   = 0x20;   // K1 -> knob: confirmed primary mode ordinal
constexpr uint8_t CC_CONFIRM_SECONDARY = 0x21;   // K1 -> knob: confirmed secondary mode ordinal

enum class CmdKind : uint8_t { ModeStep, ChanSel };
struct RemotedCmd {
    CmdKind kind;
    uint8_t channel;                             // 0 = primary, 1 = secondary
    int8_t  dir;                                 // +1 / -1 for ModeStep
};

QueueHandle_t s_cmd_queue   = nullptr;           // NimBLE host task -> main loop (SPSC)
TaskHandle_t  s_task        = nullptr;
NimBLEClient* s_client      = nullptr;
NimBLERemoteCharacteristic* s_rx_char = nullptr; // the subscribed char (also writable: K1 -> knob)
volatile bool s_linked      = false;
volatile bool s_force_confirm = false;           // push confirmed modes once on (re)link
uint8_t       s_last_pm = 255, s_last_sm = 255;  // last-sent confirmed ordinals (255 = unsent)
volatile bool s_have_target = false;
volatile bool s_scanning    = false;
NimBLEAddress s_target_addr;
portMUX_TYPE  s_target_mux  = portMUX_INITIALIZER_UNLOCKED;

// BLE-MIDI decode: strip [hdr][ts]; walk full-status CC messages (the knob always
// sends one full-status CC per packet). Mirrors the bridge's parse_events().
void decode_and_enqueue(const uint8_t* p, size_t len) {
    if (!s_cmd_queue || len < 3) return;         // [hdr][ts] + >= 1 MIDI byte
    const uint8_t* midi = p + 2;                 // skip header + timestamp
    size_t n = len - 2, i = 0;
    while (i + 3 <= n) {
        uint8_t st = midi[i];
        if ((st & 0xF0) == 0xB0) {               // Control Change
            uint8_t ch = st & 0x0F, cc = midi[i + 1], val = midi[i + 2];
            i += 3;
            RemotedCmd cmd{};
            cmd.channel = (ch == 1) ? 1 : 0;
            if (cc == CC_MODE_STEP) {
                cmd.kind = CmdKind::ModeStep;
                cmd.dir  = (val >= 0x40) ? +1 : -1;
                xQueueSend(s_cmd_queue, &cmd, 0);   // drop if full — never block host task
            } else if (cc == CC_CHAN_SEL) {
                cmd.kind = CmdKind::ChanSel;
                cmd.dir  = 0;
                xQueueSend(s_cmd_queue, &cmd, 0);
            }
        } else {
            i += 1;                              // resync past a stray byte
        }
    }
}

void on_notify(NimBLERemoteCharacteristic*, uint8_t* data, size_t len, bool) {
    decode_and_enqueue(data, len);               // host-task context: decode + enqueue ONLY
}

class ScanCB : public NimBLEScanCallbacks {
    void onResult(const NimBLEAdvertisedDevice* dev) override {
        if (s_have_target || s_linked) return;
        bool match = (dev->getName() == KNOB_NAME) ||
                     (dev->haveServiceUUID() &&
                      dev->isAdvertisingService(NimBLEUUID(BLEMIDI_SERVICE_UUID)));
        if (!match) return;
        portENTER_CRITICAL(&s_target_mux);
        s_target_addr = dev->getAddress();
        s_have_target = true;
        portEXIT_CRITICAL(&s_target_mux);
        NimBLEDevice::getScan()->stop();
        s_scanning = false;
    }
    void onScanEnd(const NimBLEScanResults&, int) override { s_scanning = false; }
};
ScanCB s_scan_cb;

class ClientCB : public NimBLEClientCallbacks {
    void onConnect(NimBLEClient*) override { s_linked = true; }
    void onDisconnect(NimBLEClient*, int) override { s_linked = false; s_have_target = false; s_rx_char = nullptr; }
    void onConnectFail(NimBLEClient*, int) override { s_linked = false; s_have_target = false; s_rx_char = nullptr; }
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
    if (!s_client->connect(addr)) return false;

    NimBLERemoteService* svc = s_client->getService(BLEMIDI_SERVICE_UUID);
    if (!svc) { s_client->disconnect(); return false; }
    NimBLERemoteCharacteristic* chr = svc->getCharacteristic(BLEMIDI_CHAR_UUID);
    if (!chr) { s_client->disconnect(); return false; }
    if (!chr->subscribe(true, on_notify)) { s_client->disconnect(); return false; }
    s_rx_char = chr;            // same characteristic is writable: K1 -> knob confirmed mode
    s_force_confirm = true;     // push current modes once the link is up
    Serial.println("[ble_remoted] linked + subscribed to Remoted dial");
    return true;
}

// Report the K1's CONFIRMED committed modes to the knob over the same BLE-MIDI
// characteristic (the knob shows these as the authoritative on-screen mode). Sends
// only on change (or `force` once per link). Write-no-response → non-blocking.
void send_confirmed_modes(bool force) {
    if (!s_rx_char) return;
    uint8_t pm = sb_k1_confirmed_mode(false);
    uint8_t sm = sb_k1_confirmed_mode(true);
    if (!force && pm == s_last_pm && sm == s_last_sm) return;
    s_last_pm = pm; s_last_sm = sm;
    uint16_t ts = (uint16_t)(millis() & 0x1FFF);
    uint8_t pkt[8] = {
        (uint8_t)(0x80 | ((ts >> 7) & 0x3F)),   // BLE-MIDI header
        (uint8_t)(0x80 | (ts & 0x7F)),          // timestamp
        0xB0, CC_CONFIRM_PRIMARY,   (uint8_t)(pm & 0x7F),
        0xB0, CC_CONFIRM_SECONDARY, (uint8_t)(sm & 0x7F),
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
                if (!s_scanning) { s_scanning = true; scan->start(0, false); }
            } else if (connect_and_subscribe()) {
                s_linked = true;
            } else {
                s_have_target = false;           // connect failed — re-scan next iteration
                vTaskDelay(pdMS_TO_TICKS(800));
            }
        }
        vTaskDelay(pdMS_TO_TICKS(150));           // low-duty orchestration; yields to audio
    }
}

} // namespace

void sb_k1_ble_remoted_begin() {
    s_cmd_queue = xQueueCreate(16, sizeof(RemotedCmd));
    NimBLEDevice::init("K1-Remoted-RX");
    // Low-priority Core-0 task: scan/connect/subscribe off the audio main loop.
    // Stack 4096 words; priority 1 (audio + LED tasks outrank it).
    xTaskCreatePinnedToCore(ble_task, "ble_remoted", 4096, nullptr, 1, &s_task, 0);
    Serial.printf("[ble_remoted] begin (gated A/B build) — free heap=%u\n", ESP.getFreeHeap());
}

void sb_k1_ble_remoted_poll(uint32_t /*now_ms*/) {
    if (!s_cmd_queue) return;
    RemotedCmd cmd;
    // Drain + apply in the MAIN-LOOP context (same as check_serial hotkeys).
    while (xQueueReceive(s_cmd_queue, &cmd, 0) == pdTRUE) {
        secondaryMode = (cmd.channel == 1);      // route to the addressed channel
        if (cmd.kind == CmdKind::ModeStep) {
            serial_adjust_target_mode(cmd.dir);  // serial_menu.h:1010 — arms that channel's mode
        }
        // ChanSel: secondaryMode already set above (matches the bridge's Space toggle).
    }
    // Push the K1's confirmed committed modes back to the knob (on change + on link).
    bool force = s_force_confirm; s_force_confirm = false;
    send_confirmed_modes(force);
}

bool sb_k1_ble_remoted_is_linked() { return s_linked; }

#endif // SB_K1_BLE_REMOTED
