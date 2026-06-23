#!/usr/bin/env python3
"""Build VP Motion Lab evidence-page data from local runtime artefacts.

This is a host-side evidence reader only. It classifies existing VPML captures,
derives centre-origin final-byte readability summaries, and writes optional
JSON/HTML output. It does not open serial, upload programmes, compile authoring
syntax, or claim visual acceptance.
"""

from __future__ import annotations

import argparse
import binascii
import html
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "forensics" / "runtime-evidence"
CENTRE_ORIGIN = {"left": 79, "right": 80}
LED_COUNT = 160
LED_BYTE_COUNT = LED_COUNT * 3
VPML_MODE = 250
REQUIRED_CAPTURE_PATHS = ("summary", "frame_gate", "frames_log", "raw_log")


CHANNEL_NAMES = {
    0: "primary",
    1: "secondary",
}


def _load_vpab_frame_gate():
    script = Path(__file__).with_name("vpab_frame_gate.py")
    spec = importlib.util.spec_from_file_location("vpab_frame_gate", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpab_frame_gate = _load_vpab_frame_gate()


PROGRAMME_METADATA = {
    "intro_bounce_loop": {
        "programme": "intro_bounce_loop",
        "label": "Intro Bounce Loop",
        "frames": 96,
        "play_command": ":vpml=play_builtin,intro_bounce_loop",
        "default": True,
        "notes": "Loop-safe built-in preview; byte-clean evidence exists, eyes-on pending.",
    },
    "intro_bounce": {
        "programme": "intro_bounce",
        "label": "Intro Bounce",
        "frames": 112,
        "play_command": ":vpml=play_builtin,intro_bounce",
        "default": False,
        "notes": "Boot-shaped reference; may include fade-trough dark samples when looped.",
    },
}


MUST_NOT_CLAIM = [
    "visual_quality",
    "product_fitness",
    "native_effect_parity",
    "audio_responsiveness",
    "captain_acceptance_from_bytes",
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
]


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, "malformed JSON: %s" % exc


def _crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def _le16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def _assemble_payload(record: dict[str, Any]) -> tuple[bytes | None, dict[str, Any] | None]:
    payload = bytearray(record["len"] or 0)
    for index in range(record["chunks"] or 0):
        chunk = record["chunk_items"].get(index)
        if chunk is None:
            return None, {"seq": record["seq"], "metric": "chunk", "message": "missing K1DF chunk", "observed": index}
        offset = chunk["off"]
        payload[offset:offset + len(chunk["payload"])] = chunk["payload"]
    out = bytes(payload)
    if record["crc"] is not None and _crc32(out) != record["crc"]:
        return None, {"seq": record["seq"], "metric": "crc", "message": "record CRC mismatch"}
    return out, None


def _decode_vpab_bytes_payload(record: dict[str, Any], payload: bytes) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if len(payload) < 32:
        return None, {
            "seq": record["seq"],
            "metric": "payload",
            "message": "VPAB bytes payload header is truncated",
            "observed": len(payload),
        }
    channel_id = payload[0]
    channel = CHANNEL_NAMES.get(channel_id)
    if channel is None:
        return None, {"seq": record["seq"], "metric": "channel", "message": "unknown VPAB channel", "observed": channel_id}

    byte_count = _le16(payload, 6)
    if byte_count > len(payload) - 32:
        return None, {
            "seq": record["seq"],
            "metric": "byte_count",
            "message": "byte_count overruns decoded payload",
            "observed": byte_count,
            "available": len(payload) - 32,
        }

    return {
        "seq": record["seq"],
        "record_frame": record["frame"],
        "channel": channel,
        "channel_id": channel_id,
        "mode": payload[1],
        "leds": _le16(payload, 4),
        "byte_count": byte_count,
        "_led_bytes": list(payload[32:32 + byte_count]),
    }, None


def _records_from_frames_log(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], [{"metric": "frames_log", "message": str(exc)}]

    _begin, _end, records, record_order, issues = vpab_frame_gate._parse_stream(text)
    failures = [{"metric": "strict_parse", **issue} for issue in issues]
    decoded_records = []
    for seq in record_order:
        record = records[seq]
        if record["kind"] != 2:
            continue
        payload, failure = _assemble_payload(record)
        if failure:
            failures.append(failure)
            continue
        decoded, failure = _decode_vpab_bytes_payload(record, payload)
        if failure:
            failures.append(failure)
            continue
        decoded_records.append(decoded)
    return decoded_records, failures


def _capture_id_from_path(path: Path) -> str:
    name = path.name
    suffixes = (
        ".vpml-summary-v2.json",
        ".vpml-summary.json",
        ".frame-gate.json",
        ".summary.json",
        ".frames.log",
        ".raw.log",
        ".vpml-annotation.json",
    )
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def discover_captures(evidence_dir: Path) -> dict[str, dict[str, Path]]:
    """Return capture artefact paths keyed by capture id."""

    evidence_dir = Path(evidence_dir)
    captures: dict[str, dict[str, Path]] = {}
    if not evidence_dir.exists():
        return captures
    for path in evidence_dir.iterdir():
        if not path.is_file() or "vpml" not in path.name:
            continue
        capture_id = _capture_id_from_path(path)
        item = captures.setdefault(capture_id, {"capture_id": capture_id, "evidence_dir": evidence_dir})
        name = path.name
        if name.endswith(".vpml-summary.json") or name.endswith(".vpml-summary-v2.json"):
            item["summary"] = path
        elif name.endswith(".frame-gate.json"):
            item["frame_gate"] = path
        elif name.endswith(".frames.log"):
            item["frames_log"] = path
        elif name.endswith(".raw.log"):
            item["raw_log"] = path
        elif name.endswith(".vpml-annotation.json"):
            item["annotation"] = path
    return dict(sorted(captures.items()))


def _programme_from_runtime(summary: dict[str, Any], capture_id: str) -> str | None:
    runtime = summary.get("runtime") or {}
    for key in ("vpml_initial_status", "vpml_final_status"):
        line = runtime.get(key)
        if not isinstance(line, str):
            continue
        match = re.search(r"programme=([A-Za-z0-9_]+)", line)
        if match and match.group(1) != "none":
            return match.group(1)
    for programme in PROGRAMME_METADATA:
        if programme.replace("_", "-") in capture_id or programme in capture_id:
            return programme
    if "intro-bounce-loop" in capture_id:
        return "intro_bounce_loop"
    if "intro-bounce" in capture_id:
        return "intro_bounce"
    return None


def _classify(summary: dict[str, Any] | None, frame_gate: dict[str, Any] | None) -> tuple[str, str]:
    if summary is None:
        return "missing_files", "not_evaluated"

    acceptance = summary.get("acceptance") or {}
    if not acceptance.get("strict_transport_clean", False):
        return "transport_failed", "transport_failed"
    if not acceptance.get("primary_and_secondary_present", False):
        return "coverage_failed", "coverage_failed"
    if not acceptance.get("vpml_mode_on_all_records", False):
        return "mode_failed", "coverage_failed"
    if not acceptance.get("chip_identity_match", True):
        return "identity_failed", "coverage_failed"
    if summary.get("result") == "FAIL" or summary.get("passed") is False:
        return "gate_failed", "not_evaluated"

    if frame_gate is not None and frame_gate.get("passed") is False:
        return "transport_failed", "transport_failed"

    dark_records = (summary.get("decoded_vpab_bytes") or {}).get("dark_sample_records") or []
    if dark_records:
        return "dark_sample_warning", "byte_clean_with_observations"

    return "byte_clean", "byte_clean"


def _summary_gate_failures(summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not summary:
        return []

    failures = []
    acceptance = summary.get("acceptance") or {}
    decoded = summary.get("decoded_vpab_bytes") or {}
    channel_counts = decoded.get("channel_counts") or {}

    if not acceptance.get("primary_and_secondary_present", True):
        missing = [channel for channel in ("primary", "secondary") if not int(channel_counts.get(channel) or 0)]
        failures.append(
            {
                "metric": "channel_coverage",
                "message": "required VPML primary/secondary channel coverage is missing",
                "missing": missing,
                "observed": channel_counts,
            }
        )

    if not acceptance.get("vpml_mode_on_all_records", True):
        failures.append(
            {
                "metric": "vpml_mode",
                "message": "decoded records do not all use the VPML sentinel mode",
                "expected": VPML_MODE,
                "observed": decoded.get("mode_counts") or {},
            }
        )

    if acceptance.get("chip_identity_match") is False:
        runtime = summary.get("runtime") or {}
        failures.append(
            {
                "metric": "chip_identity",
                "message": "observed chip id does not match expected chip id",
                "expected": runtime.get("expected_chip_id"),
                "observed": runtime.get("observed_chip_id"),
            }
        )

    if not acceptance.get("strict_transport_clean", True):
        failures.append(
            {
                "metric": "strict_transport",
                "message": "strict transport gate was not clean",
            }
        )

    return failures


def _profile_bytes(record: dict[str, Any]) -> tuple[list[int], str, str]:
    actual_bytes = record.get("_led_bytes")
    if isinstance(actual_bytes, list):
        return [int(value) & 0xFF for value in actual_bytes[:LED_BYTE_COUNT]], "evidence", "frames_log_payload"

    bytes_value = record.get("bytes")
    if isinstance(bytes_value, list):
        return [int(value) & 0xFF for value in bytes_value[:LED_BYTE_COUNT]], "evidence", "summary_full_bytes"
    hex_value = record.get("bytes_hex")
    if isinstance(hex_value, str):
        try:
            return list(bytes.fromhex(hex_value))[:LED_BYTE_COUNT], "evidence", "summary_full_bytes_hex"
        except ValueError:
            return [], "invalid", "malformed_summary_full_bytes_hex"

    # Current VPML summaries store per-record aggregate totals, not the full
    # bytes. Preserve centre-origin shape by distributing energy around a stable
    # sampled radius. This is a presentation proxy, not additional proof.
    total = int(record.get("energy_sum") or 0)
    if total <= 0:
        return [0] * LED_BYTE_COUNT, "presentation", "summary_aggregate_zero"
    radius = int(record.get("record_frame") or record.get("seq") or 0) % 80
    values = [0] * LED_BYTE_COUNT
    left = CENTRE_ORIGIN["left"] - radius
    right = CENTRE_ORIGIN["right"] + radius
    value = max(1, min(255, total // 96))
    for led in (left, right):
        if 0 <= led < LED_COUNT:
            offset = led * 3
            values[offset:offset + 3] = [value, value, value]
    return values, "presentation", "summary_aggregate_proxy"


def _radius_energy(led_bytes: list[int]) -> list[int]:
    out = []
    for radius in range(80):
        left = CENTRE_ORIGIN["left"] - radius
        right = CENTRE_ORIGIN["right"] + radius
        energy = 0
        for led in (left, right):
            if 0 <= led < LED_COUNT:
                offset = led * 3
                energy += sum(led_bytes[offset:offset + 3])
        out.append(energy)
    return out


def build_motion_readability(
    summary: dict[str, Any] | None,
    frames_log_path: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records = []
    source = "none"
    failures = []
    if frames_log_path is not None:
        records, failures = _records_from_frames_log(frames_log_path)
        source = "frames_log"
    if not records and summary:
        records = (summary.get("decoded_vpab_bytes") or {}).get("records") or []
        source = "summary_aggregate"

    profiles = []
    for record in records:
        led_bytes, proof_label, proof_basis = _profile_bytes(record)
        radius_energy = _radius_energy(led_bytes)
        total = sum(radius_energy)
        peak_radius = max(range(len(radius_energy)), key=lambda index: radius_energy[index]) if radius_energy else 0
        profiles.append(
            {
                "seq": record.get("seq"),
                "record_frame": record.get("record_frame"),
                "channel": record.get("channel"),
                "proof_label": proof_label,
                "proof_basis": proof_basis,
                "radius_energy": radius_energy,
                "total_energy": total,
                "peak_radius": peak_radius,
            }
        )

    frame_deltas = []
    by_frame: dict[int, dict[str, int]] = {}
    for profile in profiles:
        frame = int(profile.get("record_frame") or -1)
        channel = profile.get("channel")
        if channel not in ("primary", "secondary"):
            continue
        by_frame.setdefault(frame, {})[channel] = int(profile["total_energy"])
    for frame in sorted(by_frame):
        item = by_frame[frame]
        if "primary" in item and "secondary" in item:
            frame_deltas.append(
                {
                    "record_frame": frame,
                    "primary_energy": item["primary"],
                    "secondary_energy": item["secondary"],
                    "delta": item["primary"] - item["secondary"],
                }
            )

    has_presentation_proxy = any(profile["proof_label"] == "presentation" for profile in profiles)
    has_actual_bytes = any(profile["proof_label"] == "evidence" for profile in profiles)
    view_source_label = "evidence" if has_actual_bytes and not has_presentation_proxy else "presentation"

    return {
        "centre_origin": dict(CENTRE_ORIGIN),
        "radius_count": 80,
        "source": source,
        "views": ["heatmap", "centre_origin_terrain", "primary_secondary_delta", "energy_trace"],
        "proof_labels": {
            "heatmap": view_source_label,
            "centre_origin_terrain": view_source_label,
            "primary_secondary_delta": "evidence" if profiles else "not_evaluated",
            "energy_trace": "evidence" if profiles else "not_evaluated",
        },
        "profiles": profiles,
        "frame_deltas": frame_deltas,
    }, failures


def _visual_status(annotation: dict[str, Any] | None) -> str:
    if not annotation:
        return "eyes_on_pending"
    status = annotation.get("visual_status")
    if status in {"eyes_on_pending", "captain_accepted", "captain_rejected", "superseded", "not_reviewed"}:
        return status
    return "eyes_on_pending"


def _normalise_visual_status(
    *,
    annotation: dict[str, Any] | None,
    capture_id: str,
    programme: str | None,
    summary_path: Path | None,
    device: dict[str, Any],
    page_state: str,
    failures: list[dict[str, Any]],
) -> tuple[str, str, dict[str, Any] | None]:
    visual_status = _visual_status(annotation)
    if not annotation:
        return page_state, visual_status, annotation

    normalised = dict(annotation)
    stale = False

    def mark_stale(field: str, message: str, expected: Any, observed: Any) -> None:
        nonlocal stale
        stale = True
        normalised["stale"] = True
        failures.append(
            {
                "metric": "annotation_stale",
                "field": field,
                "message": message,
                "expected": expected,
                "observed": observed,
            }
        )

    annotation_capture_id = normalised.get("capture_id")
    if annotation_capture_id and annotation_capture_id != capture_id:
        mark_stale(
            "capture_id",
            "annotation capture_id does not match evidence capture_id",
            capture_id,
            annotation_capture_id,
        )

    annotation_programme = normalised.get("programme")
    if programme and annotation_programme and annotation_programme != programme:
        mark_stale(
            "programme",
            "annotation programme does not match evidence programme",
            programme,
            annotation_programme,
        )

    annotation_summary = normalised.get("source_summary")
    if annotation_summary and summary_path and Path(str(annotation_summary)).name != summary_path.name:
        mark_stale(
            "source_summary",
            "annotation source_summary does not match evidence summary",
            summary_path.name,
            annotation_summary,
        )

    annotation_device = normalised.get("device") if isinstance(normalised.get("device"), dict) else {}
    for field in ("expected_chip_id", "observed_chip_id"):
        observed = annotation_device.get(field)
        expected = device.get(field)
        if observed and expected and observed != expected:
            mark_stale(
                "device.%s" % field,
                "annotation device identity does not match evidence device identity",
                expected,
                observed,
            )

    if stale:
        return "blocked_stale_annotation", "eyes_on_pending", normalised

    if visual_status == "captain_accepted":
        missing = [
            field
            for field in ("accepted_by", "accepted_at", "review_source")
            if not normalised.get(field)
        ]
        if not normalised.get("capture_id"):
            missing.append("capture_id")
        if not normalised.get("programme"):
            missing.append("programme")
        if not normalised.get("source_summary"):
            missing.append("source_summary")
        for field in ("expected_chip_id", "observed_chip_id"):
            if not annotation_device.get(field):
                missing.append("device.%s" % field)
        if missing:
            failures.append(
                {
                    "metric": "acceptance_source",
                    "message": "Captain acceptance requires accepted_by, accepted_at, and review_source",
                    "missing": missing,
                }
            )
            return "blocked_no_acceptance_source", "eyes_on_pending", normalised
        if page_state not in ("byte_clean", "dark_sample_warning"):
            failures.append(
                {
                    "metric": "acceptance_source",
                    "message": "visual acceptance cannot override failed byte evidence",
                    "observed": page_state,
                }
            )
            return "blocked_no_acceptance_source", "eyes_on_pending", normalised

    return page_state, visual_status, normalised


def _load_annotation(paths: dict[str, Path]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    path = paths.get("annotation")
    if path is None:
        return None, []
    payload, error = _read_json(path)
    if error:
        return None, [{"metric": "annotation", "message": error}]
    return payload, []


def build_capture(paths: dict[str, Path]) -> dict[str, Any]:
    capture_id = str(paths["capture_id"])
    summary_path = paths.get("summary")
    frame_gate_path = paths.get("frame_gate")

    failures = []
    summary = None
    frame_gate = None
    summary_malformed = False
    frame_gate_malformed = False
    missing_required = [key for key in REQUIRED_CAPTURE_PATHS if paths.get(key) is None]

    for key in missing_required:
        failures.append({"metric": key, "message": "missing required VPML evidence artefact"})

    if summary_path is None:
        failures.append({"metric": "summary", "message": "missing VPML summary JSON"})
    else:
        summary, error = _read_json(summary_path)
        if error:
            summary_malformed = True
            failures.append({"metric": "summary", "message": error})

    if frame_gate_path is not None:
        frame_gate, error = _read_json(frame_gate_path)
        if error:
            frame_gate_malformed = True
            failures.append({"metric": "frame_gate", "message": error})

    if summary_malformed or frame_gate_malformed:
        page_state, byte_status = "malformed_evidence", "not_evaluated"
    elif missing_required:
        page_state, byte_status = "missing_files", "not_evaluated"
    else:
        page_state, byte_status = _classify(summary, frame_gate)
        failures.extend(summary.get("failures") or [])
        failures.extend(_summary_gate_failures(summary))
        if frame_gate and frame_gate.get("passed") is False:
            failures.extend(frame_gate.get("failures") or [])
            failures.extend({"metric": "strict_parse", **issue} for issue in frame_gate.get("issues") or [])

    annotation, annotation_failures = _load_annotation(paths)
    failures.extend(annotation_failures)
    programme = _programme_from_runtime(summary or {}, capture_id)
    runtime = (summary or {}).get("runtime") or {}
    device = {
        "port": runtime.get("port"),
        "expected_chip_id": runtime.get("expected_chip_id"),
        "observed_chip_id": runtime.get("observed_chip_id"),
    }
    decoded = (summary or {}).get("decoded_vpab_bytes") or {}
    acceptance = (summary or {}).get("acceptance") or {}
    strict_gate = (summary or {}).get("strict_gate") or frame_gate or {}
    motion_readability, motion_failures = build_motion_readability(summary, paths.get("frames_log"))
    failures.extend(motion_failures)

    page_state, visual_status, annotation = _normalise_visual_status(
        annotation=annotation,
        capture_id=capture_id,
        programme=programme,
        summary_path=summary_path,
        device=device,
        page_state=page_state,
        failures=failures,
    )

    return {
        "capture_id": capture_id,
        "page_state": page_state,
        "byte_status": byte_status,
        "visual_status": visual_status,
        "programme": programme,
        "paths": {key: str(value) for key, value in paths.items() if isinstance(value, Path)},
        "device": device,
        "gate": {
            "strict_transport_clean": bool(acceptance.get("strict_transport_clean", False)),
            "primary_and_secondary_present": bool(acceptance.get("primary_and_secondary_present", False)),
            "vpml_mode_on_all_records": bool(acceptance.get("vpml_mode_on_all_records", False)),
            "nonzero_final_bytes_on_required_channels": bool(
                acceptance.get("nonzero_final_bytes_on_required_channels", False)
            ),
            "no_dark_sample_records": bool(acceptance.get("no_dark_sample_records", False)),
            "vp_perf_no_over_or_dropped_frames": bool(acceptance.get("vp_perf_no_over_or_dropped_frames", False)),
            "chip_identity_match": acceptance.get("chip_identity_match"),
            "stream": strict_gate.get("stream") or {},
            "counts": strict_gate.get("counts") or {},
        },
        "readbacks": {
            "channel_counts": decoded.get("channel_counts") or {},
            "channel_nonzero_led_bytes_total": decoded.get("channel_nonzero_led_bytes_total") or {},
            "channel_energy_sum_total": decoded.get("channel_energy_sum_total") or {},
            "channel_max_byte": decoded.get("channel_max_byte") or {},
            "dark_sample_records": decoded.get("dark_sample_records") or [],
            "mode_counts": decoded.get("mode_counts") or {},
            "render_us": decoded.get("render_us") or {},
            "frame_us": decoded.get("frame_us") or {},
            "show_us": decoded.get("show_us") or {},
        },
        "motion_readability": motion_readability,
        "failures": failures,
        "observations": (summary or {}).get("observations") or [],
        "annotation": annotation,
        "must_not_claim": list(MUST_NOT_CLAIM),
    }


def build_page(evidence_dir: Path, capture_id: str | None = None) -> dict[str, Any]:
    captures = discover_captures(Path(evidence_dir))
    selected = []
    for item_id, paths in captures.items():
        if capture_id is not None and item_id != capture_id:
            continue
        selected.append(build_capture(paths))
    selected.sort(key=lambda item: item["capture_id"])
    return {
        "schema": "vpml_evidence_page.v1",
        "evidence_dir": str(Path(evidence_dir)),
        "capture_count": len(selected),
        "captures": selected,
        "programme_registry": list(PROGRAMME_METADATA.values()),
        "protocol_lock": {
            "state": "locked_no_adr",
            "hidden_controls": ["programme.compile", "programme.upload", "raw_receive"],
            "available_controls": ["protocol.readiness.view"],
            "missing": [
                "transport_adr",
                "host_protocol_fixtures",
                "firmware_validator_tests",
                "live_transport_proof",
                "captain_approval",
            ],
            "reason": "Protocol readiness is not proven; fixed built-ins only.",
        },
    }


def _state_label(state: str) -> str:
    return state.replace("_", " ")


def _badge_class(value: str | None) -> str:
    value = value or "unknown"
    if value in {"byte_clean", "captain_accepted"}:
        return "ok"
    if value in {"dark_sample_warning", "byte_clean_with_observations", "eyes_on_pending"}:
        return "warn"
    if value.startswith("blocked") or value.endswith("failed") or value in {"malformed_evidence", "missing_files"}:
        return "bad"
    return "neutral"


def _json_preview(value: Any) -> str:
    return html.escape(json.dumps(value, indent=2, sort_keys=True))


def _path_link(label: str, path_text: str) -> str:
    path = Path(path_text)
    href = path.resolve().as_uri() if path.exists() else "#"
    return '<a href="%s">%s</a>' % (html.escape(href), html.escape(label))


def _render_path_links(capture: dict[str, Any]) -> str:
    paths = capture.get("paths") or {}
    order = ("raw_log", "frames_log", "frame_gate", "summary", "annotation")
    links = []
    for key in order:
        path = paths.get(key)
        if path:
            links.append('<li>%s: %s</li>' % (html.escape(key), _path_link(Path(path).name, path)))
    return "<ul>%s</ul>" % "\n".join(links) if links else "<p>No artefact paths.</p>"


def _render_failures(capture: dict[str, Any]) -> str:
    failures = capture.get("failures") or []
    if not failures:
        return "<p>No recorded gate failures.</p>"
    return "<pre>%s</pre>" % _json_preview(failures)


def _render_readbacks(capture: dict[str, Any]) -> str:
    readbacks = capture.get("readbacks") or {}
    rows = []
    for key in (
        "channel_counts",
        "channel_energy_sum_total",
        "channel_nonzero_led_bytes_total",
        "channel_max_byte",
        "mode_counts",
    ):
        rows.append(
            "<tr><th>%s</th><td><code>%s</code></td></tr>"
            % (html.escape(key), html.escape(json.dumps(readbacks.get(key) or {}, sort_keys=True)))
        )
    return "<table class=\"kv\"><tbody>%s</tbody></table>" % "\n".join(rows)


def _render_motion_summary(capture: dict[str, Any]) -> str:
    motion = capture.get("motion_readability") or {}
    profiles = motion.get("profiles") or []
    deltas = motion.get("frame_deltas") or []
    peak_rows = []
    for profile in profiles[:8]:
        peak_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                html.escape(str(profile.get("seq"))),
                html.escape(str(profile.get("channel"))),
                html.escape(str(profile.get("record_frame"))),
                html.escape(str(profile.get("peak_radius"))),
                html.escape(str(profile.get("total_energy"))),
            )
        )
    delta_rows = []
    for delta in deltas[:8]:
        delta_rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                html.escape(str(delta.get("record_frame"))),
                html.escape(str(delta.get("primary_energy"))),
                html.escape(str(delta.get("secondary_energy"))),
                html.escape(str(delta.get("delta"))),
            )
        )
    return """
<div class="motion-grid">
  <div>
    <h4>Centre-Origin Peaks</h4>
    <p>Source: <code>%s</code>. Centre pair: <code>%s/%s</code>. Proof: <code>%s</code>.</p>
    <table><thead><tr><th>Seq</th><th>Channel</th><th>Frame</th><th>Peak Radius</th><th>Total Energy</th></tr></thead><tbody>%s</tbody></table>
  </div>
  <div>
    <h4>Primary / Secondary Delta</h4>
    <table><thead><tr><th>Frame</th><th>Primary</th><th>Secondary</th><th>Delta</th></tr></thead><tbody>%s</tbody></table>
  </div>
</div>
""" % (
        html.escape(str(motion.get("source"))),
        html.escape(str((motion.get("centre_origin") or {}).get("left"))),
        html.escape(str((motion.get("centre_origin") or {}).get("right"))),
        html.escape(str((motion.get("proof_labels") or {}).get("centre_origin_terrain"))),
        "\n".join(peak_rows) or '<tr><td colspan="5">No profiles.</td></tr>',
        "\n".join(delta_rows) or '<tr><td colspan="4">No deltas.</td></tr>',
    )


def _render_capture_card(capture: dict[str, Any]) -> str:
    page_state = capture.get("page_state") or "unknown"
    byte_status = capture.get("byte_status") or "unknown"
    visual_status = capture.get("visual_status") or "unknown"
    device = capture.get("device") or {}
    return """
<section class="capture">
  <div class="capture-head">
    <div>
      <h2>%s</h2>
      <p><strong>Programme:</strong> <code>%s</code> | <strong>Chip:</strong> <code>%s</code> | <strong>Port:</strong> <code>%s</code></p>
    </div>
    <div class="badges">
      <span class="badge %s">%s</span>
      <span class="badge %s">%s</span>
      <span class="badge %s">%s</span>
    </div>
  </div>
  <details open><summary>Readbacks</summary>%s</details>
  <details><summary>Motion Readability</summary>%s</details>
  <details><summary>Evidence Artefacts</summary>%s</details>
  <details><summary>Failures / Issues</summary>%s</details>
</section>
""" % (
        html.escape(str(capture.get("capture_id"))),
        html.escape(str(capture.get("programme"))),
        html.escape(str(device.get("observed_chip_id"))),
        html.escape(str(device.get("port"))),
        _badge_class(page_state),
        html.escape(_state_label(page_state)),
        _badge_class(byte_status),
        html.escape(_state_label(byte_status)),
        _badge_class(visual_status),
        html.escape(_state_label(visual_status)),
        _render_readbacks(capture),
        _render_motion_summary(capture),
        _render_path_links(capture),
        _render_failures(capture),
    )


def render_html(page: dict[str, Any]) -> str:
    rows = []
    for capture in page["captures"]:
        rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                html.escape(capture["capture_id"]),
                html.escape(_state_label(capture["page_state"])),
                html.escape(_state_label(capture["byte_status"])),
                html.escape(_state_label(capture["visual_status"])),
                html.escape(capture.get("programme") or "unknown"),
            )
        )
    captures = "\n".join(_render_capture_card(capture) for capture in page["captures"])
    lock = page.get("protocol_lock") or {}
    missing = "".join("<li>%s</li>" % html.escape(item) for item in lock.get("missing") or [])
    programmes = "".join(
        "<li><code>%s</code> - %s frames%s</li>"
        % (
            html.escape(item["programme"]),
            html.escape(str(item["frames"])),
            " - default" if item.get("default") else "",
        )
        for item in page.get("programme_registry") or []
    )
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VPML Evidence Gate</title>
  <style>
    :root { --ink: #16202a; --muted: #5d6b78; --line: #c8d1dc; --ok: #167348; --warn: #a05a00; --bad: #b42318; --panel: #f8fafc; }
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: var(--ink); background: #ffffff; }
    header { display: flex; justify-content: space-between; gap: 24px; align-items: start; margin-bottom: 20px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    h2 { margin: 0 0 6px; font-size: 18px; }
    h3 { margin: 20px 0 8px; }
    h4 { margin: 8px 0; }
    p { color: var(--muted); }
    table { border-collapse: collapse; width: 100%%; }
    th, td { border: 1px solid #c8d1dc; padding: 8px 10px; text-align: left; }
    th { background: #eef3f8; }
    .kv th { width: 260px; }
    .notice { margin: 16px 0; padding: 12px; border-left: 4px solid #b45309; background: #fff8eb; }
    .summary { display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px; margin: 20px 0; }
    .tile { border: 1px solid var(--line); background: var(--panel); padding: 14px; }
    .tile strong { display: block; font-size: 24px; }
    .capture { border: 1px solid var(--line); margin: 18px 0; padding: 16px; }
    .capture-head { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
    .badges { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
    .badge { border: 1px solid var(--line); padding: 4px 8px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
    .badge.ok { color: var(--ok); border-color: var(--ok); }
    .badge.warn { color: var(--warn); border-color: var(--warn); }
    .badge.bad { color: var(--bad); border-color: var(--bad); }
    details { border-top: 1px solid #e5eaf0; padding-top: 10px; margin-top: 10px; }
    summary { cursor: pointer; font-weight: 650; }
    pre { white-space: pre-wrap; overflow: auto; background: #0f1720; color: #e6edf3; padding: 12px; }
    code { background: #eef3f8; padding: 1px 4px; }
    a { color: #075985; }
    .motion-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    @media (max-width: 900px) { header, .capture-head { display: block; } .summary, .motion-grid { grid-template-columns: 1fr; } .badges { justify-content: flex-start; } }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>VPML Evidence Gate / Motion Readability</h1>
      <p>Local host-side evidence report. Fixed built-ins only.</p>
    </div>
    <div><strong>Schema:</strong> <code>%s</code></div>
  </header>
  <div class="notice">Byte proof only. Eyes-on pending unless Captain visual acceptance is explicitly recorded.</div>
  <section class="summary">
    <div class="tile"><span>Captures</span><strong>%s</strong></div>
    <div class="tile"><span>Playable built-ins</span><strong>%s</strong></div>
    <div class="tile"><span>Protocol state</span><strong>%s</strong></div>
  </section>
  <h3>Capture Index</h3>
  <table>
    <thead><tr><th>Capture</th><th>Page State</th><th>Byte Status</th><th>Visual Status</th><th>Programme</th></tr></thead>
    <tbody>%s</tbody>
  </table>
  <h3>Programme Registry</h3>
  <ul>%s</ul>
  <h3>Protocol Lock</h3>
  <p>Available control: <code>protocol.readiness.view</code>. Compile, upload, and raw receive controls are hidden.</p>
  <p>Missing readiness gates:</p>
  <ul>%s</ul>
  %s
</body>
</html>
""" % (
        html.escape(str(page.get("schema"))),
        html.escape(str(page.get("capture_count"))),
        html.escape(str(len(page.get("programme_registry") or []))),
        html.escape(_state_label(str(lock.get("state")))),
        "\n".join(rows),
        programmes,
        missing,
        captures,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--capture-id")
    parser.add_argument("--out")
    parser.add_argument("--html")
    args = parser.parse_args(argv)

    page = build_page(Path(args.evidence_dir), capture_id=args.capture_id)
    output = json.dumps(page, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if args.html:
        Path(args.html).write_text(render_html(page), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
