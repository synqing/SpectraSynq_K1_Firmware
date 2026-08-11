/**
 * Deck16 shared LVGL component builders (helpers).
 * Selectors/sliders/keys remain in deck_ui.cpp Operator MAIN.
 */

#include "deck_ui_internal.h"

#include <Arduino.h>

namespace {
bool g_inited = false;
}

void deck_ui_components_init(void)
{
  g_inited = true;
}

const char* deck_ui_module_marker_components(void)
{
  (void)g_inited;
  return "DECK16_MODULE:deck_ui_components";
}
