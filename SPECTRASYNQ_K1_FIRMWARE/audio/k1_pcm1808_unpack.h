#pragma once

// ESP32-S3 I2S RX 24-bit DMA packing (IDF 5.4, not classic ESP32):
//   bytes_per_sample = (data_bit_width + 7) / 8 = 3
//   stereo frame = 6 bytes
// big_endian=false => little-endian 24-bit in the DMA buffer:
//   b[0]=LSB, b[2]=MSB (bit 23 = sign).
// Never load these 3 bytes as an unaligned int32_t.

#include <stdint.h>

static inline int32_t k1_pcm1808_unpack_le24(const uint8_t b[3]) {
  const uint32_t u =
      (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16);
  const uint32_t se = (u & 0x800000u) ? (u | 0xFF000000u) : u;
  return (int32_t)se;
}

// Linear 24-bit -> 16-bit canonical: arithmetic shift with round-to-nearest
// and saturation. Not IM69 gain, not SSL.
static inline int16_t k1_pcm1808_s24_to_s16(int32_t s24) {
  int32_t rounded = (s24 >= 0) ? ((s24 + 128) >> 8) : ((s24 - 128) >> 8);
  if (rounded > 32767) {
    rounded = 32767;
  }
  if (rounded < -32768) {
    rounded = -32768;
  }
  return (int16_t)rounded;
}
