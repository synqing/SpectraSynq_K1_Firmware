/*----------------------------------------
  K1 I2S capture types + slot constants
  ----------------------------------------
  Factored out of the monolithic, guard-less i2s_audio.h (Phase A Lane 2, S1)
  so that the AP-capture telemetry TU (serial/k1_ap_capture_telemetry.cpp) can
  obtain K1AudioI2SReadDebug and the K1_I2S_* slot constants WITHOUT pulling
  i2s_audio.h's full implementation (which only compiles inside the .ino's
  include context). i2s_audio.h includes this header in place of the inline
  definitions, so there is exactly one definition of each — no ODR drift.

  Guarded (unlike i2s_audio.h itself) so it is safe to include from any TU.
*/

#ifndef K1_I2S_CAPTURE_TYPES_H
#define K1_I2S_CAPTURE_TYPES_H

#include <stdint.h>

#ifndef K1_I2S_DMA_DESC_NUM_VALUE
#define K1_I2S_DMA_DESC_NUM_VALUE 3
#endif
static const uint8_t K1_I2S_DMA_DESC_NUM = K1_I2S_DMA_DESC_NUM_VALUE;
static const uint8_t K1_I2S_SLOT_BIT_WIDTH_BITS = 32;
static const uint8_t K1_I2S_SLOT_MODE_STEREO = 2;

// Timestamp estimate used only by the non-shippable scheduling/AP probes. The
// I2S driver does not expose per-sample hardware timestamps, so read-return is
// the declared newest-sample estimate and this derives the oldest sample in the
// returned chunk. Descriptor residence before the read remains explicitly
// unknown and is never hidden by this arithmetic.
static inline uint64_t k1_i2s_estimate_oldest_sample_us(
    uint64_t read_return_us,
    uint32_t samples_read,
    uint32_t sample_rate_hz) {
  if (samples_read == 0U || sample_rate_hz == 0U) {
    return read_return_us;
  }
  const uint64_t span_us =
      (uint64_t)(samples_read - 1U) * 1000000ULL / (uint64_t)sample_rate_hz;
  return (span_us <= read_return_us) ? (read_return_us - span_us) : 0ULL;
}

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
struct K1AudioI2SReadDebug {
  uint64_t read_start_us;
  uint64_t read_return_us;
  uint64_t newest_sample_estimate_us;
  uint64_t oldest_sample_estimate_us;
  uint64_t ap_publish_us;
  uint32_t capture_sequence;
  uint32_t samples_read;
  uint32_t bytes_requested;
  uint32_t bytes_read;
  int32_t status;
  uint32_t elapsed_us;
  uint8_t sample_time_assumption_id;
};
#endif

#endif  // K1_I2S_CAPTURE_TYPES_H
