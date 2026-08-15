#include <cstdio>
#include <cstdlib>

#include "k1_mic_health.h"

static int failures = 0;

static void check(bool condition, const char* message) {
  if (!condition) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    failures++;
  }
}

static K1MicHealthFrame frame(uint32_t now_ms, uint32_t hash,
                              float rms = 2.0f, uint16_t peak = 5U,
                              bool read_ok = true) {
  K1MicHealthFrame out = {};
  out.now_ms = now_ms;
  out.buffer_hash = hash;
  out.bytes_read = read_ok ? 192U : 0U;
  out.bytes_requested = 192U;
  out.sample_count = 96U;
  out.rail_count = 0U;
  out.sample_min = -4;
  out.sample_max = 5;
  out.raw_peak_i16 = peak;
  out.raw_rms_i16 = rms;
  out.read_ok = read_ok;
  return out;
}

static void healthy_frames(K1MicHealthContext* context, uint32_t* now_ms,
                           uint32_t count, float rms = 2.0f, uint16_t peak = 5U) {
  const K1MicHealthConfig cfg = k1_mic_health_default_config();
  for (uint32_t i = 0; i < count; i++) {
    *now_ms += 8U;
    const K1MicHealthFrame f = frame(*now_ms, 0x1000U + *now_ms, rms, peak);
    k1_mic_health_model_update(context, f, cfg);
  }
}

int main() {
  const K1MicHealthConfig cfg = k1_mic_health_default_config();
  K1MicHealthContext context = {};
  uint32_t now_ms = 100U;

  k1_mic_health_model_reset(&context, 77U);
  healthy_frames(&context, &now_ms, cfg.recovery_frames);
  check(context.state == K1_MIC_HEALTH_LIVENESS_UNPROVEN,
        "healthy raw boot remains liveness-unproven until an explicit challenge");

  // A loud but static floor is not an acoustic response. Arm at the same level and
  // prove the first unchanged frame cannot self-certify liveness.
  healthy_frames(&context, &now_ms, 1U, 30.0f, 100U);
  k1_mic_health_model_begin_challenge(&context, now_ms);
  now_ms += 8U;
  k1_mic_health_model_update(&context, frame(now_ms, 0x2000U, 30.0f, 100U), cfg);
  check(context.state == K1_MIC_HEALTH_LIVENESS_UNPROVEN && !context.liveness_proven,
        "static high floor cannot pass the acoustic challenge");
  now_ms += 8U;
  k1_mic_health_model_update(&context, frame(now_ms, 0x2001U, 65.0f, 180U), cfg);
  check(context.state == K1_MIC_HEALTH_OK && context.liveness_proven,
        "known challenge response establishes OK");

  // A challenge armed on an already-loud musical frame must still be able to
  // prove liveness from the dynamic range observed across the whole window.
  k1_mic_health_model_reset(&context, 78U);
  healthy_frames(&context, &now_ms, cfg.recovery_frames, 70.0f, 180U);
  k1_mic_health_model_begin_challenge(&context, now_ms);
  now_ms += 8U;
  k1_mic_health_model_update(&context, frame(now_ms, 0x2100U, 22.0f, 70U), cfg);
  check(context.state == K1_MIC_HEALTH_OK && context.liveness_proven,
        "already-playing music establishes liveness from challenge-window span");

  healthy_frames(&context, &now_ms, 200U, 1.5f, 4U);
  check(context.state == K1_MIC_HEALTH_OK,
        "a genuinely quiet room is not a microphone fault");
  healthy_frames(&context, &now_ms, 200U, 8.0f, 20U);
  check(context.state == K1_MIC_HEALTH_OK,
        "low-level music is not a microphone fault after liveness is proven");

  now_ms += 8U;
  k1_mic_health_model_update(&context, frame(now_ms, 0x3001U, 0.0f, 0U, false), cfg);
  check(context.state == K1_MIC_HEALTH_OK,
        "one short I2S fault is rejected by the debounce");
  for (uint8_t i = 1; i < cfg.fault_debounce_frames; i++) {
    now_ms += 8U;
    k1_mic_health_model_update(&context, frame(now_ms, 0x3001U + i, 0.0f, 0U, false), cfg);
  }
  check(context.state == K1_MIC_HEALTH_STALE_I2S,
        "sustained I2S failure enters STALE_I2S");
  check(context.fault_event_count == 1U &&
        context.last_fault_state == K1_MIC_HEALTH_STALE_I2S &&
        context.last_fault_reason == K1_MIC_REASON_I2S_READ &&
        context.last_fault_frame == context.frame_count &&
        !context.last_fault_interrupted_challenge,
        "a sustained I2S failure is latched for later observation");
  const uint32_t latched_fault_frame = context.last_fault_frame;
  now_ms += 8U;
  k1_mic_health_model_update(&context, frame(now_ms, 0x3009U, 0.0f, 0U, false), cfg);
  check(context.fault_event_count == 1U &&
        context.last_fault_frame == latched_fault_frame,
        "one sustained fault episode is not counted again on every bad frame");

  healthy_frames(&context, &now_ms, cfg.recovery_frames);
  check(context.state == K1_MIC_HEALTH_LIVENESS_UNPROVEN && !context.liveness_proven,
        "raw recovery requires liveness to be re-established");
  check(context.fault_event_count == 1U &&
        context.last_fault_reason == K1_MIC_REASON_I2S_READ,
        "fault evidence survives recovery to liveness-unproven");

  k1_mic_health_model_begin_challenge(&context, now_ms);
  now_ms += 8U;
  k1_mic_health_model_update(&context, frame(now_ms, 0x4001U, 30.0f, 140U), cfg);
  check(context.state == K1_MIC_HEALTH_OK, "recovery challenge restores OK");

  context.injection = K1_MIC_INJECT_REPEATED_BUFFER;
  for (uint8_t i = 0; i < uint8_t(cfg.repeated_buffer_frames + cfg.fault_debounce_frames + 1U); i++) {
    now_ms += 8U;
    k1_mic_health_model_update(&context, frame(now_ms, 0x5001U + i, 5.0f, 12U), cfg);
  }
  check(context.state == K1_MIC_HEALTH_RAW_IMPLAUSIBLE &&
        context.reason == K1_MIC_REASON_REPEATED_BUFFER,
        "repeated buffers enter RAW_IMPLAUSIBLE");

  k1_mic_health_model_reset(&context, 88U);
  context.injection = K1_MIC_INJECT_RAIL_LOCK;
  for (uint8_t i = 0; i < cfg.fault_debounce_frames; i++) {
    now_ms += 8U;
    k1_mic_health_model_update(&context, frame(now_ms, 0x6001U + i), cfg);
  }
  check(context.state == K1_MIC_HEALTH_RAW_IMPLAUSIBLE &&
        context.reason == K1_MIC_REASON_RAIL_LOCK,
        "rail lock enters RAW_IMPLAUSIBLE");

  k1_mic_health_model_reset(&context, 99U);
  healthy_frames(&context, &now_ms, cfg.recovery_frames);
  k1_mic_health_model_begin_challenge(&context, now_ms);
  now_ms += cfg.challenge_timeout_ms + 1U;
  k1_mic_health_model_update(&context, frame(now_ms, 0x7001U, 2.0f, 5U), cfg);
  check(context.state == K1_MIC_HEALTH_NO_RESPONSE &&
        context.reason == K1_MIC_REASON_CHALLENGE_FAILED,
        "NO_RESPONSE is reachable only after an explicit failed challenge");
  check(context.fault_event_count == 1U &&
        context.last_fault_reason == K1_MIC_REASON_CHALLENGE_FAILED &&
        context.last_fault_interrupted_challenge,
        "a failed challenge is latched as a challenge-interrupting fault");

  if (failures != 0) {
    return 1;
  }
  std::puts("MIC_HEALTH_MODEL PASS");
  return 0;
}
