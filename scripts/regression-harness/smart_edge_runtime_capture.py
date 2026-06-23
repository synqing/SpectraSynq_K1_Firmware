#!/usr/bin/env python3
"""Capture Smart Director and EdgeMixer runtime evidence from K1 serial ports.

The script sends only ':' line commands. It never starts noise calibration.
"""

import argparse
import os
import sys
import time

try:
    import serial
except ImportError:
    print("error: pyserial not installed", file=sys.stderr)
    sys.exit(1)

SMART_REFERENCE_CONFIDENCE_FLOOR = 0.080


def open_retry(port, baud, tries=30, delay=0.5):
    last = None
    for _ in range(tries):
        if os.path.exists(port):
            try:
                return serial.Serial(port, baud, timeout=0.05)
            except Exception as exc:
                last = exc
        time.sleep(delay)
    raise RuntimeError("cannot open %s: %s" % (port, last))


def read_for(ser, seconds, lines):
    deadline = time.time() + seconds
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line:
            lines.append(line)


def read_for_with_periodic_status(ser, seconds, lines, period):
    deadline = time.time() + seconds
    start = time.time()
    next_status = start
    while time.time() < deadline:
        now = time.time()
        if period > 0.0 and now >= next_status:
            elapsed_ms = int((now - start) * 1000.0)
            lines.append("#TS_MS %d" % elapsed_ms)
            lines.append("#CMD :smart_status")
            ser.write(b":smart_status\n")
            ser.flush()
            next_status += period
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line:
            lines.append(line)


def send_command(ser, command, lines, settle=0.35):
    if not command.startswith(":"):
        raise ValueError("command must be colon-framed: %s" % command)
    lines.append("#CMD %s" % command)
    ser.write((command + "\n").encode("ascii"))
    ser.flush()
    read_for(ser, settle, lines)


def smart_confidence_command(value):
    return ":smart_confidence_floor=%.3f" % value


def apply_reference_visual_state(ser, lines):
    for command in (
        ":stop",
        ":ap_stream=off",
        ":vp_stream=off",
        ":set_mode=3",
        ":mood=0.250",
        ":palette_mode=on",
        ":palette_index=29",
        ":secondary_enabled=true",
        ":secondary_control=false",
        ":secondary_mode=7",
        ":secondary_palette_mode=true",
        ":secondary_palette_index=24",
        ":edge_mode=off",
        ":edge_enabled=off",
        ":edge_strength=0",
        ":smart_hooks=off",
        ":smart_switching=off",
        ":smart_assist=off",
        smart_confidence_command(SMART_REFERENCE_CONFIDENCE_FLOOR),
        ":smart_status",
        ":edge_status",
    ):
        send_command(ser, command, lines)


def restore_safe_runtime_state(ser, lines):
    lines.append("#RESTORE safe_runtime_state")
    for command in (
        ":ap_stream=off",
        ":vp_stream=off",
        ":vpab=stop",
        ":vp_perf=stop",
        ":set_mode=3",
        ":mood=0.250",
        ":palette_mode=on",
        ":palette_index=29",
        ":secondary_enabled=true",
        ":secondary_control=false",
        ":secondary_mode=7",
        ":secondary_palette_mode=true",
        ":secondary_palette_index=24",
        ":edge_enabled=off",
        ":edge_mode=off",
        ":edge_strength=0",
        ":smart_hooks=off",
        ":smart_switching=off",
        ":smart_assist=off",
        smart_confidence_command(SMART_REFERENCE_CONFIDENCE_FLOOR),
        ":smart_status",
        ":edge_status",
    ):
        send_command(ser, command, lines)


def run_vpab_leg(ser, lines, label, seconds, every_n):
    lines.append("#LEG %s" % label)
    for command in (
        ":vpab=reset",
        ":vp_perf=reset",
        ":vp_perf=start",
        ":vpab=start,%d,bytes" % every_n,
    ):
        send_command(ser, command, lines)
    lines.append("#WAIT %s %.2fs" % (label, seconds))
    read_for(ser, seconds, lines)
    for command in (":vpab=stop", ":vp_perf=stop", ":vpab=dump", ":diag=status"):
        send_command(ser, command, lines, settle=0.8)


def run_harness_capture(port, baud, out_path, settle, smart_confidence_floor):
    lines = []
    ser = open_retry(port, baud)
    try:
        time.sleep(settle)
        ser.reset_input_buffer()
        lines.append("#PORT %s" % port)
        lines.append("#ROLE harness_vpabb")
        apply_reference_visual_state(ser, lines)

        run_vpab_leg(ser, lines, "baseline_features_off", 8.0, 60)

        for command in (
            ":edge_mode=complementary",
            ":edge_strength=1.000",
            ":edge_enabled=on",
            ":edge_status",
        ):
            send_command(ser, command, lines)
        run_vpab_leg(ser, lines, "edge_complementary_strength_1", 8.0, 60)

        for command in (
            ":edge_mode=complementary",
            ":edge_strength=0.350",
            ":edge_enabled=on",
            ":smart_assist=on",
            ":smart_hooks=on",
            ":smart_switching=on",
            smart_confidence_command(smart_confidence_floor),
            ":smart_status",
            ":edge_status",
        ):
            send_command(ser, command, lines)
        run_vpab_leg(ser, lines, "smart_assist_low_floor_edge_on", 34.0, 240)

        for command in (":smart_status", ":edge_status", ":vp_perf=status"):
            send_command(ser, command, lines, settle=0.8)
    finally:
        try:
            restore_safe_runtime_state(ser, lines)
        except Exception as exc:
            lines.append("#RESTORE_ERROR %s" % exc)
        ser.close()

    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")

    vpabb_rows = sum(1 for line in lines if line.startswith("VPABB,"))
    vpab_rows = sum(1 for line in lines if line.startswith("VPAB,"))
    print(
        "harness captured %d lines, VPABB=%d, VPAB=%d -> %s"
        % (len(lines), vpabb_rows, vpab_rows, out_path),
        file=sys.stderr,
    )


def run_production_sanity(port, baud, out_path, settle, smart_confidence_floor, smart_status_period):
    lines = []
    ser = open_retry(port, baud)
    try:
        time.sleep(settle)
        ser.reset_input_buffer()
        lines.append("#PORT %s" % port)
        lines.append("#ROLE production_bench_reference")
        apply_reference_visual_state(ser, lines)
        for command in (
            ":ap_stream=on",
            ":smart_status",
            ":edge_status",
        ):
            send_command(ser, command, lines, settle=0.8)
        lines.append("#WAIT ap_stream_music 8.00s")
        read_for(ser, 8.0, lines)
        for command in (
            ":ap_stream=off",
            ":smart_assist=on",
            ":smart_hooks=on",
            ":smart_switching=on",
            smart_confidence_command(smart_confidence_floor),
            ":edge_mode=complementary",
            ":edge_strength=0.350",
            ":edge_enabled=on",
        ):
            send_command(ser, command, lines)
        lines.append("#LEG smart_music")
        lines.append("#WAIT smart_music 30.00s")
        read_for_with_periodic_status(ser, 30.0, lines, smart_status_period)
        for command in (":smart_status", ":edge_status", ":ap_stream=off"):
            send_command(ser, command, lines, settle=0.8)
    finally:
        try:
            restore_safe_runtime_state(ser, lines)
        except Exception as exc:
            lines.append("#RESTORE_ERROR %s" % exc)
        ser.close()

    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")

    ap_rows = sum(1 for line in lines if line.startswith("[AP]"))
    print(
        "production captured %d lines, AP=%d -> %s" % (len(lines), ap_rows, out_path),
        file=sys.stderr,
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness-port")
    parser.add_argument("--harness-out")
    parser.add_argument("--production-port")
    parser.add_argument("--production-out")
    parser.add_argument("--baud", type=int, default=230400)
    parser.add_argument("--settle", type=float, default=4.0)
    parser.add_argument("--smart-confidence-floor", type=float, default=SMART_REFERENCE_CONFIDENCE_FLOOR)
    parser.add_argument("--smart-status-period", type=float, default=2.0)
    args = parser.parse_args(argv)

    if args.harness_port:
        if not args.harness_out:
            parser.error("--harness-out is required with --harness-port")
        run_harness_capture(
            args.harness_port,
            args.baud,
            args.harness_out,
            args.settle,
            args.smart_confidence_floor,
        )

    if args.production_port:
        if not args.production_out:
            parser.error("--production-out is required with --production-port")
        run_production_sanity(
            args.production_port,
            args.baud,
            args.production_out,
            args.settle,
            args.smart_confidence_floor,
            args.smart_status_period,
        )

    if not args.harness_port and not args.production_port:
        parser.error("at least one port is required")
    return 0


if __name__ == "__main__":
    sys.exit(main())
