#!/usr/bin/env python3
"""B489 min/full A-B-B-A runner for the 2026-08-16 G0R flash GO.

Flashes the receipt-pinned bins (no rebuild). Two independent series:
no-play A-B-B-A, then audible Anchor Point A-B-B-A. Fail closed. No F887.
"""
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
BAKED_GIT = "be8dd1aa"
H_PIN = "14c53d239524aa891e71470880f6917d4adf2ea6"
OUTPUT_DEVICE = "Bose Mini II SoundLink"
T_FROZEN = "c1aba345603bc2cacc8cf30648768d346f572779"
DRAIN = ROOT / "scripts/regression-harness/apcad_worst_row_drain.py"
ESPTOOL = Path.home() / ".platformio/packages/tool-esptoolpy/esptool.py"
PIO_PY = Path.home() / ".platformio/penv/bin/python"
GUARD = ROOT / "scripts/platformio/k1_upload_guard.py"
IDENTITY = ROOT / "scripts/regression-harness/k1_device_identity_guard.py"
CAPTURE = PACK / "device_ap_cadence_capture_probe.py"
TRACK = Path(
    "/Users/spectrasynq/Music/Music/Media.localized/Music/"
    "Ahmed Spins_Stevo Atambire/Anchor Point EP/Anchor Point.mp3"
)
RECEIPT_BINS = {
    "MIN": PACK / "bins/min.bin",
    "FULL": PACK / "bins/full.bin",
}
RECEIPT_SHA = {
    "MIN": "c66c9dafd8e141d91878e6d98cc59a2ff778ea2f20876447ec4ceb3e0a325da2",
    "FULL": "9fec6e2514945262df510da47afbb168ae000c86cbfec62730301a556898aa9a",
}
ENVS = {
    "MIN": "k1_bench_scheduling_stage_min_probe",
    "FULL": "k1_bench_scheduling_stage_full_probe",
}
LEGS = [
    ("S1_A1", "MIN", "no_playback"),
    ("S1_B1", "FULL", "no_playback"),
    ("S1_B2", "FULL", "no_playback"),
    ("S1_A2", "MIN", "no_playback"),
    ("S2_A1", "MIN", "music"),
    ("S2_B1", "FULL", "music"),
    ("S2_B2", "FULL", "music"),
    ("S2_A2", "MIN", "music"),
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


def flash(role: str, port: str) -> None:
    bin_path = RECEIPT_BINS[role]
    digest = sha256(bin_path)
    if digest != RECEIPT_SHA[role]:
        raise FailClosed(f"{role} bin hash drifted: {digest}")
    env = ENVS[role]
    guard = run(
        [sys.executable, str(GUARD), "--env", env, "--upload-port", port],
        timeout=20,
    )
    if guard.returncode != 0:
        raise FailClosed(f"upload guard failed: {guard.stdout}{guard.stderr}")
    flash_cmd = [
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
    ]
    flashed = run(flash_cmd, timeout=180)
    if flashed.returncode != 0:
        raise FailClosed(f"esptool failed rc={flashed.returncode}: {flashed.stderr[-2000:]}")


def attest(port: str, role: str) -> dict[str, str]:
    ident = run(
        [
            sys.executable,
            str(IDENTITY),
            "--port",
            port,
            "--expect-git",
            BAKED_GIT,
            "--expect-env",
            ENVS[role],
        ],
        timeout=20,
    )
    if ident.returncode != 0:
        raise FailClosed(f"identity fail: {ident.stderr}{ident.stdout}")
    line = (ident.stdout or "").strip()
    log(line)
    return {"identity_line": line, "role": role, "port": port}


def capture(leg_id: str, role: str, fixture: str, port: str) -> dict[str, object]:
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
        f"{leg_id}_{role}_{fixture}",
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


def t_prime_record() -> dict[str, str]:
    return {
        "T_frozen": T_FROZEN,
        "T_prime_drain_sha256": sha256(DRAIN),
        "T_prime_runner_sha256": sha256(CAPTURE),
        "measurement_firmware_pin_H": H_PIN,
    }


COMPAT_KEYS = (
    "capture_admissible",
    "capture_complete",
    "compact_worst_count_mismatch",
    "row_count",
    "active_sample_rate_mode",
    "active_samples_per_chunk_mode",
    "active_tempo_decimation_mode",
)


def reparse_compact_compatible(leg_id: str) -> dict[str, object]:
    spec_obj = importlib.util.spec_from_file_location("tprime_capture", CAPTURE)
    if spec_obj is None or spec_obj.loader is None:
        raise FailClosed(f"cannot load T' runner from {CAPTURE}")
    module = importlib.util.module_from_spec(spec_obj)
    spec_obj.loader.exec_module(module)
    raw = sorted((PACK / "legs" / leg_id).glob("*__compact__raw.log"))[-1]
    summary_path = sorted((PACK / "legs" / leg_id).glob("*__compact__summary.json"))[-1]
    original = json.loads(summary_path.read_text())
    lines = raw.read_text(errors="replace").splitlines()
    soak, worst, metadata = module.parse_soak_summary(lines)
    metadata.update(
        {
            "mode": "compact_soak_from_raw",
            "status_done": any("APCAD_SOAK_DONE," in line for line in lines),
            "vp_perf_stack_hwm_words": module.parse_vp_perf_stack_hwm(lines),
        }
    )
    parsed = module.summarise_soak(soak, worst, metadata, 12800, 96, 3)
    delta = {
        key: {"original": original.get(key), "reparsed": parsed.get(key)}
        for key in COMPAT_KEYS
        if original.get(key) != parsed.get(key)
    }
    orig_done = (original.get("capture_metadata") or {}).get("done") or {}
    parsed_done = (parsed.get("capture_metadata") or {}).get("done") or {}
    for key in ("active_ap_work_p99_low_us", "active_ap_work_p99_high_us"):
        if orig_done.get(key) != parsed_done.get(key):
            delta[key] = {"original": orig_done.get(key), "reparsed": parsed_done.get(key)}
    if original.get("compact_worst_count_mismatch") is False:
        declared = int(orig_done.get("worst_count") or 16)
        if len(worst) != declared:
            delta["worst_row_count"] = {"declared": declared, "reparsed": len(worst)}
    if delta:
        raise FailClosed(f"{leg_id} T' reparse changed controlling fields: {delta}")
    return {
        "leg_id": leg_id,
        "raw": str(raw),
        "worst_rows": len(worst),
        "compatible": True,
    }


def existing_admissible_leg(leg_id: str, role: str, fixture: str) -> dict[str, object] | None:
    leg_dir = PACK / "legs" / leg_id
    manifests = sorted(leg_dir.glob("*__pair_manifest.json"))
    if not manifests:
        return None
    manifest_path = manifests[-1]
    manifest = json.loads(manifest_path.read_text())
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
    payload = {
        "classification": "paired_capture_admissible",
        "pair_manifest": str(manifest_path),
        "pair_manifest_sha256": sha256(manifest_path),
        "compact": {
            "summary_json": manifest["compact_summary_path"],
            "raw_log": manifest["compact_raw_path"],
        },
        "buffered": {
            "summary_json": manifest["buffered_summary_path"],
            "raw_log": manifest["buffered_raw_path"],
        },
        "resumed_existing": True,
    }
    record = {
        "leg_id": leg_id,
        "role": role,
        "fixture": fixture,
        "usb_serial": USB_SERIAL,
        "chip_id": "B489A500",
        "baked_git": BAKED_GIT,
        "source_pin_H": H_PIN,
        "bin_sha256": RECEIPT_SHA[role],
        "capture": payload,
        "identity_revalidated_before_flash": True,
        "resumed_existing": True,
        "boot_nonce": manifest.get("boot_nonce"),
    }
    return record


def run_leg(leg_id: str, role: str, fixture: str) -> dict[str, object]:
    existing = existing_admissible_leg(leg_id, role, fixture)
    if existing is not None:
        log(f"=== LEG {leg_id} RESUME existing admissible capture ===")
        (PACK / "legs" / leg_id / "leg.json").write_text(
            json.dumps(existing, indent=2, sort_keys=True) + "\n"
        )
        log(f"LEG OK {leg_id} (resumed)")
        return existing
    log(f"=== LEG {leg_id} role={role} fixture={fixture} ===")
    port = find_b489()
    log(f"identity-before-flash port={port}")
    flash(role, port)
    time.sleep(8)
    port = find_b489()
    attestation = attest(port, role)
    capture_result = capture(leg_id, role, fixture, port)
    record = {
        "leg_id": leg_id,
        "role": role,
        "fixture": fixture,
        "port": port,
        "usb_serial": USB_SERIAL,
        "chip_id": "B489A500",
        "baked_git": BAKED_GIT,
        "source_pin_H": H_PIN,
        "bin_sha256": RECEIPT_SHA[role],
        "identity": attestation,
        "capture": capture_result,
        "identity_revalidated_before_flash": True,
    }
    (PACK / "legs" / leg_id / "leg.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    log(f"LEG OK {leg_id}")
    return record


def main() -> int:
    (PACK / "logs").mkdir(parents=True, exist_ok=True)
    log("START G0R B489 A-B-B-A T-prime worst-row drain retry")
    if not DRAIN.exists():
        raise FailClosed(f"T' drain module missing: {DRAIN}")
    t_prime = t_prime_record()
    (PACK / "T_PRIME.json").write_text(json.dumps(t_prime, indent=2, sort_keys=True) + "\n")
    log("T' " + json.dumps(t_prime, sort_keys=True))
    if not TRACK.exists():
        raise FailClosed(f"Anchor Point missing: {TRACK}")
    if sha256(TRACK) != "02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938":
        raise FailClosed("Anchor Point SHA mismatch")
    for role, path in RECEIPT_BINS.items():
        if sha256(path) != RECEIPT_SHA[role]:
            raise FailClosed(f"frozen {role} bin hash mismatch")
    if find_b489() and any(p.serial_number == F887_SERIAL for p in list_ports.comports()):
        raise FailClosed("F887 present")
    a1 = reparse_compact_compatible("S1_A1")
    b1 = reparse_compact_compatible("S1_B1")
    (PACK / "T_PRIME_REPARSE.json").write_text(
        json.dumps({"S1_A1": a1, "S1_B1": b1}, indent=2, sort_keys=True) + "\n"
    )
    log("T' reparse S1_A1/S1_B1 UNCHANGED; retaining both legs")
    results = []
    try:
        for leg_id, role, fixture in LEGS:
            results.append(run_leg(leg_id, role, fixture))
    except Exception as exc:
        log(f"ABORT {type(exc).__name__}: {exc}")
        (PACK / "ABORT.json").write_text(
            json.dumps({"error": str(exc), "completed_legs": [r["leg_id"] for r in results]}, indent=2)
            + "\n"
        )
        raise
    (PACK / "SERIES.json").write_text(
        json.dumps({"t_prime": t_prime_record(), "legs": results}, indent=2, sort_keys=True) + "\n"
    )
    log("ALL EIGHT LEGS COMPLETE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FailClosed as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
