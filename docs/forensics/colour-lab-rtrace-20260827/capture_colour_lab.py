#!/usr/bin/env python3
"""Capture Colour Lab paint=card rtrace dumps. No HSV stim — the card is the stim.

Usage:
  python3 capture_colour_lab.py <port> rpl
  python3 capture_colour_lab.py <port> bench

RPL: slots 0/1/2/15 + paint=off + tune-save-reboot-reload.
Bench: slots 0/1 + paint=off. No runtime slot-15 claim.
"""
from __future__ import annotations

import pathlib
import sys
import time

import serial

BAUD = 115200
OUT_DIR = pathlib.Path(__file__).parent
ARM_SECS = 4
EVERY = 4
TUNE_GAIN = "1.00,0.70,0.40"
TUNE_GAMMA = "1.00"


def open_serial(port: str, reset: bool = False) -> serial.Serial:
    """S3 USB-JTAG needs DTR asserted. Wait for BUILD before any paint."""
    if reset:
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = BAUD
        ser.timeout = 0.4
        ser.dtr = False
        ser.rts = False
        ser.open()
        time.sleep(0.15)
        ser.dtr = True
        ser.close()
        time.sleep(5.0)
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = BAUD
    ser.timeout = 0.4
    ser.dtr = True
    ser.rts = False
    ser.open()
    time.sleep(1.0)
    ser.reset_input_buffer()
    return ser


def send_and_drain(ser: serial.Serial, cmd: str, wait: float = 0.6) -> str:
    ser.reset_input_buffer()
    ser.write((cmd + "\n").encode())
    ser.flush()
    time.sleep(wait)
    return ser.read(32768).decode("utf-8", errors="replace")


def wait_build(ser: serial.Serial, tries: int = 8) -> str:
    last = ""
    for _ in range(tries):
        last = send_and_drain(ser, ":build", wait=0.8)
        if "BUILD:" in last:
            return last
        time.sleep(1.0)
    return last


def assert_paint_card(ser: serial.Serial, target: str = "primary") -> None:
    """Latch paint=card and prove it survives several seconds (ACK is s_edit).

    Main RPL dual WS2816: paint_target=both at conservative grey trips TG1WDT.
    Capture uses primary so the packed card stays full-scale. Bench may use both.
    """
    last = ""
    tgt = send_and_drain(ser, f":paint_target={target}", wait=0.5)
    print("  target:", next((ln for ln in tgt.splitlines() if "PAINT" in ln), tgt.strip()[:80]))
    for _attempt in range(4):
        ack = send_and_drain(ser, ":paint=card", wait=0.8)
        last = ack
        if "mode=card" not in ack:
            time.sleep(0.8)
            continue
        t0 = time.time()
        buf = ack
        while time.time() - t0 < 4.0:
            buf += ser.read(4096).decode("utf-8", errors="replace")
            if any(k in buf for k in ("rst:", "Guru", "Brownout", "HANN")):
                raise RuntimeError(f"paint=card {target} crashed during settle:\n{buf[-800:]}")
        status = send_and_drain(ser, ":paint_status", wait=0.6)
        last = status
        if "mode=card" in status and "rst:" not in status:
            print("  paint_status:", next((ln for ln in status.splitlines() if "PAINT" in ln), status.strip()[:80]))
            return
        time.sleep(0.8)
    raise RuntimeError(f"paint did not stay latched to card:\n{last}")


def collect_dump(ser: serial.Serial, timeout_s: float = 90.0) -> str:
    ser.reset_input_buffer()
    ser.write(b":rtrace_dump=1\n")
    ser.flush()
    buf = bytearray()
    started = False
    ended = False
    deadline = time.time() + timeout_s
    while time.time() < deadline and not ended:
        chunk = ser.read(4096)
        if chunk:
            buf.extend(chunk)
            text = buf.decode("utf-8", errors="replace")
            if "[RTRACE-BEGIN" in text:
                started = True
            if "[RTRACE-END]" in text:
                ended = True
                break
        elif started:
            time.sleep(0.05)
    return buf.decode("utf-8", errors="replace")


def capture_named(ser: serial.Serial, tag: str, name: str) -> pathlib.Path:
    arm = send_and_drain(ser, f":rtrace_arm={ARM_SECS},{EVERY}", wait=0.5)
    armed = [ln for ln in arm.splitlines() if "RTRACE" in ln]
    print(f"  arm {name}: {armed[0].strip() if armed else arm.strip()[:80]}")
    time.sleep(ARM_SECS + 1.5)
    raw = collect_dump(ser)
    path = OUT_DIR / f"{tag}_{name}_dump.txt"
    path.write_text(raw, encoding="utf-8")
    frames = raw.count("\nF,")
    header = next((ln for ln in raw.splitlines() if "[RTRACE-BEGIN" in ln), "NOT FOUND")
    print(f"  saved {path.name}: {frames} frames | {header[:120]}")
    if "[RTRACE-END]" not in raw:
        print("  WARNING: dump did not end cleanly")
    return path


def usb_jtag_reset(serial_hex: str = "B4:3A:45:A5:87:90") -> None:
    """Reset ESP32-S3 USB-JTAG by chip serial. Do not pulse DTR false."""
    try:
        import usb.core
        import usb.util
    except ImportError:
        print("  pyusb missing — skip hardware reset")
        return
    for dev in usb.core.find(find_all=True, idVendor=0x303A, idProduct=0x1001):
        try:
            sn = usb.util.get_string(dev, dev.iSerialNumber)
        except Exception:
            continue
        if sn == serial_hex:
            dev.reset()
            print(f"  USB reset {sn}")
            time.sleep(4.0)
            return
    print("  USB reset: device not found")


def reopen_after_reset(port: str) -> serial.Serial:
    usb_jtag_reset()
    return open_serial(port, reset=False)


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[2] not in ("rpl", "bench"):
        print("usage: capture_colour_lab.py <port> rpl|bench [--no-tune] [--no-reboot]")
        return 2
    port = sys.argv[1]
    lane = sys.argv[2]
    tag = "rpl" if lane == "rpl" else "bench"
    skip_tune = "--no-tune" in sys.argv
    skip_reboot = "--no-reboot" in sys.argv
    print(f"Opening {port} ({lane})...")
    ser = open_serial(port, reset=False)

    ident = wait_build(ser)
    (OUT_DIR / f"{tag}_identity_probe.txt").write_text(ident, encoding="utf-8")
    print("  identity:", next((ln for ln in ident.splitlines() if "BUILD:" in ln), ident[:80]))

    status = send_and_drain(ser, ":rtrace_status=1", wait=1.0)
    if "RTRACE" not in status:
        print("ERROR: no [RTRACE] response. Probe env not on this port.")
        ser.close()
        return 1
    print("  rtrace:", next(ln for ln in status.splitlines() if "RTRACE" in ln).strip())

    dump = send_and_drain(ser, ":dump", wait=1.2)
    (OUT_DIR / f"{tag}_dump_probe.txt").write_text(dump, encoding="utf-8")

    paint_target = "primary" if lane == "rpl" else "both"
    assert_paint_card(ser, paint_target)

    slots = [0, 1, 2, 15] if lane == "rpl" else [0, 1]
    if lane == "rpl" and not skip_tune:
        print("--- generate slot 15 ---")
        print(send_and_drain(ser, f":tune_gain={TUNE_GAIN}", wait=1.2).strip()[:200])
        print(send_and_drain(ser, f":tune_gamma={TUNE_GAMMA}", wait=1.2).strip()[:200])
        assert_paint_card(ser, paint_target)

    for slot in slots:
        print(f"\n--- paint=card look={slot} ---")
        assert_paint_card(ser, paint_target)
        look = send_and_drain(ser, f":look={slot}", wait=0.8)
        print(" ", next((ln for ln in look.splitlines() if "LOOK" in ln or "look" in ln), look.strip()[:80]))
        time.sleep(1.5)
        capture_named(ser, tag, f"card_slot{slot}")

    print("\n--- paint=off ---")
    print(send_and_drain(ser, ":paint=off", wait=0.6).strip()[:160])
    time.sleep(0.4)
    capture_named(ser, tag, "paint_off")

    if lane == "rpl" and not skip_reboot:
        print("\n--- tune_save + reboot + reload ---")
        save = send_and_drain(ser, ":tune_save", wait=1.0)
        print(" ", save.strip()[:200])
        send_and_drain(ser, ":look=15", wait=0.5)
        print("  waiting 6s for delayed CONFIG persist")
        time.sleep(6.5)
        ser.close()
        ser = reopen_after_reset(port)
        boot = wait_build(ser)
        (OUT_DIR / f"{tag}_identity_post_reboot.txt").write_text(boot, encoding="utf-8")
        print("  post-reboot:", next((ln for ln in boot.splitlines() if "BUILD:" in ln), boot[:80]))
        look = send_and_drain(ser, ":look_status", wait=0.6)
        (OUT_DIR / f"{tag}_look_status_post_reboot.txt").write_text(look, encoding="utf-8")
        print("  look_status:", look.strip()[:200])
        tune = send_and_drain(ser, ":tune_status", wait=0.6)
        (OUT_DIR / f"{tag}_tune_status_post_reboot.txt").write_text(tune, encoding="utf-8")
        print("  tune_status:", tune.strip()[:200])
        assert_paint_card(ser, paint_target)
        send_and_drain(ser, ":look=15", wait=0.8)
        time.sleep(1.0)
        capture_named(ser, tag, "card_slot15_reload")

    send_and_drain(ser, ":paint=off", wait=0.4)
    send_and_drain(ser, ":look=0", wait=0.4)
    ser.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
