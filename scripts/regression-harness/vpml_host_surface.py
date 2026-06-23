#!/usr/bin/env python3
"""Render the VP Motion Lab host-side page-flow surface from local evidence.

This script is a file-backed surface model. It does not scan devices, open K1
ports, upload programmes, compile authoring syntax, use AP/REST/WebSocket
control, or claim visual acceptance.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "forensics" / "runtime-evidence"


def _load_vpml_evidence_page():
    script = Path(__file__).with_name("vpml_evidence_page.py")
    spec = importlib.util.spec_from_file_location("vpml_evidence_page", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpml_evidence_page = _load_vpml_evidence_page()


def _page_by_status(captures: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
    return [capture for capture in captures if capture.get("page_state") == status]


def _latest_capture(captures: list[dict[str, Any]], *, page_state: str | None = None) -> dict[str, Any] | None:
    candidates = captures
    if page_state is not None:
        candidates = _page_by_status(captures, page_state)
    if not candidates:
        return None
    return sorted(candidates, key=lambda capture: capture["capture_id"])[-1]


def _control(control_id: str, label: str, *, enabled: bool, requires: str, data_source: str, values=None) -> dict[str, Any]:
    out = {
        "id": control_id,
        "label": label,
        "enabled": enabled,
        "requires": requires,
        "data_source": data_source,
    }
    if values is not None:
        out["values"] = values
    return out


def _build_run_console(evidence_page: dict[str, Any]) -> dict[str, Any]:
    captures = evidence_page["captures"]
    latest = _latest_capture(captures)
    latest_byte_clean = _latest_capture(captures, page_state="byte_clean")
    latest_readback = latest_byte_clean or latest or {}
    device = latest_readback.get("device") or {}

    return {
        "id": "vpml_run_console",
        "title": "VPML Run Console",
        "state": "offline_evidence_loaded" if captures else "no_evidence_loaded",
        "user_job": "Run the existing VPML built-ins on a verified K1 and generate evidence from the live serial capture loop.",
        "primary_workflow": [
            "Load local runtime evidence.",
            "Inspect latest byte-clean capture and pending visual status.",
            "Open the picker or evidence gate.",
            "Keep live K1 controls disabled until a separate live host runner verifies device identity.",
        ],
        "controls": [
            _control("evidence.refresh", "Refresh Evidence", enabled=True, requires="local_files", data_source="evidence_dir"),
            _control("device.scan", "Scan Device", enabled=True, requires="vpml_live_runner scan", data_source="host_device_adapter"),
            _control("device.identify", "Identify Device", enabled=True, requires="port_and_chip_guard", data_source="typed_usb_cdc"),
            _control("vpml.status", "Read VPML Status", enabled=True, requires="port_and_chip_guard", data_source="typed_usb_cdc"),
            _control("programme.open_picker", "Open Programme Picker", enabled=True, requires="programme_registry", data_source="programme_registry"),
            _control("programme.play_builtin", "Play Built-In", enabled=True, requires="port_and_chip_guard", data_source="vpml_live_runner play"),
            _control("programme.stop", "Stop VPML", enabled=True, requires="port_and_chip_guard", data_source="vpml_live_runner stop"),
            _control("capture.start", "Start Capture", enabled=True, requires="port_and_chip_guard", data_source="vpml_live_runner capture"),
        ],
        "readbacks": {
            "evidence_dir": evidence_page["evidence_dir"],
            "capture_count": evidence_page["capture_count"],
            "latest_capture": latest.get("capture_id") if latest else None,
            "latest_byte_clean_capture": latest_byte_clean.get("capture_id") if latest_byte_clean else None,
            "latest_visual_status": latest_readback.get("visual_status"),
            "latest_byte_status": latest_readback.get("byte_status"),
            "programme": latest_readback.get("programme"),
            "port": device.get("port"),
            "expected_chip_id": device.get("expected_chip_id"),
            "observed_chip_id": device.get("observed_chip_id"),
            "runner_commands": {
                "scan": "python3 scripts/regression-harness/vpml_live_runner.py scan",
                "identify": "python3 scripts/regression-harness/vpml_live_runner.py identify --port <port> --expect-chip-id F887A500",
                "status": "python3 scripts/regression-harness/vpml_live_runner.py status --port <port> --expect-chip-id F887A500",
                "play_loop": "python3 scripts/regression-harness/vpml_live_runner.py play --port <port> --programme intro_bounce_loop --expect-chip-id F887A500",
                "stop": "python3 scripts/regression-harness/vpml_live_runner.py stop --port <port> --expect-chip-id F887A500",
                "capture_loop": "python3 scripts/regression-harness/vpml_live_runner.py capture --port <port> --programme intro_bounce_loop --expect-chip-id F887A500",
            },
        },
        "data_sources": {
            "capture_count": "vpml_evidence_page.build_page().capture_count",
            "latest_byte_clean_capture": "latest capture with page_state=byte_clean",
            "latest_visual_status": "capture.visual_status",
            "device_identity": "capture.device from VPML runtime summary",
            "controls": "vpml_live_runner.py command boundary plus static authoring locks",
        },
        "failure_states": ["no_evidence_loaded", "missing_files", "malformed_evidence", "transport_failed", "identity_failed"],
        "must_not_claim": list(vpml_evidence_page.MUST_NOT_CLAIM),
        "acceptance_evidence": ["local JSON surface renders", "live runner command paths are exposed", "latest capture remains eyes_on_pending"],
        "implementation_prerequisites": ["K1 connected over USB CDC", "matching chip identity", "non-shippable VPML firmware already flashed"],
        "tests_harnesses": ["tests/test_vpml_host_surface.py", "tests/test_vpml_live_runner.py", "tests/test_vpml_evidence_page.py"],
    }


def _build_picker(evidence_page: dict[str, Any]) -> dict[str, Any]:
    programmes = evidence_page["programme_registry"]
    programme_ids = [item["programme"] for item in programmes]
    return {
        "id": "programme_parameter_picker",
        "title": "Programme + Parameter Picker",
        "state": "fixed_builtins_only",
        "user_job": "Choose one of the current VPML built-ins without implying authoring support.",
        "primary_workflow": ["Open layer.", "Select fixed built-in.", "Return selection to Run Console.", "Live play remains locked in this static surface."],
        "controls": [
            _control("programme.select", "Select Programme", enabled=True, requires="programme_registry", data_source="programme_registry", values=programme_ids),
            _control("picker.close", "Close Picker", enabled=True, requires="browser_state", data_source="host_surface"),
        ],
        "readbacks": {
            "programmes": programmes,
            "default_programme": next((item["programme"] for item in programmes if item.get("default")), None),
            "parameter_model": "none_current_mvp",
            "supported_commands": [item["play_command"] for item in programmes],
        },
        "data_sources": {
            "programmes": "vpml_evidence_page.PROGRAMME_METADATA",
            "supported_commands": "fixed built-in command metadata",
            "parameter_model": "current MVP boundary",
        },
        "failure_states": ["unknown_programme", "live_play_locked", "unsupported_parameter"],
        "must_not_claim": ["custom_authoring", "runtime_upload", "compiled_programme", "saved_on_k1"],
        "acceptance_evidence": ["only intro_bounce_loop and intro_bounce appear", "no compile/upload/raw controls are present"],
        "implementation_prerequisites": ["firmware command support for any new built-in", "updated programme registry test"],
        "tests_harnesses": ["tests/test_vpml_host_surface.py::VPMLHostSurfaceTest::test_picker_exposes_fixed_builtins_only"],
    }


def _build_evidence_gate(evidence_page: dict[str, Any]) -> dict[str, Any]:
    captures = evidence_page["captures"]
    byte_clean = [capture["capture_id"] for capture in _page_by_status(captures, "byte_clean")]
    transport_failed = [capture["capture_id"] for capture in _page_by_status(captures, "transport_failed")]
    dark_sample = [capture["capture_id"] for capture in _page_by_status(captures, "dark_sample_warning")]
    state = "byte_clean_pending_visual" if byte_clean else "no_byte_clean_capture"
    return {
        "id": "evidence_gate_motion_readability",
        "title": "Evidence Gate / Motion Readability",
        "state": state,
        "user_job": "Separate transport proof, final-byte readability, and visual acceptance status.",
        "primary_workflow": ["Review strict gate state.", "Inspect centre-origin motion profiles.", "Compare rejected and accepted captures.", "Record visual status only through explicit annotation."],
        "controls": [
            _control("evidence.open_json", "Open Evidence JSON", enabled=True, requires="local_files", data_source="vpml_evidence_page"),
            _control("evidence.open_html", "Open Evidence HTML", enabled=True, requires="local_files", data_source="vpml_evidence_page"),
            _control("capture.annotate", "Record Visual Review", enabled=False, requires="captain_review_source", data_source="annotation_sidecar"),
        ],
        "readbacks": {
            "capture_count": evidence_page["capture_count"],
            "byte_clean_captures": byte_clean,
            "transport_failed_captures": transport_failed,
            "dark_sample_captures": dark_sample,
            "captures": [
                {
                    "capture_id": capture["capture_id"],
                    "programme": capture["programme"],
                    "page_state": capture["page_state"],
                    "byte_status": capture["byte_status"],
                    "visual_status": capture["visual_status"],
                    "motion_source": capture["motion_readability"]["source"],
                    "profile_count": len(capture["motion_readability"]["profiles"]),
                }
                for capture in captures
            ],
        },
        "data_sources": {
            "capture_rollup": "vpml_evidence_page.build_page().captures",
            "motion_readability": "*.frames.log VPAB byte payloads when present",
            "visual_status": "*.vpml-annotation.json sidecar or eyes_on_pending",
        },
        "failure_states": ["transport_failed", "coverage_failed", "mode_failed", "dark_sample_warning", "blocked_stale_annotation"],
        "must_not_claim": list(vpml_evidence_page.MUST_NOT_CLAIM),
        "acceptance_evidence": ["strict transport clean", "primary and secondary present", "mode 250 on records", "Captain eyes-on or equivalent review source"],
        "implementation_prerequisites": ["annotation writer after review workflow is approved"],
        "tests_harnesses": ["tests/test_vpml_evidence_page.py", "tests/test_vpml_host_surface.py"],
    }


def _build_protocol_lock(evidence_page: dict[str, Any]) -> dict[str, Any]:
    lock = evidence_page["protocol_lock"]
    return {
        "id": "protocol_readiness_authoring_lock",
        "title": "Protocol Readiness / Authoring Lock",
        "state": lock["state"],
        "user_job": "Show why authoring, upload, and raw receive remain unavailable.",
        "primary_workflow": ["Read missing readiness evidence.", "Leave authoring controls hidden.", "Return to evidence gate until protocol prerequisites exist."],
        "controls": [],
        "readbacks": {
            "hidden_controls": lock["hidden_controls"],
            "available_controls": lock.get("available_controls", []),
            "missing": lock.get("missing", []),
            "reason": lock["reason"],
        },
        "data_sources": {"protocol_lock": "vpml_evidence_page.build_page().protocol_lock"},
        "failure_states": ["locked_no_adr", "blocked_no_protocol_fixtures", "blocked_no_captain_approval"],
        "must_not_claim": ["authoring_ready", "upload_ready", "raw_receive_available", "runtime_code_allowed"],
        "acceptance_evidence": ["hidden controls remain hidden", "missing readiness list is visible"],
        "implementation_prerequisites": ["transport ADR", "host protocol fixtures", "firmware validator tests", "live transport proof", "Captain approval"],
        "tests_harnesses": ["tests/test_vpml_host_surface.py::VPMLHostSurfaceTest::test_evidence_gate_and_protocol_lock_share_evidence_page_contract"],
    }


def _build_ledger() -> dict[str, Any]:
    return {
        "id": "promotion_regression_ledger",
        "title": "Promotion + Regression Ledger",
        "state": "deferred_no_candidates",
        "user_job": "Keep promotion out of the MVP until there is accepted visual evidence.",
        "primary_workflow": ["Do nothing in the current MVP.", "Create a candidate only after visual acceptance and native promotion design exist."],
        "controls": [],
        "readbacks": {
            "candidate_count": 0,
            "candidate_ids": [],
            "deferred_reason": "No VPML capture has Captain eyes-on acceptance.",
        },
        "data_sources": {"candidate_count": "not implemented; deferred ledger is empty by design"},
        "failure_states": ["deferred_no_candidates", "blocked_no_visual_acceptance"],
        "must_not_claim": ["native_promotion_ready", "regression_baseline_ready", "shipping_effect_candidate"],
        "acceptance_evidence": ["no promotion controls exposed"],
        "implementation_prerequisites": ["Captain eyes-on acceptance", "native implementation design", "regression baseline capture", "promotion review checklist"],
        "tests_harnesses": ["tests/test_vpml_host_surface.py::VPMLHostSurfaceTest::test_deferred_ledger_has_no_promotion_controls"],
    }


def build_surface(evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> dict[str, Any]:
    evidence_page = vpml_evidence_page.build_page(Path(evidence_dir))
    pages = [
        _build_run_console(evidence_page),
        _build_picker(evidence_page),
        _build_evidence_gate(evidence_page),
        _build_protocol_lock(evidence_page),
        _build_ledger(),
    ]
    return {
        "schema": "vpml_host_surface.v1",
        "evidence_schema": evidence_page["schema"],
        "proof_boundary": "host_file_review_only",
        "evidence_dir": evidence_page["evidence_dir"],
        "pages": pages,
        "global_constraints": [
            "fixed built-ins only",
            "no firmware changes",
            "no AP/REST/WebSocket control",
            "no raw receive",
            "no host compiler",
            "no visual acceptance without Captain review source",
        ],
    }


def _label(text: str) -> str:
    return text.replace("_", " ")


def render_html(surface: dict[str, Any]) -> str:
    sections = []
    for page in surface["pages"]:
        readbacks = page.get("readbacks") or {}
        rows = []
        for key, value in readbacks.items():
            if isinstance(value, (dict, list)):
                display = json.dumps(value, sort_keys=True)
            else:
                display = "" if value is None else str(value)
            rows.append(
                "<tr><th>%s</th><td>%s</td></tr>"
                % (html.escape(_label(key)), html.escape(display))
            )
        sections.append(
            """
    <section>
      <h2>%s</h2>
      <p><strong>State:</strong> %s</p>
      <p>%s</p>
      <table>%s</table>
    </section>
            """
            % (
                html.escape(page["title"]),
                html.escape(_label(page["state"])),
                html.escape(page["user_job"]),
                "\n".join(rows),
            )
        )
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VPML Host Surface</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: #1f2933; }
    section { margin: 0 0 28px; }
    table { border-collapse: collapse; width: 100%%; table-layout: fixed; }
    th, td { border: 1px solid #c8d1dc; padding: 8px 10px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
    th { width: 220px; background: #eef3f8; }
    .notice { margin: 16px 0 24px; padding: 12px; border-left: 4px solid #b45309; background: #fff8eb; }
  </style>
</head>
<body>
  <h1>VPML Host Surface</h1>
  <div class="notice">Byte proof only. Eyes-on pending until Captain visual acceptance is explicitly recorded.</div>
  %s
</body>
</html>
""" % "\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--out")
    parser.add_argument("--html")
    args = parser.parse_args(argv)

    surface = build_surface(Path(args.evidence_dir))
    output = json.dumps(surface, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if args.html:
        Path(args.html).write_text(render_html(surface), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
