/**
 * @file IEffect.h
 * @brief Core effect interface for the K1 effect framework.
 *
 * Self-contained spine port (P1) from firmware-v3 `src/plugins/api/IEffect.h`.
 * Direct-copy — pure interface, no v3 infrastructure dependency.
 *
 * All effects (built-in, legacy-wrapped, future plugins) implement this
 * interface. The framework calls render() each visual frame on Core 1 with an
 * EffectContext carrying all dependencies — no global variables.
 *
 * Thread-safety contract:
 *   - render() is always called from the Core 1 render task.
 *   - init() and cleanup() are called from Core 0 during effect transitions.
 *
 * PSRAM allocation policy (mandatory): effects with buffers > 64 bytes allocate
 * from PSRAM in init() and free in cleanup(); never declare large arrays as
 * class members (they land in DRAM .bss and starve the system). The render path
 * itself is zero-heap.
 *
 * Namespace: `k1::effects::framework`. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

#include "EffectContext.h"
#include "EffectMetadata.h"
#include "EffectParameter.h"

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief Core effect interface.
 */
class IEffect {
public:
    virtual ~IEffect() = default;

    // ── Lifecycle ──

    /// One-time setup (Core 0, on selection). Returns false on failure.
    virtual bool init(EffectContext& ctx) = 0;

    /// Render one frame (Core 1, hot path — no alloc, no I/O, centre-origin).
    virtual void render(EffectContext& ctx) = 0;

    /// Free resources (Core 0, on switch-away). Effect may be re-initialised.
    virtual void cleanup() = 0;

    // ── Metadata ──

    /// Return reference to a static metadata struct.
    virtual const EffectMetadata& getMetadata() const = 0;

    // ── Optional parameters (override for tunables) ──

    virtual uint8_t getParameterCount() const { return 0; }

    virtual const EffectParameter* getParameter(uint8_t index) const {
        (void)index;
        return nullptr;
    }

    virtual bool setParameter(const char* name, float value) {
        (void)name;
        (void)value;
        return false;
    }

    virtual float getParameter(const char* name) const {
        (void)name;
        return 0.0f;
    }
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
