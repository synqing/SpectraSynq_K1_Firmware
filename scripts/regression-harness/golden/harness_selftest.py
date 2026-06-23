#!/usr/bin/env python3
"""Harness self-test — the Gate Fα proof (Phase F / L1), multi-oracle & generic.

Mutation testing OF THE HARNESS ITSELF. For every registered oracle, each
behaviour-changing edit in its MUTATIONS list (planted in a *copy* of the
firmware) MUST make the oracle output diverge from a freshly-captured baseline.
A mutation that slips through means the oracle is blind to a real regression —
NOT fail-proof — and the self-test fails.

Generic by design: it depends only on each oracle exposing NAME, capture(), and
MUTATIONS. The mutated re-capture is driven either via capture(firmware_root=...)
or, for oracles whose capture() uses a module-level FIRMWARE global, by
temporarily repointing that global at the mutated copy. This tolerates the
interface variations across independently-authored oracles.

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

from oracle_hostcompile import FIRMWARE, ROOT  # noqa: E402

GOLDEN_DIR = ROOT / "tests" / "golden"

# The registry — one entry per tap. Single source of truth (the golden gate
# imports this list too).
ORACLE_MODULES = [
    "oracle_onset_beat",
    "oracle_chord",
    "oracle_smart_director",
    "oracle_render",
    "oracle_gdft",   # GDFT spectrum tap (Phase A Lane 1) — int32 baseline; the
                     # int64-magnitude mutation proves the overflow is visible.
    "oracle_serial_replay",  # serial command->output replay (Phase A Lane 2 S3.0) —
                     # the 23-pure-CONFIG-setter behaviour-lock that gates the
                     # serial_menu.h handler extractions (S4+). Captures the triple
                     # (emitted text + CONFIG deltas + side-effect flags); 5 mutations
                     # each diverge a different channel (Gate-Fα teeth, not blind).
    # oracle_tempo — built + Gate-Fα-proven on mac (4/4 caught), but its 6400-rec
    #   golden has one discrete field that flips cross-platform on the CI runner
    #   (clang vs gcc boundary rounding). Re-enable after cross-platform
    #   stabilization (coarser trace / exclude the boundary field). Golden + oracle
    #   stay committed.
    # oracle_semantic_state — built; re-verify pending (import-time MODULE_CPPS
    #   binding bypasses the central mutation redirect). Re-enable once fixed.
    # oracle_spectrum_novelty — built; re-verify pending (mutations target the
    #   driver string, not firmware files). Re-enable once fixed.
]


def _load(module_name):
    spec = importlib.util.spec_from_file_location(module_name, HARNESS / f"{module_name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _norm(text):
    return "\n".join(line for line in text.splitlines() if line.strip())


def _mutated_capture(mod, pattern, replacement):
    """Apply a mutation to whichever source file in a firmware COPY matches it,
    then re-run the oracle against that copy. Returns None if the anchor is absent."""
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
            return None
        try:
            return mod.capture(firmware_root=dst)
        except TypeError:
            # Oracle uses a module-level FIRMWARE global and/or import-time-bound
            # absolute MODULE_CPPS paths. Repoint both at the mutated copy.
            saved_fw = getattr(mod, "FIRMWARE", None)
            saved_cpps = getattr(mod, "MODULE_CPPS", None)
            mod.FIRMWARE = dst
            if saved_cpps and saved_fw is not None:
                mod.MODULE_CPPS = [str(p).replace(str(saved_fw), str(dst)) for p in saved_cpps]
            try:
                return mod.capture()
            finally:
                mod.FIRMWARE = saved_fw
                if saved_cpps is not None:
                    mod.MODULE_CPPS = saved_cpps


def run_selftest():
    """Return list of (label, passed). All must pass for the harness to be trusted."""
    results = []
    for module_name in ORACLE_MODULES:
        mod = _load(module_name)
        name = getattr(mod, "NAME", module_name)
        try:
            b1 = mod.capture()
            b2 = mod.capture()
        except Exception as exc:  # noqa: BLE001
            results.append((f"[{name}] capture() runs ({type(exc).__name__}: {str(exc)[:120]})", False))
            continue
        results.append((f"[{name}] capture() is deterministic", _norm(b1) == _norm(b2)))
        muts = getattr(mod, "MUTATIONS", [])
        if not muts:
            results.append((f"[{name}] declares >=1 mutation", False))
            continue
        for pattern, replacement, desc in muts:
            mutated = _mutated_capture(mod, pattern, replacement)
            caught = (mutated is not None) and (_norm(mutated) != _norm(b1))
            results.append((f"[{name}] regression CAUGHT: {desc}", caught))
    return results


def main():
    ok = True
    for label, passed in run_selftest():
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    print("\nGATE_F-alpha:", "PROVEN — every oracle rejects its injected regressions" if ok
          else "FAILED — an oracle is BLIND or broken, do not trust it")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
