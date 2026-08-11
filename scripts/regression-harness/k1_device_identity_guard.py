#!/usr/bin/env python3
"""Assert WHICH firmware is answering before trusting a single sample from it.

Origin: 2026-08-11. A concurrent session reflashed Bench Unit 2 mid-measurement.
Forty minutes of device evidence — a noise calibration, quiet-room and music
distributions, and a derived threshold — were collected against a foreign build
that differed in input gain (4.0f vs 8.0f), PDM pin map (13/12 vs 39/38) and the
presence of the gate under test. Every number looked plausible. The only tell was
a pyserial exception reading "device disconnected or multiple access on port",
and only the first half of that sentence was read.

A capture that does not pin the build identity is not evidence. It is a plausible
number of unknown provenance, which is worse than no number at all.

Usage as a guard (exits non-zero on mismatch):
    python3 k1_device_identity_guard.py --port /dev/cu.usbmodem1101 \
        --expect-git 1249286 --expect-env k1_unit2_im69d_right

Usage as a library:
    from k1_device_identity_guard import read_identity, assert_identity
    ident = assert_identity(port, expect_git="1249286")
"""
from __future__ import annotations

import argparse
import re
import sys
import time

# BUILD: version=40103 git=622997b epoch=1786444207 env=k1_custom_silicon_closure
_BUILD_RE = re.compile(
    r"BUILD:\s*version=(?P<version>\S+)\s+git=(?P<git>\S+)\s+"
    r"epoch=(?P<epoch>\S+)\s+env=(?P<env>\S+)"
)


class IdentityMismatch(RuntimeError):
    """The device answering is not the build we intended to measure."""


def parse_build_line(text: str) -> dict[str, str] | None:
    """Extract the build identity from a :build reply. Pure function, no I/O."""
    m = _BUILD_RE.search(text)
    return dict(m.groupdict()) if m else None


def read_identity(port: str, baud: int = 115200, timeout_s: float = 4.0) -> dict[str, str]:
    """Ask the device who it is. Read-only: sends only ':build'.

    DTR must be asserted — the CDC console gates on it, and a port opened without
    it returns zero bytes while looking perfectly healthy.
    """
    import serial  # imported here so the parser stays testable without pyserial

    s = serial.Serial()
    s.port = port
    s.baudrate = baud
    s.timeout = 0.3
    s.dtr = True   # REQUIRED. Never set False — that is a hardware reset on USB-Serial-JTAG.
    s.rts = False
    s.open()
    try:
        time.sleep(0.6)
        s.reset_input_buffer()
        s.write(b":build\n")
        s.flush()
        buf = bytearray()
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                chunk = s.read(4096)
            except Exception as exc:  # noqa: BLE001 - surfaced verbatim below
                raise IdentityMismatch(
                    f"serial error while reading identity from {port}: {exc}. "
                    "'multiple access on port' means ANOTHER PROCESS OWNS THIS DEVICE — "
                    "stop and resolve ownership before measuring."
                ) from exc
            if chunk:
                buf.extend(chunk)
                ident = parse_build_line(buf.decode("utf-8", errors="replace"))
                if ident:
                    return ident
    finally:
        s.close()
    raise IdentityMismatch(
        f"{port} never answered ':build' within {timeout_s}s. Do not measure it."
    )


def assert_identity(
    port: str,
    expect_git: str | None = None,
    expect_env: str | None = None,
    expect_epoch: str | None = None,
) -> dict[str, str]:
    """Read identity and refuse to proceed unless it matches expectations."""
    ident = read_identity(port)
    problems = []
    if expect_git and not ident["git"].startswith(expect_git[: len(ident["git"])][:40]):
        if not (ident["git"].startswith(expect_git) or expect_git.startswith(ident["git"])):
            problems.append(f"git={ident['git']} expected {expect_git}")
    if expect_env and ident["env"] != expect_env:
        problems.append(f"env={ident['env']} expected {expect_env}")
    if expect_epoch and ident["epoch"] != expect_epoch:
        problems.append(f"epoch={ident['epoch']} expected {expect_epoch}")
    if problems:
        raise IdentityMismatch(
            "DEVICE IS NOT THE BUILD UNDER TEST — discard any samples taken from it.\n  "
            + "\n  ".join(problems)
            + f"\n  (device reports: {ident})"
        )
    return ident


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", default="/dev/cu.usbmodem1101")
    ap.add_argument("--expect-git")
    ap.add_argument("--expect-env")
    ap.add_argument("--expect-epoch")
    args = ap.parse_args()
    try:
        ident = assert_identity(args.port, args.expect_git, args.expect_env, args.expect_epoch)
    except IdentityMismatch as exc:
        print(f"IDENTITY FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"IDENTITY OK: git={ident['git']} env={ident['env']} epoch={ident['epoch']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
