// k1_show_state.h
// ============================================================================
// Persist primary + secondary channel presets + EdgeMixer + ENABLE_SECONDARY_LEDS
// to LittleFS (/SHOW_STATE_V1.BIN) for next-boot restore. Lightwave-parity for
// Shift+S ('S'): explicit save only — secondary edits remain RAM-only until 'S'.
// ============================================================================
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "k1_edgemixer.h"
#include "k1_effect_queue.h"

#define K1_SHOW_STATE_FILE "/SHOW_STATE_V1.BIN"
#define K1_SHOW_STATE_MAGIC 0x53534253UL  // 'SBSS' little-endian
#define K1_SHOW_STATE_VERSION 1U

// Packed on-disk / in-RAM snapshot (channel fields mirror K1ChannelPreset).
struct K1ShowState {
  K1ChannelPreset primary;
  K1ChannelPreset secondary;
  K1EdgeMixerConfig edge;
  bool enable_secondary;
};

// Capture live primary + secondary + edge + ENABLE_SECONDARY_LEDS.
K1ShowState k1_show_state_capture_live();

// Apply fields without CONFIG persistence side effects (boot / restore path).
void k1_show_state_apply(const K1ShowState& state);

// Write /SHOW_STATE_V1.BIN and immediately flush primary CONFIG via save_config().
// Returns false if the LittleFS write failed (CONFIG save is still attempted
// only after a successful blob write so a half-written show blob is not paired
// with a fresh CONFIG).
bool k1_show_state_save();

// Load + apply if file is present and valid. Missing/corrupt → no-op, true boot.
// Returns true if a valid blob was applied.
bool k1_show_state_load();

// Buffer codec (host-testable; no filesystem). Returns bytes written / true on OK.
size_t k1_show_state_encode(const K1ShowState& state, uint8_t* out, size_t out_cap);
bool k1_show_state_decode(const uint8_t* data, size_t len, K1ShowState* out);
