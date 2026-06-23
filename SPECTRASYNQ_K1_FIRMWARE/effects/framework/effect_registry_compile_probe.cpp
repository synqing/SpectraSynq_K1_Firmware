/**
 * @file effect_registry_compile_probe.cpp
 * @brief Link-witness for the EffectRegistry (R1). Exercises every lookup +
 *        the boot self-check so the registry genuinely compiles AND links.
 *
 * Mirrors the existing framework_compile_probe pattern: a single externally
 * visible no-argument function that touches the whole public surface. It is
 * never called by the production render path; its sole purpose is to force the
 * linker to resolve every registry symbol (including the native effect singleton
 * accessors and the legacy adapter bind) under K1_EFFECT_REGISTRY_V1.
 *
 * Compiled ONLY under K1_EFFECT_REGISTRY_V1 (which requires K1_EFFECT_FRAMEWORK_V1).
 * The shipping k1_hardware build defines NEITHER flag and never sees this TU.
 *
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_REGISTRY_V1

#if !defined(K1_EFFECT_FRAMEWORK_V1)
#error "K1_EFFECT_REGISTRY_V1 requires K1_EFFECT_FRAMEWORK_V1"
#endif

#include "EffectRegistry.h"
#include "config_types.h"  // NUM_MODES, LIGHT_MODE_BLOOM

namespace k1 {
namespace effects {
namespace framework {

/// Touch the entire registry public API. Returns a checksum-ish sum so the
/// compiler cannot fold the calls away. Never invoked in production.
volatile uint32_t effect_registry_compile_probe() {
    uint32_t acc = 0;

    // Boot bind + self-check.
    registry_ensure();
    acc += registry_validate() ? 1u : 0u;

    // Table walk via the public accessors.
    const EffectEntry* table = effect_registry();
    const uint16_t count = effect_registry_count();
    for (uint16_t i = 0; i < count; ++i) {
        const EffectEntry& row = table[i];
        acc += static_cast<uint32_t>(row.stable_id);
        acc += (row.effect != nullptr) ? 2u : 0u;
        acc += (row.metadata != nullptr) ? 4u : 0u;
        acc += row.enabled ? 8u : 0u;
        acc += row.director_ok ? 16u : 0u;
        acc += hasAudioDep(row.audio_deps, AudioDeps::BEAT) ? 32u : 0u;
        acc += static_cast<uint32_t>(effect_family(row.stable_id));
        acc += static_cast<uint32_t>(effect_sequence(row.stable_id));
    }

    // Lookup-by-stable-id (a legacy alias + a native row).
    const EffectEntry* bloom =
        entry_for_stable_id(static_cast<EffectId>(LIGHT_MODE_BLOOM));
    acc += (bloom != nullptr) ? 64u : 0u;
    const EffectEntry* beat = entry_for_stable_id(0x1001);
    acc += (beat != nullptr) ? 128u : 0u;
    const EffectEntry* absent = entry_for_stable_id(0xFFFE);
    acc += (absent == nullptr) ? 256u : 0u;

    // Lookup-by-legacy-ordinal (every ordinal resolves; kNoLegacy does not).
    for (uint8_t ord = 0; ord < NUM_MODES; ++ord) {
        acc += (entry_for_legacy_ordinal(ord) != nullptr) ? 512u : 0u;
    }
    acc += (entry_for_legacy_ordinal(kNoLegacy) == nullptr) ? 1024u : 0u;

    return acc;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_REGISTRY_V1
