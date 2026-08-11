#pragma once

#include "deck_state.h"
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Thin mutation API shared by touch (deck_ui) and serial/test hooks.
 * Sets pending in deck_state and requests TX (immediate for enums, coalesced
 * for continuous via dirty flag + deck_tx_tick).
 */

void deck_input_init(void);

void deck_input_set_mode(DeckControlId id, uint8_t program);
void deck_input_step_mode(DeckControlId id, int delta);

void deck_input_set_palette(DeckControlId id, uint8_t index);
void deck_input_step_palette(DeckControlId id, int delta);

void deck_input_set_photons(DeckControlId id, float unit01);
void deck_input_set_mood(DeckControlId id, float unit01);

/**
 * Continuous unit01 — MAIN glass allows photons/mood only.
 * chroma / saturation / prism_count are rejected here (dead-on-glass / not MAIN).
 */
void deck_input_set_unit01(DeckControlId id, float unit01);
void deck_input_step_unit01(DeckControlId id, float delta);

/**
 * Boolean glass controls — no-op.
 * Mirror purged from BLE/Deck 2026-08-09 — NEVER reintroduce.
 * secondary.enabled is BANISHED (Captain 2026-08-06).
 */
void deck_input_set_bool(DeckControlId id, bool on);
void deck_input_toggle_bool(DeckControlId id);

void deck_input_open_sheet(DeckSheetId sheet);
void deck_input_close_sheet(void);

#ifdef __cplusplus
}
#endif
