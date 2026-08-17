#!/usr/bin/env python3
"""B489 package A/B: pre-restamp Cross0 probe vs e911f86d Cross40+Lane4+G3/G4.

One process owns the primary eight-leg ABBA. Flash only when the arm changes.
No F887. No resume of stale pair manifests. No H-pin pass/fail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from serial.tools import list_ports

PACK = Path(__file__).resolve().parent
ROOT = PACK.parents[3]
USB_SERIAL = "B4:3A:45:A5:89:B4"
F887_SERIAL = "B4:3A:45:A5:87:F8"
OUTPUT_DEVICE = "Bose Mini II SoundLink"
T_FROZEN = "c1aba345603bc2cacc8cf30648768d346f572779"
TRACK = Path(
    "/Users/spectrasynq/Music/Music/Media.localized/Music/"
    "Ahmed Spins_Stevo Atambire/Anchor Point EP/Anchor Point.mp3"
)
TRACK_SHA = "02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938"
CAPTURE = (
    ROOT
    / "docs/forensics/runtime-evidence/20260816T-g0r-abba-b489/device_ap_cadence_capture_probe.py"
)
GUARD = ROOT / "scripts/platformio/k1_upload_guard.py"
IDENTITY = ROOT / "scripts/regression-harness/k1_device_identity_guard.py"
ESPTOOL = Path.home() / ".platformio/packages/tool-esptoolpy/esptool.py"
PIO_PY = Path.home() / ".platformio/penv/bin/python"

PRIMARY_LEGS: list[tuple[str, str, str]] = [
    ("Q_A1", "A", "no_playback"),
    ("Q_B1", "B", "no_playback"),
    ("Q_B2", "B", "no_playback"),
    ("Q_A2", "A", "no_playback"),
    ("M_A1", "A", "music"),
    ("M_B1", "B", "music"),
    ("M_B2", "B", "music"),
    ("M_A2", "A", "music"),
]
CONTINGENT_LEGS: list[tuple[str, str, str]] = [
    ("C_Q", "C", "no_playback"),
    ("C_M", "C", "music"),
]
ARMS = {
    "A": {
        "env": "k1_bench_scheduling_stage_full_probe",
        "bin": PACK / "bins" / "A.bin",
    },
    "B": {
        "env": "k1_bench_scheduling_gdft_cross40_lane4_full_probe",
        "bin": PACK / "bins" / "B.bin",
    },
    "C": {
        "env": "k1_bench_scheduling_g3_off_full_probe",
        "bin": PACK / "bins" / "C.bin",
    },
}


class FailClosed(RuntimeError):
    pass


def should_flash(previous_arm: str | None, next_arm: str) -> bool:
    if previous_arm is None:
        return True
    return previous_arm != next_arm


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    (PACK / "logs").mkdir(parents=True, exist_ok=True)
    with (PACK / "logs" / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def find_b489(*, timeout_s: float = 40.0) -> str:
    deadline = time.time() + timeout_s
    last: list[tuple[str, str | None]] = []
    while time.time() < deadline:
        last = []
        f887 = False
        for info in list_ports.comports():
            last.append((info.device, info.serial_number))
            if info.serial_number == F887_SERIAL:
                f887 = True
            if info.serial_number == USB_SERIAL:
                if f887:
                    raise FailClosed("F887 is present; this GO is B489 only")
                return info.device
        time.sleep(0.5)
    raise FailClosed(f"B489A500 USB serial {USB_SERIAL} not found; last={last}")


def refuse_f887() -> None:
    if any(p.serial_number == F887_SERIAL for p in list_ports.comports()):
        raise FailClosed("F887 present")


def run(cmd: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    log("CMD " + " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.stdout:
        (PACK / "logs" / "run.log").open("a", encoding="utf-8").write(result.stdout + "\n")
    if result.stderr:
        (PACK / "logs" / "run.log").open("a", encoding="utf-8").write(result.stderr + "\n")
    return result


def current_output_device() -> str:
    observed = run(["SwitchAudioSource", "-c", "-t", "output"], timeout=10)
    return (observed.stdout or "").strip()


def select_bose() -> None:
    restored = run(["SwitchAudioSource", "-s", OUTPUT_DEVICE], timeout=10)
    if restored.returncode != 0:
        raise FailClosed(f"could not select {OUTPUT_DEVICE}: {restored.stderr}")
    name = current_output_device()
    if name != OUTPUT_DEVICE:
        raise FailClosed(f"output device is {name!r}, required {OUTPUT_DEVICE}")


def flash(arm: str, port: str) -> None:
    spec = ARMS[arm]
    env = spec["env"]
    bin_path = spec["bin"]
    guard = run(
        [sys.executable, str(GUARD), "--env", env, "--upload-port", port],
        timeout=20,
    )
    if guard.returncode != 0:
        raise FailClosed(f"upload guard failed: {guard.stdout}{guard.stderr}")
    flashed = run(
        [
            str(PIO_PY),
            str(ESPTOOL),
            "--chip",
            "esp32s3",
            "--port",
            port,
            "--baud",
            "460800",
            "--before",
            "default_reset",
            "--after",
            "hard_reset",
            "write_flash",
            "-z",
            "0x10000",
            str(bin_path),
        ],
        timeout=180,
    )
    if flashed.returncode != 0:
        raise FailClosed(f"esptool failed rc={flashed.returncode}: {flashed.stderr[-2000:]}")


def attest(port: str, arm: str, expect_git: str) -> dict[str, str]:
    env = ARMS[arm]["env"]
    ident = run(
        [
            sys.executable,
            str(IDENTITY),
            "--port",
            port,
            "--expect-git",
            expect_git,
            "--expect-env",
            env,
        ],
        timeout=20,
    )
    if ident.returncode != 0:
        raise FailClosed(f"identity fail: {ident.stderr}{ident.stdout}")
    line = (ident.stdout or "").strip()
    log(line)
    return {"identity_line": line, "port": port, "env": env, "expect_git": expect_git, "arm": arm}


def capture(leg_id: str, arm: str, fixture: str, port: str) -> dict[str, object]:
    if fixture == "music":
        select_bose()
    out_dir = PACK / "legs" / leg_id
    out_dir.mkdir(parents=True, exist_ok=True)
    env = ARMS[arm]["env"]
    cmd = [
        sys.executable,
        str(CAPTURE),
        "--port",
        port,
        "--paired-compact-buffer",
        "--pre-roll-seconds",
        "10",
        "--dump-timeout-seconds",
        "180",
        "--expected-sample-rate",
        "12800",
        "--expected-samples-per-chunk",
        "96",
        "--expected-novelty-decimation",
        "3",
        "--expected-output-device",
        OUTPUT_DEVICE,
        "--player",
        "ffplay",
        "--playback-gain-db",
        "0.0",
        "--out-dir",
        str(out_dir),
        "--label",
        f"{leg_id}_{env}_{fixture}",
    ]
    if fixture == "no_playback":
        cmd.append("--no-playback")
    else:
        cmd.extend(["--track", str(TRACK)])
    result = run(cmd, timeout=480)
    if result.returncode not in (0, 2):
        raise FailClosed(f"{leg_id} capture rc={result.returncode}: {result.stderr[-2000:]}")
    try:
        start = result.stdout.find("{")
        if start < 0:
            raise json.JSONDecodeError("no JSON object", result.stdout, 0)
        payload, _end = json.JSONDecoder().raw_decode(result.stdout[start:])
    except json.JSONDecodeError as exc:
        raise FailClosed(f"{leg_id} capture stdout was not JSON: {result.stdout[-2000:]}") from exc
    if payload.get("classification") != "paired_capture_admissible":
        raise FailClosed(f"{leg_id} capture inadmissible: {payload}")
    return payload


def load_git_map() -> dict[str, str]:
    path = PACK / "PREFLIGHT.json"
    if not path.exists():
        raise FailClosed("PREFLIGHT.json missing; pin git SHAs after builds")
    data = json.loads(path.read_text())
    return {
        "A": data["git"]["A"],
        "B": data["git"]["B"],
        "C": data.get("git", {}).get("C", data["git"]["B"]),
    }


def run_leg(
    leg_id: str,
    arm: str,
    fixture: str,
    previous_arm: str | None,
    git_map: dict[str, str],
) -> dict[str, object]:
    refuse_f887()
    port = find_b489()
    will_flash = should_flash(previous_arm, arm)
    log(f"=== LEG {leg_id} arm={arm} fixture={fixture} flash={will_flash} ===")
    if will_flash:
        log(f"identity-before-flash port={port}")
        flash(arm, port)
        time.sleep(8)
        port = find_b489()
    else:
        log(f"skip flash; same arm {arm} still on device")
    attestation = attest(port, arm, git_map[arm])
    capture_result = capture(leg_id, arm, fixture, port)
    record = {
        "leg_id": leg_id,
        "arm": arm,
        "fixture": fixture,
        "flashed": will_flash,
        "port": port,
        "usb_serial": USB_SERIAL,
        "chip_id": "B489A500",
        "env": ARMS[arm]["env"],
        "expect_git": git_map[arm],
        "bin_sha256": sha256(ARMS[arm]["bin"]),
        "identity": attestation,
        "capture": capture_result,
        "resumed_existing": False,
    }
    (PACK / "legs" / leg_id).mkdir(parents=True, exist_ok=True)
    (PACK / "legs" / leg_id / "leg.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    log(f"LEG OK {leg_id}")
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("primary", "contingent"), default="primary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    (PACK / "logs").mkdir(parents=True, exist_ok=True)
    (PACK / "bins").mkdir(parents=True, exist_ok=True)
    log(f"START E2E_AB mode={args.mode}")
    if not CAPTURE.exists():
        raise FailClosed(f"missing admitted capture runner {CAPTURE}")
    if not TRACK.exists():
        raise FailClosed(f"Anchor Point missing: {TRACK}")
    if sha256(TRACK) != TRACK_SHA:
        raise FailClosed("Anchor Point SHA mismatch")
    refuse_f887()
    find_b489()
    git_map = load_git_map()
    legs = PRIMARY_LEGS if args.mode == "primary" else CONTINGENT_LEGS
    for _leg_id, arm, _fx in legs:
        bin_path = ARMS[arm]["bin"]
        if not bin_path.exists():
            raise FailClosed(f"missing {arm} bin {bin_path}")
    results: list[dict[str, object]] = []
    previous_arm: str | None = None
    music_hold = False
    try:
        for leg_id, arm, fixture in legs:
            if fixture == "music":
                try:
                    select_bose()
                except FailClosed as exc:
                    music_hold = True
                    hold = {
                        "reason": str(exc),
                        "observed_output": current_output_device(),
                        "required_output": OUTPUT_DEVICE,
                        "skipped_from": leg_id,
                    }
                    (PACK / "MUSIC_HOLD.json").write_text(
                        json.dumps(hold, indent=2, sort_keys=True) + "\n"
                    )
                    log(f"MUSIC_HOLD {hold}")
                    break
            record = run_leg(leg_id, arm, fixture, previous_arm, git_map)
            results.append(record)
            previous_arm = arm
    except Exception as exc:
        log(f"ABORT {type(exc).__name__}: {exc}")
        (PACK / "ABORT.json").write_text(
            json.dumps(
                {"error": str(exc), "completed_legs": [r["leg_id"] for r in results]},
                indent=2,
            )
            + "\n"
        )
        raise
    series_path = PACK / ("SERIES.json" if args.mode == "primary" else "SERIES_C.json")
    series_path.write_text(
        json.dumps(
            {
                "mode": args.mode,
                "music_hold": music_hold,
                "legs": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    log(f"SERIES COMPLETE n={len(results)} music_hold={music_hold}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FailClosed as exc:
        log(f"FAIL_CLOSED {exc}")
        raise SystemExit(2) from exc
