"""Static gates for the 2026-06-11 impact lane (Captain items 3-7).

#3 dual-edge pairing presets, #5 attack-snap asymmetric envelope,
#6 drop-cut (musical silence cuts go ACTUALLY dark, strobe-safe by design).
#4 closed as verified-non-issue (output gamma disabled since 2026-05-20).
#7 (K1Optics plate sim) is covered by tests/test_k1_optics_static.py.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

LED_UTILS = (FW / "visual" / "led_utilities.h").read_text()
I2S = (FW / "audio" / "i2s_audio.h").read_text()
PRESETS = (FW / "system" / "presets.h").read_text()
PIO = (ROOT / "platformio.ini").read_text()


class ImpactLaneStaticTest(unittest.TestCase):
    # ---- #6 drop-cut --------------------------------------------------------
    def test_drop_cut_is_flag_gated_and_applied_to_both_channels(self):
        self.assertIn("#ifdef SB_DROP_CUT_V1", LED_UTILS)
        self.assertIn("drop_cut_update();", LED_UTILS)
        # Primary and secondary brightness lines both carry the scaler.
        self.assertIn("silent_scale * SQ15x16(drop_cut_scale)", LED_UTILS)
        self.assertIn("bright_val *= drop_cut_scale;", LED_UTILS)

    def test_drop_cut_is_strobe_safe_by_construction(self):
        # The four anti-strobe mechanisms must all be present:
        body = LED_UTILS[LED_UTILS.index("inline void drop_cut_update"):]
        body = body[:body.index("#endif")]
        # 1. sustained-quiet confirmation window (no instant cuts).
        self.assertIn("below_since_ms >= 120", body)
        # 2. recent-loud requirement (idle rooms never cut).
        self.assertIn("recent_peak > DC_PEAK", body)
        # 3. hysteresis: exit threshold above entry threshold.
        enter = float(body.split("DC_ENTER = ")[1].split("f")[0])
        exit_ = float(body.split("DC_EXIT  = ")[1].split("f")[0])
        self.assertGreater(exit_, enter * 2)
        # 4. re-arm lockout after relight.
        self.assertIn("rearm_until_ms = now + 1000", body)
        # Relight is INSTANT (the payoff) — full scale on exit, no ramp up.
        self.assertIn("drop_cut_scale = 1.0f;              // relight INSTANTLY", body)

    # ---- #5 attack snap -----------------------------------------------------
    def test_peak_envelope_is_asymmetric_under_flag_with_legacy_retained(self):
        self.assertIn("#ifdef SB_PEAK_ASYM_ENV", I2S)
        self.assertIn("waveform_peak_scaled += delta * 0.65;", I2S)
        self.assertIn("waveform_peak_scaled -= delta * 0.15;", I2S)
        # Legacy symmetric path retained for off-flag builds.
        self.assertIn("waveform_peak_scaled += delta * 0.25;", I2S)
        self.assertIn("waveform_peak_scaled -= delta * 0.25;", I2S)

    # ---- #3 pairing presets -------------------------------------------------
    def test_pairing_presets_exist_with_correct_mode_pairs(self):
        pairs = {
            "harmony_rhythm": ("LIGHT_MODE_CHROMA_CONSTELLATION",
                               "LIGHT_MODE_PERCUSSION_BURST"),
            "deep_flow": ("LIGHT_MODE_RIVER_SURGE",
                          "LIGHT_MODE_DENSE_FORGE_CHORD"),
            "beat_theatre": ("LIGHT_MODE_TEMPO_COMET_ANTICIPATE",
                             "LIGHT_MODE_TEMPO_RIVER"),
            "club": ("LIGHT_MODE_DENSE_FORGE",
                     "LIGHT_MODE_PERCUSSION_BURST"),
        }
        for name, (primary, secondary) in pairs.items():
            self.assertIn(f'strcmp(preset_name, "{name}") == 0', PRESETS)
            block = PRESETS.split(f'"{name}"')[1].split("}")[0]
            self.assertIn(f"CONFIG.LIGHTSHOW_MODE = {primary};", block)
            self.assertIn(f"SECONDARY_LIGHTSHOW_MODE = {secondary};", block)
            self.assertIn("ENABLE_SECONDARY_LEDS = true;", block)

    # ---- production flags ---------------------------------------------------
    def test_flags_are_on_in_production_with_revert_levers(self):
        self.assertIn("-DSB_DROP_CUT_V1", PIO)
        self.assertIn("-DSB_PEAK_ASYM_ENV", PIO)


if __name__ == "__main__":
    unittest.main()
