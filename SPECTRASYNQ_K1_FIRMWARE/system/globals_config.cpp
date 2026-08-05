// globals_config.cpp
// ============================================================================
// PIO-SPIKE2 (2026-05-25) — Aggregate-init relocation byte-identity proof.
//
// This is the FIRST hand-written .cpp translation unit in the firmware (the
// project is otherwise a single .ino TU). It holds the file-scope
// aggregate-initialised data that Phase B (Row 3 globals partition) needs to
// move out of globals.h:
//
//   - conf CONFIG            — factory-default config (PHOTONS/MIRROR/PALETTE/...)
//   - conf CONFIG_DEFAULTS   — runtime reset target (zero-init; memcpy'd in system.h)
//   - set_led_count_from_define() — __attribute__((constructor)) that pins LED_COUNT
//   - float a_weight_table[13][2] — A-weighting LUT (mutated at runtime in system.h)
//
// globals.h now carries only `extern` declarations for these. The proof: the
// emitted initialiser bytes for CONFIG and a_weight_table are byte-identical
// before and after this relocation (objdump per-symbol comparison in
// docs/k1-refactor-2026-05/spike2/). CONFIG_DEFAULTS is zero-init (BSS), so it
// has no initialiser bytes to compare.
//
// Include hygiene: globals.h transitively provides constants.h (LIGHT_MODE_GDFT,
// NUM_MODES, LED_NEOPIXEL, DEFAULT_SAMPLE_RATE, LED_COUNT_VALUE) and FastLED.h
// (GRB). The `enum lightshow_modes` was relocated from the .ino to constants.h
// in the same commit so it is visible to THIS translation unit, not only the
// .ino's.
// ============================================================================

// Include set (PIO-SPIKE2 findings #1 + #2):
//
// Finding #1 (Class-C include hygiene): constants.h references SQ15x16 / CRGB16
// but only #includes <FixedPoints.h> — NOT <FixedPointsCommon.h> (which is where
// `using SQ15x16 = SFixed<15,16>` actually lives). The .ino works only because it
// includes <FixedPointsCommon.h> + <FastLED.h> before constants.h. A fresh TU
// must replicate that order explicitly.
//
// Finding #2 (ODR): including the full globals.h — OR constants.h — here emits
// their non-extern object definitions in a SECOND TU → mass "multiple definition"
// link errors (globals.h: ~277 globals; constants.h: incandescent_lookup,
// note_colors, hue_lookup, notes, gamma8_lut, dither_table). So this TU includes
// ONLY config_types.h, the slim ODR-safe header carrying `struct conf` plus the
// enums/macros the CONFIG initialiser needs (LIGHT_MODE_GDFT / DEFAULT_SAMPLE_RATE
// / LED_NEOPIXEL / LED_COUNT_VALUE). FastLED supplies GRB.
#include <FastLED.h>
#include "config_types.h"

// ----------------------------------------------------------------------------
// Factory defaults of the CONFIG struct ---------------------------------------
conf CONFIG = {
  // Synced values
  1.00, // PHOTONS
  0.00, // CHROMA
  0.05, // MOOD
  LIGHT_MODE_BLOOM, // LIGHTSHOW_MODE (default moved off disabled GDFT, 2026-06-02)
  true,           // MIRROR_ENABLED

  // Private values
  DEFAULT_SAMPLE_RATE, // SAMPLE_RATE
  12,                  // NOTE_OFFSET
  1.0f,                // SQUARE_ITER
  LED_NEOPIXEL,        // LED_TYPE
  161,                 // LED_COUNT (will be overwritten below)
  GRB,                 // LED_COLOR_ORDER
  true,                // LED_INTERPOLATION
  DEFAULT_SAMPLES_PER_CHUNK, // SAMPLES_PER_CHUNK
  2.4,                 // SENSITIVITY
  true,                // BOOT_ANIMATION
  DEFAULT_SWEET_SPOT_MIN_LEVEL, // SWEET_SPOT_MIN_LEVEL (fallback only; measured cal must provide provenance)
  30000,               // SWEET_SPOT_MAX_LEVEL
  0,                   // DC_OFFSET
  60,                  // CHROMAGRAM_RANGE
  CHROMA_PROFILE_DEFAULT, // CHROMA_PROFILE (= v40102: NOTE_OFFSET=12 / CHROMAGRAM_RANGE=60)
  false,               // STANDBY_DIMMING (off by default — turn back on via `standby_dimming=true` if you want auto-dim in silence)
  false,               // REVERSE_ORDER
  false,               // RESERVED_CONFIG_BYTE, kept to preserve saved-config layout
  2500,                // MAX_CURRENT_MA (was 1500; raised for 5V/~2.5A PSU headroom)
  true,                // TEMPORAL_DITHERING
  true,                // AUTO_COLOR_SHIFT
  0.00,                // INCANDESCENT_FILTER
  false,               // INCANDESCENT_MODE
  0.00,                // BULB_OPACITY
  1.00,                // SATURATION
  1.0f,                // PRISM_COUNT
  false,               // BASE_COAT
  0.00,                // VU_LEVEL_FLOOR
  0.00,                // BASE_COAT_INTENSITY (Default 0.0 = base coat off; user enables via encoder 0. Phase 1 2026-05-20: comment corrected from "full intensity"; the value has always been 0.0.)

  // --- Palette Defaults ---
  0,                   // PALETTE_INDEX (Default to the first palette)
  false,               // PALETTE_MODE_ENABLED (Default to off)
};

// Ensure LED count is set from the single #define in constants.h
__attribute__((constructor)) static void set_led_count_from_define() {
    CONFIG.LED_COUNT = LED_COUNT_VALUE;
}

conf CONFIG_DEFAULTS; // Used for resetting to default values at runtime

#ifdef K1_BOOTLOOP_GUARD_V1
// N2b: boot-loop safe-mode flag (declared extern in globals.h). False = normal boot.
bool k1_boot_safe_mode = false;
#endif

// ----------------------------------------------------------------------------
// A-weighting lookup table (parsed/mutated in system.h) -----------------------
float a_weight_table[13][2] = {
  { 10,    -70.4 },  // hz, db
  { 20,    -50.5 },
  { 40,    -34.6 },
  { 80,    -22.5 },
  { 160,   -13.4 },
  { 315,    -6.6 },
  { 630,    -1.9 },
  { 1000,    0.0 },
  { 1250,    0.6 },
  { 2500,    1.3 },
  { 5000,    0.5 },
  { 10000,  -2.5 },
  { 20000,  -9.3 }
};
