#!/usr/bin/env python3
"""Apply the S4 selection rule (AFE2 plan section 6, written before the runs) to analyse_s4.py outputs.
Per track x mode, variant against the agc case of the same track, level and mode:
  r up (>= agc r - 0.02, i.e. not down beyond rounding), contrast up (>= agc - 0.02), movement kept >= 85 %,
  hue bins >= agc - 0.5, band-at-0 % and band-at-ceiling % <= agc + 5, tempo-locked % >= agc - 10.
A variant passes if every mode passes on at least 4 of 5 tracks.
Usage: score_s4.py <variant> <agc s4.json> <variant s4.json> [<out md>]
Note: 'up' is read with a 0.02 rounding allowance, stated here before scoring attempt 2."""
import json, sys
from collections import defaultdict
var, fa, fv = sys.argv[1], sys.argv[2], sys.argv[3]
A = json.load(open(fa))["cases"]; Vc = json.load(open(fv))["cases"]
rows, perm = [], defaultdict(int)
for cid, v in sorted(Vc.items()):
    if not cid.endswith("-" + var):
        continue
    base = cid[: -len(var)] + "agc"
    a = A[base]
    mk = v["movement_loud"] / a["movement_loud"]
    checks = {"r": v["r"] >= a["r"] - 0.02, "contrast": v["contrast"] >= a["contrast"] - 0.02, "movement": mk >= 0.85,
              "hue": v["hue_bins"] >= a["hue_bins"] - 0.5, "at0": v.get("stuck0_pct", 0) <= a.get("stuck0_pct", 0) + 5,
              "ceil": v.get("stuck1_pct", 0) <= a.get("stuck1_pct", 0) + 5, "tempo": v.get("lock_pct", 0) >= a.get("lock_pct", 0) - 10}
    ok = all(checks.values())
    _, key, lvl, mode, _ = cid.split("-")
    perm[mode] += ok
    rows.append(f"| {key} | {lvl} | {mode[1:]} | {a['r']:+.2f} → {v['r']:+.2f} | {a['contrast']:.2f} → {v['contrast']:.2f} | {100*mk:.0f} % | "
                f"{a['hue_bins']:.1f} → {v['hue_bins']:.1f} | {v.get('stuck0_pct',0):.1f} / {v.get('stuck1_pct',0):.1f} | "
                f"{a.get('lock_pct',0):.0f} → {v.get('lock_pct',0):.0f} | {'PASS' if ok else 'fail: ' + ', '.join(k for k, x in checks.items() if not x)} |")
modes = sorted(perm)
verdict = all(perm[m] >= 4 for m in modes)
out = ["| track | level | mode | r agc → new | contrast | movement kept | hue bins | band at 0 / ceiling % | tempo locked % | rule |",
       "|---|---|---|---|---|---|---|---|---|---|"] + rows + ["",
       "Per mode, tracks passing: " + ", ".join(f"mode {m[1:]} {perm[m]}/5" for m in modes),
       f"VARIANT {var}: {'PASSES' if verdict else 'FAILS'} the rule (every mode on >= 4 of 5 tracks)"]
txt = "\n".join(out) + "\n"
print(txt)
if len(sys.argv) > 4:
    open(sys.argv[4], "w").write(txt)
