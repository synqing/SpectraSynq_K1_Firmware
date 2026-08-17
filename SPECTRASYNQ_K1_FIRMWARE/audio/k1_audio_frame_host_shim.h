#pragma once

// Host-only deterministic cooperative scheduler for K1AudioFrame interleave
// tests. Never compiled into production firmware (gated by K1_AUDIO_FRAME_HOST_TEST).

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*k1_af_yield_fn)(void);

void k1_af_host_set_yield(k1_af_yield_fn fn);
void k1_af_host_clear_yield(void);
void k1_af_host_maybe_yield(void);
void k1_af_host_set_yield_every_n_segments(uint32_t n);
void k1_af_host_reset_segment_counter(void);
uint32_t k1_af_host_segment_count(void);
void k1_af_host_lock_enter(void);
void k1_af_host_lock_exit(void);
int k1_af_host_lock_held(void);
void k1_af_host_note_acquire_wait(void);
void k1_af_host_suppress_yield(int suppress);

#ifdef __cplusplus
}
#endif

#define K1_AF_ENTER() k1_af_host_lock_enter()
#define K1_AF_EXIT() k1_af_host_lock_exit()
#define K1_AF_COPY_SEGMENT() k1_af_host_maybe_yield()
