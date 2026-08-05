// ble_midi_peripheral.h
// Standard Apple BLE-MIDI PERIPHERAL transport for ESP32-S3 (arduino-ESP32 core 3.x).
// The device advertises a BLE-MIDI service and NOTIFIES MIDI to a connected central
// (e.g. the SpectraSynq K1). Built on NimBLE-Arduino 2.x. Non-blocking; LVGL-loop safe.
//
// Service        : 03B80E5A-EDE8-4B33-A751-6CE34EC4C700
// Characteristic : 7772E5DB-3868-4112-A1A9-F2669D106BF3  (READ|WRITE|WRITE_NR|NOTIFY)
#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Initialise the BLE stack, create the BLE-MIDI service/characteristic and start
// advertising. Call once from setup() (allocation happens here, NOT in the loop).
// device_name: advertised complete local name. NULL/empty -> "SpectraSynq Remoted".
void blemidi_init(const char* device_name);

// True when >=1 central is connected (notifications will be delivered).
bool blemidi_connected(void);

// Wrap a raw MIDI message (status + data bytes) in standard Apple BLE-MIDI framing
// (13-bit millis timestamp -> header byte + timestamp byte) and notify the
// characteristic. No-op if not connected. Non-blocking; safe to call from loop().
// len is clamped to the internal static packet buffer.
void blemidi_send_raw(const uint8_t* midi_bytes, int len);

// Register a handler invoked when the connected central WRITES MIDI to us — the
// return path the K1 uses to report its CONFIRMED light-show mode. `data` is the
// full BLE-MIDI packet ([hdr][ts][MIDI...]); the handler parses it. NULL clears.
void blemidi_set_rx_cb(void (*cb)(const uint8_t* data, int len));

#ifdef __cplusplus
}
#endif
