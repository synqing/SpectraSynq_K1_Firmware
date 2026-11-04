#!/usr/bin/env python3
"""Score an RGB8 rtrace dump: how bright is the primary strip, frame by frame.
usage: score_rtrace.py LOG [LOG ...]"""
import re, sys, statistics as st
for fn in sys.argv[1:]:
    raw = open(fn, "rb").read().decode("latin1")
    hdr = re.search(r"\[RTRACE-BEGIN ([^\]]*)\]", raw)
    b = re.search(r"BUILD: [^\r\n]*", raw)
    frames = []
    for line in raw.splitlines():
        p = line.split(",")
        if len(p) == 5 and p[0] == "F" and len(p[4]) == 960:
            px = bytes.fromhex(p[4]); frames.append((int(p[2]), px))
    print(fn.rsplit("/", 1)[-1], "|", b.group(0) if b else "no BUILD", "|", hdr.group(1) if hdr else "no RTRACE header", "| frames parsed", len(frames))
    if not frames: continue
    mean = [sum(px) / (len(px) * 255) for _, px in frames]          # 0..1 average drive
    peak = [max(px) for _, px in frames]                              # brightest channel
    lit = [sum(1 for i in range(0, len(px), 3) if max(px[i:i+3]) > 8) for _, px in frames]
    jump = [abs(mean[i] - mean[i-1]) for i in range(1, len(mean))]
    dur = (frames[-1][0] - frames[0][0]) / 1000
    print(f"  span {dur:.1f} s | mean drive median {st.median(mean)*100:.2f}% max {max(mean)*100:.2f}% | "
          f"brightest channel median {st.median(peak)} max {max(peak)} | lit px (>8/255) median {st.median(lit)} max {max(lit)} of 160")
    print(f"  frames with mean drive >1%: {sum(m>0.01 for m in mean)} / {len(mean)} | >5%: {sum(m>0.05 for m in mean)} | "
          f"frame-to-frame jumps >2%: {sum(j>0.02 for j in jump)}")
