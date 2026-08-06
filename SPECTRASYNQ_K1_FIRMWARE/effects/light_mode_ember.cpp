#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"

// ============================================================================
// light_mode_ember — "Ember Field": a continuous, breathing field of glowing
// embers.
// ----------------------------------------------------------------------------
// A warm ember that BREATHES with energy: a glowing bloom whose REACH (how far it
// extends from centre toward the edge) and brightness swell with broadband energy
// and whose HUE tracks the music's tonal centre (chromagram centroid). Loud
// passages flood the strip with a bright warm glow; quiet contracts it to a small
// glowing core. The whole field drifts outward and fades, so it is ALWAYS
// scrolling/refreshing. No discrete objects (none of Comet's binding problem).
//
// FIX 2026-06-02 (Captain: v1 "fails — predictable, meaningless motion edge->centre
// that doesn't align with anything"): v1 used a FREE-RUNNING sine shimmer = a
// traveling pattern decoupled from the audio = a screensaver. REMOVED. ALL motion
// is now audio-driven: the bloom's extent/brightness = energy, hue = centroid, and
// the only travel is the constant outward scroll of audio content.
//
// Family: WAVEFORM-lineage history transport (draw_sprite outward) + palette
// colour authority. Centre-origin + mirror-safe. History in leds_prev_buffer.
// (fx.ember_shimmer_phase is now unused — retained for struct stability.)
// ============================================================================

static const float   EMBER_DRIFT_BASE   = 0.45f;  // outward px/frame base (scaled NR/128)
static const float   EMBER_DRIFT_SURGE  = 0.6f;   // + energy*this (faster scroll when loud)
static const float   EMBER_DRIFT_FLOOR  = 0.7f;   // always scroll >= 0.7x base (constant refresh)
static const float   EMBER_ALPHA        = 0.88f;  // CONSTANT — fades as it scrolls (no holding)
static const float   EMBER_FLOOR        = 0.015f;
static const float   EMBER_GAIN         = 0.95f;  // injection brightness
static const float   EMBER_HUE_SPREAD   = 0.18f;  // small centre->edge palette spread atop centroid hue
static const float   EMBER_MIN_REACH    = 4.0f;   // glow keeps a small core even when quiet

void light_mode_ember(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  (void)fx;  // v2 is stateless (shimmer phase removed); fx kept for signature parity
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  K1AudioSnapshot snap = k1_audio_snapshot_read();
  float energy = snap.spectral_energy;
  if (!isfinite(energy) || energy < 0.0f) energy = 0.0f;
  if (energy > 1.0f) energy = 1.0f;

  // Hue tracks the music's tonal centre (warm on bass-heavy, cool on bright).
  const float centroid = chromagram_centroid_hue();

  // 1. Outward flow of the glowing medium — ALWAYS scrolling (constant refresh),
  //    a touch faster when loud. Constant persistence (no holding).
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  const float drift = EMBER_DRIFT_BASE * (EMBER_DRIFT_FLOOR + EMBER_DRIFT_SURGE * energy) * (float(NATIVE_RESOLUTION) / 128.0f);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION, drift, SQ15x16(EMBER_ALPHA));
  for (uint16_t i = 0; i < HALF; i++) { leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0; }

  // 2. Inject the ember bloom: its REACH (extent from centre) and brightness swell
  //    with ENERGY, so the glow expands to flood the strip when loud and contracts
  //    to a small warm core when quiet — all motion audio-driven (no free-running
  //    pattern). Hue = tonal centre + a small centre->edge spread.
  const float reach = EMBER_MIN_REACH + energy * (float(HALF) - EMBER_MIN_REACH);
  for (uint16_t k = 0; k < HALF; k++) {
    if (float(k) > reach) break;                 // glow only extends to `reach`
    const float d = float(k) / reach;            // 0 at core .. 1 at glow edge
    float b = energy * (1.0f - d * d);           // bright core, soft outer edge
    b *= EMBER_GAIN;
    if (b < EMBER_FLOOR) continue;
    const float hue = centroid + d * EMBER_HUE_SPREAD;
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
