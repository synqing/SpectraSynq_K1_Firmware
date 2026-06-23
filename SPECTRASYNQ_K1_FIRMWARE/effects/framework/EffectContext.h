/**
 * @file EffectContext.h
 * @brief Dependency-injection container for effect rendering (K1 framework, P2).
 *
 * Self-contained spine port from firmware-v3 `src/plugins/api/EffectContext.h`,
 * with the P2 adapters wired in: the audio stub is replaced by the real
 * K1AudioContext, and the v3 CRGB write target is paired with the real K1
 * dual-strip CRGB16 surface (K1BufferView).
 *
 * SCOPE:
 *   - LED buffer pointer + geometry (ledCount / centrePoint), adapted to K1
 *     geometry constants (TOTAL_LEDS=320, STRIP_LENGTH=160, centre 79/80).
 *   - Global animation parameters (brightness/speed/gHue/mood/...).
 *   - Timing fields + dt-correct helpers (real K1 dt; see FPS note below).
 *   - Centre-origin geometry helpers (getDistanceFromCentre / signed / mirror /
 *     per-strip), the load-bearing K1 doctrine surface.
 *   - Dual-strip channel pointers (stripLeds[2]) — v3 CRGB geometry view.
 *
 * P2 ADAPTERS (wired here):
 *   - AUDIO: `K1AudioContext audio` maps `audio/sb_audio_snapshot.h`
 *     (SBAudioSnapshot / SBOnsetBeatEvent / SBChordState — 80-bin Goertzel +
 *     12-bin chroma + triad) onto the accessor surface effects expect
 *     (rms/getBand/beatPhase/onset/chord). It is a MAP, not a re-pipe of v3's
 *     ControlBus. P3 binds it from the live snapshot on the render path.
 *   - BUFFER: `K1BufferView k1Buffer` presents K1's TWO independent CRGB16
 *     strips (`leds_16` primary + `leds_16_secondary`) as per-strip views —
 *     NOT a unified 320 array (dual-channel doctrine). The v3 `CRGB* leds` /
 *     `stripLeds[2]` pointers remain for ported effects that write 24-bit CRGB;
 *     the K1BufferView converters (toCrgb16/toCrgb) bridge to fixed-point on the
 *     P3 render path / P4 transitions.
 *
 * FPS / dt NOTE (the 120→~100 correction):
 *   firmware-v3 dt-correction uses a 120-FPS REFERENCE; K1 documents a 100-FPS
 *   target (VP_PERF_FRAME_BUDGET_US = 8333 µs ≡ 120 FPS budget) but the live
 *   render loop runs FREE (uncapped) and the MEASURED rate (global `LED_FPS`,
 *   EMA in SPECTRASYNQ_K1_FIRMWARE.ino) is typically ~100–185 FPS depending on
 *   mode/load. Hardcoding /120.0f therefore mis-times trails on K1. EffectContext
 *   carries a REAL `deltaTimeSeconds` (P3 sets it from measured frame delta) and
 *   ported effects MUST use `getSafeDeltaSeconds()` / the dt helpers rather than
 *   any embedded 120-FPS factor. `K1_REFERENCE_FPS` records the v3 reference for
 *   any persistence-coefficient port that needs the original survival baseline.
 *
 * Namespace: `k1::effects::framework`. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>
#include <cmath>

#include <FastLED.h>

#include "K1AudioContext.h"
#include "K1BufferView.h"

namespace k1 {
namespace effects {
namespace framework {

/// firmware-v3 dt-correction reference rate. K1's measured rate (LED_FPS) differs
/// (see FPS note); kept only so persistence-coefficient ports can recover the
/// original 120-FPS survival baseline before re-deriving against real dt.
constexpr float K1_REFERENCE_FPS = 120.0f;
/// K1 documented frame-budget target (VP_PERF_FRAME_BUDGET_US = 8333 µs).
constexpr float K1_TARGET_FPS = 100.0f;

// ─── K1 geometry constants (parity-confirmed) ─────────────────────────────────
// Sourced from hardware-parity evidence (2026-06-18):
//   TOTAL_LEDS  = 320 (unified virtual buffer; 2 × 160)
//   STRIP_LENGTH = 160 LEDs per physical strip
//   CENTRE_POINT = 80 (right-of-centre index; centre pair = LEDs 79 + 80)
// These are framework-local defaults for the P1 spine. The real render path
// (P3) takes geometry from K1's NATIVE_RESOLUTION; the adapter passes it in.
constexpr uint16_t K1_TOTAL_LEDS    = 320;
constexpr uint16_t K1_STRIP_LENGTH  = 160;
constexpr uint16_t K1_CENTRE_POINT  = 80;   // unified-buffer centre (right of pair)
constexpr uint16_t K1_STRIP_CENTRE  = 79;   // per-strip centre index (left of pair)

/**
 * @brief Effect rendering context with its wired dependencies (P2).
 */
struct EffectContext {
    // ── LED buffer (v3 24-bit write target) ──
    // Ported v3 effects write 24-bit CRGB here. The real K1 fixed-point strips
    // live in `k1Buffer` (below); the P3 render path lifts CRGB → CRGB16 via the
    // K1BufferView converters. Do NOT treat `leds` as a contiguous 320 hardware
    // span — K1 is two independent strips (see k1Buffer).
    CRGB* leds = nullptr;                    ///< v3 CRGB scratch write target
    uint16_t ledCount = K1_TOTAL_LEDS;       ///< Total LED count
    uint16_t centrePoint = K1_CENTRE_POINT;  ///< Centre-origin point (80)

    // ── Palette (raw FastLED palette pointer; PaletteRef wrapper is P2) ──
    const CRGBPalette16* palette = nullptr;

    // ── Global animation parameters ──
    uint8_t brightness = 255;   ///< Master brightness (0–255)
    uint8_t speed = 15;         ///< Animation speed (1–100)
    uint8_t gHue = 0;           ///< Auto-incrementing hue (0–255)
    uint8_t mood = 128;         ///< Mood (0–255): low=reactive, high=smooth
    uint8_t intensity = 128;    ///< Effect intensity (0–255)
    uint8_t saturation = 255;   ///< Colour saturation (0–255)
    uint8_t complexity = 128;   ///< Pattern complexity (0–255)
    uint8_t variation = 64;     ///< Random variation (0–255)
    uint8_t fadeAmount = 20;    ///< Trail fade (0–255)

    // ── Timing ──
    uint32_t deltaTimeMs = 8;
    float    deltaTimeSeconds = 0.008f;
    uint32_t rawDeltaTimeMs = 8;
    float    rawDeltaTimeSeconds = 0.008f;
    uint32_t frameNumber = 0;
    uint32_t totalTimeMs = 0;
    uint32_t rawTotalTimeMs = 0;

    // ── Zone information (when rendering a zone; ZoneComposer is P5) ──
    uint8_t  zoneId = 0xFF;     ///< 0xFF = global render
    uint16_t zoneStart = 0;
    uint16_t zoneLength = 0;

    // ── Dual-strip channel API (v3 CRGB geometry view) ──
    // v3 CRGB pointers for ported dual-channel effects. The AUTHORITATIVE K1
    // hardware strips are the independent CRGB16 buffers in `k1Buffer`; these
    // CRGB pointers are scratch. K1 is two independent 160-LED strips, NOT a
    // contiguous 320 array.
    CRGB* stripLeds[2] = {nullptr, nullptr};
    uint16_t stripLength = K1_STRIP_LENGTH;  ///< 160 per strip
    uint8_t  stripCount = 2;
    uint16_t stripCentre = K1_STRIP_CENTRE;  ///< 79 per strip
    bool dualChannelMode = false;            ///< Effect wrote stripLeds[] directly

    // ── K1 dual-strip CRGB16 surface (P2 buffer adapter) ──
    // The real K1 hardware write target: two independent CRGB16 (Q8.8) strips,
    // primary + secondary. P3 binds it from leds_16 / leds_16_secondary. Holds
    // the CRGB↔CRGB16 converters the transition/zone code (P4/P5) needs.
    K1BufferView k1Buffer{};

    // ── Audio (P2 audio adapter) ──
    // Maps K1's SBAudioSnapshot / SBOnsetBeatEvent onto the v3 accessor surface
    // (rms / getBand / beatPhase / onset channels / chroma / chord). P3 binds it
    // from the live snapshot. Default-constructed → audio.available() == false.
    K1AudioContext audio{};

    // ── K1 legacy-bridge fields (P3 — LegacyEffectAdapter only) ──
    // These carry the per-channel inputs a wrapped legacy `light_mode_*` mode
    // needs, which the v3 surface above does not model. They exist solely so a
    // LegacyEffectAdapter can call K1's existing mode-dispatch unchanged and emit
    // byte-identical output. New framework-native effects ignore them entirely.
    //   - `legacyChannel` is an OPAQUE pointer to the live `RenderChannelState`
    //     (history buffer, waveform scalar refs, ChannelEffectState). It is typed
    //     `void*` so this header pulls in NO legacy effect/render code; the
    //     adapter (which lives next to the dispatch) casts it back. Null unless
    //     the render path bound a legacy channel for this frame.
    //   - `legacyMode` is the resolved K1 lightshow_modes enum value to render.
    //   - `legacyHistorySeeded` mirrors the dispatch prologue's seed flag (true
    //     when the seed-before-render copy already ran for this channel).
    void*    legacyChannel = nullptr;   ///< RenderChannelState* (opaque); P3 bridge
    uint8_t  legacyMode = 0;            ///< K1 lightshow_modes enum to dispatch
    bool     legacyHistorySeeded = false;  ///< seed prologue already ran this pass

    // ──────────────────────────────────────────────────────────────────────────
    // Centre-origin geometry helpers (load-bearing K1 doctrine surface)
    // ──────────────────────────────────────────────────────────────────────────

    /// Normalised distance from centre: 0.0 at centre, 1.0 at edges.
    float getDistanceFromCentre(uint16_t index) const {
        if (ledCount == 0 || centrePoint == 0) return 0.0f;
        int16_t d = static_cast<int16_t>(std::abs(static_cast<int>(index) -
                                                  static_cast<int>(centrePoint)));
        return static_cast<float>(d) / static_cast<float>(centrePoint);
    }

    /// Signed position from centre: -1.0 at start, 0.0 centre, +1.0 at end.
    float getSignedPosition(uint16_t index) const {
        if (ledCount == 0 || centrePoint == 0) return 0.0f;
        int16_t off = static_cast<int16_t>(static_cast<int>(index) -
                                           static_cast<int>(centrePoint));
        return static_cast<float>(off) / static_cast<float>(centrePoint);
    }

    /// Mirror an index across the centre pair (for symmetric effects).
    uint16_t mirrorIndex(uint16_t index) const {
        if (index >= ledCount) return 0;
        if (index < centrePoint) {
            return static_cast<uint16_t>(centrePoint + (centrePoint - 1 - index));
        }
        return static_cast<uint16_t>(centrePoint - 1 - (index - centrePoint));
    }

    /// Per-strip centre-origin distance (for DUAL_CHANNEL effects).
    float getDistanceFromStripCentre(uint16_t ledIdx) const {
        if (stripLength == 0 || stripCentre == 0) return 0.0f;
        int16_t off = static_cast<int16_t>(std::abs(static_cast<int>(ledIdx) -
                                                    static_cast<int>(stripCentre)));
        return static_cast<float>(off) / static_cast<float>(stripCentre);
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Timing helpers (dt-correct)
    // ──────────────────────────────────────────────────────────────────────────

    /// Normalised mood [0,1] (0=reactive, 1=smooth).
    float getMoodNormalised() const {
        return static_cast<float>(mood) / 255.0f;
    }

    /// Asymmetric rise/fall smoothing coefficients derived from mood.
    void getMoodSmoothing(float& riseOut, float& fallOut) const {
        const float m = getMoodNormalised();
        riseOut = 0.3f + 0.4f * m;   // 0.3 reactive → 0.7 smooth
        fallOut = 0.5f + 0.3f * m;   // 0.5 reactive → 0.8 smooth
    }

    /// Safe delta seconds, clamped to [0.0001, 0.05] for physics stability.
    float getSafeDeltaSeconds() const {
        float dt = deltaTimeSeconds;
        if (dt < 0.0001f) dt = 0.0001f;
        if (dt > 0.05f) dt = 0.05f;
        return dt;
    }

    /// Safe unscaled delta seconds (beat timing independent of speed).
    float getSafeRawDeltaSeconds() const {
        float dt = rawDeltaTimeSeconds;
        if (dt < 0.0001f) dt = 0.0001f;
        if (dt > 0.05f) dt = 0.05f;
        return dt;
    }

    /// True if rendering to a zone (not the full strip).
    bool isZoneRender() const { return zoneId != 0xFF; }

    EffectContext() = default;
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
