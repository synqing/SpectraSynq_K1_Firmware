/**
 * @file RenderPrimitives.h
 * @brief Context-free render primitives for centre-origin LED strips (K1 framework).
 *
 * Self-contained spine port (P1) from firmware-v3
 * `src/effects/render/RenderPrimitives.{h,cpp}`. Direct-copy — FastLED + no-heap.
 *
 * Three primitives, three motion laws:
 *   - drawDot            — discrete dot with optional motion-blur trail.
 *   - drawSpriteScrolled — additive sub-pixel buffer scroll with multiplicative
 *                          fade (wave-propagation primitive).
 *   - fillFromBins       — direct centre-origin spectral fill from frequency bins.
 *
 * Design contract (binding):
 *   - Context-free: raw `CRGB* leds`, `ledCount`, `centrePoint`. No EffectContext
 *     coupling. (Effect bases extract context fields and pass them through.)
 *   - Centre-origin: position/scroll referenced about LED `centrePoint-1` (left)
 *     and `centrePoint` (right). For K1 (ledCount=160, centrePoint=80) the centre
 *     pair is LEDs 79+80 and the edges are 0 and 159.
 *   - dt-correct: persistence/trail terms exponentiated over a 120-FPS reference
 *     (`powf(rate, dt * 120)`) → frame-rate independent.
 *     TODO(P2 adapter — FPS): K1 documents a 100-FPS target with an 8333 µs
 *       budget; audit the 120-FPS reference against measured K1 frame rate.
 *   - No heap allocation reachable from render(). A single file-scope scratch
 *     buffer in the .cpp services drawSpriteScrolled (sized for 320 LEDs).
 *   - Bounds-checked; out-of-range writes silently dropped.
 *
 * NOTE (P1): operates on FastLED CRGB (uint8). The K1 native render type is
 * CRGB16 (Q8.8 fixed-point); the CRGB16 primitive variant is a P3 render-path
 * concern. See TODO(P2/P3 adapter — BUFFER) in EffectContext.h.
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
 * @brief Draw a sub-pixel positioned dot with optional motion-blur trail.
 *
 * Position is normalised: 0.0 = centre pair, 1.0 = edges. If `prevPosition >= 0`,
 * draws an additive trail from prev to current at brightness ∝ 1/spread. Pass
 * -1.0f to disable the trail.
 *
 * @param leds         Buffer (additive — pre-clear for a hard write).
 * @param ledCount     LED count.
 * @param centrePoint  Right-of-centre index (80 for K1).
 * @param position     Normalised position [0,1]; clamped.
 * @param colour       Colour to additively blend.
 * @param opacity      Brightness scalar [0,1]; clamped.
 * @param prevPosition Previous normalised position for the trail; -1.0f disables.
 * @param mirror       Mirror symmetrically across centre (default true).
 */
void drawDot(CRGB* leds,
             uint16_t ledCount,
             uint16_t centrePoint,
             float position,
             CRGB colour,
             float opacity,
             float prevPosition = -1.0f,
             bool mirror = true);

/**
 * @brief Additive centre-origin sub-pixel buffer scroll with multiplicative fade.
 *
 * Scrolls existing content outward from centre by `scrollAmount` LEDs/call,
 * fading by `alpha`. `scrollAmount` is pre-scaled by dt by the caller; `alpha`
 * is dt-corrected internally as `powf(alpha, dt * 120)`.
 *
 * @param leds         Buffer (read-modify-write in place).
 * @param ledCount     LED count (≤ 320).
 * @param centrePoint  Right-of-centre index.
 * @param scrollAmount Fractional LEDs outward per call, dt-pre-scaled (negative = inward).
 * @param alpha        Per-frame survival at 120-FPS reference (0=clear, 1=no fade).
 * @param dt           Frame time in seconds.
 */
void drawSpriteScrolled(CRGB* leds,
                        uint16_t ledCount,
                        uint16_t centrePoint,
                        float scrollAmount,
                        float alpha,
                        float dt);

/**
 * @brief Map frequency bins to LEDs centre-origin with palette-derived colours.
 *
 * Bin 0 → centre pair; bin `binCount-1` → edges. In-between LEDs untouched.
 * Each bin's colour is sampled from `palette` and scaled by bin magnitude × brightness.
 *
 * @param leds         Buffer.
 * @param ledCount     LED count.
 * @param centrePoint  Right-of-centre index.
 * @param bins         Bin magnitudes [0,1]; clamped.
 * @param binCount     Number of bins.
 * @param palette      Colour palette (bin index → palette index linearly).
 * @param brightness   Master brightness 0–255.
 * @param additive     Additive blend if true; overwrite if false (default).
 */
void fillFromBins(CRGB* leds,
                  uint16_t ledCount,
                  uint16_t centrePoint,
                  const float* bins,
                  uint8_t binCount,
                  const CRGBPalette16& palette,
                  uint8_t brightness,
                  bool additive = false);

}  // namespace framework
}  // namespace effects
}  // namespace k1
