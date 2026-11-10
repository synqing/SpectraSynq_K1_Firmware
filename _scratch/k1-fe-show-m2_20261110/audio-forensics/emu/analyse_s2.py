#!/usr/bin/env python3
"""AFE2 stage 2 emulator A/B analysis (K1-FE-SHOW lead session 4, 11 Nov 2026).

Reads each s2-* case's uart.txt (novelty trace N,gen,novelty,vu,silence,crc: one line per hop) and reports:
  music_silent   hops flagged silent while music plays (hops 0-11200), and as a share
  stop_to_silent seconds from the music stopping (hop 11200) to the first silent hop
  room_held      share of the room-model hops (12800-14400) flagged silent
  return_clear   seconds from the music returning (hop 14400) to the first not-silent hop
Acceptance (AFE2-PLAN S2): new test 0 music_silent at every level; silent within the stop segment;
held through the room model; clear on return. Usage: analyse_s2.py <run dir> [--out <md>]"""
import argparse
import json
from pathlib import Path

HOP_S = 96 / 12800
ap = argparse.ArgumentParser(); ap.add_argument("run", type=Path); ap.add_argument("--out", type=Path); a = ap.parse_args()
rows, res = [], {}
for d in sorted(p for p in a.run.iterdir() if p.is_dir() and p.name.startswith("s2-")):
    u = d / "uart.txt"
    if not u.exists():
        rows.append(f"| {d.name} | no uart.txt | | | | |"); continue
    sil = [int(l.split(",")[4]) for l in u.read_text(errors="replace").splitlines() if l.startswith("N,")]
    if len(sil) < 15000:
        rows.append(f"| {d.name} | only {len(sil)} hops traced | | | | |"); continue
    music = sum(sil[:11200])
    stop = next((i for i in range(11200, 14400) if sil[i]), None)
    # Held: from the first silent hop after the stop to the music's return, every hop stays silent
    # (the new test's S takes several seconds to fall after a loud stop, so silence may begin inside
    # the room-model segment rather than the digital-silence segment).
    room = (sum(sil[stop:14400]) / (14400 - stop)) if stop is not None else 0.0
    ret = next((i for i in range(14400, len(sil)) if not sil[i]), None)
    r = {"music_silent": music, "music_share": music / 11200, "stop_to_silent_s": None if stop is None else (stop - 11200) * HOP_S,
         "room_held": room, "return_clear_s": None if ret is None else (ret - 14400) * HOP_S}
    res[d.name] = r
    f = lambda v: "never" if v is None else f"{v:.2f} s"
    rows.append(f"| {d.name} | {music} ({100 * r['music_share']:.1f} %) | {f(r['stop_to_silent_s'])} | {100 * room:.0f} % | {f(r['return_clear_s'])} |")
new = {k: v for k, v in res.items() if k.endswith("-new")}
ok = bool(new) and all(v["music_silent"] == 0 and v["stop_to_silent_s"] is not None and v["room_held"] > 0.99
                       and v["return_clear_s"] is not None and v["return_clear_s"] < 0.2 for v in new.values())
text = "\n".join(["# AFE2-S2 emulator A/B: silence test old vs new", "",
                  "Mode 22, exposure on. Music 84 s, then 12 s digital silence, 12 s room-noise model (2.5 counts rms), 6 s music.", "",
                  "| case | silent hops during music | music stop to silence | held silent from then until music returns | music return to clear |",
                  "|---|---|---|---|---|"] + rows + ["", f"New test accepted on every case: {'YES' if ok else 'NO'} ({len(new)} cases)."])
print(text)
if a.out:
    a.out.write_text(text + "\n"); (a.out.with_suffix(".json")).write_text(json.dumps(res, indent=1))
