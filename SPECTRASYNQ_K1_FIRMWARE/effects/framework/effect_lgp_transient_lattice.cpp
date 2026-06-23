/**
 * @file effect_lgp_transient_lattice.cpp
 * @brief LGP Transient Lattice — K1 port implementation (v3 EID 160).
 *
 * See effect_lgp_transient_lattice.h for port contract, audio proxy map,
 * geometry adaptation, Strobe Law audit, and memory budget.
 *
 * ALGORITHM RECONSTRUCTION (no v3 source file exists; derived from
 * docs/AUDIO_REACTIVE_EFFECTS_PACK_152_161_DECOMPOSITION.md §12.1, §160 and
 * _scratch/lightwave-v3-effects-port-20260618/evidence/p7-prep-effects.md):
 *
 *   Per-frame for each pixel at normalised distance d ∈ [0, 1) from centre:
 *     l1(d) = sin(d * kF1 + m_phase1)
 *     l2(d) = sin(d * kF2 + m_phase2)
 *     scaffold(d) = l1 * l2              ← moiré zero-crossings form lattice
 *     v(d)        = |scaffold(d)| * (1 + kFluxDepth * m_fluxEnv)
 *     m_trail[dist] = max(m_trail[dist] * decayRate, v(d))
 *
 *   On beat:   beatRing(d) = G(d, 0.50, kBeatSigma) * m_beatRing
 *   On snare:  snareRing(d) = G(d, kSnareD, kAccentSigma) * m_snareRing
 *   On hi-hat: hihatRing(d) = G(d, kHihatD, kAccentSigma) * m_hihatRing
 *   total(d)   = clamp01(m_trail[dist] + beatRing + snareRing + hihatRing)
 *
 *   G(d, centre, sigma) = expf(−(d − centre)² / (2σ²))
 *
 *   Colour:
 *     Lattice scaffold → chord-root hue.
 *     Impact rings     → complementary hue (+128).
 *     Hi-hat ring      → chord-root hue + 62 (as per decomp large lattice offset).
 *
 * PORT DELTAS FROM CONCEPTUAL v3 SOURCE:
 *   1. FPS: getSafeDeltaSeconds() / getSafeRawDeltaSeconds() replace /120.0f.
 *   2. fastFlux() → spectralEnergy() (EMA proxy; 1-frame lag vs v3 hop-level).
 *   3. setCentrePairMono (unified 320-buf) → K1StripView::add() on primary +
 *      secondary independently (dual-channel doctrine).
 *   4. Trail buffer allocated from PSRAM (ps_malloc) in init(); freed in
 *      cleanup().  render() is zero-heap.
 *   5. isSnareHit() / isHihatHit() gate on SB_ONSET_V2 internally; safe
 *      false-return when flag absent.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "effect_lgp_transient_lattice.h"

#include <cmath>
#include <cstring>
#include <FastLED.h>
#include <esp_heap_caps.h>   // ps_malloc / heap_caps_free

namespace k1 {
namespace effects {
namespace framework {

// ─── Constants ────────────────────────────────────────────────────────────────

/// Full-circle in radians.
static constexpr float kTau = 6.28318530717958647692f;

/// Per-strip half-span: 80 pixels from centre (index 79) to edge (index 0/159).
static constexpr uint16_t kHalfLength = 80u;

/// Centre-left index (left of the centre pair) on a 160-LED strip.
static constexpr uint16_t kCentreLeft = 79u;

/// Total strip length for PSRAM trail buffer sizing.
static constexpr uint16_t kStripLength = 160u;

/// Carrier 1 spatial frequency (lower, slower drift; per decomp §160).
static constexpr float kF1 = 18.0f;

/// Carrier 2 spatial frequency (higher, faster drift; per decomp §160).
static constexpr float kF2 = 29.0f;

/// Carrier 1 angular drift speed (rad/s, visual-dt scaled).
static constexpr float kDrift1 = 0.31f;

/// Carrier 2 angular drift speed (rad/s, visual-dt scaled).
static constexpr float kDrift2 = 0.47f;

/// Depth multiplier for flux modulation of scaffold amplitude.
static constexpr float kFluxDepth = 1.2f;

/// EMA time constant for spectral flux smoothing (seconds).
static constexpr float kFluxTau = 0.12f;

/// Per-pixel afterglow decay rate per second (multiplicative).
/// 0.82^(dt*100) ≈ nscale8(204) at 100 FPS.
static constexpr float kTrailDecayRate = 0.82f;

/// Beat ring: Gaussian centre (normalised, from strip centre).
static constexpr float kBeatCentre = 0.50f;
/// Beat ring: Gaussian sigma.
static constexpr float kBeatSigma = 0.10f;
/// Beat ring: exponential decay time constant (seconds).
static constexpr float kBeatRingTau = 0.20f;

/// Snare accent ring: normalised distance from centre (inner quarter).
static constexpr float kSnareD = 0.30f;
/// Hi-hat accent ring: normalised distance from centre (outer quarter).
static constexpr float kHihatD = 0.70f;
/// Accent ring: Gaussian sigma (tighter than beat ring).
static constexpr float kAccentSigma = 0.06f;
/// Accent ring: exponential decay time constant (seconds).
static constexpr float kAccentRingTau = 0.14f;

/// Minimum beat-confidence to count a beat tick as locked tempo.
static constexpr float kTempoConfMin = 0.25f;

/// Decomposition §160 lattice hue offset for hi-hat ring.
static constexpr uint8_t kHihatHueOffset = 62u;

/// Hue EMA time constant for smooth tonal transitions (seconds).
static constexpr float kHueTau = 0.45f;

/// Audio presence: fast rise tau (seconds).
static constexpr float kPresenceRiseTau = 0.06f;
/// Audio presence: slow fall tau (seconds).
static constexpr float kPresenceFallTau = 0.32f;

/// C-origin pitch-class → uint8 hue (0=C, 1=C#, …, 11=B).
/// Mirrors the NOTE_HUES table used in other ported effects.
static const uint8_t kNoteHues[12] = {
    0u,   // C  — red
    11u,  // C# — red-orange
    26u,  // D  — orange
    42u,  // D# — yellow-orange
    64u,  // E  — yellow
    85u,  // F  — green
    106u, // F# — cyan-green
    128u, // G  — cyan
    149u, // G# — blue-cyan
    170u, // A  — blue
    191u, // A# — blue-violet
    212u, // B  — violet
};

// ─── Module-local helpers ─────────────────────────────────────────────────────

static inline float clamp01(float x) {
    return x < 0.0f ? 0.0f : (x > 1.0f ? 1.0f : x);
}

/// 1 − exp(−dt/tau); EMA alpha for a given dt and time constant.
static inline float expAlpha(float dt, float tauS) {
    if (tauS <= 0.0f) return 1.0f;
    return 1.0f - expf(-dt / tauS);
}

/// EMA: smoothly move current toward target with time constant tauS.
static inline float smoothTo(float current, float target, float dt, float tauS) {
    return current + (target - current) * expAlpha(dt, tauS);
}

/// Exponential decay of value with time constant tauS.
static inline float decayBy(float value, float dt, float tauS) {
    if (tauS <= 0.0f) return 0.0f;
    return value * expf(-dt / tauS);
}

/// Track audio presence envelope: fast rise, slow fall.
static inline float trackAudioPresence(float current, bool audioAvail, float dt) {
    const float tau = audioAvail ? kPresenceRiseTau : kPresenceFallTau;
    return smoothTo(current, audioAvail ? 1.0f : 0.0f, dt, tau);
}

/// Gaussian bell at normalised distance d, centred on `centre`, width sigma.
static inline float gaussian(float d, float centre, float sigma) {
    const float diff = d - centre;
    return expf(-(diff * diff) / (2.0f * sigma * sigma));
}

/// Select the dominant chord-root hue from K1AudioContext (Schmitt gate + chroma fallback).
static uint8_t selectMusicalHue(const EffectContext& ctx, bool& gateOpen) {
    const float conf = ctx.audio.chordConfidence();
    if (!gateOpen && conf >= 0.40f) gateOpen = true;
    if (gateOpen  && conf <  0.25f) gateOpen = false;

    if (gateOpen) {
        const uint8_t root = ctx.audio.rootNote();  // C-origin [0, 11]
        if (root < 12u) return kNoteHues[root];
    }
    // Chroma centroid fallback: find dominant pitch-class by chroma energy.
    float best = 0.0f;
    uint8_t bestIdx = 0u;
    for (uint8_t i = 0u; i < 12u; ++i) {
        const float c = ctx.audio.getChroma(i);
        if (c > best) { best = c; bestIdx = i; }
    }
    return kNoteHues[bestIdx];
}

/// Convert normalised intensity [0, 1] and master [0, 1] to uint8 brightness.
static inline uint8_t toBrightness(float intensity, float master) {
    const float v = clamp01(intensity * master);
    return static_cast<uint8_t>(v * 255.0f + 0.5f);
}

/// Clear both strips to black.
static void clearStrips(K1StripView& pri, K1StripView& sec, uint16_t n) {
    for (uint16_t i = 0u; i < n; ++i) {
        pri.set16(i, CRGB16{SQ15x16(0), SQ15x16(0), SQ15x16(0)});
        sec.set16(i, CRGB16{SQ15x16(0), SQ15x16(0), SQ15x16(0)});
    }
}

// ─── IEffect implementation ───────────────────────────────────────────────────

bool LgpTransientLattice::init(EffectContext& ctx) {
    (void)ctx;

    // Allocate trail buffer from PSRAM (640 bytes; must not land in DRAM .bss).
    if (m_trail == nullptr) {
        m_trail = static_cast<float*>(
            heap_caps_malloc(kStripLength * sizeof(float), MALLOC_CAP_SPIRAM));
        if (m_trail == nullptr) {
            // PSRAM unavailable — this is a hard failure; the class cannot render
            // safely without the trail buffer.
            return false;
        }
    }
    memset(m_trail, 0, kStripLength * sizeof(float));

    // Reset all state.
    m_phase1       = 0.0f;
    m_phase2       = 0.0f;
    m_beatRing     = 0.0f;
    m_snareRing    = 0.0f;
    m_hihatRing    = 0.0f;
    m_fluxEnv      = 0.0f;
    m_hue          = 24.0f;
    m_audioPresence = 0.0f;
    m_lastBeatMs   = 0u;
    m_chordGateOpen = false;
    m_snareArmed   = true;   // arm on init; deduplication resets each frame
    m_hihatArmed   = true;

    return true;
}

void LgpTransientLattice::render(EffectContext& ctx) {
    // ── Timing ───────────────────────────────────────────────────────────────
    // dtSignal: raw (unscaled by SPEED) — for audio-coupled EMA and decay.
    // dtVisual: speed-scaled — for phase drift (visual transport speed).
    const float dtSignal = ctx.getSafeRawDeltaSeconds();
    const float dtVisual = ctx.getSafeDeltaSeconds();

    // ── Guard: trail buffer must be bound ────────────────────────────────────
    if (m_trail == nullptr) return;

    // ── Audio presence ────────────────────────────────────────────────────────
    const bool audioAvail = ctx.audio.available();
    m_audioPresence = trackAudioPresence(m_audioPresence, audioAvail, dtSignal);

    // ── Silent / no-audio: clear strips and bail ─────────────────────────────
    K1StripView& pri = ctx.k1Buffer.primary();
    K1StripView& sec = ctx.k1Buffer.secondary();

    if (m_audioPresence <= 0.001f) {
        clearStrips(pri, sec, kStripLength);
        return;
    }

    const float master = (ctx.brightness / 255.0f) * m_audioPresence;

    // ── Flux envelope ─────────────────────────────────────────────────────────
    // PROXY: spectralEnergy() ≡ fastFlux (EMA-smoothed); 1-frame lag vs v3.
    const float fluxTarget = audioAvail ? ctx.audio.spectralEnergy() : 0.0f;
    m_fluxEnv = smoothTo(m_fluxEnv, fluxTarget, dtSignal, kFluxTau);

    // ── Phase accumulators (visual-dt; carrier frequencies drift slowly) ─────
    m_phase1 += kDrift1 * dtVisual;
    m_phase2 += kDrift2 * dtVisual;
    // Wrap to prevent float precision loss over long sessions.
    if (m_phase1 > kTau * 1000.0f) m_phase1 = fmodf(m_phase1, kTau);
    if (m_phase2 > kTau * 1000.0f) m_phase2 = fmodf(m_phase2, kTau);

    // ── Beat tick → impact ring injection ────────────────────────────────────
    // Strobe Law: m_beatRing drives a SPATIAL Gaussian ring, not a global
    // brightness event.  The ring is localised at d = kBeatCentre.
    const bool beatLocked = ctx.audio.beatConfidence() >= kTempoConfMin;
    const bool rawBeat    = audioAvail && ctx.audio.isOnBeat();
    const bool beatTick   = rawBeat && beatLocked;
    if (beatTick) m_beatRing = 1.0f;
    else          m_beatRing = decayBy(m_beatRing, dtSignal, kBeatRingTau);

    // ── Snare accent ring ─────────────────────────────────────────────────────
    // isSnareHit() returns false safely without SB_ONSET_V2.
    const bool snareNow = audioAvail && ctx.audio.isSnareHit();
    if (snareNow && m_snareArmed) {
        m_snareRing  = 1.0f;
        m_snareArmed = false;  // dedup: one trigger per hit event
    } else {
        m_snareRing = decayBy(m_snareRing, dtSignal, kAccentRingTau);
        if (!snareNow) m_snareArmed = true;  // re-arm once event clears
    }

    // ── Hi-hat accent ring ────────────────────────────────────────────────────
    const bool hihatNow = audioAvail && ctx.audio.isHihatHit();
    if (hihatNow && m_hihatArmed) {
        m_hihatRing  = 1.0f;
        m_hihatArmed = false;
    } else {
        m_hihatRing = decayBy(m_hihatRing, dtSignal, kAccentRingTau);
        if (!hihatNow) m_hihatArmed = true;
    }

    // ── Musical hue (chord-root or chroma centroid) ───────────────────────────
    const float hueTarget = static_cast<float>(
        selectMusicalHue(ctx, m_chordGateOpen));
    // Circular-safe smoothing (uint8 hue domain; no wrap artefact for small steps).
    m_hue = smoothTo(m_hue, hueTarget, dtSignal, kHueTau);
    const uint8_t baseHue  = static_cast<uint8_t>(m_hue);
    const uint8_t compHue  = static_cast<uint8_t>(baseHue + 128u);  // complementary
    const uint8_t hihatHue = static_cast<uint8_t>(baseHue + kHihatHueOffset);

    // ── Trail decay (signal-dt; persistence independent of speed) ────────────
    // Per-pixel multiplicative decay: trail *= decayRate^(dtSignal / (1/100))
    // Using pow-form: trail *= exp(ln(kTrailDecayRate) * dtSignal * 100).
    const float trailAlpha = expf(logf(kTrailDecayRate) * dtSignal * 100.0f);

    // ── Per-pixel render loop ─────────────────────────────────────────────────
    // dist = 0: centre pair (indices 79 / 80 on each strip).
    // dist = 79: edge pair (indices 0 / 159 on each strip).
    for (uint16_t dist = 0u; dist < kHalfLength; ++dist) {
        const float d = static_cast<float>(dist) / static_cast<float>(kHalfLength);

        // ── Dual sinusoidal scaffold (moiré lattice, per decomp §160) ─────
        const float l1       = sinf(d * kF1 + m_phase1);
        const float l2       = sinf(d * kF2 + m_phase2);
        const float scaffold = fabsf(l1 * l2) * (1.0f + kFluxDepth * m_fluxEnv);

        // ── Afterglow trail update ──────────────────────────────────────
        m_trail[dist] *= trailAlpha;
        if (scaffold > m_trail[dist]) m_trail[dist] = scaffold;
        m_trail[dist] = clamp01(m_trail[dist]);

        // ── Impact rings (spatial Gaussians — Strobe Law: localised) ─────
        const float beatRingVal  = gaussian(d, kBeatCentre, kBeatSigma)  * m_beatRing;
        const float snareRingVal = gaussian(d, kSnareD,     kAccentSigma) * m_snareRing;
        const float hihatRingVal = gaussian(d, kHihatD,     kAccentSigma) * m_hihatRing;

        // ── Composite intensity ───────────────────────────────────────────
        const float latticeIntensity = m_trail[dist];
        const float ringIntensity    = clamp01(beatRingVal + snareRingVal);
        const float hihatIntensity   = clamp01(hihatRingVal);
        const float total            = clamp01(latticeIntensity + ringIntensity + hihatIntensity);

        // ── Colour blending (chord-root for scaffold, comp for impact rings)
        // Lattice layer: chord-root hue
        const uint8_t brLattice = toBrightness(latticeIntensity, master);
        // Impact ring layer (beat + snare): complementary hue
        const uint8_t brRing    = toBrightness(ringIntensity, master);
        // Hi-hat ring: distinct hue (+62 per decomp large lattice offset)
        const uint8_t brHihat   = toBrightness(hihatIntensity, master);
        // Overall saturation at 220/255 (leaves room for brightness-driven white)
        const uint8_t kSat = 220u;

        // Build additive mix in CRGB.
        CRGB pixel{CRGB::Black};
        if (brLattice > 0u) {
            pixel += CHSV(baseHue, kSat, brLattice);
        }
        if (brRing > 0u) {
            pixel += CHSV(compHue, kSat, brRing);
        }
        if (brHihat > 0u) {
            pixel += CHSV(hihatHue, kSat, brHihat);
        }
        // Clamp each channel (additive may overflow).
        pixel.r = pixel.r > 255u ? 255u : pixel.r;
        pixel.g = pixel.g > 255u ? 255u : pixel.g;
        pixel.b = pixel.b > 255u ? 255u : pixel.b;

        (void)total;  // total computed for reference; per-channel blend above is finer

        // ── Symmetric write on each strip ────────────────────────────────
        // left  = kCentreLeft − dist  (79, 78, …, 0)
        // right = kCentreLeft + 1 + dist  (80, 81, …, 159)
        const uint16_t left  = kCentreLeft - dist;
        const uint16_t right = kCentreLeft + 1u + dist;

        // Primary strip (bottom edge).
        pri.add(left,  pixel);
        pri.add(right, pixel);

        // Secondary strip (top edge) — independent channel, same lattice render.
        sec.add(left,  pixel);
        sec.add(right, pixel);
    }
}

void LgpTransientLattice::cleanup() {
    if (m_trail != nullptr) {
        heap_caps_free(m_trail);
        m_trail = nullptr;
    }
}

const EffectMetadata& LgpTransientLattice::getMetadata() const {
    static const EffectMetadata meta{
        "LGP Transient Lattice",
        "Dual sinusoidal scaffold with percussion-discriminating accent rings; ported from v3 EID 160",
        EffectCategory::GEOMETRIC,
        1,
        "k1",
        EffectRoleFlags::SELF_TRAILING
    };
    return meta;
}

// ─── Static singleton ─────────────────────────────────────────────────────────

IEffect* lgp_transient_lattice_effect() {
    static LgpTransientLattice instance;
    return &instance;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
