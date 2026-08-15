#include "k1_mic_health.h"

#include <math.h>

static uint8_t k1_mic_health_sat_inc(uint8_t value) {
  return value == 0xFFU ? value : uint8_t(value + 1U);
}

static void k1_mic_health_set_fault(K1MicHealthContext* context,
                                    K1MicHealthState state,
                                    K1MicHealthReason reason) {
  // Latch fault transitions, not every frame in one sustained fault episode.
  // Otherwise the next bad frame erases whether the first transition interrupted
  // a challenge and inflates the counter into a frame counter.
  if (context->state != state || context->reason != reason) {
    context->last_fault_state = state;
    context->last_fault_reason = reason;
    context->fault_event_count++;
    context->last_fault_frame = context->frame_count;
    context->last_fault_interrupted_challenge = context->challenge_active;
  }
  context->state = state;
  context->reason = reason;
  context->liveness_proven = false;
  context->challenge_active = false;
  context->recovery_frames = 0;
}

void k1_mic_health_model_reset(K1MicHealthContext* context, uint32_t epoch) {
  *context = {};
  context->state = K1_MIC_HEALTH_UNKNOWN;
  context->reason = K1_MIC_REASON_BOOT;
  context->last_fault_state = K1_MIC_HEALTH_UNKNOWN;
  context->last_fault_reason = K1_MIC_REASON_BOOT;
  context->injection = K1_MIC_INJECT_NONE;
  context->epoch = epoch;
}

void k1_mic_health_model_begin_challenge(K1MicHealthContext* context, uint32_t now_ms) {
  context->challenge_active = true;
  context->challenge_started_ms = now_ms;
  context->challenge_baseline_peak_i16 = context->last_raw_peak_i16;
  context->challenge_min_peak_i16 = context->last_raw_peak_i16;
  context->challenge_max_peak_i16 = context->last_raw_peak_i16;
  context->challenge_baseline_rms_i16 = context->last_raw_rms_i16;
  context->challenge_min_rms_i16 = context->last_raw_rms_i16;
  context->challenge_max_rms_i16 = context->last_raw_rms_i16;
  context->liveness_proven = false;
  context->state = K1_MIC_HEALTH_LIVENESS_UNPROVEN;
  context->reason = K1_MIC_REASON_LIVENESS_UNPROVEN;
}

void k1_mic_health_model_fail_challenge(K1MicHealthContext* context) {
  if (!context->challenge_active) {
    return;
  }
  k1_mic_health_set_fault(context,
                          K1_MIC_HEALTH_NO_RESPONSE,
                          K1_MIC_REASON_CHALLENGE_FAILED);
}

void k1_mic_health_model_update(K1MicHealthContext* context,
                                const K1MicHealthFrame& source_frame,
                                const K1MicHealthConfig& config) {
  K1MicHealthFrame frame = source_frame;
  context->frame_count++;
  context->last_frame_now_ms = frame.now_ms;

  if (context->injection == K1_MIC_INJECT_STALE_I2S) {
    frame.read_ok = false;
    frame.bytes_read = 0;
  } else if (context->injection == K1_MIC_INJECT_REPEATED_BUFFER) {
    if (context->have_last_hash) {
      frame.buffer_hash = context->last_buffer_hash;
    }
  } else if (context->injection == K1_MIC_INJECT_CONSTANT_BUFFER) {
    frame.sample_max = frame.sample_min;
  } else if (context->injection == K1_MIC_INJECT_RAIL_LOCK) {
    frame.rail_count = frame.sample_count;
  }

  context->last_raw_peak_i16 = frame.raw_peak_i16;
  context->last_raw_rms_i16 = isfinite(frame.raw_rms_i16) ? frame.raw_rms_i16 : 0.0f;

  K1MicHealthState fault_state = K1_MIC_HEALTH_UNKNOWN;
  K1MicHealthReason fault_reason = K1_MIC_REASON_BOOT;

  if (!frame.read_ok) {
    fault_state = K1_MIC_HEALTH_STALE_I2S;
    fault_reason = K1_MIC_REASON_I2S_READ;
  } else if (frame.sample_count == 0 || frame.bytes_read < frame.bytes_requested) {
    fault_state = K1_MIC_HEALTH_STALE_I2S;
    fault_reason = K1_MIC_REASON_SHORT_READ;
  } else {
    if (context->have_last_hash && frame.buffer_hash == context->last_buffer_hash) {
      context->repeated_frames = k1_mic_health_sat_inc(context->repeated_frames);
    } else {
      context->repeated_frames = 0;
    }
    context->last_buffer_hash = frame.buffer_hash;
    context->have_last_hash = true;

    const bool constant_buffer = frame.sample_min == frame.sample_max;
    const bool rail_locked = uint32_t(frame.rail_count) * 100U >=
                             uint32_t(frame.sample_count) * uint32_t(config.rail_percent);
    if (context->repeated_frames >= config.repeated_buffer_frames) {
      fault_state = K1_MIC_HEALTH_RAW_IMPLAUSIBLE;
      fault_reason = K1_MIC_REASON_REPEATED_BUFFER;
    } else if (constant_buffer) {
      fault_state = K1_MIC_HEALTH_RAW_IMPLAUSIBLE;
      fault_reason = K1_MIC_REASON_CONSTANT_BUFFER;
    } else if (rail_locked) {
      fault_state = K1_MIC_HEALTH_RAW_IMPLAUSIBLE;
      fault_reason = K1_MIC_REASON_RAIL_LOCK;
    }
  }

  if (fault_state != K1_MIC_HEALTH_UNKNOWN) {
    context->fault_frames = k1_mic_health_sat_inc(context->fault_frames);
    context->recovery_frames = 0;
    if (context->fault_frames >= config.fault_debounce_frames) {
      k1_mic_health_set_fault(context, fault_state, fault_reason);
    }
    return;
  }

  context->fault_frames = 0;
  context->recovery_frames = k1_mic_health_sat_inc(context->recovery_frames);

  if (context->challenge_active) {
    // The known excitation may already be playing when the diagnostic challenge is
    // armed. Measure dynamic range across the complete challenge window rather than
    // requiring every later frame to exceed one arbitrary musical starting frame.
    // Absolute level alone still cannot pass: a static high electrical/room floor has
    // no window span.
    if (frame.raw_peak_i16 < context->challenge_min_peak_i16) {
      context->challenge_min_peak_i16 = frame.raw_peak_i16;
    }
    if (frame.raw_peak_i16 > context->challenge_max_peak_i16) {
      context->challenge_max_peak_i16 = frame.raw_peak_i16;
    }
    if (frame.raw_rms_i16 < context->challenge_min_rms_i16) {
      context->challenge_min_rms_i16 = frame.raw_rms_i16;
    }
    if (frame.raw_rms_i16 > context->challenge_max_rms_i16) {
      context->challenge_max_rms_i16 = frame.raw_rms_i16;
    }

    const bool rms_response =
        context->challenge_max_rms_i16 >= config.challenge_rms_min_i16 &&
        context->challenge_max_rms_i16 >=
            context->challenge_min_rms_i16 + config.challenge_rms_delta_i16 &&
        context->challenge_max_rms_i16 >=
            context->challenge_min_rms_i16 * config.challenge_rms_ratio;
    const float peak_min = float(context->challenge_min_peak_i16);
    const bool peak_response =
        context->challenge_max_peak_i16 >= config.challenge_peak_min_i16 &&
        uint32_t(context->challenge_max_peak_i16) >=
            uint32_t(context->challenge_min_peak_i16) + uint32_t(config.challenge_peak_delta_i16) &&
        float(context->challenge_max_peak_i16) >= peak_min * config.challenge_peak_ratio;
    const bool responded = rms_response || peak_response;
    if (responded) {
      context->challenge_active = false;
      context->liveness_proven = true;
      context->state = K1_MIC_HEALTH_OK;
      context->reason = K1_MIC_REASON_CHALLENGE_PASSED;
      return;
    }
    if (uint32_t(frame.now_ms - context->challenge_started_ms) >= config.challenge_timeout_ms) {
      k1_mic_health_set_fault(context,
                              K1_MIC_HEALTH_NO_RESPONSE,
                              K1_MIC_REASON_CHALLENGE_FAILED);
      return;
    }
  }

  if (context->liveness_proven) {
    context->state = K1_MIC_HEALTH_OK;
    return;
  }

  if (context->recovery_frames >= config.recovery_frames) {
    context->state = K1_MIC_HEALTH_LIVENESS_UNPROVEN;
    context->reason = (context->reason == K1_MIC_REASON_I2S_READ ||
                       context->reason == K1_MIC_REASON_SHORT_READ ||
                       context->reason == K1_MIC_REASON_REPEATED_BUFFER ||
                       context->reason == K1_MIC_REASON_CONSTANT_BUFFER ||
                       context->reason == K1_MIC_REASON_RAIL_LOCK)
                        ? K1_MIC_REASON_RAW_RECOVERED
                        : K1_MIC_REASON_LIVENESS_UNPROVEN;
  }
}

const char* k1_mic_health_state_name(K1MicHealthState state) {
  switch (state) {
    case K1_MIC_HEALTH_LIVENESS_UNPROVEN: return "LIVENESS_UNPROVEN";
    case K1_MIC_HEALTH_RAW_IMPLAUSIBLE: return "RAW_IMPLAUSIBLE";
    case K1_MIC_HEALTH_STALE_I2S: return "STALE_I2S";
    case K1_MIC_HEALTH_NO_RESPONSE: return "NO_RESPONSE";
    case K1_MIC_HEALTH_OK: return "OK";
    default: return "UNKNOWN";
  }
}

const char* k1_mic_health_reason_name(K1MicHealthReason reason) {
  switch (reason) {
    case K1_MIC_REASON_LIVENESS_UNPROVEN: return "LIVENESS_UNPROVEN";
    case K1_MIC_REASON_I2S_READ: return "I2S_READ";
    case K1_MIC_REASON_SHORT_READ: return "SHORT_READ";
    case K1_MIC_REASON_REPEATED_BUFFER: return "REPEATED_BUFFER";
    case K1_MIC_REASON_CONSTANT_BUFFER: return "CONSTANT_BUFFER";
    case K1_MIC_REASON_RAIL_LOCK: return "RAIL_LOCK";
    case K1_MIC_REASON_CHALLENGE_FAILED: return "CHALLENGE_FAILED";
    case K1_MIC_REASON_CHALLENGE_PASSED: return "CHALLENGE_PASSED";
    case K1_MIC_REASON_RAW_RECOVERED: return "RAW_RECOVERED";
    default: return "BOOT";
  }
}

const char* k1_mic_health_injection_name(K1MicHealthFaultInjection injection) {
  switch (injection) {
    case K1_MIC_INJECT_STALE_I2S: return "stale";
    case K1_MIC_INJECT_REPEATED_BUFFER: return "repeat";
    case K1_MIC_INJECT_CONSTANT_BUFFER: return "constant";
    case K1_MIC_INJECT_RAIL_LOCK: return "rail";
    default: return "none";
  }
}

#ifdef K1_MIC_HEALTH_V1
static K1MicHealthContext k1_mic_health_context = {};
static const K1MicHealthConfig k1_mic_health_config = k1_mic_health_default_config();

void k1_mic_health_reset(uint32_t epoch) {
  k1_mic_health_model_reset(&k1_mic_health_context, epoch);
}

void k1_mic_health_begin_challenge() {
  // The audio loop timestamps its frame before servicing serial commands. Using
  // millis() here can therefore be newer than the very next frame timestamp;
  // unsigned timeout arithmetic would interpret that ordinary ordering as a
  // multi-week timeout. Start on the health model's own last frame clock.
  k1_mic_health_model_begin_challenge(
      &k1_mic_health_context,
      k1_mic_health_context.last_frame_now_ms);
}

void k1_mic_health_fail_challenge() {
  k1_mic_health_model_fail_challenge(&k1_mic_health_context);
}

void k1_mic_health_update(const K1MicHealthFrame& frame) {
  k1_mic_health_model_update(&k1_mic_health_context, frame, k1_mic_health_config);
}

K1MicHealthContext k1_mic_health_read() {
  return k1_mic_health_context;
}

bool k1_mic_health_allows_audio() {
  return k1_mic_health_context.state == K1_MIC_HEALTH_OK;
}

bool k1_mic_health_allows_calibration() {
  return k1_mic_health_allows_audio();
}

#ifdef K1_MIC_HEALTH_FAULT_INJECT_V1
void k1_mic_health_set_fault_injection(K1MicHealthFaultInjection injection) {
  k1_mic_health_context.injection = injection;
  k1_mic_health_context.fault_frames = 0;
  k1_mic_health_context.recovery_frames = 0;
  k1_mic_health_context.repeated_frames = 0;
}
#endif
#endif
