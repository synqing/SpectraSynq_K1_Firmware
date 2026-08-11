#pragma once
/**
 * Deck font declarations — Countach Bold Italic (hero numerals) + Berkeley Mono (all words).
 * Generated/updated by tools/deck_fonts.sh. Do not hand-edit glyph .c files.
 *
 * LICENCE: Countach assets currently from TRIAL OTFs — bench eval flashes only.
 * After Captain licence lands, re-run deck_fonts.sh against licensed binaries.
 *
 * Canon: Countach Bold Italic = mode/palette index numerals ONLY (unified DISPLAY_55).
 *        Berkeley Mono        = every word (names, labels, keys, brand, state).
 * Optical: --size ≠ ink px; hero digit box_h target [36,40] (see optical_scale_ladder_r1.json).
 */

#include <lvgl.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Live hero numerals — Countach Bold Italic (digits + hyphen + space) */
LV_FONT_DECLARE(countach_bolditalic_55);

/* Instrument / all words — Berkeley Mono ladder 21/24/34/55 */
LV_FONT_DECLARE(berkeley_mono_21);
LV_FONT_DECLARE(berkeley_mono_24);
LV_FONT_DECLARE(berkeley_mono_34);
LV_FONT_DECLARE(berkeley_mono_55);

#ifdef __cplusplus
}
#endif
