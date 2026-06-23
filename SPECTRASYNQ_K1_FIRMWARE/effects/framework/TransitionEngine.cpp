/**
 * @file TransitionEngine.cpp
 * @brief Centre-origin transition implementations (K1 P4 port).
 *
 * Single-strip, length-configurable port of firmware-v3 TransitionEngine.cpp.
 * Pixel math is transcribed verbatim from the donor with the two-strip loop
 * collapsed to one strip (m_length / m_centre) and the NUCLEAR radiation glow
 * hard-capped per the Strobe Law (kNuclearRadiationCapMax).
 *
 * Namespace: `k1::effects::framework`. British English in comments/identifiers.
 */

#include "TransitionEngine.h"

#include <Arduino.h>
#include <math.h>
#include <string.h>

#ifndef NATIVE_BUILD
#include <esp_heap_caps.h>
#endif

namespace k1 {
namespace effects {
namespace framework {

// ── Constructor / destructor ──────────────────────────────────────────────────

TransitionEngine::TransitionEngine()
    : m_active(false)
    , m_progress(0.0f)
    , m_rawProgress(0.0f)
    , m_type(TransitionType::FADE)
    , m_curve(EasingCurve::IN_OUT_QUAD)
    , m_startTime(0)
    , m_durationMs(1000)
    , m_length(0)
    , m_centre(0)
    , m_sourceBuffer(nullptr)
    , m_targetBuffer(nullptr)
    , m_outputBuffer(nullptr)
    , m_dissolveOrder(nullptr)
    , m_buffersReady(false)
    , m_activePulses(0)
    , m_irisRadius(0.0f)
    , m_shockwaveRadius(0.0f)
    , m_radiationIntensity(0.0f)
    , m_eventHorizonRadius(0.0f)
    , m_chevronAngle(0.0f)
    , m_foldCount(6)
    , m_rotationAngle(0.0f) {
    memset(m_particles, 0, sizeof(m_particles));
    memset(m_pulses, 0, sizeof(m_pulses));
    memset(m_ringPhases, 0, sizeof(m_ringPhases));
}

TransitionEngine::~TransitionEngine() {
    if (m_sourceBuffer) { free(m_sourceBuffer); m_sourceBuffer = nullptr; }
    if (m_targetBuffer) { free(m_targetBuffer); m_targetBuffer = nullptr; }
    if (m_dissolveOrder) { free(m_dissolveOrder); m_dissolveOrder = nullptr; }
}

// ── Allocation (boot only) ────────────────────────────────────────────────────

bool TransitionEngine::begin(uint16_t length) {
    if (m_buffersReady) return true;  // idempotent
    if (length == 0) return false;
    m_length = length;
    m_centre = (length > 0) ? static_cast<uint16_t>((length / 2) - 1) : 0;

#ifndef NATIVE_BUILD
    // CL-2 fail-closed: PSRAM ONLY. There is NO internal-SRAM fallback — eating
    // the thin/fragmented internal DRAM pool re-triggers the strobe-class Core-0
    // crash. If PSRAM is unavailable the buffers stay null, m_buffersReady stays
    // false, and startTransition() degrades to a hard cut (legacy/no-overlay
    // path). Fail CLOSED, never allocate internal.
    m_sourceBuffer = static_cast<CRGB*>(
        heap_caps_calloc(m_length, sizeof(CRGB), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    m_targetBuffer = static_cast<CRGB*>(
        heap_caps_calloc(m_length, sizeof(CRGB), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    m_dissolveOrder = static_cast<uint16_t*>(
        heap_caps_calloc(m_length, sizeof(uint16_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
#else
    m_sourceBuffer = static_cast<CRGB*>(calloc(m_length, sizeof(CRGB)));
    m_targetBuffer = static_cast<CRGB*>(calloc(m_length, sizeof(CRGB)));
    m_dissolveOrder = static_cast<uint16_t*>(calloc(m_length, sizeof(uint16_t)));
#endif

    m_buffersReady = (m_sourceBuffer != nullptr) &&
                     (m_targetBuffer != nullptr) &&
                     (m_dissolveOrder != nullptr);
    return m_buffersReady;
}

// ── Transition control ────────────────────────────────────────────────────────

void TransitionEngine::startTransition(const CRGB* sourceBuffer,
                                       const CRGB* targetBuffer,
                                       CRGB* outputBuffer,
                                       TransitionType type,
                                       uint16_t durationMs,
                                       EasingCurve curve) {
    if (!m_buffersReady || !m_sourceBuffer || !m_targetBuffer || !m_dissolveOrder) {
        // Degrade gracefully: hard cut to target, no transition.
        if (outputBuffer && targetBuffer && m_length > 0) {
            memcpy(outputBuffer, targetBuffer, m_length * sizeof(CRGB));
        }
        m_active = false;
        return;
    }

    // Copy BOTH frames so source/target cannot alias the caller's output.
    memcpy(m_sourceBuffer, sourceBuffer, m_length * sizeof(CRGB));
    memcpy(m_targetBuffer, targetBuffer, m_length * sizeof(CRGB));
    m_outputBuffer = outputBuffer;
    m_type = type;
    m_durationMs = durationMs;
    m_curve = curve;
    m_startTime = millis();
    m_progress = 0.0f;
    m_rawProgress = 0.0f;
    m_active = true;

    switch (type) {
        case TransitionType::DISSOLVE:     initDissolve(); break;
        case TransitionType::PULSEWAVE:    initPulsewave(); break;
        case TransitionType::IMPLOSION:    initImplosion(); break;
        case TransitionType::IRIS:         m_irisRadius = 0.0f; break;
        case TransitionType::NUCLEAR:      initNuclear(); break;
        case TransitionType::STARGATE:     initStargate(); break;
        case TransitionType::KALEIDOSCOPE: initKaleidoscope(); break;
        case TransitionType::MANDALA:      initMandala(); break;
        case TransitionType::PHASE_SHIFT:  break;  // uses progress directly
        default:                           break;
    }
}

void TransitionEngine::startTransition(const CRGB* sourceBuffer,
                                       const CRGB* targetBuffer,
                                       CRGB* outputBuffer,
                                       TransitionType type) {
    uint16_t duration = getDefaultDuration(type);
    EasingCurve curve = static_cast<EasingCurve>(getDefaultEasing(type));
    startTransition(sourceBuffer, targetBuffer, outputBuffer, type, duration, curve);
}

bool TransitionEngine::update() {
    if (!m_active) return false;

    uint32_t elapsed = millis() - m_startTime;

    if (elapsed >= m_durationMs) {
        memcpy(m_outputBuffer, m_targetBuffer, m_length * sizeof(CRGB));
        m_active = false;
        m_progress = 1.0f;
        return false;
    }

    m_rawProgress = static_cast<float>(elapsed) / static_cast<float>(m_durationMs);
    m_progress = ease(m_rawProgress, m_curve);

    switch (m_type) {
        case TransitionType::FADE:         applyFade(); break;
        case TransitionType::WIPE_OUT:     applyWipeOut(); break;
        case TransitionType::WIPE_IN:      applyWipeIn(); break;
        case TransitionType::DISSOLVE:     applyDissolve(); break;
        case TransitionType::PHASE_SHIFT:  applyPhaseShift(); break;
        case TransitionType::PULSEWAVE:    applyPulsewave(); break;
        case TransitionType::IMPLOSION:    applyImplosion(); break;
        case TransitionType::IRIS:         applyIris(); break;
        case TransitionType::NUCLEAR:      applyNuclear(); break;
        case TransitionType::STARGATE:     applyStargate(); break;
        case TransitionType::KALEIDOSCOPE: applyKaleidoscope(); break;
        case TransitionType::MANDALA:      applyMandala(); break;
        default:                           applyFade(); break;
    }
    return true;
}

void TransitionEngine::cancel() {
    if (m_active && m_outputBuffer) {
        memcpy(m_outputBuffer, m_targetBuffer, m_length * sizeof(CRGB));
    }
    m_active = false;
    m_progress = 1.0f;
}

// ── State queries ─────────────────────────────────────────────────────────────

uint32_t TransitionEngine::getElapsedMs() const {
    if (!m_active) return m_durationMs;
    return millis() - m_startTime;
}

uint32_t TransitionEngine::getRemainingMs() const {
    if (!m_active) return 0;
    uint32_t elapsed = millis() - m_startTime;
    return (elapsed >= m_durationMs) ? 0 : (m_durationMs - elapsed);
}

TransitionType TransitionEngine::getRandomTransition() {
    // SAFE default set only — never an eyes-on-pending type.
    uint8_t idx = random8(kSafeDefaultCount);
    return kSafeDefaultTransitions[idx];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

CRGB TransitionEngine::lerpColour(const CRGB& from, const CRGB& to, uint8_t blend) const {
    return ::blend(from, to, blend);  // FastLED's optimised blend
}

// ── Initialisers ──────────────────────────────────────────────────────────────

void TransitionEngine::initDissolve() {
    // Fisher-Yates shuffle of the reveal order (O(length); no allocation).
    for (uint16_t i = 0; i < m_length; i++) {
        m_dissolveOrder[i] = i;
    }
    for (uint16_t i = m_length - 1; i > 0; i--) {
        uint16_t j = random16(i + 1);
        uint16_t temp = m_dissolveOrder[i];
        m_dissolveOrder[i] = m_dissolveOrder[j];
        m_dissolveOrder[j] = temp;
    }
}

void TransitionEngine::initImplosion() {
    const uint16_t farEdge = (m_length > 30) ? (m_length - 30) : 0;
    for (uint8_t i = 0; i < MAX_PARTICLES; i++) {
        m_particles[i].active = true;
        bool leftEdge = (i % 4) < 2;
        if (leftEdge) {
            m_particles[i].position = random8(30);            // 0..29
        } else {
            m_particles[i].position = farEdge + random8(30);  // far edge band
        }
        m_particles[i].velocity = 0.5f + (random8(50) / 100.0f);
    }
}

void TransitionEngine::initPulsewave() {
    m_activePulses = 0;
    for (uint8_t i = 0; i < MAX_PULSES; i++) {
        m_pulses[i].active = false;
        m_pulses[i].radius = 0.0f;
        m_pulses[i].intensity = 0.0f;
    }
}

void TransitionEngine::initNuclear() {
    m_shockwaveRadius = 0.0f;
    m_radiationIntensity = kNuclearRadiationCapMax;  // capped from the start
}

void TransitionEngine::initStargate() {
    m_eventHorizonRadius = 0.0f;
    m_chevronAngle = 0.0f;
}

void TransitionEngine::initKaleidoscope() {
    m_foldCount = 6;
    m_rotationAngle = 0.0f;
}

void TransitionEngine::initMandala() {
    for (uint8_t i = 0; i < 5; i++) {
        m_ringPhases[i] = static_cast<float>(i) * 0.2f;
    }
}

// ── Core transitions ──────────────────────────────────────────────────────────

void TransitionEngine::applyFade() {
    // Centre-origin: fade radiates outward; centre leads, edges follow.
    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = abs((int)i - (int)m_centre) / (float)m_centre;
        float localProgress = m_progress * 2.0f - distFromCentre;
        localProgress = constrain(localProgress, 0.0f, 1.0f);
        uint8_t blend = (uint8_t)(localProgress * 255.0f);
        m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i], blend);
    }
}

void TransitionEngine::applyWipeOut() {
    // Centre-origin: expanding window reveals target centre -> edges.
    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = abs((int)i - (int)m_centre) / (float)m_centre;
        float wipeRadius = m_progress;
        float edgeWidth = 0.1f;
        float edgeStart = wipeRadius - edgeWidth;

        if (distFromCentre < edgeStart) {
            m_outputBuffer[i] = m_targetBuffer[i];
        } else if (distFromCentre < wipeRadius) {
            float blend = 1.0f - (distFromCentre - edgeStart) / edgeWidth;
            m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i],
                                           (uint8_t)(blend * 255.0f));
        } else {
            m_outputBuffer[i] = m_sourceBuffer[i];
        }
    }
}

void TransitionEngine::applyWipeIn() {
    // Centre-origin: collapsing window reveals target edges -> centre.
    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = abs((int)i - (int)m_centre) / (float)m_centre;
        float wipeRadius = 1.0f - m_progress;
        float edgeWidth = 0.1f;
        float edgeEnd = wipeRadius + edgeWidth;

        if (distFromCentre > edgeEnd) {
            m_outputBuffer[i] = m_targetBuffer[i];
        } else if (distFromCentre > wipeRadius) {
            float blend = (distFromCentre - wipeRadius) / edgeWidth;
            m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i],
                                           (uint8_t)(blend * 255.0f));
        } else {
            m_outputBuffer[i] = m_sourceBuffer[i];
        }
    }
}

void TransitionEngine::applyDissolve() {
    // Random pixel reveal: source baseline, then reveal target in shuffled order.
    uint16_t pixelsToShow = (uint16_t)(m_progress * m_length);
    memcpy(m_outputBuffer, m_sourceBuffer, m_length * sizeof(CRGB));
    for (uint16_t i = 0; i < pixelsToShow; i++) {
        uint16_t idx = m_dissolveOrder[i];
        m_outputBuffer[idx] = m_targetBuffer[idx];
    }
}

// ── Physics-based transitions ─────────────────────────────────────────────────

void TransitionEngine::applyPhaseShift() {
    // EYES-ON PENDING: standing-wave morph; per-pixel blend stays in [0,1].
    float phase = m_progress * PI * 4.0f;
    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = abs((int)i - (int)m_centre) / (float)m_centre;
        float waveFreq = 3.0f + distFromCentre * 5.0f;
        float wavePhase = phase - distFromCentre * PI * 2.0f;
        float sinMod = (sinf(wavePhase * waveFreq) + 1.0f) * 0.5f;
        float blendBase = m_progress;
        float waveInfluence = 0.3f * (1.0f - fabsf(m_progress - 0.5f) * 2.0f);
        float blend = blendBase + (sinMod - 0.5f) * waveInfluence;
        blend = constrain(blend, 0.0f, 1.0f);
        uint8_t blendByte = (uint8_t)(blend * 255.0f);
        m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i], blendByte);
    }
}

void TransitionEngine::applyPulsewave() {
    // Centre-origin: concentric rings expand outward revealing target.
    if (m_rawProgress < 0.7f) {
        float spawnThreshold = m_activePulses * 0.15f;
        if (m_rawProgress > spawnThreshold && m_activePulses < MAX_PULSES) {
            m_pulses[m_activePulses].active = true;
            m_pulses[m_activePulses].radius = 0.0f;
            m_pulses[m_activePulses].intensity = 1.0f;
            m_activePulses++;
        }
    }

    float pulseVelocity = 2.0f;
    float pulseDecay = 0.15f;
    float pulseWidth = 15.0f;

    for (uint8_t p = 0; p < MAX_PULSES; p++) {
        if (m_pulses[p].active) {
            m_pulses[p].radius += pulseVelocity * (m_progress - (p * 0.15f));
            if (m_pulses[p].radius < 0) m_pulses[p].radius = 0;
            m_pulses[p].intensity = 1.0f - (m_pulses[p].radius / (float)m_centre) * pulseDecay;
            if (m_pulses[p].intensity < 0) m_pulses[p].intensity = 0;
        }
    }

    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = (float)abs((int)i - (int)m_centre);
        float totalBlend = 0.0f;

        for (uint8_t p = 0; p < m_activePulses; p++) {
            if (!m_pulses[p].active) continue;
            float pulseRadius = m_pulses[p].radius * (float)m_centre;
            float distFromPulse = fabsf(distFromCentre - pulseRadius);
            if (distFromPulse < pulseWidth) {
                float pulseStrength = 1.0f - (distFromPulse / pulseWidth);
                pulseStrength *= pulseStrength;
                pulseStrength *= m_pulses[p].intensity;
                if (distFromCentre < pulseRadius) {
                    totalBlend = fmaxf(totalBlend, pulseStrength + (1.0f - pulseStrength) * totalBlend);
                } else {
                    totalBlend = fmaxf(totalBlend, pulseStrength * 0.5f);
                }
            }
            if (distFromCentre < pulseRadius - pulseWidth * 0.5f) {
                totalBlend = fmaxf(totalBlend, m_pulses[p].intensity);
            }
        }

        totalBlend = fmaxf(totalBlend, m_progress * m_progress);
        totalBlend = constrain(totalBlend, 0.0f, 1.0f);
        uint8_t blendByte = (uint8_t)(totalBlend * 255.0f);
        m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i], blendByte);
    }
}

void TransitionEngine::applyImplosion() {
    // Centre-origin: edge particles collapse inward; passed pixels flip to target.
    float gravity = 0.03f;
    float maxVelocity = 8.0f;

    for (uint8_t p = 0; p < MAX_PARTICLES; p++) {
        if (!m_particles[p].active) continue;
        float pos = m_particles[p].position;
        float distToCentre = fabsf(pos - (float)m_centre);
        float accel = gravity * (distToCentre / (float)m_centre + 0.5f);

        if (pos < m_centre) {
            m_particles[p].velocity += accel;
        } else {
            m_particles[p].velocity -= accel;
        }
        m_particles[p].velocity = constrain(m_particles[p].velocity, -maxVelocity, maxVelocity);

        if (pos < m_centre) {
            m_particles[p].position += m_particles[p].velocity;
        } else {
            m_particles[p].position -= fabsf(m_particles[p].velocity);
        }
        if (fabsf(m_particles[p].position - m_centre) < 3.0f) {
            m_particles[p].active = false;
        }
    }

    float furthestLeft = 0.0f;
    float furthestRight = (float)m_length - 1;
    for (uint8_t p = 0; p < MAX_PARTICLES; p++) {
        if (!m_particles[p].active) continue;
        float pos = m_particles[p].position;
        if (pos < m_centre) {
            furthestLeft = fmaxf(furthestLeft, pos);
        } else {
            furthestRight = fminf(furthestRight, pos);
        }
    }

    for (uint16_t i = 0; i < m_length; i++) {
        float blend = 0.0f;
        if (i >= (uint16_t)furthestLeft && i <= (uint16_t)furthestRight) {
            float distFromCentre = fabsf((float)i - (float)m_centre);
            float collapseProgress = 1.0f - (distFromCentre / (float)m_centre);
            blend = collapseProgress * m_progress * 2.0f;
        } else {
            blend = 1.0f;
        }

        for (uint8_t p = 0; p < MAX_PARTICLES; p++) {
            if (!m_particles[p].active) continue;
            float distToParticle = fabsf((float)i - m_particles[p].position);
            if (distToParticle < 5.0f) {
                float glow = 1.0f - (distToParticle / 5.0f);
                blend = fmaxf(blend, glow);
            }
        }

        blend = fmaxf(blend, m_progress);
        blend = constrain(blend, 0.0f, 1.0f);
        uint8_t blendByte = (uint8_t)(blend * 255.0f);
        m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i], blendByte);
    }
}

void TransitionEngine::applyIris() {
    // Centre-origin: 8-blade aperture opens from the centre.
    m_irisRadius = m_progress * (float)m_centre;
    float featherWidth = 5.0f;
    uint8_t bladeCount = 8;
    float bladeAngle = (m_progress * PI * 0.5f);

    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = fabsf((float)i - (float)m_centre);
        float normalisedPos = ((float)i / (float)m_length) * 2.0f - 1.0f;
        float angle = atan2f(normalisedPos, 0.5f) + bladeAngle;
        float bladeModulation = (sinf(angle * bladeCount) + 1.0f) * 0.5f;
        float effectiveRadius = m_irisRadius * (0.85f + bladeModulation * 0.15f);

        float blend;
        if (distFromCentre < effectiveRadius - featherWidth) {
            blend = 1.0f;
        } else if (distFromCentre < effectiveRadius) {
            blend = 1.0f - (distFromCentre - (effectiveRadius - featherWidth)) / featherWidth;
        } else {
            blend = 0.0f;
        }
        blend = fmaxf(blend, m_progress * m_progress * m_progress);
        blend = constrain(blend, 0.0f, 1.0f);
        uint8_t blendByte = (uint8_t)(blend * 255.0f);
        m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i], blendByte);
    }
}

void TransitionEngine::applyNuclear() {
    // EYES-ON PENDING + STROBE-CAPPED: shockwave from centre, radiation glow
    // hard-clamped to kNuclearRadiationCapMax so the additive white glow can
    // never read as a global full-field brightness flash.
    float shockwaveProgress = m_progress * m_progress;
    m_shockwaveRadius = shockwaveProgress * (float)m_centre * 1.3f;

    // STROBE LAW: cap the radiation bell at 0.3 (donor used full sin bell = 1.0).
    m_radiationIntensity = sinf(m_progress * PI);
    if (m_radiationIntensity > kNuclearRadiationCapMax) {
        m_radiationIntensity = kNuclearRadiationCapMax;
    }

    float shockWidth = 12.0f + m_progress * 8.0f;
    float afterglowDecay = 0.7f;

    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = fabsf((float)i - (float)m_centre);
        float blend = 0.0f;
        float radiation = 0.0f;
        float distFromShock = distFromCentre - m_shockwaveRadius;

        if (distFromShock < -shockWidth) {
            float behindDistance = fabsf(distFromShock + shockWidth);
            float afterglow = fmaxf(0.0f, 1.0f - behindDistance * afterglowDecay * 0.05f);
            radiation = afterglow * m_radiationIntensity * 0.3f;
            blend = 1.0f;
        } else if (distFromShock < shockWidth) {
            float shockPos = (distFromShock + shockWidth) / (shockWidth * 2.0f);
            radiation = (1.0f - fabsf(shockPos - 0.5f) * 2.0f) * m_radiationIntensity;
            blend = 1.0f - shockPos;
        } else {
            blend = 0.0f;
            radiation = 0.0f;
        }

        blend = fmaxf(blend, m_progress);
        blend = constrain(blend, 0.0f, 1.0f);

        CRGB colour = lerpColour(m_sourceBuffer[i], m_targetBuffer[i],
                                 (uint8_t)(blend * 255.0f));

        // Additive radiation glow (white/yellow), pre-scaled per donor.
        if (radiation > 0.01f) {
            uint8_t radByte = (uint8_t)(radiation * 200.0f * 0.65f);
            colour.r = qadd8(colour.r, radByte);
            colour.g = qadd8(colour.g, scale8(radByte, 230));
            colour.b = qadd8(colour.b, scale8(radByte, 77));
        }
        m_outputBuffer[i] = colour;
    }
}

void TransitionEngine::applyStargate() {
    // EYES-ON PENDING: portal at centre with a spatially-bounded kawoosh ring.
    float horizonTarget = (float)m_centre * 0.8f;
    if (m_progress < 0.3f) {
        float expandProgress = m_progress / 0.3f;
        m_eventHorizonRadius = horizonTarget * (1.0f + 0.3f * sinf(expandProgress * PI)) * expandProgress;
    } else if (m_progress < 0.7f) {
        m_eventHorizonRadius = horizonTarget;
    } else {
        float collapseProgress = (m_progress - 0.7f) / 0.3f;
        m_eventHorizonRadius = horizonTarget + (m_centre - horizonTarget) * collapseProgress;
    }

    m_chevronAngle += 0.15f;
    float kawooshIntensity = 0.0f;
    if (m_progress < 0.2f) {
        kawooshIntensity = sinf((m_progress / 0.2f) * PI);
    }

    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = fabsf((float)i - (float)m_centre);
        float blend = 0.0f;
        float portalGlow = 0.0f;
        float normalisedDist = distFromCentre / (float)m_centre;
        float swirlAngle = m_chevronAngle + normalisedDist * PI * 2.0f;
        float swirl = (sinf(swirlAngle * 9.0f) + 1.0f) * 0.5f;

        if (distFromCentre < m_eventHorizonRadius * 0.8f) {
            blend = 1.0f;
            portalGlow = (distFromCentre / (m_eventHorizonRadius * 0.8f)) * 0.3f;
        } else if (distFromCentre < m_eventHorizonRadius) {
            float edgePos = (distFromCentre - m_eventHorizonRadius * 0.8f) / (m_eventHorizonRadius * 0.2f);
            blend = 1.0f - edgePos;
            portalGlow = (1.0f - fabsf(edgePos - 0.5f) * 2.0f) * (0.5f + swirl * 0.5f);
        } else {
            blend = 0.0f;
            if (kawooshIntensity > 0.0f) {
                float kawooshRange = 30.0f * kawooshIntensity;
                float distFromHorizon = distFromCentre - m_eventHorizonRadius;
                if (distFromHorizon < kawooshRange) {
                    portalGlow = kawooshIntensity * (1.0f - distFromHorizon / kawooshRange);
                }
            }
        }

        blend = fmaxf(blend, m_progress * m_progress);
        blend = constrain(blend, 0.0f, 1.0f);

        CRGB colour = lerpColour(m_sourceBuffer[i], m_targetBuffer[i],
                                 (uint8_t)(blend * 255.0f));

        if (portalGlow > 0.01f) {
            uint8_t glowByte = (uint8_t)(portalGlow * 180.0f * 0.70f);
            colour.r = qadd8(colour.r, scale8(glowByte, 102));
            colour.g = qadd8(colour.g, scale8(glowByte, 179));
            colour.b = qadd8(colour.b, glowByte);
        }
        m_outputBuffer[i] = colour;
    }
}

void TransitionEngine::applyKaleidoscope() {
    // Centre-origin: fold-symmetric reveal; boundary flash is a geometric line.
    float rotationSpeed = sinf(m_progress * PI);
    m_rotationAngle += rotationSpeed * 0.1f;
    float foldAngle = (2.0f * PI) / (float)m_foldCount;

    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = fabsf((float)i - (float)m_centre);
        float normalisedDist = distFromCentre / (float)m_centre;
        float posAngle = ((float)i / (float)m_length) * PI + m_rotationAngle;
        float foldedAngle = fmodf(posAngle, foldAngle);
        if ((int)(posAngle / foldAngle) % 2 == 1) {
            foldedAngle = foldAngle - foldedAngle;
        }
        float foldProgress = foldedAngle / foldAngle;
        float edgeFactor = 1.0f - fabsf(foldProgress - 0.5f) * 2.0f;
        float distModulation = 1.0f - normalisedDist;
        float blend = m_progress * (0.5f + edgeFactor * 0.3f + distModulation * 0.2f);

        float boundaryDist = fminf(foldProgress, 1.0f - foldProgress) * foldAngle;
        if (boundaryDist < 0.1f && m_progress > 0.2f && m_progress < 0.8f) {
            blend = fminf(1.0f, blend + 0.4f);
        }

        blend = fmaxf(blend, m_progress * m_progress);
        blend = constrain(blend, 0.0f, 1.0f);
        uint8_t blendByte = (uint8_t)(blend * 255.0f);
        m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i], blendByte);
    }
}

void TransitionEngine::applyMandala() {
    // Centre-origin: staggered concentric ring phases reveal target.
    for (uint8_t r = 0; r < 5; r++) {
        float ringDelay = (float)r * 0.15f;
        float ringProgress = fmaxf(0.0f, (m_progress - ringDelay) / (1.0f - ringDelay));
        m_ringPhases[r] = ringProgress;
    }

    float ringBoundaries[6] = {0.0f, 0.15f, 0.35f, 0.55f, 0.75f, 1.0f};

    for (uint16_t i = 0; i < m_length; i++) {
        float distFromCentre = fabsf((float)i - (float)m_centre);
        float normalisedDist = distFromCentre / (float)m_centre;

        uint8_t ringIndex = 0;
        for (uint8_t r = 0; r < 5; r++) {
            if (normalisedDist >= ringBoundaries[r] && normalisedDist < ringBoundaries[r + 1]) {
                ringIndex = r;
                break;
            }
        }

        float ringStart = ringBoundaries[ringIndex];
        float ringEnd = ringBoundaries[ringIndex + 1];
        float posInRing = (normalisedDist - ringStart) / (ringEnd - ringStart);
        float ringPhase = m_ringPhases[ringIndex];

        float petalCount = 4.0f + (float)ringIndex * 2.0f;
        float petalAngle = ((float)i / (float)m_length) * PI * 2.0f;
        float petalPattern = (sinf(petalAngle * petalCount + ringPhase * PI) + 1.0f) * 0.5f;

        float patternInfluence = 0.25f * (1.0f - fabsf(ringPhase - 0.5f) * 2.0f);
        float blend = ringPhase * (1.0f - patternInfluence) + petalPattern * patternInfluence;

        float boundaryWidth = 0.08f;
        float distToInner = posInRing;
        float distToOuter = 1.0f - posInRing;
        if (distToInner < boundaryWidth && ringIndex > 0) {
            float innerBlend = m_ringPhases[ringIndex - 1];
            float t = distToInner / boundaryWidth;
            blend = blend * t + innerBlend * (1.0f - t);
        }
        if (distToOuter < boundaryWidth && ringIndex < 4) {
            float outerBlend = m_ringPhases[ringIndex + 1];
            float t = distToOuter / boundaryWidth;
            blend = blend * t + outerBlend * (1.0f - t);
        }

        blend = fmaxf(blend, m_progress * m_progress);
        blend = constrain(blend, 0.0f, 1.0f);
        uint8_t blendByte = (uint8_t)(blend * 255.0f);
        m_outputBuffer[i] = lerpColour(m_sourceBuffer[i], m_targetBuffer[i], blendByte);
    }
}

}  // namespace framework
}  // namespace effects
}  // namespace k1
