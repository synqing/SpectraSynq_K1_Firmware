#include "lightshow_modes.h"

void light_mode_bloom(CRGB16* leds_prev_buffer, SQ15x16 shift_multiplier) { // Accept previous buffer as argument
  const RenderParams* rp = active_render_params();
  // Clear output
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

  // Draw previous frame shifted with mood scaling.
  // Shift speed is in *pixels per frame*; the original 0.250..2.000 range was tuned for
  // NATIVE_RESOLUTION=128. Scale by NR/128.0 so the bloom propagates at the same visual
  // speed regardless of strip length (otherwise wider strips look like a static sheet).
  const float bloom_scale = (float(NATIVE_RESOLUTION) / 128.0f) * VP_BLOOM_SHIFT_SCALE;
  SQ15x16 vp_bloom_alpha = SQ15x16(VP_FIX_BLOOM_DECAY ? 0.88f : VP_BLOOM_ALPHA);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION,
              (0.250 + 1.750 * rp->MOOD) * bloom_scale * float(shift_multiplier), vp_bloom_alpha);

  //-------------------------------------------------------
  // Calculate new color input based on chromagram
  CRGB16 sum_color;
  SQ15x16 share = 1 / 6.0; // Normalization factor if summing all 12 bins
  memset(&sum_color, 0, sizeof(CRGB16)); // Initialize sum_color

  // Phase 1 2026-05-20: hoist palette construction OUT of the per-bin loop (was 12x redundant).
  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = render_params_palette_owns_colour(rp, render_secondary);
  uint8_t palette_to_use_bl = render_params_palette_index(rp, render_secondary);
  const CRGBPalette16& pal_bl = cached_gradient_palette(palette_to_use_bl, render_secondary);

  for (uint8_t i = 0; i < 12; i++) {
    float prog = i / 12.0;
    SQ15x16 bin = chromagram_smooth[i];

    CRGB16 add_color;
    if (palette_owns_colour) {
        add_color = {0, 0, 0};
    } else {
         // Bloom Classic: sum every note colour before applying global contrast.
         add_color = hsv(SQ15x16(prog), SQ15x16(rp->SATURATION), bin * bin * share);
    }

    sum_color.r += add_color.r;
    sum_color.g += add_color.g;
    sum_color.b += add_color.b;
  }

  // Clamp color values
  if (sum_color.r > 1.0) { sum_color.r = 1.0; };
  if (sum_color.g > 1.0) { sum_color.g = 1.0; };
  if (sum_color.b > 1.0) { sum_color.b = 1.0; };

  if (!palette_owns_colour) {
    for (uint8_t i = 0; i < rp->SQUARE_ITER; i++) {
      sum_color.r *= sum_color.r;
      sum_color.g *= sum_color.g;
      sum_color.b *= sum_color.b;
    }
  } else {
    sum_color = palette_chroma_colour(pal_bl, SQ15x16(0.0), rp->CHROMA);
  }

  // Apply saturation and hue adjustments (similar to original logic but using fixed point)
  CRGB temp_col_rgb = { uint8_t(sum_color.r * 255), uint8_t(sum_color.g * 255), uint8_t(sum_color.b * 255) };
  if (!palette_owns_colour || (VP_BLOOM_FORCE_SATURATION && !VP_FIX_BLOOM_DECAY)) {
    temp_col_rgb = force_saturation(temp_col_rgb, 255 * rp->SATURATION);
  }

  if (!palette_owns_colour && chromatic_mode == false) {
    SQ15x16 led_hue = chroma_val + hue_position + SQ15x16(0.05);
    temp_col_rgb = force_hue(temp_col_rgb, 255*float(led_hue));
  }

  CRGB16 final_insert_color = { temp_col_rgb.r / 255.0, temp_col_rgb.g / 255.0, temp_col_rgb.b / 255.0 };

  // If in palette mode (non-chromatic), override final_insert_color with the palette sum
  if (palette_owns_colour) {
      // Clamp the summed palette color before assigning
      if (sum_color.r > 1.0) sum_color.r = 1.0; else if (sum_color.r < 0.0) sum_color.r = 0.0;
      if (sum_color.g > 1.0) sum_color.g = 1.0; else if (sum_color.g < 0.0) sum_color.g = 0.0;
      if (sum_color.b > 1.0) sum_color.b = 1.0; else if (sum_color.b < 0.0) sum_color.b = 0.0;
      final_insert_color = sum_color; 
  }

  // Insert the new color at the center of the strip
  uint16_t center_idx1 = (NATIVE_RESOLUTION / 2) - 1;
  uint16_t center_idx2 = NATIVE_RESOLUTION / 2;
  leds_16[center_idx1] = final_insert_color;
  leds_16[center_idx2] = final_insert_color; // Insert in two center pixels for symmetry

  // Snapshot bounded transport history before display-only edge fade and mirror.
  finalize_additive_frame(leds_16, leds_prev_buffer, true);

  //-------------------------------------------------------

  // Apply fade towards the ends of the strip (adjust fade range if needed)
  uint16_t fade_width = NATIVE_RESOLUTION / 4; // Fade over the outer quarters
  for(uint16_t i = 0; i < fade_width; i++) {
    float prog = (float)i / (fade_width - 1);
    SQ15x16 fade_amount = SQ15x16(prog * prog); // Quadratic fade, ensure SQ15x16

    // Fade right end
    leds_16[NATIVE_RESOLUTION - 1 - i].r *= fade_amount;
    leds_16[NATIVE_RESOLUTION - 1 - i].g *= fade_amount;
    leds_16[NATIVE_RESOLUTION - 1 - i].b *= fade_amount;

    // Fade left end
    leds_16[i].r *= fade_amount;
    leds_16[i].g *= fade_amount;
    leds_16[i].b *= fade_amount;
  }

  // Mirroring is implicitly handled by the structure? Or apply explicitly if needed.
  // If the sprite shift + center insert doesn't create symmetry, uncomment:
   mirror_image_downwards(leds_16); // Re-enabled mirroring
}

void light_mode_bloom_fast(CRGB16* leds_prev_buffer) {
  light_mode_bloom(leds_prev_buffer, SQ15x16(2.0));
}
