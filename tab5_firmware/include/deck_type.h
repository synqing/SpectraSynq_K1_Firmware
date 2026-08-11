#pragma once
/**
 * deck_type.h — ONLY legal type tokens for deck_ui.
 *
 * Canon:
 *   Countach Bold Italic = hero numerals ONLY (mode / palette %02u indices)
 *   Berkeley Mono        = ALL words (mode/palette names, keys, brand, labels, state)
 *
 * Absolute cuts:
 *   - Never apply Countach to name strings or key caps
 *   - Letter-spacing: only the Countach constants below; Mono = 0
 *
 * Optical ladder (font_ladder_r1 / optical_scale_ladder_r1.json):
 *   Unified hero → DISPLAY_55 (asset retargeted; digit box_h ∈ [36,40] — NOT "55 CSS px")
 *   Instrument % / cal → MONO_55
 *   Names / sheet titles / row labels → MONO_34
 *   Soft keys / sheet values / sheet buttons → MONO_24
 *   Chrome (chevrons, brand, LINK, bus gutters, zone titles) → MONO_21
 *   DISPLAY_40 / DISPLAY_89 → DEPRECATED_DEAD (no live call sites; map to hero face)
 */

#include "fonts/deck_fonts.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Letter-spacing (px). Legal for Countach numerals only. */
#define DECK_LS_COUNTACH_40  0
#define DECK_LS_COUNTACH_55  0
#define DECK_LS_COUNTACH_89  0

typedef enum {
  DECK_TYPE_DISPLAY_89 = 0,   /* DEPRECATED_DEAD — archive only; returns unified hero */
  DECK_TYPE_DISPLAY_55,       /* Unified optical hero — Countach BI; ink band 36–40 */
  DECK_TYPE_DISPLAY_40,       /* DEPRECATED_DEAD — was mode-only shrink; returns unified hero */
  DECK_TYPE_MONO_55,          /* Large instrument values (brightness %, cal digits) */
  DECK_TYPE_MONO_34,          /* Names, sheet titles, row labels, cal state words */
  DECK_TYPE_MONO_24,          /* Soft keys, sheet values, sheet button chrome */
  DECK_TYPE_MONO_21,          /* Zone titles, chevrons, brand/LINK, bus gutters, telemetry */
  DECK_TYPE_COUNT
} DeckTypeToken;

/* Retired tokens kept as aliases so call sites compile during the v7 port. */
#define DECK_TYPE_DISPLAY_34        DECK_TYPE_MONO_34
#define DECK_TYPE_DISPLAY_STATE_34I DECK_TYPE_MONO_34

static inline const lv_font_t* deck_type_font(DeckTypeToken t)
{
  switch (t) {
    case DECK_TYPE_DISPLAY_89: /* DEPRECATED_DEAD */
    case DECK_TYPE_DISPLAY_40: /* DEPRECATED_DEAD */
    case DECK_TYPE_DISPLAY_55: return &countach_bolditalic_55;
    case DECK_TYPE_MONO_55:    return &berkeley_mono_55;
    case DECK_TYPE_MONO_34:    return &berkeley_mono_34;
    case DECK_TYPE_MONO_24:    return &berkeley_mono_24;
    case DECK_TYPE_MONO_21:    return &berkeley_mono_21;
    default:                   return &berkeley_mono_34;
  }
}

/** Letter-spacing for token. Mono always 0; Countach numerals via constants. */
static inline int deck_type_letter_space(DeckTypeToken t)
{
  switch (t) {
    case DECK_TYPE_DISPLAY_40:
      return DECK_LS_COUNTACH_40;
    case DECK_TYPE_DISPLAY_55:
      return DECK_LS_COUNTACH_55;
    case DECK_TYPE_DISPLAY_89:
      return DECK_LS_COUNTACH_89;
    default:
      return 0;
  }
}

#ifdef __cplusplus
}
#endif
