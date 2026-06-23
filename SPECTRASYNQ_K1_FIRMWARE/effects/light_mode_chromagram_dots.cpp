#include "lightshow_modes.h"

void light_mode_chromagram_dots() {
  // static SQ15x16 chromagram_last[12]; // Removed static buffer

  const RenderParams* rp = active_render_params();
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  //dim_display(0.9);

  // low_pass_array_fixed(chromagram_smooth, chromagram_last, 12, LED_FPS, float(mood_scale(3.5, 1.5))); // Removed low-pass call
  // memcpy(chromagram_last, chromagram_smooth, sizeof(float) * 12); // Removed memcpy

  bool render_secondary = vp_render_secondary_channel;
  uint8_t palette_to_use = render_secondary ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);

  for (uint8_t i = 0; i < 12; i++) {
    SQ15x16 led_hue;
    uint8_t paletteIndex = 0;
    
    if ((render_secondary && SECONDARY_PALETTE_MODE_ENABLED) || 
        (!render_secondary && CONFIG.PALETTE_MODE_ENABLED)) {
        // Use palette color based on brightness
        paletteIndex = uint8_t(float(i) / 12.0f * 255.0f); // Map note index to palette index
        // Use the CRGBPalette16 with ColorFromPalette
        CRGB rgb_color = ColorFromPalette(pal, palette_index_with_phase(paletteIndex), uint8_t(float(chromagram_smooth[i]) * 255));
        led_hue = SQ15x16(rgb_color.r/255.0);
    } else {
        // Use CHROMA directly
        led_hue = SQ15x16(rp->CHROMA) + hue_position + (sqrt(float(1.0)) * SQ15x16(0.05));
    }

    SQ15x16 magnitude = chromagram_smooth[i] * 1.0;
    if (magnitude > 1.0) { magnitude = 1.0; }

    magnitude = magnitude * magnitude;

    CRGB16 col;
    if ((render_secondary && SECONDARY_PALETTE_MODE_ENABLED) || 
        (!render_secondary && CONFIG.PALETTE_MODE_ENABLED)) {
        // --- Palette Mode ---
        // Use the CRGBPalette16 with ColorFromPalette
        CRGB rgb_color = ColorFromPalette(pal, palette_index_with_phase(paletteIndex), uint8_t(float(magnitude) * 255));
        col = crgb_to_crgb16(rgb_color);
    } else {
        // --- Original Hue/Chromatic Mode ---
        if (chromatic_mode == true) {
            led_hue = note_colors[i];
        } else {
            // Use CHROMA directly
            led_hue = SQ15x16(rp->CHROMA) + hue_position + (sqrt(float(1.0)) * SQ15x16(0.05));
        }
        col = hsv(led_hue, SQ15x16(rp->SATURATION), magnitude);
    }

    set_dot_position(RESERVED_DOTS + i * 2 + 0, magnitude * 0.45 + 0.5);
    set_dot_position(RESERVED_DOTS + i * 2 + 1, 0.5 - magnitude * 0.45);

    draw_dot(leds_16, RESERVED_DOTS + i * 2 + 0, col);
    draw_dot(leds_16, RESERVED_DOTS + i * 2 + 1, col);
  }
}
