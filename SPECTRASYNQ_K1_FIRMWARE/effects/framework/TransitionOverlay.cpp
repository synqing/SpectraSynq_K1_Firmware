/**
 * @file TransitionOverlay.cpp
 * @brief K1 crossfade-seam adapter for the TransitionEngine (P4, flag-gated).
 *
 * See TransitionOverlay.h for the seam contract. British English throughout.
 */

#include "TransitionOverlay.h"

#include <string.h>

#include "K1BufferView.h"      // toCrgb / toCrgb16 converters
#include "TransitionEngine.h"

namespace k1 {
namespace effects {
namespace framework {

namespace {

// Two independent channel engines (primary + secondary). Constructed at static
// init (no buffers yet); buffers are allocated in transitionOverlayInit().
TransitionEngine g_enginePrimary;
TransitionEngine g_engineSecondary;

// Per-channel CRGB conversion scratch (source + target + output) and the
// pending transition type the next crossfade will use. Sized at init().
struct ChannelScratch {
    CRGB* source = nullptr;
    CRGB* target = nullptr;
    CRGB* output = nullptr;
    uint16_t length = 0;
    TransitionType pendingType = TransitionType::FADE;
    bool ready = false;
};

ChannelScratch g_scratch[2];  // [0] = primary, [1] = secondary
bool g_overlayReady = false;

ChannelScratch& scratchFor(bool secondary) { return g_scratch[secondary ? 1 : 0]; }
TransitionEngine& engineFor(bool secondary) {
    return secondary ? g_engineSecondary : g_enginePrimary;
}

// Allocate a CRGB scratch triple for one channel. Boot-time only.
bool allocChannelScratch(ChannelScratch& s, uint16_t length) {
    s.length = length;
#ifndef NATIVE_BUILD
    // CL-2 fail-closed: PSRAM ONLY, no internal-SRAM fallback. On PSRAM failure
    // s.ready stays false and transitionBlendChannel() returns false so the
    // caller falls back to the legacy equal-power blend. Never allocate internal.
    s.source = static_cast<CRGB*>(
        heap_caps_calloc(length, sizeof(CRGB), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    s.target = static_cast<CRGB*>(
        heap_caps_calloc(length, sizeof(CRGB), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    s.output = static_cast<CRGB*>(
        heap_caps_calloc(length, sizeof(CRGB), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
#else
    s.source = static_cast<CRGB*>(calloc(length, sizeof(CRGB)));
    s.target = static_cast<CRGB*>(calloc(length, sizeof(CRGB)));
    s.output = static_cast<CRGB*>(calloc(length, sizeof(CRGB)));
#endif
    s.ready = (s.source != nullptr) && (s.target != nullptr) && (s.output != nullptr);
    return s.ready;
}

}  // namespace

bool transitionOverlayInit(uint16_t stripLength) {
    if (g_overlayReady) return true;  // idempotent
    if (stripLength == 0) return false;

    bool ok = true;
    ok &= g_enginePrimary.begin(stripLength);
    ok &= g_engineSecondary.begin(stripLength);
    ok &= allocChannelScratch(g_scratch[0], stripLength);
    ok &= allocChannelScratch(g_scratch[1], stripLength);

    g_overlayReady = ok;
    return g_overlayReady;
}

bool transitionOverlayReady() { return g_overlayReady; }

void transitionStartChannel(bool secondary, TransitionType type, uint16_t durationMs) {
    (void)durationMs;  // duration is taken from the queue at blend time
    scratchFor(secondary).pendingType = type;
}

bool transitionBlendChannel(bool secondary,
                            const CRGB16* source,
                            const CRGB16* target,
                            CRGB16* output,
                            uint16_t durationMs) {
    ChannelScratch& s = scratchFor(secondary);
    TransitionEngine& engine = engineFor(secondary);

    if (!g_overlayReady || !s.ready || !engine.buffersReady() || s.length == 0) {
        return false;  // caller falls back to the legacy equal-power blend
    }

    const uint16_t n = s.length;

    // Convert the CRGB16 outgoing/incoming frames into the engine's CRGB domain.
    for (uint16_t i = 0; i < n; i++) {
        s.source[i] = toCrgb(source[i]);
        s.target[i] = toCrgb(target[i]);
    }

    // Start a fresh transition at the first frame of a crossfade. The queue
    // calls this every frame while crossfading and stops when done, so an idle
    // engine here means a new crossfade has begun. startTransition() freezes the
    // source + copies the target into the engine's own PSRAM buffers (aliasing-
    // safe) but does not itself render a frame.
    if (!engine.isActive()) {
        const TransitionType type = s.pendingType;
        const EasingCurve curve = static_cast<EasingCurve>(getDefaultEasing(type));
        engine.startTransition(s.source, s.target, s.output, type, durationMs, curve);
    }

    // Always tick exactly once per seam call so s.output carries this frame.
    // update() writes s.output (the engine's bound output) and self-completes at
    // the end of the duration; a completed engine copies target -> output.
    engine.update();

    // Convert the engine's CRGB output back into the CRGB16 output strip.
    for (uint16_t i = 0; i < n; i++) {
        output[i] = toCrgb16(s.output[i]);
    }
    return true;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1
