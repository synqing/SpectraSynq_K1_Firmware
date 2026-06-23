#include "lightshow_modes.h"

void light_mode_waveform(CRGB16* leds_previous, CRGB16& last_color, float& waveform_peak_scaled_last,
                         float& shift_accum, uint32_t& last_frame_ms) {
  const RenderParams* rp = active_render_params();
  (void)leds_previous;
  (void)shift_accum;
  (void)last_frame_ms;
  SQ15x16 smoothed_peak_fixed = SQ15x16(waveform_peak_scaled) * 0.08 + SQ15x16(waveform_peak_scaled_last) * 0.92;
  waveform_peak_scaled_last = float(smoothed_peak_fixed);

  CRGB16 current_sum_color = {0,0,0};
  SQ15x16 total_magnitude = 0.0;
  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = render_params_palette_owns_colour(rp, render_secondary);
  uint8_t palette_to_use = render_params_palette_index(rp, render_secondary);
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);

  for (uint8_t c = 0; c < 12; c++) {
    float prog = c / 12.0f;
    float bin = float(chromagram_smooth[c]);

    float bright = bin;
    for (uint8_t s = 0; s < int(rp->SQUARE_ITER); s++) {
      bright *= bright;
    }
    float fract_iter = rp->SQUARE_ITER - floor(rp->SQUARE_ITER);
    if (fract_iter > 0.01) {
      float squared = bright * bright;
      bright = bright * (1.0f - fract_iter) + squared * fract_iter;
    }

    if (bright > 0.05) {
      CRGB16 note_col;
      if (palette_owns_colour) {
        note_col = {0, 0, 0};
      } else {
        note_col = hsv(SQ15x16(prog), SQ15x16(rp->SATURATION), SQ15x16(bright));
      }
      if (!palette_owns_colour) {
        current_sum_color.r += note_col.r;
        current_sum_color.g += note_col.g;
        current_sum_color.b += note_col.b;
      }
      total_magnitude += bright;
    }
  }

  if (total_magnitude < 0.01 && audio_vu_level > 0.02) {
    float failsafe_bright = float(audio_vu_level);
    SQ15x16 fallback_hue = SQ15x16(rp->CHROMA) + hue_position;
    if (fallback_hue > SQ15x16(1.0)) fallback_hue -= SQ15x16(1.0);

    current_sum_color = hsv(fallback_hue, SQ15x16(rp->SATURATION), SQ15x16(failsafe_bright));
    total_magnitude = SQ15x16(failsafe_bright);
  }

  if (palette_owns_colour && total_magnitude > 0.01) {
    current_sum_color = palette_chroma_colour(pal, clamp01_fixed(total_magnitude), rp->CHROMA);
  } else if (chromatic_mode == true && total_magnitude > 0.01) {
    SQ15x16 colour_level = clamp01_fixed(total_magnitude);
    current_sum_color.r = (current_sum_color.r / total_magnitude) * colour_level;
    current_sum_color.g = (current_sum_color.g / total_magnitude) * colour_level;
    current_sum_color.b = (current_sum_color.b / total_magnitude) * colour_level;
  } else if (chromatic_mode == false) {
    current_sum_color = hsv(chroma_val + hue_position, SQ15x16(rp->SATURATION), total_magnitude);
  }

  current_sum_color.r *= rp->PHOTONS;
  current_sum_color.g *= rp->PHOTONS;
  current_sum_color.b *= rp->PHOTONS;
  last_color = clamp_crgb16(current_sum_color);

  float abs_amp = fabsf(waveform_peak_scaled);
  if (abs_amp > 1.0f) abs_amp = 1.0f;
  SQ15x16 dynamic_fade_amount = SQ15x16(1.0f - (0.10f * abs_amp));

  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= dynamic_fade_amount;
    leds_16[i].g *= dynamic_fade_amount;
    leds_16[i].b *= dynamic_fade_amount;
  }

  float amp = waveform_peak_scaled_last;
  if (fabsf(amp) < 0.05f) {
    amp = 0.0f;
  }

  float safe_sensitivity = (rp->SENSITIVITY < 0.01f) ? 0.01f : rp->SENSITIVITY;
  amp *= 0.7f / safe_sensitivity;

  if (rp->MIRROR_ENABLED) {
    waveform_shift_upper_half_up(leds_16, 1);
  } else {
    shift_leds_up(leds_16, 1);
  }

  uint16_t pos = rp->MIRROR_ENABLED
    ? waveform_upper_half_source_position(amp)
    : waveform_full_strip_position(amp);
  leds_16[pos] = last_color;

  if (rp->MIRROR_ENABLED) {
    // Upper half is the intentional source trace; mirror only after constraining the dot there.
    mirror_image_downwards(leds_16);
  }
}
