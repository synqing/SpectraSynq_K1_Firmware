"""Integrity checks for Gate-2 harness pin H identified by receipt R."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "evidence"
    / "gate2-harness-pin-receipt.md"
)

PINNED_PATHS = (
    ("platformio.ini", "platformio_ini_sha256"),
    (
        "scripts/regression-harness/device_ap_cadence_capture.py",
        "capture_runner_sha256",
    ),
    (
        "scripts/regression-harness/k1_stage_attribution_abba_compare.py",
        "initial_comparator_sha256",
    ),
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _parse_receipt(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key and value and " " not in key:
            out[key] = value
    return out


def _load_receipt() -> dict[str, str]:
    assert RECEIPT.is_file(), f"missing receipt: {RECEIPT}"
    return _parse_receipt(RECEIPT.read_text(encoding="utf-8"))


def _is_ancestor(commit: str, tip: str = "HEAD") -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, tip],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def test_receipt_identifies_harness_commit_not_itself():
    receipt = _load_receipt()
    h = receipt["harness_commit_sha"]
    assert re.fullmatch(r"[0-9a-f]{40}", h)
    assert receipt["receipt_commit_sha"] == "SELF_NOT_EMBEDDED"
    assert _is_ancestor(h, "HEAD")
    assert receipt["admissible_as"] == "MEASUREMENT_HARNESS_PIN_NOT_G2_CLOSE"
    assert receipt["B489_ABBA_FLASH_NOW"] == "HOLD_FOR_G0R"
    assert receipt["contract_id_still_controlling"] == "K1_SCHEDULING_GATE0_2026_08_15"


def test_pinned_paths_at_H_match_receipt_hashes():
    receipt = _load_receipt()
    h = receipt["harness_commit_sha"]
    for path, field in PINNED_PATHS:
        # Hash the exact git blob at H (no text decode / strip).
        blob = subprocess.check_output(["git", "cat-file", "blob", f"{h}:{path}"], cwd=ROOT)
        digest = hashlib.sha256(blob).hexdigest()
        assert digest == receipt[field], f"{path}: {digest} != {receipt[field]}"


def test_named_probe_envs_exist_at_H():
    receipt = _load_receipt()
    h = receipt["harness_commit_sha"]
    ini = _git("show", f"{h}:platformio.ini")
    assert "[env:k1_bench_scheduling_stage_min_probe]" in ini
    assert "[env:k1_bench_scheduling_stage_full_probe]" in ini


def test_production_tuple_at_H_is_still_96_d3():
    receipt = _load_receipt()
    h = receipt["harness_commit_sha"]
    cfg = _git("show", f"{h}:SPECTRASYNQ_K1_FIRMWARE/system/config_types.h")
    assert "#define DEFAULT_SAMPLES_PER_CHUNK 96" in cfg
    contract = json.loads(
        _git(
            "show",
            f"{h}:docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json",
        )
    )
    assert contract["production_tuple"]["samples_per_chunk"] == 96
    assert contract["production_tuple"]["ap_arrival_period_us"] == 7500
    assert contract["production_tuple"]["tempo_novelty_decimation"] == 3
    assert receipt["production_tuple_at_H"] == "12800/96/d3/7500"


def test_excluded_5s_pack_is_documented_not_committed_at_H():
    receipt = _load_receipt()
    h = receipt["harness_commit_sha"]
    text = RECEIPT.read_text(encoding="utf-8")
    assert "reason_excluded_from_Gate-2_proof" in text
    assert "20260816T-gate2-stage-attribution-781c40a9" in text
    listed = _git("ls-tree", "-r", "--name-only", h)
    assert "docs/forensics/runtime-evidence/20260816T-gate2-stage-attribution-781c40a9/" not in listed
    assert (
        "stage_attr_noplay_5s_20260816_031519__apcad.log" not in listed
    )
