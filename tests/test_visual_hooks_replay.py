import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "visual_hooks_replay.py"


class VisualHooksReplayTest(unittest.TestCase):
    def test_host_replay_proves_l1_accent_semantics(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VISUAL_HOOKS_REPLAY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
