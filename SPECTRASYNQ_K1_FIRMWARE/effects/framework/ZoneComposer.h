/**
 * @file ZoneComposer.h
 * @brief Single-strip multi-zone effect compositor for the K1 framework (P5).
 *
 * Ported from firmware-v3 `src/effects/zones/ZoneComposer.h`, REDESIGNED for K1's
 * independent dual-channel doctrine and K1's CRGB16 native render surface.
 *
 * ── What it does ──
 * Runs up to K1_ZONE_MAX_ZONES effects in concentric rings on ONE 160-LED strip,
 * each zone with its own IEffect, brightness, speed and blend mode. Each zone
 * renders into its own persistent scratch buffer (preserving trails / temporal
 * smoothing, no cross-zone contamination); the zone's left/right ranges are then
 * composited into the strip's output buffer with the zone's BlendMode; finally
 * the composited CRGB strip is written into the bound K1StripView (CRGB16).
 *
 * ── Two-instance independent dual-channel design (the load-bearing decision) ──
 * v3's ZoneComposer mirrors Strip 1 onto Strip 2 (identical edges). K1's primary
 * and secondary LGP edges are INDEPENDENT and usually run different effects, so a
 * single mirroring composer cannot represent K1. Resolution: instantiate TWO
 * ZoneComposer instances —
 *     ZoneComposer primaryComposer;    // bind()s the primary K1StripView
 *     ZoneComposer secondaryComposer;  // bind()s the secondary K1StripView
 * — each owning its own zone layout and per-zone effect assignments. The two
 * edges can run completely different zone compositions. This composer NEVER
 * touches the other strip; independence is structural, not a flag.
 *
 * ── Heap discipline ──
 *   - init(): allocates per-zone CRGB scratch buffers + one CRGB output buffer
 *     ONCE, preferring PSRAM (heap_caps_malloc SPIRAM), with graceful degrade to
 *     internal heap. Allocation happens only here and on the command path.
 *   - render()/composite(): ZERO heap. memset/memcpy on pre-allocated buffers and
 *     a per-zone IEffect::render() call. No new/malloc on the hot path.
 *
 * ── Effect ownership ──
 * The composer does NOT own or construct effects (no RendererActor / EffectId
 * registry dependency, unlike v3). The caller assigns an IEffect* per zone via
 * setZoneEffect(); the composer stores the pointer and calls init()/render() on
 * it. Effects are expected to be static instances (.bss) — adapters or future
 * ported effects — so there is no heap churn from effect lifetime either.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>
#include <atomic>

#include <FastLED.h>

#include "BlendMode.h"
#include "EffectContext.h"
#include "IEffect.h"
#include "K1BufferView.h"   // K1StripView (CRGB16 per-strip surface)
#include "ZoneDefinition.h"

namespace k1 {
namespace effects {
namespace framework {

/**
 * @brief Per-zone runtime parameters (effect pointer + composition controls).
 */
struct ZoneState {
    IEffect* effect = nullptr;                 ///< Effect rendered in this zone (caller-owned)
    uint8_t  brightness = 255;                 ///< Zone brightness (0–255), applied at compositing
    uint8_t  speed = 15;                       ///< Effect speed (1–100)
    BlendMode blendMode = BlendMode::OVERWRITE;///< How this zone composites over prior zones
    bool     enabled = false;                  ///< Zone enabled flag
};

/**
 * @brief Concentric multi-zone compositor over ONE K1 strip (CRGB16).
 */
class ZoneComposer {
public:
    ZoneComposer() = default;
    ~ZoneComposer();

    // ── Lifecycle ──

    /**
     * @brief Allocate the per-zone + output scratch buffers (once). Prefer PSRAM.
     * @return true on success; false if allocation failed (composer stays unbound,
     *         render() becomes a safe no-op so the channel falls back gracefully).
     */
    bool init();

    /// Free the scratch buffers. Safe to call repeatedly.
    void deinit();

    /// True once init() succeeded and buffers are live.
    bool initialised() const { return m_initialised; }

    // ── Enable (cross-core safe) ──
    // Caller is Core 0 (command path). Release/acquire ordering makes preceding
    // layout/effect writes visible to the Core 1 render() after it acquires.
    void setEnabled(bool enabled) { m_enabled.store(enabled, std::memory_order_release); }
    bool isEnabled() const { return m_enabled.load(std::memory_order_acquire); }

    // ── Strip binding (per frame, Core 1) ──
    /// Bind the K1 CRGB16 strip this composer composes into. Call each frame from
    /// the render path with this channel's live strip view.
    void bindStrip(const K1StripView& strip) { m_strip = strip; }

    // ── Layout ──
    /**
     * @brief Set the active zone layout from a segment array.
     * @return true if applied (count in [1, K1_ZONE_MAX_ZONES]).
     */
    bool setLayout(const ZoneSegment* segments, uint8_t count);
    /// Convenience: apply a built-in layout (SINGLE / DUAL / TRIPLE).
    bool setLayout(ZoneLayout layout) {
        // Qualify the free helpers — the member getZoneCount() shadows the
        // free getZoneCount(ZoneLayout) inside class scope.
        return setLayout(k1::effects::framework::getZoneConfig(layout),
                         k1::effects::framework::getZoneCount(layout));
    }
    uint8_t getZoneCount() const { return m_zoneCount; }

    // ── Per-zone setters (Core 0 command path) ──
    void setZoneEffect(uint8_t zone, IEffect* effect);
    void setZoneBrightness(uint8_t zone, uint8_t brightness);
    void setZoneSpeed(uint8_t zone, uint8_t speed);            // clamps to [1,100]
    void setZoneBlendMode(uint8_t zone, BlendMode mode);
    void setZoneEnabled(uint8_t zone, bool enabled);

    // ── Per-zone getters ──
    IEffect*  getZoneEffect(uint8_t zone) const;
    uint8_t   getZoneBrightness(uint8_t zone) const;
    uint8_t   getZoneSpeed(uint8_t zone) const;
    BlendMode getZoneBlendMode(uint8_t zone) const;
    bool      isZoneEnabled(uint8_t zone) const;

    // ── Render ──
    /**
     * @brief Render all enabled zones and composite into the bound strip.
     *
     * Pulls global animation params (palette/hue/gHue/audio/timing) from a
     * caller-supplied EffectContext template; per-zone fields (leds buffer,
     * speed, brightness, zone geometry, per-zone time) are overridden per zone.
     * ZERO heap. No-op if not initialised, not enabled, or strip unbound.
     *
     * @param base  Frame-global context (palette, gHue, audio, dt, frameNumber).
     */
    void render(const EffectContext& base);

private:
    void renderZone(uint8_t zone, const EffectContext& base);
    void compositeSegment(uint8_t start, uint8_t end, uint8_t brightness,
                          BlendMode mode, const CRGB* zoneBuffer);
    uint8_t clampZone(uint8_t zone) const;

    // Per-zone scratch buffer base (each zone gets K1_ZONE_STRIP_LENGTH CRGB).
    CRGB* zoneBufferFor(uint8_t zone) const {
        return m_zoneBuffers +
               (static_cast<size_t>(zone) * static_cast<size_t>(K1_ZONE_STRIP_LENGTH));
    }

    bool m_initialised = false;
    std::atomic<bool> m_enabled{false};
    uint8_t m_zoneCount = 0;

    ZoneSegment m_segments[K1_ZONE_MAX_ZONES] = {};
    ZoneState   m_zones[K1_ZONE_MAX_ZONES] = {};

    // The CRGB16 strip we compose into (rebound per frame). Non-owning.
    K1StripView m_strip{};

    // One-time allocations (PSRAM-preferred). Render path never allocates.
    CRGB* m_zoneBuffers = nullptr;   ///< K1_ZONE_MAX_ZONES × STRIP_LENGTH CRGB
    CRGB* m_outputBuffer = nullptr;  ///< STRIP_LENGTH CRGB composited result

    // Per-zone independent time accumulators (stable slow-motion, no drift-sync).
    float m_zoneTimeSeconds[K1_ZONE_MAX_ZONES] = {};
    uint32_t m_zoneFrameCount[K1_ZONE_MAX_ZONES] = {};
    bool m_zoneInited[K1_ZONE_MAX_ZONES] = {};  ///< IEffect::init() already run
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
