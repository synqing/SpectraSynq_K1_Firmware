#include "lightshow_modes.h"

static const float WAVEFORM_HYBRID_FALLBACK_PALETTE_OFFSET = 0.22f;

void light_mode_waveform_hybrid(CRGB16* leds_previous, CRGB16& last_color, float& waveform_peak_scaled_last,
                                float& shift_accum, uint32_t& last_frame_ms) {
  const RenderParams* rp = active_render_params();
  const float led_share = 1.0f / 12.0f;
  uint32_t now_ms = millis();
  float dt = 1.0f / 120.0f;
  if (last_frame_ms != 0) {
    uint32_t elapsed_ms = now_ms - last_frame_ms;
    if (elapsed_ms > 0) {
      dt = float(elapsed_ms) * 0.001f;
    }
  }
  last_frame_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.050f) dt = 0.050f;

  SQ15x16 smoothed_peak_fixed = SQ15x16(waveform_peak_scaled) * 0.08 + SQ15x16(waveform_peak_scaled_last) * 0.92;
  waveform_peak_scaled_last = float(smoothed_peak_fixed);

  float abs_amp = fabsf(waveform_peak_scaled);
  if (abs_amp > 1.0f) abs_amp = 1.0f;
  float smooth_abs_amp = fabsf(waveform_peak_scaled_last);
  if (smooth_abs_amp > 1.0f) smooth_abs_amp = 1.0f;
  float vu_level = float(audio_vu_level_average);
  if (vu_level < 0.0f) vu_level = 0.0f;
  if (vu_level > 1.0f) vu_level = 1.0f;

  float waveform_reactive_raw_floor = float(rp->SWEET_SPOT_MIN_LEVEL) * VP_WAVEFORM_REACTIVE_RAW_MARGIN;
  bool raw_active = max_waveform_val_raw > waveform_reactive_raw_floor;
  bool peak_active = abs_amp >= VP_WAVEFORM_REACTIVE_PEAK_FLOOR;
  bool vu_active = vu_level >= VP_WAVEFORM_VU_FLOOR;
  bool waveform_seed_active = raw_active && (peak_active || vu_active);

  float seed_level = abs_amp;
  if (smooth_abs_amp > seed_level) seed_level = smooth_abs_amp;
  if (vu_level > seed_level) seed_level = vu_level;
  if (seed_level > 1.0f) seed_level = 1.0f;

  CRGB16 current_sum_color = {0,0,0};
  float brightness_sum = 0.0f;
  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = render_params_palette_owns_colour(rp, render_secondary);
  uint8_t palette_to_use = render_params_palette_index(rp, render_secondary);
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);
  for (uint8_t c = 0; c < 12; c++) {
    float prog = c / 12.0f;
    float bin = float(chromagram_smooth[c]);

    float bright = bin;
    for (uint8_t s = 0; s < floor(rp->SQUARE_ITER); s++) {
      bright *= bright;
    }
    float fract_iter = rp->SQUARE_ITER - floor(rp->SQUARE_ITER);
    if (fract_iter > 0.01f) {
      float squared = bright * bright;
      bright = bright * (1.0f - fract_iter) + squared * fract_iter;
    }

    bright *= 1.5f;
    if (bright > 1.0f) bright = 1.0f;

    if (palette_owns_colour) {
      brightness_sum += bright * led_share;
    } else if (chromatic_mode == true) {
      CRGB16 note_col = hsv(SQ15x16(prog), SQ15x16(rp->SATURATION), SQ15x16(bright));
      current_sum_color.r += note_col.r * led_share;
      current_sum_color.g += note_col.g * led_share;
      current_sum_color.b += note_col.b * led_share;
    } else {
      brightness_sum += bright * led_share;
    }
  }

  if (palette_owns_colour) {
    current_sum_color = palette_chroma_colour(pal, SQ15x16(brightness_sum), rp->CHROMA);
  } else if (chromatic_mode == false) {
    current_sum_color = hsv(chroma_val + hue_position, SQ15x16(rp->SATURATION), SQ15x16(brightness_sum));
  }

  float chromagram_energy = 0.0f;
  for (uint8_t c = 0; c < 12; c++) {
    chromagram_energy += float(chromagram_smooth[c]);
  }
  chromagram_energy /= 12.0f;
  SQ15x16 blend = SQ15x16(chromagram_energy * VP_WAVEFORM_CHROMA_BLEND_GAIN);
  if (blend > SQ15x16(1.0)) blend = SQ15x16(1.0);
  if (blend < SQ15x16(0.0)) blend = SQ15x16(0.0);
  SQ15x16 inv_blend = SQ15x16(1.0) - blend;
  SQ15x16 fallback_brightness = waveform_seed_active ? SQ15x16(seed_level * VP_WAVEFORM_FALLBACK_BRIGHTNESS) : SQ15x16(0.0);
  CRGB16 fallback;
  if (palette_owns_colour) {
    // PALETTE-CRUSH FIX (2026-06-11, Captain-approved B): route the fallback
    // through the offset-aware palette sampler so the fallback remains distinct
    // from the main chromagram centroid sample during low-chroma passages.
    fallback = palette_chroma_colour_with_offset(pal, fallback_brightness, rp->CHROMA,
                                                 WAVEFORM_HYBRID_FALLBACK_PALETTE_OFFSET);
  } else {
    fallback = hsv(SQ15x16(rp->CHROMA), SQ15x16(rp->SATURATION), fallback_brightness);
  }
  last_color.r = current_sum_color.r * blend + fallback.r * inv_blend;
  last_color.g = current_sum_color.g * blend + fallback.g * inv_blend;
  last_color.b = current_sum_color.b * blend + fallback.b * inv_blend;
  last_color = clamp_crgb16(last_color);

  float target_fade = VP_WAVEFORM_IDLE_FADE;
  if (waveform_seed_active) {
    float active_fade = 1.0f - (VP_WAVEFORM_ACTIVE_FADE_REDUCTION * (1.0f - seed_level));
    if (active_fade < VP_WAVEFORM_IDLE_FADE) active_fade = VP_WAVEFORM_IDLE_FADE;
    if (active_fade > 0.999f) active_fade = 0.999f;
    target_fade = active_fade;
  }
  if (target_fade < 0.0f) target_fade = 0.0f;
  if (target_fade > 0.999f) target_fade = 0.999f;

  float frame_scale = dt * 120.0f;
  SQ15x16 dynamic_fade_amount = SQ15x16(1.0f - ((1.0f - target_fade) * frame_scale));
  if (dynamic_fade_amount < SQ15x16(0.0)) dynamic_fade_amount = SQ15x16(0.0);
  if (dynamic_fade_amount > SQ15x16(0.999)) dynamic_fade_amount = SQ15x16(0.999);

  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= dynamic_fade_amount;
    leds_16[i].g *= dynamic_fade_amount;
    leds_16[i].b *= dynamic_fade_amount;
  }

  shift_accum += VP_WAVEFORM_SHIFT_RATE * dt;
  uint8_t shift_steps = uint8_t(shift_accum);
  if (shift_steps > 8) shift_steps = 8;
  if (shift_steps > 0) {
    shift_accum -= shift_steps;
    waveform_shift_outward(leds_16, shift_steps);
  }

  if (waveform_seed_active) {
    SQ15x16 seed_gain = SQ15x16(0.30f + (0.70f * seed_level));
    const uint16_t centre_left = (NATIVE_RESOLUTION / 2) - 1;
    const uint16_t centre_right = NATIVE_RESOLUTION / 2;
    const bool use_waveform_history =
      (waveform_history != nullptr) &&
      (rp->SAMPLES_PER_CHUNK > 1) &&
      (rp->SAMPLES_PER_CHUNK <= 1024);

    if (use_waveform_history) {
      uint8_t seed_radius = 3 + uint8_t(seed_level * 7.0f);
      if (seed_radius > 10) seed_radius = 10;

      const uint16_t sample_count = rp->SAMPLES_PER_CHUNK;
      float waveform_norm = max_waveform_val_raw;
      if (waveform_norm < 1.0f) waveform_norm = 1.0f;

      for (uint8_t r = 0; r <= seed_radius; r++) {
        uint16_t sample_index =
          uint16_t((uint32_t(r) * uint32_t(sample_count - 1)) / uint32_t(seed_radius));
        uint32_t abs_sum = 0;
        uint16_t abs_count = 0;

        for (uint8_t frame = 0; frame < 4; frame++) {
          for (int8_t tap = -2; tap <= 2; tap++) {
            int32_t idx = int32_t(sample_index) + tap;
            if (idx < 0) idx = 0;
            if (idx >= int32_t(sample_count)) idx = int32_t(sample_count) - 1;

            int32_t sample = waveform_history[frame][idx];
            if (sample < 0) sample = -sample;

            abs_sum += uint32_t(sample);
            abs_count++;
          }
        }

        float shape = 0.0f;
        if (abs_count > 0) {
          shape = (float(abs_sum) / float(abs_count)) / waveform_norm;
        }

        if (shape < 0.0f) shape = 0.0f;
        if (shape > 1.0f) shape = 1.0f;
        shape = sqrtf(shape);

        SQ15x16 edge_taper = SQ15x16(1.0f - (float(r) / float(seed_radius + 1)));
        SQ15x16 width_scale = SQ15x16(0.25f) + (edge_taper * SQ15x16(0.75f));
        SQ15x16 waveform_shape_scale = SQ15x16(shape);
        CRGB16 seed_color = {
          last_color.r * seed_gain * width_scale * waveform_shape_scale,
          last_color.g * seed_gain * width_scale * waveform_shape_scale,
          last_color.b * seed_gain * width_scale * waveform_shape_scale
        };
        if (centre_left >= r) {
          leds_16[centre_left - r] = seed_color;
        }
        if ((centre_right + r) < NATIVE_RESOLUTION) {
          leds_16[centre_right + r] = seed_color;
        }
      }
    } else {
      uint8_t seed_radius = 1 + uint8_t(seed_level * 3.0f);
      if (seed_radius > 4) seed_radius = 4;

      for (uint8_t r = 0; r <= seed_radius; r++) {
        SQ15x16 width_scale = SQ15x16(1.0f - (float(r) / float(seed_radius + 1)));
        CRGB16 seed_color = {
          last_color.r * seed_gain * width_scale,
          last_color.g * seed_gain * width_scale,
          last_color.b * seed_gain * width_scale
        };
        if (centre_left >= r) {
          leds_16[centre_left - r] = seed_color;
        }
        if ((centre_right + r) < NATIVE_RESOLUTION) {
          leds_16[centre_right + r] = seed_color;
        }
      }
    }
  }

  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
