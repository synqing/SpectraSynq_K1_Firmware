#!/usr/bin/env python3
"""Computes every figure's data for the technical explainer (K1-FE-SHOW lead, 11 Nov 2026). Host only.
Writes design/explainer_data.json and design/keo-*.png.
Usage: explainer_data.py --export <afe2 src export> --cache <decoded pcm cache>"""
import argparse, array, json, math, re, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent; AF = HERE.parent; EMU = AF / "emu"; LANED = AF.parent.parent / "k1-fe-show-m1_20261109" / "lane-d"
ap = argparse.ArgumentParser(); ap.add_argument("--export", type=Path, required=True); ap.add_argument("--cache", type=Path, required=True); a = ap.parse_args()
sys.path.insert(0, str(a.export / "tools" / "esp_emulator")); sys.path.insert(0, str(EMU)); sys.path.insert(0, str(HERE)); sys.path.insert(0, str(a.export / "tests"))
import analyse as A, emu_capture as ec, afe2_reference as ref, model_frontend as mf
import test_k1_afe2_native as T
RATE, HOP = 12800, 96; FPS = RATE / HOP
out = {}
r3 = lambda x: [round(float(v), 4) for v in x]

# ---- 1. step response of the compiled firmware module, and the old envelope on the same samples
prog = T._programme()
exe = a.cache / "k1_afe2_host"
subprocess.run(["c++", "-std=c++17", "-O2", f"-I{a.export / 'SPECTRASYNQ_K1_FIRMWARE' / 'audio'}", str(a.export / "tests" / "k1_afe2_host.cpp"),
                str(a.export / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_afe2.cpp"), "-o", str(exe)], check=True)
pcm = a.cache / "programme.s16le"; pcm.write_bytes(prog.tobytes())
rows = np.array([[float(v) for v in l.split()] for l in subprocess.run([str(exe), str(pcm), "96", "12800", "1.0", "0.25"], capture_output=True, text=True, check=True).stdout.splitlines()])
want = np.array(T._reference(prog))
E_old = mf.today_peak_scaled(np.frombuffer(prog.tobytes(), dtype="<i2").astype(np.float64))
k = 10; t = (np.arange(len(rows)) + 1) / FPS
out["step"] = {"t": r3(t[::k]), "how": r3(rows[::k, 0]), "sec_rms": r3(np.sqrt(rows[::k, 1])), "anc_rms": r3(np.sqrt(rows[::k, 2])), "fast": [int(v) for v in rows[::k, 3]],
               "old_env": r3(np.convolve(E_old, np.ones(40) / 40, mode="same")[::k]), "max_abs_diff_vs_reference": float(np.abs(rows[:, 0] - want).max()), "hops": int(len(rows)),
               "programme": [[s, amp] for s, amp in T.PROGRAMME]}

# ---- 2. measured level transfer on seven tracks: how much of a level change survives, by modulation frequency
lore = mf.decode(mf.TRACKS[next(iter(mf.TRACKS))], a.cache); kk = 250.0 / np.abs(lore[int(56 * RATE): int(155 * RATE)]).max()
nper = 8192; acc = {n: 0 for n in ("xx", "x_old", "x_new", "x_tot", "old", "new", "tot")}
for name, path in mf.TRACKS.items():
    raw = mf.decode(path, a.cache) * kk
    E = np.clip(mf.today_peak_scaled(raw), 1e-3, 1.0); p = mf.proposed(raw, E)
    x = p["L"]; ok = p["L3"] > p["gate"]; x, E, how = x[ok], E[ok], p["how_much"][ok]
    y_old = 20 * np.log10(E); y_new = 20 * np.log10(how); y_tot = y_old + y_new
    f, pxx = signal.welch(x, FPS, nperseg=nper, detrend="constant"); acc["xx"] = acc["xx"] + pxx
    for key, y in (("old", y_old), ("new", y_new), ("tot", y_tot)):
        _, pxy = signal.csd(x, y, FPS, nperseg=nper, detrend="constant"); _, pyy = signal.welch(y, FPS, nperseg=nper, detrend="constant")
        acc["x_" + key] = acc["x_" + key] + pxy; acc[key] = acc[key] + pyy
edges = np.logspace(math.log10(0.02), math.log10(30), 26); mt = {"f": [], "old": [], "new": [], "tot": [], "coh_old": [], "coh_new": []}
for lo, hi in zip(edges[:-1], edges[1:]):
    s = (f >= lo) & (f < hi)
    if not s.any(): continue
    mt["f"].append(round(float(np.sqrt(lo * hi)), 4))
    for key in ("old", "new", "tot"):
        mt[key].append(round(float(np.abs(acc["x_" + key][s].sum()) / acc["xx"][s].sum()), 4))
    for key in ("old", "new"):
        mt["coh_" + key].append(round(float(np.abs(acc["x_" + key][s].sum()) ** 2 / (acc["xx"][s].sum() * acc[key][s].sum())), 4))
out["transfer"] = mt

# ---- 3. high-pass response, coefficients, per-hop coefficients
st = ref.Afe2(RATE); b, aa = [st.b0, st.b1, st.b2], [1.0, st.a1, st.a2]
ff = np.logspace(math.log10(10), math.log10(4000), 80); _, h = signal.freqz(b, aa, worN=ff, fs=RATE)
dt = HOP / RATE
out["hpf"] = {"f": r3(ff), "db": r3(20 * np.log10(np.abs(h))), "coeffs": {"b0": st.b0, "b1": st.b1, "b2": st.b2, "a1": st.a1, "a2": st.a2},
              "at": {str(q): float(20 * np.log10(abs(signal.freqz(b, aa, worN=[q], fs=RATE)[1][0]))) for q in (28, 50, 80, 110, 220)}}
out["alphas"] = {n: 1 - math.exp(-dt / tau) for n, tau in (("S attack", ref.TAU_S_ATTACK), ("S release", ref.TAU_S_RELEASE), ("A up", ref.TAU_A_UP), ("A slow", ref.TAU_A_SLOW), ("A fast", ref.TAU_A_FAST))}

# ---- 4. anchor decay inside a 10 dB breakdown, for three slow time constants (reference code, one constant changed)
sens = {}
for tau in (20.0, 60.0, 120.0):
    ref.TAU_A_SLOW = tau; s2 = ref.Afe2(RATE); hw = []
    for i in range(int(150 * FPS)):
        tt = i / FPS; e = 1600.0 if tt < 30 else 160.0
        hw.append(s2.update(e, dt))
    sens[str(int(tau))] = r3(np.array(hw)[int(28 * FPS)::20])
ref.TAU_A_SLOW = 60.0
out["sens"] = {"t": r3((np.arange(int(28 * FPS), int(150 * FPS), 20) / FPS) - 30.0), "tau": sens}

# ---- 5. the old chain on the bench (Main RPL @ a6bad318, Captain's volume, mode 22)
old = []
for line in (LANED / "runs" / "R_volume_test" / "V0dB_ap.jsonl").read_text().splitlines():
    r = json.loads(line); s = r.get("line", "")
    if s.startswith("[AP]"):
        g = lambda key: float(re.search(r"\b" + key + r"=(-?[0-9.]+)", s).group(1))
        old.append((r["mono"], g("raw_i16_abs_peak"), g("peak_scaled"), g("gdft_trim"), g("agc_gain"), g("peak_pin"), g("silence"), g("raw_i16_rms")))
old = np.array(old); old[:, 0] -= old[0, 0]
out["bench_old"] = {"t": r3(old[:, 0]), "raw_peak_dbfs": r3(20 * np.log10(np.maximum(old[:, 1], 1) / 32768)), "peak_scaled": r3(old[:, 2]), "gdft_trim": r3(old[:, 3]),
                    "agc_gain_bass": r3(old[:, 4]), "peak_pin": r3(old[:, 5]), "silence": [int(v) for v in old[:, 6]]}
new = []
for line in (LANED / "runs" / "A_M1_m22_live_music_afe_on_m10dB" / "ap.jsonl").read_text().splitlines():
    r = json.loads(line); s = r.get("line", "")
    if s.startswith("[AP]"):
        g = lambda key: float(re.search(r"\b" + key + r"=(-?[0-9.]+)", s).group(1))
        new.append((r["mono"], g("how"), g("sec"), g("anc"), g("silence"), g("gdft_trim")))
new = np.array(new); new[:, 0] -= new[0, 0]
out["bench_new"] = {"t": r3(new[:, 0]), "how": r3(new[:, 1]), "sec": r3(new[:, 2]), "anc": r3(new[:, 3]), "silence": [int(v) for v in new[:, 4]], "gdft_trim": r3(new[:, 5])}

# ---- 6. emulator: light output and pixel-time pictures (real firmware, room level)
import matplotlib; matplotlib.use("Agg"); import matplotlib.image as mi
emu = {}
for m in (22, 32, 18):
    off, on = A.load_case(ec, EMU / "runs" / "afe2" / f"afeoff-m{m}"), A.load_case(ec, EMU / "runs" / "afe2" / f"afeon-m{m}")
    tt = 128.0 + (on["hops"] + 1) * HOP / RATE; d = lambda x: np.asarray(x[: len(x) // 10 * 10]).reshape(-1, 10).mean(1)
    br = lambda c: c["A"].reshape(len(c["A"]), -1).mean(1) / 65535 * 100
    emu[str(m)] = {"t": r3(d(tt)), "off": r3(d(br(off))), "on": r3(d(br(on))), "level": r3(d(off["peak"])), "rms": r3(d(on["rms"]))}
    for lab, c in (("off", off), ("on", on)):
        img = np.clip((c["A"] / 65535.0) ** (1 / 2.2), 0, 1)                      # frames x 160 x 3
        img = img[: len(img) // 2 * 2].reshape(-1, 2, 160, 3).mean(1).transpose(1, 0, 2)[::-1]
        mi.imsave(HERE / f"keo-m{m}-{lab}.png", np.repeat(img, 1, axis=0))
out["emu"] = emu
out["afe2"] = json.loads((EMU / "analysis-afe2" / "afe2.json").read_text())
model = json.loads((HERE / "model.json").read_text())
out["tracks"] = [{"name": n.split(" (")[0], "kind": n.split("(")[-1].rstrip(")"), "today": v["0"]["today"], "afe2": v["0"]["proposed"], "afe2_m10": v["-10"]["proposed"], "afe2_p10": v["10"]["proposed"]} for n, v in model["tracks"].items()]
out["model_validation"] = model.get("validation_vs_emulator_peak_scaled")
(HERE / "explainer_data.json").write_text(json.dumps(out)); print("ok", {k2: (len(v) if hasattr(v, "__len__") else v) for k2, v in out.items()})
print("transfer:", list(zip(mt["f"], mt["old"], mt["new"], mt["tot"]))[::3]); print("hpf at:", out["hpf"]["at"]); print("alphas:", out["alphas"]); print("step diff:", out["step"]["max_abs_diff_vs_reference"])
