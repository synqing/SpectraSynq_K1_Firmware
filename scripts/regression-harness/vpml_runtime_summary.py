#!/usr/bin/env python3
"""Summarise VP Motion Lab VPAB byte captures.

This wraps the strict K1DF frame gate and then decodes VPABBytesPayload fields
needed by VPML evidence. It proves byte transport and final-byte coverage only;
it is not an eyes-on visual acceptance gate.
"""

import argparse
import binascii
import importlib.util
import json
import re
import sys
from pathlib import Path


CHANNEL_NAMES = {
    0: "primary",
    1: "secondary",
}


def _load_vpab_frame_gate():
    script = Path(__file__).with_name("vpab_frame_gate.py")
    spec = importlib.util.spec_from_file_location("vpab_frame_gate", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vpab_frame_gate = _load_vpab_frame_gate()


def _crc32(data):
    return binascii.crc32(data) & 0xFFFFFFFF


def _le16(data, offset):
    return int.from_bytes(data[offset:offset + 2], "little")


def _le32(data, offset):
    return int.from_bytes(data[offset:offset + 4], "little")


def _stats(values):
    if not values:
        return None
    return {
        "min": min(values),
        "max": max(values),
        "avg": round(float(sum(values)) / float(len(values)), 2),
    }


def _assemble_payload(record):
    payload = bytearray(record["len"] or 0)
    for index in range(record["chunks"] or 0):
        chunk = record["chunk_items"][index]
        offset = chunk["off"]
        payload[offset:offset + len(chunk["payload"])] = chunk["payload"]
    return bytes(payload)


def _decode_vpab_bytes_payload(record, payload):
    if len(payload) < 32:
        return None, {"seq": record["seq"], "field": "len", "message": "VPAB bytes payload header is truncated", "observed": len(payload)}
    channel_id = payload[0]
    channel = CHANNEL_NAMES.get(channel_id)
    if channel is None:
        return None, {"seq": record["seq"], "field": "channel", "message": "unknown VPAB channel", "observed": channel_id}

    mode = payload[1]
    leds = _le16(payload, 4)
    byte_count = _le16(payload, 6)
    if byte_count > len(payload) - 32:
        return None, {
            "seq": record["seq"],
            "field": "byte_count",
            "message": "byte_count overruns decoded payload",
            "observed": byte_count,
            "available": len(payload) - 32,
        }

    led_bytes = payload[32:32 + byte_count]
    return {
        "seq": record["seq"],
        "record_frame": record["frame"],
        "t_us": record["t_us"],
        "kind": "vpab_bytes",
        "channel": channel,
        "channel_id": channel_id,
        "mode": mode,
        "dither_step_value": payload[2],
        "fastled_dither": payload[3],
        "leds": leds,
        "byte_count": byte_count,
        "nonzero_led_bytes": sum(1 for byte in led_bytes if byte != 0),
        "energy_sum": sum(led_bytes),
        "max_byte": max(led_bytes) if led_bytes else 0,
        "render_us": _le32(payload, 8),
        "quant_us": _le32(payload, 12),
        "frame_us": _le32(payload, 16),
        "show_us": _le32(payload, 20),
        "over_budget_frames": _le32(payload, 24),
        "dropped_frames": _le32(payload, 28),
    }, None


def _raw_runtime_facts(raw_text):
    facts = {
        "port": None,
        "baud": None,
        "expected_chip_id": None,
        "observed_chip_id": None,
        "vpml_play_seen": False,
        "vpml_initial_status": None,
        "vpml_final_status": None,
        "vpab_records": None,
        "vp_perf_frame": None,
        "k1df_begin": None,
        "k1df_end": None,
    }
    if not raw_text:
        return facts
    for line in raw_text.splitlines():
        if line.startswith("#VPML_CAPTURE"):
            match = re.search(r"port=(\S+) baud=(\d+) expect_chip=([0-9A-Fa-f]+)", line)
            if match:
                facts["port"] = match.group(1)
                facts["baud"] = int(match.group(2))
                facts["expected_chip_id"] = match.group(3).upper()
        elif line.startswith("#IDENTITY"):
            match = re.search(r"chip_id=([0-9A-Fa-f]+) expected=([0-9A-Fa-f]+)", line)
            if match:
                facts["observed_chip_id"] = match.group(1).upper()
                facts["expected_chip_id"] = match.group(2).upper()
        elif line.startswith("VPML play_builtin,") and " active=1" in line:
            facts["vpml_play_seen"] = True
        elif line.startswith("VPML status active=1") and facts["vpml_initial_status"] is None:
            facts["vpml_initial_status"] = line
        elif line.startswith("VPML status active=0"):
            facts["vpml_final_status"] = line
        elif line.startswith("VPAB_RECORDS:"):
            facts["vpab_records"] = line
        elif line.startswith("VP_PERF_FRAME:"):
            facts["vp_perf_frame"] = line
        elif line.startswith("K1DF_BEGIN"):
            facts["k1df_begin"] = line
        elif line.startswith("K1DF_END"):
            facts["k1df_end"] = line
    return facts


def evaluate_text(frames_text, raw_text="", require_mode=250, require_channels=None,
                  fail_on_dark_sample=False, expect_chip_id=None):
    require_channels = set(require_channels or ("primary", "secondary"))
    strict_gate = vpab_frame_gate.evaluate_text(
        frames_text,
        require_modes={require_mode},
        require_channels=require_channels,
        require_kinds={"vpab_bytes"},
    )

    begin, end, records, record_order, issues = vpab_frame_gate._parse_stream(frames_text)
    failures = []
    decoded_records = []
    channel_counts = {}
    channel_nonzero_totals = {}
    channel_energy_totals = {}
    channel_max_byte = {}
    channel_render_us = {}
    channel_frame_us = {}
    channel_show_us = {}
    mode_counts = {}
    dark_sample_records = []

    if issues:
        failures.append({"metric": "strict_parse", "message": "raw K1DF stream has parser issues", "observed": len(issues)})

    for seq in record_order:
        record = records[seq]
        if record["kind"] != 2:
            continue
        payload = _assemble_payload(record)
        if record["crc"] is not None and _crc32(payload) != record["crc"]:
            failures.append({"seq": seq, "metric": "crc", "message": "record CRC mismatch"})
            continue
        decoded, failure = _decode_vpab_bytes_payload(record, payload)
        if failure:
            failures.append(failure)
            continue
        if decoded["mode"] != require_mode:
            failures.append({"seq": seq, "metric": "mode", "expected": require_mode, "observed": decoded["mode"]})
        if decoded["leds"] != 160:
            failures.append({"seq": seq, "metric": "leds", "expected": 160, "observed": decoded["leds"]})
        if decoded["byte_count"] != 480:
            failures.append({"seq": seq, "metric": "byte_count", "expected": 480, "observed": decoded["byte_count"]})
        if decoded["nonzero_led_bytes"] == 0:
            dark_sample_records.append({
                "seq": decoded["seq"],
                "record_frame": decoded["record_frame"],
                "channel": decoded["channel"],
            })

        channel = decoded["channel"]
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
        channel_nonzero_totals[channel] = channel_nonzero_totals.get(channel, 0) + decoded["nonzero_led_bytes"]
        channel_energy_totals[channel] = channel_energy_totals.get(channel, 0) + decoded["energy_sum"]
        channel_max_byte[channel] = max(channel_max_byte.get(channel, 0), decoded["max_byte"])
        channel_render_us.setdefault(channel, []).append(decoded["render_us"])
        channel_frame_us.setdefault(channel, []).append(decoded["frame_us"])
        channel_show_us.setdefault(channel, []).append(decoded["show_us"])
        mode_counts[str(decoded["mode"])] = mode_counts.get(str(decoded["mode"]), 0) + 1
        decoded_records.append(decoded)

    missing_channels = sorted(channel for channel in require_channels if channel not in channel_counts)
    if missing_channels:
        failures.append({"metric": "coverage.channel", "message": "required VPML channel missing", "expected": sorted(require_channels), "observed": sorted(channel_counts)})
    for channel in require_channels:
        if channel_nonzero_totals.get(channel, 0) <= 0 or channel_energy_totals.get(channel, 0) <= 0:
            failures.append({"metric": "coverage.bytes", "message": "channel has no nonzero final bytes", "channel": channel})
    if fail_on_dark_sample and dark_sample_records:
        failures.append({"metric": "dark_sample_records", "message": "dark sampled records are forbidden for this capture", "observed": dark_sample_records})

    raw_facts = _raw_runtime_facts(raw_text)
    chip_identity_match = None
    if expect_chip_id:
        expected = expect_chip_id.upper()
        observed = raw_facts.get("observed_chip_id")
        chip_identity_match = observed == expected
        if not chip_identity_match:
            failures.append({"metric": "chip_id", "message": "chip identity mismatch", "expected": expected, "observed": observed})

    observations = []
    if dark_sample_records:
        observations.append({
            "kind": "dark_sample_records",
            "message": "At least one sampled VPAB byte record was all dark. This may be valid for boot fade captures, but loop-safe captures should use --fail-on-dark-sample.",
            "records": dark_sample_records,
        })

    acceptance = {
        "strict_transport_clean": strict_gate["passed"],
        "primary_and_secondary_present": not missing_channels,
        "vpml_mode_on_all_records": mode_counts == {str(require_mode): len(decoded_records)},
        "nonzero_final_bytes_on_required_channels": all(
            channel_nonzero_totals.get(channel, 0) > 0 and channel_energy_totals.get(channel, 0) > 0
            for channel in require_channels
        ),
        "no_dark_sample_records": not dark_sample_records,
    }
    if raw_text:
        acceptance["vpml_started_and_stopped"] = raw_facts["vpml_play_seen"] and raw_facts["vpml_final_status"] is not None
        acceptance["vp_perf_no_over_or_dropped_frames"] = "over=0 dropped=0" in (raw_facts["vp_perf_frame"] or "")
    if expect_chip_id:
        acceptance["chip_identity_match"] = chip_identity_match

    passed = bool(decoded_records) and strict_gate["passed"] and not failures
    return {
        "schema": "vpml_runtime_summary.v1",
        "result": "PASS" if passed else "FAIL",
        "passed": passed,
        "acceptance": acceptance,
        "strict_gate": {
            "passed": strict_gate["passed"],
            "counts": strict_gate["counts"],
            "coverage": strict_gate["coverage"],
            "stream": strict_gate["stream"],
        },
        "runtime": raw_facts,
        "decoded_vpab_bytes": {
            "expected_mode": require_mode,
            "mode_counts": mode_counts,
            "channel_counts": channel_counts,
            "channel_nonzero_led_bytes_total": channel_nonzero_totals,
            "channel_energy_sum_total": channel_energy_totals,
            "channel_max_byte": channel_max_byte,
            "dark_sample_records": dark_sample_records,
            "render_us": {channel: _stats(values) for channel, values in channel_render_us.items()},
            "frame_us": {channel: _stats(values) for channel, values in channel_frame_us.items()},
            "show_us": {channel: _stats(values) for channel, values in channel_show_us.items()},
            "records": decoded_records,
        },
        "observations": observations,
        "failures": failures,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("frames_log", help="K1DF framed VPAB log path, or - for stdin")
    parser.add_argument("--raw-log", help="optional raw session log with identity/runtime status")
    parser.add_argument("--out", help="write JSON result to this path")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--require-mode", type=int, default=250)
    parser.add_argument("--require-channel", action="append", default=[])
    parser.add_argument("--fail-on-dark-sample", action="store_true")
    parser.add_argument("--expect-chip-id")
    args = parser.parse_args(argv)

    try:
        if args.frames_log == "-":
            frames_text = sys.stdin.read()
        else:
            frames_text = Path(args.frames_log).read_text(errors="replace")
        raw_text = Path(args.raw_log).read_text(errors="replace") if args.raw_log else ""
    except OSError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    channels = args.require_channel or ["primary", "secondary"]
    result = evaluate_text(
        frames_text,
        raw_text=raw_text,
        require_mode=args.require_mode,
        require_channels=channels,
        fail_on_dark_sample=args.fail_on_dark_sample,
        expect_chip_id=args.expect_chip_id,
    )
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        try:
            Path(args.out).write_text(output + "\n")
        except OSError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
    else:
        print(output)
    if args.summary:
        print(
            "VPML runtime summary %s: %d records, %d failure(s)"
            % (result["result"], len(result["decoded_vpab_bytes"]["records"]), len(result["failures"])),
            file=sys.stderr,
        )
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
