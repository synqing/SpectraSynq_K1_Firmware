import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "smart_director_replay.py"


class SmartDirectorReplayTest(unittest.TestCase):
    def test_host_replay_proves_autonomy_semantics(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SMART_DIRECTOR_REPLAY_OK cases=12", result.stdout)


if __name__ == "__main__":
    unittest.main()
