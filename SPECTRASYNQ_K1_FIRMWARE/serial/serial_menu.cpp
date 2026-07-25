/*----------------------------------------
  K1 UART COMMAND LINE — out-of-line implementation
  ----------------------------------------
  M2.1 Phase R1: kill the serial_menu.h ODR bomb. serial_menu.h defines 104
  non-inline, external-linkage functions at file scope — legal today ONLY because
  exactly one TU (SPECTRASYNQ_K1_FIRMWARE.ino) includes it. This TU is the new
  home for those definitions, moved out family-by-family (LEAF-FIRST), with the
  declarations left behind in serial_menu.h.

  It includes the SUBSTRATE serial_menu.h itself uses (globals.h + the k1_*.h
  stack) but NOT serial_menu.h — that avoids re-pulling the remaining in-header
  definitions into this TU (which would be an ODR double-definition against the
  .ino TU). build_src_filter already globs the serial subdir's .cpp files, so
  this file compiles with no platformio.ini change.

  Behaviour-preserving by construction: the serial_replay + serial_struct goldens
  must reproduce byte-for-byte after each move (tests/test_golden_master.py +
  harness_selftest.py Gate-Fα). The replay oracle links this TU via its
  MODULE_CPPS list (mirrors the S4 serial_cmd_handlers.cpp precedent).

  --- Moved so far (batch 1, edge-mixer name/parse helpers, serial_menu.h:574-678):
      k1_edge_mode_name / k1_parse_edge_mode / k1_edge_rotation_name /
      k1_edge_dual_name / k1_parse_edge_rotation / k1_parse_edge_dual /
      k1_parse_edge_uniform. Pure leaves: strcmp + K1EdgeMixer* enums only.
*/

#include "globals.h"    // CONFIG + global state (serial_menu.h:8)
#include "constants.h"  // NUM_AGC_BANDS etc. (serial_menu.h:9)
#include "k1_trace.h"   // (serial_menu.h:10)
#include <stdint.h>
#include <stdlib.h>
#include <string.h>     // strcmp
#include <math.h>

// k1_*.h substrate stack (mirrors serial_menu.h:30-38) — provides the types,
// enums and inline APIs the moved bodies reference. k1_edgemixer.h carries the
// K1EdgeMixerMode / K1EdgeMixerRotationSpace / K1EdgeMixerDualEdge enums the edge
// helpers switch on, plus the K1_STM gate.
#include "k1_audio_snapshot.h"
#include "k1_edgemixer.h"
#include "k1_mode_selection.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
#include "k1_smart_director.h"
#include "k1_visual_hooks.h"
#include "k1_noise_cal_arm.h"
#include "k1_effect_queue.h"
#include "serial_tx.h"    // tx_begin / tx_end (edge status/control family, batch 2)
#ifdef K1_EFFECT_FRAMEWORK_V1
#include "beat_aware_director.h"  // bad_director_* accessors (beat_director status, batch 4; same gate as serial_menu.h:24)
#endif

// vp_bool_text() is a leaf still defined in serial_menu.h; forward-declare it here
// (external linkage) so the moved edge status printers link against that single
// definition — same cross-TU pattern serial_cmd_handlers.cpp uses for its callees.
const char* vp_bool_text(bool value);

// ---------------------------------------------------------------------------
// Edge-mixer name/parse helpers (moved VERBATIM from serial_menu.h:574-678).
// Declarations remain in serial_menu.h so the in-header status printers and the
// extracted serial_cmd_dispatch_edge_mixer() (serial_cmd_handlers.cpp) resolve
// against these single out-of-line definitions.
// ---------------------------------------------------------------------------

const char* k1_edge_mode_name(K1EdgeMixerMode mode) {
  switch (mode) {
    case K1_EDGE_MIXER_ANALOGOUS: return "analogous";
    case K1_EDGE_MIXER_COMPLEMENTARY: return "complementary";
    case K1_EDGE_MIXER_SPLIT_COMPLEMENTARY: return "split";
    case K1_EDGE_MIXER_SATURATION_VEIL: return "veil";
    case K1_EDGE_MIXER_TRIADIC: return "triadic";
    case K1_EDGE_MIXER_TETRADIC: return "tetradic";
#ifdef K1_STM
    case K1_EDGE_MIXER_STM_DUAL: return "stm_dual";
    case K1_EDGE_MIXER_STM_SPECTRAL_MAP: return "stm_spectral_map";
#endif
    case K1_EDGE_MIXER_OFF:
    default: return "off";
  }
}

bool k1_parse_edge_mode(const char* text, K1EdgeMixerMode* out_mode) {
  if (strcmp(text, "off") == 0) {
    *out_mode = K1_EDGE_MIXER_OFF;
  } else if (strcmp(text, "analogous") == 0) {
    *out_mode = K1_EDGE_MIXER_ANALOGOUS;
  } else if (strcmp(text, "complementary") == 0) {
    *out_mode = K1_EDGE_MIXER_COMPLEMENTARY;
  } else if (strcmp(text, "split") == 0 || strcmp(text, "split_complementary") == 0) {
    *out_mode = K1_EDGE_MIXER_SPLIT_COMPLEMENTARY;
  } else if (strcmp(text, "veil") == 0 || strcmp(text, "saturation_veil") == 0) {
    *out_mode = K1_EDGE_MIXER_SATURATION_VEIL;
  } else if (strcmp(text, "triadic") == 0) {
    *out_mode = K1_EDGE_MIXER_TRIADIC;
  } else if (strcmp(text, "tetradic") == 0) {
    *out_mode = K1_EDGE_MIXER_TETRADIC;
#ifdef K1_STM
  } else if (strcmp(text, "stm_dual") == 0) {
    *out_mode = K1_EDGE_MIXER_STM_DUAL;
  } else if (strcmp(text, "stm_spectral_map") == 0 || strcmp(text, "stm_spectral") == 0) {
    *out_mode = K1_EDGE_MIXER_STM_SPECTRAL_MAP;
#endif
  } else {
    return false;
  }
  return true;
}

const char* k1_edge_rotation_name(K1EdgeMixerRotationSpace space) {
  switch (space) {
    case K1_EDGE_ROTATION_LUMA_PRESERVING: return "luma";
    case K1_EDGE_ROTATION_OKLAB:           return "oklab";
    default:                               return "faithful";
  }
}

const char* k1_edge_dual_name(K1EdgeMixerDualEdge dual) {
  switch (dual) {
    case K1_EDGE_DUAL_SPLIT:  return "split";
    case K1_EDGE_DUAL_MIRROR: return "mirror";
    default:                  return "one_sided";
  }
}

// faithful -> SUM_PRESERVING (grey-axis rotation, +/-1 LSB golden parity);
// luma     -> LUMA_PRESERVING (grey-axis rotation + per-pixel BT.601 luma rescale);
// oklab    -> OKLAB (perceptual hue rotation in the OKLab a/b plane, holds L constant).
bool k1_parse_edge_rotation(const char* text, K1EdgeMixerRotationSpace* out_space) {
  if (strcmp(text, "faithful") == 0 || strcmp(text, "sum") == 0) {
    *out_space = K1_EDGE_ROTATION_SUM_PRESERVING;
  } else if (strcmp(text, "luma") == 0) {
    *out_space = K1_EDGE_ROTATION_LUMA_PRESERVING;
  } else if (strcmp(text, "oklab") == 0) {
    *out_space = K1_EDGE_ROTATION_OKLAB;
  } else {
    return false;
  }
  return true;
}

// one_sided (or one) -> ONE_SIDED (secondary only; certified default);
// split               -> SPLIT (both edges +/- theta/2 about the 79/80 centre);
// mirror              -> MIRROR (both edges +/- theta, full opposite rotations).
bool k1_parse_edge_dual(const char* text, K1EdgeMixerDualEdge* out_dual) {
  if (strcmp(text, "one_sided") == 0 || strcmp(text, "one") == 0) {
    *out_dual = K1_EDGE_DUAL_ONE_SIDED;
  } else if (strcmp(text, "split") == 0) {
    *out_dual = K1_EDGE_DUAL_SPLIT;
  } else if (strcmp(text, "mirror") == 0) {
    *out_dual = K1_EDGE_DUAL_MIRROR;
  } else {
    return false;
  }
  return true;
}

// uniform -> spatialUniform true (shift applied evenly across the strip);
// masked  -> false (centre-masked: fades from 0 at the 79/80 centre to full at the
// ends). Ref E. Scriptable counterpart to the 'm' hotkey.
bool k1_parse_edge_uniform(const char* text, bool* out_uniform) {
  if (strcmp(text, "uniform") == 0) {
    *out_uniform = true;
  } else if (strcmp(text, "masked") == 0) {
    *out_uniform = false;
  } else {
    return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// Edge-mixer status + live-hotkey control (moved VERBATIM from serial_menu.h,
// M2.1 Phase R1 batch 2). These call the batch-1 edge name helpers above (same
// TU) + tx_begin/tx_end (serial_tx.h) + vp_bool_text (forward-declared above).
// Source order preserved so k1_edge_warn_if_collapsed precedes its callers.
// ---------------------------------------------------------------------------

void k1_print_edge_status() {
  K1EdgeMixerConfig edge = k1_edgemixer_config();
  tx_begin();
  USBSerial.print("EDGE_ENABLED: ");
  USBSerial.println(vp_bool_text(edge.enabled));
  USBSerial.print("EDGE_MODE: ");
  USBSerial.println(k1_edge_mode_name(edge.mode));
  USBSerial.print("EDGE_STRENGTH: ");
  USBSerial.println(edge.strength, 3);
  USBSerial.print("EDGE_SPREAD: ");
  USBSerial.println((int)edge.spreadDegrees);
  USBSerial.print("EDGE_ROTATION: ");
  USBSerial.println(k1_edge_rotation_name(edge.rotationSpace));
  USBSerial.print("EDGE_SPATIAL: ");
  USBSerial.println(edge.spatialUniform ? "uniform" : "masked");
  USBSerial.print("EDGE_DUAL: ");
  USBSerial.println(k1_edge_dual_name(edge.dualEdge));
  tx_end();
}

// A-lane UX guard: MIRROR + COMPLEMENTARY makes both edges rotate +/-180deg to the
// SAME hue (2*180 = 360 = 0 separation), collapsing the two edges into one. Honest
// maths, but a UX trap — so warn (informative, NOT a hard block) whenever a change
// makes that combo active. Called from the mode + dual-edge change handlers.
void k1_edge_warn_if_collapsed(const K1EdgeMixerConfig& e) {
  if (e.dualEdge == K1_EDGE_DUAL_MIRROR && e.mode == K1_EDGE_MIXER_COMPLEMENTARY) {
    tx_begin();
    USBSerial.println("EDGE_WARN: mirror+complementary collapses both edges to the same hue (2x180=0 separation) - use split at complementary, or mirror at analogous/triadic.");
    tx_end();
  }
}

// --- EdgeMixer live-hotkey helpers (each mutates the transplanted config via
// k1_edgemixer_config()/set_config() and prints only its own new state) ---
void serial_edge_toggle_enabled() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  e.enabled = !e.enabled;
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_ENABLED: ");
  USBSerial.println(vp_bool_text(e.enabled));
  tx_end();
}

void serial_edge_cycle_mode() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  // off -> analogous -> complementary -> split -> veil -> triadic -> tetradic -> off
  // (under K1_STM the cycle continues: tetradic -> stm_dual -> stm_spectral_map -> off)
  uint8_t next = (uint8_t)e.mode + 1;
#ifdef K1_STM
  if (next > (uint8_t)K1_EDGE_MIXER_STM_SPECTRAL_MAP) {
    next = (uint8_t)K1_EDGE_MIXER_OFF;
  }
#else
  if (next > (uint8_t)K1_EDGE_MIXER_TETRADIC) {
    next = (uint8_t)K1_EDGE_MIXER_OFF;
  }
#endif
  e.mode = (K1EdgeMixerMode)next;
  e.enabled = (e.mode != K1_EDGE_MIXER_OFF);  // colour mode -> visible; off -> disabled
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_MODE: ");
  USBSerial.println(k1_edge_mode_name(e.mode));
  tx_end();
  k1_edge_warn_if_collapsed(e);
}

void serial_edge_adjust_spread(int delta) {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  int s = (int)e.spreadDegrees + delta;
  if (s < 0) { s = 0; }
  if (s > 60) { s = 60; }
  e.spreadDegrees = (uint8_t)s;
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_SPREAD: ");
  USBSerial.println((int)e.spreadDegrees);
  tx_end();
}

void serial_edge_adjust_strength(float delta) {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  e.strength = constrain(e.strength + delta, 0.0f, 1.0f);
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_STRENGTH: ");
  USBSerial.println(e.strength, 3);
  tx_end();
}

void serial_edge_toggle_rotation() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  // 3-way cycle: faithful (SUM) -> luma -> oklab -> faithful. This is the bench
  // A/B control for the OKLab-vs-luma-rescale perceptual comparison on the plate.
  switch (e.rotationSpace) {
    case K1_EDGE_ROTATION_SUM_PRESERVING:
      e.rotationSpace = K1_EDGE_ROTATION_LUMA_PRESERVING;
      break;
    case K1_EDGE_ROTATION_LUMA_PRESERVING:
      e.rotationSpace = K1_EDGE_ROTATION_OKLAB;
      break;
    default:
      e.rotationSpace = K1_EDGE_ROTATION_SUM_PRESERVING;
      break;
  }
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_ROTATION: ");
  USBSerial.println(k1_edge_rotation_name(e.rotationSpace));
  tx_end();
}

void serial_edge_toggle_dual_edge() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  // 3-way cycle: one_sided -> split -> mirror -> one_sided. Symmetric dual-edge
  // (A lane) — the plate A/B for "make BOTH edges participate about the 79/80
  // centre". one_sided = only the secondary strip shifts (certified default);
  // split = both edges +/- theta/2; mirror = both edges +/- theta.
  switch (e.dualEdge) {
    case K1_EDGE_DUAL_ONE_SIDED:
      e.dualEdge = K1_EDGE_DUAL_SPLIT;
      break;
    case K1_EDGE_DUAL_SPLIT:
      e.dualEdge = K1_EDGE_DUAL_MIRROR;
      break;
    default:
      e.dualEdge = K1_EDGE_DUAL_ONE_SIDED;
      break;
  }
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_DUAL: ");
  USBSerial.println(k1_edge_dual_name(e.dualEdge));
  tx_end();
  k1_edge_warn_if_collapsed(e);
}

void serial_edge_toggle_uniform() {
  K1EdgeMixerConfig e = k1_edgemixer_config();
  e.spatialUniform = !e.spatialUniform;  // ref E: centre-masked <-> uniform
  k1_edgemixer_set_config(e);
  tx_begin();
  USBSerial.print("EDGE_SPATIAL: ");
  USBSerial.println(e.spatialUniform ? "uniform" : "masked");
  tx_end();
}

// ---------------------------------------------------------------------------
// Vivid pre-comp helpers (moved VERBATIM from serial_menu.h, M2.1 Phase R1
// batch 3). Gated by K1_VIVID_PRECOMP_V1, same as the extracted
// serial_cmd_dispatch_vivid (serial_cmd_handlers.cpp) and the 'v' hotkey. Source
// order preserved so the sibling helpers are defined before their callers.
// ---------------------------------------------------------------------------
#ifdef K1_VIVID_PRECOMP_V1
void serial_update_vivid_enabled_from_levels() {
  VP_VIVID_PRECOMP = (VP_VIVID_CHROMA_LEVEL > 0.0f) || (VP_VIVID_BLACK_LEVEL > 0.0f);
}

void serial_ensure_vivid_defaults() {
  if (VP_VIVID_CHROMA_LEVEL <= 0.0f && VP_VIVID_BLACK_LEVEL <= 0.0f) {
    VP_VIVID_CHROMA_LEVEL = 1.0f;
    VP_VIVID_BLACK_LEVEL = VIVID_BLACK_LEVEL_DEFAULT;
  }
}

void serial_set_vivid_level(float value) {
  float level = constrain(value, 0.0f, 1.0f);
  VP_VIVID_CHROMA_LEVEL = level;
  VP_VIVID_BLACK_LEVEL = constrain(level * VIVID_BLACK_LEVEL_DEFAULT, 0.0f, 1.0f);
  serial_update_vivid_enabled_from_levels();
}

void serial_print_vivid_precomp_status() {
  USBSerial.print("VIVID_PRECOMP: ");
  USBSerial.println(vp_bool_text(VP_VIVID_PRECOMP));
  USBSerial.print("VIVID_CHROMA_LEVEL: ");
  USBSerial.println(VP_VIVID_CHROMA_LEVEL, 3);
  USBSerial.print("VIVID_BLACK_LEVEL: ");
  USBSerial.println(VP_VIVID_BLACK_LEVEL, 3);
}

void serial_toggle_vivid_precomp() {
  VP_VIVID_PRECOMP = !VP_VIVID_PRECOMP;
  if (VP_VIVID_PRECOMP) {
    serial_ensure_vivid_defaults();
  }
  tx_begin();
  serial_print_vivid_precomp_status();
  tx_end();
}
#endif

// ---------------------------------------------------------------------------
// K1 loud-guard serial helpers (moved VERBATIM from serial_menu.h, M2.1 R1
// batch 4). Gated K1_LOUD_GUARD_V1. Uses globals (k1_loud_*) + vp_bool_text.
// ---------------------------------------------------------------------------
#ifdef K1_LOUD_GUARD_V1
void serial_print_k1_loud_guard_status() {
  USBSerial.print("K1_LOUD_GUARD: ");
  USBSerial.println(vp_bool_text(k1_loud_guard_enabled));
  USBSerial.print("K1_LOUD_INPUT_TRIM: ");
  USBSerial.println(k1_loud_input_trim, 3);
  USBSerial.print("K1_LOUD_GDFT_TRIM: ");
  USBSerial.println(k1_loud_gdft_trim, 3);
  USBSerial.print("K1_LOUD_AGC_GAIN: ");
  USBSerial.println(float(agc_bands[0].gain), 4);
  USBSerial.print("K1_LOUD_CLIP_DUTY: ");
  USBSerial.println(k1_loud_clip_duty, 4);
  USBSerial.print("K1_LOUD_NEAR_RAIL_DUTY: ");
  USBSerial.println(k1_loud_near_rail_duty, 4);
  USBSerial.print("K1_LOUD_PEAK_PIN_DUTY: ");
  USBSerial.println(k1_loud_peak_pin_duty, 4);
  USBSerial.print("K1_LOUD_SPEC_SAT_DUTY: ");
  USBSerial.println(k1_loud_spec_sat_duty, 4);
  USBSerial.print("K1_LOUD_GUARD_MODE: ");
  USBSerial.println(k1_loud_guard_mode);   // 0=baseline 1=conservative 2=aggressive
}

void serial_set_k1_loud_guard(bool enabled) {
  k1_loud_guard_enabled = enabled;
  if (!k1_loud_guard_enabled) {
    k1_loud_input_trim = 1.0f;
    k1_loud_gdft_trim = 1.0f;
    k1_loud_clip_duty = 0.0f;
    k1_loud_near_rail_duty = 0.0f;
    k1_loud_peak_pin_duty = 0.0f;
    k1_loud_spec_sat_duty = 0.0f;
    k1_loud_spec_sat_fraction = 0.0f;
  }
}

// A/B retune matrix cycle: 0 BASELINE -> 1 CONSERVATIVE -> 2 AGGRESSIVE -> 0.
// Ships dormant at 0 (byte-identical shipping behaviour); DEGRADED-MODE until
// the loud-room hardware A/B + Captain sign-off.
void serial_cycle_k1_loud_guard_mode() {
  k1_loud_guard_mode = (k1_loud_guard_mode + 1) % 3;
  USBSerial.print("K1_LOUD_GUARD_MODE -> ");
  USBSerial.print(k1_loud_guard_mode);
  const char* label = (k1_loud_guard_mode == 0) ? " BASELINE (2.20s/flat)"
                    : (k1_loud_guard_mode == 1) ? " CONSERVATIVE (1.30s/hybrid)"
                    :                             " AGGRESSIVE (0.80s/hybrid)";
  USBSerial.println(label);
}
#endif

// ---------------------------------------------------------------------------
// beat_director serial helper (moved VERBATIM from serial_menu.h, M2.1 R1
// batch 4). Gated K1_EFFECT_FRAMEWORK_V1; uses bad_director_* accessors
// (beat_aware_director.h, included gated above).
// ---------------------------------------------------------------------------
#ifdef K1_EFFECT_FRAMEWORK_V1
void serial_print_beat_director_status() {
  // READ-ONLY: uses pure accessors only — never ticks the director or arms a
  // transition, so a status query never advances selection/dwell state.
  const bool enabled = bad_director_enabled();
  const bool locked  = bad_director_tempo_locked();
  USBSerial.print("BEAT_DIRECTOR: ");
  USBSerial.println(vp_bool_text(enabled));
  USBSerial.print("BEAT_DIRECTOR_MODE: ");
  USBSerial.println(bad_director_current_mode());
  USBSerial.print("BEAT_DIRECTOR_TEMPO_LOCKED: ");
  USBSerial.println(vp_bool_text(locked));
  USBSerial.print("BEAT_DIRECTOR_BPM: ");
  USBSerial.println(bad_director_bpm(), 1);
  USBSerial.print("BEAT_DIRECTOR_TEMPO_CONF: ");
  USBSerial.println(bad_director_tempo_confidence(), 3);
  USBSerial.print("BEAT_DIRECTOR_FALLBACK: ");
  USBSerial.println(vp_bool_text(!locked));  // time-fallback active when unlocked
}
#endif  // K1_EFFECT_FRAMEWORK_V1
