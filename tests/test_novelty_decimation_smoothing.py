"""Task E: AP novelty -> tempo decimation aggregates (peak-hold), it does not
naively pick every Nth raw sample.

The task asks: if AP novelty is decimated, verify smoothing/aggregation exists
before frames are dropped; if missing, add it. Here it ALREADY exists as a
peak-hold (max over the decimation window, k1_tempo.cpp:1294-1326), which is the
correct anti-alias mechanism for an onset/impulse signal. This test locks that
contract two ways:

  1. constant parity: the host model's decimation factor matches the firmware
     #define and the platformio build flag (cannot silently drift);
  2. behaviour: with onset spikes landing on NON-emit frames, the peak-hold
     decimator preserves them while a naive every-Nth sampler drops them.

A linear pre-decimation low-pass is intentionally NOT added: it would smear
onset transients and regress beat detection (the firmware comment at
k1_tempo.cpp:1294 — "preserves onset spikes" — is the design intent).
"""

import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
MODEL_PATH = ROOT / "scripts" / "regression-harness" / "novelty_decimation_model.py"
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text(encoding="utf-8")
TEMPO_SRC = (FW / "audio" / "k1_tempo.cpp").read_text(encoding="utf-8")
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")

spec = importlib.util.spec_from_file_location("novelty_decimation_model", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def _define_number(text, name):
    match = re.search(rf"#define\s+{re.escape(name)}\s+([^\s/]+)", text)
    assert match, f"missing #define {name}"
    raw = re.sub(r"[fFuUlL]+$", "", match.group(1))
    return float(raw) if "." in raw else int(raw)


class NoveltyDecimationTest(unittest.TestCase):
    def test_model_decimation_matches_firmware_define(self):
        fw = _define_number(CONFIG_TYPES, "K1_TEMPO_NOVELTY_DECIMATION")
        self.assertEqual(model.DEFAULT_DECIMATION, fw)

    def test_model_decimation_matches_build_flag(self):
        m = re.search(r"-DK1_TEMPO_NOVELTY_DECIMATION=(\d+)U?", PLATFORMIO)
        self.assertIsNotNone(m, "k1 build flag K1_TEMPO_NOVELTY_DECIMATION not found")
        self.assertEqual(model.DEFAULT_DECIMATION, int(m.group(1)))

    def test_firmware_uses_peak_hold_not_naive_decimation(self):
        # Static guard: the aggregation accumulator must still be present.
        self.assertIn("if (novelty > k1_accum) k1_accum = novelty", TEMPO_SRC)
        self.assertIn("K1_NOVELTY_DECIMATION", TEMPO_SRC)

    def test_peak_hold_preserves_offbeat_onset_spikes(self):
        dec = model.DEFAULT_DECIMATION
        # Spikes on frames that are NOT emit frames (frame 1, 4, 7, ... with a
        # prime at frame 0 and emits every `dec`-th frame). A naive every-Nth
        # sampler reads the emit frame (a zero) and drops the spike.
        stream = [0.0]  # prime frame
        n_windows = 6
        for w in range(n_windows):
            window = [0.0] * dec
            window[0] = 1.0  # spike on the first (non-emit) frame of the window
            stream.extend(window)

        emitted = model.run_stream(stream, dec)
        naive = model.naive_every_nth(stream, dec)

        self.assertEqual(len(emitted), n_windows)
        # Peak-hold catches every spike...
        for s in emitted:
            self.assertAlmostEqual(s, 1.0, places=6)
        # ...the naive sampler drops them all (reads the trailing zeros).
        self.assertTrue(all(abs(v) < 1e-6 for v in naive))
        # The two decimators therefore disagree: aggregation is real, not a
        # rename of "pick every third raw sample".
        self.assertNotEqual(emitted, naive)

    def test_peak_hold_is_aggregation_within_window(self):
        # Within a window the emit equals the MAX of the frames, not the last.
        dec = model.DEFAULT_DECIMATION
        stream = [0.0]  # prime
        # window frames: rising then falling, peak in the middle.
        stream.extend([0.3, 0.9, 0.2][:dec] + [0.0] * max(0, dec - 3))
        emitted = model.run_stream(stream, dec)
        self.assertEqual(len(emitted), 1)
        self.assertAlmostEqual(emitted[0], 0.9, places=6)


if __name__ == "__main__":
    unittest.main()
