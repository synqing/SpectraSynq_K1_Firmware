/**
 * @file effect_beat_pulse_resonant.h
 * @brief Beat Pulse (Resonant) — dual inward-contracting ring: white attack
 *        snap over a warm resonant body thud.
 *
 * Ported from firmware-v3 `src/effects/ieffect/BeatPulseResonantEffect.h/.cpp`
 * (EID 0x1404, class `BeatPulseResonantEffect`).  All v3 infrastructure
 * dependencies (CoreEffects.h, BeatPulseRenderUtils.h, SET_CENTER_PAIR,
 * ctx.rawTotalTimeMs) replaced with K1-framework equivalents.
 *
 * SPOT-CHECK FINDING (2026-06-19):
 *   v3 source confirmed SPATIAL — not a global brightness pulse.  Two rings
 *   travel edge → centre via independent timing (attack 280 ms, body 480 ms).
 *   Global brightness appears ONLY as a scale factor on the per-ring Gaussian
 *   / hard-edge kernel, never as a frame-wide setGlobalBrightness call.
 *   Strobe Law: COMPLIANT — beat spawns ring motion, not a full-field flash.
 *
 * GEOMETRY (v3 → K1 centre-origin):
 *   v3 loops `dist 0..HALF_LENGTH-1` and writes via SET_CENTER_PAIR which
 *   mirrors to the unified 320-LED buffer (primary strip left/right of centre,
 *   secondary strip left/right of centre).  K1 dual-strip doctrine: we write
 *   the same mirror pair directly to `ctx.k1Buffer.primary()` and
 *   `ctx.k1Buffer.secondary()` using K1StripView::set().
 *   HALF_LENGTH = stripLength (160); dist 0 = edge, dist 159 = centre.
 *   dist01 = (dist + 0.5) / 160; ring contracts: pos starts at 1.0 (edge)
 *   and moves toward 0.0 (centre).
 *
 * AUDIO PROXY MAP (v3 ControlBus → K1AudioContext):
 *   v3 `ctx.audio.isOnBeat()`          → `ctx.audio.isOnBeat()`     (direct)
 *   v3 `ctx.audio.beatStrength()`      → `ctx.audio.onsetStrength()` (proxy:
 *       onset_strength is the per-frame beat energy scalar; no beatStrength
 *       accessor on K1; semantically equivalent for ring intensity)
 *   v3 `ctx.audio.tempoConfidence()`   → `ctx.audio.beatConfidence()` (direct)
 *   v3 `ctx.audio.available`           → `ctx.audio.available()`    (method)
 *   v3 `ctx.rawTotalTimeMs`            → `ctx.rawTotalTimeMs`        (direct)
 *
 *   Fallback BPM metronome preserved identically from v3 BeatPulseTiming.
 *
 * COLOUR:
 *   v3 samples `ctx.palette.getColor(bodyPaletteIdx, brightness)`.
 *   K1: `ColorFromPalette(*ctx.palette, bodyPaletteIdx, bodyBrightU8)`.
 *   Attack ring is near-white (ATTACK_WHITE = 0.85 desaturation).
 *
 * MEMORY:
 *   State: 2× float + 1× uint32_t = 12 bytes of class members.  Well within
 *   the 256 B static budget.  No heap, no PSRAM, no IRAM_ATTR.
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

class BeatPulseResonant final : public IEffect {
public:
    BeatPulseResonant() = default;
    ~BeatPulseResonant() override = default;

    bool init(EffectContext& ctx) override;
    void render(EffectContext& ctx) override;
    void cleanup() override;
    const EffectMetadata& getMetadata() const override;

private:
    /// Intensity latch: slammed to 1.0 on beat, decays via per-ring envelopes.
    float    m_beatIntensity   = 0.0f;
    /// Timestamp (ms) of the most recent beat tick.
    uint32_t m_lastBeatTimeMs  = 0;
    /// Fallback BPM used when tempo confidence is below gate threshold.
    float    m_fallbackBpm     = 128.0f;
};

/// Static singleton accessor — pass to the effect registry / director.
IEffect* beat_pulse_resonant_effect();

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
