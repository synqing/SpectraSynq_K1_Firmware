#!/usr/bin/env python3
"""B489 tempo-emit exact residual v1. Two legs. No F887. No ABBA. No reference rerun."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

from serial.tools import list_ports

ROOT = Path(__file__).resolve().parents[4]
PACK = Path(__file__).resolve().parent
USB_SERIAL = "B4:3A:45:A5:89:B4"
F887_SERIAL = "B4:3A:45:A5:87:F8"
ENV = "k1_bench_scheduling_gdft_cross40_lane4_tempo_inc_full_probe"
OUTPUT_DEVICE = "Bose Mini II SoundLink"
T_FROZEN = "c1aba345603bc2cacc8cf30648768d346f572779"
H_PIN = "14c53d239524aa891e71470880f6917d4adf2ea6"
DRAIN = ROOT / "scripts/regression-harness/apcad_worst_row_drain.py"
ESPTOOL = Path.home() / ".platformio/packages/tool-esptoolpy/esptool.py"
PIO_PY = Path.home() / ".platformio/penv/bin/python"
GUARD = ROOT / "scripts/platformio/k1_upload_guard.py"
IDENTITY = ROOT / "scripts/regression-harness/k1_device_identity_guard.py"
CAPTURE = (
    ROOT
    / "docs/forensics/runtime-evidence/20260816T-g0r-abba-b489/device_ap_cadence_capture_probe.py"
)
FIRMWARE_BIN = ROOT / ".pio/build" / ENV / "firmware.bin"
TRACK = Path(
    "/Users/spectrasynq/Music/Music/Media.localized/Music/"
    "Ahmed Spins_Stevo Atambire/Anchor Point EP/Anchor Point.mp3"
)
TRACK_SHA = "02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938"
LEGS = [
    ("L1_noplay", "no_playback"),
    ("L2_anchor", "music"),
]


class FailClosed(RuntimeError):
    pass


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
    last = []
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


def git_short() -> str:
    result = run(["git", "rev-parse", "--short", "HEAD"], timeout=10)
    if result.returncode != 0:
        raise FailClosed("git rev-parse failed")
    return (result.stdout or "").strip()


def flash(port: str, bin_path: Path) -> None:
    guard = run(
        [sys.executable, str(GUARD), "--env", ENV, "--upload-port", port],
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


def attest(port: str, expect_git: str) -> dict[str, str]:
    ident = run(
        [
            sys.executable,
            str(IDENTITY),
            "--port",
            port,
            "--expect-git",
            expect_git,
            "--expect-env",
            ENV,
        ],
        timeout=20,
    )
    if ident.returncode != 0:
        raise FailClosed(f"identity fail: {ident.stderr}{ident.stdout}")
    line = (ident.stdout or "").strip()
    log(line)
    return {"identity_line": line, "port": port, "env": ENV, "expect_git": expect_git}


def capture(leg_id: str, fixture: str, port: str) -> dict[str, object]:
    if fixture == "music":
        restored = run(["SwitchAudioSource", "-s", OUTPUT_DEVICE], timeout=10)
        if restored.returncode != 0:
            raise FailClosed(f"could not select {OUTPUT_DEVICE}: {restored.stderr}")
        observed = run(["SwitchAudioSource", "-c", "-t", "output"], timeout=10)
        name = (observed.stdout or "").strip()
        if name != OUTPUT_DEVICE:
            raise FailClosed(f"output device is {name!r}, required {OUTPUT_DEVICE}")
    out_dir = PACK / "legs" / leg_id
    out_dir.mkdir(parents=True, exist_ok=True)
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
        f"{leg_id}_{ENV}_{fixture}",
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


def existing_admissible_leg(leg_id: str, fixture: str) -> dict[str, object] | None:
    leg_dir = PACK / "legs" / leg_id
    manifests = sorted(leg_dir.glob("*__pair_manifest.json"))
    if not manifests:
        return None
    manifest = json.loads(manifests[-1].read_text())
    compact = json.loads(Path(manifest["compact_summary_path"]).read_text())
    buffered = json.loads(Path(manifest["buffered_summary_path"]).read_text())
    if not compact.get("capture_admissible") or not buffered.get("capture_admissible"):
        log(f"{leg_id} existing capture is not admissible; will recapture")
        return None
    if compact.get("active_sample_rate_mode") != 12800:
        raise FailClosed(f"{leg_id} existing capture sample rate mismatch")
    if compact.get("active_samples_per_chunk_mode") != 96:
        raise FailClosed(f"{leg_id} existing capture chunk mismatch")
    if compact.get("active_tempo_decimation_mode") != 3:
        raise FailClosed(f"{leg_id} existing capture decimation mismatch")
    return {
        "leg_id": leg_id,
        "fixture": fixture,
        "usb_serial": USB_SERIAL,
        "chip_id": "B489A500",
        "env": ENV,
        "capture": {
            "classification": "paired_capture_admissible",
            "pair_manifest": str(manifests[-1]),
            "compact": {"summary_json": manifest["compact_summary_path"]},
            "buffered": {"summary_json": manifest["buffered_summary_path"]},
        },
        "resumed_existing": True,
    }


def run_leg(leg_id: str, fixture: str, port: str, expect_git: str, bin_sha: str) -> dict[str, object]:
    existing = existing_admissible_leg(leg_id, fixture)
    if existing is not None:
        log(f"=== LEG {leg_id} RESUME existing admissible capture ===")
        (PACK / "legs" / leg_id / "leg.json").write_text(
            json.dumps(existing, indent=2, sort_keys=True) + "\n"
        )
        return existing
    log(f"=== LEG {leg_id} fixture={fixture} ===")
    attestation = attest(port, expect_git)
    capture_result = capture(leg_id, fixture, port)
    record = {
        "leg_id": leg_id,
        "fixture": fixture,
        "port": port,
        "usb_serial": USB_SERIAL,
        "chip_id": "B489A500",
        "env": ENV,
        "expect_git": expect_git,
        "bin_sha256": bin_sha,
        "identity": attestation,
        "capture": capture_result,
    }
    (PACK / "legs" / leg_id / "leg.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    log(f"LEG OK {leg_id}")
    return record


def main() -> int:
    (PACK / "logs").mkdir(parents=True, exist_ok=True)
    log("START G2_TEMPO_EMIT_EXACT_RESIDUAL_V1 B489")
    if not FIRMWARE_BIN.exists():
        raise FailClosed(f"missing firmware bin {FIRMWARE_BIN}; build first")
    if not CAPTURE.exists():
        raise FailClosed(f"missing admitted capture runner {CAPTURE}")
    if not TRACK.exists():
        raise FailClosed(f"Anchor Point missing: {TRACK}")
    if sha256(TRACK) != TRACK_SHA:
        raise FailClosed("Anchor Point SHA mismatch")
    expect_git = git_short()
    bin_sha = sha256(FIRMWARE_BIN)
    provenance = {
        "experiment": "G2_TEMPO_EMIT_EXACT_RESIDUAL_V1",
        "env": ENV,
        "git_short": expect_git,
        "bin_sha256": bin_sha,
        "bin_path": str(FIRMWARE_BIN),
        "capture_runner_sha256": sha256(CAPTURE),
        "drain_sha256": sha256(DRAIN),
        "T_frozen": T_FROZEN,
        "measurement_firmware_pin_H": H_PIN,
        "output_device": OUTPUT_DEVICE,
        "track_sha256": TRACK_SHA,
    }
    (PACK / "PREFLIGHT.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    log("PREFLIGHT " + json.dumps(provenance, sort_keys=True))
    port = find_b489()
    if any(p.serial_number == F887_SERIAL for p in list_ports.comports()):
        raise FailClosed("F887 present")
    log(f"identity-before-flash port={port}")
    flash(port, FIRMWARE_BIN)
    time.sleep(8)
    port = find_b489()
    attest(port, expect_git)
    results = []
    try:
        for leg_id, fixture in LEGS:
            port = find_b489()
            if any(p.serial_number == F887_SERIAL for p in list_ports.comports()):
                raise FailClosed("F887 present")
            results.append(run_leg(leg_id, fixture, port, expect_git, bin_sha))
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
    (PACK / "SERIES.json").write_text(
        json.dumps({"provenance": provenance, "legs": results}, indent=2, sort_keys=True) + "\n"
    )
    log("BOTH LEGS COMPLETE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FailClosed as exc:
        log(f"FAIL_CLOSED {exc}")
        raise SystemExit(2) from exc
