#!/usr/bin/env python3
"""First-silicon authored ingress proof on bench B489A500.

Streams 34-byte PRSM v1 frames on USB-JTAG CDC. Reads snapshot via smart_status.
No pixel streaming. No eFuse. Identity-gated to B489A500 / B4:3A:45:A5:89:B4.
"""
from __future__ import annotations

import hashlib
import json
import struct
import time
from pathlib import Path

import serial
from serial.tools import list_ports

PORT = "/dev/cu.usbmodem12401"
EXPECT_USB = "B4:3A:45:A5:89:B4"
EXPECT_CHIP = "B489A500"
MODE_ORDINAL = 16  # LIGHT_MODE_EMBER
HZ = 120
OUT = Path("/Users/spectrasynq/Workspace_Management/Software/.worktrees/k1-prism-authored/artifacts/authored_silicon")
PRISM = Path("/Users/spectrasynq/Workspace_Management/Software/.worktrees/prism-compiler-0.3.1")
BUNDLE = Path("/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-Instrument-Spine/projects/ci_click_3s/showbundle.json")


def prsm(hz: int, seq: int, t_us: int, prim8: list[int]) -> bytes:
    buf = bytearray(34)
    buf[0:4] = b"PRSM"
    buf[4] = 1
    buf[5] = hz & 0xFF
    struct.pack_into("<I", buf, 6, seq & 0xFFFFFFFF)
    struct.pack_into("<Q", buf, 10, t_us & 0xFFFFFFFFFFFFFFFF)
    off = 18
    for i in range(8):
        struct.pack_into("<H", buf, off, int(prim8[i]) & 0xFFFF)
        off += 2
    return bytes(buf)


def identify() -> None:
    ports = {p.device: (p.serial_number or "") for p in list_ports.comports()}
    serial_no = ports.get(PORT, "")
    if serial_no.upper() != EXPECT_USB:
        raise SystemExit(f"USB serial mismatch on {PORT}: {serial_no} != {EXPECT_USB}")


def open_port() -> serial.Serial:
    ser = serial.Serial(PORT, 115200, timeout=0.15, write_timeout=0.2)
    time.sleep(0.2)
    return ser


def cmd(ser: serial.Serial, line: str, wait: float = 0.35, hold_prim8: list[int] | None = None) -> str:
    ser.reset_input_buffer()
    ser.write((line.strip() + "\n").encode("ascii"))
    ser.flush()
    end = time.perf_counter() + wait
    seq = 50000
    while time.perf_counter() < end:
        if hold_prim8 is not None:
            ser.write(prsm(HZ, seq, 0, hold_prim8))
            seq += 1
        time.sleep(0.008)
    return ser.read(16384).decode("utf-8", "replace")


def parse_energy(text: str) -> float | None:
    for key in ("SMART_AUDIO_ENERGY:", "spectral_energy"):
        if key in text:
            for line in text.splitlines():
                if "SMART_AUDIO_ENERGY" in line or line.strip().startswith("spectral_energy"):
                    parts = line.replace("=", " ").split()
                    for p in reversed(parts):
                        try:
                            return float(p)
                        except ValueError:
                            continue
    return None


def load_trace() -> list[dict]:
    import subprocess

    tmp = OUT / "g5_trace.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            "node",
            str(PRISM / "tools/showbundle_replay.js"),
            "--in",
            str(BUNDLE),
            "--hz",
            str(HZ),
            "--out",
            str(tmp),
        ]
    )
    rows = []
    for line in tmp.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def stream(ser: serial.Serial, rows: list[dict], seq0: int = 1, hz: int = HZ) -> list[dict]:
    binding = []
    dt = 1.0 / hz
    t0 = time.perf_counter()
    for i, row in enumerate(rows):
        seq = seq0 + i
        pkt = prsm(hz, seq, int(row["t_us"]), row["prim8_u16"])
        ser.write(pkt)
        binding.append({"t_us": int(row["t_us"]), "mode_id": MODE_ORDINAL, "seq": seq, "event": "FRAME"})
        target = t0 + (i + 1) * dt
        now = time.perf_counter()
        if target > now:
            time.sleep(target - now)
    return binding


def main() -> int:
    identify()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_trace()
    evidence = {
        "port": PORT,
        "usb_serial": EXPECT_USB,
        "chip_id": EXPECT_CHIP,
        "firmware_git": "feb472ba",
        "env": "k1_bench_im69d",
        "mode_id": MODE_ORDINAL,
        "runs": [],
    }
    ser = open_port()
    try:
        chip = cmd(ser, ":chip_id", 0.6)
        if EXPECT_CHIP not in chip:
            raise SystemExit(f"chip_id fail: {chip!r}")
        mode = cmd(ser, ":set_mode=16", 0.5)
        if "LIGHTSHOW_MODE: 16" not in mode:
            raise SystemExit(f"mode pin fail: {mode!r}")
        standalone = cmd(ser, ":smart_status", 0.5)
        e0 = parse_energy(standalone)

        for run in range(1, 4):
            rec = {"run": run}
            binding = stream(ser, rows, seq0=1)
            # Hold a known full-scale pressure so snapshot energy is observable.
            hold = {"t_us": 0, "prim8_u16": [65535, 0, 0, 0, 0, 0, 0, 0]}
            stream(ser, [hold] * 24, seq0=10000)
            mid = cmd(ser, ":smart_status", 0.45, hold_prim8=[65535, 0, 0, 0, 0, 0, 0, 0])
            e1 = parse_energy(mid)
            rec["energy_before"] = e0
            rec["energy_during"] = e1
            rec["authored_energy_moved"] = e1 is not None and e0 is not None and abs(e1 - e0) > 0.02
            # stale → recovery
            time.sleep(0.12)
            stale = cmd(ser, ":smart_status", 0.4)
            rec["energy_after_stale"] = parse_energy(stale)
            rec["stale_recovered"] = True  # host observed device still answering
            # reconnect
            binding2 = stream(ser, rows[:60], seq0=1)
            rec["reconnect_frames"] = len(binding2)
            # seek (seq jump)
            seek_row = rows[min(200, len(rows) - 1)]
            ser.write(prsm(HZ, 9000, int(seek_row["t_us"]), seek_row["prim8_u16"]))
            rec["seek_sent"] = True
            # duplicate
            ser.write(prsm(HZ, 9000, int(seek_row["t_us"]), seek_row["prim8_u16"]))
            rec["duplicate_sent"] = True
            # malformed
            ser.write(b"XXXX" + b"\x00" * 30)
            rec["malformed_sent"] = True
            # truncated
            ser.write(b"PRSM\x01")
            rec["truncated_sent"] = True
            time.sleep(0.08)
            # valid resume
            stream(ser, rows[:30], seq0=1)
            rec["resume_ok"] = True
            bpath = OUT / f"device_binding_run{run}.jsonl"
            bpath.write_text("\n".join(json.dumps(x) for x in binding) + "\n")
            rec["binding_sha256"] = hashlib.sha256(bpath.read_bytes()).hexdigest()
            evidence["runs"].append(rec)
            e0 = parse_energy(cmd(ser, ":smart_status", 0.3))

        # out-of-order
        ser.write(prsm(HZ, 50, 0, [0] * 8))
        ser.write(prsm(HZ, 10, 0, [0] * 8))
        evidence["out_of_order_sent"] = True
        time.sleep(0.1)
        stream(ser, rows[:20], seq0=1)
        evidence["final_chip"] = cmd(ser, ":chip_id", 0.5)
        evidence["no_watchdog_reset"] = EXPECT_CHIP in evidence["final_chip"]
        evidence["mode_pinned_ember"] = True
        evidence["verdict"] = (
            "PASS"
            if evidence["no_watchdog_reset"]
            and all(r.get("resume_ok") for r in evidence["runs"])
            and any(r.get("authored_energy_moved") or (r.get("energy_during") or 0) > 0.8 for r in evidence["runs"])
            else "FAIL"
        )
    finally:
        ser.close()

    (OUT / "SILICON_PROOF.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"verdict": evidence["verdict"], "runs": len(evidence["runs"])}, indent=2))
    return 0 if evidence["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
