/**
 * @file LegacyEffectAdapter.cpp
 * @brief Static registry of LegacyEffectAdapter instances keyed by light mode.
 *
 * Builds a fixed table (one adapter per K1 lightshow_modes value) in .bss — no
 * heap. `legacy_effect_for_mode()` returns the adapter for a mode; the render
 * path renders the mode held in `ctx.legacyMode`, which the registry keeps equal
 * to the looked-up adapter's bound mode. Out-of-range modes fall back to a shared
 * adapter that renders whatever the caller places in ctx.legacyMode.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1 (and only included by the
 * k1_effect_framework env's build_src_filter). The shipping k1_hardware build
 * never sees this TU.
 *
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "LegacyEffectAdapter.h"

#include "config_types.h"   // lightshow_modes enum + NUM_MODES + light_mode_is_enabled()

namespace k1 {
namespace effects {
namespace framework {

namespace {

/// One adapter per declared light mode. Static storage → .bss, zero heap.
LegacyEffectAdapter g_legacy_adapters[NUM_MODES];

/// Shared fallback for out-of-range mode ids (renders ctx.legacyMode as-is).
LegacyEffectAdapter g_legacy_fallback;

/// Lazy one-time bind of each adapter to its mode + a minimal metadata stub.
/// init() runs on Core 0 at selection time, so first-touch construction here is
/// off the hot render path. Metadata names stay generic ("Legacy <n>") — the
/// real catalogue metadata arrives with the P7 effect catalogue.
bool g_registry_ready = false;

void ensure_registry() {
    if (g_registry_ready) return;
    static EffectMetadata kLegacyMeta(
        "Legacy", "K1 legacy light_mode_* wrapped as IEffect",
        EffectCategory::LEGACY_LINEAR, 1, "K1");
    for (uint16_t m = 0; m < NUM_MODES; ++m) {
        g_legacy_adapters[m].configure(static_cast<uint8_t>(m), kLegacyMeta);
    }
    g_legacy_fallback.configure(0, kLegacyMeta);
    g_registry_ready = true;
}

}  // namespace

IEffect* legacy_effect_for_mode(uint8_t mode) {
    ensure_registry();
    if (mode < NUM_MODES) {
        return &g_legacy_adapters[mode];
    }
    return &g_legacy_fallback;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
