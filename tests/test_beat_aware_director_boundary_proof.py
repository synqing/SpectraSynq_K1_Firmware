"""Host tests for Proposal 3 BeatAwareDirector boundary proof scaffolding."""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
BOUNDARY = HARNESS / "beat_aware_director_boundary_proof.py"
DEVICE = HARNESS / "beat_aware_director_device_proof.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Dataclass needs the module registered before exec_module on Py3.14+.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class BeatAwareDirectorBoundaryProofTest(unittest.TestCase):
    def test_host_boundary_proof_passes(self):
        mod = _load(BOUNDARY, "bad_boundary_proof")
        result = mod.run_proof()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["device_status"], "PENDING_DEVICE")
        self.assertIn("BEAT_AWARE_DIRECTOR_BOUNDARY_OK", result["stdout"])

    def test_device_fixture_scorer_passes_synthetic(self):
        mod = _load(DEVICE, "bad_device_proof")
        with tempfile.TemporaryDirectory() as td:
            fixture = Path(td) / "bad_fixture.log"
            mod.write_example_fixture(fixture)
            result = mod.score_fixture(fixture)
        self.assertEqual(result["status"], "PASS", result)
        self.assertGreaterEqual(result["locked_beat_q_ok"], 1)
        self.assertEqual(result["locked_beat_q_bad"], 0)
        self.assertGreaterEqual(result["unlocked_beat_q_ok"], 1)
        self.assertEqual(result["unlocked_beat_q_bad"], 0)
        self.assertEqual(result["device_status"], "PENDING_DEVICE")

    def test_opt_in_envs_present_and_default_shipping_untouched(self):
        text = (ROOT / "platformio.ini").read_text(encoding="utf-8")
        self.assertIn("[env:k1_prod_im73d_bad]", text)
        self.assertIn("[env:k1_bench_im73d_bad]", text)
        self.assertIn("-DK1_BEAT_AWARE_DIRECTOR_V1", text)
        # Shipping k1_prod_im73d body (before the Proposal-3 comment/env) must
        # not enable framework/BAD flags.
        m = re.search(
            r"\[env:k1_prod_im73d\]\n(?P<body>extends = env:k1_hardware\n"
            r"build_flags =\n(?:    .*\n)+)",
            text,
        )
        self.assertIsNotNone(m, "k1_prod_im73d build_flags stanza missing")
        prod_flags = m.group("body")
        self.assertNotIn("K1_BEAT_AWARE_DIRECTOR_V1", prod_flags)
        self.assertNotIn("K1_EFFECT_FRAMEWORK_V1", prod_flags)
        self.assertIn("K1_MIC_IM73D_PDM_V1", prod_flags)

    def test_identities_register_bad_envs(self):
        import json

        data = json.loads(
            (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
                encoding="utf-8"
            )
        )
        main_envs = next(e["envs"] for e in data["authorized"] if e["chip_id"] == "F887A500")
        bench_envs = next(e["envs"] for e in data["authorized"] if e["chip_id"] == "B489A500")
        self.assertIn("k1_prod_im73d_bad", main_envs)
        self.assertIn("k1_bench_im73d_bad", bench_envs)


if __name__ == "__main__":
    unittest.main()
