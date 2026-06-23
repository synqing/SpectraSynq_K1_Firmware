"""Unit tests for --strict harness semantics (SC-2)."""

from __future__ import annotations

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


def test_strict_rejects_control_without_k1_port() -> None:
    harness = load_harness()
    result = {
        "command": "UI_SLIDER BRIGHTNESS 70",
        "expected_control": "primary.photons",
        "expected_value": "0.7000",
        "ack_line": "OK UI_SLIDER name=BRIGHTNESS value=70",
        "send_line": None,
        "result_line": None,
        "k1_line": None,
        "send_id": None,
        "result_fields": {},
        "ok": True,
    }
    failures = harness.evaluate_strict_result(result, k1_port=None, strict=True)
    assert any("requires k1_port" in item for item in failures)


def test_strict_rejects_ack_only_pass() -> None:
    harness = load_harness()
    result = {
        "command": "UI_SLIDER COLOUR 61",
        "expected_control": "primary.chroma",
        "expected_value": "0.6100",
        "ack_line": "OK UI_SLIDER name=COLOUR value=61",
        "send_line": None,
        "result_line": None,
        "k1_line": None,
        "send_id": None,
        "result_fields": {},
        "ok": True,
    }
    failures = harness.evaluate_strict_result(result, k1_port="/dev/k1", strict=True)
    assert any("missing Tab5 send line" in item for item in failures)
    assert any("missing Tab5 result line" in item for item in failures)
    assert any("missing K1 control.set line" in item for item in failures)


def test_strict_accepts_correlated_control_proof() -> None:
    harness = load_harness()
    result = {
        "command": "UI_SLIDER BRIGHTNESS 70",
        "expected_control": "primary.photons",
        "expected_value": "0.7000",
        "ack_line": "OK UI_SLIDER name=BRIGHTNESS value=70",
        "send_line": "[UI] Sending K1 control id=20 control=primary.photons value=0.7000",
        "result_line": "[UI] K1 result ok=1 id=20 seq=6 control=primary.photons value=0.7000",
        "k1_line": "[K1WS] client 0 control.set id=20 control=primary.photons",
        "send_id": "20",
        "result_fields": {"id": "20", "control": "primary.photons", "value": "0.7000", "ok": "1"},
        "ok": True,
    }
    assert harness.evaluate_strict_result(result, k1_port="/dev/k1", strict=True) == []


def test_surface_drift_oracle_secondary_chroma() -> None:
    harness = load_harness()
    selected = "primary"
    _, selected = harness.expected_control("UI_SURFACE SECONDARY", selected)
    assert selected == "secondary"
    control, selected = harness.expected_control("UI_SLIDER COLOUR 61", selected)
    assert control == "secondary.chroma"
    assert harness.expected_value("UI_SLIDER COLOUR 61", selected) == "0.6100"


def test_summarize_strict_flags_unhealthy_status() -> None:
    harness = load_harness()
    results = [{"command": "PING", "expected_control": None, "ok": True}]
    health_samples = [
        {
            "line": "OK UI_STATUS ws=DISC k1_seen=0",
            "fields": {"ws": "DISC", "k1_seen": "0"},
            "ok": False,
        }
    ]
    _, _, failures = harness.summarize_strict(
        results,
        k1_port="/dev/k1",
        strict=True,
        health_samples=health_samples,
        require_health=True,
    )
    assert failures
