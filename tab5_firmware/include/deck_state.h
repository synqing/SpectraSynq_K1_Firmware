#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  DECK_CTRL_PRIMARY_MODE = 0,
  DECK_CTRL_PRIMARY_PALETTE,
  DECK_CTRL_SECONDARY_MODE,
  DECK_CTRL_SECONDARY_PALETTE,
  DECK_CTRL_PRIMARY_PHOTONS,
  DECK_CTRL_SECONDARY_PHOTONS,
  DECK_CTRL_PRIMARY_MOOD,
  DECK_CTRL_SECONDARY_MOOD,
  /* Banned from MAIN glass (dead-on-glass / BANISHED / Tier-2 misplaced).
   * Kept for RX confirm of remaining layout paths only — not Operator MAIN.
   * Mirror IDs purged 2026-08-09 — NEVER reintroduce on BLE/Deck. */
  DECK_CTRL_PRIMARY_CHROMA,
  DECK_CTRL_PRIMARY_SATURATION,
  DECK_CTRL_PRIMARY_PRISM_COUNT,
  DECK_CTRL_SECONDARY_CHROMA,
  DECK_CTRL_SECONDARY_SATURATION,
  DECK_CTRL_SECONDARY_ENABLED,
  DECK_CTRL_COUNT
} DeckControlId;

typedef enum {
  DECK_SHEET_NONE = 0,
  DECK_SHEET_CALIBRATE,
  DECK_SHEET_SENSITIVITY,
  DECK_SHEET_RENDER,
  DECK_SHEET_SMART,
  DECK_SHEET_EDGE,
  DECK_SHEET_DIRECTOR,
  DECK_SHEET_VIVID,
  DECK_SHEET_COUNT
} DeckSheetId;

typedef struct {
  float confirmed;
  float pending;
  bool pending_active;
  bool echo;
} DeckValueF;

typedef struct {
  uint8_t confirmed;
  uint8_t pending;
  bool pending_active;
  bool echo;
} DeckValueU8;

void deck_state_init(void);

void deck_state_set_pending_f(DeckControlId id, float value);
void deck_state_set_pending_u8(DeckControlId id, uint8_t value);

/** Promote pending → confirmed after successful TX. echo=false until return channel.
 *  After Deck16 B2: HARD-GATED — no-op. Confirmed writes go through deck_state_rx only. */
void deck_state_ack_tx(DeckControlId id);

/** Exclusive confirmed writers for deck_state_rx (Phase 5). */
void deck_state_apply_confirmed_f(DeckControlId id, float value);
void deck_state_apply_confirmed_u8(DeckControlId id, uint8_t value);

/** Gap / overflow recovery: confirmed image is incomplete until next snapshot. */
void deck_state_mark_confirmed_stale(void);
void deck_state_clear_confirmed_stale(void);
bool deck_state_confirmed_stale(void);

const DeckValueF* deck_state_get_f(DeckControlId id);
const DeckValueU8* deck_state_get_u8(DeckControlId id);

/** Prefer pending when pending_active (dim affordance); else confirmed. */
float deck_state_display_f(DeckControlId id);
uint8_t deck_state_display_u8(DeckControlId id);

bool deck_state_is_continuous(DeckControlId id);
bool deck_state_is_enum(DeckControlId id);

uint32_t deck_state_last_tx_ms(DeckControlId id);
void deck_state_mark_tx_ms(DeckControlId id, uint32_t now_ms);

bool deck_state_tx_dirty(DeckControlId id);
void deck_state_clear_tx_dirty(DeckControlId id);

uint32_t deck_state_sent_count(void);
uint32_t deck_state_confirmed_count(void);
void deck_state_bump_sent(void);
void deck_state_bump_confirmed(void);

/** Clear all pending_active + gTxDirty without resetting confirmed values.
 *  Called on every disconnect and HELLO to prevent stale pending TX on
 *  re-link.  Tab5 must never push uncommanded values to K1 across sessions. */
void deck_state_clear_pending_all(void);

void deck_state_set_sheet(DeckSheetId sheet);
DeckSheetId deck_state_sheet(void);

uint8_t deck_state_clamp_mode(int value);
uint8_t deck_state_clamp_palette(int value);
float deck_state_clamp_photons(float value);
float deck_state_clamp_unit01(float value);

#ifdef __cplusplus
}
#endif
