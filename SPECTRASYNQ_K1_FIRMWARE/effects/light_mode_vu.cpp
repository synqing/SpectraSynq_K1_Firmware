#include "lightshow_modes.h"

void light_mode_vu(SQ15x16& level_smooth, SQ15x16& max_level) {
  const RenderParams* rp = active_render_params();
  SQ15x16 mix_amount = mood_scale(0.10, 0.05, rp->MOOD);

  level_smooth = (audio_vu_level_average * mix_amount) + (level_smooth * (1.0 - mix_amount));

  if (level_smooth * 1.1 > max_level) {
    SQ15x16 distance = (level_smooth * 1.1) - max_level;
    max_level += distance * 0.1;
  } else {
    max_level *= 0.9999;
    if (max_level < 0.0025) {
      max_level = 0.0025;
    }
  }

  SQ15x16 bar_level = level_smooth / max_level;
  if (bar_level > 1.0) bar_level = 1.0;
  if (bar_level < 0.0) bar_level = 0.0;

  clear_leds();

  const uint16_t half_res = NATIVE_RESOLUTION / 2;
  const SQ15x16 inv_half = SQ15x16(1.0) / SQ15x16(half_res);
  SQ15x16 brightness = SQ15x16(sqrtf((float)bar_level));

  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = render_params_palette_owns_colour(rp, render_secondary);
  uint8_t palette_to_use = render_params_palette_index(rp, render_secondary);
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);

  for (uint16_t i = 0; i < half_res; i++) {
    SQ15x16 inner = SQ15x16(i) * inv_half;
    SQ15x16 outer = SQ15x16(i + 1) * inv_half;
    SQ15x16 coverage = 0.0;

    if (bar_level >= outer) {
      coverage = 1.0;
    } else if (bar_level > inner) {
      coverage = (bar_level - inner) * SQ15x16(half_res);
    }

    if (coverage <= 0.0) {
      continue;
    }

    SQ15x16 value = brightness * coverage;
    CRGB16 color;
    if (palette_owns_colour) {
      color = palette_manual_colour(pal, inner, value);
    } else {
      SQ15x16 hue = chroma_val + hue_position;
      color = hsv(hue, SQ15x16(rp->SATURATION), value);
    }

    leds_16[half_res + i] = color;
    leds_16[half_res - 1 - i] = color;
  }
}
