#!/usr/bin/env python3
"""Front-end design model (K1-FE-SHOW lead, session 3, 10 Nov 2026). Host only. A MODEL, not firmware.

Question: what "how loud is it" signal do the effects receive today, and what would they receive
from a design that keeps absolute level and applies ONE slow exposure control?

Input: real tracks from the fixture inventory, decoded to the firmware's rate (12.8 kHz mono) and
scaled by ONE common factor so Loreen's 56-155 s excerpt peaks at 250 raw counts (the Main RPL
microphone level measured on 10 Nov at the Captain's Bose volume). Every track therefore sits at
"the same volume knob". Playback-level variants: -10, 0, +10 dB.

TODAY (firmware a6bad318 constants, audio-forensics/source/CHAIN-MAP.md stages 3-12):
  s = clamp(x * 8 * 2.7); P = max|s| per 96-sample hop; D = max(0, P - SSL);
  follower F: up 0.200, down 0.0038 per hop (about 2 s), floor SSL; r = D / F;
  E (peak_scaled): up 0.582, down 0.117 per hop; modes 22 and 32 take brightness from E in [0, 1].
  This is checked against the emulator's own peak_scaled trace (--validate).

PROPOSED "what x how much" (prototype v0, parameters are starting values, not tuned):
  what     = today's E (beat-scale shape; the 2 s self-normalised punch stays as it is)
  loudness = 10 log10 of hop energy above 110 Hz (the plate shows nothing below its lowest bin)
  L3       = 3 s energy mean of loudness (section level)
  Ref      = exposure anchor on L3: rises with tau 4 s, falls with tau 60 s, frozen below the gate
  how much = clip((pressure at L3 / pressure at Ref) ^ GAMMA, FLOOR, 1): GAMMA = 1 means light is
             proportional to sound pressure relative to the slow anchor; GAMMA = 0 is exactly today.
             FLOOR = 0.25 (never a gap). Equivalent to dividing by a slow reference instead of a 2 s one.
  drive    = what * how much
  Music-present frames = L3 within 40 dB of the track's own 95th percentile (independent of playback level).

Metrics per track and level (music-present frames only, after 20 s of settling):
  section_r     Pearson r between the 3 s mean of drive and L3 (dB)
  contrast      mean drive in the loudest quarter of L3 / mean drive in the quietest quarter
  punch         mean |frame-to-frame change| of drive (beat motion)
  mean_drive    mean drive (room-volume invariance check across the three playback levels)
Usage: model_frontend.py --cache <dir for decoded pcm> --out <dir> [--validate <emu case dir> --export <src export>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
RATE, HOP = 12800, 96
FPS = RATE / HOP
SSL = 157.0
GAIN = 8 * 2.7
GAMMA, FLOOR = 1.0, 0.25
PRESENT_DB = 40.0
TAU_UP_S, TAU_DOWN_S = 4.0, 60.0
GATE_DB_ABOVE_FLOOR = 8.0
MIC_NOISE_RAW_RMS = 15.0          # Main RPL quiet-room raw_i16_rms (bench telemetry, 13-19)
TRACKS = {
    "Loreen - My Heart Is Refusing Me (pop)": "/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3",
    "Naeleck - Stay (dense, clipped EDM)": "/Users/spectrasynq/Workspace_Management/Software/YT_Saver/Naeleck, Jenil, Heon Seo - Stay.mp3",
    "Regard - Ride It (steady groove)": "/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Regard_Ride_It.mp3",
    "Shelter - Yoel Lewis remix (kick and drop)": "/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3",
    "Carte Blanche (sparse breakdown, build)": "/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Carte-Blanche-Mixed.mp3",
    "Ania Kanwan - The Secret Game (film song)": "/Users/spectrasynq/Workspace_Management/Software/YT_Saver/Ania Kanwan - The Secret Game (Piosenka z filmu Ukryta Gra).mp3",
    "Dimitri Vegas and Like Mike - Mammoth (big room)": "/Users/spectrasynq/Workspace_Management/Software/YT_Saver/Dimitri Vegas & Like Mike - Mammoth.mp3",
}


def decode(path: str, cache: Path) -> np.ndarray:
    out = cache / (Path(path).stem.replace(" ", "_")[:40] + ".f32")
    if not out.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-y", str(out)], check=True)
    return np.fromfile(out, dtype="<f4").astype(np.float64)


def hops(x: np.ndarray) -> np.ndarray:
    n = len(x) // HOP
    return x[: n * HOP].reshape(n, HOP)


def today_peak_scaled(raw: np.ndarray) -> np.ndarray:
    s = np.clip(np.trunc(raw * GAIN), -32767, 32767)
    P = np.abs(hops(s)).max(axis=1)
    D = np.maximum(0.0, P - SSL)
    E = np.zeros(len(D))
    F, e = SSL, 0.0
    for i, d in enumerate(D):
        F = F + 0.200 * (d - F) if d > F else F - 0.0038 * (F - d)
        F = max(F, SSL, 1.0)
        r = d / F
        e = e + 0.582 * (r - e) if r > e else e - 0.117 * (e - r)
        E[i] = e
    return E


def loudness_db(raw: np.ndarray) -> np.ndarray:
    sos = butter(2, 110.0, btype="highpass", fs=RATE, output="sos")
    y = sosfilt(sos, raw)
    return 10 * np.log10((hops(y) ** 2).mean(axis=1) + 1e-3)


def energy_mean_db(L: np.ndarray, seconds: float) -> np.ndarray:
    n = max(1, int(round(seconds * FPS)))
    p = 10 ** (L / 10)
    c = np.cumsum(np.insert(p, 0, 0.0))
    idx = np.arange(1, len(p) + 1)
    lo = np.maximum(0, idx - n)
    return 10 * np.log10((c[idx] - c[lo]) / (idx - lo) + 1e-12)


def proposed(raw: np.ndarray, E: np.ndarray) -> dict:
    """The AFE2 reference (afe2_reference.py) on this track. The filter is vectorised with the reference's own
    biquad coefficients; the per-hop update is the reference's own code."""
    import afe2_reference as ref
    from scipy.signal import lfilter
    st = ref.Afe2(RATE)
    y = lfilter([st.b0, st.b1, st.b2], [1.0, st.a1, st.a2], raw)
    e = (hops(y) ** 2).mean(axis=1)
    L = 10 * np.log10(e + 1e-3)
    L3 = energy_mean_db(L, 3.0)
    how = np.zeros(len(e)); anchor = np.zeros(len(e)); dt = HOP / RATE
    for i, v in enumerate(e):
        how[i] = st.update(float(v), dt); anchor[i] = st.A
    gate = float(np.percentile(L3, 95) - PRESENT_DB)
    return {"L": L, "L3": L3, "ref": 10 * np.log10(anchor), "how_much": how, "drive": E * how, "gate": gate}


def metrics(drive: np.ndarray, L3: np.ndarray, gate: float) -> dict:
    n0 = int(20 * FPS)
    d3 = np.convolve(drive, np.ones(int(3 * FPS)) / int(3 * FPS), mode="same")
    sel = np.zeros(len(drive), bool)
    sel[n0:] = True
    sel &= L3 > gate
    if sel.sum() < 100:
        return {}
    q1, q3 = np.percentile(L3[sel], [25, 75])
    lo, hi = sel & (L3 <= q1), sel & (L3 >= q3)
    return {"section_r": float(np.corrcoef(d3[sel], L3[sel])[0, 1]),
            "contrast": float(drive[hi].mean() / max(drive[lo].mean(), 1e-9)),
            "loud_minus_quiet_db": float(L3[hi].mean() - L3[lo].mean()),
            "punch": float(np.abs(np.diff(drive[sel])).mean()), "mean_drive": float(drive[sel].mean())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--validate", type=Path)
    ap.add_argument("--export", type=Path)
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(parents=True, exist_ok=True)
    lore = decode(TRACKS[next(iter(TRACKS))], a.cache)
    k = 250.0 / np.abs(lore[int(56 * RATE): int(155 * RATE)]).max()      # one volume knob for every track
    res = {"scale_to_raw_counts": k, "tracks": {}}
    keep = {}
    for name, path in TRACKS.items():
        x = decode(path, a.cache) * k
        res["tracks"][name] = {}
        for lvl in (-10, 0, 10):
            raw = x * 10 ** (lvl / 20)
            E = np.clip(today_peak_scaled(raw), 0, 1)
            p = proposed(raw, E)
            res["tracks"][name][str(lvl)] = {"raw_peak": float(np.abs(raw).max()),
                                             "clip_share_today": float((np.abs(raw) * GAIN > 32767).mean()),
                                             "today": metrics(E, p["L3"], p["gate"]),
                                             "proposed": metrics(p["drive"], p["L3"], p["gate"])}
            if lvl == 0:
                keep[name] = (E, p)
    if a.validate and a.export:
        import sys
        sys.path.insert(0, str(a.export / "tools" / "esp_emulator"))
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "emu"))
        import analyse as A
        import emu_capture as ec
        c = A.load_case(ec, a.validate)
        pcm = A.blob_pcm(a.validate / "scenario-blob.bin").astype(np.float64)
        Em = today_peak_scaled(pcm)[c["hops"]]
        ok = ~np.isnan(c["peak"])
        res["validation_vs_emulator_peak_scaled"] = {
            "case": str(a.validate), "frames": int(ok.sum()),
            "pearson_r": float(np.corrcoef(Em[ok], c["peak"][ok])[0, 1]),
            "mean_abs_error": float(np.abs(Em[ok] - c["peak"][ok]).mean()),
            "model_mean": float(Em[ok].mean()), "firmware_mean": float(c["peak"][ok].mean())}
    (a.out / "model.json").write_text(json.dumps(res, indent=1))
    np.savez_compressed(a.cache / "keep.npz", **{f"{i}_{k2}": v for i, (n, (E, p)) in enumerate(keep.items())
                                                 for k2, v in (("E", E), ("L3", p["L3"]), ("ref", p["ref"]), ("drive", p["drive"]), ("how", p["how_much"]))})
    (a.cache / "keep_names.json").write_text(json.dumps(list(keep)))
    rows = ["| track | level | loud-quiet gap dB | TODAY section r | TODAY contrast | PROPOSED section r | PROPOSED contrast | punch kept % | clipped samples today % |", "|---|---|---|---|---|---|---|---|---|"]
    for n, lv in res["tracks"].items():
        for l, m in lv.items():
            t, p = m["today"], m["proposed"]
            if not t:
                continue
            rows.append(f"| {n} | {int(l):+d} dB | {t['loud_minus_quiet_db']:.1f} | {t['section_r']:+.2f} | {t['contrast']:.2f} | {p['section_r']:+.2f} | {p['contrast']:.2f} | {100 * p['punch'] / t['punch']:.0f} | {100 * m['clip_share_today']:.2f} |")
    (a.out / "model.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))
    print(json.dumps(res.get("validation_vs_emulator_peak_scaled"), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
