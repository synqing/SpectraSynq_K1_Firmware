#!/usr/bin/env python3
"""One-shot Main RPL fps/agc probe capture. DTR asserted, RTS clear. No reset."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import serial

PORT = "/dev/cu.usbmodem1401"
OUT = Path(__file__).resolve().parent
EXPECT_GIT = "dec5fb53"
EXPECT_ENV = "k1_main_rpl_fps_agc_probe"


def open_port() -> serial.Serial:
    s = serial.Serial()
    s.port = PORT
    s.baudrate = 115200
    s.timeout = 0.2
    s.dtr = True
    s.rts = False
    s.open()
    time.sleep(0.6)
    s.reset_input_buffer()
    return s


def drain(s: serial.Serial, seconds: float) -> str:
    buf = bytearray()
    deadline = time.time() + seconds
    while time.time() < deadline:
        chunk = s.read(4096)
        if chunk:
            buf.extend(chunk)
    return buf.decode("utf-8", "replace")


def cmd(s: serial.Serial, line: str, wait: float = 0.8) -> str:
    s.reset_input_buffer()
    s.write((line + "\n").encode("ascii"))
    s.flush()
    return drain(s, wait)


def parse_fps(text: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(r"SYSTEM_FPS:\s*([0-9.]+)", text)]


def parse_led_fps(text: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(r"LED_FPS:\s*([0-9.]+)", text)]


def main() -> None:
    s = open_port()
    log: dict = {"port": PORT, "t0": time.time()}
    try:
        build = cmd(s, ":build", 1.2)
        (OUT / "01_build.txt").write_text(build)
        log["build"] = build.strip()
        dump = cmd(s, ":dump", 2.5)
        (OUT / "02_dump.txt").write_text(dump)

        baseline = []
        for i in range(6):
            t = time.time()
            txt = cmd(s, ":fps", 0.4)
            vals = parse_fps(txt)
            baseline.append({"t": t, "raw": txt.strip(), "fps": vals[-1] if vals else None})
            time.sleep(0.3)
        (OUT / "03_fps_baseline.json").write_text(json.dumps(baseline, indent=2))

        start = cmd(s, ":vp_perf=start", 0.6)
        vpf = start + drain(s, 8.0)
        status = cmd(s, ":vp_perf=status", 1.0)
        (OUT / "04_vpf_stream.txt").write_text(vpf)
        (OUT / "05_vp_perf_status.txt").write_text(status)

        pre = []
        for _ in range(4):
            t = time.time()
            txt = cmd(s, ":fps", 0.35)
            vals = parse_fps(txt)
            pre.append({"phase": "pre", "t": t, "fps": vals[-1] if vals else None, "raw": txt.strip()})
            time.sleep(0.25)
        skip_ack = cmd(s, ":show_skip=5000", 0.5)
        skip_status = cmd(s, ":show_skip=status", 0.4)
        during = []
        t_skip = time.time()
        while time.time() - t_skip < 6.2:
            t = time.time()
            txt = cmd(s, ":fps", 0.3)
            vals = parse_fps(txt)
            during.append(
                {
                    "phase": "show_skip",
                    "t": t,
                    "dt_s": t - t_skip,
                    "fps": vals[-1] if vals else None,
                    "raw": txt.strip(),
                }
            )
            time.sleep(0.15)
        off_ack = cmd(s, ":show_skip=off", 0.4)
        post = []
        for _ in range(6):
            t = time.time()
            txt = cmd(s, ":fps", 0.35)
            vals = parse_fps(txt)
            post.append({"phase": "post", "t": t, "fps": vals[-1] if vals else None, "raw": txt.strip()})
            time.sleep(0.25)
        led = cmd(s, ":led_fps", 0.4)
        (OUT / "06_show_skip_series.json").write_text(
            json.dumps(
                {
                    "skip_ack": skip_ack.strip(),
                    "skip_status": skip_status.strip(),
                    "off_ack": off_ack.strip(),
                    "led_fps": led.strip(),
                    "pre": pre,
                    "during": during,
                    "post": post,
                },
                indent=2,
            )
        )
        log["skip_ack"] = skip_ack.strip()
        log["skip_status"] = skip_status.strip()
        log["off_ack"] = off_ack.strip()
        log["led_fps"] = parse_led_fps(led)
        log["fps_baseline"] = [x["fps"] for x in baseline]
        log["fps_pre"] = [x["fps"] for x in pre]
        log["fps_during"] = [x["fps"] for x in during]
        log["fps_post"] = [x["fps"] for x in post]
        (OUT / "00_summary.json").write_text(json.dumps(log, indent=2))
        print(json.dumps({k: log[k] for k in log if k != "build"}, indent=2))
        print("BUILD", log["build"][:200])
    finally:
        s.close()


if __name__ == "__main__":
    os.chdir(OUT)
    main()
