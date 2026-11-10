"""Lane D: did the heard audio play continuously? Camera-microphone recording vs the source file.

Usage: python audio_continuity.py OUT.json ASSET START_S DUR_S RUN_DIR [RUN_DIR ...]

For each run: decode the a7S III clip's audio (camera microphone = what was heard in the room)
and the source passage, both mono 8 kHz. Align once by cross-correlating 10 ms log-energy
envelopes (one fixed offset per run). Then, in 10 ms windows where the SOURCE is loud
(>= its 30th percentile), flag windows where the captured level falls >= 15 dB below its own
local median (500 ms around it) — a dropout or stutter the source does not contain.
Also report the best-fit playback-speed ratio (envelope alignment at the start vs the end).
Coarse check: room acoustics and the speaker shape the capture; only sharp, source-absent
level holes are counted. Not a timing measurement.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 8000
WIN = 80  # 10 ms


def decode(path, start=None, dur=None):
    cmd = ["ffmpeg", "-nostdin", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, "<f4")


def env_db(x):
    n = len(x) // WIN
    e = (x[: n * WIN].reshape(n, WIN) ** 2).mean(1)
    return 10 * np.log10(e + 1e-12)


def best_offset(a, b, lo_s=1.0, hi_s=7.0):
    """offset (windows) such that capture a[n + off] ~ source b[n]. Searched only in
    [lo_s, hi_s]: the camera starts before the player (run.json), and music repeats every
    bar, so an unconstrained peak can land a bar or two away."""
    a0 = a - a.mean()
    b0 = b - b.mean()
    c = np.correlate(a0, b0, mode="full")
    lags = np.arange(len(c)) - (len(b0) - 1)
    m = (lags >= int(lo_s * SR / WIN)) & (lags <= int(hi_s * SR / WIN))
    k = int(np.argmax(np.where(m, c, -np.inf)))
    return int(lags[k]), float(c[k] / (np.linalg.norm(a0) * np.linalg.norm(b0) + 1e-12))


def main():
    out = Path(sys.argv[1])
    asset, start, dur = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    src = env_db(decode(asset, start, dur))
    res = {"method": __doc__.strip().splitlines()[0], "runs": {}}
    for rd in sys.argv[5:]:
        rd = Path(rd)
        cap = env_db(decode(rd / "a7s3.mp4"))
        off, r = best_offset(cap, src)
        idx = np.arange(len(src))
        ci = idx + off
        ok = (ci >= 0) & (ci < len(cap))
        s, c = src[ok], cap[ci[ok]]
        loud = s >= np.percentile(s, 30)
        k = 50
        med = np.array([np.median(c[max(0, i - k):i + k]) for i in range(len(c))])
        hole = loud & (c <= med - 15.0)
        # merge consecutive hole windows into events
        ev, i = [], 0
        hi = np.where(hole)[0]
        while i < len(hi):
            j = i
            while j + 1 < len(hi) and hi[j + 1] == hi[j] + 1:
                j += 1
            ev.append({"t_s": round(float(hi[i] * WIN / SR), 2), "ms": int((hi[j] - hi[i] + 1) * 10)})
            i = j + 1
        res["runs"][rd.name] = {
            "offset_s": round(off * WIN / SR, 3), "envelope_r": round(r, 3),
            "windows_checked": int(ok.sum()), "hole_windows": int(hole.sum()),
            "hole_events_ge_20ms": [e for e in ev if e["ms"] >= 20][:20],
            "n_hole_events_ge_20ms": sum(1 for e in ev if e["ms"] >= 20),
        }
        print(rd.name, res["runs"][rd.name]["offset_s"], res["runs"][rd.name]["envelope_r"],
              res["runs"][rd.name]["n_hole_events_ge_20ms"], res["runs"][rd.name]["hole_events_ge_20ms"][:6])
    out.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
