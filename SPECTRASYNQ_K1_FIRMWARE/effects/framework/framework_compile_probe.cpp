/**
 * @file framework_compile_probe.cpp
 * @brief Compile-only probe for the K1 effect-framework spine (P1).
 *
 * Forces compilation + linkage of every new framework header and the two
 * primitive translation units. It instantiates and uses each ported type enough
 * that the compiler must fully parse and codegen them. Nothing here runs on the
 * device's render path — it is a build-surface witness only.
 *
 * Guarded by K1_EFFECT_FRAMEWORK_V1: present ONLY in the `k1_effect_framework`
 * env. The shipping `k1_hardware` env neither defines the flag nor includes this
 * TU in its build_src_filter, so the production firmware is byte-unchanged.
 *
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include <FastLED.h>

#include "BlendMode.h"
#include "EffectContext.h"
#include "EffectId.h"
#include "EffectMetadata.h"
#include "EffectParameter.h"
#include "FrameBlend.h"
#include "IEffect.h"
#include "K1AudioContext.h"
#include "K1BufferView.h"
#include "RenderPrimitives.h"

// Pull in the K1 audio struct definitions so the probe can build real (silent)
// snapshot/onset frames and drive K1AudioContext through them — this is the TU
// that forces K1AudioContext + K1BufferView to genuinely codegen (nothing on the
// shipping render path includes them yet).
#include "sb_audio_snapshot.h"

namespace k1 {
namespace effects {
namespace framework {
namespace probe {

// ── Concrete IEffect to exercise the full virtual interface ──
class FrameworkProbeEffect final : public IEffect {
public:
    bool init(EffectContext& ctx) override {
        (void)ctx;
        return true;
    }

    void render(EffectContext& ctx) override {
        // Exercise the centre-origin geometry surface + timing helpers.
        const float dt = ctx.getSafeDeltaSeconds();
        const uint16_t mid = ctx.centrePoint;
        const float dist = ctx.getDistanceFromCentre(mid);
        const float sgn = ctx.getSignedPosition(0);
        const uint16_t mirrored = ctx.mirrorIndex(0);
        const float stripDist = ctx.getDistanceFromStripCentre(0);
        float rise = 0.0f, fall = 0.0f;
        ctx.getMoodSmoothing(rise, fall);

        // Exercise the render primitives against the unified buffer.
        if (ctx.leds != nullptr && ctx.palette != nullptr) {
            drawDot(ctx.leds, ctx.ledCount, ctx.centrePoint,
                    dist, CRGB::White, 1.0f, sgn >= 0.0f ? 0.0f : -1.0f,
                    /*mirror=*/true);

            float bins[4] = {0.10f, 0.40f, 0.70f, 1.00f};
            fillFromBins(ctx.leds, ctx.ledCount, ctx.centrePoint,
                         bins, 4, *ctx.palette, ctx.brightness,
                         /*additive=*/false);

            drawSpriteScrolled(ctx.leds, ctx.ledCount, ctx.centrePoint,
                               1.0f, 0.95f, dt);
        }

        // Touch the remaining locals so nothing is optimised to a parse-only no-op.
        m_witness = static_cast<uint32_t>(rise + fall + stripDist) +
                    mirrored + ctx.frameNumber;
    }

    void cleanup() override { m_witness = 0; }

    const EffectMetadata& getMetadata() const override {
        static const EffectMetadata meta{
            "Framework Probe",
            "P1 compile witness",
            EffectCategory::CUSTOM,
            1,
            "k1",
            EffectRoleFlags::SELF_TRAILING | EffectRoleFlags::DUAL_CHANNEL};
        return meta;
    }

    uint8_t getParameterCount() const override { return 1; }

    const EffectParameter* getParameter(uint8_t index) const override {
        static const EffectParameter p{
            "gain", "Gain", 0.0f, 2.0f, 1.0f,
            EffectParameterType::FLOAT, 0.01f, "wave", "x", false};
        return (index == 0) ? &p : nullptr;
    }

private:
    uint32_t m_witness = 0;
};

// ── Free-function witness: instantiate / use every spine type at least once. ──
// Returns a non-trivial value so the optimiser cannot discard the whole body.
uint32_t k1_framework_compile_probe() {
    uint32_t acc = 0;

    // EffectId + sentinel.
    EffectId id = INVALID_EFFECT_ID;
    acc += static_cast<uint32_t>(id);

    // EffectParameter (both constructors) + EffectParameterType.
    EffectParameter p5{"a", "A", 0.0f, 1.0f, 0.5f};
    EffectParameter p10{"b", "B", 0.0f, 2.0f, 1.0f,
                        EffectParameterType::INT, 1.0f, "g", "u", true};
    acc += static_cast<uint32_t>(p5.minValue + p10.maxValue);

    // EffectMetadata + EffectCategory + EffectRoleFlags helpers.
    EffectMetadata meta{"m", "d", EffectCategory::QUANTUM, 2, "k1",
                        EffectRoleFlags::BACKGROUND};
    acc += static_cast<uint32_t>(meta.version);
    acc += hasRoleFlag(meta.roleFlags, EffectRoleFlags::BACKGROUND) ? 1u : 0u;

    // BlendMode enum + blend functions + names.
    CRGB base{10, 20, 30};
    CRGB top{200, 100, 50};
    for (uint8_t m = 0; m < static_cast<uint8_t>(BlendMode::MODE_COUNT); ++m) {
        CRGB out = blendPixels(base, top, static_cast<BlendMode>(m));
        acc += out.r + out.g + out.b;
        acc += (getBlendModeName(m)[0] != '\0') ? 1u : 0u;
    }

    // EffectContext + helpers.
    EffectContext ctx;
    static CRGBPalette16 palette(CRGB::Blue, CRGB::Green, CRGB::Red, CRGB::White);
    static CRGB buf[K1_TOTAL_LEDS];
    static CRGB prev[K1_TOTAL_LEDS];
    for (uint16_t i = 0; i < K1_TOTAL_LEDS; ++i) { buf[i] = CRGB::Black; prev[i] = CRGB::Black; }
    ctx.leds = buf;
    ctx.ledCount = K1_TOTAL_LEDS;
    ctx.centrePoint = K1_CENTRE_POINT;
    ctx.palette = &palette;
    ctx.stripLeds[0] = buf;
    ctx.stripLeds[1] = buf + K1_STRIP_LENGTH;
    acc += static_cast<uint32_t>(ctx.getDistanceFromCentre(0) * 100.0f);
    acc += ctx.isZoneRender() ? 1u : 0u;

    // ── K1AudioContext: drive every accessor through real (silent) K1 frames. ──
    // Build a snapshot + onset event on the stack; bind the context to them and
    // exercise energy / band / chroma / chord / beat / percussive accessors so
    // the adapter is fully instantiated and codegen'd.
    static SBAudioSnapshot snap{};
    static SBOnsetBeatEvent beat{};
    snap.vu_level = 0.42f;
    snap.peak_scaled = 0.31f;
    snap.novelty = 0.20f;
    snap.spectral_energy = 0.55f;
    snap.low_energy = 0.6f;
    snap.mid_energy = 0.4f;
    snap.high_energy = 0.2f;
    snap.chroma_strength = 0.5f;
    snap.silence = false;
#ifdef SB_ONSET_V2
    for (uint8_t b = 0; b < SB_ONSET_SPECTRUM_BINS; ++b) {
        snap.spectrum[b] = static_cast<float>(b) / SB_ONSET_SPECTRUM_BINS;
    }
#endif
#ifdef SB_CHORD_V2
    for (uint8_t c = 0; c < SB_CHROMA_PC_BINS; ++c) {
        snap.chroma_pc[c] = (c == 0) ? 0.9f : 0.1f;  // A-origin index 0 = A
    }
    snap.chord.rootNote = 0;                 // A-origin root
    snap.chord.type = SBChordType::MAJOR;
    snap.chord.confidence = 0.8f;
#endif
    beat.beat_phase = 0.25f;
    beat.beat_confidence = 0.7f;
    beat.beat = true;
    beat.onset = true;
    beat.onset_strength = 0.6f;
    beat.bass_onset_strength = 0.5f;

    K1AudioContext audioCtx(&snap, &beat);
    acc += audioCtx.available() ? 1u : 0u;
    acc += static_cast<uint32_t>(audioCtx.rms() * 100.0f);
    acc += static_cast<uint32_t>(audioCtx.peak() * 100.0f);
    acc += static_cast<uint32_t>(audioCtx.flux() * 100.0f);
    acc += static_cast<uint32_t>(audioCtx.spectralEnergy() * 100.0f);
    acc += audioCtx.isSilent() ? 0u : 1u;
    for (uint8_t b = 0; b < K1_FRAMEWORK_BAND_COUNT; ++b) {
        acc += static_cast<uint32_t>(audioCtx.getBand(b) * 100.0f);
    }
    acc += static_cast<uint32_t>((audioCtx.bass() + audioCtx.mid() +
                                  audioCtx.treble()) * 100.0f);
    acc += static_cast<uint32_t>(audioCtx.beatPhase() * 100.0f);
    acc += static_cast<uint32_t>(audioCtx.beatConfidence() * 100.0f);
    acc += audioCtx.isOnBeat() ? 1u : 0u;
    acc += audioCtx.hasOnset() ? 1u : 0u;
    acc += static_cast<uint32_t>(audioCtx.onsetStrength() * 100.0f);
    acc += static_cast<uint32_t>(audioCtx.bassOnsetStrength() * 100.0f);
    acc += audioCtx.isKickHit() ? 1u : 0u;
    acc += audioCtx.isSnareHit() ? 1u : 0u;
    acc += audioCtx.isHihatHit() ? 1u : 0u;
    acc += static_cast<uint32_t>((audioCtx.kickLevel() + audioCtx.snareLevel() +
                                  audioCtx.hihatLevel()) * 100.0f);
    // Chroma rotation witness: pitch-class A (C-origin label 9) must read the
    // A-origin array index 0 (= 0.9 above), proving the +3 label→index map.
    acc += static_cast<uint32_t>(audioCtx.getChroma(9) * 100.0f);
    acc += static_cast<uint32_t>(audioCtx.chromaStrength() * 100.0f);
    acc += audioCtx.hasChord() ? 1u : 0u;
    acc += audioCtx.rootNote();           // A-origin root 0 → C-origin label 9
    acc += static_cast<uint32_t>(audioCtx.chordConfidence() * 100.0f);
    acc += audioCtx.isMajor() ? 1u : 0u;
    acc += audioCtx.isMinor() ? 1u : 0u;

    // Wire the same context onto the EffectContext audio field (P2 integration).
    ctx.audio.bind(&snap, &beat);
    acc += ctx.audio.available() ? 1u : 0u;
    acc += static_cast<uint32_t>(ctx.audio.rms() * 100.0f);

    // ── K1BufferView: per-strip CRGB16 surface + CRGB↔CRGB16 converters. ──
    static CRGB16 stripPrimary[K1_BUFFER_STRIP_LENGTH];
    static CRGB16 stripSecondary[K1_BUFFER_STRIP_LENGTH];
    for (uint16_t i = 0; i < K1_BUFFER_STRIP_LENGTH; ++i) {
        stripPrimary[i] = CRGB16{0, 0, 0};
        stripSecondary[i] = CRGB16{0, 0, 0};
    }
    K1BufferView bufView(stripPrimary, stripSecondary);
    ctx.k1Buffer.bind(stripPrimary, stripSecondary);
    acc += bufView.available() ? 1u : 0u;
    acc += ctx.k1Buffer.available() ? 1u : 0u;
    acc += bufView.stripLength();
    acc += K1BufferView::stripCount();
    acc += bufView.primary().centre() + bufView.secondary().centre();

    // Exercise per-strip read/write/add + both converters (round-trip).
    bufView.primary().set(bufView.primary().centre(), CRGB::OrangeRed);
    bufView.secondary().set16(0, toCrgb16(CRGB::Cyan));
    bufView.primary().add(0, CRGB(20, 40, 60));
    CRGB roundTrip = toCrgb(toCrgb16(CRGB(128, 64, 200)));
    acc += roundTrip.r + roundTrip.g + roundTrip.b;
    acc += bufView.primary().get(bufView.primary().centre()).r;
    acc += static_cast<uint32_t>(
        static_cast<float>(bufView.secondary().get16(0).g) * 100.0f);
    acc += static_cast<uint32_t>(
        ctx.k1Buffer.strip(K1Strip::PRIMARY).length());

    // IEffect via the concrete probe effect.
    FrameworkProbeEffect effect;
    acc += effect.init(ctx) ? 1u : 0u;
    effect.render(ctx);
    acc += effect.getMetadata().version;
    acc += effect.getParameterCount();
    const EffectParameter* gp = effect.getParameter(0);
    acc += (gp != nullptr) ? static_cast<uint32_t>(gp->defaultValue) : 0u;
    effect.cleanup();

    // FrameBlend.
    applyFrameBlending(buf, prev, K1_TOTAL_LEDS, /*mood=*/200, /*dt=*/0.008f);
    acc += buf[0].r + prev[0].g;

    return acc;
}

}  // namespace probe
}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
