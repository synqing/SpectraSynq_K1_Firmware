#!/usr/bin/env python3
"""Paired control for the one S3/S31 difference (startup-sqr).

startup-sqr is the only maintained case on the boot_monotonic epoch: its clock follows the
emulated timer from reset, so it inherits each chip's emulated boot time. This runs the same
case on both chips with the clock declared instead (1.0 s, the policy every other music case
uses), through run.run_case and the unchanged acceptance, then compares the two captures with
emu_capture.deterministic_view and localises any difference with stress_repeat.localise.
If the declared-clock pair matches, the boot-time clock is the cause of the original difference.

    python3 startup_epoch_control.py --output <fresh dir>
"""
import argparse
import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "tools/esp_emulator"))
import emu_capture as ec  # noqa: E402
import run  # noqa: E402
import stress_repeat as sr  # noqa: E402


def one(scenario: str, out: Path, emu: Path) -> tuple[dict, Path]:
    sc = run.select_profile(run.load_scenario(REPO / scenario), "fe")
    case = copy.deepcopy(sc["cases"]["startup-sqr"])
    case["epoch"] = {"policy": "declared", "us": 1000000}
    sc["cases"]["startup-sqr-declared"] = case
    out.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    run.load_asset(sc, case["pcm"], cache, out)
    rec = run.run_case(sc, "startup-sqr-declared", out, emu, run.build_dir_for(sc, sc["profile"]["env"]), cache, {})
    return rec, out / "startup-sqr-declared" / "uart.txt"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    out = Path(ap.parse_args().output).resolve()
    emu, _ = run.resolve_esp_emu(json.loads((REPO / "tools/esp_emulator/tool-lock.json").read_text()))
    r3, u3 = one("tools/esp_emulator/s3_music_regression.json", out / "s3", emu)
    r31, u31 = one("tools/esp_emulator/s31_music_regression.json", out / "s31", emu)
    a = ec.decode(u3.read_text(errors="replace"))
    b = ec.decode(u31.read_text(errors="replace"))
    res = {"label": "simulated, not hardware", "s3_status": r3["status"], "s31_status": r31["status"],
           "frames": [len(a.frames), len(b.frames)],
           "equal": ec.deterministic_view(a) == ec.deterministic_view(b),
           "localise": sr.localise(a, b)}
    (out / "control.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps(res, indent=1, default=str))
    return 0 if res["equal"] and r3["status"] == r31["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
