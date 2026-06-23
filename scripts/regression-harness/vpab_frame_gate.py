#!/usr/bin/env python3
"""Strict gate for deferred VPAB diagnostic frames.

This parser is intentionally fail-closed. A capture with survivor frames plus
unexpected fragments is invalid evidence.
"""

import argparse
import binascii
import json
import sys


BEGIN_TAG = "K1DF_BEGIN"
RECORD_TAG = "K1DFR"
CHUNK_TAG = "K1DFC"
END_TAG = "K1DF_END"
ERROR_TAG = "K1DF_ERROR"

VALID_TAGS = {BEGIN_TAG, RECORD_TAG, CHUNK_TAG, END_TAG, ERROR_TAG}
KIND_NAMES = {
    1: "vpab_metrics",
    2: "vpab_bytes",
    4: "k1_pin_evidence",
}
CHANNEL_NAMES = {
    0: "primary",
    1: "secondary",
}


def _issue(line, field, message, value=None):
    out = {"line": line, "field": field, "message": message}
    if value is not None:
        out["value"] = value
    return out


def _parse_int(value):
    text = str(value).strip()
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(text, 10)


def _parse_fields(raw, line_no):
    parts = [part.strip() for part in raw.split(",")]
    tag = parts[0] if parts else ""
    fields = {}
    issues = []
    if tag not in VALID_TAGS:
        issues.append(_issue(line_no, None, "unexpected line in strict frame stream", raw))
        return tag, fields, issues
    for part in parts[1:]:
        if not part:
            issues.append(_issue(line_no, None, "empty token", part))
            continue
        if "=" not in part:
            issues.append(_issue(line_no, None, "token without key=value", part))
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in fields:
            issues.append(_issue(line_no, key, "duplicate field", value))
            continue
        fields[key] = value
    return tag, fields, issues


def _require_int(fields, field, line_no, issues):
    if field not in fields:
        issues.append(_issue(line_no, field, "missing mandatory field"))
        return None
    try:
        return _parse_int(fields[field])
    except ValueError:
        issues.append(_issue(line_no, field, "field must be integer", fields[field]))
        return None


def _require_hex_payload(fields, line_no, issues):
    if "hex" not in fields:
        issues.append(_issue(line_no, "hex", "missing mandatory field"))
        return b""
    text = fields["hex"].strip()
    if len(text) % 2 != 0:
        issues.append(_issue(line_no, "hex", "hex payload has odd length", text))
        return b""
    try:
        return binascii.unhexlify(text)
    except (binascii.Error, ValueError):
        issues.append(_issue(line_no, "hex", "hex payload is malformed", text))
        return b""


def _crc32(data):
    return binascii.crc32(data) & 0xFFFFFFFF


def _parse_stream(text):
    issues = []
    begin = None
    end = None
    records = {}
    record_order = []

    for line_no, raw_line in enumerate(text.splitlines(), 1):
        raw = raw_line.strip()
        if not raw:
            continue
        tag, fields, field_issues = _parse_fields(raw, line_no)
        issues.extend(field_issues)
        if field_issues:
            continue
        if tag == ERROR_TAG:
            issues.append(_issue(line_no, None, "device reported frame-stream error", raw))
            continue
        ver = _require_int(fields, "ver", line_no, issues)
        if ver is not None and ver != 1:
            issues.append(_issue(line_no, "ver", "unsupported frame-stream version", ver))

        if tag == BEGIN_TAG:
            if begin is not None:
                issues.append(_issue(line_no, None, "duplicate K1DF_BEGIN"))
            begin = {"line": line_no, "fields": fields}
            for key in ("records", "captured", "dropped", "corrupt", "overflowed", "payload_max", "chunk_bytes"):
                _require_int(fields, key, line_no, issues)
        elif tag == END_TAG:
            if end is not None:
                issues.append(_issue(line_no, None, "duplicate K1DF_END"))
            end = {"line": line_no, "fields": fields}
            for key in ("records", "chunks", "dropped", "corrupt", "overflowed"):
                _require_int(fields, key, line_no, issues)
        elif tag == RECORD_TAG:
            seq = _require_int(fields, "seq", line_no, issues)
            kind = _require_int(fields, "kind", line_no, issues)
            frame = _require_int(fields, "frame", line_no, issues)
            t_us = _require_int(fields, "t_us", line_no, issues)
            flags = _require_int(fields, "flags", line_no, issues)
            length = _require_int(fields, "len", line_no, issues)
            crc = _require_int(fields, "crc", line_no, issues)
            chunks = _require_int(fields, "chunks", line_no, issues)
            if seq is None:
                continue
            if seq in records:
                issues.append(_issue(line_no, "seq", "duplicate record sequence", seq))
                continue
            records[seq] = {
                "line": line_no,
                "seq": seq,
                "kind": kind,
                "frame": frame,
                "t_us": t_us,
                "flags": flags,
                "len": length,
                "crc": crc,
                "chunks": chunks,
                "chunk_items": {},
            }
            record_order.append(seq)
        elif tag == CHUNK_TAG:
            seq = _require_int(fields, "seq", line_no, issues)
            idx = _require_int(fields, "idx", line_no, issues)
            off = _require_int(fields, "off", line_no, issues)
            length = _require_int(fields, "len", line_no, issues)
            crc = _require_int(fields, "crc", line_no, issues)
            payload = _require_hex_payload(fields, line_no, issues)
            if seq is None or idx is None:
                continue
            if seq not in records:
                issues.append(_issue(line_no, "seq", "chunk references unknown record sequence", seq))
                continue
            if idx in records[seq]["chunk_items"]:
                issues.append(_issue(line_no, "idx", "duplicate chunk index for sequence", idx))
                continue
            if length is not None and len(payload) != length:
                issues.append(_issue(line_no, "len", "chunk length does not match decoded hex bytes", length))
            if crc is not None and _crc32(payload) != crc:
                issues.append(_issue(line_no, "crc", "chunk CRC mismatch", fields.get("crc")))
            records[seq]["chunk_items"][idx] = {
                "line": line_no,
                "idx": idx,
                "off": off,
                "len": length,
                "crc": crc,
                "payload": payload,
            }

    return begin, end, records, record_order, issues


def _parsed_int_fields(fields):
    parsed = {}
    for key, value in fields.items():
        try:
            parsed[key] = _parse_int(value)
        except ValueError:
            parsed[key] = value
    return parsed


def _coverage_from_payload(record, payload):
    if record["kind"] == 4:
        if len(payload) < 4:
            return None
        channel_value = payload[1]
        mode_value = payload[2] | (payload[3] << 8)
    elif len(payload) >= 2:
        channel_value = payload[0]
        mode_value = payload[1]
    else:
        return None

    return {
        "seq": record["seq"],
        "kind": KIND_NAMES.get(record["kind"], "unknown"),
        "kind_id": record["kind"],
        "mode": mode_value,
        "channel": CHANNEL_NAMES.get(channel_value, "unknown"),
        "channel_id": channel_value,
        "frame": record["frame"],
    }


def evaluate_text(text, require_modes=None, require_channels=None, require_kinds=None):
    require_modes = set(require_modes or [])
    require_channels = set(require_channels or [])
    require_kinds = set(require_kinds or [])

    begin, end, records, record_order, issues = _parse_stream(text)
    failures = []
    assembled = []
    total_chunks = 0

    if begin is None:
        issues.append(_issue(0, None, "missing K1DF_BEGIN"))
    if end is None:
        issues.append(_issue(0, None, "missing K1DF_END"))

    if record_order:
        expected = record_order[0]
        for seq in record_order:
            if seq != expected:
                failures.append(
                    {
                        "seq": seq,
                        "metric": "seq",
                        "message": "record sequence gap",
                        "expected": expected,
                        "observed": seq,
                    }
                )
                expected = seq
            expected += 1

    for seq in record_order:
        record = records[seq]
        if record["kind"] not in KIND_NAMES:
            failures.append({"seq": seq, "metric": "kind", "message": "unknown diagnostic record kind", "observed": record["kind"]})
        chunk_items = record["chunk_items"]
        expected_chunks = record["chunks"]
        if expected_chunks is None:
            continue
        if len(chunk_items) != expected_chunks:
            failures.append(
                {
                    "seq": seq,
                    "metric": "chunks",
                    "message": "chunk count mismatch",
                    "expected": expected_chunks,
                    "observed": len(chunk_items),
                }
            )
            continue
        payload = bytearray(record["len"] or 0)
        cursor = 0
        for idx in range(expected_chunks):
            if idx not in chunk_items:
                failures.append({"seq": seq, "metric": "idx", "message": "missing chunk index", "expected": idx})
                continue
            chunk = chunk_items[idx]
            if chunk["off"] != cursor:
                failures.append(
                    {
                        "seq": seq,
                        "metric": "off",
                        "message": "chunk offset is not contiguous",
                        "expected": cursor,
                        "observed": chunk["off"],
                    }
                )
            chunk_end = (chunk["off"] or 0) + len(chunk["payload"])
            if chunk_end > len(payload):
                failures.append({"seq": seq, "metric": "len", "message": "chunk overruns declared record length", "observed": chunk_end})
            else:
                payload[chunk["off"]:chunk_end] = chunk["payload"]
            cursor = chunk_end
            total_chunks += 1
        if cursor != (record["len"] or 0):
            failures.append(
                {
                    "seq": seq,
                    "metric": "len",
                    "message": "assembled payload length mismatch",
                    "expected": record["len"],
                    "observed": cursor,
                }
            )
        payload_bytes = bytes(payload)
        if record["crc"] is not None and _crc32(payload_bytes) != record["crc"]:
            failures.append({"seq": seq, "metric": "crc", "message": "record CRC mismatch", "observed": "0x%08X" % _crc32(payload_bytes)})
        coverage = _coverage_from_payload(record, payload_bytes)
        if coverage is not None:
            assembled.append(coverage)

    begin_fields = begin["fields"] if begin else {}
    end_fields = end["fields"] if end else {}
    for source, fields in (("begin", begin_fields), ("end", end_fields)):
        for key in ("dropped", "corrupt", "overflowed"):
            if key in fields:
                try:
                    value = _parse_int(fields[key])
                except ValueError:
                    continue
                if value != 0:
                    failures.append(
                        {
                            "source": source,
                            "metric": key,
                            "message": "diagnostic transport counter must be zero",
                            "observed": value,
                            "threshold": "== 0",
                        }
                    )

    if begin and "records" in begin_fields:
        expected_records = _parse_int(begin_fields["records"])
        if expected_records != len(record_order):
            failures.append({"metric": "begin.records", "message": "begin record count mismatch", "expected": expected_records, "observed": len(record_order)})
    if end and "records" in end_fields:
        expected_records = _parse_int(end_fields["records"])
        if expected_records != len(assembled):
            failures.append({"metric": "end.records", "message": "end record count mismatch", "expected": expected_records, "observed": len(assembled)})
    if end and "chunks" in end_fields:
        expected_chunks = _parse_int(end_fields["chunks"])
        if expected_chunks != total_chunks:
            failures.append({"metric": "end.chunks", "message": "end chunk count mismatch", "expected": expected_chunks, "observed": total_chunks})

    modes_seen = sorted({item["mode"] for item in assembled})
    channels_seen = sorted({item["channel"] for item in assembled})
    kinds_seen = sorted({item["kind"] for item in assembled})
    stream = {
        "begin": _parsed_int_fields(begin_fields) if begin else {},
        "end": _parsed_int_fields(end_fields) if end else {},
    }

    for mode in sorted(require_modes):
        if mode not in modes_seen:
            failures.append({"metric": "coverage.mode", "message": "required mode missing", "expected": mode, "observed": modes_seen})
    for channel in sorted(require_channels):
        if channel not in channels_seen:
            failures.append({"metric": "coverage.channel", "message": "required channel missing", "expected": channel, "observed": channels_seen})
    for kind in sorted(require_kinds):
        if kind not in kinds_seen:
            failures.append({"metric": "coverage.kind", "message": "required record kind missing", "expected": kind, "observed": kinds_seen})

    passed = not issues and not failures and bool(assembled)
    return {
        "schema": "vpab_frame_gate.v1",
        "result": "PASS" if passed else "FAIL",
        "passed": passed,
        "counts": {
            "records": len(record_order),
            "assembled_records": len(assembled),
            "chunks": total_chunks,
            "issues": len(issues),
            "failures": len(failures),
        },
        "coverage": {
            "modes": modes_seen,
            "channels": channels_seen,
            "kinds": kinds_seen,
            "records": assembled,
        },
        "stream": stream,
        "issues": issues,
        "failures": failures,
    }


def _parse_kind(value):
    text = str(value).strip()
    for kind_id, name in KIND_NAMES.items():
        if text == name:
            return name
        if text == str(kind_id):
            return name
    raise argparse.ArgumentTypeError("unknown kind %s" % value)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("log", help="K1DF framed log path, or - for stdin")
    parser.add_argument("--out", help="write JSON result to this path")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--require-mode", action="append", type=int, default=[])
    parser.add_argument("--require-channel", action="append", choices=sorted(CHANNEL_NAMES.values()), default=[])
    parser.add_argument("--require-kind", action="append", type=_parse_kind, default=[])
    args = parser.parse_args(argv)

    try:
        if args.log == "-":
            text = sys.stdin.read()
        else:
            with open(args.log, "r", errors="replace") as handle:
                text = handle.read()
    except OSError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    result = evaluate_text(
        text,
        require_modes=args.require_mode,
        require_channels=args.require_channel,
        require_kinds=args.require_kind,
    )
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        try:
            with open(args.out, "w") as handle:
                handle.write(output)
                handle.write("\n")
        except OSError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
    else:
        print(output)
    if args.summary:
        print(
            "VPAB frame gate %s: %d records, %d issue(s), %d failure(s)"
            % (
                result["result"],
                result["counts"]["assembled_records"],
                result["counts"]["issues"],
                result["counts"]["failures"],
            ),
            file=sys.stderr,
        )
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
