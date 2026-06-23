import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpml_evidence_page.py"
EVIDENCE = ROOT / "docs" / "forensics" / "runtime-evidence"

spec = importlib.util.spec_from_file_location("vpml_evidence_page", SCRIPT)
vpml_evidence_page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpml_evidence_page)


ACCEPTED_ID = "20260609T193511-vpml-intro-bounce-loop-1401"
REJECTED_ID = "20260609T193419-vpml-intro-bounce-loop-1401"
DARK_ID = "20260609T190853-vpml-intro-bounce-1401"


def _summary(
    *,
    programme="intro_bounce_loop",
    strict_transport_clean=True,
    primary_and_secondary_present=True,
    vpml_mode_on_all_records=True,
    chip_identity_match=True,
):
    return {
        "result": "PASS",
        "passed": True,
        "runtime": {
            "port": "/dev/cu.usbmodem1401",
            "expected_chip_id": "F887A500",
            "observed_chip_id": "F887A500",
            "vpml_final_status": "VPML active=0 programme=%s frame=0 frames=96 loops=1 vpab_mode=250"
            % programme,
        },
        "acceptance": {
            "chip_identity_match": chip_identity_match,
            "no_dark_sample_records": True,
            "nonzero_final_bytes_on_required_channels": True,
            "primary_and_secondary_present": primary_and_secondary_present,
            "strict_transport_clean": strict_transport_clean,
            "vp_perf_no_over_or_dropped_frames": True,
            "vpml_mode_on_all_records": vpml_mode_on_all_records,
            "vpml_started_and_stopped": True,
        },
        "decoded_vpab_bytes": {
            "channel_counts": {"primary": 1, "secondary": 1}
            if primary_and_secondary_present
            else {"primary": 1},
            "channel_energy_sum_total": {"primary": 1200, "secondary": 1400},
            "channel_max_byte": {"primary": 100, "secondary": 120},
            "channel_nonzero_led_bytes_total": {"primary": 12, "secondary": 14},
            "dark_sample_records": [],
            "expected_mode": 250,
            "mode_counts": {"250": 2} if vpml_mode_on_all_records else {"249": 2},
            "records": [
                {
                    "channel": "primary",
                    "energy_sum": 1200,
                    "mode": 250 if vpml_mode_on_all_records else 249,
                    "record_frame": 36,
                    "seq": 1,
                },
                {
                    "channel": "secondary",
                    "energy_sum": 1400,
                    "mode": 250 if vpml_mode_on_all_records else 249,
                    "record_frame": 36,
                    "seq": 2,
                },
            ],
        },
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload) + "\n")


def _write_capture(root, capture_id, summary):
    _write_json(root / ("%s.vpml-summary.json" % capture_id), summary)
    _write_json(
        root / ("%s.frame-gate.json" % capture_id),
        {
            "passed": True,
            "counts": {"failures": 0, "issues": 0},
            "stream": {"begin": {"dropped": 0, "overflowed": 0}, "end": {"dropped": 0, "overflowed": 0}},
        },
    )
    (root / ("%s.raw.log" % capture_id)).write_text("VPML synthetic raw log\n")
    (root / ("%s.frames.log" % capture_id)).write_text("")


class VPMLEvidencePageTest(unittest.TestCase):
    def test_current_captures_are_classified_from_existing_evidence(self):
        page = vpml_evidence_page.build_page(EVIDENCE)
        captures = {item["capture_id"]: item for item in page["captures"]}

        self.assertGreaterEqual(page["capture_count"], 3)
        self.assertTrue({ACCEPTED_ID, REJECTED_ID, DARK_ID}.issubset(set(captures)))
        for capture_id in (ACCEPTED_ID, REJECTED_ID, DARK_ID):
            capture = captures[capture_id]
            self.assertIn("summary", capture["paths"])
            self.assertIn("frame_gate", capture["paths"])
            self.assertIn("frames_log", capture["paths"])
            self.assertIn("raw_log", capture["paths"])

        accepted = captures[ACCEPTED_ID]
        self.assertEqual(accepted["page_state"], "byte_clean")
        self.assertEqual(accepted["byte_status"], "byte_clean")
        self.assertEqual(accepted["visual_status"], "eyes_on_pending")
        self.assertEqual(accepted["programme"], "intro_bounce_loop")
        self.assertEqual(accepted["device"]["observed_chip_id"], "F887A500")
        self.assertEqual(accepted["gate"]["strict_transport_clean"], True)
        self.assertEqual(accepted["readbacks"]["channel_counts"], {"primary": 15, "secondary": 15})

        rejected = captures[REJECTED_ID]
        self.assertEqual(rejected["page_state"], "transport_failed")
        self.assertEqual(rejected["byte_status"], "transport_failed")
        self.assertEqual(rejected["gate"]["strict_transport_clean"], False)
        self.assertTrue(any(item["metric"] == "strict_parse" for item in rejected["failures"]))
        self.assertEqual(rejected["gate"]["stream"]["begin"]["dropped"], 28)
        self.assertEqual(rejected["gate"]["stream"]["begin"]["overflowed"], 1)

        dark = captures[DARK_ID]
        self.assertEqual(dark["page_state"], "dark_sample_warning")
        self.assertEqual(dark["byte_status"], "byte_clean_with_observations")
        self.assertEqual(dark["programme"], "intro_bounce")
        self.assertEqual(len(dark["readbacks"]["dark_sample_records"]), 2)

    def test_motion_readability_uses_centre_origin_profiles(self):
        capture = vpml_evidence_page.build_capture(
            vpml_evidence_page.discover_captures(EVIDENCE)[ACCEPTED_ID]
        )
        readability = capture["motion_readability"]

        self.assertEqual(readability["centre_origin"], {"left": 79, "right": 80})
        self.assertEqual(readability["radius_count"], 80)
        self.assertGreaterEqual(len(readability["profiles"]), 2)
        first = readability["profiles"][0]
        self.assertIn(first["channel"], ("primary", "secondary"))
        self.assertEqual(first["proof_label"], "evidence")
        self.assertEqual(first["proof_basis"], "frames_log_payload")
        self.assertEqual(len(first["radius_energy"]), 80)
        self.assertGreater(first["total_energy"], 0)
        self.assertGreaterEqual(first["peak_radius"], 0)
        self.assertLessEqual(first["peak_radius"], 79)
        self.assertEqual(readability["source"], "frames_log")
        self.assertEqual(readability["proof_labels"]["centre_origin_terrain"], "evidence")
        self.assertTrue(readability["frame_deltas"])

    def test_missing_and_malformed_evidence_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad-vpml-demo.frame-gate.json").write_text("{}\n")
            (root / "malformed-vpml-demo.vpml-summary.json").write_text("{not json\n")
            _write_json(root / "summary-only-vpml-demo.vpml-summary.json", _summary())
            _write_json(root / "bad-frame-gate-vpml-demo.vpml-summary.json", _summary())
            (root / "bad-frame-gate-vpml-demo.frame-gate.json").write_text("{not json\n")
            page = vpml_evidence_page.build_page(root)
            captures = {item["capture_id"]: item for item in page["captures"]}

        self.assertEqual(captures["bad-vpml-demo"]["page_state"], "missing_files")
        self.assertEqual(captures["bad-vpml-demo"]["byte_status"], "not_evaluated")
        self.assertEqual(captures["malformed-vpml-demo"]["page_state"], "malformed_evidence")
        self.assertEqual(captures["malformed-vpml-demo"]["byte_status"], "not_evaluated")
        self.assertEqual(captures["summary-only-vpml-demo"]["page_state"], "missing_files")
        self.assertEqual(captures["summary-only-vpml-demo"]["byte_status"], "not_evaluated")
        self.assertTrue(any(item["metric"] == "raw_log" for item in captures["summary-only-vpml-demo"]["failures"]))
        self.assertTrue(any(item["metric"] == "frames_log" for item in captures["summary-only-vpml-demo"]["failures"]))
        self.assertTrue(any(item["metric"] == "frame_gate" for item in captures["summary-only-vpml-demo"]["failures"]))
        self.assertEqual(captures["bad-frame-gate-vpml-demo"]["page_state"], "malformed_evidence")
        self.assertEqual(captures["bad-frame-gate-vpml-demo"]["byte_status"], "not_evaluated")
        self.assertTrue(
            any(
                item["metric"] == "frame_gate" and "malformed JSON" in item["message"]
                for item in captures["bad-frame-gate-vpml-demo"]["failures"]
            )
        )

    def test_cli_writes_json_and_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "vpml-page.json"
            html = Path(tmp) / "vpml-page.html"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--evidence-dir",
                    str(EVIDENCE),
                    "--capture-id",
                    ACCEPTED_ID,
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
            html_text = html.read_text()

        self.assertEqual(payload["captures"][0]["capture_id"], ACCEPTED_ID)
        self.assertEqual(payload["captures"][0]["page_state"], "byte_clean")
        self.assertIn("eyes-on pending", html_text.lower())
        self.assertIn("byte proof only", html_text.lower())

    def test_programme_registry_is_fixed_builtins_only(self):
        page = vpml_evidence_page.build_page(EVIDENCE)
        registry = page["programme_registry"]
        programmes = [item["programme"] for item in registry]
        firmware_source = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "diag" / "vp_motion_lab.h").read_text()
        by_id = {item["programme"]: item for item in registry}

        self.assertEqual(programmes, ["intro_bounce_loop", "intro_bounce"])
        self.assertEqual(sum(1 for item in registry if item.get("default")), 1)
        for item in registry:
            self.assertIn("play_builtin,%s" % item["programme"], firmware_source)
            self.assertIn(item["play_command"], {
                ":vpml=play_builtin,intro_bounce_loop",
                ":vpml=play_builtin,intro_bounce",
            })
            self.assertNotIn("compile", json.dumps(item).lower())
            self.assertNotIn("upload", json.dumps(item).lower())
            self.assertNotIn("raw", json.dumps(item).lower())
        self.assertEqual(by_id["intro_bounce_loop"]["frames"], 96)
        self.assertTrue(by_id["intro_bounce_loop"]["default"])
        self.assertEqual(by_id["intro_bounce"]["frames"], 112)
        self.assertIn("fade-trough dark samples", by_id["intro_bounce"]["notes"])

    def test_protocol_readiness_lock_hides_authoring_controls(self):
        page = vpml_evidence_page.build_page(EVIDENCE)
        lock = page["protocol_lock"]

        self.assertEqual(lock["state"], "locked_no_adr")
        self.assertEqual(lock["hidden_controls"], ["programme.compile", "programme.upload", "raw_receive"])
        self.assertIn("transport_adr", lock["missing"])
        self.assertIn("host_protocol_fixtures", lock["missing"])
        self.assertIn("firmware_validator_tests", lock["missing"])
        self.assertIn("captain_approval", lock["missing"])
        self.assertNotIn("programme.compile", lock.get("available_controls", []))
        self.assertIn("fixed built-ins only", lock["reason"])
        self.assertNotIn("authoring", vpml_evidence_page.render_html(page).lower())
        self.assertNotIn("production ready", vpml_evidence_page.render_html(page).lower())
        self.assertNotIn("audio reactive", vpml_evidence_page.render_html(page).lower())

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

    def test_missing_secondary_and_mode_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_capture(root, "missing-secondary-vpml-demo", _summary(primary_and_secondary_present=False))
            _write_capture(root, "mode-mismatch-vpml-demo", _summary(vpml_mode_on_all_records=False))
            page = vpml_evidence_page.build_page(root)
            captures = {item["capture_id"]: item for item in page["captures"]}

        self.assertEqual(captures["missing-secondary-vpml-demo"]["page_state"], "coverage_failed")
        self.assertEqual(captures["missing-secondary-vpml-demo"]["byte_status"], "coverage_failed")
        self.assertEqual(captures["missing-secondary-vpml-demo"]["readbacks"]["channel_counts"], {"primary": 1})
        self.assertFalse(captures["missing-secondary-vpml-demo"]["gate"]["primary_and_secondary_present"])
        self.assertTrue(
            any(
                item["metric"] == "channel_coverage" and item["missing"] == ["secondary"]
                for item in captures["missing-secondary-vpml-demo"]["failures"]
            )
        )
        self.assertEqual(captures["mode-mismatch-vpml-demo"]["page_state"], "mode_failed")
        self.assertEqual(captures["mode-mismatch-vpml-demo"]["byte_status"], "coverage_failed")
        self.assertFalse(captures["mode-mismatch-vpml-demo"]["gate"]["vpml_mode_on_all_records"])
        self.assertEqual(captures["mode-mismatch-vpml-demo"]["readbacks"]["mode_counts"], {"249": 2})
        self.assertTrue(
            any(
                item["metric"] == "vpml_mode" and item["expected"] == 250
                for item in captures["mode-mismatch-vpml-demo"]["failures"]
            )
        )

    def test_frame_gate_failure_preempts_dark_sample_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = _summary()
            summary["decoded_vpab_bytes"]["dark_sample_records"] = [
                {"channel": "primary", "record_frame": 36}
            ]
            _write_capture(root, "transport-dark-vpml-demo", summary)
            _write_json(
                root / "transport-dark-vpml-demo.frame-gate.json",
                {
                    "passed": False,
                    "failures": [{"metric": "dropped", "message": "dropped records observed"}],
                    "issues": [{"line": 12, "message": "unexpected stream fragment"}],
                    "counts": {"failures": 1, "issues": 1},
                    "stream": {"begin": {"dropped": 1}, "end": {"dropped": 1}},
                },
            )
            capture = vpml_evidence_page.build_page(root)["captures"][0]

        self.assertEqual(capture["page_state"], "transport_failed")
        self.assertEqual(capture["byte_status"], "transport_failed")
        self.assertTrue(any(item["metric"] == "strict_parse" for item in capture["failures"]))

    def test_stale_annotation_cannot_upgrade_visual_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_capture(root, "accepted-vpml-demo", _summary())
            _write_json(
                root / "accepted-vpml-demo.vpml-annotation.json",
                {
                    "schema": "vpml_annotation.v1",
                    "capture_id": "different-vpml-demo",
                    "programme": "intro_bounce_loop",
                    "visual_status": "captain_accepted",
                    "verdict": "accepted",
                    "accepted_by": "Captain",
                    "accepted_at": "2026-06-09T20:00:00Z",
                    "review_source": "Captain eyes-on",
                },
            )
            capture = vpml_evidence_page.build_page(root)["captures"][0]

        self.assertEqual(capture["page_state"], "blocked_stale_annotation")
        self.assertEqual(capture["byte_status"], "byte_clean")
        self.assertEqual(capture["visual_status"], "eyes_on_pending")
        self.assertTrue(capture["annotation"]["stale"])
        self.assertTrue(any(item["metric"] == "annotation_stale" for item in capture["failures"]))

    def test_annotation_programme_mismatch_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_capture(root, "accepted-vpml-demo", _summary())
            _write_json(
                root / "accepted-vpml-demo.vpml-annotation.json",
                {
                    "schema": "vpml_annotation.v1",
                    "capture_id": "accepted-vpml-demo",
                    "programme": "intro_bounce",
                    "visual_status": "captain_accepted",
                    "verdict": "accepted",
                    "accepted_by": "Captain",
                    "accepted_at": "2026-06-09T20:00:00Z",
                    "review_source": "Captain eyes-on",
                },
            )
            capture = vpml_evidence_page.build_page(root)["captures"][0]

        self.assertEqual(capture["page_state"], "blocked_stale_annotation")
        self.assertEqual(capture["visual_status"], "eyes_on_pending")
        self.assertTrue(capture["annotation"]["stale"])
        self.assertTrue(any(item["metric"] == "annotation_stale" for item in capture["failures"]))

    def test_annotation_source_summary_and_device_mismatch_are_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_capture(root, "accepted-vpml-demo", _summary())
            _write_json(
                root / "accepted-vpml-demo.vpml-annotation.json",
                {
                    "schema": "vpml_annotation.v1",
                    "capture_id": "accepted-vpml-demo",
                    "programme": "intro_bounce_loop",
                    "device": {
                        "expected_chip_id": "F887A500",
                        "observed_chip_id": "WRONG",
                    },
                    "source_summary": "different-vpml-demo.vpml-summary.json",
                    "visual_status": "captain_accepted",
                    "verdict": "accepted",
                    "accepted_by": "Captain",
                    "accepted_at": "2026-06-09T20:00:00Z",
                    "review_source": "Captain eyes-on",
                },
            )
            capture = vpml_evidence_page.build_page(root)["captures"][0]

        self.assertEqual(capture["page_state"], "blocked_stale_annotation")
        self.assertEqual(capture["visual_status"], "eyes_on_pending")
        self.assertTrue(capture["annotation"]["stale"])
        self.assertTrue(
            any(
                item["metric"] == "annotation_stale" and item["field"] == "source_summary"
                for item in capture["failures"]
            )
        )
        self.assertTrue(
            any(
                item["metric"] == "annotation_stale" and item["field"] == "device.observed_chip_id"
                for item in capture["failures"]
            )
        )

    def test_acceptance_annotation_requires_review_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_capture(root, "accepted-vpml-demo", _summary())
            _write_json(
                root / "accepted-vpml-demo.vpml-annotation.json",
                {
                    "schema": "vpml_annotation.v1",
                    "capture_id": "accepted-vpml-demo",
                    "programme": "intro_bounce_loop",
                    "visual_status": "captain_accepted",
                    "verdict": "accepted",
                },
            )
            capture = vpml_evidence_page.build_page(root)["captures"][0]

        self.assertEqual(capture["page_state"], "blocked_no_acceptance_source")
        self.assertEqual(capture["byte_status"], "byte_clean")
        self.assertEqual(capture["visual_status"], "eyes_on_pending")
        self.assertTrue(any(item["metric"] == "acceptance_source" for item in capture["failures"]))

    def test_safe_wording_and_claim_boundaries_are_explicit(self):
        page = vpml_evidence_page.build_page(EVIDENCE)
        html_text = vpml_evidence_page.render_html(page).lower()
        for capture in page["captures"]:
            for key in (
                "beat_tempo_onset_causality",
                "host_preview_equals_k1_output",
                "production_ready",
                "uploaded_programme",
                "compiled_programme",
                "saved_on_k1",
                "tab5_live",
                "ap_connected",
                "rest_websocket_control",
                "byte_clean_equals_captain_acceptance",
            ):
                self.assertIn(key, capture["must_not_claim"])

        for phrase in (
            "looks good",
            "captain accepted",
            "production ready",
            "uploaded programme",
            "compiled programme",
            "saved on k1",
            "tab5 live",
            "ap connected",
            "rest/websocket control",
            "byte-clean equals captain acceptance",
        ):
            self.assertNotIn(phrase, html_text)


if __name__ == "__main__":
    unittest.main()
