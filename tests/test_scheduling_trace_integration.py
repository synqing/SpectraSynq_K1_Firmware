"""Gate 1 structural checks for the bounded scheduling trace integration."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
LEDS = FW / "visual" / "led_utilities.h"
TRACE = FW / "serial" / "k1_scheduling_trace_telemetry.cpp"
TABLE = FW / "serial" / "serial_typed_cmd_table.def"
SERIAL = FW / "serial" / "serial_menu.cpp"
PIO = ROOT / "platformio.ini"
IDENTITIES = ROOT / "scripts" / "platformio" / "k1_device_identities.json"


def test_trace_wait_and_identity_publish_are_immediately_before_fastled_show():
    source = LEDS.read_text(encoding="utf-8")
    hook = source.index("k1_scheduling_trace_before_fastled_show")
    show = source.index("FastLED.show(); // This will update both LED strips", hook)
    assert hook < show
    between = source[hook:show]
    assert "k1_scheduling_trace_before_fastled_show();" in between
    assert "esp_crc" not in between


def test_bootstrap_epoch_is_initialised_before_unarmed_bootstrap_show():
    source = INO.read_text(encoding="utf-8")
    initialise = source.index("k1_scheduling_trace_initialise()")
    bootstrap = source.index("FastLED.show();", initialise)
    assert initialise < bootstrap


def test_capture_auto_stops_at_fixed_capacity_before_overwrite():
    source = TRACE.read_text(encoding="utf-8")
    assert "scheduled >= capacity" in source
    assert "k1_rmt_completion_trace_stop()" in source
    assert "s_auto_stop_count" in source
    assert "s_dump_records[16]" in source
    assert "while (count != 0)" in source


def test_first_rmt_channel_creation_is_a_bootstrap_state_not_a_wait_failure():
    source = TRACE.read_text(encoding="utf-8")
    latch = source.index("s_channels_ready_latched")
    snapshot = source.index("K1RmtCompletionTraceSnapshot structural_snapshot", latch)
    ready = source.index("structural_snapshot.exactly_two_channels_ready == 0", snapshot)
    wait = source.index("k1_rmt_completion_trace_wait_previous", ready)
    assert latch < snapshot < ready < wait


def test_render_hook_has_no_logging_or_allocation():
    source = TRACE.read_text(encoding="utf-8")
    start = source.index("void k1_scheduling_trace_before_fastled_show")
    end = source.index("bool k1_scheduling_trace_command", start)
    body = source[start:end]
    for forbidden in ("USBSerial", "printf", "malloc", "new ", "delay("):
        assert forbidden not in body


def test_typed_command_is_trace_only_and_harness_classified():
    table = TABLE.read_text(encoding="utf-8")
    gate = table.index("#ifdef K1_SCHEDULING_TRACE_V1")
    command = table.index('SERIAL_TYPED_CMD("scheduling_trace"', gate)
    end = table.index("#endif", command)
    assert gate < command < end
    assert "CMD_HARNESS" in table[command:end]
    serial = SERIAL.read_text(encoding="utf-8")
    assert 'strcmp(command_type, "scheduling_trace") == 0' in serial
    assert "k1_scheduling_trace_command(command_type, command_data)" in serial


def test_connected_bench_smoke_env_uses_physical_im69d_parent_and_is_allowlisted():
    pio = PIO.read_text(encoding="utf-8")
    start = pio.index("[env:k1_bench_scheduling_trace_dev]")
    end = pio.find("\n[env:", start + 1)
    section = pio[start : end if end >= 0 else len(pio)]
    assert "extends = env:k1_bench_im69d_ap_integrity_probe" in section
    assert "-DK1_SCHEDULING_TRACE_V1" in section
    assert "-Wl,--wrap=rmt_new_tx_channel" in section
    assert "-Wl,--wrap=rmt_transmit" in section
    identities = IDENTITIES.read_text(encoding="utf-8")
    assert '"k1_bench_scheduling_trace_dev"' in identities
    baseline_start = pio.index("[env:k1_bench_scheduling_baseline_probe]")
    baseline_end = pio.find("\n[env:", baseline_start + 1)
    baseline = pio[baseline_start : baseline_end if baseline_end >= 0 else len(pio)]
    assert "extends = env:k1_bench_im69d" in baseline
    assert "-DENABLE_AP_FRONTEND_DEBUG=1" in baseline
    assert "K1_SCHEDULING_TRACE_V1" not in baseline
    assert "FEATURE_MABUTRACE" not in baseline
    assert "--wrap=rmt_" not in baseline
    assert '"k1_bench_scheduling_baseline_probe"' in identities
