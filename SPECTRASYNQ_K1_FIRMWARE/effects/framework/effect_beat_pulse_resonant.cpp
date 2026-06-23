/**
 * @file effect_beat_pulse_resonant.cpp
 * @brief Beat Pulse (Resonant) — K1 port of firmware-v3 EID 0x1404.
 *
 * VISUAL IDENTITY (preserved from v3):
 *   You see the ANATOMY of a hit.  Two distinct rings: a thin, bright,
 *   near-white ATTACK snap leads; a wide, warm, saturated-colour BODY thud
 *   follows.  Both contract inward from the strip edges toward the centre on
 *   every beat.  Both are visible simultaneously via additive blending.
 *
 * K1 GEOMETRY ADAPTATION:
 *   K1 is two independent 160-LED strips (primary + secondary).  Each strip is
 *   centre-origin: index 79 is the left-of-pair centre, index 80 is the
 *   right-of-pair centre.  The render loop iterates `dist` from 0 (edge) to
 *   stripCentre (79, centre-adjacent) and writes symmetrically:
 *     left  pixel = stripCentre - dist  (indices 79 downto 0)
 *     right pixel = stripCentre + 1 + dist  (indices 80 upto 159)
 *   Both primary and secondary strips receive the same ring render (unified
 *   dual-channel look on the diffused LGP plate).
 *
 * STROBE LAW COMPLIANCE:
 *   The beat trigger sets m_beatIntensity = 1.0 and records a timestamp.
 *   Per-frame, per-ring envelopes (exp decay) scale per-pixel Gaussian/hard-
 *   edge kernels that are spatially localised to the ring's current position.
 *   No frame-wide brightness call.  Global brightness appears only as a uint8
 *   multiplier inside per-pixel colour construction, NOT as a uniform flash.
 *
 * PORT CHANGES vs v3:
 *   1. SET_CENTER_PAIR macro → explicit per-strip symmetric index writes via
 *      K1StripView::set() with additive blending (K1StripView::add()).
 *   2. ctx.rawTotalTimeMs → ctx.rawTotalTimeMs (identical field name, direct).
 *   3. ctx.audio.available (bool field) → ctx.audio.available() (method).
 *   4. ctx.audio.beatStrength() → ctx.audio.onsetStrength() (proxy; see .h).
 *   5. ctx.audio.tempoConfidence() → ctx.audio.beatConfidence() (direct).
 *   6. ctx.palette.getColor(idx, brightness) → ColorFromPalette(*ctx.palette, idx, u8).
 *   7. BeatPulseRenderUtils RingProfile::gaussian / hardEdge inlined here
 *      (avoid v3 header dependency; functions are trivial one-liners).
 *   8. v3 HALF_LENGTH (80) corrected to K1 stripCentre (79) — K1 centre pair
 *      is at 79/80, so the half-span in the direction of travel is 80 pixels
 *      (indices 0..79 inclusive).  dist01 normalised over 80.0f.
 *
 * All original timing constants preserved from v3.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "effect_beat_pulse_resonant.h"

#include <cmath>
#include <FastLED.h>

namespace k1 {
namespace effects {
namespace framework {

// ─── Ring timing and shape constants (verbatim from v3) ──────────────────────

// Attack ring: percussive snap (thin, hard-edged, near-white, fast)
static constexpr float kAttackTravelMs  = 280.0f;  ///< Edge-to-centre travel time
static constexpr float kAttackDecayMs   = 150.0f;  ///< Exponential decay time constant
static constexpr float kAttackWidth     = 0.06f;   ///< Hard-edge half-width (normalised)
static constexpr float kAttackSoftness  = 0.012f;  ///< Anti-alias softness on hard edge
static constexpr float kAttackWhite     = 0.85f;   ///< Desaturation toward white [0=colour,1=white]

// Body ring: resonant thud (wide, Gaussian, saturated, slower)
static constexpr float kBodyTravelMs    = 480.0f;  ///< Edge-to-centre travel time
static constexpr float kBodyDecayMs     = 380.0f;  ///< Exponential decay time constant
static constexpr float kBodySigma       = 0.14f;   ///< Gaussian sigma (wide soft ring)

// Fallback tempo gate (mirrors v3 BeatPulseTiming::kTempoConfMin)
static constexpr float kTempoConfMin    = 0.25f;

// Per-strip half-span: 80 pixels from edge (index 0) to centre-adjacent (index 79).
// normalisation denominator for dist01
static constexpr float kHalfSpan        = 80.0f;

// ─── Inline ring profile functions (replaces BeatPulseRenderUtils dependency) ─

/// Gaussian ring profile: exp(-0.5 * (d/sigma)^2).  Returns [0, 1].
static inline float ringGaussian(float d, float sigma) {
    const float r = d / sigma;
    return expf(-0.5f * r * r);
}

/// Hard-edge ring profile with AA softness.  Returns [0, 1].
static inline float ringHardEdge(float d, float halfWidth, float softness) {
    if (d <= halfWidth) return 1.0f;
    const float over = d - halfWidth;
    return (over < softness) ? (1.0f - over / softness) : 0.0f;
}

/// Float [0,1] → uint8 brightness, clamped.
static inline uint8_t toU8(float v) {
    if (v <= 0.0f) return 0;
    if (v >= 1.0f) return 255;
    return static_cast<uint8_t>(v * 255.0f + 0.5f);
}

/// Saturating uint8 add.
static inline uint8_t addSat8(uint8_t a, uint8_t b) {
    const uint16_t s = static_cast<uint16_t>(a) + b;
    return (s > 255u) ? 255u : static_cast<uint8_t>(s);
}

// ─── Beat-tick helper (mirrors v3 BeatPulseTiming::computeBeatTick) ──────────

static bool computeBeatTick(const EffectContext& ctx,
                             float fallbackBpm,
                             uint32_t& lastBeatMs) {
    const bool beatLocked = ctx.audio.available() &&
                            (ctx.audio.beatConfidence() >= kTempoConfMin);
    if (beatLocked) {
        const bool tick = ctx.audio.isOnBeat();
        if (tick) lastBeatMs = ctx.rawTotalTimeMs;
        return tick;
    }
    // Fallback metronome
    const uint32_t nowMs = ctx.rawTotalTimeMs;
    const float intervalMs = 60000.0f / (fallbackBpm > 30.0f ? fallbackBpm : 30.0f);
    if (lastBeatMs == 0 ||
        static_cast<float>(nowMs - lastBeatMs) >= intervalMs) {
        lastBeatMs = nowMs;
        return true;
    }
    return false;
}

// ─── IEffect implementation ───────────────────────────────────────────────────

bool BeatPulseResonant::init(EffectContext& ctx) {
    (void)ctx;
    m_beatIntensity  = 0.0f;
    m_lastBeatTimeMs = 0;
    m_fallbackBpm    = 128.0f;
    return true;
}

void BeatPulseResonant::render(EffectContext& ctx) {
    // ── Beat source ──────────────────────────────────────────────────────────
    const bool beatTick = computeBeatTick(ctx, m_fallbackBpm, m_lastBeatTimeMs);
    const uint32_t nowMs = ctx.rawTotalTimeMs;

    if (beatTick) {
        m_beatIntensity = 1.0f;
        // Scale fallback BPM toward current tempo when locked.
        if (ctx.audio.available() && ctx.audio.beatConfidence() >= kTempoConfMin) {
            // beatPhase is not BPM, but onsetStrength scales visual weight.
            // Fallback BPM unchanged — it only fires when unlocked.
        }
    }

    // ── Age since last beat ──────────────────────────────────────────────────
    const float ageMs = (m_lastBeatTimeMs != 0)
                        ? static_cast<float>(nowMs - m_lastBeatTimeMs)
                        : 999999.0f;

    // ── Per-ring envelope (exponential resonant decay) ───────────────────────
    const float attackEnv = expf(-ageMs / kAttackDecayMs) * m_beatIntensity;
    const float bodyEnv   = expf(-ageMs / kBodyDecayMs)   * m_beatIntensity;

    // ── Ring positions: start at edge (1.0), contract toward centre (0.0) ───
    // clamp so rings stop at centre and do not wrap.
    const float attackPos = 1.0f - fminf(ageMs / kAttackTravelMs, 1.0f);
    const float bodyPos   = 1.0f - fminf(ageMs / kBodyTravelMs,   1.0f);

    // ── Body colour palette index (travels with the ring) ───────────────────
    // bodyPos in [0,1]: 1.0 = edge (index 0), 0.0 = centre (index 255).
    const uint8_t bodyPaletteIdx = toU8(1.0f - bodyPos);

    // ── Early-out when both rings are fully decayed ──────────────────────────
    if (attackEnv < 0.001f && bodyEnv < 0.001f) {
        // Clear both strips so no stale pixels persist.
        K1StripView& pri = ctx.k1Buffer.primary();
        K1StripView& sec = ctx.k1Buffer.secondary();
        for (uint16_t i = 0; i < ctx.stripLength; ++i) {
            pri.set16(i, CRGB16{0, 0, 0});
            sec.set16(i, CRGB16{0, 0, 0});
        }
        return;
    }

    // ── Per-pixel render ─────────────────────────────────────────────────────
    // dist = 0 at the edge (index 0 / 159), dist = 79 at the centre-adjacent pixel.
    // dist01 = normalised distance from edge toward centre.
    //
    // Centre-origin write:
    //   left  = stripCentre - dist       (79, 78, … 0)
    //   right = stripCentre + 1 + dist   (80, 81, … 159)
    //
    // Using K1StripView::add() for additive blending (both rings accumulate).
    // Strips must be pre-cleared by the framework before render() is called
    // (consistent with v3 behaviour — v3 never calls fadeToBlackBy here).

    K1StripView& pri = ctx.k1Buffer.primary();
    K1StripView& sec = ctx.k1Buffer.secondary();

    const uint16_t centre = ctx.stripCentre;  // 79

    for (uint16_t dist = 0; dist < ctx.stripLength / 2; ++dist) {
        const float dist01 = (static_cast<float>(dist) + 0.5f) / kHalfSpan;

        // ── Attack ring: hard-edge, near-white, fast ─────────────────────────
        const float attackDiff = fabsf(dist01 - attackPos);
        const float attackHit  = ringHardEdge(attackDiff, kAttackWidth, kAttackSoftness)
                                  * attackEnv;

        // ── Body ring: Gaussian, saturated palette colour, slower ─────────────
        const float bodyDiff = fabsf(dist01 - bodyPos);
        const float bodyHit  = ringGaussian(bodyDiff, kBodySigma) * bodyEnv;

        // ── Body colour: palette at body ring position ────────────────────────
        CRGB bodyColour = CRGB::Black;
        if (ctx.palette && bodyHit > 0.001f) {
            bodyColour = ColorFromPalette(*ctx.palette,
                                          bodyPaletteIdx,
                                          toU8(bodyHit),
                                          LINEARBLEND);
        }

        // ── Attack colour: near-white desaturated flash ───────────────────────
        const uint8_t attackBri = toU8(attackHit * kAttackWhite);
        const CRGB attackColour{attackBri, attackBri, attackBri};

        // ── Additive blend: body + attack ─────────────────────────────────────
        CRGB c;
        c.r = addSat8(bodyColour.r, attackColour.r);
        c.g = addSat8(bodyColour.g, attackColour.g);
        c.b = addSat8(bodyColour.b, attackColour.b);

        // ── Write symmetric pair (CRGB → CRGB16 via K1StripView::set) ────────
        const uint16_t leftIdx  = (dist <= centre) ? (centre - dist)           : 0;
        const uint16_t rightIdx = (centre + 1 + dist < ctx.stripLength)
                                  ? (centre + 1 + dist) : (ctx.stripLength - 1);

        pri.set(leftIdx,  c);
        pri.set(rightIdx, c);
        sec.set(leftIdx,  c);
        sec.set(rightIdx, c);
    }
}

void BeatPulseResonant::cleanup() {
    m_beatIntensity  = 0.0f;
    m_lastBeatTimeMs = 0;
}

const EffectMetadata& BeatPulseResonant::getMetadata() const {
    static const EffectMetadata meta{
        "Beat Pulse (Resonant)",
        "Dual-ring anatomy: white attack snap contracts inward over warm resonant body thud",
        EffectCategory::PARTY,
        1,
        "LightwaveOS/K1-port"
    };
    return meta;
}

// ─── Static singleton accessor ───────────────────────────────────────────────

IEffect* beat_pulse_resonant_effect() {
    static BeatPulseResonant instance;
    return &instance;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
