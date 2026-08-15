// Gate-1 scheduling trace orchestration. The gate precedes every target include
// so production builds compile an empty translation unit.
#ifdef K1_SCHEDULING_TRACE_V1

#include "k1_scheduling_trace_telemetry.h"

#include <Arduino.h>
#include <esp_random.h>
#include <string.h>

#include "globals.h"
#include "k1_rmt_completion_trace.h"
#include "serial_tx.h"

namespace {

enum : uint32_t {
  K1_SCHED_TRACE_REQUEST_NONE = 0,
  K1_SCHED_TRACE_REQUEST_START = 1,
  K1_SCHED_TRACE_REQUEST_STOP = 2,
};

static volatile uint32_t s_request = K1_SCHED_TRACE_REQUEST_NONE;
static volatile uint32_t s_active = 0;
static volatile uint32_t s_initialised = 0;
static volatile uint32_t s_channels_ready_latched = 0;
static volatile uint32_t s_boot_epoch = 0;
static volatile uint32_t s_vp_frame_sequence = 0;
static volatile uint32_t s_scheduled_frames = 0;
static volatile uint32_t s_wait_failure_count = 0;
static volatile uint32_t s_pending_failure_count = 0;
static volatile uint32_t s_start_failure_count = 0;
static volatile uint32_t s_stop_failure_count = 0;
static volatile uint32_t s_auto_stop_count = 0;

// The ISR-owned rings retain the full 64 records per channel. Serial export
// reuses a smaller chunk so the main trace build stays within internal DRAM.
static K1RmtCompletionTraceRecord s_dump_records[16];

static uint32_t k1_scheduling_trace_next_nonzero(uint32_t value) {
  value++;
  return value == 0 ? 1U : value;
}

static uint32_t k1_scheduling_trace_new_epoch(void) {
  uint32_t epoch = esp_random();
  return epoch == 0 ? 1U : epoch;
}

static uint32_t k1_scheduling_trace_load(const volatile uint32_t* value) {
  return __atomic_load_n(value, __ATOMIC_ACQUIRE);
}

static void k1_scheduling_trace_store(
    volatile uint32_t* value,
    uint32_t next) {
  __atomic_store_n(value, next, __ATOMIC_RELEASE);
}

static void k1_scheduling_trace_increment(volatile uint32_t* value) {
  __atomic_add_fetch(value, 1U, __ATOMIC_RELAXED);
}

static void k1_scheduling_trace_print_snapshot(void) {
  K1RmtCompletionTraceSnapshot snapshot = {};
  const bool snapshot_ok = k1_rmt_completion_trace_snapshot(&snapshot);
  tx_begin();
  USBSerial.print("K1_SCHED_TRACE_STATUS,ver=1,snapshot_ok=");
  USBSerial.print(snapshot_ok ? 1 : 0);
  USBSerial.print(",initialised=");
  USBSerial.print(k1_scheduling_trace_load(&s_initialised));
  USBSerial.print(",active=");
  USBSerial.print(k1_scheduling_trace_load(&s_active));
  USBSerial.print(",request=");
  USBSerial.print(k1_scheduling_trace_load(&s_request));
  USBSerial.print(",epoch=");
  USBSerial.print(snapshot.boot_epoch);
  USBSerial.print(",frames=");
  USBSerial.print(k1_scheduling_trace_load(&s_scheduled_frames));
  USBSerial.print(",capacity=");
  USBSerial.print(k1_rmt_completion_trace_ring_capacity());
  USBSerial.print(",channels_ready=");
  USBSerial.print(snapshot.exactly_two_channels_ready);
  USBSerial.print(",capture_valid=");
  USBSerial.print(snapshot.capture_valid);
  USBSerial.print(",wait_timeout_ms=");
  USBSerial.print(snapshot.wait_timeout_ms);
  USBSerial.print(",wait_failures=");
  USBSerial.print(k1_scheduling_trace_load(&s_wait_failure_count));
  USBSerial.print(",pending_failures=");
  USBSerial.print(k1_scheduling_trace_load(&s_pending_failure_count));
  USBSerial.print(",start_failures=");
  USBSerial.print(k1_scheduling_trace_load(&s_start_failure_count));
  USBSerial.print(",stop_failures=");
  USBSerial.print(k1_scheduling_trace_load(&s_stop_failure_count));
  USBSerial.print(",auto_stops=");
  USBSerial.print(k1_scheduling_trace_load(&s_auto_stop_count));
  USBSerial.print(",p_submit=");
  USBSerial.print(snapshot.channels[K1_RMT_TRACE_PRIMARY_CHANNEL].accepted_submit_count);
  USBSerial.print(",p_complete=");
  USBSerial.print(snapshot.channels[K1_RMT_TRACE_PRIMARY_CHANNEL].confirmed_completion_count);
  USBSerial.print(",s_submit=");
  USBSerial.print(snapshot.channels[K1_RMT_TRACE_SECONDARY_CHANNEL].accepted_submit_count);
  USBSerial.print(",s_complete=");
  USBSerial.print(snapshot.channels[K1_RMT_TRACE_SECONDARY_CHANNEL].confirmed_completion_count);
  USBSerial.print(",p_drops=");
  USBSerial.print(snapshot.channels[K1_RMT_TRACE_PRIMARY_CHANNEL].trace_drop_count);
  USBSerial.print(",s_drops=");
  USBSerial.println(snapshot.channels[K1_RMT_TRACE_SECONDARY_CHANNEL].trace_drop_count);
  tx_end();
}

static void k1_scheduling_trace_dump(void) {
  if (k1_scheduling_trace_load(&s_active) != 0 ||
      k1_scheduling_trace_load(&s_request) != K1_SCHED_TRACE_REQUEST_NONE) {
    tx_begin(true);
    USBSerial.println("K1_SCHED_TRACE_DUMP_REJECTED: stop capture and wait for inactive status");
    tx_end(true);
    return;
  }

  K1RmtCompletionTraceSnapshot before = {};
  k1_rmt_completion_trace_snapshot(&before);
  tx_begin();
  USBSerial.print("K1RMT_BEGIN,ver=1,epoch=");
  USBSerial.print(before.boot_epoch);
  USBSerial.print(",capacity=");
  USBSerial.print(k1_rmt_completion_trace_ring_capacity());
  USBSerial.print(",capture_valid=");
  USBSerial.println(before.capture_valid);

  uint32_t total = 0;
  for (uint8_t channel = 0; channel < K1_RMT_TRACE_CHANNEL_COUNT; channel++) {
    size_t count = 0;
    do {
      count = k1_rmt_completion_trace_reap_completions(
          channel,
          s_dump_records,
          sizeof(s_dump_records) / sizeof(s_dump_records[0]));
      total += static_cast<uint32_t>(count);
      for (size_t i = 0; i < count; i++) {
        const K1RmtCompletionTraceRecord& record = s_dump_records[i];
        USBSerial.printf(
            "K1RMT,channel=%lu,seq=%lu,epoch=%lu,vp_seq=%lu,crc=%08lx,"
            "submit_seq=%lu,gpio=%ld,submit_us=%lld,complete_us=%lld,"
            "duration_us=%lld,payload_bytes=%lu,num_symbols=%lu,flags=%lu\n",
            (unsigned long)record.channel_index,
            (unsigned long)record.sequence,
            (unsigned long)record.boot_epoch,
            (unsigned long)record.vp_frame_sequence,
            (unsigned long)record.final_bytes_crc,
            (unsigned long)record.submit_sequence,
            (long)record.gpio_num,
            (long long)record.rmt_submit_us,
            (long long)record.rmt_complete_us,
            (long long)(record.rmt_complete_us - record.rmt_submit_us),
            (unsigned long)record.payload_bytes,
            (unsigned long)record.num_symbols,
            (unsigned long)record.flags);
      }
    } while (count != 0);
  }

  K1RmtCompletionTraceSnapshot after = {};
  k1_rmt_completion_trace_snapshot(&after);
  USBSerial.print("K1RMT_DONE,ver=1,records=");
  USBSerial.print(total);
  USBSerial.print(",capture_valid=");
  USBSerial.print(after.capture_valid);
  USBSerial.print(",p_reaped=");
  USBSerial.print(after.channels[K1_RMT_TRACE_PRIMARY_CHANNEL].reaped_sequence);
  USBSerial.print(",s_reaped=");
  USBSerial.println(after.channels[K1_RMT_TRACE_SECONDARY_CHANNEL].reaped_sequence);
  tx_end();
}

}  // namespace

void k1_scheduling_trace_initialise(void) {
  const uint32_t epoch = k1_scheduling_trace_new_epoch();
  const bool reset_ok = k1_rmt_completion_trace_reset(epoch);
  k1_scheduling_trace_store(&s_boot_epoch, epoch);
  k1_scheduling_trace_store(&s_initialised, reset_ok ? 1U : 0U);
  k1_scheduling_trace_store(&s_channels_ready_latched, 0U);
  k1_scheduling_trace_store(&s_active, 0U);
  k1_scheduling_trace_store(&s_request, K1_SCHED_TRACE_REQUEST_NONE);
  k1_scheduling_trace_store(&s_vp_frame_sequence, 0U);
  k1_scheduling_trace_store(&s_scheduled_frames, 0U);
}

void k1_scheduling_trace_before_fastled_show(void) {
  if (k1_scheduling_trace_load(&s_initialised) == 0) {
    return;
  }

  // The first ever FastLED load creates the IDF RMT channels. There is no prior
  // payload to protect at that point, so absence of both registered channels is
  // a bootstrap state, not a wait failure. Preserve any queued start request
  // for the first structurally ready frame.
  if (k1_scheduling_trace_load(&s_channels_ready_latched) == 0) {
    K1RmtCompletionTraceSnapshot structural_snapshot = {};
    k1_rmt_completion_trace_snapshot(&structural_snapshot);
    if (structural_snapshot.exactly_two_channels_ready == 0) {
      return;
    }
    k1_scheduling_trace_store(&s_channels_ready_latched, 1U);
  }

  K1RmtCompletionTraceWaitReport wait_report = {};
  if (!k1_rmt_completion_trace_wait_previous(&wait_report)) {
    k1_scheduling_trace_increment(&s_wait_failure_count);
  }

  const uint32_t request = __atomic_exchange_n(
      &s_request, K1_SCHED_TRACE_REQUEST_NONE, __ATOMIC_ACQ_REL);
  if (request == K1_SCHED_TRACE_REQUEST_STOP) {
    if (k1_rmt_completion_trace_stop()) {
      k1_scheduling_trace_store(&s_active, 0U);
    } else {
      k1_scheduling_trace_increment(&s_stop_failure_count);
    }
  } else if (request == K1_SCHED_TRACE_REQUEST_START) {
    if (k1_scheduling_trace_load(&s_active) != 0 &&
        !k1_rmt_completion_trace_stop()) {
      k1_scheduling_trace_increment(&s_stop_failure_count);
      k1_scheduling_trace_store(&s_active, 0U);
    }
    const uint32_t epoch = k1_scheduling_trace_new_epoch();
    if (k1_rmt_completion_trace_reset(epoch) &&
        k1_rmt_completion_trace_ready()) {
      k1_scheduling_trace_store(&s_boot_epoch, epoch);
      k1_scheduling_trace_store(&s_vp_frame_sequence, 0U);
      k1_scheduling_trace_store(&s_scheduled_frames, 0U);
      k1_scheduling_trace_store(&s_active, 1U);
    } else {
      k1_scheduling_trace_increment(&s_start_failure_count);
      k1_scheduling_trace_store(&s_active, 0U);
    }
  }

  if (k1_scheduling_trace_load(&s_active) == 0) {
    return;
  }

  const uint32_t capacity = k1_rmt_completion_trace_ring_capacity();
  const uint32_t scheduled = k1_scheduling_trace_load(&s_scheduled_frames);
  if (scheduled >= capacity) {
    if (k1_rmt_completion_trace_stop()) {
      k1_scheduling_trace_store(&s_active, 0U);
      k1_scheduling_trace_increment(&s_auto_stop_count);
    } else {
      k1_scheduling_trace_increment(&s_stop_failure_count);
    }
    return;
  }

  uint32_t vp_sequence = k1_scheduling_trace_load(&s_vp_frame_sequence);
  vp_sequence = k1_scheduling_trace_next_nonzero(vp_sequence);
  if (k1_rmt_completion_trace_set_pending_frame(
          k1_scheduling_trace_load(&s_boot_epoch),
          vp_sequence)) {
    k1_scheduling_trace_store(&s_vp_frame_sequence, vp_sequence);
    k1_scheduling_trace_store(&s_scheduled_frames, scheduled + 1U);
  } else {
    k1_scheduling_trace_increment(&s_pending_failure_count);
    k1_rmt_completion_trace_stop();
    k1_scheduling_trace_store(&s_active, 0U);
  }
}

bool k1_scheduling_trace_command(
    const char* command_type,
    const char* command_data) {
  if (command_data == nullptr || command_data[0] == '\0' ||
      strcmp(command_data, "status") == 0) {
    k1_scheduling_trace_print_snapshot();
    return true;
  }
  if (strcmp(command_data, "start") == 0) {
    k1_scheduling_trace_store(&s_request, K1_SCHED_TRACE_REQUEST_START);
    tx_begin();
    USBSerial.print("K1_SCHED_TRACE_START_REQUESTED,capacity_per_channel=");
    USBSerial.println(k1_rmt_completion_trace_ring_capacity());
    tx_end();
    return true;
  }
  if (strcmp(command_data, "stop") == 0) {
    k1_scheduling_trace_store(&s_request, K1_SCHED_TRACE_REQUEST_STOP);
    tx_begin();
    USBSerial.println("K1_SCHED_TRACE_STOP_REQUESTED");
    tx_end();
    return true;
  }
  if (strcmp(command_data, "dump") == 0) {
    k1_scheduling_trace_dump();
    return true;
  }
  bad_command(command_type, command_data);
  return true;
}

#endif  // K1_SCHEDULING_TRACE_V1
