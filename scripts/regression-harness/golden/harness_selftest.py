#!/usr/bin/env python3
"""Harness self-test — the Gate Fα proof (Phase F / L1).

Mutation testing OF THE HARNESS ITSELF. For each deliberate behaviour change
planted in a *copy* of the firmware, the oracle output MUST diverge from the
frozen golden. A mutation that slips through means the harness is blind to a real
regression — i.e. NOT fail-proof — and the self-test fails.

This is the objective evidence that autonomous behaviour-preserving lanes can be
trusted to ride this oracle: the oracle provably rejects injected regressions.

Run:  python harness_selftest.py
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))

from oracle_hostcompile import host_compile_run, FIRMWARE, ROOT  # noqa: E402
import oracle_onset_beat as onset  # noqa: E402

GOLDEN = ROOT / "tests" / "golden" / "onset_beat.golden.jsonl"
MODULE_REL = Path("audio") / "sb_onset_beat.cpp"

# (regex anchor, replacement, description) — each is a behaviour-changing edit
# PROVEN to shift the golden, spanning distinct detector mechanisms (per-band
# threshold, per-band refractory, transient peak-wait). Verified diverged lines:
# KICK_K=228, KICK_REFR=264, HIHAT_REFR=171, PEAK_WAIT=67.
MUTATIONS = [
    (r"SBV2_KICK_K\s*=\s*0\.8f", "SBV2_KICK_K = 6.0f", "raise kick threshold factor (0.8->6.0)"),
    (r"SBV2_KICK_REFR\s*=\s*6;", "SBV2_KICK_REFR = 12;", "widen kick refractory (6->12 frames)"),
    (r"SBV2_HIHAT_REFR\s*=\s*3;", "SBV2_HIHAT_REFR = 9;", "widen hihat refractory (3->9 frames)"),
    (r"SBV2_PEAK_WAIT\s*=\s*4;", "SBV2_PEAK_WAIT = 16;", "widen transient peak-wait (4->16 frames)"),
]


def _capture(firmware_root) -> str:
    rc, out, err = host_compile_run(
        onset.MODULE_CPPS, onset.DRIVER, defines=onset.DEFINES, firmware_root=firmware_root)
    if rc != 0:
        raise RuntimeError(f"oracle compile/run failed (rc={rc}):\n{err}")
    return out


def _mutated_capture(pattern, replacement) -> str:
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "SPECTRASYNQ_K1_FIRMWARE"
        shutil.copytree(FIRMWARE, dst)
        cpp = dst / MODULE_REL
        text = cpp.read_text(encoding="utf-8")
        new, n = re.subn(pattern, replacement, text, count=1)
        if n == 0:
            raise RuntimeError(f"mutation anchor not found: {pattern}")
        cpp.write_text(new, encoding="utf-8")
        return _capture(dst)


def run_selftest():
    """Return list of (label, passed). All must pass for the harness to be trusted."""
    golden = GOLDEN.read_text(encoding="utf-8")
    results = [("baseline (unmutated copy) reproduces golden", _capture(FIRMWARE) == golden)]
    for pattern, replacement, desc in MUTATIONS:
        diverged = _mutated_capture(pattern, replacement) != golden
        results.append((f"regression CAUGHT: {desc}", diverged))
    return results


def main():
    ok = True
    for label, passed in run_selftest():
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    print("\nGATE_F-alpha:", "PROVEN — harness rejects injected regressions" if ok
          else "FAILED — harness is BLIND to a regression, do not trust it")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
