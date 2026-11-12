"""Gate Fα mutation self-test — RETIRED from execution on 10 Nov 2026
(Modernes C++ next phase, Stage A). This file now checks the retirement holds.

What it used to do: harness_selftest.run_selftest() ran every registered oracle
twice, then for each MUTATIONS entry copied the firmware tree, rewrote a
.cpp/.h file with a planted fault and recompiled/re-captured it — firmware
mutants built on every `pytest tests/` (every commit gate and replay host check).

Why: the Captain's standing order of 22 Oct 2026 bans planted-fault / mutation
testing and repeated runs to "prove" a check ("One real test of the actual
behaviour per change, run once"; ~/.claude/CLAUDE.md). The previous phase still
executed these mutants and repointed five serial anchors to keep them passing;
that was a policy violation, not harmless anchor upkeep.

Coverage after retirement:
* tests/test_golden_master.py still runs EVERY registered oracle once against
  its frozen golden (behaviour lock) and checks the golden manifest.
* Behavioural tests of real production code remain.
* Lost by design: the per-oracle planted-fault proof and the run-twice
  determinism probe — exactly the work the order bans.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness" / "golden"
sys.path.insert(0, str(HARNESS))

import harness_selftest  # noqa: E402


def test_mutant_self_test_refuses_to_build_firmware_mutants(monkeypatch, tmp_path):
    monkeypatch.delenv("K1_ALLOW_FIRMWARE_MUTANTS", raising=False)
    copies = []
    monkeypatch.setattr(harness_selftest.shutil, "copytree",
                        lambda *a, **k: copies.append(a) or (_ for _ in ()).throw(AssertionError("copied")))
    with pytest.raises(RuntimeError, match="retired"):
        harness_selftest.run_selftest()
    assert copies == []  # no firmware copy, no mutant, no capture


def test_golden_registry_still_feeds_the_behaviour_lock():
    # The golden master imports ORACLE_MODULES from here; retirement must not
    # empty it.
    assert len(harness_selftest.ORACLE_MODULES) >= 10
