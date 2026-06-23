/**
 * @file LegacyEffectAdapter.h
 * @brief IEffect wrapper over K1's existing light_mode_* dispatch (P3).
 *
 * Routes the K1 render path through the effect-framework `IEffect::render()`
 * virtual call WITHOUT changing on-plate output. Each adapter instance holds a
 * K1 lightshow_modes enum value and renders it by calling the SAME underlying
 * dispatch the legacy path uses (`dispatch_legacy_lightshow`), reading the
 * per-channel inputs from the EffectContext legacy-bridge fields. It is a pure
 * pass-through: flag-ON output equals flag-OFF output by construction, because
 * the identical mode body runs either way.
 *
 * Wiring contract (set by the render path each frame, before render()):
 *   - ctx.legacyChannel        = &RenderChannelState (opaque void*)
 *   - ctx.legacyMode           = resolved lightshow_modes enum
 *   - ctx.legacyHistorySeeded  = whether the seed-before-render copy already ran
 *
 * No heap: adapters are static instances in the registry (.bss). render() does
 * no allocation — it forwards to the existing zero-heap dispatch.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

#include "EffectContext.h"
#include "EffectMetadata.h"
#include "IEffect.h"

// Forward declarations of the K1 legacy render surface. Defined in
// SPECTRASYNQ_K1_FIRMWARE.ino; declared here (not included) so the framework
// header pulls in no legacy effect/render code. The adapter casts the opaque
// EffectContext::legacyChannel back to RenderChannelState* at the call site.
struct RenderChannelState;
void dispatch_legacy_lightshow(uint8_t mode, RenderChannelState& channel,
                               bool history_seeded);

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief Thin IEffect that delegates to a single K1 legacy light mode.
 *
 * Construct with the mode enum and a static metadata reference. render() pulls
 * the live channel + seed flag from the context's legacy-bridge fields and calls
 * the shared K1 dispatch. init()/cleanup() are no-ops: legacy modes keep their
 * own per-channel state in the RenderChannelState the render path owns.
 */
class LegacyEffectAdapter final : public IEffect {
public:
    LegacyEffectAdapter() = default;

    LegacyEffectAdapter(uint8_t legacyMode, const EffectMetadata& metadata)
        : m_legacyMode(legacyMode), m_metadata(metadata) {}

    /// Bind which legacy mode this adapter renders (used by the registry table).
    void configure(uint8_t legacyMode, const EffectMetadata& metadata) {
        m_legacyMode = legacyMode;
        m_metadata = metadata;
    }

    bool init(EffectContext& ctx) override {
        (void)ctx;
        return true;  // legacy modes hold state in RenderChannelState; nothing to do
    }

    void render(EffectContext& ctx) override {
        // Pure pass-through to the existing K1 dispatch. If the render path did
        // not bind a legacy channel this frame, do nothing (cannot fabricate the
        // per-channel state a legacy mode needs).
        if (ctx.legacyChannel == nullptr) return;
        RenderChannelState* channel =
            static_cast<RenderChannelState*>(ctx.legacyChannel);
        // ctx.legacyMode lets the caller override the adapter's bound mode (e.g.
        // a single shared adapter rendering the resolved per-frame mode). When
        // unset by the caller it equals m_legacyMode (the registry binds both).
        const uint8_t mode = ctx.legacyMode;
        dispatch_legacy_lightshow(mode, *channel, ctx.legacyHistorySeeded);
    }

    void cleanup() override {}

    const EffectMetadata& getMetadata() const override { return m_metadata; }

    uint8_t legacyMode() const { return m_legacyMode; }

private:
    uint8_t m_legacyMode = 0;
    EffectMetadata m_metadata{};
};

// ─── Registry ─────────────────────────────────────────────────────────────────
// A static table of LegacyEffectAdapter instances keyed by the K1 lightshow_modes
// enum. Lives in .bss (no heap). `legacy_effect_for_mode()` returns the adapter
// for a mode (or a shared fallback adapter that renders whatever mode the caller
// places in ctx.legacyMode), so the render path can dispatch any mode via IEffect.

/// Resolve the IEffect that renders the given K1 lightshow mode. Never null while
/// the framework flag is defined: the returned adapter forwards to the identical
/// legacy dispatch for that mode. The mode actually rendered is taken from
/// ctx.legacyMode at render() time (the registry keeps the two consistent).
IEffect* legacy_effect_for_mode(uint8_t mode);

}  // namespace framework
}  // namespace effects
}  // namespace k1
