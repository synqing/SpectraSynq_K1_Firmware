/*----------------------------------------
  Sensory Bridge I2S capture types + slot constants
  ----------------------------------------
  Factored out of the monolithic, guard-less i2s_audio.h (Phase A Lane 2, S1)
  so that the AP-capture telemetry TU (serial/k1_ap_capture_telemetry.cpp) can
  obtain SBAudioI2SReadDebug and the SB_I2S_* slot constants WITHOUT pulling
  i2s_audio.h's full implementation (which only compiles inside the .ino's
  include context). i2s_audio.h includes this header in place of the inline
  definitions, so there is exactly one definition of each — no ODR drift.

  Guarded (unlike i2s_audio.h itself) so it is safe to include from any TU.
*/

#ifndef SB_I2S_CAPTURE_TYPES_H
#define SB_I2S_CAPTURE_TYPES_H

#include <stdint.h>

#ifndef SB_I2S_DMA_DESC_NUM_VALUE
#define SB_I2S_DMA_DESC_NUM_VALUE 3
#endif
static const uint8_t SB_I2S_DMA_DESC_NUM = SB_I2S_DMA_DESC_NUM_VALUE;
static const uint8_t SB_I2S_SLOT_BIT_WIDTH_BITS = 32;
static const uint8_t SB_I2S_SLOT_MODE_STEREO = 2;

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
struct SBAudioI2SReadDebug {
  uint32_t bytes_requested;
  uint32_t bytes_read;
  int32_t status;
  uint32_t elapsed_us;
};
#endif

#endif  // SB_I2S_CAPTURE_TYPES_H
