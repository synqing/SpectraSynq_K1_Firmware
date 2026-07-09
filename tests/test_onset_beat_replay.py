import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "onset_beat_replay.py"


class OnsetBeatReplayTest(unittest.TestCase):
    def test_host_replay_proves_event_semantics(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ONSET_BEAT_REPLAY_OK cases=7", result.stdout)

    def test_onset_v2_synthetic_asserts(self):
        # K1_ONSET_V2 path: per-band refractory, channel separation, and the
        # gate-permission-only baseline invariant. Production (no-flag) build is
        # asserted byte-identical by the case above.
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--v2"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ONSET_V2_REPLAY_OK cases=3", result.stdout)


if __name__ == "__main__":
    unittest.main()
