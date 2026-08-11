#ifndef CONFIG_TYPES_H
#define CONFIG_TYPES_H

// config_types.h
// ============================================================================
// PIO-SPIKE2 (2026-05-25) — slim declarations header for the config aggregate.
//
// The split-justification matrix (02-SPLIT-JUSTIFICATION-MATRIX.md §8 Q2) names
// the Phase B pattern explicitly: "create a slim declarations header plus one
// compiled definition unit." This header is that slim declarations header for
// the `conf` config struct.
//
// Why it exists: globals_config.cpp needs the `conf` TYPE to define `CONFIG` and
// `CONFIG_DEFAULTS`, but it must NOT pull in the ~277 object definitions still
// living in globals.h (doing so triggers mass ODR "multiple definition" link
// errors — the second failure class observed in this spike). Isolating just the
// type here lets the definition TU see the type without the object sea.
//
// `conf` is pure POD (float / uintN_t / bool / int32_t) — it references no
// SQ15x16 / CRGB16 / FastLED types, so this header is dependency-light.
// ============================================================================

#include <stdint.h>
#include <stdbool.h>

// ------------------------------------------------------------
// ODR-safe symbols the CONFIG aggregate initialiser needs -----
// PIO-SPIKE2 (2026-05-25): the CONFIG initialiser in globals_config.cpp
// references these enums/macros. They are ODR-safe (no storage), so they can be
// shared by both the .ino TU and the definition TU. They previously lived in
// constants.h interleaved with the (deferred, header-only) object definitions
// (incandescent_lookup, note_colors, hue_lookup, ...) which a second TU CANNOT
// re-include without "multiple definition" link errors. constants.h now
// #includes this header so there is a single source of truth (no duplication).

#ifndef DEFAULT_SAMPLE_RATE
#define DEFAULT_SAMPLE_RATE 12800
#endif

#ifndef DEFAULT_SAMPLES_PER_CHUNK
#define DEFAULT_SAMPLES_PER_CHUNK 96
#endif

#ifndef DEFAULT_SWEET_SPOT_MIN_LEVEL
#define DEFAULT_SWEET_SPOT_MIN_LEVEL 350U
#endif

#ifndef DEFAULT_AUDIO_RESPONSE_GAIN
#define DEFAULT_AUDIO_RESPONSE_GAIN 1.0f
#endif

#define AUDIO_RESPONSE_GAIN_MIN 0.25f
#define AUDIO_RESPONSE_GAIN_MAX 4.0f

#define K1_SENSITIVITY_MIN 0.10f
#define K1_SENSITIVITY_MAX 20.0f

#ifndef K1_TEMPO_NOVELTY_DECIMATION
#define K1_TEMPO_NOVELTY_DECIMATION 3U
#endif

// Spectral analysis window (Hann) for the GDFT magnitude path. DEFAULT OFF:
// production is byte-identical (the windowed branch in GDFT.h is compiled out).
// Enable for an A/B device test with -DK1_SPECTRAL_WINDOW_V1=1; reduces inter-bin
// spectral leakage at the cost of a per-sample multiply on Core 0. Amplitude is
// preserved by the explicit Hann coherent gain (k1_spectral_honesty.h). Visual
// impact is unproven — Captain eyes-on required before any default flip.
#ifndef K1_SPECTRAL_WINDOW_V1
#define K1_SPECTRAL_WINDOW_V1 0
#endif

// Exact-frequency ("true centre") Goertzel coefficient for the GDFT path. DEFAULT
// OFF: production is byte-identical (the #else in precompute_goertzel_constants()
// reproduces the legacy rounded-k coefficient verbatim). When ON, each
// representable bin (target_freq <= Nyquist) resonates at its EXACT note
// frequency via the generalized (non-integer-k) Goertzel: w = 2*PI*target/fs,
// coeff = 2*cos(w). Above Nyquist the note is not physically representable, so
// those bins KEEP rounded-k (their response is aliased either way; the
// above-Nyquist raw-bin policy is a separate lane). Measurement evidence: rounded
// k pulls every centre below its label (A4 440 Hz -> ~420 Hz; device-confirmed on
// bench K1 B489A500 that 440 Hz lights the B4-labelled bin 26). Visual/perceptual
// impact unproven — device A/B + Captain eyes-on required before any default flip.
#ifndef K1_GDFT_TRUE_CENTER_V1
#define K1_GDFT_TRUE_CENTER_V1 0
#endif

// int64 magnitude-squared for the GDFT Goertzel. DEFAULT OFF: production is
// byte-identical (the #else in process_GDFT() reproduces the legacy int32 formula
// verbatim). Device-proven (bench K1 B489A500, GDFTP5 telemetry 2026-06-21): the
// int32 magnitude `q2*q2 + q1*q1 - (mult>>14)*q2` OVERFLOWS at sustained resonance
// (the undamped resonator grows q~160k; q*q ~2.6e10 wraps int32 -> negative -> the
// `if(<0)=0` clamp ZEROES the bin). Near-resonance neighbour bins read exactly 0.00
// in BOTH the rounded-k and true-centre paths. ON widens ONLY the magnitude-squared
// expression to int64 (the recurrence q0/q1/q2 is unchanged this pass). Adds an
// int64 multiply per bin on Core 0 -> perf/MabuTrace pass owed before any default
// flip. Visual impact unproven; default flip needs device A/B + Captain eyes-on.
#ifndef K1_GDFT_INT64_MAGNITUDE_V1
#define K1_GDFT_INT64_MAGNITUDE_V1 0
#endif

// int64 recurrence-multiply for the GDFT Goertzel inner loop. DEFAULT OFF:
// production is byte-identical (the #else in process_GDFT() reproduces the legacy
// recurrence verbatim). Device-proven 2nd overflow (bench K1 B489A500, leg C of the
// int64-magnitude A/B): the legacy loop `mult = coeff_q14 * (int32_t)q1` computes
// the product in int32 BEFORE storing to int64, so it overflows once q1 > ~67k
// (coeff_q14 ~32k); at the harness's sustained 16000-amplitude tone q reaches ~160k,
// corrupting the resonator BEFORE the (int64) magnitude is taken — so int64
// magnitude alone could not deliver correct true-centre argmax. ON computes the
// product with int64 operands ((int64_t)coeff_q14 * (int64_t)q1) before the >>14.
// q-state (q0/q1/q2) stays int32: q ~160k << INT32_MAX, so the proven bug is the
// MULTIPLY width, not the q range (the harness reports a q0 overflow count to
// confirm). Acceptance requires INT64_MAGNITUDE=1 AND INT64_RECURRENCE=1 together.
#ifndef K1_GDFT_INT64_RECURRENCE_V1
#define K1_GDFT_INT64_RECURRENCE_V1 0
#endif

// Number of Goertzel frequency bins (canvas pixels). Single source of truth for
// the definition TUs (globals.cpp) that size spectrogram_smooth[] without
// including constants.h. constants.h mirrors this same value (identical token →
// legal redefinition) next to its NATIVE_RESOLUTION derivation comment.
#define NUM_FREQS 80

// LED strip mode selection: 1=61 LEDs, 2=91 LEDs, 3=160 LEDs (default).
#define LED_STRIP_MODE 3
#if defined(K1_UNIT2_IM69D_V1)
  // Unit 2 hardware truth (Captain, 2026-08-11): two independent physical
  // WS2812B channels of 206 pixels each. The effect/render canvas remains 160;
  // both output paths resample that canvas onto their physical strip.
  #define LED_COUNT_VALUE 206
  #define SECONDARY_LED_COUNT_VALUE 206
#else
#ifdef K1_CUSTOM_LED_V1
  // Custom single-channel wall-bounce build (2026-07-06): 224 LEDs on the primary
  // GPIO only, secondary channel dropped (see the .ino:670/693 guards). The 160-px
  // render canvas (NATIVE_RESOLUTION) is UNCHANGED — scale_to_strip() resamples it
  // onto 224 physical LEDs, exactly as strip-modes 61/91/160 already do. Output
  // buffers are heap-allocated to CONFIG.LED_COUNT so 224 is memory-safe. Flag-gated:
  // when K1_CUSTOM_LED_V1 is unset every env resolves 160 -> byte-identical.
  #define LED_COUNT_VALUE 224
  #define SECONDARY_LED_COUNT_VALUE 160
#elif LED_STRIP_MODE == 1
  #define LED_COUNT_VALUE 61
  #define SECONDARY_LED_COUNT_VALUE 160
#elif LED_STRIP_MODE == 2
  #define LED_COUNT_VALUE 91
  #define SECONDARY_LED_COUNT_VALUE 160
#else
  // Default to 160 LEDs (K1 / SB v9 hardware: 160 per channel)
  #define LED_COUNT_VALUE 160
  #define SECONDARY_LED_COUNT_VALUE 160
#endif
#endif

enum led_types {
  LED_NEOPIXEL,
  LED_NEOPIXEL_X2,
  LED_DOTSTAR
};

// Lightshow modes by name. Enumerator order is load-bearing: LIGHT_MODE_GDFT == 0
// and NUM_MODES tracks the append-only roster. IDs are persisted in CONFIG; never
// reorder existing entries. WAVEFORM_TEMPO appended as ID 18 on wf/wip-tempo,
// 2026-06-03; TEMPO_RIVER 19 and TEMPO_COMET 20 appended 2026-06-04; BEAT_PALETTE
// removed 2026-06-04 (Captain 0/10). SNAPWAVE/PULSE PRISM promoted as IDs 22/23;
// the short-lived SAT A/B aliases that once occupied 24/25 are retired because
// 24/25 are now real current modes and must survive persisted config reloads.
enum lightshow_modes {
  LIGHT_MODE_GDFT,                  // ------------- GDFT - Goertzel-based Discrete Fourier Transform
  LIGHT_MODE_GDFT_CHROMAGRAM,       // -- Chromagram of GDFT
  LIGHT_MODE_GDFT_CHROMAGRAM_DOTS,  // -- Chromagram of GDFT
  LIGHT_MODE_BLOOM,                 // -- Bloom Mode
  LIGHT_MODE_VU_DOT,                // -- Not a real VU, just a dance-y LED show
  LIGHT_MODE_KALEIDOSCOPE,          // -- 2D Perlin noise driven by low/mid/high onsets
  LIGHT_MODE_QUANTUM_COLLAPSE,      // -- Added new mode
  LIGHT_MODE_WAVEFORM_FAST,         // -- Current Waveform behaviour, preserved as fast variant
  LIGHT_MODE_WAVEFORM,              // -- Centre-origin tunable Waveform mode
  LIGHT_MODE_BLOOM_FAST,            // -- Faster centre-origin Bloom variant
  LIGHT_MODE_VU,                    // -- Centre-origin VU bar
  LIGHT_MODE_WAVEFORM_HYBRID,       // -- Waveform history seed with centre-origin trails
  LIGHT_MODE_AURORA,                // -- Colour-in-motion: palette flowing aurora (BLOOM-family)
  LIGHT_MODE_COMET,                 // -- Onset-driven traveling comets + trail (WAVEFORM-family)
  LIGHT_MODE_SPECTRUM_RIVER,        // -- Spectrum mapped to space, flowed outward (WAVEFORM-family)
  LIGHT_MODE_SPECTRUM_RIVER_V2,     // -- Spectrum River, drift/persistence breathing with bass energy
  LIGHT_MODE_EMBER,                 // -- Energy-bloom glow, centre-anchored core (continuous, organic)
  LIGHT_MODE_EMBER_V2,              // -- Ember, full-strip variant (MOOD-driven scroll)
  LIGHT_MODE_WAVEFORM_TEMPO,        // -- Tempo-phase-locked continuous scroll velocity (WAVEFORM-family, WIP-1)
  LIGHT_MODE_TEMPO_RIVER,           // -- Spectrum-River flow VELOCITY locked to beat phase (Transport; 2026-06-04)
  LIGHT_MODE_TEMPO_COMET,           // -- Beat-grid-locked travelling comets (Particle; 2026-06-04)
  LIGHT_MODE_DENSE_FORGE,           // -- Dense/clipped EDM: onset-density intensity, confidence-clamped (2026-06-07)
  LIGHT_MODE_SNAPWAVE,              // -- Tonal chroma phase-interference oscillator with tanh snap (2026-06-07)
  LIGHT_MODE_PULSE_PRISM,           // -- Kick-primary centre shockwave rings for dense EDM (2026-06-07)
  LIGHT_MODE_DENSE_FORGE_CHORD,     // -- Dense Forge variant: chord-root hue anchor (Tier 1 item 1; 2026-06-11)
  LIGHT_MODE_CHROMA_CONSTELLATION,  // -- 12 pitch-class stars, circle-of-fifths positions, outward transport (2026-06-11)
  LIGHT_MODE_PERCUSSION_BURST,      // -- Event-gated kick/snare/hihat spatial decomposition, particle pool (2026-06-11)
  LIGHT_MODE_TEMPO_COMET_ANTICIPATE,// -- Tempo Comet variant: comets decelerate INTO the next beat (2026-06-11)
  LIGHT_MODE_RIVER_SURGE,           // -- Spectrum River v2 variant: build/drop macro-dynamics axis (2026-06-11)
  LIGHT_MODE_TEMPO_RIVER_WALK,      // -- Tempo River variant: palette walks one step per bar (2026-06-11)
  // ID-reserve slots 30/31 keep WAVEFORM_HYBRID_K1 at ordinal 32 (append-only
  // parity with lane/gem-port-beat-pulse). Bodies not shipped here; both are
  // unselectable via light_mode_is_enabled().
  LIGHT_MODE_BEAT_PULSE,            // -- ID reserve 30 (tombstone; no body on this branch)
  LIGHT_MODE_BLOOM_BT,              // -- ID reserve 31 (tombstone; no body on this branch)
  LIGHT_MODE_WAVEFORM_HYBRID_K1,    // -- Waveform Hybrid K1: amplitude-bouncing dot + decaying scroll trail (2026-08-05 all-builds)

  NUM_MODES  // used to know the length of this list if it changes in the future
};

// Modes removed from the product (Captain 2026-06-02): unfit for purpose.
// Kept as enumerators for ID stability (append-only rule); made unreachable in
// every selection path (cycle / set_mode / secondary / director / boot) via
// these helpers. Disabled: GDFT(0), VU_DOT(4), KALEIDOSCOPE(5),
// CHROMAGRAM(1), CHROMAGRAM_DOTS(2), QUANTUM_COLLAPSE(6), VU(10).
inline bool light_mode_is_enabled(uint8_t mode) {
  switch (mode) {
    case LIGHT_MODE_GDFT:
    case LIGHT_MODE_GDFT_CHROMAGRAM:
    case LIGHT_MODE_GDFT_CHROMAGRAM_DOTS:
    case LIGHT_MODE_VU_DOT:
    case LIGHT_MODE_KALEIDOSCOPE:
    case LIGHT_MODE_QUANTUM_COLLAPSE:
    case LIGHT_MODE_VU:
    case LIGHT_MODE_EMBER_V2:   // pulled 2026-06-02 (Captain: "fucked, not going anywhere"); code kept, unselectable
    case LIGHT_MODE_BEAT_PULSE: // ID reserve 30 — unselectable on this branch (no effect body)
    case LIGHT_MODE_BLOOM_BT:   // ID reserve 31 — unselectable on this branch (no effect body)
      return false;
    default:
      return true;
  }
}

// Return `mode` if enabled, else the next enabled mode scanning in `dir`
// (>=0 forward, <0 backward). Falls back to `mode` only if none are enabled.
inline uint8_t light_mode_next_enabled(uint8_t mode, int dir) {
  const int step = (dir < 0) ? -1 : 1;
  for (uint8_t i = 0; i < NUM_MODES; i++) {
    int m = (int(mode) + step * int(i)) % int(NUM_MODES);
    if (m < 0) m += NUM_MODES;
    if (light_mode_is_enabled((uint8_t)m)) return (uint8_t)m;
  }
  return mode;
}

inline uint8_t light_mode_sanitize_persisted(uint8_t mode) {
  if (mode >= NUM_MODES) return LIGHT_MODE_BLOOM;
  return light_mode_is_enabled(mode) ? mode : light_mode_next_enabled(mode, 1);
}

// Chromagram profile presets. Front-end for the NOTE_OFFSET + CHROMAGRAM_RANGE
// pair (previously toggled only via the raw `bass_mode` command). The chromagram
// is shared/global audio analysis (computed once per frame), so this is a single
// global preset, NOT a per-channel setting. CHROMA_PROFILE_DEFAULT == 0 maps to
// the v40102 values (NOTE_OFFSET=12 / CHROMAGRAM_RANGE=60) so the DEFAULT profile
// leaves the chromagram bit-identical. Enumerator order is load-bearing
// (DEFAULT == 0 is the CONFIG default).
enum ChromaProfile {
  CHROMA_PROFILE_DEFAULT = 0, // NOTE_OFFSET=12, CHROMAGRAM_RANGE=60 (= v40102)
  CHROMA_PROFILE_BASS    = 1, // NOTE_OFFSET=0,  CHROMAGRAM_RANGE=24 (bass-mode alias)
  CHROMA_PROFILE_FULL    = 2  // NOTE_OFFSET=0,  CHROMAGRAM_RANGE=NUM_FREQS
};

// ------------------------------------------------------------
// Configuration structure ------------------------------------
struct conf {
  // Synced values
  float   PHOTONS;
  float   CHROMA;
  float   MOOD;
  uint8_t LIGHTSHOW_MODE;
  bool    MIRROR_ENABLED;

  // Private values
  uint32_t SAMPLE_RATE;
  uint8_t  NOTE_OFFSET;
  float    SQUARE_ITER;
  uint8_t  LED_TYPE;
  uint16_t LED_COUNT;
  uint16_t LED_COLOR_ORDER;
  bool     LED_INTERPOLATION;
  uint16_t SAMPLES_PER_CHUNK;
  float    SENSITIVITY;
  bool     BOOT_ANIMATION;
  uint32_t SWEET_SPOT_MIN_LEVEL;
  uint32_t SWEET_SPOT_MAX_LEVEL;
  int32_t  DC_OFFSET;
  uint8_t  CHROMAGRAM_RANGE;
  uint8_t  CHROMA_PROFILE;   // ChromaProfile preset; front-end for NOTE_OFFSET+CHROMAGRAM_RANGE (global, not per-channel)
  bool     STANDBY_DIMMING;
  bool     REVERSE_ORDER;
  bool     RESERVED_CONFIG_BYTE;
  uint32_t MAX_CURRENT_MA;
  bool     TEMPORAL_DITHERING;
  bool     AUTO_COLOR_SHIFT;
  float    INCANDESCENT_FILTER;
  bool     INCANDESCENT_MODE;
  float    BULB_OPACITY;
  float    SATURATION;
  float    PRISM_COUNT;
  bool     BASE_COAT;
  float    VU_LEVEL_FLOOR;
  float    BASE_COAT_INTENSITY;

  // --- Palette Settings ---
  uint8_t PALETTE_INDEX;         // Index of the currently selected palette
  bool    PALETTE_MODE_ENABLED;  // True if palette mode is active
};

// Boot palette lock (Captain standing order, 2026-08-05): EVERY K1 — bench and
// main, every env — comes up on K1_Naberius_Gold_gp with palette mode ON for both
// the primary and secondary channel. Index 40 into gGradientPalettes[] /
// paletteNames[] in visual/Palettes.h; the two arrays are written in one order and
// tests/test_boot_palette_lock_static.py fails the build if this index stops
// naming K1_Naberius_Gold_gp, so a palette reordering cannot silently ship the
// wrong colour. Runtime palette changes still work — they simply do not survive a
// reboot, which is what "always start with" requires.
#define K1_BOOT_PALETTE_NAME  "K1_Naberius_Gold_gp"
#define K1_BOOT_PALETTE_INDEX 40

#endif // CONFIG_TYPES_H
