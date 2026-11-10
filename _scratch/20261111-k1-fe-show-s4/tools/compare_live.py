#!/usr/bin/env python3
"""Live regression comparison: per emulator case, count frames whose LED payload differs between two runs.

Usage: compare_live.py --export <export holding tools/esp_emulator> --old <run dir> --new <run dir> [--out <txt>]
Each run dir holds one sub-directory per case with uart.txt (run.py --suite default --profile scenario).
A case passes when both captures decode, hold the same number of frames and 0 frames differ.
"""
import argparse
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--export", type=Path, required=True)
ap.add_argument("--old", type=Path, required=True)
ap.add_argument("--new", type=Path, required=True)
ap.add_argument("--out", type=Path)
a = ap.parse_args()
sys.path.insert(0, str(a.export / "tools" / "esp_emulator"))
import emu_capture as ec  # noqa: E402


def load(case_dir: Path):
    u = case_dir / "uart.txt"
    if not u.exists():
        return None, "no uart.txt"
    try:
        return ec.decode(u.read_text(errors="replace")), None
    except Exception as e:  # report, never hide
        return None, f"decode error: {e}"


old_cases = {p.name for p in a.old.iterdir() if (p / "uart.txt").exists()}
new_cases = {p.name for p in a.new.iterdir() if (p / "uart.txt").exists()}
lines, bad = [], 0
for name in sorted(old_cases | new_cases):
    if name not in old_cases or name not in new_cases:
        lines.append(f"{name:24s} ONLY-IN-{'NEW' if name in new_cases else 'OLD'}")
        continue
    co, eo = load(a.old / name)
    cn, en = load(a.new / name)
    if eo or en:
        bad += 1
        lines.append(f"{name:24s} FAIL old={eo} new={en}")
        continue
    po, pn = ec.native_payload(co), ec.native_payload(cn)
    n = min(len(po), len(pn))
    diff = sum(1 for i in range(n) if po[i] != pn[i])
    ok = diff == 0 and len(po) == len(pn)
    bad += 0 if ok else 1
    lines.append(f"{name:24s} {'PASS' if ok else 'FAIL'} frames old={len(po)} new={len(pn)} differing={diff}")
common = len(old_cases & new_cases)
lines.append(f"cases compared {common}; failing {bad}; old-only {len(old_cases - new_cases)}; new-only {len(new_cases - old_cases)}")
text = "\n".join(lines)
print(text)
if a.out:
    a.out.write_text(text + "\n")
sys.exit(1 if bad else 0)
