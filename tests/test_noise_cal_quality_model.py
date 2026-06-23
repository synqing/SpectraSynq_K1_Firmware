import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "scripts" / "regression-harness" / "noise_cal_quality_model.py"
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
CONSTANTS = (FW / "system" / "constants.h").read_text(encoding="utf-8")
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text(encoding="utf-8")
I2S = (FW / "audio" / "i2s_audio.h").read_text(encoding="utf-8")

spec = importlib.util.spec_from_file_location("noise_cal_quality_model", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = model
spec.loader.exec_module(model)


def define_number(text, name):
    match = re.search(rf"#define\s+{re.escape(name)}\s+([^\s/]+)", text)
    assert match, f"missing #define {name}"
    raw = match.group(1)
    raw = re.sub(r"[fFuUlL]+$", "", raw)
    return float(raw) if "." in raw else int(raw)


class NoiseCalibrationQualityModelTest(unittest.TestCase):
    def test_host_model_constants_match_firmware_contract(self):
        self.assertEqual(model.DC_PHASE_A_FRAMES, define_number(CONSTANTS, "NOISE_CAL_DC_PHASE_A_FRAMES"))
        self.assertEqual(model.SAMPLES_PER_CHUNK, define_number(CONFIG_TYPES, "DEFAULT_SAMPLES_PER_CHUNK"))
        self.assertEqual(model.DC_MIN_VALID_RATIO_NUM, define_number(CONSTANTS, "NOISE_CAL_DC_MIN_VALID_RATIO_NUM"))
        self.assertEqual(model.DC_MIN_VALID_RATIO_DEN, define_number(CONSTANTS, "NOISE_CAL_DC_MIN_VALID_RATIO_DEN"))
        self.assertEqual(model.DC_MAX_VALID_ABS, define_number(CONSTANTS, "NOISE_CAL_DC_MAX_VALID_ABS"))
        self.assertEqual(model.SAMPLE_RAIL_THRESHOLD, define_number(I2S, "SAMPLE_RAIL_THRESHOLD"))
        self.assertEqual(model.SSL_PHASE_B_MAX_RAW, define_number(CONSTANTS, "NOISE_CAL_SSL_PHASE_B_MAX_RAW"))
        self.assertEqual(
            model.SSL_PHASE_B_MIN_ACCEPTED_FRAMES,
            define_number(CONSTANTS, "NOISE_CAL_SSL_PHASE_B_MIN_ACCEPTED_FRAMES"),
        )
        self.assertEqual(model.SSL_TRUSTED_P90_MAX_RAW, define_number(CONSTANTS, "NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW"))
        self.assertEqual(
            model.SSL_MAX_P90_TO_P50_RATIO,
            define_number(CONSTANTS, "NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO"),
        )
        self.assertEqual(model.SSL_MIN_VALID_RAW, define_number(CONSTANTS, "NOISE_CAL_SSL_MIN_VALID_RAW"))
        self.assertEqual(model.SSL_MAX_VALID_RAW, define_number(CONSTANTS, "NOISE_CAL_SSL_MAX_VALID_RAW"))

    def test_clean_silence_window_is_accepted(self):
        dc_samples = [-4710] * (model.DC_PHASE_A_FRAMES * model.SAMPLES_PER_CHUNK)
        peaks = [260.0] * 80 + [320.0] * 20 + [390.0] * 12

        decision = model.decide_noise_calibration(dc_samples, peaks)

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.reason, "none")
        self.assertEqual(decision.dc_offset, -4710)
        self.assertEqual(decision.sweet_spot_min, 352)

    def test_recent_elevated_no_music_window_is_rejected_as_too_loud(self):
        dc_samples = [-4715] * (model.DC_PHASE_A_FRAMES * model.SAMPLES_PER_CHUNK)
        # Mirrors the observed bad shape: learned SSL around 900 means p90 around 820.
        peaks = [520.0] * 70 + [720.0] * 30 + [825.0] * 12

        decision = model.decide_noise_calibration(dc_samples, peaks)

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "ssl_too_loud")
        self.assertEqual(decision.dc_offset, -4715)

    def test_sparse_quiet_frames_do_not_make_a_valid_profile(self):
        dc_samples = [-900] * (model.DC_PHASE_A_FRAMES * model.SAMPLES_PER_CHUNK)
        peaks = [250.0] * 40 + [1800.0] * 72

        decision = model.decide_noise_calibration(dc_samples, peaks)

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "ssl_samples")

    def test_unstable_window_is_rejected_even_when_under_absolute_ceiling(self):
        dc_samples = [-900] * (model.DC_PHASE_A_FRAMES * model.SAMPLES_PER_CHUNK)
        peaks = [120.0] * 90 + [600.0] * 22

        decision = model.decide_noise_calibration(dc_samples, peaks)

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "ssl_unstable")

    def test_dc_rail_window_is_rejected(self):
        dc_samples = [32767] * (model.DC_PHASE_A_FRAMES * model.SAMPLES_PER_CHUNK)
        peaks = [260.0] * model.SSL_PHASE_B_MIN_ACCEPTED_FRAMES

        decision = model.decide_noise_calibration(dc_samples, peaks)

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "dc_samples")


if __name__ == "__main__":
    unittest.main()
