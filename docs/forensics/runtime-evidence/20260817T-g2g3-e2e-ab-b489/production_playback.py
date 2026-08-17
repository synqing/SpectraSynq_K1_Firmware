#!/usr/bin/env python3
"""Production-territory playback on restored k1_bench_im69d.

Not an APCAD p99 gate. Collects 1 Hz [AP] lines for quiet then locked-track
music on the Bose. Does not stamp G2_DEVICE CLOSED.
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import serial
from serial.tools import list_ports

PACK = Path(__file__).resolve().parent
USB_SERIAL = "B4:3A:45:A5:89:B4"
F887_SERIAL = "B4:3A:45:A5:87:F8"
OUTPUT_DEVICE = "Bose Mini II SoundLink"
TRACK = Path(
    "/Users/spectrasynq/Music/Music/Media.localized/Music/"
    "Ahmed Spins_Stevo Atambire/Anchor Point EP/Anchor Point.mp3"
)
TRACK_SHA = "02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938"
AP_RE = re.compile(
    r"\[AP\].*?max_raw=(?P<max_raw>-?\d+(?:\.\d+)?).*?silence=(?P<silence>\d+)"
    r".*?bpm=(?P<bpm>-?\d+(?:\.\d+)?).*?conf=(?P<conf>-?\d+(?:\.\d+)?)"
    r".*?lock=(?P<lock>\d+)"
)
BUILD_RE = re.compile(
    r"BUILD:\s*version=(?P<version>\S+)\s+git=(?P<git>\S+)\s+"
    r"epoch=(?P<epoch>\S+)\s+env=(?P<env>\S+)"
)


class FailClosed(RuntimeError):
    pass


def find_b489() -> str:
    f887 = False
    b489 = None
    for info in list_ports.comports():
        if info.serial_number == F887_SERIAL:
            f887 = True
        if info.serial_number == USB_SERIAL:
            b489 = info.device
    if f887:
        raise FailClosed("F887 present")
    if not b489:
        raise FailClosed("B489 not found")
    return b489


def output_device() -> str:
    return subprocess.check_output(
        ["SwitchAudioSource", "-c", "-t", "output"], text=True, timeout=10
    ).strip()


def select_bose() -> None:
    subprocess.check_call(["SwitchAudioSource", "-s", OUTPUT_DEVICE], timeout=10)
    name = output_device()
    if name != OUTPUT_DEVICE:
        raise FailClosed(f"output is {name!r}, required {OUTPUT_DEVICE}")


def summarise(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    max_raw = [r["max_raw"] for r in rows]
    silence = [r["silence"] for r in rows]
    lock = [r["lock"] for r in rows]
    conf = [r["conf"] for r in rows]
    bpm = [r["bpm"] for r in rows]
    return {
        "n": len(rows),
        "silence_frac": sum(silence) / len(silence),
        "lock_frac": sum(lock) / len(lock),
        "max_raw_min": min(max_raw),
        "max_raw_max": max(max_raw),
        "max_raw_mean": statistics.fmean(max_raw),
        "conf_mean": statistics.fmean(conf),
        "bpm_mean": statistics.fmean(bpm),
    }


def main() -> int:
    port = find_b489()
    select_bose()
    if not TRACK.exists():
        raise FailClosed("track missing")
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = 115200
    ser.timeout = 0.3
    ser.dtr = True
    ser.rts = False
    ser.open()
    time.sleep(0.6)
    ser.reset_input_buffer()
    ser.write(b":build\n")
    ser.flush()
    buf = bytearray()
    deadline = time.time() + 4
    ident = None
    while time.time() < deadline:
        chunk = ser.read(4096)
        if chunk:
            buf.extend(chunk)
            ident = BUILD_RE.search(buf.decode("utf-8", errors="replace"))
            if ident:
                break
    if ident is None:
        raise FailClosed("no :build")
    identity = ident.groupdict()
    if identity["env"] != "k1_bench_im69d" or not identity["git"].startswith("e911f86"):
        raise FailClosed(f"wrong identity {identity}")
    ser.write(b":ap_stream=1\n")
    ser.flush()
    time.sleep(0.4)
    ser.reset_input_buffer()

    def collect(seconds: float) -> list[dict]:
        rows: list[dict] = []
        end = time.time() + seconds
        acc = ""
        while time.time() < end:
            chunk = ser.read(4096)
            if chunk:
                acc += chunk.decode("utf-8", errors="replace")
                while "\n" in acc:
                    line, acc = acc.split("\n", 1)
                    match = AP_RE.search(line)
                    if match:
                        rows.append(
                            {
                                "max_raw": float(match.group("max_raw")),
                                "silence": int(match.group("silence")),
                                "bpm": float(match.group("bpm")),
                                "conf": float(match.group("conf")),
                                "lock": int(match.group("lock")),
                                "line": line.strip(),
                            }
                        )
            else:
                time.sleep(0.05)
        return rows

    quiet = collect(20.0)
    player = subprocess.Popen(
        [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            "-t",
            "120",
            "-i",
            str(TRACK),
        ]
    )
    try:
        if output_device() != OUTPUT_DEVICE:
            raise FailClosed("Bose lost at music start")
        music = collect(120.0)
    finally:
        player.poll()
        if player.returncode is None:
            player.terminate()
            try:
                player.wait(timeout=5)
            except subprocess.TimeoutExpired:
                player.kill()
    ser.close()
    report = {
        "experiment": "B489_PRODUCTION_TERRITORY_PLAYBACK",
        "not_a_p99_gate": True,
        "G2_DEVICE": "NOT_CLOSED",
        "identity": identity,
        "port": port,
        "usb_serial": USB_SERIAL,
        "output_device": OUTPUT_DEVICE,
        "track_sha256": TRACK_SHA,
        "quiet_s": 20,
        "music_s": 120,
        "quiet": summarise(quiet),
        "music": summarise(music),
        "quiet_tail": [r["line"] for r in quiet[-3:]],
        "music_tail": [r["line"] for r in music[-3:]],
    }
    (PACK / "PRODUCTION_PLAYBACK.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({k: report[k] for k in (
        "experiment", "G2_DEVICE", "identity", "quiet", "music"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FailClosed as exc:
        print(f"FAIL_CLOSED {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
