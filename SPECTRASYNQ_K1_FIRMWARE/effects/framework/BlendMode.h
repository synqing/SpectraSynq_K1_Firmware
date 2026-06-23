/**
 * @file BlendMode.h
 * @brief Pixel blend modes for zone/layer compositing (K1 effect framework).
 *
 * Self-contained spine port (P1) from firmware-v3
 * `src/effects/zones/BlendMode.h`. Direct-copy — FastLED-only dependency, no
 * heap, no branches beyond the mode switch.
 *
 * Namespace policy: `k1::effects::framework::BlendMode` is the canonical
 * BlendMode for this framework. Do NOT introduce another `BlendMode` enum in a
 * different namespace; future blend-related types in other domains use a
 * domain-prefixed name (LayerBlendMode, MaskBlendMode, ...).
 *
 * NOTE (P1): operates on FastLED CRGB (uint8). The K1 native render type is
 * CRGB16 (Q8.8 fixed-point); the CRGB16 blend variant is a P3 render-path
 * concern. See TODO(P2/P3 adapter — BUFFER) in EffectContext.h.
 *
 * British English in comments and identifiers.
 */

#pragma once

#include <FastLED.h>
#include <algorithm>

namespace k1 {
namespace effects {
namespace framework {

enum class BlendMode : uint8_t {
    OVERWRITE = 0,   // Replace: pixel = new
    ADDITIVE  = 1,   // Add (light accumulation) with pre-scale to avoid white-out
    MULTIPLY  = 2,   // pixel = (pixel * new) / 255
    SCREEN    = 3,   // Inverse multiply (lighten)
    OVERLAY   = 4,   // Multiply if dark, screen if light
    ALPHA     = 5,   // 50/50 mix
    LIGHTEN   = 6,   // Take brighter pixel per channel
    DARKEN    = 7,   // Take darker pixel per channel
    MODE_COUNT = 8
};

inline const char* getBlendModeName(BlendMode mode) {
    switch (mode) {
        case BlendMode::OVERWRITE: return "Overwrite";
        case BlendMode::ADDITIVE:  return "Additive";
        case BlendMode::MULTIPLY:  return "Multiply";
        case BlendMode::SCREEN:    return "Screen";
        case BlendMode::OVERLAY:   return "Overlay";
        case BlendMode::ALPHA:     return "Alpha";
        case BlendMode::LIGHTEN:   return "Lighten";
        case BlendMode::DARKEN:    return "Darken";
        default:                   return "Unknown";
    }
}

inline const char* getBlendModeName(uint8_t mode) {
    return getBlendModeName(static_cast<BlendMode>(mode));
}

/**
 * @brief Blend two pixels using the specified mode.
 * @param base  Existing pixel (destination).
 * @param blend New pixel (source).
 * @param mode  Blend mode.
 * @return Blended result.
 */
inline CRGB blendPixels(const CRGB& base, const CRGB& blend, BlendMode mode) {
    switch (mode) {
        case BlendMode::OVERWRITE:
            return blend;

        case BlendMode::ADDITIVE: {
            // Pre-scale both inputs (~70%) to leave headroom and avoid white-out.
            constexpr uint8_t ADDITIVE_SCALE = 180;
            return CRGB(
                qadd8(scale8(base.r, ADDITIVE_SCALE), scale8(blend.r, ADDITIVE_SCALE)),
                qadd8(scale8(base.g, ADDITIVE_SCALE), scale8(blend.g, ADDITIVE_SCALE)),
                qadd8(scale8(base.b, ADDITIVE_SCALE), scale8(blend.b, ADDITIVE_SCALE)));
        }

        case BlendMode::MULTIPLY:
            return CRGB(
                scale8(base.r, blend.r),
                scale8(base.g, blend.g),
                scale8(base.b, blend.b));

        case BlendMode::SCREEN:
            return CRGB(
                255 - scale8(255 - base.r, 255 - blend.r),
                255 - scale8(255 - base.g, 255 - blend.g),
                255 - scale8(255 - base.b, 255 - blend.b));

        case BlendMode::OVERLAY:
            return CRGB(
                (base.r < 128) ? scale8(base.r * 2, blend.r)
                               : 255 - scale8((255 - base.r) * 2, 255 - blend.r),
                (base.g < 128) ? scale8(base.g * 2, blend.g)
                               : 255 - scale8((255 - base.g) * 2, 255 - blend.g),
                (base.b < 128) ? scale8(base.b * 2, blend.b)
                               : 255 - scale8((255 - base.b) * 2, 255 - blend.b));

        case BlendMode::ALPHA:
            return CRGB(
                (base.r + blend.r) / 2,
                (base.g + blend.g) / 2,
                (base.b + blend.b) / 2);

        case BlendMode::LIGHTEN:
            return CRGB(
                std::max(base.r, blend.r),
                std::max(base.g, blend.g),
                std::max(base.b, blend.b));

        case BlendMode::DARKEN:
            return CRGB(
                std::min(base.r, blend.r),
                std::min(base.g, blend.g),
                std::min(base.b, blend.b));

        default:
            return blend;
    }
}

}  // namespace framework
}  // namespace effects
}  // namespace k1
