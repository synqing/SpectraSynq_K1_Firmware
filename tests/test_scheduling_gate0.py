"""Gate 0 qualification for the K1 scheduling admission oracle."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "k1_scheduling_gate0.py"
CONTRACT = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "gate0"
    / "contract.json"
)
FIXTURE = ROOT / "tests" / "fixtures" / "scheduling_gate0" / "valid_oracle_run.json"
TRUST_ROOT = CONTRACT.parent / "trust_root.json"
FAULT_NAMES = json.loads(CONTRACT.read_text(encoding="utf-8"))["required_faults"]


def _load_module():
    spec = importlib.util.spec_from_file_location("k1_scheduling_gate0", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def oracle():
    return _load_module()


@pytest.fixture(scope="module")
def contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def valid_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_good_control_is_green(oracle, contract, valid_fixture):
    result = oracle.validate_run(contract, valid_fixture)
    assert result.records == 2
    assert result.checks > 50


def test_registered_fault_battery_is_exact_and_red(oracle, contract, valid_fixture):
    caught = oracle.run_fault_battery(contract, valid_fixture)
    assert set(caught) == set(contract["required_faults"])


def test_good_control_is_deterministic_three_times(oracle, contract, valid_fixture):
    results = [oracle.validate_run(contract, valid_fixture) for _ in range(3)]
    assert results[0] == results[1] == results[2]


@pytest.mark.parametrize(
    "fault_name",
    FAULT_NAMES,
)
def test_each_fault_rejects_independently(oracle, contract, valid_fixture, fault_name):
    mutation = oracle.fault_mutations(valid_fixture)[fault_name]
    with pytest.raises(oracle.Gate0Error):
        oracle.validate_run(contract, mutation)


def test_cli_fault_battery_reports_inner_red_witnesses():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--contract", str(CONTRACT), "fault-battery", str(FIXTURE)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert f"GATE0_FAULT_BATTERY PASS caught={len(FAULT_NAMES)}" in result.stdout
    for fault_name in json.loads(CONTRACT.read_text())["required_faults"]:
        assert fault_name in result.stdout


def test_frozen_trust_root_hashes_all_gate0_oracle_inputs(oracle):
    assert oracle.verify_trust_root(TRUST_ROOT) == 6


def test_source_manifest_is_deterministic_and_covers_first_party_roots(oracle):
    first = oracle.source_manifest(ROOT)
    second = oracle.source_manifest(ROOT)
    assert first == second
    paths = [row["path"] for row in first["rows"]]
    assert paths == sorted(set(paths))
    assert "platformio.ini" in paths
    for prefix in ("SPECTRASYNQ_K1_FIRMWARE/", "scripts/", "tests/"):
        assert any(path.startswith(prefix) for path in paths)
    # The exact Gate 0 population is anchored in gate0-implementation-provenance.json.
    # Later gates are expected to add their own source/tests; each admitted run records
    # a new exact manifest and compares expected versus observed rather than weakening
    # this oracle or pretending the repository must remain frozen forever.
    assert first["count"] >= 537


def test_contract_keeps_scheduler_rewrite_out_and_free_running_renderer_in():
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    locked = value["locked_architecture"]
    assert locked["ap_core"] == 0
    assert locked["vp_core"] == 1
    assert locked["broad_rtos_rewrite"] is False
    assert locked["multi_actor_audio_pipeline"] is False
    assert locked["added_pacing_clock"] is False
    assert value["vp_contract"]["cadence"] == "free_running_measured_no_added_clock"
    assert value["threshold_ownership"]["production_unit_may_edit_thresholds"] is False


def test_feature_contracts_have_named_origin_endpoint_and_budget():
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for feature in value["feature_latency_contracts"]:
        assert feature["origin"]
        assert feature["endpoint"]
        assert any(key in feature for key in ("budget_us", "budget_p99_us", "budget_formula"))


def test_no_production_file_imports_gate0_oracle():
    for path in (ROOT / "SPECTRASYNQ_K1_FIRMWARE").rglob("*"):
        if path.is_file() and path.suffix in {".ino", ".h", ".cpp"}:
            assert "k1_scheduling_gate0" not in path.read_text(encoding="utf-8", errors="ignore")
