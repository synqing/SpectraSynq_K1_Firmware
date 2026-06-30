"""PlatformIO upload guard for K1 GPIO pin-map targets.

The two bench K1 units expose the same ESP32-S3 USB product name, so the build
environment must be matched to the physical USB serial before any upload.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class K1Target:
    envs: tuple[str, ...]
    role: str
    upload_port: str
    usb_serial: str
    chip_id: str
    pinmap: str


K1_TARGETS: tuple[K1Target, ...] = (
    K1Target(
        envs=(
            "k1_hardware",
            "k1_hardware_harness",
            "k1_hardware_trace_dev",
            "k1_motion_probe",
            "k1_tempo_probe",
            "k1_ap_frontend_probe",
            "k1_ap_frontend_probe_matrix_12800_96_d3",
            "k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1",
            "k1_ap_frontend_probe_matrix_12800_128_d2",
            "k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1",
            "k1_ap_frontend_probe_matrix_16000_120_d3",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread8",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_gdft",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_novelty",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_snapshot",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_onset",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_saliency",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_d8",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread16",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread12",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread8",
            "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread4",
            "k1_ap_frontend_probe_matrix_16000_160_d2",
            "k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1",
            "k1_sample_rate_32k_spike",
            "k1_ble_remoted_probe",
            "k1_acf_probe",
            "k1_agc_probe",
            "k1_effect_framework",
            "k1_effect_registry",
            "k1_vp_motion_lab",
            "k1_wireless_ab_probe",
        ),
        role="main K1",
        upload_port="/dev/tty.usbmodem1401",
        usb_serial="B4:3A:45:A5:87:F8",
        chip_id="F887A500",
        pinmap="default K1 hardware GPIO assignment",
    ),
    K1Target(
        envs=(
            "k1_bench_reference",
            "k1_bench_reference_harness",
            "k1_bench_tempo_probe",
            "k1_bench_ap_frontend_probe",
            "k1_bench_ap_frontend_probe_matrix_16000_120_d3",
            "k1_bench_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            "k1_bench_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4",
            "k1_bench_acf_probe",
            "k1_bench_agc_probe",
        ),
        role="2nd bench K1",
        upload_port="/dev/tty.usbmodem12201",
        usb_serial="B4:3A:45:A5:89:B4",
        chip_id="B489A500",
        pinmap="bench-reference GPIO assignment",
    ),
)

BLOCKED_UPLOAD_ENVS: dict[str, str] = {
    "k1_sample_rate_32k_spike": (
        "32 kHz spike is build-only until acquisition-only, AP/VP, "
        "calibration, and watchdog gates are explicitly re-opened"
    ),
}


def _normalise_port(port: str) -> str:
    value = str(port or "").strip()
    if value.startswith("/dev/cu."):
        return "/dev/tty." + value[len("/dev/cu.") :]
    return value


def expected_target_for_env(pioenv: str) -> K1Target | None:
    for target in K1_TARGETS:
        if pioenv in target.envs:
            return target
    return None


def list_serial_ports() -> list[dict[str, str | None]]:
    try:
        from serial.tools import list_ports
    except Exception as exc:  # pragma: no cover - depends on PlatformIO runtime
        raise RuntimeError(f"pyserial list_ports unavailable: {exc}") from exc

    ports: list[dict[str, str | None]] = []
    for port in list_ports.comports():
        device = port.device or ""
        if "usbmodem" not in device:
            continue
        ports.append(
            {
                "device": device,
                "normalised_device": _normalise_port(device),
                "serial_number": port.serial_number,
                "location": port.location,
                "hwid": port.hwid,
            }
        )
    return ports


def find_port(upload_port: str, ports: Iterable[dict[str, str | None]]) -> dict[str, str | None] | None:
    expected = _normalise_port(upload_port)
    for port in ports:
        if _normalise_port(str(port.get("device") or "")) == expected:
            return port
    return None


def validate_upload_target(
    pioenv: str,
    upload_port: str,
    ports: Iterable[dict[str, str | None]] | None = None,
) -> tuple[bool, str]:
    if pioenv in BLOCKED_UPLOAD_ENVS:
        return False, f"{pioenv}: upload blocked: {BLOCKED_UPLOAD_ENVS[pioenv]}"

    target = expected_target_for_env(pioenv)
    if target is None:
        return True, f"{pioenv}: no K1 upload mapping enforced"

    port_list = list(ports) if ports is not None else list_serial_ports()
    port = find_port(upload_port, port_list)
    if port is None:
        return False, f"{pioenv}: {upload_port} is not currently enumerated"

    actual_serial = str(port.get("serial_number") or "")
    if actual_serial != target.usb_serial:
        return (
            False,
            (
                f"{pioenv}: {upload_port} has USB serial {actual_serial or '<missing>'}; "
                f"expected {target.usb_serial} for {target.role} ({target.pinmap}); "
                f"configured default is {target.upload_port}"
            ),
        )

    return (
        True,
        (
            f"{pioenv}: {upload_port} verified as {target.role} "
            f"({target.usb_serial}, chip {target.chip_id}, {target.pinmap})"
        ),
    )


def _guard_upload_action(source, target, env) -> None:  # pragma: no cover - exercised by PlatformIO
    pioenv = env.subst("$PIOENV")
    upload_port = env.subst("$UPLOAD_PORT")
    ok, message = validate_upload_target(pioenv, upload_port)
    prefix = "[k1-upload-guard] "
    if not ok:
        raise SystemExit(prefix + message)
    print(prefix + message)


def _install_platformio_hook() -> None:
    try:
        Import("env")  # type: ignore[name-defined]  # noqa: F821
    except NameError:
        return
    env.AddPreAction("upload", _guard_upload_action)  # type: ignore[name-defined]  # noqa: F821


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate K1 PlatformIO upload target mapping.")
    parser.add_argument("--env", dest="pioenv", required=True)
    parser.add_argument("--upload-port", required=True)
    parser.add_argument("--ports-json", type=Path)
    args = parser.parse_args(argv)

    ports = None
    if args.ports_json is not None:
        ports = json.loads(args.ports_json.read_text())

    ok, message = validate_upload_target(args.pioenv, args.upload_port, ports)
    print(message)
    return 0 if ok else 2


_install_platformio_hook()


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
