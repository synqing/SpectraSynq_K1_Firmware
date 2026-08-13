#!/usr/bin/env python3
"""Colour-fix-lane capture driver (2026-08-13).

One measurement leg on the bench (k1_bench_im69d_hueaud):
  1. apply the measurement config (era knobs + measured SSL) via typed commands,
     reading back each echo — a command whose echo is missing/Bad is FATAL
     (HF-48: prove the command exists on the flashed build);
  2. set the target mode and verify it via the HUEAUD line's mode= field;
  3. prove the ACOUSTIC PATH (music actually reaching the mic): sample the 1 Hz
     AP line and require silence=0 on >=80% of frames — otherwise abort loudly
     (a silence-latched capture measures the gate, not the colour path);
  4. :rtrace_arm, wait, :rtrace_dump — save the full serial log.

Usage:
  colour_baseline_capture.py --port /dev/cu.usbmodem12201 --mode 32 \
      --seconds 60 --out _scratch/colour_fix_20260813/mode32_main.log
      [--ssl 187] [--skip-config]

Then: hue_coverage.py rtrace <out> --palette 40 \
      --palette-ref scripts/regression-harness/results/palette_reference.json
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import serial  # pyserial

AP_RE = re.compile(r"\[AP\] .*silence=(?P<sil>[01]) ")
HUEAUD_MODE_RE = re.compile(
    r"HUEAUD,ver=1,ch=p,lit=\d+,mode=(?P<mode>-?\d+)"
    r"(?:,pal=(?P<pal>\d+),pmode=(?P<pmode>[01]),acs=(?P<acs>[01]))?"
    r"(?:,(?!h=)[a-z0-9_]+=[^,]*)*,h=")


class Leg:
    def __init__(self, port: str, log_path: Path):
        self.log = open(log_path, "w", buffering=1, errors="replace")
        s = serial.Serial()
        s.port = port
        s.baudrate = 115200
        s.timeout = 0.3
        s.dtr = True   # set BEFORE open is a no-op kwarg trap; attribute is fine
        s.rts = False
        s.open()
        time.sleep(0.6)
        s.reset_input_buffer()
        self.s = s

    def pump(self, seconds: float) -> list[str]:
        """Read+log everything for `seconds`; return the lines."""
        lines: list[str] = []
        buf = bytearray()
        end = time.time() + seconds
        while time.time() < end:
            chunk = self.s.read(4096)
            if chunk:
                buf.extend(chunk)
                while b"\n" in buf:
                    raw, _, rest = bytes(buf).partition(b"\n")
                    buf = bytearray(rest)
                    line = raw.decode("utf-8", "replace").rstrip("\r")
                    self.log.write(line + "\n")
                    lines.append(line)
        return lines

    def cmd(self, command: str, wait: float = 1.2) -> list[str]:
        self.log.write(f">>> :{command}\n")
        self.s.write(f":{command}\n".encode())
        self.s.flush()
        return self.pump(wait)

    def cmd_expect(self, command: str, needle: str, wait: float = 1.5) -> None:
        lines = self.cmd(command, wait)
        joined = "\n".join(lines)
        if "Bad command" in joined:
            raise SystemExit(f"FATAL: ':{command}' answered Bad command — "
                             f"command missing on the flashed build (HF-48)")
        if needle not in joined:
            raise SystemExit(f"FATAL: ':{command}' echo missing '{needle}'. Got:\n{joined[-500:]}")
        print(f"  ok :{command}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--mode", type=int, required=True)
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--every", type=int, default=4)
    ap.add_argument("--ssl", type=int, default=187)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-config", action="store_true",
                    help="knobs already applied this session; only mode+capture")
    ap.add_argument("--edge-off", action="store_true",
                    help="disable the edge mixer for this leg (layer-5 side door "
                         "bleeds secondary HSV over the primary; runtime-only)")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    leg = Leg(args.port, out)

    print("== settle + boot noise")
    leg.pump(2.0)

    if not args.skip_config:
        print("== measurement config (era knobs + measured SSL)")
        leg.cmd_expect("chromagram_range=60", "CHROMAGRAM_RANGE: 60")
        leg.cmd_expect("sensitivity=2.40", "SENSITIVITY")
        leg.cmd_expect("chroma=0.05", "CHROMA")
        leg.cmd_expect("mood=0.05", "MOOD")
        leg.cmd_expect(f"sweet_spot_min={args.ssl}", "SWEET_SPOT")

    if args.edge_off:
        print("== edge mixer OFF for this leg")
        leg.cmd("edge_enabled=off", 1.0)

    print(f"== mode {args.mode}")
    leg.cmd(f"set_mode={args.mode}", 1.5)
    leg.cmd("get_mode_name", 1.0)
    # Verify via the HUEAUD line (1 Hz) — the applied mode, not the request.
    lines = leg.pump(3.0)
    states = [m for l in lines if (m := HUEAUD_MODE_RE.search(l))]
    if not states:
        raise SystemExit("FATAL: no HUEAUD lines — wrong build on device?")
    last = states[-1]
    if int(last.group("mode")) != args.mode:
        raise SystemExit(f"FATAL: device reports mode {last.group('mode')}, wanted "
                         f"{args.mode} (dense-index trap — probe the right index)")
    # Palette-authority identity (HF-41): the measurement is VOID unless the
    # palette state is proven. Builds with the pal= fields must show 40/1.
    if last.group("pal") is not None:
        pal, pmode = int(last.group("pal")), int(last.group("pmode"))
        if pal != 40 or pmode != 1:
            raise SystemExit(f"FATAL: palette state pal={pal} pmode={pmode} — expected "
                             f"Naberius 40 with palette mode ON (show-state override?)")
        print(f"  ok mode={last.group('mode')} pal={pal} pmode={pmode} acs={last.group('acs')}")
    else:
        print(f"  ok mode={last.group('mode')} (build has no pal= fields — palette UNPROVEN)")

    print("== acoustic path proof (10 s)")
    lines = leg.pump(10.0)
    sils = [int(m.group("sil")) for l in lines if (m := AP_RE.search(l))]
    if len(sils) < 5:
        raise SystemExit(f"FATAL: only {len(sils)} AP lines in 10 s — AP stream off?")
    awake = sils.count(0) / len(sils)
    print(f"  silence=0 on {awake:.0%} of {len(sils)} frames")
    if awake < 0.8:
        raise SystemExit("FATAL: device is silence-latched — music is NOT reaching "
                         "the mic at capture level. Fix audio before capturing.")

    print(f"== capture {args.seconds}s (every_n={args.every})")
    leg.cmd_expect(f"rtrace_arm={args.seconds},{args.every}", "[RTRACE] ARMED")
    leg.pump(args.seconds + 3)
    leg.cmd_expect("rtrace_status=1", "[RTRACE]")
    print("== dump (AP stream off for a clean dump; re-enabled after)")
    leg.cmd("ap_stream=0", 1.0)
    lines = leg.cmd("rtrace_dump=1", 30.0)
    n = sum(1 for l in lines if l.startswith("F,"))
    ended = any("[RTRACE-END]" in l for l in lines)
    if not ended or n == 0:
        raise SystemExit(f"FATAL: dump incomplete (frames={n}, end={ended})")
    print(f"  ok {n} frames dumped -> {out}")
    # Never leave the AP stream off (the AP-stream-off blind spot).
    leg.cmd("ap_stream=1", 1.0)
    leg.s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
