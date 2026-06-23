/**
 * @file effect_lgp_transient_lattice.h
 * @brief LGP Transient Lattice — dual sinusoidal scaffold with percussion-
 *        discriminating accent rings (K1 port of v3 EID 160, P7 Batch-1).
 *
 * VISUAL DESCRIPTION:
 *   Two sinusoidal lattice carriers (`l1 * l2`) produce a moiré scaffold whose
 *   zero-crossings form a slowly drifting interference pattern across the LGP
 *   plate.  Each pixel accumulates scaffold value into a per-pixel afterglow
 *   (trail) buffer that decays at a configurable rate, giving the lattice a
 *   luminous memory.  Three classes of percussive event drive distinct spatial
 *   ring events:
 *     - Beat (isOnBeat):  primary Gaussian impact ring expanding from centre
 *       (d = 0.5, inner half-plate), complementary hue.
 *     - Snare (isSnareHit): accent ring fixed at d = 0.3 (inner quarter),
 *       complementary hue.
 *     - Hi-hat (isHihatHit): accent ring fixed at d = 0.7 (outer quarter),
 *       chord-root hue + offset.
 *   Each ring decays exponentially in brightness from its emission time.
 *   Spectral flux modulates the depth of the lattice scaffold, making the
 *   pattern more complex during dense musical passages.  Chord root anchors
 *   the lattice colour.
 *
 *   K1 is the only platform with both snare and hi-hat channels live; this
 *   effect is therefore the most musically granular visual in the catalogue.
 *
 * AUDIO SURFACE (v3 → K1AudioContext proxies, per p7-prep §EID-160):
 *   v3 `ctx.audio.fastFlux()`    → `ctx.audio.spectralEnergy()`  (EMA proxy;
 *       documented below as PROXY — 1-frame delay vs v3 hop-level fastFlux)
 *   v3 `ctx.audio.isOnBeat()`    → `ctx.audio.isOnBeat()`        (exact)
 *   v3 `ctx.audio.isSnareHit()`  → `ctx.audio.isSnareHit()`      (exact,
 *       SB_ONSET_V2 gate; falls back to false when flag absent)
 *   v3 `ctx.audio.isHihatHit()`  → `ctx.audio.isHihatHit()`      (exact,
 *       SB_ONSET_V2 gate; falls back to false when flag absent)
 *   v3 `ctx.audio.chroma[i]`     → `ctx.audio.getChroma(i)`      (C-origin
 *       label; rotation applied internally in K1AudioContext)
 *
 * GEOMETRY (v3 → K1 dual-strip):
 *   v3 addressed a unified buffer via `setCentrePairMono`.  K1 dual-channel
 *   doctrine: primary strip (bottom edge) and secondary strip (top edge) are
 *   independent 160-LED CRGB16 buffers.  This effect writes both strips with
 *   the same lattice render — symmetric visual across both channels.
 *   `dist` iterates 0..79 (kHalfLength); each `dist` maps to a pair of mirror
 *   indices on each strip: left = kCentreLeft − dist, right = kCentreLeft + 1 + dist.
 *
 * STROBE LAW: COMPLIANT.
 *   Beat, snare, and hi-hat transients each drive a SPATIAL Gaussian ring at a
 *   fixed normalised distance on the plate.  No global-brightness event.  The
 *   impact ring Gaussian `expf(−(d − centre)² / (2σ²))` is localised in space.
 *   `m_fluxEnv` scales per-pixel scaffold depth in a spatially varying way —
 *   never a uniform multiply over all LEDs.  The afterglow trail fade is a
 *   persistence operation, not a beat-triggered flash.
 *
 * MEMORY:
 *   `m_trail[kStripLength]` — 160 floats = 640 bytes — allocated from PSRAM
 *   in `init()` via `ps_malloc`; freed in `cleanup()`.  Class members that
 *   remain in DRAM: 8 floats + 3 bools + 1 uint32 = ~37 bytes, well within
 *   the 256 B static DRAM budget.  No allocation in render().  No IRAM_ATTR.
 *
 * PORT NOTES:
 *   - No v3 source file exists for EID 160 in the Lightwave-Ledstrip repo as of
 *     2026-06-19; the implementation reconstructs the algorithm from the
 *     decomposition document (§12.1, §160) and p7-prep-effects.md EID-160 entry.
 *   - All carrier frequency and decay constants originate from the decomposition
 *     spec; no v3 verbatim lines to preserve.
 *   - FPS: uses `ctx.getSafeDeltaSeconds()` / `ctx.getSafeRawDeltaSeconds()`.
 *     No /120.0f hardcoding.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1.  The shipping k1_hardware build
 * never includes this translation unit.
 *
 * Namespace: k1::effects::framework.  British English in comments and identifiers.
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

/**
 * @brief LGP Transient Lattice — percussion-discriminating moiré scaffold
 *        with per-channel accent rings (v3 EID 160 port).
 *
 * DRAM budget: 8× float + 3× bool + 1× uint32 = ~37 bytes.
 * PSRAM: 160× float (m_trail) = 640 bytes, allocated in init().
 */
class LgpTransientLattice final : public IEffect {
public:
    LgpTransientLattice() = default;
    ~LgpTransientLattice() override = default;

    // ── IEffect lifecycle ──────────────────────────────────────────────────

    bool init(EffectContext& ctx) override;
    void render(EffectContext& ctx) override;
    void cleanup() override;

    const EffectMetadata& getMetadata() const override;

private:
    // ── Lattice carrier phase accumulators (DRAM, hot) ────────────────────
    /// Phase of carrier 1 (lower spatial frequency, slow drift).
    float m_phase1       = 0.0f;
    /// Phase of carrier 2 (higher spatial frequency, faster drift).
    float m_phase2       = 0.0f;

    // ── Impact ring states (one per percussion class) ─────────────────────
    /// Primary ring amplitude (beat); decays from 1.0 at tau = kBeatRingTau.
    float m_beatRing     = 0.0f;
    /// Snare accent ring amplitude; decays from 1.0 at tau = kAccentRingTau.
    float m_snareRing    = 0.0f;
    /// Hi-hat accent ring amplitude; decays from 1.0 at tau = kAccentRingTau.
    float m_hihatRing    = 0.0f;

    // ── Audio / colour smoothing ─────────────────────────────────────────
    /// Smoothed spectral flux / energy envelope (EMA tau = kFluxTau).
    float m_fluxEnv      = 0.0f;
    /// Smoothed lattice hue in uint8 float domain [0, 255).
    float m_hue          = 24.0f;
    /// Audio presence envelope (fast rise, slow fall EMA).
    float m_audioPresence = 0.0f;

    // ── Timing / gating ──────────────────────────────────────────────────
    /// Timestamp of last beat tick (ms); used for metronome fallback guard.
    uint32_t m_lastBeatMs = 0u;
    /// Schmitt-trigger gate: chord confidence ≥ 0.40 opens, clears at 0.25.
    bool m_chordGateOpen = false;
    /// Deduplication flags — prevent ring re-trigger within the same frame.
    bool m_snareArmed    = false;
    bool m_hihatArmed    = false;

    // ── PSRAM-allocated trail buffer ─────────────────────────────────────
    /// Per-pixel afterglow buffer [0, 1]; 160 floats = 640 B, lives in PSRAM.
    float* m_trail = nullptr;
};

/// Return a pointer to the single static instance of LgpTransientLattice.
IEffect* lgp_transient_lattice_effect();

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
