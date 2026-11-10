#!/usr/bin/env python3
"""Edge brightness of one captured emulator case: level_stats.py <gates run dir> <case id> [...]
Prints per edge: mean of all 16-bit channel values, mean of the brightest pixel, mean lit pixels."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-emu")
import gates as g
run = Path(sys.argv[1]).resolve()
meta = json.loads((run / "meta.json").read_text()) if (run / "meta.json").is_file() else json.loads((run / "plan.json").read_text())
tree = Path(meta.get("work") or meta["tree"])
sys.path.insert(0, str(tree / "tools/esp_emulator"))
import emu_capture as ec
for cid in sys.argv[2:]:
    c = g.load_case(ec, run / "emu", cid)
    out = [f"{run.name} {cid} frames {c['n_frames']}"]
    for e, i in (("A", 0), ("B", 1)):
        arr = np.stack([np.frombuffer(v[i], ">u2").astype(np.int64) for _, v in sorted(c["frames"].items())])
        px = arr.reshape(len(arr), 160, 3).max(axis=2)
        out.append(f"edge {e}: mean {arr.mean():.1f}  brightest-pixel mean {px.max(axis=1).mean():.1f}  max {arr.max()}  lit px mean {(px > 0).sum(axis=1).mean():.1f}")
    print(" | ".join(out))
