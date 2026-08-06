import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "k1_stm_replay.py"


class K1StmReplayTest(unittest.TestCase):
    def test_host_replay_proves_stm_producer(self):
        # Compiles the REAL producer (audio/k1_stm.cpp) with -DK1_STM and drives
        # synthetic spectra with KNOWN modulation. Asserts: warm-up gating with
        # exactly-zero (non-fabricated) outputs, steady->~0 vs 4 Hz->high temporal
        # discrimination, spectral-ripple localisation to bin (K-1), and silence as
        # an honest exact zero.
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("K1_STM_REPLAY_OK cases=5", result.stdout)


if __name__ == "__main__":
    unittest.main()
