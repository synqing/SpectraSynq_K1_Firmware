#pragma once

#ifdef K1_B489_WS2816_V1
#include <stdint.h>
#include "ws2816_pack.h"

// B489 compatibility envelope, NOT measured WS2816 milliamps. Preserve the
// pinned FastLED 3.10.3 power_mgt.cpp estimator and its global 255-brightness
// decision on logical pixels, never on the doubled CRGB wire carrier.
// Its historical 80/55/75 colour weights, 5/pixel idle and 125 MCU terms are
// estimates; WS2816 code-to-current transfer remains NOT_CALIBRATED.
// Inputs are BOTH final post-look, pre-limit frames. A disabled but held peer
// still participates. Do not scale these caches in place (held frames would
// otherwise be repeatedly dimmed). Apply the returned gain while packing.
struct K1B489LegacyPowerLimit {
  uint16_t scale_q16;  // 65535 is exact identity; other values divide by 65536.
  uint8_t legacy_brightness;
  uint32_t estimated_unscaled_mw;
  uint32_t estimated_requested_mw;
};

static inline uint8_t k1_b489_legacy_power_proxy(uint16_t channel) {
  // Upper RGB8 projection: exact on v8*257; never understates a native code.
  return static_cast<uint8_t>((static_cast<uint32_t>(channel) + 256U) / 257U);
}

static inline uint32_t k1_b489_legacy_power_edge(const Pixel16* pixels,
                                               uint16_t count) {
  constexpr uint32_t kPhysicalPixelsPerDin = 80U;
  uint32_t total = 5U * count;
  // FastLED floors each colour sum separately for each controller. B489 has
  // two 80-pixel DIN controllers per edge; carrier slots are not pixels.
  for (uint32_t base = 0U; base < count; base += kPhysicalPixelsPerDin) {
    uint32_t red = 0U, green = 0U, blue = 0U;
    const uint32_t remaining = static_cast<uint32_t>(count) - base;
    const uint32_t n = remaining < kPhysicalPixelsPerDin
                           ? remaining : kPhysicalPixelsPerDin;
    if (pixels != nullptr) {
      for (uint32_t i = 0U; i < n; ++i) {
        const Pixel16& pixel = pixels[base + i];
        red += k1_b489_legacy_power_proxy(pixel.r);
        green += k1_b489_legacy_power_proxy(pixel.g);
        blue += k1_b489_legacy_power_proxy(pixel.b);
      }
    }
    total += ((red * 80U) >> 8U) + ((green * 55U) >> 8U) +
             ((blue * 75U) >> 8U);
  }
  return total;
}

static inline K1B489LegacyPowerLimit k1_b489_legacy_power_limit(
    const Pixel16* primary, uint16_t primary_count,
    const Pixel16* secondary, uint16_t secondary_count,
    uint16_t maximum_current_ma) {
  const uint32_t total = 125U +
      k1_b489_legacy_power_edge(primary, primary_count) +
      k1_b489_legacy_power_edge(secondary, secondary_count);
  const uint32_t requested = static_cast<uint32_t>(
      (static_cast<uint64_t>(total) * 255U) / 256U);
  const uint32_t budget = static_cast<uint32_t>(maximum_current_ma) * 5U;
  const uint8_t brightness = requested < budget ? 255U :
      static_cast<uint8_t>((255U * budget) / requested);
  // Preserve FastLED's brightness decision; round the native normalised gain
  // down. Do not apply FastLED byte scaling to the packed 48-bit carrier.
  const uint16_t scale = brightness == 255U ? 65535U :
      static_cast<uint16_t>((static_cast<uint32_t>(brightness) << 16U) / 255U);
  return {scale, brightness, total, requested};
}

static inline uint16_t k1_b489_legacy_power_apply(uint16_t channel,
                                                uint16_t scale_q16) {
  if (scale_q16 == 65535U) return channel;
  return static_cast<uint16_t>(
      (static_cast<uint32_t>(channel) * scale_q16) >> 16U);
}
#endif
