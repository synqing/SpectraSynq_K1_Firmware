#!/usr/bin/env python3
"""Restore k1_main_rpl_im69d @ b625e89a to Main RPL only. Identity = MAC."""

from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
import sys
import time

import serial
from serial.tools import list_ports

EXPECTED_MAC = "b4:3a:45:a5:87:90"
FACTORY = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "20260824T165900Z-corrected-parent",
        "restore_k1_main_rpl_im69d_b625e89a.factory.bin",
    )
)
EXPECTED_SHA = "973084b464c8a22cab9b1db434a7e385a95c6b1755dc8946ac5af01633a69ce3"
PIO_PY = os.path.expanduser("~/.platformio/penv/bin/python")
ESPTOOL = os.path.expanduser("~/.platformio/penv/bin/esptool.py")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def ports():
    rows = []
    for p in list_ports.comports():
        rows.append(
            {
                "device": p.device,
                "serial": p.serial_number,
                "product": p.product,
                "vid": p.vid,
                "pid": p.pid,
            }
        )
    return rows


def dump_ports(label):
    rows = ports()
    print(label, rows, flush=True)
    return rows


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def enter_rom(cdc):
    print("1200_touch", cdc, flush=True)
    s = serial.Serial()
    s.port = cdc
    s.baudrate = 1200
    s.dtr = False
    s.rts = False
    s.timeout = 0.2
    s.open()
    time.sleep(0.15)
    s.dtr = True
    time.sleep(0.15)
    s.close()
    time.sleep(1.6)


def esptool(args, log_name):
    cmd = [PIO_PY, ESPTOOL, *args]
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, text=True, capture_output=True)
    path = os.path.join(OUT_DIR, log_name)
    with open(path, "w") as f:
        f.write(proc.stdout)
        f.write(proc.stderr)
    print(proc.stdout, proc.stderr, sep="", flush=True)
    if proc.returncode != 0:
        raise SystemExit(f"esptool failed rc={proc.returncode} log={path}")
    return proc.stdout + proc.stderr


def pick_jtag(rows):
    for r in rows:
        serial = (r.get("serial") or "").lower().replace(":", "")
        product = (r.get("product") or "").lower()
        if "b43a45a58790" in serial or "b4:3a:45:a5:87:90" in (r.get("serial") or "").lower():
            return r["device"]
        if "jtag" in product:
            return r["device"]
    return None


def main():
    digest = sha256(FACTORY)
    if digest != EXPECTED_SHA:
        raise SystemExit(f"factory SHA mismatch {digest}")
    print("factory_sha", digest, "size", os.path.getsize(FACTORY), flush=True)

    before = dump_ports("ports_before")
    cdc = None
    jtag = pick_jtag(before)
    after = before
    if jtag:
        print("already_rom_or_jtag", jtag, flush=True)
    else:
        for r in before:
            serial = (r.get("serial") or "").upper()
            product = (r.get("product") or "")
            if "9087A5453AB4" in serial or "USB Audio" in product:
                cdc = r["device"]
                break
        if cdc is None:
            modem = sorted(glob.glob("/dev/cu.usbmodem*"))
            if len(modem) == 1:
                cdc = modem[0]
        if not cdc:
            raise SystemExit("no TinyUSB CDC to enter ROM")
        enter_rom(cdc)
        after = dump_ports("ports_after_1200")
        jtag = pick_jtag(after)
    if not jtag:
        raise SystemExit("no JTAG/ROM port after 1200; do not guess")
    print("jtag", jtag, flush=True)

    mac_out = esptool(
        ["--chip", "esp32s3", "--port", jtag, "read_mac"],
        "restore_read_mac.txt",
    )
    if EXPECTED_MAC not in mac_out.lower():
        raise SystemExit(f"MAC mismatch — refusing write. output:\n{mac_out}")
    print("IDENTITY_OK", EXPECTED_MAC, flush=True)

    esptool(
        [
            "--chip",
            "esp32s3",
            "--port",
            jtag,
            "--baud",
            "921600",
            "--before",
            "default_reset",
            "--after",
            "no_reset",
            "write_flash",
            "--flash_mode",
            "dio",
            "--flash_freq",
            "80m",
            "--flash_size",
            "16MB",
            "0x0",
            FACTORY,
        ],
        "restore_write.txt",
    )
    verify = esptool(
        [
            "--chip",
            "esp32s3",
            "--port",
            jtag,
            "--baud",
            "921600",
            "--before",
            "no_reset",
            "--after",
            "no_reset",
            "verify_flash",
            "--diff",
            "yes",
            "0x0",
            FACTORY,
        ],
        "restore_verify.txt",
    )
    if "verify OK" not in verify:
        raise SystemExit("verify_flash did not print verify OK")

    # Probe flash needed watchdog_reset; product restore last time used RTS.
    # Try watchdog first so the app leaves ROM download.
    esptool(
        ["--chip", "esp32s3", "--port", jtag, "--after", "watchdog_reset", "chip_id"],
        "restore_watchdog_reset.txt",
    )
    time.sleep(3.0)
    live = dump_ports("ports_after_reset")
    receipt = {
        "expected_mac": EXPECTED_MAC,
        "factory": FACTORY,
        "factory_sha256": digest,
        "cdc_before": cdc,
        "jtag": jtag,
        "ports_before": before,
        "ports_after_1200": after,
        "ports_after_reset": live,
    }
    with open(os.path.join(OUT_DIR, "restore_ports.json"), "w") as f:
        json.dump(receipt, f, indent=2)
    print("WRITE_VERIFY_OK", flush=True)


if __name__ == "__main__":
    main()
