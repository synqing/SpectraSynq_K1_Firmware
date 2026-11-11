#!/usr/bin/env python3
"""S4 acceptance identity (session 5, 12 Nov 2026): the accepted build (no switch; s4-*-agc cases now run the one
spectrum gain) must give the same LED frames as attempt 2's section cases (s4-*-sec on wip/k1-afe2-s4 27810f69,
the build the Captain judged on camera). Both runs are the k1_main_rpl_emu_tempo_probe image with a declared epoch.
Usage: compare_accept.py <export> <accepted run> <attempt-2 run> <out txt>"""
import sys
from pathlib import Path
exp, new, old, out = map(Path, sys.argv[1:5])
sys.path.insert(0, str(exp / "tools" / "esp_emulator"))
import emu_capture as ec
lines, bad, n = [], 0, 0
for d in sorted(new.glob("s4-*-agc")):
    o = old / (d.name[: -len("agc")] + "sec")
    if not (o / "uart.txt").exists():
        lines.append(f"{d.name}: no attempt-2 case {o.name}"); bad += 1; continue
    pn = ec.native_payload(ec.decode((d / "uart.txt").read_text(errors="replace")))
    po = ec.native_payload(ec.decode((o / "uart.txt").read_text(errors="replace")))
    k = min(len(pn), len(po)); diff = sum(1 for i in range(k) if pn[i] != po[i]); n += 1
    ok = diff == 0 and len(pn) == len(po); bad += 0 if ok else 1
    lines.append(f"{d.name:28s} vs {o.name:28s} {'PASS' if ok else 'FAIL'} frames {len(pn)}/{len(po)} differing {diff}")
lines.append(f"compared {n}; failing {bad}")
txt = "\n".join(lines); print(txt); out.write_text(txt + "\n")
sys.exit(1 if bad else 0)
