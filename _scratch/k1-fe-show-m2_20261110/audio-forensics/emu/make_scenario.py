#!/usr/bin/env python3
"""Write the loud-guard ON/OFF emulator scenario (af-emu lane, 10 Nov 2026).

Matrix: guard {on, off} x input level {fixture peak 4096 raw, room peak 250 raw} x mode {22, 32, 18},
plus one repeat (room, mode 32, guard on) as the determinism control.

Passage: Loreen (loreen_127) original 116.0-143.0 s = 27.0 s = 3600 hops. Hops 0-1599 (116.0-128.0 s,
12.0 s) are uncaptured preroll (tempo novelty window 10.24 s); hops 1600-3599 (128.0-143.0 s, 2000
frames, the trace capacity) are captured at every hop. 128-135 s is the loud chorus (2 s RMS ~12000 of
32768 decoded), 137-143 s the quiet section (RMS ~1500-2600), so the window holds a ~18 dB level drop.

Every case: set_mode=M, secondary_mode=M, secondary_enabled=true (both edges in mode M) and
sensitivity=2.7 (the Main RPL NVS value measured today; firmware default is 2.4). Guard OFF adds
k1_loud_guard=false at hop 0 (production parser, serial_menu.cpp:3611 -> serial_set_k1_loud_guard).
Guard ON sends nothing: it is the boot default (globals.h:128, k1_loud_guard_enabled = true).

Usage: make_scenario.py --export <export dir> [--suite-cases id,id,...]
Writes <export>/tools/esp_emulator/guard_ab_scenario.json and a copy next to this script.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODES = (22, 32, 18)
LEVELS = {"fix": ("ab_fixture", "fixture level: excerpt peak 4096 raw (the R3 fixture gain)"),
          "room": ("ab_room", "room level: excerpt peak 250 raw (device mic today: per-hop peak p95 ~190, max ~270)")}
PASS_START_MS = 60000          # loreen_src offset of 116.0 s (asset excerpt starts at 56.0 s)
PASS_END_MS = 87000            # 143.0 s
CAPTURE = {"start_hop": 1600, "end_hop": 3600, "every": 1}


def case_id(level: str, mode: int, guard: str) -> str:
    return f"{level}-m{mode}-{guard}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True, type=Path)
    ap.add_argument("--suite-cases", default="", help="comma list for suite 'pick' (default: none)")
    a = ap.parse_args()
    exp = a.export.resolve()
    sc = json.loads((exp / "tools/esp_emulator/s3_music_regression.json").read_text())
    sc["name"] = "k1-loud-guard-ab"
    sc["description"] = ("af-emu lane 10 Nov 2026: loud guard ON (boot default) vs OFF (k1_loud_guard=false) on "
                         "k1_main_rpl_emu at a6bad318, fixture level and room level, modes 22/32/18 on both edges, "
                         "sensitivity 2.7, Loreen 116-143 s (captured 128-143 s).")
    room = copy.deepcopy(sc["assets"]["loreen_src"])
    room["conversion"]["gain"] = {"peak": 250, "rule": "one uniform gain so the excerpt peak is 250 raw: the Main RPL "
                                  "microphone level measured today (per-hop raw peak p95 ~190, max ~270; clip point "
                                  "32767/(8*2.7) = 1517)"}
    room["origin"] = "loreen_127 at room level (af-emu guard A/B). " + room.get("origin", "")
    sc["assets"]["loreen_room"] = room
    for lvl, (aid, label) in LEVELS.items():
        src = "loreen_src" if lvl == "fix" else "loreen_room"
        sc["assets"][aid] = {"kind": "concat", "qualification": "real_music",
                             "segments": [{"asset": src, "from_ms": PASS_START_MS, "to_ms": PASS_END_MS,
                                           "label": f"original 116.0-143.0 s, {label}"}],
                             "origin": "af-emu guard A/B passage: 27.0 s = 3600 hops; 128-135 s loud chorus, "
                                       "137-143 s quiet section"}
    cases = {}
    for m in MODES:
        for g in ("on", "off"):
            cmds = [f"set_mode={m}", f"secondary_mode={m}", "secondary_enabled=true", "sensitivity=2.7"]
            if g == "off":
                cmds.append("k1_loud_guard=false")
            sc["compositions"][f"ab_m{m}_{g}"] = {
                "commands": cmds,
                "note": f"both edges mode {m}, sensitivity 2.7, loud guard {'OFF (runtime command)' if g == 'off' else 'ON (boot default, no command)'}"}
            for lvl, (aid, _) in LEVELS.items():
                cases[case_id(lvl, m, g)] = {
                    "purpose": f"Guard {g.upper()}, {lvl} level, mode {m} on both edges; Loreen 116-143 s, captured 128-143 s.",
                    "pcm": aid, "epoch": {"policy": "declared", "us": 1000000},
                    "capture": dict(CAPTURE), "composition": f"ab_m{m}_{g}", "trace_novelty": True}
    cases["room-m32-on-rep"] = dict(cases["room-m32-on"], purpose="Determinism control: fresh repeat of room-m32-on.")
    sc["cases"].update(cases)
    order = [case_id(l, m, g) for m in (32, 22, 18) for l in ("room", "fix") for g in ("on", "off")] + ["room-m32-on-rep"]
    sc["suites"]["guardab"] = order
    sc["suites"]["checkpoint"] = ["room-m32-on", "room-m32-off"]
    sc["suites"]["rest"] = [c for c in order if c not in sc["suites"]["checkpoint"]]
    if a.suite_cases:
        sc["suites"]["pick"] = [c.strip() for c in a.suite_cases.split(",") if c.strip()]
    sc["host_checks"] = {"pytest": ["tests/test_esp_emulator_seams_static.py"], "builds": [],
                         "requires_git": sc.get("host_checks", {}).get("requires_git", [])}
    out = exp / "tools/esp_emulator/guard_ab_scenario.json"
    out.write_text(json.dumps(sc, indent=2) + "\n")
    shutil.copy(out, HERE / "guard_ab_scenario.json")
    print(out)
    print("suites:", {k: v for k, v in sc["suites"].items() if k in ("guardab", "checkpoint", "rest", "pick")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
