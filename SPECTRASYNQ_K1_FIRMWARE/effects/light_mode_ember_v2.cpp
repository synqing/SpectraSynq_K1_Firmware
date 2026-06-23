#include "lightshow_modes.h"
#include "sb_audio_snapshot.h"

// ============================================================================
// light_mode_ember_v2 — "Ember Field 2": the full-strip sibling of Ember.
// ----------------------------------------------------------------------------
// Ember v1 (mode 16) is a centre-anchored energy CORE — its glow reach contracts
// to the middle ~40-60 LEDs at moderate energy (Captain: that "serves a purpose
// which isn't bad", so v1 is kept as-is). Ember v2 is the FULL-STRIP counterpart:
// the glowing medium fills the ENTIRE strip and breathes with energy across its
// whole length (brightens loud, dims quiet) rather than expanding/contracting from
// the centre. A broad ambient colour wash vs v1's focused core.
//
// Same organic law as the family: CONSTANT outward scroll (always refreshing) +
// ALL motion audio-driven. Speed is driven by the MOOD knob (universal motion
// control). Colour: full palette gradient across the strip (centre warm -> edge
// cool) atop the tonal-centre hue. Palette-native, centre-origin, mirror-safe.
// History in the passed leds_prev_buffer. (fx unused — signature parity.)
// ============================================================================

static const float   EMBERV2_DRIFT_MIN    = 0.40f; // px/frame at MOOD=0 (scaled NR/128)
static const float   EMBERV2_DRIFT_MOOD   = 1.60f; // + MOOD * this  (MOOD knob sets scroll speed)
static const float   EMBERV2_DRIFT_SURGE  = 0.50f; // + energy * this (a touch faster when loud)
static const float   EMBERV2_ALPHA        = 0.88f; // CONSTANT — fades as it scrolls (no holding)
static const float   EMBERV2_FLOOR        = 0.015f;
static const float   EMBERV2_GAIN         = 0.85f; // injection brightness (full-strip => keep moderate)
static const float   EMBERV2_CENTRE_BIAS  = 0.30f; // mild centre-bright falloff (still reaches the edge)
static const float   EMBERV2_HUE_SPREAD   = 0.55f; // wide centre->edge palette spread (full-strip colour)

void light_mode_ember_v2(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  (void)fx;  // stateless; fx kept for signature parity
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  SBAudioSnapshot snap = sb_audio_snapshot_read();
  float energy = snap.spectral_energy;
  if (!isfinite(energy) || energy < 0.0f) energy = 0.0f;
  if (energy > 1.0f) energy = 1.0f;

  const float centroid = chromagram_centroid_hue();

  // 1. Outward flow — speed from the MOOD knob (+ a small energy surge). Always
  //    scrolling/refreshing; constant persistence (no holding).
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  const float drift = (EMBERV2_DRIFT_MIN + EMBERV2_DRIFT_MOOD * float(rp->MOOD)
                       + EMBERV2_DRIFT_SURGE * energy) * (float(NATIVE_RESOLUTION) / 128.0f);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION, drift, SQ15x16(EMBERV2_ALPHA));
  for (uint16_t i = 0; i < HALF; i++) { leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0; }

  // 2. Inject a FULL-STRIP glow: the whole upper half is lit, brightness = energy
  //    with a mild centre bias (but always reaching the edge), hue swept across the
  //    palette centre->edge atop the tonal-centre hue.
  for (uint16_t k = 0; k < HALF; k++) {
    const float pos = float(k) / float(HALF - 1);     // 0 centre .. 1 edge
    float b = energy * (1.0f - EMBERV2_CENTRE_BIAS * pos);
    b *= EMBERV2_GAIN;
    if (b < EMBERV2_FLOOR) continue;
    const float hue = centroid + pos * EMBERV2_HUE_SPREAD;
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(b));
    const uint16_t idx = HALF + k;
    leds_16[idx].r += col.r;
    leds_16[idx].g += col.g;
    leds_16[idx].b += col.b;
  }

  // 3. Bound additive overflow before it becomes next frame's flow.
  finalize_additive_frame(leds_16, leds_prev_buffer, true);

  // 4. Mirror.
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
