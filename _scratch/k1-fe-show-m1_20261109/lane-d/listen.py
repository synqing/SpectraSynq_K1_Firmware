"""Read-only K1 telemetry logger (lead, 10 Nov 2026). Opens the named unit's port, writes NOTHING,
records every line with monotonic/UTC stamps for SECONDS, then closes.

Usage: K1_UNIT=rpl python3.13 listen.py OUT.jsonl SECONDS
Port identity from lane-d/units.py (USB serial); DTR asserted, RTS low (repo convention).
A 'NOISE_CAL' line is recorded and flagged; nothing is ever sent in reply.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import serial

sys.path.insert(0, str(Path(__file__).resolve().parent))
from units import port_for, unit_name  # noqa: E402


def main() -> int:
    out, seconds = Path(sys.argv[1]), float(sys.argv[2])
    port = port_for(unit_name())
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, 115200, 0.2
    s.dtr, s.rts = True, False
    s.open()
    buf = b""
    flagged = 0
    end = time.monotonic() + seconds
    with out.open("w") as f:
        while time.monotonic() < end:
            buf += s.read(4096)
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                if "NOISE_CAL" in line and not line.startswith("[AP]"):
                    flagged += 1
                f.write(json.dumps({"mono": time.monotonic(), "utc": time.strftime("%H:%M:%S"),
                                    "line": line}) + "\n")
    s.close()
    print(f"port {port} lines logged; noise_cal_lines={flagged}")
    return 3 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
