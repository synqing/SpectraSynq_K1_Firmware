#!/usr/bin/env python3
"""Harness self-test — the Gate Fα proof (Phase F / L1), multi-oracle.

Mutation testing OF THE HARNESS ITSELF. For every registered oracle, each
behaviour-changing edit in its MUTATIONS list (planted in a *copy* of the
firmware) MUST make the oracle output diverge from the frozen golden. A mutation
that slips through means the oracle is blind to a real regression — NOT
fail-proof — and the self-test fails.

This is the objective evidence that autonomous behaviour-preserving lanes can be
trusted to ride these oracles: they provably reject injected regressions.

Each oracle module is self-describing — it exports NAME, MODULE_CPPS, DEFINES,
DRIVER, capture(), and MUTATIONS. Registering a new tap is one line below.

Run:  python harness_selftest.py
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))

from oracle_hostcompile import host_compile_run, FIRMWARE, ROOT  # noqa: E402

GOLDEN_DIR = ROOT / "tests" / "golden"

# The registry — one entry per tap. Extended as oracles land + pass Gate Fα.
ORACLE_MODULES = [
    "oracle_onset_beat",
]


def _load(module_name):
    spec = importlib.util.spec_from_file_location(module_name, HARNESS / f"{module_name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _capture(mod, firmware_root):
    rc, out, err = host_compile_run(
        mod.MODULE_CPPS, mod.DRIVER, defines=mod.DEFINES, firmware_root=firmware_root)
    if rc != 0:
        raise RuntimeError(f"[{mod.NAME}] oracle compile/run failed (rc={rc}):\n{err}")
    return out


def _mutated_capture(mod, pattern, replacement):
    """Apply a mutation to whichever source file in a firmware COPY matches it."""
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "SPECTRASYNQ_K1_FIRMWARE"
        shutil.copytree(FIRMWARE, dst)
        target = None
        for f in dst.rglob("*"):
            if f.suffix in (".cpp", ".h") and f.is_file():
                text = f.read_text(encoding="utf-8", errors="ignore")
                if re.search(pattern, text):
                    f.write_text(re.sub(pattern, replacement, text, count=1), encoding="utf-8")
                    target = f
                    break
        if target is None:
            raise RuntimeError(f"[{mod.NAME}] mutation anchor not found anywhere: {pattern}")
        return _capture(mod, dst)


def run_selftest():
    """Return list of (label, passed). All must pass for the harness to be trusted."""
    results = []
    for module_name in ORACLE_MODULES:
        mod = _load(module_name)
        golden = (GOLDEN_DIR / f"{mod.NAME}.golden.jsonl").read_text(encoding="utf-8")
        results.append((f"[{mod.NAME}] baseline (unmutated copy) reproduces golden",
                        _capture(mod, FIRMWARE) == golden))
        if not getattr(mod, "MUTATIONS", None):
            results.append((f"[{mod.NAME}] declares >=1 proven mutation", False))
            continue
        for pattern, replacement, desc in mod.MUTATIONS:
            diverged = _mutated_capture(mod, pattern, replacement) != golden
            results.append((f"[{mod.NAME}] regression CAUGHT: {desc}", diverged))
    return results


def main():
    ok = True
    for label, passed in run_selftest():
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    print("\nGATE_F-alpha:", "PROVEN — every oracle rejects its injected regressions" if ok
          else "FAILED — an oracle is BLIND to a regression, do not trust it")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
