// ============================================================================
// render_host_globals.cpp — HOST-ONLY definitions for render_replay (Tier 1)
// ============================================================================
// VE-Auto-Loop render_replay harness (docs/prd/ve-auto-loop/01-render-replay-harness.md §5.4).
//
// Supplies the `extern` symbols the render call graph ODR-uses that are NOT
// covered by the firmware's own data TUs we compile (visual/render_params.cpp,
// visual/Palettes.cpp, system/globals.cpp). Defining the remainder HERE keeps the
// audio-pipeline / hardware .cpp files OFF the host (PRD R-GLOBAL): we never pull
// i2s_audio / GDFT / sb_onset_beat .cpp just to satisfy one extern.
//
// globals.h's `inline` variables (leds_16, chromatic_mode, VP_BLOOM_*,
// MASTER_BRIGHTNESS, mode_names, hue_shifting_mix, USBSerial, debug_mode,
// waveform_peak_scaled, max_waveform_val_raw, effect_state_primary/secondary,
// i2s buffers, ...) are defined by merely including the header.
//
// The Row-3 data globals (SB_PASS/SB_FAIL, chromagram_smooth, spectrogram_smooth,
// chroma_val, audio_vu_level*, hue_position, vp_render_secondary_channel,
// note_chromagram, palette_owns_colour_source) are owned by system/globals.cpp,
// now compiled in COMMON_SOURCES — so they are NOT redefined here (the Phase-B
// refactor, 2026-06-03, moved them there + flipped SB_PASS/SB_FAIL macros→externs).
//
// NON-SHIPPING. Compiled only under -DSB_RENDER_HOST_TEST.
// ============================================================================
#include "globals.h"
#include "sb_onset_beat.h"   // SBOnsetBeatEvent + sb_onset_beat_read() — host-stubbed below

// --- host platform singletons (declared extern in stubs/) ------------------
HostSerial Serial;
CFastLED   FastLED;
EspClass   ESP;

// --- conf objects (firmware: globals_config.cpp, which we do NOT compile — it
//     drags persistence/NVS). The render path only reads RenderParams (pushed via
//     push_render_params), not CONFIG fields, so zero-init is sufficient here. ---
conf CONFIG          = {};
conf CONFIG_DEFAULTS = {};

// Force an ODR-use of globals.h's `inline bool SECONDARY_PALETTE_MODE_ENABLED` so
// this TU emits its definition. globals.cpp's palette_owns_colour_source() declares
// it `extern` (globals.cpp does NOT include globals.h), so without an emitter the
// link fails for any mode reaching the palette source (spectrum_river / palette mode).
const bool* sb_host_force_secondary_palette = &SECONDARY_PALETTE_MODE_ENABLED;

// --- onset/beat host stub (comet) ------------------------------------------
// light_mode_comet() reads onsets via sb_onset_beat_read() (audio/sb_onset_beat.cpp,
// which drags portMUX/FreeRTOS — explicitly NOT compiled on host, per the D8 recon
// + PRD R-GLOBAL). Instead the driver sets g_host_onset_event each frame and this
// stub returns it. Settable global => fully deterministic, no audio pipeline.
SBOnsetBeatEvent g_host_onset_event = {};
SBOnsetBeatEvent sb_onset_beat_read() { return g_host_onset_event; }
