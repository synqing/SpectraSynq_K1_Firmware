#!/usr/bin/env python3
"""P5.B dual-206 numeric matrix leg (runbook §P5.B) — Unit 2, matrix audit build.

Usage: p5b_matrix_leg.py <label> <port> <primary_ord> <secondary_ord> <seconds>
                         [volume]      # volume omitted -> quiet leg

Sets the mode pair by ORDINAL (probes the dense set_mode index space until the
[MX] mode/smode witnesses report the requested ordinals), waits for transition
idle, then captures the mx_* witnesses per frame. Saves full frames.

PRE-REGISTERED predicates (locked before any run; evaluated offline):
  P1  18/18 music:  frames with silence=0 -> mx_pmax>2 AND mx_smax>2 duty >= 95%
  P2  18/18 drain:  after stimulus stop, mx_pmax<=2 within 15 s (silence dwell
                    5000 ms dominates; pre-registered bound 15 s)
  P3  18/21 music:  while mode=18, mx_smax>2 duty >= 50% (DF not stuck black)
  P4  DF quiet-live: non-silence-latched quiet room, mx_dfinj > 0 on >=1 frame/30 s
"""
import json
import os
import re
import subprocess
import sys
import time

import serial

label, port = sys.argv[1], sys.argv[2]
p_ord, s_ord, DUR = int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
VOL = int(sys.argv[6]) if len(sys.argv) > 6 else None
TRACK = "/Users/spectrasynq/musica/apps/musica-vj/exports/moonlight-lyria-sequenced-composition.mp3"
FIELD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(-?[\d.]+)")

s = serial.Serial(port, 115200, timeout=0.1)
s.dtr = True
time.sleep(0.3)
s.reset_input_buffer()


def read_frames(seconds):
    """Per-LINE timestamps: t_rel is stamped when each complete line ARRIVES."""
    t0 = time.time()
    end = t0 + seconds
    buf = b""
    out = []
    while time.time() < end:
        n = s.in_waiting
        if n:
            buf += s.read(n)
            while b"\n" in buf:
                ln, buf = buf.split(b"\n", 1)
                txt = ln.decode(errors="replace")
                if "[AP]" in txt and "mx_pmax" in txt:
                    d = {k: float(v) for k, v in FIELD.findall(txt)}
                    d["t_rel"] = round(time.time() - t0, 1)
                    out.append(d)
        else:
            time.sleep(0.01)
    return out


def current_modes():
    fr = read_frames(1.6)
    if not fr:
        return None, None
    return int(fr[-1]["mode"]), int(fr[-1]["smode"])


def set_pair(want_p, want_s):
    """set_mode takes the DENSE index; probe until the [MX] ordinal matches."""
    for cmd, want, key in (("set_mode", want_p, "mode"),
                           ("secondary_mode", want_s, "smode")):
        cur = current_modes()[0 if key == "mode" else 1]
        if cur == want:
            continue
        hit = False
        for dense in range(0, 30):
            s.write(f":{cmd}={dense}\n".encode())
            time.sleep(0.7)
            fr = read_frames(1.6)
            if fr and int(fr[-1][key]) == want:
                hit = True
                break
        if not hit:
            raise SystemExit(f"could not reach ordinal {want} via {cmd}")
    print(f"pair set: {current_modes()}")


set_pair(p_ord, s_ord)
time.sleep(2.0)  # transition idle

player = None
if VOL is not None:
    subprocess.run(["osascript", "-e", f"set volume output volume {VOL}"])
    player = subprocess.Popen(["afplay", TRACK],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

print(f"P5B LEG '{label}' pair={p_ord}/{s_ord} {DUR:.0f}s " +
      (f"music vol {VOL}" if VOL else "QUIET"))
frames = read_frames(DUR)
stop_ts = time.time()
drain = []
if player:
    player.terminate()
    subprocess.run(["osascript", "-e", "set volume output volume 50"])
    # capture the drain window for P2
    drain = read_frames(25)
s.close()

outdir = "docs/forensics/im69d-stage1b-stage2-2026-08-12/matrix"
os.makedirs(outdir, exist_ok=True)
path = f"{outdir}/leg_{label}.json"
json.dump({"label": label, "pair": [p_ord, s_ord], "dur": DUR, "vol": VOL,
           "track": TRACK if VOL is not None else None,
           "frames": frames, "drain": drain}, open(path, "w"))
print(f"frames={len(frames)} drain={len(drain)} -> {path}")
