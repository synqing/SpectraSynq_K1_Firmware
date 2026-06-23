import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "k1_phase345_runtime_proof.py"


def load_module():
    spec = importlib.util.spec_from_file_location("k1_phase345_runtime_proof", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Phase345RuntimeProofTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = load_module()

    def test_command_guard_rejects_destructive_or_calibration_commands(self):
        safe = [
            ":chip_id",
            ":version",
            ":event_status",
            ":slot_list",
            ":queue_mode=on",
            ":transition_style=dip",
            ":transition_dip_ms=120",
            ":commit_quantise=off",
            ":slot_save=10,primary",
            ":set_mode=9",
            ":slot_load=10,primary",
            ":commit",
            ":queue_mode=off",
        ]
        self.proof.assert_command_plan_is_safe(safe)
        for command in (":start_noise_cal", ":clear_noise_cal CONFIRM",
                        ":factory_reset CONFIRM", ":restore_defaults CONFIRM",
                        ":reset", ":dump_raw=silence"):
            with self.assertRaisesRegex(ValueError, "forbidden"):
                self.proof.validate_runtime_command(command)

    def test_slot_parser_selects_empty_slot_only(self):
        lines = [
            "PRESET SLOTS (/PRESETS_V1.BIN)",
            "SLOT 1: mode=8 (WAVEFORM) palette=3 palette_mode=on",
            "SLOT 2: EMPTY",
            "SLOT 3: [ 38310][E][vfs_api.cpp:99] open(): /littlefs/PRESETS_V1.BIN does not exist, no permits for creation",
            "SLOT 10: EMPTY",
            "queue_mode=off transition_style=dip dip_ms=120 xfade_ms=400 commit_quantise=off",
        ]
        self.assertEqual(self.proof.first_empty_slot(lines), 2)
        self.assertEqual(self.proof.slot_validity(lines)[1], "valid")
        self.assertEqual(self.proof.slot_validity(lines)[2], "empty")
        self.assertEqual(self.proof.slot_validity(lines)[3], "empty")

    def test_event_status_parser_requires_percussion_fields(self):
        line = (
            "EVENT_STATUS,t=1200,frame_ms=1190,age=20,onset=1,bass=0,beat=0,"
            "ostr=0.200,bstr=0.000,phase=0.100,conf=0.400,kick=1,snare=0,hihat=1,"
            "tid=4,kid=3,sid=1,hid=2,tlvl=0.700,klvl=0.800,slvl=0.100,hlvl=0.500,"
            "tstr=0.900,kstr=0.800,sstr=0.000,hstr=0.600,energy=0.500,nov=0.250,sil=0"
        )
        parsed = self.proof.parse_kv_line(line)
        self.assertEqual(parsed["kick"], "1")
        self.assertEqual(parsed["snare"], "0")
        self.assertEqual(parsed["hihat"], "1")
        self.proof.assert_event_status_complete(parsed)

    def test_mode_parser_extracts_numeric_mode(self):
        self.assertEqual(self.proof.extract_mode(["MODE: 8"]), 8)
        self.assertEqual(self.proof.extract_mode(["CONFIG.LIGHTSHOW_MODE: 12"]), 12)
        self.assertIsNone(self.proof.extract_mode(["noise"]))


if __name__ == "__main__":
    unittest.main()
