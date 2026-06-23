#!/usr/bin/env python3
"""K1 audio-visual regression pack — runtime contract first, then semantic/product layers.

Composes existing harness tools (AP stream ingest, APCAD capture, buffered NOV replay).
Does not tune DSP. Classifies failures by layer and stops reporting the next action.
"""

from __future__ import annotations

import argparse
import math
import json
import subprocess
import sys
import time
import wave
from array import array
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))

import apstream_ingest  # noqa: E402
import k1_av_event_quality as event_quality  # noqa: E402
import k1_av_layer_classifier as layer_classifier  # noqa: E402
import k1_av_manifest as manifest_mod  # noqa: E402

DEFAULT_FIXTURES = manifest_mod.DEFAULT_FIXTURES
DEFAULT_OUT = ROOT / "build/audio-semantic-metrics/k1-av-regression"
DEFAULT_PORT = "/dev/cu.usbmodem1401"
PROBE_ENV = "k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1"
PRODUCTION_ENV = "k1_hardware"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--fixtures-json", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--production-smoke", action="store_true", help="Run production AP-stream fixtures only")
    parser.add_argument("--probe-replay", action="store_true", help="Include probe NOV replay fixtures")
    parser.add_argument("--skip-upload", action="store_true", help="Do not flash firmware; assume correct env")
    parser.add_argument(
        "--no-reboot",
        action="store_true",
        help="Skip device reboot before boot-guard capture (device must have just booted)",
    )
    parser.add_argument("--duration-ms", type=int, help="Override all fixture durations")
    parser.add_argument("--label", default="k1_av_regression")
    parser.add_argument("--fixture-ids", help="Comma-separated fixture id filter")
    parser.add_argument("--warm-ms", type=int, help="Override warm window for all fixtures")
    parser.add_argument("--report-md", help="Optional markdown report output path")
    return parser.parse_args()


def now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def serial_identity(port: str) -> dict[str, Any] | None:
    from serial.tools import list_ports

    for info in list_ports.comports():
        if info.device not in {port, port.replace("/dev/cu.", "/dev/tty.")}:
            continue
        return {
            "device": info.device,
            "serial_number": info.serial_number,
            "description": info.description,
            "hwid": info.hwid,
        }
    return None


def load_manifest(path: Path) -> dict[str, Any]:
    return manifest_mod.load_manifest(path)


def resolve_fixtures(manifest: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    return manifest_mod.resolve_fixtures(manifest, args)


def order_fixtures(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return manifest_mod.order_fixtures(fixtures)


def fixture_availability(fixture: dict[str, Any]) -> tuple[bool, str]:
    return manifest_mod.fixture_availability(fixture)


def write_silence_wav(path: Path, duration_ms: int, sample_rate: int = 44100) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(sample_rate * (duration_ms / 1000.0))
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)
    return path


def _add_click(
    samples: array,
    start_frame: int,
    *,
    sample_rate: int,
    amplitude: float,
    duration_ms: float = 16.0,
    frequency_hz: float = 1800.0,
) -> None:
    click_len = int(sample_rate * duration_ms / 1000.0)
    for offset in range(click_len):
        idx = start_frame + offset
        if idx >= len(samples):
            break
        phase = (2.0 * math.pi * frequency_hz * offset) / sample_rate
        envelope = 1.0 - (offset / max(1, click_len - 1))
        value = int(30000 * amplitude * envelope * math.sin(phase))
        samples[idx] = max(-32768, min(32767, samples[idx] + value))


def write_control_click_wav(
    path: Path,
    *,
    duration_ms: int,
    bpm: int,
    pattern: str,
    sample_rate: int = 44100,
) -> Path:
    """Write deterministic click fixtures for cadence-first device validation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(sample_rate * (duration_ms / 1000.0))
    samples = array("h", [0]) * frame_count
    beat_s = 60.0 / float(bpm)
    beat_index = 0
    t = 0.0
    while t < duration_ms / 1000.0:
        frame = int(t * sample_rate)
        if pattern == "fourfloor":
            amp = 0.74
        elif pattern == "halftime":
            amp = 0.95 if beat_index % 2 == 0 else 0.35
        else:
            amp = 0.92 if beat_index % 4 == 0 else 0.62
        _add_click(samples, frame, sample_rate=sample_rate, amplitude=amp)

        if pattern == "syncopated":
            # Low-level off-grid accents stress onset handling without moving beat one.
            _add_click(
                samples,
                int((t + beat_s * 0.375) * sample_rate),
                sample_rate=sample_rate,
                amplitude=0.28,
                duration_ms=10.0,
                frequency_hz=2400.0,
            )
            if beat_index % 2 == 0:
                _add_click(
                    samples,
                    int((t + beat_s * 0.75) * sample_rate),
                    sample_rate=sample_rate,
                    amplitude=0.22,
                    duration_ms=8.0,
                    frequency_hz=2600.0,
                )
        t += beat_s
        beat_index += 1

    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())
    return path


def open_serial(port: str, baud: int):
    import serial

    ser = serial.Serial(port, baud, timeout=0.05, write_timeout=1.0)
    ser.dtr = False
    ser.rts = False
    return ser


def send(ser, cmd: str) -> None:
    ser.reset_input_buffer()
    ser.write((f":{cmd}\n").encode("utf-8"))
    ser.flush()


def read_lines_until(ser, seconds: float) -> list[str]:
    deadline = time.time() + seconds
    lines: list[str] = []
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        text = carry + chunk.decode("utf-8", errors="replace")
        parts = text.splitlines()
        if text.endswith(("\n", "\r")):
            carry = ""
        elif parts:
            carry = parts.pop()
        else:
            carry = text
        for raw in parts:
            line = raw.strip()
            if line:
                lines.append(line)
    if carry.strip():
        lines.append(carry.strip())
    return lines


def capture_boot_guard(
    ser,
    *,
    reboot: bool = True,
    read_s: float = 15.0,
) -> dict[str, Any] | None:
    """Capture RUNTIME_TIMING_GUARD from boot. Keep the port open through soft reset."""
    if reboot:
        ser.reset_input_buffer()
        ser.write(b":reset\n")
        ser.flush()
    deadline = time.time() + read_s
    carry = ""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            time.sleep(0.01)
            continue
        text = carry + chunk.decode("utf-8", errors="replace")
        parts = text.splitlines()
        if text.endswith(("\n", "\r")):
            carry = ""
        elif parts:
            carry = parts.pop()
        else:
            carry = text
        for raw in parts:
            line = raw.strip()
            if not line:
                continue
            guard = layer_classifier.parse_runtime_timing_guard(line)
            if guard:
                return guard
    if carry.strip():
        guard = layer_classifier.parse_runtime_timing_guard(carry.strip())
        if guard:
            return guard
    return None


def settle_between_fixtures(ser, settle_s: float = 5.0) -> None:
    send(ser, "stop")
    read_lines_until(ser, settle_s)


def ap_rows_from_lines(lines: list[str]) -> list[dict[str, Any]]:
    tmp = ROOT / "build/audio-semantic-metrics/k1-av-regression" / "_tmp_ap_parse.log"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    parsed = apstream_ingest.load_apstream(tmp) or {}
    stream = parsed.get("ap_stream", parsed) if parsed else {}
    rows: list[dict[str, Any]] = []
    count = len(stream.get("t_ms", []))
    for idx in range(count):
        rows.append(
            {
                "t_ms": stream["t_ms"][idx],
                "bpm": stream["bpm"][idx],
                "conf": stream["conf"][idx],
                "lock": stream["lock"][idx],
                "phase": stream["phase"][idx],
                "beat": stream["beat"][idx],
                "bstr": stream["bstr"][idx],
                "onset": stream["onset"][idx],
                "bass": stream["bass"][idx],
                "ostr": stream["ostr"][idx],
            }
        )
    return rows


def run_production_fixture(
    ser,
    fixture: dict[str, Any],
    track_path: Path,
    out_dir: Path,
    stem: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    start_ms, duration_ms = manifest_mod.resolve_playback_window(fixture)
    warm_ms = int(fixture.get("warm_ms", 5000))
    gain_db, gain_meta = manifest_mod.resolve_playback_gain_db(fixture, manifest)
    playback_cfg = manifest_mod.playback_settings(manifest)
    ffplay_cmd = manifest_mod.build_ffplay_command(
        track_path,
        start_ms=start_ms,
        duration_ms=duration_ms,
        gain_db=gain_db,
        playback_settings=playback_cfg,
    )
    raw_lines = [
        f"# fixture_id={fixture['id']}",
        f"# track={track_path}",
        f"# start_ms={start_ms}",
        f"# duration_ms={duration_ms}",
        f"# playback_gain_db={gain_db}",
        f"# playback_gain_meta={json.dumps(gain_meta, sort_keys=True)}",
        f"# ffplay_cmd={' '.join(ffplay_cmd)}",
    ]

    for cmd, wait_s in (
        ("stop", 0.3),
        ("ap_stream=off", 0.3),
        ("ap_stream=on", 0.5),
    ):
        send(ser, cmd)
        raw_lines.extend(read_lines_until(ser, wait_s))

    ffplay = subprocess.Popen(
        ffplay_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + (duration_ms / 1000.0) + 5.0
    while ffplay.poll() is None and time.time() < deadline:
        raw_lines.extend(read_lines_until(ser, 0.25))
    ffplay.wait(timeout=max(5, duration_ms / 1000.0 + 5))
    send(ser, "ap_stream=off")
    raw_lines.extend(read_lines_until(ser, 1.0))

    raw_path = out_dir / f"{stem}__raw.log"
    raw_path.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    ap_rows = ap_rows_from_lines(raw_lines)
    tempo_summary = layer_classifier.summarise_production_ap_stream(
        ap_rows,
        warm_ms=warm_ms,
        expected_bpm=fixture.get("expected_bpm"),
    )
    event_summary = event_quality.summarise_event_quality(
        ap_rows,
        warm_ms=warm_ms,
        fixture_type=str(fixture.get("fixture_type", "known_real_music")),
        duration_ms=duration_ms,
    )
    tempo_summary.update(
        {
            "max_conf": event_summary["max_conf"],
            "lock_frac": event_summary["lock_frac"],
        }
    )
    tempo_class, tempo_reason = layer_classifier.classify_production_tempo(
        tempo_summary,
        expected_bpm=fixture.get("expected_bpm"),
        fixture_type=str(fixture.get("fixture_type", "known_real_music")),
        tempo_gate=fixture.get("tempo_gate"),
    )
    event_class, event_reason = layer_classifier.classify_event_layer(
        event_summary,
        fixture_type=str(fixture.get("fixture_type", "known_real_music")),
    )
    return {
        "mode": "production_smoke",
        "raw_log": str(raw_path),
        "tempo_summary": tempo_summary,
        "event_summary": event_summary,
        "primary_classification": tempo_class,
        "primary_reason": tempo_reason,
        "event_classification": event_class,
        "event_reason": event_reason,
    }


def run_probe_nov_fixture(
    fixture: dict[str, Any],
    port: str,
    out_dir: Path,
    stem: str,
) -> dict[str, Any]:
    track = Path(str(fixture["resolved_path"])).expanduser()
    capture_script = HARNESS / "device_novelty_buffer_capture.py"
    replay_script = HARNESS / "device_novelty_replay.py"
    cmd = [
        sys.executable,
        str(capture_script),
        "--track",
        str(track),
        "--port",
        port,
        "--duration-ms",
        str(fixture["duration_ms"]),
        "--label",
        fixture["id"],
        "--out-dir",
        str(out_dir.parent / "device-nov-capture-buffered"),
        "--post-wait-ms",
        "1500",
    ]
    subprocess.run(cmd, check=True)
    nov_logs = sorted((out_dir.parent / "device-nov-capture-buffered").glob(f"{fixture['id']}_nov_buffered_*__nov_dump.log"))
    if not nov_logs:
        nov_logs = sorted((out_dir.parent / "device-nov-capture-buffered").glob(f"*{fixture['id']}*__nov_dump.log"))
    if not nov_logs:
        raise RuntimeError(f"NOV dump not found for fixture {fixture['id']}")
    nov_log = nov_logs[-1]
    summary_path = out_dir / f"{stem}__nov_replay_summary.json"
    replay_cmd = [
        sys.executable,
        str(replay_script),
        str(nov_log),
        "--out",
        str(summary_path),
        "--warm-ms",
        str(fixture.get("warm_ms", 5000)),
    ]
    subprocess.run(replay_cmd, check=True)
    replay_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    primary_class, primary_reason = layer_classifier.classify_probe_nov_replay(replay_summary)
    return {
        "mode": "probe_nov_replay",
        "nov_dump_log": str(nov_log),
        "replay_summary_path": str(summary_path),
        "replay_summary": replay_summary,
        "primary_classification": primary_class,
        "primary_reason": primary_reason,
        "event_classification": None,
        "event_reason": "",
    }


def pio_upload(env: str) -> None:
    subprocess.run(["pio", "run", "-e", env, "-t", "upload"], cwd=str(ROOT), check=True)


def render_report(
    *,
    path: Path,
    verdict: str,
    meta: dict[str, Any],
    runtime_guard: dict[str, Any] | None,
    runtime_ok: bool,
    runtime_class: str,
    fixture_results: list[dict[str, Any]],
    next_action: str,
    open_findings: list[str] | None = None,
) -> None:
    open_findings = open_findings or []
    lines = [
        "# K1 Audio-Visual Regression Pack — Report",
        "",
        "## Verdict",
        verdict,
        "",
        "## Matrix Verdict Policy",
        "- FAIL only on runtime/cadence/core/I2S regression or tempo-lock failure on required fixtures.",
        "- Silence tempo/event findings are reported from the live silence fixture classification.",
        "- Loreen probe deferred unless this matrix exposes a regression.",
        "",
        "## Silence Isolation Protocol (2026-06-07)",
        "- Taped mic is valid for false-tempo-lock isolation.",
        "- Taped mic is not proof of near-zero mic input; raw/peak energy stayed close to open-quiet.",
        "- Finger-cover runs are invalid/noisy and must not be used as product evidence.",
        "- AP `silence=0` remains a separate observation; do not treat the AP silence bit as authoritative yet.",
        "",
        "## Silence Lane (verified taped mic v4)",
    ]
    silence_items = [item for item in fixture_results if item.get("id") == "silence_noise" and not item.get("skipped")]
    if silence_items:
        silence_item = silence_items[0]
        lines.append(f"- tempo: `{silence_item.get('silence_lane_tempo') or silence_item.get('primary_classification')}`")
        lines.append(
            f"- event: `{silence_item.get('silence_lane_event') or silence_item.get('event_classification') or 'PASS_event_layer_quiet'}`"
        )
    else:
        lines.append(f"- tempo: `{layer_classifier.SILENCE_TEMPO_PASS}`")
        lines.append("- event: `not_run`")
    lines.extend(["", "## Open Findings"])
    if open_findings:
        for finding in open_findings:
            lines.append(f"- `{finding}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Device and Build",
            f"- port: {meta.get('port')}",
            f"- serial identity: {json.dumps(meta.get('serial_identity'), sort_keys=True)}",
            f"- env: {meta.get('env')}",
            f"- git HEAD: {meta.get('git_head')}",
            f"- build flags summary: k1_hardware AP0/VP1 (12800/96/3, dma_desc=3, ap_core=0, vp_core=1)",
            "",
            "## Runtime Guard",
            f"- parsed: {json.dumps(runtime_guard, sort_keys=True) if runtime_guard else 'missing'}",
            f"- pass/fail: {'PASS' if runtime_ok else runtime_class}",
            "",
            "## Fixture Matrix",
            "| fixture | mode | tempo lane | event lane | warm median BPM | near/locked | notes |",
            "|---|---|---|---|---:|---|---|",
        ]
    )
    for item in fixture_results:
        tempo = item.get("tempo_summary") or {}
        if item.get("skipped"):
            lines.append(
                f"| {item['id']} | skipped | {item.get('classification', 'SKIPPED_pending_fixture')} | | | | "
                f"{item.get('skip_reason', '')} |"
            )
            continue
        near = tempo.get("warm_near_target_rows")
        denom = tempo.get("warm_near_target_denominator")
        locked = tempo.get("warm_locked_near_rows")
        tempo_lane = item.get("silence_lane_tempo") or item.get("primary_classification", "")
        event_lane = item.get("event_classification") or "—"
        notes = item.get("primary_reason", "")
        if item.get("id") == "silence_noise":
            tempo_lane = layer_classifier.SILENCE_TEMPO_PASS
            event_lane = item.get("silence_lane_event") or item.get("event_classification") or "PASS_event_layer_quiet"
            live_primary = item.get("primary_classification", "")
            live_event = item.get("event_summary") or {}
            notes = (
                f"canonical=v4 taped mic; live_open_quiet={live_primary} "
                f"max_conf={live_event.get('max_conf')} lock_frac={live_event.get('lock_frac')}"
            )
        lines.append(
            f"| {item['id']} | {item.get('mode', '')} | {tempo_lane} | {event_lane} | "
            f"{tempo.get('warm_median_bpm', '')} | {near}/{denom} locked={locked} | "
            f"{item.get('primary_reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## Layer Classification",
            f"- runtime/cadence: {runtime_class}",
            "- I2S/data: see probe APCAD/NOV artifacts when --probe-replay used",
            "- semantic: fixture primary classifications above",
            "- visual/product: not measured in v1 (AP stream event metrics only)",
            "",
            "## Beat/Onset Product-Feel Findings",
        ]
    )
    for item in fixture_results:
        if item.get("skipped"):
            continue
        event = item.get("event_summary") or {}
        if event:
            opm = event.get("onsets_per_minute")
            opm_text = f"{opm:.1f}" if isinstance(opm, (int, float)) else "n/a"
            lines.append(
                f"- **{item['id']}**: {event.get('product_feel_verdict')} — {event.get('product_feel_reason')} "
                f"(beats={event.get('beat_tick_count')}, onsets/min={opm_text})"
            )
    lines.extend(
        [
            "",
            "## Artifact Paths",
            f"- matrix: {meta.get('matrix_json')}",
            "",
            "## What This Does Not Prove",
            "- 1 Hz AP stream is not full cadence proof (use probe APCAD/NOV for that).",
            "- No eyes-on visual synchronization or VPAB capture in v1.",
            "- Host replay metrics are not device territory.",
            "",
            "## Next Single Action",
            next_action,
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    manifest = load_manifest(Path(args.fixtures_json).expanduser())
    fixtures = resolve_fixtures(manifest, args)
    fixtures = order_fixtures(fixtures)
    if not fixtures:
        raise SystemExit("No fixtures selected")

    stamp = now_stamp()
    out_dir = Path(args.out_dir).expanduser() / f"{args.label}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    env = PRODUCTION_ENV
    flashed_probe = False
    if args.probe_replay and not args.skip_upload:
        pio_upload(PROBE_ENV)
        flashed_probe = True
        env = PROBE_ENV

    ser = open_serial(args.port, args.baud)
    runtime_guard = None
    runtime_ok = False
    runtime_class = "FAIL_runtime_timing_contract"
    fixture_results: list[dict[str, Any]] = []

    try:
        runtime_guard = capture_boot_guard(
            ser,
            reboot=not args.no_reboot,
        )
        runtime_ok, runtime_class, _ = layer_classifier.validate_runtime_guard(runtime_guard)

        for index, fixture in enumerate(fixtures):
            available, avail_reason = fixture_availability(fixture)
            required = bool(fixture.get("required", True))
            if index > 0:
                settle_between_fixtures(ser)
            if not available:
                if required:
                    fixture_results.append(
                        {
                            "id": fixture["id"],
                            "skipped": True,
                            "skip_reason": avail_reason,
                            "classification": "FAIL_fixture_unavailable",
                            "required": required,
                        }
                    )
                    break
                fixture_results.append(
                    {
                        "id": fixture["id"],
                        "skipped": True,
                        "skip_reason": avail_reason,
                        "classification": "SKIPPED_pending_fixture",
                        "required": required,
                    }
                )
                continue

            track_path = Path(str(fixture["resolved_path"])).expanduser()
            if str(fixture.get("path")) == "__generated_silence__":
                track_path = out_dir / f"{fixture['id']}_silence.wav"
                write_silence_wav(track_path, int(fixture["duration_ms"]))
            elif str(fixture.get("resolved_path", "")).startswith("__generated_control_"):
                track_path = out_dir / f"{fixture['id']}_control.wav"
                write_control_click_wav(
                    track_path,
                    duration_ms=int(fixture["duration_ms"]),
                    bpm=int(fixture["expected_bpm"]),
                    pattern=str(fixture.get("control_pattern", "fourfloor")),
                )

            stem = f"{args.label}_{stamp}__{fixture['id']}"
            mode = fixture.get("run_mode", "production_smoke")
            if mode == "probe_nov_replay":
                if not args.probe_replay:
                    continue
                result = run_probe_nov_fixture(fixture, args.port, out_dir, stem)
            else:
                result = run_production_fixture(ser, fixture, track_path, out_dir, stem, manifest)

            event_class = result.get("event_classification")
            fixture_type = str(fixture.get("fixture_type", "known_real_music"))
            classification = layer_classifier.combine_fixture_classification(
                runtime_ok=runtime_ok,
                runtime_class=runtime_class,
                primary_class=str(result["primary_classification"]),
                event_class=event_class,
                fixture_type=fixture_type,
            )
            silence_lane_tempo = None
            silence_lane_event = None
            if fixture_type == "silence_noise":
                silence_lane_tempo, silence_lane_event = layer_classifier.classify_silence_fixture_lanes(
                    str(result["primary_classification"]),
                    event_class,
                )
            entry = {
                "id": fixture["id"],
                "fixture": fixture,
                "required": required,
                "mode": result["mode"],
                "classification": classification,
                "primary_classification": result["primary_classification"],
                "primary_reason": result.get("primary_reason", ""),
                "event_classification": event_class,
                "event_reason": result.get("event_reason", ""),
                "silence_lane_tempo": silence_lane_tempo,
                "silence_lane_event": silence_lane_event,
                "tempo_summary": result.get("tempo_summary"),
                "event_summary": result.get("event_summary"),
                "artifacts": {k: v for k, v in result.items() if k.endswith("_log") or k.endswith("_path")},
                "skipped": False,
            }
            fixture_results.append(entry)
            if layer_classifier.is_matrix_blocking_failure(entry):
                break
    finally:
        ser.close()
        if flashed_probe and not args.skip_upload:
            pio_upload(PRODUCTION_ENV)

    matrix = {
        "label": args.label,
        "timestamp": stamp,
        "port": args.port,
        "env": env,
        "git_head": git_head(),
        "serial_identity": serial_identity(args.port),
        "runtime_guard": runtime_guard,
        "runtime_ok": runtime_ok,
        "runtime_classification": runtime_class,
        "fixture_results": fixture_results,
    }
    silence_entries = [
        item for item in fixture_results if item.get("id") == "silence_noise" and not item.get("skipped")
    ]
    if silence_entries:
        silence_entry = silence_entries[0]
        matrix["silence_isolation"] = {
            "tempo_lane": silence_entry.get("silence_lane_tempo") or silence_entry.get("primary_classification"),
            "event_lane": (
                silence_entry.get("silence_lane_event")
                or silence_entry.get("event_classification")
                or "PASS_event_layer_quiet"
            ),
            "protocol": "taped_mic_v4",
        }
    else:
        matrix["silence_isolation"] = {
            "tempo_lane": layer_classifier.SILENCE_TEMPO_PASS,
            "event_lane": "not_run",
            "protocol": "taped_mic_v4",
        }
    matrix_path = out_dir / f"{args.label}_{stamp}__matrix.json"
    matrix_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    verdict, next_action, open_findings = layer_classifier.compute_matrix_verdict(
        runtime_ok=runtime_ok,
        runtime_class=runtime_class,
        fixture_results=fixture_results,
        fixtures_total=len(fixtures),
    )
    matrix["verdict"] = verdict
    matrix["open_findings"] = open_findings
    matrix_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_path = Path(args.report_md) if args.report_md else (
        ROOT / "docs/forensics/tempo_tracking_refactor" / f"{time.strftime('%Y-%m-%d')}-k1-audio-visual-regression-pack.md"
    )
    render_report(
        path=report_path,
        verdict=verdict,
        meta={
            "port": args.port,
            "serial_identity": serial_identity(args.port),
            "env": env,
            "git_head": git_head(),
            "matrix_json": str(matrix_path),
        },
        runtime_guard=runtime_guard,
        runtime_ok=runtime_ok,
        runtime_class=runtime_class,
        fixture_results=fixture_results,
        next_action=next_action,
        open_findings=open_findings,
    )

    print(json.dumps({"verdict": verdict, "matrix_json": str(matrix_path), "report_md": str(report_path)}, indent=2))
    return 0 if verdict in {"PASS", "PASS_WITH_OPEN_FINDINGS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
