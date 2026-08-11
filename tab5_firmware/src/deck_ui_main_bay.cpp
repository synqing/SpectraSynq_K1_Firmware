/**
 * Retired Precision Bay MAIN stub — DEAD / DEPRECATED (Captain 2026-08-09).
 * Operator MAIN is assembled in deck_ui.cpp and binds deck_state + LINK phase.
 * This translation unit remains only so link markers stay stable; do not revive Bay.
 */

#include "deck_ui_internal.h"

void deck_ui_main_bay_build(lv_obj_t* /*screen*/)
{
  /* No Bay chrome. MAIN lives in deck_ui.cpp. */
}

void deck_ui_main_bay_refresh(void)
{
  /* Confirmed/pending refresh is owned by Deck_UI_Tick. */
}

const char* deck_ui_module_marker_main_bay(void)
{
  return "DECK16_RETIRED:deck_ui_main_bay";
}
