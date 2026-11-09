#!/usr/bin/env python3
"""C4 analysis over one or more run directories (PROTOTYPE ADAPTER runs).

Decodes each accepted case's uart.txt with the export's own emu_capture (no new decoder),
then reports per case: native A/B payload sha256 (ec.payload_sha256), authored-state
transitions (EMU_AUTH), RX accounting (EMU_RX_END), show-state changes after the hop-0
composition (EMU_SS when=shown — hotkeys reaching state), and per pair: first differing hop
and the count of differing captured frames per edge.
Usage: analyse_c4.py OUT.json RUN_DIR [RUN_DIR ...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src-407fdf6f" / "tools" / "esp_emulator"))
import emu_capture as ec  # noqa: E402

HOP = 96


def load(run: Path, cid: str):
    uart = (run / cid / "uart.txt").read_text(errors="replace")
    cap = ec.decode(uart)
    frames = {}
    for f in cap.frames:
        h = ec.frame_hop(cap, f, HOP)
        frames[h] = (bytes(f.A), bytes(f.B))
    auth = [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r"EMU_AUTH after_hop=(-?\d+) state=(\d+)", uart)]
    rx_end = re.search(r"EMU_RX_END (.*)", uart)
    shown = [s for s in cap.show_states if s.get("when") == "shown" and int(s.get("hop", 0)) > 1]
    return {"cap": cap, "frames": frames, "auth": auth, "rx_end": rx_end.group(1) if rx_end else None,
            "shown_changes": [(int(s["hop"]), s["hex"]) for s in shown]}


def diff(a, b, from_hop=None):
    hops = sorted(set(a["frames"]) & set(b["frames"]))
    if from_hop is not None:
        hops = [h for h in hops if h >= from_hop]
    first = None
    da = db = 0
    last_diff = None
    for h in hops:
        fa, fb = a["frames"][h], b["frames"][h]
        d = (fa[0] != fb[0], fa[1] != fb[1])
        da += d[0]
        db += d[1]
        if any(d):
            last_diff = h
            if first is None:
                first = h
    return {"compared_frames": len(hops), "first_diff_hop": first, "last_diff_hop": last_diff,
            "diff_frames_A": da, "diff_frames_B": db, "identical": first is None}


def main() -> int:
    out = Path(sys.argv[1])
    cases = {}
    for run in map(Path, sys.argv[2:]):
        res = json.loads((run / "result.json").read_text())
        for cid, rec in res["cases"].items():
            if rec.get("status") != "PASS" or cid.startswith("smoke"):
                continue
            c = load(run, cid)
            c["run"] = str(run)
            c["sha"] = ec.payload_sha256(c["cap"])
            c["rx"] = rec.get("rx_stream")
            cases[cid] = c
    rep = {"cases": {k: {"run": v["run"], "payload_sha256": v["sha"], "frames": len(v["frames"]),
                         "auth_transitions": v["auth"], "rx_end": v["rx_end"], "rx_stream": v["rx"],
                         "show_state_changes_after_hop1": len(v["shown_changes"]),
                         "first_show_state_change_hop": v["shown_changes"][0][0] if v["shown_changes"] else None}
                     for k, v in cases.items()},
           "pairs": {}}
    for tag in ("wfh", "snap"):
        pairs = [("base", "auth-1"), ("auth-1", "auth-2"), ("auth-1", "auth-3"), ("base", "rej-hz0"),
                 ("base", "rej-ver2"), ("base", "rej-hz241"), ("base", "rej-magic"), ("auth-1", "auth-zeropcm"), ("auth-1", "seek"),
                 ("base-dense", "stop")]
        for a, b in pairs:
            ka, kb = f"{tag}-{a}", f"{tag}-{b}"
            if ka in cases and kb in cases:
                rep["pairs"][f"{ka} vs {kb}"] = diff(cases[ka], cases[kb])
    # stop: after the stop + settle, does output return to the live baseline's frames?
    if "wfh-stop" in cases and "wfh-base-dense" in cases:
        s, b = cases["wfh-stop"], cases["wfh-base-dense"]
        hops = sorted(set(s["frames"]) & set(b["frames"]))
        tail_equal_from = None
        for h in reversed(hops):
            if s["frames"][h] != b["frames"][h]:
                break
            tail_equal_from = h
        rep["stop"] = {"tail_byte_identical_to_baseline_from_hop": tail_equal_from, "window": [hops[0], hops[-1]],
                       "auth": s["auth"]}
    out.write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
