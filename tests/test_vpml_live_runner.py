import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpml_live_runner.py"
EVIDENCE = ROOT / "docs" / "forensics" / "runtime-evidence"
ACCEPTED_FRAMES = EVIDENCE / "20260609T193511-vpml-intro-bounce-loop-1401.frames.log"

spec = importlib.util.spec_from_file_location("vpml_live_runner", SCRIPT)
vpml_live_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpml_live_runner)


class FakeTransport:
    def __init__(self, responses):
        self.responses = {key: list(value) for key, value in responses.items()}
        self.commands = []
        self.sleeps = []

    def command(self, command, read_seconds):
        self.commands.append(command)
        queue = self.responses.get(command, [])
        if queue:
            return queue.pop(0)
        return []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        return []


def _successful_responses():
    frames = ACCEPTED_FRAMES.read_text().splitlines()
    return {
        ":chip_id": [["F887A500"]],
        ":vpml=stop": [
            ["VPML stopped"],
            ["VPML stopped"],
        ],
        ":ap_stream=off": [["AP_STREAM: off"]],
        ":vp_stream=off": [["VP_STREAM: off"]],
        ":vpab=reset": [["VPAB_CAPTURE: idle count=0"]],
        ":vp_perf=reset": [["VP_PERF: reset"]],
        ":vp_perf=start": [["VP_PERF: start budget_us=10000 render_budget_us=2000"]],
        ":vpml=status": [
            ["VPML status active=0 programme=none frame=0 frames=112 loops=0 vpab_mode=250"],
            ["VPML status active=1 programme=intro_bounce_loop frame=76 frames=96 loops=0 vpab_mode=250"],
            ["VPML status active=0 programme=none frame=0 frames=96 loops=1 vpab_mode=250"],
        ],
        ":vpab=start,36,bytes": [["VPAB_CAPTURE: armed every_n=36 mode=bytes"]],
        ":vpml=play_builtin,intro_bounce_loop": [
            ["VPML play_builtin,intro_bounce_loop active=1 frames=96 vpab_mode=250"]
        ],
        ":vpab=stop": [
            ["VPAB_RECORDS: captured=0 dropped=0 high_water=0 overflowed=0"],
            ["VPAB_RECORDS: captured=30 dropped=0 high_water=30 overflowed=0"],
        ],
        ":vp_perf=stop": [
            ["VP_PERF: stopped"],
            [
                "VP_PERF: stopped",
                "VP_PERF_SEQ: 96",
                "VP_PERF_FRAME: avg=3934 max=4100 over=0 dropped=0",
            ]
        ],
        ":vpab=frames": [frames],
    }


class VPMLLiveRunnerTest(unittest.TestCase):
    def test_capture_flow_writes_gate_summary_and_raw_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = vpml_live_runner.CaptureConfig(
                port="/dev/cu.usbmodem1401",
                programme="intro_bounce_loop",
                duration_ms=0,
                evidence_dir=Path(tmp),
                label="vpml-test",
                settle_seconds=0,
            )
            transport = FakeTransport(_successful_responses())
            result = vpml_live_runner.run_capture_transport(transport, config)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["summary_result"], "PASS")
            self.assertTrue(result["frame_gate_passed"])
            self.assertEqual(result["observed_chip_id"], "F887A500")
            self.assertEqual(
                transport.commands,
                [
                    ":chip_id",
                    ":vpml=status",
                    ":vpab=stop",
                    ":vp_perf=stop",
                    ":vpml=stop",
                    ":vpab=reset",
                    ":vp_perf=reset",
                    ":vpml=play_builtin,intro_bounce_loop",
                    ":vpml=status",
                    ":vp_perf=start",
                    ":vpab=start,36,bytes",
                    ":vpab=stop",
                    ":vp_perf=stop",
                    ":vpab=frames",
                    ":vpml=stop",
                    ":vpml=status",
                ],
            )

            paths = {key: Path(value) for key, value in result["paths"].items()}
            for path in paths.values():
                self.assertTrue(path.exists(), path)
            raw_text = paths["raw_log"].read_text()
            self.assertIn("#VPML_CAPTURE port=/dev/cu.usbmodem1401", raw_text)
            self.assertIn("#IDENTITY chip_id=F887A500 expected=F887A500", raw_text)
            self.assertIn("#CMD :vpml=play_builtin,intro_bounce_loop", raw_text)
            self.assertIn("#WAIT preview_capture 0.00s", raw_text)
            self.assertIn("VP_PERF_FRAME: avg=3934 max=4100 over=0 dropped=0", raw_text)
            self.assertNotIn(":ap_stream", raw_text)
            self.assertNotIn(":vp_stream", raw_text)

            summary = json.loads(paths["summary"].read_text())
            self.assertEqual(summary["result"], "PASS")
            self.assertEqual(summary["acceptance"]["chip_identity_match"], True)
            self.assertEqual(summary["acceptance"]["vpml_started_and_stopped"], True)
            self.assertEqual(summary["decoded_vpab_bytes"]["channel_counts"], {"primary": 15, "secondary": 15})

    def test_chip_mismatch_stops_before_play_or_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = vpml_live_runner.CaptureConfig(
                port="/dev/cu.usbmodem1401",
                programme="intro_bounce_loop",
                duration_ms=0,
                evidence_dir=Path(tmp),
                settle_seconds=0,
            )
            transport = FakeTransport({":chip_id": [["B489A500"]]})
            result = vpml_live_runner.run_capture_transport(transport, config)

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "chip_identity_mismatch")
            self.assertEqual(transport.commands, [":chip_id"])
            self.assertNotIn(":vpml=play_builtin,intro_bounce_loop", transport.commands)
            self.assertNotIn(":vpab=start,1,bytes", transport.commands)

    def test_identify_status_and_parse_helpers(self):
        transport = FakeTransport(
            {
                ":chip_id": [["noise", "CHIP ID: F887A500"]],
                ":vpml=status": [
                    ["VPML status active=1 programme=intro_bounce_loop frame=12 frames=96 loops=0 vpab_mode=250"]
                ],
            }
        )
        result = vpml_live_runner.run_status_transport(transport, "F887A500")

        self.assertTrue(result["ok"])
        self.assertEqual(result["identity"]["observed_chip_id"], "F887A500")
        self.assertEqual(result["status"]["active"], 1)
        self.assertEqual(result["status"]["programme"], "intro_bounce_loop")
        self.assertEqual(result["status"]["vpab_mode"], 250)

    def test_unsupported_programme_is_rejected_before_serial_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = vpml_live_runner.CaptureConfig(
                port="/dev/cu.usbmodem1401",
                programme="custom_runtime_code",
                evidence_dir=Path(tmp),
                settle_seconds=0,
            )
            transport = FakeTransport({})
            with self.assertRaises(ValueError):
                vpml_live_runner.run_capture_transport(transport, config)
            self.assertEqual(transport.commands, [])

    def test_live_runner_is_fixed_builtins_only_no_authoring_transport(self):
        source = SCRIPT.read_text()

        self.assertEqual(sorted(vpml_live_runner.PROGRAMMES), ["intro_bounce", "intro_bounce_loop"])
        for forbidden in (
            ":vpml=begin",
            ":vpml=chunk",
            ":vpml=commit",
            ":vpml=play,",
            ":ap_stream",
            ":vp_stream",
            "programme.compile",
            "programme.upload",
            "raw_receive",
            "websockets.connect",
            "websocket.create_connection",
            "requests",
            "httpx",
            "--target upload",
            "esptool",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
