#!/usr/bin/env python3
"""Chroma-gate probe (K1-FE-SHOW lead session 3, 10 Nov 2026): is the dark loud chorus in mode 22
caused by the chroma sparseness gate (VP_FIX_CHROMAGRAM_SPARSENESS, runtime command vp_chroma_gate)?
Room level, Loreen 116-143 s (captured 128-143 s), same as the guard A/B cases room-m22-on/off.
Cases: gate off (guard on), gate off + guard off, both for mode 22; gate off for mode 18. Suite: gate.
Usage: make_scenario_gate.py <export dir>"""
import copy, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
exp = Path(sys.argv[1]).resolve()
sc = json.loads((HERE / "guard_ab_scenario.json").read_text()); sc["name"] = "k1-chroma-gate-probe"
ids = []
for m, guard in ((22, "on"), (22, "off"), (18, "on")):
    comp = copy.deepcopy(sc["compositions"][f"ab_m{m}_{guard}"]); comp["commands"] = comp["commands"] + ["vp_chroma_gate=false"]
    comp["note"] += "; chroma sparseness gate OFF (vp_chroma_gate=false)"
    sc["compositions"][f"gate_m{m}_{guard}"] = comp
    cid = f"gateoff-m{m}-guard{guard}"
    sc["cases"][cid] = dict(copy.deepcopy(sc["cases"][f"room-m{m}-{guard}"]), composition=f"gate_m{m}_{guard}",
                            purpose=f"Chroma gate OFF, guard {guard.upper()}, room level, mode {m}; Loreen 116-143 s, captured 128-143 s.")
    ids.append(cid)
sc["suites"]["gate"] = ids
out = exp / "tools/esp_emulator/chroma_gate_scenario.json"; out.write_text(json.dumps(sc, indent=2) + "\n"); shutil.copy(out, HERE / "chroma_gate_scenario.json"); print(out, ids)
