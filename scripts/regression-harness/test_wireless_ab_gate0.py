#!/usr/bin/env python3
"""pytest shim: run Gate 0 (the wireless_ab_bench fault-evidence selftest) in CI.

The admission gate is the trust root for the BLE/WiFi coexistence A/B — it must
run in INFRASTRUCTURE, not depend on someone remembering
`python3 gate0_selftest.py`. This collects under the default pytest discovery
(test_*.py / test_*); it is a thin wrapper over gate0_selftest.main().
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_GATE0 = Path(__file__).resolve().parent / "gate0_selftest.py"
_spec = importlib.util.spec_from_file_location("gate0_selftest", _GATE0)
_gate0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate0)


def test_wireless_ab_gate0_is_fault_evident() -> None:
    """Every known-bad capture (cb1/cb2 + synthetic + corrupt files) is rejected,
    every valid capture is admitted, and compare refuses PASS/FAIL on any set
    containing a rejected/corrupt capture."""
    assert _gate0.main() == 0, "Gate 0 RED — wireless_ab_bench admission has a blind spot"


if __name__ == "__main__":
    raise SystemExit(_gate0.main())
