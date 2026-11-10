#!/usr/bin/env python3
"""AFE2 stage 2 (one silence test from the meter), emulator A/B (K1-FE-SHOW lead session 4, 11 Nov 2026).

Five tracks x three room levels (excerpt peak 79 / 250 / 791 raw = -10 / 0 / +10 dB about the measured
room level) x silence test old / new (:k1_afe_silence=false / true). Mode 22, exposure on (the bench default).
Each case: the 84 s five-track passage, then 12 s of digital silence, then 12 s of a room-noise MODEL
(Gaussian noise, 2.5 counts rms = the median quiet-room section level measured on the Main RPL, 11 Nov),
then the first 6 s of the passage again (music returns). Hops: music 0-11200, zeros 11200-12800,
room 12800-14400, music 14400-15200. The silence flag per hop comes from the novelty trace (N lines).
The room segment is a model, not a recording: no raw microphone recording of the quiet room exists.
Adds three local fixtures to the EXPORT's copy of the inventory (scratch only, never committed).
Usage: make_scenario_s2.py <export dir>   (run make_scenario_tracks.py on the same export first)"""
import copy
import json
import shutil
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
exp = Path(sys.argv[1]).resolve()
TR = ["loreen", "stay", "rideit", "secret", "mammoth"]
LEVELS = (("m10", 79), ("room", 250), ("p10", 791))
ROOM_RMS = 2.5

# Room-noise model: 14 s Gaussian at 12.8 kHz, written once beside this script.
room_wav = HERE / "room_model_12k8.wav"
rng = np.random.default_rng(20261111)
x = rng.standard_normal(14 * 12800) * 3000.0
x = np.clip(np.round(x), -32767, 32767).astype("<i2")
with wave.open(str(room_wav), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(12800); w.writeframes(x.tobytes())
room_peak = int(round(ROOM_RMS * float(np.abs(x).max()) / float(np.sqrt(np.mean(x.astype(float) ** 2)))))

invp = exp / "scripts/regression-harness/fixtures/k1_av_regression_fixtures.template.json"
inv = json.loads(invp.read_text())
if not any(f["id"] == "afe2_room_model" for f in inv["fixtures"]):
    inv["fixtures"].append({"id": "afe2_room_model", "path": str(room_wav), "start_ms": 0, "duration_ms": 14000, "warm_ms": 0,
                            "expected_bpm": None, "fixture_type": "synthetic_diagnostic", "purpose": "AFE2-S2 room-noise model (scratch export only)",
                            "run_mode": "production_smoke", "required": False, "status": "active", "tempo_gate": "product_feel_only"})
invp.write_text(json.dumps(inv, indent=2) + "\n")

sc = json.loads((exp / "tools/esp_emulator/afe2_tracks_scenario.json").read_text())
sc["name"] = "k1-afe2-s2-silence"
room_src = copy.deepcopy(sc["assets"]["trk_loreen_src"])
room_src.update({"fixture_id": "afe2_room_model", "excerpt": {"start_ms": 0, "duration_ms": 12000},
                 "qualification": "synthetic_diagnostic", "origin": f"room-noise model, Gaussian, {ROOM_RMS} counts rms (peak {room_peak})",
                 "note": "AFE2-S2 quiet-room model"})
room_src["conversion"] = copy.deepcopy(room_src["conversion"]); room_src["conversion"]["gain"] = {"peak": room_peak, "rule": f"peak {room_peak} gives {ROOM_RMS} counts rms"}
sc["assets"]["s2_room"] = room_src
ids = []
for key in TR:
    for lab, peak in LEVELS:
        src = copy.deepcopy(sc["assets"][f"trk_{key}_src"])
        src["conversion"] = copy.deepcopy(src["conversion"]); src["conversion"]["gain"] = {"peak": peak, "rule": f"excerpt peak {peak} raw ({lab})"}
        src["origin"] = src["origin"].replace("room level", f"{lab} (peak {peak})")
        sc["assets"][f"s2_{key}_{lab}_src"] = src
        sc["assets"][f"s2_{key}_{lab}"] = {"kind": "concat", "qualification": "diagnostic_composite", "origin": "AFE2-S2 silence probe", "segments": [
            {"asset": f"s2_{key}_{lab}_src", "from_ms": 0, "to_ms": 84000, "label": "music passage"},
            {"zeros_ms": 12000, "label": "declared digital silence: the music stops"},
            {"asset": "s2_room", "from_ms": 0, "to_ms": 12000, "label": "room-noise model"},
            {"asset": f"s2_{key}_{lab}_src", "from_ms": 72000, "to_ms": 78000, "label": "music returns"}]}
        for test in ("old", "new"):
            comp = f"s2_{test}"
            sc["compositions"][comp] = {"commands": ["set_mode=22", "secondary_mode=22", "secondary_enabled=true", "sensitivity=2.7",
                                                     "k1_afe=true", f"k1_afe_silence={'true' if test == 'new' else 'false'}"],
                                        "note": f"mode 22, exposure on, silence test {test}"}
            cid = f"s2-{key}-{lab}-{test}"
            sc["cases"][cid] = {"purpose": f"{key} at {lab}: music, stop, room model, music; silence test {test}.", "pcm": f"s2_{key}_{lab}",
                                "epoch": {"policy": "declared", "us": 1000000}, "capture": {"start_hop": 14400, "end_hop": 15200, "every": 8},
                                "composition": comp, "trace_novelty": True}
            ids.append(cid)
sc["suites"]["s2"] = ids
sc["suites"]["s2_probe"] = [i for i in ids if i.startswith("s2-loreen-room")]
out = exp / "tools/esp_emulator/afe2_s2_scenario.json"
out.write_text(json.dumps(sc, indent=2) + "\n")
shutil.copy(out, HERE / "afe2_s2_scenario.json")
print(len(ids), "cases; room peak", room_peak)
