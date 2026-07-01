import importlib.util
import math
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "scripts" / "regression-harness" / "golden" / "oracle_ble_midi_diff.py"
K1_HEADER_GEN = ROOT / "scripts" / "ble_midi" / "gen_k1_ble_midi_header.py"
K1_HEADER = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network" / "k1_ble_midi_map.h"
K1_BLE_MIDI_MAX_RECORDS_PER_PACKET = 16


def _load_oracle():
    spec = importlib.util.spec_from_file_location("oracle_ble_midi_diff", ORACLE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _flatten(messages):
    out = [0x80, 0x80]
    for status, d1, d2 in messages:
        out.extend([status, d1])
        if d2 is not None:
            out.append(d2)
    return out


def _driver_source():
    return textwrap.dedent(
        r"""
        #include <stdint.h>
        #include <stdlib.h>

        #include <iomanip>
        #include <iostream>
        #include <sstream>
        #include <string>
        #include <vector>

        #include "k1_ble_midi_decoder.h"

        const char* kind_name(SBWirelessValueKind kind) {
          switch (kind) {
            case SB_WIRELESS_VALUE_NONE: return "NONE";
            case SB_WIRELESS_VALUE_NUMBER: return "NUMBER";
            case SB_WIRELESS_VALUE_TEXT: return "TEXT";
          }
          return "UNKNOWN";
        }

        int main() {
          std::cout << std::setprecision(10);
          std::string line;
          while (std::getline(std::cin, line)) {
            if (line.empty()) continue;
            std::istringstream in(line);
            size_t cap = 0;
            in >> cap;
            std::vector<uint8_t> packet;
            std::string token;
            while (in >> token) {
              packet.push_back(static_cast<uint8_t>(strtoul(token.c_str(), nullptr, 16)));
            }

            K1BleMidiDecoderState state;
            k1_ble_midi_decoder_reset(&state);
            K1WirelessControlRecord records[K1_BLE_MIDI_MAX_RECORDS_PER_PACKET];
            size_t count = 0;
            K1BleMidiDecodeStatus status = k1_ble_midi_decode_packet(
                &state, packet.data(), packet.size(), records, cap, &count);
            std::cout << k1_ble_midi_decode_status_name(status) << "|" << count;
            for (size_t i = 0; i < count; ++i) {
              std::cout << "|" << records[i].control
                        << "," << kind_name(records[i].value_kind)
                        << "," << records[i].number_value
                        << "," << records[i].text_value;
            }
            std::cout << "\n";
          }
          return 0;
        }
        """
    )


def _build_driver(tmp_path, *extra_flags):
    driver = tmp_path / "decoder_driver.cpp"
    exe = tmp_path / ("decoder_driver_" + str(abs(hash(extra_flags))))
    driver.write_text(_driver_source(), encoding="utf-8")
    cmd = [
        "c++",
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I",
        str(ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network"),
        "-I",
        str(ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control"),
        *extra_flags,
        str(driver),
        str(ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network" / "k1_ble_midi_decoder.cpp"),
        "-o",
        str(exe),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    return exe


def _decode_many(exe, packets, cap=K1_BLE_MIDI_MAX_RECORDS_PER_PACKET):
    lines = []
    for packet in packets:
        line = " ".join([str(cap)] + [f"{b:02x}" for b in packet])
        lines.append(line)
    proc = subprocess.run(
        [str(exe)],
        input="\n".join(lines) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    return [_parse_output(line) for line in proc.stdout.splitlines()]


def _parse_output(line):
    parts = line.split("|")
    records = []
    for raw in parts[2:]:
        control, kind, number, text = raw.split(",", 3)
        records.append({
            "control": control,
            "value_kind": kind,
            "number_value": float(number),
            "text_value": text,
        })
    return {"status": parts[0], "count": int(parts[1]), "records": records}


def _vectors():
    oracle = _load_oracle()
    contract = oracle.load_map()
    for entry in contract["entries"]:
        for sample in oracle._samples(entry):
            if sample == "__structural__":
                value = 0
                mode = "structural"
            else:
                mode, value = sample if isinstance(sample, tuple) else (None, sample)
            yield entry, mode, value, _flatten(oracle.encode(entry, value)), oracle.ws_record(entry, value)


def _record_matches(entry, mode, value, actual, expected):
    if actual["control"] != expected["control"] or actual["value_kind"] != expected["value_kind"]:
        return False
    if mode == "structural":
        return True
    if actual["value_kind"] == "TEXT":
        return actual["text_value"] == expected["text_value"]
    if actual["value_kind"] == "NONE":
        return True
    if entry["type"] == "float":
        lo, hi = entry["min"], entry["max"]
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            return True
        step = (hi - lo) / 16383.0
        exact_tol = 1e-6 * max(1.0, abs(hi))
        loose_tol = step / 2.0 + exact_tol
        tol = exact_tol if mode == "grid" else loose_tol
        return math.isclose(actual["number_value"], float(value), abs_tol=tol)
    return math.isclose(actual["number_value"], expected["number_value"], abs_tol=1e-9)


def test_generated_k1_header_matches_committed_map(tmp_path):
    generated = tmp_path / "k1_ble_midi_map.h"
    subprocess.run(
        ["python3", str(K1_HEADER_GEN), "--out", str(generated)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert generated.read_text(encoding="utf-8") == K1_HEADER.read_text(encoding="utf-8")


def test_firmware_decoder_matches_oracle_for_all_71_controls(tmp_path):
    exe = _build_driver(tmp_path)
    vectors = list(_vectors())
    outputs = _decode_many(exe, [packet for *_rest, packet, _expected in vectors],
                           cap=K1_BLE_MIDI_MAX_RECORDS_PER_PACKET)

    failures = []
    for (entry, mode, value, _packet, expected), output in zip(vectors, outputs):
        if output["status"] != "OK" or output["count"] != 1:
            failures.append((entry["path"], value, output))
            continue
        if not _record_matches(entry, mode, value, output["records"][0], expected):
            failures.append((entry["path"], value, output["records"][0], expected))
    assert not failures


def test_decoder_framing_fault_and_overflow_behaviour(tmp_path):
    oracle = _load_oracle()
    contract = oracle.load_map()
    exe = _build_driver(tmp_path)

    cc7_a = next(e for e in contract["entries"] if e["path"] == "primary.palette_mode")
    cc7_b = next(e for e in contract["entries"] if e["path"] == "secondary.enabled")
    multi = _flatten(oracle.encode(cc7_a, 1) + oracle.encode(cc7_b, 1))
    malformed_short = [0x80]
    malformed_partial = [0x80, 0x80, 0xB0, 0x01]
    oversized = [0x80, 0x80] + [0xF8] * 246

    normal, overflow, short, partial, too_big = _decode_many(
        exe,
        [multi, multi, malformed_short, malformed_partial, oversized],
        cap=K1_BLE_MIDI_MAX_RECORDS_PER_PACKET,
    )
    assert normal["status"] == "OK"
    assert normal["count"] == 2

    overflow = _decode_many(exe, [multi], cap=1)[0]
    assert overflow["status"] == "OUTPUT_OVERFLOW"
    assert overflow["count"] == 1

    assert short["status"] == "MALFORMED"
    assert partial["status"] == "MALFORMED"
    assert too_big["status"] == "OVERSIZED"


def test_decoder_nrpn_incomplete_sequence_resets_then_accepts_valid_nrpn(tmp_path):
    oracle = _load_oracle()
    contract = oracle.load_map()
    exe = _build_driver(tmp_path)

    preset = next(e for e in contract["entries"] if e["path"] == "primary.preset")
    incomplete_then_valid = [
        0x80, 0x80,
        0xB0, 38, 0,  # data LSB before param/data MSB: ignored and resets channel state
        *_flatten(oracle.encode(preset, 4))[2:],
    ]
    output = _decode_many(exe, [incomplete_then_valid], cap=K1_BLE_MIDI_MAX_RECORDS_PER_PACKET)[0]
    assert output["status"] == "OK"
    assert output["count"] == 1
    assert output["records"][0]["control"] == "primary.preset"
    assert output["records"][0]["value_kind"] == "TEXT"
    assert output["records"][0]["text_value"] == "classic"


def test_injected_decoder_faults_are_caught(tmp_path):
    fault_sets = [
        ("-DK1_BLE_MIDI_DECODER_FAULT_DROP_LSB=1",),
        ("-DK1_BLE_MIDI_DECODER_FAULT_TWELVE_BIT=1",),
        ("-DK1_BLE_MIDI_DECODER_FAULT_CC_OFF_BY_ONE=1",),
        ("-DK1_BLE_MIDI_DECODER_BOOL_THRESHOLD=200",),
        ("-DK1_BLE_MIDI_DECODER_FAULT_MODE_OFF_BY_ONE=1",),
    ]
    vectors = list(_vectors())
    packets = [packet for *_rest, packet, _expected in vectors]
    for flags in fault_sets:
        exe = _build_driver(tmp_path, *flags)
        outputs = _decode_many(exe, packets, cap=K1_BLE_MIDI_MAX_RECORDS_PER_PACKET)
        mismatches = 0
        for (entry, mode, value, _packet, expected), output in zip(vectors, outputs):
            if output["status"] != "OK" or output["count"] != 1:
                mismatches += 1
                continue
            if not _record_matches(entry, mode, value, output["records"][0], expected):
                mismatches += 1
        assert mismatches > 0, flags
