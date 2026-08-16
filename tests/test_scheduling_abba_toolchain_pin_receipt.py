"""Integrity checks for ABBA toolchain pin T identified by its receipt."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "evidence"
    / "gate2-abba-toolchain-pin-receipt.md"
)
COMPARATOR = ROOT / "scripts" / "regression-harness" / "k1_stage_attribution_abba_compare.py"


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


def test_receipt_identifies_toolchain_commit_not_itself():
    receipt = _load_receipt()
    t = receipt["toolchain_commit_sha"]
    h = receipt["harness_commit_sha"]
    assert re.fullmatch(r"[0-9a-f]{40}", t)
    assert re.fullmatch(r"[0-9a-f]{40}", h)
    assert receipt["receipt_commit_sha"] == "SELF_NOT_EMBEDDED"
    assert t != h
    assert _is_ancestor(t, "HEAD")
    assert _is_ancestor(h, "HEAD")
    assert receipt["FINAL_ABBA_TOOLCHAIN_PIN_SHA"] == t
    assert receipt["HARNESS_FIRMWARE_PIN_SHA"] == h
    assert receipt["B489_ABBA_FLASH_NOW"] == "HOLD"


def test_T_contains_frame_class_symbols():
    receipt = _load_receipt()
    t = receipt["toolchain_commit_sha"]
    blob = subprocess.check_output(
        ["git", "show", f"{t}:scripts/regression-harness/k1_stage_attribution_abba_compare.py"],
        cwd=ROOT,
    )
    text = blob.decode("utf-8")
    for symbol in (
        "def frame_class_distributions",
        "def compare_frame_classes",
        "def perturbation_limits",
        "EXCLUSIVE_FRAME_CLASSES",
    ):
        assert symbol in text
    assert hashlib.sha256(blob).hexdigest() == receipt["comparator_sha256"]


def test_H_still_has_production_96_d3():
    receipt = _load_receipt()
    h = receipt["harness_commit_sha"]
    cfg = _git("show", f"{h}:SPECTRASYNQ_K1_FIRMWARE/system/config_types.h")
    assert "DEFAULT_SAMPLES_PER_CHUNK 96" in cfg or "DEFAULT_SAMPLES_PER_CHUNK=96" in cfg
    contract = _git(
        "show",
        f"{h}:docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json",
    )
    assert '"samples_per_chunk": 96' in contract
    assert '"ap_arrival_period_us": 7500' in contract
