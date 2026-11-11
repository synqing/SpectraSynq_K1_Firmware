#!/usr/bin/env python3
"""AFE2 stage 4 A/B scenario (K1-FE-SHOW lead session 5, 11 Nov 2026): one spectrum gain against the four-band AGC.
Real firmware, five tracks (make_scenario_tracks.py), each an 84 s passage ending 24 s after a breakdown returns:
24 s uncaptured preroll, 60 s captured every 4th hop (2,000 frames). Levels: m10 (excerpt peak 79 raw), room (250),
p10 (791). Modes 14 (Spectrum River), 21 (Dense Forge), 22 (Snapwave), 32 (Waveform Hybrid K1). Exposure on
(k1_afe=true) in every case, as on the bench build. Variants: agc (no k1_afe_spec command: the four-band AGC, so the
same case runs unchanged on fe/k1-afe2-s3), anc (k1_afe_spec=anchor), sec (k1_afe_spec=section).
Built with the per-hop probe record (env k1_main_rpl_emu_tempo_probe): G lines carry the stage-4 fields.
Suites: s4cal (5 tracks, room, mode 22, agc), s4sel (room, 4 modes, 3 variants), s4ident (room, 4 modes, agc),
s4lvl (m10 and p10, modes 14 and 22, agc + the variant named by S4_LVL_VAR, default sec).
Usage: make_scenario_tracks.py <export> first (it writes afe2_tracks_scenario.json and the inventory), then
       make_scenario_s4.py <export>   -> <export>/tools/esp_emulator/afe2_s4_scenario.json (copied beside this script).
Afterwards restore the export (handover §6): checkout-index the fixtures template, delete tools/esp_emulator/afe2_*scenario.json."""
import copy, json, os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
exp = Path(sys.argv[1]).resolve()
TR = ["loreen", "stay", "rideit", "secret", "mammoth"]
LEVELS = {"m10": 79, "room": 250, "p10": 791}
MODES = (14, 21, 22, 32)
VARS = {"agc": [], "anc": ["k1_afe_spec=anchor"], "sec": ["k1_afe_spec=section"]}
LVL_VAR = os.environ.get("S4_LVL_VAR", "sec")

sc = json.loads((exp / "tools/esp_emulator/afe2_tracks_scenario.json").read_text())
sc["name"] = "k1-afe2-s4-spectrum"
sc["profile"]["env"] = "k1_main_rpl_emu_tempo_probe"
sc["profile"]["adapter_flags"] = sorted(set(sc["profile"]["adapter_flags"]) | {"ENABLE_TEMPO_STREAM", "K1_EMU_TEMPO_PROBE"})
suites = {"s4cal": [], "s4sel": [], "s4ident": [], "s4lvl": []}
for key in TR:
    for lab, peak in LEVELS.items():
        src = copy.deepcopy(sc["assets"][f"trk_{key}_src"])
        src["conversion"] = copy.deepcopy(src["conversion"])
        src["conversion"]["gain"] = {"peak": peak, "rule": f"excerpt peak {peak} raw ({lab})"}
        src["origin"] = src["origin"].replace("room level", f"{lab} (peak {peak})")
        sc["assets"][f"s4_{key}_{lab}_src"] = src
        sc["assets"][f"s4_{key}_{lab}"] = {"kind": "concat", "qualification": "real_music", "origin": "AFE2-S4 spectrum probe",
                                         "segments": [{"asset": f"s4_{key}_{lab}_src", "from_ms": 0, "to_ms": 84000, "label": "music passage"}]}
        for m in MODES:
            for var, extra in VARS.items():
                comp = f"s4_m{m}_{var}"
                sc["compositions"][comp] = {"commands": [f"set_mode={m}", f"secondary_mode={m}", "secondary_enabled=true", "sensitivity=2.7",
                                                         "k1_afe=true"] + extra, "note": f"mode {m}, exposure on, spectrum {var}"}
                cid = f"s4-{key}-{lab}-m{m}-{var}"
                sc["cases"][cid] = {"purpose": f"{key} at {lab}, mode {m}, spectrum {var}; 84 s passage, last 60 s captured every 4th hop.",
                                    "pcm": f"s4_{key}_{lab}", "epoch": {"policy": "declared", "us": 1000000},
                                    "capture": {"start_hop": 3200, "end_hop": 11200, "every": 4}, "composition": comp, "trace_novelty": True}
                if lab == "room" and m == 22 and var == "agc":
                    suites["s4cal"].append(cid)
                if lab == "room":
                    suites["s4sel"].append(cid)
                    if var == "agc":
                        suites["s4ident"].append(cid)
                elif m in (14, 22) and var in ("agc", LVL_VAR):
                    suites["s4lvl"].append(cid)
sc["suites"].update(suites)
out = exp / "tools/esp_emulator/afe2_s4_scenario.json"
out.write_text(json.dumps(sc, indent=2) + "\n")
shutil.copy(out, HERE / "afe2_s4_scenario.json")
print({k: len(v) for k, v in suites.items()})
