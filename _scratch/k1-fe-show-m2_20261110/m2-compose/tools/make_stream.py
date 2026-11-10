#!/usr/bin/env python3
"""make_stream — ShowBundle Intent Trace (PRISM VM, tools/showbundle_replay.js @120 Hz) -> prepared
Prim8 stream (.prsm + k1-prim8-stream/0 sidecar) via lane-b prim8_stream.py.

Rows are taken verbatim from the VM replay; this script does no value arithmetic. It asserts that
every trace row lies on the VM tick grid (t_us == tick_time_us(i, hz), i contiguous from the passage
start tick), that the bundle is device_profile "none", and that the stream fits inside the asset.

Usage: make_stream.py --run DIR --project COMPOSITION.json --wav ASSET.wav --out STREAM.prsm [--name N]
  DIR holds showbundle.json, compile_manifest.json, trace_120hz.jsonl (compose.mjs run-a folder).
"""
from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

LANE_B = Path("/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-b")
sys.path.insert(0, str(LANE_B))
import prim8_stream as ps  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--wav", help="decoded asset WAV (identity read from it)")
    ap.add_argument("--asset-json", help="asset identity JSON {sha256,sample_rate,sample_count,channels,path_hint}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hz", type=int, default=120)
    a = ap.parse_args()

    run = Path(a.run)
    bundle = json.loads((run / "showbundle.json").read_text())
    if bundle.get("device_profile", "none") != "none":
        raise SystemExit(f"device_profile {bundle.get('device_profile')} != none")
    trace_path = run / "trace_120hz.jsonl"
    rows = [json.loads(ln) for ln in trace_path.read_text().splitlines() if ln.strip()]

    if a.asset_json:
        asset = json.loads(Path(a.asset_json).read_text())
        asset = {k: asset[k] for k in ("sha256", "sample_rate", "sample_count", "channels", "path_hint",
                                       "decoded_sha256", "decoded_path_hint") if k in asset}
    else:
        with wave.open(a.wav, "rb") as w:
            rate_, count_, ch_ = w.getframerate(), w.getnframes(), w.getnchannels()
        asset = {
            "sha256": ps.sha256_file(a.wav),
            "sample_rate": rate_,
            "sample_count": count_,
            "channels": ch_,
            "path_hint": Path(a.wav).name,
        }
    rate, count = asset["sample_rate"], asset["sample_count"]

    passage_start_sample = 0
    start_tick = ps.first_tick_at_or_after_us(ps.sample_to_us(passage_start_sample, rate), a.hz)
    for k, r in enumerate(rows):
        want = ps.tick_time_us(start_tick + k, a.hz)
        if r["t_us"] != want:
            raise SystemExit(f"trace row {k} t_us {r['t_us']} != tick_time_us {want}")
        if len(r["prim8_u16"]) != 8:
            raise SystemExit(f"trace row {k} has {len(r['prim8_u16'])} values")
    last_us = rows[-1]["t_us"]
    asset_end_us = ps.sample_to_us(count, rate)
    if last_us >= asset_end_us:
        raise SystemExit(f"last t_us {last_us} beyond asset end {asset_end_us}")
    if bundle["duration_us"] > asset_end_us:
        print(f"WARNING bundle duration_us {bundle['duration_us']} > asset end {asset_end_us}")

    frames = ps.build_frames([r["prim8_u16"] for r in rows], a.hz, start_tick, seq0=0)
    project = Path(a.project)
    source = {
        "chain": "composition -> PRISM compiler 0.3.1 (cc00556d) -> ShowBundle 0.3 -> src/vm.js replayToJsonl"
                 " via tools/showbundle_replay.js --hz 120 -> lane-b prim8_stream.build_frames",
        "composition_sha256": ps.sha256_file(project),
        "showbundle_sha256": ps.sha256_file(run / "showbundle.json"),
        "compile_manifest_sha256": ps.sha256_file(run / "compile_manifest.json"),
        "intent_trace_sha256": ps.sha256_file(trace_path),
        "device_profile": "none",
    }
    # The composition file changes when outputs are recorded; hash the inputs block instead so the
    # stream identity depends only on what was authored.
    proj = json.loads(project.read_text())
    source["composition_inputs_sha256"] = ps.sha256_bytes(
        json.dumps(proj["inputs"], sort_keys=True, separators=(",", ":")).encode())
    del source["composition_sha256"]
    side = ps.write_stream(a.out, frames, asset=asset, passage_start_sample=passage_start_sample,
                           hz=a.hz, source=source,
                           notes="Prim8 heat/space/gravity are AUTHORED constants (0) in the profile; "
                                 "unconsumed by FE firmware, not repurposed.")
    print(f"STREAM: wrote {a.out} frames={side['frame_count']} sha256={side['stream_sha256']}")
    print(f"SIDECAR_SHA256={ps.sha256_file(a.out + '.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
