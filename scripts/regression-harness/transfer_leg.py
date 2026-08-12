#!/usr/bin/env python3
"""Transfer-test leg runner — both IM69D units, concurrent, with stimulus + witness.

Usage:  transfer_leg.py <label> <seconds> [volume] [track]
          volume omitted -> QUIET leg (no playback)

Reads BOTH units continuously in threads. Continuous reads matter: a sleep-then-read
overflows the OS serial buffer and yields zero frames on a live, streaming device.

`:ap_stream=1` is type=value (a space returns Bad command). It is SC_TYPED_ONLY +
CMD_HARNESS but NOT CMD_PERSISTS — RAM flag only, no config write. Restored to 0.

NEVER fires calibration.
"""
import re, sys, time, threading, subprocess, os, statistics as st
import serial

label = sys.argv[1]
DUR = float(sys.argv[2])
VOL = int(sys.argv[3]) if len(sys.argv) > 3 else None
TRACK = sys.argv[4] if len(sys.argv) > 4 else \
    "/Users/spectrasynq/Music/PioneerDJ/Demo Tracks/Demo Track 1.mp3"

UNITS = [("Unit2", "/dev/cu.usbmodem1101"), ("bench", "/dev/cu.usbmodem12201")]
AP = re.compile(r"\[AP\][^\n]*")
FIELD = re.compile(r"\b(\w+)=(-?[\d.]+)")
out, wit = {}, {}


def cap(name, port):
    try:
        s = serial.Serial(port, 115200, timeout=0.1)
        s.dtr = True
        time.sleep(0.6)
        s.reset_input_buffer()
        s.write(b":ap_stream=1\n"); s.flush()
        time.sleep(1.0)
        s.reset_input_buffer()
        buf, end = b"", time.time() + DUR
        while time.time() < end:                 # CONTINUOUS — never sleep-then-read
            n = s.in_waiting
            if n:
                buf += s.read(n)
            else:
                time.sleep(0.01)
        s.write(b":ap_stream=0\n"); s.flush(); time.sleep(0.2); s.close()
        fr = []
        for ln in AP.findall(buf.decode(errors="replace")):
            d = {k: float(v) for k, v in FIELD.findall(ln)}
            if "max_raw" in d and "SSL" in d:
                fr.append(d)
        out[name] = fr
    except Exception as e:
        out[name] = e


def witness():
    try:
        lst = subprocess.run(["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                             capture_output=True, text=True).stderr
        m = re.search(r"\[(\d+)\] MacBook Pro Microphone", lst)   # BY NAME — indices shift
        if not m:
            wit["err"] = "witness mic not found by name"; return
        idx = m.group(1)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "avfoundation", "-i", f":{idx}",
                            "-t", str(DUR), "-af",
                            "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
        v = [float(x) for x in re.findall(r"RMS_level=(-?[\d.]+)", r)]
        wit.update(idx=idx, mean=st.mean(v) if v else float("nan"),
                   mx=max(v) if v else float("nan"), n=len(v))
    except Exception as e:
        wit["err"] = str(e)


player = None
if VOL is not None:
    subprocess.run(["osascript", "-e", f"set volume output volume {VOL}"])
    player = subprocess.Popen(["afplay", TRACK],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)                                # let the Bose spin up

print(f"LEG '{label}'  {DUR:.0f}s  " + (f"music @ system vol {VOL}" if VOL else "QUIET (no playback)"))
ths = [threading.Thread(target=cap, args=u) for u in UNITS] + [threading.Thread(target=witness)]
[t.start() for t in ths]; [t.join() for t in ths]
if player:
    player.terminate()


def pct(v, p):
    v = sorted(v)
    if not v: return float("nan")
    k = (len(v)-1)*p/100.0; f = int(k); c = min(f+1, len(v)-1)
    return v[f] + (v[c]-v[f])*(k-f)


if "err" in wit:
    print(f"  WITNESS ERROR: {wit['err']}")
else:
    print(f"  witness[{wit['idx']}] mean {wit['mean']:.1f} dBFS  max {wit['mx']:.1f} dBFS  ({wit['n']} frames)")

print(f"\n{'':<7}{'frames':>7}{'SSL':>6}{'sil%':>7}{'rms med':>9}{'rms max':>9}"
      f"{'ratio med':>11}{'ratio p95':>11}{'lock%':>7}{'conf med':>10}")
print("-" * 84)
res = {}
for name, _ in UNITS:
    f = out.get(name)
    if isinstance(f, Exception): print(f"{name:<7} ERROR: {f}"); continue
    if not f: print(f"{name:<7} NO FRAMES"); continue
    ssl = st.median([d["SSL"] for d in f])
    r = [d["max_raw"]/d["SSL"] for d in f if d["SSL"] > 0]
    sil = [d["silence"] for d in f if "silence" in d]
    rms = [d["rms_raw"] for d in f if "rms_raw" in d]
    lk = [d["lock"] for d in f if "lock" in d]
    cf = [d["conf"] for d in f if "conf" in d]
    res[name] = dict(ratio=r, ssl=ssl)
    print(f"{name:<7}{len(f):>7}{int(ssl):>6}{100*sum(sil)/len(sil):>6.1f}%"
          f"{st.median(rms):>9.4f}{max(rms):>9.4f}{st.median(r):>10.2f}x{pct(r,95):>10.2f}x"
          f"{(100*sum(lk)/len(lk) if lk else 0):>6.1f}%{(st.median(cf) if cf else 0):>10.2f}")

if len(res) == 2:
    a, b = res["Unit2"]["ratio"], res["bench"]["ratio"]
    ma, mb = st.median(a), st.median(b)
    print(f"\n  SSL-normalised: Unit2 {ma:.2f}x  bench {mb:.2f}x  "
          f"delta {abs(ma-mb):.2f}x ({100*abs(ma-mb)/max(ma,mb):.0f}%)")
    import json
    json.dump({"label": label, "dur": DUR, "vol": VOL,
               "witness": {k: v for k, v in wit.items()},
               "Unit2": res["Unit2"]["ratio"], "bench": res["bench"]["ratio"],
               "pky": {n: [d["pky"] for d in out[n] if "pky" in d] for n, _ in UNITS},
               "ssl": {"Unit2": res["Unit2"]["ssl"], "bench": res["bench"]["ssl"]}},
              open(f"leg_{label}.json", "w"))
    print(f"  raw ratios -> leg_{label}.json")
