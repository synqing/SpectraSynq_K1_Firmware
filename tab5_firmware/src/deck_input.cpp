#include "deck_input.h"
#include "deck_tx.h"
#include "deck_names.h"

void deck_input_init(void) {}

static void commit_enum(DeckControlId id)
{
  deck_tx_send(id);
}

void deck_input_set_mode(DeckControlId id, uint8_t program)
{
  if (id != DECK_CTRL_PRIMARY_MODE && id != DECK_CTRL_SECONDARY_MODE) return;
  deck_state_set_pending_u8(id, program);
  commit_enum(id);
}

void deck_input_step_mode(DeckControlId id, int delta)
{
  if (id != DECK_CTRL_PRIMARY_MODE && id != DECK_CTRL_SECONDARY_MODE) return;
  int cur = static_cast<int>(deck_state_display_u8(id));
  const int step = (delta < 0) ? -1 : 1;
  for (int n = 0; n < DECK_MODE_COUNT; ++n) {
    cur += step;
    if (cur < 0) cur = DECK_MODE_COUNT - 1;
    if (cur >= DECK_MODE_COUNT) cur = 0;
    if (deck_mode_is_enabled(static_cast<uint8_t>(cur))) break;
  }
  deck_input_set_mode(id, static_cast<uint8_t>(cur));
}

void deck_input_set_palette(DeckControlId id, uint8_t index)
{
  if (id != DECK_CTRL_PRIMARY_PALETTE && id != DECK_CTRL_SECONDARY_PALETTE) return;
  deck_state_set_pending_u8(id, index);
  commit_enum(id);
}

void deck_input_step_palette(DeckControlId id, int delta)
{
  if (id != DECK_CTRL_PRIMARY_PALETTE && id != DECK_CTRL_SECONDARY_PALETTE) return;
  int cur = static_cast<int>(deck_state_display_u8(id));
  cur += delta;
  if (cur < 0) cur = DECK_PALETTE_COUNT - 1;
  if (cur >= DECK_PALETTE_COUNT) cur = 0;
  deck_input_set_palette(id, static_cast<uint8_t>(cur));
}

void deck_input_set_photons(DeckControlId id, float unit01)
{
  if (id != DECK_CTRL_PRIMARY_PHOTONS && id != DECK_CTRL_SECONDARY_PHOTONS) return;
  deck_state_set_pending_f(id, unit01);
  // Continuous: dirty flag set; deck_tx_tick coalesces ≤30 Hz.
}

void deck_input_set_mood(DeckControlId id, float unit01)
{
  if (id != DECK_CTRL_PRIMARY_MOOD && id != DECK_CTRL_SECONDARY_MOOD) return;
  deck_state_set_pending_f(id, unit01);
}

void deck_input_set_unit01(DeckControlId id, float unit01)
{
  switch (id) {
    case DECK_CTRL_PRIMARY_PHOTONS:
    case DECK_CTRL_SECONDARY_PHOTONS:
      deck_input_set_photons(id, unit01);
      return;
    case DECK_CTRL_PRIMARY_MOOD:
    case DECK_CTRL_SECONDARY_MOOD:
      deck_input_set_mood(id, unit01);
      return;
    /* Dead-on-glass / Tier-2-misplaced — no glass pending→apply (serial map= only). */
    case DECK_CTRL_PRIMARY_CHROMA:
    case DECK_CTRL_PRIMARY_SATURATION:
    case DECK_CTRL_PRIMARY_PRISM_COUNT:
    case DECK_CTRL_SECONDARY_CHROMA:
    case DECK_CTRL_SECONDARY_SATURATION:
      return;
    default:
      return;
  }
}

void deck_input_step_unit01(DeckControlId id, float delta)
{
  float cur = deck_state_display_f(id);
  cur += delta;
  deck_input_set_unit01(id, cur);
  if (deck_state_tx_dirty(id)) {
    (void)deck_tx_send(id);
  }
}

/**
 * Bool setters for remaining glass bools only.
 * Mirror purged from BLE/Deck 2026-08-09 — NEVER reintroduce TX.
 * secondary.enabled is BANISHED (Captain 2026-08-06).
 */
void deck_input_set_bool(DeckControlId id, bool on)
{
  (void)id;
  (void)on;
}

void deck_input_toggle_bool(DeckControlId id)
{
  const uint8_t cur = deck_state_display_u8(id);
  deck_input_set_bool(id, cur == 0);
}

void deck_input_open_sheet(DeckSheetId sheet)
{
  deck_state_set_sheet(sheet);
}

void deck_input_close_sheet(void)
{
  deck_state_set_sheet(DECK_SHEET_NONE);
}
