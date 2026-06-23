/**
 * @file RenderPrimitives.cpp
 * @brief Implementation of the K1 effect-framework render primitives (P1 spine).
 *
 * Self-contained spine port from firmware-v3
 * `src/effects/render/RenderPrimitives.cpp`. Owns the single file-scope scratch
 * buffer used by drawSpriteScrolled (in-place sub-pixel scatter, no per-call
 * heap). Sized for K1's largest frame (320 LEDs). Single-threaded on Core 1, so
 * no concurrency guard is required.
 *
 * Compiled ONLY under the `k1_effect_framework` env (K1_EFFECT_FRAMEWORK_V1).
 * Guarded so the TU is inert if ever pulled into another build's source filter.
 *
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "RenderPrimitives.h"

#include <cmath>

namespace k1 {
namespace effects {
namespace framework {

// ─── File-scope scratch buffer ────────────────────────────────────────────────
static constexpr uint16_t kMaxScratchLeds = 320;
static CRGB g_scratchBuf[kMaxScratchLeds];

// ─── Local helpers ────────────────────────────────────────────────────────────

static inline void addScaled(CRGB& dst, const CRGB& src, float weight) {
    if (weight <= 0.0f) return;
    if (weight > 1.0f) weight = 1.0f;
    int r = static_cast<int>(dst.r) + static_cast<int>(static_cast<float>(src.r) * weight);
    int g = static_cast<int>(dst.g) + static_cast<int>(static_cast<float>(src.g) * weight);
    int b = static_cast<int>(dst.b) + static_cast<int>(static_cast<float>(src.b) * weight);
    if (r > 255) r = 255;
    if (g > 255) g = 255;
    if (b > 255) b = 255;
    dst.r = static_cast<uint8_t>(r);
    dst.g = static_cast<uint8_t>(g);
    dst.b = static_cast<uint8_t>(b);
}

static inline float clamp01(float x) {
    if (x < 0.0f) return 0.0f;
    if (x > 1.0f) return 1.0f;
    return x;
}

static inline void plotSubPixel(CRGB* leds,
                                uint16_t ledCount,
                                float floatIdx,
                                CRGB colour,
                                float weight) {
    if (weight <= 0.0f) return;
    const int floorI = static_cast<int>(::floorf(floatIdx));
    const float frac = floatIdx - static_cast<float>(floorI);
    const int ceilI = floorI + 1;
    const float wFloor = (1.0f - frac) * weight;
    const float wCeil = frac * weight;
    if (floorI >= 0 && floorI < static_cast<int>(ledCount)) {
        addScaled(leds[floorI], colour, wFloor);
    }
    if (ceilI >= 0 && ceilI < static_cast<int>(ledCount)) {
        addScaled(leds[ceilI], colour, wCeil);
    }
}

// ─── drawDot ──────────────────────────────────────────────────────────────────

void drawDot(CRGB* leds,
             uint16_t ledCount,
             uint16_t centrePoint,
             float position,
             CRGB colour,
             float opacity,
             float prevPosition,
             bool mirror) {
    if (leds == nullptr || ledCount == 0 || centrePoint == 0 ||
        centrePoint >= ledCount) {
        return;
    }
    position = clamp01(position);
    opacity = clamp01(opacity);
    if (opacity <= 0.0f) return;

    const float leftSpan = static_cast<float>(centrePoint - 1);
    const float rightSpan = static_cast<float>(ledCount - 1 - centrePoint);

    auto rightIdxOf = [&](float pos) {
        return static_cast<float>(centrePoint) + pos * rightSpan;
    };
    auto leftIdxOf = [&](float pos) {
        return static_cast<float>(centrePoint - 1) - pos * leftSpan;
    };

    if (prevPosition < 0.0f) {
        plotSubPixel(leds, ledCount, rightIdxOf(position), colour, opacity);
        if (mirror) {
            plotSubPixel(leds, ledCount, leftIdxOf(position), colour, opacity);
        }
        return;
    }

    prevPosition = clamp01(prevPosition);
    const float dist01 = ::fabsf(position - prevPosition);
    const float spreadRef = (leftSpan > rightSpan) ? leftSpan : rightSpan;
    float spread = dist01 * spreadRef;
    if (spread < 1.0f) spread = 1.0f;
    const float lineWeight = (1.0f / spread) * opacity;
    const int steps = static_cast<int>(::ceilf(spread));
    for (int s = 0; s <= steps; ++s) {
        const float t = (steps > 0)
                            ? static_cast<float>(s) / static_cast<float>(steps)
                            : 0.0f;
        const float p = prevPosition + t * (position - prevPosition);
        plotSubPixel(leds, ledCount, rightIdxOf(p), colour, lineWeight);
        if (mirror) {
            plotSubPixel(leds, ledCount, leftIdxOf(p), colour, lineWeight);
        }
    }
}

// ─── drawSpriteScrolled ───────────────────────────────────────────────────────

void drawSpriteScrolled(CRGB* leds,
                        uint16_t ledCount,
                        uint16_t centrePoint,
                        float scrollAmount,
                        float alpha,
                        float dt) {
    if (leds == nullptr || ledCount == 0 || centrePoint == 0 ||
        centrePoint >= ledCount) {
        return;
    }
    if (ledCount > kMaxScratchLeds) {
        ledCount = kMaxScratchLeds;
    }

    if (alpha < 0.0f) alpha = 0.0f;
    if (alpha > 1.0f) alpha = 1.0f;
    const float effAlpha = (dt > 0.0f) ? ::powf(alpha, dt * 120.0f) : alpha;

    for (uint16_t i = 0; i < ledCount; ++i) {
        g_scratchBuf[i] = leds[i];
        leds[i] = CRGB::Black;
    }

    for (uint16_t i = 0; i < ledCount; ++i) {
        const CRGB& src = g_scratchBuf[i];
        if (src.r == 0 && src.g == 0 && src.b == 0) {
            continue;
        }
        const float signedScroll =
            (i >= centrePoint) ? scrollAmount : -scrollAmount;
        const float destF = static_cast<float>(i) + signedScroll;
        plotSubPixel(leds, ledCount, destF, src, effAlpha);
    }
}

// ─── fillFromBins ─────────────────────────────────────────────────────────────

void fillFromBins(CRGB* leds,
                  uint16_t ledCount,
                  uint16_t centrePoint,
                  const float* bins,
                  uint8_t binCount,
                  const CRGBPalette16& palette,
                  uint8_t brightness,
                  bool additive) {
    if (leds == nullptr || bins == nullptr || ledCount == 0 ||
        centrePoint == 0 || centrePoint >= ledCount || binCount == 0) {
        return;
    }
    const float leftSpan = static_cast<float>(centrePoint - 1);
    const float rightSpan = static_cast<float>(ledCount - 1 - centrePoint);
    const float denom = (binCount > 1) ? static_cast<float>(binCount - 1) : 1.0f;

    if (!additive) {
        for (uint16_t i = 0; i < ledCount; ++i) leds[i] = CRGB::Black;
    }

    for (uint8_t b = 0; b < binCount; ++b) {
        const float ratio = static_cast<float>(b) / denom;
        float mag = bins[b];
        if (mag < 0.0f) mag = 0.0f;
        if (mag > 1.0f) mag = 1.0f;

        const uint8_t paletteIdx =
            static_cast<uint8_t>(ratio * 255.0f + 0.5f);
        const uint8_t valBri =
            static_cast<uint8_t>(static_cast<float>(brightness) * mag + 0.5f);
        if (valBri == 0) continue;
        const CRGB c =
            ColorFromPalette(palette, paletteIdx, valBri, LINEARBLEND);

        const int rIdx =
            static_cast<int>(static_cast<float>(centrePoint) + ratio * rightSpan + 0.5f);
        const int lIdx =
            static_cast<int>(static_cast<float>(centrePoint - 1) - ratio * leftSpan + 0.5f);

        if (rIdx >= 0 && rIdx < static_cast<int>(ledCount)) {
            if (additive) {
                leds[rIdx] += c;
            } else {
                leds[rIdx] = c;
            }
        }
        if (lIdx >= 0 && lIdx < static_cast<int>(ledCount) && lIdx != rIdx) {
            if (additive) {
                leds[lIdx] += c;
            } else {
                leds[lIdx] = c;
            }
        }
    }
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
