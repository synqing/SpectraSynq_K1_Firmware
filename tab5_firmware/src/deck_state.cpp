#include "deck_state.h"
#include "deck_names.h"

#include <math.h>

static DeckValueU8 gU8[DECK_CTRL_COUNT];
static DeckValueF gF[DECK_CTRL_COUNT];
static uint32_t gLastTxMs[DECK_CTRL_COUNT];
static bool gTxDirty[DECK_CTRL_COUNT];
static uint32_t gSentCount = 0;
static uint32_t gConfirmedCount = 0;
static DeckSheetId gSheet = DECK_SHEET_NONE;
static bool gConfirmedStale = false;

static bool is_u8(DeckControlId id)
{
  switch (id) {
    case DECK_CTRL_PRIMARY_MODE:
    case DECK_CTRL_PRIMARY_PALETTE:
    case DECK_CTRL_SECONDARY_MODE:
    case DECK_CTRL_SECONDARY_PALETTE:
    case DECK_CTRL_SECONDARY_ENABLED:
      return true;
    default:
      return false;
  }
}

void deck_state_init(void)
{
  for (int i = 0; i < DECK_CTRL_COUNT; ++i) {
    gU8[i] = {0, 0, false, false};
    gF[i] = {0.0f, 0.0f, false, false};
    gLastTxMs[i] = 0;
    gTxDirty[i] = false;
  }

  gF[DECK_CTRL_PRIMARY_PHOTONS].confirmed = 0.78f;
  gF[DECK_CTRL_PRIMARY_PHOTONS].pending = 0.78f;
  gF[DECK_CTRL_SECONDARY_PHOTONS].confirmed = 0.62f;
  gF[DECK_CTRL_SECONDARY_PHOTONS].pending = 0.62f;
  gF[DECK_CTRL_PRIMARY_MOOD].confirmed = 0.40f;
  gF[DECK_CTRL_PRIMARY_MOOD].pending = 0.40f;
  gF[DECK_CTRL_SECONDARY_MOOD].confirmed = 0.55f;
  gF[DECK_CTRL_SECONDARY_MOOD].pending = 0.55f;

  gU8[DECK_CTRL_PRIMARY_MODE].confirmed = 16;
  gU8[DECK_CTRL_PRIMARY_MODE].pending = 16;
  gU8[DECK_CTRL_SECONDARY_MODE].confirmed = 16;
  gU8[DECK_CTRL_SECONDARY_MODE].pending = 16;
  gU8[DECK_CTRL_PRIMARY_PALETTE].confirmed = 40;
  gU8[DECK_CTRL_PRIMARY_PALETTE].pending = 40;
  gU8[DECK_CTRL_SECONDARY_PALETTE].confirmed = 7;
  gU8[DECK_CTRL_SECONDARY_PALETTE].pending = 7;

  /* Layout v1 extras — defaults until K1 snapshot overwrites confirmed. */
  gF[DECK_CTRL_PRIMARY_CHROMA].confirmed = 0.50f;
  gF[DECK_CTRL_PRIMARY_CHROMA].pending = 0.50f;
  gF[DECK_CTRL_PRIMARY_SATURATION].confirmed = 0.70f;
  gF[DECK_CTRL_PRIMARY_SATURATION].pending = 0.70f;
  /* Default OFF — never boot-seed a look that can resurrect on first P8 touch
   * before/without a fresh K1 snapshot (2026-08-09 primary bulb/prism kill). */
  gF[DECK_CTRL_PRIMARY_PRISM_COUNT].confirmed = 0.0f;
  gF[DECK_CTRL_PRIMARY_PRISM_COUNT].pending = 0.0f;
  gF[DECK_CTRL_SECONDARY_CHROMA].confirmed = 0.50f;
  gF[DECK_CTRL_SECONDARY_CHROMA].pending = 0.50f;
  gF[DECK_CTRL_SECONDARY_SATURATION].confirmed = 0.70f;
  gF[DECK_CTRL_SECONDARY_SATURATION].pending = 0.70f;
  gU8[DECK_CTRL_SECONDARY_ENABLED].confirmed = 1;
  gU8[DECK_CTRL_SECONDARY_ENABLED].pending = 1;

  gSentCount = 0;
  gConfirmedCount = 0;
  gSheet = DECK_SHEET_NONE;
  gConfirmedStale = false;
}

void deck_state_clear_pending_all(void)
{
  for (int i = 0; i < DECK_CTRL_COUNT; ++i) {
    gF[i].pending_active = false;
    gU8[i].pending_active = false;
    gTxDirty[i] = false;
  }
}

void deck_state_mark_confirmed_stale(void) { gConfirmedStale = true; }
void deck_state_clear_confirmed_stale(void) { gConfirmedStale = false; }
bool deck_state_confirmed_stale(void) { return gConfirmedStale; }

uint8_t deck_state_clamp_mode(int value)
{
  if (value < 0) return 0;
  if (value >= DECK_MODE_COUNT) return DECK_MODE_COUNT - 1;
  return static_cast<uint8_t>(value);
}

uint8_t deck_state_clamp_palette(int value)
{
  if (value < 0) return 0;
  if (value >= DECK_PALETTE_COUNT) return DECK_PALETTE_COUNT - 1;
  return static_cast<uint8_t>(value);
}

float deck_state_clamp_photons(float value)
{
  if (value < 0.05f) return 0.05f;
  if (value > 1.0f) return 1.0f;
  return value;
}

float deck_state_clamp_unit01(float value)
{
  if (value < 0.0f) return 0.0f;
  if (value > 1.0f) return 1.0f;
  return value;
}

void deck_state_set_pending_f(DeckControlId id, float value)
{
  if (id < 0 || id >= DECK_CTRL_COUNT || is_u8(id)) return;
  if (id == DECK_CTRL_PRIMARY_PHOTONS || id == DECK_CTRL_SECONDARY_PHOTONS) {
    value = deck_state_clamp_photons(value);
  } else if (id == DECK_CTRL_PRIMARY_PRISM_COUNT) {
    if (value < 0.0f) value = 0.0f;
    if (value > 8.0f) value = 8.0f;
  } else {
    value = deck_state_clamp_unit01(value);
  }
  gF[id].pending = value;
  gF[id].pending_active = true;
  gTxDirty[id] = true;
}

void deck_state_set_pending_u8(DeckControlId id, uint8_t value)
{
  if (id < 0 || id >= DECK_CTRL_COUNT || !is_u8(id)) return;
  if (id == DECK_CTRL_PRIMARY_MODE || id == DECK_CTRL_SECONDARY_MODE) {
    value = deck_state_clamp_mode(value);
  } else if (id == DECK_CTRL_PRIMARY_PALETTE || id == DECK_CTRL_SECONDARY_PALETTE) {
    value = deck_state_clamp_palette(value);
  } else {
    value = value ? 1 : 0;
  }
  gU8[id].pending = value;
  gU8[id].pending_active = true;
  gTxDirty[id] = true;
}

void deck_state_ack_tx(DeckControlId id)
{
  (void)id;
  /* Phase 5: optimistic TX confirm removed. Exclusive writer = deck_state_rx. */
}

void deck_state_apply_confirmed_f(DeckControlId id, float value)
{
  if (id < 0 || id >= DECK_CTRL_COUNT || is_u8(id)) return;
  if (id == DECK_CTRL_PRIMARY_PHOTONS || id == DECK_CTRL_SECONDARY_PHOTONS) {
    value = deck_state_clamp_photons(value);
  } else if (id == DECK_CTRL_PRIMARY_PRISM_COUNT) {
    if (value < 0.0f) value = 0.0f;
    if (value > 8.0f) value = 8.0f;
  } else {
    value = deck_state_clamp_unit01(value);
  }
  gF[id].confirmed = value;
  if (gF[id].pending_active) {
    // Clear pending only when confirmed catches the pending request.
    const float d = gF[id].pending - value;
    const float tol = (id == DECK_CTRL_PRIMARY_PRISM_COUNT) ? 0.05f : 0.02f;
    if (d > -tol && d < tol) {
      gF[id].pending_active = false;
      gTxDirty[id] = false;
    }
  }
  gF[id].echo = true;
  ++gConfirmedCount;
}

void deck_state_apply_confirmed_u8(DeckControlId id, uint8_t value)
{
  if (id < 0 || id >= DECK_CTRL_COUNT || !is_u8(id)) return;
  if (id == DECK_CTRL_PRIMARY_MODE || id == DECK_CTRL_SECONDARY_MODE) {
    value = deck_state_clamp_mode(value);
  } else if (id == DECK_CTRL_PRIMARY_PALETTE || id == DECK_CTRL_SECONDARY_PALETTE) {
    value = deck_state_clamp_palette(value);
  } else {
    value = value ? 1 : 0;
  }
  gU8[id].confirmed = value;
  if (gU8[id].pending_active && gU8[id].pending == value) {
    gU8[id].pending_active = false;
    gTxDirty[id] = false;
  }
  gU8[id].echo = true;
  ++gConfirmedCount;
}

const DeckValueF* deck_state_get_f(DeckControlId id)
{
  if (id < 0 || id >= DECK_CTRL_COUNT || is_u8(id)) return nullptr;
  return &gF[id];
}

const DeckValueU8* deck_state_get_u8(DeckControlId id)
{
  if (id < 0 || id >= DECK_CTRL_COUNT || !is_u8(id)) return nullptr;
  return &gU8[id];
}

float deck_state_display_f(DeckControlId id)
{
  const DeckValueF* v = deck_state_get_f(id);
  if (!v) return 0.0f;
  return v->pending_active ? v->pending : v->confirmed;
}

uint8_t deck_state_display_u8(DeckControlId id)
{
  const DeckValueU8* v = deck_state_get_u8(id);
  if (!v) return 0;
  return v->pending_active ? v->pending : v->confirmed;
}

bool deck_state_is_continuous(DeckControlId id)
{
  switch (id) {
    case DECK_CTRL_PRIMARY_PHOTONS:
    case DECK_CTRL_SECONDARY_PHOTONS:
    case DECK_CTRL_PRIMARY_MOOD:
    case DECK_CTRL_SECONDARY_MOOD:
    case DECK_CTRL_PRIMARY_CHROMA:
    case DECK_CTRL_PRIMARY_SATURATION:
    case DECK_CTRL_PRIMARY_PRISM_COUNT:
    case DECK_CTRL_SECONDARY_CHROMA:
    case DECK_CTRL_SECONDARY_SATURATION:
      return true;
    default:
      return false;
  }
}

bool deck_state_is_enum(DeckControlId id)
{
  return id == DECK_CTRL_PRIMARY_MODE || id == DECK_CTRL_PRIMARY_PALETTE ||
         id == DECK_CTRL_SECONDARY_MODE || id == DECK_CTRL_SECONDARY_PALETTE;
}

uint32_t deck_state_last_tx_ms(DeckControlId id)
{
  if (id < 0 || id >= DECK_CTRL_COUNT) return 0;
  return gLastTxMs[id];
}

void deck_state_mark_tx_ms(DeckControlId id, uint32_t now_ms)
{
  if (id < 0 || id >= DECK_CTRL_COUNT) return;
  gLastTxMs[id] = now_ms;
}

bool deck_state_tx_dirty(DeckControlId id)
{
  if (id < 0 || id >= DECK_CTRL_COUNT) return false;
  return gTxDirty[id];
}

void deck_state_clear_tx_dirty(DeckControlId id)
{
  if (id < 0 || id >= DECK_CTRL_COUNT) return;
  gTxDirty[id] = false;
}

uint32_t deck_state_sent_count(void) { return gSentCount; }
uint32_t deck_state_confirmed_count(void) { return gConfirmedCount; }
void deck_state_bump_sent(void) { ++gSentCount; }
void deck_state_bump_confirmed(void) { ++gConfirmedCount; }

void deck_state_set_sheet(DeckSheetId sheet) { gSheet = sheet; }
DeckSheetId deck_state_sheet(void) { return gSheet; }
