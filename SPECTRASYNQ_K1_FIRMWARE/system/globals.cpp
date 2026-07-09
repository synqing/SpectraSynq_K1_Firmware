// globals.cpp
// ============================================================================
// Row 3 (2026-05-25) — globals.h MINIMAL partition.
//
// Second hand-written definition TU (after globals_config.cpp). Holds the
// definitions of the mode/vp_probe-referenced global subset that Row 2's
// per-mode .cpp translation units must link against via `extern` declarations
// in globals.h. PURE RELOCATION — zero behaviour change; init values and types
// are preserved exactly (chroma_val stays 1.0; the rest are zero-init).
//
// Include hygiene (Spike #2 Findings #1b/#2): this subset is SQ15x16-typed, so
// this TU includes <FixedPointsCommon.h> (where `using SQ15x16 = SFixed<15,16>`
// actually lives) in correct order — unlike globals_config.cpp, whose POD
// `conf` needed no FixedPoints. It includes ONLY the slim config_types.h
// (conf + NUM_FREQS + ODR-safe enums/macros), NEVER the full globals.h or
// constants.h, which would re-emit their object definitions → "multiple
// definition" link errors.
// ============================================================================
#include <FastLED.h>
#include <FixedPointsCommon.h>
#include "config_types.h"   // conf, NUM_FREQS, ODR-safe enums/macros

// Serial/status response tokens. Keep bytes identical: external parsers and
// boot logs rely on these exact strings.
extern const char K1_PASS[] = "PASS";
extern const char K1_FAIL[] = "FAIL ###################";

// Externs this TU references but does not own --------------------------------
extern conf CONFIG;                          // defined in globals_config.cpp
extern bool SECONDARY_PALETTE_MODE_ENABLED;  // defined in globals.h object sea

// ----------------------------------------------------------------------------
// Spectrograms (read by light_mode_gdft / chromagram modes) -------------------
SQ15x16 spectrogram_smooth[NUM_FREQS] = { 0.0 };
SQ15x16 chromagram_smooth[12] = { 0.0 };
#ifdef K1_PALETTE_VIBRANCY_V1
SQ15x16 chromagram_pregate[12] = { 0.0 };  // K1 PALETTE VIBRANCY: pre-gate chroma for palette coordinates
#endif
float   note_chromagram[12] = { 0 };

SQ15x16 chroma_val = 1.0;

// ----------------------------------------------------------------------------
// VU calculation (read by VU / waveform modes) --------------------------------
SQ15x16 audio_vu_level = 0.0;
SQ15x16 audio_vu_level_average = 0.0;
SQ15x16 audio_vu_level_last = 0.0;

// ----------------------------------------------------------------------------
// Auto color shift (read by render colour path) -------------------------------
SQ15x16 hue_position = 0.0;

// ----------------------------------------------------------------------------
// VP render channel selector (read by vp_probe machinery + palette source) ----
bool vp_render_secondary_channel = false;

// ----------------------------------------------------------------------------
// Palette colour-source ownership (read by render + vp_probe) -----------------
bool palette_owns_colour_source(bool secondary_channel) {
  return secondary_channel ? SECONDARY_PALETTE_MODE_ENABLED : CONFIG.PALETTE_MODE_ENABLED;
}

bool palette_owns_render_colour_source() {
  return palette_owns_colour_source(vp_render_secondary_channel);
}
