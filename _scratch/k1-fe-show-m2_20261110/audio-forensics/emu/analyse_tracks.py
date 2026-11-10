#!/usr/bin/env python3
"""AFE2 on five tracks, LED-level analysis (K1-FE-SHOW lead session 3, 11 Nov 2026). Host only.
Reads runs/tracks (make_scenario_tracks.py). Per track, mode and variant (off, on, g2):
  r          Pearson r between the 3 s mean of light output and section loudness (dB), over the 60 s capture
  slope      least-squares slope of 10*log10(3 s mean light) on section loudness: dB of light per dB of sound
  contrast   mean light in the loudest third of the capture / the quietest third (by section loudness)
  movement   mean frame-to-frame change in the loudest third
Section loudness = 3 s energy mean of the hop energy above 110 Hz of the exact samples the firmware processed.
Writes analysis-tracks/{tracks.json,tracks.md}.  Usage: analyse_tracks.py --export <src export>"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.signal import lfilter
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--export", type=Path, required=True); a = ap.parse_args()
sys.path.insert(0, str(a.export / "tools" / "esp_emulator")); sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "design"))
import analyse as A, emu_capture as ec, afe2_reference as ref
RUN = HERE / "runs" / "tracks"; FS = 65535.0; FPS = A.RATE / A.HOP
TR = [("loreen", "Loreen - My Heart Is Refusing Me", "pop"), ("stay", "Naeleck - Stay", "dense EDM"), ("rideit", "Regard - Ride It", "steady groove"), ("secret", "Ania Kanwan - The Secret Game", "film song"), ("mammoth", "Dimitri Vegas and Like Mike - Mammoth", "big room")]
st = json.loads((RUN / "result.json").read_text())["cases"]
def sm(x, n): return np.convolve(x, np.ones(n) / n, mode="same")
out, rows = {"cases": {}, "series": {}}, []
for key, name, kind in TR:
    for m in (22, 32):
        base = None
        for var in ("off", "on", "g2"):
            cid = f"{key}-m{m}-{var}"
            if st.get(cid, {}).get("status") != "PASS": continue
            c = A.load_case(ec, RUN / cid)
            pcm = A.blob_pcm(RUN / cid / "scenario-blob.bin").astype(np.float64)
            s0 = ref.Afe2(A.RATE); y = lfilter([s0.b0, s0.b1, s0.b2], [1.0, s0.a1, s0.a2], pcm); e = (y[: len(y) // A.HOP * A.HOP].reshape(-1, A.HOP) ** 2).mean(1)
            n3 = int(3 * FPS); L3all = 10 * np.log10(np.convolve(e, np.ones(n3) / n3, mode="same") + 1e-3); L3 = L3all[c["hops"]]
            br = c["A"].reshape(len(c["A"]), -1).mean(1) / FS; b3 = sm(br, 100)                       # 100 captured frames = 3 s at every 4th hop
            lo, hi = np.percentile(L3, [33.3, 66.7]); q, l = L3 <= lo, L3 >= hi
            mv = np.abs(np.diff(c["A"], axis=0)).mean(axis=(1, 2)) / FS; mvl = float(mv[l[1:]].mean())
            sl = float(np.polyfit(L3, 10 * np.log10(b3 + 1e-6), 1)[0])
            r = {"frames": c["n_frames"], "rejects": len(c["rejects"]), "r": float(np.corrcoef(b3, L3)[0, 1]), "slope_db_per_db": sl, "contrast": float(br[l].mean() / br[q].mean()),
                 "movement_loud": mvl, "mean_light": float(br.mean()), "loud_minus_quiet_db": float(L3[l].mean() - L3[q].mean())}
            if var == "off": base = r
            r["movement_kept"] = (mvl / base["movement_loud"]) if base else None
            out["cases"][cid] = r
            t = (c["hops"] + 1) / FPS
            d = lambda x: [round(float(v), 4) for v in np.asarray(x[: len(x) // 10 * 10]).reshape(-1, 10).mean(1)]
            out["series"][cid] = {"t": d(t), "light": d(br * 100), "L3": d(L3 - np.percentile(L3all, 95))}
            rows.append(f"| {name} | {m} | {var} | {r['loud_minus_quiet_db']:.1f} | {r['r']:+.2f} | {r['slope_db_per_db']:+.2f} | {r['contrast']:.2f} | {('%.0f %%' % (100 * r['movement_kept'])) if r['movement_kept'] else ''} |")
o = HERE / "analysis-tracks"; o.mkdir(exist_ok=True); (o / "tracks.json").write_text(json.dumps(out))
hdr = ["| track | mode | AFE2 | loud − quiet dB | r(light, loudness) | dB light per dB sound | contrast | movement kept |", "|---|---|---|---|---|---|---|---|"]
(o / "tracks.md").write_text("\n".join(hdr + rows) + "\n"); print("\n".join(hdr + rows)); print("status", {k: v.get("status") for k, v in st.items() if v.get("status") != "PASS"})
