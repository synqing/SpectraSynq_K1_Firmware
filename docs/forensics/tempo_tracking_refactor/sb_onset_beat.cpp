#include "sb_onset_beat.h"

#include <Arduino.h>
#include <math.h>

static portMUX_TYPE sb_onset_mux = portMUX_INITIALIZER_UNLOCKED;
static SBOnsetBeatEvent sb_onset_event = {};

static uint32_t sb_onset_last_ms = 0;
static uint32_t sb_last_accept_ms = 0;
static uint32_t sb_last_interval_ms = 0;
static uint32_t sb_interval_estimate_ms = 0;
static uint8_t sb_stable_intervals = 0;
static float sb_novelty_fast = 0.0f;
static float sb_novelty_slow = 0.0f;
static float sb_low_fast = 0.0f;
static float sb_low_slow = 0.0f;
static float sb_peak_fast = 0.0f;
static float sb_peak_slow = 0.0f;
static float sb_prev_novelty = 0.0f;
static float sb_prev_low_energy = 0.0f;
static float sb_prev_peak = 0.0f;
static bool sb_onset_primed = false;
static const uint32_t SB_ONSET_EVENT_WINDOW_MS = 80UL;
static const uint32_t SB_ONSET_REFRACTORY_MS = 240UL;
static const uint32_t SB_BEAT_INTERVAL_MIN_MS = 300UL;
static const uint32_t SB_BEAT_INTERVAL_MAX_MS = 1000UL;
static const uint8_t SB_INTERVAL_TOLERANCE_DIVISOR = 4U;
static const uint8_t SB_STABLE_INTERVAL_MAX = 4U;

static float sb_ob_clamp(float value, float low, float high) {
  if (!isfinite(value)) {
    return low;
  }
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}

static float sb_ob_alpha(uint32_t dt_ms, float tau_ms) {
  if (tau_ms <= 0.0f) {
    return 1.0f;
  }
  float dt = float(dt_ms);
  return sb_ob_clamp(dt / (tau_ms + dt), 0.0f, 1.0f);
}

static void sb_publish_event(const SBOnsetBeatEvent& event) {
  portENTER_CRITICAL(&sb_onset_mux);
  sb_onset_event = event;
  portEXIT_CRITICAL(&sb_onset_mux);
}

static uint32_t sb_event_age(uint32_t now_ms, uint32_t event_ms) {
  if (event_ms == 0 || now_ms < event_ms) {
    return UINT32_MAX;
  }
  return now_ms - event_ms;
}

static void sb_decay_beat_lock() {
  if (sb_stable_intervals > 0) {
    sb_stable_intervals--;
  }
  if (sb_stable_intervals == 0) {
    sb_interval_estimate_ms = 0;
    sb_last_interval_ms = 0;
  }
}

static bool sb_interval_close(uint32_t interval_ms, uint32_t reference_ms) {
  if (interval_ms == 0 || reference_ms == 0) {
    return false;
  }
  uint32_t bigger = interval_ms > reference_ms ? interval_ms : reference_ms;
  uint32_t smaller = interval_ms > reference_ms ? reference_ms : interval_ms;
  return (bigger - smaller) <= (bigger / SB_INTERVAL_TOLERANCE_DIVISOR);
}

static void sb_note_accepted_interval(uint32_t interval_ms) {
  if (interval_ms < SB_BEAT_INTERVAL_MIN_MS || interval_ms > SB_BEAT_INTERVAL_MAX_MS) {
    sb_decay_beat_lock();
    sb_stable_intervals = 0;
    return;
  }

  if (sb_interval_estimate_ms == 0) {
    sb_interval_estimate_ms = interval_ms;
    sb_last_interval_ms = interval_ms;
    return;
  }

  bool close_interval = sb_interval_close(interval_ms, sb_interval_estimate_ms);
  bool half_time_alias = sb_interval_close(interval_ms * 2UL, sb_interval_estimate_ms);
  bool double_time_alias = sb_interval_close(interval_ms, sb_interval_estimate_ms * 2UL);
  if (close_interval && !half_time_alias && !double_time_alias) {
    sb_interval_estimate_ms = (sb_interval_estimate_ms * 3UL + interval_ms) / 4UL;
    sb_last_interval_ms = interval_ms;
    if (sb_stable_intervals < SB_STABLE_INTERVAL_MAX) {
      sb_stable_intervals++;
    }
  } else {
    sb_decay_beat_lock();
    sb_stable_intervals = 0;
    sb_interval_estimate_ms = interval_ms;
    sb_last_interval_ms = interval_ms;
  }
}

void sb_onset_beat_reset() {
  sb_onset_last_ms = 0;
  sb_last_accept_ms = 0;
  sb_last_interval_ms = 0;
  sb_interval_estimate_ms = 0;
  sb_stable_intervals = 0;
  sb_novelty_fast = 0.0f;
  sb_novelty_slow = 0.0f;
  sb_low_fast = 0.0f;
  sb_low_slow = 0.0f;
  sb_peak_fast = 0.0f;
  sb_peak_slow = 0.0f;
  sb_prev_novelty = 0.0f;
  sb_prev_low_energy = 0.0f;
  sb_prev_peak = 0.0f;
  sb_onset_primed = false;
  SBOnsetBeatEvent empty = {};
  sb_publish_event(empty);
}

void sb_onset_beat_update(const SBAudioSnapshot& audio) {
  uint32_t now_ms = audio.frame_ms;
  uint32_t dt_ms = (sb_onset_last_ms == 0 || now_ms < sb_onset_last_ms) ? 0 : now_ms - sb_onset_last_ms;
  sb_onset_last_ms = now_ms;

  SBOnsetBeatEvent event = sb_onset_beat_read();
  event.event_age_ms = sb_event_age(now_ms, event.event_ms);
  bool event_active = event.event_age_ms <= SB_ONSET_EVENT_WINDOW_MS;
  if (!event_active) {
    event.onset = false;
    event.bass_onset = false;
    event.beat = false;
    event.onset_strength = 0.0f;
    event.bass_onset_strength = 0.0f;
  }

  float novelty = sb_ob_clamp(audio.novelty, 0.0f, 1.0f);
  float low_energy = sb_ob_clamp(audio.low_energy, 0.0f, 1.0f);
  float peak_scaled = sb_ob_clamp(audio.peak_scaled, 0.0f, 1.0f);

  if (!sb_onset_primed) {
    sb_novelty_fast = novelty;
    sb_novelty_slow = novelty;
    sb_low_fast = low_energy;
    sb_low_slow = low_energy;
    sb_peak_fast = peak_scaled;
    sb_peak_slow = peak_scaled;
    sb_prev_novelty = novelty;
    sb_prev_low_energy = low_energy;
    sb_prev_peak = peak_scaled;
    sb_onset_primed = true;
  }

  float novelty_attack = sb_ob_clamp(novelty - sb_novelty_slow, 0.0f, 1.0f);
  float low_attack = sb_ob_clamp(low_energy - sb_low_slow, 0.0f, 1.0f);
  float peak_attack = sb_ob_clamp(peak_scaled - sb_peak_slow, 0.0f, 1.0f);
  float novelty_rise = novelty - sb_prev_novelty;
  float low_rise = low_energy - sb_prev_low_energy;
  float peak_rise = peak_scaled - sb_prev_peak;

  float fast_alpha = sb_ob_alpha(dt_ms, 80.0f);
  float slow_alpha = sb_ob_alpha(dt_ms, 1200.0f);
  sb_novelty_fast += (novelty - sb_novelty_fast) * fast_alpha;
  sb_novelty_slow += (novelty - sb_novelty_slow) * slow_alpha;
  sb_low_fast += (low_energy - sb_low_fast) * fast_alpha;
  sb_low_slow += (low_energy - sb_low_slow) * slow_alpha;
  sb_peak_fast += (peak_scaled - sb_peak_fast) * fast_alpha;
  sb_peak_slow += (peak_scaled - sb_peak_slow) * slow_alpha;

  if (audio.silence) {
    sb_last_accept_ms = 0;
    sb_decay_beat_lock();
    sb_stable_intervals = 0;
    event.event_age_ms = sb_event_age(now_ms, event.event_ms);
    event.onset = false;
    event.bass_onset = false;
    event.beat = false;
    event.onset_strength = 0.0f;
    event.bass_onset_strength = 0.0f;
    event.beat_phase = 0.0f;
    event.beat_confidence = 0.0f;
    sb_prev_novelty = novelty;
    sb_prev_low_energy = low_energy;
    sb_prev_peak = peak_scaled;
    sb_publish_event(event);
    return;
  }

  float novelty_delta = sb_novelty_fast - sb_novelty_slow;
  float low_delta = sb_low_fast - sb_low_slow;
  float peak_delta = sb_peak_fast - sb_peak_slow;
  float novelty_strength = sb_ob_clamp(novelty_delta * 3.5f, 0.0f, 1.0f);
  float peak_strength = sb_ob_clamp(peak_delta * 2.8f, 0.0f, 1.0f);
  float onset_strength = novelty_strength > peak_strength ? novelty_strength : peak_strength;
  float bass_strength = sb_ob_clamp(low_delta * 4.0f, 0.0f, 1.0f);
  bool refractory_open = (sb_last_accept_ms == 0) || (now_ms - sb_last_accept_ms >= SB_ONSET_REFRACTORY_MS);
  bool novelty_candidate = novelty_strength > 0.14f && novelty_attack > 0.03f && novelty_rise > 0.018f;
  bool peak_candidate = peak_strength > 0.20f && peak_attack > 0.06f && peak_rise > 0.05f;
  bool bass_candidate = bass_strength > 0.16f && low_attack > 0.03f && low_rise > 0.018f;
  bool accepted = refractory_open && (novelty_candidate || peak_candidate || bass_candidate);

  if (accepted) {
    uint32_t interval_ms = (sb_last_accept_ms == 0) ? 0 : now_ms - sb_last_accept_ms;
    if (interval_ms > 0) {
      sb_note_accepted_interval(interval_ms);
    }

    sb_last_accept_ms = now_ms;
    event.event_id++;
    event.event_ms = now_ms;
    event.event_age_ms = 0;
    event.onset_strength = onset_strength;
    event.bass_onset_strength = bass_strength;
    event.onset = novelty_candidate || peak_candidate;
    event.bass_onset = bass_candidate;
    event_active = true;
  }

  if (sb_interval_estimate_ms >= SB_BEAT_INTERVAL_MIN_MS && sb_last_accept_ms > 0) {
    uint32_t age_ms = now_ms - sb_last_accept_ms;
    float phase = float(age_ms % sb_interval_estimate_ms) / float(sb_interval_estimate_ms);
    event.beat_phase = sb_ob_clamp(phase, 0.0f, 1.0f);
    event.beat_confidence = sb_ob_clamp(float(sb_stable_intervals) / 2.0f, 0.0f, 1.0f);
    if (accepted && event.beat_confidence >= 0.5f) {
      event.beat = true;
    } else if (!event_active) {
      event.beat = false;
    }
  } else {
    event.beat_phase = 0.0f;
    event.beat_confidence = 0.0f;
    if (!event_active) {
      event.beat = false;
    }
  }

  if (!accepted) {
    event.event_age_ms = sb_event_age(now_ms, event.event_ms);
  }
  sb_prev_novelty = novelty;
  sb_prev_low_energy = low_energy;
  sb_prev_peak = peak_scaled;
  sb_publish_event(event);
}

SBOnsetBeatEvent sb_onset_beat_read() {
  SBOnsetBeatEvent event;
  portENTER_CRITICAL(&sb_onset_mux);
  event = sb_onset_event;
  portEXIT_CRITICAL(&sb_onset_mux);
  return event;
}
