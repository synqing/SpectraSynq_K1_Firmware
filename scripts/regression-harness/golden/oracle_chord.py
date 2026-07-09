#!/usr/bin/env python3
"""Golden-master oracle for the K1_CHORD_V2 chord detector.

Compiles the REAL firmware k1_chord_detect.cpp on the host (clang++) against a
minimal Arduino stub, drives it with a fixed deterministic chroma trace, and
captures a JSON-lines golden record that any refactor must reproduce byte-for-byte.

Design mirrors oracle_onset_beat.py:
  NAME           — module identifier
  MODULE_CPPS    — firmware translation units to compile
  DEFINES        — production-matching -D flags (grep platformio.ini [env:k1_hardware])
  DRIVER         — C++ stdin driver; emits one JSON record per step
  capture()      — compile + run, return JSON-lines string (deterministic)
  MUTATIONS      — 4 real constants, each in the SUPPRESSING direction,
                   each PROVEN to diverge from the golden record

Usage:
  python3 scripts/regression-harness/golden/oracle_chord.py          # print golden
  python3 -c "from oracle_chord import capture; print(len(capture().splitlines()))"
  pytest tests/golden/test_golden_master.py -k chord                  # regression gate

NON-SHIPPING. Host-only. Run from the repo root or from within this directory.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]          # SensoryBridge-main 9/
FW   = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# ---------------------------------------------------------------------------
# Module identity (mirrors oracle_onset_beat.py contract)
# ---------------------------------------------------------------------------
NAME = "chord"

MODULE_CPPS = [
    "audio/k1_chord_detect.cpp",
]

# Production-matching defines (from platformio.ini [env:k1_hardware]).
# K1_CHORD_V2 is mandatory (the TU is a no-op without it).
# K1_ONSET_V2 is included so K1AudioSnapshot carries the spectrum[] field
# that sits between the base struct and the chord fields — this keeps the
# struct layout matching production exactly (additive fields are ordered:
# onset_spectrum → chroma_pc → chord).
DEFINES = [
    "K1_CHORD_V2",
    "K1_ONSET_V2",
]

# ---------------------------------------------------------------------------
# Minimal Arduino stub
# k1_chord_detect.cpp only touches portMUX (none), stdint, and math.h.
# It does NOT pull globals.h, fixed-point, or FastLED — by design.
# The stub matches the one used by chord_saliency_replay.py exactly.
# ---------------------------------------------------------------------------
ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
#include <math.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""

# ---------------------------------------------------------------------------
# C++ driver
#
# Protocol: reads lines on stdin of the form:
#   "C <c0> <c1> ... <c11>"  — 12 float chroma_pc values (A-origin)
# Outputs one JSON object per line:
#   {"step":<int>, "root":<int>, "type":<int>,
#    "confidence":"<%.5f>", "rootStrength":"<%.5f>",
#    "thirdStrength":"<%.5f>", "fifthStrength":"<%.5f>"}
#
# All floats emitted at %.5f for stable cross-platform comparison.
# ints are exact (no fp variance).
# ---------------------------------------------------------------------------
DRIVER = r"""
#include "k1_audio_snapshot.h"
#include <cstdio>
#include <cstring>

// Forward declaration — defined in k1_chord_detect.cpp (compiled alongside).
void k1_detect_chord(const float* chroma, K1ChordState& cs);

int main() {
    char tag;
    int step = 0;
    while (std::scanf(" %c", &tag) == 1) {
        if (tag != 'C') {
            // skip rest of line
            int ch;
            while ((ch = std::getchar()) != '\n' && ch != EOF) {}
            continue;
        }
        float c[12];
        for (int i = 0; i < 12; ++i) {
            if (std::scanf("%f", &c[i]) != 1) c[i] = 0.0f;
        }
        K1ChordState cs{};
        k1_detect_chord(c, cs);
        // Emit one JSON record per step.
        // type cast: K1ChordType is uint8_t enum — cast to int for printf.
        std::printf(
            "{\"step\":%d,\"root\":%d,\"type\":%d,"
            "\"confidence\":\"%.5f\",\"rootStrength\":\"%.5f\","
            "\"thirdStrength\":\"%.5f\",\"fifthStrength\":\"%.5f\"}\n",
            step,
            (int)cs.rootNote,
            (int)static_cast<uint8_t>(cs.type),
            cs.confidence,
            cs.rootStrength,
            cs.thirdStrength,
            cs.fifthStrength
        );
        ++step;
    }
    return 0;
}
"""

# ---------------------------------------------------------------------------
# Input trace — fixed, deterministic chroma sequences
#
# Strategy (hard-won lesson: avoid saturation):
#   * Use borderline energies so the confidence threshold at 0.3 is a
#     live decision boundary — mutations that shift it will flip NONE/non-NONE.
#   * Vary root, chord type, and energy balance so root-selection and
#     interval-energy comparisons are all exercised.
#   * Include near-ties so that changes to interval arithmetic flip the type.
#   * Include one clean strong triad to anchor the confidence ratio mutation.
#
# A-origin convention: bin 0 = A, 1 = A#/Bb, 2 = B, 3 = C, ...
#   A major  = bins 0(A) 4(C#) 7(E)    intervals +4 +7
#   A minor  = bins 0(A) 3(C)  7(E)    intervals +3 +7
#   A dim    = bins 0(A) 3(C)  6(D#)   intervals +3 +6
#   A aug    = bins 0(A) 4(C#) 8(F)    intervals +4 +8
#   C major  = bins 3(C) 7(E)  10(G)   intervals +4 +7 (C-origin +0+4+7)
# ---------------------------------------------------------------------------

def _chroma(pairs):
    """Build a 12-bin float chroma from [(bin, value), ...]; rest = 0."""
    v = [0.0] * 12
    for b, x in pairs:
        v[b] = float(x)
    return v

# Each entry: (label, chroma_list)
TRACE = [
    # 1. Clean A-major — strong, confidence well above 0.3
    ("A_major_strong",     _chroma([(0, 0.90), (4, 0.70), (7, 0.60)])),

    # 2. A-minor — strong, type contrast with entry 1
    ("A_minor_strong",     _chroma([(0, 0.90), (3, 0.70), (7, 0.60)])),

    # 3. A-major borderline — triad/total ratio near the 0.3 confidence gate
    #    total = 0.45+0.25+0.18+0.30+0.20 = 1.38; triad = 0.45+0.25+0.18 = 0.88
    #    ratio = 0.88/1.38/0.4 ≈ 1.59 → confidence = 1.0 (clamped)
    #    But with noise bins: total grows, ratio drops toward gate.
    #    Use weaker triad + noise: triad=0.22+0.13+0.11=0.46,
    #    noise = 0.20+0.18+0.17+0.16+0.15+0.14+0.12+0.11+0.10
    #    total ≈ 0.46+1.33 = 1.79; ratio = 0.46/1.79/0.4 ≈ 0.643 → conf ≈ 0.64
    #    Still above 0.3, but mutations that lower 0.4 denominator → higher conf,
    #    mutations that raise it → lower conf, potentially crossing 0.3 gate.
    ("A_major_mid",        _chroma([(0, 0.22), (4, 0.13), (7, 0.11),
                                    (1, 0.20), (2, 0.18), (3, 0.17),
                                    (5, 0.16), (6, 0.15), (8, 0.14),
                                    (9, 0.12), (10, 0.11), (11, 0.10)])),

    # 4. Near-threshold case — triad just above 0.3 confidence gate
    #    triad = 0.15+0.09+0.07=0.31; total=0.31+0.80 noise = 1.11
    #    ratio = 0.31/1.11/0.4 ≈ 0.698 → conf ≈ 0.698 (above 0.3)
    #    But shrinking triad or raising denominator puts it below.
    ("A_major_near_gate",  _chroma([(0, 0.15), (4, 0.09), (7, 0.07),
                                    (1, 0.12), (2, 0.11), (3, 0.10),
                                    (5, 0.09), (6, 0.08), (8, 0.07),
                                    (9, 0.07), (10, 0.06), (11, 0.06)])),

    # 5. A-dim (tritone fifth at +6) — exercises dimFifth > perfectFifth branch
    ("A_dim_strong",       _chroma([(0, 0.80), (3, 0.65), (6, 0.55)])),

    # 6. A-aug (augmented fifth at +8) — exercises augFifth > dimFifth branch
    ("A_aug_strong",       _chroma([(0, 0.80), (4, 0.65), (8, 0.55)])),

    # 7. Near-tie major/minor third — minorThird vs majorThird compete
    #    bin 3 (minor) = 0.401, bin 4 (major) = 0.400 → MINOR wins narrowly.
    #    A mutation that changes how interval energies are computed flips this.
    ("A_near_tie_minor",   _chroma([(0, 0.85), (3, 0.401), (4, 0.400), (7, 0.55)])),

    # 8. Near-tie major/minor third flipped — bin 4 > bin 3 → MAJOR
    ("A_near_tie_major",   _chroma([(0, 0.85), (3, 0.400), (4, 0.401), (7, 0.55)])),

    # 9. C-major (A-origin root = bin 3)
    ("C_major_strong",     _chroma([(3, 0.88), (7, 0.70), (10, 0.58)])),

    # 10. E-minor (A-origin: E=bin 7, G=bin 10, B=bin 2)
    ("E_minor_strong",     _chroma([(7, 0.85), (10, 0.68), (2, 0.55)])),

    # 11. Sub-0.6 confidence gate case: conf ≈ 0.438, above 0.3 but below 0.6.
    #     A-major: root=0(A)=0.30 (dominant), majorThird=bin4=0.04, fifth=bin7=0.03.
    #     Competing interval bins (bin3,bin6,bin8) held at 0.02 so type=MAJOR holds.
    #     Six background bins at 0.28 (below root); these inflate total energy.
    #     triad=0.37, total=2.11, conf=(0.37/2.11)/0.4≈0.438.
    #     Raising the confidence threshold from 0.3 → 0.6 flips type to NONE.
    ("A_major_sub_0p6_conf", _chroma([(0, 0.30), (4, 0.04), (7, 0.03),
                                      (3, 0.02), (6, 0.02), (8, 0.02),
                                      (1, 0.28), (2, 0.28), (5, 0.28),
                                      (9, 0.28), (10, 0.28), (11, 0.28)])),

    # 12. Below-threshold — all energy diffuse, confidence collapses to NONE
    ("diffuse_noise",      _chroma([(i, 0.083) for i in range(12)])),

    # 12. Single-bin dominant — extreme root, but interval bins near zero → NONE
    ("single_bin_A",       _chroma([(0, 0.95)])),

    # 13. G#/Ab major (A-origin root = bin 11, intervals: bin 3=C, bin 6=D#)
    #     Wait: A-origin, Ab = bin 11 (+3=bin2=B, +4=bin3=C, +7=bin6=D#)
    #     Ab major: root=11, major3rd=3(C), fifth=6(D#/Eb)  → +4=3, +7=6
    ("Ab_major_strong",    _chroma([(11, 0.82), (3, 0.64), (6, 0.52)])),

    # 14. Borderline total-energy guard (totalEnergy <= 0.01 branch → NONE)
    ("zero_energy",        _chroma([])),

    # 15. Repeated root change sequence — exercises root-dominance path
    ("Bb_major_strong",    _chroma([(1, 0.88), (5, 0.70), (8, 0.58)])),

    # 16. A-major again after different root — root comparison
    ("A_major_again",      _chroma([(0, 0.88), (4, 0.70), (7, 0.58)])),
]


def _build_stdin():
    lines = []
    for _label, chroma in TRACE:
        vals = " ".join(f"{x:.6f}" for x in chroma)
        lines.append(f"C {vals}")
    return "\n".join(lines) + "\n"


STDIN_TEXT = _build_stdin()

# ---------------------------------------------------------------------------
# Compile + run helpers (mirror chord_saliency_replay.py build() / run())
# ---------------------------------------------------------------------------

def _compile(workdir: Path, extra_defines=None, firmware_root=None):
    """Compile DRIVER + MODULE_CPPS in workdir; return Path to binary."""
    fw = Path(firmware_root) if firmware_root else FW
    stub_dir = workdir / "stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")

    main_cpp = workdir / "main.cpp"
    main_cpp.write_text(DRIVER, encoding="utf-8")

    binary = workdir / "oracle_chord_bin"
    defines = list(DEFINES) + (extra_defines or [])

    cmd = [
        "clang++", "-std=c++17",
        # -O0 for strict determinism — no constant-folding across TU boundary
        "-O0",
        "-I", str(stub_dir),
        "-I", str(fw),
        "-I", str(fw / "audio"),
    ]
    for d in defines:
        cmd.append(f"-D{d}")

    # Compile the firmware TU(s) and the driver together.
    for rel in MODULE_CPPS:
        cmd.append(str(fw / rel))
    cmd.append(str(main_cpp))
    cmd += ["-o", str(binary), "-lm"]

    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"oracle_chord compile failed:\n{r.stderr}"
        )
    return binary


def _run(binary: Path) -> str:
    r = subprocess.run(
        [str(binary)], input=STDIN_TEXT, text=True, capture_output=True
    )
    if r.returncode != 0:
        raise RuntimeError(f"oracle_chord run failed:\n{r.stderr}")
    return r.stdout


def capture(firmware_root=None) -> str:
    """Compile + run; return deterministic JSON-lines golden string."""
    with tempfile.TemporaryDirectory(prefix="oracle_chord_") as td:
        binary = _compile(Path(td), firmware_root=firmware_root)
        return _run(binary)


# ---------------------------------------------------------------------------
# Mutations — 4 real constants from k1_chord_detect.cpp, SUPPRESSING direction
#
# Each must cause capture() on the mutated firmware to diverge from baseline.
# All are in the suppressing direction (weaker detection / collapsed output)
# so that the test proves the oracle CATCHES degradation, not enhancement.
# ---------------------------------------------------------------------------

MUTATIONS = [
    # 1. Confidence threshold: raise from 0.3 → 0.6
    #    Cases near the gate (entries 3,4,8) will collapse to NONE.
    #    Line in k1_chord_detect.cpp: "if (cs.confidence < 0.3f)"
    (
        r"if \(cs\.confidence < 0\.3f\)",
        r"if (cs.confidence < 0.6f)",
        "raise_confidence_threshold_0.3_to_0.6",
    ),

    # 2. Triad-energy ratio denominator: raise from 0.4 → 0.8
    #    Halves the confidence for every case → more cases collapse to NONE.
    #    Line: "cs.confidence = k1_chord_clamp01((triadEnergy / totalEnergy) / 0.4f);"
    (
        r"/ 0\.4f\)",
        r"/ 0.8f)",
        "raise_triad_energy_denominator_0.4_to_0.8",
    ),

    # 3. Perfect-fifth interval from +7 → +5 (wrong semitone)
    #    Changes which bin is tested as perfectFifth for every case.
    #    For A-major (bins 0,4,7): perfectFifth was bin 7, now bin 5 (≈0).
    #    Line: "const float perfectFifth = chroma[(rootIdx + 7) % 12];"
    (
        r"const float perfectFifth = chroma\[\(rootIdx \+ 7\) % 12\];",
        r"const float perfectFifth = chroma[(rootIdx + 5) % 12];",
        "shift_perfect_fifth_interval_7_to_5",
    ),

    # 4. Minor-third interval from +3 → +2 (whole-tone instead of semitone)
    #    Changes the minor-third bin; flips MINOR/MAJOR decisions where the
    #    near-tie traces put almost equal energy at bins +2 and +3.
    #    Line: "const float minorThird   = chroma[(rootIdx + 3) % 12];"
    (
        r"const float minorThird\s*= chroma\[\(rootIdx \+ 3\) % 12\];",
        r"const float minorThird   = chroma[(rootIdx + 2) % 12];",
        "shift_minor_third_interval_3_to_2",
    ),
]


# ---------------------------------------------------------------------------
# Mutation verification helper (used by __main__ and by the gate test)
# ---------------------------------------------------------------------------

def verify_mutations(baseline: str, firmware_root=None) -> list[dict]:
    """
    For each mutation in MUTATIONS, copy the firmware tree to a temp dir,
    apply the regex substitution to k1_chord_detect.cpp, recompile, run,
    and count diverged lines vs baseline.  Returns a list of dicts:
      {"desc": str, "diverged_lines": int, "caught": bool}
    """
    fw_src = Path(firmware_root) if firmware_root else FW
    results = []

    for pattern, replacement, desc in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="oracle_chord_mut_") as td:
            td_path = Path(td)
            # Copy only the audio/ subdirectory (the TUs we compile).
            fw_copy = td_path / "fw"
            shutil.copytree(fw_src, fw_copy, dirs_exist_ok=True)

            target = fw_copy / "audio" / "k1_chord_detect.cpp"
            original = target.read_text(encoding="utf-8")
            mutated = re.sub(pattern, replacement, original)
            if mutated == original:
                results.append({
                    "desc": desc,
                    "diverged_lines": 0,
                    "caught": False,
                    "error": "regex did not match — mutation not applied",
                })
                continue

            target.write_text(mutated, encoding="utf-8")

            try:
                mutant_out = capture(firmware_root=fw_copy)
            except RuntimeError as exc:
                results.append({
                    "desc": desc,
                    "diverged_lines": 0,
                    "caught": False,
                    "error": str(exc)[:200],
                })
                continue

            base_lines = baseline.strip().splitlines()
            mut_lines  = mutant_out.strip().splitlines()
            diverged = sum(
                1 for a, b in zip(base_lines, mut_lines) if a != b
            ) + abs(len(base_lines) - len(mut_lines))

            results.append({
                "desc": desc,
                "diverged_lines": diverged,
                "caught": diverged > 0,
            })

    return results


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Chord golden-master oracle: capture baseline and verify mutations."
    )
    parser.add_argument(
        "--verify-mutations", action="store_true",
        help="After printing the golden record, verify each mutation diverges."
    )
    args = parser.parse_args()

    # Step 1: capture baseline.
    baseline = capture()
    lines = baseline.strip().splitlines()
    print(baseline, end="")

    # Step 2: determinism check — run twice, compare.
    baseline2 = capture()
    if baseline != baseline2:
        print("DETERMINISM FAILURE: two runs produced different output.", file=sys.stderr)
        sys.exit(1)

    print(f"\n# golden_record_count={len(lines)}", file=sys.stderr)
    print(f"# determinism=OK (two runs byte-identical)", file=sys.stderr)

    if args.verify_mutations:
        print("\n# --- Mutation verification ---", file=sys.stderr)
        results = verify_mutations(baseline)
        all_caught = True
        for r in results:
            status = "CAUGHT" if r["caught"] else "MISSED"
            err = f"  error={r.get('error','')}" if not r["caught"] else ""
            print(
                f"#  [{status}] {r['desc']} → diverged_lines={r['diverged_lines']}{err}",
                file=sys.stderr,
            )
            if not r["caught"]:
                all_caught = False
        if all_caught:
            print("# all mutations caught.", file=sys.stderr)
        else:
            print("# WARNING: one or more mutations were not caught.", file=sys.stderr)
            sys.exit(1)
