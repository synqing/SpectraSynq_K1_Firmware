#!/usr/bin/env python3
"""Capture the bench K1's FINAL rendered LED bytes (mode 37 Melodic Bloom) and quantify
steppy brightness / motion. Drives the vp_probe VPAB frame capture over serial:
  :vpab=reset  ->  :vpab=start,1,bytes  ->  (fill)  ->  :vpab=stop  ->  :vpab=frames
Parses K1DFR/K1DFC records: each payload = 32B header + 160*RGB (offset 32).
Saves raw dump + parsed frames; prints per-frame brightness (steppiness) + timing.
"""
import sys, time, glob, re
PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbmodem1401"
FILL_S = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
OUT = "/private/tmp/claude-501/-Users-spectrasynq-muscriptor/8ccdc945-ed73-409b-8ff9-8a2283d83642/scratchpad"

try:
    import serial
except ImportError:
    print("NO_PYSERIAL"); sys.exit(3)

def send(ser, s):
    ser.write((s + "\n").encode()); ser.flush(); time.sleep(0.15)

def read_until(ser, marker, timeout):
    buf = b""; t0 = time.time()
    while time.time() - t0 < timeout:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            if marker in buf: break
        else:
            time.sleep(0.02)
    return buf

try:
    ser = serial.Serial(PORT, 115200, timeout=0.1)
except Exception as e:
    print(f"PORT_OPEN_FAIL: {e}"); sys.exit(4)

time.sleep(0.3); ser.reset_input_buffer()
send(ser, ":vpab=reset")
send(ser, ":vpab=start,1,bytes")
time.sleep(FILL_S)
send(ser, ":vpab=stop")
ser.reset_input_buffer()
send(ser, ":vpab=frames")
raw = read_until(ser, b"K1DF_END", timeout=8.0)
ser.close()

open(f"{OUT}/vpab_raw_dump.txt", "wb").write(raw)
txt = raw.decode("ascii", "replace")
print("=== headers ===")
for line in txt.splitlines():
    if line.startswith("K1DF_BEGIN") or line.startswith("K1DF_END"):
        print(" ", line.strip())

# reassemble frames: K1DFR starts a frame; K1DFC hex chunks follow (by seq)
frames = {}   # seq -> {frame, t_us, hexparts:{idx:hex}}
cur = None
for line in txt.splitlines():
    line = line.strip()
    if line.startswith("K1DFR,"):
        d = dict(kv.split("=", 1) for kv in line[len("K1DFR,"):].split(",") if "=" in kv)
        seq = int(d.get("seq", -1)); cur = seq
        frames[seq] = {"frame": int(d.get("frame", 0)), "t_us": int(d.get("t_us", 0)), "hex": {}}
    elif line.startswith("K1DFC,") and cur is not None:
        d = {}
        m = re.search(r"idx=(\d+)", line); off = re.search(r"hex=([0-9a-fA-F]+)", line)
        if m and off:
            frames[cur]["hex"][int(m.group(1))] = off.group(1)

seqs = sorted(frames)
print(f"\nparsed {len(seqs)} frame records")
if not seqs:
    print("NO FRAMES — device idle/undriven or port contention. First 400 chars of dump:")
    print(txt[:400]); sys.exit(0)

def payload(seq):
    parts = frames[seq]["hex"]
    return bytes.fromhex("".join(parts[i] for i in sorted(parts)))

import numpy as np
rows = []
prev_t = None
for seq in seqs:
    p = payload(seq)
    if len(p) < 32:
        continue
    channel = p[0]; mode = p[1]; dither_step = p[2]; fastled_dither = p[3]
    leds = int.from_bytes(p[4:6], "little")
    render_us = int.from_bytes(p[8:12], "little")
    frame_us = int.from_bytes(p[16:20], "little")
    rgb = np.frombuffer(p[32:32 + leds * 3], dtype=np.uint8).astype(np.int32).reshape(-1, 3)
    lum = rgb.max(axis=1)  # per-pixel brightness proxy (max channel)
    ft = frames[seq]["t_us"]
    dt_ms = (ft - prev_t) / 1000.0 if prev_t is not None else 0.0
    prev_t = ft
    rows.append(dict(seq=seq, frame=frames[seq]["frame"], mode=mode, dither=fastled_dither,
                     dstep=dither_step, leds=leds, dt_ms=dt_ms,
                     total=int(lum.sum()), cmax=int(lum.max()),
                     centre=int(lum[78:82].max()), lum=lum))

L = np.stack([r["lum"] for r in rows])   # frames x pixels
print(f"\nframes={len(rows)} leds={rows[0]['leds']} mode={rows[0]['mode']} "
      f"fastled_dither={rows[0]['dither']} lit_frac={(L>0).mean():.2f} maxlum={L.max()}")
if L.max() == 0:
    print(">> ALL PIXELS DARK — no drive (silence). Need audio playing to capture content.")
    sys.exit(0)

print(f"\n{'seq':>4} {'frame':>6} {'dt_ms':>6} {'total':>7} {'centre':>6} {'cmax':>5} {'dstep':>5}")
for r in rows[:40]:
    print(f"{r['seq']:>4} {r['frame']:>6} {r['dt_ms']:>6.1f} {r['total']:>7} {r['centre']:>6} {r['cmax']:>5} {r['dstep']:>5}")

# STEPPINESS metrics — temporal deltas of per-pixel brightness
dL = np.abs(np.diff(L.astype(np.int32), axis=0))
print(f"\n=== TEMPORAL STEPPINESS (per-pixel |Δbrightness| frame-to-frame) ===")
print(f"  mean |Δ| = {dL.mean():.2f}   p99 |Δ| = {np.percentile(dL,99):.1f}   max |Δ| = {dL.max()}")
print(f"  frames with a pixel jump >32 (of 255): {(dL.max(axis=1)>32).sum()} / {len(rows)-1}")
# centre-brightness stepping over time (the 'steppy brightness' signature)
centre = np.array([r['centre'] for r in rows])
print(f"  centre lum series: {list(centre[:24])}")
dc = np.abs(np.diff(centre))
print(f"  centre |Δ| mean={dc.mean():.1f} max={dc.max()}  (steppy if large discrete jumps)")
# dt cadence — is the frame interval itself stepping?
dts = np.array([r['dt_ms'] for r in rows[1:]])
print(f"  frame dt_ms: mean={dts.mean():.2f} min={dts.min():.2f} max={dts.max():.2f}")
np.savez(f"{OUT}/vpab_frames.npz", L=L, centre=centre)
print(f"\nsaved raw -> vpab_raw_dump.txt, parsed -> vpab_frames.npz")
