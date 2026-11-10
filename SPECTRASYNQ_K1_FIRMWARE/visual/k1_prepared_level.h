#pragma once

// Prepared-show level (K1-FE-SHOW change request R3-2, 10 November 2026).
//
// While a prepared show plays there is no live chroma, so the admitted effects
// (Waveform Hybrid K1, Waveform Tempo) take their colour from the peak-seeded
// fallback: the selected palette sampled at the CHROMA knob, multiplied by the
// show's level. Measured on the emulator at a6bad318, that multiplied the show's
// level by how dark the palette happens to be at that coordinate. The boot
// palette (K1_Naberius_Gold) starts at (2, 0, 20) of 255, so Waveform Tempo
// could never rise above about 8 % of full scale however hard the show drove
// it, and below a level of about 0.26 the product fell under the 0.02 "black
// stop" floor and the effect switched to an HSV colour that is not in the
// palette at all, brighter than the palette colour above it.
//
// Rule for prepared playback only: the palette supplies the hue, the show
// supplies the level. The palette colour is taken at full strength and scaled
// so that its strongest channel equals the requested level. A level of 1.0
// therefore reaches full scale, 0.5 reaches half, on every palette. Live
// (microphone) rendering does not call this.
//
// Returns false, leaving *out alone, when the palette is black at that
// coordinate (no hue to keep); the caller's existing black-stop rule applies.

#include <math.h>

#include "constants.h"

static const float K1_PREPARED_LEVEL_BLACK_STOP = 1.0f / 256.0f;

inline bool k1_prepared_level_colour(const CRGB16& full_strength, float level, CRGB16* out) {
  const float r = float(full_strength.r);
  const float g = float(full_strength.g);
  const float b = float(full_strength.b);
  const float top = fmaxf(fmaxf(r, g), b);
  if (!(top >= K1_PREPARED_LEVEL_BLACK_STOP)) return false;
  if (!(level > 0.0f)) level = 0.0f;
  if (level > 1.0f) level = 1.0f;
  const float k = level / top;
  out->r = SQ15x16(r * k);
  out->g = SQ15x16(g * k);
  out->b = SQ15x16(b * k);
  return true;
}
