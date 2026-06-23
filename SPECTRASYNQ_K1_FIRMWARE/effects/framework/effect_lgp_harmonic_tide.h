/**
 * @file effect_lgp_harmonic_tide.h
 * @brief K1 port of v3 EID 154 — LGP Harmonic Tide (P7 Batch-1).
 *
 * Chord-anchored tidal wave field: three superposed sinusoidal wave families
 * (outward, inward, standing) propagate from centre to edges. Wave speed is
 * driven by midrange energy; amplitude is enveloped by chord confidence so
 * the effect falls quiet during atonal passages and comes alive on tonal music.
 * Colour is derived from the detected chord root (root / third / fifth triad
 * hues blended by distance from centre), all via K1AudioContext accessors.
 *
 * Audio surface used:
 *   - ctx.audio.chordConfidence()   — harmonic saliency proxy; tide amplitude
 *   - ctx.audio.mid()               — wave propagation speed (heavyMid proxy)
 *   - ctx.audio.rootNote()          — C-origin chord root for hue anchor
 *   - ctx.audio.isMajor()/isMinor() — third interval (major=4, minor=3)
 *   - ctx.audio.getChroma(i)        — dominant note fallback (no chord lock)
 *   - ctx.audio.available()         — guard; fade to black when unavailable
 *   - ctx.audio.isSilent()          — graceful silence decay
 *
 * Strobe Law: COMPLIANT. No beat-triggered brightness events. Amplitude is
 * modulated by chordConfidence(), a slow-moving harmonic signal. All brightness
 * changes are spatial (wave position through plate), never full-field.
 *
 * Heap discipline: all state is ≤ 6 floats + 1 bool in class members (DRAM).
 * No PSRAM, no malloc, no new, no IRAM_ATTR.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. The shipping k1_hardware build
 * never includes this translation unit.
 *
 * Namespace: k1::effects::framework. British English in comments.
 */

#pragma once

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "IEffect.h"
#include "EffectContext.h"
#include "EffectMetadata.h"

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief LGP Harmonic Tide — chord-anchored tidal wave field (EID 154 port).
 *
 * Static member count: 6 floats + 1 bool = 25 bytes. Well within the 256 B
 * static budget; no PSRAM or render-path allocation required.
 */
class LgpHarmonicTide final : public IEffect {
public:
    LgpHarmonicTide() = default;

    // ── IEffect lifecycle ──

    bool init(EffectContext& ctx) override;
    void render(EffectContext& ctx) override;
    void cleanup() override;

    const EffectMetadata& getMetadata() const override;

private:
    /// Global phase accumulator — drives wave travel speed.
    float m_phase        = 0.0f;
    /// Smoothed harmonic saliency (chordConfidence proxy).
    float m_harmonic     = 0.0f;
    /// Circular-smoothed root note index [0, 12).
    float m_rootSmooth   = 0.0f;
    /// Hue carry-over for smooth tonal transitions (circular smoothing).
    float m_hue          = 24.0f;
    /// Audio presence tracker — fades out during silence.
    float m_audioPresence = 0.0f;
    /// Schmitt-trigger gate: true when chord confidence ≥ 0.40, clears at 0.25.
    bool  m_chordGateOpen = false;
};

/// Return a pointer to the single static instance of LgpHarmonicTide.
IEffect* lgp_harmonic_tide_effect();

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
