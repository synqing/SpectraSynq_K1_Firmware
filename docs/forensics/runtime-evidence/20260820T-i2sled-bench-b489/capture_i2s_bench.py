#!/usr/bin/env python3
"""Bench B489 I2S/LCD_CAM LED emit eval capture. DTR asserted, RTS clear."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import serial

PORT = "/dev/cu.usbmodem1101"
OUT = Path(__file__).resolve().parent
EXPECT_GIT = "e5fb5710"
EXPECT_ENV = "k1_bench_im69d_i2sled_probe"


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
        try:
            chunk = s.read(4096)
        except serial.SerialException:
            break
        if chunk:
            buf.extend(chunk)
    return buf.decode("utf-8", "replace")


def cmd(s: serial.Serial, line: str, wait: float = 0.8) -> str:
    s.reset_input_buffer()
    s.write((line + "\n").encode("ascii"))
    s.flush()
    return drain(s, wait)


def parse(pattern: str, text: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(pattern, text)]


def main() -> None:
    s = open_port()
    log: dict = {"port": PORT, "t0": time.time()}
    try:
        build = cmd(s, ":build", 1.2)
        (OUT / "01_build.txt").write_text(build)
        log["build"] = build.strip()
        if EXPECT_GIT not in build or EXPECT_ENV not in build:
            print("IDENTITY MISMATCH — aborting capture")
            print(build[:400])
            return
        dump = cmd(s, ":dump", 2.5)
        (OUT / "02_dump.txt").write_text(dump)

        series = []
        for _ in range(10):
            t = time.time()
            fps_txt = cmd(s, ":fps", 0.35)
            led_txt = cmd(s, ":led_fps", 0.35)
            fps = parse(r"SYSTEM_FPS:\s*([0-9.]+)", fps_txt)
            led = parse(r"LED_FPS:\s*([0-9.]+)", led_txt)
            series.append(
                {
                    "t": t,
                    "system_fps": fps[-1] if fps else None,
                    "led_fps": led[-1] if led else None,
                }
            )
            time.sleep(0.25)
        (OUT / "03_fps_series.json").write_text(json.dumps(series, indent=2))

        start = cmd(s, ":vp_perf=start", 0.6)
        vpf = start + drain(s, 10.0)
        status = cmd(s, ":vp_perf=status", 1.0)
        (OUT / "04_vpf_stream.txt").write_text(vpf)
        (OUT / "05_vp_perf_status.txt").write_text(status)

        log["fps_series"] = series
        (OUT / "00_summary.json").write_text(json.dumps(log, indent=2))
        print(json.dumps({k: log[k] for k in log if k != "build"}, indent=2))
        print("BUILD", log["build"][:200])
    finally:
        s.close()


if __name__ == "__main__":
    os.chdir(OUT)
    main()
