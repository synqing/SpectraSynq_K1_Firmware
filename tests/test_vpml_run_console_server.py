import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpml_run_console_server.py"

spec = importlib.util.spec_from_file_location("vpml_run_console_server", SCRIPT)
vpml_run_console_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpml_run_console_server)


def _summary(capture_id, records):
    return {
        "result": "PASS",
        "passed": True,
        "runtime": {
            "port": "/dev/cu.usbmodem1401",
            "expected_chip_id": "F887A500",
            "observed_chip_id": "F887A500",
            "vpml_final_status": "VPML active=0 programme=intro_bounce_loop frame=0 frames=96 loops=1 vpab_mode=250",
        },
        "acceptance": {
            "chip_identity_match": True,
            "no_dark_sample_records": True,
            "nonzero_final_bytes_on_required_channels": True,
            "primary_and_secondary_present": True,
            "strict_transport_clean": True,
            "vp_perf_no_over_or_dropped_frames": True,
            "vpml_mode_on_all_records": True,
            "vpml_started_and_stopped": True,
        },
        "strict_gate": {
            "counts": {"records": records, "chunks": records * 2},
            "stream": {"begin": {"dropped": 0, "overflowed": 0}},
        },
        "decoded_vpab_bytes": {
            "channel_counts": {"primary": records // 2, "secondary": records // 2},
            "channel_energy_sum_total": {"primary": 1200, "secondary": 1300},
            "channel_max_byte": {"primary": 100, "secondary": 120},
            "channel_nonzero_led_bytes_total": {"primary": 12, "secondary": 14},
            "dark_sample_records": [],
            "mode_counts": {"250": records},
            "records": [
                {
                    "channel": "primary",
                    "energy_sum": 1200,
                    "mode": 250,
                    "record_frame": 36,
                    "seq": 1,
                },
                {
                    "channel": "secondary",
                    "energy_sum": 1300,
                    "mode": 250,
                    "record_frame": 36,
                    "seq": 2,
                },
            ],
        },
        "capture_id": capture_id,
    }


def _write_capture(root, capture_id, records):
    (root / ("%s.vpml-summary.json" % capture_id)).write_text(
        json.dumps(_summary(capture_id, records)) + "\n",
        encoding="utf-8",
    )
    (root / ("%s.frame-gate.json" % capture_id)).write_text(
        json.dumps({"passed": True, "counts": {"records": records, "chunks": records * 2}}) + "\n",
        encoding="utf-8",
    )
    (root / ("%s.raw.log" % capture_id)).write_text("VPML synthetic raw log\n", encoding="utf-8")
    (root / ("%s.frames.log" % capture_id)).write_text("", encoding="utf-8")


class VPMLRunConsoleServerTest(unittest.TestCase):
    def test_render_page_includes_run_form_and_latest_byte_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_capture = "20260609T010000-vpml-intro-bounce-loop-1401"
            latest_capture = "20260609T020000-vpml-intro-bounce-loop-1401"
            _write_capture(root, old_capture, records=6)
            _write_capture(root, latest_capture, records=12)

            html = vpml_run_console_server.render_page(evidence_dir=root)

        self.assertIn('<form method="post" action="/run">', html)
        self.assertIn('name="port" value="/dev/cu.usbmodem1401"', html)
        self.assertIn('<select name="programme">', html)
        self.assertIn('value="intro_bounce_loop" selected', html)
        self.assertIn("Latest Byte Evidence", html)
        self.assertIn(
            "<div class=\"stat\"><span>Capture</span><strong>%s</strong></div>" % latest_capture,
            html,
        )
        self.assertIn("<div class=\"stat\"><span>Records</span><strong>12</strong></div>", html)
        self.assertIn("<div class=\"stat\"><span>Chip</span><strong>F887A500</strong></div>", html)

    def test_parse_run_form_rejects_unsupported_programmes_and_non_dev_ports(self):
        bad_forms = [
            {"programme": "custom_code", "port": "/dev/cu.usbmodem1401"},
            {"programme": "intro_bounce_loop", "port": "http://192.168.4.1/ws"},
            {"programme": "intro_bounce_loop", "port": "COM3"},
        ]

        for form in bad_forms:
            with self.subTest(form=form):
                with self.assertRaises(ValueError):
                    vpml_run_console_server.parse_run_form(form)

    def test_run_capture_from_form_can_be_stubbed_without_serial(self):
        calls = {}
        runner = vpml_run_console_server.vpml_run_console
        original_run_vpml_session = runner.run_vpml_session
        original_capture_prefix = runner.capture_prefix
        original_write_capture_outputs = runner.write_capture_outputs
        original_refresh_dashboard = runner.refresh_dashboard

        def fake_run_vpml_session(**kwargs):
            calls["request"] = dict(kwargs)
            lines = kwargs["lines"]
            lines.extend(["#CMD :version", "VERSION: 40103"])

        def fake_capture_prefix(programme, port):
            calls["prefix_args"] = (programme, port)
            return "stub-vpml-intro-bounce-loop-1401"

        def fake_write_capture_outputs(*, lines, prefix, evidence_dir, expect_chip, programme):
            calls["write_args"] = {
                "lines": list(lines),
                "prefix": prefix,
                "expect_chip": expect_chip,
                "programme": programme,
            }
            evidence_dir.mkdir(parents=True, exist_ok=True)
            summary = evidence_dir / ("%s.vpml-summary.json" % prefix)
            summary.write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "passed": True,
                        "runtime": {"observed_chip_id": expect_chip, "vpab_records": 2, "vp_perf_frame": "ok"},
                        "strict_gate": {"counts": {"records": 2, "chunks": 4}},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            raw = evidence_dir / ("%s.raw.log" % prefix)
            raw.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return {"summary": summary, "raw": raw}

        def fake_refresh_dashboard(evidence_dir, dashboard_dir):
            dashboard_dir.mkdir(parents=True, exist_ok=True)
            dashboard = dashboard_dir / "vpml-page.json"
            dashboard.write_text("{}", encoding="utf-8")
            calls["dashboard_args"] = (Path(evidence_dir), Path(dashboard_dir))
            return {"dashboard_json": dashboard}

        runner.run_vpml_session = fake_run_vpml_session
        runner.capture_prefix = fake_capture_prefix
        runner.write_capture_outputs = fake_write_capture_outputs
        runner.refresh_dashboard = fake_refresh_dashboard
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = vpml_run_console_server.run_capture_from_form(
                    {
                        "port": "/dev/cu.usbmodem1401",
                        "baud": "115200",
                        "expect_chip": "f887a500",
                        "programme": "intro_bounce_loop",
                        "seconds": "0",
                        "every": "36",
                        "command_read_seconds": "0.1",
                        "frame_read_seconds": "0.1",
                    },
                    evidence_dir=root / "runtime-evidence",
                    dashboard_dir=root / "vp_motion_lab",
                )
                summary_path_existed = Path(result["paths"]["summary"]).exists()
        finally:
            runner.run_vpml_session = original_run_vpml_session
            runner.capture_prefix = original_capture_prefix
            runner.write_capture_outputs = original_write_capture_outputs
            runner.refresh_dashboard = original_refresh_dashboard

        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "PASS")
        self.assertEqual(result["summary"]["records"], 2)
        self.assertEqual(result["summary"]["chunks"], 4)
        self.assertEqual(result["summary"]["chip"], "F887A500")
        self.assertTrue(summary_path_existed)
        self.assertEqual(calls["prefix_args"], ("intro_bounce_loop", "/dev/cu.usbmodem1401"))
        self.assertEqual(calls["request"]["port"], "/dev/cu.usbmodem1401")
        self.assertEqual(calls["request"]["baud"], 115200)
        self.assertEqual(calls["request"]["programme"], "intro_bounce_loop")
        self.assertEqual(calls["request"]["expect_chip"], "F887A500")
        self.assertEqual(calls["write_args"]["lines"], ["#CMD :version", "VERSION: 40103"])


if __name__ == "__main__":
    unittest.main()
