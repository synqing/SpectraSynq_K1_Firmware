"""Host-only static contract test for the P0.4 sync probe firmware.

No device, no compile — a grep-level proof that the firmware TU
(network/k1_sync_link.cpp) emits EXACTLY the serial grammar the P0.3 oracle
parses, that every .ino / serial_menu wiring point is #ifdef SB_K1_SYNC_PROBE
gated (so production stays radio-clean), and that the load-bearing hard rules
hold (no cal, ISR is IRAM_ATTR + Serial-free, the one added task is on Core 1).

The parse half is the strong link: each firmware printf template is turned into
a concrete line and fed through the oracle's own parser, so firmware↔oracle
grammar drift is caught here, before P0.5 ever flashes silicon.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from dual_sync_probe import logfmt  # noqa: E402

_FW = os.path.join(_ROOT, "SPECTRASYNQ_K1_FIRMWARE")
_CPP = os.path.join(_FW, "network", "k1_sync_link.cpp")
_H = os.path.join(_FW, "network", "k1_sync_link.h")
_REMOTED = os.path.join(_FW, "network", "ble_remoted_central.cpp")
_INO = os.path.join(_FW, "SPECTRASYNQ_K1_FIRMWARE.ino")
_MENU = os.path.join(_FW, "serial", "serial_menu.h")
_PIO = os.path.join(_ROOT, "platformio.ini")
_GUARD = os.path.join(_ROOT, "scripts", "platformio", "k1_upload_guard.py")
_WRAPPER = os.path.join(_ROOT, "scripts", "agent", "pio-build.sh")


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _gated_by_sync_probe(text: str, needle: str) -> bool:
    """True if ``needle`` sits inside a `#ifdef SB_K1_SYNC_PROBE ... #endif`
    block — the nearest preceding conditional directive opens that gate."""
    idx = text.index(needle)
    before = text[:idx]
    # nearest preceding preprocessor conditional
    matches = list(re.finditer(r"^\s*#(ifdef|ifndef|if|endif)\b.*$", before, re.M))
    if not matches:
        return False
    last = matches[-1].group(0)
    return "SB_K1_SYNC_PROBE" in last and "#ifndef" not in last


# --------------------------------------------------------------------------- #
# Firmware ↔ oracle grammar contract                                          #
# --------------------------------------------------------------------------- #

# (printf-template substring that MUST be in the TU, a concrete valid line,
#  the oracle record type that line must parse to)
_GRAMMAR = [
    ("[sync_oracle] trig_out seq=%u t_us=%llu",
     "[sync_oracle] trig_out seq=7 t_us=123456", logfmt.TrigOut),
    ("[sync_oracle] trig_in seq=%u t_us=%llu",
     "[sync_oracle] trig_in seq=7 t_us=123460", logfmt.TrigIn),
    ("[k1_sync] clk role=follower t_local_us=%llu est_offset_us=%lld ",
     "[k1_sync] clk role=follower t_local_us=5000010 "
     "est_offset_us=-42 rtt_us=8000 n=16", logfmt.Clk),
    ("[k1_sync] tx seq=%u t_leader_us=%llu",
     "[k1_sync] tx seq=3 t_leader_us=999", logfmt.Tx),
    ("[k1_sync] rx seq=%u t_leader_us=%llu t_local_us=%llu",
     "[k1_sync] rx seq=3 t_leader_us=999 t_local_us=5000999", logfmt.Rx),
    ("[k1_sync] apply seq=%u t_render_us=%llu",
     "[k1_sync] apply seq=3 t_render_us=5012000", logfmt.Apply),
]


def test_firmware_emits_oracle_grammar():
    cpp = _read(_CPP)
    for template, sample, rec_type in _GRAMMAR:
        assert template in cpp, f"firmware missing printf template: {template!r}"
        parsed = logfmt.parse_line(sample)
        assert isinstance(parsed, rec_type), (
            f"oracle cannot parse firmware line for {rec_type.__name__}: {sample!r}"
        )


def test_firmware_health_line_matches_grammar():
    cpp = _read(_CPP)
    # the health printf is split across two adjacent string literals
    for part in ("[k1_sync] health role=%s fps=%.2f heap_min=%u ap_p95_us=%u dial_linked=%d",
                 "loss=%u dup=%u"):
        assert part in cpp, f"firmware missing health template part: {part!r}"
    sample = ("[k1_sync] health role=leader fps=99.50 heap_min=60000 ap_p95_us=700 "
              "dial_linked=1 loss=0 dup=0")
    assert isinstance(logfmt.parse_line(sample), logfmt.Health)


def test_firmware_emits_strict_link_lifecycle_grammar():
    cpp = _read(_CPP)
    assert "[k1_sync] link down role=%s epoch=%u reason=%d" in cpp
    samples = (
        ("[k1_sync] begin role=leader", logfmt.Begin),
        ("[k1_sync] link up role=leader epoch=1 handle=3 mtu=247", logfmt.LinkUp),
        (
            "[k1_sync] negotiated role=leader epoch=1 interval_units=6 "
            "latency=0 mtu=247 phy_tx=2 phy_rx=2",
            logfmt.Negotiated,
        ),
        ("[k1_sync] link down role=leader epoch=1 reason=19", logfmt.LinkDown),
    )
    for sample, record_type in samples:
        assert isinstance(logfmt.parse_line(sample), record_type)


# --------------------------------------------------------------------------- #
# Compile-gating (production stays radio-clean)                               #
# --------------------------------------------------------------------------- #


def test_tu_fully_gated():
    cpp = _read(_CPP)
    assert "#ifdef SB_K1_SYNC_PROBE" in cpp
    assert "#endif  // SB_K1_SYNC_PROBE" in cpp
    # the very first meaningful directive gates the whole body
    first_ifdef = cpp.index("#ifdef SB_K1_SYNC_PROBE")
    assert cpp.index("namespace k1_sync") > first_ifdef


def test_ino_wiring_is_gated():
    ino = _read(_INO)
    for needle in ('#include "network/k1_sync_link.h"',
                   "k1_sync::begin();",
                   "k1_sync::poll();"):
        assert needle in ino, f".ino missing wiring: {needle!r}"
        assert _gated_by_sync_probe(ino, needle), f".ino wiring not gated: {needle!r}"


def test_serial_menu_wiring_is_gated():
    menu = _read(_MENU)
    for needle in ('#include "k1_sync_link.h"',
                   'strcmp(command_type, "sync_status")',
                   "k1_sync::status()",
                   'strcmp(command_type, "sync_fault")',
                   "k1_sync::set_fault(command_data)"):
        assert needle in menu, f"serial_menu missing wiring: {needle!r}"
        assert _gated_by_sync_probe(menu, needle), (
            f"serial_menu wiring not gated: {needle!r}"
        )


# --------------------------------------------------------------------------- #
# Load-bearing hard rules                                                      #
# --------------------------------------------------------------------------- #


def test_no_calibration_or_persistence():
    cpp = _read(_CPP)
    for forbidden in ("start_noise_cal", "save_config", "noise_cal"):
        assert forbidden not in cpp, f"sync TU must not touch {forbidden!r}"


def test_isr_is_iram_and_serial_free():
    cpp = _read(_CPP)
    m = re.search(r"void\s+IRAM_ATTR\s+trig_in_isr\s*\(\s*\)\s*\{(.*?)\n\}",
                  cpp, re.S)
    assert m, "trig_in_isr must be defined with IRAM_ATTR"
    body = m.group(1)
    assert "Serial" not in body, "ISR must not touch Serial"
    assert "malloc" not in body and "new " not in body, "ISR must not allocate"


def test_added_task_pinned_to_core1_low_prio():
    cpp = _read(_CPP)
    m = re.search(r"xTaskCreatePinnedToCore\((.*?)\)\s*:", cpp, re.S)
    assert m, "expected exactly one xTaskCreatePinnedToCore in the sync TU"
    args = [a.strip() for a in m.group(1).split(",")]
    # signature: fn, name, stack, param, priority, handle, coreID
    assert args[1].strip('"') == "k1_sync_io"
    assert args[4] == "1", f"task priority must be 1, got {args[4]}"
    assert args[6] == "1", f"task must be pinned to Core 1, got {args[6]}"


def test_single_added_task_only():
    cpp = _read(_CPP)
    assert cpp.count("xTaskCreatePinnedToCore") == 1, (
        "sync TU must add exactly one FreeRTOS task (the follower scan loop)"
    )


# --------------------------------------------------------------------------- #
# F1 link establishment and identity contract                                 #
# --------------------------------------------------------------------------- #


def _function_body(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:index]
    raise AssertionError(f"unterminated function: {signature}")


def _env_section(text: str, env: str) -> str:
    marker = f"[env:{env}]"
    start = text.index(marker)
    next_section = text.find("\n[", start + len(marker))
    return text[start:] if next_section < 0 else text[start:next_section]


def test_scan_start_uses_controller_state_and_checked_retry_in_both_tus():
    for path, prefix in ((_CPP, "[k1_sync_diag]"), (_REMOTED, "[ble_remoted_diag]")):
        text = _read(path)
        assert "scan->isScanning()" in text
        assert "const bool started = scan->start(0, false);" in text
        assert f'{prefix} scan_start ok=%u active=%u' in text
        assert "s_scanning = true" not in text


def test_advertising_payload_and_returns_are_honest():
    cpp = _read(_CPP)
    begin = _function_body(cpp, "void begin_leader()")
    assert begin.index("adv->enableScanResponse(true);") < begin.index(
        "adv->setName(kSyncDeviceName)"
    )
    assert "const bool uuid_ok = adv->addServiceUUID" in begin
    assert "const bool name_ok = adv->setName" in begin
    assert "const bool start_ok = adv->start()" in begin
    assert "const bool active = adv->isAdvertising()" in begin
    assert not re.search(r"=\s*adv->enableScanResponse", begin)


def test_sync_discovery_is_uuid_first_and_handles_both_callbacks():
    cpp = _read(_CPP)
    scan = cpp[cpp.index("class ScanCB") : cpp.index("ScanCB s_scan_cb")]
    assert "void consider(const NimBLEAdvertisedDevice* dev)" in scan
    assert "void onDiscovered(" in scan
    assert "void onResult(" in scan
    assert "isAdvertisingService(NimBLEUUID(kSyncServiceUuid))" in scan
    decision = scan[: scan.index("portENTER_CRITICAL")]
    assert "dev->getName() ==" not in decision


def test_raw_gap_connection_cannot_become_usable_link():
    cpp = _read(_CPP)
    server_connect = _function_body(
        cpp, "void onConnect(NimBLEServer* server, NimBLEConnInfo& info)"
    )
    client_connect = _function_body(
        cpp, "void onConnect(NimBLEClient* client)"
    )
    assert "s_connected = true;" in server_connect
    assert "s_linked = true;" not in server_connect
    assert "link up" not in server_connect
    assert "getAdvertising()->start" not in server_connect
    assert "s_connected = true;" in client_connect
    assert "s_linked = true;" not in client_connect
    assert "link up" not in client_connect


def test_leader_ready_requires_both_cccds_and_follower_clock_request():
    cpp = _read(_CPP)
    ready = _function_body(
        cpp, "void mark_leader_ready(const NegotiatedSnapshot& snapshot,"
    )
    assert "s_stream_subscribed &&" in ready
    assert "s_clock_subscribed &&" in ready
    assert "s_connection_generation == generation" in ready
    assert "s_conn_handle == snapshot.handle" in ready
    assert "s_ready_announcement = true;" in ready
    assert "s_linked = true;" in ready
    clock_write = _function_body(
        cpp,
        "void onWrite(NimBLECharacteristic* chr, NimBLEConnInfo& info) override",
    )
    assert clock_write.index("s_peer_clock_ready = true;") > clock_write.index(
        "v.length() < 13"
    )
    service = _function_body(cpp, "void leader_ready_service()")
    assert service.count("portENTER_CRITICAL(&s_state_mux)") == 1
    assert service.count("portEXIT_CRITICAL(&s_state_mux)") == 1
    assert "s_peer_clock_ready;" in service
    assert "s_negotiation_candidate_generation != generation" in service
    assert "mark_leader_ready(current, generation);" in service
    assert cpp.count("void onSubscribe(") == 2


def test_follower_link_up_is_after_both_subscriptions():
    cpp = _read(_CPP)
    connect = _function_body(cpp, "bool connect_and_subscribe()")
    stream_sub = connect.index("stream->subscribe")
    clock_sub = connect.index("clock->subscribe")
    linked = connect.index("s_linked = true;")
    link_log = connect.index("[k1_sync] link up role=follower")
    assert stream_sub < clock_sub < linked < link_log
    assert "s_ready_announcement = true;" in connect
    assert "s_ready_announcement = false;" in connect
    assert "s_link_down_pending = true;" in cpp


def test_follower_uses_local_characteristics_and_generation_revalidation():
    cpp = _read(_CPP)
    connect = _function_body(cpp, "bool connect_and_subscribe()")
    assert "NimBLERemoteCharacteristic* stream =" in connect
    assert "NimBLERemoteCharacteristic* clock =" in connect
    assert connect.count("connection_is_current(generation)") >= 3
    assert "s_client->connect(addr, false)" in connect
    assert "read_stable_client_snapshot(generation, &settled)" in connect
    stable = _function_body(
        cpp,
        "bool read_stable_client_snapshot(uint32_t generation,",
    )
    assert "kNegotiationSettleUs" in stable
    assert "same_snapshot(previous, current)" in stable
    assert connect.index("s_stream_rx = stream;") > connect.index(
        "clock->subscribe"
    )
    assert "if (!s_client)" in connect
    assert "connect_setup_fail role=follower step=create_client" in connect


def test_clock_transmission_has_one_owner_and_rejects_stale_responses():
    cpp = _read(_CPP)
    ingest = _function_body(
        cpp, "void ingest_clock_response(const uint8_t* data, size_t len,"
    )
    service = _function_body(cpp, "void follower_clock_service()")
    assert "send_clock_request()" not in ingest
    assert "s_clock_send_pending = true;" in ingest
    assert "response_seq != s_clock_inflight_seq" in ingest
    assert "if (s_clock_send_pending)" in service
    assert service.count("send_clock_request();") == 3
    send = _function_body(cpp, "bool send_clock_request()")
    assert "NimBLERemoteCharacteristic* const clock = s_clock_rx;" in send
    assert "clock->writeValue" in send
    callback = _function_body(
        cpp,
        "void on_clock_notify(NimBLERemoteCharacteristic*, uint8_t* data,"
    )
    assert "xQueueSend(s_clock_response_queue" in callback
    assert "ingest_clock_response" not in callback
    assert "response.t4_us = now_us();" in callback
    assert "response.generation = s_connection_generation;" in callback
    io_task = _function_body(cpp, "void sync_io_task(void*)")
    assert "xQueueReceive(s_clock_response_queue" in io_task
    assert "ingest_clock_response(response.data" in io_task
    assert "response.t4_us, response.generation" in io_task


def test_all_sync_ble_operations_are_owned_by_core1_io_task():
    cpp = _read(_CPP)
    poll = _function_body(cpp, "void poll()")
    io_task = _function_body(cpp, "void sync_io_task(void*)")
    for operation in (
        "leader_ready_service();",
        "leader_stream_service();",
        "follower_clock_service();",
    ):
        assert operation in io_task
        assert operation not in poll
    assert "writeValue" not in poll
    assert "notify(" not in poll


def test_leader_disconnect_defers_advertising_and_stream_is_generation_bound():
    cpp = _read(_CPP)
    disconnect = _function_body(
        cpp, "void onDisconnect(NimBLEServer*, NimBLEConnInfo&, int reason)"
    )
    stream = _function_body(cpp, "void leader_stream_service()")
    io_task = _function_body(cpp, "void sync_io_task(void*)")
    assert "s_adv_restart_pending = true;" in disconnect
    assert "getAdvertising" not in disconnect
    assert "adv->start()" not in disconnect
    assert "s_connection_generation == generation" in stream
    assert "s_conn_handle == handle" in stream
    assert "notify(pkt, sizeof(pkt), handle)" in stream
    assert "restart_pending && !connected" in io_task
    assert "adv->start()" in io_task


def test_status_replays_only_a_coherent_ready_snapshot():
    cpp = _read(_CPP)
    header = _read(_H)
    status = _function_body(cpp, "void status()")
    assert "void status();" in header
    assert "s_linked && s_ready_snapshot_valid && !s_ready_announcement" in status
    assert "SYNC_STATUS: role=%s linked=%u" in status
    assert "[k1_sync] link up role=%s epoch=%u handle=%u mtu=%u" in status
    assert "[k1_sync] negotiated role=%s epoch=%u interval_units=%u" in status
    assert status.index("if (!ready)") < status.index("[k1_sync] link up")


def test_requested_and_actual_ble_diagnostics_are_not_conflated():
    cpp = _read(_CPP)
    for callback in (
        "void onConnParamsUpdate(NimBLEConnInfo& info) override",
        "void onMTUChange(uint16_t mtu, NimBLEConnInfo& info) override",
        "void onMTUChange(NimBLEClient* client, uint16_t mtu) override",
        "void onPhyUpdate(NimBLEConnInfo& info, uint8_t tx_phy,",
        "void onPhyUpdate(NimBLEClient* client, uint8_t tx_phy,",
    ):
        assert callback in cpp
    assert "[k1_sync_diag] link_request role=leader" in cpp
    assert "[k1_sync_diag] link_request role=follower" in cpp
    assert "[k1_sync_diag] link_actual role=leader" in cpp
    assert "[k1_sync_diag] link_actual role=follower" in cpp
    assert "requested_octets=251 negotiated=UNMEASURED" in cpp
    assert not re.search(r"(?:const|bool)\s+\w+\s*=\s*server->updateConnParams", cpp)
    assert not re.search(r"(?:const|bool)\s+\w+\s*=\s*server->setDataLen", cpp)
    valid = _function_body(
        cpp, "bool valid_snapshot(const NegotiatedSnapshot& snapshot)"
    )
    assert "snapshot.interval_units == kConnIntervalUnits" in valid
    assert "snapshot.latency == kConnLatency" in valid
    assert "snapshot.mtu == kSyncMtu" in valid
    assert valid.count("BLE_GAP_LE_PHY_2M") == 2


def test_init_task_and_steady_state_failures_are_observable():
    cpp = _read(_CPP)
    remoted = _read(_REMOTED)
    assert cpp.count("NimBLEDevice::isInitialized() || NimBLEDevice::init") == 2
    assert "task_result == pdPASS" in cpp
    assert "stream_notify_fail" in cpp
    assert "clock_notify_fail" in cpp
    assert "clock_write_fail" in cpp
    assert "NimBLEDevice::isInitialized() || NimBLEDevice::init" in remoted
    assert "task_result == pdPASS" in remoted


def test_dual_role_capacity_and_remoted_symbol_guards():
    cpp = _read(_CPP)
    assert "CONFIG_BT_NIMBLE_MAX_CONNECTIONS >= 2" in cpp
    guard = "#if defined(K1_SYNC_ROLE_LEADER) && defined(SB_K1_BLE_REMOTED)"
    assert cpp.count(guard) >= 3
    assert "const int dial = sb_k1_ble_remoted_is_linked() ? 1 : 0;" in cpp


def test_leader_initialises_sync_before_optional_remoted():
    ino = _read(_INO)
    sync_leader = (
        "#if defined(SB_K1_SYNC_PROBE) && defined(K1_SYNC_ROLE_LEADER)\n"
        "  k1_sync::begin();\n"
        "#endif"
    )
    remoted = (
        "#ifdef SB_K1_BLE_REMOTED\n"
        "  sb_k1_ble_remoted_begin();\n"
        "#endif"
    )
    follower = (
        "#if defined(SB_K1_SYNC_PROBE) && defined(K1_SYNC_ROLE_FOLLOWER)\n"
        "  k1_sync::begin();\n"
        "#endif"
    )
    assert sync_leader in ino
    assert remoted in ino
    assert follower in ino
    assert ino.index(sync_leader) < ino.index(remoted) < ino.index(follower)


def test_case_a_environment_is_sync_only_and_exactly_pinned():
    section = _env_section(_read(_PIO), "k1_sync_probe_main_sync_only")
    assert "extends = env:k1_hardware_harness" in section
    assert "+<network/k1_sync_link.cpp>" in section
    assert "-DSB_K1_SYNC_PROBE" in section
    assert "-DK1_SYNC_ROLE_LEADER" in section
    assert "h2zero/NimBLE-Arduino@2.5.0" in section
    for forbidden in (
        "SB_K1_BLE_REMOTED",
        "ble_remoted_central.cpp",
        "k1_ble_midi_decoder.cpp",
    ):
        assert forbidden not in section


def test_case_a_is_registered_in_guard_and_exact_wrapper_allowlist():
    guard = _read(_GUARD)
    wrapper = _read(_WRAPPER)
    env = "k1_sync_probe_main_sync_only"
    assert env in guard
    assert env in wrapper
    assert f"|{env}|" in wrapper or f"|{env})" in wrapper
    assert 'pio run -e "$ENV"' in wrapper
    assert 'case "$ENV" in' in wrapper


def test_build_wrapper_rejects_case_a_suffix_and_argument_injection():
    for rejected in (
        "k1_sync_probe_main_sync_only_extra",
        "k1_sync_probe_main_sync_only --target upload",
    ):
        result = subprocess.run(
            ["bash", _WRAPPER, rejected],
            cwd=_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert "not in allowed list" in result.stderr


def test_remoted_probe_task_is_off_audio_core():
    remoted = _read(_REMOTED)
    begin = _function_body(remoted, "void sb_k1_ble_remoted_begin()")
    assert '&s_task, 1)' in begin
    assert "core=1" in begin


def test_remoted_ready_publish_is_generation_checked_and_not_caller_latched():
    remoted = _read(_REMOTED)
    connect = _function_body(remoted, "bool connect_and_subscribe()")
    task = _function_body(remoted, "void ble_task(void*)")
    assert "if (!s_client)" in connect
    assert "connect_setup_fail step=create_client" in connect
    assert connect.count("connection_is_current(generation)") >= 2
    assert "s_client->connect(addr, false)" in connect
    assert "s_connection_generation == generation" in connect
    assert "s_linked = true;" in connect
    assert "connect_and_subscribe()) {\n        s_linked = true;" not in task
    queue = _function_body(remoted, "void queue_confirmed_modes(bool force)")
    send = _function_body(remoted, "void send_pending_confirmation()")
    poll = _function_body(remoted, "void sb_k1_ble_remoted_poll(")
    assert "s_confirmation_pending = true;" in queue
    assert "NimBLERemoteCharacteristic* const rx_char = s_rx_char;" in send
    assert "rx_char->writeValue" in send
    assert "send_pending_confirmation();" in task
    assert "queue_confirmed_modes(force);" in poll
    assert "writeValue" not in poll


def test_header_does_not_claim_timestamp_delays_are_real_gate0_faults():
    header = _read(_H)
    assert "NOT Gate-0 delay proof" in header
    assert '"delay5"  — adds 5 ms to the printed consume stamp only' in header
    assert '"delay20" — adds 20 ms to the printed consume stamp only' in header
