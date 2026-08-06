#!/usr/bin/env python3
"""Replay device-captured APDBG novelty through the host k1_tempo harness.

This bridges the K1 mic/AGC/GDFT territory to the existing host tempo map.
`[APDBG]` rows are emitted once per k1_tempo accepted novelty sample. The host
harness expects AP-frame input and performs the same /3 peak-hold decimation
internally, so this script expands each accepted sample into three AP frames
whose final timestamp is the captured `emit_ms`.

No DSP is reimplemented. The only transformation is transport reconstruction:

  APDBG accepted novelty sample -> synthetic 3-frame AP packet -> tempo_replay

Use raw `nov` by default. `nov_scaled` is available only for sensitivity checks;
feeding it into k1_tempo applies the firmware scale logic a second time.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import apstream_ingest as api  # noqa: E402
import tempo_replay as trp  # noqa: E402


FINAL_DEFINES = ["K1_TEMPO_CONF_V2", "K1_TEMPO_FLYWHEEL_V2"]
AP_FRAME_DT_MS = 1000.0 / (12800.0 / 96.0)


def _median(values):
    vals = [float(v) for v in values if v == v]
    return statistics.median(vals) if vals else None


def _parse_tempo_stdout(stdout):
    rows = []
    rawspec = None
    for line in stdout.splitlines():
        if line.startswith("T "):
            parts = line.split()
            if len(parts) >= 7:
                rows.append({
                    "t_ms": int(parts[1]),
                    "bpm": float(parts[2]),
                    "conf": float(parts[3]),
                    "lock": int(parts[4]),
                    "phase01": float(parts[5]),
                    "beat": int(parts[6]),
                })
        elif line.startswith("RAWSPEC"):
            try:
                rawspec = [float(v) for v in line.split()[1:]]
            except ValueError:
                rawspec = None
    return rows, rawspec


def _expanded_ap_frames(apdbg_records, value_key):
    frames = []
    last_emit_ms = None
    for row in apdbg_records:
        if value_key not in row:
            continue
        emit_ms = int(row.get("emit_ms", row.get("t_ms", 0)))
        value = float(row[value_key])
        if last_emit_ms is not None and emit_ms <= last_emit_ms:
            continue
        last_emit_ms = emit_ms

        # Recreate the host k1_tempo accepted-frame cadence:
        # two leading quiet AP frames then the accepted sample on the third
        # frame (which drives emit cadence).
        t0 = max(0, int(round(emit_ms - 2.0 * AP_FRAME_DT_MS)))
        t1 = max(0, int(round(emit_ms - 1.0 * AP_FRAME_DT_MS)))
        t2 = emit_ms
        silence = int(row.get("sil", 0))
        frames.append((t0, 0.0, 0))
        frames.append((t1, 0.0, 0))
        frames.append((t2, value, silence))
    return frames


def replay_apdbg(log_path, defines, value_key="nov", compiler="clang++"):
    parsed = api.load_apstream(log_path)
    if parsed is None:
        raise FileNotFoundError(log_path)
    records = parsed["ap_frontend_debug"]["records"]
    frames = _expanded_ap_frames(records, value_key=value_key)
    if not frames:
        raise ValueError(f"no APDBG frames with key {value_key!r} in {log_path}")

    text = "\n".join(f"{ms} {nov:.6f} {sil}" for ms, nov, sil in frames) + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        ok, binary, comp = trp.build_binary(tmp, compiler=compiler, defines=defines)
        if not ok:
            return {"ok": False, "stage": "compile", "compile": comp}
        run = trp.replay_stdin(binary, text)

    tempo_rows, rawspec = _parse_tempo_stdout(run["stdout"])
    device_bpm = [r.get("bpm") for r in records if "bpm" in r]
    device_conf = [r.get("conf") for r in records if "conf" in r]
    replay_bpm = [r["bpm"] for r in tempo_rows]
    replay_conf = [r["conf"] for r in tempo_rows]

    return {
        "ok": bool(run["ok"]),
        "stage": "run",
        "source_log": str(log_path),
        "value_key": value_key,
        "defines": defines,
        "apdbg_records": len(records),
        "expanded_ap_frames": len(frames),
        "tempo_rows": len(tempo_rows),
        "device_summary": {
            "bpm_median": _median(device_bpm),
            "conf_median": _median(device_conf),
            "lock_count": int(sum(int(r.get("lock", 0)) for r in records)),
            "beat_count": int(sum(int(r.get("beat", 0)) for r in records)),
        },
        "replay_summary": {
            "bpm_median": _median(replay_bpm),
            "conf_median": _median(replay_conf),
            "lock_count": int(sum(r["lock"] for r in tempo_rows)),
            "beat_count": int(sum(r["beat"] for r in tempo_rows)),
        },
        "tempo_rows_head": tempo_rows[:12],
        "rawspec": rawspec,
        "stderr": run["stderr"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", help="serial log containing [APDBG] rows")
    parser.add_argument("--value-key", default="nov", choices=["nov", "nov_scaled"],
                        help="APDBG novelty field to replay; default raw nov")
    parser.add_argument("--define", action="append", default=[],
                        help="extra -D preprocessor define; defaults to final tempo flags")
    parser.add_argument("--baseline", action="store_true",
                        help="use baseline k1_tempo with no final flags")
    parser.add_argument("--compiler", default="clang++")
    parser.add_argument("--out", help="optional JSON output path")
    args = parser.parse_args(argv)

    defines = [] if args.baseline else list(FINAL_DEFINES)
    defines.extend(args.define)
    result = replay_apdbg(args.log, defines=defines, value_key=args.value_key, compiler=args.compiler)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=1), encoding="utf-8")

    print(json.dumps(result, indent=1))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
