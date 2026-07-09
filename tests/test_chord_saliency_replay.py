import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "chord_saliency_replay.py"


class ChordSaliencyReplayTest(unittest.TestCase):
    def test_chord_detection_and_harmonic_axis_revival(self):
        # K1_CHORD_V2 path, host-compiled REAL firmware TUs:
        #   - k1_chord_detect.cpp: triad detection on labelled synthetic chroma
        #     (major/minor/dim/aug root+type correct, monotone with triad purity,
        #     documented donor limits on flat/unison input).
        #   - k1_musical_saliency.cpp: harmonic axis A/B — incumbent dead proxy
        #     (no flag) vs revived chord root/type-change axis (K1_CHORD_V2).
        #   - byte-identity guard: the no-flag harmonic axis still computes the
        #     legacy chroma-delta proxy exactly (production path unchanged).
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CHORD_SALIENCY_REPLAY_OK chord_cases=6 saliency_ab=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
