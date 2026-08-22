#include "lightshow_modes.h"

void light_mode_vu_dot(ChannelEffectState& fx) {
  // ChannelEffectState (items 9-15): the three formerly function-local statics
  // (dot_pos_last, audio_vu_level_smooth, max_level) now live in per-channel
  // state bound by reference, so primary and secondary no longer bleed. The old
  // vp_probe_reset_generation block is removed — probe determinism is now handled
  // by vp_probe_prepare_render() resetting effect_state_primary.

  SQ15x16 mix_amount = mood_scale(0.10, 0.05);

  fx.vu_dot_audio_level_smooth = (audio_vu_level_average * mix_amount) + (fx.vu_dot_audio_level_smooth * (1.0 - mix_amount));

  if (fx.vu_dot_audio_level_smooth * 1.1 > fx.vu_dot_max_level) {
    SQ15x16 distance = (fx.vu_dot_audio_level_smooth * 1.1) - fx.vu_dot_max_level;
    fx.vu_dot_max_level += distance *= 0.1;
  } else {
    fx.vu_dot_max_level *= 0.9999;
    if (fx.vu_dot_max_level < 0.0025) {
      fx.vu_dot_max_level = 0.0025;
    }
  }
  SQ15x16 multiplier = 1.0 / fx.vu_dot_max_level;

  SQ15x16 dot_pos = (fx.vu_dot_audio_level_smooth * multiplier);

  if (dot_pos > 1.0) {
    dot_pos = 1.0;
  }

  SQ15x16 mix = mood_scale(0.25, 0.24);
  SQ15x16 dot_pos_smooth = (dot_pos * mix) + (fx.vu_dot_pos_last * (1.0-mix));
  fx.vu_dot_pos_last = dot_pos_smooth;

  SQ15x16 brightness = SQ15x16(sqrtf((float)dot_pos_smooth)); // Phase 1 2026-05-20: sqrt→sqrtf, direct operator float() (no double trip)

  set_dot_position(RESERVED_DOTS + 0, dot_pos_smooth * 0.5 + 0.5);
  set_dot_position(RESERVED_DOTS + 1, 0.5 - dot_pos_smooth * 0.5);

  clear_leds();
  //fade_grayscale(0.15);

  CRGB16 color;
  bool render_secondary = vp_render_secondary_channel;
  if ((render_secondary && SECONDARY_PALETTE_MODE_ENABLED) || 
      (!render_secondary && CONFIG.PALETTE_MODE_ENABLED)) {
      // Use palette color based on brightness
      uint8_t palette_to_use = render_secondary ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
      const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);
      color = palette_manual_colour(pal, brightness, brightness);
  } else {
      // Original hue calculation
      SQ15x16 hue = chroma_val + hue_position;
      color = hsv(hue, CONFIG.SATURATION, brightness);
  }
  
  draw_dot(leds_16, RESERVED_DOTS + 0, color);
  draw_dot(leds_16, RESERVED_DOTS + 1, color);
}
