#!/usr/bin/env python3
"""Run the K1 AP cadence timing matrix on the 127 BPM click control.

This is a non-shippable diagnostic runner. It flashes probe environments,
sets the runtime audio config to match each binary's declared timing map,
captures APCAD rows, extracts the accepted NOV stream, and replays that stream
through the host tempo harness at the declared rate.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import serial

import device_ap_cadence_capture as apcad


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "build/audio-semantic-metrics/device-ap-cadence-matrix"

VARIANTS = [
    {
        "label": "a_12800_96_d3",
        "env": "k1_ap_frontend_probe_matrix_12800_96_d3",
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "decimation": 3,
        "dma_desc": 3,
        "purpose": "current baseline with DMA cushion",
    },
    {
        "label": "a2_12800_96_d3_ap0_vp1",
        "env": "k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1",
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "decimation": 3,
        "dma_desc": 3,
        "expected_ap_core": 0,
        "expected_vp_core": 1,
        "purpose": "core-isolation test on current timing map",
    },
    {
        "label": "b_12800_128_d2",
        "env": "k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1",
        "sample_rate": 12800,
        "samples_per_chunk": 128,
        "decimation": 2,
        "dma_desc": 3,
        "expected_ap_core": 0,
        "expected_vp_core": 1,
        "purpose": "100 Hz AP budget-isolation test",
    },
    {
        "label": "c_16000_120_d3_ap0_vp1",
        "env": "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
        "sample_rate": 16000,
        "samples_per_chunk": 120,
        "decimation": 3,
        "dma_desc": 3,
        "expected_ap_core": 0,
        "expected_vp_core": 1,
        "purpose": "BCLK-safe cadence-preserving timing map",
    },
    {
        "label": "d_16000_160_d2",
        "env": "k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1",
        "sample_rate": 16000,
        "samples_per_chunk": 160,
        "decimation": 2,
        "dma_desc": 3,
        "expected_ap_core": 0,
        "expected_vp_core": 1,
        "purpose": "100 Hz AP product-candidate timing map",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/cu.usbmodem2101")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--duration-ms", type=int, default=15000)
    parser.add_argument("--only", action="append", help="variant label to run; may be repeated")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--skip-config", action="store_true")
    parser.add_argument("--no-stop-early", action="store_true")
    parser.add_argument("--replay-warm-ms", type=int, default=5000)
    return parser.parse_args()


def run_cmd(cmd: list[str], cwd: Path = ROOT, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stdout}")
    return result


def ensure_no_afplay() -> None:
    result = subprocess.run(["ps", "-ax", "-o", "pid,command"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    offenders = [line for line in result.stdout.splitlines() if "afplay" in line and "device_ap_cadence_matrix.py" not in line]
    if offenders:
        raise RuntimeError("afplay is already running; refusing to start overlapping audio:\n" + "\n".join(offenders))


def send_rebooting_config(port: str, baud: int, cmd: str) -> None:
    with serial.Serial(port, baud, timeout=0.05, write_timeout=1.0) as ser:
        ser.dtr = True
        ser.rts = True
        time.sleep(3.0)
        ser.reset_input_buffer()
        ser.write((f":{cmd}\n").encode("utf-8"))
        ser.flush()
        time.sleep(0.7)
    time.sleep(5.0)


def configure_device(port: str, baud: int, sample_rate: int, samples_per_chunk: int) -> None:
    send_rebooting_config(port, baud, f"sample_rate={sample_rate}")
    send_rebooting_config(port, baud, f"samples_per_chunk={samples_per_chunk}")


def parse_runner_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError(f"no JSON object found in command output:\n{text}")
    return json.loads(text[start : end + 1])


def write_nov_from_apcad(apcad_log: Path, out_path: Path) -> int:
    rows, metadata = apcad.parse_apcad_rows(apcad_log.read_text(errors="replace").splitlines())
    out_lines = [
        f"NOV_CAPTURE_BEGIN,count={sum(1 for row in rows if int(apcad.numeric(row, 'emitted')) == 1)},source=apcad",
    ]
    seen: set[int] = set()
    for row in rows:
        if int(apcad.numeric(row, "emitted")) != 1:
            continue
        emit = int(apcad.numeric(row, "emit"))
        if emit in seen:
            continue
        seen.add(emit)
        out_lines.append(
            "NOV,"
            f"t={int(apcad.numeric(row, 'emit_ms'))},"
            f"emit={emit},"
            f"nov={float(apcad.numeric(row, 'nov')):.5f},"
            f"nov_scaled={float(apcad.numeric(row, 'nov_scaled')):.5f},"
            "scale=1.00000,"
            f"sil={int(apcad.numeric(row, 'sil'))},"
            f"acf={int(apcad.numeric(row, 'acf'))},"
            "src=buf"
        )
    out_lines.append(f"NOV_CAPTURE_DONE,count={len(seen)},dropped={metadata.get('done', {}).get('dropped', 0)}")
    out_path.write_text("\n".join(out_lines) + "\n")
    return len(seen)


def gate_variant(summary: dict, replay: dict, variant: dict) -> dict:
    sample_rate = variant["sample_rate"]
    chunk = variant["samples_per_chunk"]
    decim = variant["decimation"]
    dma_desc = variant["dma_desc"]
    ap_hz = sample_rate / chunk
    nov_hz = ap_hz / decim
    period_ms = 1000.0 / ap_hz

    measured_ap = summary.get("measured_ap_frame_rate_hz")
    measured_nov = summary.get("measured_emitted_novelty_rate_hz")
    timing = summary.get("timing_us", {}).get("total_ap_loop_elapsed_us", {})
    median_total_ms = (timing.get("median") / 1000.0) if isinstance(timing.get("median"), (int, float)) else None
    p95_total_ms = (timing.get("p95") / 1000.0) if isinstance(timing.get("p95"), (int, float)) else None
    max_total_ms = (timing.get("max") / 1000.0) if isinstance(timing.get("max"), (int, float)) else None
    observed_ap_cores = summary.get("unique_ap_core_id", []) or []
    observed_vp_cores = summary.get("unique_vp_core_id", []) or []
    replay_summary = replay.get("replay_summary", {})
    warm = replay_summary.get("warm_frame_count", 0) or 0
    near = replay_summary.get("warm_high_or_locked_near_127_rows", 0) or 0
    high_or_locked = replay_summary.get("warm_high_or_locked_count", 0) or 0
    warm_counts = replay_summary.get("warm_bpm_counts", {}) or {}
    dominant_bpm = int(next(iter(warm_counts.keys()))) if warm_counts else None

    def close(measured: float | None, expected: float, tol: float = 0.02) -> bool:
        return isinstance(measured, (int, float)) and math.isfinite(measured) and abs(measured - expected) / expected <= tol

    gates = {
        "ap_rate_within_2pct": close(measured_ap, ap_hz),
        "nov_rate_within_2pct": close(measured_nov, nov_hz),
        "p95_total_lt_T": isinstance(p95_total_ms, (int, float)) and p95_total_ms < period_ms,
        "max_total_le_dma_cushion": isinstance(max_total_ms, (int, float)) and max_total_ms <= dma_desc * period_ms,
        "i2s_status_clean": summary.get("i2s_not_ok_count") == 0 and summary.get("bytes_mismatch_count") == 0,
        "click_replay_near_127": bool(124 <= (dominant_bpm or 0) <= 130 and high_or_locked > 0 and near / high_or_locked >= 0.60),
    }
    if "expected_ap_core" in variant:
        gates["ap_core_matches_expected"] = observed_ap_cores == [variant["expected_ap_core"]]
    if "expected_vp_core" in variant:
        gates["vp_core_matches_expected"] = observed_vp_cores == [variant["expected_vp_core"]]
    cadence_replay_contract_keys = [
        key for key in gates
        if key not in {"p95_total_lt_T", "max_total_le_dma_cushion"}
    ]
    cadence_replay_contract_passed = all(gates[key] for key in cadence_replay_contract_keys)
    timing_budget_passed = gates["p95_total_lt_T"] and gates["max_total_le_dma_cushion"]
    return {
        "expected_ap_rate_hz": ap_hz,
        "expected_nov_rate_hz": nov_hz,
        "period_ms": period_ms,
        "measured_ap_rate_hz": measured_ap,
        "measured_nov_rate_hz": measured_nov,
        "total_loop_ms": {"median": median_total_ms, "p95": p95_total_ms, "max": max_total_ms},
        "observed_ap_core_id": observed_ap_cores,
        "observed_vp_core_id": observed_vp_cores,
        "dominant_replay_bpm": dominant_bpm,
        "warm_high_or_locked_near_127_rows": near,
        "warm_high_or_locked_rows": high_or_locked,
        "gates": gates,
        "cadence_replay_contract_passed": cadence_replay_contract_passed,
        "timing_budget_passed": timing_budget_passed,
        "passed": all(gates.values()),
    }


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = [v for v in VARIANTS if not args.only or v["label"] in set(args.only)]
    if not selected:
        raise RuntimeError("no variants selected")

    identity = apcad.serial_identity(args.port)
    if identity is None:
        raise RuntimeError(f"serial port not found: {args.port}")
    ensure_no_afplay()

    matrix: dict[str, object] = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "port": args.port,
        "serial_identity": identity,
        "duration_ms": args.duration_ms,
        "variants": [],
        "non_actions": ["no calibration command", "no production DSP tuning", "no Loreen run"],
    }

    for variant in selected:
        label = variant["label"]
        env = variant["env"]
        if not args.skip_upload:
            upload = run_cmd(["pio", "run", "-e", env, "-t", "upload", "--upload-port", args.port], timeout=90)
        else:
            upload = subprocess.CompletedProcess([], 0, stdout="upload skipped")
        if not args.skip_config:
            configure_device(args.port, args.baud, variant["sample_rate"], variant["samples_per_chunk"])

        capture_cmd = [
            sys.executable,
            str(ROOT / "scripts/regression-harness/device_ap_cadence_capture.py"),
            "--port",
            args.port,
            "--duration-ms",
            str(args.duration_ms),
            "--label",
            label,
            "--out-dir",
            str(out_dir),
            "--expected-sample-rate",
            str(variant["sample_rate"]),
            "--expected-samples-per-chunk",
            str(variant["samples_per_chunk"]),
            "--expected-novelty-decimation",
            str(variant["decimation"]),
        ]
        capture = run_cmd(capture_cmd, timeout=max(60, args.duration_ms // 1000 + 40))
        capture_meta = parse_runner_json(capture.stdout)
        summary_path = Path(capture_meta["summary_json"])
        apcad_log = Path(capture_meta["apcad_log"])
        summary = json.loads(summary_path.read_text())

        nov_log = out_dir / f"{label}__nov_from_apcad.log"
        nov_rows = write_nov_from_apcad(apcad_log, nov_log)
        ap_hz = variant["sample_rate"] / variant["samples_per_chunk"]
        nov_hz = ap_hz / variant["decimation"]
        replay_json = out_dir / f"{label}__declared_rate_replay.json"
        replay_traj = out_dir / f"{label}__declared_rate_replay_trajectory.log"
        replay_stdin = out_dir / f"{label}__declared_rate_replay_input.txt"
        replay_cmd = [
            sys.executable,
            str(ROOT / "scripts/regression-harness/device_novelty_replay.py"),
            str(nov_log),
            "--novelty-rate-hz",
            f"{nov_hz:.9f}",
            "--ap-frame-hz",
            f"{ap_hz:.9f}",
            "--decimation",
            str(variant["decimation"]),
            "--out",
            str(replay_json),
            "--trajectory-out",
            str(replay_traj),
            "--stdin-out",
            str(replay_stdin),
            "--warm-ms",
            str(args.replay_warm_ms),
        ]
        run_cmd(replay_cmd, timeout=60)
        replay = json.loads(replay_json.read_text())
        gate = gate_variant(summary, replay, variant)
        matrix["variants"].append(
            {
                **variant,
                "upload_tail": "\n".join(upload.stdout.splitlines()[-20:]),
                "capture_summary": str(summary_path),
                "apcad_log": str(apcad_log),
                "nov_from_apcad": str(nov_log),
                "nov_rows": nov_rows,
                "declared_rate_replay": str(replay_json),
                "gate": gate,
            }
        )
        if not args.no_stop_early:
            if label == "a_12800_96_d3" and gate["cadence_replay_contract_passed"]:
                matrix["stop_reason"] = "current timing map cadence/replay contract passed with DMA desc 3"
                break
            if label == "a2_12800_96_d3_ap0_vp1" and gate["cadence_replay_contract_passed"]:
                matrix["stop_reason"] = "core isolation rescued current timing map cadence/replay contract"
                break
            if label == "b_12800_128_d2" and not gate["cadence_replay_contract_passed"]:
                matrix["stop_reason"] = "100 Hz budget-isolation cadence/replay contract failed; skipping 16k/160"
                break

    matrix_path = out_dir / f"ap_cadence_matrix_{time.strftime('%Y%m%d_%H%M%S')}__summary.json"
    matrix_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"matrix_summary": str(matrix_path), "variants": len(matrix["variants"])}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
