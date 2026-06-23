#include "lightshow_modes.h"

// ============================================================================
// light_mode_aurora — "Aurora": palette-native flowing colour-in-motion.
// ----------------------------------------------------------------------------
// Design lineage: BLOOM (mode 3) only — history-transport via draw_sprite,
// centre-origin, mirror-safe, per-channel history (leds_prev_buffer).
//
// Distinct from BLOOM via the long-trail FULL-STRIP fill (high alpha + only the
// outermost px softened) — the colour reaches both ends and flows, rather than
// blooming and decaying in the centre quarter.
//
// Colour (2026-06-02 fix v2): uses effect_palette_or_chroma_colour — the SAME
// colour authority as BLOOM, branch-for-branch. The earlier fix called
// palette_chroma_colour directly, but that is the PALETTE-mode engine only; the
// K1 default is chromatic_mode==true with palette mode OFF, so it pinned Aurora
// to one colour and ignored auto-colour-shift. Now Aurora's colour == BLOOM's
// colour in every configuration (palette mode -> palette; chromatic default ->
// note-sum HSV + force_hue(chroma_val + hue_position) auto-shift). Aurora differs
// from BLOOM ONLY in motion (the long full-strip trail), never colour.
// ============================================================================

// --- Tuning constants (hardware-tunable) ---
static const float    AURORA_PROP_BASE   = 0.80f;     // base outward px/frame (fills even at low MOOD)
static const float    AURORA_PROP_MOOD   = 1.20f;     // + this * MOOD
static const float    AURORA_TRAIL_ALPHA = 0.98f;     // long trail => fills full strip
static const uint16_t AURORA_EDGE_FADE   = 6;         // only outer px softened

void light_mode_aurora(CRGB16* leds_prev_buffer) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;

  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

  // 1. Transport: re-inject per-channel history propagated outward, long trail.
  const float prop_scale = float(NATIVE_RESOLUTION) / 128.0f;
  const float propagate  = (AURORA_PROP_BASE + AURORA_PROP_MOOD * float(rp->MOOD)) * prop_scale;
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION, propagate, SQ15x16(AURORA_TRAIL_ALPHA));

  // 2. Colour via the proven BLOOM colour authority (palette mode -> palette;
  //    chromatic default -> note-sum HSV + auto-shift). Full brightness.
  CRGB16 inject = effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0));

  // 3. Stamp the two centre pixels (overwrite => bounded), centre-origin.
  const uint16_t centre_left  = (NATIVE_RESOLUTION / 2) - 1;
  const uint16_t centre_right = NATIVE_RESOLUTION / 2;
  leds_16[centre_left]  = inject;
  leds_16[centre_right] = inject;

  // 4. Snapshot bounded transport history BEFORE display-only edge-fade + mirror.
  finalize_additive_frame(leds_16, leds_prev_buffer, true);

  // 5. Soften only the outermost few px so the strip fills end-to-end.
  for (uint16_t i = 0; i < AURORA_EDGE_FADE; i++) {
    const SQ15x16 fade = SQ15x16(float(i + 1) / float(AURORA_EDGE_FADE + 1));
    leds_16[NATIVE_RESOLUTION - 1 - i].r *= fade;
    leds_16[NATIVE_RESOLUTION - 1 - i].g *= fade;
    leds_16[NATIVE_RESOLUTION - 1 - i].b *= fade;
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }

  // 6. Centre-origin mirror (respects the user MIRROR param).
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
