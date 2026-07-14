#!/usr/bin/env python3
"""Score focused effect AP captures without treating sequential playback as paired audio."""

from __future__ import annotations

import argparse
import collections
import json
import re
import shlex
import statistics
from pathlib import Path


AP_RE = re.compile(r"^\[AP\]\s+(.*)$")
TEMPO_RE = re.compile(
    r"^TEMPO,t=(\d+),bpm=([0-9.]+),phase=([0-9.]+),conf=([0-9.]+),"
    r"beat=(\d),lock=(\d),str=([0-9.]+)$"
)
EVENT_RE = re.compile(r"^EVENT_STATUS,(.*)$")
CRASH_RE = re.compile(
    r"Guru Meditation|Backtrace:|rst:0x|watchdog|abort\(\) was called|assert failed|panic(?:'ed|:)",
    re.IGNORECASE,
)
KEY_VALUE_RE = re.compile(r"\b([A-Za-z0-9_]+)=([^\s|,]+)")
LEGACY_EFFECTS = {
    12: ("aurora", "AURORA"),
    16: ("ember", "EMBER FIELD"),
    18: ("waveform_tempo", "WAVEFORM TEMPO"),
    20: ("tempo_comet", "TEMPO COMET"),
    21: ("dense_forge", "DENSE FORGE"),
    23: ("pulse_prism", "PULSE PRISM"),
    24: ("dense_forge_chord", "DENSE FORGE CHORD"),
    26: ("percussion_burst", "PERCUSSION BURST"),
    32: ("waveform_hybrid_k1", "WAVEFORM HYBRID K1"),
}
INTENDED_BY_LABEL = {
    "dense-forge-chord": ("dense_forge_chord", "DENSE FORGE CHORD"),
    "percussion-burst": ("percussion_burst", "PERCUSSION BURST"),
    "tempo-comet": ("tempo_comet", "TEMPO COMET"),
    "waveform-hybrid-k1": ("waveform_hybrid_k1", "WAVEFORM HYBRID K1"),
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    return parser.parse_args()


def number(value: str) -> int | float:
    return float(value) if any(marker in value for marker in (".", "e", "E")) else int(value)


def parse_key_values(payload: str) -> dict[str, int | float | str]:
    values: dict[str, int | float | str] = {}
    for key, raw in KEY_VALUE_RE.findall(payload):
        try:
            values[key] = number(raw)
        except ValueError:
            values[key] = raw
    return values


def median(rows: list[dict[str, object]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if key in row]
    return statistics.median(values) if values else None


def maximum(rows: list[dict[str, object]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if key in row]
    return max(values) if values else None


def id_delta(rows: list[dict[str, object]], key: str) -> int | None:
    values = [int(row[key]) for row in rows if key in row]
    return values[-1] - values[0] if len(values) >= 2 else None


def capture_rerun(summary: dict[str, object]) -> str:
    actions = summary.get("actions") or []
    command = [
        "python3",
        "scripts/regression-harness/device_novelty_buffer_capture.py",
        "--track",
        str(summary["track_file"]),
        "--port",
        str(summary["port"]),
        "--expected-chip-id",
        str(summary["expected_chip_id"]),
        "--expected-build-env",
        str(summary["expected_build_env"]),
        "--duration-ms",
        str(summary["duration_ms_requested"]),
        "--out-dir",
        str(summary["out_dir"]),
        "--label",
        Path(str(summary["raw_log"])).name.split("_nov_buffered_", 1)[0],
        "--set-mode",
        str((summary.get("mode_selection") or {}).get("requested_input", summary.get("set_mode_dense"))),
    ]
    expected_ordinal = (summary.get("mode_selection") or {}).get(
        "expected_ordinal", summary.get("set_mode_dense")
    )
    command.extend(("--expected-mode-ordinal", str(expected_ordinal)))
    if "ap_stream=on" in actions:
        command.append("--capture-ap-stream")
    if "tempo_stream=on" in actions:
        command.append("--capture-tempo-stream")
    if summary.get("apcad_soak"):
        command.append("--capture-apcad-soak")
    period = int(summary.get("event_status_period_ms") or 0)
    if period:
        command.extend(("--event-status-period-ms", str(period)))
    return shlex.join(command)


def intended_effect(summary_path: Path, summary: dict[str, object]) -> tuple[str | None, str | None]:
    selection = summary.get("mode_selection") or {}
    if selection.get("effect_key") and selection.get("effect_name"):
        return str(selection["effect_key"]), str(selection["effect_name"])
    label = summary_path.name.split("_nov_buffered_", 1)[0]
    for marker, effect in INTENDED_BY_LABEL.items():
        if marker in label:
            return effect
    return None, None


def corrected_rerun(summary: dict[str, object], effect_key: str | None) -> str | None:
    if effect_key is None:
        return None
    command = capture_rerun(summary).split()
    set_index = command.index("--set-mode")
    del command[set_index : set_index + 4]
    command.extend(("--set-effect", effect_key))
    return shlex.join(command)


def analyse(summary_path: Path) -> dict[str, object]:
    summary = json.loads(summary_path.read_text())
    raw_path = Path(summary["raw_log"])
    lines = raw_path.read_text(errors="replace").splitlines()
    ap_rows = [parse_key_values(match.group(1)) for line in lines if (match := AP_RE.match(line))]
    event_rows = [parse_key_values(match.group(1)) for line in lines if (match := EVENT_RE.match(line))]
    tempo_rows = [tuple(number(value) for value in match.groups()) for line in lines if (match := TEMPO_RE.match(line))]
    if not ap_rows:
        raise ValueError(f"missing AP rows in {raw_path}")

    validation = summary.get("validation") or {}
    apcad = summary.get("apcad_soak") or {}
    compact = apcad.get("compact_soak") or {}
    crash_lines = [line for line in lines if CRASH_RE.search(line)]
    integrity_errors = list(validation.get("errors") or [])
    for key in ("frame_gap_count", "timestamp_regression_count", "i2s_not_ok_count", "bytes_mismatch_count"):
        if int(apcad.get(key, 0) or 0):
            integrity_errors.append(f"{key}={apcad[key]}")
    if crash_lines:
        integrity_errors.append(f"crash_signatures={len(crash_lines)}")

    selection = summary.get("mode_selection") or {}
    mode = int(selection.get("observed_ordinal", summary.get("set_mode_dense")))
    environment = str(summary["expected_build_env"])
    variant = "v1_off" if environment.endswith("_v1_off") else "v2"
    actual_key, actual_name = LEGACY_EFFECTS.get(mode, (None, f"RAW ORDINAL {mode}"))
    intended_key, intended_name = intended_effect(summary_path, summary)
    selection_matches = intended_key is not None and intended_key == actual_key
    capture_verdict = str(validation.get("verdict", "NOT_VERIFIED"))
    accepted = capture_verdict == "PASS" and not integrity_errors and selection_matches
    tempo_mode = None
    tempo_locked_fraction = None
    if tempo_rows:
        tempo_mode = collections.Counter(round(float(row[1])) for row in tempo_rows).most_common(1)[0][0]
        tempo_locked_fraction = sum(int(row[5]) for row in tempo_rows) / len(tempo_rows)

    return {
        "summary": str(summary_path),
        "raw_log": str(raw_path),
        "variant": variant,
        "actual_effect": actual_name,
        "actual_effect_key": actual_key,
        "intended_effect": intended_name,
        "intended_effect_key": intended_key,
        "effect_selection_verdict": "PASS" if selection_matches else "MISLABELLED_INVALID",
        "mode_ordinal": mode,
        "build_env": environment,
        "chip_id": (summary.get("runtime_identity") or {}).get("chip_id"),
        "capture_verdict": capture_verdict,
        "accepted": accepted,
        "integrity_errors": integrity_errors,
        "ap_rate_hz": compact.get("meas_ap_hz"),
        "active_p95_us": compact.get("active_p95_us"),
        "active_max_us": compact.get("active_max_us"),
        "frame_gaps": apcad.get("frame_gap_count"),
        "i2s_faults": apcad.get("i2s_not_ok_count"),
        "crash_signatures": len(crash_lines),
        "ap": {
            "rows": len(ap_rows),
            "onset_positive_rows": sum(int(row.get("onset", 0)) for row in ap_rows),
            "bass_positive_rows": sum(int(row.get("bass", 0)) for row in ap_rows),
            "max_raw_median": median(ap_rows, "max_raw"),
            "peak_scaled_median": median(ap_rows, "peak_scaled"),
            "peak_scaled_max": maximum(ap_rows, "peak_scaled"),
            "raw_i16_rms_median": median(ap_rows, "raw_i16_rms"),
            "raw_i16_abs_peak_median": median(ap_rows, "raw_i16_abs_peak"),
            "gdft_trim_median": median(ap_rows, "gdft_trim"),
            "agc_gain_median": median(ap_rows, "agc_gain"),
        },
        "events": {
            "rows": len(event_rows),
            "kick_positive_rows": sum(int(row.get("kick", 0)) for row in event_rows),
            "snare_positive_rows": sum(int(row.get("snare", 0)) for row in event_rows),
            "hihat_positive_rows": sum(int(row.get("hihat", 0)) for row in event_rows),
            "transient_id_delta": id_delta(event_rows, "tid"),
            "kick_id_delta": id_delta(event_rows, "kid"),
            "snare_id_delta": id_delta(event_rows, "sid"),
            "hihat_id_delta": id_delta(event_rows, "hid"),
        },
        "tempo": {
            "rows": len(tempo_rows),
            "mode_bpm": tempo_mode,
            "locked_fraction": tempo_locked_fraction,
        },
        "rerun_command": capture_rerun(summary),
        "corrected_rerun_command": corrected_rerun(summary, intended_key),
    }


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(payload: dict[str, object]) -> str:
    rows = payload["captures"]
    lines = [
        "# Device Effect AP Input Matrix",
        "",
        "[FACT] No row in this matrix is accepted as intended-effect evidence because numeric mode inputs selected different raw enum ordinals from the labels.",
        "",
        "[FACT] Capture-integrity PASS remains valid for the actual rendered effect, but every mislabelled row is excluded from the audio-semantic eyes-on gate.",
        "",
        "| Variant | Intended effect | Actual effect | Raw ordinal | Selection | Capture | AP Hz | p95 us | AP rows | Peak median / max | Raw RMS median |",
        "|---|---|---|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['variant']} | {row['intended_effect']} | {row['actual_effect']} | {row['mode_ordinal']} | "
            f"{row['effect_selection_verdict']} | {row['capture_verdict']} | "
            f"{fmt(row['ap_rate_hz'])} | {fmt(row['active_p95_us'], 0)} | {row['ap']['rows']} | "
            f"{fmt(row['ap']['peak_scaled_median'])} / {fmt(row['ap']['peak_scaled_max'])} | "
            f"{fmt(row['ap']['raw_i16_rms_median'])} |"
        )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "[FACT] `set_mode` in both probe environments used legacy raw ordinals because `K1_EFFECT_REGISTRY_V1` was absent. The earlier dense-index assumption was false.",
            "",
            "[FACT] Ordinal 12 rendered Aurora, 16 rendered Ember Field, 18 rendered Waveform Tempo, and 23 rendered Pulse Prism.",
            "",
            "[FACT] The Captain's observations identified the mismatch before gate closure; all associated Waveform Hybrid, Tempo Comet, Dense Forge Chord, and Percussion Burst claims are withdrawn.",
            "",
            "[FACT] AP and event telemetry still describes the audio pipeline, but it does not prove that the labelled intended effect consumed that feed.",
            "",
            "[FACT] Two V2 captures also failed the cadence contract under high diagnostic load; those remain capture-invalid independently of the mode-selection failure.",
            "",
            "[FACT] The effect-level eyes-on verdict is `NOT_VERIFIED` until corrected stable-key runs target ordinals 20, 24, 26, and 32.",
            "",
            "## Source Boundaries",
            "",
            "- [FACT] `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:167-206` defines the append-only raw enum ordinals.",
            "- [FACT] `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:1617-1632` makes `set_mode` dense only when `K1_EFFECT_REGISTRY_V1` is compiled.",
            "- [FACT] `platformio.ini` does not add `K1_EFFECT_REGISTRY_V1` to either bench AP probe environment.",
            "",
            "## Exact Re-runs",
            "",
            "[FACT] Regenerate this matrix:",
            "",
            "```bash",
            payload["rerun_command"],
            "```",
            "",
        ]
    )
    for row in rows:
        lines.extend(
            (
                f"[FACT] Corrected re-run for `{row['variant']} / {row['intended_effect']}`:",
                "",
                "```bash",
                row["corrected_rerun_command"],
                "```",
                "",
            )
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    summaries = sorted(input_dir.glob("*__summary.json"))
    if not summaries:
        raise SystemExit(f"no capture summaries found in {input_dir}")
    captures = [analyse(path) for path in summaries]
    rerun = shlex.join(
        [
            "python3",
            "scripts/regression-harness/device_effect_ap_matrix_score.py",
            "--input-dir",
            args.input_dir,
            "--out-json",
            args.out_json,
            "--out-md",
            args.out_md,
        ]
    )
    payload = {
        "verdict": "MISLABELLED_INVALID",
        "captures": captures,
        "accepted_count": sum(bool(row["accepted"]) for row in captures),
        "invalid_count": sum(not bool(row["accepted"]) for row in captures),
        "mislabelled_count": sum(row["effect_selection_verdict"] != "PASS" for row in captures),
        "rerun_command": rerun,
    }
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    Path(args.out_md).write_text(render_markdown(payload))
    print(json.dumps({"accepted": payload["accepted_count"], "invalid": payload["invalid_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
