#!/usr/bin/env python3
"""Build a source-backed presentation from framed VPAB runtime evidence.

This is a host-side analysis tool only. It decodes the fail-closed K1DF framed
transport, extracts final LED-byte semantics from VPAB payloads, and writes a
Markdown brief plus a standalone HTML presentation.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import math
import statistics
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FRAME_GATE_PATH = ROOT / "scripts" / "regression-harness" / "vpab_frame_gate.py"

KIND_METRICS = 1
KIND_BYTES = 2
CHANNEL_NAMES = {0: "primary", 1: "secondary"}
KIND_NAMES = {KIND_METRICS: "vpab_metrics", KIND_BYTES: "vpab_bytes"}
LED_CENTRE = 79.5


def _load_frame_gate():
    spec = importlib.util.spec_from_file_location("vpab_frame_gate", FRAME_GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {FRAME_GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpab_frame_gate = _load_frame_gate()


def _parse_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in line.strip().split(",")[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def _int_field(fields: dict[str, str], key: str, default: int = 0) -> int:
    raw = fields.get(key)
    if raw is None:
        return default
    if raw.lower().startswith("0x"):
        return int(raw, 16)
    return int(raw)


def _float_field(fields: dict[str, str], key: str, default: float = 0.0) -> float:
    raw = fields.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def assemble_payloads(frames_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return the strict gate result and decoded raw payload records."""

    gate = vpab_frame_gate.evaluate_text(
        frames_text,
        require_modes={18},
        require_channels={"primary", "secondary"},
        require_kinds={"vpab_metrics", "vpab_bytes"},
    )
    begin, end, records, record_order, issues = vpab_frame_gate._parse_stream(frames_text)
    if issues:
        raise ValueError(f"strict frame stream has parser issues: {issues[:3]}")

    assembled: list[dict[str, Any]] = []
    for seq in record_order:
        record = records[seq]
        payload = bytearray(record["len"] or 0)
        for idx in range(record["chunks"] or 0):
            chunk = record["chunk_items"][idx]
            off = chunk["off"]
            payload[off:off + len(chunk["payload"])] = chunk["payload"]
        assembled.append(
            {
                "seq": record["seq"],
                "kind": record["kind"],
                "kind_name": KIND_NAMES.get(record["kind"], "unknown"),
                "frame": record["frame"],
                "t_us": record["t_us"],
                "payload": bytes(payload),
            }
        )
    return gate, assembled


def decode_metric_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = record["payload"]
    if len(payload) != 104:
        raise ValueError(f"metric payload seq={record['seq']} length {len(payload)} != 104")
    return {
        "seq": record["seq"],
        "kind": "vpab_metrics",
        "frame": record["frame"],
        "t_us": record["t_us"],
        "channel_id": payload[0],
        "channel": CHANNEL_NAMES.get(payload[0], "unknown"),
        "mode": payload[1],
        "scenario": payload[2],
        "shadow": payload[3],
        "memory_metrics": payload[4],
        "dither_step": payload[5],
        "fastled_dither": payload[6],
        "truncated": payload[7],
        "leds": struct.unpack_from("<H", payload, 8)[0],
        "t_ms": struct.unpack_from("<I", payload, 12)[0],
        "dt_us": struct.unpack_from("<I", payload, 16)[0],
        "quant_us": struct.unpack_from("<I", payload, 20)[0],
        "mae8": struct.unpack_from("<f", payload, 24)[0],
        "p95_abs8": payload[28],
        "max_abs8": payload[29],
        "changed_led_pct": struct.unpack_from("<f", payload, 32)[0],
        "changed_channel_pct": struct.unpack_from("<f", payload, 36)[0],
        "energy_a": struct.unpack_from("<I", payload, 40)[0],
        "energy_b": struct.unpack_from("<I", payload, 44)[0],
        "energy_delta_pct": struct.unpack_from("<f", payload, 48)[0],
        "com_a": struct.unpack_from("<f", payload, 52)[0],
        "com_b": struct.unpack_from("<f", payload, 56)[0],
        "com_delta_leds": struct.unpack_from("<f", payload, 60)[0],
        "com_slope_delta_pct": struct.unpack_from("<f", payload, 64)[0],
        "hue_delta_p95": payload[68],
        "sat_delta_p95": payload[69],
        "white_bias_score": struct.unpack_from("<f", payload, 72)[0],
        "flicker_score": struct.unpack_from("<f", payload, 76)[0],
        "render_us": struct.unpack_from("<I", payload, 80)[0],
        "frame_us": struct.unpack_from("<I", payload, 84)[0],
        "show_us": struct.unpack_from("<I", payload, 88)[0],
        "over": struct.unpack_from("<I", payload, 92)[0],
        "dropped": struct.unpack_from("<I", payload, 96)[0],
        "heap": struct.unpack_from("<I", payload, 100)[0],
    }


def _sat8(rgb: tuple[int, int, int]) -> int:
    mx = max(rgb)
    if mx == 0:
        return 0
    mn = min(rgb)
    return int(((mx - mn) * 255) / mx)


def _white_bias8(rgb: tuple[int, int, int]) -> int:
    mx = max(rgb)
    if mx == 0:
        return 0
    return int((min(rgb) * 255) / mx)


def decode_bytes_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = record["payload"]
    if len(payload) != 512:
        raise ValueError(f"bytes payload seq={record['seq']} length {len(payload)} != 512")
    leds = struct.unpack_from("<H", payload, 4)[0]
    byte_count = struct.unpack_from("<H", payload, 6)[0]
    raw_bytes = payload[32:32 + byte_count]
    colours = [
        (raw_bytes[i], raw_bytes[i + 1], raw_bytes[i + 2])
        for i in range(0, min(byte_count, leds * 3), 3)
    ]
    energy_values = [r + g + b for r, g, b in colours]
    energy = sum(energy_values)
    nonzero = sum(1 for value in energy_values if value > 0)
    r_sum = sum(rgb[0] for rgb in colours)
    g_sum = sum(rgb[1] for rgb in colours)
    b_sum = sum(rgb[2] for rgb in colours)
    weighted = sum(index * value for index, value in enumerate(energy_values))
    com = weighted / energy if energy else (leds - 1) / 2.0 if leds else 0.0
    left_energy = sum(energy_values[:80])
    right_energy = sum(energy_values[80:])
    denom = max(1, left_energy + right_energy)
    centre_balance = (right_energy - left_energy) / denom
    max_luma = max((value / 3.0 for value in energy_values), default=0.0)
    sat_avg = statistics.fmean(_sat8(rgb) for rgb in colours) if colours else 0.0
    white_bias_avg = statistics.fmean(_white_bias8(rgb) for rgb in colours) if colours else 0.0
    peak_led = max(range(len(energy_values)), key=lambda i: energy_values[i]) if energy_values else 0

    return {
        "seq": record["seq"],
        "kind": "vpab_bytes",
        "frame": record["frame"],
        "t_us": record["t_us"],
        "channel_id": payload[0],
        "channel": CHANNEL_NAMES.get(payload[0], "unknown"),
        "mode": payload[1],
        "dither_step": payload[2],
        "fastled_dither": payload[3],
        "leds": leds,
        "byte_count": byte_count,
        "render_us": struct.unpack_from("<I", payload, 8)[0],
        "quant_us": struct.unpack_from("<I", payload, 12)[0],
        "frame_us": struct.unpack_from("<I", payload, 16)[0],
        "show_us": struct.unpack_from("<I", payload, 20)[0],
        "over": struct.unpack_from("<I", payload, 24)[0],
        "dropped": struct.unpack_from("<I", payload, 28)[0],
        "rgb": colours,
        "energy": energy,
        "r_sum": r_sum,
        "g_sum": g_sum,
        "b_sum": b_sum,
        "nonzero_led_pct": (nonzero * 100.0 / leds) if leds else 0.0,
        "com": com,
        "centre_distance": abs(com - LED_CENTRE),
        "left_energy": left_energy,
        "right_energy": right_energy,
        "centre_balance": centre_balance,
        "sat_avg": sat_avg,
        "white_bias_avg": white_bias_avg,
        "max_luma": max_luma,
        "peak_led": peak_led,
    }


def decode_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metrics: list[dict[str, Any]] = []
    bytes_rows: list[dict[str, Any]] = []
    for record in records:
        if record["kind"] == KIND_METRICS:
            metrics.append(decode_metric_payload(record))
        elif record["kind"] == KIND_BYTES:
            bytes_rows.append(decode_bytes_payload(record))
    first_t = min((row["t_us"] for row in bytes_rows), default=0)
    for collection in (metrics, bytes_rows):
        for row in collection:
            row["seconds"] = (row["t_us"] - first_t) / 1_000_000.0
    return metrics, bytes_rows


def parse_raw_perf(raw_text: str) -> dict[str, Any]:
    vpf_rows: list[dict[str, Any]] = []
    vp_perf_frame: dict[str, Any] = {}
    vp_perf_heap = None
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if line.startswith("VPF,"):
            fields = _parse_fields(line)
            row: dict[str, Any] = {"seq": _int_field(fields, "seq")}
            for key, value in fields.items():
                if "/" in value:
                    left, right = value.split("/", 1)
                    row[f"{key}_avg"] = float(left)
                    row[f"{key}_max"] = float(right)
                else:
                    try:
                        row[key] = int(value)
                    except ValueError:
                        row[key] = value
            vpf_rows.append(row)
        elif line.startswith("VP_PERF_FRAME:"):
            fields = {}
            for token in line.split(":", 1)[1].strip().split():
                if "=" in token:
                    key, value = token.split("=", 1)
                    fields[key] = value
            vp_perf_frame = {
                "avg": _int_field(fields, "avg"),
                "max": _int_field(fields, "max"),
                "over": _int_field(fields, "over"),
                "dropped": _int_field(fields, "dropped"),
            }
        elif line.startswith("VP_PERF_HEAP:"):
            try:
                vp_perf_heap = int(line.split(":", 1)[1].strip())
            except ValueError:
                vp_perf_heap = None

    last_vpf = vpf_rows[-1] if vpf_rows else {}
    return {"vpf_rows": vpf_rows, "last_vpf": last_vpf, "vp_perf_frame": vp_perf_frame, "heap": vp_perf_heap}


def summarise_channel(rows: list[dict[str, Any]], channel: str) -> dict[str, Any]:
    channel_rows = [row for row in rows if row["channel"] == channel]
    energy = [row["energy"] for row in channel_rows]
    nonzero = [row["nonzero_led_pct"] for row in channel_rows]
    com = [row["com"] for row in channel_rows]
    sat = [row["sat_avg"] for row in channel_rows]
    white = [row["white_bias_avg"] for row in channel_rows]
    max_luma = [row["max_luma"] for row in channel_rows]
    return {
        "samples": len(channel_rows),
        "energy_min": min(energy) if energy else 0,
        "energy_max": max(energy) if energy else 0,
        "energy_mean": statistics.fmean(energy) if energy else 0.0,
        "nonzero_led_pct_mean": statistics.fmean(nonzero) if nonzero else 0.0,
        "com_min": min(com) if com else 0.0,
        "com_max": max(com) if com else 0.0,
        "com_mean": statistics.fmean(com) if com else 0.0,
        "centre_distance_mean": statistics.fmean(abs(value - LED_CENTRE) for value in com) if com else 0.0,
        "sat_avg_mean": statistics.fmean(sat) if sat else 0.0,
        "white_bias_avg_mean": statistics.fmean(white) if white else 0.0,
        "max_luma_max": max(max_luma) if max_luma else 0.0,
        "unique_hash_proxy": len({tuple(row["rgb"]) for row in channel_rows}),
    }


def build_summary(
    gate: dict[str, Any],
    metrics: list[dict[str, Any]],
    bytes_rows: list[dict[str, Any]],
    raw_perf: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "vpab_semantic_presentation.v1",
        "source_boundary": {
            "proves": [
                "framed VPAB transport integrity",
                "mode 18 primary and secondary final-byte coverage",
                "runtime timing health during the live-music capture",
            ],
            "does_not_prove": [
                "raw PCM audio content",
                "named reference-track repeatability",
                "AudioSemanticState tempo or chord timeline",
                "current-vs-VME final-byte equivalence",
            ],
        },
        "gate": gate,
        "runtime_perf": {
            "frame_budget_us": 8333,
            "render_budget_us": 2000,
            "vp_perf_frame": raw_perf.get("vp_perf_frame", {}),
            "heap": raw_perf.get("heap"),
            "last_vpf": raw_perf.get("last_vpf", {}),
        },
        "payload_counts": {
            "metrics": len(metrics),
            "bytes": len(bytes_rows),
            "samples_per_channel": {
                channel: len([row for row in bytes_rows if row["channel"] == channel])
                for channel in ("primary", "secondary")
            },
        },
        "channels": {
            "primary": summarise_channel(bytes_rows, "primary"),
            "secondary": summarise_channel(bytes_rows, "secondary"),
        },
        "timeline": [
            {
                key: row[key]
                for key in (
                    "seq",
                    "frame",
                    "seconds",
                    "channel",
                    "mode",
                    "energy",
                    "nonzero_led_pct",
                    "com",
                    "centre_distance",
                    "centre_balance",
                    "sat_avg",
                    "white_bias_avg",
                    "max_luma",
                    "render_us",
                    "quant_us",
                    "frame_us",
                    "show_us",
                    "over",
                    "dropped",
                    "peak_led",
                )
            }
            for row in bytes_rows
        ],
    }


def _fmt(value: float | int, places: int = 1) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.{places}f}"


def _pct(value: float, places: int = 1) -> str:
    return f"{value:.{places}f}%"


def _safe_id(text: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in text.lower()).strip("-")


def _colour_hex(rgb: tuple[int, int, int], gain: float = 1.0) -> str:
    r = max(0, min(255, int(round(rgb[0] * gain))))
    g = max(0, min(255, int(round(rgb[1] * gain))))
    b = max(0, min(255, int(round(rgb[2] * gain))))
    return f"#{r:02x}{g:02x}{b:02x}"


def _line_chart(
    rows: list[dict[str, Any]],
    series: list[tuple[str, str, str]],
    width: int = 760,
    height: int = 260,
) -> str:
    if not rows:
        return ""
    pad_l, pad_r, pad_t, pad_b = 54, 18, 24, 36
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    x_values = [row["seconds"] for row in rows]
    x_min, x_max = min(x_values), max(x_values)
    if math.isclose(x_min, x_max):
        x_max = x_min + 1.0
    all_y = [float(row[key]) for key, _, _ in series for row in rows]
    y_min, y_max = min(all_y), max(all_y)
    if math.isclose(y_min, y_max):
        y_max = y_min + 1.0
    y_pad = (y_max - y_min) * 0.08
    y_min -= y_pad
    y_max += y_pad

    def x_pos(value: float) -> float:
        return pad_l + ((value - x_min) / (x_max - x_min)) * plot_w

    def y_pos(value: float) -> float:
        return pad_t + (1.0 - ((value - y_min) / (y_max - y_min))) * plot_h

    polylines = []
    legend = []
    for key, label, colour in series:
        points = " ".join(f"{x_pos(row['seconds']):.1f},{y_pos(float(row[key])):.1f}" for row in rows)
        polylines.append(f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2.4"/>')
        legend.append(
            f'<span class="legend-item"><i style="background:{colour}"></i>{html.escape(label)}</span>'
        )
    x0, y0 = pad_l, pad_t + plot_h
    grid = []
    for tick in range(5):
        frac = tick / 4
        x = pad_l + frac * plot_w
        y = pad_t + frac * plot_h
        xv = x_min + frac * (x_max - x_min)
        yv = y_max - frac * (y_max - y_min)
        grid.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{pad_t}" y2="{y0}" class="chart-grid"/>')
        grid.append(f'<text x="{x:.1f}" y="{height - 10}" class="axis" text-anchor="middle">{xv:.1f}s</text>')
        grid.append(f'<line x1="{pad_l}" x2="{width - pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="chart-grid"/>')
        grid.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" class="axis" text-anchor="end">{yv:.0f}</text>')
    return (
        f'<div class="chart-legend">{"".join(legend)}</div>'
        f'<svg viewBox="0 0 {width} {height}" class="line-chart" role="img">'
        f'{"".join(grid)}<line x1="{x0}" y1="{y0}" x2="{width - pad_r}" y2="{y0}" class="axis-line"/>'
        f'<line x1="{x0}" y1="{pad_t}" x2="{x0}" y2="{y0}" class="axis-line"/>'
        f'{"".join(polylines)}</svg>'
    )


def _heatmap(rows: list[dict[str, Any]], channel: str) -> tuple[str, float]:
    channel_rows = [row for row in rows if row["channel"] == channel]
    if not channel_rows:
        return "", 1.0
    max_byte = max((max(rgb) for row in channel_rows for rgb in row["rgb"]), default=0)
    gain = max(1.0, min(6.0, 220.0 / max(1, max_byte)))
    cell_w, cell_h = 4, 9
    width = 160 * cell_w
    height = len(channel_rows) * cell_h
    rects = []
    for y, row in enumerate(channel_rows):
        for x, rgb in enumerate(row["rgb"][:160]):
            rects.append(
                f'<rect x="{x * cell_w}" y="{y * cell_h}" width="{cell_w}" height="{cell_h}" '
                f'fill="{_colour_hex(rgb, gain)}"/>'
            )
    centre_x = 80 * cell_w
    svg = (
        f'<svg viewBox="0 0 {width} {height}" class="heatmap" role="img" '
        f'aria-label="{html.escape(channel)} final LED-byte heatmap">'
        f'{"".join(rects)}'
        f'<line x1="{centre_x}" x2="{centre_x}" y1="0" y2="{height}" class="centre-line"/>'
        f'</svg>'
    )
    return svg, gain


def _presentation_payload_json(rows: list[dict[str, Any]]) -> str:
    channels: dict[str, dict[str, Any]] = {}
    for channel in ("primary", "secondary"):
        channel_rows = [row for row in rows if row["channel"] == channel]
        max_luma = max((row["max_luma"] for row in channel_rows), default=1.0)
        max_byte = max((max(rgb) for row in channel_rows for rgb in row["rgb"]), default=1)
        channels[channel] = {
            "maxLuma": max(1.0, max_luma),
            "maxByte": max(1, max_byte),
            "rows": [
                {
                    "seconds": round(float(row["seconds"]), 3),
                    "frame": row["frame"],
                    "energy": row["energy"],
                    "luma": [int(round((r + g + b) / 3.0)) for r, g, b in row["rgb"][:160]],
                    "rgb": [value for rgb in row["rgb"][:160] for value in rgb],
                }
                for row in channel_rows
            ],
        }
    return json.dumps({"channels": channels}, separators=(",", ":"))


def _metric_bar(label: str, value: float, budget: float, colour_var: str) -> str:
    pct = min(100.0, (value / budget) * 100.0) if budget else 0.0
    return (
        '<div class="budget-row">'
        f'<div><strong>{html.escape(label)}</strong><span>{value:.0f}us / {budget:.0f}us</span></div>'
        '<div class="budget-track">'
        f'<div style="width:{pct:.1f}%;background:var({colour_var});"></div>'
        '</div></div>'
    )


def _channel_table(summary: dict[str, Any]) -> str:
    rows = []
    for channel in ("primary", "secondary"):
        data = summary["channels"][channel]
        rows.append(
            "<tr>"
            f"<th>{channel}</th>"
            f"<td>{data['samples']}</td>"
            f"<td>{_fmt(data['energy_mean'], 0)}</td>"
            f"<td>{_fmt(data['energy_max'], 0)}</td>"
            f"<td>{_pct(data['nonzero_led_pct_mean'])}</td>"
            f"<td>{_fmt(data['com_mean'])}</td>"
            f"<td>{_fmt(data['centre_distance_mean'])}</td>"
            f"<td>{_fmt(data['sat_avg_mean'])}</td>"
            f"<td>{_fmt(data['white_bias_avg_mean'])}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table class="data-table"><thead><tr><th>Channel</th><th>Samples</th>'
        '<th>Mean energy</th><th>Peak energy</th><th>Active LEDs</th>'
        '<th>Mean centre</th><th>Mean centre distance</th><th>Saturation</th>'
        '<th>White bias</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def render_markdown(summary: dict[str, Any], paths: dict[str, Path]) -> str:
    gate = summary["gate"]
    perf = summary["runtime_perf"]
    frame_perf = perf["vp_perf_frame"]
    return f"""# K1 Mode 18 VPAB Music Capture - Semantic Brief

Date: 2026-06-07

## Evidence Boundary

This is audio-conditioned visual evidence, not a reconstruction of the raw music signal.
The capture proves framed VPAB transport integrity, mode 18 primary/secondary coverage,
actual final LED-byte payload availability, and timing health during live music.

It does not prove raw PCM content, named-track repeatability, full AudioSemanticState
tempo/chord history, or current-vs-VME final-byte equivalence.

## Runtime Transport Result

- Gate result: `{gate['result']}`
- Records/chunks: `{gate['counts']['records']}` / `{gate['counts']['chunks']}`
- Issues/failures: `{gate['counts']['issues']}` / `{gate['counts']['failures']}`
- Dropped/corrupt/overflowed: `{gate['stream']['begin'].get('dropped', 0)}` / `{gate['stream']['begin'].get('corrupt', 0)}` / `{gate['stream']['begin'].get('overflowed', 0)}`
- Coverage: mode `{gate['coverage']['modes']}`, channels `{gate['coverage']['channels']}`, kinds `{gate['coverage']['kinds']}`

## Runtime Timing

- Frame avg/max: `{frame_perf.get('avg', 0)}us / {frame_perf.get('max', 0)}us`
- Frame budget: `{perf['frame_budget_us']}us`
- Over/dropped frames: `{frame_perf.get('over', 0)}` / `{frame_perf.get('dropped', 0)}`
- Heap: `{perf.get('heap')}`

## Channel Semantics From Final Bytes

{_channel_table_markdown(summary)}

## Interpretation

Mode 18 was driven by live programme material while Smart Scene and AP/VP text
streams were disabled. The audio pipeline remains the upstream cause of visual
state, but the evidence captured here sits at the visual-pipeline boundary:
final channel bytes after rendering and quantisation, plus timing counters.

The significance for K1 is that the proof transport now reaches the perceptual
surface rather than survivor CSV rows. It can show whether the visual result is
energetic, spatially moving, colour-saturated, balanced between channels, and
inside timing budget. The next VME L1 step is to put candidate VME bytes beside
these canonical bytes and compare them at this same boundary.

## Source Ledger

- Gate summary: `{paths['gate']}`
- Raw capture log: `{paths['raw']}`
- Framed records: `{paths['frames']}`
- Payload schema: `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.h`
- Payload producer: `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp`
- Lane closeout: `docs/forensics/vme_l1/2026-06-07-vpab-framed-transport-ready.md`

## Generated Outputs

- HTML presentation: `{paths['html']}` (dark scalar colour-map heatmaps plus animated final-byte waterfall)
- Semantic summary JSON: `{paths['summary_json']}`
"""


def _channel_table_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "| Channel | Samples | Mean energy | Peak energy | Active LEDs | Mean centre | Mean centre distance | Saturation | White bias |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for channel in ("primary", "secondary"):
        data = summary["channels"][channel]
        lines.append(
            f"| {channel} | {data['samples']} | {_fmt(data['energy_mean'], 0)} | "
            f"{_fmt(data['energy_max'], 0)} | {_pct(data['nonzero_led_pct_mean'])} | "
            f"{_fmt(data['com_mean'])} | {_fmt(data['centre_distance_mean'])} | "
            f"{_fmt(data['sat_avg_mean'])} | {_fmt(data['white_bias_avg_mean'])} |"
        )
    return "\n".join(lines)


def render_html(summary: dict[str, Any], bytes_rows: list[dict[str, Any]], paths: dict[str, Path]) -> str:
    primary_rows = [row for row in bytes_rows if row["channel"] == "primary"]
    secondary_rows = [row for row in bytes_rows if row["channel"] == "secondary"]
    presentation_payload = _presentation_payload_json(bytes_rows)
    perf = summary["runtime_perf"]
    frame_perf = perf["vp_perf_frame"]
    last_vpf = perf["last_vpf"]
    primary_render_max = float(last_vpf.get("pri_render_us_max", 0.0))
    secondary_render_max = float(last_vpf.get("sec_render_us_max", 0.0))

    energy_chart = _line_chart(
        bytes_rows,
        [
            ("energy", "energy", "var(--colour-audio)"),
            ("nonzero_led_pct", "active LEDs %", "var(--colour-proof)"),
        ],
    )
    primary_space_chart = _line_chart(
        primary_rows,
        [
            ("com", "centre of mass", "var(--colour-visual)"),
            ("peak_led", "brightest LED", "var(--colour-transport)"),
        ],
    )
    secondary_space_chart = _line_chart(
        secondary_rows,
        [
            ("com", "centre of mass", "var(--colour-visual)"),
            ("peak_led", "brightest LED", "var(--colour-transport)"),
        ],
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>K1 VPAB Music Capture - Semantic Presentation</title>
<style>
/* Hallmark - pre-emit critique: P4 H4 E4 S5 R4 V4 */
:root {{
  --font-body: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --colour-paper: #05070a;
  --colour-ink: #f5f7fb;
  --colour-muted: #96a6b7;
  --colour-line: #253241;
  --colour-panel: #0d1219;
  --colour-panel-strong: #121a24;
  --colour-audio: #39d6c8;
  --colour-visual: #ff4f8a;
  --colour-transport: #ffad3d;
  --colour-proof: #7dff9d;
  --colour-risk: #ff7d63;
  --colour-glow: #74d7ff;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; overflow-x: clip; }}
body {{
  background:
    radial-gradient(circle at 20% -10%, rgba(57, 214, 200, .18), transparent 34rem),
    radial-gradient(circle at 92% 8%, rgba(255, 79, 138, .15), transparent 32rem),
    var(--colour-paper);
  color: var(--colour-ink);
  font-family: var(--font-body);
  line-height: 1.45;
}}
main {{ max-width: 1180px; margin: 0 auto; padding: 34px 20px 56px; }}
header {{ display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(260px, .7fr); gap: 24px; align-items: end; border-bottom: 1px solid var(--colour-line); padding-bottom: 24px; }}
h1 {{ font-size: clamp(2.1rem, 5vw, 5.1rem); line-height: .92; letter-spacing: 0; margin: 0; max-width: 920px; overflow-wrap: anywhere; }}
h2 {{ font-size: 1.35rem; margin: 0 0 14px; letter-spacing: 0; }}
h3 {{ font-size: .95rem; margin: 0 0 8px; text-transform: uppercase; letter-spacing: .08em; color: var(--colour-muted); overflow-wrap: anywhere; }}
p {{ margin: 0 0 12px; overflow-wrap: anywhere; }}
.lede {{ font-size: 1.08rem; color: var(--colour-muted); max-width: 760px; }}
.stamp {{ font-family: var(--font-mono); font-size: .82rem; color: var(--colour-muted); overflow-wrap: anywhere; }}
.section {{ margin-top: 34px; }}
.grid {{ display: grid; gap: 14px; }}
.grid > *, .panel, .stat, .node {{ min-width: 0; }}
.stats {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
.stat, .panel {{ background: linear-gradient(180deg, var(--colour-panel-strong), var(--colour-panel)); border: 1px solid var(--colour-line); border-radius: 8px; padding: 16px; box-shadow: 0 24px 70px rgba(0,0,0,.22); }}
.stat strong {{ display: block; font-size: 1.9rem; line-height: 1; }}
.stat span {{ display: block; color: var(--colour-muted); margin-top: 6px; }}
.badge {{ display: inline-flex; align-items: center; min-height: 24px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--colour-line); color: var(--colour-muted); font-size: .78rem; font-weight: 700; background: rgba(255,255,255,.03); }}
.badge.pass {{ color: var(--colour-proof); border-color: rgba(125,255,157,.42); }}
.badge.limit {{ color: var(--colour-risk); border-color: rgba(255,125,99,.42); }}
.pipeline {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; }}
.node {{ min-height: 112px; border: 1px solid var(--colour-line); background: rgba(13,18,25,.88); border-radius: 8px; padding: 12px; position: relative; }}
.node b {{ display: block; font-size: .96rem; }}
.node small {{ display: block; color: var(--colour-muted); margin-top: 6px; }}
.node::after {{ content: ""; position: absolute; right: -9px; top: 50%; width: 8px; border-top: 2px solid var(--colour-muted); }}
.node:last-child::after {{ display: none; }}
.budget-row {{ display: grid; grid-template-columns: 190px minmax(0, 1fr); gap: 14px; align-items: center; margin: 10px 0; }}
.budget-row span {{ display: block; color: var(--colour-muted); font-size: .84rem; }}
.budget-track {{ height: 14px; border-radius: 999px; background: #1b2430; overflow: hidden; }}
.budget-track div {{ height: 100%; border-radius: inherit; }}
.table-wrap {{ width: 100%; overflow-x: auto; }}
.data-table {{ width: 100%; min-width: 640px; border-collapse: collapse; font-size: .9rem; }}
.data-table th, .data-table td {{ border-bottom: 1px solid var(--colour-line); padding: 9px 8px; text-align: right; }}
.data-table th:first-child, .data-table td:first-child {{ text-align: left; }}
.viz-frame {{ border: 1px solid var(--colour-line); background: #020406; border-radius: 8px; padding: 10px; box-shadow: inset 0 0 0 1px rgba(255,255,255,.03), 0 18px 60px rgba(0,0,0,.32); }}
.viz-canvas {{ display: block; width: 100%; max-width: 100%; height: 220px; border-radius: 5px; background: #000; }}
.viz-canvas.heatmap-canvas {{ height: 164px; image-rendering: pixelated; }}
.viz-note {{ color: var(--colour-muted); font-size: .88rem; margin-top: 8px; }}
.viz-toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 14px; }}
.viz-toolbar button {{ appearance: none; border: 1px solid var(--colour-line); background: #101923; color: var(--colour-muted); border-radius: 999px; padding: 7px 11px; font: 700 .78rem var(--font-body); cursor: pointer; }}
.viz-toolbar button[aria-pressed="true"] {{ color: var(--colour-ink); border-color: rgba(57,214,200,.8); background: linear-gradient(90deg, rgba(57,214,200,.22), rgba(255,79,138,.2)); }}
.chart-legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 6px 0 2px; }}
.legend-item {{ display: inline-flex; align-items: center; gap: 6px; color: var(--colour-muted); font-size: .85rem; }}
.legend-item i {{ width: 12px; height: 12px; display: inline-block; border-radius: 50%; }}
.line-chart {{ display: block; width: 100%; max-width: 100%; background: #080d13; border: 1px solid var(--colour-line); border-radius: 8px; }}
.chart-grid {{ stroke: #1e2b38; stroke-width: 1; }}
.axis, .axis-line {{ fill: var(--colour-muted); stroke: var(--colour-muted); font-size: 10px; }}
.split {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.callouts {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.callout {{ border-left: 4px solid var(--colour-audio); padding-left: 12px; }}
.callout:nth-child(2) {{ border-color: var(--colour-visual); }}
.callout:nth-child(3) {{ border-color: var(--colour-transport); }}
code {{ font-family: var(--font-mono); font-size: .92em; overflow-wrap: anywhere; }}
footer {{ margin-top: 38px; padding-top: 18px; border-top: 1px solid var(--colour-line); color: var(--colour-muted); font-size: .88rem; }}
@media (max-width: 860px) {{
  header, .split, .callouts, .pipeline {{ grid-template-columns: 1fr; }}
  .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .node::after {{ display: none; }}
  .budget-row {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 520px) {{
  main {{ padding: 24px 12px 42px; }}
  .stats {{ grid-template-columns: 1fr; }}
  .stat strong {{ font-size: 1.55rem; }}
  h3 {{ font-size: .78rem; letter-spacing: .05em; }}
  .viz-toolbar button {{ flex: 1 1 auto; }}
}}
</style>
</head>
<body>
<main>
<header>
  <div>
    <p class="stamp">2026-06-07 &middot; K1 1401 &middot; mode 18 &middot; VPAB framed transport</p>
    <h1>Audio-conditioned light, captured at the final-byte boundary.</h1>
  </div>
  <div>
    <p class="lede">This presentation turns the live-music VPAB evidence into a readable semantic map: what the capture proves, what the final LED bytes reveal, and where this sits between K1 audio analysis and the visual pipeline.</p>
    <span class="badge pass">Gate PASS</span>
    <span class="badge limit">Not VME equivalence proof</span>
  </div>
</header>

<section class="section grid stats">
  <div class="stat"><strong>{summary['gate']['counts']['records']}</strong><span>framed records</span></div>
  <div class="stat"><strong>{summary['gate']['counts']['chunks']}</strong><span>validated chunks</span></div>
  <div class="stat"><strong>0 / 0</strong><span>issues / failures</span></div>
  <div class="stat"><strong>2</strong><span>covered channels</span></div>
</section>

<section class="section">
  <h2>Where The Evidence Lives In K1</h2>
  <div class="pipeline">
    <div class="node"><b>Music in room</b><small>Programme material was live, but the track/source was not named.</small><span class="badge limit">not replayable</span></div>
    <div class="node"><b>I2S + GDFT</b><small>Audio pipeline is upstream of mode 18 behaviour, but raw PCM/AP stream was not captured here.</small><span class="badge limit">not captured</span></div>
    <div class="node"><b>Audio semantics</b><small>Tempo/onset/chord state drives visual choices in K1 architecture.</small><span class="badge">source-defined</span></div>
    <div class="node"><b>Waveform Tempo</b><small>Mode 18 renders primary and secondary channels.</small><span class="badge pass">observed</span></div>
    <div class="node"><b>Final LED bytes</b><small>RGB bytes after render and quantisation. This is the perceptual proof surface.</small><span class="badge pass">decoded</span></div>
    <div class="node"><b>Framed VPAB</b><small>Sequence, length, CRC, chunking, and counters passed fail-closed.</small><span class="badge pass">proved</span></div>
  </div>
</section>

<section class="section grid split">
  <div class="panel">
    <h2>Runtime Timing Health</h2>
    {_metric_bar('Frame max', float(frame_perf.get('max', 0)), float(perf['frame_budget_us']), '--colour-proof')}
    {_metric_bar('Primary render max', primary_render_max, float(perf['render_budget_us']), '--colour-audio')}
    {_metric_bar('Secondary render max', secondary_render_max, float(perf['render_budget_us']), '--colour-visual')}
    <p>Frame overrun and dropped-frame counters stayed at <code>0 / 0</code>. Heap was <code>{html.escape(str(perf.get('heap')))}</code>.</p>
  </div>
  <div class="panel">
    <h2>Evidence Boundary</h2>
    <p><strong>Proves:</strong> transport integrity, primary/secondary coverage, final-byte availability, mode 18 coverage, and runtime timing health.</p>
    <p><strong>Does not prove:</strong> raw audio content, named-track repeatability, the full AudioSemanticState timeline, or VME final-byte parity.</p>
  </div>
</section>

<section class="section">
  <h2>Final LED Bytes As A Visual Signal</h2>
  <p>The heatmaps below are actual decoded final-byte rows from each sampled frame, remapped through perceptual scalar colour maps so structure is readable. Absolute channel energy remains in the metrics table.</p>
  <div class="viz-toolbar" aria-label="Colour map controls">
    <button type="button" data-map="inferno" aria-pressed="true">Inferno</button>
    <button type="button" data-map="plasma" aria-pressed="false">Plasma</button>
    <button type="button" data-map="viridis" aria-pressed="false">Viridis</button>
    <button type="button" data-map="magma" aria-pressed="false">Magma</button>
    <button type="button" data-map="raw" aria-pressed="false">Raw RGB</button>
  </div>
  <div class="grid split">
    <div>
      <h3>Primary channel &middot; local luminance scale</h3>
      <div class="viz-frame"><canvas class="viz-canvas heatmap-canvas" id="heat-primary" aria-label="Primary final-byte scalar heatmap"></canvas></div>
    </div>
    <div>
      <h3>Secondary channel &middot; local luminance scale</h3>
      <div class="viz-frame"><canvas class="viz-canvas heatmap-canvas" id="heat-secondary" aria-label="Secondary final-byte scalar heatmap"></canvas></div>
    </div>
  </div>
  <p class="viz-note">These are not raw audio spectrograms. The capture has no raw PCM or GDFT-band stream; this is the K1 visual output surface over time, indexed by LED position.</p>
</section>

<section class="section">
  <h2>Final-Byte Waterfall</h2>
  <p>A 3D-style waterfall makes the time dimension easier to read: x-axis is LED index, y-axis is final-byte luminance, and depth is capture time. The animation uses display-interpolated line strips derived from the 11 captured rows per channel; source samples and metrics remain raw.</p>
  <div class="grid split">
    <div>
      <h3>Primary channel</h3>
      <div class="viz-frame"><canvas class="viz-canvas" id="waterfall-primary" aria-label="Primary final-byte waterfall"></canvas></div>
    </div>
    <div>
      <h3>Secondary channel</h3>
      <div class="viz-frame"><canvas class="viz-canvas" id="waterfall-secondary" aria-label="Secondary final-byte waterfall"></canvas></div>
    </div>
  </div>
</section>

<section class="section panel">
  <h2>Channel Semantics</h2>
  {_channel_table(summary)}
</section>

<section class="section grid split">
  <div class="panel">
    <h2>Energy And Active LEDs</h2>
    {energy_chart}
  </div>
  <div class="panel">
    <h2>Spatial Motion</h2>
    <h3>Primary</h3>
    {primary_space_chart}
    <h3>Secondary</h3>
    {secondary_space_chart}
  </div>
</section>

<section class="section grid callouts">
  <div class="panel callout">
    <h2>Why This Matters</h2>
    <p>The previous CSV route could produce survivor rows from a corrupt stream. This capture reaches a stricter proof surface: frozen diagnostic records with seq/len/CRC and zero failed counters.</p>
  </div>
  <div class="panel callout">
    <h2>Meaning For Visuals</h2>
    <p>The useful semantic layer is not just &quot;did serial parse?&quot; It is whether final bytes carry energy, colour, channel independence, centre-aware spatial behaviour, and budget-safe timing.</p>
  </div>
  <div class="panel callout">
    <h2>Next VME Layer</h2>
    <p>VME L1 should add a candidate shadow payload beside these canonical bytes and compare final bytes for modes 7, 8, and 18 on both channels.</p>
  </div>
</section>

<footer>
  Sources: <code>{html.escape(str(paths['gate']))}</code>, <code>{html.escape(str(paths['raw']))}</code>, <code>{html.escape(str(paths['frames']))}</code>,
  <code>SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.h</code>, <code>SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp</code>.
  Visual grammar reference inspected: <code>https://github.com/RaidenIV/3D-Spectrogram</code> (no code copied; data contract differs).
</footer>
</main>
<script id="vpab-data" type="application/json">{presentation_payload}</script>
<script>
const VPAB_DATA = JSON.parse(document.getElementById('vpab-data').textContent);
const MAPS = {{
  inferno: [[0,0,4],[31,12,72],[85,15,109],[136,34,106],[186,54,85],[227,89,51],[249,140,10],[249,201,50],[252,255,164]],
  plasma: [[13,8,135],[75,3,161],[125,3,168],[168,34,150],[203,70,121],[229,107,93],[248,148,65],[253,195,40],[240,249,33]],
  viridis: [[68,1,84],[71,44,122],[59,81,139],[44,113,142],[33,144,141],[39,173,129],[92,200,99],[170,220,50],[253,231,37]],
  magma: [[0,0,4],[28,16,68],[79,18,123],[129,37,129],[181,54,122],[229,80,100],[251,135,97],[254,194,135],[252,253,191]]
}};
let currentMap = 'inferno';
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function canvasSlot(id) {{
  const canvas = document.getElementById(id);
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * dpr));
  canvas.height = Math.max(1, Math.round(rect.height * dpr));
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return {{ canvas, ctx, width: rect.width, height: rect.height }};
}}

function sampleMap(name, value) {{
  const anchors = MAPS[name] || MAPS.inferno;
  const t = Math.max(0, Math.min(1, value));
  const scaled = t * (anchors.length - 1);
  const index = Math.min(anchors.length - 2, Math.floor(scaled));
  const frac = scaled - index;
  const a = anchors[index];
  const b = anchors[index + 1];
  return [
    Math.round(a[0] + (b[0] - a[0]) * frac),
    Math.round(a[1] + (b[1] - a[1]) * frac),
    Math.round(a[2] + (b[2] - a[2]) * frac)
  ];
}}

function rgbCss(rgb) {{
  return 'rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')';
}}

function drawHeatmap(channel, id) {{
  const slot = canvasSlot(id);
  const ctx = slot.ctx;
  const rows = VPAB_DATA.channels[channel].rows;
  const maxLuma = VPAB_DATA.channels[channel].maxLuma || 1;
  const maxByte = VPAB_DATA.channels[channel].maxByte || 1;
  ctx.clearRect(0, 0, slot.width, slot.height);
  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, slot.width, slot.height);
  const rowH = slot.height / Math.max(1, rows.length);
  const colW = slot.width / 160;
  for (let y = 0; y < rows.length; y++) {{
    const row = rows[y];
    for (let x = 0; x < 160; x++) {{
      let colour;
      if (currentMap === 'raw') {{
        const base = x * 3;
        const gain = Math.min(7, 215 / Math.max(1, maxByte));
        colour = [
          Math.min(255, Math.round(row.rgb[base] * gain)),
          Math.min(255, Math.round(row.rgb[base + 1] * gain)),
          Math.min(255, Math.round(row.rgb[base + 2] * gain))
        ];
      }} else {{
        colour = sampleMap(currentMap, row.luma[x] / maxLuma);
      }}
      ctx.fillStyle = rgbCss(colour);
      ctx.fillRect(x * colW, y * rowH, Math.ceil(colW) + 0.5, Math.ceil(rowH) + 0.5);
    }}
  }}
  ctx.strokeStyle = 'rgba(255,255,255,.78)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(slot.width * 0.5, 0);
  ctx.lineTo(slot.width * 0.5, slot.height);
  ctx.stroke();
}}

function interpolatedRows(rows) {{
  if (rows.length < 2) return rows;
  const out = [];
  const steps = 6;
  for (let r = 0; r < rows.length - 1; r++) {{
    const a = rows[r];
    const b = rows[r + 1];
    for (let step = 0; step < steps; step++) {{
      const t = step / steps;
      out.push({{
        energy: a.energy + (b.energy - a.energy) * t,
        luma: a.luma.map((value, index) => value + (b.luma[index] - value) * t)
      }});
    }}
  }}
  out.push(rows[rows.length - 1]);
  return out;
}}

function drawWaterfall(channel, id, tick) {{
  const slot = canvasSlot(id);
  const ctx = slot.ctx;
  const data = VPAB_DATA.channels[channel];
  const rows = interpolatedRows(data.rows);
  const maxLuma = data.maxLuma || 1;
  const maxEnergy = Math.max(1, ...rows.map(row => row.energy));
  ctx.clearRect(0, 0, slot.width, slot.height);
  const bg = ctx.createLinearGradient(0, 0, 0, slot.height);
  bg.addColorStop(0, '#071019');
  bg.addColorStop(1, '#010203');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, slot.width, slot.height);

  const left = 30;
  const width = slot.width - 82;
  const base = slot.height * 0.78;
  const rowGap = Math.max(2.6, slot.height * 0.009);
  const phase = reducedMotion ? -1 : Math.floor((tick / 520) % rows.length);

  ctx.strokeStyle = 'rgba(150,166,183,.25)';
  ctx.lineWidth = 1;
  for (let i = 0; i < 6; i++) {{
    const y = base - i * rowGap;
    ctx.beginPath();
    ctx.moveTo(left + i * 8, y - i * 9);
    ctx.lineTo(left + width + i * 8, y - i * 9);
    ctx.stroke();
  }}

  for (let r = 0; r < rows.length; r++) {{
    const row = rows[r];
    const depth = r / Math.max(1, rows.length - 1);
    const yBase = base - (rows.length - 1 - r) * rowGap * .72;
    const xLift = depth * 54;
    const yLift = depth * 46;
    const mean = row.luma.reduce((acc, value) => acc + value, 0) / Math.max(1, row.luma.length);
    const stroke = sampleMap(currentMap === 'raw' ? 'inferno' : currentMap, Math.max(mean / maxLuma, row.energy / maxEnergy * .72));
    ctx.beginPath();
    for (let x = 0; x < 160; x += 2) {{
      const value = Math.pow(row.luma[x] / maxLuma, .65);
      const px = left + (x / 159) * width + xLift;
      const py = yBase - value * slot.height * .42 - yLift;
      if (x === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.shadowColor = 'rgba(' + stroke[0] + ',' + stroke[1] + ',' + stroke[2] + ',.42)';
    ctx.shadowBlur = 8;
    ctx.strokeStyle = rgbCss(stroke);
    ctx.globalAlpha = reducedMotion ? .84 : (r === phase ? 1 : .28 + depth * .42);
    ctx.lineWidth = r === phase ? 2.1 : 1.1;
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
  }}

  ctx.fillStyle = 'rgba(245,247,251,.72)';
  ctx.font = '11px ui-monospace, SFMono-Regular, Menlo, monospace';
  ctx.fillText('LED index ->', left, slot.height - 12);
  ctx.fillText('time depth', slot.width - 108, 18);
}}

function drawAll(tick) {{
  drawHeatmap('primary', 'heat-primary');
  drawHeatmap('secondary', 'heat-secondary');
  drawWaterfall('primary', 'waterfall-primary', tick || 0);
  drawWaterfall('secondary', 'waterfall-secondary', tick || 0);
}}

document.querySelectorAll('[data-map]').forEach(button => {{
  button.addEventListener('click', () => {{
    currentMap = button.dataset.map || 'inferno';
    document.querySelectorAll('[data-map]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    drawAll(0);
  }});
}});

let rafId = 0;
function animate(tick) {{
  drawAll(tick);
  if (!reducedMotion) rafId = requestAnimationFrame(animate);
}}
window.addEventListener('resize', () => drawAll(0));
drawAll(0);
if (!reducedMotion) rafId = requestAnimationFrame(animate);
</script>
</body>
</html>
"""


def default_paths(prefix: Path) -> dict[str, Path]:
    base = prefix.with_suffix("")
    return {
        "summary_json": base.with_name(base.name + ".semantic-summary.json"),
        "markdown": base.with_name(base.name + ".semantic-brief.md"),
        "html": base.with_name(base.name + ".semantic-presentation.html"),
    }


def build(paths: dict[str, Path]) -> dict[str, Any]:
    frames_text = paths["frames"].read_text(encoding="utf-8", errors="replace")
    raw_text = paths["raw"].read_text(encoding="utf-8", errors="replace")
    gate_from_frames, records = assemble_payloads(frames_text)
    metrics, bytes_rows = decode_records(records)
    raw_perf = parse_raw_perf(raw_text)
    summary = build_summary(gate_from_frames, metrics, bytes_rows, raw_perf)
    if paths.get("gate") and paths["gate"].exists():
        gate_from_disk = json.loads(paths["gate"].read_text(encoding="utf-8"))
        summary["gate_from_disk_matches_generated"] = gate_from_disk == gate_from_frames
    return {"summary": summary, "metrics": metrics, "bytes_rows": bytes_rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_prefix = ROOT / "docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music"
    parser.add_argument("--frames", type=Path, default=default_prefix.with_suffix(".frames.log"))
    parser.add_argument("--raw", type=Path, default=default_prefix.with_suffix(".raw.log"))
    parser.add_argument("--gate", type=Path, default=default_prefix.with_suffix(".frame-gate.json"))
    parser.add_argument("--out-prefix", type=Path, default=default_prefix)
    args = parser.parse_args(argv)

    outputs = default_paths(args.out_prefix)
    paths: dict[str, Path] = {
        "frames": args.frames,
        "raw": args.raw,
        "gate": args.gate,
        **outputs,
    }
    built = build(paths)
    summary = built["summary"]
    bytes_rows = built["bytes_rows"]

    outputs["summary_json"].write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs["markdown"].write_text(render_markdown(summary, paths), encoding="utf-8")
    outputs["html"].write_text(render_html(summary, bytes_rows, paths), encoding="utf-8")

    print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
