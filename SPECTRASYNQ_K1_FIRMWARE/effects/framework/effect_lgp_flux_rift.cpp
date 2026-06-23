/**
 * @file effect_lgp_flux_rift.cpp
 * @brief LGP Flux Rift — K1 port implementation (EID 152, v3 source :178-222).
 *
 * See effect_lgp_flux_rift.h for port contract, audio proxy map, geometry
 * adaptation, Strobe Law audit, and memory budget.
 *
 * PORT DELTA FROM v3 LGPFluxRiftEffect::render():
 *   1. ctx.audio.available (bool field)   → ctx.audio.available() (method).
 *   2. ctx.audio.fastFlux()               → ctx.audio.spectralFlux()
 *      (1-frame-EMA proxy; seam slightly slower than v3 — documented in .h).
 *   3. ctx.audio.overallSaliency()        → ctx.audio.rms().
 *   4. AudioReactivePolicy::audioBeatTick → computeBeatTick() local helper
 *      (K1 beatConfidence() >= 0.25 gate + metronome fallback at 128 BPM).
 *   5. ctx.audio.chroma() pointer         → ctx.audio.getChroma(i) per-index.
 *   6. ctx.palette.getColor(idx, br)      → ColorFromPalette(*ctx.palette, idx, br).
 *   7. fadeToBlackByDt(leds, n, 30, dt)   → per-strip nscale8 inline loop.
 *   8. setCentrePairMono (unified 320-buf) → explicit K1StripView::set() on
 *      primary + secondary, each 160-LED, centre pair at idx 79/80.
 *   9. /120.0f FPS factor removed; phase advance uses ctx.getSafeDeltaSeconds()
 *      (real measured dt — see EffectContext.h FPS note).
 *  10. AudioReactivePolicy::signalDt      → ctx.getSafeRawDeltaSeconds().
 *  11. AudioReactivePolicy::visualDt      → ctx.getSafeDeltaSeconds().
 *  All render maths constants preserved verbatim from v3.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "effect_lgp_flux_rift.h"

#include <cmath>
#include <FastLED.h>

namespace k1 {
namespace effects {
namespace framework {

// ─── Module-local constants (verbatim from v3 LGPExperimentalAudioPack.cpp) ──

/// Full-circle in radians.
static constexpr float kTau = 6.28318530717958647692f;

/// Per-strip half-span: 80 pixels from centre (index 79) to edge (index 0 / 159).
static constexpr uint16_t kHalfLength = 80u;

/// Centre-left index (left of the centre pair).
static constexpr uint16_t kCentreLeft = 79u;

/// Minimum beat-confidence threshold for locked-tempo gating (mirrors v3 kTempoConfMin).
static constexpr float kTempoConfMin = 0.25f;

/// Fallback BPM for the metronome when tempo is not locked.
static constexpr float kFallbackBpm = 128.0f;

/// Per-frame trail fade factor applied via nscale8 (mirrors v3 fadeToBlackByDt scale=30).
/// At ~100 FPS, nscale8(230) ≈ 30/255 fade per frame, matching the v3 behaviour.
static constexpr uint8_t kFadeScale = 230u;

/// Note-to-hue look-up table: pitch class [0=C .. 11=B] → uint8 hue (C-origin).
/// Copied verbatim from v3 NOTE_HUES[12].
static constexpr uint8_t kNoteHues[12] = {
    0, 12, 24, 40, 56, 74, 92, 112, 134, 154, 178, 202
};

// ─── Module-local inline helpers ─────────────────────────────────────────────

/// Clamp v to [0, 1].
static inline float clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

/// Exponential-decay alpha for EMA: 1 - exp(-dt / tauS).
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

/// Track audio presence (fast rise, slow fall EMA).
static inline float trackAudioPresence(float current, bool audioAvailable, float dtSignal) {
    const float tau = audioAvailable ? 0.06f : 0.32f;
    return smoothTo(current, audioAvailable ? 1.0f : 0.0f, dtSignal, tau);
}

/// Fallback sine oscillator for the no-audio visual state.
static inline float fallbackSine(uint32_t rawMs, float rate, float phaseOffset = 0.0f) {
    return 0.5f + 0.5f * sinf(static_cast<float>(rawMs) * rate + phaseOffset);
}

/// Float [0,1] * master → uint8 brightness (clamped).
static inline uint8_t toBrightness(float intensity, float master) {
    return static_cast<uint8_t>(255.0f * clamp01(intensity) * clamp01(master));
}

/**
 * @brief Resolve a beat tick: locked PLL or metronome fallback.
 *
 * K1 K1AudioContext adaptation of v3 AudioReactivePolicy::audioBeatTick().
 * Uses ctx.audio.isOnBeat() when beatConfidence() >= kTempoConfMin, otherwise
 * fires a metronome at kFallbackBpm.
 */
static bool computeBeatTick(const EffectContext& ctx, uint32_t& lastBeatMs) {
    const bool locked = ctx.audio.available() &&
                        (ctx.audio.beatConfidence() >= kTempoConfMin);
    if (locked) {
        const bool tick = ctx.audio.isOnBeat();
        if (tick) lastBeatMs = ctx.rawTotalTimeMs;
        return tick;
    }
    // Metronome fallback
    const uint32_t nowMs = ctx.rawTotalTimeMs;
    const float intervalMs = 60000.0f / kFallbackBpm;
    if (lastBeatMs == 0 ||
        static_cast<float>(nowMs - lastBeatMs) >= intervalMs) {
        lastBeatMs = nowMs;
        return true;
    }
    return false;
}

/**
 * @brief Derive a musical hue (0-255 uint8 domain) from chord root or chroma centroid.
 *
 * K1 port of v3 selectMusicalHue().  The Schmitt-trigger hysteresis gate is
 * identical; the chroma access switches from ctx.audio.chroma()[i] pointer to
 * ctx.audio.getChroma(i) per-index (C-origin label → A-origin index bridge is
 * inside K1AudioContext::getChroma(), transparent to the caller).
 *
 * @param ctx          Render context.
 * @param[in,out] gateOpen  Persistent Schmitt-trigger state.
 * @return  Hue as a uint8 [0,255] value in the float domain.
 */
static uint8_t selectMusicalHue(const EffectContext& ctx, bool& gateOpen) {
    if (!ctx.audio.available()) return 24u;

    // Schmitt trigger: enter chord-root mode at confidence >= 0.40, exit <= 0.25.
    const float conf = ctx.audio.chordConfidence();
    if (conf >= 0.40f) gateOpen = true;
    else if (conf <= 0.25f) gateOpen = false;

    if (gateOpen) {
        // Chord root: A-origin index from K1AudioContext, converted to C-origin label
        // inside rootNote() — returned value is already in [0,11] C-origin.
        return kNoteHues[ctx.audio.rootNote() % 12u];
    }

    // Chroma circular centroid (C-origin): mirrors v3 dominantNoteFromChroma().
    // K1 uses getChroma(cOriginLabel) which handles the +3 mod-12 bridge internally.
    float cx = 0.0f, sy = 0.0f;
    for (uint8_t i = 0u; i < 12u; ++i) {
        // Pre-compute cos/sin for pitch-class angle (30° steps, i=0 → C).
        const float angle = static_cast<float>(i) * (kTau / 12.0f);
        const float score = ctx.audio.getChroma(i);
        cx += score * cosf(angle);
        sy += score * sinf(angle);
    }
    float a = atan2f(sy, cx);
    if (a < 0.0f) a += kTau;
    // Map angle back to nearest note index [0,11].
    const uint8_t note = static_cast<uint8_t>(roundf(a * (12.0f / kTau))) % 12u;
    return kNoteHues[note];
}

/**
 * @brief Short-arc-aware hue smoothing (wraps correctly around the uint8 wheel).
 *
 * Verbatim logic from v3 smoothHue(), operating in the [0,255] domain.
 */
static float smoothHue(float current, float target, float dt, float tauS) {
    float delta = target - current;
    // Shortest-arc wrap in [−128, +128].
    while (delta > 128.0f) delta -= 256.0f;
    while (delta < -128.0f) delta += 256.0f;
    float next = current + delta * expAlpha(dt, tauS);
    // Wrap result to [0, 255).
    next = fmodf(next, 256.0f);
    if (next < 0.0f) next += 256.0f;
    return next;
}

// ─── IEffect implementation ───────────────────────────────────────────────────

bool LgpFluxRift::init(EffectContext& ctx) {
    (void)ctx;
    m_phase         = 0.0f;
    m_fluxEnv       = 0.0f;
    m_beatPulse     = 0.0f;
    m_hue           = 24.0f;
    m_audioPresence = 0.0f;
    m_lastBeatMs    = 0u;
    m_chordGateOpen = false;
    return true;
}

void LgpFluxRift::render(EffectContext& ctx) {
    // ── Timing ───────────────────────────────────────────────────────────────
    // signalDt: raw (unscaled by SPEED) — for all audio-coupled EMA maths.
    // visualDt: speed-scaled — for phase accumulator (transport speed).
    const float dtSignal = ctx.getSafeRawDeltaSeconds();
    const float dtVisual = ctx.getSafeDeltaSeconds();

    // ── Audio-presence envelope ───────────────────────────────────────────────
    const bool audioAvail = ctx.audio.available();
    m_audioPresence = trackAudioPresence(m_audioPresence, audioAvail, dtSignal);

    // ── Silent / no-audio: fade to black and bail ─────────────────────────────
    if (m_audioPresence <= 0.001f) {
        K1StripView& pri = ctx.k1Buffer.primary();
        K1StripView& sec = ctx.k1Buffer.secondary();
        for (uint16_t i = 0u; i < ctx.stripLength; ++i) {
            pri.set16(i, CRGB16{SQ15x16(0), SQ15x16(0), SQ15x16(0)});
            sec.set16(i, CRGB16{SQ15x16(0), SQ15x16(0), SQ15x16(0)});
        }
        return;
    }

    const float master = (ctx.brightness / 255.0f) * m_audioPresence;

    // ── Flux envelope (tau=0.10s, verbatim from v3) ───────────────────────────
    // fastFlux → flux() proxy (K1AudioContext novelty surface; see port delta #2).
    // overallSaliency → rms() proxy.
    const float fluxTarget = audioAvail
        ? clamp01(0.70f * ctx.audio.flux() + 0.30f * ctx.audio.rms())
        : fallbackSine(ctx.rawTotalTimeMs, 0.0013f, 0.7f);
    m_fluxEnv = smoothTo(m_fluxEnv, fluxTarget, dtSignal, 0.10f);

    // ── Beat tick → shock injection (tau=0.25s, verbatim from v3) ────────────
    // Strobe Law: m_beatPulse modulates the SPATIAL Gaussian shock envelope,
    // never a global brightness multiplier.
    const bool beatTick = computeBeatTick(ctx, m_lastBeatMs);
    if (beatTick) {
        m_beatPulse = 1.0f;
    } else {
        m_beatPulse = decayBy(m_beatPulse, dtSignal, 0.25f);
    }

    // ── Phase accumulator (verbatim from v3, using real dt not /120.0f) ───────
    m_phase += 0.85f * (0.55f + 1.20f * m_fluxEnv) * dtVisual;
    if (m_phase > 100000.0f) m_phase = fmodf(m_phase, kTau);

    // ── Seam position [0,1]: at centre (0) on beat, at edge (1) when silent ──
    // (verbatim from v3: seamPos = 1 - beatPulse)
    const float seamPos = clamp01(1.0f - m_beatPulse);

    // ── Musical hue ───────────────────────────────────────────────────────────
    const float hueTarget = static_cast<float>(selectMusicalHue(ctx, m_chordGateOpen));
    m_hue = smoothHue(m_hue, hueTarget, dtSignal, 0.45f);
    const uint8_t baseHue = static_cast<uint8_t>(m_hue);

    // ── Per-frame trail fade (mirrors v3 fadeToBlackByDt with scale=30) ───────
    // nscale8(kFadeScale) per pixel per strip — persistence without a heap buffer.
    // Strobe Law: this is a persistence fade, not a beat-triggered flash.
    K1StripView& pri = ctx.k1Buffer.primary();
    K1StripView& sec = ctx.k1Buffer.secondary();
    for (uint16_t i = 0u; i < ctx.stripLength; ++i) {
        {
            CRGB c = pri.get(i);
            c.nscale8(kFadeScale);
            pri.set(i, c);
        }
        {
            CRGB c = sec.get(i);
            c.nscale8(kFadeScale);
            sec.set(i, c);
        }
    }

    // ── Centre-origin render loop (verbatim math from v3 :211-222) ───────────
    // dist=0 → centre pair (indices 79 / 80); dist=79 → edge pair (0 / 159).
    // K1 replacement for setCentrePairMono: write symmetric pair on each strip.
    for (uint16_t dist = 0u; dist < kHalfLength; ++dist) {
        const float d = static_cast<float>(dist) / static_cast<float>(kHalfLength);

        // Tanh-compressed phase-dislocation seam field (verbatim from v3).
        const float seam      = tanhf((d - seamPos) * (8.0f + 16.0f * m_fluxEnv));
        const float carrierA  = sinf(static_cast<float>(dist) * 0.22f - m_phase * 3.5f);
        const float carrierB  = sinf(static_cast<float>(dist) * 0.09f + m_phase * 5.1f);
        const float disloc    = 0.5f + 0.5f * tanhf(-1.35f * seam + 0.65f * carrierA + 0.35f * carrierB);

        // Gaussian shock term: spatial, centred on the seam boundary.
        // Strobe Law: expf(-|d - seamPos| * 16) is spatially localised,
        // not a full-field amplitude change.
        const float shock     = expf(-fabsf(d - seamPos) * 16.0f) * m_beatPulse;

        const float intensity = clamp01(disloc * (0.35f + 0.65f * m_fluxEnv) + 0.9f * shock);

        // Palette colour: hue index travels slightly with distance and flux.
        const uint8_t br   = toBrightness(intensity, master);
        const uint8_t idxA = static_cast<uint8_t>(
            baseHue
            + static_cast<uint8_t>(d * 48.0f)
            + static_cast<uint8_t>(m_fluxEnv * 22.0f));
        const CRGB colour = (ctx.palette != nullptr)
            ? ColorFromPalette(*ctx.palette, idxA, br, LINEARBLEND)
            : CHSV(idxA, 220u, br);

        // Symmetric write on each strip.
        // left  = kCentreLeft - dist  (79, 78, … 0)
        // right = kCentreLeft + 1 + dist  (80, 81, … 159)
        const uint16_t left  = kCentreLeft - dist;
        const uint16_t right = kCentreLeft + 1u + dist;

        // Primary strip (bottom edge).
        pri.add(left,  colour);
        pri.add(right, colour);

        // Secondary strip (top edge) — independent channel, same rift render.
        sec.add(left,  colour);
        sec.add(right, colour);
    }
}

void LgpFluxRift::cleanup() {}

const EffectMetadata& LgpFluxRift::getMetadata() const {
    static const EffectMetadata meta{
        "LGP Flux Rift",
        "Spectral-flux dislocation seam with beat shock; ported from v3 EID 152",
        EffectCategory::PARTY,
        1,
        "k1"
    };
    return meta;
}

// ─── Static singleton ─────────────────────────────────────────────────────────

IEffect* lgp_flux_rift_effect() {
    static LgpFluxRift instance;
    return &instance;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
