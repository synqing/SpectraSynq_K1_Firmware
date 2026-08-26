#!/usr/bin/env python3
"""Capture :rtrace dumps for look-parity investigation.

Sends :look=N, arms stim, waits, dumps. Saves raw serial log per slot.
Usage: python3 capture_rtrace.py <port> <device_tag>
"""
import sys, time, serial, pathlib

BAUD = 115200
OUT_DIR = pathlib.Path(__file__).parent

SLOTS = [0, 1, 2]
ARM_SECS = 12
EVERY = 1  # dense capture
STIM = True


def send_and_drain(ser, cmd: str, wait: float = 0.5) -> str:
    ser.reset_input_buffer()
    ser.write((cmd + '\n').encode())
    time.sleep(wait)
    out = ser.read(8192).decode('utf-8', errors='replace')
    return out


def send_cmd(ser, cmd: str):
    ser.write((cmd + '\n').encode())


def collect(ser, secs: float) -> bytes:
    buf = bytearray()
    end = time.time() + secs
    while time.time() < end:
        chunk = ser.read(4096)
        if chunk:
            buf.extend(chunk)
    return bytes(buf)


def main():
    if len(sys.argv) < 3:
        print("usage: capture_rtrace.py <port> <device_tag>")
        sys.exit(1)

    port = sys.argv[1]
    tag = sys.argv[2]

    print(f"Opening {port} ({tag})...")
    ser = serial.Serial(port, BAUD, timeout=0.3)
    time.sleep(1.0)
    ser.reset_input_buffer()

    # Quick sanity: confirm rtrace is compiled in
    out = send_and_drain(ser, ':rtrace_status=1', wait=1.0)
    rtrace_lines = [l for l in out.splitlines() if 'RTRACE' in l]
    if not rtrace_lines:
        print(f"ERROR: no [RTRACE] response from {port}. Is K1_RENDER_TRACE_V1 compiled in?")
        ser.close()
        sys.exit(1)
    print(f"  rtrace confirmed: {rtrace_lines[0].strip()}")

    arm_cmd = f':rtrace_arm={ARM_SECS},{EVERY}'
    if STIM:
        arm_cmd += ',stim'

    for slot in SLOTS:
        print(f"\n--- slot {slot} ---")

        # Set look slot
        send_and_drain(ser, f':look={slot}', wait=0.5)
        time.sleep(0.3)

        # Arm rtrace
        arm_out = send_and_drain(ser, arm_cmd, wait=0.5)
        armed_lines = [l for l in arm_out.splitlines() if 'RTRACE' in l or 'ARMED' in l]
        if armed_lines:
            print(f"  {armed_lines[0].strip()}")

        # Wait for capture
        print(f"  capturing {ARM_SECS}s stim frames (every={EVERY})...")
        time.sleep(ARM_SECS + 2)

        # Check status
        status_out = send_and_drain(ser, ':rtrace_status=1', wait=0.8)
        for l in status_out.splitlines():
            if 'RTRACE' in l:
                print(f"  status: {l.strip()}")

        # Dump
        print(f"  dumping...")
        ser.reset_input_buffer()
        send_cmd(ser, ':rtrace_dump=1')

        dump_buf = bytearray()
        dump_started = False
        dump_ended = False
        end_time = time.time() + 90  # generous timeout for large dumps
        while time.time() < end_time and not dump_ended:
            chunk = ser.read(4096)
            if chunk:
                dump_buf.extend(chunk)
                text_so_far = dump_buf.decode('utf-8', errors='replace')
                if '[RTRACE-BEGIN' in text_so_far:
                    dump_started = True
                if '[RTRACE-END]' in text_so_far:
                    dump_ended = True
                    break
            elif dump_started:
                time.sleep(0.05)

        raw_text = dump_buf.decode('utf-8', errors='replace')
        fname = OUT_DIR / f"{tag}_slot{slot}_dump.txt"
        fname.write_text(raw_text, encoding='utf-8')

        # Count frames
        frame_count = raw_text.count('\nF,')
        begin_line = next((l for l in raw_text.splitlines() if '[RTRACE-BEGIN' in l), 'NOT FOUND')
        print(f"  saved {fname.name}: {frame_count} frames")
        print(f"  header: {begin_line[:100]}")
        if not dump_ended:
            print(f"  WARNING: dump did not end cleanly (RTRACE-END not found)")

    # Park at slot 0
    send_and_drain(ser, ':look=0', wait=0.3)
    print(f"\nParked at slot 0. Done.")
    ser.close()


if __name__ == '__main__':
    main()
