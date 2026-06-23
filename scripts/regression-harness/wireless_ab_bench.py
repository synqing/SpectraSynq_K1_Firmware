#!/usr/bin/env python3
"""Wireless A/B bench — eyes-free AP/VP performance comparison, K1 WiFi AP ON vs OFF.

delegation_id=SSA-WIFI-AB-BENCH-01

PURPOSE
  Quantify whether the K1 wireless AP+WebSocket stack degrades audio-pipeline /
  visual-pipeline performance ("interference theory"). Two firmware conditions:
    off — k1_hardware_harness   (wireless stack absent)
    on  — k1_wireless_ab_probe     (wireless stack active; same serial surfaces)
  The operator flashes between conditions; THIS TOOL NEVER FLASHES, ERASES, OR
  RESETS the device. It only opens a serial port, sends colon-framed runtime
  stream toggles, plays a deterministic stimulus WAV via `afplay`, logs serial
  output with host timestamps, and computes metrics.

DOCTRINE / SCOPE OF CLAIM (load-bearing)
  This is a SCALAR A/B SYMPTOM measurement. Per the Developer Instrumentation
  Boundary, scalar diagnostics quantify symptoms; they DO NOT close causal
  attribution. If this bench finds degradation, the verdict is "measured delta
  under condition ON" — never "WiFi caused it". Causal attribution (frame-drop
  causality, cross-core ordering, audio-to-render timeline) escalates to the
  MabuTrace dev-trace lane (k1_hardware_trace_dev). This tool must not be cited
  as causal proof.

SERIAL SURFACES USED (and their honest resolution)
  [AP]   1 Hz line (runtime `:ap_stream=on`; audio/i2s_audio.h ~:534).
         Fields: SSL DC max_raw follower peak_scaled silent_scale silence
         cal_source cal_valid | bpm conf lock phase beat bstr | onset bass ostr.
         Resolution: 1 Hz INSTANTANEOUS SAMPLES of pipeline state. bpm/conf/lock
         are slowly-varying state -> faithful at 1 Hz. beat/onset/bass are
         per-frame flags sampled at 1 Hz -> "onset count" here is a SAMPLED
         PROXY (count of 1 Hz samples where the flag happened to be high), not
         a true 133 Hz event count. Valid for A/B comparison under identical
         stimulus; not valid as an absolute event rate.
         Inter-arrival jitter of these lines (host timestamps) is a coarse
         main-loop health proxy at ~1 s granularity: sustained stalls >~50 ms
         show up; sub-frame jitter does not.
  [APCAP] windowed full-frame-rate aggregate (`:ap_capture=<ms>`, compile gate
         ENABLE_AP_STREAM, present in both bench envs). One summary line per
         armed window: min/max of max_raw and peak_scaled, follower_mean,
         spec_argmax, chroma_mean, silence_any — accumulated at the FULL 133 Hz
         frame rate, reported once per window. Highest-rate AP amplitude
         evidence available; no per-frame stream exists in these envs.
  [VP]   1 Hz line (runtime `:vp_stream=on`): render_us (last frame),
         render_avg, render_max. 1 Hz samples; fallback render surface.
  VPF,   vp_perf audit (compile gate ENABLE_VP_PERF_AUDIT, runtime
         `:vp_perf=start`; report interval VP_PERF_REPORT_INTERVAL_MS = 1000).
         Per-stage avg/max in us accumulated over EVERY frame (~100 FPS) within
         each 1 s report window, including frame_us. This is the best render
         timing surface: full-frame-rate aggregation, 1 Hz reporting. "p95" of
         render timing below is the p95 of per-second frame_us AVERAGES plus
         the global frame_us MAX — not a per-frame percentile (no per-frame
         stream ships in these envs). VPF `seq=` gaps double as a serial-loss
         detector.

SUBCOMMANDS
  make-stimulus  write the deterministic 90 s test WAV (see STIMULUS below)
  run            capture ONE condition run (serial + afplay + metrics JSON)
  compare        N OFF-runs vs N ON-runs -> verdict table + JSON
  protocol       print the interleaved ABAB runbook (flashing stays manual)

STIMULUS (deterministic, numpy-generated)
  48000 Hz mono 16-bit WAV, 90 s, peak amplitude 0.7 FS (~-3.1 dBFS):
    - 120 BPM kick (60 Hz decaying burst) + click (2 kHz, 6 ms) every 0.5 s
    - bass-band bursts (80 Hz, 400 ms) every 2 s
    - mid-band melody tones (440/523/659/784 Hz, 250 ms) cycling per beat
    - TWO deliberate 1.5 s full-silence cuts at t=30.0 and t=55.0 (exercises
      the drop-cut path)
    - final 10 s full silence (t=80..90)
  Default path: scripts/regression-harness/fixtures/wireless_ab_stimulus.wav
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Any

try:
    import serial  # pyserial — only needed for `run`
except ImportError:  # pragma: no cover - host without pyserial; analysis still works.
    serial = None

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STIMULUS = Path(__file__).resolve().parent / "fixtures" / "wireless_ab_stimulus.wav"
DEFAULT_PORT = "/dev/cu.usbmodem1401"
DEFAULT_CHIP_ID = "F887A500"  # main K1
DEFAULT_BAUD = 115200

# ---------------------------------------------------------------------------
# Stimulus constants (documented, deterministic)
# ---------------------------------------------------------------------------
STIMULUS_SR = 48000
STIMULUS_DURATION_S = 90.0
STIMULUS_PEAK = 0.7          # fixed amplitude, ~-3.1 dBFS
STIMULUS_BPM = 120
SILENCE_CUTS = ((30.0, 31.5), (55.0, 56.5))   # two deliberate 1.5 s drop-cuts
FINAL_SILENCE_START_S = 80.0                   # final 10 s silence

# ---------------------------------------------------------------------------
# PRE-REGISTERED THRESHOLDS (compare verdict). Rationale per constant.
# Direction: a delta is FAIL only when ON is worse than OFF in the harmful
# direction (or, for level/count metrics, when |delta| exceeds the bound —
# identical stimulus means level/count should not move either way).
# ---------------------------------------------------------------------------
# Beat lock ratio (active samples): lock FSM threshold is 0.60 with hysteresis;
# run-to-run variance under identical stimulus is small. >5 percentage-point
# absolute drop exceeds expected bench noise.
THRESH_LOCK_RATIO_DROP = 0.05
# Mean tempo confidence (active samples): settled confidence ~0.62 post
# forward-graft; a 0.05 drop (~8% relative) is beyond replay variance.
THRESH_CONF_DROP = 0.05
# Onset sampled-count: the 1 Hz sampled proxy is intrinsically noisy, so the
# bound is loose (15% relative, symmetric) — catches systematic suppression,
# tolerates sampling noise.
THRESH_ONSET_COUNT_REL = 0.15
# peak_scaled mean: identical stimulus + fixed speaker volume -> the AP input
# level should not move. >10% relative shift (either way) indicates front-end /
# AGC disturbance.
THRESH_PEAK_SCALED_REL = 0.10
# [AP] 1 Hz cadence p95 jitter: the emitter is gated on millis() in the main
# loop; >100 ms added p95 jitter implies main-loop stalls of order >=100 ms.
THRESH_AP_JITTER_P95_MS = 100.0
# Crash/reboot markers: any reset during a run invalidates the run and fails
# the comparison outright (in either condition — a crashing bench is no bench).
THRESH_CRASH_MARKERS = 0
# Render p95 (frame_us): 100 FPS budget is 10 ms/frame; +10% relative erosion
# of the p95 frame time is a material headroom loss. Only checked when a render
# surface (VPF preferred, [VP] fallback) parsed in BOTH conditions.
THRESH_RENDER_P95_REL = 0.10

# ---------------------------------------------------------------------------
# Serial line parsing
# ---------------------------------------------------------------------------
HOST_TS_RE = re.compile(r"^\[(\d+\.\d+)\]\s+(.*)$")
SPACE_KV_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s|,]+)")
CHIP_ID_RE = re.compile(r"\b[0-9A-Fa-f]{8}\b")

CRASH_MARKERS = (
    "Guru Meditation",
    "Backtrace:",
    "abort()",
    "assert failed",
    "rst:0x",
    "ESP-ROM:",
    "register dump",
    "Rebooting...",
)

FORBIDDEN_COMMAND_TYPES = (
    "start_noise_cal",
    "clear_noise_cal",
    "factory_reset",
    "restore_defaults",
    "erase",
    "reset",
    "dump_raw",
)


def validate_runtime_command(command: str) -> None:
    """Refuse anything that is not a colon-framed safe runtime command."""
    if not command.startswith(":"):
        raise ValueError("command must be colon-framed: %s" % command)
    body = command[1:].strip().lower()
    command_type = body.split("=", 1)[0].split(" ", 1)[0]
    if command_type in FORBIDDEN_COMMAND_TYPES:
        raise ValueError("forbidden runtime command: %s" % command)


def setup_commands(mode: int | None, smart_scene: str | None) -> list[str]:
    commands = [":stop", ":ap_stream=off", ":vp_stream=off"]
    if mode is not None:
        commands.append(":set_mode=%d" % mode)
    if smart_scene:
        commands.append(":smart_scene=%s" % smart_scene)
    return commands


def capture_start_commands(enable_vp_perf: bool) -> list[str]:
    commands = [":ap_stream=on", ":vp_stream=on"]
    if enable_vp_perf:
        commands.extend([":vp_perf=reset", ":vp_perf=start"])
    return commands


def capture_stop_commands(enable_vp_perf: bool) -> list[str]:
    commands = []
    if enable_vp_perf:
        commands.append(":vp_perf=stop")
    commands.extend([":ap_stream=off", ":vp_stream=off"])
    return commands


def assert_command_plan_is_safe(commands: list[str]) -> None:
    for command in commands:
        validate_runtime_command(command)


def parse_number(value: str) -> int | float | str:
    cleaned = value.strip().rstrip(",")
    if re.fullmatch(r"[-+]?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", cleaned):
        return float(cleaned)
    return cleaned


def split_host_line(raw_line: str) -> tuple[float | None, str]:
    """Split '[<host epoch>] payload' -> (ts, payload)."""
    match = HOST_TS_RE.match(raw_line)
    if not match:
        return None, raw_line.strip()
    return float(match.group(1)), match.group(2).strip()


def parse_kv_payload(payload: str) -> dict[str, int | float | str]:
    return {key: parse_number(value) for key, value in SPACE_KV_RE.findall(payload)}


def parse_vpf_payload(payload: str) -> dict[str, Any]:
    """Parse 'VPF,ver=1,seq=..,frame_us=<avg>/<max>,..' csv with avg/max pairs."""
    out: dict[str, Any] = {}
    for part in payload.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key, value = key.strip(), value.strip()
        if "/" in value:
            left, right = value.split("/", 1)
            out[key] = {"avg": parse_number(left), "max": parse_number(right)}
        else:
            out[key] = parse_number(value)
    return out


def is_crash_marker(payload: str) -> bool:
    return any(marker in payload for marker in CRASH_MARKERS)


def is_garbage(payload: str) -> bool:
    return "�" in payload


# ---------------------------------------------------------------------------
# Small stats helpers (pure python; metric paths must not require numpy)
# ---------------------------------------------------------------------------
def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    lo = int(math.floor(rank))
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def safe_mean(values: list[float]) -> float | None:
    return round(mean(values), 6) if values else None


def safe_stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return 0.0 if values else None
    return round(stdev(values), 6)


# ---------------------------------------------------------------------------
# Per-run metric computation (from a host-timestamped serial log)
# ---------------------------------------------------------------------------
def compute_run_metrics(lines: list[str]) -> dict[str, Any]:
    ap_ts: list[float] = []
    ap_samples: list[dict[str, Any]] = []
    apcap_samples: list[dict[str, Any]] = []
    vp_render_us: list[float] = []
    vp_render_max: list[float] = []
    vpf_frame_avg: list[float] = []
    vpf_frame_max: list[float] = []
    vpf_seq: list[int] = []
    crash_count = 0
    garbage_count = 0
    total = 0

    for raw_line in lines:
        total += 1
        ts, payload = split_host_line(raw_line)
        if payload.startswith(">>>") or payload.startswith("#"):
            continue
        if is_garbage(payload):
            garbage_count += 1
        if is_crash_marker(payload):
            crash_count += 1

        if "[APCAP]" in payload:
            apcap_samples.append(parse_kv_payload(payload.split("[APCAP]", 1)[1]))
            continue
        if "[AP]" in payload:
            fields = parse_kv_payload(payload.split("[AP]", 1)[1])
            if ts is not None:
                ap_ts.append(ts)
            ap_samples.append(fields)
            continue
        if "[VP]" in payload:
            fields = parse_kv_payload(payload.split("[VP]", 1)[1])
            if isinstance(fields.get("render_us"), (int, float)):
                vp_render_us.append(float(fields["render_us"]))
            if isinstance(fields.get("render_max"), (int, float)):
                vp_render_max.append(float(fields["render_max"]))
            continue
        marker = payload.find("VPF,")
        if marker >= 0:
            fields = parse_vpf_payload(payload[marker:])
            frame = fields.get("frame_us")
            if isinstance(frame, dict):
                if isinstance(frame.get("avg"), (int, float)):
                    vpf_frame_avg.append(float(frame["avg"]))
                if isinstance(frame.get("max"), (int, float)):
                    vpf_frame_max.append(float(frame["max"]))
            if isinstance(fields.get("seq"), int):
                vpf_seq.append(fields["seq"])

    # --- [AP] cadence (1 Hz health proxy; ~1 s resolution) ---
    gaps = [b - a for a, b in zip(ap_ts, ap_ts[1:])]
    cadence: dict[str, Any] = {"samples": len(ap_ts)}
    if gaps:
        nominal = percentile(gaps, 50.0)
        jitter_ms = [abs(g - nominal) * 1000.0 for g in gaps]
        cadence.update(
            {
                "mean_gap_s": safe_mean(gaps),
                "median_gap_s": round(nominal, 6),
                "max_gap_s": round(max(gaps), 6),
                "p95_jitter_ms": round(percentile(jitter_ms, 95.0), 3),
            }
        )
    else:
        cadence.update({"mean_gap_s": None, "median_gap_s": None, "max_gap_s": None, "p95_jitter_ms": None})

    # --- beat / onset / level from [AP] samples ---
    def numeric(sample: dict[str, Any], key: str) -> float | None:
        value = sample.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    active = [s for s in ap_samples if numeric(s, "silence") == 0.0]
    conf_all = [v for s in ap_samples if (v := numeric(s, "conf")) is not None]
    conf_active = [v for s in active if (v := numeric(s, "conf")) is not None]
    lock_active = [v for s in active if (v := numeric(s, "lock")) is not None]
    locked = [s for s in active if numeric(s, "lock") == 1.0]
    bpm_locked = [v for s in locked if (v := numeric(s, "bpm")) is not None]
    onset_count = sum(1 for s in ap_samples if numeric(s, "onset") == 1.0)
    bass_count = sum(1 for s in ap_samples if numeric(s, "bass") == 1.0)
    peaks = [v for s in ap_samples if (v := numeric(s, "peak_scaled")) is not None]

    hist_edges = [round(i * 0.1, 1) for i in range(11)]  # last bin catches >=1.0
    hist = [0] * 10
    for value in peaks:
        idx = min(int(value * 10.0), 9) if value >= 0 else 0
        hist[idx] += 1

    bpm_mean = safe_mean(bpm_locked)
    metrics: dict[str, Any] = {
        "lines_total": total,
        "garbage_lines": garbage_count,
        "crash_markers": crash_count,
        "ap_cadence": cadence,
        "beat": {
            "conf_mean_all": safe_mean(conf_all),
            "conf_mean_active": safe_mean(conf_active),
            "lock_ratio_active": safe_mean(lock_active),
            "bpm_mean_locked": bpm_mean,
            "bpm_std_locked": safe_stdev(bpm_locked),
            "bpm_abs_err_vs_120": round(abs(bpm_mean - 120.0), 6) if bpm_mean is not None else None,
            "locked_samples": len(locked),
            "active_samples": len(active),
        },
        "onset": {
            # 1 Hz SAMPLED PROXY counts (see module docstring) — A/B comparable,
            # not absolute 133 Hz event counts.
            "onset_sampled_count": onset_count,
            "bass_sampled_count": bass_count,
            "ostr_mean": safe_mean([v for s in ap_samples if (v := numeric(s, "ostr")) is not None]),
            "bstr_mean": safe_mean([v for s in ap_samples if (v := numeric(s, "bstr")) is not None]),
        },
        "peak_scaled": {
            "mean": safe_mean(peaks),
            "p95": round(percentile(peaks, 95.0), 6) if peaks else None,
            "hist_counts": hist,
            "hist_edges": hist_edges,
        },
        "apcap": {
            "windows": len(apcap_samples),
            "peak_scaled_window_max": max(
                (float(v) for s in apcap_samples for v in [s.get("peak_scaled")] if isinstance(v, (int, float))),
                default=None,
            ),
        },
        "vpf": {
            "reports": len(vpf_seq),
            "seq_gaps": sum(max(0, b - a - 1) for a, b in zip(vpf_seq, vpf_seq[1:])),
        },
    }

    # --- render timing surface selection (honest about resolution) ---
    if len(vpf_frame_avg) >= 5:
        metrics["render"] = {
            "surface": "vpf_frame_us",
            "resolution": "full-frame-rate avg/max aggregated per 1 s VPF report; p95 over per-second avgs",
            "p95_us": round(percentile(vpf_frame_avg, 95.0), 3),
            "mean_us": safe_mean(vpf_frame_avg),
            "max_us": max(vpf_frame_max) if vpf_frame_max else None,
        }
    elif len(vp_render_us) >= 5:
        metrics["render"] = {
            "surface": "vp_render_us",
            "resolution": "1 Hz last-frame samples ([VP] line); p95 over 1 Hz samples",
            "p95_us": round(percentile(vp_render_us, 95.0), 3),
            "mean_us": safe_mean(vp_render_us),
            "max_us": max(vp_render_max) if vp_render_max else None,
        }
    else:
        metrics["render"] = {"surface": None, "resolution": None, "p95_us": None, "mean_us": None, "max_us": None}

    return metrics


# ---------------------------------------------------------------------------
# Comparison / verdict
# ---------------------------------------------------------------------------
def _metric(run: dict[str, Any], *path: str) -> float | None:
    node: Any = run
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return float(node) if isinstance(node, (int, float)) else None


def _condition_stats(runs: list[dict[str, Any]], *path: str) -> dict[str, Any]:
    values = [v for run in runs if (v := _metric(run, *path)) is not None]
    return {"values": values, "mean": safe_mean(values), "sd": safe_stdev(values), "n": len(values)}


def compare_runs(off_runs: list[dict[str, Any]], on_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Pre-registered verdict. PASS only if every check passes and no check is MISSING.

    Render check is SKIPPED (not MISSING) when no render surface parsed in
    either condition — per contract it only gates when the surface is available.
    """
    checks: list[dict[str, Any]] = []

    def add_check(
        name: str,
        path: tuple[str, ...],
        threshold: float,
        kind: str,
        note: str = "",
        skip_if_unavailable: bool = False,
    ) -> None:
        off = _condition_stats(off_runs, *path)
        on = _condition_stats(on_runs, *path)
        row: dict[str, Any] = {
            "metric": name,
            "off_mean": off["mean"],
            "off_sd": off["sd"],
            "on_mean": on["mean"],
            "on_sd": on["sd"],
            "threshold": threshold,
            "kind": kind,
            "note": note,
        }
        if off["mean"] is None or on["mean"] is None:
            row["delta"] = None
            row["status"] = "SKIPPED" if skip_if_unavailable else "MISSING"
            checks.append(row)
            return
        delta = on["mean"] - off["mean"]
        row["delta"] = round(delta, 6)
        if kind == "drop":              # FAIL when ON drops below OFF by > threshold (absolute)
            failed = (-delta) > threshold
        elif kind == "abs_rel":         # FAIL when |delta| / |off| > threshold
            failed = abs(off["mean"]) > 1e-12 and abs(delta) / abs(off["mean"]) > threshold
        elif kind == "increase_abs":    # FAIL when ON exceeds OFF by > threshold (absolute)
            failed = delta > threshold
        elif kind == "increase_rel":    # FAIL when (ON-OFF)/OFF > threshold
            failed = abs(off["mean"]) > 1e-12 and (delta / abs(off["mean"])) > threshold
        else:
            raise ValueError("unknown check kind: %s" % kind)
        row["status"] = "FAIL" if failed else "PASS"
        checks.append(row)

    add_check(
        "beat_lock_ratio_active", ("beat", "lock_ratio_active"), THRESH_LOCK_RATIO_DROP, "drop",
        note="absolute drop >%.2f fails" % THRESH_LOCK_RATIO_DROP,
    )
    add_check(
        "beat_conf_mean_active", ("beat", "conf_mean_active"), THRESH_CONF_DROP, "drop",
        note="absolute drop >%.2f fails" % THRESH_CONF_DROP,
    )
    add_check(
        "onset_sampled_count", ("onset", "onset_sampled_count"), THRESH_ONSET_COUNT_REL, "abs_rel",
        note="1 Hz sampled proxy; |delta| >%.0f%% fails" % (THRESH_ONSET_COUNT_REL * 100),
    )
    add_check(
        "peak_scaled_mean", ("peak_scaled", "mean"), THRESH_PEAK_SCALED_REL, "abs_rel",
        note="identical stimulus; |delta| >%.0f%% fails" % (THRESH_PEAK_SCALED_REL * 100),
    )
    add_check(
        "ap_cadence_p95_jitter_ms", ("ap_cadence", "p95_jitter_ms"), THRESH_AP_JITTER_P95_MS, "increase_abs",
        note="1 Hz line cadence; increase >%.0f ms fails" % THRESH_AP_JITTER_P95_MS,
    )
    add_check(
        "render_p95_us", ("render", "p95_us"), THRESH_RENDER_P95_REL, "increase_rel",
        note="VPF/[VP] surface; increase >%.0f%% fails; skipped if unavailable" % (THRESH_RENDER_P95_REL * 100),
        skip_if_unavailable=True,
    )

    # Crash markers: any marker in ANY run (either condition) fails outright —
    # a rebooting bench invalidates the comparison.
    total_crashes = sum(int(_metric(run, "crash_markers") or 0) for run in off_runs + on_runs)
    checks.append(
        {
            "metric": "crash_markers_total",
            "off_mean": safe_mean([float(_metric(r, "crash_markers") or 0) for r in off_runs]),
            "off_sd": None,
            "on_mean": safe_mean([float(_metric(r, "crash_markers") or 0) for r in on_runs]),
            "on_sd": None,
            "delta": total_crashes,
            "threshold": THRESH_CRASH_MARKERS,
            "kind": "any",
            "status": "FAIL" if total_crashes > THRESH_CRASH_MARKERS else "PASS",
            "note": "any crash/reboot marker in any run fails",
        }
    )

    statuses = [check["status"] for check in checks]
    if "FAIL" in statuses:
        verdict = "FAIL"
    elif "MISSING" in statuses:
        verdict = "INCOMPLETE"
    else:
        verdict = "PASS"

    return {
        "verdict": verdict,
        "n_off_runs": len(off_runs),
        "n_on_runs": len(on_runs),
        "checks": checks,
        "doctrine_note": (
            "Scalar A/B symptom measurement only. A FAIL is a measured delta under "
            "condition ON, NOT causal proof that the wireless stack caused it. "
            "Causal attribution requires the MabuTrace dev-trace lane."
        ),
    }


def format_comparison_table(result: dict[str, Any]) -> str:
    def fmt(value: Any) -> str:
        if value is None:
            return "n/a"
        if isinstance(value, float):
            return "%.4f" % value
        return str(value)

    header = "%-28s %12s %10s %12s %10s %12s %8s" % ("metric", "off_mean", "off_sd", "on_mean", "on_sd", "delta", "status")
    rows = [header, "-" * len(header)]
    for check in result["checks"]:
        rows.append(
            "%-28s %12s %10s %12s %10s %12s %8s"
            % (
                check["metric"],
                fmt(check["off_mean"]),
                fmt(check["off_sd"]),
                fmt(check["on_mean"]),
                fmt(check["on_sd"]),
                fmt(check["delta"]),
                check["status"],
            )
        )
    rows.append("-" * len(header))
    rows.append("OVERALL VERDICT: %s   (off runs=%d, on runs=%d)" % (result["verdict"], result["n_off_runs"], result["n_on_runs"]))
    rows.append("NOTE: %s" % result["doctrine_note"])
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Stimulus generation (numpy only here)
# ---------------------------------------------------------------------------
def generate_stimulus(duration_s: float = STIMULUS_DURATION_S, sr: int = STIMULUS_SR):
    """Deterministic test signal as float32 in [-STIMULUS_PEAK, STIMULUS_PEAK]."""
    import numpy as np

    n = int(round(duration_s * sr))
    out = np.zeros(n, dtype=np.float64)
    t_axis = np.arange(n) / float(sr)
    beat_period = 60.0 / STIMULUS_BPM  # 0.5 s
    active_end = min(FINAL_SILENCE_START_S, duration_s)

    def add_tone(start_s: float, length_s: float, freq: float, amp: float, decay: float | None = None) -> None:
        i0 = int(round(start_s * sr))
        i1 = min(int(round((start_s + length_s) * sr)), n)
        if i1 <= i0:
            return
        seg_t = t_axis[: i1 - i0]
        env = np.exp(-seg_t / decay) if decay else np.ones_like(seg_t)
        fade = min(int(0.005 * sr), (i1 - i0) // 2)
        if fade > 0 and decay is None:
            ramp = np.linspace(0.0, 1.0, fade)
            env[:fade] *= ramp
            env[-fade:] *= ramp[::-1]
        out[i0:i1] += amp * env * np.sin(2.0 * np.pi * freq * seg_t)

    melody = (440.0, 523.25, 659.25, 783.99)
    beat_index = 0
    beat_time = 0.0
    while beat_time < active_end:
        add_tone(beat_time, 0.10, 60.0, 0.60, decay=0.03)          # kick
        add_tone(beat_time, 0.006, 2000.0, 0.50)                    # click
        if beat_index % 4 == 0:
            add_tone(beat_time, 0.40, 80.0, 0.50)                   # bass-band burst
        add_tone(beat_time + 0.05, 0.25, melody[beat_index % 4], 0.20)  # mid melody
        beat_index += 1
        beat_time = beat_index * beat_period

    peak = float(np.max(np.abs(out)))
    if peak > 0.0:
        out *= STIMULUS_PEAK / peak

    for cut_start, cut_end in SILENCE_CUTS:
        out[int(round(cut_start * sr)): int(round(cut_end * sr))] = 0.0
    out[int(round(FINAL_SILENCE_START_S * sr)):] = 0.0

    return out.astype(np.float32)


def write_stimulus_wav(path: Path, duration_s: float = STIMULUS_DURATION_S, sr: int = STIMULUS_SR) -> dict[str, Any]:
    import numpy as np
    import wave

    samples = generate_stimulus(duration_s, sr)
    pcm = np.clip(np.round(samples * 32767.0), -32768, 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(pcm.tobytes())
    return {
        "path": str(path),
        "sample_rate": sr,
        "duration_s": duration_s,
        "peak_amplitude": STIMULUS_PEAK,
        "bpm": STIMULUS_BPM,
        "silence_cuts_s": list(list(cut) for cut in SILENCE_CUTS),
        "final_silence_start_s": FINAL_SILENCE_START_S,
        "samples": int(pcm.size),
    }


# ---------------------------------------------------------------------------
# Serial capture session (read-only posture; safe runtime commands only)
# ---------------------------------------------------------------------------
class CaptureSession:
    def __init__(self, port: str, baud: int = DEFAULT_BAUD):
        if serial is None:
            raise RuntimeError("pyserial is not installed; `run` requires it (pip install pyserial)")
        self.port = port
        self.baud = baud
        self.lines: list[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ser = None

    def open(self) -> None:
        self.ser = serial.Serial(
            self.port, self.baud, timeout=0.05, write_timeout=0.5,
            dsrdtr=False, rtscts=False, xonxoff=False,
        )
        time.sleep(2.0)
        self.ser.reset_input_buffer()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self.ser.readline()
            except Exception as exc:  # pragma: no cover - hardware path
                self.mark("#READ_ERROR %s: %s" % (type(exc).__name__, exc))
                self._stop.set()
                break
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line:
                self.mark(line)

    def mark(self, text: str) -> None:
        with self._lock:
            self.lines.append("[%.3f] %s" % (time.time(), text))

    def send(self, command: str, settle: float = 0.30) -> None:
        validate_runtime_command(command)
        self.mark(">>> %s" % command)
        self.ser.write((command + "\n").encode("ascii"))
        time.sleep(settle)

    def verify_identity(self, expected_chip_id: str) -> dict[str, str | None]:
        self.send(":version", settle=0.8)
        self.send(":chip_id", settle=0.8)
        identity: dict[str, str | None] = {"version": None, "chip_id": None}
        with self._lock:
            snapshot = list(self.lines)
        for raw_line in snapshot:
            _, payload = split_host_line(raw_line)
            if payload.startswith(">>>") or payload.startswith("#"):
                continue
            if "VERSION:" in payload:
                identity["version"] = payload.split("VERSION:", 1)[1].strip().split()[0]
            elif "CHIP_ID:" in payload:
                match = CHIP_ID_RE.search(payload.split("CHIP_ID:", 1)[1])
                if match:
                    identity["chip_id"] = match.group(0).upper()
            elif CHIP_ID_RE.fullmatch(payload):
                identity["chip_id"] = payload.upper()
        observed = identity.get("chip_id")
        if not observed:
            raise RuntimeError("identity probe failed on %s: %s" % (self.port, identity))
        if expected_chip_id and observed != expected_chip_id.upper():
            raise RuntimeError(
                "chip_id mismatch on %s: observed %s expected %s — WRONG DEVICE, refusing to continue"
                % (self.port, observed, expected_chip_id.upper())
            )
        return identity

    def snapshot_lines(self) -> list[str]:
        with self._lock:
            return list(self.lines)

    def close(self) -> None:
        if self.ser:
            self._stop.set()
            if self._thread:
                self._thread.join(timeout=1.0)
            try:
                self.ser.close()
            except Exception:  # pragma: no cover
                pass


def run_condition_capture(args: argparse.Namespace) -> Path:
    stimulus = Path(args.stimulus)
    if not stimulus.exists():
        raise SystemExit(
            "stimulus WAV missing: %s — generate it first with `wireless_ab_bench.py make-stimulus`" % stimulus
        )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r"[a-z0-9_\-]+", args.condition):
        raise SystemExit("condition must be a simple slug (e.g. off / on / on_client)")

    session = CaptureSession(args.port, args.baud)
    afplay: subprocess.Popen | None = None
    failure: str | None = None
    identity: dict[str, str | None] = {}
    started_at = datetime.now().isoformat()
    try:
        session.open()
        if not args.no_identity_check:
            identity = session.verify_identity(args.chip_id)

        commands = setup_commands(
            None if args.no_configure else args.mode,
            None if args.no_configure else args.smart_scene,
        )
        assert_command_plan_is_safe(commands)
        for command in commands:
            session.send(command, settle=0.45)

        start_commands = capture_start_commands(not args.no_vp_perf)
        assert_command_plan_is_safe(start_commands)
        for command in start_commands:
            session.send(command, settle=0.30)

        afplay = subprocess.Popen(
            ["afplay", str(stimulus)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        session.mark("#AFPLAY_START %s" % stimulus)

        start = time.time()
        next_apcap = start if args.apcap_window_s > 0 else None
        deadline = start + args.duration
        while time.time() < deadline:
            now = time.time()
            if next_apcap is not None and now >= next_apcap:
                remaining_ms = int(max(0.0, deadline - now) * 1000)
                window_ms = min(int(args.apcap_window_s * 1000), remaining_ms)
                if window_ms >= 1000:
                    session.send(":ap_capture=%d" % window_ms, settle=0.05)
                next_apcap = now + args.apcap_window_s + 0.5
            if afplay.poll() is not None and now < deadline - 1.0:
                session.mark("#AFPLAY_EXIT rc=%s (early)" % afplay.returncode)
                break
            time.sleep(0.05)

        if afplay.poll() is None:
            afplay.terminate()
            try:
                afplay.wait(timeout=3.0)
            except subprocess.TimeoutExpired:  # pragma: no cover
                afplay.kill()
        session.mark("#AFPLAY_DONE rc=%s" % afplay.returncode)

        stop_commands = capture_stop_commands(not args.no_vp_perf)
        assert_command_plan_is_safe(stop_commands)
        for command in stop_commands:
            session.send(command, settle=0.35)
    except Exception as exc:
        failure = "%s: %s" % (type(exc).__name__, exc)
    finally:
        if afplay is not None and afplay.poll() is None:  # pragma: no cover - safety net
            afplay.kill()
        session.close()

    lines = session.snapshot_lines()
    stem = "%s_%d" % (args.condition, args.index)
    log_path = out_dir / ("%s.log" % stem)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    metrics = compute_run_metrics(lines)
    payload = {
        "tool": "wireless_ab_bench",
        "condition": args.condition,
        "index": args.index,
        "port": args.port,
        "identity": identity,
        "stimulus": str(stimulus),
        "duration_s": args.duration,
        "started_at": started_at,
        "afplay_rc": afplay.returncode if afplay is not None else None,
        "failure": failure,
        "raw_log": str(log_path),
        "metrics": metrics,
        "doctrine_note": "Scalar symptom capture; not causal attribution (MabuTrace lane for causality).",
    }
    json_path = out_dir / ("%s.json" % stem)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failure:
        raise SystemExit("capture failed (artifacts kept at %s): %s" % (json_path, failure))
    print("wrote %s" % json_path)
    return json_path


# ---------------------------------------------------------------------------
# Protocol runbook
# ---------------------------------------------------------------------------
PROTOCOL_TEXT = """\
WIRELESS A/B BENCH PROTOCOL (interleaved ABAB, 3 cycles)
=========================================================
Device: main K1, /dev/cu.usbmodem1401, chip_id F887A500. Verify identity before
every flash and run. Flashing is an OPERATOR action — this tool never flashes.

Fixed environment (hold constant for ALL runs):
  - Same speaker, same position, FIXED volume (mark the dial; do not touch it).
  - Same room, no other audio sources, no people moving between speaker and mic.
  - Same stimulus WAV: scripts/regression-harness/fixtures/wireless_ab_stimulus.wav
    (generate once: python3 scripts/regression-harness/wireless_ab_bench.py make-stimulus)
  - Do NOT run noise calibration between conditions.

Conditions:
  OFF — wireless stack absent:
    pio run -e k1_hardware_harness -t upload --upload-port /dev/cu.usbmodem1401
  ON  — wireless AP+WebSocket stack active (same serial surfaces):
    pio run -e k1_wireless_ab_probe  -t upload --upload-port /dev/cu.usbmodem1401
  ON+CLIENT (optional 3rd condition): flash ON, connect the Tab5 controller to
    the K1 AP and leave its UI open during the run; condition slug: on_client.

Interleaved sequence (controls drift in room acoustics / device temperature):
  cycle 1: flash OFF -> run off_1 ; flash ON -> run on_1
  cycle 2: flash OFF -> run off_2 ; flash ON -> run on_2
  cycle 3: flash OFF -> run off_3 ; flash ON -> run on_3
  (optional: on_client_1..3 appended per cycle)
After each flash: wait for boot to settle (~10 s) before starting the run.

Per run (90 s stimulus):
  python3 scripts/regression-harness/wireless_ab_bench.py run \\
      --condition off --index 1 --out docs/forensics/runtime-evidence/wireless-ab/<date> \\
      --port /dev/cu.usbmodem1401

Verdict:
  python3 scripts/regression-harness/wireless_ab_bench.py compare \\
      --off <out>/off_*.json --on <out>/on_*.json

Doctrine: the compare verdict quantifies SYMPTOM deltas only. If it FAILs,
causal attribution escalates to the MabuTrace dev-trace lane
(k1_hardware_trace_dev); do not report this bench as causal proof.
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wireless A/B bench (AP/VP symptom deltas, WiFi ON vs OFF)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stim = sub.add_parser("make-stimulus", help="generate the deterministic 90 s stimulus WAV")
    p_stim.add_argument("--out", default=str(DEFAULT_STIMULUS))
    p_stim.add_argument("--duration", type=float, default=STIMULUS_DURATION_S)
    p_stim.add_argument("--sample-rate", type=int, default=STIMULUS_SR)

    p_run = sub.add_parser("run", help="capture one condition run (serial + afplay + metrics)")
    p_run.add_argument("--condition", required=True, help="condition slug: off / on / on_client")
    p_run.add_argument("--index", type=int, required=True, help="run number within the condition (1..N)")
    p_run.add_argument("--out", required=True, help="output directory for <condition>_<n>.json/.log")
    p_run.add_argument("--port", default=DEFAULT_PORT)
    p_run.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    p_run.add_argument("--chip-id", default=DEFAULT_CHIP_ID)
    p_run.add_argument("--no-identity-check", action="store_true")
    p_run.add_argument("--stimulus", default=str(DEFAULT_STIMULUS))
    p_run.add_argument("--duration", type=float, default=STIMULUS_DURATION_S)
    p_run.add_argument("--mode", type=int, default=22)
    p_run.add_argument("--smart-scene", default="l1")
    p_run.add_argument("--no-configure", action="store_true", help="observational: no set_mode/smart_scene")
    p_run.add_argument("--no-vp-perf", action="store_true", help="skip :vp_perf commands")
    p_run.add_argument("--apcap-window-s", type=float, default=5.0, help="0 disables :ap_capture windows")

    p_cmp = sub.add_parser("compare", help="N OFF runs vs N ON runs -> verdict")
    p_cmp.add_argument("--off", nargs="+", required=True, help="OFF-condition run JSON files")
    p_cmp.add_argument("--on", nargs="+", required=True, help="ON-condition run JSON files")
    p_cmp.add_argument("--json-out", default=None, help="optional path for the verdict JSON")

    sub.add_parser("protocol", help="print the ABAB runbook")

    args = parser.parse_args(argv)

    if args.cmd == "make-stimulus":
        info = write_stimulus_wav(Path(args.out), args.duration, args.sample_rate)
        print(json.dumps(info, indent=2))
        return 0

    if args.cmd == "run":
        run_condition_capture(args)
        return 0

    if args.cmd == "compare":
        def load_metrics(paths: list[str]) -> list[dict[str, Any]]:
            runs = []
            for raw in paths:
                payload = json.loads(Path(raw).read_text(encoding="utf-8"))
                runs.append(payload.get("metrics", payload))
            return runs

        result = compare_runs(load_metrics(args.off), load_metrics(args.on))
        print(format_comparison_table(result))
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.json_out:
            Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.json_out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if result["verdict"] == "PASS" else 1

    if args.cmd == "protocol":
        print(PROTOCOL_TEXT)
        return 0

    return 2  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
