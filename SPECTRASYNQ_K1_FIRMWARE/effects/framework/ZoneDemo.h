/**
 * @file ZoneDemo.h
 * @brief Two-instance independent dual-channel ZoneComposer demo (P5).
 *
 * Proves the P5 deliverable: TWO ZoneComposer instances (one per K1 channel),
 * each with its OWN zone layout and per-zone effects, composited with blend
 * modes. This is the ADDITIVE zone-composed render option a future P6 director
 * can choose — it does not replace the single-effect path.
 *
 * The demo wires a concrete preset:
 *   PRIMARY strip   → DUAL layout: inner ring = ZoneFillEffect (warm),
 *                     outer ring = ZoneScanEffect (cool), blended SCREEN.
 *   SECONDARY strip → DIFFERENT layout (TRIPLE) running DIFFERENT effects,
 *                     to demonstrate the two edges are genuinely independent.
 *
 * The two demo effects are tiny self-contained IEffect implementations (no audio
 * dependency, no heap) so the demo proves multi-zone composition end-to-end
 * without pulling in the catalogue.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

#include "EffectContext.h"
#include "EffectMetadata.h"
#include "IEffect.h"
#include "K1BufferView.h"
#include "ZoneComposer.h"

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief Demo effect: centre-origin radial fill from the palette.
 *
 * Fills its zone buffer with palette colours indexed by distance-from-centre,
 * pulsing with frameNumber. Self-contained, zero-heap, no audio.
 */
class ZoneFillEffect final : public IEffect {
public:
    bool init(EffectContext& ctx) override { (void)ctx; return true; }

    void render(EffectContext& ctx) override {
        if (ctx.leds == nullptr) return;
        const uint8_t phase = static_cast<uint8_t>(ctx.frameNumber & 0xFF);
        for (uint16_t i = 0; i < ctx.ledCount; ++i) {
            const float d = ctx.getDistanceFromCentre(i);     // 0..1
            const uint8_t idx = static_cast<uint8_t>(d * 255.0f) + phase;
            if (ctx.palette != nullptr) {
                ctx.leds[i] = ColorFromPalette(*ctx.palette, idx, 255, LINEARBLEND);
            } else {
                ctx.leds[i] = CHSV(idx, 255, 255);
            }
        }
    }

    void cleanup() override {}

    const EffectMetadata& getMetadata() const override {
        static const EffectMetadata meta{
            "Zone Fill", "Centre-origin palette fill",
            EffectCategory::AMBIENT, 1, "k1"};
        return meta;
    }
};

/**
 * @brief Demo effect: a single bright dot scanning out from the centre.
 *
 * A moving highlight whose position tracks frameNumber; demonstrates an effect
 * with its own per-zone time (the two zones run at different speeds).
 */
class ZoneScanEffect final : public IEffect {
public:
    bool init(EffectContext& ctx) override { (void)ctx; return true; }

    void render(EffectContext& ctx) override {
        if (ctx.leds == nullptr || ctx.ledCount == 0) return;
        // Fade the persistent buffer to leave a short trail (no heap; in-place).
        for (uint16_t i = 0; i < ctx.ledCount; ++i) {
            ctx.leds[i].nscale8(200);
        }
        const uint16_t pos =
            static_cast<uint16_t>(ctx.frameNumber % ctx.ledCount);
        const uint8_t hue = static_cast<uint8_t>(ctx.gHue + (pos << 1));
        ctx.leds[pos] = CHSV(hue, 200, 255);
    }

    void cleanup() override {}

    const EffectMetadata& getMetadata() const override {
        static const EffectMetadata meta{
            "Zone Scan", "Centre-out scanning dot with trail",
            EffectCategory::GEOMETRIC, 1, "k1",
            EffectRoleFlags::SELF_TRAILING};
        return meta;
    }
};

/**
 * @brief The two-instance demo: one ZoneComposer per K1 channel, independent.
 *
 * Owns its demo effects as members (.bss-friendly statics at use site). init()
 * allocates both composers' scratch buffers; configureDemoPreset() assigns the
 * concrete multi-zone layout per channel; render() composes both channels into
 * the supplied dual-strip surface — proving genuine dual-channel independence.
 */
class DualChannelZoneDemo {
public:
    /// Allocate both composers (PSRAM-preferred). Returns false on alloc failure.
    bool init() {
        const bool a = m_primary.init();
        const bool b = m_secondary.init();
        return a && b;
    }

    /// Assign the concrete demo preset: DIFFERENT layouts + effects per channel.
    void configureDemoPreset() {
        // ── PRIMARY: 2 concentric zones, fill (inner) + scan (outer), SCREEN ──
        m_primary.setLayout(ZoneLayout::DUAL);
        m_primary.setZoneEffect(0, &m_fill);
        m_primary.setZoneBrightness(0, 255);
        m_primary.setZoneSpeed(0, 15);
        m_primary.setZoneBlendMode(0, BlendMode::OVERWRITE);
        m_primary.setZoneEnabled(0, true);

        m_primary.setZoneEffect(1, &m_scan);
        m_primary.setZoneBrightness(1, 255);
        m_primary.setZoneSpeed(1, 30);
        m_primary.setZoneBlendMode(1, BlendMode::SCREEN);
        m_primary.setZoneEnabled(1, true);
        m_primary.setEnabled(true);

        // ── SECONDARY: 3 concentric zones, DIFFERENT effect/blend mix ──
        // Proves the second edge is genuinely independent (different layout AND
        // a different effect-to-zone mapping than the primary edge).
        m_secondary.setLayout(ZoneLayout::TRIPLE);
        m_secondary.setZoneEffect(0, &m_scan);          // centre: scan
        m_secondary.setZoneSpeed(0, 10);
        m_secondary.setZoneBlendMode(0, BlendMode::OVERWRITE);
        m_secondary.setZoneEnabled(0, true);

        m_secondary.setZoneEffect(1, &m_fill);          // middle: fill
        m_secondary.setZoneSpeed(1, 25);
        m_secondary.setZoneBlendMode(1, BlendMode::ADDITIVE);
        m_secondary.setZoneEnabled(1, true);

        m_secondary.setZoneEffect(2, &m_fill);          // outer: fill (slow)
        m_secondary.setZoneSpeed(2, 8);
        m_secondary.setZoneBlendMode(2, BlendMode::ADDITIVE);
        m_secondary.setZoneEnabled(2, true);
        m_secondary.setEnabled(true);
    }

    /**
     * @brief Compose both channels into the dual-strip surface.
     * @param surface Live K1 dual-strip CRGB16 surface (primary + secondary).
     * @param base    Frame-global context (palette, gHue, dt, frameNumber).
     */
    void render(K1BufferView& surface, const EffectContext& base) {
        m_primary.bindStrip(surface.primary());
        m_primary.render(base);
        m_secondary.bindStrip(surface.secondary());
        m_secondary.render(base);
    }

    ZoneComposer& primaryComposer() { return m_primary; }
    ZoneComposer& secondaryComposer() { return m_secondary; }

private:
    ZoneComposer m_primary;
    ZoneComposer m_secondary;
    ZoneFillEffect m_fill;
    ZoneScanEffect m_scan;
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
