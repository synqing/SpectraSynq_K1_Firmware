// Gate-1 trace-only RMT completion and payload-lifetime instrumentation.
// Keep the gate before all target headers so non-trace environments compile an
// empty translation unit even if this file is accidentally selected.
#ifdef K1_SCHEDULING_TRACE_V1

#include "k1_rmt_completion_trace.h"

#include <driver/rmt_tx.h>
#include <esp_attr.h>
#include <esp_crc.h>
#include <esp_timer.h>

#ifdef K1_RMT_COMPLETION_TRACE_HOST_TEST
// Host-only deterministic record-core harness. Target builds always derive
// GPIOs and geometry from the firmware's compile-time K1 constants below.
static constexpr int32_t K1_RMT_EXPECTED_PRIMARY_GPIO = 6;
static constexpr int32_t K1_RMT_EXPECTED_SECONDARY_GPIO = 7;
static constexpr uint32_t K1_RMT_PRIMARY_LED_COUNT = 160;
static constexpr uint32_t K1_RMT_SECONDARY_LED_COUNT = 160;
#else
#include "../system/constants.h"
static constexpr int32_t K1_RMT_EXPECTED_PRIMARY_GPIO = LED_DATA_PIN;
static constexpr int32_t K1_RMT_EXPECTED_SECONDARY_GPIO = LED_CLOCK_PIN;
static constexpr uint32_t K1_RMT_PRIMARY_LED_COUNT = LED_COUNT_VALUE;
static constexpr uint32_t K1_RMT_SECONDARY_LED_COUNT = SECONDARY_LED_COUNT_VALUE;
#endif

static_assert(K1_RMT_EXPECTED_PRIMARY_GPIO >= 0,
              "K1 scheduling trace requires a physical primary LED GPIO");
static_assert(K1_RMT_EXPECTED_SECONDARY_GPIO >= 0,
              "K1 scheduling trace requires a physical secondary LED GPIO");
static_assert(K1_RMT_EXPECTED_PRIMARY_GPIO != K1_RMT_EXPECTED_SECONDARY_GPIO,
              "K1 scheduling trace requires two distinct LED GPIOs");
static_assert(K1_RMT_PRIMARY_LED_COUNT > 0 && K1_RMT_SECONDARY_LED_COUNT > 0,
              "K1 scheduling trace requires non-zero LED geometry");

namespace {

constexpr uint32_t K1_RMT_TRACE_RING_CAPACITY = 64;
constexpr uint32_t K1_WS2812_RGB_WIRE_US_PER_PIXEL = 30;
constexpr uint32_t K1_FASTLED_RMT_RESET_US = 280;
constexpr uint32_t K1_RMT_COMPLETION_MARGIN_US = 500;
constexpr uint32_t K1_RMT_MAX_LED_COUNT =
    (K1_RMT_PRIMARY_LED_COUNT > K1_RMT_SECONDARY_LED_COUNT)
        ? K1_RMT_PRIMARY_LED_COUNT
        : K1_RMT_SECONDARY_LED_COUNT;
constexpr uint32_t K1_RMT_WIRE_TIME_US =
    (K1_RMT_MAX_LED_COUNT * K1_WS2812_RGB_WIRE_US_PER_PIXEL) +
    K1_FASTLED_RMT_RESET_US;
constexpr uint32_t K1_RMT_WAIT_TIMEOUT_MS =
    (K1_RMT_WIRE_TIME_US + K1_RMT_COMPLETION_MARGIN_US + 999U) / 1000U;

static_assert(K1_RMT_WAIT_TIMEOUT_MS > 0 && K1_RMT_WAIT_TIMEOUT_MS < 100,
              "RMT completion wait must remain finite and geometry-bounded");

struct K1RmtPendingRecord {
  volatile uint32_t boot_epoch;
  volatile uint32_t vp_frame_sequence;
  volatile uint32_t sequence;
};

struct K1RmtActiveRecord {
  volatile uint32_t boot_epoch;
  volatile uint32_t vp_frame_sequence;
  volatile uint32_t final_bytes_crc;
  volatile uint32_t submit_sequence;
  volatile int64_t rmt_submit_us;
  volatile uint32_t payload_bytes;
  volatile uint32_t traced;
  volatile uint32_t mapping_valid;
  volatile uint32_t sequence;
};

struct K1RmtCompletionSlot {
  volatile uint32_t boot_epoch;
  volatile uint32_t vp_frame_sequence;
  volatile uint32_t final_bytes_crc;
  volatile uint32_t submit_sequence;
  volatile uint32_t channel_index;
  volatile int32_t gpio_num;
  volatile int64_t rmt_submit_us;
  volatile int64_t rmt_complete_us;
  volatile uint32_t payload_bytes;
  volatile uint32_t num_symbols;
  volatile uint32_t flags;
  volatile uint32_t sequence;
};

struct K1RmtChannelState {
  rmt_channel_handle_t handle;
  int32_t expected_gpio_num;
  uint32_t channel_index;
  volatile uint32_t recognised;
  volatile uint32_t callback_registered;
  volatile uint32_t transfer_active;
  K1RmtPendingRecord pending;
  volatile uint32_t pending_consumed_sequence;
  K1RmtActiveRecord active;
  K1RmtCompletionSlot completions[K1_RMT_TRACE_RING_CAPACITY];
  volatile uint32_t submit_sequence;
  volatile uint32_t completion_sequence;
  volatile uint32_t reaped_sequence;
  volatile uint32_t accepted_submit_count;
  volatile uint32_t confirmed_completion_count;
  volatile uint32_t pending_drop_count;
  volatile uint32_t pending_overwrite_count;
  volatile uint32_t unmatched_submit_count;
  volatile uint32_t inflight_overwrite_count;
  volatile uint32_t transmit_error_count;
  volatile uint32_t wait_timeout_count;
  volatile uint32_t wait_error_count;
  volatile uint32_t completion_overwrite_count;
  volatile uint32_t unmatched_completion_count;
  volatile uint32_t stale_epoch_completion_count;
  volatile uint32_t reap_drop_count;
  volatile uint32_t corrupt_record_count;
  volatile uint32_t trace_drop_count;
};

// All callback state, pending identities and completion slots are fixed-size
// BSS in internal data RAM. Nothing is allocated when rendering or in the ISR.
static DRAM_ATTR K1RmtChannelState s_channels[K1_RMT_TRACE_CHANNEL_COUNT] = {
    {nullptr, K1_RMT_EXPECTED_PRIMARY_GPIO, K1_RMT_TRACE_PRIMARY_CHANNEL},
    {nullptr, K1_RMT_EXPECTED_SECONDARY_GPIO,
     K1_RMT_TRACE_SECONDARY_CHANNEL},
};

static DRAM_ATTR volatile uint32_t s_boot_epoch = 0;
static DRAM_ATTR volatile uint32_t s_reset_count = 0;
static DRAM_ATTR volatile uint32_t s_capture_armed = 0;
static DRAM_ATTR volatile uint32_t s_structural_failure = 0;
static DRAM_ATTR volatile uint32_t s_capture_failure = 0;
static DRAM_ATTR volatile uint32_t s_duplicate_channel_count = 0;
static DRAM_ATTR volatile uint32_t s_callback_registration_error_count = 0;
static DRAM_ATTR volatile uint32_t s_reset_while_active_count = 0;
static DRAM_ATTR volatile uint32_t s_stop_blocked_count = 0;
static DRAM_ATTR volatile uint32_t s_epoch_mismatch_count = 0;
static DRAM_ATTR volatile uint32_t s_not_ready_count = 0;

static inline void IRAM_ATTR k1_rmt_trace_memory_barrier() {
#if defined(__XTENSA__)
  __asm__ __volatile__("memw" ::: "memory");
#else
  __atomic_thread_fence(__ATOMIC_SEQ_CST);
#endif
}

static uint32_t IRAM_ATTR k1_rmt_next_sequence(uint32_t sequence) {
  sequence++;
  return (sequence == 0) ? 1U : sequence;
}

static int k1_rmt_channel_for_gpio(int32_t gpio_num) {
  if (gpio_num == K1_RMT_EXPECTED_PRIMARY_GPIO) {
    return K1_RMT_TRACE_PRIMARY_CHANNEL;
  }
  if (gpio_num == K1_RMT_EXPECTED_SECONDARY_GPIO) {
    return K1_RMT_TRACE_SECONDARY_CHANNEL;
  }
  return -1;
}

static int k1_rmt_channel_for_handle(rmt_channel_handle_t handle) {
  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    if (s_channels[i].recognised != 0 && s_channels[i].handle == handle) {
      return static_cast<int>(i);
    }
  }
  return -1;
}

static bool k1_rmt_exact_channels_registered() {
  if (s_structural_failure != 0) {
    return false;
  }
  const K1RmtChannelState& primary = s_channels[K1_RMT_TRACE_PRIMARY_CHANNEL];
  const K1RmtChannelState& secondary = s_channels[K1_RMT_TRACE_SECONDARY_CHANNEL];
  return primary.recognised != 0 && secondary.recognised != 0 &&
         primary.callback_registered != 0 &&
         secondary.callback_registered != 0 && primary.handle != nullptr &&
         secondary.handle != nullptr && primary.handle != secondary.handle;
}

static void k1_rmt_clear_capture_channel(K1RmtChannelState& state) {
  state.transfer_active = 0;
  state.pending.sequence = 0;
  state.pending_consumed_sequence = 0;
  state.active.sequence = 0;
  state.submit_sequence = 0;
  state.completion_sequence = 0;
  state.reaped_sequence = 0;
  state.accepted_submit_count = 0;
  state.confirmed_completion_count = 0;
  state.pending_drop_count = 0;
  state.pending_overwrite_count = 0;
  state.unmatched_submit_count = 0;
  state.inflight_overwrite_count = 0;
  state.transmit_error_count = 0;
  state.wait_timeout_count = 0;
  state.wait_error_count = 0;
  state.completion_overwrite_count = 0;
  state.unmatched_completion_count = 0;
  state.stale_epoch_completion_count = 0;
  state.reap_drop_count = 0;
  state.corrupt_record_count = 0;
  state.trace_drop_count = 0;
  for (uint32_t i = 0; i < K1_RMT_TRACE_RING_CAPACITY; i++) {
    state.completions[i].sequence = 0;
  }
}

static bool IRAM_ATTR k1_rmt_on_trans_done(
    rmt_channel_handle_t tx_channel,
    const rmt_tx_done_event_data_t* event_data,
    void* user_context) {
  K1RmtChannelState* state = static_cast<K1RmtChannelState*>(user_context);
  if (state == nullptr || state->handle != tx_channel) {
    if (state != nullptr) {
      state->unmatched_completion_count++;
      state->trace_drop_count++;
    }
    s_capture_failure = 1;
    return false;
  }

  const uint32_t active_sequence = state->active.sequence;
  k1_rmt_trace_memory_barrier();
  const uint32_t traced = state->active.traced;
  const uint32_t mapping_valid = state->active.mapping_valid;
  const uint32_t boot_epoch = state->active.boot_epoch;
  const uint32_t vp_frame_sequence = state->active.vp_frame_sequence;
  const uint32_t final_bytes_crc = state->active.final_bytes_crc;
  const uint32_t submit_sequence = state->active.submit_sequence;
  const int64_t rmt_submit_us = state->active.rmt_submit_us;
  const uint32_t payload_bytes = state->active.payload_bytes;
  k1_rmt_trace_memory_barrier();
  const uint32_t checked_active_sequence = state->active.sequence;

  if (active_sequence == 0 || active_sequence != checked_active_sequence ||
      state->transfer_active == 0) {
    if (s_capture_armed != 0) {
      state->unmatched_completion_count++;
      state->trace_drop_count++;
      s_capture_failure = 1;
    }
    return false;
  }

  if (traced != 0 && mapping_valid != 0) {
    if (boot_epoch != s_boot_epoch) {
      state->stale_epoch_completion_count++;
      state->trace_drop_count++;
      s_capture_failure = 1;
    } else {
      const uint32_t next_sequence =
          k1_rmt_next_sequence(state->completion_sequence);
      const uint32_t outstanding =
          state->completion_sequence - state->reaped_sequence;
      if (outstanding >= K1_RMT_TRACE_RING_CAPACITY) {
        state->completion_overwrite_count++;
        state->trace_drop_count++;
        s_capture_failure = 1;
      }

      K1RmtCompletionSlot& slot =
          state->completions[(next_sequence - 1U) % K1_RMT_TRACE_RING_CAPACITY];
      slot.sequence = 0;
      slot.boot_epoch = boot_epoch;
      slot.vp_frame_sequence = vp_frame_sequence;
      slot.final_bytes_crc = final_bytes_crc;
      slot.submit_sequence = submit_sequence;
      slot.channel_index = state->channel_index;
      slot.gpio_num = state->expected_gpio_num;
      slot.rmt_submit_us = rmt_submit_us;
      slot.rmt_complete_us = esp_timer_get_time();
      slot.payload_bytes = payload_bytes;
      slot.num_symbols = (event_data != nullptr)
                             ? static_cast<uint32_t>(event_data->num_symbols)
                             : 0U;
      slot.flags = K1_RMT_TRACE_RECORD_CONFIRMED;
      k1_rmt_trace_memory_barrier();
      slot.sequence = next_sequence;
      k1_rmt_trace_memory_barrier();
      state->completion_sequence = next_sequence;
      state->confirmed_completion_count++;
    }
  } else if (traced != 0) {
    state->unmatched_completion_count++;
    state->trace_drop_count++;
    s_capture_failure = 1;
  }

  state->transfer_active = 0;
  k1_rmt_trace_memory_barrier();
  state->active.sequence = 0;
  return false;  // Never request a task wake from the RMT ISR.
}

static bool k1_rmt_prepare_active(K1RmtChannelState& state,
                                  const void* payload,
                                  size_t payload_bytes) {
  const bool traced = s_capture_armed != 0;
  bool mapping_valid = false;

  if (state.transfer_active != 0 || state.active.sequence != 0) {
    state.inflight_overwrite_count++;
    state.trace_drop_count++;
    s_capture_failure = 1;
    return false;
  }

  const uint32_t pending_sequence = state.pending.sequence;
  uint32_t pending_boot_epoch = s_boot_epoch;
  uint32_t pending_vp_frame_sequence = 0;
  if (traced) {
    if (pending_sequence == 0 ||
        pending_sequence == state.pending_consumed_sequence) {
      state.unmatched_submit_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
    } else {
      k1_rmt_trace_memory_barrier();
      pending_boot_epoch = state.pending.boot_epoch;
      pending_vp_frame_sequence = state.pending.vp_frame_sequence;
      k1_rmt_trace_memory_barrier();
      const uint32_t check_sequence = state.pending.sequence;
      if (check_sequence == pending_sequence) {
        mapping_valid = true;
      } else {
        state.unmatched_submit_count++;
        state.trace_drop_count++;
        s_capture_failure = 1;
      }
    }
    if (mapping_valid && (payload == nullptr || payload_bytes == 0)) {
      state.unmatched_submit_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
      mapping_valid = false;
    }
  }

  // This is the authoritative final-byte seam: FastLED has already applied
  // scaling/dithering and passes its private 3*LED_COUNT byte payload to IDF.
  // Hash it synchronously before the asynchronous driver can consume/reuse it.
  const uint32_t final_bytes_crc =
      mapping_valid
          ? esp_crc32_le(0, static_cast<const uint8_t*>(payload), payload_bytes)
          : 0U;

  const uint32_t submit_sequence =
      k1_rmt_next_sequence(state.submit_sequence);
  state.active.sequence = 0;
  state.active.boot_epoch = mapping_valid ? pending_boot_epoch : s_boot_epoch;
  state.active.vp_frame_sequence =
      mapping_valid ? pending_vp_frame_sequence : 0U;
  state.active.final_bytes_crc = final_bytes_crc;
  state.active.submit_sequence = submit_sequence;
  state.active.payload_bytes = static_cast<uint32_t>(payload_bytes);
  state.active.traced = traced ? 1U : 0U;
  state.active.mapping_valid = mapping_valid ? 1U : 0U;
  state.active.rmt_submit_us = esp_timer_get_time();
  state.transfer_active = 1;
  k1_rmt_trace_memory_barrier();
  state.active.sequence = submit_sequence;
  state.submit_sequence = submit_sequence;
  if (mapping_valid) {
    state.pending_consumed_sequence = pending_sequence;
  }
  return true;
}

static void k1_rmt_copy_channel_snapshot(
    const K1RmtChannelState& state,
    K1RmtCompletionTraceChannelSnapshot& snapshot) {
  snapshot.expected_gpio_num = state.expected_gpio_num;
  snapshot.recognised = state.recognised;
  snapshot.callback_registered = state.callback_registered;
  snapshot.transfer_active = state.transfer_active;
  snapshot.pending_available =
      (state.pending.sequence != 0 &&
       state.pending.sequence != state.pending_consumed_sequence)
          ? 1U
          : 0U;
  snapshot.pending_sequence = state.pending.sequence;
  snapshot.submit_sequence = state.submit_sequence;
  snapshot.completion_sequence = state.completion_sequence;
  snapshot.reaped_sequence = state.reaped_sequence;
  snapshot.accepted_submit_count = state.accepted_submit_count;
  snapshot.confirmed_completion_count = state.confirmed_completion_count;
  snapshot.pending_drop_count = state.pending_drop_count;
  snapshot.pending_overwrite_count = state.pending_overwrite_count;
  snapshot.unmatched_submit_count = state.unmatched_submit_count;
  snapshot.inflight_overwrite_count = state.inflight_overwrite_count;
  snapshot.transmit_error_count = state.transmit_error_count;
  snapshot.wait_timeout_count = state.wait_timeout_count;
  snapshot.wait_error_count = state.wait_error_count;
  snapshot.completion_overwrite_count = state.completion_overwrite_count;
  snapshot.unmatched_completion_count = state.unmatched_completion_count;
  snapshot.stale_epoch_completion_count = state.stale_epoch_completion_count;
  snapshot.reap_drop_count = state.reap_drop_count;
  snapshot.corrupt_record_count = state.corrupt_record_count;
  snapshot.trace_drop_count = state.trace_drop_count;
}

}  // namespace

extern "C" esp_err_t __real_rmt_new_tx_channel(
    const rmt_tx_channel_config_t* config,
    rmt_channel_handle_t* returned_channel);
extern "C" esp_err_t __real_rmt_transmit(
    rmt_channel_handle_t tx_channel,
    rmt_encoder_handle_t encoder,
    const void* payload,
    size_t payload_bytes,
    const rmt_transmit_config_t* config);

extern "C" esp_err_t __wrap_rmt_new_tx_channel(
    const rmt_tx_channel_config_t* config,
    rmt_channel_handle_t* returned_channel) {
  const esp_err_t result = __real_rmt_new_tx_channel(config, returned_channel);
  if (result != ESP_OK || config == nullptr || returned_channel == nullptr) {
    return result;
  }

  rmt_channel_handle_t handle = *returned_channel;
  const int channel_index = k1_rmt_channel_for_gpio(config->gpio_num);
  if (channel_index < 0) {
    return result;  // Deliberately ignore every non-LED RMT channel.
  }

  K1RmtChannelState& state = s_channels[channel_index];
  if (handle == nullptr || state.recognised != 0 ||
      k1_rmt_channel_for_handle(handle) >= 0) {
    s_duplicate_channel_count++;
    s_structural_failure = 1;
    return result;
  }

  state.handle = handle;
  state.recognised = 1;
  const rmt_tx_event_callbacks_t callbacks = {k1_rmt_on_trans_done};
  const esp_err_t callback_result =
      rmt_tx_register_event_callbacks(handle, &callbacks, &state);
  if (callback_result == ESP_OK) {
    state.callback_registered = 1;
  } else {
    s_callback_registration_error_count++;
    s_structural_failure = 1;
  }

  return result;  // Preserve the real channel-creation result exactly.
}

extern "C" esp_err_t __wrap_rmt_transmit(
    rmt_channel_handle_t tx_channel,
    rmt_encoder_handle_t encoder,
    const void* payload,
    size_t payload_bytes,
    const rmt_transmit_config_t* config) {
  const int channel_index = k1_rmt_channel_for_handle(tx_channel);
  if (channel_index < 0) {
    return __real_rmt_transmit(tx_channel, encoder, payload, payload_bytes,
                               config);
  }

  K1RmtChannelState& state = s_channels[channel_index];
  const bool active_prepared =
      k1_rmt_prepare_active(state, payload, payload_bytes);
  const uint32_t active_sequence =
      active_prepared ? state.active.sequence : 0U;
  const esp_err_t result =
      __real_rmt_transmit(tx_channel, encoder, payload, payload_bytes, config);
  if (result == ESP_OK) {
    state.accepted_submit_count++;
  } else {
    state.transmit_error_count++;
    if (active_prepared && state.active.sequence == active_sequence) {
      state.transfer_active = 0;
      k1_rmt_trace_memory_barrier();
      state.active.sequence = 0;
    }
    if (s_capture_armed != 0) {
      state.trace_drop_count++;
      s_capture_failure = 1;
    }
  }
  return result;  // Preserve the real transmission result exactly.
}

bool k1_rmt_completion_trace_reset(uint32_t boot_epoch) {
  if (boot_epoch == 0) {
    s_epoch_mismatch_count++;
    s_capture_failure = 1;
    return false;
  }
  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    if (s_channels[i].transfer_active != 0) {
      s_reset_while_active_count++;
      s_capture_failure = 1;
      return false;
    }
  }

  s_capture_armed = 0;
  s_boot_epoch = boot_epoch;
  s_capture_failure = 0;
  s_epoch_mismatch_count = 0;
  s_not_ready_count = 0;
  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    k1_rmt_clear_capture_channel(s_channels[i]);
  }
  s_reset_count++;
  return true;
}

bool k1_rmt_completion_trace_ready(void) {
  return k1_rmt_exact_channels_registered() && s_capture_failure == 0 &&
         s_boot_epoch != 0;
}

bool k1_rmt_completion_trace_stop(void) {
  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    const K1RmtChannelState& state = s_channels[i];
    const bool pending_available =
        state.pending.sequence != 0 &&
        state.pending.sequence != state.pending_consumed_sequence;
    if (state.transfer_active != 0 || state.active.sequence != 0 ||
        pending_available) {
      s_stop_blocked_count++;
      return false;
    }
  }
  s_capture_armed = 0;
  return true;
}

uint32_t k1_rmt_completion_trace_ring_capacity(void) {
  return K1_RMT_TRACE_RING_CAPACITY;
}

uint32_t k1_rmt_completion_trace_wait_timeout_ms(void) {
  return K1_RMT_WAIT_TIMEOUT_MS;
}

bool k1_rmt_completion_trace_wait_previous(
    K1RmtCompletionTraceWaitReport* report) {
  if (report == nullptr) {
    return false;
  }
  report->timeout_ms = K1_RMT_WAIT_TIMEOUT_MS;
  report->attempted_mask = 0;
  report->completed_mask = 0;
  report->timeout_mask = 0;
  report->error_mask = 0;
  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    report->driver_status[i] = ESP_OK;
  }

  // Keep the payload-lifetime barrier alive after a capture/oracle fault. A
  // trace failure invalidates evidence, but must never re-open the early-write
  // defect this bounded wait exists to prevent.
  if (!k1_rmt_exact_channels_registered() || s_boot_epoch == 0) {
    s_not_ready_count++;
    return false;
  }

  bool all_complete = true;
  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    K1RmtChannelState& state = s_channels[i];
    if (state.transfer_active == 0) {
      continue;
    }
    const uint32_t mask = 1UL << i;
    report->attempted_mask |= mask;
    const esp_err_t result =
        rmt_tx_wait_all_done(state.handle, K1_RMT_WAIT_TIMEOUT_MS);
    report->driver_status[i] = result;
    if (result == ESP_OK) {
      report->completed_mask |= mask;
    } else if (result == ESP_ERR_TIMEOUT) {
      report->timeout_mask |= mask;
      state.wait_timeout_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
      all_complete = false;
    } else {
      report->error_mask |= mask;
      state.wait_error_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
      all_complete = false;
    }
  }
  return all_complete;
}

bool k1_rmt_completion_trace_set_pending_frame(
    uint32_t boot_epoch,
    uint32_t vp_frame_sequence) {
  if (!k1_rmt_completion_trace_ready()) {
    s_not_ready_count++;
    return false;
  }
  if (boot_epoch == 0 || boot_epoch != s_boot_epoch) {
    s_epoch_mismatch_count++;
    s_capture_failure = 1;
    return false;
  }

  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    K1RmtChannelState& state = s_channels[i];
    if (state.transfer_active != 0) {
      state.pending_drop_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
      return false;
    }
    if (state.pending.sequence != 0 &&
        state.pending.sequence != state.pending_consumed_sequence) {
      state.pending_overwrite_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
      return false;
    }
  }

  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    K1RmtChannelState& state = s_channels[i];
    const uint32_t next_sequence =
        k1_rmt_next_sequence(state.pending.sequence);
    state.pending.sequence = 0;
    state.pending.boot_epoch = boot_epoch;
    state.pending.vp_frame_sequence = vp_frame_sequence;
    k1_rmt_trace_memory_barrier();
    state.pending.sequence = next_sequence;
  }
  s_capture_armed = 1;
  return true;
}

bool k1_rmt_completion_trace_snapshot(K1RmtCompletionTraceSnapshot* snapshot) {
  if (snapshot == nullptr) {
    return false;
  }
  snapshot->boot_epoch = s_boot_epoch;
  snapshot->reset_count = s_reset_count;
  snapshot->capture_armed = s_capture_armed;
  snapshot->exactly_two_channels_ready =
      k1_rmt_exact_channels_registered() ? 1U : 0U;
  snapshot->capture_valid =
      (k1_rmt_completion_trace_ready() && s_capture_failure == 0) ? 1U : 0U;
  snapshot->completion_ring_capacity_per_channel =
      K1_RMT_TRACE_RING_CAPACITY;
  snapshot->wait_timeout_ms = K1_RMT_WAIT_TIMEOUT_MS;
  snapshot->duplicate_channel_count = s_duplicate_channel_count;
  snapshot->callback_registration_error_count =
      s_callback_registration_error_count;
  snapshot->reset_while_active_count = s_reset_while_active_count;
  snapshot->stop_blocked_count = s_stop_blocked_count;
  snapshot->epoch_mismatch_count = s_epoch_mismatch_count;
  snapshot->not_ready_count = s_not_ready_count;
  for (uint32_t i = 0; i < K1_RMT_TRACE_CHANNEL_COUNT; i++) {
    k1_rmt_copy_channel_snapshot(s_channels[i], snapshot->channels[i]);
  }
  return true;
}

size_t k1_rmt_completion_trace_reap_completions(
    uint8_t channel_index,
    K1RmtCompletionTraceRecord* records,
    size_t record_capacity) {
  if (channel_index >= K1_RMT_TRACE_CHANNEL_COUNT || records == nullptr ||
      record_capacity == 0) {
    return 0;
  }
  if (record_capacity > K1_RMT_TRACE_RING_CAPACITY) {
    record_capacity = K1_RMT_TRACE_RING_CAPACITY;
  }

  K1RmtChannelState& state = s_channels[channel_index];
  size_t copied = 0;
  uint32_t write_sequence = state.completion_sequence;
  uint32_t read_sequence = state.reaped_sequence;
  uint32_t available = write_sequence - read_sequence;
  if (available > K1_RMT_TRACE_RING_CAPACITY) {
    const uint32_t lost = available - K1_RMT_TRACE_RING_CAPACITY;
    state.reap_drop_count += lost;
    state.trace_drop_count += lost;
    s_capture_failure = 1;
    read_sequence = write_sequence - K1_RMT_TRACE_RING_CAPACITY;
    state.reaped_sequence = read_sequence;
    available = K1_RMT_TRACE_RING_CAPACITY;
  }

  while (copied < record_capacity && available > 0) {
    const uint32_t expected_sequence = k1_rmt_next_sequence(read_sequence);
    K1RmtCompletionSlot& slot =
        state.completions[(expected_sequence - 1U) %
                          K1_RMT_TRACE_RING_CAPACITY];
    const uint32_t first_sequence = slot.sequence;
    if (first_sequence != expected_sequence) {
      state.corrupt_record_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
      break;
    }

    K1RmtCompletionTraceRecord& output = records[copied];
    output.sequence = 0;
    output.boot_epoch = slot.boot_epoch;
    output.vp_frame_sequence = slot.vp_frame_sequence;
    output.final_bytes_crc = slot.final_bytes_crc;
    output.submit_sequence = slot.submit_sequence;
    output.channel_index = slot.channel_index;
    output.gpio_num = slot.gpio_num;
    output.rmt_submit_us = slot.rmt_submit_us;
    output.rmt_complete_us = slot.rmt_complete_us;
    output.payload_bytes = slot.payload_bytes;
    output.num_symbols = slot.num_symbols;
    output.flags = slot.flags;
    k1_rmt_trace_memory_barrier();
    const uint32_t second_sequence = slot.sequence;
    if (second_sequence != first_sequence) {
      state.corrupt_record_count++;
      state.trace_drop_count++;
      s_capture_failure = 1;
      break;
    }
    output.sequence = second_sequence;
    read_sequence = second_sequence;
    state.reaped_sequence = read_sequence;
    copied++;
    available--;
  }
  return copied;
}

#endif  // K1_SCHEDULING_TRACE_V1
