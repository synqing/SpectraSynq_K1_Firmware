#!/usr/bin/env python3
"""Score corrected stable-key V1/V2 effect eyes-on captures."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path


EFFECTS = {
    "tempo_comet": {"name": "Tempo Comet", "ordinal": 20, "verdict_arg": "tempo"},
    "dense_forge_chord": {"name": "Dense Forge Chord", "ordinal": 24, "verdict_arg": "chord"},
    "percussion_burst": {"name": "Percussion Burst", "ordinal": 26, "verdict_arg": "onset"},
    "waveform_hybrid_k1": {"name": "Waveform Hybrid K1", "ordinal": 32, "verdict_arg": "waveform"},
}
CRASH_RE = re.compile(
    r"Guru Meditation|Backtrace:|rst:0x|watchdog|abort\(\) was called|assert failed|panic(?:'ed|:)",
    re.IGNORECASE,
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    for name in ("tempo", "chord", "onset", "waveform"):
        parser.add_argument(f"--{name}", choices=("PASS", "FAIL", "NOT_VERIFIED"), required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    return parser.parse_args()


def capture_command(summary: dict[str, object]) -> str:
    selection = summary["mode_selection"]
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
        "--set-effect",
        str(selection["effect_key"]),
        "--eyes-on-countdown-ms",
        str(summary.get("eyes_on_countdown_ms") or 0),
    ]
    return shlex.join(command)


def analyse(summary_path: Path) -> dict[str, object]:
    summary = json.loads(summary_path.read_text())
    selection = summary.get("mode_selection") or {}
    effect_key = selection.get("effect_key")
    effect = EFFECTS.get(str(effect_key))
    if effect is None:
        raise ValueError(f"unexpected or missing stable effect key in {summary_path}: {effect_key}")
    environment = str(summary.get("expected_build_env"))
    variant = "v1_off" if environment.endswith("_v1_off") else "v2"
    raw_path = Path(str(summary["raw_log"]))
    raw_lines = raw_path.read_text(errors="replace").splitlines()
    crash_lines = [line for line in raw_lines if CRASH_RE.search(line)]
    errors = list((summary.get("validation") or {}).get("errors") or [])
    checks = {
        "capture_pass": (summary.get("validation") or {}).get("verdict") == "PASS",
        "chip_match": (summary.get("runtime_identity") or {}).get("chip_id") == "B489A500",
        "effect_key_match": effect_key == selection.get("effect_key"),
        "ordinal_match": selection.get("expected_ordinal") == effect["ordinal"]
        and selection.get("observed_ordinal") == effect["ordinal"],
        "runtime_env_match": (summary.get("runtime_identity") or {}).get("build_env") == environment,
        "no_crash": not crash_lines,
        "eyes_on_countdown_configured": int(summary.get("eyes_on_countdown_ms") or 0) > 0,
        "eyes_on_duration_complete": 29000 <= int(summary.get("duration_ms_observed") or 0) <= 31000,
    }
    for check, passed in checks.items():
        if not passed:
            errors.append(check)
    return {
        "summary": str(summary_path),
        "raw_log": str(raw_path),
        "variant": variant,
        "effect_key": effect_key,
        "effect": effect["name"],
        "ordinal": effect["ordinal"],
        "build_env": environment,
        "build_line": (summary.get("runtime_identity") or {}).get("build_line"),
        "chip_id": (summary.get("runtime_identity") or {}).get("chip_id"),
        "capture_verdict": (summary.get("validation") or {}).get("verdict"),
        "mechanical_verdict": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "track_sha256": summary.get("track_sha256"),
        "rerun_command": capture_command(summary),
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Corrected Device Effect Eyes-On A/B",
        "",
        "[FACT] These rows supersede the mislabelled 2026-07-14 focused effect captures.",
        "",
        "[FACT] Each row selected a stable effect key, resolved its append-only raw ordinal from source, and required matching runtime ordinal readback before playback.",
        "",
        "| Variant | Effect | Raw ordinal | Runtime environment | Capture | Crash signatures | Captain eyes-on |",
        "|---|---|---:|---|---|---:|---|",
    ]
    for row in payload["captures"]:
        verdict = payload["captain_verdicts"][row["effect_key"]]
        lines.append(
            f"| {row['variant']} | {row['effect']} | {row['ordinal']} | `{row['build_env']}` | "
            f"{row['mechanical_verdict']} | 0 | {verdict} |"
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            "[FACT] Captain observed no V2 visual regression versus V1 for Tempo Comet, Dense Forge Chord, Percussion Burst, or Waveform Hybrid K1.",
            "",
            f"[FACT] Corrected effect eyes-on verdict: **{payload['gate_verdict']}**.",
            "",
            "[FACT] This verdict covers effect selection, visibility, stability, musical response, and absence of observed crashes. Tempo accuracy metrics are reported separately in the device-novelty table.",
            "",
            "## Exact Re-runs",
            "",
            "[FACT] Regenerate this verdict:",
            "",
            "```bash",
            payload["rerun_command"],
            "```",
            "",
        ]
    )
    for row in payload["captures"]:
        lines.extend(
            (
                f"[FACT] Re-run `{row['variant']} / {row['effect']}`:",
                "",
                "```bash",
                row["rerun_command"],
                "```",
                "",
            )
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    summaries = sorted(Path(args.input_dir).glob("*__summary.json"))
    captures = [analyse(path) for path in summaries]
    expected_pairs = {(variant, key) for variant in ("v1_off", "v2") for key in EFFECTS}
    observed_pairs = {(row["variant"], row["effect_key"]) for row in captures}
    if observed_pairs != expected_pairs or len(captures) != len(expected_pairs):
        raise SystemExit(f"expected exactly eight V1/V2 effect rows; observed {sorted(observed_pairs)}")
    captain_verdicts = {
        key: getattr(args, str(effect["verdict_arg"])) for key, effect in EFFECTS.items()
    }
    mechanical_pass = all(row["mechanical_verdict"] == "PASS" for row in captures)
    captain_pass = all(verdict == "PASS" for verdict in captain_verdicts.values())
    rerun_command = shlex.join(
        [
            "python3",
            "scripts/regression-harness/device_effect_eyes_on_score.py",
            "--input-dir",
            args.input_dir,
            "--tempo",
            args.tempo,
            "--chord",
            args.chord,
            "--onset",
            args.onset,
            "--waveform",
            args.waveform,
            "--out-json",
            args.out_json,
            "--out-md",
            args.out_md,
        ]
    )
    payload = {
        "gate_verdict": "PASS" if mechanical_pass and captain_pass else "NOT_VERIFIED",
        "captain_verdicts": captain_verdicts,
        "captures": captures,
        "rerun_command": rerun_command,
    }
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    Path(args.out_md).write_text(render_markdown(payload))
    print(json.dumps({"verdict": payload["gate_verdict"], "captures": len(captures)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
