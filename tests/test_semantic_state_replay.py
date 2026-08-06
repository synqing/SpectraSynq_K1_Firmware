import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "semantic_state_replay.py"


class SemanticStateReplayTest(unittest.TestCase):
    def test_spine_packs_produced_fields(self):
        # Compiles the REAL spine (audio/k1_semantic_state.cpp) against the REAL
        # tempo + onset producers (k1_tempo.cpp, k1_onset_beat.cpp) and the REAL
        # chord detector (k1_chord_detect.cpp via a snapshot read-stub), with ALL
        # flags (K1_SEMANTIC_STATE / K1_ONSET_V2 / K1_CHORD_V2). Asserts:
        #   - audio_semantic_read() forwards tempo/onset/chord field-for-field,
        #   - the rate diagnostics equal the firmware derivation
        #     (12800/96 = 133.33 Hz AP, /3 = 44.44 Hz novelty, 7.5 ms frame).
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SEMANTIC_STATE_REPLAY_OK rate=1 tempo=1 onset=1 chord=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
