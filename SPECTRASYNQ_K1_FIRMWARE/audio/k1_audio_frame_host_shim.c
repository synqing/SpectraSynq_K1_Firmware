#include "k1_audio_frame_host_shim.h"

static k1_af_yield_fn s_yield = 0;
static uint32_t s_every_n = 0;
static uint32_t s_segments = 0;
static int s_lock_depth = 0;
static int s_acquire_waiting = 0;
static int s_suppress_yield = 0;
static int s_in_yield_callback = 0;

void k1_af_host_set_yield(k1_af_yield_fn fn) {
  s_yield = fn;
}

void k1_af_host_clear_yield(void) {
  s_yield = 0;
}

void k1_af_host_set_yield_every_n_segments(uint32_t n) {
  s_every_n = n;
}

void k1_af_host_reset_segment_counter(void) {
  s_segments = 0;
}

uint32_t k1_af_host_segment_count(void) {
  return s_segments;
}

void k1_af_host_lock_enter(void) {
  s_lock_depth++;
}

void k1_af_host_lock_exit(void) {
  if (s_lock_depth > 0) {
    s_lock_depth--;
  }
  if (s_lock_depth == 0 && s_acquire_waiting && s_yield && !s_in_yield_callback) {
    s_acquire_waiting = 0;
    s_in_yield_callback = 1;
    s_yield();
    s_in_yield_callback = 0;
  }
}

int k1_af_host_lock_held(void) {
  return s_lock_depth > 0;
}

void k1_af_host_note_acquire_wait(void) {
  s_acquire_waiting = 1;
}

void k1_af_host_suppress_yield(int suppress) {
  s_suppress_yield = suppress ? 1 : 0;
}

void k1_af_host_maybe_yield(void) {
  s_segments++;
  if (s_suppress_yield || s_yield == 0 || s_in_yield_callback) {
    return;
  }
  if (s_every_n == 0) {
    s_in_yield_callback = 1;
    s_yield();
    s_in_yield_callback = 0;
    return;
  }
  if ((s_segments % s_every_n) == 0) {
    s_in_yield_callback = 1;
    s_yield();
    s_in_yield_callback = 0;
  }
}
