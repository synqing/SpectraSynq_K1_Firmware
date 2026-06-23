/**
 * @file zone_composer_compile_probe.cpp
 * @brief Compile-only probe for the P5 ZoneComposer + two-instance demo.
 *
 * Forces compilation, linkage and genuine codegen of ZoneComposer, ZoneDemo (the
 * two-instance independent dual-channel wiring) and the demo preset. It builds
 * two live K1 CRGB16 strips, runs the dual-channel demo for several frames, and
 * touches the composed output so the optimiser cannot discard the path. Nothing
 * here runs on the device render path — build-surface witness only.
 *
 * Guarded by K1_EFFECT_FRAMEWORK_V1: present ONLY in the `k1_effect_framework`
 * env. The shipping `k1_hardware` env never defines the flag nor includes this
 * TU, so production firmware is byte-unchanged.
 *
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include <FastLED.h>

#include "EffectContext.h"
#include "K1BufferView.h"
#include "ZoneComposer.h"
#include "ZoneDefinition.h"
#include "ZoneDemo.h"

namespace k1 {
namespace effects {
namespace framework {
namespace probe {

/// Drive the full P5 surface; return a non-trivial value so nothing is elided.
uint32_t k1_zone_composer_compile_probe() {
    uint32_t acc = 0;

    // ── Two live K1 CRGB16 strips (the independent dual channels). ──
    static CRGB16 primaryStrip[K1_ZONE_STRIP_LENGTH];
    static CRGB16 secondaryStrip[K1_ZONE_STRIP_LENGTH];
    for (uint16_t i = 0; i < K1_ZONE_STRIP_LENGTH; ++i) {
        primaryStrip[i] = CRGB16{0, 0, 0};
        secondaryStrip[i] = CRGB16{0, 0, 0};
    }
    K1BufferView surface(primaryStrip, secondaryStrip);
    acc += surface.available() ? 1u : 0u;

    // ── Frame-global context: a palette + timing. ──
    static CRGBPalette16 palette(CRGB::Blue, CRGB::Green, CRGB::Red, CRGB::White);
    EffectContext base;
    base.palette = &palette;
    base.gHue = 32;
    base.deltaTimeSeconds = 0.008f;
    base.deltaTimeMs = 8;

    // ── Two-instance demo: init + concrete preset + multi-frame render. ──
    static DualChannelZoneDemo demo;
    acc += demo.init() ? 1u : 0u;
    demo.configureDemoPreset();

    // Confirm the two channels carry DIFFERENT layouts (independence witness).
    acc += demo.primaryComposer().getZoneCount();     // 2 (DUAL)
    acc += demo.secondaryComposer().getZoneCount();    // 3 (TRIPLE)
    acc += (demo.primaryComposer().getZoneCount() !=
            demo.secondaryComposer().getZoneCount()) ? 100u : 0u;

    for (uint32_t frame = 0; frame < 8; ++frame) {
        base.frameNumber = frame;
        demo.render(surface, base);
    }

    // Touch the composed output of BOTH strips so codegen is forced.
    for (uint16_t i = 0; i < K1_ZONE_STRIP_LENGTH; ++i) {
        acc += static_cast<uint32_t>(static_cast<float>(primaryStrip[i].r) * 8.0f);
        acc += static_cast<uint32_t>(static_cast<float>(secondaryStrip[i].g) * 8.0f);
    }

    // ── Direct single-strip ZoneComposer exercise (the additive render API). ──
    static ZoneComposer solo;
    static ZoneFillEffect soloFill;
    acc += solo.init() ? 1u : 0u;
    solo.setLayout(ZoneLayout::SINGLE);
    solo.setZoneEffect(0, &soloFill);
    solo.setZoneEnabled(0, true);
    solo.setZoneBlendMode(0, BlendMode::OVERWRITE);
    solo.setEnabled(true);
    solo.bindStrip(surface.primary());
    base.frameNumber = 99;
    solo.render(base);
    acc += solo.getZoneCount();
    acc += solo.isZoneEnabled(0) ? 1u : 0u;
    acc += static_cast<uint32_t>(solo.getZoneBlendMode(0));

    // Exercise blend-mode round-trip via every mode on a zone setter.
    for (uint8_t m = 0; m < static_cast<uint8_t>(BlendMode::MODE_COUNT); ++m) {
        solo.setZoneBlendMode(0, static_cast<BlendMode>(m));
        acc += static_cast<uint32_t>(solo.getZoneBlendMode(0));
    }

    return acc;
}

}  // namespace probe
}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
