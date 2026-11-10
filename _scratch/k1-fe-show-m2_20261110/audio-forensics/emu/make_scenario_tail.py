#!/usr/bin/env python3
"""Final-chorus extension of the loud-guard ON/OFF emulator A/B (K1-FE-SHOW lead, session 3, 10 Nov 2026).

The first matrix (make_scenario.py) captured 128-143 s, which ends before the passage where the bench
saw the guard's deepest cut (gdft_trim 0.34 at ~147-154 s). This adds, at ROOM level only (peak 250 raw):
passage original 128.0-155.0 s (3600 hops); hops 0-1599 preroll (128-140 s), captured 140.0-155.0 s
(breakdown 140-148 s, final chorus return 149-155 s). Modes 22/32/18, guard on/off. Suite name: tail.
Usage: make_scenario_tail.py <export dir>
"""
import copy, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
exp = Path(sys.argv[1]).resolve()
sc = json.loads((HERE / "guard_ab_scenario.json").read_text())
sc["name"] = "k1-loud-guard-ab-tail"
sc["assets"]["ab_room_tail"] = {"kind": "concat", "qualification": "real_music",
    "segments": [{"asset": "loreen_room", "from_ms": 72000, "to_ms": 99000,
                  "label": "original 128.0-155.0 s, room level (peak 250 raw)"}],
    "origin": "session-3 tail passage: 27.0 s = 3600 hops; breakdown 140-148 s, final chorus 149-155 s"}
ids = []
for m in (22, 32, 18):
    for g in ("on", "off"):
        cid = f"tail-m{m}-{g}"
        sc["cases"][cid] = dict(copy.deepcopy(sc["cases"][f"room-m{m}-{g}"]), pcm="ab_room_tail",
            purpose=f"Guard {g.upper()}, room level, mode {m} both edges; Loreen 128-155 s, captured 140-155 s.")
        ids.append(cid)
sc["suites"]["tail"] = ids
out = exp / "tools/esp_emulator/guard_ab_tail_scenario.json"
out.write_text(json.dumps(sc, indent=2) + "\n")
shutil.copy(out, HERE / "guard_ab_tail_scenario.json")
print(out, ids)
