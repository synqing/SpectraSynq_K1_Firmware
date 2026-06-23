/**
 * @file EffectParameter.h
 * @brief Tunable-parameter descriptor for the K1 effect framework.
 *
 * Self-contained spine port (P1) from firmware-v3 `src/plugins/api/IEffect.h`
 * (the EffectParameter / EffectParameterType portion). Direct-copy — pure data
 * struct, no infrastructure dependency.
 *
 * Enables rich UI generation on control surfaces. Both the full 10-field and
 * the backward-compatible 5-field constructors are preserved.
 *
 * Namespace: `k1::effects::framework`. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief Parameter value type hint for UI generation.
 */
enum class EffectParameterType : uint8_t {
    FLOAT = 0,  // Continuous float slider
    INT   = 1,  // Integer stepper
    BOOL  = 2,  // Toggle switch
    ENUM  = 3   // Discrete choice picker
};

/**
 * @brief Effect parameter descriptor.
 */
struct EffectParameter {
    const char* name;            // Parameter name (used as key)
    const char* displayName;     // UI label
    float minValue;              // Minimum allowed value
    float maxValue;              // Maximum allowed value
    float defaultValue;          // Initial value
    EffectParameterType type;    // Value type for UI/validation
    float step;                  // Suggested step size for UI
    const char* group;           // Control group (timing/wave/blend/...)
    const char* unit;            // Display unit (s, Hz, %, x, ...)
    bool advanced;               // True = dense/internal control

    // Full 10-field constructor.
    EffectParameter(const char* n, const char* d,
                    float min, float max, float def,
                    EffectParameterType t,
                    float s,
                    const char* g,
                    const char* u,
                    bool adv)
        : name(n), displayName(d), minValue(min), maxValue(max), defaultValue(def),
          type(t), step(s), group(g), unit(u), advanced(adv) {}

    // Backward-compatible 5-field constructor.
    EffectParameter(const char* n = "", const char* d = "",
                    float min = 0.0f, float max = 1.0f, float def = 0.5f)
        : name(n), displayName(d), minValue(min), maxValue(max), defaultValue(def),
          type(EffectParameterType::FLOAT), step(0.01f), group(""), unit(""), advanced(false) {}
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
