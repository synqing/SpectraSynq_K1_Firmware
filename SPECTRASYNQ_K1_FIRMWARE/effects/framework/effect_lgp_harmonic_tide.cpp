/**
 * @file effect_lgp_harmonic_tide.cpp
 * @brief K1 port of v3 EID 154 — LGP Harmonic Tide (P7 Batch-1).
 *
 * Port fidelity:
 *   v3 field              → K1 accessor            notes
 *   harmonicSaliency      → audio.chordConfidence() proxy (documented in P7 prep)
 *   heavyMid              → audio.mid()             exact fidelity
 *   chroma[i] C-origin    → audio.getChroma(i)      C-origin label; bridge verified P2
 *   rootNote C-origin     → audio.rootNote()        A-origin→C-origin +9 bridge in K1AudioContext
 *   isMajor/isMinor       → audio.isMajor/isMinor() exact
 *   AudioReactivePolicy::signalDt → ctx.getSafeDeltaSeconds()
 *   AudioReactivePolicy::visualDt → ctx.getSafeDeltaSeconds() (same dt on K1)
 *   fadeToBlackByDt       → manual per-element fade using getSafeDeltaSeconds()
 *   ctx.palette.getColor  → ColorFromPalette(*ctx.palette, hue, brightness)
 *   ctx.audio.available   → ctx.audio.available()
 *
 * Strobe Law: COMPLIANT. All visual modulation is spatial (wave position through
 * the plate). chordConfidence() is slow-moving; no beat-triggered brightness step.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. British English in comments.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "effect_lgp_harmonic_tide.h"

#include <cmath>
#include <FastLED.h>

namespace k1 {
namespace effects {
namespace framework {

// ─── File-scope constants (mirror v3 LGPExperimentalAudioPack anonymous ns) ──

namespace {

static constexpr float kPi  = 3.14159265358979323846f;
static constexpr float kTau = 6.28318530717958647692f;

/// Per-strip LED count (160). Matches K1_BUFFER_STRIP_LENGTH / NATIVE_RESOLUTION.
static constexpr uint16_t kStripLen   = 160u;
/// Half-strip extent — tide runs from centre outward over 80 LEDs per side.
static constexpr uint16_t kHalfLen    = 80u;
/// Unified-buffer centre (right-of-pair) — matches K1_CENTRE_POINT.
static constexpr uint16_t kCentreRight = 80u;
/// Left-of-pair centre index.
static constexpr uint16_t kCentreLeft  = 79u;

/// Note-to-hue mapping (C-origin, 30-degree steps, FastLED HSV wheel).
static constexpr uint8_t kNoteHues[12] = {
    0, 12, 24, 40, 56, 74, 92, 112, 134, 154, 178, 202
};

// ─── Inline maths helpers ─────────────────────────────────────────────────────

static inline float clamp01(float v) {
    return v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v);
}

/// EMA coefficient: 1 − exp(−dt / tauS). Returns 1 when tauS ≤ 0.
static inline float expAlpha(float dt, float tauS) {
    return (tauS <= 0.0f) ? 1.0f : (1.0f - expf(-dt / tauS));
}

/// Exponential smoothing toward target with time constant tauS (seconds).
static inline float smoothTo(float cur, float target, float dt, float tauS) {
    return cur + (target - cur) * expAlpha(dt, tauS);
}

/// Per-frame multiplicative decay with time constant tauS (seconds).
static inline float decay(float val, float dt, float tauS) {
    return (tauS <= 0.0f) ? 0.0f : (val * expf(-dt / tauS));
}

/// Circular (shortest-arc) smoothing for note index domain [0, 12).
static inline float smoothNoteCircular(float cur, float target, float dt, float tauS) {
    float delta = target - cur;
    // Wrap delta to shortest arc in [−6, +6).
    if (delta >  6.0f) delta -= 12.0f;
    if (delta < -6.0f) delta += 12.0f;
    float next = cur + delta * expAlpha(dt, tauS);
    // Wrap result to [0, 12).
    if (next < 0.0f)  next += 12.0f;
    if (next >= 12.0f) next -= 12.0f;
    return next;
}

/// Circular smoothing for hue in [0, 256) with shortest-arc.
static inline float smoothHue(float cur, float target, float dt, float tauS) {
    float delta = target - cur;
    if (delta >  128.0f) delta -= 256.0f;
    if (delta < -128.0f) delta += 256.0f;
    float next = cur + delta * expAlpha(dt, tauS);
    if (next < 0.0f)   next += 256.0f;
    if (next >= 256.0f) next -= 256.0f;
    return next;
}

/// Track audio presence: rises quickly when audio is available, decays otherwise.
static inline float trackAudioPresence(float prev, bool available, float dt) {
    const float target = available ? 1.0f : 0.0f;
    // Fast rise (100 ms), slow decay (400 ms).
    const float tau = available ? 0.10f : 0.40f;
    return smoothTo(prev, target, dt, tau);
}

/**
 * @brief Circular-weighted dominant note from the 12-bin chroma vector.
 *
 * K1 port: v3 used ctx.audio.chroma() (raw pointer) with cosine table from
 * ChromaUtils. K1AudioContext exposes getChroma(cOriginLabel) per-element.
 * We reimplement the same circular weighted-mean with per-element calls.
 * The return value is a C-origin note index [0, 11].
 */
static inline uint8_t dominantNoteFromChroma(const EffectContext& ctx) {
    if (!ctx.audio.available()) return 0u;
    // 30-degree (π/6) steps over 12 pitch classes (C-origin).
    float cx = 0.0f, sy = 0.0f;
    for (uint8_t i = 0u; i < 12u; ++i) {
        const float angle = static_cast<float>(i) * (kTau / 12.0f);
        const float w = ctx.audio.getChroma(i);  // C-origin label → correct bridge
        cx += w * cosf(angle);
        sy += w * sinf(angle);
    }
    float ang = atan2f(sy, cx);
    if (ang < 0.0f) ang += kTau;
    return static_cast<uint8_t>(static_cast<uint8_t>(roundf(ang * (12.0f / kTau))) % 12u);
}

/**
 * @brief Hue from chord root or dominant chroma note via Schmitt-trigger gate.
 *
 * Hysteresis prevents rapid hue flip: gate opens at chordConfidence ≥ 0.40,
 * closes at ≤ 0.25. When open, hue tracks the chord root; when closed it
 * follows the highest-energy chroma bin.
 */
static inline uint8_t selectMusicalHue(const EffectContext& ctx, bool& gateOpen) {
    if (!ctx.audio.available()) return 24u;
    const float conf = ctx.audio.chordConfidence();
    if (conf >= 0.40f) gateOpen = true;
    else if (conf <= 0.25f) gateOpen = false;
    const uint8_t note = gateOpen
        ? static_cast<uint8_t>(ctx.audio.rootNote() % 12u)
        : dominantNoteFromChroma(ctx);
    return kNoteHues[note];
}

/**
 * @brief Fallback sine oscillation used when no audio is available.
 *
 * Keeps the effect alive and pleasant during audio-unavailable init frames.
 */
static inline float fallbackSine(uint32_t rawMs, float rate, float phaseOffset = 0.0f) {
    return 0.5f + 0.5f * sinf(static_cast<float>(rawMs) * rate + phaseOffset);
}

/**
 * @brief Fade the unified CRGB buffer toward black (replaces v3 fadeToBlackByDt).
 *
 * v3 called fadeToBlackByDt(leds, count, 30, dt) which applies a per-frame
 * factor of powf(1 - 30/255, dt * 120). We reproduce the same dt-normalised
 * decay inline so the framework carries no PersistenceHelpers dependency.
 *
 * At 100 FPS (dt ≈ 0.010 s) this is nearly equivalent to FastLED's
 * fadeToBlackBy(leds, count, 3) per frame — a gentle trail that preserves
 * spatial wave structure without ghosting.
 */
static inline void fadeBufferByDt(CRGB* leds, uint16_t count, float dt) {
    // Survival fraction per second: (1 - 30/255)^120 ≈ 0.0005; per-frame:
    //   survival = powf(base, dt * 120)  where base = (225/255).
    const float survival = powf(225.0f / 255.0f, dt * 120.0f);
    const uint8_t keep = static_cast<uint8_t>(survival * 255.0f);
    for (uint16_t i = 0u; i < count; ++i) {
        leds[i].nscale8(keep);
    }
}

/**
 * @brief Write a mirrored pixel pair to both strips at distance dist from centre.
 *
 * K1 has two independent 160-LED strips in a contiguous CRGB scratch buffer
 * (ctx.leds = 320 LEDs: [0..159] = primary, [160..319] = secondary).
 * Centre-origin: primary centre-left = 79, centre-right = 80.
 * Both strips receive the same colour (mono tide; no secondary variation).
 */
static inline void writeCentrePairMono(CRGB* leds, uint16_t count,
                                       uint16_t dist, const CRGB& colour) {
    const uint16_t l1 = kCentreLeft  - dist;
    const uint16_t r1 = kCentreRight + dist;
    const uint16_t l2 = kStripLen + kCentreLeft  - dist;
    const uint16_t r2 = kStripLen + kCentreRight + dist;
    if (l1 < count) leds[l1] += colour;
    if (r1 < count) leds[r1] += colour;
    if (l2 < count) leds[l2] += colour;
    if (r2 < count) leds[r2] += colour;
}

}  // anonymous namespace

// ─── LgpHarmonicTide ─────────────────────────────────────────────────────────

bool LgpHarmonicTide::init(EffectContext& ctx) {
    (void)ctx;
    m_phase         = 0.0f;
    m_harmonic      = 0.0f;
    m_rootSmooth    = 0.0f;
    m_hue           = 24.0f;
    m_audioPresence = 0.0f;
    m_chordGateOpen = false;
    return true;
}

void LgpHarmonicTide::render(EffectContext& ctx) {
    if (ctx.leds == nullptr) return;

    // ── Timing ────────────────────────────────────────────────────────────────
    // K1 has a single measured dt; v3 split into signalDt (audio coupling) and
    // visualDt (phase advance). We use getSafeDeltaSeconds() for both — the
    // difference matters only when speed knob scales visual dt, which the K1
    // framework does not currently differentiate for ported effects.
    const float dt = ctx.getSafeDeltaSeconds();

    // ── Audio presence gate ───────────────────────────────────────────────────
    const bool audioOk = ctx.audio.available();
    m_audioPresence = trackAudioPresence(m_audioPresence, audioOk, dt);
    if (m_audioPresence <= 0.001f) {
        fadeBufferByDt(ctx.leds, ctx.ledCount, dt);
        return;
    }
    const float master = clamp01(ctx.brightness / 255.0f) * m_audioPresence;

    // ── Harmonic saliency (chordConfidence proxy) ─────────────────────────────
    // v3: fmaxf(harmonicSaliency, chordConfidence).
    // K1: both map to chordConfidence(); the proxy gap is documented in P7 prep.
    // When chord detection is weak the tide amplitude falls; more musically
    // correct than always-on — see P7-prep §4.5 proxy gap note.
    const float harmonicTarget = audioOk
        ? clamp01(ctx.audio.chordConfidence())
        : fallbackSine(ctx.rawTotalTimeMs, 0.0008f, 1.6f);
    m_harmonic = smoothTo(m_harmonic, harmonicTarget, dt, 0.20f);

    // ── Schmitt-trigger chord gate + root-note circular smoothing ─────────────
    if (audioOk) {
        const float conf = ctx.audio.chordConfidence();
        if (conf >= 0.40f) m_chordGateOpen = true;
        else if (conf <= 0.25f) m_chordGateOpen = false;
    }

    const float rootTarget = audioOk
        ? static_cast<float>(
              m_chordGateOpen
                  ? static_cast<uint8_t>(ctx.audio.rootNote() % 12u)
                  : dominantNoteFromChroma(ctx))
        : 2.0f;  // default to D (calm, neutral when no audio)
    m_rootSmooth = smoothNoteCircular(m_rootSmooth, rootTarget, dt, 0.30f);

    // ── Wave phase accumulator ────────────────────────────────────────────────
    // Speed scales with mid energy: higher mid → faster wave propagation.
    // v3: m_phase += 0.75 * (0.65 + 1.15 * mid) * dtVisual
    const float midEnergy = audioOk ? clamp01(ctx.audio.mid()) : 0.25f;
    m_phase += 0.75f * (0.65f + 1.15f * midEnergy) * dt;
    if (m_phase > 100000.0f) m_phase = fmodf(m_phase, kTau);

    // ── Chord triad hue derivation ────────────────────────────────────────────
    const uint8_t rootBin  = static_cast<uint8_t>(roundf(m_rootSmooth)) % 12u;
    const bool    isMinor  = audioOk && ctx.audio.isMinor();
    const uint8_t thirdBin = static_cast<uint8_t>((rootBin + (isMinor ? 3u : 4u)) % 12u);
    const uint8_t fifthBin = static_cast<uint8_t>((rootBin + 7u) % 12u);

    // Hue values: root / third / fifth spread across the FastLED HSV wheel.
    // binStep = 255 / 12 ≈ 21; gHue shifts the whole triad globally.
    static constexpr uint8_t kBinStep = static_cast<uint8_t>(255u / 12u);
    const uint8_t hueRoot  = static_cast<uint8_t>(ctx.gHue + rootBin  * kBinStep);
    const uint8_t hueThird = static_cast<uint8_t>(ctx.gHue + thirdBin * kBinStep);
    const uint8_t hueFifth = static_cast<uint8_t>(ctx.gHue + fifthBin * kBinStep);

    // ── Render: fade trail then write tidal wave field ────────────────────────
    // Trail fade: same per-frame survival as v3 fadeToBlackByDt(…, 30, dt).
    fadeBufferByDt(ctx.leds, ctx.ledCount, dt);

    for (uint16_t dist = 0u; dist < kHalfLen; ++dist) {
        // Normalised distance from centre [0, 1). d = 0 → centre, d → 1 → edge.
        const float d = static_cast<float>(dist) / static_cast<float>(kHalfLen);

        // Three-wave superposition (v3 render math, verbatim):
        //   outward:  0.5 + 0.5 * sin(dist * k_out  - phase * omega_out)
        //   inward:   0.5 + 0.5 * sin(dist * k_in   + phase * omega_in)
        //   standing: |sin(dist * k_stand + phase * omega_stand)|
        // All omega terms are already absorbed into m_phase accumulation above.
        const float outward  = 0.5f + 0.5f * sinf(
                                   static_cast<float>(dist) * 0.09f - m_phase * 3.8f);
        const float inward   = 0.5f + 0.5f * sinf(
                                   static_cast<float>(dist) * 0.07f + m_phase * 2.7f);
        const float standing = fabsf(sinf(
                                   static_cast<float>(dist) * 0.043f + m_phase * 1.1f));

        // Amplitude envelope: harmonic saliency × centre-pressure curve.
        // powf(1-d, 2) concentrates energy near the centre (continuous hold).
        const float envelope = (0.28f + 0.72f * m_harmonic) *
                               (0.30f + 0.70f * expf(-d * 2.0f));

        // Superposed intensity: Strobe Law — this is a SPATIAL wave value,
        // not a global brightness event. Amplitude never triggers a full-field flash.
        const float intensity = clamp01(
            (0.45f * outward + 0.35f * inward + 0.20f * standing) * envelope);

        // Per-pixel brightness: master × intensity.
        const float pixelF    = master * intensity;
        const uint8_t brightness = static_cast<uint8_t>(255.0f * pixelF);
        if (brightness == 0u) continue;

        // Palette index scrolls with phase, creating a colour drift along the wave.
        const uint8_t paletteIndex = static_cast<uint8_t>(
            static_cast<uint8_t>(m_phase * 30.0f) + dist * 2u);

        // Triad weight distribution (v3 verbatim):
        //   root  dominates near centre (high at d=0, falls off linearly)
        //   fifth dominates at edges (grows with d)
        //   third is a midband peak at d≈0.35, gated by harmonic saliency
        float wRoot  = clamp01(1.20f - 1.55f * d);
        float wFifth = clamp01(0.30f + 1.00f * d);
        float wThird = m_harmonic * clamp01(1.0f - fabsf(d - 0.35f) * 3.1f);
        const float wSum = wRoot + wThird + wFifth;
        if (wSum > 0.0001f) {
            wRoot  /= wSum;
            wThird /= wSum;
            wFifth /= wSum;
        }

        const uint8_t bRoot  = static_cast<uint8_t>(brightness * wRoot);
        const uint8_t bThird = static_cast<uint8_t>(brightness * wThird);
        const uint8_t bFifth = static_cast<uint8_t>(brightness * wFifth);

        // Build colour from triad components via FastLED palette lookup.
        // K1 uses raw CRGBPalette16 pointer; null-guard ctx.leds check above.
        CRGB pixel = CRGB::Black;
        if (bRoot && ctx.palette) {
            pixel += ColorFromPalette(*ctx.palette,
                                      static_cast<uint8_t>(hueRoot + paletteIndex),
                                      bRoot);
        }
        if (bThird && ctx.palette) {
            pixel += ColorFromPalette(*ctx.palette,
                                      static_cast<uint8_t>(hueThird + paletteIndex),
                                      bThird);
        }
        if (bFifth && ctx.palette) {
            pixel += ColorFromPalette(*ctx.palette,
                                      static_cast<uint8_t>(hueFifth + paletteIndex),
                                      bFifth);
        }

        writeCentrePairMono(ctx.leds, ctx.ledCount, dist, pixel);
    }
}

void LgpHarmonicTide::cleanup() {
    // No PSRAM / heap to release. State resets on next init().
}

const EffectMetadata& LgpHarmonicTide::getMetadata() const {
    static const EffectMetadata kMeta{
        "LGP Harmonic Tide",
        "Chord-anchored tidal wave field — quiet in atonal passages",
        EffectCategory::AMBIENT,
        1,
        "k1-port-p7",
        EffectRoleFlags::SELF_TRAILING
    };
    return kMeta;
}

// ─── Static instance accessor ─────────────────────────────────────────────────

IEffect* lgp_harmonic_tide_effect() {
    static LgpHarmonicTide s_instance;
    return &s_instance;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
