"""Fault-evident guard for Tab5 procedural palette motion."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tab5_firmware/scripts/tab5_palette_motion_mutation.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("tab5_palette_motion_mutation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_positive_control_and_every_motion_mutant_are_evident():
    report = load_gate().run_gate(REPO_ROOT)
    assert report["passed"] is True
    assert report["positive_control"] == {"passed": True, "findings": []}
    assert report["mutation_count"] == 7
    assert all(row["killed"] for row in report["mutations"])
    assert all(
        row["expected_finding"] in row["observed_findings"]
        for row in report["mutations"]
    )


def test_cli_writes_a_deterministic_receipt(tmp_path: Path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    command = [sys.executable, str(SCRIPT), "--repo-root", str(REPO_ROOT), "--json"]
    first_run = subprocess.run(command + [str(first)], check=True, capture_output=True, text=True)
    subprocess.run(command + [str(second)], check=True, capture_output=True, text=True)
    assert "TAB5_PALETTE_MOTION_MUTATION_GATE=PASS mutants=7" in first_run.stdout
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text(encoding="utf-8"))["passed"] is True
