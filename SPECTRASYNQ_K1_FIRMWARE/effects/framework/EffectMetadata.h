/**
 * @file EffectMetadata.h
 * @brief Effect metadata + role-flag descriptors for the K1 effect framework.
 *
 * Self-contained spine port (P1) from firmware-v3
 * `src/plugins/api/IEffect.h` (the EffectMetadata / EffectCategory /
 * EffectRoleFlags portion). Direct-copy per the architecture probe — pure
 * data structs with no audio/render infrastructure dependency.
 *
 * Namespace: `k1::effects::framework`. Clean names only (no legacy SB_/sb_
 * prefixes, no brand words) per the 2026-06-18 naming rule.
 *
 * Compiled ONLY under the `k1_effect_framework` PlatformIO env (flag
 * `K1_EFFECT_FRAMEWORK_V1`). The shipping `k1_hardware` build never sees it.
 *
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

#include "EffectId.h"

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief Effect category for UI organisation and filtering.
 */
enum class EffectCategory : uint8_t {
    UNCATEGORISED = 0,
    FIRE,            // Fire, heat, warmth effects
    WATER,           // Ocean, waves, rain
    NATURE,          // Aurora, forest, organic
    GEOMETRIC,       // Patterns, shapes, mathematical
    QUANTUM,         // LGP interference, wave physics
    SHOCKWAVE,       // Pulse, burst, explosion
    AMBIENT,         // Subtle, background, mood
    PARTY,           // Fast, dynamic, music-reactive
    CUSTOM,          // User-created via designer
    LEGACY_LINEAR    // Linear patterns exempt from centre-origin (v1 parity)
};

/**
 * @brief Per-effect role hints for downstream composition / persistence passes.
 *
 * A bitmask of declarative tags describing what an effect does to the
 * framebuffer, so cross-cutting passes (frame-blend LPF, invert-input negative
 * space, colour/geometry split, background/foreground composition, persistence
 * opt-out) can decide per-effect whether their pass applies without scanning
 * render bodies. Default `NONE` preserves baseline behaviour; effects opt in by
 * ORing flags into their EffectMetadata.
 */
enum class EffectRoleFlags : uint8_t {
    NONE                    = 0,
    SELF_TRAILING           = 1u << 0,  // bakes its own trail — skip whole-frame LPF
    RENDERS_COLOUR_ONLY     = 1u << 1,  // writes hue/sat only — geometry pass may run alongside
    RENDERS_GEOMETRY_ONLY   = 1u << 2,  // writes value/position only — colour pass may run alongside
    INVERT_INPUT_OK         = 1u << 3,  // safe to feed inverted input for negative space
    BACKGROUND              = 1u << 4,  // composes as background layer; absence = foreground
    OPTS_OUT_OF_PERSISTENCE = 1u << 5,  // skip persistence wrappers
    DUAL_CHANNEL            = 1u << 6   // renders strips independently via stripLeds[]; skip unified→strip mirror
};

/// Bitwise OR for EffectRoleFlags (scoped enum → explicit operator).
inline EffectRoleFlags operator|(EffectRoleFlags a, EffectRoleFlags b) {
    return static_cast<EffectRoleFlags>(
        static_cast<uint8_t>(a) | static_cast<uint8_t>(b));
}

/// Bitwise AND for EffectRoleFlags (membership test).
inline EffectRoleFlags operator&(EffectRoleFlags a, EffectRoleFlags b) {
    return static_cast<EffectRoleFlags>(
        static_cast<uint8_t>(a) & static_cast<uint8_t>(b));
}

/// True if `flag` is set within `flags`.
inline bool hasRoleFlag(EffectRoleFlags flags, EffectRoleFlags flag) {
    return static_cast<uint8_t>(flags & flag) != 0;
}

/**
 * @brief Effect metadata for registration and UI display.
 */
struct EffectMetadata {
    const char* name;            // Display name (max 32 chars)
    const char* description;     // Brief description (max 128 chars)
    EffectCategory category;     // Category for filtering
    uint8_t version;             // Effect version (for updates)
    const char* author;          // Creator name (optional)
    EffectRoleFlags roleFlags;   // Role hints (default NONE = baseline)
    EffectId id;                 // Stable namespaced ID (set during registration)

    EffectMetadata(const char* n = "Unnamed",
                   const char* d = "",
                   EffectCategory c = EffectCategory::UNCATEGORISED,
                   uint8_t v = 1,
                   const char* a = nullptr,
                   EffectRoleFlags r = EffectRoleFlags::NONE)
        : name(n)
        , description(d)
        , category(c)
        , version(v)
        , author(a)
        , roleFlags(r)
        , id(INVALID_EFFECT_ID) {}
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
