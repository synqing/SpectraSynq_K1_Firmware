import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpml_run_console_server.py"
EVIDENCE = ROOT / "docs" / "forensics" / "runtime-evidence"

spec = importlib.util.spec_from_file_location("vpml_run_console_server", SCRIPT)
vpml_run_console_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpml_run_console_server)


class VPMLRunConsoleServerSmokeTest(unittest.TestCase):
    def test_render_page_exposes_run_console_without_forbidden_control_tokens(self):
        rendered = vpml_run_console_server.render_page(evidence_dir=EVIDENCE)

        self.assertIn("VPML Run Console", rendered)
        self.assertIn("Run Capture", rendered)
        self.assertIn("20260609T220729-vpml-intro-bounce-loop-1401", rendered)
        self.assertIn("Eyes-on pending", rendered)
        self.assertIn("Capture Duration Seconds", rendered)
        self.assertIn("Capture Every N Frames", rendered)
        self.assertNotIn(">Seconds<", rendered)
        self.assertNotIn(">Every N Frames<", rendered)
        self.assertNotIn("raw_receive", rendered)
        self.assertNotIn("programme.compile", rendered)
        self.assertNotIn("programme.upload", rendered)

    def test_bind_host_is_loopback_locked_by_default(self):
        vpml_run_console_server.validate_bind_host("127.0.0.1")
        vpml_run_console_server.validate_bind_host("localhost")
        vpml_run_console_server.validate_bind_host("::1")
        vpml_run_console_server.validate_bind_host("0.0.0.0", allow_non_loopback=True)

        with self.assertRaises(ValueError):
            vpml_run_console_server.validate_bind_host("0.0.0.0")

    def test_parse_run_form_rejects_unsupported_programme_and_non_dev_port(self):
        parsed = vpml_run_console_server.parse_run_form(
            {
                "port": "/dev/cu.usbmodem1401",
                "programme": "intro_bounce_loop",
                "baud": "115200",
                "seconds": "2.4",
                "every": "36",
            }
        )

        self.assertEqual(parsed["port"], "/dev/cu.usbmodem1401")
        self.assertEqual(parsed["baud"], 115200)
        self.assertEqual(parsed["programme"], "intro_bounce_loop")
        self.assertEqual(parsed["every"], 36)

        with self.assertRaises(ValueError):
            vpml_run_console_server.parse_run_form(
                {"port": "http://127.0.0.1", "programme": "intro_bounce_loop"}
            )
        with self.assertRaises(ValueError):
            vpml_run_console_server.parse_run_form(
                {"port": "/dev/cu.usbmodem1401", "programme": "custom_code"}
            )

    def test_run_capture_from_form_can_be_stubbed_without_serial(self):
        original_run = vpml_run_console_server.vpml_run_console.run_vpml_session
        original_write = vpml_run_console_server.vpml_run_console.write_capture_outputs
        original_refresh = vpml_run_console_server.vpml_run_console.refresh_dashboard

        def fake_run_vpml_session(*, lines, **_kwargs):
            lines.extend(["#VPML_CAPTURE fake", "#CMD :vpml=play_builtin,intro_bounce_loop"])
            return lines

        def fake_write_capture_outputs(*, prefix, evidence_dir, **_kwargs):
            evidence_dir.mkdir(parents=True, exist_ok=True)
            raw = evidence_dir / ("%s.raw.log" % prefix)
            frames = evidence_dir / ("%s.frames.log" % prefix)
            gate = evidence_dir / ("%s.frame-gate.json" % prefix)
            summary = evidence_dir / ("%s.vpml-summary.json" % prefix)
            raw.write_text("#VPML_CAPTURE fake\n", encoding="utf-8")
            frames.write_text("K1DF_BEGIN\nK1DF_END\n", encoding="utf-8")
            gate.write_text(json.dumps({"passed": True}) + "\n", encoding="utf-8")
            summary.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "result": "PASS",
                        "strict_gate": {"counts": {"records": 2, "chunks": 12}},
                        "runtime": {
                            "observed_chip_id": "F887A500",
                            "vpab_records": "VPAB_RECORDS: captured=2 dropped=0",
                            "vp_perf_frame": "VP_PERF_FRAME: avg=1 max=1 over=0 dropped=0",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            return {"raw": raw, "frames": frames, "frame_gate": gate, "summary": summary}

        def fake_refresh_dashboard(evidence_dir, dashboard_dir):
            dashboard_dir.mkdir(parents=True, exist_ok=True)
            page = dashboard_dir / "latest-vpml-evidence-page.html"
            payload = dashboard_dir / "latest-vpml-evidence-page.json"
            page.write_text("<html></html>", encoding="utf-8")
            payload.write_text("{}\n", encoding="utf-8")
            return {"dashboard_html": page, "dashboard_json": payload}

        vpml_run_console_server.vpml_run_console.run_vpml_session = fake_run_vpml_session
        vpml_run_console_server.vpml_run_console.write_capture_outputs = fake_write_capture_outputs
        vpml_run_console_server.vpml_run_console.refresh_dashboard = fake_refresh_dashboard
        try:
            with tempfile.TemporaryDirectory() as tmp:
                result = vpml_run_console_server.run_capture_from_form(
                    {
                        "port": "/dev/cu.usbmodem1401",
                        "programme": "intro_bounce_loop",
                        "baud": "115200",
                        "seconds": "0",
                        "every": "36",
                    },
                    evidence_dir=Path(tmp) / "runtime-evidence",
                    dashboard_dir=Path(tmp) / "vp_motion_lab",
                )
        finally:
            vpml_run_console_server.vpml_run_console.run_vpml_session = original_run
            vpml_run_console_server.vpml_run_console.write_capture_outputs = original_write
            vpml_run_console_server.vpml_run_console.refresh_dashboard = original_refresh

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["records"], 2)
        self.assertEqual(result["summary"]["chip"], "F887A500")
        self.assertIn("raw", result["paths"])


if __name__ == "__main__":
    unittest.main()
