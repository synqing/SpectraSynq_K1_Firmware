#ifndef PALETTES_H
#define PALETTES_H

#include <FastLED.h>

// From ColorWavesWithPalettes by Mark Kriegsman: https://gist.github.com/kriegsman/8281905786e8b2632aeb

// Gradient colour palette definitions for the curated cpt-city and K1-native
// colour palettes.
//    956 bytes of PROGMEM for the original cpt-city palettes,
//   +618 bytes of PROGMEM for gradient palette code (AVR), plus the K1-native
//   additions below.

// Gradient palette data definitions live in Palettes.cpp (one definition only).
// Each palette is forward-declared here via DECLARE_GRADIENT_PALETTE so that
// any number of .cpp translation units may include this header without causing
// "multiple definition" link errors. DEFINE_GRADIENT_PALETTE expands to an
// external-linkage definition and therefore must appear in exactly one TU.

DECLARE_GRADIENT_PALETTE(ib_jul01_gp);
DECLARE_GRADIENT_PALETTE(es_vintage_57_gp);
DECLARE_GRADIENT_PALETTE(es_vintage_01_gp);
DECLARE_GRADIENT_PALETTE(es_rivendell_15_gp);
DECLARE_GRADIENT_PALETTE(rgi_15_gp);
DECLARE_GRADIENT_PALETTE(retro2_16_gp);
DECLARE_GRADIENT_PALETTE(Analogous_1_gp);
DECLARE_GRADIENT_PALETTE(es_pinksplash_08_gp);
DECLARE_GRADIENT_PALETTE(es_pinksplash_07_gp);
DECLARE_GRADIENT_PALETTE(Coral_reef_gp);
DECLARE_GRADIENT_PALETTE(es_ocean_breeze_068_gp);
DECLARE_GRADIENT_PALETTE(es_ocean_breeze_036_gp);
DECLARE_GRADIENT_PALETTE(departure_gp);
DECLARE_GRADIENT_PALETTE(es_landscape_64_gp);
DECLARE_GRADIENT_PALETTE(es_landscape_33_gp);
DECLARE_GRADIENT_PALETTE(rainbowsherbet_gp);
DECLARE_GRADIENT_PALETTE(gr65_hult_gp);
DECLARE_GRADIENT_PALETTE(gr64_hult_gp);
DECLARE_GRADIENT_PALETTE(GMT_drywet_gp);
DECLARE_GRADIENT_PALETTE(ib15_gp);
DECLARE_GRADIENT_PALETTE(Fuschia_7_gp);
DECLARE_GRADIENT_PALETTE(es_emerald_dragon_08_gp);
DECLARE_GRADIENT_PALETTE(lava_gp);
DECLARE_GRADIENT_PALETTE(fire_gp);
DECLARE_GRADIENT_PALETTE(Colorfull_gp);
DECLARE_GRADIENT_PALETTE(Magenta_Evening_gp);
DECLARE_GRADIENT_PALETTE(Pink_Purple_gp);
DECLARE_GRADIENT_PALETTE(Sunset_Real_gp);
DECLARE_GRADIENT_PALETTE(es_autumn_19_gp);
DECLARE_GRADIENT_PALETTE(BlacK_Blue_Magenta_White_gp);
DECLARE_GRADIENT_PALETTE(BlacK_Magenta_Red_gp);
DECLARE_GRADIENT_PALETTE(BlacK_Red_Magenta_Yellow_gp);
DECLARE_GRADIENT_PALETTE(Blue_Cyan_Yellow_gp);
DECLARE_GRADIENT_PALETTE(K1_Iris_Apricot_gp);
DECLARE_GRADIENT_PALETTE(K1_Tropical_Ultraviolet_gp);
DECLARE_GRADIENT_PALETTE(K1_Chameleon_Flare_gp);
DECLARE_GRADIENT_PALETTE(K1_Coral_Sunset_gp);
DECLARE_GRADIENT_PALETTE(K1_Night_Sea_Amber_gp);
DECLARE_GRADIENT_PALETTE(K1_Crimson_Gold_gp);
DECLARE_GRADIENT_PALETTE(K1_Ultraviolet_Ascend_gp);
DECLARE_GRADIENT_PALETTE(K1_Naberius_Gold_gp);
DECLARE_GRADIENT_PALETTE(K1_Vepar_Pink_gp);
DECLARE_GRADIENT_PALETTE(K1_Flourish_Sweep_gp);
DECLARE_GRADIENT_PALETTE(K1_Ultraviolet_Bright_gp);


// Single array of defined gradient palettes.
// This will let us programmatically choose one based on
// a number, rather than having to activate each explicitly
// by name every time.
// Since it is const, this array could also be moved
// into PROGMEM to save SRAM, but for simplicity of illustration
// we'll keep it in a regular SRAM array.
//
// This list of colour palettes acts as a "playlist"; you can
// add or delete, or re-arrange as you wish.
const TProgmemRGBGradientPaletteRef gGradientPalettes[] = {
  Sunset_Real_gp,
  es_rivendell_15_gp,
  es_ocean_breeze_036_gp,
  rgi_15_gp,
  retro2_16_gp,
  Analogous_1_gp,
  es_pinksplash_08_gp,
  Coral_reef_gp,
  es_ocean_breeze_068_gp,
  es_pinksplash_07_gp,
  es_vintage_01_gp,
  departure_gp,
  es_landscape_64_gp,
  es_landscape_33_gp,
  rainbowsherbet_gp,
  gr65_hult_gp,
  gr64_hult_gp,
  GMT_drywet_gp,
  ib_jul01_gp,
  es_vintage_57_gp,
  ib15_gp,
  Fuschia_7_gp,
  es_emerald_dragon_08_gp,
  lava_gp,
  fire_gp,
  Colorfull_gp,
  Magenta_Evening_gp,
  Pink_Purple_gp,
  es_autumn_19_gp,
  BlacK_Blue_Magenta_White_gp,
  BlacK_Magenta_Red_gp,
  BlacK_Red_Magenta_Yellow_gp,
  Blue_Cyan_Yellow_gp,
  K1_Iris_Apricot_gp,
  K1_Tropical_Ultraviolet_gp,
  K1_Chameleon_Flare_gp,
  K1_Coral_Sunset_gp,
  K1_Night_Sea_Amber_gp,
  K1_Crimson_Gold_gp,
  K1_Ultraviolet_Ascend_gp,
  K1_Naberius_Gold_gp,
  K1_Vepar_Pink_gp,
  K1_Flourish_Sweep_gp,
  K1_Ultraviolet_Bright_gp
};

// Count of how many gradients are defined:
const uint8_t gGradientPaletteCount =
  sizeof(gGradientPalettes) / sizeof(TProgmemRGBGradientPaletteRef);

// Legacy extern declarations retained for existing include sites.
extern const TProgmemRGBGradientPaletteRef gGradientPalettes[];

extern const uint8_t gGradientPaletteCount;

// Definition of palette name pointers in PROGMEM for UI/debug output
const char* const paletteNames[] PROGMEM = {
  "Sunset_Real_gp",
  "es_rivendell_15_gp",
  "es_ocean_breeze_036_gp",
  "rgi_15_gp",
  "retro2_16_gp",
  "Analogous_1_gp",
  "es_pinksplash_08_gp",
  "Coral_reef_gp",
  "es_ocean_breeze_068_gp",
  "es_pinksplash_07_gp",
  "es_vintage_01_gp",
  "departure_gp",
  "es_landscape_64_gp",
  "es_landscape_33_gp",
  "rainbowsherbet_gp",
  "gr65_hult_gp",
  "gr64_hult_gp",
  "GMT_drywet_gp",
  "ib_jul01_gp",
  "es_vintage_57_gp",
  "ib15_gp",
  "Fuschia_7_gp",
  "es_emerald_dragon_08_gp",
  "lava_gp",
  "fire_gp",
  "Colorfull_gp",
  "Magenta_Evening_gp",
  "Pink_Purple_gp",
  "es_autumn_19_gp",
  "BlacK_Blue_Magenta_White_gp",
  "BlacK_Magenta_Red_gp",
  "BlacK_Red_Magenta_Yellow_gp",
  "Blue_Cyan_Yellow_gp",
  "K1_Iris_Apricot_gp",
  "K1_Tropical_Ultraviolet_gp",
  "K1_Chameleon_Flare_gp",
  "K1_Coral_Sunset_gp",
  "K1_Night_Sea_Amber_gp",
  "K1_Crimson_Gold_gp",
  "K1_Ultraviolet_Ascend_gp",
  "K1_Naberius_Gold_gp",
  "K1_Vepar_Pink_gp",
  "K1_Flourish_Sweep_gp",
  "K1_Ultraviolet_Bright_gp"
};

#endif // PALETTES_H
