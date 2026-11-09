#!/usr/bin/env python3
"""Prove (or refute) the resync preamble against the real firmware scanner for every device
start state, and confirm the partial-frame hazard without it. Writes raw/preamble_proof.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
sys.path.insert(0, str(LANE))
import audit_prsm_bytes as apb  # noqa: E402

STREAM = (LANE / "fixtures" / "constant.prsm").read_bytes()
FRAME0 = STREAM[:34]


def stale(variant: str, f: int) -> bytes:
    if variant == "frame":
        return FRAME0[:f]
    return b"PRSM"[:min(f, 4)] + b"\xff" * max(0, f - 4)


def summarise(r):
    return {k: r[k] for k in ("eligible", "frames_accepted", "actionable_hotkeys",
                              "command_mode_entries", "command_mode_bytes_swallowed",
                              "pre_existing_line_executed")} | {
        "ours_executed": len(r["commands_executed_ours"]),
        "stale_frames": [(s["mapped"], s["hz"]) for s in r["stale_frames_completed"]],
        "reasons": r["reasons"]}


def main():
    out = {"stream": "fixtures/constant.prsm (24 frames)", "preamble_hex": apb.PREAMBLE.hex(),
           "without_preamble": {}, "with_preamble": {}, "command_mode_with_preamble": {}}
    for variant in ("frame", "ff"):
        for f in range(34):
            key = f"{variant}/fill{f}"
            out["without_preamble"][key] = summarise(
                apb.audit(STREAM, preamble=False, fill=f, stale=stale(variant, f)))
            out["with_preamble"][key] = summarise(
                apb.audit(STREAM, preamble=True, fill=f, stale=stale(variant, f)))
    for pending in (0, 1, 20, 126):
        for f in (0, 1, 3, 4, 5, 6, 18, 20, 33):
            key = f"pending{pending}/fill{f}"
            out["command_mode_with_preamble"][key] = summarise(
                apb.audit(STREAM, preamble=True, fill=f, stale=stale("frame", f), cmd=pending))
    out["command_mode_without_preamble"] = {
        f"pending{pending}": summarise(apb.audit(STREAM, preamble=False, cmd=pending))
        for pending in (0, 20)}

    wp = out["with_preamble"]
    cm = out["command_mode_with_preamble"]
    out["verdict"] = {
        "with_preamble_all_68_states_eligible": all(v["eligible"] for v in wp.values()),
        "with_preamble_max_hotkeys": max(v["actionable_hotkeys"] for v in wp.values()),
        "command_mode_all_states_eligible": all(v["eligible"] for v in cm.values()),
        "command_mode_pre_existing_line_executed_when_pending": sorted(
            {k.split('/')[0] for k, v in cm.items() if v["pre_existing_line_executed"]}),
        "without_preamble_unsafe_states": sorted(
            k for k, v in out["without_preamble"].items() if not v["eligible"]),
        "stale_frame_accepted_states_with_preamble": sorted(
            k for k, v in wp.items() if any(m for m, _ in v["stale_frames"])),
    }
    (LANE / "raw" / "preamble_proof.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["verdict"], indent=1))


if __name__ == "__main__":
    main()
