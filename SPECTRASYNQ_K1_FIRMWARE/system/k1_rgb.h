#pragma once

#include <cstdint>

// Colour-type seam for the (flag-off) effect framework and any future
// IDF-native P4 compile that must not pull FastLED's RMT engine.
//
// Working canvas for shipping K1 remains CRGB16 in constants.h.
// FastLED CRGB is the v3 8-bit scratch / serializer bucket on Arduino.
// Do not treat CRGB as 16-bit WS2816 domain (ADR-0007).

#include <FastLED.h>
