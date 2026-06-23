void set_preset(char* preset_name) {
  // Modifies current CONFIG struct based on input preset name

  if (strcmp(preset_name, "default") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0.80;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = true;
    CONFIG.BULB_OPACITY = 0.0;
    CONFIG.SATURATION = 1.0;
  }

  else if (strcmp(preset_name, "tinted_bulbs") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0.80;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = false;
    CONFIG.BULB_OPACITY = 1.0;
    CONFIG.SATURATION = 1.0;
  }

  else if (strcmp(preset_name, "incandescent") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 1.0;
    CONFIG.INCANDESCENT_MODE = true;
    CONFIG.BASE_COAT = true;
    CONFIG.BULB_OPACITY = 0.0;
    CONFIG.SATURATION = 1.0;
  }

  else if (strcmp(preset_name, "white") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = true;
    CONFIG.BULB_OPACITY = 0.0;
    CONFIG.SATURATION = 0.0;
  }

  else if (strcmp(preset_name, "classic") == 0) {
    CONFIG.SQUARE_ITER = 1;
    CONFIG.INCANDESCENT_FILTER = 0.0;
    CONFIG.INCANDESCENT_MODE = false;
    CONFIG.BASE_COAT = false;
    CONFIG.BULB_OPACITY = 0.0;
    CONFIG.SATURATION = 1.0;
  }

  // ── Dual-edge PAIRING presets (2026-06-11, impact lane item 3) ─────────────
  // The LGP physically interferes the two edge injections; these pairings put
  // a complementary effect on each edge so the plate shows interior depth no
  // single channel can. Modes only — colour authority/palette stay as set.
  // Invoke via the existing serial command: preset=<name>

  else if (strcmp(preset_name, "harmony_rhythm") == 0) {
    // Melody on the bottom edge, drum kit on the top edge.
    CONFIG.LIGHTSHOW_MODE = LIGHT_MODE_CHROMA_CONSTELLATION;
    SECONDARY_LIGHTSHOW_MODE = LIGHT_MODE_PERCUSSION_BURST;
    ENABLE_SECONDARY_LEDS = true;
    SECONDARY_MIRROR_ENABLED = true;
  }

  else if (strcmp(preset_name, "deep_flow") == 0) {
    // Song-arc river against the chord-anchored lattice.
    CONFIG.LIGHTSHOW_MODE = LIGHT_MODE_RIVER_SURGE;
    SECONDARY_LIGHTSHOW_MODE = LIGHT_MODE_DENSE_FORGE_CHORD;
    ENABLE_SECONDARY_LEDS = true;
    SECONDARY_MIRROR_ENABLED = true;
  }

  else if (strcmp(preset_name, "beat_theatre") == 0) {
    // Anticipating comets landing on the beat over a beat-locked flow.
    CONFIG.LIGHTSHOW_MODE = LIGHT_MODE_TEMPO_COMET_ANTICIPATE;
    SECONDARY_LIGHTSHOW_MODE = LIGHT_MODE_TEMPO_RIVER;
    ENABLE_SECONDARY_LEDS = true;
    SECONDARY_MIRROR_ENABLED = true;
  }

  else if (strcmp(preset_name, "club") == 0) {
    // Clipped-EDM intensity field with the drum kit cutting through it.
    CONFIG.LIGHTSHOW_MODE = LIGHT_MODE_DENSE_FORGE;
    SECONDARY_LIGHTSHOW_MODE = LIGHT_MODE_PERCUSSION_BURST;
    ENABLE_SECONDARY_LEDS = true;
    SECONDARY_MIRROR_ENABLED = true;
  }
}