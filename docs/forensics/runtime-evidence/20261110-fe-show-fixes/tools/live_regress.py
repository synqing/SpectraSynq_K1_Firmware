#!/usr/bin/env python3
"""Live (no prepared stream) emulator regression, modes 32 and 18, both edges.
usage: live_regress.py <tree> <out-dir> [--profile fe]
Runs the tree's own tools/esp_emulator/run.py on a two-case scenario derived from its own
s3_music_regression.json (music_chorus PCM), then prints per-case, per-edge sha256 of the native frames."""
import hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
tree, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
profile = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--profile" else "scenario"
ESP_EMU = "/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/tools/esp-emu-pin/bin/esp-emu"
if not (tree / ".pio/libdeps").is_dir():
    (tree / ".pio").mkdir(exist_ok=True)
    shutil.copytree("/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-emu/src-ed0aa984/.pio/libdeps",
                    tree / ".pio/libdeps", symlinks=True)
sc = json.loads((tree / "tools/esp_emulator/s3_music_regression.json").read_text())
sc["name"] = "fe-show-fixes-live-regression"
cases = {}
for mode in (32, 18):
    sc["compositions"][f"live_m{mode}"] = {"commands": [f"set_mode={mode}", f"secondary_mode={mode}", "secondary_enabled=true"],
                                           "note": f"both edges mode {mode}, live microphone only"}
    c = dict(sc["cases"]["music-a"])
    c["composition"] = f"live_m{mode}"
    c["purpose"] = f"Live regression: music_chorus on mode {mode}, both edges, no prepared stream."
    cases[f"live-m{mode}"] = c
sc["cases"].update(cases)
sc["suites"]["live"] = list(cases)
sc["host_checks"] = {"pytest": [], "builds": [], "requires_git": sc.get("host_checks", {}).get("requires_git", [])}
scen = tree / "tools/esp_emulator/live_regress_scenario.json"
scen.write_text(json.dumps(sc, indent=2) + "\n")
env = dict(os.environ); env.setdefault("K1_ESP_EMU", ESP_EMU)
cmd = [sys.executable, str(tree / "tools/esp_emulator/run.py"), "--scenario", str(scen), "--suite", "live", "--output", str(out)]
if profile != "scenario":
    cmd[2:2] = ["--profile", profile]
rc = subprocess.run(cmd, cwd=tree, env=env, stdout=open(str(out) + ".log", "w"), stderr=subprocess.STDOUT).returncode
print("run.py exit", rc)
for cid in cases:
    uart = (out / cid / "uart.txt").read_text(errors="replace")
    a, b, n = hashlib.sha256(), hashlib.sha256(), 0
    for line in uart.splitlines():
        if line.startswith("F,"):
            p = line.split(",")
            a.update(p[4].encode()); b.update(p[5].encode() if len(p) > 5 else b""); n += 1
    print(cid, "frames", n, "A", a.hexdigest(), "B", b.hexdigest())
