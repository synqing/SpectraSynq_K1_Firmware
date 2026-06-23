import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpml_run_console.py"
EVIDENCE = ROOT / "docs" / "forensics" / "runtime-evidence"
ACCEPTED_FRAMES = EVIDENCE / "20260609T193511-vpml-intro-bounce-loop-1401.frames.log"

spec = importlib.util.spec_from_file_location("vpml_run_console", SCRIPT)
vpml_run_console = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpml_run_console)


class FakeSerial:
    def __init__(self, responses):
        self.responses = {key: list(value) for key, value in responses.items()}
        self.pending = []
        self.commands = []
        self.closed = False

    def reset_input_buffer(self):
        self.pending = []

    def write(self, data):
        command = data.decode("ascii").strip()
        self.commands.append(command)
        variants = self.responses.get(command, [[]])
        if variants:
            self.pending.extend(variants.pop(0))

    def flush(self):
        pass

    def readline(self):
        if not self.pending:
            return b""
        return (self.pending.pop(0) + "\n").encode("utf-8")

    def close(self):
        self.closed = True


class WriteFailureSerial(FakeSerial):
    def write(self, data):
        command = data.decode("ascii").strip()
        if command == ":vpml=play_builtin,intro_bounce_loop":
            raise OSError("USB CDC write failed")
        super().write(data)


class NoisySerial:
    def readline(self):
        return b"[K1WS] client 1 state.get id=999\n"


class VPMLRunConsoleTest(unittest.TestCase):
    def test_live_runner_uses_safe_vpml_command_sequence_and_writes_outputs(self):
        frame_lines = ACCEPTED_FRAMES.read_text().splitlines()
        fake = FakeSerial(
            {
                ":version": [["sbr{{", "VERSION: 40103", "}}"]],
                ":chip_id": [["sbr{{", "F887A500", "}}"]],
                ":vpml=status": [
                    ["VPML status active=0 programme=none frame=0 frames=112 loops=0 vpab_mode=250"],
                    ["VPML status active=1 programme=intro_bounce_loop frame=12 frames=96 loops=0 vpab_mode=250"],
                    ["VPML status active=0 programme=none frame=0 frames=112 loops=1 vpab_mode=250"],
                ],
                ":vpml=play_builtin,intro_bounce_loop": [
                    ["VPML play_builtin,intro_bounce_loop active=1"]
                ],
                ":vpab=reset": [["VPAB_RECORDS: captured=0 dropped=0 high_water=0 overflowed=0"]],
                ":vp_perf=reset": [["VP_PERF_RESET"]],
                ":vp_perf=start": [["VP_PERF_START"]],
                ":vpab=start,36,bytes": [["VPAB_RECORDS: captured=0 dropped=0 high_water=0 overflowed=0"]],
                ":vpab=stop": [
                    ["VPAB_RECORDS: captured=0 dropped=0 high_water=0 overflowed=0"],
                    ["VPAB_RECORDS: captured=30 dropped=0 high_water=30 overflowed=0"],
                ],
                ":vp_perf=stop": [
                    ["VP_PERF_STOP"],
                    ["VP_PERF_FRAME: avg=3938 max=5010 over=0 dropped=0"],
                ],
                ":vpml=stop": [
                    ["VPML stop active=0"],
                ],
                ":vpab=frames": [frame_lines],
            }
        )

        lines = vpml_run_console.run_vpml_session(
            port="/dev/cu.usbmodem1401",
            baud=230400,
            expect_chip="F887A500",
            programme="intro_bounce_loop",
            seconds=0.0,
            every=36,
            idle_reads=1,
            serial_factory=lambda _port, _baud: fake,
        )

        self.assertEqual(
            fake.commands,
            [
                ":version",
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
        self.assertTrue(fake.closed)
        for command in fake.commands:
            self.assertNotIn("ap_stream", command)
            self.assertNotIn("websocket", command)
            self.assertNotIn("compile", command)
            self.assertNotIn("upload", command)
            self.assertNotIn("raw_receive", command)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = vpml_run_console.write_capture_outputs(
                lines=lines,
                prefix="test-vpml-intro-bounce-loop-1401",
                evidence_dir=root / "runtime-evidence",
                expect_chip="F887A500",
                programme="intro_bounce_loop",
            )
            dashboards = vpml_run_console.refresh_dashboard(root / "runtime-evidence", root / "vp_motion_lab")
            summary = json.loads(paths["summary"].read_text())
            gate = json.loads(paths["frame_gate"].read_text())
            page = json.loads(dashboards["dashboard_json"].read_text())

        self.assertTrue(summary["passed"], summary["failures"])
        self.assertTrue(gate["passed"], gate["failures"])
        self.assertEqual(page["capture_count"], 1)
        self.assertEqual(page["captures"][0]["page_state"], "byte_clean")
        self.assertEqual(page["captures"][0]["visual_status"], "eyes_on_pending")

    def test_rejects_unsupported_programme_before_serial_open(self):
        with self.assertRaises(ValueError):
            vpml_run_console.run_vpml_session(
                port="/dev/cu.usbmodem1401",
                baud=230400,
                expect_chip="F887A500",
                programme="custom_code",
                seconds=0.0,
                every=36,
                serial_factory=lambda _port, _baud: FakeSerial({}),
            )

    def test_rejects_forbidden_command_fragments(self):
        for command in (":programme=upload", ":raw_receive=start", ":compile=demo"):
            with self.assertRaises(ValueError):
                vpml_run_console.validate_command(command)

    def test_read_idle_line_cap_bounds_continuous_telemetry(self):
        lines = []
        vpml_run_console.read_idle(
            NoisySerial(),
            lines,
            idle_reads=60,
            max_seconds=10.0,
            max_lines=5,
        )

        self.assertEqual(len(lines), 5)
        self.assertTrue(all(line.startswith("[K1WS]") for line in lines))

    def test_missing_expected_response_preserves_transcript(self):
        fake = FakeSerial(
            {
                ":version": [["VERSION: 40103"]],
                ":chip_id": [["F887A500"]],
                ":vpml=status": [["VPML status active=0 programme=none frame=0 frames=112 loops=0 vpab_mode=250"]],
                ":vpml=play_builtin,intro_bounce_loop": [["Bad command"]],
                ":vpab=stop": [["VPAB_RECORDS: captured=0 dropped=0 high_water=0 overflowed=0"]],
                ":vp_perf=stop": [["VP_PERF_STOP"]],
                ":vpml=stop": [["VPML stop active=0"]],
            }
        )

        with self.assertRaises(vpml_run_console.VPMLRunError) as raised:
            vpml_run_console.run_vpml_session(
                port="/dev/cu.usbmodem1401",
                baud=115200,
                expect_chip="F887A500",
                programme="intro_bounce_loop",
                seconds=0.0,
                every=36,
                idle_reads=1,
                serial_factory=lambda _port, _baud: fake,
            )

        lines = raised.exception.lines
        self.assertIn("#CMD :vpml=play_builtin,intro_bounce_loop", lines)
        self.assertTrue(any("Bad command" in line for line in lines))
        self.assertTrue(any(line.startswith("#SESSION_ERROR") for line in lines))
        self.assertTrue(fake.closed)

    def test_main_writes_partial_evidence_on_serial_exception(self):
        fake = WriteFailureSerial(
            {
                ":version": [["VERSION: 40103"]],
                ":chip_id": [["F887A500"]],
                ":vpml=status": [["VPML status active=0 programme=none frame=0 frames=112 loops=0 vpab_mode=250"]],
                ":vpab=stop": [["VPAB_RECORDS: captured=0 dropped=0 high_water=0 overflowed=0"]],
                ":vp_perf=stop": [["VP_PERF_STOP"]],
                ":vpml=stop": [["VPML stop active=0"]],
            }
        )
        original_open_retry = vpml_run_console.open_retry
        vpml_run_console.open_retry = lambda _port, _baud: fake
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out_dir = Path(tmp) / "runtime-evidence"
                code = vpml_run_console.main(
                    [
                        "--port",
                        "/dev/cu.usbmodem1401",
                        "--baud",
                        "115200",
                        "--programme",
                        "intro_bounce_loop",
                        "--seconds",
                        "0",
                        "--every",
                        "36",
                        "--out-dir",
                        str(out_dir),
                        "--prefix",
                        "partial-failure",
                        "--no-dashboard",
                    ]
                )

                raw_path = out_dir / "partial-failure.raw.log"
                error_path = out_dir / "partial-failure.session-error.json"
                summary_path = out_dir / "partial-failure.vpml-summary.json"
                error = json.loads(error_path.read_text())
                summary = json.loads(summary_path.read_text())
                raw = raw_path.read_text()
        finally:
            vpml_run_console.open_retry = original_open_retry

        self.assertEqual(code, 1)
        self.assertIn("#SESSION_ERROR OSError: USB CDC write failed", raw)
        self.assertEqual(error["error_type"], "VPMLRunError")
        self.assertFalse(error["passed"])
        self.assertFalse(summary["passed"])
        self.assertTrue(fake.closed)


if __name__ == "__main__":
    unittest.main()
