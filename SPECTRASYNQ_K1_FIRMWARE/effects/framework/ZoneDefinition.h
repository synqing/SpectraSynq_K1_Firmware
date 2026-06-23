/**
 * @file ZoneDefinition.h
 * @brief Single-strip concentric-zone layout for the K1 effect framework (P5).
 *
 * Ported from firmware-v3 `src/effects/zones/ZoneDefinition.h`, REDESIGNED for
 * K1's independent dual-channel doctrine.
 *
 * THE LOAD-BEARING DESIGN CHANGE (vs v3):
 *   firmware-v3 zones address the WHOLE 320-LED pair: each ZoneSegment carries
 *   Strip-1 left/right ranges and Strip 2 is rendered as a hard MIRROR of Strip 1
 *   (index + 160). That is correct for v3 (both edges always identical) but it
 *   VIOLATES K1's primary/secondary independence — the two LGP edges usually run
 *   DIFFERENT effects.
 *
 *   The K1 port therefore makes a zone address a SINGLE 160-LED strip only. A
 *   ZoneSegment here has ONE strip's left/right ranges (no s2* mirror fields).
 *   Dual-channel independence is achieved by instantiating TWO ZoneComposer
 *   instances — one bound to the primary strip, one to the secondary — each with
 *   its OWN zone layout and its OWN per-zone IEffect assignments. See
 *   ZoneComposer.h for the two-instance contract.
 *
 * Geometry is centre-origin: the centre pair is LEDs 79/80, zones radiate
 * outward. A zone is a concentric ring described by a left range (toward LED 0)
 * and a right range (toward LED 159), symmetric about the centre pair.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

namespace k1 {
namespace effects {
namespace framework {

// ─── Constants ────────────────────────────────────────────────────────────────

/// Maximum concentric zones per strip (hard cap; matches v3).
constexpr uint8_t K1_ZONE_MAX_ZONES = 3;
/// One physical K1 strip = 160 LEDs (NATIVE_RESOLUTION).
constexpr uint16_t K1_ZONE_STRIP_LENGTH = 160;
/// Per-strip centre-origin index (left of the centre pair 79/80).
constexpr uint16_t K1_ZONE_STRIP_CENTRE = (K1_ZONE_STRIP_LENGTH / 2) - 1;  // 79

// ─── Zone Segment Definition (single strip) ───────────────────────────────────

/**
 * @brief LED index ranges for one concentric zone on a SINGLE 160-LED strip.
 *
 * Centre-origin: a zone is symmetric about the centre pair (79/80), described by
 * a left segment (toward LED 0) and a right segment (toward LED 159). There is
 * deliberately NO Strip-2 mirror here — the second physical strip is owned by a
 * SEPARATE ZoneComposer instance (dual-channel independence).
 */
struct ZoneSegment {
    uint8_t zoneId;       ///< 0-indexed zone identity (0 = innermost / centre)
    uint8_t leftStart;    ///< Left segment start (toward LED 0)
    uint8_t leftEnd;      ///< Left segment end (inclusive)
    uint8_t rightStart;   ///< Right segment start (toward LED 159)
    uint8_t rightEnd;     ///< Right segment end (inclusive)
    uint8_t totalLeds;    ///< Total LEDs in this zone (left + right span)
};

// ─── 1-Zone Configuration (unified) ───────────────────────────────────────────

/**
 * 1-Zone Layout: the whole 160-LED strip is one zone.
 *   [0 ─────── 79 | 80 ─────── 159]
 */
constexpr ZoneSegment K1_ZONE_1_CONFIG[1] = {
    { /*zoneId*/ 0, /*leftStart*/ 0, /*leftEnd*/ 79,
      /*rightStart*/ 80, /*rightEnd*/ 159, /*totalLeds*/ 160 }
};

// ─── 2-Zone Configuration (dual split — default) ──────────────────────────────

/**
 * 2-Zone Layout: inner ring near centre + outer ring toward the edges.
 *      ZONE 1 (OUTER)  |     ZONE 0 (CENTRE)     |  ZONE 1 (OUTER)
 *        [0----49]     |   [50--79 | 80--109]    |   [110----159]
 *                            60 LEDs                  100 LEDs outer
 */
constexpr ZoneSegment K1_ZONE_2_CONFIG[2] = {
    // Zone 0 = CENTRE (60 LEDs)
    { /*zoneId*/ 0, /*leftStart*/ 50, /*leftEnd*/ 79,
      /*rightStart*/ 80, /*rightEnd*/ 109, /*totalLeds*/ 60 },
    // Zone 1 = OUTER (100 LEDs)
    { /*zoneId*/ 1, /*leftStart*/ 0, /*leftEnd*/ 49,
      /*rightStart*/ 110, /*rightEnd*/ 159, /*totalLeds*/ 100 }
};

// ─── 3-Zone Configuration (concentric rings) ──────────────────────────────────

/**
 * 3-Zone Layout: centre + middle + outer concentric rings.
 *    ZONE 2  | ZONE 1  | ZONE 0  | ZONE 1  | ZONE 2
 *   [0--19]  | [20-64] | [65-94] | [95-139]| [140-159]
 *   40 LEDs    90 LEDs   30 LEDs   90 LEDs   40 LEDs
 */
constexpr ZoneSegment K1_ZONE_3_CONFIG[3] = {
    // Zone 0 = CENTRE (30 LEDs)
    { /*zoneId*/ 0, /*leftStart*/ 65, /*leftEnd*/ 79,
      /*rightStart*/ 80, /*rightEnd*/ 94, /*totalLeds*/ 30 },
    // Zone 1 = MIDDLE (90 LEDs)
    { /*zoneId*/ 1, /*leftStart*/ 20, /*leftEnd*/ 64,
      /*rightStart*/ 95, /*rightEnd*/ 139, /*totalLeds*/ 90 },
    // Zone 2 = OUTER (40 LEDs)
    { /*zoneId*/ 2, /*leftStart*/ 0, /*leftEnd*/ 19,
      /*rightStart*/ 140, /*rightEnd*/ 159, /*totalLeds*/ 40 }
};

// ─── Zone Layout Selector ─────────────────────────────────────────────────────

enum class ZoneLayout : uint8_t {
    SINGLE = 1,   ///< Whole strip as one zone
    DUAL   = 2,   ///< 2 concentric zones (inner + outer) — default
    TRIPLE = 3    ///< 3 concentric zones
};

/// Resolve a built-in segment array for a layout (defaults to DUAL).
inline const ZoneSegment* getZoneConfig(ZoneLayout layout) {
    switch (layout) {
        case ZoneLayout::SINGLE: return K1_ZONE_1_CONFIG;
        case ZoneLayout::DUAL:   return K1_ZONE_2_CONFIG;
        case ZoneLayout::TRIPLE: return K1_ZONE_3_CONFIG;
        default:                 return K1_ZONE_2_CONFIG;
    }
}

/// Zone count for a layout (1, 2, or 3).
inline uint8_t getZoneCount(ZoneLayout layout) {
    return static_cast<uint8_t>(layout);
}

}  // namespace framework
}  // namespace effects
}  // namespace k1
