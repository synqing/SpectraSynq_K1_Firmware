#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2025-2026 SpectraSynq
"""Registry -> BLE-MIDI control-map generator + parity oracle (Remoted Phase F).

WHY THIS EXISTS
---------------
The Remoted knob drives the K1 over BLE-MIDI by mapping each physical gesture to
a MIDI CC / NRPN / Program Change, which the K1 parses back into a
``control.set <path> <value>`` against its transport-agnostic facade. The map
from {control path} -> {MIDI message} must cover EXACTLY the K1 control surface
and must be *generated*, never hand-typed. A prior hand-transcription laundered
"68 controls / 21 modes" into a ratified ADR when the real surface is 71/22 ---
this module makes that error class impossible to repeat.

SOURCES OF TRUTH (parsed, not trusted-by-prose)
------------------------------------------------
1. ``docs/protocol/k1-ws-controls-registry.yaml`` -- the canonical SET and ORDER
   of control paths (the 71). Its md5 is recorded in the generated map; the gate
   regenerates from the live registry, so any registry edit without a regen FAILS.
2. ``SPECTRASYNQ_K1_FIRMWARE/control/k1_control_facade.cpp`` -- the per-control
   TYPE, derived from the helper used inside each path's ``apply()`` branch:
     parse_bool_value(...)            -> bool   (CC 7-bit, 0/127)
     needs_number_range(...,min,max)  -> float  (CC 14-bit, range from source)
     parse_index(v, N, ...)           -> enum   (mode -> Program Change; else CC 7-bit)
     needs_text / parse_* / apply_*   -> text   (NRPN long tail)

DETERMINISTIC ENCODING (collision-free bands, assigned by registry order)
-------------------------------------------------------------------------
  namespace -> MIDI channel:  primary=0 secondary=1 global=2
                              director/hooks=3 edge/scene=4 vp=5
  per channel, by type:
    mode (enum, path endswith '.mode')  -> Program Change
    float  -> 14-bit CC pair: msb in [1..31], lsb = msb+32  (CC0 reserved/bank)
    bool   -> 7-bit CC in [64..95]        value 0=off / 127=on
    enum   -> 7-bit CC in [96..119]       value = index
    text   -> NRPN param, sequential per channel from 0
  Bands never overlap; any band overflow is a hard error (no silent truncation).

This module is BOTH:
  * the generator  ( ``--write`` emits docs/protocol/k1-ble-midi-map.json )
  * the parity gate ( ``--gate`` : coverage + collision + committed==fresh )
  * a Gate-F-alpha oracle ( NAME / capture() / MUTATIONS ) so harness_selftest.py
    mutation-proves it has teeth on facade type/range/path changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Repo root = the ancestor that contains SPECTRASYNQ_K1_FIRMWARE (matches oracle_hostcompile).
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "SPECTRASYNQ_K1_FIRMWARE").is_dir())
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
REGISTRY_YAML = ROOT / "docs" / "protocol" / "k1-ws-controls-registry.yaml"
FACADE_REL = "control/k1_control_facade.cpp"
MAP_JSON = ROOT / "docs" / "protocol" / "k1-ble-midi-map.json"

NAME = "ble_midi_map"

# strcmp paths that intentionally have an apply() branch but are NOT registry
# controls (rejected aliases that route the user to the two-step calibration).
KNOWN_NON_REGISTRY_BRANCHES = {"calibration.noise.start", "start_noise_cal"}

NAMESPACE_CHANNEL = {
    "primary": 0,
    "secondary": 1,
    "global": 2,
    "director": 3,
    "hooks": 3,
    "edge": 4,
    "scene": 4,
    "vp": 5,
    "calibration": 6,  # tier c1 two-step (arm/confirm/status/clear) -- mapped for
                       # completeness; NOT knob-bound by default (destructive setup).
}

# Controllers RESERVED by the MIDI spec — never assign to ordinary controls:
# 0/32 bank-select, 6/38 data-entry, 96/97 data inc/dec, 98/99 NRPN, 100/101 RPN,
# 120-127 channel-mode. Our NRPN long tail uses 6/38/98/99, so a 14-bit CC landing
# on 6 (+lsb 38) would be ambiguous with NRPN data — the differential oracle caught
# exactly that (primary.incandescent_filter @ cc6/38 mis-decoded as primary.preset).
RESERVED_CC = {0, 32, 6, 38, 96, 97, 98, 99, 100, 101,
               120, 121, 122, 123, 124, 125, 126, 127}
# Band layout per channel (reserved controllers excluded from every band).
CC14_MSB_RANGE = [n for n in range(1, 32)
                  if n not in RESERVED_CC and (n + 32) not in RESERVED_CC]  # 30 floats max
CC7_BOOL_RANGE = [n for n in range(64, 96) if n not in RESERVED_CC]        # 32 toggles max
CC7_ENUM_RANGE = [n for n in range(102, 120) if n not in RESERVED_CC]      # 18 enums max


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_registry_controls(yaml_path: Path = REGISTRY_YAML):
    """Flat ordered list of control paths between 'controls:' and 'rejected:'.

    Hand-rolled (no yaml dep) so the gate runs in a bare CI image; the structure
    is a simple block sequence and this is the authoritative SET + ORDER.
    """
    controls = []
    in_controls = False
    for line in yaml_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("controls:"):
            in_controls = True
            continue
        if in_controls and re.match(r"^[A-Za-z_]", line):  # next top-level key
            break
        if in_controls:
            m = re.match(r"\s*-\s*(\S+)", line)
            if m:
                controls.append(m.group(1))
    return controls


def _branch_bodies(facade_src: str):
    """Map each strcmp(record.control,"X") branch -> the source slice for that
    branch (from its strcmp to the next branch's strcmp)."""
    markers = [(m.group(1), m.start())
               for m in re.finditer(r'strcmp\(record\.control,\s*"([^"]+)"\)', facade_src)]
    bodies = {}
    for i, (path, start) in enumerate(markers):
        end = markers[i + 1][1] if i + 1 < len(markers) else len(facade_src)
        bodies.setdefault(path, facade_src[start:end])
    return bodies


def _function_body(src: str, name: str) -> str:
    marker = re.search(rf"(?:bool|const char\*)\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", src)
    if not marker:
        raise ValueError(f"cannot find facade helper {name}()")
    start = marker.end()
    depth = 1
    i = start
    while i < len(src) and depth:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    if depth:
        raise ValueError(f"unterminated facade helper {name}()")
    return src[start:i - 1]


def _strcmp_values(body: str, arg_name: str) -> list[str]:
    values: list[str] = []
    for value in re.findall(rf'strcmp\({re.escape(arg_name)},\s*"([^"]+)"\)', body):
        if value not in values:
            values.append(value)
    return values


def _edge_mode_text_values(body: str) -> tuple[list[str], list[str]]:
    canonical: list[str] = []
    accepted: list[str] = []
    for cond in re.findall(r"if\s*\((.*?)\)\s*\{", body, re.S):
        values = re.findall(r'"([^"]+)"', cond)
        if not values:
            continue
        canonical.append(values[0])
        for value in values:
            if value not in accepted:
                accepted.append(value)
    return canonical, accepted


def _scene_text_values(body: str) -> tuple[list[str], list[str]]:
    canonical: list[str] = []
    accepted: list[str] = []
    for cond, ret in re.findall(r'if\s*\((.*?)\)\s*\{\s*return\s+"([^"]+)";\s*\}', body, re.S):
        if ret not in canonical:
            canonical.append(ret)
        for value in re.findall(r'"([^"]+)"', cond):
            if value not in accepted:
                accepted.append(value)
    return canonical, accepted


def _text_value_tables(facade_src: str) -> dict[str, dict[str, list[str]]]:
    """Derive exact NRPN text tables from the facade helpers.

    The knob and K1 decoder both consume these canonical values. Aliases remain
    visible as accepted_text_values for audit, but emission uses only the exact
    canonical text the facade accepts without normalisation drift.
    """
    preset_body = _function_body(facade_src, "apply_primary_preset")
    edge_body = _function_body(facade_src, "parse_edge_mode")
    scene_body = _function_body(facade_src, "normalise_scene_smart")
    vp_body = _function_body(facade_src, "parse_vp_profile")

    edge_values, edge_accepted = _edge_mode_text_values(edge_body)
    scene_values, scene_accepted = _scene_text_values(scene_body)
    preset_values = _strcmp_values(preset_body, "preset_name")
    vp_values = _strcmp_values(vp_body, "text")

    return {
        "primary.preset": {
            "text_values": preset_values,
            "accepted_text_values": preset_values,
        },
        "edge.mode": {
            "text_values": edge_values,
            "accepted_text_values": edge_accepted,
        },
        "scene.smart": {
            "text_values": scene_values,
            "accepted_text_values": scene_accepted,
        },
        "vp.profile": {
            "text_values": vp_values,
            "accepted_text_values": vp_values,
        },
        "calibration.noise.arm": {
            "text_values": [],
            "accepted_text_values": [],
        },
        "calibration.noise.confirm": {
            "text_values": [],
            "accepted_text_values": [],
        },
        "calibration.noise.status": {
            "text_values": [],
            "accepted_text_values": [],
        },
        "calibration.noise.clear": {
            "text_values": ["CONFIRM"],
            "accepted_text_values": ["CONFIRM"],
        },
    }


def _num_or_expr(token: str):
    """Numeric literal -> float; otherwise the source expression verbatim
    (e.g. ``float(NUM_FREQS)`` -> resolved on-device at runtime)."""
    t = token.strip()
    if re.fullmatch(r"[-+]?[\d.]+(?:[eE][-+]?\d+)?f?", t):
        return float(t.rstrip("fF"))
    return t


def classify(path: str, body: str) -> dict:
    """Derive {type, range/max} for a control from its apply() branch body.
    Raises if the branch uses no recognised helper (no silent default).

    Discriminator: value controls return ok_number() and parse a number/bool;
    command/status controls return ok_text() and parse no value."""
    if "parse_bool_value(" in body:
        return {"type": "bool"}
    mr = re.search(r'needs_number_range\(record,\s*&result,\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*"', body)
    if mr:
        lo, hi = _num_or_expr(mr.group(1)), _num_or_expr(mr.group(2))
        e = {"type": "float", "min": lo, "max": hi}
        if isinstance(lo, str) or isinstance(hi, str):
            e["range_symbolic"] = True   # bound resolved at runtime on the K1
        return e
    mi = re.search(r"parse_index\(record\.number_value,\s*([^,]+?),", body)
    if mi:
        max_expr = mi.group(1).strip()
        if path.endswith(".mode"):
            return {"type": "mode", "max_expr": max_expr}
        return {"type": "enum", "max_expr": max_expr}
    if ("needs_text(" in body or "parse_vp_profile(" in body or "parse_edge_mode(" in body
            or "apply_primary_preset(" in body or "apply_scene_smart(" in body):
        return {"type": "text"}
    if "needs_number(" in body:
        # number with no explicit range (e.g. count). Treat as float 0..1 default,
        # flagged so a reviewer notices rather than a silent guess shipping.
        return {"type": "float", "min": 0.0, "max": 1.0, "range_inferred": True}
    if "ok_text(" in body:
        # Command/status control (calibration two-step: arm/confirm/status/clear).
        # No numeric value -> long-tail NRPN trigger; not knob-bound by default.
        return {"type": "text", "command": True}
    raise ValueError(f"cannot classify control '{path}': no recognised helper in apply() branch")


def build_map(firmware_root: Path | None = None) -> dict:
    """Pure function of (registry, facade) -> the deterministic BLE-MIDI map."""
    firmware = Path(firmware_root) if firmware_root else FIRMWARE
    facade_src = (firmware / FACADE_REL).read_text(encoding="utf-8")
    controls = load_registry_controls()
    bodies = _branch_bodies(facade_src)
    text_tables = _text_value_tables(facade_src)

    # Parity check 1: bijection registry<->apply() branches.
    branch_paths = set(bodies) - KNOWN_NON_REGISTRY_BRANCHES
    reg_set = set(controls)
    missing = sorted(reg_set - branch_paths)        # registry path with no branch
    orphan = sorted(branch_paths - reg_set)         # branch with no registry entry
    if missing:
        raise ValueError(f"registry paths missing an apply() branch: {missing}")
    if orphan:
        raise ValueError(f"apply() branches not in registry (unexpected): {orphan}")

    # Per-channel band allocators.
    alloc = {ch: {"cc14": iter(CC14_MSB_RANGE), "bool": iter(CC7_BOOL_RANGE),
                  "enum": iter(CC7_ENUM_RANGE), "nrpn": 0} for ch in set(NAMESPACE_CHANNEL.values())}

    def take(ch, kind):
        try:
            return next(alloc[ch][kind])
        except StopIteration:
            raise ValueError(f"band '{kind}' overflow on channel {ch} -- widen the band layout")

    entries = []
    for path in controls:
        ns = path.split(".", 1)[0]
        if ns not in NAMESPACE_CHANNEL:
            raise ValueError(f"control '{path}' has unmapped namespace '{ns}'")
        ch = NAMESPACE_CHANNEL[ns]
        info = classify(path, bodies[path])
        e = {"path": path, "channel": ch, "type": info["type"]}
        if info["type"] == "mode":
            e.update({"midi": "pc", "max_expr": info["max_expr"],
                      "encode": "program = mode_index"})
        elif info["type"] == "float":
            msb = take(ch, "cc14")
            e.update({"midi": "cc14", "cc_msb": msb, "cc_lsb": msb + 32,
                      "min": info["min"], "max": info["max"],
                      "encode": "v14 = round((value-min)/(max-min)*16383)"})
            for flag in ("range_inferred", "range_symbolic"):
                if info.get(flag):
                    e[flag] = True
        elif info["type"] == "bool":
            e.update({"midi": "cc7", "cc": take(ch, "bool"), "encode": "0=off,127=on"})
        elif info["type"] == "enum":
            e.update({"midi": "cc7", "cc": take(ch, "enum"), "max_expr": info["max_expr"],
                      "encode": "value = index (clamped 0..127)"})
        elif info["type"] == "text":
            e.update({"midi": "nrpn", "nrpn_param": alloc[ch]["nrpn"],
                      "encode": "enumerated string / command long-tail"})
            table = text_tables.get(path)
            if table is not None:
                e.update(table)
            if info.get("command"):
                e["command"] = True
            if path.startswith("calibration.noise."):
                e["protected_apply"] = True
            alloc[ch]["nrpn"] += 1
        entries.append(e)

    # Parity check 2: no duplicate physical MIDI assignment.
    seen = set()
    for e in entries:
        keys = []
        if e["midi"] == "cc14":
            keys = [(e["channel"], "cc", e["cc_msb"]), (e["channel"], "cc", e["cc_lsb"])]
        elif e["midi"] == "cc7":
            keys = [(e["channel"], "cc", e["cc"])]
        elif e["midi"] == "nrpn":
            keys = [(e["channel"], "nrpn", e["nrpn_param"])]
        elif e["midi"] == "pc":
            keys = [(e["channel"], "pc", None)]
        for k in keys:
            if k in seen:
                raise ValueError(f"MIDI assignment collision at {k} (path {e['path']})")
            seen.add(k)

    return {
        "schema": "k1.ble-midi-map/1",
        "generated_by": "scripts/regression-harness/golden/oracle_ble_midi_map.py",
        "registry_version": "2026-06-09",
        "registry_md5": md5_of(REGISTRY_YAML),
        "control_count": len(entries),
        "channel_map": {k: NAMESPACE_CHANNEL[k] for k in NAMESPACE_CHANNEL},
        "entries": entries,
    }


def render_json(m: dict) -> str:
    return json.dumps(m, indent=2, sort_keys=False) + "\n"


# --- Gate-F-alpha oracle interface (harness_selftest.py) ---------------------

def capture(firmware_root: Path | None = None) -> str:
    """Deterministic JSONL representation of the map (the oracle output).
    A facade edit that changes any control's type/range/path-set changes this.

    A facade that no longer parses cleanly (e.g. a control path dropped from
    apply()) is itself a regression: we return a deterministic error sentinel so
    it diverges from the baseline rather than crashing the generic self-test."""
    try:
        m = build_map(firmware_root=firmware_root)
    except Exception as exc:  # noqa: BLE001 -- the error IS the divergent observation
        return json.dumps({
            "error": "MAP_BUILD_ERROR",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }, sort_keys=True)
    text_value_count = sum(len(e.get("text_values", [])) for e in m["entries"])
    protected_count = sum(1 for e in m["entries"] if e.get("protected_apply"))
    lines = [json.dumps({
        "control_count": m["control_count"],
        "registry_md5": m["registry_md5"],
        "text_value_count": text_value_count,
        "protected_apply_count": protected_count,
    }, sort_keys=True)]
    for e in m["entries"]:
        rec = {
            "path": e["path"],
            "type": e["type"],
            "channel": e["channel"],
            "midi": e["midi"],
        }
        for k in ("cc_msb", "cc_lsb", "cc", "nrpn_param", "min", "max", "max_expr"):
            if k in e:
                rec[k] = e[k]
        if e.get("text_values") is not None:
            rec["text_values"] = e.get("text_values", [])
            rec["accepted_text_values"] = e.get("accepted_text_values", [])
        if e.get("command"):
            rec["command"] = True
        if e.get("protected_apply"):
            rec["protected_apply"] = True
        lines.append(json.dumps(rec, sort_keys=True))
    return "\n".join(lines)


# Mutations target the FACADE (under FIRMWARE, copied by the self-test). Each
# MUST make capture() diverge -- proving the oracle is not blind to a real
# facade regression. (Registry-set drift is caught by the --gate md5 binding,
# a separate gate, since the registry lives outside the mutated FIRMWARE tree.)
MUTATIONS = [
    (r'needs_number_range\(record, &result, 0\.05f, 1\.0f, "Primary photons',
     r'needs_number_range(record, &result, 0.05f, 2.0f, "Primary photons',
     "float range widened (primary.photons max 1.0->2.0)"),
    (r'strcmp\(record\.control, "primary\.auto_color_shift"\)',
     r'strcmp(record.control, "primary.auto_color_shift_DROPPED")',
     "control path dropped from apply() (primary.auto_color_shift) -> missing-branch caught"),
    (r'parse_index\(record\.number_value, NUM_MODES - 1',
     r'parse_index(record.number_value, NUM_MODES - 2',
     "mode index range changed (NUM_MODES-1 -> NUM_MODES-2)"),
    (r'(if \(strcmp\(preset_name, )"classic"(\) == 0\) \{\n    CONFIG\.SQUARE_ITER = 1;\n    CONFIG\.INCANDESCENT_FILTER = 0\.0f;)',
     r'\1"classic_DROPPED"\2',
     "text value table changed (primary.preset classic removed)"),
]


# --- Parity gate -------------------------------------------------------------

def assert_parity() -> int:
    """Standalone gate: coverage + collision + committed-map == freshly-generated.
    Returns 0 on pass, 1 on fail; prints a one-line verdict per check."""
    ok = True

    def check(label, cond):
        nonlocal ok
        ok = ok and cond
        print(f"[{'PASS' if cond else 'FAIL'}] {label}")

    fresh = build_map()                       # raises on coverage/collision failure
    controls = load_registry_controls()
    check(f"registry control_count == 68 (got {len(controls)})", len(controls) == 68)
    check(f"map covers exactly the registry set ({fresh['control_count']} entries)",
          {e["path"] for e in fresh["entries"]} == set(controls))
    check("every control typed (no unclassified)",
          all(e["type"] in {"mode", "float", "bool", "enum", "text"} for e in fresh["entries"]))

    if MAP_JSON.exists():
        committed = MAP_JSON.read_text(encoding="utf-8")
        check("committed map == freshly generated (regenerate after registry/facade change)",
              committed == render_json(fresh))
        try:
            cm = json.loads(committed)
            live_md5 = md5_of(REGISTRY_YAML)
            check(f"committed registry_md5 == live registry md5 ({live_md5[:12]}...)",
                  cm.get("registry_md5") == live_md5)
        except json.JSONDecodeError:
            check("committed map is valid JSON", False)
    else:
        check(f"committed map exists at {MAP_JSON.relative_to(ROOT)}", False)

    print("\nBLE_MIDI_MAP_PARITY:",
          "PROVEN -- map covers registry, no collisions, in sync with registry+facade" if ok
          else "FAILED -- map drifted from registry/facade; regenerate with --write")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="(re)generate docs/protocol/k1-ble-midi-map.json")
    ap.add_argument("--gate", action="store_true", help="run the parity gate (CI)")
    ap.add_argument("--print", dest="show", action="store_true", help="print the capture() representation")
    args = ap.parse_args()

    if args.write:
        m = build_map()
        MAP_JSON.write_text(render_json(m), encoding="utf-8")
        print(f"wrote {MAP_JSON.relative_to(ROOT)} "
              f"({m['control_count']} controls, registry_md5={m['registry_md5'][:12]}...)")
        return 0
    if args.show:
        print(capture())
        return 0
    if args.gate:
        return assert_parity()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
