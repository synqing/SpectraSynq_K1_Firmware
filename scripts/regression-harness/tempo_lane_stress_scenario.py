#!/usr/bin/env python3
"""Derived scenario for determinism repeats of a lane image (lane R1, Captain supplement 2026-10-21, item 3).

tools/esp_emulator/stress_repeat.py takes the emulator env from the scenario profile. This writes a copy of
s3_music_regression.json whose profile names the lane image and which adds one case, `consumer-music-a`:
the R3 music-a case with Tempo Comet (edge A) and Tempo Comet Anticipate (edge B) selected through the
production command parser at hop 0, so the repeats exercise the repaired consumers as well as the tracker.
Nothing else in the scenario changes; asset paths resolve from the repository root as before.

  tempo_lane_stress_scenario.py --env k1_main_rpl_emu_tempo_r1_lockoff --out DIR/scenario.json
  python3 tools/esp_emulator/stress_repeat.py run --scenario DIR/scenario.json --case consumer-music-a \
      --runs 20 --parallel 8 --output DIR/runs [--no-trace]
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tools/esp_emulator/s3_music_regression.json"
CASE = "consumer-music-a"


def derive(env: str) -> dict:
    sc = json.loads(BASE.read_text())
    sc["profile"]["env"] = env
    case = copy.deepcopy(sc["cases"]["music-a"])
    case["purpose"] = ("Lane R1 repeat case: R3 music-a with Tempo Comet on A and Tempo Comet Anticipate on B "
                       "(production set_mode / secondary_mode at hop 0).")
    case["commands"] = [{"hop": 0, "text": "set_mode=20"}, {"hop": 0, "text": "secondary_mode=27"}]
    sc["cases"][CASE] = case
    return sc


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(derive(a.env), indent=1) + "\n")
    print(f"scenario for {a.env} with case {CASE} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
