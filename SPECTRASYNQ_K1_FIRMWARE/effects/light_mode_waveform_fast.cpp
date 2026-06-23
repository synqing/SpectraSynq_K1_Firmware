#include "lightshow_modes.h"

static const float WAVEFORM_FAST_FALLBACK_PALETTE_OFFSET = 0.18f;

void light_mode_waveform_fast(CRGB16* leds_previous, CRGB16& last_color, float& waveform_peak_scaled_last,
                              float& shift_accum, uint32_t& last_frame_ms) {
  const RenderParams* rp = active_render_params();
  const float led_share = 1.0 / 12.0; // Corrected share calculation

  // PIO-WAVEFORM-FAST-DT (2026-05-25): dt-scaled transport. Previously this mode
  // shifted exactly 1 LED per render call, so trail speed tracked LED_FPS — on K1
  // (~185 FPS) that is ~1.60x faster than the S2 reference (~116 FPS). Mirror
  // light_mode_waveform_hybrid: integrate VP_WAVEFORM_SHIFT_RATE over real dt.
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
  // static CRGB16 sum_color_last = {0,0,0}; // REMOVED internal static color
  // Use the passed 'last_color' reference instead

  // --- Waveform Debugging Start ---
  bool is_secondary = (leds_previous == leds_16_prev_secondary);
  static uint32_t last_waveform_debug = 0;
  if (debug_mode && (millis() - last_waveform_debug > 500)) { // Rate limit debug output
    // Check if the previous buffer seems valid (e.g., not all zeros if it shouldn't be)
    SQ15x16 prev_sum = 0;
    for(int k=0; k<NATIVE_RESOLUTION; ++k) { prev_sum += leds_previous[k].r + leds_previous[k].g + leds_previous[k].b; }
    
    USBSerial.print("[DBG WFM] Ch: "); USBSerial.print(is_secondary ? 2 : 1);
    USBSerial.print(" | PrevSum: "); USBSerial.print(float(prev_sum));
    USBSerial.print(" | LastClr R: "); USBSerial.print(float(last_color.r));
    USBSerial.print(" G: "); USBSerial.print(float(last_color.g));
    USBSerial.print(" B: "); USBSerial.println(float(last_color.b));
    last_waveform_debug = millis();
  }
  // --- Waveform Debugging End ---

  // --- Color Calculation (Mostly kept as is, using CRGB16) ---
  // ... (rest of color calculation logic using 'last_color') ...
  SQ15x16 smoothed_peak_fixed = SQ15x16(waveform_peak_scaled) * 0.05 + SQ15x16(waveform_peak_scaled_last) * 0.95;
  waveform_peak_scaled_last = float(smoothed_peak_fixed);
  float abs_amp = fabsf(waveform_peak_scaled);
  if (abs_amp > 1.0f) abs_amp = 1.0f;
  float waveform_reactive_raw_floor = float(rp->SWEET_SPOT_MIN_LEVEL) * WAVEFORM_REACTIVE_RAW_MARGIN;
  bool waveform_reactive = (max_waveform_val_raw > waveform_reactive_raw_floor) && (abs_amp >= WAVEFORM_REACTIVE_PEAK_FLOOR);

  CRGB16 current_sum_color = {0,0,0};
  float brightness_sum = 0.0;
  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = render_params_palette_owns_colour(rp, render_secondary);
  uint8_t palette_to_use = render_params_palette_index(rp, render_secondary);
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);
  for (uint8_t c = 0; c < 12; c++) {
    float prog = c / 12.0f;
    float bin = float(chromagram_smooth[c]);

    float bright = bin;
    // Apply full iterations
    for (uint8_t s = 0; s < floor(rp->SQUARE_ITER); s++) {
      bright *= bright;
    }
    // Apply fractional iteration
    float fract_iter = rp->SQUARE_ITER - floor(rp->SQUARE_ITER);
    if (fract_iter > 0.01) {
      float squared = bright * bright;
      bright = bright * (1.0f - fract_iter) + squared * fract_iter;
    }
    
    bright *= 1.5; 
    if (bright > 1.0) { bright = 1.0; }

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

#if ENABLE_WAVEFORM_CHROMAGRAM_COLOR
  // Phase 2 Change 11 (2026-05-20): restore chromagram-driven trail color.
  // Prior code hardcoded last_color = hsv(CONFIG.CHROMA, SAT, 1.0), discarding
  // the chromagram math above. Per observation 53369, naive use of current_sum_color
  // collapses to black when chromagram is silent — so we blend with CHROMA fallback
  // based on chromagram total energy.
  {
    float chromagram_energy = 0.0f;
    for (uint8_t c = 0; c < 12; c++) chromagram_energy += float(chromagram_smooth[c]);
    chromagram_energy /= 12.0f;  // 0 to ~1
    SQ15x16 blend = SQ15x16(chromagram_energy * 2.0f); // ramp aggressively toward chromagram
    if (blend > SQ15x16(1.0)) blend = SQ15x16(1.0);
    SQ15x16 inv_blend = SQ15x16(1.0) - blend;
    SQ15x16 fallback_brightness = waveform_reactive ? SQ15x16(abs_amp) : SQ15x16(0.0);
    CRGB16 fallback;
    if (palette_owns_colour) {
      // PALETTE-CRUSH FIX (2026-06-11, Captain-approved B): route the fallback
      // through the offset-aware palette sampler so the fallback remains a
      // palette identity sample instead of reusing the exact same held centroid
      // as the main chromagram colour.
      fallback = palette_chroma_colour_with_offset(pal, fallback_brightness, rp->CHROMA,
                                                   WAVEFORM_FAST_FALLBACK_PALETTE_OFFSET);
    } else {
      fallback = hsv(SQ15x16(rp->CHROMA), SQ15x16(rp->SATURATION), fallback_brightness);
    }
    last_color.r = current_sum_color.r * blend + fallback.r * inv_blend;
    last_color.g = current_sum_color.g * blend + fallback.g * inv_blend;
    last_color.b = current_sum_color.b * blend + fallback.b * inv_blend;
    last_color = clamp_crgb16(last_color);
  }
#else
  // Original (prior firmware): hardcoded CHROMA-driven color, chromagram math wasted
  if (palette_owns_colour) {
    last_color = palette_manual_colour(pal, SQ15x16(rp->CHROMA), SQ15x16(1.0));
  } else {
    last_color = hsv(SQ15x16(rp->CHROMA), SQ15x16(rp->SATURATION), SQ15x16(1.0));
  }
  last_color = clamp_crgb16(last_color);
#endif
  // --- End Color Calculation ---

  // --- Dynamic Fading for Trails ---
  // Operate directly on the global leds_16 buffer, assuming it holds the *target* state from previous frame
  float max_fade_reduction = 0.10; 
  SQ15x16 dynamic_fade_amount = waveform_reactive ? SQ15x16(1.0 - (max_fade_reduction * abs_amp)) : SQ15x16(WAVEFORM_IDLE_FADE);

  // Apply the dynamic fade TO THE GLOBAL leds_16 buffer
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
      leds_16[i].r *= dynamic_fade_amount;
      leds_16[i].g *= dynamic_fade_amount;
      leds_16[i].b *= dynamic_fade_amount;
  }

  // --- Waveform Display ---
  float amp = waveform_peak_scaled;

  // PIO-WAVEFORM-FAST-DT (2026-05-25): integer steps from the dt accumulator,
  // capped at 8/frame (matches hybrid). 0 steps on a fast frame is correct.
  shift_accum += VP_WAVEFORM_SHIFT_RATE * dt;
  uint8_t shift_steps = uint8_t(shift_accum);
  if (shift_steps > 8) shift_steps = 8;
  if (shift_steps > 0) {
    shift_accum -= shift_steps;
    if (rp->MIRROR_ENABLED) {
      waveform_shift_upper_half_up(leds_16, shift_steps);
    } else {
      shift_leds_up(leds_16, shift_steps); // Shift the global leds_16 buffer
    }
  }

  // Set the new dot only once the calibrated audio floor has been crossed.
  if (waveform_reactive) {
    uint16_t pos = rp->MIRROR_ENABLED
      ? waveform_upper_half_source_position(amp)
      : waveform_full_strip_position(amp);
    leds_16[pos] = last_color; // Draw onto the global leds_16 buffer
  }

  if (rp->MIRROR_ENABLED) {
    // Upper half is the intentional source trace; mirror only after constraining the dot there.
    mirror_image_downwards(leds_16);
  }
}
