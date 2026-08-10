/**
 * Deck16 link/RSSI/status feedback helpers.
 * Honest LINK phase lives in deck_ui.cpp (deck_state_rx_phase).
 */

#include "deck_ui_internal.h"

#include <Arduino.h>

namespace {
bool g_inited = false;
}

void deck_ui_feedback_init(void)
{
  g_inited = true;
}

void deck_ui_feedback_refresh(void)
{
  /* Facade Deck_UI_Tick owns phase / pending / confirmed refresh. */
}

const char* deck_ui_module_marker_feedback(void)
{
  (void)g_inited;
  return "DECK16_MODULE:deck_ui_feedback";
}
