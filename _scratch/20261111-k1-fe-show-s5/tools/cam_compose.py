#!/usr/bin/env python3
"""Side-by-side camera A/B of the K1 plate (K1-FE-SHOW lead session 5, 12 Nov 2026).

Inputs: camera/m{14,21,22,32}_{off,section}/ from cam_ab.sh (cam.mjpg + cam_t.json + player.jsonl).
Time alignment: show_player.py's footer holds audio_dac_trace rows [sample, dac latency s, monotonic ns]: the
sample reaches the speaker at monotonic + latency. A least-squares line maps host time to song time; every camera
frame (stamped with monotonic_ns on arrival) gets a song time. The camera's own delay is the same in every pass,
so off and on line up with each other; picture vs sound may lag by that delay (a fraction of a second).
Brightness: mean over the plate crop of the decoded image, sRGB decoded to linear. The camera's tone curve is
its own (Picture Profile as set on 12 Nov), so camera ratios are for comparing off against on, not absolute.
Outputs (camera/compose/): ab-4modes.mp4 (with the song's audio), brightness.png, still-loud.png,
still-breakdown.png, summary.json.
Usage: cam_compose.py"""
import json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CAM = Path.home() / "SpectraSynq_K1_Firmware/_scratch/20261111-k1-fe-show-s5/camera"
OUT = CAM / "compose"; OUT.mkdir(exist_ok=True)
ASSET = "/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3"
MODES = [(14, "Spectrum River"), (21, "Dense Forge"), (22, "Snapwave"), (32, "Waveform Hybrid")]
CX, CY, CW, CH = 200, 228, 660, 136          # plate in the 1024 x 576 live view (checked on frame60.png)
T0, T1, FPS = 75.6, 154.4, 25
LOUD, BREAK = (95.0, 109.0), (141.0, 153.0)  # song seconds = bench windows 20-34 s and 66-78 s
SR = 44100
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"


def song_map(pj):
    foot = [json.loads(l) for l in pj.read_text().splitlines() if '"footer"' in l][0]
    tr = np.array(foot["audio_dac_trace"], dtype=np.float64)
    host = tr[:, 2] / 1e9 + tr[:, 1]; song = tr[:, 0] / SR
    a, b = np.polyfit(host, song, 1)
    res = float(np.abs(song - (a * host + b)).max())
    return (lambda t_ns: a * (np.asarray(t_ns, dtype=np.float64) / 1e9) + b), a, res


def lin(x):
    x = x / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


class Pass:
    def __init__(self, d):
        self.d = d
        t = json.loads((d / "cam_t.json").read_text())
        f, self.rate, self.res = song_map(d / "player.jsonl")
        self.ts = f(t["t_ns"]); self.n = len(self.ts)
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-f", "mjpeg", "-i", str(d / "cam.mjpg"), "-vf", f"crop={CW}:{CH}:{CX}:{CY}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.i, self.cur = -1, np.zeros((CH, CW, 3), np.uint8); self.bright = []

    def at(self, t):
        while self.i + 1 < self.n and self.ts[self.i + 1] <= t:
            buf = self.p.stdout.read(CW * CH * 3)
            if len(buf) < CW * CH * 3:
                self.n = self.i + 1; break
            self.i += 1; self.cur = np.frombuffer(buf, np.uint8).reshape(CH, CW, 3)
            self.bright.append((float(self.ts[self.i]), float(lin(self.cur.astype(np.float64)).mean())))
        return self.cur


passes = {(m, s): Pass(CAM / f"m{m}_{s}") for m, _ in MODES for s in ("off", "section")}
LW, GAP, TOP, ROWH, BOT = 190, 14, 56, CH + 30, 70
W = LW + 2 * CW + GAP + 20; H = TOP + len(MODES) * ROWH + BOT
W += W % 2; H += H % 2
fb, fs, fl = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 17), ImageFont.truetype(FONT, 26)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-ss", str(T0), "-t", str(T1 - T0), "-i", ASSET, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(OUT / "ab-4modes.mp4")], stdin=subprocess.PIPE)
stills = {"loud": 102.0, "breakdown": 147.0}
nframes = int((T1 - T0) * FPS)
for k in range(nframes):
    t = T0 + k / FPS
    img = Image.new("RGB", (W, H), (10, 10, 12)); dr = ImageDraw.Draw(img)
    dr.text((LW, 14), "Setting OFF (today)", font=fb, fill=(230, 230, 230))
    dr.text((LW + CW + GAP, 14), "Setting ON  (:k1_afe_spec=section)", font=fb, fill=(120, 190, 255))
    for r, (m, name) in enumerate(MODES):
        y = TOP + r * ROWH
        dr.text((14, y + CH // 2 - 22), f"Mode {m}", font=fb, fill=(230, 230, 230))
        dr.text((14, y + CH // 2 + 6), name, font=fs, fill=(160, 160, 165))
        img.paste(Image.fromarray(passes[(m, "off")].at(t)), (LW, y))
        img.paste(Image.fromarray(passes[(m, "section")].at(t)), (LW + CW + GAP, y))
    sec = "LOUD CHORUS" if LOUD[0] <= t < LOUD[1] else ("BREAKDOWN" if BREAK[0] <= t < BREAK[1] else "")
    mm, ss = divmod(t, 60)
    dr.text((14, H - BOT + 18), f"Loreen - My Heart Is Refusing Me   {int(mm)}:{ss:04.1f}", font=fs, fill=(200, 200, 200))
    if sec:
        dr.text((W - 300, H - BOT + 14), sec, font=fl, fill=(255, 200, 80) if sec == "LOUD CHORUS" else (150, 200, 255))
    x0, x1 = LW, W - 330; dr.rectangle((x0, H - 18, x1, H - 12), fill=(50, 50, 55))
    dr.rectangle((x0, H - 18, x0 + int((x1 - x0) * (t - T0) / (T1 - T0)), H - 12), fill=(200, 200, 200))
    enc.stdin.write(img.tobytes())
    for nm, ts in stills.items():
        if abs(t - ts) < 0.5 / FPS:
            img.save(OUT / f"still-{nm}.png")
enc.stdin.close(); enc.wait()

summ = {}
fig, axs = plt.subplots(len(MODES), 1, figsize=(12, 10), sharex=True)
for ax, (m, name) in zip(axs, MODES):
    for s, col in (("off", "#d08a2a"), ("section", "#2f7fd8")):
        p = passes[(m, s)]; b = np.array(p.bright)
        t, v = b[:, 0], b[:, 1]
        k = max(1, int(round(FPS)))
        vs = np.convolve(v, np.ones(k) / k, mode="same")
        ax.plot(t, 100 * vs, color=col, lw=1.4, label=f"{'off (today)' if s == 'off' else 'on (section)'}")
        lo = v[(t >= LOUD[0]) & (t < LOUD[1])].mean(); br = v[(t >= BREAK[0]) & (t < BREAK[1])].mean()
        summ[f"m{m}_{s}"] = {"frames": int(len(t)), "fps": float(len(t) / (t[-1] - t[0])), "clock_rate": p.rate, "map_residual_s": p.res,
                             "loud_mean_pct": 100 * lo, "breakdown_mean_pct": 100 * br, "loud_over_breakdown": lo / br, "mean_pct": 100 * float(v.mean())}
    for (a0, a1), c in ((LOUD, "#ffd27a"), (BREAK, "#9cc8ff")):
        ax.axvspan(a0, a1, color=c, alpha=0.25, lw=0)
    ax.set_ylabel(f"mode {m}\n{name}\nplate %", fontsize=9); ax.grid(alpha=0.25)
    ax.text(0.01, 0.92, f"loud ÷ breakdown: off {summ[f'm{m}_off']['loud_over_breakdown']:.2f}   on {summ[f'm{m}_section']['loud_over_breakdown']:.2f}",
            transform=ax.transAxes, fontsize=9, va="top")
axs[0].legend(loc="upper right", fontsize=9); axs[-1].set_xlabel("song time, seconds (Loreen 75-155 s at 10 dB under the Captain's volume)")
fig.suptitle("K1 plate brightness from the camera, setting off vs on (yellow = loud chorus, blue = breakdown)", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "brightness.png", dpi=110)
(OUT / "summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(summ, indent=1))
