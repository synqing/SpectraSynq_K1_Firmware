"""Captain stamp A: G0R amendment affirms deployed 7.5 ms; not a live pointer."""

from __future__ import annotations

import importlib.util
import json
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
LIVE_G0R_AMENDMENT = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "gate0"
    / "amendments"
    / "G0R_2026-08-16.draft.json"
)
HISTORICAL_G0R_CONTRACT_SHA256 = (
    "d17aa7c66b05281b79bafed2178f40f823ce92c04463b920d51fae63df919849"
)
CURRENT_CONTRACT_SHA256 = (
    "3f6f8856ae8a90bdc91347043d8d60fb91ecdbc5689092d08b249ca69aabbef0"
)
SERVICE_RESTAMP = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "gate0"
    / "amendments"
    / "G2_SERVICE_8000_2026-08-16.json"
)
TUPLE_96 = {
    "sample_rate_hz": 12800,
    "samples_per_chunk": 96,
    "tempo_novelty_decimation": 3,
    "ap_arrival_period_us": 7500,
}


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


def test_live_g0r_amendment_is_captain_stamped_a(oracle):
    doc = json.loads(LIVE_G0R_AMENDMENT.read_text(encoding="utf-8"))
    assert doc["status"] == "CAPTAIN_STAMPED"
    assert doc["captain_stamp"] == "A"
    assert doc["TEN_MS_AP_HOP_AUTHORISED"] is False
    assert doc["stamped_target_role"] == "DEPLOYED_CONTRACT"
    assert doc["candidate_scope"]["status"] == "NOT_CREATED"
    assert doc["candidate_scope"]["scope"] == "NONE"
    assert doc["candidate_scope"]["applicable_envs"] == []
    # Stamp A froze the hop against the then-deployed contract bytes.
    assert doc["old_contract_sha256"] == HISTORICAL_G0R_CONTRACT_SHA256
    for name, field in doc["fields"].items():
        assert "old" in field and "new" in field, name
        assert field["new"] == field["old"], name
    assert not (LIVE_G0R_AMENDMENT.parent / "live_pointer.json").exists()
    assert oracle.DEFAULT_CONTRACT.resolve() == CONTRACT.resolve()
    # Evening restamp moved the service p99 to 8000 without reopening 10 ms.
    assert oracle.sha256_file(CONTRACT) == CURRENT_CONTRACT_SHA256
    restamp = json.loads(SERVICE_RESTAMP.read_text(encoding="utf-8"))
    assert restamp["status"] == "CAPTAIN_STAMPED"
    assert restamp["fields"]["AP_SERVICE_P99_LIMIT_US"]["new"] == 8000
    assert restamp["fields"]["TEN_MS_AP_HOP_AUTHORISED"]["new"] is False
    assert restamp["prior_contract_sha256_at_g0r_stamp_a"] == HISTORICAL_G0R_CONTRACT_SHA256
    assert restamp["new_contract_sha256"] == CURRENT_CONTRACT_SHA256


def test_pointer_to_stamped_a_amendment_is_not_a_selectable_candidate(oracle, tmp_path):
    pointer = tmp_path / "pointer.json"
    pointer.write_text(
        json.dumps({"target_path": str(LIVE_G0R_AMENDMENT)}),
        encoding="utf-8",
    )
    with pytest.raises(oracle.Gate0Error, match="pointer_target_scope_not_candidate"):
        oracle.select_contract(
            ROOT,
            pointer_path=pointer,
            build_env="k1_hardware",
            measured_tuple=TUPLE_96,
        )
