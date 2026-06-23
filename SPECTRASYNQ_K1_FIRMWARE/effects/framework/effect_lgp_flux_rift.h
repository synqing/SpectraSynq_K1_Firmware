/**
 * @file effect_lgp_flux_rift.h
 * @brief LGP Flux Rift — spectral-flux dislocation seam with beat shock injection.
 *
 * Ported from firmware-v3
 * `src/effects/ieffect/LGPExperimentalAudioPack.h/.cpp`
 * (class `LGPFluxRiftEffect`, EID_LGP_FLUX_RIFT = 0x1A00, catalogue entry 152).
 * Source lines in v3: LGPExperimentalAudioPack.cpp :178-222.
 *
 * VISUAL DESCRIPTION:
 *   A tanh-compressed phase-dislocation seam bisects the LGP plate at the
 *   centre origin.  High spectral flux drives the seam outward from centre;
 *   on beat, a sharp Gaussian shock is injected along the seam boundary and
 *   decays rapidly.  The result: the plate appears to crack open with every
 *   transient and heal again as flux subsides.  Colour anchors on the chord
 *   root note (Schmitt-gate hysteresis) or the chroma circular centroid when
 *   no chord is locked.  No equivalent look in K1's current catalogue.
 *
 * AUDIO PROXY MAP (v3 ControlBus/EffectContext → K1AudioContext):
 *   v3 `ctx.audio.available`           → `ctx.audio.available()`          (method)
 *   v3 `ctx.audio.fastFlux()`          → `ctx.audio.spectralFlux()`       (proxy:
 *       K1 `spectralFlux()` reads `SBAudioSnapshot::spectral_energy`, a 1-frame-EMA
 *       of spectral novelty — not raw hop-level fastFlux.  Seam responds slightly
 *       slower than v3; acceptable for P7 first port. See p7-prep §4.2.)
 *   v3 `ctx.audio.overallSaliency()`   → `ctx.audio.rms()`                (proxy)
 *   v3 `ctx.audio.isOnBeat()`          → `ctx.audio.isOnBeat()`           (exact,
 *       with beatConfidence() >= 0.25 guard + metronome fallback)
 *   v3 `ctx.audio.chordConfidence()`   → `ctx.audio.chordConfidence()`    (direct)
 *   v3 `ctx.audio.rootNote()`          → `ctx.audio.rootNote()`           (direct)
 *   v3 `ctx.audio.chroma()[i]`         → `ctx.audio.getChroma(i)`         (direct;
 *       C-origin label → A-origin index bridge already inside getChroma())
 *   v3 `AudioReactivePolicy::signalDt` → `ctx.getSafeRawDeltaSeconds()`   (raw dt)
 *   v3 `AudioReactivePolicy::visualDt` → `ctx.getSafeDeltaSeconds()`      (speed-scaled dt)
 *   v3 `ctx.rawTotalTimeMs`            → `ctx.rawTotalTimeMs`             (direct)
 *   v3 `ctx.brightness`                → `ctx.brightness`                 (direct)
 *   v3 `ctx.palette.getColor(i, br)`   → `ColorFromPalette(*ctx.palette, i, br)` (K1 raw ptr)
 *   v3 `fadeToBlackByDt(leds,n,30,dt)` → per-strip inline `nscale8` trail fade
 *
 * GEOMETRY (v3 → K1 dual-strip):
 *   v3 loops `dist 0..HALF_LENGTH-1` (HALF_LENGTH=80) writing into a unified
 *   320-LED buffer via setCentrePairMono.  K1 dual-channel doctrine: primary
 *   strip (bottom edge) and secondary strip (top edge) are independent 160-LED
 *   buffers.  Both receive the same rift render (unified look across the physical
 *   LGP plate).  Written via `ctx.k1Buffer.primary()` / `.secondary()` K1StripView.
 *   Centre pair: index 79 (left-of-pair) + 80 (right-of-pair) per strip.
 *   dist=0 → centre pair; dist=79 → edge pair.
 *
 * STROBE LAW AUDIT (COMPLIANT):
 *   Beat drives SPATIAL position of the seam boundary (seamPos) and the spatial
 *   Gaussian shock envelope centred on the seam.  No global full-field brightness
 *   change.  The per-frame trail fade (`nscale8(230)`) is a persistence fade, not
 *   a beat-triggered flash.  `m_fluxEnv` scales per-pixel intensity in a
 *   spatially varying way (tanh field) — never a uniform multiply over all LEDs.
 *
 * MEMORY:
 *   Static members: 6× float + 1× bool + 1× uint32 = 29 bytes.  Well within 256 B.
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

class LgpFluxRift final : public IEffect {
public:
    LgpFluxRift() = default;
    ~LgpFluxRift() override = default;

    bool init(EffectContext& ctx) override;
    void render(EffectContext& ctx) override;
    void cleanup() override;
    const EffectMetadata& getMetadata() const override;

private:
    float    m_phase         = 0.0f;   ///< Phase accumulator for carrier sinusoids
    float    m_fluxEnv       = 0.0f;   ///< Smoothed flux envelope (EMA tau=0.10s)
    float    m_beatPulse     = 0.0f;   ///< Beat shock amplitude (decays at tau=0.25s)
    float    m_hue           = 24.0f;  ///< Smoothed musical hue [0,255 uint8 domain, float]
    float    m_audioPresence = 0.0f;   ///< Audio-presence envelope for silent fade
    uint32_t m_lastBeatMs    = 0;      ///< Timestamp of the last beat tick (metronome fallback)
    bool     m_chordGateOpen = false;  ///< Schmitt-trigger gate: chord-root vs chroma centroid hue
};

/// Static singleton accessor — pass to the effect registry / director.
IEffect* lgp_flux_rift_effect();

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
