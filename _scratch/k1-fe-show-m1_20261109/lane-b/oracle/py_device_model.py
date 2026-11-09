"""Independent Python model of the FE device's PRSM byte path (second implementation for the
differential oracle; the first is the real firmware C compiled by device_oracle.cpp).

Written from the behaviour described in B-P1-contract.md (scanner: hunt 'P', require 'R','S','M'
in sequence, re-hunt the breaking byte; after 34 bytes parse magic+version; authored layer rejects
hz outside 30..240; check_serial demux: scanner first, then ':' command mode, CR/LF skip, rest are
hotkey candidates). It does not import or translate the C source line by line.
"""

from __future__ import annotations

import struct

FRAME = 34
MAGIC = b"PRSM"

# Immediate hotkeys, serial_menu.cpp serial_hotkey_is_immediate() at 407fdf6f (lines 1730-1825),
# unconditional cases only. 'm' is present unless ENABLE_MOTION_PROBE (non-shipping).
IMMEDIATE_HOTKEYS = set("gGuym-=_+ hN;Y[]0123456789!@#$%^&*()\\UiIoOpPjJkKlLqQwWeErRtT,./asSdf")
# Build-flag-conditional (K1_LOOK_LIB_V1 / K1_VIVID_PRECOMP_V1); not resolved for k1_fe here.
CONDITIONAL_HOTKEYS = set("zZv")
# Hotkeys with persistent or Captain-gated side effects (serial_menu.cpp handlers at 407fdf6f):
# 'N' arm noise calibration, 'Y' confirm noise calibration, '!'..')' preset slot save,
# 'S' save show state for next boot, '1'..'9' preset slot load.
DANGEROUS_HOTKEYS = set("NY!@#$%^&*()S123456789")


def parse_frame(buf: bytes):
    """Return dict or None, mirroring the device's acceptance of a complete 34-byte frame."""
    if len(buf) < FRAME or buf[:4] != MAGIC or buf[4] != 1:
        return None
    hz = buf[5]
    seq, t_us = struct.unpack_from("<IQ", buf, 6)
    prim8 = list(struct.unpack_from("<8H", buf, 18))
    return {"hz": hz, "seq": seq, "t_us": t_us, "p": prim8}


def authored_maps(frame) -> bool:
    return frame is not None and 30 <= frame["hz"] <= 240


class Scanner:
    def __init__(self):
        self.buf = bytearray()

    def push(self, b: int):
        """Returns ('NONE'|'CONSUMED'|'FRAME_OK'|'FRAME_BAD', frame|None)."""
        n = len(self.buf)
        if n == 0:
            if b != MAGIC[0]:
                return "NONE", None
            self.buf.append(b)
            return "CONSUMED", None
        if n < 4:
            if b == MAGIC[n]:
                self.buf.append(b)
                return "CONSUMED", None
            self.buf.clear()
            return self.push(b)
        self.buf.append(b)
        if len(self.buf) < FRAME:
            return "CONSUMED", None
        fr = parse_frame(bytes(self.buf))
        self.buf.clear()
        return ("FRAME_OK", fr) if fr else ("FRAME_BAD", None)


def chunk_verdicts(data: bytes):
    out = []
    for k in range(len(data) // FRAME):
        fr = parse_frame(data[k * FRAME:(k + 1) * FRAME])
        out.append({"k": k, "parse": int(fr is not None), "map": int(authored_maps(fr))})
    return out


def scan_events(data: bytes):
    sc = Scanner()
    ev = []
    for i, b in enumerate(data):
        r, fr = sc.push(b)
        if r == "CONSUMED":
            continue
        e = {"off": i, "r": r, "b": b}
        if fr:
            e.update(hz=fr["hz"], seq=fr["seq"], t_us=fr["t_us"])
        ev.append(e)
    return ev, len(sc.buf)


def demux(data: bytes):
    sc = Scanner()
    cmd_mode = False
    cmd = bytearray()
    frames, leaks, enters, commands = [], [], [], []
    for i, b in enumerate(data):
        if cmd_mode:
            if b in (0x0D, 0x0A):
                if cmd:
                    commands.append({"end_off": i, "len": len(cmd)})
                cmd.clear()
                cmd_mode = False
            else:
                cmd.append(b)
                if len(cmd) >= 127:
                    commands.append({"end_off": i, "len": len(cmd)})
                    cmd.clear()
                    cmd_mode = False
            continue
        r, fr = sc.push(b)
        if r != "NONE":
            if r == "FRAME_OK":
                frames.append({"off": i, "seq": fr["seq"], "t_us": fr["t_us"], "hz": fr["hz"],
                               "mapped": int(authored_maps(fr)), "p": fr["p"]})
            continue
        if b == ord(":"):
            cmd_mode = True
            cmd.clear()
            enters.append(i)
        elif b in (0x0D, 0x0A):
            pass
        else:
            leaks.append(i)
    return {"frames_ok": frames, "leak_offsets": leaks, "command_mode_enter": enters,
            "commands_parsed": commands, "command_mode_at_eof": int(cmd_mode),
            "pending_cmd_len": len(cmd)}


def hotkey_report(data: bytes, leak_offsets):
    hits = [(o, chr(data[o])) for o in leak_offsets if chr(data[o]) in IMMEDIATE_HOTKEYS]
    cond = [(o, chr(data[o])) for o in leak_offsets if chr(data[o]) in CONDITIONAL_HOTKEYS]
    danger = [(o, c) for o, c in hits if c in DANGEROUS_HOTKEYS]
    return {"hotkeys": hits, "conditional_hotkeys": cond, "dangerous_hotkeys": danger}
