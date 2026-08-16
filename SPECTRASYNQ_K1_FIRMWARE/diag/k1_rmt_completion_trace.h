#pragma once

// Gate-1 scheduling instrumentation only. This header intentionally exposes no
// production no-op surface: integration call sites must use the same compile
// gate, so K1 hardware builds cannot accidentally depend on trace behaviour.
#ifdef K1_SCHEDULING_TRACE_V1

#include <stddef.h>
#include <stdint.h>

enum : uint8_t {
  K1_RMT_TRACE_PRIMARY_CHANNEL = 0,
  K1_RMT_TRACE_SECONDARY_CHANNEL = 1,
  K1_RMT_TRACE_CHANNEL_COUNT = 2,
};

enum : uint32_t {
  K1_RMT_TRACE_RECORD_CONFIRMED = 1UL << 0,
};

struct K1RmtCompletionTraceRecord {
  uint32_t boot_epoch;
  uint32_t vp_frame_sequence;
  uint32_t final_bytes_crc;
  uint32_t submit_sequence;
  uint32_t channel_index;
  int32_t gpio_num;
  int64_t rmt_submit_us;
  int64_t rmt_complete_us;
  uint32_t payload_bytes;
  uint32_t num_symbols;
  uint32_t flags;
  // The producer writes this commit sequence after every field above.
  uint32_t sequence;
};

struct K1RmtCompletionTraceChannelSnapshot {
  int32_t expected_gpio_num;
  uint32_t recognised;
  uint32_t callback_registered;
  uint32_t transfer_active;
  uint32_t pending_available;
  uint32_t pending_sequence;
  uint32_t submit_sequence;
  uint32_t completion_sequence;
  uint32_t reaped_sequence;
  uint32_t accepted_submit_count;
  uint32_t confirmed_completion_count;
  uint32_t pending_drop_count;
  uint32_t pending_overwrite_count;
  uint32_t unmatched_submit_count;
  uint32_t inflight_overwrite_count;
  uint32_t transmit_error_count;
  uint32_t wait_timeout_count;
  uint32_t wait_error_count;
  uint32_t completion_overwrite_count;
  uint32_t unmatched_completion_count;
  uint32_t stale_epoch_completion_count;
  uint32_t reap_drop_count;
  uint32_t corrupt_record_count;
  uint32_t trace_drop_count;
};

struct K1RmtCompletionTraceSnapshot {
  uint32_t boot_epoch;
  uint32_t reset_count;
  uint32_t capture_armed;
  uint32_t exactly_two_channels_ready;
  uint32_t capture_valid;
  uint32_t completion_ring_capacity_per_channel;
  uint32_t wait_timeout_ms;
  uint32_t duplicate_channel_count;
  uint32_t callback_registration_error_count;
  uint32_t reset_while_active_count;
  uint32_t stop_blocked_count;
  uint32_t epoch_mismatch_count;
  uint32_t not_ready_count;
  K1RmtCompletionTraceChannelSnapshot channels[K1_RMT_TRACE_CHANNEL_COUNT];
};

struct K1RmtCompletionTraceWaitReport {
  uint32_t timeout_ms;
  uint32_t attempted_mask;
  uint32_t completed_mask;
  uint32_t timeout_mask;
  uint32_t error_mask;
  int32_t driver_status[K1_RMT_TRACE_CHANNEL_COUNT];
};

// Reset capture state for a new non-zero boot epoch. This is bounded and must
// be called only while the render owner is stopped or before it starts.
bool k1_rmt_completion_trace_reset(uint32_t boot_epoch);

// True only after the exact two compile-time K1 LED GPIO channels have been
// recognised, both official callbacks registered, and no trace fault latched.
bool k1_rmt_completion_trace_ready(void);

// Disarm only after both transfers have completed and both pending identities
// were consumed. Returns false without disarming if capture is still active.
bool k1_rmt_completion_trace_stop(void);

// Fixed internal-RAM completion capacity per channel. Any overflow is counted,
// latches capture invalid, and is therefore never silently accepted.
uint32_t k1_rmt_completion_trace_ring_capacity(void);

// Geometry-derived finite timeout used by wait_previous().
uint32_t k1_rmt_completion_trace_wait_timeout_ms(void);

// Core-1 lifetime barrier. Call before the next FastLED buffer load. It waits
// only for transfers still known active and never passes an infinite timeout.
bool k1_rmt_completion_trace_wait_previous(
    K1RmtCompletionTraceWaitReport* report);

// Publish immutable identity for the next primary and secondary submissions.
// Call after wait_previous() and before FastLED loads the next frame. The
// wrapper derives final_bytes_crc from the actual payload passed to ESP-IDF;
// callers cannot supply or fabricate that identity.
bool k1_rmt_completion_trace_set_pending_frame(
    uint32_t boot_epoch,
    uint32_t vp_frame_sequence);

// Deferred, allocation-free readers. No serial/log formatting occurs here.
bool k1_rmt_completion_trace_snapshot(K1RmtCompletionTraceSnapshot* snapshot);
size_t k1_rmt_completion_trace_reap_completions(
    uint8_t channel_index,
    K1RmtCompletionTraceRecord* records,
    size_t record_capacity);

#endif  // K1_SCHEDULING_TRACE_V1
