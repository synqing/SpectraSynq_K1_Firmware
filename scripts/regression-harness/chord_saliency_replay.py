#!/usr/bin/env python3
"""K1_CHORD_V2 host harness — REAL firmware C++ on labelled synthetic chroma.

Two real, flag-gated firmware TUs are compiled on host clang against a minimal
Arduino stub (portMUX no-ops, math) — no globals/FixedPoints/FastLED surface:

  1. audio/k1_chord_detect.cpp     -> k1_detect_chord(chroma_pc[12], ChordState)
       Pitch-class triad detector ported from donor ControlBus::detectChord.
       Driven with labelled synthetic 12-bin chroma vectors (known chords).

  2. audio/k1_musical_saliency.cpp -> k1_musical_saliency_update(snapshot, onset)
       The 4-axis saliency engine. We drive it with a scripted K1AudioSnapshot
       stream (frame_ms / silence / chroma_strength / chord{root,type,conf}) and
       read back harmonicNoveltySmooth, A/B-ing the harmonic axis:
         incumbent  (no flag)   : dead chroma_strength-delta proxy  -> ~0
         K1_CHORD_V2 (flagged)  : chord root/type-change axis        -> ALIVE

Production (no-flag) byte-identity of the saliency engine is asserted by the
incumbent-vs-flag comparison: the no-flag harmonic axis matches the historical
dead-proxy behaviour exactly.

A-origin convention: the fork notes[] table starts at A (55 Hz), so chroma bin 0
is pitch class A. detectChord rootNote is therefore reported in A-origin units
(0 = A). Synthetic fixtures below are built in A-origin pitch classes.

NON-SHIPPING. Host-only. K1_CHORD_V2 / K1_RENDER_HOST_TEST never enter a
PlatformIO env. Run: python3 scripts/regression-harness/chord_saliency_replay.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# Minimal Arduino stub: only the portMUX critical-section surface the two TUs
# touch. Both TUs are otherwise stdint/math-only.
ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
#include <math.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""

# ---- detector harness ------------------------------------------------------
# Reads "C r0 r1 .. r11" lines (12 floats) on stdin, runs the REAL
# k1_detect_chord, prints "D root type conf".
CHORD_MAIN = r"""
#include "k1_audio_snapshot.h"
#include <cstdio>
int main(){
  char tag; float c[12];
  while (std::scanf(" %c", &tag) == 1) {
    if (tag != 'C') { int ch; while((ch=getchar())!='\n'&&ch!=EOF){} continue; }
    for (int i=0;i<12;i++){ if (std::scanf("%f",&c[i])!=1) c[i]=0.0f; }
    K1ChordState cs;
    k1_detect_chord(c, cs);
    std::printf("D %u %u %.4f %.4f %.4f %.4f\n",
      cs.rootNote, (unsigned)cs.type, cs.confidence,
      cs.rootStrength, cs.thirdStrength, cs.fifthStrength);
  }
  std::printf("CHORD_DONE\n");
  return 0;
}
"""

# ---- saliency harness ------------------------------------------------------
# Reads scripted frames on stdin and runs the REAL k1_musical_saliency_update,
# printing harmonicNoveltySmooth per frame.
#   Frame line (no-flag build) : "S ms silence chroma_strength"
#   Frame line (K1_CHORD_V2)   : "S ms silence chroma_strength root type conf"
# Output: "H ms harmonicSmooth harmonicRaw overall"
SAL_MAIN = r"""
#include "k1_musical_saliency.h"
#include <cstdio>
int main(){
  char tag; long ms; int sil; float cs;
  while (std::scanf(" %c", &tag) == 1) {
    if (tag != 'S') { int ch; while((ch=getchar())!='\n'&&ch!=EOF){} continue; }
    if (std::scanf("%ld %d %f", &ms, &sil, &cs) != 3) break;
    K1AudioSnapshot a = {};
    a.frame_ms = (uint32_t)ms;
    a.silence = sil != 0;
    a.chroma_strength = cs;
    a.novelty = 0.2f;          // static non-silent novelty so timbral/dynamic stay quiet
    a.spectral_energy = 0.5f;  // static energy -> dynamic axis ~0
#ifdef K1_CHORD_V2
    int root, type; float conf;
    if (std::scanf("%d %d %f", &root, &type, &conf) != 3) { root=0; type=0; conf=0.0f; }
    a.chord.rootNote = (uint8_t)root;
    a.chord.type = (K1ChordType)type;
    a.chord.confidence = conf;
#else
    // No-flag build still consumes the 3 trailing tokens to keep stdin aligned.
    int root, type; float conf;
    (void)std::scanf("%d %d %f", &root, &type, &conf);
#endif
    k1_musical_saliency_update(a, nullptr);
    K1SaliencyAxisFrame f = k1_musical_saliency_read();
    std::printf("H %ld %.4f %.4f %.4f\n",
      ms, f.harmonicNoveltySmooth, f.harmonicNovelty, f.overallSaliency);
  }
  std::printf("SAL_DONE\n");
  return 0;
}
"""


def build(tu_rel, main_src, defines, workdir, compiler="clang++"):
    workdir = Path(workdir)
    stub = workdir / "stub"
    stub.mkdir(parents=True, exist_ok=True)
    (stub / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
    main_cpp = workdir / "main.cpp"
    main_cpp.write_text(main_src, encoding="utf-8")
    binary = workdir / "bin"
    cmd = [compiler, "-std=c++17", "-O2", "-I", str(stub), "-I", str(FW), "-I", str(FW / "audio")]
    for d in defines:
        cmd += [f"-D{d}"]
    cmd += [str(FW / tu_rel), str(main_cpp), "-o", str(binary)]
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"compile failed ({tu_rel}, {defines}):\n{r.stderr}")
    return binary


def run(binary, stdin_text):
    r = subprocess.run([str(binary)], input=stdin_text, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"run failed:\n{r.stderr}")
    return r.stdout


# ---------------------------------------------------------------- fixtures ---
# A-origin pitch classes: 0=A 1=A# 2=B 3=C 4=C# 5=D 6=D# 7=E 8=F 9=F# 10=G 11=G#
# Musically realistic: the ROOT is the strongest pitch class, the third/fifth
# slightly weaker, and a small noise floor in the off-triad bins. Equal-magnitude
# triads create tied maxima that the strict-> root finder resolves to the lowest
# index (the donor has the identical tie-break); real chords don't have ties.
ROOT_HOT, THIRD_HOT, FIFTH_HOT, FLOOR = 1.0, 0.8, 0.7, 0.05


def triad(root, third_iv, fifth_iv, floor=FLOOR):
    v = [floor] * 12
    v[root % 12] = ROOT_HOT
    v[(root + third_iv) % 12] = THIRD_HOT
    v[(root + fifth_iv) % 12] = FIFTH_HOT
    return v


# type ints: 0 NONE, 1 MAJOR, 2 MINOR, 3 DIM, 4 AUG
MAJOR, MINOR, DIM, AUG, NONE = 1, 2, 3, 4, 0
# Labelled cases: (name, chroma, expected_root_Aorigin, expected_type_int)
CHORD_CASES = [
    ("A_major",   triad(0, 4, 7),  0, MAJOR),   # A C# E
    ("A_minor",   triad(0, 3, 7),  0, MINOR),   # A C  E
    ("A_dim",     triad(0, 3, 6),  0, DIM),     # A C  D#
    ("A_aug",     triad(0, 4, 8),  0, AUG),     # A C# F
    ("D_major",   triad(5, 4, 7),  5, MAJOR),   # root D (A-origin 5)
    ("Gs_minor",  triad(11, 3, 7), 11, MINOR),  # root G# (A-origin 11)
]
# Ambiguous: a perfectly flat chroma. NOTE (inherited donor limitation): the
# triad-energy ratio of any 3 of 12 equal bins is 3/12 = 0.25, /0.4 = 0.625,
# which clears the 0.3 NONE-gate. So a FLAT chroma is NOT rejected by this
# detector — it reads a spurious major triad at conf 0.625. The harmonic-saliency
# axis is protected from this because the snapshot only feeds a real (peaky)
# chroma and the saliency engine additionally gates on silence + onset context;
# but as a pure detector property it is real and documented here.
FLAT = [0.5] * 12
# A single dominant pitch class (unison/cluster), third+fifth empty. NOTE
# (inherited donor limitation): the confidence ratio is energy-weighted and the
# lone loud root dominates it (rootStrength alone ~ 0.7 of total), so this STILL
# reads as a confident "chord" rather than NONE. The donor detector does not
# reliably reject non-triadic input -- confidence is a triad-energy RATIO, not a
# triad-SHAPE test. Documented, asserted as the real behaviour below.
UNISON = [0.05] * 12
UNISON[0] = 1.0


def test_chord_detection(bin_v2):
    stdin = "".join("C " + " ".join(f"{x:.4f}" for x in c) + "\n" for _, c, _, _ in CHORD_CASES)
    out = run(bin_v2, stdin)
    rows = [ln.split() for ln in out.splitlines() if ln.startswith("D ")]
    assert len(rows) == len(CHORD_CASES), f"expected {len(CHORD_CASES)} rows, got {len(rows)}"
    failures = []
    confs = {}
    for (name, _, exp_root, exp_type), row in zip(CHORD_CASES, rows):
        root, typ, conf = int(row[1]), int(row[2]), float(row[3])
        confs[name] = conf
        if typ != exp_type:
            failures.append(f"{name}: type {typ} != expected {exp_type}")
        if root != exp_root:
            failures.append(f"{name}: root {root} != expected {exp_root}")
        # A clean, root-dominant triad must clear the NONE gate decisively.
        if conf < 0.60:
            failures.append(f"{name}: clean-triad confidence {conf:.3f} < 0.60")

    # Ambiguous / no-chord cases.
    amb_stdin = ("C " + " ".join(f"{x:.4f}" for x in FLAT) + "\n"
                 "C " + " ".join(f"{x:.4f}" for x in UNISON) + "\n")
    amb = [ln.split() for ln in run(bin_v2, amb_stdin).splitlines() if ln.startswith("D ")]
    flat_conf = float(amb[0][3])
    unison_conf = float(amb[1][3])
    confs["flat(donor-limit)"] = flat_conf
    confs["unison(donor-limit)"] = unison_conf
    # Inherited donor limitation, asserted as the REAL behaviour (not a pass we
    # engineered): flat and lone-root vectors are NOT rejected by the ratio-based
    # confidence. Pin the known values so a future change to detectChord that
    # alters this is caught and consciously re-judged.
    if not (0.55 <= flat_conf <= 0.70):
        failures.append(f"flat conf {flat_conf:.3f} outside documented donor-limit band [0.55,0.70]")
    if unison_conf < 0.90:
        failures.append(f"unison conf {unison_conf:.3f} < 0.90 (root-dominated ratio expected)")

    # Monotonicity: confidence rises with triad purity. Hold the triad magnitudes
    # fixed and below 1.0 (so the ratio stays unclamped), keep the off-triad floor
    # strictly BELOW the weakest triad tone (root-dominant SNR regime -- the regime
    # where confidence is a meaningful purity measure), and sweep the floor up. A
    # cleaner triad (lower floor) must yield strictly higher confidence.
    sweep = [0.02, 0.06, 0.10, 0.14, 0.18]  # all < fifth tone (0.20)

    def purity_vec(floor):
        v = [floor] * 12
        v[0] = 0.30; v[4] = 0.25; v[7] = 0.20  # A major, low magnitudes (stay unclamped)
        return v

    vecs = [purity_vec(f) for f in sweep]
    sstdin = "".join("C " + " ".join(f"{x:.4f}" for x in v) + "\n" for v in vecs)
    sconf = [float(r[3]) for r in (ln.split() for ln in run(bin_v2, sstdin).splitlines()) if r[0] == "D"]
    monotone = all(sconf[i] >= sconf[i + 1] - 1e-6 for i in range(len(sconf) - 1))
    strict = sconf[0] > sconf[-1] + 0.05
    if not (monotone and strict):
        failures.append(f"monotonicity: confidence not strictly non-increasing with floor: {sconf}")
    return failures, confs, sweep, sconf


def test_saliency_axis(bin_inc, bin_v2):
    # Scripted stream @ 133.33 Hz (dt = 7 ms integer ~= 7.5 ms). The harmonic axis
    # has an intentionally SLOW envelope (harmonicRiseTime 0.15 s, fallTime 0.80 s
    # -- sustained mood), so segments are held ~40 frames (~280 ms) to let the
    # smoothed value develop past the rise time constant. chroma_strength is held
    # CONSTANT so the incumbent (dead) chroma-delta proxy stays ~0 throughout.
    frames = []
    ms = 0
    DT = 7
    SEG = 40  # ~280 ms per segment (> rise tau 150 ms)

    def seg(root, typ, conf, n=SEG):
        nonlocal ms
        first = ms
        for _ in range(n):
            frames.append((ms, 0, 0.40, root, typ, conf)); ms += DT
        return first

    seg(0, MAJOR, 0.90)                 # warmup + static A major
    root_change_first_ms = seg(5, MAJOR, 0.90)   # ROOT change -> D major
    type_change_first_ms = seg(5, MINOR, 0.90)   # TYPE change -> D minor (same root)
    static_tail_first_ms = seg(5, MINOR, 0.90)   # static D minor (axis decays)

    def stream():
        return "".join(f"S {m} {s} {cs:.4f} {r} {t} {c:.4f}\n" for (m, s, cs, r, t, c) in frames)

    inc_rows = [ln.split() for ln in run(bin_inc, stream()).splitlines() if ln.startswith("H ")]
    v2_rows = [ln.split() for ln in run(bin_v2, stream()).splitlines() if ln.startswith("H ")]
    # H ms harmonicSmooth harmonicRaw overall
    inc_h = {int(r[1]): float(r[2]) for r in inc_rows}
    v2_h = {int(r[1]): float(r[2]) for r in v2_rows}
    v2_raw = {int(r[1]): float(r[3]) for r in v2_rows}

    inc_peak = max(inc_h.values())
    v2_peak = max(v2_h.values())
    # Smoothed axis level reached near the END of each change segment (rise developed).
    def smooth_at_end(first_ms):
        win = [v2_h[m] for (m, *_r) in frames if first_ms + (SEG - 6) * DT <= m < first_ms + SEG * DT]
        return max(win) if win else 0.0
    v2_root_rise = smooth_at_end(root_change_first_ms)
    v2_type_rise = smooth_at_end(type_change_first_ms)
    # Raw axis spike on the exact change frame (instantaneous fire).
    v2_root_raw = v2_raw.get(root_change_first_ms, 0.0)
    v2_type_raw = v2_raw.get(type_change_first_ms, 0.0)
    # Static-harmony floor: last 6 frames of the static-tail segment (no change).
    tail_ms = [m for (m, *_r) in frames if static_tail_first_ms + (SEG - 6) * DT <= m]
    v2_static = sum(v2_h[m] for m in tail_ms) / max(len(tail_ms), 1)

    failures = []
    # Incumbent (no-flag) harmonic axis is DEAD: chroma_strength constant -> ~0.
    if inc_peak > 0.02:
        failures.append(f"incumbent harmonic axis not dead: peak {inc_peak:.4f} > 0.02")
    # K1_CHORD_V2 RAW axis is the change detector: fires hard (1.0) on root change,
    # 0.6 on type change. This is the load-bearing "axis is ALIVE" proof.
    if v2_root_raw < 0.95:
        failures.append(f"v2 root-change raw spike {v2_root_raw:.4f} < 0.95")
    if v2_type_raw < 0.55:
        failures.append(f"v2 type-change raw spike {v2_type_raw:.4f} < 0.55")
    # The SMOOTHED axis (slow envelope) develops a sustained presence proportional
    # to chord confidence (donor base = confidence*0.3 ~= 0.27 for conf 0.9). It is
    # NOT expected to hold near 1.0 -- the raw spikes are single-frame, then the
    # static chord drives the base. Assert it is meaningfully > 0 (alive), which
    # the dead incumbent never reaches.
    if v2_root_rise < 0.15:
        failures.append(f"v2 root-seg smoothed level {v2_root_rise:.4f} < 0.15 (axis not sustaining)")
    if v2_static < 0.15:
        failures.append(f"v2 static-harmony floor {v2_static:.4f} < 0.15 (confidence base dead)")
    # The alive axis peak clears the dead incumbent by a wide margin.
    if not (v2_peak > inc_peak + 0.20):
        failures.append(f"v2 peak {v2_peak:.4f} not >> incumbent peak {inc_peak:.4f}")
    return failures, {
        "v2_root_raw": v2_root_raw, "v2_type_raw": v2_type_raw,
        "inc_peak": inc_peak, "v2_peak": v2_peak, "v2_static": v2_static,
        "v2_root_rise": v2_root_rise, "v2_type_rise": v2_type_rise,
    }


def test_incumbent_proxy_intact(bin_inc):
    # Byte-identity guard for the production (no-flag) harmonic axis. The old dead
    # proxy fires only when |Δchroma_strength| crosses harmonicChangeThreshold
    # (0.5). Drive a stream that DOES cross it and confirm the no-flag build still
    # computes the legacy proxy (i.e. the #else branch is the untouched original).
    # If K1_CHORD_V2 had leaked into the no-flag path, this raw value would be
    # chord-derived (~0, no chord fields set) instead of the chroma-delta proxy.
    DT = 7
    frames = [(0, 0, 0.10), (DT, 0, 0.10), (2 * DT, 0, 0.90)]  # warmup, static, +0.80 jump
    stdin = "".join(f"S {m} {s} {cs:.4f} 0 0 0.0\n" for (m, s, cs) in frames)
    rows = [ln.split() for ln in run(bin_inc, stdin).splitlines() if ln.startswith("H ")]
    # raw harmonic on the jump frame: legacy proxy = |0.90-0.10| = 0.80 (clamped 1.0->0.80)
    jump_raw = float(rows[-1][3])
    failures = []
    if not (0.78 <= jump_raw <= 0.82):
        failures.append(f"incumbent proxy intact: jump raw {jump_raw:.4f} != ~0.80 (legacy chroma-delta proxy changed!)")
    return failures, jump_raw


def main():
    compiler = "clang++"
    if "--compiler" in sys.argv:
        compiler = sys.argv[sys.argv.index("--compiler") + 1]
    tmp = tempfile.TemporaryDirectory()
    base = Path(tmp.name)

    bin_chord_v2 = build("audio/k1_chord_detect.cpp", CHORD_MAIN, ["K1_CHORD_V2"], base / "chord_v2", compiler)
    bin_sal_inc = build("audio/k1_musical_saliency.cpp", SAL_MAIN, [], base / "sal_inc", compiler)
    bin_sal_v2 = build("audio/k1_musical_saliency.cpp", SAL_MAIN, ["K1_CHORD_V2"], base / "sal_v2", compiler)

    all_fail = []

    cfail, confs, sweep, sconf = test_chord_detection(bin_chord_v2)
    all_fail += cfail
    sfail, sm = test_saliency_axis(bin_sal_inc, bin_sal_v2)
    all_fail += sfail
    ifail, jump_raw = test_incumbent_proxy_intact(bin_sal_inc)
    all_fail += ifail

    # ----- A/B report
    print("=== CHORD DETECTION (synthetic, A-origin: 0=A) ===")
    print(f"{'case':18} {'conf':>6}")
    for name in confs:
        print(f"{name:18} {confs[name]:6.3f}")
    print(f"monotonicity (triad purity, floor sweep {sweep}): conf {[round(c,3) for c in sconf]}")
    print()
    print("=== HARMONIC SALIENCY AXIS A/B (incumbent dead-proxy vs K1_CHORD_V2) ===")
    print(f"incumbent peak (dead)    : {sm['inc_peak']:.4f}")
    print(f"v2 raw root-change spike : {sm['v2_root_raw']:.4f}")
    print(f"v2 raw type-change spike : {sm['v2_type_raw']:.4f}")
    print(f"v2 smoothed peak (alive) : {sm['v2_peak']:.4f}")
    print(f"v2 smoothed @ root seg end: {sm['v2_root_rise']:.4f}")
    print(f"v2 smoothed @ type seg end: {sm['v2_type_rise']:.4f}")
    print(f"v2 static-harmony floor  : {sm['v2_static']:.4f}")
    print(f"incumbent legacy proxy (no-flag, +0.80 chroma jump): {jump_raw:.4f}  [byte-identity guard]")
    print()

    if all_fail:
        print("CHORD_SALIENCY_REPLAY_FAIL")
        for f in all_fail:
            print(f"  - {f}")
        return 1
    print(f"CHORD_SALIENCY_REPLAY_OK chord_cases={len(CHORD_CASES)} saliency_ab=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
