#!/usr/bin/env python3
"""Live (no prepared stream) output, old against new: live_compare.py <old emu out> <new emu out> <tree>
Both are outputs of `run.py --scenario tools/esp_emulator/s3_music_regression.json --suite default
--profile scenario`. For every case present in both: decode with the tree's emu_capture and count the
captured frames whose edge A or edge B bytes differ. Exit code = number of cases that differ or
cannot be compared."""
import json, sys
from pathlib import Path
old, new, tree = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(tree / "tools/esp_emulator"))
import emu_capture as ec
ro, rn = json.loads((old / "result.json").read_text()), json.loads((new / "result.json").read_text())
bad = 0
print(f"# old {old}\n# new {new}")
for cid in rn["cases"]:
    so, sn = ro["cases"].get(cid, {}).get("status"), rn["cases"][cid].get("status")
    uo, un = old / cid / "uart.txt", new / cid / "uart.txt"
    if not (uo.is_file() and un.is_file()):
        print(f"{cid}: NOT COMPARED (uart missing; old status {so}, new status {sn})"); bad += 1; continue
    co, cn = ec.decode(uo.read_text(errors="replace")), ec.decode(un.read_text(errors="replace"))
    n = min(len(co.frames), len(cn.frames))
    da = sum(1 for a, b in zip(co.frames, cn.frames) if bytes(a.A) != bytes(b.A))
    db = sum(1 for a, b in zip(co.frames, cn.frames) if bytes(a.B) != bytes(b.B))
    same_len = len(co.frames) == len(cn.frames)
    ok = same_len and da == 0 and db == 0
    bad += 0 if ok else 1
    print(f"{cid}: status old {so} new {sn}; frames old {len(co.frames)} new {len(cn.frames)}; differing A {da} B {db}; {'IDENTICAL' if ok else 'DIFFERENT'}")
print(f"cases {len(rn['cases'])}; differing or not compared: {bad}")
raise SystemExit(bad)
