"""Golden-master behaviour-equivalence gate (Phase F / L1), multi-oracle.

Re-runs every registered oracle and asserts its full numeric output matches the
frozen golden (ints/bools exact, floats within tolerance), and that the golden
files have not been edited (checksum manifest — anti-gaming). This is the
behaviour contract a refactor must preserve: if a number here changes, behaviour
changed.

Oracles are self-describing (export NAME, capture(), MUTATIONS). Registering a
new tap is one line in scripts/regression-harness/golden/harness_selftest.py
(ORACLE_MODULES) — this gate imports the same list.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "tests" / "golden"
HARNESS = ROOT / "scripts" / "regression-harness" / "golden"
sys.path.insert(0, str(HARNESS))

from harness_selftest import ORACLE_MODULES  # single source of truth for the registry

FLOAT_TOL = 1e-4


def _parse(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _load_oracle(module_name):
    spec = importlib.util.spec_from_file_location(module_name, HARNESS / f"{module_name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _field_matches(fresh, gold):
    if isinstance(gold, bool):
        return fresh == gold
    if isinstance(gold, float):
        return abs(float(fresh) - gold) <= FLOAT_TOL
    return fresh == gold  # int / str exact


class GoldenMasterTest(unittest.TestCase):
    def test_manifest_integrity(self):
        """Anti-gaming: a refactor lane must not edit the golden/oracle output."""
        manifest = (GOLDEN_DIR / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
        self.assertTrue([l for l in manifest if l.strip()], "MANIFEST.sha256 is empty")
        for line in manifest:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            digest, name = parts[0], parts[-1]
            actual = hashlib.sha256((GOLDEN_DIR / name).read_bytes()).hexdigest()
            self.assertEqual(actual, digest, f"golden '{name}' checksum drift — was it edited?")

    def test_oracles_reproduce_golden(self):
        for module_name in ORACLE_MODULES:
            with self.subTest(oracle=module_name):
                mod = _load_oracle(module_name)
                fresh = _parse(mod.capture())
                gold = _parse((GOLDEN_DIR / f"{mod.NAME}.golden.jsonl").read_text(encoding="utf-8"))
                self.assertEqual(len(fresh), len(gold),
                                 f"{mod.NAME}: record-count drift {len(fresh)} vs {len(gold)}")
                for i, (f, g) in enumerate(zip(fresh, gold)):
                    self.assertEqual(set(f), set(g), f"{mod.NAME} rec {i}: field-set drift")
                    for k, gv in g.items():
                        self.assertTrue(_field_matches(f[k], gv),
                                        f"{mod.NAME} rec {i} field '{k}': {f[k]} vs {gv}")


if __name__ == "__main__":
    unittest.main()
