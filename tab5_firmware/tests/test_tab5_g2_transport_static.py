"""G2 source-bound ownership, RSSI and production-configuration gates."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = ROOT / "tab5_firmware/src/ble_midi_transport.cpp"
TRANSPORT_H = ROOT / "tab5_firmware/src/ble_midi_transport.h"
UI = ROOT / "tab5_firmware/src/deck_ui.cpp"
MAIN = ROOT / "tab5_firmware/src/main.cpp"
PIO = ROOT / "tab5_firmware/platformio.ini"


def _class_body(text: str, name: str) -> str:
    start = text.index(f"class {name}")
    end = text.index("\n};", start) + 3
    return text[start:end]


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
                return text[brace + 1 : index]
    raise AssertionError(f"unterminated function {signature}")


def test_nimble_callbacks_are_bounded_copy_only():
    text = TRANSPORT.read_text(encoding="utf-8")
    callbacks = "\n".join(
        _class_body(text, name)
        for name in (
            "MidiServerCallbacks",
            "MidiCharacteristicCallbacks",
            "StateCharacteristicCallbacks",
        )
    )
    forbidden = (
        r"\bString\b",
        r"\bSerial\b",
        r"\bdeck_(?:state|ui|tx|input)",
        r"\blv_[A-Za-z0-9_]*\s*\(",
        r"\bble_gap_[A-Za-z0-9_]*\s*\(",
        r"\bstartAdvertising\s*\(",
        r"\b(?:malloc|calloc|realloc|new)\b",
    )
    for pattern in forbidden:
        assert not re.search(pattern, callbacks), pattern
    assert "enqueue_link_event" in callbacks
    assert callbacks.count("enqueue_payload_event") == 2
    assert "getData()" in callbacks and "getLength()" in callbacks
    one_arg_connect = _function_body(
        callbacks, "void onConnect(BLEServer* server) override"
    )
    descriptor_connect = _function_body(
        callbacks, "void onConnect(BLEServer* server, ble_gap_conn_desc* desc) override"
    )
    assert "enqueue_link_event" not in one_arg_connect
    assert descriptor_connect.count("enqueue_link_event") == 1


def test_link_queue_cannot_be_starved_by_payloads_and_loss_is_fail_closed():
    text = TRANSPORT.read_text(encoding="utf-8")
    connect = _function_body(
        text,
        "static void apply_connected(uint16_t conn_handle, uint32_t ingress_generation)",
    )
    assert "gLinkQueue" in text and "gPayloadQueue" in text
    assert "kPayloadDrainLimit = 8" in text
    assert "kPayloadDrainBudgetUs = 1000" in text
    assert "gIngressLoss.store(true" in text
    assert 'deck_state_rx_on_ingress_loss("transport_queue")' in text
    assert "deck_state_rx_recovery_required()" in text
    assert "purge_payload_queue();" in text
    assert "gIngressHandle.store(conn_handle" in text
    assert "gIngressHandle.load(std::memory_order_acquire)" in text
    assert "gIngressGeneration" in text
    assert "event.ingress_generation != gConnectionGeneration" in text
    assert "purge_payload_queue" not in connect
    assert "kRecoveryDisconnectDeadlineMs = 2500" in text
    assert 'apply_disconnected("RECOVERY_TIMEOUT")' in text


def test_rssi_is_one_inflight_worker_owned_and_ui_is_cache_only():
    text = TRANSPORT.read_text(encoding="utf-8")
    getter = _function_body(text, "bool connectionRssi(int8_t* out_dbm)")
    worker = _function_body(text, "static void rssi_worker(void*)")
    assert "ble_gap_conn_rssi" not in getter
    assert "gCachedRssi" in getter
    assert worker.count("ble_gap_conn_rssi") == 1
    assert "gRssiWorkerBusy" in text
    assert "gRssiInFlight" in text
    assert "kRssiIntervalMs = 2000" in text
    assert "kRssiDeadlineMs = 2200" in text
    assert "30000UL" in text
    assert "RSSI_UNKNOWN_HANDLE" in text
    assert "RSSI_DISCONNECTED" in text
    assert "RSSI_FATAL" in text
    assert "gRssiStaleCompletions" in text
    ui = UI.read_text(encoding="utf-8")
    assert "gLastRssiPollMs" not in ui
    assert "Cache-only read" in ui
    assert "ble_gap_conn_rssi" not in ui
    assert "Never sends HCI or blocks" in TRANSPORT_H.read_text(encoding="utf-8")


def test_production_diagnostics_fail_closed_and_transport_starts_last():
    transport = TRANSPORT.read_text(encoding="utf-8")
    pio = PIO.read_text(encoding="utf-8")
    assert '#error "Production Tab5 build cannot enable HCI or per-value diagnostics"' in transport
    production = pio[pio.index("[env:tab5_p4]") : pio.index("[env:tab5_p4_hci_diag]")]
    assert "-DTAB5_PRODUCTION_BUILD=1" in production
    assert "-DTAB5_HCI_PATH_DIAG=0" in production
    assert "-DTAB5_BLE_VERBOSE_DIAG=0" in production
    main = MAIN.read_text(encoding="utf-8")
    assert main.index("Deck_UI_Init") < main.index("init_transport();")
