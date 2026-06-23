/**
 * @file FrameBlend.h
 * @brief Whole-image one-pole IIR frame post-process (K1 effect framework).
 *
 * Self-contained spine port (P1) from firmware-v3
 * `src/effects/render/FrameBlend.{h,cpp}`. Direct-copy — pure FastLED math.
 *
 * `applyFrameBlending` replaces per-effect fade-to-black motion mechanisms with
 * a single mood-controlled blend across the whole frame buffer.
 *
 * Integration point (a LATER phase, NOT P1): the render path calls this once per
 * frame after all effects + zone composition, before FastLED.show(). The
 * previous-frame buffer is owned by the caller.
 *
 * Design contract (binding):
 *   - Persistence is mood-driven: mood=0 → no blend; mood=255 → coeff 0.92.
 *   - dt-correct: coefficient exponentiated over a 120-FPS reference.
 *     TODO(P2 adapter — FPS): audit the 120-FPS reference vs measured K1 rate.
 *   - In-place; caller owns both buffers. No heap allocation.
 *
 * NOTE (P1): operates on FastLED CRGB (uint8). K1's native render type is CRGB16
 * (Q8.8 fixed-point); the CRGB16 variant is a P3 render-path concern.
 * See TODO(P2/P3 adapter — BUFFER) in EffectContext.h.
 *
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

#include <FastLED.h>

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief Whole-image one-pole IIR blend, mood-controlled persistence.
 *
 * Per-pixel:
 *   blendCoeff   = (mood / 255) × 0.92
 *   dtCorrected  = blendCoeff ^ (dt × 120)
 *   leds[i]      = prevFrame[i] × dtCorrected + leds[i] × (1 - dtCorrected)
 *   prevFrame[i] = leds[i]
 *
 * mood=0 short-circuits the blend (output == input) and syncs prevFrame.
 *
 * @param leds       Current frame buffer (read + written in place).
 * @param prevFrame  Previous frame buffer (read + written in place; caller-owned).
 * @param ledCount   Number of LEDs in both buffers.
 * @param mood       Persistence knob (0–255). 0 = no blend, 255 = soft trails.
 * @param dt         Frame interval in seconds.
 */
void applyFrameBlending(CRGB* leds,
                        CRGB* prevFrame,
                        uint16_t ledCount,
                        uint8_t mood,
                        float dt);

}  // namespace framework
}  // namespace effects
}  // namespace k1
