// ble_midi_peripheral.cpp
// NimBLE-Arduino 2.x implementation of a standard Apple BLE-MIDI peripheral.
//
// NimBLE-Arduino 2.x notes (vs 1.x):
//  - Properties use NIMBLE_PROPERTY::* flags (unchanged from 1.x).
//  - Advertising: enableScanResponse(bool) REPLACES 1.x setScanResponse(bool);
//    setName(...) + addServiceUUID(...) are the canonical 2.x server-example calls.
//  - We deliberately avoid NimBLEServerCallbacks so we do NOT depend on the 2.x
//    onConnect/onDisconnect(NimBLEConnInfo&, int reason) signature change. Connection
//    state is read via NimBLEServer::getConnectedCount() (stable across 1.x/2.x), and
//    re-advertising on disconnect is handled by advertiseOnDisconnect(true) (default).
#include "ble_midi_peripheral.h"

#include <Arduino.h>
#include <NimBLEDevice.h>

// ---- Standard Apple BLE-MIDI UUIDs (same as the SMC-Mixer BLE-MIDI contract) ----
#define BLEMIDI_SERVICE_UUID "03B80E5A-EDE8-4B33-A751-6CE34EC4C700"
#define BLEMIDI_CHAR_UUID    "7772E5DB-3868-4112-A1A9-F2669D106BF3"
#define BLEMIDI_DEFAULT_NAME "SpectraSynq Remoted"

// Static, zero-heap-in-loop packet buffer: 2 framing bytes + MIDI payload.
#define BLEMIDI_MAX_MIDI   245
#define BLEMIDI_MAX_PACKET (2 + BLEMIDI_MAX_MIDI)

static NimBLEServer*         s_server = nullptr;
static NimBLECharacteristic* s_char   = nullptr;
static uint8_t               s_packet[BLEMIDI_MAX_PACKET];

// Return path: the connected central (the K1) WRITES MIDI to us to report its
// confirmed light-show mode. We forward the raw BLE-MIDI packet to the registered
// handler (parsed in remoted_control); the peripheral stays protocol-agnostic.
static void (*s_rx_cb)(const uint8_t*, int) = nullptr;

class BleMidiRxCallbacks : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic* c, NimBLEConnInfo&) override {
        if (!s_rx_cb) return;
        NimBLEAttValue v = c->getValue();   // public accessor (returns the written bytes)
        s_rx_cb(v.data(), (int)v.length());
    }
};
static BleMidiRxCallbacks s_rx_callbacks;

void blemidi_init(const char* device_name) {
    const char* name = (device_name && device_name[0]) ? device_name : BLEMIDI_DEFAULT_NAME;

    NimBLEDevice::init(name);

    s_server = NimBLEDevice::createServer();
    s_server->advertiseOnDisconnect(true);  // auto re-advertise when a central drops

    NimBLEService* service = s_server->createService(BLEMIDI_SERVICE_UUID);

    s_char = service->createCharacteristic(
        BLEMIDI_CHAR_UUID,
        NIMBLE_PROPERTY::READ |
        NIMBLE_PROPERTY::WRITE |
        NIMBLE_PROPERTY::WRITE_NR |
        NIMBLE_PROPERTY::NOTIFY);

    s_char->setCallbacks(&s_rx_callbacks);   // receive the K1's confirmed-mode writes

    service->start();

    NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
    adv->setName(name);
    adv->addServiceUUID(BLEMIDI_SERVICE_UUID);
    adv->enableScanResponse(true);  // name does not fit beside a 128-bit UUID in 31B
    adv->start();
}

bool blemidi_connected(void) {
    return s_server != nullptr && s_server->getConnectedCount() > 0;
}

void blemidi_send_raw(const uint8_t* midi_bytes, int len) {
    if (!midi_bytes || len <= 0) return;
    if (s_char == nullptr || !blemidi_connected()) return;

    if (len > BLEMIDI_MAX_MIDI) len = BLEMIDI_MAX_MIDI;

    // 13-bit timestamp from millis(): header carries the high 6 bits, the timestamp
    // byte carries the low 7 bits; both have bit7 set (BLE-MIDI running status spec).
    uint16_t ts = (uint16_t)(millis() & 0x1FFF);
    s_packet[0] = (uint8_t)(0x80 | ((ts >> 7) & 0x3F));  // header byte
    s_packet[1] = (uint8_t)(0x80 | (ts & 0x7F));         // timestamp byte

    for (int i = 0; i < len; i++) {
        s_packet[2 + i] = midi_bytes[i];
    }

    s_char->setValue(s_packet, (size_t)(2 + len));
    s_char->notify();  // queues to the NimBLE host task; does not block the caller
}

void blemidi_set_rx_cb(void (*cb)(const uint8_t*, int)) { s_rx_cb = cb; }
