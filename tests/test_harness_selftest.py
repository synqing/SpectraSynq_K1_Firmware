"""Gate Fα in CI: the golden oracle must catch injected regressions.

Wraps scripts/regression-harness/golden/harness_selftest.py so the mutation
self-test runs in the host suite. If any planted regression slips through, the
harness is not fail-proof and this test fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness" / "golden"
sys.path.insert(0, str(HARNESS))

import harness_selftest  # noqa: E402


def test_harness_catches_injected_regressions():
    for label, passed in harness_selftest.run_selftest():
        assert passed, f"harness self-test failed: {label}"
