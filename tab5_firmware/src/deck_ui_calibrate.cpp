/**
 * Deck16 CALIBRATE sheet helper stub.
 * Live calibrate UI remains in deck_ui.cpp until a clean module move.
 */

#include "deck_ui_internal.h"

#include <Arduino.h>

namespace {
bool g_built = false;
}

void deck_ui_calibrate_build(lv_obj_t* /*screen*/)
{
  g_built = true;
}

const char* deck_ui_module_marker_calibrate(void)
{
  (void)g_built;
  return "DECK16_MODULE:deck_ui_calibrate";
}
