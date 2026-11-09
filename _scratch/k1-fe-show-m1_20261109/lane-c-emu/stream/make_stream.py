#!/usr/bin/env python3
"""C3 — prepared Prim8 stream for the K1-FE-SHOW-M1 passage (Lane C-emu).

Offline "prepared" analysis of the ORIGINAL recording (not the emulator's 12.8 kHz copy):
decode the asset with ffmpeg at its native rate, mono = mean(L, R), evaluate one analysis
frame per 120 Hz tick on the asset-anchored grid of lane-b/prim8_stream.py, and encode
the five Prim8 channels the FE firmware consumes. Unconsumed channels are a documented
constant. Output: stream/<name>.prsm + .prsm.json (lane-b sidecar schema) + a PNG plot.

Method (recorded in the sidecar "source" block):
  analysis frame   2048-sample Hann window centred on the tick time (46.4 ms at 44.1 kHz)
  pressure  (0)    RMS of the window in dBFS mapped linearly FLOOR dBFS -> 0, -6 dBFS -> 1 (v1 FLOOR=-48:
                   rejected, breakdown only fell to ~0.5; v2 FLOOR=-30, the frozen C3 stream);
                   follower attack instant, release tau 300 ms ("hit hard, let go slow");
                   floor 0.02 while the window is above -60 dBFS ("never a gap")
  impact    (1)    log-magnitude spectral flux (half-wave rectified) between consecutive
                   ticks; adaptive threshold = median over +-250 ms + 0.5 x MAD-scaled
                   spread; an onset is a local maximum over +-50 ms above threshold; its
                   strength = excess / p95(excess over the passage), clipped to 1; the
                   channel is the max of onset pulses each decaying with tau 120 ms
  mass      (2)    band power 20-150 Hz, dB, normalised p05..p99 over the passage,
                   follower release tau 200 ms
  momentum  (3)    band power 150-2000 Hz, same normalisation and follower
  texture   (6)    band power 2000-16000 Hz, same normalisation and follower
  heat, space, gravity (4, 5, 7)  constant 0 (no device consumer on FE firmware 407fdf6f)
seq = global tick index (seq == i), so any start offset or seek is a seq jump by construction.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LANE_B = HERE.parent.parent / "lane-b"
sys.path.insert(0, str(LANE_B))
import prim8_stream as ps  # noqa: E402

HZ = 120
WIN = 2048


def decode(path: Path, rate: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0",
                          "-f", "s16le", "-acodec", "pcm_s16le", "-ar", str(rate), "-"],
                         check=True, capture_output=True).stdout
    st = np.frombuffer(raw, dtype="<i2").reshape(-1, 2).astype(np.float64) / 32768.0
    return st, st.mean(axis=1)


def follower(x: np.ndarray, release_s: float, hz: int = HZ) -> np.ndarray:
    a = np.exp(-1.0 / (release_s * hz))
    y = np.empty_like(x)
    acc = 0.0
    for k, v in enumerate(x):
        acc = v if v >= acc else a * acc + (1 - a) * v
        y[k] = acc
    return y


def norm_pct(db: np.ndarray, lo=5, hi=99) -> tuple[np.ndarray, float, float]:
    p_lo, p_hi = np.percentile(db, lo), np.percentile(db, hi)
    return np.clip((db - p_lo) / max(p_hi - p_lo, 1e-9), 0, 1), float(p_lo), float(p_hi)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset-json", default=str(HERE.parent.parent / "lane-a" / "ASSET.json"))
    ap.add_argument("--name", default="loreen_75_155_120hz_v2")
    ap.add_argument("--pressure-floor-db", type=float, default=-30.0)
    args = ap.parse_args()
    asset = json.loads(Path(args.asset_json).read_text())
    src = Path(asset["path"])
    if ps.sha256_file(src) != asset["sha256"]:
        raise SystemExit("asset sha256 mismatch")
    R = asset["sample_rate"]
    stereo, x = decode(src, R)
    if len(x) != asset["frames"]:
        raise SystemExit(f"decoded {len(x)} frames != ASSET.json {asset['frames']}")
    start_us = int(round(asset["passage_start_s"] * 1e6))
    end_us = int(round(asset["passage_end_s"] * 1e6))
    i0 = ps.first_tick_at_or_after_us(start_us, HZ)
    i1 = ps.first_tick_at_or_after_us(end_us, HZ)
    ticks = np.arange(i0, i1)
    # one tick before the passage for the first flux difference
    centres = np.array([ps.us_to_sample(ps.tick_time_us(int(i), HZ), R) for i in range(i0 - 1, i1)])
    win = np.hanning(WIN)
    freqs = np.fft.rfftfreq(WIN, 1 / R)
    bands = {"low": (20, 150), "mid": (150, 2000), "high": (2000, 16000)}
    bmask = {k: (freqs >= a) & (freqs < b) for k, (a, b) in bands.items()}
    rms_db, bdb, logmag = [], {k: [] for k in bands}, []
    for c in centres:
        seg = x[c - WIN // 2:c + WIN // 2]
        rms = np.sqrt(np.mean(seg ** 2) + 1e-20)
        rms_db.append(20 * np.log10(rms))
        mag = np.abs(np.fft.rfft(seg * win))
        pw = mag ** 2
        for k in bands:
            bdb[k].append(10 * np.log10(pw[bmask[k]].sum() + 1e-12))
        logmag.append(np.log1p(100.0 * mag))
    rms_db = np.array(rms_db)
    logmag = np.array(logmag)
    flux = np.maximum(np.diff(logmag, axis=0), 0).sum(axis=1)       # len = n ticks
    rms_db = rms_db[1:]
    for k in bands:
        bdb[k] = np.array(bdb[k])[1:]
    n = len(ticks)
    # pressure
    p_lin = np.clip((rms_db - args.pressure_floor_db) / (-6.0 - args.pressure_floor_db), 0, 1)
    pressure = follower(p_lin, 0.300)
    pressure = np.where(rms_db > -60.0, np.maximum(pressure, 0.02), pressure)
    # impact: adaptive-threshold peak picking on spectral flux
    half = int(0.25 * HZ)
    med = np.array([np.median(flux[max(0, k - half):k + half + 1]) for k in range(n)])
    mad = np.array([np.median(np.abs(flux[max(0, k - half):k + half + 1] - med[k])) for k in range(n)])
    thr = med + 0.5 * 1.4826 * mad
    nb = int(0.05 * HZ)
    onsets = [k for k in range(n) if flux[k] > thr[k] and flux[k] == flux[max(0, k - nb):k + nb + 1].max()]
    excess = np.array([flux[k] - thr[k] for k in onsets])
    scale = np.percentile(excess, 95) if len(excess) else 1.0
    pulses = np.zeros(n)
    for k, e in zip(onsets, excess):
        pulses[k] = min(1.0, e / scale)
    impact = follower(pulses, 0.120)
    band_norm = {}
    chans = {}
    for k, idx in (("low", "mass"), ("mid", "momentum"), ("high", "texture")):
        v, lo, hi = norm_pct(bdb[k])
        band_norm[k] = {"p05_db": lo, "p99_db": hi}
        chans[idx] = follower(v, 0.200)
    rows = []
    for k in range(n):
        vals = [pressure[k], impact[k], chans["mass"][k], chans["momentum"][k], 0.0, 0.0,
                chans["texture"][k], 0.0]
        rows.append([int(round(min(1.0, max(0.0, v)) * 65535)) for v in vals])
    frames = [ps.encode_frame(int(i), ps.tick_time_us(int(i), HZ), r, HZ) for i, r in zip(ticks, rows)]
    out = HERE / f"{args.name}.prsm"
    source = {
        "tool": "lane-c-emu/stream/make_stream.py", "analysis": "offline prepared analysis of the original recording",
        "decode": f"ffmpeg s16le at {R} Hz, mono = mean(L,R)", "window": f"{WIN}-sample Hann centred on tick time",
        "method": __doc__.split("Method (recorded in the sidecar \"source\" block):")[1].split("seq = ")[0].strip(),
        "seq_rule": "seq == global tick index i (start offset or seek is a seq jump by construction)",
        "onsets": len(onsets), "onset_flux_excess_p95": float(scale), "band_norm": band_norm,
        "passage_s": [asset["passage_start_s"], asset["passage_end_s"]], "transition_s": asset["transition_s"],
        "constants": {"heat": 0, "space": 0, "gravity": 0},
        "pressure_map_dbfs": [args.pressure_floor_db, -6.0],
    }
    side = ps.write_stream(out, frames, hz=HZ, passage_start_sample=ps.us_to_sample(start_us, R),
                           asset={"sha256": asset["sha256"], "sample_rate": R, "sample_count": asset["frames"],
                                  "channels": asset["channels"], "path_hint": str(src)},
                           epochs=[{"epoch_id": "e0", "first_frame": 0, "kind": "start", "seq_start": int(i0)}],
                           source=source, notes="Lane C-emu C3. Approval label: " + asset["approval_label"][:40])
    # plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = np.array([ps.tick_time_us(int(i), HZ) for i in ticks]) / 1e6
    fig, axs = plt.subplots(6, 1, figsize=(16, 12), sharex=True)
    axs[0].plot(t, rms_db, lw=0.6, color="#444")
    axs[0].set_ylabel("RMS dBFS")
    for ax, (name, arr) in zip(axs[1:], (("pressure (0)", pressure), ("impact (1)", impact),
                                          ("mass (2) low", chans["mass"]), ("momentum (3) mid", chans["momentum"]),
                                          ("texture (6) high", chans["texture"]))):
        ax.plot(t, arr, lw=0.6)
        ax.set_ylim(-0.02, 1.05)
        ax.set_ylabel(name)
    for ax in axs:
        ax.axvline(asset["transition_s"], color="red", lw=1.5)
        for b in asset.get("secondary_boundaries_s", []):
            ax.axvline(b, color="orange", lw=0.8, ls="--")
    axs[0].set_title(f"{out.name}  sha256 {side['stream_sha256'][:16]}  {n} frames @ {HZ} Hz  "
                     f"original {asset['passage_start_s']}-{asset['passage_end_s']} s  red = transition {asset['transition_s']} s")
    axs[-1].set_xlabel("original recording time (s)")
    fig.tight_layout()
    fig.savefig(HERE / f"{args.name}.png", dpi=90)
    print(json.dumps({"frames": n, "first_tick": int(i0), "onsets": len(onsets), "stream_sha256": side["stream_sha256"],
                      "sidecar_sha256": ps.sha256_file(str(out) + ".json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
