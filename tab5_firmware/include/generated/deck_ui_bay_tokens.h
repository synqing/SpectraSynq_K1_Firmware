/* DEPRECATED — Precision Bay geometry tokens (Captain 2026-08-09).
 * Do not include from Operator MAIN. Archaeology / optical teaching FAIL packs only.
 * Historical source: ui/spec/precision_bay_r1_spec.json
 * Status: DEPRECATED (never product destination).
 */
#ifndef DECK_UI_BAY_TOKENS_H
#define DECK_UI_BAY_TOKENS_H

#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Screen */
#define BAY_SCREEN_W 1280
#define BAY_SCREEN_H 720
#define BAY_TOUCH_MIN_PX 105

/* Major regions */
#define BAY_HEADER_X 0
#define BAY_HEADER_Y 0
#define BAY_HEADER_W 1280
#define BAY_HEADER_H 50

#define BAY_SEC_X 14
#define BAY_SEC_Y 60
#define BAY_SEC_W 1252
#define BAY_SEC_H 244

#define BAY_PRI_X 14
#define BAY_PRI_Y 314
#define BAY_PRI_W 1252
#define BAY_PRI_H 244

#define BAY_DOCK_X 12
#define BAY_DOCK_Y 568
#define BAY_DOCK_W 1256
#define BAY_DOCK_H 140

/* Channel grid tracks (px): RAIL | MODE | PALETTE | MACROS */
#define BAY_TRACK_RAIL_W 122
#define BAY_TRACK_MODE_W 244
#define BAY_TRACK_PALETTE_W 420
#define BAY_TRACK_MACROS_W 466  /* 1252 - (122+244+420) */

/* Mode module */
#define BAY_MODE_TITLE_X 14
#define BAY_MODE_TITLE_Y 13
#define BAY_MODE_NAV_VISUAL_W 44
#define BAY_MODE_NAV_VISUAL_H 126
#define BAY_MODE_NAV_TOP 49
#define BAY_MODE_HERO_NUMERAL_TOP 58
#define BAY_MODE_NAME_TOP 136

/* Palette module — absolute law */
#define BAY_PAL_INDEX_X 56
#define BAY_PAL_INDEX_Y 55
#define BAY_PAL_INDEX_W 90
#define BAY_PAL_NAME_X 166
#define BAY_PAL_NAME_Y 55
#define BAY_PAL_NAME_H 67
#define BAY_PAL_NAME_RIGHT_INSET 42
#define BAY_PAL_STRIP_LEFT 56
#define BAY_PAL_STRIP_RIGHT 42
#define BAY_PAL_STRIP_Y 150
#define BAY_PAL_STRIP_H 38

/* Macro controls */
#define BAY_MACRO_HEADER_INSET_LR 14
#define BAY_MACRO_HEADER_TOP 12
#define BAY_MACRO_TRACK_INSET_LR 14
#define BAY_MACRO_TRACK_TOP 51
#define BAY_MACRO_TRACK_VISUAL_H 36
#define BAY_MACRO_THUMB_W 24
#define BAY_MACRO_THUMB_H 52

/* Soft-key dock */
#define BAY_SOFT_KEY_COUNT 7
#define BAY_SOFT_KEY_EQUAL_COL_W 179  /* floor(1256/7); equal columns preferred */
#define BAY_SOFT_KEY_ANNUNCIATOR_SLOT_W 16
#define BAY_SOFT_KEY_ANNUNCIATOR_SLOT_H 16
#define BAY_SOFT_KEY_LAMP_W 13
#define BAY_SOFT_KEY_LAMP_H 13

/* Animation (ms) */
#define BAY_ANIM_PENDING_PULSE_MS 120
#define BAY_ANIM_SHEET_OPEN_MS 160
#define BAY_ANIM_SHEET_CLOSE_MS 120

/* Spec provenance (UTF-8 hex digests of authority files at G1 freeze) */
#define BAY_SPEC_SHA256_HEX \
  "72ba513f8baf17625e7ae7e5da9b2191a11c8b4eef7bb09207b7b16941ca135e"
#define BAY_MAP_SHA256_HEX \
  "2bdadaf8e8cb51c09b10e810b5dc068cdb198d7da655bf534ff9e1426e3bc86a"
#define BAY_MANIFEST_SHA256_HEX \
  "5e3f9dcbba48a70218353ecd96761af353aba3b9ceabf3f172d6683fabec89c6"

#ifdef __cplusplus
}
#endif

#endif /* DECK_UI_BAY_TOKENS_H */
