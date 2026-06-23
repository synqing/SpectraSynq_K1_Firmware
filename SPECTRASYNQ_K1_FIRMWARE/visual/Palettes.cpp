#include <FastLED.h>

// Gradient palette definitions for the original cpt-city set and K1-native
// additions.
// Moved here verbatim from Palettes.h so that DEFINE_GRADIENT_PALETTE (which
// expands to an external-linkage definition) is emitted in exactly ONE
// translation unit. Palettes.h now forward-declares each via
// DECLARE_GRADIENT_PALETTE so multiple .cpp TUs can include it without
// multiple-definition link errors.

// Gradient palette "ib_jul01_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/ing/xmas/tn/ib_jul01.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 16 bytes of program space.
DEFINE_GRADIENT_PALETTE(ib_jul01_gp){
  0, 194, 1, 1,
  94, 1, 29, 18,
  132, 57, 131, 28,
  255, 113, 1, 1
};

// Gradient palette "es_vintage_57_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/vintage/tn/es_vintage_57.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 20 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_vintage_57_gp){
  0, 2, 1, 1,
  53, 18, 1, 0,
  104, 69, 29, 1,
  153, 167, 135, 10,
  255, 46, 56, 4
};

// Gradient palette "es_vintage_01_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/vintage/tn/es_vintage_01.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 32 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_vintage_01_gp){
  0, 4, 1, 1,
  51, 16, 0, 1,
  76, 97, 104, 3,
  101, 255, 131, 19,
  127, 67, 9, 4,
  153, 16, 0, 1,
  229, 4, 1, 1,
  255, 4, 1, 1
};

// Gradient palette "es_rivendell_15_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/rivendell/tn/es_rivendell_15.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 20 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_rivendell_15_gp){
  0, 1, 14, 5,
  101, 16, 36, 14,
  165, 56, 68, 30,
  242, 150, 156, 99,
  255, 150, 156, 99
};

// Gradient palette "rgi_15_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/ds/rgi/tn/rgi_15.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 36 bytes of program space.
DEFINE_GRADIENT_PALETTE(rgi_15_gp){
  0, 4, 1, 31,
  31, 55, 1, 16,
  63, 197, 3, 7,
  95, 59, 2, 17,
  127, 6, 2, 34,
  159, 39, 6, 33,
  191, 112, 13, 32,
  223, 56, 9, 35,
  255, 22, 6, 38
};

// Gradient palette "retro2_16_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/ma/retro2/tn/retro2_16.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 8 bytes of program space.
DEFINE_GRADIENT_PALETTE(retro2_16_gp){
  0, 188, 135, 1,
  255, 46, 7, 1
};

// Gradient palette "Analogous_1_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/red/tn/Analogous_1.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 20 bytes of program space.
DEFINE_GRADIENT_PALETTE(Analogous_1_gp){
  0, 3, 0, 255,
  63, 23, 0, 255,
  127, 67, 0, 255,
  191, 142, 0, 45,
  255, 255, 0, 0
};

// Gradient palette "es_pinksplash_08_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/pink_splash/tn/es_pinksplash_08.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 20 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_pinksplash_08_gp){
  0, 126, 11, 255,
  127, 197, 1, 22,
  175, 210, 157, 172,
  221, 157, 3, 112,
  255, 157, 3, 112
};

// Gradient palette "es_pinksplash_07_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/pink_splash/tn/es_pinksplash_07.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_pinksplash_07_gp){
  0, 229, 1, 1,
  61, 242, 4, 63,
  101, 255, 12, 255,
  127, 249, 81, 252,
  153, 255, 11, 235,
  193, 244, 5, 68,
  255, 232, 1, 5
};

// Gradient palette "Coral_reef_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/other/tn/Coral_reef.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 24 bytes of program space.
DEFINE_GRADIENT_PALETTE(Coral_reef_gp){
  0, 40, 199, 197,
  50, 10, 152, 155,
  96, 1, 111, 120,
  96, 43, 127, 162,
  139, 10, 73, 111,
  255, 1, 34, 71
};

// Gradient palette "es_ocean_breeze_068_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/ocean_breeze/tn/es_ocean_breeze_068.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 24 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_ocean_breeze_068_gp){
  0, 100, 156, 153,
  51, 1, 99, 137,
  101, 1, 68, 84,
  104, 35, 142, 168,
  178, 0, 63, 117,
  255, 1, 10, 10
};

// Gradient palette "es_ocean_breeze_036_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/ocean_breeze/tn/es_ocean_breeze_036.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 16 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_ocean_breeze_036_gp){
  0, 1, 6, 7,
  89, 1, 99, 111,
  153, 144, 209, 255,
  255, 0, 73, 82
};

// Gradient palette "departure_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/mjf/tn/departure.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 88 bytes of program space.
DEFINE_GRADIENT_PALETTE(departure_gp){
  0, 8, 3, 0,
  42, 23, 7, 0,
  63, 75, 38, 6,
  84, 169, 99, 38,
  106, 213, 169, 119,
  116, 255, 255, 255,
  138, 135, 255, 138,
  148, 22, 255, 24,
  170, 0, 255, 0,
  191, 0, 136, 0,
  212, 0, 55, 0,
  255, 0, 55, 0
};

// Gradient palette "es_landscape_64_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/landscape/tn/es_landscape_64.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 36 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_landscape_64_gp){
  0, 0, 0, 0,
  37, 2, 25, 1,
  76, 15, 115, 5,
  127, 79, 213, 1,
  128, 126, 211, 47,
  130, 188, 209, 247,
  153, 144, 182, 205,
  204, 59, 117, 250,
  255, 1, 37, 192
};

// Gradient palette "es_landscape_33_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/landscape/tn/es_landscape_33.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 24 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_landscape_33_gp){
  0, 1, 5, 0,
  19, 32, 23, 1,
  38, 161, 55, 1,
  63, 229, 144, 1,
  66, 39, 142, 74,
  255, 1, 4, 1
};

// Gradient palette "rainbowsherbet_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/ma/icecream/tn/rainbowsherbet.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(rainbowsherbet_gp){
  0, 255, 33, 4,
  43, 255, 68, 25,
  86, 255, 7, 25,
  127, 255, 82, 103,
  170, 255, 255, 242,
  209, 42, 255, 22,
  255, 87, 255, 65
};

// Gradient palette "gr65_hult_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/hult/tn/gr65_hult.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 24 bytes of program space.
DEFINE_GRADIENT_PALETTE(gr65_hult_gp){
  0, 247, 176, 247,
  48, 255, 136, 255,
  89, 220, 29, 226,
  160, 7, 82, 178,
  216, 1, 124, 109,
  255, 1, 124, 109
};

// Gradient palette "gr64_hult_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/hult/tn/gr64_hult.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 32 bytes of program space.
DEFINE_GRADIENT_PALETTE(gr64_hult_gp){
  0, 1, 124, 109,
  66, 1, 93, 79,
  104, 52, 65, 1,
  130, 115, 127, 1,
  150, 52, 65, 1,
  201, 1, 86, 72,
  239, 0, 55, 45,
  255, 0, 55, 45
};

// Gradient palette "GMT_drywet_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/gmt/tn/GMT_drywet.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(GMT_drywet_gp){
  0, 47, 30, 2,
  42, 213, 147, 24,
  84, 103, 219, 52,
  127, 3, 219, 207,
  170, 1, 48, 214,
  212, 1, 1, 111,
  255, 1, 7, 33
};

// Gradient palette "ib15_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/ing/general/tn/ib15.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 24 bytes of program space.
DEFINE_GRADIENT_PALETTE(ib15_gp){
  0, 113, 91, 147,
  72, 157, 88, 78,
  89, 208, 85, 33,
  107, 255, 29, 11,
  141, 137, 31, 39,
  255, 59, 33, 89
};

// Gradient palette "Fuschia_7_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/ds/fuschia/tn/Fuschia-7.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 20 bytes of program space.
DEFINE_GRADIENT_PALETTE(Fuschia_7_gp){
  0, 43, 3, 153,
  63, 100, 4, 103,
  127, 188, 5, 66,
  191, 161, 11, 115,
  255, 135, 20, 182
};

// Gradient palette "es_emerald_dragon_08_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/emerald_dragon/tn/es_emerald_dragon_08.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 16 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_emerald_dragon_08_gp){
  0, 97, 255, 1,
  101, 47, 133, 1,
  178, 13, 43, 1,
  255, 2, 10, 1
};

// Gradient palette "lava_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/neota/elem/tn/lava.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 52 bytes of program space.
DEFINE_GRADIENT_PALETTE(lava_gp){
  0, 0, 0, 0,
  46, 18, 0, 0,
  96, 113, 0, 0,
  108, 142, 3, 1,
  119, 175, 17, 1,
  146, 213, 44, 2,
  174, 255, 82, 4,
  188, 255, 115, 4,
  202, 255, 156, 4,
  218, 255, 203, 4,
  234, 255, 255, 4,
  244, 255, 255, 71,
  255, 255, 255, 255
};

// Gradient palette "fire_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/neota/elem/tn/fire.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(fire_gp){
  0, 1, 1, 0,
  76, 32, 5, 0,
  146, 192, 24, 0,
  197, 220, 105, 5,
  240, 252, 255, 31,
  250, 252, 255, 111,
  255, 255, 255, 255
};

// Gradient palette "Colorfull_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/atmospheric/tn/Colorfull.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 44 bytes of program space.
DEFINE_GRADIENT_PALETTE(Colorfull_gp){
  0, 10, 85, 5,
  25, 29, 109, 18,
  60, 59, 138, 42,
  93, 83, 99, 52,
  106, 110, 66, 64,
  109, 123, 49, 65,
  113, 139, 35, 66,
  116, 192, 117, 98,
  124, 255, 255, 137,
  168, 100, 180, 155,
  255, 22, 121, 174
};

// Gradient palette "Magenta_Evening_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/atmospheric/tn/Magenta_Evening.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(Magenta_Evening_gp){
  0, 71, 27, 39,
  31, 130, 11, 51,
  63, 213, 2, 64,
  70, 232, 1, 66,
  76, 252, 1, 69,
  108, 123, 2, 51,
  255, 46, 9, 35
};

// Gradient palette "Pink_Purple_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/atmospheric/tn/Pink_Purple.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 44 bytes of program space.
DEFINE_GRADIENT_PALETTE(Pink_Purple_gp){
  0, 19, 2, 39,
  25, 26, 4, 45,
  51, 33, 6, 52,
  76, 68, 62, 125,
  102, 118, 187, 240,
  109, 163, 215, 247,
  114, 217, 244, 255,
  122, 159, 149, 221,
  149, 113, 78, 188,
  183, 128, 57, 155,
  255, 146, 40, 123
};

// Gradient palette "Sunset_Real_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/atmospheric/tn/Sunset_Real.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(Sunset_Real_gp){
  0, 120, 0, 0,
  22, 179, 22, 0,
  51, 255, 104, 0,
  85, 167, 22, 18,
  135, 100, 0, 103,
  198, 16, 0, 130,
  255, 0, 0, 160
};

// Gradient palette "es_autumn_19_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/es/autumn/tn/es_autumn_19.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 52 bytes of program space.
DEFINE_GRADIENT_PALETTE(es_autumn_19_gp){
  0, 26, 1, 1,
  51, 67, 4, 1,
  84, 118, 14, 1,
  104, 137, 152, 52,
  112, 113, 65, 1,
  122, 133, 149, 59,
  124, 137, 152, 52,
  135, 113, 65, 1,
  142, 139, 154, 46,
  163, 113, 13, 1,
  204, 55, 3, 1,
  249, 17, 1, 1,
  255, 17, 1, 1
};

// Gradient palette "BlacK_Blue_Magenta_White_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/basic/tn/BlacK_Blue_Magenta_White.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(BlacK_Blue_Magenta_White_gp){
  0, 0, 0, 0,
  42, 0, 0, 45,
  84, 0, 0, 255,
  127, 42, 0, 255,
  170, 255, 0, 255,
  212, 255, 55, 255,
  255, 255, 255, 255
};

// Gradient palette "BlacK_Magenta_Red_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/basic/tn/BlacK_Magenta_Red.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 20 bytes of program space.
DEFINE_GRADIENT_PALETTE(BlacK_Magenta_Red_gp){
  0, 0, 0, 0,
  63, 42, 0, 45,
  127, 255, 0, 255,
  191, 255, 0, 45,
  255, 255, 0, 0
};

// Gradient palette "BlacK_Red_Magenta_Yellow_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/basic/tn/BlacK_Red_Magenta_Yellow.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 28 bytes of program space.
DEFINE_GRADIENT_PALETTE(BlacK_Red_Magenta_Yellow_gp){
  0, 0, 0, 0,
  42, 42, 0, 0,
  84, 255, 0, 0,
  127, 255, 0, 45,
  170, 255, 0, 255,
  212, 255, 55, 45,
  255, 255, 255, 0
};

// Gradient palette "Blue_Cyan_Yellow_gp", originally from
// http://soliton.vm.bytemark.co.uk/pub/cpt-city/nd/basic/tn/Blue_Cyan_Yellow.png.index.html
// converted for FastLED with gammas (2.6, 2.2, 2.5)
// Size: 20 bytes of program space.
DEFINE_GRADIENT_PALETTE(Blue_Cyan_Yellow_gp){
  0, 0, 0, 255,
  63, 0, 55, 255,
  127, 0, 255, 255,
  191, 42, 255, 45,
  255, 255, 255, 0
};

// K1-native palettes adapted from Captain-supplied screen references for
// WS2812B/LGP output. Near-white, beige, grey, and muddy screen stops are
// intentionally omitted; dark separators keep wide hue jumps from blending into
// low-chroma RGB mush on the acrylic plate.
DEFINE_GRADIENT_PALETTE(K1_Iris_Apricot_gp){
  0, 3, 2, 24,
  30, 40, 20, 130,
  58, 92, 45, 255,
  88, 190, 0, 180,
  118, 255, 32, 72,
  154, 255, 95, 0,
  196, 255, 150, 0,
  226, 255, 72, 0,
  255, 24, 1, 18
};

DEFINE_GRADIENT_PALETTE(K1_Tropical_Ultraviolet_gp){
  0, 0, 4, 18,
  28, 0, 42, 70,
  58, 0, 150, 160,
  88, 0, 220, 210,
  116, 82, 220, 0,
  144, 34, 150, 0,
  170, 0, 55, 10,
  190, 8, 3, 18,
  216, 165, 0, 130,
  238, 245, 0, 170,
  255, 12, 2, 28
};

DEFINE_GRADIENT_PALETTE(K1_Chameleon_Flare_gp){
  0, 0, 5, 35,
  32, 0, 90, 145,
  66, 0, 210, 230,
  98, 0, 130, 160,
  126, 120, 0, 255,
  154, 180, 0, 255,
  182, 235, 0, 175,
  212, 255, 130, 0,
  236, 255, 85, 0,
  255, 0, 5, 35
};

DEFINE_GRADIENT_PALETTE(K1_Coral_Sunset_gp){
  0, 18, 0, 3,
  34, 96, 8, 10,
  70, 210, 35, 40,
  105, 255, 72, 45,
  138, 255, 105, 20,
  172, 255, 150, 0,
  205, 255, 190, 20,
  232, 170, 0, 95,
  255, 18, 0, 3
};

DEFINE_GRADIENT_PALETTE(K1_Night_Sea_Amber_gp){
  0, 0, 3, 18,
  34, 0, 20, 90,
  68, 0, 85, 190,
  102, 0, 180, 220,
  132, 0, 110, 130,
  160, 0, 20, 40,
  182, 4, 2, 10,
  208, 255, 135, 0,
  234, 255, 75, 0,
  255, 35, 0, 8
};

DEFINE_GRADIENT_PALETTE(K1_Crimson_Gold_gp){
  0, 12, 0, 10,
  32, 65, 0, 45,
  64, 145, 0, 80,
  96, 220, 0, 70,
  128, 255, 36, 24,
  160, 255, 92, 0,
  192, 255, 145, 0,
  218, 255, 190, 40,
  240, 255, 70, 120,
  255, 12, 0, 10
};

// Second adaptation pass (2026-06-11): hue families present in the screen
// references but not covered by the first six K1-native palettes.

// Hot pink -> magenta -> violet -> indigo ramp ("Vibrant" row 1 / "Ascend").
DEFINE_GRADIENT_PALETTE(K1_Ultraviolet_Ascend_gp){
  0, 8, 0, 24,
  34, 30, 0, 130,
  70, 70, 0, 235,
  104, 130, 0, 255,
  138, 190, 0, 220,
  172, 235, 0, 160,
  206, 255, 8, 96,
  232, 255, 0, 60,
  255, 8, 0, 24
};

// Deep blue -> indigo -> violet body with a single gold accent ("Naberius").
// Dark separator before the gold stop prevents violet->gold blending through
// muddy mauve mid-tones.
DEFINE_GRADIENT_PALETTE(K1_Naberius_Gold_gp){
  0, 2, 0, 20,
  34, 10, 0, 140,
  70, 28, 0, 225,
  106, 70, 10, 255,
  140, 120, 0, 255,
  170, 40, 0, 120,
  190, 6, 2, 14,
  212, 255, 140, 0,
  236, 255, 95, 0,
  255, 2, 0, 20
};

// Plum -> burgundy -> magenta -> hot pink ("Vepar"; cream stop dropped).
DEFINE_GRADIENT_PALETTE(K1_Vepar_Pink_gp){
  0, 14, 0, 14,
  38, 64, 0, 48,
  78, 150, 0, 80,
  116, 220, 0, 120,
  152, 255, 0, 150,
  188, 255, 30, 120,
  220, 255, 70, 150,
  255, 14, 0, 14
};

// Green -> teal -> cyan -> azure -> violet -> magenta cool sweep ("Flourish").
DEFINE_GRADIENT_PALETTE(K1_Flourish_Sweep_gp){
  0, 0, 16, 6,
  34, 0, 170, 40,
  66, 0, 220, 120,
  98, 0, 210, 210,
  130, 0, 120, 255,
  162, 60, 30, 255,
  194, 140, 0, 255,
  224, 220, 0, 170,
  255, 16, 0, 14
};

// A/B probe for the dark-anchor hypothesis: same hue family as
// K1_Ultraviolet_Ascend_gp but bright end-to-end (no dark anchors or
// separators). Chroma-driven modes map pitch class across the full palette
// range, so dark anchors become per-note dead zones; this variant lets
// eyes-on compare the two treatments on the same musical material.
DEFINE_GRADIENT_PALETTE(K1_Ultraviolet_Bright_gp){
  0, 255, 8, 96,
  52, 235, 0, 160,
  104, 190, 0, 220,
  156, 130, 0, 255,
  208, 70, 0, 235,
  255, 30, 0, 130
};
