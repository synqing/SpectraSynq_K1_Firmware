#include "lightshow_modes.h"

void light_mode_kaleidoscope(ChannelEffectState& fx) {
  // ChannelEffectState (items 9-15): the six formerly function-local statics
  // (pos_r/g/b, brightness_low/mid/high) now live in per-channel state bound by
  // reference, so primary and secondary no longer bleed. The old
  // vp_probe_reset_generation block is removed — probe determinism is now handled
  // by vp_probe_prepare_render() resetting effect_state_primary.

  SQ15x16 sum_low = 0.0;
  SQ15x16 sum_mid = 0.0;
  SQ15x16 sum_high = 0.0;

  // --- Safety Check for Config Values ---
  if (!isfinite(float(CONFIG.MOOD)) || !isfinite(float(CONFIG.SQUARE_ITER))) {
    if (debug_mode) USBSerial.println("!!! WARNING [Kal]: Invalid float in CONFIG (MOOD/SQUARE_ITER)!");
    if (!isfinite(float(CONFIG.MOOD))) CONFIG.MOOD = 0.05;
    if (!isfinite(float(CONFIG.SQUARE_ITER))) CONFIG.SQUARE_ITER = 1.0;
  }

  // Consolidate brightness calculation
  for (uint8_t i = 0; i < 20; i++) {
    // Ensure we don't exceed array bounds
    if (i >= NUM_FREQS || (20+i) >= NUM_FREQS || (40+i) >= NUM_FREQS) {
      continue;
    }
    
    // Safety Check for Spectrogram Data
    if (!isfinite(float(spectrogram_smooth[i])) || !isfinite(float(spectrogram_smooth[20+i])) || !isfinite(float(spectrogram_smooth[40+i]))) {
      if (debug_mode) { USBSerial.print("!!! WARNING [Kal]: Invalid spectrogram_smooth[] at index "); USBSerial.println(i); }
      continue;
    }
    
    SQ15x16 bin_low = spectrogram_smooth[i]; // 0-19
    SQ15x16 bin_mid = spectrogram_smooth[20 + i]; // 20-39
    SQ15x16 bin_high = spectrogram_smooth[40 + i]; // 40-59

    // Apply gentle squaring for emphasis
    bin_low = bin_low * 0.5 + (bin_low * bin_low) * 0.5;
    bin_mid = bin_mid * 0.5 + (bin_mid * bin_mid) * 0.5;
    bin_high = bin_high * 0.5 + (bin_high * bin_high) * 0.5;

    sum_low += bin_low;
    sum_mid += bin_mid;
    sum_high += bin_high;

    // Update brightness smoothly
    if (bin_low > fx.kal_brightness_low) fx.kal_brightness_low += fabs_fixed(bin_low - fx.kal_brightness_low) * 0.1;
    if (bin_mid > fx.kal_brightness_mid) fx.kal_brightness_mid += fabs_fixed(bin_mid - fx.kal_brightness_mid) * 0.1;
    if (bin_high > fx.kal_brightness_high) fx.kal_brightness_high += fabs_fixed(bin_high - fx.kal_brightness_high) * 0.1;
  }

  fx.kal_brightness_low *= 0.99; // Apply decay
  fx.kal_brightness_mid *= 0.99;
  fx.kal_brightness_high *= 0.99;

  // Clamp brightness to prevent blowouts
  if (fx.kal_brightness_low > 1.0) fx.kal_brightness_low = 1.0;
  if (fx.kal_brightness_mid > 1.0) fx.kal_brightness_mid = 1.0;
  if (fx.kal_brightness_high > 1.0) fx.kal_brightness_high = 1.0;


  // Calculate shift speed based on mood, capped for stability
  SQ15x16 shift_speed = (SQ15x16)100 + ((SQ15x16)500 * (SQ15x16)CONFIG.MOOD);
  if (shift_speed > 600.0) shift_speed = 600.0; // Cap max shift speed

  SQ15x16 shift_r = (shift_speed * sum_low);
  SQ15x16 shift_g = (shift_speed * sum_mid);
  SQ15x16 shift_b = (shift_speed * sum_high);

  // Clamp shift values to prevent extreme moves and scale down for smoother movement
  const SQ15x16 max_shift = 100.0;
  const SQ15x16 shift_scale = 0.005; // Reduced scale factor for even smoother movement
  if (shift_r > max_shift) shift_r = max_shift;
  if (shift_g > max_shift) shift_g = max_shift;
  if (shift_b > max_shift) shift_b = max_shift;

  fx.kal_pos_r += float(shift_r * shift_scale);
  fx.kal_pos_g += float(shift_g * shift_scale);
  fx.kal_pos_b += float(shift_b * shift_scale);

  // Clear the LED buffer before drawing
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

  // Loop through the first half of the strip to calculate colors
  uint16_t half_res = NATIVE_RESOLUTION >> 1;
  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = palette_owns_render_colour_source();
  uint8_t palette_to_use = render_secondary ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);
  for (uint16_t i = 0; i < half_res; i++) {
    uint32_t y_pos_r = fx.kal_pos_r;
    uint32_t y_pos_g = fx.kal_pos_g;
    uint32_t y_pos_b = fx.kal_pos_b;

    // Consistent noise coordinate scaling
    SQ15x16 noise_coord_scale = 3.0; // Adjusted scale slightly
    uint32_t i_scaled = uint32_t((SQ15x16)i * noise_coord_scale); // Use 'i' directly for smoother mapping

    // Generate noise values
    SQ15x16 r_val = inoise16(i_scaled + y_pos_r) / 65536.0;
    SQ15x16 g_val = inoise16(i_scaled + 10000 + y_pos_g) / 65536.0; // Add offsets for variation
    SQ15x16 b_val = inoise16(i_scaled + 20000 + y_pos_b) / 65536.0;

    // Clamp values
    if (r_val > 1.0) r_val = 1.0; else if (r_val < 0.0) r_val = 0.0;
    if (g_val > 1.0) g_val = 1.0; else if (g_val < 0.0) g_val = 0.0;
    if (b_val > 1.0) b_val = 1.0; else if (b_val < 0.0) b_val = 0.0;

    // Apply contrast safely
    uint8_t base_iters = floor(CONFIG.SQUARE_ITER);
    float fract_iter = CONFIG.SQUARE_ITER - base_iters;
    
    for (uint8_t s = 0; s < base_iters; s++) {
      r_val *= r_val; g_val *= g_val; b_val *= b_val;
    }
    if (fract_iter > 0.01) {
      SQ15x16 r_sq = r_val * r_val; SQ15x16 g_sq = g_val * g_val; SQ15x16 b_sq = b_val * b_val;
      r_val = r_val * (1.0 - fract_iter) + r_sq * fract_iter;
      g_val = g_val * (1.0 - fract_iter) + g_sq * fract_iter;
      b_val = b_val * (1.0 - fract_iter) + b_sq * fract_iter;
    }

    // Fade brightness towards the start of the half-strip
    SQ15x16 prog = 1.0;
    uint16_t quarter_res = NATIVE_RESOLUTION >> 2;
    if (i < quarter_res && quarter_res > 1) {
      prog = (SQ15x16)i / (SQ15x16)(quarter_res - 1);
      prog = prog * prog; // Quadratic fade
    } else if (quarter_res <= 1) {
      prog = 1.0; // Avoid division by zero
    }

    // Modulate by band brightness and fade profile
    r_val *= prog * fx.kal_brightness_low;
    g_val *= prog * fx.kal_brightness_mid;
    b_val *= prog * fx.kal_brightness_high;

    SQ15x16 brightness = 0.0;
    if(r_val > brightness) brightness = r_val;
    if(g_val > brightness) brightness = g_val;
    if(b_val > brightness) brightness = b_val;

    CRGB16 col;
    if (palette_owns_colour) {
      uint8_t palette_index = (half_res > 1) ? uint8_t((float(i) / float(half_res - 1)) * 255.0f) : 0;
      CRGB rgb_color = ColorFromPalette(pal, palette_index_with_phase(palette_index), uint8_t(float(brightness) * 255));
      col = crgb_to_crgb16(rgb_color);
    } else {
      col = { r_val, g_val, b_val };

      // Apply desaturation based on CONFIG.SATURATION
      col = desaturate(col, 1.0 - CONFIG.SATURATION);

      if (chromatic_mode == false) {
        // Calculate hue progression safely
        SQ15x16 hue_prog = (half_res > 1) ? (SQ15x16)i / (SQ15x16)(half_res - 1) : 0.0;

        // Calculate final hue
        SQ15x16 led_hue = CONFIG.CHROMA + hue_position + ((SQ15x16(sqrtf((float)brightness)) * SQ15x16(0.05)) + (hue_prog * SQ15x16(0.10)) * hue_shifting_mix); // Phase 1 2026-05-20: sqrt→sqrtf, direct operator float() (no double trip)

        // Wrap hue value
        while (led_hue < 0.0) led_hue += 1.0;
        while (led_hue >= 1.0) led_hue -= 1.0;

        // Create colour using HSV
        col = hsv(led_hue, CONFIG.SATURATION, brightness);
      }
    }

    // Write directly to the first half
    leds_16[i] = col;
    
    // Explicitly mirror to the second half if enabled
    if (CONFIG.MIRROR_ENABLED) {
      leds_16[NATIVE_RESOLUTION - 1 - i] = col;
    } else {
      // If not mirroring, maybe clear the second half or apply a different pattern?
      // For now, let's just leave it potentially empty if not mirroring.
      // You could uncomment the line below to explicitly clear the second half when mirror is off:
      // leds_16[NATIVE_RESOLUTION - 1 - i] = {0,0,0}; 
    }
  }
  
  // If mirroring is disabled, the second half might not have been written to.
  // We might need to explicitly calculate values for the second half here
  // if a full-strip, non-mirrored effect is desired when MIRROR_ENABLED is false.
  // For now, this fix assumes mirroring is the primary way this mode is used.
}
