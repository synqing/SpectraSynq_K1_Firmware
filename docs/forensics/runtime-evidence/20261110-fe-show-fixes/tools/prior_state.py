#!/usr/bin/env python3
"""Deterministic start: the same prepared stream after two different prior LIVE states.
usage: prior_state.py <tree export> <out dir> [--profile fe]
Case music: 9.975 s of real music into the live microphone path, then the stream starts.
Case zero : 9.975 s of all-zero PCM, then the same stream at the same hop.
From the first hop of the stream on, both edges must be byte-identical. Modes 32 and 18."""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
# Stream scheduling helpers come from the K1-FE-SHOW lane's gate script (git-ignored _scratch).
sys.path.insert(0, "/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-emu")
import gates as g
tree, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
profile = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--profile" else "scenario"
out.mkdir(parents=True)
if not (tree / ".pio/libdeps").is_dir():
    (tree / ".pio").mkdir(exist_ok=True)
    shutil.copytree(g.DEFAULT_SRC / ".pio/libdeps", tree / ".pio/libdeps", symlinks=True)
PRE, MUS0, DUR = 9.975, 75.0, 20.025           # 1330 hops of prior live input, then 2670 hops of show
start_hop = round(PRE * 1e6) // g.HOP_US
th = g.total_hops_for(PRE + DUR)
m1 = g.read_frames(g.M1_STREAM)
raw, info = g.schedule(m1, [(g.us(PRE), g.us(MUS0), g.us(DUR))], th)
sched = out / "prior.rx"; sched.write_bytes(raw)
sc = json.loads((tree / "tools/esp_emulator/s3_music_regression.json").read_text())
sc["name"] = "fe-show-fixes-prior-live-state"
show = g.loreen_seg(MUS0, MUS0 + DUR, "show passage 75.000-95.025 s")
sc["assets"]["prior_music"] = {"kind": "concat", "qualification": "real_music", "origin": "prior live music then show passage",
                               "segments": [g.loreen_seg(56.0, 56.0 + PRE, "prior live music 56.000-65.975 s"), show]}
sc["assets"]["prior_zero"] = {"kind": "concat", "qualification": "diagnostic_composite", "origin": "prior silence then show passage",
                              "segments": [{"zeros_ms": int(PRE * 1000), "label": "prior all-zero PCM"}, show]}
cases = {}
for mode in (32, 18):
    sc["compositions"][f"prior_m{mode}"] = {"commands": [f"set_mode={mode}", f"secondary_mode={mode}", "secondary_enabled=true"],
                                            "note": f"both edges mode {mode}"}
    for kind in ("music", "zero"):
        cases[f"prior-{kind}-m{mode}"] = {
            "purpose": f"Prepared stream after prior live {kind}, mode {mode}.", "pcm": f"prior_{kind}",
            "epoch": {"policy": "declared", "us": 1000000}, "partial_hop": "zero_pad", "composition": f"prior_m{mode}",
            "capture": {"start_hop": start_hop - 40, "end_hop": start_hop + 1294, "every": 1},
            "rx_stream": {"schedule": str(sched), "sha256": hashlib.sha256(raw).hexdigest(), "note": "M1 stream from run 9.975 s"}}
sc["cases"].update(cases); sc["suites"]["prior"] = list(cases)
sc["host_checks"] = {"pytest": [], "builds": [], "requires_git": sc.get("host_checks", {}).get("requires_git", [])}
scen = tree / "tools/esp_emulator/prior_state_scenario.json"; scen.write_text(json.dumps(sc, indent=2) + "\n")
env = dict(os.environ); env.setdefault("K1_ESP_EMU", g.ESP_EMU)
cmd = [sys.executable, str(tree / "tools/esp_emulator/run.py"), "--profile", profile, "--scenario", str(scen), "--suite", "prior", "--output", str(out / "emu")]
rc = subprocess.run(cmd, cwd=tree, env=env, stdout=open(out / "emu-run.log", "w"), stderr=subprocess.STDOUT).returncode
print("run.py exit", rc, "stream starts at run hop", start_hop, info)
def frames(cid):
    rows = []
    for line in (out / "emu" / cid / "uart.txt").read_text(errors="replace").splitlines():
        if line.startswith("F,"):
            p = line.split(","); rows.append((p[4], p[5]))
    return rows
res = {}
for mode in (32, 18):
    a, b = frames(f"prior-music-m{mode}"), frames(f"prior-zero-m{mode}")
    n = min(len(a), len(b)); pre = 40
    d_pre = sum(1 for i in range(pre) if a[i] != b[i])
    d_a = [i for i in range(pre, n) if a[i][0] != b[i][0]]; d_b = [i for i in range(pre, n) if a[i][1] != b[i][1]]
    res[mode] = {"frames": n, "differ_in_40_hops_before_stream": d_pre, "edge_A_differ_after_start": len(d_a), "edge_B_differ_after_start": len(d_b),
                 "first_diff_after_start": (d_a + d_b and min(d_a + d_b) - pre)}
    print("mode", mode, res[mode])
(out / "prior_state.json").write_text(json.dumps(res, indent=2) + "\n")
