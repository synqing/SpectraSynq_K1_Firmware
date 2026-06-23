/**
 * @file K1BufferView.h
 * @brief K1 dual-strip pixel-buffer surface for the effect framework (P2).
 *
 * Presents the framework's write target over K1's TWO INDEPENDENT 160-LED
 * strips, honouring the dual-channel doctrine: K1 is a primary + a secondary
 * strip, each its own `CRGB16[STRIP_LENGTH]` buffer (`leds_16` /
 * `leds_16_secondary` in system/globals.h) — NOT one contiguous 320 array. The
 * eye sees a diffused plate per channel; the two channels usually run different
 * effects. This adapter therefore exposes a per-strip view, never a unified 320
 * span. (See _scratch/.../evidence/p4-prep-transitions.md for the render seam.)
 *
 * PIXEL FORMAT BRIDGE (P4-prep documents this seam):
 *   - v3 effects write FastLED `CRGB`   — 24-bit, three uint8 channels [0,255].
 *   - K1 effects write `CRGB16`         — 48-bit, three SQ15x16 (Q8.8 fixed-point)
 *                                         channels carrying a NORMALISED [0,1]
 *                                         intensity (the K1 convention: 1.0 = full),
 *                                         scaled to LED counts downstream.
 *   The `toCrgb16` / `toCrgb` helpers convert between the two. They mirror the
 *   canonical K1 `crgb_to_crgb16` (visual/lightshow_modes.h:65: channel/255.0f)
 *   but are kept self-contained here so the framework pulls in no effect code.
 *
 * READ-ONLY ADAPTER over caller-owned buffers. Holds `CRGB16*` pointers to the
 * two live K1 strip buffers (P3 render path supplies them) and presents a
 * bounds-checked per-strip view. Adds NO behaviour to any build; the K1 render
 * path and DSP are untouched. Default-constructed → not bound → safe no-ops.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

#include <FastLED.h>          // CRGB (v3 24-bit pixel)
#include "constants.h"        // CRGB16 (Q8.8 SQ15x16), NATIVE_RESOLUTION

namespace k1 {
namespace effects {
namespace framework {

/// Per-strip LED count (K1 NATIVE_RESOLUTION). One physical strip = 160 LEDs.
constexpr uint16_t K1_BUFFER_STRIP_LENGTH = NATIVE_RESOLUTION;  // 160
/// Per-strip centre-origin index (centre pair = idx 79 + 80; 79 is the
/// left-of-pair index the K1 mirror-fill anchors on).
constexpr uint16_t K1_BUFFER_STRIP_CENTRE = (NATIVE_RESOLUTION / 2) - 1;  // 79

/// Logical channel identity. Two independent strips; never blended into one span.
enum class K1Strip : uint8_t { PRIMARY = 0, SECONDARY = 1 };

// ─── Pixel-format converters (CRGB 24-bit ↔ CRGB16 Q8.8 normalised) ───────────
// Mirror visual/lightshow_modes.h crgb_to_crgb16 (channel / 255.0f) but keep the
// framework free of effect-code includes. The transition/zone code (P4/P5) needs
// these to lift v3 CRGB effect output into K1's fixed-point compositing domain.

/// v3 CRGB (24-bit, [0,255]) → K1 CRGB16 (Q8.8, normalised [0,1]).
inline CRGB16 toCrgb16(const CRGB& c) {
    return CRGB16{
        SQ15x16(static_cast<float>(c.r) / 255.0f),
        SQ15x16(static_cast<float>(c.g) / 255.0f),
        SQ15x16(static_cast<float>(c.b) / 255.0f)};
}

/// K1 CRGB16 (Q8.8, normalised [0,1]) → v3 CRGB (24-bit, [0,255]), clamped.
inline CRGB toCrgb(const CRGB16& c) {
    auto to8 = [](const SQ15x16& ch) -> uint8_t {
        float v = static_cast<float>(ch) * 255.0f;
        if (v < 0.0f) v = 0.0f;
        if (v > 255.0f) v = 255.0f;
        return static_cast<uint8_t>(v + 0.5f);
    };
    return CRGB{to8(c.r), to8(c.g), to8(c.b)};
}

/**
 * @brief Bounds-checked view over ONE K1 CRGB16 strip buffer.
 *
 * Non-owning. Construct with a pointer to a live `CRGB16[length]` strip. Every
 * accessor is bounds-checked; out-of-range writes are dropped and reads return
 * black, so an effect can never scribble past a strip into the other channel.
 */
class K1StripView {
public:
    K1StripView() = default;
    K1StripView(CRGB16* pixels, uint16_t length)
        : m_pixels(pixels), m_length(length) {}

    bool bound() const { return m_pixels != nullptr && m_length > 0; }
    uint16_t length() const { return m_length; }
    /// Per-strip centre-origin index for symmetric (mirror-fill) effects.
    uint16_t centre() const {
        return (m_length > 0) ? static_cast<uint16_t>((m_length / 2) - 1) : 0;
    }

    /// Raw fixed-point read (black if out of range / unbound).
    CRGB16 get16(uint16_t i) const {
        if (!bound() || i >= m_length) return CRGB16{0, 0, 0};
        return m_pixels[i];
    }
    /// Raw fixed-point write (dropped if out of range / unbound).
    void set16(uint16_t i, const CRGB16& c) {
        if (!bound() || i >= m_length) return;
        m_pixels[i] = c;
    }

    /// v3-domain read: returns the pixel as 24-bit CRGB (for ported effects).
    CRGB get(uint16_t i) const { return toCrgb(get16(i)); }
    /// v3-domain write: accepts a 24-bit CRGB and stores it as CRGB16.
    void set(uint16_t i, const CRGB& c) { set16(i, toCrgb16(c)); }

    /// Additive v3-domain blend into the fixed-point buffer (saturating at 1.0).
    void add(uint16_t i, const CRGB& c) {
        if (!bound() || i >= m_length) return;
        CRGB16 cur = m_pixels[i];
        CRGB16 inc = toCrgb16(c);
        m_pixels[i] = CRGB16{satAdd(cur.r, inc.r), satAdd(cur.g, inc.g),
                             satAdd(cur.b, inc.b)};
    }

    /// Direct fixed-point buffer pointer (for K1-native fill loops). May be null.
    CRGB16* raw() const { return m_pixels; }

private:
    static SQ15x16 satAdd(const SQ15x16& a, const SQ15x16& b) {
        SQ15x16 s = a + b;
        return (s > SQ15x16(1.0f)) ? SQ15x16(1.0f) : s;
    }

    CRGB16* m_pixels = nullptr;
    uint16_t m_length = 0;
};

/**
 * @brief Dual-strip pixel surface: primary + secondary, each independent.
 *
 * Construct/`bind()` with pointers to the two live K1 strip buffers (P3 supplies
 * `leds_16` + `leds_16_secondary`). Exposes a `K1StripView` per channel. There is
 * deliberately NO unified 320-pixel accessor — the dual-channel doctrine forbids
 * treating the two strips as one contiguous span.
 */
class K1BufferView {
public:
    K1BufferView() = default;

    K1BufferView(CRGB16* primary, CRGB16* secondary,
                 uint16_t length = K1_BUFFER_STRIP_LENGTH)
        : m_primary(primary, length), m_secondary(secondary, length) {}

    /// Rebind to a fresh frame's K1 strip buffers (P3 render path calls this).
    void bind(CRGB16* primary, CRGB16* secondary,
              uint16_t length = K1_BUFFER_STRIP_LENGTH) {
        m_primary = K1StripView(primary, length);
        m_secondary = K1StripView(secondary, length);
    }

    bool available() const { return m_primary.bound() && m_secondary.bound(); }

    K1StripView& primary() { return m_primary; }
    const K1StripView& primary() const { return m_primary; }
    K1StripView& secondary() { return m_secondary; }
    const K1StripView& secondary() const { return m_secondary; }

    /// Select a strip by channel id.
    K1StripView& strip(K1Strip ch) {
        return (ch == K1Strip::PRIMARY) ? m_primary : m_secondary;
    }
    const K1StripView& strip(K1Strip ch) const {
        return (ch == K1Strip::PRIMARY) ? m_primary : m_secondary;
    }

    uint16_t stripLength() const { return m_primary.length(); }
    static constexpr uint8_t stripCount() { return 2; }

private:
    K1StripView m_primary;
    K1StripView m_secondary;
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
