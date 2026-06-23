/**
 * @file effect_lgp_beat_prism.h
 * @brief LGP Beat Prism — onset-driven prism-texture radiating from plate centre.
 *
 * Ported from firmware-v3
 * `src/effects/ieffect/LGPBeatPrismOnsetEffect.h/.cpp`
 * (EID_LGP_BEAT_PRISM_ONSET = 0x1E00, class `LGPBeatPrismOnsetEffect`).
 * Catalogue entry: v3-catalog.md EID 153 / LGP Beat Prism family (onset-driven
 * variant selected as the canonical K1 port — kick/snare/hihat channels map
 * directly to K1AudioContext without proxy gaps).
 *
 * VISUAL DESCRIPTION:
 *   Spoke/facet/refract carriers form a prism texture radiating from the LGP
 *   plate centre.  Three percussion channels drive three visual dimensions:
 *     Kick  → radial pressure-front ring propagating outward from centre.
 *     Snare → prism refraction intensity (spoke density, speed, front sharpness).
 *     Hihat → high-frequency shimmer overlay on the spoke field.
 *   Continuous treble energy (getBand 5-7) is the primary prism driver; onset
 *   channels are accents on top.  Hue anchors on chord root note via chroma
 *   circular centroid when chord confidence is below the gate.
 *   No equivalent in K1's current effect catalogue.
 *
 * AUDIO PROXY MAP (v3 ControlBus/EffectContext → K1AudioContext):
 *   v3 `ctx.audio.available`           → `ctx.audio.available()`         (method)
 *   v3 `ctx.audio.audioConfidence()`   → `ctx.audio.beatConfidence()`     (proxy:
 *       K1 has no audioConfidence() composite; beatConfidence() is the PLL-lock
 *       quality scalar and the nearest single-value confidence term)
 *   v3 `ctx.audio.isKickHit()`         → `ctx.audio.isKickHit()`          (direct)
 *   v3 `ctx.audio.isSnareHit()`        → `ctx.audio.isSnareHit()`         (direct)
 *   v3 `ctx.audio.isHihatHit()`        → `ctx.audio.isHihatHit()`         (direct)
 *   v3 `ctx.audio.bands()[5..7]`       → `ctx.audio.getBand(5..7)`        (fold)
 *   v3 `ctx.audio.chordConfidence()`   → `ctx.audio.chordConfidence()`    (direct)
 *   v3 `ctx.audio.rootNote()`          → `ctx.audio.rootNote()`           (direct)
 *   v3 `ctx.audio.chroma()[i]`         → `ctx.audio.getChroma(i)`         (direct,
 *       C-origin label → A-origin index bridge already inside getChroma())
 *   v3 `AudioReactivePolicy::signalDt` → `ctx.getSafeRawDeltaSeconds()`   (raw dt)
 *   v3 `AudioReactivePolicy::visualDt` → `ctx.getSafeDeltaSeconds()`      (speed-scaled dt)
 *   v3 `ctx.rawTotalTimeMs`            → `ctx.rawTotalTimeMs`             (direct)
 *   v3 `ctx.brightness`                → `ctx.brightness`                 (direct)
 *   v3 `ctx.palette.getColor(i, br)`   → `ColorFromPalette(*ctx.palette, i, br)` (K1 raw ptr)
 *   v3 `fadeToBlackByDt(leds,n,30,dt)` → per-strip `fadeToBlackBy` scaled by dt (inline)
 *
 * GEOMETRY (v3 → K1 dual-strip):
 *   v3 loops `dist 0..HALF_LENGTH-1` (HALF_LENGTH=80) and writes four pixels
 *   per distance via SET_CENTER_PAIR — two mirror pairs across a unified 320
 *   buffer.  K1 dual-channel doctrine: primary strip (bottom edge) receives the
 *   prism pattern; secondary strip (top edge) runs the same pattern independently
 *   (unified prism show across both physical channels).  Written via
 *   `ctx.k1Buffer.primary()` and `ctx.k1Buffer.secondary()` K1StripView::set().
 *   Centre pair: indices 79 (left-of-centre) + 80 (right-of-centre) per strip.
 *   dist=0 → centre pair; dist=79 → edge pair.
 *
 * STROBE LAW AUDIT (COMPLIANT):
 *   Beat/onset events drive SPATIAL position (kick front ring travel from centre
 *   outward, spoke density, shimmer texture).  No global full-field brightness
 *   toggle on beat.  `fadeToBlackBy` is a per-frame trail fade (persistence),
 *   not a beat-triggered full-field flash.
 *
 * MEMORY:
 *   Static members: 8× float + 1× bool = 33 bytes.  Well within 256 B budget.
 *   No heap allocation in render().  No PSRAM.  No IRAM_ATTR.
 *
 * Compiled only under K1_EFFECT_FRAMEWORK_V1.
 * Namespace: k1::effects::framework.
 * British English in comments and identifiers.
 */

#pragma once

#ifdef K1_EFFECT_FRAMEWORK_V1

#include <cstdint>
#include <FastLED.h>

#include "IEffect.h"
#include "EffectContext.h"
#include "EffectMetadata.h"

namespace k1 {
namespace effects {
namespace framework {

class LgpBeatPrism final : public IEffect {
public:
    LgpBeatPrism() = default;
    ~LgpBeatPrism() override = default;

    bool init(EffectContext& ctx) override;
    void render(EffectContext& ctx) override;
    void cleanup() override;
    const EffectMetadata& getMetadata() const override;

private:
    float m_phase         = 0.0f;  ///< Shared phase accumulator (spoke / facet / refract)
    float m_prism         = 0.0f;  ///< Smoothed prism intensity [0,1]
    float m_kickPulse     = 0.0f;  ///< Kick-driven beat-front radial pulse envelope
    float m_snareBurst    = 0.0f;  ///< Snare-driven prism refraction accent
    float m_hihatShimmer  = 0.0f;  ///< Hihat-driven spoke shimmer overlay
    float m_hue           = 24.0f; ///< Smoothed hue (chord-anchored, degrees 0–255)
    float m_audioPresence = 0.0f;  ///< Audio-presence envelope (rise/fall EMA)
    bool  m_chordGateOpen = false; ///< Schmitt-trigger gate for chord-hue lock
};

/// Static singleton accessor — pass to the effect registry / director.
IEffect* lgp_beat_prism_effect();

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
