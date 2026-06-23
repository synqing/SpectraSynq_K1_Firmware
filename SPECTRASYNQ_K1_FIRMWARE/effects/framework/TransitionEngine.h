/**
 * @file TransitionEngine.h
 * @brief Centre-origin animated crossfade between two effect frames (K1 P4).
 *
 * Self-contained port of firmware-v3 `src/effects/transitions/TransitionEngine`.
 * Three-buffer model (source + target -> output) and 12 transition types, all
 * radiating from the strip centre to honour the Light Guide Plate physics model.
 *
 * K1 ADAPTATION (vs v3):
 *   - v3 drives ONE contiguous 320-LED span with an internal two-strip loop.
 *     K1 strips are TWO INDEPENDENT channels rendered by separate passes, so this
 *     engine is SINGLE-STRIP and length-configurable (default 160 = K1
 *     NATIVE_RESOLUTION). The K1 render path instantiates one engine PER CHANNEL
 *     (primary + secondary), each transitioning independently — no mirroring.
 *   - The engine works in FastLED `CRGB` (24-bit). The K1 seam converts the live
 *     `CRGB16` (Q8.8) strip buffers to/from CRGB via the K1BufferView converters
 *     at startTransition()/update() time (cosmetic 8->16->8 round-trip, accepted
 *     by the prep).
 *
 * HEAP DISCIPLINE (mandatory):
 *   - source/target/dissolveOrder are allocated ONCE in the constructor (boot),
 *     PSRAM-first with internal-RAM fallback, m_buffersReady gates use.
 *   - The render path — update() -> apply<Type>() — performs NO heap allocation.
 *   - initDissolve() (Fisher-Yates) runs at startTransition() only — O(length)
 *     integer shuffle, no alloc, on Core 1 at the mode-switch boundary.
 *   - If PSRAM + fallback both fail, startTransition() degrades to a hard cut
 *     (copies target to output) and never enters a transition — no crash.
 *
 * STROBE LAW: NUCLEAR radiation intensity is capped at <= 0.3 (kNuclearRadiation
 * CapMax). PHASE_SHIFT / STARGATE are compiled but flagged eyes-on-pending in
 * TransitionTypes.h; the director must not auto-select them.
 *
 * State machine: IDLE -> startTransition() -> ACTIVE -> update() until complete.
 *
 * Namespace: `k1::effects::framework`. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <FastLED.h>

#include "EasingCurves.h"
#include "TransitionTypes.h"

namespace k1 {
namespace effects {
namespace framework {

// ── Constants ─────────────────────────────────────────────────────────────────

/// Default per-strip length (K1 NATIVE_RESOLUTION = 160).
static constexpr uint16_t TRANSITION_DEFAULT_STRIP_LENGTH = 160;

/// Implosion particle budget.
static constexpr uint8_t MAX_PARTICLES = 30;

/// Pulsewave ring budget.
static constexpr uint8_t MAX_PULSES = 5;

/// STROBE LAW: hard ceiling on the NUCLEAR additive radiation glow (prep §4).
static constexpr float kNuclearRadiationCapMax = 0.3f;

// ── Particle (Implosion) ──────────────────────────────────────────────────────

struct TransitionParticle {
    float position;   // 0..length-1 position on the strip
    float velocity;   // speed toward centre
    bool active;
};

// ── Pulse (Pulsewave) ─────────────────────────────────────────────────────────

struct TransitionPulse {
    float radius;     // normalised distance from centre (0..1)
    float intensity;  // brightness (0..1)
    bool active;
};

// ── TransitionEngine ──────────────────────────────────────────────────────────

class TransitionEngine {
public:
    TransitionEngine();
    ~TransitionEngine();

    /// Allocate the source/target/dissolve buffers for a strip of `length` LEDs.
    /// Call ONCE at boot (Core 0/1 init), never on the render path. Returns false
    /// if allocation fails (engine then degrades to hard-cut transitions).
    bool begin(uint16_t length = TRANSITION_DEFAULT_STRIP_LENGTH);

    // ── Transition control ──

    /**
     * @brief Start a centre-origin transition between two CRGB frames.
     * @param sourceBuffer Old effect frame (copied; aliasing-safe).
     * @param targetBuffer New effect frame (copied; aliasing-safe).
     * @param outputBuffer Caller-owned output (written each update()).
     * @param type         Transition type.
     * @param durationMs   Duration in milliseconds.
     * @param curve        Easing curve.
     */
    void startTransition(const CRGB* sourceBuffer,
                         const CRGB* targetBuffer,
                         CRGB* outputBuffer,
                         TransitionType type,
                         uint16_t durationMs,
                         EasingCurve curve);

    /// Start with the type's default duration + easing.
    void startTransition(const CRGB* sourceBuffer,
                         const CRGB* targetBuffer,
                         CRGB* outputBuffer,
                         TransitionType type);

    /// Advance one frame. Returns true while active; false (and copies target to
    /// output) when complete. No heap allocation.
    bool update();

    /// Hard-snap to target and stop.
    void cancel();

    // ── State queries ──

    bool isActive() const { return m_active; }
    bool buffersReady() const { return m_buffersReady; }
    float getProgress() const { return m_progress; }
    TransitionType getType() const { return m_type; }
    uint16_t stripLength() const { return m_length; }
    uint32_t getElapsedMs() const;
    uint32_t getRemainingMs() const;

    /// Weighted random transition (SAFE default set only — never eyes-on-pending).
    static TransitionType getRandomTransition();

private:
    // ── State machine ──
    bool m_active;
    float m_progress;        // eased progress (0..1)
    float m_rawProgress;     // linear progress (0..1)
    TransitionType m_type;
    EasingCurve m_curve;
    uint32_t m_startTime;
    uint16_t m_durationMs;

    // ── Geometry (single strip) ──
    uint16_t m_length;       // LEDs in the strip
    uint16_t m_centre;       // centre-origin index ((length/2) - 1)

    // ── Buffers (PSRAM-backed, allocated in begin()) ──
    CRGB* m_sourceBuffer;
    CRGB* m_targetBuffer;
    CRGB* m_outputBuffer;    // non-owning pointer to the caller's output
    uint16_t* m_dissolveOrder;
    bool m_buffersReady;

    // ── Effect-specific state (embedded — no heap) ──
    TransitionParticle m_particles[MAX_PARTICLES];
    TransitionPulse m_pulses[MAX_PULSES];
    uint8_t m_activePulses;
    float m_irisRadius;
    float m_shockwaveRadius;
    float m_radiationIntensity;
    float m_eventHorizonRadius;
    float m_chevronAngle;
    uint8_t m_foldCount;
    float m_rotationAngle;
    float m_ringPhases[5];

    // ── Helpers ──
    CRGB lerpColour(const CRGB& from, const CRGB& to, uint8_t blend) const;

    // ── Initialisers (mode-switch boundary only) ──
    void initDissolve();
    void initImplosion();
    void initPulsewave();
    void initNuclear();
    void initStargate();
    void initKaleidoscope();
    void initMandala();

    // ── Transition implementations ──
    void applyFade();
    void applyWipeOut();
    void applyWipeIn();
    void applyDissolve();
    void applyPhaseShift();
    void applyPulsewave();
    void applyImplosion();
    void applyIris();
    void applyNuclear();
    void applyStargate();
    void applyKaleidoscope();
    void applyMandala();
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
