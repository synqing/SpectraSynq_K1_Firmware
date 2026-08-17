// Host interleave driver for K1AudioFrame. Compiled only by
// tests/test_k1_audio_frame_interleave.py — never by PlatformIO.

#include "k1_audio_frame.h"
#include "k1_audio_frame_host_shim.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern "C" K1AudioFrame* k1_audio_frame_host_shared_slot_for_test(void);

static int g_fail = 0;
static const char* g_fail_case = "";

static void fail(const char* case_name, const char* msg) {
  fprintf(stderr, "FAIL %s: %s\n", case_name, msg);
  g_fail = 1;
  g_fail_case = case_name;
}

static void stamp_frame(K1AudioFrame* f, uint32_t gen) {
  memset(f, 0, sizeof(*f));
  f->boot_epoch = 1;
  f->ap_generation = gen;
  f->capture_sequence = gen;
  f->i2s_read_return_us = 1000u + gen;
  f->newest_sample_estimate_us = 1000u + gen;
  f->oldest_sample_estimate_us = 900u + gen;
  f->sample_time_assumption_id = 1;
  f->ap_publish_us = 2000u + gen;
  f->onset_epoch = 1;
  f->onset_sequence_total = gen;
  f->last_onset_time_us = 3000u + gen;
  f->last_onset_strength = (float)gen;
  f->beat_epoch = 1;
  f->beat_sequence_total = gen;
  f->last_beat_time_us = 4000u + gen;
  f->semantic.watermark = gen;
  f->semantic.bpm = 100.0f + (float)gen;
  f->semantic.tempo_confidence = 0.5f;
  f->semantic.beat_phase01 = 0.25f;
  f->semantic.onset_strength = (float)gen * 0.1f;
  f->semantic.frame_ms = gen;
}

static int frames_equal(const K1AudioFrame* a, const K1AudioFrame* b) {
  return memcmp(a, b, sizeof(K1AudioFrame)) == 0;
}

static uint32_t payload_generation(const K1AudioFrame* f) {
  if (f->semantic.watermark != f->capture_sequence) return 0xffffffffu;
  if (f->i2s_read_return_us != 1000u + f->semantic.watermark) return 0xffffffffu;
  if (f->onset_sequence_total != f->semantic.watermark) return 0xffffffffu;
  if (f->beat_sequence_total != f->semantic.watermark) return 0xffffffffu;
  return f->semantic.watermark;
}

static int case1_consumer_during_private_build(void) {
  const char* name = "case1_consumer_during_private_build";
  k1_audio_frame_stats_reset();
  K1AudioFrame n;
  stamp_frame(&n, 5);
  k1_audio_frame_publish(n);

  K1AudioFrame building;
  stamp_frame(&building, 6);
  for (int i = 0; i < 20; i++) {
    building.last_onset_strength = (float)i;
    K1AudioFrame got;
    if (!k1_audio_frame_acquire(&got)) {
      fail(name, "acquire failed");
      return 1;
    }
    if (got.ap_generation != 5) {
      fail(name, "saw next generation during private build");
      return 1;
    }
    K1AudioFrame expect;
    stamp_frame(&expect, 5);
    if (!frames_equal(&got, &expect)) {
      fail(name, "payload mutated during private build");
      return 1;
    }
  }
  k1_audio_frame_publish(building);
  printf("PASS %s\n", name);
  return 0;
}

static uint32_t s_pause_target = 0;
static int s_pause_fired = 0;
static K1AudioFrame s_pause_sample;

static void pause_yield(void) {
  if (s_pause_fired) return;
  if (k1_af_host_segment_count() < s_pause_target) return;
  if (k1_audio_frame_acquire(&s_pause_sample)) {
    s_pause_fired = 1;
  } else {
    k1_af_host_note_acquire_wait();
  }
}

static int case2_segment_pause_complete_only(void) {
  const char* name = "case2_segment_pause_complete_only";
  K1AudioFrame oldf, newf;
  stamp_frame(&oldf, 10);
  stamp_frame(&newf, 11);

  for (uint32_t pause_after = 1; pause_after < 24; pause_after++) {
    k1_audio_frame_stats_reset();
    k1_audio_frame_publish(oldf);
    s_pause_target = pause_after;
    s_pause_fired = 0;
    memset(&s_pause_sample, 0, sizeof(s_pause_sample));
    k1_af_host_reset_segment_counter();
    k1_af_host_set_yield_every_n_segments(0);
    k1_af_host_set_yield(pause_yield);
    k1_audio_frame_publish(newf);
    k1_af_host_clear_yield();
    if (!s_pause_fired) {
      (void)k1_audio_frame_acquire(&s_pause_sample);
    }
    if (!(frames_equal(&s_pause_sample, &oldf) || frames_equal(&s_pause_sample, &newf))) {
      fail(name, "mixed frame observed");
      return 1;
    }
  }
  K1AudioFrameStats st;
  k1_audio_frame_stats(&st);
  if (st.mixed_generation_count != 0) {
    fail(name, "mixed_generation_count != 0");
    return 1;
  }
  printf("PASS %s\n", name);
  return 0;
}

static int case3_vp_local_survives_40ms_stall(void) {
  const char* name = "case3_vp_local_survives_40ms_stall";
  k1_audio_frame_stats_reset();
  K1AudioFrame n;
  stamp_frame(&n, 20);
  k1_audio_frame_publish(n);
  K1AudioFrame vp;
  if (!k1_audio_frame_acquire(&vp)) {
    fail(name, "initial acquire failed");
    return 1;
  }
  K1AudioFrame before = vp;
#if defined(MUTANT_TWO_SLOT_REUSE)
  K1AudioFrame* shared = k1_audio_frame_host_shared_slot_for_test();
  for (uint32_t g = 21; g <= 26; g++) {
    stamp_frame(&n, g);
    k1_audio_frame_publish(n);
    if (shared->ap_generation != before.ap_generation) {
      fail(name, "shared pointer mutated during stall");
      return 1;
    }
  }
#else
  for (uint32_t g = 21; g <= 26; g++) {
    stamp_frame(&n, g);
    k1_audio_frame_publish(n);
    for (int i = 0; i < 10; i++) {
      if (!frames_equal(&vp, &before) || vp.ap_generation != 20) {
        fail(name, "VP-local frame mutated during stall");
        return 1;
      }
    }
  }
  printf("PASS %s\n", name);
  return 0;
#endif
}

static int s_case4_bad = 0;
static void case4_yield(void) {
  K1AudioFrame got;
  if (!k1_audio_frame_acquire(&got)) return;
  if (payload_generation(&got) != got.ap_generation) {
    s_case4_bad = 1;
  }
}

static int case4_generation_before_payload(void) {
  const char* name = "case4_generation_before_payload";
  k1_audio_frame_stats_reset();
  K1AudioFrame oldf, newf;
  stamp_frame(&oldf, 30);
  stamp_frame(&newf, 31);
  k1_audio_frame_publish(oldf);

  s_case4_bad = 0;
  k1_af_host_reset_segment_counter();
  k1_af_host_set_yield_every_n_segments(1);
  k1_af_host_set_yield(case4_yield);
  k1_audio_frame_publish(newf);
  k1_af_host_clear_yield();

#if defined(MUTANT_EARLY_GENERATION)
  if (!s_case4_bad) {
    fail(name, "early generation mutant not observed");
    return 1;
  }
  fail(name, "generation visible before payload");
  return 1;
#else
  if (s_case4_bad) {
    fail(name, "generation/payload mismatch");
    return 1;
  }
  printf("PASS %s\n", name);
  return 0;
#endif
}

static int case5_two_events_yield_delta_two(void) {
  const char* name = "case5_two_events_yield_delta_two";
  k1_audio_frame_stats_reset();
  K1AudioFrame f;
  stamp_frame(&f, 40);
  f.onset_sequence_total = 100;
  f.beat_sequence_total = 200;
  f.semantic.watermark = 40;
  f.capture_sequence = 40;
  k1_audio_frame_publish(f);
  K1AudioFrame got;
  k1_audio_frame_acquire(&got);
  uint32_t last_onset = got.onset_sequence_total;
  uint32_t last_beat = got.beat_sequence_total;

#if defined(MUTANT_LOST_EVENT)
  stamp_frame(&f, 41);
  f.onset_sequence_total = 1;
  f.beat_sequence_total = 1;
  k1_audio_frame_publish(f);
  stamp_frame(&f, 42);
  f.onset_sequence_total = 1;
  f.beat_sequence_total = 1;
  k1_audio_frame_publish(f);
  k1_audio_frame_acquire(&got);
  fail(name, "event represented as boolean lost the first of two");
  return 1;
#else
  stamp_frame(&f, 41);
  f.onset_sequence_total = last_onset + 1;
  f.beat_sequence_total = last_beat + 1;
  k1_audio_frame_publish(f);
  stamp_frame(&f, 42);
  f.onset_sequence_total = last_onset + 2;
  f.beat_sequence_total = last_beat + 2;
  k1_audio_frame_publish(f);
  k1_audio_frame_acquire(&got);
  if ((uint32_t)(got.onset_sequence_total - last_onset) != 2 ||
      (uint32_t)(got.beat_sequence_total - last_beat) != 2) {
    fail(name, "sequence delta != 2");
    return 1;
  }
  printf("PASS %s\n", name);
  return 0;
#endif
}

static int case6_epoch_reset_no_phantom(void) {
  const char* name = "case6_epoch_reset_no_phantom";
  k1_audio_frame_stats_reset();
  K1AudioFrame f;
  stamp_frame(&f, 50);
  f.onset_sequence_total = 0xFFFFFFFEu;
  f.beat_sequence_total = 0xFFFFFFFEu;
  f.onset_epoch = 1;
  f.beat_epoch = 1;
  // Keep payload watermark coherent with generation for publish integrity.
  f.semantic.watermark = 50;
  f.capture_sequence = 50;
  k1_audio_frame_publish(f);
  K1AudioFrame got;
  k1_audio_frame_acquire(&got);
  uint32_t old_onset = got.onset_sequence_total;
  uint32_t old_beat = got.beat_sequence_total;
  uint32_t old_epoch = got.onset_epoch;

  for (uint32_t i = 0; i < 3; i++) {
    stamp_frame(&f, 51 + i);
    f.onset_epoch = 1;
    f.beat_epoch = 1;
    f.onset_sequence_total = old_onset + 1 + i;
    f.beat_sequence_total = old_beat + 1 + i;
    k1_audio_frame_publish(f);
  }
  k1_audio_frame_acquire(&got);
  if ((uint32_t)(got.onset_sequence_total - old_onset) != 3 ||
      (uint32_t)(got.beat_sequence_total - old_beat) != 3) {
    fail(name, "wrap delta != 3");
    return 1;
  }

  stamp_frame(&f, 60);
  f.onset_epoch = old_epoch + 1;
  f.beat_epoch = old_epoch + 1;
  f.onset_sequence_total = 0;
  f.beat_sequence_total = 0;
  k1_audio_frame_publish(f);
  k1_audio_frame_acquire(&got);
  if (got.onset_epoch == old_epoch) {
    fail(name, "epoch did not change");
    return 1;
  }
  uint32_t new_events =
      (got.onset_epoch != old_epoch) ? 0u : (uint32_t)(got.onset_sequence_total - old_onset);
  if (new_events != 0) {
    fail(name, "phantom burst on epoch reset");
    return 1;
  }
  printf("PASS %s\n", name);
  return 0;
}

static void case7_noise_yield(void) {
  K1AudioFrame tmp;
  (void)k1_audio_frame_acquire(&tmp);
}

static int case7_field_stamp_matches_generation(void) {
  const char* name = "case7_field_stamp_matches_generation";
  k1_audio_frame_stats_reset();
  uint32_t seed = 0xC0FFEEu;
  for (int i = 0; i < 10000; i++) {
    seed = seed * 1664525u + 1013904223u;
    uint32_t gen = 100 + (seed & 0xfffu);
    K1AudioFrame f;
    stamp_frame(&f, gen);
#if defined(MUTANT_DIRECT_GLOBAL)
    static uint32_t live_global = 0;
    live_global = gen + 7;
    f.semantic.watermark = live_global;
#endif
    k1_af_host_reset_segment_counter();
    if ((seed & 3u) == 0u) {
      k1_af_host_set_yield_every_n_segments(1 + (seed % 5u));
      k1_af_host_set_yield(case7_noise_yield);
    } else {
      k1_af_host_clear_yield();
    }
    k1_audio_frame_publish(f);
    K1AudioFrame got;
    if (!k1_audio_frame_acquire(&got)) {
      fail(name, "acquire failed");
      return 1;
    }
    if (payload_generation(&got) != got.ap_generation) {
      fail(name, "watermark mismatch");
      return 1;
    }
  }
  K1AudioFrameStats st;
  k1_audio_frame_stats(&st);
  if (st.mixed_generation_count != 0) {
    fail(name, "mixed_generation_count != 0");
    return 1;
  }
#if defined(MUTANT_DIRECT_GLOBAL)
  fail(name, "direct global read mutated stamps");
  return 1;
#else
  printf("PASS %s\n", name);
  return 0;
#endif
}

int main(int argc, char** argv) {
  const char* only = (argc > 1) ? argv[1] : "all";
  int rc = 0;
  if (strcmp(only, "all") == 0 || strcmp(only, "case1_consumer_during_private_build") == 0)
    rc |= case1_consumer_during_private_build();
  if (strcmp(only, "all") == 0 || strcmp(only, "case2_segment_pause_complete_only") == 0)
    rc |= case2_segment_pause_complete_only();
  if (strcmp(only, "all") == 0 || strcmp(only, "case3_vp_local_survives_40ms_stall") == 0)
    rc |= case3_vp_local_survives_40ms_stall();
  if (strcmp(only, "all") == 0 || strcmp(only, "case4_generation_before_payload") == 0)
    rc |= case4_generation_before_payload();
  if (strcmp(only, "all") == 0 || strcmp(only, "case5_two_events_yield_delta_two") == 0)
    rc |= case5_two_events_yield_delta_two();
  if (strcmp(only, "all") == 0 || strcmp(only, "case6_epoch_reset_no_phantom") == 0)
    rc |= case6_epoch_reset_no_phantom();
  if (strcmp(only, "all") == 0 || strcmp(only, "case7_field_stamp_matches_generation") == 0)
    rc |= case7_field_stamp_matches_generation();
  if (rc == 0) {
    printf("ALL_PASS\n");
  } else if (g_fail_case[0]) {
    printf("CAUGHT_BY %s\n", g_fail_case);
  }
  return rc;
}
