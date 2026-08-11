#pragma once

#include <Arduino.h>
#include <stdint.h>
#include <stddef.h>

namespace BleMidiTransport {

static constexpr const char* kServiceUuid = "03B80E5A-EDE8-4B33-A751-6CE34EC4C700";
static constexpr const char* kCharacteristicUuid = "7772E5DB-3868-4112-A1A9-F2669D106BF3";

void init();
void tick();
bool ready();
bool gattAvailable();
/** True while a BLE central is connected to the Tab5 peripheral. */
bool connected();

/** Read loop-owned cached RSSI. Never sends HCI or blocks the UI path. */
bool connectionRssi(int8_t* out_dbm);

uint8_t unitToMidi7(float value);
uint16_t unitToMidi14(float value);

// Channel-aware raw MIDI (ch is 0..15 MIDI channel index).
void sendProgramChange(uint8_t channel, uint8_t program);
void sendControlChange(uint8_t channel, uint8_t controller, uint8_t value);
void sendControlChange14(uint8_t channel, uint8_t cc_msb, uint8_t cc_lsb, uint16_t value14);
void sendNrpn(uint8_t channel, uint16_t param, uint16_t data14);
void sendPitchBend(uint8_t channel, uint16_t value14);

// Encode from docs/protocol/k1-ble-midi-map.json via generated k1_ble_midi_map.h.
bool sendMappedNumber(const char* path, float value);
bool sendMappedBool(const char* path, bool value);
bool sendMappedEnum(const char* path, uint8_t index);
bool sendMappedProgram(const char* path, uint8_t program);
/** NRPN text / command long-tail: local index into entry text slice (0..text_count-1). */
bool sendMappedText(const char* path, uint8_t local_index);

// Convenience Tier-1 deck controls (canonical paths).
void sendPrimaryMode(uint8_t program);
void sendPrimaryPhotons(float unit01);
void sendPrimaryMood(float unit01);
void sendPrimaryPalette(uint8_t paletteIndex);
void sendSecondaryMode(uint8_t program);
void sendSecondaryPhotons(float unit01);
void sendSecondaryMood(float unit01);
void sendSecondaryPalette(uint8_t paletteIndex);

// Calibration.noise.* (map-generated NRPN). clear uses data index 0 → "CONFIRM".
bool sendCalArm();
bool sendCalConfirm();
bool sendCalClear();

// Phase-6 proof harness (backend only; no deck_ui).
bool disconnectCentral();
/** mode: ok | md5 | product | short — mutates identity GATT then disconnects. */
bool setIdentityFault(const char* mode);
void dumpConnPerf();

} // namespace BleMidiTransport
