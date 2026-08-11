"""Unit tests for the standalone Tab5 G1 mutation gate."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tab5_firmware/scripts/tab5_gate1_mutation.py"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("tab5_gate1_mutation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_positive_control_and_every_active_mutant_are_evident():
    gate = load_gate_module()
    report = gate.run_gate(REPO_ROOT)

    assert report["passed"] is True
    assert report["positive_control"]["passed"] is True
    assert report["coverage"] == [f"M{i}" for i in range(1, 10)]
    assert report["no_fail_everything_oracle"] is True
    assert all(row["changed"] for row in report["mutations"])
    assert all(row["killed"] for row in report["mutations"])
    assert all(row["finding"] in row["observed_findings"] for row in report["mutations"])


def test_variant_battery_covers_every_clause_of_m1_m9():
    gate = load_gate_module()
    counts = Counter(mutation.finding for mutation in gate.mutations())
    assert counts == {
        "M1": 6,
        "M2": 1,
        "M3": 2,
        "M4": 1,
        "M5": 8,
        "M6": 5,
        "M7": 5,
        "M8": 2,
        "M9": 5,
    }


def test_inert_or_ambiguous_text_mutation_is_rejected(tmp_path: Path):
    gate = load_gate_module()
    target = tmp_path / "target.txt"
    target.write_text("one one\n", encoding="utf-8")

    with pytest.raises(ValueError, match="target count"):
        gate.replace_exact(target, "one", "two")
    with pytest.raises(ValueError, match="target count"):
        gate.replace_exact(target, "missing", "two")


def test_cli_writes_deterministic_caller_owned_json(tmp_path: Path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    command = [
        sys.executable,
        str(SCRIPT),
        "--repo-root",
        str(REPO_ROOT),
        "--json",
    ]
    first_run = subprocess.run(command + [str(first)], check=True, capture_output=True, text=True)
    second_run = subprocess.run(command + [str(second)], check=True, capture_output=True, text=True)

    assert "TAB5_G1_MUTATION_GATE=PASS" in first_run.stdout
    assert first.read_bytes() == second.read_bytes()
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["mutation_count"] == 35
