#pragma once
// ============================================================================
// beat_pulse_math.h — pure, host-testable closed-form maths for the Beat Pulse
// (Resonant) light mode. NO Arduino / FixedPoints / heap dependencies, so the
// algorithm is unit-testable on host (tests/native/test_beat_pulse_math.cpp).
//
// Faithful port of firmware-v3 BeatPulseResonantEffect (effect 0x1404) and its
// BeatPulseRenderUtils.h helpers. Two rings CONTRACT edge -> centre on each
// beat — a white ~280 ms attack snap chased by a warm ~480 ms Gaussian body.
// The only INWARD transport in the gem set. Pure closed-form of the time since
// the last beat: no trail buffer, deterministic, scalar state only.
//
// Coordinate convention: dist01 in [0,1], 0 = plate centre (LED 79/80),
// 1 = plate edge. British English throughout.
// ============================================================================

#include <cmath>
#include <cstdint>

namespace beat_pulse {

// --- Timing / geometry constants (authoritative: firmware-v3
//     BeatPulseResonantEffect.cpp lines 31-42; the .h docstring there is STALE) ---
constexpr float ATTACK_TRAVEL_MS = 280.0f;  // edge -> centre travel time, attack ring
constexpr float ATTACK_DECAY_MS  = 150.0f;  // exp decay tau (ms), attack envelope
constexpr float ATTACK_WIDTH     = 0.06f;   // hard-edge ring half-width (dist01)
constexpr float ATTACK_SOFTNESS  = 0.012f;  // hard-edge anti-alias half-width (dist01)
constexpr float ATTACK_WHITE     = 0.85f;   // white attack luminance scale
constexpr float BODY_TRAVEL_MS   = 480.0f;  // edge -> centre travel time, body ring
constexpr float BODY_DECAY_MS    = 380.0f;  // exp decay tau (ms), body envelope
constexpr float BODY_SIGMA       = 0.14f;   // Gaussian body sigma (dist01)
constexpr float FALLBACK_BPM     = 128.0f;  // metronome BPM when tempo unconfident
constexpr float TEMPO_CONF_MIN   = 0.25f;   // confidence gate for audio beats

inline float clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

// Gaussian ring profile: exp(-0.5*(distance/sigma)^2).
// (firmware-v3 RingProfile::gaussian)
inline float gaussian(float distance, float sigma) {
    const float ratio = distance / sigma;
    return std::exp(-0.5f * ratio * ratio);
}

// Hard-edged ring with soft anti-aliased boundary — a sharp pressure-wave front.
// (firmware-v3 RingProfile::hardEdge) diff = |dist01 - ringPos|.
inline float hardEdge(float diff, float width, float softness) {
    if (diff >= width + softness) return 0.0f;
    if (diff <= width - softness) return 1.0f;
    return 1.0f - (diff - (width - softness)) / (2.0f * softness);
}

// Ring position in dist01: 1 (edge) at the beat instant, sweeping to 0 (centre)
// over travelMs, then clamped at the centre. THIS is the inward transport.
inline float ringPos(float ageMs, float travelMs) {
    return 1.0f - clamp01(ageMs / travelMs);
}

// Temporal envelope: exp(-age/decay), gated by beatIntensity (0 before the first
// beat, latched to 1 thereafter — the visible decay is entirely this envelope).
inline float ringEnv(float ageMs, float decayMs, float beatIntensity) {
    return std::exp(-ageMs / decayMs) * beatIntensity;
}

// Per-LED attack (white snap) contribution in [0,1]. `travelMs` defaults to the
// constant; the effect scales it per beat (strong beat = shorter travel = faster
// inward snap) to give per-beat MOTION variation the original lacked.
inline float attackHit(float dist01, float ageMs, float beatIntensity,
                       float travelMs = ATTACK_TRAVEL_MS) {
    const float pos = ringPos(ageMs, travelMs);
    const float env = ringEnv(ageMs, ATTACK_DECAY_MS, beatIntensity);
    return hardEdge(std::fabs(dist01 - pos), ATTACK_WIDTH, ATTACK_SOFTNESS) * env;
}

// Per-LED body (warm Gaussian) contribution in [0,1]. `travelMs` per-beat scalable.
inline float bodyHit(float dist01, float ageMs, float beatIntensity,
                     float travelMs = BODY_TRAVEL_MS) {
    const float pos = ringPos(ageMs, travelMs);
    const float env = ringEnv(ageMs, BODY_DECAY_MS, beatIntensity);
    return gaussian(std::fabs(dist01 - pos), BODY_SIGMA) * env;
}

// Palette position [0,1] that travels with the body ring (firmware-v3 indexes
// the palette by floatToByte(bodyPos); here we expose the [0,1] position and let
// the fork's palette-bounded colour helper apply it — no free-running hue).
// `travelMs` matches the (per-beat scaled) body travel so colour tracks the ring.
inline float bodyPalettePos(float ageMs, float travelMs = BODY_TRAVEL_MS) {
    return ringPos(ageMs, travelMs);
}

// Beat timing with tempo-confidence gate + fallback metronome.
// (firmware-v3 BeatPulseTiming::computeBeatTick). Returns true on a beat tick and
// latches nowMs into lastBeatMs. nowMs must be an UNSCALED ms clock (millis()).
inline bool computeBeatTick(bool audioAvailable, float tempoConfidence,
                            bool audioOnBeat, uint32_t nowMs,
                            uint32_t& lastBeatMs) {
    const bool locked = audioAvailable && (tempoConfidence >= TEMPO_CONF_MIN);
    if (locked) {
        if (audioOnBeat) { lastBeatMs = nowMs; return true; }
        return false;
    }
    const float bpm = (FALLBACK_BPM < 30.0f) ? 30.0f : FALLBACK_BPM;
    const uint32_t intervalMs = static_cast<uint32_t>(60000.0f / bpm);
    if (lastBeatMs == 0 || (nowMs - lastBeatMs) >= intervalMs) {
        lastBeatMs = nowMs;
        return true;
    }
    return false;
}

} // namespace beat_pulse
