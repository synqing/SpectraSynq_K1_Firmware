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
