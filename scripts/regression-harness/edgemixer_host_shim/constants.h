// Minimal host shim for SPECTRASYNQ_K1_FIRMWARE/system/constants.h, used ONLY by
// the EdgeMixer parity probe. director/sb_edgemixer_lite.h includes "constants.h"
// purely for the SQ15x16 type, the CRGB16 struct and NATIVE_RESOLUTION. This shim
// provides EXACTLY those three, sourced identically to the real header:
//   - SQ15x16  : the genuine FixedPoints SFixed<15,16> alias (FixedPointsCommon)
//   - CRGB16   : { SQ15x16 r,g,b } — byte-identical layout to the firmware struct
//   - NATIVE_RESOLUTION : 160 — identical to the firmware #define
// It deliberately omits the rest of constants.h (config_types.h, FastLED, notes
// tables) which the EdgeMixer module does not reference. Device builds use the
// genuine constants.h; this shim never enters a device build.
#ifndef CONSTANTS_H
#define CONSTANTS_H

#include <FixedPoints.h>        // FixedPoints core
#include <FixedPointsCommon.h>  // SQ15x16 = SFixed<15,16> alias
#include <stdint.h>

struct CRGB16 {  // SQ15x16 normalised 0..1 colour channels (matches firmware)
  SQ15x16 r;
  SQ15x16 g;
  SQ15x16 b;
};

#define NATIVE_RESOLUTION 160

#endif  // CONSTANTS_H
