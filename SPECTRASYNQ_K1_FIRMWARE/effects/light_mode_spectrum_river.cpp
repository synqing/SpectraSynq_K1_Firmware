#include "lightshow_modes.h"

// ============================================================================
// light_mode_spectrum_river — "Spectrum River": the GDFT spectrum mapped to
// SPACE and flowed outward.
// ----------------------------------------------------------------------------
// The 80 frequency bins map 1:1 onto the 80 pixels of the upper half (bin 0 /
// bass -> centre, bin 79 / treble -> outer edge). Each frame the LIVE spectrum is
// injected at its frequency position (colour from the palette BY FREQUENCY,
// brightness from bin energy) and the whole spectral image is transported
// OUTWARD via draw_sprite, leaving a flowing "river" of spectral history: bass
// wells up at the centre and streams out, treble flickers as filaments at the
// edge. The only mode that renders the spectrum AS space.
//
// Family: WAVEFORM-lineage (leds_16 IS the persisted trail) using BLOOM's
// draw_sprite as the proven outward transport. Colour is palette-native via
// palette_manual_colour (auto-colour-shift phase folded in) — NEVER raw HSV.
// Centre-origin + mirror-safe. Per-channel history lives in the passed
// leds_prev_buffer (channel.history) — no new ChannelEffectState fields, no heap,
// no statics; reads via active_render_params().
//
// Data: spectrogram_smooth[NUM_FREQS] (clamped 0..1, refreshed every render frame
// by get_smooth_spectrogram() in the .ino loop). NUM_FREQS(80) == HALF strip.
// ============================================================================

static const float   RIVER_DRIFT_BASE   = 0.55f;  // outward px/frame (scaled by NR/128)
static const float   RIVER_TRAIL_ALPHA  = 0.90f;  // river persistence as it flows outward
static const float   RIVER_FLOOR        = 0.015f; // skip near-silent bins
static const float   RIVER_INJECT_GAIN  = 0.90f;  // injection cap (additive white-out guard)
static const uint8_t RIVER_MAX_ITERS    = 4;      // contrast cap (rp->SQUARE_ITER can be large)

void light_mode_spectrum_river(CRGB16* leds_prev_buffer) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);

  const uint16_t HALF = NATIVE_RESOLUTION / 2;   // 80

  // 1. Flow: transport the previous river OUTWARD (toward the +end) with decay.
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  const float drift = RIVER_DRIFT_BASE * (float(NATIVE_RESOLUTION) / 128.0f);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION,
              drift, SQ15x16(RIVER_TRAIL_ALPHA));

  // Keep the river in the upper half only (the mirror-authoritative half); clear
  // anything that drifted across the centre so it can't bleed past the origin.
  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0;
  }

  // 2. Inject the live spectrum: bin k -> pixel (HALF + k). Colour from the
  //    palette BY FREQUENCY (bass -> palette start, treble -> palette end;
  //    palette_manual_colour folds in the auto-colour-shift phase), brightness
  //    from the contrast-enhanced bin energy.
  //    Analysis authority: only nyquist-safe bins (ghosts 71–79 retired).
  uint8_t iters = (uint8_t)rp->SQUARE_ITER;
  if (iters > RIVER_MAX_ITERS) iters = RIVER_MAX_ITERS;
  const uint8_t analysis_bins =
      sb_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET);
  const float hue_denom =
      float((analysis_bins > 1) ? (analysis_bins - 1) : 1);
  for (uint16_t k = 0; k < analysis_bins && k < HALF; k++) {
    float e = float(spectrogram_smooth[k]);
    if (!isfinite(e) || e < 0.0f) e = 0.0f;
    if (e > 1.0f) e = 1.0f;
    for (uint8_t s = 0; s < iters; s++) e *= e;     // contrast (square-iter), family convention
    if (e < RIVER_FLOOR) continue;
    const float hue = float(k) / hue_denom;   // frequency -> palette position
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(e * RIVER_INJECT_GAIN));
    const uint16_t idx = HALF + k;
    leds_16[idx].r += col.r;
    leds_16[idx].g += col.g;
    leds_16[idx].b += col.b;
  }

  // 3. Bound additive overflow before it becomes next frame's trail state.
  finalize_additive_frame(leds_16, leds_prev_buffer, true);

  // 4. Centre-origin mirror (upper half -> lower half).
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
