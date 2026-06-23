#!/usr/bin/env python3
"""Local browser console for the non-shippable VP Motion Lab host runner."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import sys
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "forensics" / "runtime-evidence"
DEFAULT_DASHBOARD_DIR = ROOT / "docs" / "forensics" / "vp_motion_lab"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_SERIAL_PORT = "/dev/cu.usbmodem1401"
DEFAULT_BAUD = 115200
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _load_script(name: str):
    script = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpml_evidence_page = _load_script("vpml_evidence_page.py")
vpml_run_console = _load_script("vpml_run_console.py")


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _state_label(value: str | None) -> str:
    return (value or "unknown").replace("_", " ")


def _badge_class(value: str | None) -> str:
    value = value or "unknown"
    if value in {"byte_clean", "captain_accepted", "PASS"}:
        return "ok"
    if value in {"eyes_on_pending", "dark_sample_warning", "byte_clean_with_observations"}:
        return "warn"
    if value.startswith("blocked") or value.endswith("failed") or value in {"FAIL", "missing_files", "malformed_evidence"}:
        return "bad"
    return "neutral"


def latest_capture(page: dict[str, Any], *, state: str | None = None) -> dict[str, Any] | None:
    captures = page.get("captures") or []
    if state is not None:
        captures = [capture for capture in captures if capture.get("page_state") == state]
    if not captures:
        return None
    return sorted(captures, key=lambda capture: capture.get("capture_id") or "")[-1]


def parse_run_form(form: dict[str, str]) -> dict[str, Any]:
    programme = form.get("programme", "intro_bounce_loop")
    if programme not in vpml_run_console.PROGRAMMES:
        raise ValueError("unsupported VPML programme: %s" % programme)

    port = form.get("port", DEFAULT_SERIAL_PORT).strip()
    if not port.startswith("/dev/"):
        raise ValueError("port must be a local /dev serial path")

    baud = int(form.get("baud", str(DEFAULT_BAUD)))
    seconds = float(form.get("seconds", "2.4"))
    every = int(form.get("every", str(vpml_run_console.PROGRAMMES[programme]["default_every"])))
    command_read_seconds = float(form.get("command_read_seconds", "2.0"))
    frame_read_seconds = float(form.get("frame_read_seconds", "8.0"))
    command_max_lines = int(form.get("command_max_lines", "400"))
    frame_max_lines = int(form.get("frame_max_lines", "20000"))

    if baud <= 0:
        raise ValueError("baud must be positive")
    if not (0.0 <= seconds <= 15.0):
        raise ValueError("seconds must be between 0 and 15")
    if every <= 0:
        raise ValueError("every must be positive")
    if command_read_seconds <= 0 or frame_read_seconds <= 0:
        raise ValueError("read windows must be positive")
    if command_max_lines <= 0 or frame_max_lines <= 0:
        raise ValueError("line caps must be positive")

    return {
        "port": port,
        "baud": baud,
        "expect_chip": form.get("expect_chip", vpml_run_console.DEFAULT_CHIP_ID).strip().upper(),
        "programme": programme,
        "seconds": seconds,
        "every": every,
        "command_read_seconds": command_read_seconds,
        "command_max_lines": command_max_lines,
        "frame_read_seconds": frame_read_seconds,
        "frame_max_lines": frame_max_lines,
    }


def validate_bind_host(host: str, *, allow_non_loopback: bool = False) -> None:
    if allow_non_loopback:
        return
    if host not in LOOPBACK_HOSTS:
        raise ValueError("VPML Run Console binds only to loopback unless --allow-non-loopback is set")


def run_capture_from_form(
    form: dict[str, str],
    *,
    evidence_dir: Path,
    dashboard_dir: Path,
) -> dict[str, Any]:
    request = parse_run_form(form)
    prefix = vpml_run_console.capture_prefix(request["programme"], request["port"])
    lines: list[str] = []
    paths: dict[str, Path] = {}
    error: Exception | None = None

    try:
        vpml_run_console.run_vpml_session(lines=lines, **request)
    except Exception as exc:
        error = exc
    finally:
        if lines:
            paths = vpml_run_console.write_capture_outputs(
                lines=lines,
                prefix=prefix,
                evidence_dir=evidence_dir,
                expect_chip=request["expect_chip"],
                programme=request["programme"],
            )
            if error is not None:
                paths["session_error"] = vpml_run_console.write_session_error(
                    error=error,
                    prefix=prefix,
                    evidence_dir=evidence_dir,
                    port=request["port"],
                    baud=request["baud"],
                    expect_chip=request["expect_chip"],
                    programme=request["programme"],
                )
            paths.update(vpml_run_console.refresh_dashboard(evidence_dir, dashboard_dir))

    if error is not None:
        if not lines:
            raise error
        return {
            "ok": False,
            "message": str(error),
            "error_type": error.__class__.__name__,
            "paths": {key: str(value) for key, value in paths.items()},
        }

    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    return {
        "ok": bool(summary.get("passed")),
        "message": summary.get("result", "UNKNOWN"),
        "paths": {key: str(value) for key, value in paths.items()},
        "summary": {
            "records": ((summary.get("strict_gate") or {}).get("counts") or {}).get("records"),
            "chunks": ((summary.get("strict_gate") or {}).get("counts") or {}).get("chunks"),
            "chip": (summary.get("runtime") or {}).get("observed_chip_id"),
            "vpab_records": (summary.get("runtime") or {}).get("vpab_records"),
            "vp_perf_frame": (summary.get("runtime") or {}).get("vp_perf_frame"),
        },
    }


def _artifact_link(path_text: str | None) -> str:
    if not path_text:
        return ""
    name = Path(path_text).name
    return '<a href="/evidence/%s">%s</a>' % (
        urllib.parse.quote(name),
        _esc(name),
    )


def _render_capture_rows(page: dict[str, Any]) -> str:
    rows = []
    for capture in reversed(page.get("captures") or []):
        paths = capture.get("paths") or {}
        rows.append(
            """
            <tr>
              <td><code>%s</code></td>
              <td><span class="badge %s">%s</span></td>
              <td><span class="badge %s">%s</span></td>
              <td>%s</td>
              <td>%s</td>
              <td>%s</td>
            </tr>
            """
            % (
                _esc(capture.get("capture_id")),
                _badge_class(capture.get("page_state")),
                _esc(_state_label(capture.get("page_state"))),
                _badge_class(capture.get("visual_status")),
                _esc(_state_label(capture.get("visual_status"))),
                _esc(capture.get("programme")),
                _artifact_link(paths.get("summary")),
                _artifact_link(paths.get("raw_log")),
            )
        )
    return "\n".join(rows) or '<tr><td colspan="6">No captures yet.</td></tr>'


def _render_programme_options(selected: str) -> str:
    options = []
    for programme in sorted(vpml_run_console.PROGRAMMES):
        options.append(
            '<option value="%s"%s>%s</option>'
            % (
                _esc(programme),
                " selected" if programme == selected else "",
                _esc(programme),
            )
        )
    return "\n".join(options)


def _render_result(result: dict[str, Any] | None) -> str:
    if not result:
        return ""
    paths = result.get("paths") or {}
    links = "".join(
        "<li>%s: %s</li>" % (_esc(key), _artifact_link(path))
        for key, path in paths.items()
        if key in {"raw", "frames", "frame_gate", "summary", "session_error"}
    )
    summary = result.get("summary") or {}
    return """
    <section class="result">
      <div>
        <h2>Last Run</h2>
        <span class="badge %s">%s</span>
      </div>
      <p>%s</p>
      <dl>
        <dt>Records</dt><dd>%s</dd>
        <dt>Chunks</dt><dd>%s</dd>
        <dt>Chip</dt><dd><code>%s</code></dd>
      </dl>
      <ul>%s</ul>
    </section>
    """ % (
        "ok" if result.get("ok") else "bad",
        "PASS" if result.get("ok") else "FAIL",
        _esc(result.get("message")),
        _esc(summary.get("records")),
        _esc(summary.get("chunks")),
        _esc(summary.get("chip")),
        links,
    )


def _latest_profile(capture: dict[str, Any], channel: str) -> dict[str, Any] | None:
    profiles = ((capture.get("motion_readability") or {}).get("profiles") or [])
    for profile in reversed(profiles):
        if profile.get("channel") == channel:
            return profile
    return None


def _bucketed(values: list[int], bucket_count: int = 40) -> list[int]:
    if not values:
        return []
    out = []
    width = max(1, len(values) // bucket_count)
    for start in range(0, len(values), width):
        chunk = values[start:start + width]
        out.append(max(chunk) if chunk else 0)
    return out[:bucket_count]


def _render_motion_lane(label: str, profile: dict[str, Any] | None) -> str:
    if not profile:
        return """
        <div class="motion-row">
          <div class="motion-label">%s</div>
          <div class="motion-empty">No byte profile</div>
        </div>
        """ % _esc(label)

    values = _bucketed([int(value) for value in profile.get("radius_energy") or []])
    peak = max(values) if values else 0
    cells = []
    for value in values:
        strength = 0 if peak <= 0 else value / peak
        alpha = 0.12 + (0.88 * strength)
        height = 18 + int(34 * strength)
        cells.append('<span class="motion-cell" style="height:%dpx; opacity:%.3f"></span>' % (height, alpha))
    return """
    <div class="motion-row">
      <div class="motion-label">%s</div>
      <div class="motion-strip">%s</div>
      <div class="motion-meta">frame %s | peak radius %s | energy %s</div>
    </div>
    """ % (
        _esc(label),
        "".join(cells),
        _esc(profile.get("record_frame")),
        _esc(profile.get("peak_radius")),
        _esc(profile.get("total_energy")),
    )


def _render_gate_checks(capture: dict[str, Any]) -> str:
    gate = capture.get("gate") or {}
    checks = [
        ("Transport", gate.get("strict_transport_clean")),
        ("Channels", gate.get("primary_and_secondary_present")),
        ("Mode 250", gate.get("vpml_mode_on_all_records")),
        ("Nonzero Bytes", gate.get("nonzero_final_bytes_on_required_channels")),
        ("No Dark Sample", gate.get("no_dark_sample_records")),
        ("No Drops", gate.get("vp_perf_no_over_or_dropped_frames")),
        ("Chip Match", gate.get("chip_identity_match")),
    ]
    return "".join(
        '<span class="check %s">%s</span>' % ("ok" if value is True else "bad", _esc(label))
        for label, value in checks
    )


def _render_motion_panel(capture: dict[str, Any]) -> str:
    if not capture:
        return ""
    motion = capture.get("motion_readability") or {}
    proof = (motion.get("proof_labels") or {}).get("centre_origin_terrain") or "unknown"
    return """
    <section>
      <div class="section-head">
        <h2>Latest Motion Readback</h2>
        <span class="badge %s">%s</span>
      </div>
      <div class="gate-checks">%s</div>
      <div class="motion-panel">
        %s
        %s
      </div>
    </section>
    """ % (
        "ok" if proof == "evidence" else "warn",
        _esc(proof),
        _render_gate_checks(capture),
        _render_motion_lane("Primary", _latest_profile(capture, "primary")),
        _render_motion_lane("Secondary", _latest_profile(capture, "secondary")),
    )


def render_page(
    *,
    evidence_dir: Path,
    result: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> str:
    defaults = defaults or {}
    page = vpml_evidence_page.build_page(evidence_dir)
    latest = latest_capture(page) or {}
    latest_clean = latest_capture(page, state="byte_clean") or latest
    device = latest_clean.get("device") or {}
    readbacks = latest_clean.get("readbacks") or {}
    selected = defaults.get("programme") or latest_clean.get("programme") or "intro_bounce_loop"
    port = defaults.get("port") or device.get("port") or DEFAULT_SERIAL_PORT
    baud = int(defaults.get("baud") or DEFAULT_BAUD)
    every = int(defaults.get("every") or vpml_run_console.PROGRAMMES[selected]["default_every"])

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VPML Run Console</title>
  <style>
    :root {
      --ink: #17212b;
      --muted: #5f6d7a;
      --line: #cfd8e3;
      --panel: #f7f9fb;
      --field: #ffffff;
      --ok: #0f7a4c;
      --warn: #9a5a00;
      --bad: #b42318;
      --action: #155e75;
      --action-ink: #ffffff;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: #ffffff; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; }
    header { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; margin-bottom: 18px; }
    h1 { font-size: 28px; margin: 0 0 6px; }
    h2 { font-size: 17px; margin: 0 0 10px; }
    p { margin: 0 0 10px; color: var(--muted); }
    .grid { display: grid; grid-template-columns: minmax(320px, 420px) minmax(0, 1fr); gap: 18px; align-items: start; }
    section { border-top: 1px solid var(--line); padding-top: 16px; margin-top: 16px; }
    .panel { background: var(--panel); border: 1px solid var(--line); padding: 16px; }
    form { display: grid; gap: 12px; }
    label { display: grid; gap: 5px; font-size: 13px; font-weight: 650; }
    input, select { width: 100%%; border: 1px solid var(--line); background: var(--field); padding: 9px 10px; font: inherit; min-height: 40px; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    button, .button { min-height: 40px; border: 1px solid var(--action); background: var(--action); color: var(--action-ink); padding: 9px 12px; font-weight: 700; cursor: pointer; text-decoration: none; text-align: center; }
    .button.secondary { background: #ffffff; color: var(--action); }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; }
    .badge { display: inline-block; border: 1px solid var(--line); padding: 3px 7px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0; white-space: nowrap; }
    .badge.ok { color: var(--ok); border-color: var(--ok); background: #f0fff7; }
    .badge.warn { color: var(--warn); border-color: var(--warn); background: #fff8eb; }
    .badge.bad { color: var(--bad); border-color: var(--bad); background: #fff1f0; }
    .section-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .gate-checks { display: flex; flex-wrap: wrap; gap: 7px; margin: 8px 0 14px; }
    .check { border: 1px solid var(--line); background: #ffffff; color: var(--muted); padding: 4px 7px; font-size: 12px; font-weight: 700; }
    .check.ok { border-color: var(--ok); color: var(--ok); background: #f0fff7; }
    .check.bad { border-color: var(--bad); color: var(--bad); background: #fff1f0; }
    .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .stat { border: 1px solid var(--line); background: #ffffff; padding: 12px; min-height: 76px; }
    .stat span { display: block; color: var(--muted); font-size: 12px; }
    .stat strong { display: block; margin-top: 4px; font-size: 20px; overflow-wrap: anywhere; }
    table { width: 100%%; border-collapse: collapse; table-layout: fixed; }
    th, td { border: 1px solid var(--line); padding: 8px 9px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
    th { background: #edf3f7; font-size: 12px; }
    code { background: #e9eff5; padding: 1px 4px; }
    dl { display: grid; grid-template-columns: 100px 1fr; gap: 6px 10px; margin: 8px 0; }
    dt { color: var(--muted); }
    dd { margin: 0; }
    .notice { border-left: 4px solid var(--warn); background: #fff8eb; padding: 10px 12px; margin: 12px 0; }
    .result { border: 1px solid var(--line); padding: 14px; background: #ffffff; }
    .motion-panel { display: grid; gap: 14px; border: 1px solid var(--line); background: #ffffff; padding: 14px; }
    .motion-row { display: grid; grid-template-columns: 86px minmax(0, 1fr) 190px; gap: 12px; align-items: center; }
    .motion-label { font-weight: 800; }
    .motion-strip { display: grid; grid-template-columns: repeat(40, 1fr); gap: 2px; min-height: 56px; align-items: end; border-bottom: 1px solid var(--line); }
    .motion-cell { display: block; min-width: 3px; background: linear-gradient(180deg, #14b8a6, #155e75); }
    .motion-row:nth-child(2) .motion-cell { background: linear-gradient(180deg, #f59e0b, #b42318); }
    .motion-meta, .motion-empty { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
    @media (max-width: 900px) {
      main { padding: 16px; }
      header, .grid { display: block; }
      .stats, .two, .motion-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>VPML Run Console</h1>
      <p>Host-side fixed built-in runner for the non-shippable VP Motion Lab surface.</p>
    </div>
    <div><span class="badge warn">Eyes-on pending</span></div>
  </header>
  <div class="notice">Byte proof is not visual acceptance. This page does not compile, upload, use raw receive, or use AP/REST/WebSocket control.</div>
  <div class="grid">
    <div class="panel">
      <h2>Run Capture</h2>
      <form method="post" action="/run">
        <label>Port
          <input name="port" value="%s" autocomplete="off">
        </label>
        <div class="two">
          <label>Baud
            <input name="baud" type="number" value="%s" min="1">
          </label>
          <label>Expected Chip
            <input name="expect_chip" value="%s" autocomplete="off">
          </label>
        </div>
        <label>Programme
          <select name="programme">%s</select>
        </label>
        <div class="two">
          <label>Capture Duration Seconds
            <input name="seconds" type="number" value="2.4" min="0" max="15" step="0.1">
          </label>
          <label>Capture Every N Frames
            <input name="every" type="number" value="%s" min="1">
          </label>
        </div>
        <div class="two">
          <label>Command Read Seconds
            <input name="command_read_seconds" type="number" value="2.0" min="0.1" step="0.1">
          </label>
          <label>Frame Read Seconds
            <input name="frame_read_seconds" type="number" value="8.0" min="0.1" step="0.1">
          </label>
        </div>
        <input name="command_max_lines" type="hidden" value="400">
        <input name="frame_max_lines" type="hidden" value="20000">
        <div class="actions">
          <button type="submit">Run Capture</button>
          <a class="button secondary" href="/">Refresh</a>
        </div>
      </form>
      %s
    </div>
    <div>
      <section>
        <h2>Latest Byte Evidence</h2>
        <div class="stats">
          <div class="stat"><span>Capture</span><strong>%s</strong></div>
          <div class="stat"><span>Byte Status</span><strong>%s</strong></div>
          <div class="stat"><span>Chip</span><strong>%s</strong></div>
          <div class="stat"><span>Records</span><strong>%s</strong></div>
          <div class="stat"><span>Mode Counts</span><strong>%s</strong></div>
          <div class="stat"><span>Visual Status</span><strong>%s</strong></div>
        </div>
      </section>
      %s
      <section>
        <h2>Capture Index</h2>
        <table>
          <thead><tr><th>Capture</th><th>Byte Gate</th><th>Visual</th><th>Programme</th><th>Summary</th><th>Raw</th></tr></thead>
          <tbody>%s</tbody>
        </table>
      </section>
    </div>
  </div>
</main>
</body>
</html>
""" % (
        _esc(port),
        _esc(baud),
        _esc(device.get("expected_chip_id") or vpml_run_console.DEFAULT_CHIP_ID),
        _render_programme_options(selected),
        _esc(every),
        _render_result(result),
        _esc(latest_clean.get("capture_id")),
        _esc(_state_label(latest_clean.get("byte_status"))),
        _esc(device.get("observed_chip_id")),
        _esc(((latest_clean.get("gate") or {}).get("counts") or {}).get("records")),
        _esc(json.dumps(readbacks.get("mode_counts") or {}, sort_keys=True)),
        _esc(_state_label(latest_clean.get("visual_status"))),
        _render_motion_panel(latest_clean),
        _render_capture_rows(page),
    )


class VPMLConsoleHandler(BaseHTTPRequestHandler):
    server_version = "VPMLRunConsole/1"

    def _send_html(self, text: str, status: int = 200) -> None:
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_page(evidence_dir=self.server.evidence_dir))
            return
        if parsed.path.startswith("/evidence/"):
            name = Path(urllib.parse.unquote(parsed.path.removeprefix("/evidence/"))).name
            self._send_file(self.server.evidence_dir / name)
            return
        if parsed.path == "/data.json":
            payload = json.dumps(vpml_evidence_page.build_page(self.server.evidence_dir), indent=2, sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if urllib.parse.urlparse(self.path).path != "/run":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(size).decode("utf-8", errors="replace")
        values = urllib.parse.parse_qs(body, keep_blank_values=True)
        form = {key: item[-1] for key, item in values.items()}
        try:
            result = run_capture_from_form(
                form,
                evidence_dir=self.server.evidence_dir,
                dashboard_dir=self.server.dashboard_dir,
            )
            status = 200
        except Exception as exc:  # pragma: no cover - exercised by live server.
            result = {
                "ok": False,
                "message": "%s: %s" % (exc.__class__.__name__, exc),
                "traceback": traceback.format_exc(limit=4),
            }
            status = 500
        self._send_html(render_page(evidence_dir=self.server.evidence_dir, result=result, defaults=form), status=status)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args), file=sys.stderr)


class VPMLConsoleServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, *, evidence_dir: Path, dashboard_dir: Path):
        super().__init__(server_address, handler_class)
        self.evidence_dir = Path(evidence_dir)
        self.dashboard_dir = Path(dashboard_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--dashboard-dir", default=str(DEFAULT_DASHBOARD_DIR))
    parser.add_argument("--allow-non-loopback", action="store_true")
    args = parser.parse_args(argv)

    try:
        validate_bind_host(args.host, allow_non_loopback=args.allow_non_loopback)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    server = VPMLConsoleServer(
        (args.host, args.port),
        VPMLConsoleHandler,
        evidence_dir=Path(args.evidence_dir),
        dashboard_dir=Path(args.dashboard_dir),
    )
    print("VPML Run Console: http://%s:%d/" % (args.host, args.port), file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
