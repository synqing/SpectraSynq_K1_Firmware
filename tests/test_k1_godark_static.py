"""Static guard for the silence go-dark fix (raw-RMS pre-gate port).

Asserts the STRUCTURE of the fix without hardware: the raw-RMS signal is captured, the
`silence` latch is driven off it (not the SSL/sweet_spot_state gate that never latched),
the absolute thresholds + serial tuners + telemetry exist, and the feature ships DORMANT
(STANDBY_DIMMING factory-default false). Behavioural calibration is validated on the bench
(scripts/regression-harness/k1_godark_measure.py + k1_godark_validate.py); this test only
prevents the wiring from silently regressing.
"""
import re
import unittest
from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface, typed_command_registered

ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
GLOBALS = (FW.base / "system" / "globals.h").read_text(encoding="utf-8")
GLOBALS_CFG = (FW.base / "system" / "globals_config.cpp").read_text(encoding="utf-8")
I2S = (FW.base / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
SERIAL = read_serial_menu_surface(FW)


class RawRmsThresholds(unittest.TestCase):
    def test_globals_declare_absolute_rms_thresholds(self):
        self.assertRegex(GLOBALS, r"inline\s+float\s+K1_SILENCE_RMS_ENTER\s*=\s*[\d.]+f?;")
        self.assertRegex(GLOBALS, r"inline\s+float\s+K1_SILENCE_RMS_EXIT\s*=\s*[\d.]+f?;")
        self.assertRegex(GLOBALS, r"inline\s+float\s+k1_silence_rms_raw\s*=")

    def test_exit_threshold_above_enter(self):
        """Schmitt gap: exit must be strictly greater than enter."""
        enter = float(re.search(r"K1_SILENCE_RMS_ENTER\s*=\s*([\d.]+)f?;", GLOBALS).group(1))
        exit_ = float(re.search(r"K1_SILENCE_RMS_EXIT\s*=\s*([\d.]+)f?;", GLOBALS).group(1))
        self.assertGreater(enter, 0.0)
        self.assertGreater(exit_, enter)


class RawRmsSignalCaptured(unittest.TestCase):
    def test_calculate_vu_captures_raw_rms(self):
        # k1_silence_rms_raw is set from the raw pre-floor RMS, right at `audio_vu_level = rms`.
        self.assertRegex(
            I2S, r"audio_vu_level\s*=\s*rms;\s*\n\s*k1_silence_rms_raw\s*=\s*\(float\)rms;")


class SilenceLatchDrivenByRawRms(unittest.TestCase):
    def test_latch_uses_raw_rms_hysteresis(self):
        self.assertIn("k1_rms_silent_state", I2S)
        self.assertIn("k1_silence_rms_raw < K1_SILENCE_RMS_EXIT", I2S)
        self.assertIn("k1_silence_rms_raw < K1_SILENCE_RMS_ENTER", I2S)

    def test_latch_no_longer_gated_on_sweet_spot_state(self):
        """The go-dark latch must NOT re-couple to sweet_spot_state==-1 (the floor that
        never latched in a normal room)."""
        # The dwell branch must be reached via the raw-RMS state, not `else if (sweet_spot_state == -1)`.
        self.assertNotIn("} else if (sweet_spot_state == -1) {", I2S)

    def test_dwell_and_asymmetric_fade_preserved(self):
        self.assertIn("SILENCE_DWELL_MS", I2S)
        self.assertIn("SILENT_FADE_DOWN_ALPHA", I2S)
        self.assertIn("SILENT_FADE_UP_ALPHA", I2S)


class TelemetryAndSerial(unittest.TestCase):
    def test_ap_telemetry_exposes_rms_raw(self):
        self.assertIn("rms_raw=%.4f", I2S)
        self.assertIn("k1_silence_rms_raw, CONFIG.STANDBY_DIMMING", I2S)

    def test_serial_tuners_present(self):
        self.assertTrue(typed_command_registered(SERIAL, "silence_rms_enter"))
        self.assertTrue(typed_command_registered(SERIAL, "silence_rms_exit"))


class ShipsLive(unittest.TestCase):
    def test_standby_dimming_factory_default_true(self):
        # Default-flipped 2026-07-10 (Captain-signed): go-dark ships ON. Detection is raw-RMS
        # + dwell, cal-independent; hardware-validated latch->true-black->wake.
        self.assertRegex(GLOBALS_CFG, r"true,\s*//\s*STANDBY_DIMMING")

    def test_no_boot_force_off(self):
        # Both boot force-offs (unconditional IM73D-boot + SSL-cal-validity guard) are removed:
        # go-dark detection is raw-RMS/cal-independent, so neither guard's rationale holds and
        # both wrongly disabled go-dark on fresh units. No system.h boot path may force it false.
        SYSTEM = (FW / "system" / "system.h").read_text(encoding="utf-8")
        self.assertEqual(SYSTEM.count("CONFIG.STANDBY_DIMMING = false;"), 0)


if __name__ == "__main__":
    unittest.main()
