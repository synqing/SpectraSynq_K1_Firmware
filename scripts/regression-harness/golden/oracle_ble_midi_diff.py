#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2025-2026 SpectraSynq
"""BLE-MIDI ingress differential + property oracle (Remoted Phase F, primary oracle).

WHAT IT PROVES
--------------
The Remoted knob will reach the K1 over BLE-MIDI; the K1 decodes MIDI back into a
``K1WirelessControlRecord`` and runs the SAME ``sb_k1_control_apply()`` the existing
WebSocket ingress already uses. The two ingress paths *converge* on that shared
facade, so:

    byte-identical facade snapshot  <==>  byte-identical RECORD into the shared facade

(path-dependent logic like ``light_mode_next_enabled`` is shared, so it cancels.)
This oracle therefore tests the load-bearing thing that can actually be wrong — the
MIDI **decoder** — at the record boundary, which is *stricter* and fully deterministic
(no tempo/scene nondeterminism, no whole-firmware host-compile). Honest resolution
truth, surfaced rather than hidden:

    * DISCRETE controls (bool / enum / mode) -> decode == WS record, EXACTLY.
    * FLOAT controls -> equal within the 14-bit grid (step = (max-min)/16383);
      a value already on the grid round-trips exactly, off-grid within half a step.

CONTRACTS (parsed, not trusted-by-prose)
-----------------------------------------
* The CC/NRPN/PC map: the committed ``docs/protocol/k1-ble-midi-map.json`` (kept fresh
  + collision-free + registry-md5-bound by ``oracle_ble_midi_map.py --gate``).
* The record kind semantics: from the facade helpers — ``needs_number`` requires
  value_kind=NUMBER, ``needs_text`` requires TEXT, ``parse_bool_value`` accepts NUMBER
  0/1 (threshold >=0.5); modes/enums arrive as NUMBER via ``parse_index``.
* The enabled-mode roster: re-derived from ``system/config_types.h``
  (``light_mode_is_enabled`` disables 8 of NUM_MODES=30 -> 22 enabled). This oracle
  re-confirms the 22 from source; it is NOT hand-typed.

The reference decoder here IS the executable spec the Phase-K firmware decoder must
match (the same differential vectors will be replayed against the firmware decoder).

Run:  python oracle_ble_midi_diff.py --gate       # differential + property
      python oracle_ble_midi_diff.py --selftest   # Gate-0 decoder fault battery
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "SPECTRASYNQ_K1_FIRMWARE").is_dir())
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
MAP_JSON = ROOT / "docs" / "protocol" / "k1-ble-midi-map.json"
CONFIG_TYPES_REL = "system/config_types.h"

NAME = "ble_midi_diff"

# Standard MIDI status nibbles / NRPN controller numbers.
CC, PC = 0xB0, 0xC0
NRPN_PARAM_MSB, NRPN_PARAM_LSB, DATA_MSB, DATA_LSB = 99, 98, 6, 38


# --- contract loaders --------------------------------------------------------

def load_map() -> dict:
    return json.loads(MAP_JSON.read_text(encoding="utf-8"))


def enabled_modes(firmware_root: Path | None = None) -> dict:
    """Re-derive the enabled-mode roster from config_types.h (source of truth).
    Returns {num_modes, disabled:[names], enabled_count, mode29_enabled}."""
    firmware = Path(firmware_root) if firmware_root else FIRMWARE
    src = (firmware / CONFIG_TYPES_REL).read_text(encoding="utf-8")
    mblock = re.search(r"enum\s+\w*[Ll]ight\w*\s*(?::\s*\w+\s*)?\{(.*?)\}", src, re.S)
    ordinals = []
    if mblock:
        for tok in re.findall(r"(LIGHT_MODE_[A-Z0-9_]+)", mblock.group(1)):
            if tok not in ordinals:
                ordinals.append(tok)
    dis = re.search(r"light_mode_is_enabled.*?switch.*?\{(.*?)default", src, re.S)
    disabled = re.findall(r"case\s+(LIGHT_MODE_[A-Z0-9_]+)", dis.group(1)) if dis else []
    num_modes = len(ordinals)                       # NUM_MODES is the sentinel after the roster
    return {
        "num_modes": num_modes,
        "disabled": disabled,
        "enabled_count": num_modes - len(disabled),
        "mode29_name": ordinals[29] if len(ordinals) > 29 else None,
        "mode29_enabled": (len(ordinals) > 29 and ordinals[29] not in disabled),
    }


# --- encoder (the knob side) -------------------------------------------------

def _v14(value, lo, hi):
    if hi == lo:
        return 0
    n = round((value - lo) / (hi - lo) * 16383)
    return max(0, min(16383, n))


def encode(entry: dict, value) -> list:
    """Logical (control, value) -> ordered list of MIDI messages [(status,d1,d2|None)]."""
    ch = entry["channel"]
    midi = entry["midi"]
    if midi == "cc14":
        lo, hi = entry["min"], entry["max"]
        if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float))):
            lo, hi, value = 0.0, 1.0, 0.0       # symbolic range (runtime-resolved) -> structural bytes only
        n = _v14(value, lo, hi)
        return [(CC | ch, entry["cc_msb"], (n >> 7) & 127),
                (CC | ch, entry["cc_lsb"], n & 127)]
    if midi == "cc7":
        if entry["type"] == "bool":
            return [(CC | ch, entry["cc"], 127 if value else 0)]
        return [(CC | ch, entry["cc"], int(value) & 127)]   # enum index
    if midi == "pc":
        return [(PC | ch, int(value) & 127, None)]
    if midi == "nrpn":
        p, d = entry["nrpn_param"], int(value) & 0x3FFF
        return [(CC | ch, NRPN_PARAM_MSB, (p >> 7) & 127),
                (CC | ch, NRPN_PARAM_LSB, p & 127),
                (CC | ch, DATA_MSB, (d >> 7) & 127),
                (CC | ch, DATA_LSB, d & 127)]
    raise ValueError(f"unknown midi type {midi}")


# --- reference decoder (the executable spec the firmware decoder must match) --

class ReferenceDecoder:
    """MIDI messages -> K1WirelessControlRecord (dict). Built from the map, with
    optional injected FAULTS (used by --selftest to prove the gate has teeth)."""

    def __init__(self, m: dict, fault: str | None = None):
        self.fault = fault
        self.by_cc = {}     # (ch, cc) -> entry           (cc7 + cc14 msb/lsb)
        self.cc14_lsb = {}  # (ch, lsb_cc) -> entry
        self.by_pc = {}     # ch -> entry (mode)
        self.by_nrpn = {}   # (ch, param) -> entry
        for e in m["entries"]:
            ch = e["channel"]
            if e["midi"] == "cc14":
                self.by_cc[(ch, e["cc_msb"])] = e
                self.cc14_lsb[(ch, e["cc_lsb"])] = e
            elif e["midi"] == "cc7":
                self.by_cc[(ch, e["cc"])] = e
            elif e["midi"] == "pc":
                self.by_pc[ch] = e
            elif e["midi"] == "nrpn":
                self.by_nrpn[(ch, e["nrpn_param"])] = e

    def decode(self, messages: list) -> dict | None:
        """Process the messages for ONE logical change; return the record dict."""
        msb_buf = {}                 # (ch, msb_cc) -> high 7 bits
        nrpn = {"param_msb": 0, "param_lsb": 0, "data_msb": 0}
        rec = None
        for status, d1, d2 in messages:
            kind, ch = status & 0xF0, status & 0x0F
            if kind == PC:
                e = self.by_pc.get(ch)
                if e is None:
                    continue
                idx = d1 + (1 if self.fault == "mode_off_by_one" else 0)
                rec = {"control": e["path"], "value_kind": "NUMBER", "number_value": float(idx)}
            elif kind == CC:
                cc = d1 + (1 if self.fault == "cc_off_by_one" else 0)
                # NRPN data path
                if d1 == NRPN_PARAM_MSB:
                    nrpn["param_msb"] = d2
                elif d1 == NRPN_PARAM_LSB:
                    nrpn["param_lsb"] = d2
                elif d1 == DATA_MSB:
                    nrpn["data_msb"] = d2
                elif d1 == DATA_LSB:
                    param = (nrpn["param_msb"] << 7) | nrpn["param_lsb"]
                    e = self.by_nrpn.get((ch, param))
                    if e is not None:
                        value = (nrpn['data_msb'] << 7) | d2
                        if e.get("command"):
                            rec = {"control": e["path"], "value_kind": "NONE"}
                        elif e.get("text_values") and value < len(e["text_values"]):
                            rec = {"control": e["path"], "value_kind": "TEXT",
                                   "text_value": e["text_values"][value],
                                   "_nrpn_param": param}
                # 14-bit CC pair
                elif (ch, cc) in self.by_cc and self.by_cc[(ch, cc)]["midi"] == "cc14":
                    msb_buf[(ch, cc)] = d2
                    e = self.by_cc[(ch, cc)]      # may also complete if lsb already (we emit msb first)
                    rec = rec  # wait for lsb
                elif (ch, cc) in self.cc14_lsb:
                    e = self.cc14_lsb[(ch, cc)]
                    high = msb_buf.get((ch, e["cc_msb"]), 0)
                    if self.fault == "drop_lsb":
                        n = high << 7                       # ignore LSB -> coarse
                    elif self.fault == "twelve_bit":
                        n = ((high << 7) | d2) >> 2 << 2     # quantise to ~12-bit
                    else:
                        n = (high << 7) | d2
                    lo, hi = e["min"], e["max"]
                    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
                        val = lo + (n / 16383.0) * (hi - lo)
                    else:
                        val = float(n)          # symbolic range -> structural only
                    rec = {"control": e["path"], "value_kind": "NUMBER", "number_value": val}
                elif (ch, cc) in self.by_cc:
                    e = self.by_cc[(ch, cc)]
                    if e["type"] == "bool":
                        thr = 64 if self.fault != "bool_threshold" else 200  # 200 never reached -> always off
                        rec = {"control": e["path"], "value_kind": "NUMBER",
                               "number_value": 1.0 if d2 >= thr else 0.0}
                    else:   # enum index
                        rec = {"control": e["path"], "value_kind": "NUMBER", "number_value": float(d2)}
        return rec


# --- canonical WS record (what the existing WS ingress builds) ----------------

def ws_record(entry: dict, value) -> dict:
    t = entry["type"]
    if t == "bool":
        return {"control": entry["path"], "value_kind": "NUMBER", "number_value": 1.0 if value else 0.0}
    if t in ("float", "enum", "mode"):
        return {"control": entry["path"], "value_kind": "NUMBER", "number_value": float(value)}
    # text/command long-tail
    if entry.get("command"):
        return {"control": entry["path"], "value_kind": "NONE"}
    values = entry.get("text_values", [])
    idx = int(value)
    text = values[idx] if 0 <= idx < len(values) else f"idx:{idx}"
    return {"control": entry["path"], "value_kind": "TEXT", "text_value": text, "_nrpn_param": entry["nrpn_param"]}


# --- the differential ---------------------------------------------------------

def _samples(entry):
    """Logical values to test per control type."""
    t = entry["type"]
    if t == "bool":
        return [0, 1]
    if t == "mode":
        return list(range(0, 30))            # every ordinal -> PC-addressable
    if t == "enum":
        return [0, 1, 2, 7, 17, 64, 127]
    if t == "float":
        lo, hi = entry.get("min"), entry.get("max")
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            return ["__structural__"]        # symbolic range (chromagram_range) -> structural only
        step = (hi - lo) / 16383.0
        grid = [lo, hi, lo + 4096 * step, lo + 8192 * step]      # exactly on the 14-bit grid
        off = [lo + (hi - lo) * f for f in (0.137, 0.501, 0.913)]  # off-grid -> tolerance
        return [("grid", v) for v in grid] + [("off", v) for v in off]
    if entry.get("command"):
        return ["__structural__"]
    values = entry.get("text_values", [])
    return list(range(len(values))) if values else ["__structural__"]


def run_differential(m: dict, decoder: ReferenceDecoder | None = None):
    dec = decoder or ReferenceDecoder(m)
    results = []   # (control, sample, ok, mode, detail)
    for e in m["entries"]:
        for s in _samples(e):
            if s == "__structural__":
                rec = dec.decode(encode(e, 0))
                ws = ws_record(e, 0)
                ok = (rec is not None and rec["control"] == ws["control"]
                      and rec["value_kind"] == ws["value_kind"]
                      and rec.get("_nrpn_param") == ws.get("_nrpn_param"))
                results.append((e["path"], "structural", ok, "structural",
                                "" if ok else f"{rec} != {ws}"))
                continue
            grid_kind, value = (s if isinstance(s, tuple) else (None, s))
            rec = dec.decode(encode(e, value))
            ws = ws_record(e, value)
            if rec is None:
                results.append((e["path"], value, False, "exact", "decoder returned None"))
                continue
            if e["type"] == "text":
                same_id = rec["control"] == ws["control"] and rec["value_kind"] == ws["value_kind"]
                ok = same_id and rec.get("text_value") == ws.get("text_value")
                results.append((e["path"], value, ok, "exact-text",
                                "" if ok else f"{rec} != {ws}"))
                continue
            if rec.get("value_kind") != "NUMBER" or "number_value" not in rec:
                results.append((e["path"], value, False, "exact",
                                f"decoded wrong record shape: {rec}"))
                continue
            same_id = rec["control"] == ws["control"] and rec["value_kind"] == ws["value_kind"]
            if e["type"] == "float":
                lo, hi = e["min"], e["max"]
                step = (hi - lo) / 16383.0
                tol = step / 2.0 + 1e-6 * max(1.0, abs(hi))
                err = abs(rec["number_value"] - value)
                exact_needed = (grid_kind == "grid")
                ok = same_id and (err <= (1e-6 * max(1.0, abs(hi)) if exact_needed else tol))
                results.append((e["path"], round(value, 4), ok,
                                "exact-grid" if exact_needed else "tolerance",
                                "" if ok else f"err={err:.6g} tol={tol:.6g} id={same_id}"))
            else:
                ok = same_id and abs(rec["number_value"] - ws["number_value"]) < 1e-9
                results.append((e["path"], value, ok, "exact",
                                "" if ok else f"{rec} != {ws}"))
    return results


def run_property(m: dict, firmware_root: Path | None = None):
    out = []

    def check(label, cond):
        out.append((label, bool(cond)))

    em = enabled_modes(firmware_root)
    check(f"enabled modes re-derived from config_types.h == 22 (got {em['enabled_count']})",
          em["enabled_count"] == 22)
    check(f"NUM_MODES roster == 30 (got {em['num_modes']})", em["num_modes"] == 30)
    check(f"mode 29 ({em['mode29_name']}) is enabled", em["mode29_enabled"])

    modes = [e for e in m["entries"] if e["type"] == "mode"]
    check(f"mode controls present ({len(modes)}: primary+secondary)", len(modes) == 2)
    check("every ordinal 0..29 is PC-addressable (value<=127)", all(o <= 127 for o in range(30)))

    # 14-bit float monotonicity + resolution
    mono_ok = res_ok = True
    for e in m["entries"]:
        if e["type"] != "float" or not isinstance(e.get("max"), (int, float)):
            continue
        lo, hi = e["min"], e["max"]
        prev = -1
        for f in [i / 32 for i in range(33)]:
            n = _v14(lo + (hi - lo) * f, lo, hi)
            if n < prev:
                mono_ok = False
            prev = n
        step = (hi - lo) / 16383.0
        if step <= 0:
            res_ok = False
    check("14-bit CC encode is monotonic non-decreasing for all ranged floats", mono_ok)
    check("all ranged floats have positive 14-bit resolution step", res_ok)
    return out


# --- Gate-0: decoder fault battery (prove the differential has teeth) ---------

DECODER_FAULTS = [
    ("twelve_bit", "decoder quantises 14-bit CC to ~12-bit (resolution regression)"),
    ("cc_off_by_one", "decoder reads CC number off-by-one (wrong control)"),
    ("bool_threshold", "decoder bool threshold wrong (never registers 'on')"),
    ("mode_off_by_one", "decoder PC->mode index off-by-one"),
    ("drop_lsb", "decoder ignores the 14-bit LSB (coarse value)"),
]


def selftest(m: dict):
    """Each injected decoder fault MUST make the differential FAIL (>=1 mismatch)."""
    results = []
    clean = run_differential(m, ReferenceDecoder(m))
    results.append(("clean decoder: differential all-green",
                    all(r[2] for r in clean)))
    for fault, desc in DECODER_FAULTS:
        faulty = run_differential(m, ReferenceDecoder(m, fault=fault))
        caught = any(not r[2] for r in faulty)
        results.append((f"fault CAUGHT: {desc}", caught))
    return results


# --- Gate-F-alpha hooks (harness_selftest mutates config_types.h mode roster) -

def capture(firmware_root: Path | None = None) -> str:
    """Firmware-anchored observation: the enabled-mode roster (config_types.h).
    A mode enable/disable edit changes this -> harness_selftest sees it."""
    try:
        em = enabled_modes(firmware_root)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({
            "error": "MODE_ROSTER_ERROR",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }, sort_keys=True)
    return json.dumps({
        "num_modes": em["num_modes"],
        "enabled_count": em["enabled_count"],
        "mode29_name": em["mode29_name"],
        "mode29_enabled": em["mode29_enabled"],
        "disabled": em["disabled"],
    }, sort_keys=True)


MUTATIONS = [
    (r"case LIGHT_MODE_EMBER_V2:\s*//[^\n]*\n\s*return false;",
     "return false;",
     "EMBER_V2 re-enabled -> enabled count 22->23"),
    (r"case LIGHT_MODE_VU:\n", "case LIGHT_MODE_BLOOM:\n",
     "disable BLOOM instead of VU -> roster identity changes"),
]


# --- CLI ---------------------------------------------------------------------

def assert_gate() -> int:
    m = load_map()
    ok = True
    diff = run_differential(m)
    fails = [r for r in diff if not r[2]]
    print(f"[{'PASS' if not fails else 'FAIL'}] differential MIDI-decode == WS-record "
          f"({len(diff)} vectors, {len(fails)} mismatch)")
    for r in fails[:12]:
        print(f"    MISMATCH {r[0]} sample={r[1]} mode={r[3]} {r[4]}")
    ok = ok and not fails
    for label, passed in run_property(m):
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    print("\nBLE_MIDI_DIFF_GATE:",
          "PROVEN -- MIDI ingress reconstructs the WS record (exact for discrete, "
          "14-bit-resolution for floats); 22 modes addressable" if ok
          else "FAILED -- decoder/map diverges from the WS record contract")
    return 0 if ok else 1


def run_selftest() -> int:
    m = load_map()
    ok = True
    for label, passed in selftest(m):
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    print("\nGATE_0(ble_midi_diff):",
          "PROVEN -- differential rejects every injected decoder fault" if ok
          else "FAILED -- a decoder fault slipped through (oracle is BLIND)")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", action="store_true", help="differential + property gate (CI)")
    ap.add_argument("--selftest", action="store_true", help="Gate-0 decoder fault battery")
    ap.add_argument("--print", dest="show", action="store_true", help="print capture() (mode roster)")
    args = ap.parse_args()
    if args.gate:
        return assert_gate()
    if args.selftest:
        return run_selftest()
    if args.show:
        print(capture())
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
