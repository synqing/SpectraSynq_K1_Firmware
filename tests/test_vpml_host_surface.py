import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpml_host_surface.py"
EVIDENCE = ROOT / "docs" / "forensics" / "runtime-evidence"

spec = importlib.util.spec_from_file_location("vpml_host_surface", SCRIPT)
vpml_host_surface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpml_host_surface)


class VPMLHostSurfaceTest(unittest.TestCase):
    def test_surface_contains_all_scoped_pages_in_order(self):
        surface = vpml_host_surface.build_surface(EVIDENCE)
        page_ids = [page["id"] for page in surface["pages"]]

        self.assertEqual(
            page_ids,
            [
                "vpml_run_console",
                "programme_parameter_picker",
                "evidence_gate_motion_readability",
                "protocol_readiness_authoring_lock",
                "promotion_regression_ledger",
            ],
        )
        self.assertEqual(surface["schema"], "vpml_host_surface.v1")
        self.assertEqual(surface["proof_boundary"], "host_file_review_only")

    def test_run_console_is_evidence_backed_and_exposes_live_runner_controls(self):
        surface = vpml_host_surface.build_surface(EVIDENCE)
        run_console = surface["pages"][0]
        controls = {item["id"]: item for item in run_console["controls"]}
        evidence_page = vpml_host_surface.vpml_evidence_page.build_page(EVIDENCE)
        byte_clean_ids = [
            capture["capture_id"]
            for capture in evidence_page["captures"]
            if capture["page_state"] == "byte_clean"
        ]

        self.assertEqual(run_console["state"], "offline_evidence_loaded")
        self.assertEqual(run_console["readbacks"]["latest_byte_clean_capture"], sorted(byte_clean_ids)[-1])
        self.assertEqual(run_console["readbacks"]["latest_visual_status"], "eyes_on_pending")
        self.assertEqual(run_console["readbacks"]["observed_chip_id"], "F887A500")
        self.assertEqual(controls["evidence.refresh"]["enabled"], True)
        self.assertEqual(controls["device.scan"]["requires"], "vpml_live_runner scan")
        for control_id in ("device.scan", "device.identify", "vpml.status", "programme.play_builtin", "programme.stop", "capture.start"):
            self.assertTrue(controls[control_id]["enabled"], control_id)
        for control_id in ("device.identify", "vpml.status", "programme.play_builtin", "programme.stop", "capture.start"):
            self.assertEqual(controls[control_id]["requires"], "port_and_chip_guard")
        runner_commands = run_console["readbacks"]["runner_commands"]
        self.assertIn("vpml_live_runner.py capture", runner_commands["capture_loop"])
        self.assertIn("--programme intro_bounce_loop", runner_commands["capture_loop"])

    def test_picker_exposes_fixed_builtins_only(self):
        surface = vpml_host_surface.build_surface(EVIDENCE)
        picker = surface["pages"][1]
        programmes = [item["programme"] for item in picker["readbacks"]["programmes"]]
        controls = {item["id"]: item for item in picker["controls"]}

        self.assertEqual(programmes, ["intro_bounce_loop", "intro_bounce"])
        self.assertEqual(picker["state"], "fixed_builtins_only")
        self.assertTrue(controls["programme.select"]["enabled"])
        self.assertEqual(controls["programme.select"]["values"], programmes)
        for forbidden in ("programme.compile", "programme.upload", "raw_receive"):
            self.assertNotIn(forbidden, controls)
        self.assertEqual(picker["readbacks"]["parameter_model"], "none_current_mvp")

    def test_evidence_gate_and_protocol_lock_share_evidence_page_contract(self):
        surface = vpml_host_surface.build_surface(EVIDENCE)
        evidence_gate = surface["pages"][2]
        protocol_lock = surface["pages"][3]

        self.assertEqual(evidence_gate["state"], "byte_clean_pending_visual")
        self.assertGreaterEqual(evidence_gate["readbacks"]["capture_count"], 3)
        self.assertIn("20260609T193511-vpml-intro-bounce-loop-1401", evidence_gate["readbacks"]["byte_clean_captures"])
        self.assertIn("20260609T193419-vpml-intro-bounce-loop-1401", evidence_gate["readbacks"]["transport_failed_captures"])
        self.assertIn("20260609T190853-vpml-intro-bounce-1401", evidence_gate["readbacks"]["dark_sample_captures"])
        self.assertIn("captain_acceptance_from_bytes", evidence_gate["must_not_claim"])

        self.assertEqual(protocol_lock["state"], "locked_no_adr")
        self.assertEqual(protocol_lock["readbacks"]["hidden_controls"], ["programme.compile", "programme.upload", "raw_receive"])
        self.assertIn("captain_approval", protocol_lock["readbacks"]["missing"])
        self.assertEqual(protocol_lock["controls"], [])

    def test_deferred_ledger_has_no_promotion_controls(self):
        surface = vpml_host_surface.build_surface(EVIDENCE)
        ledger = surface["pages"][4]

        self.assertEqual(ledger["state"], "deferred_no_candidates")
        self.assertEqual(ledger["controls"], [])
        self.assertEqual(ledger["readbacks"]["candidate_count"], 0)
        self.assertIn("Captain eyes-on acceptance", ledger["implementation_prerequisites"])

    def test_cli_writes_json_and_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "surface.json"
            html = Path(tmp) / "surface.html"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--evidence-dir",
                    str(EVIDENCE),
                    "--out",
                    str(out),
                    "--html",
                    str(html),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(out.read_text())
            html_text = html.read_text().lower()

        self.assertEqual(payload["schema"], "vpml_host_surface.v1")
        self.assertIn("vpml run console", html_text)
        self.assertIn("programme + parameter picker", html_text)
        self.assertIn("byte proof only", html_text)
        self.assertNotIn("production ready", html_text)
        self.assertNotIn("audio reactive", html_text)

    def test_script_has_no_device_or_network_access_path(self):
        source = SCRIPT.read_text()
        for token in (
            "serial.Serial",
            "import socket",
            "socket.socket",
            "websockets.connect",
            "websocket.create_connection",
            "requests",
            "httpx",
            "pio run",
            "--target upload",
            "esptool",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
