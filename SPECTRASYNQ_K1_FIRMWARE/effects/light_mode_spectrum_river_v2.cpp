#include "lightshow_modes.h"
#include "sb_audio_snapshot.h"

// ============================================================================
// light_mode_spectrum_river_v2 — "Spectrum River 2": the 10/10 Spectrum River,
// now BREATHING.
// ----------------------------------------------------------------------------
// Spectrum River v1 flows outward at a CONSTANT drift. SRv2 keeps the entire
// winning loop byte-for-byte (continuous 80-bin->80-px spectrum, sub-pixel
// draw_sprite outward transport, frequency->palette colour, the 3-filter
// "just-right" responsiveness) and changes ONLY the SCROLL SPEED: the outward
// drift SURGES with bass energy. Result: the colour field rushes outward on the
// drop and eases on breakdowns — but it ALWAYS scrolls/refreshes.
//
// FIX 2026-06-02 (Captain): v2.0 raised trail persistence when quiet, which made
// the strip HOLD — content didn't fade/refresh, so changes looked on/off and
// "mechanical". CONSTANT-SCROLL + CONSTANT-REFRESH is what makes the family feel
// organic (it's why all the reference effects scroll). So: alpha is now CONSTANT
// (== v1's 0.90 — never raised), and the breathing lives ONLY in scroll speed,
// with a high drift FLOOR so it never slows enough to feel like it's holding.
//
// Per the SR decode the load-bearing magic is untouched: injection gain, the 1:1
// spectrum map, freq->palette colour, floor/contrast caps == v1. Tune TRANSPORT,
// not gain or persistence.
//
// State: one per-channel float (fx.river_tide_env) — a slow EMA of low_energy so
// the breathing is organic, never twitchy. History in the passed leds_prev_buffer.
// ============================================================================

static const float   RIVERV2_DRIFT_BASE   = 0.55f; // matches SR v1 base
static const float   RIVERV2_DRIFT_FLOOR  = 0.9f;  // always scroll >= 0.9x base (constant refresh — no holding)
static const float   RIVERV2_DRIFT_SURGE  = 0.9f;  // drift = BASE*(FLOOR + SURGE*tide) => up to ~1.8x on bass
static const float   RIVERV2_ALPHA        = 0.90f; // CONSTANT == SR v1. Raising/holding alpha was the on/off bug.
static const float   RIVERV2_TIDE_EMA     = 0.05f; // slow EMA on bass energy (organic)
static const float   RIVERV2_FLOOR        = 0.015f;
static const float   RIVERV2_INJECT_GAIN  = 0.90f; // == SR v1 (do not raise)
static const uint8_t RIVERV2_MAX_ITERS    = 4;

void light_mode_spectrum_river_v2(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  // Tide envelope: slow EMA of bass energy -> breathing drift (no twitch).
  SBAudioSnapshot snap = sb_audio_snapshot_read();
  float low = snap.low_energy;
  if (!isfinite(low) || low < 0.0f) low = 0.0f;
  if (low > 1.0f) low = 1.0f;
  fx.river_tide_env += (low - fx.river_tide_env) * RIVERV2_TIDE_EMA;
  float tide = fx.river_tide_env;
  if (tide < 0.0f) tide = 0.0f;
  if (tide > 1.0f) tide = 1.0f;

  // 1. Flow OUTWARD — ALWAYS scrolling (constant refresh); drift surges with bass.
  //    Persistence is CONSTANT (== v1) — never raised, so it never "holds".
  const float drift = RIVERV2_DRIFT_BASE * (RIVERV2_DRIFT_FLOOR + RIVERV2_DRIFT_SURGE * tide) * (float(NATIVE_RESOLUTION) / 128.0f);

  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION, drift, SQ15x16(RIVERV2_ALPHA));
  for (uint16_t i = 0; i < HALF; i++) { leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0; }

  // 2. Inject the live spectrum (identical to SR v1: bin k -> pixel HALF+k,
  //    colour by frequency, brightness by contrast-enhanced energy).
  uint8_t iters = (uint8_t)rp->SQUARE_ITER;
  if (iters > RIVERV2_MAX_ITERS) iters = RIVERV2_MAX_ITERS;
  for (uint16_t k = 0; k < NUM_FREQS && k < HALF; k++) {
    float e = float(spectrogram_smooth[k]);
    if (!isfinite(e) || e < 0.0f) e = 0.0f;
    if (e > 1.0f) e = 1.0f;
    for (uint8_t s = 0; s < iters; s++) e *= e;
    if (e < RIVERV2_FLOOR) continue;
    const float hue = float(k) / float(NUM_FREQS - 1);
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(e * RIVERV2_INJECT_GAIN));
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
