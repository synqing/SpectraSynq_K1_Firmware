/**
 * @file ZoneComposer.cpp
 * @brief Implementation of the single-strip multi-zone compositor (P5).
 *
 * See ZoneComposer.h for the design contract (two-instance independent
 * dual-channel, single-strip zone model, PSRAM-at-init / zero-heap-render).
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1.
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_FRAMEWORK_V1

#include "ZoneComposer.h"

#include <cstring>          // memset / memcpy

#include <esp_heap_caps.h>  // heap_caps_malloc / MALLOC_CAP_SPIRAM

namespace k1 {
namespace effects {
namespace framework {

namespace {
/// Map a 1–100 speed knob to a per-frame time-scale factor (1.0 ≈ nominal).
/// Mirrors the v3 intent: low speed slows the effect's time, high speed quickens.
inline float computeSpeedTimeFactor(uint8_t speed) {
    if (speed < 1) speed = 1;
    if (speed > 100) speed = 100;
    // 50 → 1.0×, 1 → ~0.1×, 100 → ~2.0×. Linear about the midpoint.
    return static_cast<float>(speed) / 50.0f;
}
}  // namespace

ZoneComposer::~ZoneComposer() { deinit(); }

// ── Lifecycle ────────────────────────────────────────────────────────────────

bool ZoneComposer::init() {
    if (m_initialised) return true;

    const size_t zoneBytes =
        static_cast<size_t>(K1_ZONE_MAX_ZONES) *
        static_cast<size_t>(K1_ZONE_STRIP_LENGTH) * sizeof(CRGB);
    const size_t outBytes =
        static_cast<size_t>(K1_ZONE_STRIP_LENGTH) * sizeof(CRGB);

    // CL-2 fail-closed: PSRAM ONLY. The internal-heap (malloc) fallback is
    // REMOVED — drawing these multi-KB zone buffers from the thin internal DRAM
    // pool re-triggers the strobe-class Core-0 crash. On PSRAM failure we free
    // whatever was obtained, stay uninitialised (m_initialised == false), and the
    // composer is bypassed in favour of the single-effect legacy path.
    m_zoneBuffers = static_cast<CRGB*>(
        heap_caps_malloc(zoneBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    m_outputBuffer = static_cast<CRGB*>(
        heap_caps_malloc(outBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));

    if (m_zoneBuffers == nullptr || m_outputBuffer == nullptr) {
        // Graceful degrade: free whatever was obtained and stay uninitialised.
        deinit();
        return false;
    }

    memset(m_zoneBuffers, 0, zoneBytes);
    memset(m_outputBuffer, 0, outBytes);
    for (uint8_t z = 0; z < K1_ZONE_MAX_ZONES; ++z) {
        m_zoneTimeSeconds[z] = 0.0f;
        m_zoneFrameCount[z] = 0;
        m_zoneInited[z] = false;
    }

    m_initialised = true;
    return true;
}

void ZoneComposer::deinit() {
    if (m_zoneBuffers) { free(m_zoneBuffers); m_zoneBuffers = nullptr; }
    if (m_outputBuffer) { free(m_outputBuffer); m_outputBuffer = nullptr; }
    m_initialised = false;
}

// ── Layout ───────────────────────────────────────────────────────────────────

bool ZoneComposer::setLayout(const ZoneSegment* segments, uint8_t count) {
    if (segments == nullptr || count == 0 || count > K1_ZONE_MAX_ZONES) {
        return false;
    }
    // Quiesce the render path while we mutate the layout so Core 1 cannot read a
    // half-written segment table. Release store publishes the new layout.
    const bool wasEnabled = isEnabled();
    setEnabled(false);

    for (uint8_t z = 0; z < count; ++z) {
        m_segments[z] = segments[z];
        // Reset per-zone temporal state when geometry changes (avoid stale trails).
        m_zoneTimeSeconds[z] = 0.0f;
        m_zoneFrameCount[z] = 0;
    }
    m_zoneCount = count;

    if (wasEnabled) setEnabled(true);
    return true;
}

// ── Per-zone setters ─────────────────────────────────────────────────────────

uint8_t ZoneComposer::clampZone(uint8_t zone) const {
    return (zone < K1_ZONE_MAX_ZONES) ? zone : 0;
}

void ZoneComposer::setZoneEffect(uint8_t zone, IEffect* effect) {
    const uint8_t z = clampZone(zone);
    if (m_zones[z].effect != effect) {
        m_zones[z].effect = effect;
        m_zoneInited[z] = false;       // re-init the new effect on next render
        // Clear this zone's persistent buffer to avoid a flash of the old trail.
        if (m_zoneBuffers) {
            memset(zoneBufferFor(z), 0,
                   static_cast<size_t>(K1_ZONE_STRIP_LENGTH) * sizeof(CRGB));
        }
    }
}

void ZoneComposer::setZoneBrightness(uint8_t zone, uint8_t brightness) {
    m_zones[clampZone(zone)].brightness = brightness;
}

void ZoneComposer::setZoneSpeed(uint8_t zone, uint8_t speed) {
    if (speed < 1) speed = 1;
    if (speed > 100) speed = 100;
    m_zones[clampZone(zone)].speed = speed;
}

void ZoneComposer::setZoneBlendMode(uint8_t zone, BlendMode mode) {
    m_zones[clampZone(zone)].blendMode = mode;
}

void ZoneComposer::setZoneEnabled(uint8_t zone, bool enabled) {
    const uint8_t z = clampZone(zone);
    if (enabled && !m_zones[z].enabled && m_zoneBuffers) {
        memset(zoneBufferFor(z), 0,
               static_cast<size_t>(K1_ZONE_STRIP_LENGTH) * sizeof(CRGB));
    }
    m_zones[z].enabled = enabled;
}

IEffect* ZoneComposer::getZoneEffect(uint8_t zone) const {
    return m_zones[clampZone(zone)].effect;
}
uint8_t ZoneComposer::getZoneBrightness(uint8_t zone) const {
    return m_zones[clampZone(zone)].brightness;
}
uint8_t ZoneComposer::getZoneSpeed(uint8_t zone) const {
    return m_zones[clampZone(zone)].speed;
}
BlendMode ZoneComposer::getZoneBlendMode(uint8_t zone) const {
    return m_zones[clampZone(zone)].blendMode;
}
bool ZoneComposer::isZoneEnabled(uint8_t zone) const {
    return m_zones[clampZone(zone)].enabled;
}

// ── Render ───────────────────────────────────────────────────────────────────

void ZoneComposer::render(const EffectContext& base) {
    if (!m_initialised) return;
    if (!m_enabled.load(std::memory_order_acquire)) return;
    if (!m_strip.bound()) return;
    if (m_zoneBuffers == nullptr || m_outputBuffer == nullptr) return;

    // Clear the composited output (OVERWRITE only writes a zone's own segments;
    // gaps between zones must read black).
    memset(m_outputBuffer, 0,
           static_cast<size_t>(K1_ZONE_STRIP_LENGTH) * sizeof(CRGB));

    for (uint8_t z = 0; z < m_zoneCount; ++z) {
        if (m_zones[z].enabled && m_zones[z].effect != nullptr) {
            renderZone(z, base);
        }
    }

    // Commit composited CRGB strip → bound K1 CRGB16 strip via the converter.
    const uint16_t n = m_strip.length();
    const uint16_t limit =
        (n < K1_ZONE_STRIP_LENGTH) ? n : K1_ZONE_STRIP_LENGTH;
    for (uint16_t i = 0; i < limit; ++i) {
        m_strip.set16(i, toCrgb16(m_outputBuffer[i]));
    }
}

void ZoneComposer::renderZone(uint8_t zone, const EffectContext& base) {
    const uint8_t z = clampZone(zone);
    if (z >= m_zoneCount) return;

    ZoneState& state = m_zones[z];
    const ZoneSegment& seg = m_segments[z];
    IEffect* effect = state.effect;
    if (effect == nullptr) return;

    CRGB* zoneBuffer = zoneBufferFor(z);

    // Build this zone's context off the frame-global template. Copy carries
    // palette/gHue/audio/global params; we override the per-zone fields.
    EffectContext ctx = base;
    ctx.leds = zoneBuffer;
    ctx.ledCount = K1_ZONE_STRIP_LENGTH;
    ctx.centrePoint = K1_ZONE_STRIP_CENTRE;     // 79 — single-strip centre origin
    ctx.stripLength = K1_ZONE_STRIP_LENGTH;
    ctx.stripCentre = K1_ZONE_STRIP_CENTRE;
    // Effects render at full brightness; the compositor applies zone.brightness
    // during composition to avoid squaring brightness.
    ctx.brightness = 255;
    ctx.speed = state.speed;
    ctx.zoneId = z;
    ctx.zoneStart = seg.leftStart;
    ctx.zoneLength = seg.totalLeds;

    // Per-zone independent time: each zone advances on its own accumulator so two
    // zones at different speeds never drift into lockstep.
    const float speedFactor = computeSpeedTimeFactor(state.speed);
    const float scaledDt = base.deltaTimeSeconds * speedFactor;
    m_zoneTimeSeconds[z] += scaledDt;
    m_zoneFrameCount[z] += 1;
    ctx.deltaTimeSeconds = scaledDt;
    ctx.deltaTimeMs = static_cast<uint32_t>(scaledDt * 1000.0f + 0.5f);
    ctx.frameNumber = m_zoneFrameCount[z];
    ctx.totalTimeMs =
        static_cast<uint32_t>(m_zoneTimeSeconds[z] * 1000.0f + 0.5f);

    // One-time per-zone IEffect::init() (Core 0 normally, but safe here: a
    // framework-native effect's init() is its own concern; legacy adapters no-op).
    if (!m_zoneInited[z]) {
        effect->init(ctx);
        m_zoneInited[z] = true;
    }

    // Render the effect into the zone's persistent buffer.
    effect->render(ctx);

    // Composite this zone's left + right segments into the output buffer.
    compositeSegment(seg.leftStart, seg.leftEnd, state.brightness,
                     state.blendMode, zoneBuffer);
    compositeSegment(seg.rightStart, seg.rightEnd, state.brightness,
                     state.blendMode, zoneBuffer);
}

void ZoneComposer::compositeSegment(uint8_t start, uint8_t end,
                                    uint8_t brightness, BlendMode mode,
                                    const CRGB* zoneBuffer) {
    for (uint16_t i = start;
         i <= end && i < K1_ZONE_STRIP_LENGTH; ++i) {
        CRGB pixel = zoneBuffer[i];
        if (brightness != 255) pixel.nscale8(brightness);
        m_outputBuffer[i] = blendPixels(m_outputBuffer[i], pixel, mode);
    }
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_FRAMEWORK_V1
