import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "k1_paired_snappiness_capture.py"


def load_module():
    spec = importlib.util.spec_from_file_location("k1_paired_snappiness_capture", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class K1PairedSnappinessCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = load_module()

    def test_default_devices_follow_current_spec_index_assignment(self):
        devices = self.capture.default_devices()
        self.assertEqual(devices[0]["name"], "main-1401")
        self.assertEqual(devices[0]["port"], "/dev/tty.usbmodem1401")
        self.assertEqual(devices[0]["expected_chip_id"], "F887A500")
        self.assertEqual(devices[0]["env"], "k1_hardware")
        self.assertEqual(devices[1]["name"], "bench-12201")
        self.assertEqual(devices[1]["port"], "/dev/tty.usbmodem12201")
        self.assertEqual(devices[1]["expected_chip_id"], "B489A500")
        self.assertEqual(devices[1]["env"], "k1_bench_reference")

    def test_command_plan_contains_only_safe_runtime_commands(self):
        commands = (
            self.capture.setup_commands(22, "l1")
            + self.capture.capture_start_commands(
                enable_vp_perf=True,
                tempo_stream=True,
                ap_frontend_debug=True,
                live_streams=False,
                nov_capture_ms=60000,
                apcad_capture_ms=20000,
            )
            + self.capture.capture_stop_commands(
                enable_vp_perf=True,
                tempo_stream=True,
                ap_frontend_debug=True,
                live_streams=False,
                nov_capture_ms=60000,
                apcad_capture_ms=20000,
            )
            + [self.capture.response_gain_command({"response_gain": "2.218"})]
        )
        self.capture.assert_command_plan_is_safe(commands)
        joined = "\n".join(commands)
        self.assertIn(":set_mode=22", commands)
        self.assertIn(":smart_scene=l1", commands)
        self.assertIn(":response_gain=2.218", commands)
        self.assertNotIn(":ap_stream=on", commands)
        self.assertNotIn(":vp_stream=on", commands)
        self.assertIn(":tempo_stream=on", commands)
        self.assertIn(":apdbg=on", commands)
        self.assertIn(":nov_capture=60000", commands)
        self.assertIn(":apcad_capture=20000", commands)
        self.assertIn(":nov_dump=1", commands)
        self.assertIn(":apcad_dump=1", commands)
        self.assertIn(":apdbg=off", commands)
        self.assertIn(":tempo_stream=off", commands)
        for forbidden in (
            "start_noise_cal",
            "clear_noise_cal",
            "factory_reset",
            "restore_defaults",
            "erase",
            "dump_raw",
        ):
            self.assertNotIn(forbidden, joined)

    def test_response_gain_command_is_optional_and_runtime_only(self):
        self.assertIsNone(self.capture.response_gain_command({}))
        self.assertIsNone(self.capture.response_gain_command({"response_gain": ""}))
        self.assertEqual(
            self.capture.response_gain_command({"response_gain": "2.218"}),
            ":response_gain=2.218",
        )
        self.capture.validate_runtime_command(":response_gain=2.218")

    def test_buffered_probe_dump_commands_get_longer_settle_time(self):
        self.assertGreaterEqual(self.capture.command_settle_seconds(":nov_dump=1"), 8.0)
        self.assertGreaterEqual(self.capture.command_settle_seconds(":apcad_dump=1"), 8.0)
        self.assertLess(self.capture.command_settle_seconds(":ap_stream=on"), 1.0)

    def test_forbidden_command_guard_rejects_calibration_and_reset(self):
        with self.assertRaisesRegex(ValueError, "forbidden"):
            self.capture.validate_runtime_command(":start_noise_cal")
        with self.assertRaisesRegex(ValueError, "forbidden"):
            self.capture.validate_runtime_command(":reset")

    def test_extract_identity_parses_version_and_chip_id(self):
        lines = [
            "[1.0] VERSION: 40103",
            "[1.1] sbr{{",
            "[1.2] F887A500",
            "[1.3] }}",
        ]
        identity = self.capture.extract_identity(lines)
        self.assertEqual(identity["version"], "40103")
        self.assertEqual(identity["chip_id"], "F887A500")

    def test_extract_identity_ignores_expected_chip_metadata(self):
        lines = [
            "[1.0] #DEVICE role=bench-reference expected_chip_id=B489A500",
            "[1.1] >>> :chip_id",
        ]
        identity = self.capture.extract_identity(lines)
        self.assertIsNone(identity["version"])
        self.assertIsNone(identity["chip_id"])

    def test_parse_capture_log_summarises_ap_vp_vpf_and_dump_fields(self):
        text = "\n".join(
            [
                "[1.0] VERSION: 40103",
                "[1.1] F887A500",
                "[2.0] CONFIG.SAMPLE_RATE: 12800",
                "[2.1] CONFIG.SAMPLES_PER_CHUNK: 96",
                "[2.2] CONFIG.SWEET_SPOT_MIN_LEVEL: 224",
                "[2.3] AUDIO_RESPONSE_GAIN: 1.000000",
                "[3.0] SMART_APPLIED_MODE: 22",
                "[3.1] SMART_BEAT_CONFIDENCE: 0.700",
                "[4.0] [AP] SSL=224 DC=-32767 max_raw=5000 follower=8000 peak_scaled=0.350 silent_scale=1.000 silence=0 cal_source=config cal_valid=1 | bpm=128.0 conf=0.60 lock=1 phase=0.20 beat=0 bstr=0.30 | onset=1 bass=0 ostr=0.25",
                "[5.0] [VP] profile=original fix=111111 agc_gain=1.2000 bloom_alpha=0.9900 wave_shift=140.0000 render_us=650 render_avg=700 render_max=900",
                "[6.0] VPF,ver=1,seq=1,mode=22,gdft_us=3300/7600,pri_render_us=640/900,frame_us=3900/5000,over=0,dropped=0,heap=86336",
            ]
        )

        summary = self.capture.parse_capture_log(text)

        self.assertEqual(summary["identity"]["chip_id"], "F887A500")
        self.assertEqual(summary["dump"]["CONFIG.SAMPLE_RATE"], 12800)
        self.assertEqual(summary["dump"]["CONFIG.SAMPLES_PER_CHUNK"], 96)
        self.assertEqual(summary["dump"]["AUDIO_RESPONSE_GAIN"], 1.0)
        self.assertEqual(summary["smart"]["SMART_APPLIED_MODE"], 22)
        self.assertEqual(summary["counts"], {"ap": 1, "vp": 1, "vpf": 1})
        self.assertEqual(summary["ap"]["peak_scaled"]["last"], 0.35)
        self.assertEqual(summary["ap"]["max_raw"]["last"], 5000)
        self.assertNotIn("SMART_BEAT_CONFIDENCE", summary["ap"])
        self.assertEqual(summary["smart_metrics"]["SMART_BEAT_CONFIDENCE"]["last"], 0.7)
        self.assertEqual(summary["vp"]["render_us"]["last"], 650)
        self.assertEqual(summary["vp"]["render_max"]["last"], 900)
        self.assertEqual(summary["vpf"]["gdft_us_avg"]["last"], 3300)
        self.assertEqual(summary["vpf"]["gdft_us_max"]["last"], 7600)

    def test_build_comparison_reports_timing_parity(self):
        summaries = {
            "main-1401": {
                "dump": {"CONFIG.SAMPLE_RATE": 12800, "CONFIG.SAMPLES_PER_CHUNK": 96, "AUDIO_RESPONSE_GAIN": 1.0},
                "vp": {"render_us": {"mean": 650, "last": 640}, "render_max": {"last": 900}},
                "ap": {"peak_scaled": {"mean": 0.3, "last": 0.35}, "max_raw": {"mean": 5000, "last": 5100}},
                "smart_metrics": {"SMART_BEAT_CONFIDENCE": {"mean": 0.7}, "SMART_APPLIED_MODE": {"last": 22}},
                "vpf": {"gdft_us_avg": {"mean": 3300}, "frame_us_avg": {"mean": 3900}},
            },
            "bench-12201": {
                "dump": {"CONFIG.SAMPLE_RATE": 12800, "CONFIG.SAMPLES_PER_CHUNK": 96, "AUDIO_RESPONSE_GAIN": 2.0},
                "vp": {"render_us": {"mean": 900, "last": 910}, "render_max": {"last": 1200}},
                "ap": {"peak_scaled": {"mean": 0.5, "last": 0.55}, "max_raw": {"mean": 5200, "last": 5300}},
                "smart_metrics": {"SMART_BEAT_CONFIDENCE": {"mean": 0.8}, "SMART_APPLIED_MODE": {"last": 22}},
                "vpf": {"gdft_us_avg": {"mean": 3400}, "frame_us_avg": {"mean": 3950}},
            },
        }

        comparison = self.capture.build_comparison(summaries)

        self.assertTrue(comparison["timing_parity"])
        self.assertEqual(comparison["response_gain"]["main-1401"], 1.0)
        self.assertEqual(comparison["response_gain"]["bench-12201"], 2.0)
        self.assertEqual(comparison["render_us_mean"]["main-1401"], 650)
        self.assertEqual(comparison["peak_scaled_mean"]["bench-12201"], 0.5)
        self.assertEqual(comparison["smart_beat_confidence_mean"]["main-1401"], 0.7)
        self.assertEqual(comparison["smart_applied_mode_last"]["bench-12201"], 22)


if __name__ == "__main__":
    unittest.main()
