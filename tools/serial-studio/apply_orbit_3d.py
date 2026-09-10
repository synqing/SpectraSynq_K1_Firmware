#!/usr/bin/env python3
"""Restore three Plot3D groups as tempo-phase orbits. Does not steal USB."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

SS = Path("/Users/spectrasynq/Serial-Studio")
sys.path.insert(0, str(SS / "tests" / "utils"))

from api_client import APIError, SerialStudioClient  # noqa: E402

HERE = Path(__file__).resolve().parent
PARSER = (HERE / "parsers" / "k1_ap_parser.js").read_text()
EXPORT_A = HERE / "K1-Dual-UART-Observability.ssproj"
LIVE = Path.home() / "Documents/Serial Studio/Projects/K1 Dual UART Observability.ssproj"
EXPORT_B = SS / "examples" / "K1 Dual UART" / "K1-Dual-Observability.ssproj"

PLOT3D = 6
BARPANEL = 90

# group uniqueId → (title, sourceId, z_index, z_title, keep uniqueIds)
ORBIT_GROUPS = {
    35: {
        "title": "Bench orbit (energy)",
        "sourceId": 0,
        "z_index": 11,
        "z_title": "Energy",
        "ids": (71, 72, 73),
    },
    39: {
        "title": "Main orbit (energy)",
        "sourceId": 1,
        "z_index": 11,
        "z_title": "Energy",
        "ids": (76, 77, 78),
    },
    44: {
        "title": "Bench orbit (conf)",
        "sourceId": 0,
        "z_index": 2,
        "z_title": "Beat conf",
        "ids": (86, 87, 88),
    },
}


def ds(
    dataset_id: int,
    group_id: int,
    unique_id: int,
    title: str,
    index: int,
    widget: str,
    source_id: int,
    plot_min: float,
    plot_max: float,
) -> dict:
    return {
        "datasetId": dataset_id,
        "displayFormat": "0d",
        "displayTickCount": 5,
        "fft": False,
        "fftMax": 0,
        "fftMin": 0,
        "fftSamples": 256,
        "fftSamplingRate": 133 if source_id == 0 else 4,
        "fftWindow": 5,
        "graph": False,
        "groupId": group_id,
        "index": index,
        "led": False,
        "ledHigh": 80,
        "log": False,
        "numericValue": 0,
        "plotMax": plot_max,
        "plotMin": plot_min,
        "sourceId": source_id,
        "title": title,
        "uniqueId": unique_id,
        "units": "",
        "value": "",
        "widget": widget,
        "widgetMax": plot_max,
        "widgetMin": plot_min,
        "xAxis": -2,
    }


def orbit_group(cfg_group: dict, spec: dict) -> dict:
    g = deepcopy(cfg_group)
    gid = int(g.get("groupId", g.get("uniqueId")))
    # groupId in datasets is the array index; keep whatever was serialized
    dataset_group_id = 0
    if g.get("datasets"):
        dataset_group_id = int(g["datasets"][0].get("groupId", 0))
    ox, oy, oz = spec["ids"]
    sid = spec["sourceId"]
    g["title"] = spec["title"]
    g["widget"] = "plot3d"
    g["sourceId"] = sid
    g["datasets"] = [
        ds(0, dataset_group_id, ox, "orbit_x", 23, "x", sid, -1, 1),
        ds(1, dataset_group_id, oy, "orbit_y", 24, "y", sid, -1, 1),
        ds(2, dataset_group_id, oz, spec["z_title"], spec["z_index"], "z", sid, 0, 1),
    ]
    return g


def ensure_orbit_on_multiplot(group: dict, source_id: int, unique_ids: tuple[int, int, int]) -> None:
    """Subscribe phase/orbit on the 2D group so Plot3D can duplicate those indices (EM Wave pattern)."""
    existing = {int(d.get("index") or -1): d for d in group.get("datasets") or []}
    specs = (
        (22, "phase", unique_ids[0], 0.0, 1.0),
        (23, "orbit_x", unique_ids[1], -1.0, 1.0),
        (24, "orbit_y", unique_ids[2], -1.0, 1.0),
    )
    gid = int(group.get("datasets", [{}])[0].get("groupId", 0)) if group.get("datasets") else 0
    for index, title, uid, pmin, pmax in specs:
        if index in existing:
            d = existing[index]
            d["title"] = title
            d["index"] = index
            d["graph"] = True
            d["fft"] = False
            d["led"] = False
            d["sourceId"] = source_id
            continue
        group.setdefault("datasets", []).append(
            ds(len(group.get("datasets") or []), gid, uid, title, index, "", source_id, pmin, pmax)
        )
        group["datasets"][-1]["graph"] = True


def patch_config(cfg: dict) -> dict:
    groups = cfg.get("groups") or []
    title_alias = {
        "Bench mix 0-1": 35,
        "Main mix 0-1": 39,
        "FPS": 44,
        "Bench orbit (energy)": 35,
        "Main orbit (energy)": 39,
        "Bench orbit (conf)": 44,
        "3D Plot": 35,
        "3D Plot (2)": 39,
        "3D Plot (3)": 44,
    }
    for i, g in enumerate(groups):
        uid = int(g.get("uniqueId") or 0)
        title = str(g.get("title") or "")
        if uid == 1 or title.startswith("K1 Bench"):
            ensure_orbit_on_multiplot(g, 0, (90, 91, 92))
            for d in g.get("datasets") or []:
                d["groupId"] = i
        if uid == 17 or title.startswith("K1 Main"):
            ensure_orbit_on_multiplot(g, 1, (93, 94, 95))
            for d in g.get("datasets") or []:
                d["groupId"] = i
        if uid not in ORBIT_GROUPS:
            alias = title_alias.get(title)
            if alias is not None:
                uid = alias
                g["uniqueId"] = uid
        if uid in ORBIT_GROUPS:
            patched = orbit_group(g, ORBIT_GROUPS[uid])
            for d in patched["datasets"]:
                d["groupId"] = i
                d["graph"] = True
            groups[i] = patched
    nxt = int(cfg.get("nextUniqueId") or 96)
    cfg["nextUniqueId"] = max(nxt, 96)

    for src in cfg.get("sources") or []:
        src["frameParserCode"] = PARSER

    ws = cfg.setdefault("widgetSettings", {})
    orbit_settings = {
        "anaglyphEnabled": False,
        "autoCenter": True,
        "interpolationEnabled": True,
        "orbitNavigation": True,
    }
    ws["6:0:-1"] = dict(orbit_settings)
    ws["6:1:-1"] = dict(orbit_settings)
    ws["6:2:-1"] = dict(orbit_settings)

    def retarget(obj):
        if isinstance(obj, dict):
            gid = obj.get("groupId")
            if gid in ORBIT_GROUPS and obj.get("widgetType") == BARPANEL:
                obj["widgetType"] = PLOT3D
            if obj.get("widgetType") == BARPANEL and obj.get("id") in ORBIT_GROUPS:
                obj["widgetType"] = PLOT3D
            for v in obj.values():
                retarget(v)
        elif isinstance(obj, list):
            for v in obj:
                retarget(v)

    retarget(cfg.get("workspaces"))
    # layout geometries: widgetType 90 tiles that were the mix/FPS bars
    layouts = [k for k in ws if str(k).startswith("layout:")]
    for key in layouts:
        geos = (((ws.get(key) or {}).get("data") or {}).get("geometries")) or []
        plot3d_rel = 0
        for geo in geos:
            if geo.get("widgetType") == BARPANEL:
                geo["widgetType"] = PLOT3D
                geo["relativeIndex"] = plot3d_rel
                plot3d_rel += 1

    # Overview widgetRefs relativeIndex among Plot3D widgets
    for workspace in cfg.get("workspaces") or []:
        plot3d_i = 0
        for ref in workspace.get("widgetRefs") or []:
            if ref.get("groupId") in ORBIT_GROUPS:
                ref["widgetType"] = PLOT3D
                ref["relativeIndex"] = plot3d_i
                plot3d_i += 1

    return cfg


def cmd(c: SerialStudioClient, name: str, params=None):
    try:
        return c.command(name, params)
    except APIError as e:
        print(f"ERR {name}: {e.code}: {e.message}")
        return {"_error": e.code, "_message": e.message}


def main() -> int:
    if "SCHEMA = 1.2" not in PARSER:
        print("parser is not v1.2")
        return 1

    c = SerialStudioClient(timeout=30)
    c.connect()
    print("API ok")

    st = cmd(c, "io.getStatus")
    print("io.getStatus", {k: st.get(k) for k in ("isConnected", "connected", "bus") if isinstance(st, dict)})

    exp = cmd(c, "project.exportJson")
    cfg = exp.get("config") if isinstance(exp, dict) else None
    if not cfg:
        print("exportJson failed", exp)
        return 1

    before = [(g.get("uniqueId"), g.get("title"), g.get("widget")) for g in cfg.get("groups") or []]
    print("before", before)

    cfg = patch_config(cfg)

    after = [(g.get("uniqueId"), g.get("title"), g.get("widget")) for g in cfg.get("groups") or []]
    print("after", after)

    for src in cfg.get("sources") or []:
        code = src.get("frameParserCode") or ""
        print(f"source {src.get('sourceId')} parser SCHEMA", "1.2" if "SCHEMA = 1.2" in code else "MISSING", "len", len(code))

    load = cmd(c, "project.loadJson", {"config": cfg})
    print("loadJson", load if not isinstance(load, dict) or load.get("_error") else "ok")
    if isinstance(load, dict) and load.get("_error"):
        return 1

    act = cmd(c, "project.activate")
    print("activate", act if not isinstance(act, dict) or act.get("_error") else "ok")

    saved = cmd(c, "project.save", {"filePath": str(LIVE)})
    print("save", saved if not isinstance(saved, dict) or saved.get("_error") else "ok")

    listed = cmd(c, "project.group.list")
    groups = listed.get("groups") if isinstance(listed, dict) else None
    if not groups:
        print("group.list failed", listed)
        return 1
    for g in groups:
        title = g.get("title")
        widget = g.get("widget")
        uid = g.get("uniqueId")
        ds_sum = g.get("datasetSummary") or []
        axes = [(d.get("title"), d.get("widget"), d.get("index"), d.get("sourceId")) for d in ds_sum]
        print(f"live group uid={uid} widget={widget} title={title} datasets={axes}")

    text = json.dumps(cfg, indent=4)
    for path in (EXPORT_A, LIVE, EXPORT_B):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            print(f"wrote {path} ({path.stat().st_size} bytes)")
        except OSError as e:
            print(f"skip write {path}: {e}")

    st2 = cmd(c, "io.getStatus")
    print("uart after", {k: st2.get(k) for k in ("isConnected", "connected") if isinstance(st2, dict)})
    c.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
