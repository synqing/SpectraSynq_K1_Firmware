/**
 * @file effect_lgp_beat_prism.cpp
 * @brief LGP Beat Prism — onset-driven prism-texture implementation.
 *
 * Ported from firmware-v3
 * `src/effects/ieffect/LGPBeatPrismOnsetEffect.cpp`
 * (EID_LGP_BEAT_PRISM_ONSET = 0x1E00).
 *
 * See effect_lgp_beat_prism.h for full proxy map, geometry notes, and
 * Strobe Law audit.
 *
 * Compiled only under K1_EFFECT_FRAMEWORK_V1.
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "effect_lgp_beat_prism.h"

#include <cmath>
#include <cstdint>

#include <FastLED.h>

#include "EffectContext.h"
#include "K1AudioContext.h"
#include "K1BufferView.h"

namespace k1 {
namespace effects {
namespace framework {

// ─── file-scope constants ────────────────────────────────────────────────────

namespace {

static constexpr float kPi  = 3.14159265358979323846f;
static constexpr float kTau = 6.28318530717958647692f;

/// LEDs per physical strip.
static constexpr uint16_t kStripLen   = 160;
/// Half-strip length (render loop iterates 0..kHalf-1).
static constexpr uint16_t kHalf       = 80;
/// Left-of-centre index within each strip.
static constexpr uint16_t kCentreLeft  = 79;
/// Right-of-centre index within each strip.
static constexpr uint16_t kCentreRight = 80;

/// Palette hue offset per pitch class (C-origin, 0=C..11=B).
/// Maps the 12 chromatic pitch classes to evenly-spaced palette indices.
static constexpr uint8_t kNoteHues[12] = {
    0, 12, 24, 40, 56, 74, 92, 112, 134, 154, 178, 202
};

// ─── local maths helpers ────────────────────────────────────────────────────

static inline float clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

/// First-order EMA towards `target` with time constant `tauS` (seconds).
static inline float smoothTo(float current, float target, float dt, float tauS) {
    const float alpha = 1.0f - expf(-dt / fmaxf(tauS, 0.001f));
    return current + (target - current) * alpha;
}

/// Exponential decay with time constant `tauS` (seconds).
static inline float decay(float value, float dt, float tauS) {
    return value * expf(-dt / fmaxf(tauS, 0.001f));
}

/// Convert a normalised intensity and master scalar to a FastLED brightness byte.
static inline uint8_t toBrightness(float intensity, float master) {
    return static_cast<uint8_t>(255.0f * clamp01(intensity) * clamp01(master));
}

/// Rise/fall EMA that tracks audio presence (1.0 when audio available, else 0.0).
static inline float trackAudioPresence(float current, bool audioAvailable, float dt) {
    const float tau = audioAvailable ? 0.06f : 0.32f;
    return smoothTo(current, audioAvailable ? 1.0f : 0.0f, dt, tau);
}

/// Fallback sinusoidal oscillator for silent / no-audio frames.
static inline float fallbackSine(uint32_t rawMs, float rate, float phaseOffset = 0.0f) {
    return 0.5f + 0.5f * sinf(static_cast<float>(rawMs) * rate + phaseOffset);
}

/// Shortest-path hue smoothing (wraps at 256).
static inline float smoothHue(float current, float target, float dt, float tauS) {
    float diff = target - current;
    if (diff >  128.0f) diff -= 256.0f;
    if (diff < -128.0f) diff += 256.0f;
    const float alpha = 1.0f - expf(-dt / fmaxf(tauS, 0.001f));
    return current + diff * alpha;
}

/// Circular-centroid dominant note from 12-bin C-origin chroma array.
/// Returns a C-origin pitch-class index 0..11.
static inline uint8_t dominantNoteFromChroma(const K1AudioContext& audio) {
    float cx = 0.0f, sy = 0.0f;
    for (uint8_t i = 0; i < 12; ++i) {
        // Uniform angular spacing around the chroma wheel.
        const float angle = static_cast<float>(i) * (kTau / 12.0f);
        const float w = audio.getChroma(i);  // C-origin label → A-origin index via getChroma()
        cx += w * cosf(angle);
        sy += w * sinf(angle);
    }
    float a = atan2f(sy, cx);
    if (a < 0.0f) a += kTau;
    return static_cast<uint8_t>(static_cast<int>(a * (12.0f / kTau) + 0.5f) % 12);
}

/// Chord-gated musical hue selector.
/// Returns a palette-index offset (0–255 range) reflecting the current pitch class.
/// Uses Schmitt-trigger hysteresis on chord confidence to avoid jitter.
///
/// Proxy note: v3 calls `ctx.audio.chordConfidence()` which is mapped directly
/// to K1AudioContext::chordConfidence() (SBChordState::confidence, SB_CHORD_V2).
/// When chord confidence is below the gate, falls back to circular chroma centroid.
static inline uint8_t selectMusicalHue(const K1AudioContext& audio, bool& chordGateOpen) {
    if (!audio.available()) return 24;  // warm amber fallback on silence
    const float conf = audio.chordConfidence();
    if (conf >= 0.40f) chordGateOpen = true;
    else if (conf <= 0.25f) chordGateOpen = false;
    const uint8_t note = chordGateOpen
        ? static_cast<uint8_t>(audio.rootNote() % 12)
        : dominantNoteFromChroma(audio);
    return kNoteHues[note];
}

// ─── per-strip render helper ─────────────────────────────────────────────────

/// Write the prism pattern for one distance step to both left and right LEDs
/// of one strip, mirroring across the centre pair.
///
/// K1 centre-origin geometry (per-strip, 160 LEDs):
///   left  = kCentreLeft  - dist  (79, 78, 77, … 0)
///   right = kCentreRight + dist  (80, 81, 82, … 159)
static inline void writeCentrePair(K1StripView& strip,
                                   uint16_t dist,
                                   const CRGB& colour) {
    // Underflow guard: dist ≤ kCentreLeft (79) so left index ≥ 0.
    if (dist <= kCentreLeft) {
        strip.set(kCentreLeft  - dist, colour);
    }
    const uint16_t right = kCentreRight + dist;
    if (right < kStripLen) {
        strip.set(right, colour);
    }
}

/// dt-scaled trail fade on one strip (replaces v3 PersistenceHelpers::fadeToBlackByDt).
/// Reference: fadeToBlackBy() at 30/255 per frame @ 100 FPS ≈ 11.8 %/frame.
/// dt-scaled version: amount = 30 * dt / (1.0/100.0) = 30 * dt * 100, clamped [0,255].
static inline void fadeStripByDt(K1StripView& strip, float dt) {
    constexpr float kRefRate = 100.0f;
    const uint8_t amount = static_cast<uint8_t>(
        fminf(255.0f, 30.0f * dt * kRefRate));
    if (amount == 0) return;
    for (uint16_t i = 0; i < kStripLen; ++i) {
        CRGB c = strip.get(i);
        c.fadeToBlackBy(amount);
        strip.set(i, c);
    }
}

}  // anonymous namespace

// ─── IEffect lifecycle ───────────────────────────────────────────────────────

bool LgpBeatPrism::init(EffectContext& ctx) {
    (void)ctx;
    m_phase         = 0.0f;
    m_prism         = 0.0f;
    m_kickPulse     = 0.0f;
    m_snareBurst    = 0.0f;
    m_hihatShimmer  = 0.0f;
    m_hue           = 24.0f;
    m_audioPresence = 0.0f;
    m_chordGateOpen = false;
    return true;
}

void LgpBeatPrism::render(EffectContext& ctx) {
    // ── dt split ──────────────────────────────────────────────────────────────
    // v3 AudioReactivePolicy::signalDt → raw dt (audio-phase timing, unscaled).
    // v3 AudioReactivePolicy::visualDt → speed-scaled dt (visual phase advance).
    const float dtSignal = ctx.getSafeRawDeltaSeconds();
    const float dtVisual = ctx.getSafeDeltaSeconds();

    // ── Audio-presence envelope ───────────────────────────────────────────────
    m_audioPresence = trackAudioPresence(m_audioPresence, ctx.audio.available(), dtSignal);
    if (m_audioPresence <= 0.001f) {
        // Silent / no audio: fade both strips and return.
        if (ctx.k1Buffer.available()) {
            fadeStripByDt(ctx.k1Buffer.primary(),   dtSignal);
            fadeStripByDt(ctx.k1Buffer.secondary(), dtSignal);
        }
        return;
    }

    // ── Master brightness ──────────────────────────────────────────────────────
    // v3 `ctx.audio.audioConfidence()` → K1AudioContext::beatConfidence()
    // (proxy: beatConfidence() is the PLL-lock quality scalar; no composite
    // audioConfidence() exists on K1. Semantically equivalent — drives down
    // master when lock is poor / audio is uncertain.)
    const float confidence = ctx.audio.beatConfidence();
    const float master = (static_cast<float>(ctx.brightness) / 255.0f)
                         * m_audioPresence
                         * confidence;

    // ── Percussion onset channels ─────────────────────────────────────────────
    // Kick → beat-front radial pulse (primary visual event).
    if (ctx.audio.isKickHit()) {
        m_kickPulse = 1.0f;
    }
    m_kickPulse = decay(m_kickPulse, dtSignal, 0.24f);

    // Snare → prism refraction accent.
    if (ctx.audio.isSnareHit()) {
        m_snareBurst = 1.0f;
    }
    m_snareBurst = decay(m_snareBurst, dtSignal, 0.15f);

    // Hihat → spoke shimmer overlay (surface detail only).
    if (ctx.audio.isHihatHit()) {
        m_hihatShimmer = 1.0f;
    }
    m_hihatShimmer = decay(m_hihatShimmer, dtSignal, 0.08f);

    // ── Prism intensity (continuous treble driver + onset accents) ────────────
    // v3 `ctx.audio.bands()[5..7]` → K1AudioContext::getBand(5..7)
    // (80-bin → 8-band fold; bands 5-7 cover the hi-mid and treble range)
    const bool audioAvail = ctx.audio.available();
    const float treble = audioAvail
        ? (ctx.audio.getBand(5) + ctx.audio.getBand(6) + ctx.audio.getBand(7)) * (1.0f / 3.0f)
        : 0.0f;
    const float prismTarget = audioAvail
        ? clamp01(0.28f * treble + 0.32f * m_snareBurst + 0.10f * m_hihatShimmer)
        : fallbackSine(ctx.rawTotalTimeMs, 0.0011f, 1.0f);
    m_prism = smoothTo(m_prism, prismTarget, dtSignal, 0.12f);

    // ── Phase advance ─────────────────────────────────────────────────────────
    // Speed-scaled dt (dtVisual) so the visual rate is user-controllable.
    // No /120.0f hard-coded fps factor — uses real K1 dt.
    m_phase += 0.90f * (0.55f + 0.75f * m_prism) * dtVisual;
    m_phase = fmodf(m_phase, kTau);

    // ── Beat-front position ───────────────────────────────────────────────────
    // STROBE LAW: kick drives SPATIAL ring position, not global brightness.
    // frontPos = 1.0 when kick just fired (front at edge),
    //          → 0.0 as pulse decays (front travels toward centre).
    const float frontPos = clamp01(1.0f - m_kickPulse);

    // ── Hue from chord detection ──────────────────────────────────────────────
    // chordConfidence() / rootNote() / getChroma() all map directly from K1AudioContext.
    const float hueTarget = static_cast<float>(
        static_cast<uint8_t>(selectMusicalHue(ctx.audio, m_chordGateOpen) + 8));
    m_hue = smoothHue(m_hue, hueTarget, dtSignal, 0.45f);
    const uint8_t baseHue = static_cast<uint8_t>(m_hue);

    // ── Trail fade (persistence) ──────────────────────────────────────────────
    // Replaced v3 fadeToBlackByDt on the unified ctx.leds; write to K1 dual strips.
    if (!ctx.k1Buffer.available()) return;
    fadeStripByDt(ctx.k1Buffer.primary(),   dtSignal);
    fadeStripByDt(ctx.k1Buffer.secondary(), dtSignal);

    // ── Per-pixel render loop ─────────────────────────────────────────────────
    // Iterates by radial distance from centre (dist=0 → centre pair, dist=79 → edge).
    // All geometry is SPATIAL; no global brightness set on beat.
    for (uint16_t dist = 0; dist < kHalf; ++dist) {
        const float d = static_cast<float>(dist) / static_cast<float>(kHalf);

        // Spoke field — radial sine waves driven by prism intensity.
        const float spokes = fabsf(sinf((d * (5.5f + 10.0f * m_prism) - m_phase * 0.7f) * kPi));

        // Facet layer — slower cosine ring that adds structural depth.
        const float facets = 0.5f + 0.5f * cosf((d * 3.5f + m_phase * 0.35f) * kTau);

        // Refraction layer — the prism texture; density and speed driven by m_prism.
        const float refract = 0.5f + 0.5f * sinf(
            d * (2.2f + 3.2f * m_prism) * kTau - m_phase * 1.10f);

        // Kick-front radial ring: SPATIAL — position `d` relative to frontPos.
        // STROBE LAW: beat drives ring position only, not full-field amplitude.
        const float front = expf(-fabsf(d - frontPos) * (7.5f + 4.5f * m_prism))
                            * m_kickPulse;

        // Hihat shimmer: fine high-frequency texture overlay.
        const float shimmer = m_hihatShimmer > 0.01f
            ? (0.5f + 0.5f * sinf(d * 34.0f + m_phase * 3.6f)) * m_hihatShimmer * 0.18f
            : 0.0f;

        // Combine layers.
        const float intensity = clamp01(
            (0.20f + 0.80f * spokes) * (0.25f + 0.75f * facets) *
            (0.20f + 0.80f * refract) + front * 1.10f + shimmer);

        const uint8_t br = toBrightness(intensity, master);

        // Palette index: base hue + spoke colour-striping + radial gradient + snare accent.
        const uint8_t paletteIdx = static_cast<uint8_t>(
            baseHue
            + static_cast<uint8_t>(spokes    * 26.0f)
            + static_cast<uint8_t>(d         * 28.0f)
            + static_cast<uint8_t>(m_snareBurst * 10.0f));

        // Colour from FastLED palette.
        // v3 `ctx.palette.getColor(idx, br)` → `ColorFromPalette(*ctx.palette, idx, br)`
        const CRGB colour = (ctx.palette != nullptr)
            ? ColorFromPalette(*ctx.palette, paletteIdx, br)
            : CRGB(br, br >> 1, br >> 2);  // warm amber fallback if no palette bound

        // Write mirror pair to both K1 strips (dual-channel doctrine).
        writeCentrePair(ctx.k1Buffer.primary(),   dist, colour);
        writeCentrePair(ctx.k1Buffer.secondary(), dist, colour);
    }
}

void LgpBeatPrism::cleanup() {
    // No heap to free; state reset on next init().
}

const EffectMetadata& LgpBeatPrism::getMetadata() const {
    static EffectMetadata meta{
        "LGP Beat Prism",
        "Onset-driven prism radiating from plate centre — kick front, snare refraction, hihat shimmer",
        EffectCategory::PARTY,
        1,
        nullptr,
        EffectRoleFlags::SELF_TRAILING  // bakes its own trail via fadeToBlackBy
    };
    return meta;
}

// ─── singleton accessor ──────────────────────────────────────────────────────

IEffect* lgp_beat_prism_effect() {
    static LgpBeatPrism g_lgp_beat_prism_instance;
    return &g_lgp_beat_prism_instance;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
