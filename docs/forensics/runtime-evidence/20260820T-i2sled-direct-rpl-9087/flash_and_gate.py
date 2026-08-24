#!/usr/bin/env python3
"""Main RPL I2S-direct probe: 30 s baseline, full-chain flash, verify, boot gate.

On any flash/verify/boot-gate failure: full-chain restore of d276fd68.
DTR asserted, RTS clear on pyserial (no extra reset beyond esptool's).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import serial

PORT = "/dev/cu.usbmodem1401"
EXPECT_MAC = "b4:3a:45:a5:87:90"
ESPTOOL = str(Path.home() / ".platformio/penv/bin/esptool.py")
ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "probe"
RESTORE = ROOT / "restore"
COMMON = ROOT / "common"
BOOT_APP0 = COMMON / "boot_app0.bin"


def esptool(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    cmd = [ESPTOOL, "--chip", "esp32s3", "--port", PORT, *args]
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )


def wait_port(seconds: float = 20.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if Path(PORT).exists():
            return True
        time.sleep(0.25)
    return False


def open_serial() -> serial.Serial:
    if not wait_port(25.0):
        raise RuntimeError(f"CDC {PORT} did not reappear")
    time.sleep(1.0)
    s = serial.Serial()
    s.port = PORT
    s.baudrate = 115200
    s.timeout = 0.2
    # USB-JTAG: RTS hard-reset straps DOWNLOAD (boot:0x0). Leave both lines low.
    s.dtr = False
    s.rts = False
    s.open()
    s.dtr = False
    s.rts = False
    time.sleep(0.4)
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


def send(s: serial.Serial, line: str, wait: float) -> str:
    s.reset_input_buffer()
    s.write((line + "\n").encode("ascii"))
    s.flush()
    return drain(s, wait)


def write_chain(kind: str) -> bool:
    src = PROBE if kind == "probe" else RESTORE
    cp = esptool(
        [
            "--baud",
            "460800",
            "--after",
            "no_reset",
            "write_flash",
            "--flash_mode",
            "dio",
            "--flash_freq",
            "80m",
            # 16MB rewrites the bootloader SHA ("SHA digest in image updated")
            # and this USB-JTAG S3 then XOR-rejects the app. keep was the
            # unbrick. See DIAGNOSIS.md. Never 16MB on 9087A500.
            "--flash_size",
            "keep",
            "0x0",
            str(src / "bootloader.bin"),
            "0x8000",
            str(src / "partitions.bin"),
            "0xe000",
            str(BOOT_APP0),
            "0x10000",
            str(src / "firmware.bin"),
        ]
    )
    (ROOT / f"{kind}_write_flash.log").write_text(
        cp.stdout + "\n--- stderr ---\n" + cp.stderr
    )
    print(cp.stdout)
    print(cp.stderr, file=sys.stderr)
    return cp.returncode == 0


def verify_app(kind: str) -> bool:
    src = PROBE if kind == "probe" else RESTORE
    cp = esptool(
        [
            "--baud",
            "460800",
            "--before",
            "no_reset",
            "--after",
            "no_reset",
            "verify_flash",
            "0x10000",
            str(src / "firmware.bin"),
        ]
    )
    (ROOT / f"{kind}_verify_flash.log").write_text(
        cp.stdout + "\n--- stderr ---\n" + cp.stderr
    )
    print(cp.stdout)
    print(cp.stderr, file=sys.stderr)
    return cp.returncode == 0


def restore_now(reason: str) -> int:
    print(f"AUTO-RESTORE: {reason}", flush=True)
    (ROOT / "RESTORE_REASON.txt").write_text(reason + "\n")
    if not write_chain("restore"):
        print("RESTORE WRITE FAILED", file=sys.stderr)
        return 2
    if not verify_app("restore"):
        print("RESTORE VERIFY FAILED", file=sys.stderr)
        return 2
    run = esptool(["--before", "no_reset", "--after", "watchdog_reset", "run"])
    (ROOT / "restore_run.log").write_text(run.stdout + "\n--- stderr ---\n" + run.stderr)
    time.sleep(4.0)
    if not wait_port(25.0):
        print("RESTORE: CDC did not return", file=sys.stderr)
        return 2
    s = open_serial()
    try:
        boot = drain(s, 8.0)
        boot += send(s, ":build", 1.5)
        boot += send(s, ":dump", 2.5)
    finally:
        s.close()
    (ROOT / "RESTORE_BOOT.txt").write_text(boot)
    if "git=d276fd68" in boot and "env=k1_main_rpl_im69d" in boot:
        print("RESTORE BOOT GATE PASS")
        return 1
    print("RESTORE BOOT GATE FAIL — see RESTORE_BOOT.txt", file=sys.stderr)
    return 2


def main() -> int:
    # MAC already confirmed this session (b4:3a:45:a5:87:90). Do not enter the
    # stub before the 30 s baseline — USB-JTAG RTS leaves boot:0x0 DOWNLOAD.
    time.sleep(1.0)
    s = open_serial()
    try:
        baseline = drain(s, 4.0)
        baseline += send(s, ":build", 1.5)
        baseline += send(s, ":dump", 2.5)
        baseline += send(s, ":fps", 0.6)
        baseline += send(s, ":led_fps", 0.6)
        t0 = time.time()
        while time.time() - t0 < 22.0:
            baseline += send(s, ":fps", 0.4)
            baseline += send(s, ":led_fps", 0.4)
            time.sleep(1.5)
    finally:
        s.close()
    (ROOT / "BASELINE.txt").write_text(baseline)
    print("BASELINE written", len(baseline), "chars")

    if not write_chain("probe"):
        return restore_now("probe write_flash failed")
    if not verify_app("probe"):
        return restore_now("probe verify_flash failed")
    run = esptool(["--before", "no_reset", "--after", "watchdog_reset", "run"])
    (ROOT / "probe_run.log").write_text(run.stdout + "\n--- stderr ---\n" + run.stderr)
    time.sleep(4.0)
    if not wait_port(25.0):
        return restore_now("CDC did not return after probe watchdog_reset")

    s = open_serial()
    try:
        boot = drain(s, 12.0)
        boot += send(s, ":build", 1.5)
        boot += send(s, ":dump", 2.5)
        remain = 30.0 - 16.0
        if remain > 0:
            boot += drain(s, remain)
    finally:
        s.close()
    (ROOT / "BOOT_GATE.txt").write_text(boot)

    bad = (
        "esp_image" in boot
        or "Checksum failed" in boot
        or "No bootable app" in boot
        or "I2S_EMIT: FAIL" in boot
        or "waiting for download" in boot
        or "DOWNLOAD(USB/UART0)" in boot
    )
    ok_init = "INIT_LEDS: PASS" in boot
    ok_id = "env=k1_main_rpl_i2sled_probe" in boot
    ok_i2s = "I2S_EMIT: init core=1" in boot
    panic = "Guru Meditation" in boot
    print("boot INIT_LEDS", ok_init, "IDENTITY", ok_id, "I2S_EMIT core1", ok_i2s)
    # INIT_LEDS PASS is Core-0 show skip under K1_RMT_ALLOC_ON_VP_CORE_V1.
    # Yves is proven only by a complete I2S_EMIT init line without a panic.
    if bad or panic or not (ok_id and ok_i2s):
        return restore_now(
            f"boot gate fail init={ok_init} id={ok_id} i2s={ok_i2s} panic={panic} bad={bad}"
        )
    print("BOOT GATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
