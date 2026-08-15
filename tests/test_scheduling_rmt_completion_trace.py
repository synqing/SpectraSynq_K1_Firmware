from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "SPECTRASYNQ_K1_FIRMWARE/diag/k1_rmt_completion_trace.h"
SOURCE = ROOT / "SPECTRASYNQ_K1_FIRMWARE/diag/k1_rmt_completion_trace.cpp"
PLATFORMIO = ROOT / "platformio.ini"


def _environment_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^\[env:{re.escape(name)}\]\n(.*?)(?=^\[env:|\Z)", text
    )
    assert match is not None, f"missing PlatformIO environment {name}"
    return match.group(1)


def test_trace_environment_is_non_shippable_and_wraps_exact_idf_calls() -> None:
    ini = PLATFORMIO.read_text()
    trace = _environment_block(ini, "k1_scheduling_trace_dev")
    production = _environment_block(ini, "k1_hardware")

    assert "NON-SHIPPABLE" in trace
    assert "extends = env:k1_hardware_trace_dev" in trace
    assert "+<diag/k1_rmt_completion_trace.cpp>" in trace
    assert "-DK1_SCHEDULING_TRACE_V1" in trace
    assert "-DENABLE_TEMPO_STREAM=1" in trace
    assert "-DENABLE_AP_FRONTEND_DEBUG=1" in trace
    assert "-Wl,--wrap=rmt_new_tx_channel" in trace
    assert "-Wl,--wrap=rmt_transmit" in trace

    assert "K1_SCHEDULING_TRACE_V1" not in production
    assert "--wrap=rmt_new_tx_channel" not in production
    assert "--wrap=rmt_transmit" not in production
    assert "k1_rmt_completion_trace.cpp" not in production


def test_source_is_compile_gated_and_uses_compile_time_k1_gpio_truth() -> None:
    source = SOURCE.read_text()
    header = HEADER.read_text()

    assert source.lstrip().startswith("// Gate-1 trace-only")
    assert "#ifdef K1_SCHEDULING_TRACE_V1" in source[:500]
    assert "#ifdef K1_SCHEDULING_TRACE_V1" in header
    assert "K1_RMT_EXPECTED_PRIMARY_GPIO = LED_DATA_PIN" in source
    assert "K1_RMT_EXPECTED_SECONDARY_GPIO = LED_CLOCK_PIN" in source
    assert "K1_RMT_PRIMARY_LED_COUNT = LED_COUNT_VALUE" in source
    assert "K1_RMT_SECONDARY_LED_COUNT = SECONDARY_LED_COUNT_VALUE" in source
    assert "k1_rmt_channel_for_gpio(config->gpio_num)" in source
    assert "usbmodem" not in source.lower()
    assert "upload_port" not in source.lower()
    assert "/dev/" not in source.lower()


def test_callback_is_official_static_internal_ram_and_isr_safe() -> None:
    source = SOURCE.read_text()
    assert "rmt_tx_register_event_callbacks" in source
    assert ".on_trans_done" not in source  # C++17-compatible positional init.
    assert "IRAM_ATTR k1_rmt_on_trans_done" in source
    assert "static DRAM_ATTR K1RmtChannelState s_channels" in source
    assert "static DRAM_ATTR volatile uint32_t s_boot_epoch" in source

    callback = re.search(
        r"(?s)static bool IRAM_ATTR k1_rmt_on_trans_done\(.*?\n\}\n\n"
        r"static bool k1_rmt_prepare_active",
        source,
    )
    assert callback is not None
    callback_body = callback.group(0)
    for forbidden in (
        "malloc",
        "calloc",
        "realloc",
        "free(",
        "new ",
        "delete",
        "String",
        "Serial",
        "ESP_LOG",
        "printf",
        "xQueue",
        "FromISR",
        "vTask",
        "yield",
    ):
        assert forbidden not in callback_body
    assert "return false;  // Never request a task wake" in callback_body


def test_sequence_commit_counters_and_fail_closed_contract_are_present() -> None:
    source = SOURCE.read_text()
    header = HEADER.read_text()

    # Completion payload is filled before the per-slot commit sequence.
    fill = source.index("slot.boot_epoch = boot_epoch;")
    commit = source.index("slot.sequence = next_sequence;", fill)
    assert fill < commit
    assert "state->completion_overwrite_count++" in source
    assert "state->unmatched_completion_count++" in source
    assert "state.pending_overwrite_count++" in source
    assert "state.inflight_overwrite_count++" in source
    assert "state->stale_epoch_completion_count++" in source
    assert "s_capture_failure = 1" in source
    assert "primary.handle != secondary.handle" in source
    assert "exactly_two_channels_ready" in header
    assert "capture_valid" in header
    assert "k1_rmt_completion_trace_stop" in header
    assert "k1_rmt_completion_trace_ring_capacity" in header
    assert "completion_ring_capacity_per_channel" in header


def test_previous_transfer_wait_is_finite_and_geometry_derived() -> None:
    source = SOURCE.read_text()
    assert "K1_RMT_MAX_LED_COUNT" in source
    assert "K1_WS2812_RGB_WIRE_US_PER_PIXEL" in source
    assert "K1_FASTLED_RMT_RESET_US" in source
    assert "K1_RMT_COMPLETION_MARGIN_US" in source
    assert "K1_RMT_WAIT_TIMEOUT_MS" in source
    assert "rmt_tx_wait_all_done(state.handle, K1_RMT_WAIT_TIMEOUT_MS)" in source
    assert "rmt_tx_wait_all_done(state.handle, -1)" not in source
    assert "K1_RMT_WAIT_TIMEOUT_MS < 100" in source
    wait_start = source.index("bool k1_rmt_completion_trace_wait_previous")
    wait_end = source.index("bool k1_rmt_completion_trace_set_pending_frame")
    wait_body = source[wait_start:wait_end]
    assert "k1_rmt_exact_channels_registered()" in wait_body
    assert "!k1_rmt_completion_trace_ready()" not in wait_body


def test_wrappers_preserve_real_results() -> None:
    source = SOURCE.read_text()
    assert "const esp_err_t result = __real_rmt_new_tx_channel" in source
    assert "return result;  // Preserve the real channel-creation result exactly." in source
    assert "const esp_err_t result =\n      __real_rmt_transmit" in source
    assert "return result;  // Preserve the real transmission result exactly." in source


def test_final_byte_identity_is_derived_only_from_actual_idf_payload() -> None:
    source = SOURCE.read_text()
    header = HEADER.read_text()
    assert "esp_crc32_le(0, static_cast<const uint8_t*>(payload), payload_bytes)" in source
    assert "k1_rmt_prepare_active(state, payload, payload_bytes)" in source
    pending = re.search(r"struct K1RmtPendingRecord \{(?P<body>.*?)\};", source, re.S)
    assert pending is not None
    assert "final_bytes_crc" not in pending.group("body")
    declaration = header[header.index("bool k1_rmt_completion_trace_set_pending_frame"):]
    declaration = declaration[:declaration.index(");")]
    assert "final_bytes_crc" not in declaration


def test_host_record_core_compile_and_completion_round_trip(tmp_path: Path) -> None:
    stub_root = tmp_path / "stubs"
    (stub_root / "driver").mkdir(parents=True)
    (stub_root / "driver/rmt_tx.h").write_text(
        r'''
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef int32_t esp_err_t;
#define ESP_OK 0
#define ESP_ERR_TIMEOUT 0x107
struct FakeRmtChannel;
typedef FakeRmtChannel* rmt_channel_handle_t;
typedef void* rmt_encoder_handle_t;
typedef struct { int32_t gpio_num; } rmt_tx_channel_config_t;
typedef struct { int loop_count; } rmt_transmit_config_t;
typedef struct { size_t num_symbols; } rmt_tx_done_event_data_t;
typedef bool (*rmt_tx_done_callback_t)(rmt_channel_handle_t,
                                       const rmt_tx_done_event_data_t*, void*);
typedef struct { rmt_tx_done_callback_t on_trans_done; }
    rmt_tx_event_callbacks_t;
#ifdef __cplusplus
extern "C" {
#endif
esp_err_t rmt_tx_register_event_callbacks(
    rmt_channel_handle_t, const rmt_tx_event_callbacks_t*, void*);
esp_err_t rmt_tx_wait_all_done(rmt_channel_handle_t, int);
#ifdef __cplusplus
}
#endif
'''
    )
    (stub_root / "esp_attr.h").write_text(
        "#pragma once\n#define DRAM_ATTR\n#define IRAM_ATTR\n"
    )
    (stub_root / "esp_timer.h").write_text(
        '#pragma once\n#include <stdint.h>\n#ifdef __cplusplus\nextern "C" {\n#endif\n'
        "int64_t esp_timer_get_time(void);\n"
        '#ifdef __cplusplus\n}\n#endif\n'
    )
    (stub_root / "esp_crc.h").write_text(
        r'''
#pragma once
#include <stddef.h>
#include <stdint.h>
static inline uint32_t esp_crc32_le(uint32_t crc, const uint8_t* data, size_t len) {
  crc = ~crc;
  for (size_t i = 0; i < len; ++i) {
    crc ^= data[i];
    for (uint32_t bit = 0; bit < 8; ++bit) {
      crc = (crc >> 1U) ^ (0xEDB88320U & (0U - (crc & 1U)));
    }
  }
  return ~crc;
}
'''
    )

    harness = tmp_path / "rmt_trace_host.cpp"
    harness.write_text(
        r'''
#include <assert.h>
#include <stdint.h>
#include "driver/rmt_tx.h"
#include "k1_rmt_completion_trace.h"

struct FakeRmtChannel { int index; int gpio; };
static FakeRmtChannel g_channels[3] = {{0, 6}, {1, 7}, {2, 21}};
static rmt_tx_done_callback_t g_callbacks[3] = {};
static void* g_contexts[3] = {};
static bool g_active[3] = {};
static int64_t g_now_us = 1000;
static esp_err_t g_new_result = ESP_OK;
static esp_err_t g_transmit_result = ESP_OK;

extern "C" esp_err_t __wrap_rmt_new_tx_channel(
    const rmt_tx_channel_config_t*, rmt_channel_handle_t*);
extern "C" esp_err_t __wrap_rmt_transmit(
    rmt_channel_handle_t, rmt_encoder_handle_t, const void*, size_t,
    const rmt_transmit_config_t*);

extern "C" int64_t esp_timer_get_time(void) { return g_now_us; }

static int index_for_gpio(int gpio) {
  if (gpio == 6) return 0;
  if (gpio == 7) return 1;
  return 2;
}

extern "C" esp_err_t __real_rmt_new_tx_channel(
    const rmt_tx_channel_config_t* config, rmt_channel_handle_t* out) {
  if (g_new_result != ESP_OK) return g_new_result;
  const int index = index_for_gpio(config->gpio_num);
  g_channels[index].gpio = config->gpio_num;
  *out = &g_channels[index];
  return ESP_OK;
}

extern "C" esp_err_t rmt_tx_register_event_callbacks(
    rmt_channel_handle_t channel, const rmt_tx_event_callbacks_t* callbacks,
    void* context) {
  g_callbacks[channel->index] = callbacks->on_trans_done;
  g_contexts[channel->index] = context;
  return ESP_OK;
}

extern "C" esp_err_t __real_rmt_transmit(
    rmt_channel_handle_t channel, rmt_encoder_handle_t, const void*, size_t,
    const rmt_transmit_config_t*) {
  if (g_transmit_result == ESP_OK) g_active[channel->index] = true;
  return g_transmit_result;
}

static void finish(int index, size_t symbols) {
  assert(g_active[index]);
  g_now_us += 5080;
  const rmt_tx_done_event_data_t event = {symbols};
  assert(g_callbacks[index] != nullptr);
  assert(!g_callbacks[index](&g_channels[index], &event, g_contexts[index]));
  g_active[index] = false;
}

extern "C" esp_err_t rmt_tx_wait_all_done(
    rmt_channel_handle_t channel, int timeout_ms) {
  assert(timeout_ms == 6);
  if (g_active[channel->index]) finish(channel->index, 3841);
  return ESP_OK;
}

int main() {
  assert(k1_rmt_completion_trace_reset(0x1234U));
  assert(!k1_rmt_completion_trace_ready());

  rmt_tx_channel_config_t unrelated_config = {21};
  rmt_channel_handle_t unrelated = nullptr;
  assert(__wrap_rmt_new_tx_channel(&unrelated_config, &unrelated) == ESP_OK);
  assert(!k1_rmt_completion_trace_ready());

  rmt_tx_channel_config_t primary_config = {6};
  rmt_tx_channel_config_t secondary_config = {7};
  rmt_channel_handle_t primary = nullptr;
  rmt_channel_handle_t secondary = nullptr;
  assert(__wrap_rmt_new_tx_channel(&primary_config, &primary) == ESP_OK);
  assert(!k1_rmt_completion_trace_ready());
  assert(__wrap_rmt_new_tx_channel(&secondary_config, &secondary) == ESP_OK);
  assert(k1_rmt_completion_trace_ready());
  assert(k1_rmt_completion_trace_wait_timeout_ms() == 6U);
  assert(k1_rmt_completion_trace_ring_capacity() == 64U);

  assert(k1_rmt_completion_trace_set_pending_frame(0x1234U, 42U));
  uint8_t primary_payload[480] = {};
  uint8_t secondary_payload[480] = {};
  secondary_payload[0] = 1U;
  const rmt_transmit_config_t tx_config = {0};
  assert(__wrap_rmt_transmit(primary, nullptr, primary_payload, sizeof(primary_payload),
                             &tx_config) == ESP_OK);
  assert(__wrap_rmt_transmit(secondary, nullptr, secondary_payload, sizeof(secondary_payload),
                             &tx_config) == ESP_OK);
  finish(0, 3841);
  finish(1, 3841);

  K1RmtCompletionTraceRecord records[2] = {};
  assert(k1_rmt_completion_trace_reap_completions(0, records, 2) == 1U);
  assert(records[0].boot_epoch == 0x1234U);
  assert(records[0].vp_frame_sequence == 42U);
  const uint32_t first_primary_crc = records[0].final_bytes_crc;
  assert(first_primary_crc != 0U);
  assert(records[0].channel_index == 0U);
  assert(records[0].gpio_num == 6);
  assert(records[0].rmt_complete_us > records[0].rmt_submit_us);
  assert(records[0].num_symbols == 3841U);
  assert(records[0].flags == K1_RMT_TRACE_RECORD_CONFIRMED);
  assert(records[0].sequence != 0U);

  assert(k1_rmt_completion_trace_reap_completions(1, records, 2) == 1U);
  const uint32_t first_secondary_crc = records[0].final_bytes_crc;
  assert(first_secondary_crc != 0U);
  assert(first_secondary_crc != first_primary_crc);
  assert(records[0].channel_index == 1U);
  assert(records[0].gpio_num == 7);

  // The finite wait is the lifetime barrier for the next FastLED load.
  primary_payload[0] = 2U;
  assert(k1_rmt_completion_trace_set_pending_frame(0x1234U, 43U));
  assert(__wrap_rmt_transmit(primary, nullptr, primary_payload, sizeof(primary_payload),
                             &tx_config) == ESP_OK);
  assert(__wrap_rmt_transmit(secondary, nullptr, secondary_payload, sizeof(secondary_payload),
                             &tx_config) == ESP_OK);
  assert(!k1_rmt_completion_trace_stop());
  K1RmtCompletionTraceWaitReport wait_report = {};
  assert(k1_rmt_completion_trace_wait_previous(&wait_report));
  assert(wait_report.timeout_ms == 6U);
  assert(wait_report.attempted_mask == 3U);
  assert(wait_report.completed_mask == 3U);
  assert(wait_report.timeout_mask == 0U);
  assert(wait_report.error_mask == 0U);
  assert(k1_rmt_completion_trace_reap_completions(0, records, 2) == 1U);
  assert(records[0].final_bytes_crc != first_primary_crc);
  assert(k1_rmt_completion_trace_reap_completions(1, records, 2) == 1U);
  assert(records[0].final_bytes_crc == first_secondary_crc);

  K1RmtCompletionTraceSnapshot snapshot = {};
  assert(k1_rmt_completion_trace_snapshot(&snapshot));
  assert(snapshot.exactly_two_channels_ready == 1U);
  assert(snapshot.capture_valid == 1U);
  assert(snapshot.channels[0].accepted_submit_count == 2U);
  assert(snapshot.channels[1].confirmed_completion_count == 2U);
  assert(snapshot.channels[0].trace_drop_count == 0U);
  assert(snapshot.completion_ring_capacity_per_channel == 64U);
  assert(snapshot.stop_blocked_count == 1U);

  assert(k1_rmt_completion_trace_stop());

  // A trace fault invalidates evidence but cannot disable the lifetime wait.
  assert(k1_rmt_completion_trace_set_pending_frame(0x1234U, 44U));
  assert(__wrap_rmt_transmit(primary, nullptr, primary_payload, sizeof(primary_payload),
                             &tx_config) == ESP_OK);
  assert(__wrap_rmt_transmit(secondary, nullptr, secondary_payload, sizeof(secondary_payload),
                             &tx_config) == ESP_OK);
  assert(!k1_rmt_completion_trace_set_pending_frame(0x1234U, 45U));
  K1RmtCompletionTraceWaitReport post_fault_wait = {};
  assert(k1_rmt_completion_trace_wait_previous(&post_fault_wait));
  assert(post_fault_wait.attempted_mask == 3U);
  assert(post_fault_wait.completed_mask == 3U);
  assert(!k1_rmt_completion_trace_ready());

  // A real-driver error is returned unchanged.
  g_transmit_result = -77;
  assert(__wrap_rmt_transmit(primary, nullptr, primary_payload, sizeof(primary_payload),
                             &tx_config) == -77);
  assert(!k1_rmt_completion_trace_ready());
  return 0;
}
'''
    )

    binary = tmp_path / "rmt_trace_host"
    command = [
        "c++",
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-DK1_SCHEDULING_TRACE_V1",
        "-DK1_RMT_COMPLETION_TRACE_HOST_TEST",
        "-I",
        str(stub_root),
        "-I",
        str(HEADER.parent),
        str(SOURCE),
        str(harness),
        "-o",
        str(binary),
    ]
    compile_result = subprocess.run(command, text=True, capture_output=True)
    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run([str(binary)], text=True, capture_output=True)
    assert run_result.returncode == 0, run_result.stderr
