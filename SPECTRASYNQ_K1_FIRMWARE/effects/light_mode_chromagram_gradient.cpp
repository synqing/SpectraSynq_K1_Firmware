#include "lightshow_modes.h"

void light_mode_chromagram_gradient() {
  const RenderParams* rp = active_render_params();
  // First, clear the entire LED strip
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

  // Phase 1 2026-05-20: hoist palette construction OUT of per-LED loop (was 80x redundant).
  bool render_secondary = vp_render_secondary_channel;
  uint8_t palette_to_use_cg = render_secondary ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
  const CRGBPalette16& pal_cg = cached_gradient_palette(palette_to_use_cg, render_secondary);

  // Loop through the second half of the strip
  for (uint16_t i = 0; i < (NATIVE_RESOLUTION / 2); i++) {
    // Calculate progress across half-strip (0.0 to 1.0)
    SQ15x16 prog = (SQ15x16)i / (SQ15x16)(NATIVE_RESOLUTION / 2 - 1);
    if (prog < 0.0) prog = 0.0; // Safety check
    
    // Get chromagram value using safe interpolation
    SQ15x16 note_index = prog * 11.0; // Map 0-1 to 0-11 (12 notes)
    uint8_t idx1 = note_index.getInteger();
    uint8_t idx2 = idx1 + 1;
    if (idx2 >= 12) idx2 = 0; // Wrap around for last index
    
    SQ15x16 fract = note_index - idx1;
    SQ15x16 val1 = chromagram_smooth[idx1];
    SQ15x16 val2 = chromagram_smooth[idx2];
    
    // Interpolate between adjacent chromagram bins
    SQ15x16 note_magnitude = val1 * (1.0 - fract) + val2 * fract;
    note_magnitude = note_magnitude * 0.9 + 0.1; // Add a base level
    
    // Apply contrast
    uint8_t base_iters = floor(rp->SQUARE_ITER);
    float fract_iter = rp->SQUARE_ITER - base_iters;

    // Apply full iterations
    for (uint8_t s = 0; s < base_iters; s++) {
      note_magnitude = (note_magnitude * note_magnitude) * SQ15x16(0.65) + (note_magnitude * SQ15x16(0.35));
    }

    // Apply fractional iteration if needed
    if (fract_iter > 0.01) {
      SQ15x16 squared = (note_magnitude * note_magnitude) * SQ15x16(0.65) + (note_magnitude * SQ15x16(0.35));
      note_magnitude = note_magnitude * (1.0 - fract_iter) + squared * fract_iter;
    }

    // Calculate hue
    SQ15x16 led_hue;
    CRGB16 col;
    
    if ((render_secondary && SECONDARY_PALETTE_MODE_ENABLED) ||
        (!render_secondary && CONFIG.PALETTE_MODE_ENABLED)) {
        // --- Palette Mode ---
        // Phase 1 2026-05-20: `pal_cg` and `palette_to_use_cg` now hoisted above the for(i) loop.
        col = palette_manual_colour(pal_cg, prog, note_magnitude * note_magnitude);
    } else {
        // --- Original Hue/Chromatic Mode ---
        if (chromatic_mode == true) {
            // Use musical note colors
            // Interpolate note colors based on progress across the half-strip
            SQ15x16 color_prog = prog * 11.0; // Map 0-1 progress to 0-11 index range
            uint8_t idx1_hue = color_prog.getInteger();
            uint8_t idx2_hue = idx1_hue + 1;
            if (idx2_hue >= 12) idx2_hue = 11; // Clamp index
            SQ15x16 fract_hue = color_prog - idx1_hue;
            
            SQ15x16 hue1 = note_colors[idx1_hue];
            SQ15x16 hue2 = note_colors[idx2_hue];
            
            // Handle hue wrap-around during interpolation
            if (fabs_fixed(hue1 - hue2) > 0.5) {
                if (hue1 < hue2) hue1 += 1.0; else hue2 += 1.0;
            }
            led_hue = hue1 * (1.0 - fract_hue) + hue2 * fract_hue;
            if (led_hue >= 1.0) led_hue -= 1.0; // Normalize back to 0-1 range
        } else {
            // Use CHROMA with position modulation
            led_hue = SQ15x16(rp->CHROMA) + hue_position + ((prog * SQ15x16(0.10)) * hue_shifting_mix);
            // Ensure hue wraps
            while (led_hue < 0.0) led_hue += 1.0;
            while (led_hue >= 1.0) led_hue -= 1.0;
        }
        col = hsv(led_hue, SQ15x16(rp->SATURATION), note_magnitude * note_magnitude);
    }

    // Write to both halves (with position mirroring)
    leds_16[(NATIVE_RESOLUTION / 2) + i] = col;
    leds_16[(NATIVE_RESOLUTION / 2) - 1 - i] = col;
  }
}
