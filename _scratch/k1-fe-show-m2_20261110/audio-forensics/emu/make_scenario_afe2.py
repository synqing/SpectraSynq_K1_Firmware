#!/usr/bin/env python3
"""AFE2 exposure, emulator A/B (K1-FE-SHOW lead session 3, 10 Nov 2026).
Room level (peak 250 raw), Loreen 128-155 s (captured 140-155 s: breakdown, then the final chorus).
Per mode 22 / 32 / 18: exposure off (must equal the a6bad318 captures runs/tail/tail-m*-on byte for
byte) and exposure on (:k1_afe=true). Suite: afe2.  Usage: make_scenario_afe2.py <export dir>"""
import copy, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
exp = Path(sys.argv[1]).resolve()
sc = json.loads((HERE / "guard_ab_tail_scenario.json").read_text()); sc["name"] = "k1-afe2-exposure-ab"
ids = []
for m in (22, 32, 18):
    for state in ("off", "on"):
        comp = copy.deepcopy(sc["compositions"][f"ab_m{m}_on"])
        comp["commands"] = comp["commands"] + [f"k1_afe={'true' if state == 'on' else 'false'}"]
        comp["note"] = f"both edges mode {m}, sensitivity 2.7, loud guard ON (boot default), AFE2 exposure {state.upper()}"
        sc["compositions"][f"afe_m{m}_{state}"] = comp
        cid = f"afe{state}-m{m}"
        sc["cases"][cid] = dict(copy.deepcopy(sc["cases"][f"tail-m{m}-on"]), composition=f"afe_m{m}_{state}",
                                purpose=f"AFE2 exposure {state.upper()}, room level, mode {m}; Loreen 128-155 s, captured 140-155 s.")
        ids.append(cid)
comp = copy.deepcopy(sc["compositions"]["afe_m22_on"]); comp["commands"] = comp["commands"] + ["k1_afe_level=true"]
comp["note"] += "; level path also scaled (k1_afe_level=true)"
sc["compositions"]["afe_m22_both"] = comp
sc["cases"]["afeboth-m22"] = dict(copy.deepcopy(sc["cases"]["afeon-m22"]), composition="afe_m22_both",
                                 purpose="AFE2 exposure on brightness AND on the level path, room level, mode 22.")
ids.append("afeboth-m22")
sc["suites"]["afe2"] = ids
out = exp / "tools/esp_emulator/afe2_scenario.json"; out.write_text(json.dumps(sc, indent=2) + "\n"); shutil.copy(out, HERE / "afe2_scenario.json"); print(out, ids)
