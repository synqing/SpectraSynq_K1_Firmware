/**
 * @file FrameBlend.cpp
 * @brief Implementation of applyFrameBlending (K1 effect framework, P1 spine).
 *
 * Self-contained spine port from firmware-v3
 * `src/effects/render/FrameBlend.cpp`. Per-pixel cost ~one float multiply-add
 * plus a CRGB lerp; well under the per-frame render ceiling.
 *
 * Compiled ONLY under the `k1_effect_framework` env (K1_EFFECT_FRAMEWORK_V1).
 * Guarded so the TU is inert if ever pulled into another build's source filter.
 *
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "FrameBlend.h"

#include <cmath>

namespace k1 {
namespace effects {
namespace framework {

static inline CRGB lerpCRGB(const CRGB& a, const CRGB& b, float mix) {
    if (mix <= 0.0f) return a;
    if (mix >= 1.0f) return b;
    const float inv = 1.0f - mix;
    int r = static_cast<int>(static_cast<float>(a.r) * inv +
                             static_cast<float>(b.r) * mix + 0.5f);
    int g = static_cast<int>(static_cast<float>(a.g) * inv +
                             static_cast<float>(b.g) * mix + 0.5f);
    int b8 = static_cast<int>(static_cast<float>(a.b) * inv +
                              static_cast<float>(b.b) * mix + 0.5f);
    if (r < 0) r = 0; else if (r > 255) r = 255;
    if (g < 0) g = 0; else if (g > 255) g = 255;
    if (b8 < 0) b8 = 0; else if (b8 > 255) b8 = 255;
    return CRGB(static_cast<uint8_t>(r),
                static_cast<uint8_t>(g),
                static_cast<uint8_t>(b8));
}

void applyFrameBlending(CRGB* leds,
                        CRGB* prevFrame,
                        uint16_t ledCount,
                        uint8_t mood,
                        float dt) {
    if (leds == nullptr || prevFrame == nullptr || ledCount == 0) {
        return;
    }

    if (mood == 0) {
        for (uint16_t i = 0; i < ledCount; ++i) {
            prevFrame[i] = leds[i];
        }
        return;
    }

    const float blendCoeff =
        (static_cast<float>(mood) / 255.0f) * 0.92f;

    float dtCorrected;
    if (dt <= 0.0f) {
        dtCorrected = blendCoeff;
    } else if (blendCoeff < 1.0e-6f) {
        dtCorrected = 0.0f;
    } else {
        dtCorrected = ::powf(blendCoeff, dt * 120.0f);
        if (dtCorrected < 0.0f) dtCorrected = 0.0f;
        if (dtCorrected > 1.0f) dtCorrected = 1.0f;
    }

    const float mixToCurrent = 1.0f - dtCorrected;

    for (uint16_t i = 0; i < ledCount; ++i) {
        const CRGB blended = lerpCRGB(prevFrame[i], leds[i], mixToCurrent);
        leds[i] = blended;
        prevFrame[i] = blended;
    }
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
