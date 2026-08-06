/**
 * @file TransitionOverlay.h
 * @brief K1 crossfade-seam adapter for the TransitionEngine (P4, flag-gated).
 *
 * Bridges the K1 effects-queue crossfade seam (render_queue_xfade_overlay in the
 * .ino) to the ported, centre-origin TransitionEngine. Holds TWO engine
 * instances (one per independent channel) plus per-channel CRGB scratch buffers
 * for the CRGB16 <-> CRGB conversion the engine requires.
 *
 * SEAM CONTRACT (mirrors the original equal-power blend it replaces):
 *   The .ino overlay snapshots the OUTGOING frame into k1_queue_xfade_out_buf
 *   (CRGB16) and renders the INCOMING frame into leds_16 (CRGB16). Under the
 *   flag, instead of the per-pixel equal-power blend, the overlay calls
 *   transitionBlendChannel(secondary, outgoing, incoming, leds_16, durationMs):
 *     - source  = outgoing snapshot (k1_queue_xfade_out_buf)
 *     - target  = incoming frame    (leds_16, just rendered)
 *     - output  = leds_16            (blended in place, CRGB16)
 *   The adapter converts source+target into its CRGB scratch, drives the engine,
 *   and converts the engine output back into leds_16. Output is byte-equivalent
 *   to a centre-origin animated crossfade; the legacy equal-power blend is the
 *   #else path in the .ino and is unchanged.
 *
 * P6 DIRECTOR API (the seam the director will call later):
 *   - transitionStartChannel(secondary, type, durationMs) selects the transition
 *     type for the NEXT crossfade on a channel (default FADE if never set).
 *   - transitionUpdateChannel(...) is the per-frame tick (called via
 *     transitionBlendChannel from the seam).
 *
 * HEAP: engines + scratch allocated ONCE in transitionOverlayInit() (boot). The
 * blend path is zero-heap. If PSRAM/SRAM alloc fails the adapter reports not-ready
 * and the .ino falls back to the legacy equal-power blend (graceful degrade).
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. Clean names; British English.
 */

#pragma once

#include <cstdint>

#include <FastLED.h>
#include "constants.h"  // CRGB16

#include "TransitionTypes.h"

namespace k1 {
namespace effects {
namespace framework {

/// Allocate the two per-channel engines + scratch (boot only). Returns false if
/// any allocation fails — the seam then keeps the legacy equal-power blend.
bool transitionOverlayInit(uint16_t stripLength);

/// True if both channel engines allocated successfully.
bool transitionOverlayReady();

/// Select the transition TYPE used for the next crossfade on a channel.
/// Eyes-on-pending types are accepted (explicit caller intent) but the P6
/// director should restrict itself to transitionIsSafeDefault() picks.
void transitionStartChannel(bool secondary, TransitionType type, uint16_t durationMs);

/**
 * @brief Drive one channel's crossfade frame, writing the blended CRGB16 output.
 *
 * Called from the .ino seam in place of the equal-power blend. `source` and
 * `target` are CRGB16 strip buffers (outgoing snapshot + incoming frame);
 * `output` is the CRGB16 strip written in place (may alias `target`). The engine
 * (re)starts on the first frame of a crossfade and is ticked thereafter.
 *
 * @param secondary  false = primary channel engine, true = secondary.
 * @param source     Outgoing frame (CRGB16, length stripLength).
 * @param target     Incoming frame (CRGB16, length stripLength).
 * @param output     Output strip (CRGB16, length stripLength); written in place.
 * @param durationMs Crossfade duration from the queue (clamped to engine).
 * @return true if the engine produced the blend; false if not ready (caller
 *         must fall back to the legacy blend).
 */
bool transitionBlendChannel(bool secondary,
                            const CRGB16* source,
                            const CRGB16* target,
                            CRGB16* output,
                            uint16_t durationMs);

}  // namespace framework
}  // namespace effects
}  // namespace k1
