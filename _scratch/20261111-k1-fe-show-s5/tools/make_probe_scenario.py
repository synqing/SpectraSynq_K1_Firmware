#!/usr/bin/env python3
"""T2 (session 5): copy of audio-forensics/emu/guard_ab_scenario.json that builds the emulator image with the
per-hop probe record (env k1_main_rpl_emu_tempo_probe: + ENABLE_TEMPO_STREAM, K1_EMU_TEMPO_PROBE) and adds
suite `hotprobe` (fix-m22-on, fix-m32-on, fix-m18-on) and `roomprobe` (room-m22-on, room-m32-on, room-m18-on).
usage: make_probe_scenario.py <export dir>   -> writes <export>/tools/esp_emulator/guard_probe_scenario.json
"""
import json, sys
from pathlib import Path

SRC = Path.home() / "SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/audio-forensics/emu/guard_ab_scenario.json"
x = Path(sys.argv[1])
d = json.loads(SRC.read_text())
d["name"] = d["name"] + "-probe"
d["profile"]["env"] = "k1_main_rpl_emu_tempo_probe"
d["profile"]["adapter_flags"] = sorted(set(d["profile"]["adapter_flags"]) | {"ENABLE_TEMPO_STREAM", "K1_EMU_TEMPO_PROBE"})
d["suites"]["hotprobe"] = ["fix-m22-on", "fix-m32-on", "fix-m18-on"]
d["suites"]["roomprobe"] = ["room-m22-on", "room-m32-on", "room-m18-on"]
out = x / "tools/esp_emulator/guard_probe_scenario.json"
out.write_text(json.dumps(d, indent=1))
print(out)
