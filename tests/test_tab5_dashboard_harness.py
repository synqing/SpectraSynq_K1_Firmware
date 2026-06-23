import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "tab5_k1_dashboard_harness.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("tab5_k1_dashboard_harness", HARNESS)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_key_value_fields() -> None:
    harness = load_harness()
    fields = harness.parse_key_value_fields(
        'OK UI_STATUS ws=OK wifi=OK last_error=none control="primary.chroma" value=0.6100'
    )

    assert fields["ws"] == "OK"
    assert fields["wifi"] == "OK"
    assert fields["last_error"] == "none"
    assert fields["control"] == "primary.chroma"
    assert fields["value"] == "0.6100"


def test_parse_status_and_result_lines() -> None:
    harness = load_harness()

    status = harness.parse_ui_status(
        "OK PERF_STATUS ws=OK wifi=OK pending_count=0 k1_age_ms=42 "
        "ws_reconnects=1 lvgl_flush_max_ms=7 antenna_probe=done"
    )
    antenna = harness.parse_ui_status(
        "OK ANTENNA_STATUS ws=OK wifi=OK antenna_selector=LOW antenna_selected_rssi=-43"
    )
    result = harness.parse_tab5_result_line(
        "[UI] K1 result ok=1 id=37 seq=9 control=primary.photons value=0.7000"
    )
    send = harness.parse_tab5_send_line(
        "[UI] Sending K1 control id=37 control=primary.photons value=0.7000"
    )
    k1 = harness.parse_k1_control_line(
        "[K1WS] client 0 control.set id=37 control=primary.photons"
    )

    assert status["pending_count"] == "0"
    assert status["antenna_probe"] == "done"
    assert antenna["antenna_selector"] == "LOW"
    assert antenna["antenna_selected_rssi"] == "-43"
    assert send["id"] == "37"
    assert result["id"] == "37"
    assert result["control"] == "primary.photons"
    assert k1["control"] == "primary.photons"


def test_expected_control_and_value_mapping() -> None:
    harness = load_harness()

    control, selected = harness.expected_control("UI_SLIDER BRIGHTNESS 70", "primary")
    assert control == "primary.photons"
    assert selected == "primary"
    assert harness.expected_value("UI_SLIDER BRIGHTNESS 70", selected) == "0.7000"

    control, selected = harness.expected_control("UI_SURFACE SECONDARY", selected)
    assert control is None
    assert selected == "secondary"

    control, selected = harness.expected_control("UI_SCENE ASSIST", selected)
    assert control == "scene.smart"
    assert selected == "secondary"
    assert harness.expected_value("UI_SCENE ASSIST", selected) == "assist"


def healthy_fields() -> dict[str, str]:
    return {
        "ws": "OK",
        "wifi": "OK",
        "ws_status": "CONNECTED",
        "ws_last_error": "none",
        "k1_seen": "1",
        "k1_age_ms": "42",
        "pending_count": "0",
        "last_error": "none",
        "rssi_dbm": "-52.0",
        "k1_tx_dropped": "0",
        "antenna": "selector_low",
        "antenna_selector": "LOW",
        "antenna_selected_selector": "LOW",
        "antenna_latch": "0",
        "antenna_mapping": "verified",
        "antenna_selected_rssi": "-43",
        "antenna_probe": "done",
        "antenna_mapping_suspect": "0",
        "ws_loop_max_ms": "12",
        "lvgl_handler_max_ms": "18",
        "lvgl_flush_max_ms": "9",
    }


def test_evaluate_health_accepts_nominal_status() -> None:
    harness = load_harness()

    assert harness.evaluate_health(healthy_fields()) == []


def test_evaluate_health_rejects_bad_rssi_and_never_seen_state() -> None:
    harness = load_harness()

    bad_rssi = healthy_fields()
    bad_rssi["rssi_dbm"] = "-69.0"
    assert any("rssi_dbm" in failure for failure in harness.evaluate_health(bad_rssi))

    never_seen = healthy_fields()
    never_seen["k1_seen"] = "0"
    never_seen["k1_age_ms"] = "0"
    failures = harness.evaluate_health(never_seen)
    assert any("k1_seen=0" in failure for failure in failures)
    assert any("k1_age_ms invalid" in failure for failure in failures)


def test_evaluate_health_rejects_stale_pending_errors_and_drops() -> None:
    harness = load_harness()

    stale = healthy_fields()
    stale["k1_age_ms"] = "9000"
    assert any("k1_age_ms" in failure for failure in harness.evaluate_health(stale))

    pending = healthy_fields()
    pending["pending_count"] = "1"
    assert any("pending_count=1" in failure for failure in harness.evaluate_health(pending))

    last_error = healthy_fields()
    last_error["last_error"] = "timeout"
    assert any("last_error=timeout" in failure for failure in harness.evaluate_health(last_error))

    ws_error = healthy_fields()
    ws_error["ws_last_error"] = "disconnected"
    assert any("ws_last_error=disconnected" in failure for failure in harness.evaluate_health(ws_error))

    tx_drop = healthy_fields()
    tx_drop["k1_tx_dropped"] = "1"
    assert any("k1_tx_dropped=1" in failure for failure in harness.evaluate_health(tx_drop))


def test_evaluate_health_rejects_slow_loops_and_antenna_ambiguity() -> None:
    harness = load_harness()

    slow_ws = healthy_fields()
    slow_ws["ws_loop_max_ms"] = "251"
    assert any("ws_loop_max_ms=251" in failure for failure in harness.evaluate_health(slow_ws))

    failed_probe = healthy_fields()
    failed_probe["antenna_probe"] = "failed"
    assert any("antenna_probe=failed" in failure for failure in harness.evaluate_health(failed_probe))

    suspect_mapping = healthy_fields()
    suspect_mapping["antenna_mapping_suspect"] = "1"
    suspect_mapping["antenna_mapping"] = "suspect"
    assert harness.evaluate_health(suspect_mapping) == []

    weak_selected = healthy_fields()
    weak_selected["antenna_mapping_suspect"] = "1"
    weak_selected["antenna_mapping"] = "suspect"
    weak_selected["antenna_selected_rssi"] = "-70"
    assert any("antenna_selected_rssi=-70" in failure for failure in harness.evaluate_health(weak_selected))

    bad_latch = healthy_fields()
    bad_latch["antenna_latch"] = "1"
    assert any("antenna_latch=1 expected=0 for LOW" in failure for failure in harness.evaluate_health(bad_latch))


def test_collect_status_health_extracts_status_samples() -> None:
    harness = load_harness()
    fields = " ".join(f"{key}={value}" for key, value in healthy_fields().items())

    samples = harness.collect_status_health([
        {"dir": "tx", "line": "PERF_STATUS"},
        {"dir": "rx", "line": f"OK PERF_STATUS {fields}"},
    ])

    assert len(samples) == 1
    assert samples[0]["ok"] is True


def test_parse_ui_status_includes_v3_page_fields() -> None:
    harness = load_harness()
    status = harness.parse_ui_status(
        'OK UI_STATUS ws=OK wifi=OK ui_page=HEALTH health=LIVE link=LIVE ack_pending=0 '
        "overlay=NONE pending_count=0"
    )
    assert status["ui_page"] == "HEALTH"
    assert status["health"] == "LIVE"
    assert status["link"] == "LIVE"
    assert status["ack_pending"] == "0"
    assert status["overlay"] == "NONE"
    assert status["pending_count"] == "0"


def test_evaluate_health_rejects_fault_link_state() -> None:
    harness = load_harness()
    fault = healthy_fields()
    fault["link"] = "FAULT"
    fault["health"] = "FAULT"
    failures = harness.evaluate_health(fault)
    assert any("link=FAULT" in item for item in failures)
