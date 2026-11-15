#!/usr/bin/env python3
"""Compare two emulator runs of the same scenario on different chips, case by case.

    python3 tools/esp_emulator/cross_chip_compare.py \
        --base _scratch/esp-emulator/<s3-run> --other _scratch/esp-emulator/<s31-run> \
        --output _scratch/esp-emulator/<s31-run>/cross-chip.json

Uses the existing comparison code only: a case matches when emu_capture.deterministic_view
(payload of both edges plus per-frame source metadata, the test the suite's "equal"
comparisons use) is identical. No tolerance exists or is added. For a case that differs,
stress_repeat.localise reports where the second run first departs (producer, handoff or
render) and the measured size of the difference is given per edge (frames differing,
pixels differing, largest 16-bit channel difference). Every number is simulated, not
hardware. Exit status is 0 only when every compared case matches exactly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import emu_capture as ec  # noqa: E402
import stress_repeat as sr  # noqa: E402


def edge_difference(a: ec.Capture, b: ec.Capture) -> dict:
    out = {}
    for edge in ("A", "B"):
        frames = pixels = 0
        worst = 0
        for f, g in zip(a.frames, b.frames):
            pa, pb = ec.wire_to_rgb16(getattr(f, edge)), ec.wire_to_rgb16(getattr(g, edge))
            diff = [max(abs(x - y) for x, y in zip(p, q)) for p, q in zip(pa, pb) if p != q]
            if diff:
                frames += 1
                pixels += len(diff)
                worst = max(worst, max(diff))
        out[edge] = {"frames_differing": frames, "pixels_differing": pixels, "max_channel_diff_rgb16": worst}
    return out


def compare_case(base_dir: Path, other_dir: Path, cid: str, base_status: str, other_status: str) -> dict:
    rec = {"case": cid, "base_status": base_status, "other_status": other_status}
    if base_status != "PASS" or other_status != "PASS":
        rec["result"] = "NOT_COMPARED"
        rec["reason"] = "a case must be accepted on both chips before its frames are compared"
        return rec
    a = ec.decode((base_dir / cid / "uart.txt").read_text(errors="replace"))
    b = ec.decode((other_dir / cid / "uart.txt").read_text(errors="replace"))
    va, vb = ec.deterministic_view(a), ec.deterministic_view(b)
    rec.update(frames_base=len(a.frames), frames_other=len(b.frames),
               payload_sha256_base=ec.payload_sha256(a), payload_sha256_other=ec.payload_sha256(b),
               metadata_frames_differing=sum(1 for x, y in zip(va, vb) if x[4] != y[4]))
    rec["equal"] = va == vb
    rec["result"] = "MATCH" if rec["equal"] else "DIFFER"
    if not rec["equal"]:
        rec["difference"] = edge_difference(a, b)
        rec["first_divergence"] = sr.localise(a, b)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", required=True, help="run folder of the reference chip (S3)")
    ap.add_argument("--other", required=True, help="run folder of the chip under test (S31)")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    base, other = Path(args.base), Path(args.other)
    rb = json.loads((base / "result.json").read_text())
    ro = json.loads((other / "result.json").read_text())
    cases = [c for c in rb["cases"] if c in ro["cases"]]
    report = {
        "schema": "k1-emu-cross-chip/1", "label": "simulated, not hardware",
        "base": {"run": str(base), "chip": rb["profile"]["emulator"]["chip"], "source": rb["source"].get("head"),
                 "scenario_sha256": rb["scenario"]["sha256"]},
        "other": {"run": str(other), "chip": ro["profile"]["emulator"]["chip"], "source": ro["source"].get("head"),
                  "scenario_sha256": ro["scenario"]["sha256"]},
        "only_in_base": sorted(set(rb["cases"]) - set(ro["cases"])),
        "only_in_other": sorted(set(ro["cases"]) - set(rb["cases"])),
        "cases": [compare_case(base, other, c, rb["cases"][c]["status"], ro["cases"][c]["status"]) for c in cases],
    }
    report["summary"] = {k: sum(1 for c in report["cases"] if c["result"] == k)
                         for k in ("MATCH", "DIFFER", "NOT_COMPARED")}
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    for c in report["cases"]:
        extra = ""
        if c["result"] == "DIFFER":
            d = c["difference"]
            extra = (f" A:{d['A']['frames_differing']}fr/{d['A']['max_channel_diff_rgb16']}max "
                     f"B:{d['B']['frames_differing']}fr/{d['B']['max_channel_diff_rgb16']}max "
                     f"side={c['first_divergence'].get('side')}")
        elif c["result"] == "NOT_COMPARED":
            extra = f" ({c['base_status']}/{c['other_status']})"
        print(f"{c['case']:22} {c['result']}{extra}")
    print("summary", report["summary"], "(simulated, not hardware)")
    ok = report["summary"]["DIFFER"] == 0 and report["summary"]["NOT_COMPARED"] == 0 and report["cases"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
