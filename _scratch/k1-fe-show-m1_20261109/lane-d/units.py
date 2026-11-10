"""Known bench K1 units for the lane-d tools (10 Nov 2026). Identity = USB-Serial-JTAG serial
number (= ESP32-S3 MAC); the port is discovered from it, never assumed (ports drift).
Source: docs/hardware/device-build-registry.md and the lead's read-backs.
Pin maps are per-build references, not locks (Captain, 10 Nov 2026); nothing here encodes pins.
"""
from __future__ import annotations

import os

from serial.tools import list_ports

UNITS = {
    # Bench K1v2: k1_fe_bench_b489 @ ed0aa984 read back 9 Nov; WS2812, 8-bit rtrace, primary edge only.
    "b489": {"usb": "B4:3A:45:A5:89:B4", "chip": "B489A500"},
    # Main RPL: k1_main_rpl_im69d @ 2a620f7e read back 10 Nov; WS2816 dual-DIN; 16-bit rtrace only in
    # capture builds (k1_main_rpl_rtrace_probe-style), none in the resident build.
    "rpl": {"usb": "B4:3A:45:A5:87:90", "chip": "9087A500"},
}


def unit_name() -> str:
    u = os.environ.get("K1_UNIT", "").strip().lower()
    if u not in UNITS:
        raise SystemExit(f"set K1_UNIT to one of {sorted(UNITS)} (got {u!r}); identity is never assumed")
    return u


def port_for(unit: str) -> str:
    want = UNITS[unit]["usb"]
    hits = [p.device for p in list_ports.comports()
            if (p.serial_number or "").upper() == want and p.device.startswith("/dev/cu.")]
    if len(hits) != 1:
        raise SystemExit(f"REFUSED: unit {unit} (USB {want}) found on {hits or 'no port'}; need exactly one")
    return hits[0]
