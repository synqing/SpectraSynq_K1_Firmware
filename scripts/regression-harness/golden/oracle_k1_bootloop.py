#!/usr/bin/env python3
"""Behavioural golden-master oracle for the N2b boot-loop guard decision core.

THE PROBLEM. The boot-loop guard decides — from an RTC-resident crash streak plus
this boot's reset reason — whether to enter a non-destructive safe mode. That decision
gates whether a brick-looping K1 recovers. The ESP orchestration (RTC_NOINIT var,
esp_reset_reason, the setup/loop wiring) drags Arduino/ESP-IDF and never host-compiles,
but the DECISION itself was deliberately extracted into a PURE, FS-free, ESP-free header
(system/k1_bootloop_guard.h: k1_bootloop_eval / k1_bootloop_mark_stable) precisely so it
CAN be host-compiled and run. This oracle is that real proof: it compiles a tiny driver
that #includes the core and feeds it the boot scenarios the field will produce, then
freezes the decision + resulting crash count each one yields.

THE ARGUMENT. A refactor of the core internals that preserves the contract REPRODUCES
the golden byte-for-byte; any change to the decision table — a flipped magic/version
validity check, a moved trip threshold, a broken crash-increment gate — diverges at
least one step's recorded (decision, count). That divergence is the alarm.

THE SCENARIOS (the boot situations the field actually produces):
  * S1  uninitialised RTC (garbage magic) + crash      -> re-seed,  NORMAL (count 0)
  * S2  clean power-on with a stale high count          -> re-seed,  NORMAL (count 0)
  * S3  4 consecutive crash reboots                     -> trips SAFE_MODE exactly at 4
  * S4  mark_stable clears, then a later crash restarts -> count 0 then 1
  * S5  intentional (non-crash) reboot                  -> count unchanged, NORMAL
  * S6  already at threshold + a benign reset           -> stays SAFE_MODE
  * S7  power-on overriding a crash flag                -> re-seed, NORMAL (cold boot)
  * S8  valid magic but stale/garbage VERSION + crash   -> re-seed, NORMAL (version guard)

FAULT-EVIDENCE (the Gate-Fα teeth, proven by harness_selftest.py): the MUTATIONS list
flips one decision-bearing line of k1_bootloop_guard.h per branch — the version validity
compare, the trip-threshold compare, and the crash-increment gate — each MUST change at
least one step's recorded (decision, count). Every anchor matches EXACTLY ONCE across
the firmware tree (the pure core is the only place these lines exist).

NON-SHIPPING. Host-only (compile + run the pure core against a driver; no device, no
firmware .cpp). Mirrors the oracle PUBLIC INTERFACE (NAME / capture(firmware_root=None)
/ MUTATIONS), registered in harness_selftest.ORACLE_MODULES, gated by test_golden_master.py.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout (mirrors oracle_bridge_fs_codec.py)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]          # SpectraSynq_K1_Firmware/
FW   = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# The pure core header lives here; -I points at this dir so the driver's
# #include "k1_bootloop_guard.h" resolves. (The ESP shell inside the header is
# #if defined(ESP_PLATFORM)||defined(ARDUINO) — excluded on the host compile.)
_CORE_DIR_REL = ("system",)
_CORE_HEADER  = "k1_bootloop_guard.h"

NAME = "k1_bootloop"


def _find_compiler():
    return shutil.which("clang++") or shutil.which("g++")


# ---------------------------------------------------------------------------
# C++ driver — runs the boot scenarios through the pure core, prints JSON lines.
#
# Output protocol: one JSON object per step, in a FIXED order:
#   {"step":"<id>","decision":<0|1>,"count":<n>}
# decision is the raw K1BootDecision int (K1_BOOT_NORMAL=0, K1_BOOT_SAFE_MODE=1);
# count is the resulting fail_count. ints only — no float variance, cross-platform stable.
# ---------------------------------------------------------------------------
DRIVER = r"""
#include "k1_bootloop_guard.h"
#include <cstdio>

static void emit(const char* step, K1BootDecision d, const K1BootloopState* s) {
    std::printf("{\"step\":\"%s\",\"decision\":%d,\"count\":%u}\n",
                step, (int)d, (unsigned)s->fail_count);
}

int main() {
    const uint32_t M = K1_BOOTLOOP_MAGIC;
    const uint32_t V = K1_BOOTLOOP_VERSION;
    const uint32_t T = K1_BOOTLOOP_THRESHOLD;

    // S1: uninitialised RTC (garbage magic) + crash -> re-seed, NORMAL.
    { K1BootloopState s = {0xDEADBEEFu, 0u, 99u};
      emit("S1", k1_bootloop_eval(&s, 0, 1, T), &s); }

    // S2: clean power-on with a stale high count -> re-seed, NORMAL.
    { K1BootloopState s = {M, V, 7u};
      emit("S2", k1_bootloop_eval(&s, 1, 0, T), &s); }

    // S3: 4 consecutive crash reboots -> trips SAFE_MODE exactly at the threshold.
    { K1BootloopState s = {M, V, 0u};
      emit("S3.1", k1_bootloop_eval(&s, 0, 1, 4), &s);
      emit("S3.2", k1_bootloop_eval(&s, 0, 1, 4), &s);
      emit("S3.3", k1_bootloop_eval(&s, 0, 1, 4), &s);
      emit("S3.4", k1_bootloop_eval(&s, 0, 1, 4), &s);
      emit("S3.5", k1_bootloop_eval(&s, 0, 1, 4), &s); }

    // S4: mark_stable clears the streak; a later crash restarts from 1.
    { K1BootloopState s = {M, V, 4u};
      k1_bootloop_mark_stable(&s);
      emit("S4.stable", K1_BOOT_NORMAL, &s);
      emit("S4.crash", k1_bootloop_eval(&s, 0, 1, 4), &s); }

    // S5: a non-crash reset (intentional reboot) does not increment.
    { K1BootloopState s = {M, V, 2u};
      emit("S5", k1_bootloop_eval(&s, 0, 0, 4), &s); }

    // S6: already at threshold + a benign reset -> stays SAFE_MODE.
    { K1BootloopState s = {M, V, 4u};
      emit("S6", k1_bootloop_eval(&s, 0, 0, 4), &s); }

    // S7: power-on precedence over a crash flag (a cold boot is never a loop).
    { K1BootloopState s = {M, V, 9u};
      emit("S7", k1_bootloop_eval(&s, 1, 1, 4), &s); }

    // S8: valid magic but stale/garbage VERSION + crash -> re-seed, NORMAL.
    { K1BootloopState s = {M, 0xBADu, 99u};
      emit("S8", k1_bootloop_eval(&s, 0, 1, T), &s); }

    return 0;
}
"""

# Expected golden (decision, count) per step, for the __main__ self-check.
EXPECTED = {
    "S1": (0, 0), "S2": (0, 0),
    "S3.1": (0, 1), "S3.2": (0, 2), "S3.3": (0, 3), "S3.4": (1, 4), "S3.5": (1, 5),
    "S4.stable": (0, 0), "S4.crash": (0, 1),
    "S5": (0, 2), "S6": (1, 4), "S7": (0, 0), "S8": (0, 0),
}


# ---------------------------------------------------------------------------
# Compile + run
# ---------------------------------------------------------------------------
def _compile(workdir: Path, firmware_root=None) -> Path:
    fw = Path(firmware_root) if firmware_root else FW
    core_dir = fw.joinpath(*_CORE_DIR_REL)
    main_cpp = workdir / "driver.cpp"
    main_cpp.write_text(DRIVER, encoding="utf-8")
    binary = workdir / "oracle_k1_bootloop_bin"

    cxx = _find_compiler()
    if not cxx:
        raise RuntimeError("no C++ compiler (clang++/g++) found on PATH")

    cmd = [
        cxx, "-std=c++17",
        "-O0",                  # strict determinism; the core is integer-only anyway
        "-I", str(core_dir),    # resolves #include "k1_bootloop_guard.h"
        str(main_cpp),
        "-o", str(binary),
    ]
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"oracle_k1_bootloop compile failed:\n{r.stderr}")
    return binary


def _run(binary: Path) -> str:
    r = subprocess.run([str(binary)], text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"oracle_k1_bootloop run failed:\n{r.stderr}")
    return r.stdout


def capture(firmware_root=None) -> str:
    """Compile + run the boot-scenario driver; return deterministic JSON-lines golden."""
    with tempfile.TemporaryDirectory(prefix="oracle_k1_bootloop_") as td:
        binary = _compile(Path(td), firmware_root=firmware_root)
        return _run(binary)


# ---------------------------------------------------------------------------
# Mutations — the Gate-Fα teeth. One per decision branch, each anchoring a line
# IN k1_bootloop_guard.h and each flipping at least one step's (decision, count).
# Every anchor matches EXACTLY ONCE across the firmware tree (the pure core is the
# only place these lines exist).
# ---------------------------------------------------------------------------
MUTATIONS = [
    # 1. (version validity) INVERT THE VERSION COMPARE: re-seed when the version MATCHES
    #    instead of when it differs. A valid record (correct version) is then wiped on
    #    every eval, so the streak never accrues: S3.4 SAFE_MODE(1) -> NORMAL(0). And a
    #    stale-version record (S8) no longer re-seeds, so it counts up and trips:
    #    S8 NORMAL(0) -> SAFE_MODE(1).
    (
        r"s->version != K1_BOOTLOOP_VERSION",
        r"s->version == K1_BOOTLOOP_VERSION",
        "version_validity_inverted (S3.4 trip lost / S8 false-trip divergence)",
    ),
    # 2. (trip threshold) WEAKEN THE TRIP COMPARE from >= to >: safe mode no longer fires
    #    AT the threshold, only past it. S3.4 (count==4, threshold==4): SAFE_MODE(1) ->
    #    NORMAL(0). The whole point — "trips exactly at threshold" — is gone.
    (
        r"s->fail_count >= threshold",
        r"s->fail_count > threshold",
        "trip_threshold_off_by_one (S3.4 no longer trips at threshold)",
    ),
    # 3. (crash gate) INVERT THE CRASH-INCREMENT GATE: count crashes only when this reset
    #    was NOT a crash. The crash streak then never grows under real crashes: S3.4
    #    SAFE_MODE(1) -> NORMAL(0), and the per-step counts diverge across S3.
    (
        r"if \(is_crash\) \{",
        r"if (!is_crash) {",
        "crash_increment_gate_inverted (S3 streak never accrues under real crashes)",
    ),
]


# ---------------------------------------------------------------------------
# Standalone regen / self-check (mirrors oracle_bridge_fs_codec.py __main__).
#   python3 oracle_k1_bootloop.py > tests/golden/k1_bootloop.golden.jsonl
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Behavioural oracle for the N2b boot-loop guard decision core."
    )
    parser.add_argument("--verify-mutations", action="store_true")
    args = parser.parse_args()

    baseline = capture()
    print(baseline, end="")

    baseline2 = capture()
    if baseline != baseline2:
        print("DETERMINISM FAILURE: two runs produced different output.", file=sys.stderr)
        sys.exit(1)

    recs = {json.loads(l)["step"]: (json.loads(l)["decision"], json.loads(l)["count"])
            for l in baseline.strip().splitlines()}
    if recs != EXPECTED:
        print(f"DECISION MISMATCH: got {recs}, expected {EXPECTED}", file=sys.stderr)
        sys.exit(1)

    print(f"\n# golden_record_count={len(baseline.strip().splitlines())}", file=sys.stderr)
    print("# determinism=OK (two runs byte-identical)", file=sys.stderr)
    print("# decisions match expected", file=sys.stderr)

    if args.verify_mutations:
        print("\n# --- Mutation verification ---", file=sys.stderr)
        all_caught = True
        for pattern, replacement, desc in MUTATIONS:
            with tempfile.TemporaryDirectory() as td:
                dst = Path(td) / "SPECTRASYNQ_K1_FIRMWARE"
                shutil.copytree(FW, dst)
                target = None
                for f in dst.rglob("*"):
                    if f.suffix in (".cpp", ".h") and f.is_file():
                        txt = f.read_text(encoding="utf-8", errors="ignore")
                        if re.search(pattern, txt):
                            f.write_text(re.sub(pattern, replacement, txt, count=1), encoding="utf-8")
                            target = f
                            break
                try:
                    caught = target is not None and capture(firmware_root=dst) != baseline
                except RuntimeError as exc:
                    caught = target is not None
                    print(f"#    (compile diverged: {str(exc)[:80]})", file=sys.stderr)
                all_caught = all_caught and caught
                print(f"#  [{'CAUGHT' if caught else 'MISSED'}] {desc}", file=sys.stderr)
        print("# all mutations caught." if all_caught
              else "# WARNING: a mutation was not caught.", file=sys.stderr)
        sys.exit(0 if all_caught else 1)
