#!/usr/bin/env python3
"""Read-only Serial Studio subscriber: parse_seq continuity + device/host skew.

Never calls io.writeData, console.send, or connect/disconnect.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("/Users/spectrasynq/Serial-Studio/tests/utils")))
from api_client import APIError, SerialStudioClient  # noqa: E402

WATCH = (
    "device_ms",
    "frame_ms",
    "parse_seq",
    "host_parse_seq",
    "record_kind",
    "update_mask",
    "frame_dt_ms",
    "host_device_skew_ms",
    "transport_residual_ms",
    "BPM",
    "System FPS",
)


def values_for(group: dict) -> dict:
    out = {}
    for d in group.get("datasets", []):
        title = d.get("title")
        if title in WATCH:
            out[title] = d.get("numericValue")
    return out


def main() -> int:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
    c = SerialStudioClient(timeout=6)
    c.connect()
    prev_seq = {}
    t_end = time.time() + seconds
    print(f"subscribe_readonly {seconds:.1f}s (no device writes)")
    while time.time() < t_end:
        try:
            data = c.command("dashboard.getData")
        except APIError as e:
            print("api", e)
            time.sleep(0.5)
            continue
        for g in data.get("frame", {}).get("groups", []):
            title = g.get("title") or ""
            if not title.startswith("K1 "):
                continue
            vals = values_for(g)
            seq = vals.get("host_parse_seq")
            if seq is None:
                seq = vals.get("parse_seq")
            gap = None
            if seq is not None and title in prev_seq and prev_seq[title] is not None:
                gap = seq - prev_seq[title]
                if gap > 1:
                    print(f"GAP {title} host_parse_seq +{gap} (parser-derived, not device frame_seq)")
            prev_seq[title] = seq
            print(
                f"{title}: seq={seq} device_ms={vals.get('device_ms')} "
                f"dt={vals.get('frame_dt_ms')} skew={vals.get('host_device_skew_ms')} "
                f"bpm={vals.get('BPM')} sys_fps={vals.get('System FPS')}"
            )
        time.sleep(0.5)
    print("status", json.dumps(c.command("io.getStatus").get("_summary")))
    print("sessions", json.dumps(c.command("sessions.getStatus")))
    c.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
