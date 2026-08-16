"""Offline replay of AP generation / VP acquire sequences for K1AudioFrame."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness"))
from k1_scheduling_gate0 import select_contract  # noqa: E402


def replay(frames: list[dict], contract: dict) -> dict:
    vp_budget = next(
        c["budget_p99_us"]
        for c in contract["feature_latency_contracts"]
        if c["feature"] == "vp_generation_age"
    )
    published = 0
    acquired = 0
    skip = 0
    mixed = 0
    onset_hist: Counter[int] = Counter()
    beat_hist: Counter[int] = Counter()
    epoch_resync = 0
    phantom = 0
    max_age = 0
    last_onset = None
    last_beat = None
    last_onset_epoch = None
    last_pub_gen = None
    last_acq_gen = None

    for row in frames:
        kind = row["kind"]
        if kind == "publish":
            published += 1
            gen = int(row["ap_generation"])
            if last_pub_gen is not None and gen > last_pub_gen + 1:
                skip += gen - last_pub_gen - 1
            last_pub_gen = gen
        elif kind == "acquire":
            acquired += 1
            gen = int(row["ap_generation"])
            payload_gen = int(row.get("payload_generation", gen))
            if payload_gen != gen:
                mixed += 1
            age = int(row.get("vp_generation_age_us", 0))
            max_age = max(max_age, age)
            onset = int(row["onset_sequence_total"])
            beat = int(row["beat_sequence_total"])
            onset_epoch = int(row["onset_epoch"])
            if last_onset_epoch is not None and onset_epoch != last_onset_epoch:
                epoch_resync += 1
                if last_onset is not None and ((onset - last_onset) & 0xFFFFFFFF) > 1000:
                    phantom += 1
            elif last_onset is not None:
                onset_hist[(onset - last_onset) & 0xFFFFFFFF] += 1
                beat_hist[(beat - last_beat) & 0xFFFFFFFF] += 1
            last_onset = onset
            last_beat = beat
            last_onset_epoch = onset_epoch
            last_acq_gen = gen
            if last_pub_gen is not None and gen < last_pub_gen:
                skip += last_pub_gen - gen

    return {
        "generations_published": published,
        "generations_acquired": acquired,
        "generation_skip_count": skip,
        "mixed_generation_count": mixed,
        "onset_delta_histogram": {str(k): v for k, v in sorted(onset_hist.items())},
        "beat_delta_histogram": {str(k): v for k, v in sorted(beat_hist.items())},
        "epoch_resynchronisations": epoch_resync,
        "phantom_burst_count": phantom,
        "max_vp_generation_age_us": max_age,
        "vp_generation_age_budget_p99_us": vp_budget,
        "last_acquired_generation": last_acq_gen,
        "pass": mixed == 0 and phantom == 0 and max_age <= vp_budget,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    selection = select_contract(
        ROOT,
        deployed_contract_path=args.contract if args.contract.is_file() else None,
    )
    contract = json.loads(Path(selection.selected_contract_path).read_text(encoding="utf-8"))
    frames = []
    with args.capture.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                frames.append(json.loads(line))
    result = replay(frames, contract)
    result["contract_id"] = selection.selected_contract_id
    result["selected_contract_sha256"] = selection.selected_contract_sha256
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "output": str(args.output)}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
