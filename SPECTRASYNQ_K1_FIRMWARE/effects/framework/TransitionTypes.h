/**
 * @file TransitionTypes.h
 * @brief 12 centre-origin transition types for the K1 effect framework.
 *
 * Self-contained port (P4) of firmware-v3
 * `src/effects/transitions/TransitionTypes.h`. Every transition radiates from the
 * strip centre (K1 LED 79/80) to honour the Light Guide Plate physics model.
 *
 * STROBE-LAW CLASSIFICATION (P4-prep audit, evidence/p4-prep-transitions.md §4):
 *   - SAFE_DEFAULT set: FADE, WIPE_OUT, WIPE_IN, DISSOLVE, IRIS, IMPLOSION,
 *     PULSEWAVE, KALEIDOSCOPE, MANDALA — per-pixel spatial blends, no global
 *     full-field amplitude modulation. The director (P6) draws from the
 *     transitionIsSafeDefault() subset below.
 *   - EYES_ON_PENDING set: PHASE_SHIFT (high-frequency edge modulation),
 *     STARGATE (kawoosh edge burst). Compiled and selectable, but NOT a default;
 *     transitionRequiresEyesOn() flags them so the director never auto-picks them.
 *   - NUCLEAR: additive radiation glow capped at <= 0.3 in TransitionEngine
 *     (see m_radiationIntensity clamp); also marked eyes-on-pending here.
 *
 * Namespace: `k1::effects::framework`. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <Arduino.h>

namespace k1 {
namespace effects {
namespace framework {

// ── Transition identifiers ────────────────────────────────────────────────────

/**
 * @brief 12 centre-origin transition effects.
 *
 * Each uses distance-from-centre to modulate progress, producing
 * outward-radiating or inward-collapsing animation.
 */
enum class TransitionType : uint8_t {
    FADE = 0,           // Crossfade radiating from centre outward
    WIPE_OUT = 1,       // Wipe expanding centre -> edges
    WIPE_IN = 2,        // Wipe collapsing edges -> centre
    DISSOLVE = 3,       // Random pixel reveal (shuffled order)
    PHASE_SHIFT = 4,    // Frequency-based wave morph (EYES-ON PENDING)
    PULSEWAVE = 5,      // Concentric energy rings from centre
    IMPLOSION = 6,      // Particles converge to centre
    IRIS = 7,           // Aperture open from centre
    NUCLEAR = 8,        // Shockwave from centre (radiation capped; eyes-on)
    STARGATE = 9,       // Portal at centre (kawoosh; EYES-ON PENDING)
    KALEIDOSCOPE = 10,  // Symmetric fold patterns radiating
    MANDALA = 11,       // Concentric ring phases
    TYPE_COUNT = 12
};

// ── Names (diagnostics only) ──────────────────────────────────────────────────

inline const char* getTransitionName(TransitionType type) {
    switch (type) {
        case TransitionType::FADE:         return "Fade";
        case TransitionType::WIPE_OUT:     return "Wipe Out";
        case TransitionType::WIPE_IN:      return "Wipe In";
        case TransitionType::DISSOLVE:     return "Dissolve";
        case TransitionType::PHASE_SHIFT:  return "Phase Shift";
        case TransitionType::PULSEWAVE:    return "Pulsewave";
        case TransitionType::IMPLOSION:    return "Implosion";
        case TransitionType::IRIS:         return "Iris";
        case TransitionType::NUCLEAR:      return "Nuclear";
        case TransitionType::STARGATE:     return "Stargate";
        case TransitionType::KALEIDOSCOPE: return "Kaleidoscope";
        case TransitionType::MANDALA:      return "Mandala";
        default:                           return "Unknown";
    }
}

// ── Default durations (ms) ────────────────────────────────────────────────────

inline uint16_t getDefaultDuration(TransitionType type) {
    switch (type) {
        case TransitionType::FADE:         return 800;
        case TransitionType::WIPE_OUT:     return 1200;
        case TransitionType::WIPE_IN:      return 1200;
        case TransitionType::DISSOLVE:     return 1500;
        case TransitionType::PHASE_SHIFT:  return 1400;
        case TransitionType::PULSEWAVE:    return 2000;
        case TransitionType::IMPLOSION:    return 1500;
        case TransitionType::IRIS:         return 1200;
        case TransitionType::NUCLEAR:      return 2500;
        case TransitionType::STARGATE:     return 3000;
        case TransitionType::KALEIDOSCOPE: return 1800;
        case TransitionType::MANDALA:      return 2200;
        default:                           return 1000;
    }
}

// ── Default easing curve (returns the EasingCurve integer index) ──────────────
// Kept as uint8_t to avoid pulling EasingCurves.h into this header; the engine
// casts the returned value to EasingCurve. The mapping mirrors v3 exactly.

inline uint8_t getDefaultEasing(TransitionType type) {
    switch (type) {
        case TransitionType::FADE:         return 3;   // IN_OUT_QUAD
        case TransitionType::WIPE_OUT:     return 5;   // OUT_CUBIC
        case TransitionType::WIPE_IN:      return 4;   // IN_CUBIC
        case TransitionType::DISSOLVE:     return 0;   // LINEAR
        case TransitionType::PHASE_SHIFT:  return 6;   // IN_OUT_CUBIC
        case TransitionType::PULSEWAVE:    return 2;   // OUT_QUAD
        case TransitionType::IMPLOSION:    return 4;   // IN_CUBIC
        case TransitionType::IRIS:         return 3;   // IN_OUT_QUAD
        case TransitionType::NUCLEAR:      return 8;   // OUT_ELASTIC
        case TransitionType::STARGATE:     return 14;  // IN_OUT_BACK
        case TransitionType::KALEIDOSCOPE: return 6;   // IN_OUT_CUBIC
        case TransitionType::MANDALA:      return 9;   // IN_OUT_ELASTIC
        default:                           return 0;
    }
}

// ── Strobe-Law classification (P4-prep §4) ────────────────────────────────────

/**
 * @brief True if the transition needs on-device eyes-on sign-off before ship.
 *
 * PHASE_SHIFT and STARGATE carry local edge modulation flagged MARGINAL/
 * CONDITIONAL in the prep audit; NUCLEAR carries an additive radiation glow
 * (capped at 0.3 in the engine, but still pending visual confirmation). The
 * director (P6) must never auto-select an eyes-on-pending transition.
 */
inline bool transitionRequiresEyesOn(TransitionType type) {
    return type == TransitionType::PHASE_SHIFT ||
           type == TransitionType::STARGATE ||
           type == TransitionType::NUCLEAR;
}

/**
 * @brief True if the transition is in the SAFE default set the director may pick.
 *
 * The canonical P4 safe default set the director (P6) draws from is the prep's
 * named subset: FADE, WIPE (OUT/IN), DISSOLVE, IRIS, IMPLOSION. PULSEWAVE,
 * KALEIDOSCOPE and MANDALA are audited SAFE too but are held back from the
 * default rotation until P4 batch 2 confirms feel; they remain selectable
 * explicitly. Anything flagged eyes-on is excluded by construction.
 */
inline bool transitionIsSafeDefault(TransitionType type) {
    if (transitionRequiresEyesOn(type)) return false;
    switch (type) {
        case TransitionType::FADE:
        case TransitionType::WIPE_OUT:
        case TransitionType::WIPE_IN:
        case TransitionType::DISSOLVE:
        case TransitionType::IRIS:
        case TransitionType::IMPLOSION:
            return true;
        default:
            return false;
    }
}

/// The SAFE default set, in director-pick order. Length kSafeDefaultCount.
constexpr TransitionType kSafeDefaultTransitions[] = {
    TransitionType::FADE,
    TransitionType::WIPE_OUT,
    TransitionType::WIPE_IN,
    TransitionType::DISSOLVE,
    TransitionType::IRIS,
    TransitionType::IMPLOSION,
};
constexpr uint8_t kSafeDefaultCount =
    sizeof(kSafeDefaultTransitions) / sizeof(kSafeDefaultTransitions[0]);

}  // namespace framework
}  // namespace effects
}  // namespace k1
