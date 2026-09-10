#!/usr/bin/env python3
"""Patch the live Serial Studio K1 project: clocks, transforms, workspaces, recording."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SS = Path("/Users/spectrasynq/Serial-Studio")
sys.path.insert(0, str(SS / "tests" / "utils"))

from api_client import APIError, SerialStudioClient  # noqa: E402

HERE = Path(__file__).resolve().parent
PARSER = (HERE / "parsers" / "k1_ap_parser.js").read_text()
EXPORT_A = HERE / "K1-Dual-UART-Observability.ssproj"
EXPORT_B = SS / "examples" / "K1 Dual UART" / "K1-Dual-Observability.ssproj"

BENCH = "K1 Bench B489A500"
MAIN = "K1 Main RPL 9087A500"

CLOCK_FIELDS = [
    (16, "device_ms", "device_ms", "ms"),
    (17, "frame_ms", "frame_ms", "ms"),
    (18, "host_parse_seq", "host_parse_seq", ""),
    (19, "event_tid", "event_tid", ""),
    (20, "record_kind", "record_kind", ""),
    (21, "update_mask", "update_mask", ""),
]

DT_JS = """\
var prev = NaN;
function transform(value) {
  var dt = (isFinite(prev) && isFinite(value)) ? (value - prev) : 0;
  prev = value;
  if (dt < 0)
    dt = 0;
  return dt;
}
"""

SKEW_JS = """\
var t0Host;
var t0Dev;
function transform(value, info) {
  if (value === undefined || value === null || !isFinite(value))
    return 0;
  if (info === undefined || info.timestampMs === undefined)
    return 0;
  if (t0Host === undefined) {
    t0Host = info.timestampMs;
    t0Dev = value;
    return 0;
  }
  return (info.timestampMs - t0Host) - (value - t0Dev);
}
"""

RESIDUAL_JS = """\
var t0Host;
var t0Dev;
var baseline;
function transform(value, info) {
  if (value === undefined || value === null || !isFinite(value))
    return 0;
  if (info === undefined || info.timestampMs === undefined)
    return 0;
  if (t0Host === undefined) {
    t0Host = info.timestampMs;
    t0Dev = value;
    baseline = 0;
    return 0;
  }
  var skew = (info.timestampMs - t0Host) - (value - t0Dev);
  if (baseline === undefined || baseline === 0)
    baseline = skew;
  return skew - baseline;
}
"""


def cmd(c: SerialStudioClient, name: str, params=None):
    try:
        return c.command(name, params)
    except APIError as e:
        print(f"ERR {name}: {e.code}: {e.message}")
        return {"_error": e.code, "_message": e.message}


def groups_by_title(c: SerialStudioClient) -> dict:
    listed = c.command("project.group.list")["groups"]
    out = {}
    for i, g in enumerate(listed):
        g = dict(g)
        g["_pos"] = i
        out[g["title"]] = g
    return out


def ensure_clock_datasets(c: SerialStudioClient, pos: int, source_id: int, prefix: str) -> None:
    listed = c.command("project.group.list")["groups"][pos]
    titles = {d["title"]: d for d in listed.get("datasetSummary", [])}
    next_index = max((int(d.get("index") or 0) for d in listed.get("datasetSummary", [])), default=0) + 1

    for index, alias, title, units in CLOCK_FIELDS:
        existing = titles.get(title)
        if existing is None:
            cmd(
                c,
                "project.dataset.add",
                {"groupId": pos, "options": 1},
            )
            listed = c.command("project.group.list")["groups"][pos]
            ds_id = listed["datasetCount"] - 1
            idx = next_index
            next_index += 1
        else:
            ds_id = existing["datasetId"]
            idx = existing.get("index") or index
        cmd(
            c,
            "project.dataset.update",
            {
                "groupId": pos,
                "datasetId": ds_id,
                "title": title,
                "alias": f"{prefix}_{alias}",
                "index": idx if idx else index,
                "sourceId": source_id,
                "units": units,
                "graph": True,
                "fft": False,
                "fftSamplingRate": 133 if source_id == 0 else 4,
            },
        )


def add_virtual(c: SerialStudioClient, pos: int, source_id: int, prefix: str, title: str, alias: str, code: str) -> None:
    listed = c.command("project.group.list")["groups"][pos]
    titles = {d["title"]: d for d in listed.get("datasetSummary", [])}
    if title in titles:
        ds_id = titles[title]["datasetId"]
    else:
        cmd(c, "project.dataset.add", {"groupId": pos, "options": 1})
        listed = c.command("project.group.list")["groups"][pos]
        ds_id = listed["datasetCount"] - 1
    cmd(
        c,
        "project.dataset.update",
        {
            "groupId": pos,
            "datasetId": ds_id,
            "title": title,
            "alias": f"{prefix}_{alias}",
            "sourceId": source_id,
            "graph": True,
            "fft": False,
            "virtual": True,
            "transformCode": code,
            "transformLanguage": 0,
        },
    )
    cmd(c, "project.dataset.setVirtual", {"groupId": pos, "datasetId": ds_id, "virtual": True})
    cmd(
        c,
        "project.dataset.setTransformCode",
        {"groupId": pos, "datasetId": ds_id, "code": code, "language": 0},
    )


def pin_fft_rates(c: SerialStudioClient, pos: int, rate: int) -> None:
    listed = c.command("project.group.list")["groups"][pos]
    for d in listed.get("datasetSummary", []):
        cmd(
            c,
            "project.dataset.update",
            {
                "groupId": pos,
                "datasetId": d["datasetId"],
                "fft": False,
                "fftSamplingRate": rate,
            },
        )


def ensure_workspaces(c: SerialStudioClient, bench_uid: int, main_uid: int) -> None:
    cmd(c, "project.workspace.setCustomizeMode", {"enabled": True})
    time.sleep(0.2)
    existing = {w["title"]: w for w in cmd(c, "project.workspace.list").get("workspaces", [])}
    wanted = [
        ("Timing", "multiplot", bench_uid),
        ("Audio/AP", "multiplot", bench_uid),
        ("Renderer", "multiplot", bench_uid),
        ("Dual-device sync", "multiplot", main_uid),
        ("Experiment state", "datagrid", bench_uid),
    ]
    for title, wtype, uid in wanted:
        if title not in existing:
            cmd(c, "project.workspace.add", {"title": title})
            time.sleep(0.05)
    listed = cmd(c, "project.workspace.list").get("workspaces", [])
    by_title = {w["title"]: w for w in listed}
    for title, wtype, uid in wanted:
        ws = by_title.get(title)
        if not ws:
            continue
        r = cmd(
            c,
            "project.workspace.addWidget",
            {"workspaceId": ws["id"], "groupId": uid, "widgetType": wtype},
        )
        print(f"workspace {title}: {r}")


def export_project(c: SerialStudioClient) -> None:
    exp = cmd(c, "project.exportJson")
    cfg = exp.get("config") if isinstance(exp, dict) else None
    if not cfg:
        print("export failed", exp)
        return
    text = json.dumps(cfg, indent=2)
    for path in (EXPORT_A, EXPORT_B):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path} ({path.stat().st_size} bytes)")


def main() -> int:
    c = SerialStudioClient(timeout=10)
    c.connect()
    print("API ok")

    st = cmd(c, "io.getStatus")
    if st.get("isConnected"):
        cmd(c, "io.disconnect")
        time.sleep(0.4)

    cmd(c, "dashboard.setOperationMode", {"mode": 0})
    groups = groups_by_title(c)
    if BENCH not in groups or MAIN not in groups:
        print("missing K1 groups", list(groups))
        return 1

    bench = groups[BENCH]
    main = groups[MAIN]

    c.set_frame_parser_code(PARSER, language=0, source_id=0)
    c.set_frame_parser_code(PARSER, language=0, source_id=1)

    ensure_clock_datasets(c, bench["_pos"], 0, "s0")
    ensure_clock_datasets(c, main["_pos"], 1, "s1")
    add_virtual(c, bench["_pos"], 0, "s0", "frame_dt_ms", "frame_dt_ms", DT_JS)
    add_virtual(c, main["_pos"], 1, "s1", "frame_dt_ms", "frame_dt_ms", DT_JS)
    add_virtual(c, bench["_pos"], 0, "s0", "host_device_skew_ms", "host_device_skew_ms", SKEW_JS)
    add_virtual(c, main["_pos"], 1, "s1", "host_device_skew_ms", "host_device_skew_ms", SKEW_JS)
    add_virtual(c, bench["_pos"], 0, "s0", "transport_residual_ms", "transport_residual_ms", RESIDUAL_JS)
    add_virtual(c, main["_pos"], 1, "s1", "transport_residual_ms", "transport_residual_ms", RESIDUAL_JS)

    pin_fft_rates(c, bench["_pos"], 133)
    pin_fft_rates(c, main["_pos"], 4)

    groups = groups_by_title(c)
    ensure_workspaces(c, groups[BENCH]["uniqueId"], groups[MAIN]["uniqueId"])

    csv = cmd(c, "csvExport.getStatus")
    print("csv status", csv)
    cmd(c, "csvExport.setEnabled", {"enabled": True})
    rec = cmd(c, "sessions.setExportEnabled", {"enabled": True})
    print("historian", rec, cmd(c, "sessions.getStatus"))
    print("db", cmd(c, "sessions.getDbPath"))

    opened = cmd(c, "io.connect")
    print("connect", opened)
    time.sleep(1.2)
    print("io", cmd(c, "io.getStatus").get("_summary"))
    print("dash", cmd(c, "dashboard.getStatus").get("_summary"))

    export_project(c)
    (SS / "examples" / "K1 Dual UART" / "k1_ap_parser.js").write_text(PARSER)
    c.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
