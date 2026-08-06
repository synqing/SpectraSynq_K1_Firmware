#include "lightshow_modes.h"

void light_mode_gdft() {
  const RenderParams* rp = active_render_params();
  // Phase 1 2026-05-20: hoist palette construction OUT of per-LED loop (was 80x redundant).
  // palette_to_use is loop-invariant (depends on render channel + CONFIG.PALETTE_INDEX, both
  // stable for the lifetime of this call). Construct once even if palette mode is off —
  // ~50 cycles unconditionally costs less than 80 reconstructions when it IS on.
  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = palette_owns_render_colour_source();
  uint8_t palette_to_use = render_secondary ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);

  // Analysis authority: only bins with target_freq <= fs/2. Canvas width stays
  // NATIVE_RESOLUTION/2 (= NUM_FREQS); ghosts [safe_hi, NUM_FREQS) are not resolution.
  const uint8_t analysis_bins =
      sb_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET);
  const uint8_t analysis_hi = (analysis_bins > 1) ? (uint8_t)(analysis_bins - 1) : 0;

  // Calculate frequency data for the first half of the strip
  for (uint16_t i = 0; i < (NATIVE_RESOLUTION / 2); i++) {
    // Map representable bins across the first half (NATIVE_RESOLUTION / 2 LEDs)
    SQ15x16 freq_prog = (SQ15x16)i / (SQ15x16)(NATIVE_RESOLUTION / 2);
    SQ15x16 freq_index_f = freq_prog * (SQ15x16)analysis_hi;
    uint16_t freq_index_i = freq_index_f.getInteger();
    SQ15x16 freq_fract = freq_index_f - freq_index_i;

    // Ensure we don't index out of bounds within analysis authority
    if (freq_index_i >= analysis_hi) {
      freq_index_i = (analysis_hi > 0) ? (uint16_t)(analysis_hi - 1) : 0;
      freq_fract = 1.0;
    }
    
    // Additional bounds check for safety
    if (freq_index_i < 0) {
      freq_index_i = 0;
      freq_fract = 0.0;
    }

    // Ensure both indices are within analysis authority before accessing data
    if (freq_index_i >= analysis_bins || freq_index_i + 1 >= analysis_bins) {
      if (debug_mode) { USBSerial.print("!!! WARNING [GDFT]: Out of bounds freq_index_i: "); USBSerial.println(freq_index_i); }
      continue; // Skip this iteration if indices are invalid
    }

    // Interpolate between adjacent frequency bins
    SQ15x16 bin1 = spectrogram_smooth[freq_index_i];
    SQ15x16 bin2 = spectrogram_smooth[freq_index_i + 1];
    
    // Check for NaN/Inf values in the bins
    if (!isfinite(float(bin1)) || !isfinite(float(bin2)) || !isfinite(float(freq_fract))) {
      if (debug_mode) { USBSerial.print("!!! WARNING [GDFT]: Invalid bin values at index "); USBSerial.println(freq_index_i); }
      bin1 = 0.0; bin2 = 0.0; // Reset to safe values
    }
    
    SQ15x16 bin = bin1 * (1.0 - freq_fract) + bin2 * freq_fract;

    // Clamp the bin value safely
    if (!isfinite(float(bin))) bin = 0.0;
    if (bin > 1.0) bin = 1.0;
    if (bin < 0.0) bin = 0.0;

    uint8_t base_iters = floor(rp->SQUARE_ITER);
    float fract_iter = rp->SQUARE_ITER - base_iters;

    uint8_t extra_iters = 0;
    if (!palette_owns_colour && chromatic_mode == true) {
      extra_iters = 1;
    }

    // Apply full iterations first
    for (uint8_t s = 0; s < base_iters + extra_iters; s++) {
      bin = (bin * bin) * SQ15x16(0.65) + (bin * SQ15x16(0.35));
    }

    // Apply fractional iteration if needed
    if (fract_iter > 0.01) {
      SQ15x16 squared = (bin * bin) * SQ15x16(0.65) + (bin * SQ15x16(0.35));
      bin = bin * (1.0 - fract_iter) + squared * fract_iter;
    }

    CRGB16 final_color;
    if (palette_owns_colour) {
        // --- Palette Mode ---
        // Phase 1 2026-05-20: `pal` and `palette_to_use` now hoisted above the for(i) loop.
        uint8_t paletteIndex = uint8_t(float(freq_prog) * 255); // Map frequency progress (0-1) to palette index (0-255)
        // Use the CRGBPalette16 with ColorFromPalette
        CRGB rgb_color = ColorFromPalette(pal, palette_index_with_phase(paletteIndex), uint8_t(float(bin) * 255));
        final_color = crgb_to_crgb16(rgb_color);
    } else {
        // --- Original Hue/Chromatic Mode ---
        SQ15x16 led_hue;
        SQ15x16 prog = (SQ15x16)i / (SQ15x16)(NATIVE_RESOLUTION / 2); // Use LED position for hue progression
        if (chromatic_mode == true) {
            // Ensure indices for note colors are within bounds
            uint8_t idx1 = freq_index_i % 12;
            uint8_t idx2 = (freq_index_i + 1) % 12;
            
            // Interpolate note colors across the half-strip based on frequency index
            SQ15x16 hue1 = note_colors[idx1];
            SQ15x16 hue2 = note_colors[idx2];
            
            // Handle hue wrap-around during interpolation
            if (fabs_fixed(hue1 - hue2) > 0.5) { // Detect wrap around 0.0/1.0
                if (hue1 < hue2) hue1 += 1.0; else hue2 += 1.0;
            }
            led_hue = hue1 * (1.0 - freq_fract) + hue2 * freq_fract;
            if (led_hue >= 1.0) led_hue -= 1.0; // Normalize back to 0-1 range
        } else {
            // Use CHROMA directly
            SQ15x16 base_hue = SQ15x16(rp->CHROMA) + hue_position;
            SQ15x16 bin_mod = (SQ15x16(sqrtf((float)bin)) * SQ15x16(0.05)); // Phase 1 2026-05-20: sqrt→sqrtf, direct operator float() (no double trip)
            SQ15x16 prog_mod = (prog * SQ15x16(0.10)) * hue_shifting_mix;
            led_hue = base_hue + bin_mod + prog_mod;
            // Ensure hue wraps
            while (led_hue < 0.0) led_hue += 1.0;
            while (led_hue >= 1.0) led_hue -= 1.0;
        }
        
        // Add safety check for HSV components
        SQ15x16 final_sat = SQ15x16(rp->SATURATION);
        SQ15x16 final_val = bin;
        if (!isfinite(float(led_hue)) || !isfinite(float(final_sat)) || !isfinite(float(final_val))) {
          if (debug_mode) { USBSerial.print("!!! WARNING [GDFT]: Invalid final HSV components! i="); USBSerial.println(i); }
          led_hue = 0; final_sat = 1.0; final_val = 0; // Reset problematic components
        }
        final_color = hsv(led_hue, final_sat, final_val);
    }
    
    // Place calculated color in the second half of the strip
    uint16_t second_half_idx = i + (NATIVE_RESOLUTION / 2);
    if (second_half_idx < NATIVE_RESOLUTION) {
        leds_16[second_half_idx] = final_color;
    }
    
    // Directly mirror to the first half instead of relying on mirror_image_downwards
    // This ensures that mirroring works correctly regardless of the mirror function
    if (rp->MIRROR_ENABLED) {
        uint16_t first_half_idx = (NATIVE_RESOLUTION / 2) - 1 - i;
        if (first_half_idx < NATIVE_RESOLUTION) {
            leds_16[first_half_idx] = final_color;
        }
    }
  }
}
