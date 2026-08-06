"""feat/gdft-center-honesty: alias-aware per-Goertzel-bin frequency honesty for
the REAL K1 bin config (DEFAULT profile, NOTE_OFFSET=12).

Measurement-only. Validates the host reconstruction in
scripts/regression-harness/gdft_center_honesty_model.py against the firmware:
constants + formula text are parity-checked; alias/Nyquist honesty and the
geometry properties are asserted over all 80 real bins; headline values locked.

Two distinct truths, kept separate:
  - REPRESENTABLE bins (target <= Nyquist): the rounded-k coefficient offsets the
    centre below the label (A4 440 Hz -> ~420 Hz; worst ~-248 Hz at bin 70).
  - ABOVE-NYQUIST bins (71..79): the label is not physically representable at
    fs=12800; the raw Goertzel centre FOLDS into the real band, so no physical
    resonance above Nyquist is ever claimed.
"""

import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
MODEL_PATH = ROOT / "scripts" / "regression-harness" / "gdft_center_honesty_model.py"
SYSTEM_H = (FW / "system" / "system.h").read_text(encoding="utf-8")
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text(encoding="utf-8")

spec = importlib.util.spec_from_file_location("gdft_center_honesty_model", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def _define_int(text, name):
    m = re.search(rf"#define\s+{re.escape(name)}\s+(\d+)", text)
    assert m, f"missing #define {name}"
    return int(m.group(1))


class GdftCenterHonestyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bins = model.compute_bins()
        cls.summary = model.summarize(cls.bins)

    # --- parity: parsed config + formulas match firmware (Captain test 5) ---
    def test_config_matches_firmware(self):
        self.assertEqual(model.SAMPLE_RATE, _define_int(CONFIG_TYPES, "DEFAULT_SAMPLE_RATE"))
        self.assertEqual(model.NUM_FREQS, _define_int(CONFIG_TYPES, "NUM_FREQS"))
        self.assertEqual(model.SAMPLE_RATE, 12800)
        self.assertEqual(model.NUM_FREQS, 80)
        self.assertEqual(model.NOTE_OFFSET, 12)
        self.assertEqual(model.BLOCK_SIZE_CAP, 2000)
        self.assertEqual(model.NYQUIST_HZ, 6400.0)

    def test_notes_table_parsed(self):
        self.assertEqual(len(model.NOTES), 96)
        self.assertAlmostEqual(float(model.NOTES[0]), 55.0, places=2)
        self.assertAlmostEqual(float(model.NOTES[12]), 110.0, places=2)
        self.assertAlmostEqual(float(model.NOTES[36]), 440.0, places=2)

    def test_formula_text_matches_firmware(self):
        # Phase 2: crossover Rayleigh (default crossover=0 → global 1-semitone).
        self.assertIn("K1_GDFT_X2_CROSSOVER_BIN", SYSTEM_H)
        self.assertRegex(
            SYSTEM_H,
            r"resolution_div\s*=\s*\(i\s*<\s*x2_cross\)\s*\?\s*2\.0f\s*:\s*1\.0f")
        self.assertRegex(
            SYSTEM_H,
            r"block_size\s*=\s*CONFIG\.SAMPLE_RATE\s*/\s*\(max_distance_hz\s*\*\s*resolution_div\)")
        self.assertRegex(
            SYSTEM_H,
            r"\(int\)\(0\.5\s*\+\s*\(\(frequencies\[i\]\.block_size\s*\*\s*"
            r"frequencies\[i\]\.target_freq\)\s*/\s*CONFIG\.SAMPLE_RATE\)\)")

    # --- folding function ---------------------------------------------------
    def test_fold_function(self):
        fold = model.fold_to_real_audio_band
        self.assertAlmostEqual(fold(5000.0), 5000.0, places=4)      # below Nyquist: unchanged
        self.assertAlmostEqual(fold(6400.0), 6400.0, places=4)      # exactly Nyquist
        self.assertAlmostEqual(fold(8533.3333), 4266.6667, places=3)  # above -> folds
        self.assertAlmostEqual(fold(8869.844), 3930.156, places=2)
        self.assertAlmostEqual(fold(12800.0), 0.0, places=4)        # full rate -> DC
        self.assertAlmostEqual(fold(13000.0), 200.0, places=4)      # past fs -> baseband

    # --- geometry identities ------------------------------------------------
    def test_bin_count_and_targets(self):
        self.assertEqual(len(self.bins), 80)
        for b in self.bins:
            self.assertAlmostEqual(b["target_hz"], float(model.NOTES[b["bin"] + 12]), places=2)

    def test_identities(self):
        fs = model.SAMPLE_RATE
        for b in self.bins:
            self.assertGreater(b["block_size"], 0)
            self.assertLessEqual(b["block_size"], 2000)
            self.assertAlmostEqual(b["true_resolution_hz"], fs / b["block_size"], places=4)
            self.assertAlmostEqual(b["raw_center_hz"], b["k"] * fs / b["block_size"], places=4)
            self.assertAlmostEqual(b["effective_center_hz"],
                                   model.fold_to_real_audio_band(b["raw_center_hz"]), places=4)
            self.assertAlmostEqual(b["target_error_hz"],
                                   b["effective_center_hz"] - b["target_folded_hz"], places=4)

    def test_raw_center_within_half_cell_of_target(self):
        # k-rounding bound on the BARE Goertzel centre (pre-fold) holds for all bins.
        for b in self.bins:
            self.assertLessEqual(abs(b["raw_center_hz"] - b["target_hz"]),
                                 0.5 * b["true_resolution_hz"] + 1e-3,
                                 f"bin {b['bin']} raw centre exceeds half-cell bound")

    # --- alias / Nyquist honesty (Captain tests 1-3) ------------------------
    def test_every_effective_center_at_or_below_nyquist(self):  # Captain #1
        for b in self.bins:
            self.assertLessEqual(b["effective_center_hz"], b["nyquist_hz"] + 1e-6,
                                 f"bin {b['bin']} effective centre above Nyquist")

    def test_above_nyquist_targets_flagged(self):  # Captain #2
        flagged = [b["bin"] for b in self.bins if b["target_above_nyquist"]]
        truly_above = [b["bin"] for b in self.bins if b["target_hz"] > b["nyquist_hz"]]
        self.assertEqual(flagged, truly_above)
        self.assertEqual(flagged, list(range(71, 80)))  # 9 bins, 71..79
        self.assertEqual(self.summary["num_above_nyquist"], 9)

    def test_above_nyquist_bins_make_no_physical_resonance_claim(self):  # Captain #3
        for b in self.bins:
            if b["target_above_nyquist"]:
                # not representable: label_error suppressed, centre folded into band.
                self.assertIsNone(b["label_error_hz"])
                self.assertLessEqual(b["effective_center_hz"], b["nyquist_hz"] + 1e-6)

    # --- regression locks: below-Nyquist vs above-Nyquist (Captain test 4) --
    def test_a4_below_nyquist_lock(self):  # representable case (Phase 2: 1-semitone)
        b = self.bins[24]
        self.assertFalse(b["target_above_nyquist"])
        self.assertAlmostEqual(b["target_hz"], 440.0, places=2)
        self.assertEqual(b["block_size"], 489)
        self.assertEqual(b["k"], 17)
        self.assertAlmostEqual(b["raw_center_hz"], 444.99, delta=0.1)
        # below Nyquist: no fold, so effective == raw, and label_error is real.
        self.assertAlmostEqual(b["effective_center_hz"], b["raw_center_hz"], places=4)
        self.assertAlmostEqual(b["label_error_hz"], 4.99, delta=0.1)

    def test_high_bin_above_nyquist_folded_lock(self):  # aliased case
        b = self.bins[76]
        self.assertTrue(b["target_above_nyquist"])
        self.assertAlmostEqual(b["target_hz"], 8869.84, delta=0.1)
        self.assertEqual(b["k"], 17)
        self.assertEqual(b["block_size"], 24)
        self.assertAlmostEqual(b["raw_center_hz"], 9066.67, delta=0.1)   # bare Goertzel
        self.assertAlmostEqual(b["effective_center_hz"], 3733.33, delta=0.1)  # FOLDED real centre
        self.assertAlmostEqual(b["target_folded_hz"], 3930.16, delta=0.1)
        self.assertIsNone(b["label_error_hz"])

    def test_worst_representable_label_error(self):
        # Phase 2 1-semitone: worst representable error lands near bin 67 (~5.3 kHz).
        self.assertEqual(self.summary["max_representable_label_error_bin"], 67)
        self.assertAlmostEqual(self.summary["max_representable_label_error_hz"], 154.0, delta=2.0)

    def test_representable_error_grows_with_frequency(self):
        self.assertGreater(abs(self.bins[60]["label_error_hz"]),
                           abs(self.bins[0]["label_error_hz"]))
        self.assertGreater(abs(self.bins[70]["label_error_hz"]),
                           abs(self.bins[24]["label_error_hz"]))

    def test_resolution_span(self):
        self.assertAlmostEqual(self.summary["min_resolution_hz"], 6.54, delta=0.1)
        self.assertAlmostEqual(self.summary["max_resolution_hz"], 609.52, delta=1.0)
    def test_renderer_smoke(self):
        md = model.render_markdown(self.bins)
        self.assertIn("alias-aware", md)
        self.assertIn("raw_center_hz", md)
        self.assertIn("effective_center_hz", md)
        data_rows = re.findall(r"(?m)^\|\s*\d+\s*\|", md)
        self.assertEqual(len(data_rows), 80)


class GdftTrueCenterTest(unittest.TestCase):
    """K1_GDFT_TRUE_CENTER_V1 A/B: host model + firmware gate parity.

    Default-OFF must reproduce rounded-k byte-for-byte (no behaviour change). ON,
    representable bins resonate at the EXACT target (the host analog of the device
    acceptance 'A4 440 Hz lands on bin 24'); above-Nyquist bins are unchanged.
    """

    @classmethod
    def setUpClass(cls):
        cls.off = model.compute_bins()                      # default == rounded_k
        cls.rounded = model.compute_bins(mode="rounded_k")
        cls.on = model.compute_bins(mode="true_center")

    def test_default_mode_is_rounded_k(self):
        # OFF path (no mode arg) must be IDENTICAL to explicit rounded_k.
        self.assertEqual(self.off, self.rounded)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            model.compute_bins(mode="nope")

    def test_representable_bins_resonate_at_exact_target(self):
        # The headline ON property: every bin whose note is representable centres
        # exactly on its label (label_error -> 0), unlike rounded-k.
        for b in self.on:
            if not b["target_above_nyquist"]:
                self.assertAlmostEqual(b["effective_center_hz"], b["target_hz"], delta=0.05,
                                       msg=f"bin {b['bin']} not centred on target when ON")
                self.assertAlmostEqual(b["label_error_hz"], 0.0, delta=0.05)
                self.assertAlmostEqual(b["raw_center_hz"], b["target_hz"], delta=0.05)

    def test_a4_bin24_host_acceptance(self):
        # Host analog of the device acceptance gate (440 Hz -> bin 24).
        b = self.on[24]
        self.assertAlmostEqual(b["target_hz"], 440.0, places=2)
        self.assertFalse(b["target_above_nyquist"])
        self.assertAlmostEqual(b["effective_center_hz"], 440.0, delta=0.05)
        self.assertAlmostEqual(b["label_error_hz"], 0.0, delta=0.05)
        # block_size (resolution) is unchanged by the coefficient choice.
        self.assertEqual(b["block_size"], self.off[24]["block_size"])

    def test_true_center_improves_every_representable_bin(self):
        for on_b, off_b in zip(self.on, self.rounded):
            if not on_b["target_above_nyquist"]:
                self.assertLessEqual(abs(on_b["label_error_hz"]), abs(off_b["label_error_hz"]) + 1e-9,
                                     msg=f"bin {on_b['bin']} ON error not <= OFF error")

    def test_above_nyquist_bins_unchanged_when_on(self):
        # ON must NOT claim >Nyquist sensitivity: those bins keep rounded-k exactly.
        for on_b, off_b in zip(self.on, self.rounded):
            if on_b["target_above_nyquist"]:
                self.assertEqual(on_b, off_b,
                                 msg=f"bin {on_b['bin']} above Nyquist changed when ON")

    # --- firmware parity: the flag and the gated coefficient exist as specified -
    def test_flag_defined_default_off(self):
        self.assertRegex(CONFIG_TYPES,
                         r"#ifndef\s+K1_GDFT_TRUE_CENTER_V1\s*\n\s*#define\s+K1_GDFT_TRUE_CENTER_V1\s+0")

    def test_firmware_gates_coefficient(self):
        self.assertRegex(SYSTEM_H, r"#if\s+K1_GDFT_TRUE_CENTER_V1")
        # ON branch: exact-frequency coefficient for representable bins.
        self.assertRegex(
            SYSTEM_H,
            r"frequencies\[i\]\.target_freq\s*<=\s*CONFIG\.SAMPLE_RATE\s*\*\s*0\.5f")
        self.assertRegex(
            SYSTEM_H,
            r"w\s*=\s*\(2\.0\s*\*\s*PI\s*\*\s*frequencies\[i\]\.target_freq\)\s*/\s*CONFIG\.SAMPLE_RATE")
        # #else branch keeps the legacy rounded-k formula verbatim (byte-identical OFF).
        self.assertRegex(SYSTEM_H, r"#else")
        self.assertRegex(SYSTEM_H, r"#endif")


if __name__ == "__main__":
    unittest.main()
