#!/usr/bin/env python3
"""audit_prsm_bytes — bench-eligibility gate: would any byte of (preamble + stream) reach the
K1's hotkey dispatcher or ':' command mode?

Feeds the bytes through the REAL firmware scanner/mapper (oracle/byte_audit.cpp compiled against
oracle/fw_407fdf6f, byte-identical to ed0aa984) inside a replica of check_serial()'s demux, then
classifies every byte the scanner does not consume.

Usage:
  audit_prsm_bytes.py STREAM.prsm [--no-preamble] [--fill N --stale HEX] [--cmd L] [--json OUT]

Exit codes: 0 BENCH-ELIGIBLE, 1 NOT ELIGIBLE, 3 usage / build error.
--allow-rejected-frames: for the deliberate rejected-input case (bad hz / bad version) only; frames
may be rejected, but every byte must still be consumed by the scanner and nothing may reach
hotkeys or command mode.

Eligible means ALL of:
  - zero bytes classified as actionable hotkeys (immediate set incl. build-conditional z/Z/v)
  - zero ':' command-mode entries, zero bytes swallowed by command mode, zero commands executed
    (except a pending line that existed BEFORE the preamble; see --cmd, reported separately)
  - every stream byte consumed by the PRSM scanner, no FRAME_BAD, every stream frame accepted
  - scanner fill 0 and command mode off at the end
Bytes of the preamble that reach the dispatcher are allowed only if inert (CR/LF, or a byte for
which serial_hotkey_is_immediate() is false).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "oracle"))
import prim8_stream as ps  # noqa: E402
import py_device_model as dm  # noqa: E402

ORACLE = HERE / "oracle"
FW = ORACLE / "fw_407fdf6f"
SRC = [ORACLE / "byte_audit.cpp", FW / "k1_prsm.cpp", FW / "k1_authored_source.cpp"]
PREAMBLE = ps.RESYNC_PREAMBLE
ACTIONABLE = dm.IMMEDIATE_HOTKEYS | dm.CONDITIONAL_HOTKEYS
_EXE = None


def build() -> Path:
    global _EXE
    if _EXE and _EXE.exists():
        return _EXE
    h = hashlib.sha256(b"".join(p.read_bytes() for p in SRC + [FW / "k1_prsm.h",
                                                               FW / "k1_authored_source.h"]))
    exe = Path(tempfile.gettempdir()) / f"laneb_byte_audit_{h.hexdigest()[:16]}"
    if not exe.exists():
        cc = next((c for c in ("c++", "clang++", "g++") if shutil.which(c)), None)
        if cc is None:
            raise RuntimeError("no host C++ compiler")
        r = subprocess.run([cc, "-std=c++17", "-O2", "-Wall", "-Wextra", f"-I{FW}",
                            *map(str, SRC), "-o", str(exe)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
    _EXE = exe
    return exe


def run_engine(data: bytes, fill=0, stale=b"", cmd=None) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as t:
        t.write(data)
        path = t.name
    args = [str(build()), path, "--fill", str(fill), "--stale", stale.hex()]
    if cmd is not None:
        args += ["--cmd", str(cmd)]
    try:
        r = subprocess.run(args, capture_output=True, text=True)
    finally:
        Path(path).unlink(missing_ok=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def audit(stream: bytes, *, preamble: bool = True, fill=0, stale=b"", cmd=None,
          allow_rejected_frames: bool = False, guard: int = 0) -> dict:
    pre = PREAMBLE if preamble else b""
    guard_offsets = set()
    if guard:
        wire = bytearray()
        full = len(stream) - len(stream) % ps.FRAME_LEN
        for k in range(0, full, ps.FRAME_LEN):
            guard_offsets.update(range(len(pre) + len(wire), len(pre) + len(wire) + guard))
            wire += b"\x00" * guard + stream[k:k + ps.FRAME_LEN]
        wire += stream[full:]
        data = pre + bytes(wire)
    else:
        data = pre + stream
    eng = run_engine(data, fill, stale, cmd)
    p = len(pre)
    actionable, inert, stream_leak = [], [], []
    for off, b in eng["none"]:
        ch = chr(b)
        if b in (0x0D, 0x0A) or ch not in ACTIONABLE:
            inert.append(off)
        else:
            actionable.append((off, ch))
        if off >= p and not (off in guard_offsets and b == 0):
            stream_leak.append(off)
    # Initial command-mode episode (device was already in ':' mode before our first byte): the
    # bytes until the first CR/LF (or 127-byte overflow) belong to that episode. If they are all
    # preamble bytes, they are the preamble doing its job (exiting command mode). A line pending
    # BEFORE we started is executed by that terminator; current firmware has no abort byte, so it
    # is reported separately (pre_existing_line_executed), not counted as our fault.
    episode = set()
    if cmd is not None:
        n = cmd
        for i, b in enumerate(data):
            episode.add(i)
            if b in (0x0D, 0x0A):
                break
            n += 1
            if n >= 127:
                break
    episode_in_preamble = episode and max(episode) < p
    executed = eng["commands_executed"]
    pre_existing = [e for e in executed if episode_in_preamble and e["end_off"] in episode]
    ours = [e for e in executed if e not in pre_existing]
    n_frames, rem = divmod(len(stream), ps.FRAME_LEN)
    stream_frames = [f for f in eng["frames"] if f["off"] >= p]
    accepted = [f for f in stream_frames if f["mapped"]]
    stale_frames = [f for f in eng["frames"] if f["off"] < p]
    swallowed = [o for o in eng["command_mode_bytes"]
                 if not (episode_in_preamble and o in episode)]
    reasons = []
    if actionable:
        reasons.append(f"{len(actionable)} byte(s) reach immediate hotkeys, first at {actionable[0][0]} "
                       f"({actionable[0][1]!r})")
    if eng["command_mode_enter"]:
        reasons.append(f"{len(eng['command_mode_enter'])} ':' command-mode entr(y/ies), first at "
                       f"{eng['command_mode_enter'][0]}")
    if swallowed:
        reasons.append(f"{len(swallowed)} byte(s) swallowed by command mode, first at {swallowed[0]}")
    if ours:
        reasons.append(f"{len(ours)} command line(s) executed, first ending at {ours[0]['end_off']}")
    if stream_leak:
        reasons.append(f"{len(stream_leak)} stream byte(s) not consumed by the PRSM scanner, first at "
                       f"{stream_leak[0]}")
    bad_in_stream = [o for o in eng["frame_bad"] if o >= p]
    if bad_in_stream and not allow_rejected_frames:
        reasons.append(f"{len(bad_in_stream)} FRAME_BAD in stream, first ending at {bad_in_stream[0]}")
    if rem:
        reasons.append(f"stream length not a multiple of 34 ({rem} trailing bytes)")
    if len(accepted) != n_frames and not allow_rejected_frames:
        reasons.append(f"device accepts {len(accepted)} of {n_frames} stream frames")
    if eng["final"]["fill"] or eng["final"]["command_mode"]:
        reasons.append(f"end state fill={eng['final']['fill']} command_mode={eng['final']['command_mode']}")
    return {
        "eligible": not reasons, "reasons": reasons,
        "preamble_len": p, "stream_frames": n_frames, "frames_accepted": len(accepted),
        "actionable_hotkeys": len(actionable), "actionable_first": actionable[:5],
        "inert_dispatch_bytes": len(inert), "command_mode_entries": len(eng["command_mode_enter"]),
        "command_mode_bytes_swallowed": len(swallowed),
        "commands_executed_ours": ours, "pre_existing_line_executed": bool(pre_existing),
        "stale_frames_completed": [{"off": f["off"], "mapped": f["mapped"], "hz": f["hz"],
                                    "p": f["p"]} for f in stale_frames],
        "frame_bad_offsets": eng["frame_bad"], "final": eng["final"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PRSM bench-eligibility byte audit")
    ap.add_argument("stream")
    ap.add_argument("--no-preamble", action="store_true")
    ap.add_argument("--fill", type=int, default=0)
    ap.add_argument("--stale", default="")
    ap.add_argument("--cmd", type=int)
    ap.add_argument("--json")
    ap.add_argument("--guard", type=int, default=0,
                    help="per-frame NUL guard the player writes before each frame (30 recommended)")
    ap.add_argument("--allow-rejected-frames", action="store_true",
                    help="rejected-input test case: frames may be rejected (bad hz/version) but no "
                         "byte may reach hotkeys or command mode")
    a = ap.parse_args(argv)
    try:
        rep = audit(Path(a.stream).read_bytes(), preamble=not a.no_preamble, fill=a.fill,
                    stale=bytes.fromhex(a.stale), cmd=a.cmd,
                    allow_rejected_frames=a.allow_rejected_frames, guard=a.guard)
    except (OSError, RuntimeError, ValueError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 3
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    head = "BENCH-ELIGIBLE" if rep["eligible"] else "NOT ELIGIBLE"
    print(f"{head} {a.stream} frames={rep['frames_accepted']}/{rep['stream_frames']} "
          f"hotkeys={rep['actionable_hotkeys']} cmd_entries={rep['command_mode_entries']} "
          f"cmd_swallowed={rep['command_mode_bytes_swallowed']} "
          f"cmds_executed={len(rep['commands_executed_ours'])} "
          f"preamble={'off' if a.no_preamble else len(ps.RESYNC_PREAMBLE)}B guard={a.guard}B")
    for r in rep["reasons"]:
        print("  - " + r)
    return 0 if rep["eligible"] else 1


if __name__ == "__main__":
    sys.exit(main())
