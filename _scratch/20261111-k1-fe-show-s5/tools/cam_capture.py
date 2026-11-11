#!/usr/bin/env python3
"""Record the Sony a7S III live view over USB (PTP, gphoto2) with a host timestamp on every frame.
(K1-FE-SHOW lead session 5, 12 Nov 2026.)

The camera must be in PC Remote mode. macOS's ptpcamerad claims the camera exclusively and is restarted
by launchd on demand, so it is stopped by PID immediately before gphoto2 opens the device.
Exposure is the camera's own (it was in movie Manual mode, fixed ISO, shutter 1/100 s, Daylight WB on
12 Nov 2026); this script never changes a camera setting.

Output: <out>/cam.mjpg (concatenated JPEG frames, as received) and <out>/cam_t.json
  {"t_ns": [time.monotonic_ns() at the end of each frame], "started_ns": ..., "ended_ns": ..., "rc": ...}
time.monotonic_ns() is the clock show_player.py writes in its log, so frames map to song time exactly.
Usage: cam_capture.py <out dir> <seconds>"""
import json, os, signal, subprocess, sys, time
from pathlib import Path

out = Path(sys.argv[1]); secs = int(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
pid = subprocess.run(["pgrep", "ptpcamerad"], capture_output=True, text=True).stdout.split()
for p in pid:
    try:
        os.kill(int(p), signal.SIGKILL)
    except ProcessLookupError:
        pass
started = time.monotonic_ns()
proc = subprocess.Popen(["gphoto2", f"--capture-movie={secs}s", "--stdout"], stdout=subprocess.PIPE, stderr=open(out / "gphoto2.err", "wb"))
t_ns, buf = [], b""
with open(out / "cam.mjpg", "wb") as fh:
    while True:
        chunk = proc.stdout.read1(1 << 16) if hasattr(proc.stdout, "read1") else proc.stdout.read(1 << 16)
        if not chunk:
            break
        now = time.monotonic_ns()
        buf += chunk
        while True:
            s = buf.find(b"\xff\xd8")
            if s < 0:
                buf = b""
                break
            e = buf.find(b"\xff\xd9", s + 2)
            if e < 0:
                buf = buf[s:]
                break
            fh.write(buf[s:e + 2]); t_ns.append(now)
            buf = buf[e + 2:]
rc = proc.wait()
(out / "cam_t.json").write_text(json.dumps({"t_ns": t_ns, "started_ns": started, "ended_ns": time.monotonic_ns(), "rc": rc, "frames": len(t_ns)}))
fps = len(t_ns) / max(1e-9, (t_ns[-1] - t_ns[0]) / 1e9) if len(t_ns) > 1 else 0
print(f"cam frames={len(t_ns)} fps={fps:.1f} rc={rc}")
