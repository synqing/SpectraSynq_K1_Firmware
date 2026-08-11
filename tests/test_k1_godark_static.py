"""Static guard for silence go-dark wiring + STANDBY_DIMMING struck state.

Asserts the STRUCTURE of raw-RMS silence detection without hardware, and that
STANDBY_DIMMING is permanently struck: factory default false, boot force-off for
stale NVS, and Core-0 silent_scale pin (IIR dimming path inert).
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
        """Schmitt gap: exit must be strictly greater than enter (every #if branch)."""
        enters = [float(v) for v in re.findall(r"K1_SILENCE_RMS_ENTER\s*=\s*([\d.]+)f?;", GLOBALS)]
        exits = [float(v) for v in re.findall(r"K1_SILENCE_RMS_EXIT\s*=\s*([\d.]+)f?;", GLOBALS)]
        self.assertGreaterEqual(len(enters), 1)
        self.assertEqual(len(enters), len(exits))
        for enter, exit_ in zip(enters, exits):
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
        # Fade constants may remain for historical telemetry; dimming path itself is struck.
        self.assertIn("SILENCE_DWELL_MS", I2S)
        self.assertIn("SILENT_FADE_DOWN_ALPHA", GLOBALS)
        self.assertIn("SILENT_FADE_UP_ALPHA", GLOBALS)


class TelemetryAndSerial(unittest.TestCase):
    def test_ap_telemetry_exposes_rms_raw(self):
        self.assertIn("rms_raw=%.4f", I2S)
        # k1_silence_rms_raw must still be a live argument of the same [AP] printf that
        # reports STANDBY_DIMMING. Additional fields may be interleaved between them
        # (e.g. the peakiness `pky` telemetry added by the silence-break gate), so the
        # check is adjacency-within-the-argument-list, not literal adjacency.
        self.assertRegex(I2S, r"k1_silence_rms_raw,[^;]*CONFIG\.STANDBY_DIMMING")

    def test_serial_rms_tuners_present(self):
        self.assertTrue(typed_command_registered(SERIAL, "silence_rms_enter"))
        self.assertTrue(typed_command_registered(SERIAL, "silence_rms_exit"))

    def test_standby_dimming_not_in_typed_table(self):
        self.assertFalse(typed_command_registered(SERIAL, "standby_dimming"))


class StandbyDimmingStruck(unittest.TestCase):
    def test_standby_dimming_factory_default_false(self):
        self.assertRegex(GLOBALS_CFG, r"false,\s*//\s*STANDBY_DIMMING")

    def test_boot_force_off(self):
        SYSTEM = (FW / "system" / "system.h").read_text(encoding="utf-8")
        self.assertGreaterEqual(SYSTEM.count("CONFIG.STANDBY_DIMMING = false;"), 1)

    def test_silent_scale_pinned_unconditionally(self):
        """IIR dimming path must not be reachable via CONFIG.STANDBY_DIMMING."""
        self.assertIn("silent_scale      = 1.0f;", I2S)
        self.assertIn("silent_scale_last = 1.0f;", I2S)
        self.assertNotIn("if (CONFIG.STANDBY_DIMMING)", I2S)


if __name__ == "__main__":
    unittest.main()
