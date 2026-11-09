"""Read-only identity read-back for the bench K1 (Lane D0, K1-FE-SHOW-M1 Rev 2).

Sends only ':build' (the repo's identity guard method, S3 USB-CDC: DTR asserted,
RTS low), captures the raw reply for a fixed window, saves it, and parses the build
line with the repo's own parser. No flash, no reset, no other command.

Usage: python3.13 read_build.py <port> <out_raw_path> [window_s]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness"))
from k1_device_identity_guard import parse_build_line  # noqa: E402

import serial  # noqa: E402


def main() -> int:
    port, out = sys.argv[1], Path(sys.argv[2])
    window = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, 115200, 0.2
    s.dtr, s.rts = True, False
    t_open = time.time()
    s.open()
    buf = bytearray()
    try:
        time.sleep(0.6)
        pre = s.read(65536)  # whatever the device was already printing
        s.write(b":build\n")
        s.flush()
        t_sent = time.time()
        end = t_sent + window
        while time.time() < end:
            buf.extend(s.read(4096))
    finally:
        s.close()
    text = buf.decode("utf-8", errors="replace")
    out.write_text(
        f"# port={port} opened_utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_open))}"
        f" sent=:build window_s={window}\n# --- pre-command bytes: {len(pre)} ---\n"
        + pre.decode("utf-8", errors="replace")
        + "\n# --- reply ---\n" + text
    )
    ident = parse_build_line(text)
    print(json.dumps({"port": port, "pre_bytes": len(pre), "reply_bytes": len(buf),
                      "identity": ident}, indent=1))
    return 0 if ident else 2


if __name__ == "__main__":
    raise SystemExit(main())
