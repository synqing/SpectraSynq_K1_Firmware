#pragma once
/**
 * net.h
 * BLE MIDI transport facade for deck controls.
 */
#include <Arduino.h>
#include "ui.h"

namespace Net {

// Initialise transport (non-blocking)
void init();

// Per-loop handler (call from loop())
void tick();

// Send control messages to the K1 host
void sendSelectEffect(int effectIndex);
void sendBrightness(float value);        // [0..1]
void sendParam(uint8_t index, float v);  // 1..N, value [0..1]

// Expose link status to UI. wifiOnline() is retained for older UI surfaces.
bool wifiOnline();
bool hostOnline();

} // namespace Net
