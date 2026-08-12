#!/usr/bin/env python3
"""P4.A baseline leg — capture EVERY [AP] field on one unit, save full frames.

Usage: p4_baseline_leg.py <label> <port> <seconds> [volume] [track]
       volume omitted -> quiet leg (no playback)

Writes docs/forensics/im69d-consumer-baseline-2026-08-12/raw/leg_<label>.json:
{label, dur, vol, track, witness{mean,max,n}, frames:[{field:val,...},...]}

Read-only serial (:ap_stream toggles a RAM flag). NEVER fires calibration.
"""
import json
import os
import re
import statistics as st
import subprocess
import sys
import threading
import time

import serial

label, port, DUR = sys.argv[1], sys.argv[2], float(sys.argv[3])
VOL = int(sys.argv[4]) if len(sys.argv) > 4 else None
TRACK = sys.argv[5] if len(sys.argv) > 5 else \
    "/Users/spectrasynq/musica/apps/musica-vj/exports/moonlight-lyria-sequenced-composition.mp3"

FIELD = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(-?[\d.]+)")
AP = re.compile(r"\[AP\][^\r\n]*")
frames, wit = [], {}


def cap():
    s = serial.Serial(port, 115200, timeout=0.1)
    s.dtr = True
    time.sleep(0.3)
    s.reset_input_buffer()
    s.write(b":ap_stream=1\n")
    s.flush()
    buf = b""
    end = time.time() + DUR
    while time.time() < end:
        n = s.in_waiting
        if n:
            buf += s.read(n)
        else:
            time.sleep(0.01)
    s.write(b":ap_stream=0\n")
    s.flush()
    time.sleep(0.2)
    s.close()
    for ln in AP.findall(buf.decode(errors="replace")):
        d = {k: float(v) for k, v in FIELD.findall(ln)}
        if "SSL" in d:
            frames.append(d)


def witness():
    try:
        lst = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True, text=True).stderr
        m = re.search(r"\[(\d+)\] MacBook Pro Microphone", lst)  # BY NAME — indices shift
        if not m:
            wit["err"] = "witness mic not found"
            return
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "avfoundation", "-i", f":{m.group(1)}",
             "-t", str(DUR), "-af",
             "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
             "-f", "null", "-"], capture_output=True, text=True).stderr
        v = [float(x) for x in re.findall(r"RMS_level=(-?[\d.]+)", r)]
        wit.update(mean=st.mean(v) if v else None, max=max(v) if v else None, n=len(v))
    except Exception as e:  # witness is evidence, not control flow
        wit["err"] = str(e)


player = None
if VOL is not None:
    subprocess.run(["osascript", "-e", f"set volume output volume {VOL}"])
    player = subprocess.Popen(["afplay", TRACK],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

print(f"P4 LEG '{label}' {DUR:.0f}s " + (f"music vol {VOL}" if VOL else "QUIET"))
ths = [threading.Thread(target=cap), threading.Thread(target=witness)]
[t.start() for t in ths]
[t.join() for t in ths]
if player:
    player.terminate()

outdir = "docs/forensics/im69d-consumer-baseline-2026-08-12/raw"
os.makedirs(outdir, exist_ok=True)
path = f"{outdir}/leg_{label}.json"
json.dump({"label": label, "dur": DUR, "vol": VOL,
           "track": TRACK if VOL is not None else None,
           "witness": wit, "frames": frames}, open(path, "w"))
print(f"frames={len(frames)} witness={wit} -> {path}")
