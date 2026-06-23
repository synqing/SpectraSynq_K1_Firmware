"""Golden-master behaviour-equivalence gate (Phase F / L1).

Re-runs each registered oracle and asserts its full numeric output matches the
frozen golden within tolerance, and that the golden files have not been edited
(checksum manifest). This is the behaviour contract a refactor must preserve:
if a number here changes, behaviour changed.
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

# Registry — adding a module is one line + its frozen golden file.
ORACLES = [
    {"name": "onset_beat", "module": "oracle_onset_beat", "golden": "onset_beat.golden.jsonl"},
]
FLOAT_FIELDS = {"conf", "phase", "trans"}
FLOAT_TOL = 1e-4


def _parse(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _load_oracle(module_name):
    spec = importlib.util.spec_from_file_location(module_name, HARNESS / f"{module_name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        for spec in ORACLES:
            with self.subTest(oracle=spec["name"]):
                mod = _load_oracle(spec["module"])
                fresh = _parse(mod.capture())
                gold = _parse((GOLDEN_DIR / spec["golden"]).read_text(encoding="utf-8"))
                self.assertEqual(len(fresh), len(gold),
                                 f"{spec['name']}: record-count drift {len(fresh)} vs {len(gold)}")
                for i, (f, g) in enumerate(zip(fresh, gold)):
                    self.assertEqual(set(f), set(g), f"{spec['name']} rec {i}: field-set drift")
                    for k, gv in g.items():
                        if k in FLOAT_FIELDS:
                            self.assertLessEqual(
                                abs(float(f[k]) - float(gv)), FLOAT_TOL,
                                f"{spec['name']} rec {i} '{k}': {f[k]} vs {gv}")
                        else:
                            self.assertEqual(f[k], gv, f"{spec['name']} rec {i} field '{k}'")


if __name__ == "__main__":
    unittest.main()
