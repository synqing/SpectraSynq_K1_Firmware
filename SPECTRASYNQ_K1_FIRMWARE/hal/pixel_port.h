#pragma once

// HAL abstraction skeleton for the colour pixel boundary.
//
// Source-grounded reason for this file:
// - FastLED/CRGB types now dominate VP-path coupling.
// - The portable-core seam should not import FastLED or hardware headers directly.

#include <cstdint>

namespace k1 {
namespace hal {

using PixelIndex = uint16_t;

struct LedPixel {
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

struct LedPixelSlice {
    LedPixel* pixels;
    uint16_t pixel_count;
    uint16_t capacity;
};

class PixelPort {
public:
    virtual ~PixelPort() = default;

    virtual void begin() = 0;
    virtual void configure(PixelIndex total_pixels) = 0;
    virtual void write(const LedPixelSlice& slice) = 0;
    virtual void flush() = 0;
};

}  // namespace hal
}  // namespace k1
