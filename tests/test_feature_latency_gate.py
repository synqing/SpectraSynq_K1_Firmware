"""Guard the feature-latency gate itself.

The defect this gate was built for was a budget nothing read: gate0's
`feature_latency_contracts` carried eight fixed budgets and the Gate 0 runner
referenced them zero times. Replacing one unread number with an unverified
checker would repeat the mistake, so these tests do two things:

1. Positive controls — a healthy capture passes, and the gate reports honest
   coverage rather than a bare green.
2. Mutations — a deliberately blown budget must turn the RIGHT feature red while
   the others stay green. A gate that reddens everything is as useless as one
   that reddens nothing.

Every case runs on synthetic captures, so this file needs no device.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "scripts", "regression-harness", "k1_feature_latency_gate.py")
CONTRACT = os.path.join(
    ROOT, "docs", "forensics", "2026-08-15-freertos-scheduling-audit",
    "gate0", "contract.json",
)
BENCH_CAPTURE = os.path.join(
    ROOT, "docs", "forensics", "runtime-evidence",
    "20260910T-audio-to-led-latency", "bench-B489A500",
)


def _load_gate():
    spec = importlib.util.spec_from_file_location("k1_feature_latency_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gate():
    assert os.path.isfile(GATE), "feature latency gate script is missing"
    return _load_gate()


def _verdicts(gate, tmp_path, name, ap_leg_us, wire_us):
    capture = gate._synth(str(tmp_path / name), ap_leg_us=ap_leg_us, wire_us=wire_us)
    rows, n_fail, n_unmeasurable = gate.evaluate(
        gate.SELFTEST_CONTRACT, gate.load_capture(capture)
    )
    return {r[0]: r[3] for r in rows}, n_fail, n_unmeasurable


def test_self_test_battery_passes(gate):
    """The script's own five-case battery, including its two mutations."""
    assert gate.self_test() == 0


def test_script_self_test_exits_zero():
    """Same battery through the CLI, so a broken entry point is caught too."""
    result = subprocess.run(
        [sys.executable, GATE, "--self-test"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_positive_control_healthy_capture_passes(gate, tmp_path):
    verdicts, n_fail, _ = _verdicts(gate, tmp_path, "good", 4700, 4600)
    assert verdicts["ap_publication_freshness"] == "PASS"
    assert verdicts["raw_peak_vu"] == "PASS"
    assert n_fail == 0


def test_mutation_blown_ap_leg_turns_only_that_budget_red(gate, tmp_path):
    verdicts, n_fail, _ = _verdicts(gate, tmp_path, "bad_ap", 9200, 4600)
    assert verdicts["ap_publication_freshness"] == "FAIL"
    assert verdicts["raw_peak_vu"] == "PASS", "gate reddened an unrelated budget"
    assert n_fail == 1


def test_mutation_blown_end_to_end_turns_only_that_budget_red(gate, tmp_path):
    verdicts, n_fail, _ = _verdicts(gate, tmp_path, "bad_e2e", 4700, 21000)
    assert verdicts["raw_peak_vu"] == "FAIL"
    assert verdicts["ap_publication_freshness"] == "PASS"
    assert n_fail == 1


def test_unmeasurable_budgets_are_not_reported_as_passes(gate, tmp_path):
    """The whole point: a budget the capture cannot evaluate must say so."""
    verdicts, _, n_unmeasurable = _verdicts(gate, tmp_path, "honest", 4700, 4600)
    assert verdicts["rmt_output"] == "NOT_MEASURABLE"
    assert verdicts["tempo_beat_phase"] == "NOT_MEASURABLE"
    assert n_unmeasurable == 2


def test_empty_capture_never_reads_as_a_pass(gate, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    rows, n_fail, n_unmeasurable = gate.evaluate(
        gate.SELFTEST_CONTRACT, gate.load_capture(str(empty))
    )
    assert n_fail == 0
    assert n_unmeasurable == len(gate.SELFTEST_CONTRACT["feature_latency_contracts"])
    assert not any(r[3] == "PASS" for r in rows)


def test_real_contract_parses_and_reports_honest_coverage(gate):
    """Against the shipped contract and the 2026-09-10 bench capture.

    Pins the two facts that matter: the measurable budgets pass, and the gate
    admits how few of them there are. If a later change makes more budgets
    measurable this assertion should be raised deliberately, not silently.
    """
    if not (os.path.isfile(CONTRACT) and os.path.isdir(BENCH_CAPTURE)):
        pytest.skip("contract or bench capture not present")
    with open(CONTRACT) as handle:
        import json
        contract = json.load(handle)
    rows, n_fail, n_unmeasurable = gate.evaluate(
        contract, gate.load_capture(BENCH_CAPTURE)
    )
    verdicts = {r[0]: r[3] for r in rows}
    assert n_fail == 0, "shipped contract fails on the committed bench capture"
    assert verdicts["ap_publication_freshness"] == "PASS"
    assert verdicts["raw_peak_vu"] == "PASS"
    # Coverage is poor by design-of-record: most budgets need event timestamps
    # the capture does not carry. Recorded so the gap cannot be forgotten.
    evaluated = len(rows) - n_unmeasurable
    assert evaluated == 2, (
        "evaluable-budget count changed from 2 to %d; update this assertion "
        "deliberately and say why in the commit" % evaluated
    )
