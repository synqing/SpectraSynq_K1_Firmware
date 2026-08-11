#pragma once

/**
 * Named motion durations for the Operator UI (Phase F).
 * Value changes are always 0 ms — an instrument answers instantly.
 * No animation may target width/height/layout — translate and opa only.
 */

#define DECK_MOTION_PRESS_MS         100
/* Sheet/scrim motion retired under PARTIAL — snap opaque reveal (MERGE Task 3.x). */
#define DECK_MOTION_SHEET_MS         0
#define DECK_MOTION_SCRIM_MS         0
#define DECK_MOTION_SHEET_LEGACY_MS  260
#define DECK_MOTION_SCRIM_LEGACY_MS  200
#define DECK_MOTION_CONFIRM_MS       2000
#define DECK_MOTION_CONFIRM_SNAP_MS  200
#define DECK_MOTION_ARM_MS           5000
#define DECK_MOTION_VALUE_MS         0
