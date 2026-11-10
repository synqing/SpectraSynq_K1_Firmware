#!/usr/bin/env python3
"""AFE2 on five tracks (K1-FE-SHOW lead session 3, 11 Nov 2026): real firmware, room level (excerpt peak 250 raw).
Each passage is 84 s ending 24 s after a breakdown returns to full: 24 s uncaptured preroll, then 60 s captured at
every 4th hop (2000 frames). Modes 22 and 32, exposure off and on; gamma 2 on the first track. Suite: tracks.
Adds two local fixtures to the EXPORT's copy of the inventory (scratch only, never committed).
Usage: make_scenario_tracks.py <export dir>"""
import copy, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; exp = Path(sys.argv[1]).resolve()
TR = [("loreen", "loreen_127", 148.2), ("stay", "dense_clipped_edm", 81.9), ("rideit", "acestep_steady_groove", 106.6), ("secret", "afe2_secret_game", 140.8), ("mammoth", "afe2_mammoth", 158.6)]
EXTRA = {"afe2_secret_game": "/Users/spectrasynq/Workspace_Management/Software/YT_Saver/Ania Kanwan - The Secret Game (Piosenka z filmu Ukryta Gra).mp3",
         "afe2_mammoth": "/Users/spectrasynq/Workspace_Management/Software/YT_Saver/Dimitri Vegas & Like Mike - Mammoth.mp3"}
invp = exp / "scripts/regression-harness/fixtures/k1_av_regression_fixtures.template.json"; inv = json.loads(invp.read_text())
for fid, path in EXTRA.items():
    if not any(f["id"] == fid for f in inv["fixtures"]):
        inv["fixtures"].append({"id": fid, "path": path, "start_ms": 0, "duration_ms": 90000, "warm_ms": 0, "expected_bpm": None, "fixture_type": "known_real_music",
                                "purpose": "AFE2 multi-track probe (scratch export only)", "run_mode": "production_smoke", "required": False, "status": "active", "tempo_gate": "product_feel_only"})
invp.write_text(json.dumps(inv, indent=2) + "\n")
sc = json.loads((HERE / "afe2_scenario.json").read_text()); sc["name"] = "k1-afe2-five-tracks"
base = sc["assets"]["loreen_room"]; ids = []
for key, fid, ret in TR:
    a = copy.deepcopy(base); a["fixture_id"] = fid; a.pop("source_sha256", None); a["excerpt"] = {"start_ms": int(round((ret - 60) * 1000)), "duration_ms": 84000}
    a["origin"] = f"{fid}: 84 s ending 24 s after the return at {ret} s; room level"; a["note"] = "AFE2 multi-track probe"
    sc["assets"][f"trk_{key}_src"] = a
    sc["assets"][f"trk_{key}"] = {"kind": "concat", "qualification": "real_music", "segments": [{"asset": f"trk_{key}_src", "from_ms": 0, "to_ms": 84000, "label": f"{fid} passage"}], "origin": "AFE2 multi-track probe"}
    for m in (22, 32):
        variants = [("off", ["k1_afe=false"]), ("on", ["k1_afe=true"])] + ([("g2", ["k1_afe=true", "k1_afe_gamma=2"])] if key == "loreen" else [])
        for lab, extra in variants:
            comp = f"trk_m{m}_{lab}"
            sc["compositions"][comp] = {"commands": [f"set_mode={m}", f"secondary_mode={m}", "secondary_enabled=true", "sensitivity=2.7"] + extra, "note": f"mode {m}, AFE2 {lab}"}
            cid = f"{key}-m{m}-{lab}"
            sc["cases"][cid] = {"purpose": f"{fid}, mode {m}, AFE2 {lab}; 84 s passage, last 60 s captured every 4th hop.", "pcm": f"trk_{key}", "epoch": {"policy": "declared", "us": 1000000},
                                "capture": {"start_hop": 3200, "end_hop": 11200, "every": 4}, "composition": comp, "trace_novelty": True}
            ids.append(cid)
sc["suites"]["tracks"] = ids; sc["suites"]["tracks_probe"] = ids[:1]
out = exp / "tools/esp_emulator/afe2_tracks_scenario.json"; out.write_text(json.dumps(sc, indent=2) + "\n"); shutil.copy(out, HERE / "afe2_tracks_scenario.json"); print(len(ids), ids[:4])
