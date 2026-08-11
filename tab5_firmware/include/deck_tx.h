#pragma once

#include "deck_state.h"
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

void deck_tx_init(void);

/**
 * Send the control's pending (or confirmed if idle) value via BleMidiTransport
 * map paths. On success: bump sent counters only; confirmed via deck_state_rx.
 * Continuous controls should prefer deck_tx_tick coalesce; enums may call directly.
 */
bool deck_tx_send(DeckControlId id);

/** ≤30 Hz coalesce for continuous dirty controls; enums ignored here. */
void deck_tx_tick(uint32_t now_ms);

bool deck_tx_ready(void);

/** Calibration.noise.* NRPN commands via map-generated paths (no raw MIDI in UI). */
bool deck_tx_cal_arm(void);
bool deck_tx_cal_confirm(void);
bool deck_tx_cal_clear(void);

/** Manifest-path TX (no invented CCs). Returns false on map miss / transport fail. */
bool deck_tx_send_bool(const char* path, bool value);
bool deck_tx_send_number(const char* path, float value);
bool deck_tx_send_text(const char* path, uint8_t local_index);

/**
 * Full-map path TX: lookup k1-ble-midi-map entry, send by type, note T0.
 * Requires deck_state_rx ARMED/LIVE. Does not invent CCs.
 * value semantics: float for CC14; 0/1 for bool; index for enum/pc/nrpn-text.
 */
bool deck_tx_send_path(const char* path, float value);

#ifdef __cplusplus
}
#endif
