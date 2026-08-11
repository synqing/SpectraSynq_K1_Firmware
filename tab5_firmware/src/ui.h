#pragma once
/**
 * ui.h
 * LVGL UI: local deck controls plus compact transport status overlay.
 */
#include <Arduino.h>

namespace UI {

struct Snapshot {
  int   effectIndex = 0;
  float brightness  = 0.5f; // [0..1]
  float p1          = 0.0f; // [0..1]
  float p2          = 0.0f; // [0..1]
  float bpm         = 0.0f; // informative
  int   key         = -1;   // informative (optional)
};

enum class LinkState : uint8_t { Off=0, On=1 }; // reserved for future

// Build UI; must be called after LVGL/display init
void init();

// Per-loop LVGL handler (non-blocking)
void tick();

// Apply latest local/control snapshot
void applySnapshot(const Snapshot& s);

// Overlay state changes. setWifiOnline is a legacy UI slot and is forced off
// while BLE MIDI is the active transport.
void setWifiOnline(bool online);
void setHostOnline(bool online);

// Read back current state used by Input to send deltas
Snapshot getLocal();

} // namespace UI
