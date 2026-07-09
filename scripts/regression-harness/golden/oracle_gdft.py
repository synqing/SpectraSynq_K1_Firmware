#!/usr/bin/env python3
"""Golden-master oracle for the GDFT spectrum transform (process_GDFT + novelty).

Compiles the REAL firmware audio/k1_gdft_core.cpp on the host (g++), drives it
with a fixed deterministic audio trace — INCLUDING a sustained 440 Hz @ amplitude
16000 tone (>=10 frames) so the Goertzel resonator q-state reaches ~160k and the
int32 overflow path is exercised — and captures a JSON-lines golden record that
any refactor must reproduce.

This is the spectrum tap — the one gap the Phase-F fan-out could only replicate.
It pins the int32 (int64-OFF) baseline so the K1_GDFT_INT64_* promotion (S2) is a
verifiable delta. Extraction contract: docs/architecture/gdft-decomposition-lane.md.

Design mirrors oracle_chord.py's PUBLIC INTERFACE (NAME / MODULE_CPPS / DEFINES /
DRIVER / capture(firmware_root=None) / MUTATIONS) and oracle_render.py's COMPILE
MACHINERY (GCC + stubs/ + FixedPoints + render_host_globals.cpp + the
globals/Palettes/render_params COMMON TUs), because k1_gdft_core.cpp pulls the
full globals.h surface (FastLED/USB/palette types) exactly like a render TU does.

Output per frame:
  {"f":<int>, "nov":"<%.5f>", "spec":[<%.5f>*80], "mag_i32":[<int>*80]}
- spec[i]   = spectrogram[i] (post-AGC SQ15x16, the real downstream spectrum)
- mag_i32[i]= the RAW int32_t magnitudes[i] BEFORE sqrtf is NOT recoverable as an
  int (firmware stores sqrtf result back into magnitudes[]), so we capture the
  pre-sqrt magnitude-squared by reading the real magnitudes[] right after the
  GDFT loop via the driver — see note below. A Site-B wrap-to-negative under the
  16000 tone shows up as the int32-clamped 0 vs the int64 true value.

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
# Repo layout (mirrors oracle_render.py)
# ---------------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parents[3]            # SpectraSynq_K1_Firmware/
FIRMWARE    = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
STUBS       = ROOT / "scripts" / "regression-harness" / "stubs"
FIXEDPOINTS = ROOT / "libraries" / "FixedPoints" / "src"
HOST_GLOBALS = ROOT / "scripts" / "regression-harness" / "render_host_globals.cpp"

# Firmware subdirs added to -I (mirrors oracle_render.py FW_SUBDIRS, plus the
# ones a full-globals.h TU reaches).
FW_SUBDIRS = ("audio", "visual", "effects", "director", "serial", "system",
              "persistence", "calibration", "diag", "control", "network")

# Sources compiled for the GDFT TU. globals.cpp/Palettes.cpp/render_params.cpp +
# render_host_globals.cpp are the same COMMON substrate the render oracle uses to
# satisfy globals.h's data globals + palette tables + the host singletons
# (Serial/FastLED/ESP/CONFIG). k1_gdft_core.cpp is the real transform under test.
COMMON_SOURCES = [
    "system/globals.cpp",
    "visual/Palettes.cpp",
    "visual/render_params.cpp",
]

# Compiler preference order (GCC, for FixedPoints SQ15x16 compound-literal compat;
# mirrors oracle_render.py).
_GPP_CANDIDATES = ["g++-15", "g++-14", "g++-13", "g++-12", "g++"]

# ---------------------------------------------------------------------------
# Oracle identity
# ---------------------------------------------------------------------------
NAME = "gdft"

MODULE_CPPS = [
    "audio/k1_gdft_core.cpp",
]

# Production-matching defines, with the int32 (int64-OFF) baseline pinned.
#   - DEFAULT_SAMPLE_RATE / DEFAULT_SAMPLES_PER_CHUNK / K1_TEMPO_NOVELTY_DECIMATION:
#       the [env:k1_hardware] audio contract.
#   - K1_LOUD_GUARD_V1: ON in [env:k1_hardware]; k1_loud_guard_enabled defaults
#       true, so the AGC loud-trim path is LIVE in production — the golden must
#       lock the production spectrum, so it is included here too.
#   - K1_RENDER_HOST_TEST: render_host_globals.cpp's host singletons (no functional
#       effect on the GDFT transform; matches the render substrate it shares).
#   - NO K1_GDFT_INT64_MAGNITUDE_V1 / _RECURRENCE_V1 / K1_GDFT_TRUE_CENTER_V1 /
#       K1_SPECTRAL_WINDOW_V1 ⇒ pins the buggy int32 baseline; the int64 promotion
#       (S2) is then a verifiable golden delta.
DEFINES = [
    "DEFAULT_SAMPLE_RATE=12800",
    "DEFAULT_SAMPLES_PER_CHUNK=96",
    "K1_TEMPO_NOVELTY_DECIMATION=3U",
    "K1_LOUD_GUARD_V1",
    "K1_RENDER_HOST_TEST",
]

# ---------------------------------------------------------------------------
# C++ driver
#
# Self-contained. Provides:
#   * host no-op stubs for the 5 cross-TU cal/flash symbols k1_gdft_core.cpp
#     forward-declares (never executed: the driver sets noise_complete=true so
#     the cal-completion block is unreachable; they only need to LINK).
#   * a VERBATIM lift of precompute_goertzel_constants() (int32 / non-true-centre
#     path, system.h:301-306) to populate frequencies[] exactly as the firmware
#     does at boot — the host cannot run system.h (it drags led_utilities/esp_*),
#     so the boot-time init is reconstructed here from the SAME formula + notes[].
#   * the deterministic trace: silence warm-up, then a sustained 440 Hz @ 16000
#     tone for 12 frames (bin 24 == 440.0 Hz at NOTE_OFFSET=12 ⇒ q ~160k ⇒ the
#     int32 magnitude path overflows; the int64 mutation diverges here).
#
# Emits one JSON record per frame: f, nov, spec[80], mag_i32[80].
# mag_i32[i] is the pre-sqrt magnitude-squared recomputed in-driver from the SAME
# q-state the firmware uses is NOT accessible (q is a function-local); instead we
# capture the firmware's magnitudes[] AFTER sqrtf as an integer (it is stored back
# into the int32_t magnitudes[] array) — a Site-B wrap shows as a 0 where the
# int64 path yields a large positive value. This keeps the firmware math UNTOUCHED.
# ---------------------------------------------------------------------------
DRIVER = r"""
#include "globals.h"
#include "constants.h"
#include "k1_gdft_core.h"
#include "k1_spectral_honesty.h"   // k1_hann_window_mult (for the lifted coeff init)

#include <cstdio>
#include <cmath>
#include <cstring>

// --- host no-op stubs for the cross-TU cal/flash symbols (never executed) ----
void clear_spectral_noise_samples() {}
void noise_cal_restore_previous_or_invalidate() {}
void save_config() {}
void save_ambient_noise_calibration() {}
bool save_calibration_profile(uint8_t) { return true; }

// --- VERBATIM lift of precompute_goertzel_constants() int32 path -------------
// Source: SPECTRASYNQ_K1_FIRMWARE/system/system.h:242-311 (K1_GDFT_TRUE_CENTER_V1
// and K1_SPECTRAL_WINDOW_V1 OFF — the production int32 baseline). Reconstructs
// the boot-time frequencies[] init the host cannot run. Statement-identical to
// the firmware's #else (non-true-centre) branch.
static void host_precompute_goertzel_constants() {
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    int16_t n = i;
    frequencies[i].target_freq = notes[n + CONFIG.NOTE_OFFSET];

    float neighbor_left;
    float neighbor_right;

    if (i == 0) {
      neighbor_left = notes[n + CONFIG.NOTE_OFFSET];
      neighbor_right = notes[n + CONFIG.NOTE_OFFSET + 1];
    } else if (i == NUM_FREQS - 1) {
      neighbor_left = notes[n + CONFIG.NOTE_OFFSET - 1];
      neighbor_right = notes[n + CONFIG.NOTE_OFFSET];
    } else {
      neighbor_left = notes[n + CONFIG.NOTE_OFFSET - 1];
      neighbor_right = notes[n + CONFIG.NOTE_OFFSET + 1];
    }

    float neighbor_left_distance_hz = fabs(neighbor_left - frequencies[i].target_freq);
    float neighbor_right_distance_hz = fabs(neighbor_right - frequencies[i].target_freq);
    float max_distance_hz = 0;
    if (neighbor_left_distance_hz > max_distance_hz) {
      max_distance_hz = neighbor_left_distance_hz;
    }
    if (neighbor_right_distance_hz > max_distance_hz) {
      max_distance_hz = neighbor_right_distance_hz;
    }

    frequencies[i].block_size = CONFIG.SAMPLE_RATE / (max_distance_hz * 2.0);

    if(frequencies[i].block_size > 2000){
        frequencies[i].block_size = 2000;
    }

    if (frequencies[i].block_size > 0) {
        frequencies[i].inv_block_size_half = 2.0 / frequencies[i].block_size;
    } else {
        frequencies[i].inv_block_size_half = 0.0;
    }

    frequencies[i].block_size_recip = 1.0 / float(frequencies[i].block_size);

    float k = (int)(0.5 + ((frequencies[i].block_size * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE));
    float w = (2.0 * PI * k) / frequencies[i].block_size;
    float cosine = cos(w);
    float sine = sin(w);
    float coeff = 2.0 * cosine;
    frequencies[i].coeff_q14 = (1 << 14) * coeff;

    frequencies[i].window_mult = k1_hann_window_mult(frequencies[i].block_size);
  }
}

// --- VERBATIM lift of the broadband-AGC tilt LUT init ------------------------
// Source: SPECTRASYNQ_K1_FIRMWARE/system/system.h:636-646. Like frequencies[],
// spectral_tilt_lut[] is an inline array zero-initialised in globals.h and filled
// at boot — the host cannot run system.h, so this reconstructs that init from the
// SAME formula. Without it spectral_tilt_lut[]==0 ⇒ the post-AGC spectrogram is
// uniformly zero and the spec[] field is blind. Statement-identical to the source.
static void host_init_spectral_tilt_lut() {
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    float freq = frequencies[i].target_freq;
    float tilt;
    if (freq < 200.0f)        tilt = 1.30f;  // bass emphasis
    else if (freq > 3000.0f)  tilt = 0.85f;  // treble protection
    else                       tilt = 1.00f; // mids neutral
    spectral_tilt_lut[i] = SQ15x16(tilt);
  }
  agc_envelope = SQ15x16(0.0);
  agc_noise_floor = SQ15x16(0.001);
  agc_gated = true;
}

int main() {
  // v40102 chroma-profile defaults the firmware boots with (config_types.h):
  // NOTE_OFFSET=12 ⇒ bin 24 == 440.0 Hz exactly. SAMPLE_RATE=12800 ⇒ the
  // [env:k1_hardware] audio contract.
  CONFIG.SAMPLE_RATE = 12800;
  CONFIG.NOTE_OFFSET = 12;
  CONFIG.MOOD = 0.5f;
  CONFIG.LIGHTSHOW_MODE = 0;   // not LIGHT_MODE_BLOOM ⇒ MOOD_VAL stays 0.5
  host_precompute_goertzel_constants();
  host_init_spectral_tilt_lut();

  // Calibration is INERT in the oracle: noise_complete=true so the cal FSM gate
  // (if (noise_complete==false)) is never entered ⇒ no flash/serial side effects.
  noise_complete = true;

  // Deterministic trace. Each frame fills the full sliding window so the Goertzel
  // (which reads sample_window[SAMPLE_HISTORY_LENGTH-1] downward) sees a coherent
  // signal. A continuous phase clock (advanced 96 samples/frame) keeps the tone
  // phase-consistent across frames, as on device.
  const int WARMUP_FRAMES = 4;      // silence (lets EMAs/AGC settle deterministically)
  const int TONE_FRAMES   = 12;     // sustained 440 Hz @ 16000 (>=10, per contract)
  const int TOTAL_FRAMES  = WARMUP_FRAMES + TONE_FRAMES;
  const double w440 = 2.0 * M_PI * 440.0 / 12800.0;

  for (int f = 0; f < TOTAL_FRAMES; f++) {
    const bool tone = (f >= WARMUP_FRAMES);
    const double amp = tone ? 16000.0 : 0.0;
    // Newest sample at index SAMPLE_HISTORY_LENGTH-1; reconstruct a coherent sine
    // whose phase advances by 96 samples each frame (frame f covers absolute
    // sample offset f*96 .. f*96 + SAMPLE_HISTORY_LENGTH-1).
    const long base = (long)(f - WARMUP_FRAMES) * 96; // tone time origin
    for (int s = SAMPLE_HISTORY_LENGTH - 1; s >= 0; s--) {
      double t = (double)(base + (SAMPLE_HISTORY_LENGTH - 1 - s));
      sample_window[s] = (short)(amp * sin(w440 * t));
    }

    process_GDFT();
    calculate_novelty((uint32_t)f);

    // Emit one JSON record per frame.
    std::printf("{\"f\":%d,\"nov\":\"%.5f\",\"spec\":[", f,
                (float)novelty_curve[spectral_history_index == 0
                    ? (SPECTRAL_HISTORY_LENGTH - 1) : (spectral_history_index - 1)]);
    for (int i = 0; i < NUM_FREQS; i++) {
      std::printf("%s\"%.5f\"", (i ? "," : ""), (float)spectrogram[i]);
    }
    std::printf("],\"mag_i32\":[");
    for (int i = 0; i < NUM_FREQS; i++) {
      std::printf("%s%d", (i ? "," : ""), (int)magnitudes[i]);
    }
    std::printf("]}\n");
  }
  return 0;
}
"""

# ---------------------------------------------------------------------------
# Mutations — >=3 real-mechanism + the int64-overflow one. Each must diverge the
# golden (proven by harness_selftest.py / __main__ --verify-mutations).
# The first three are in audio/k1_gdft_core.cpp; the int64 one flips the compile.
# ---------------------------------------------------------------------------
MUTATIONS = [
    # 1. Goertzel input shift: (sample >> 6) -> (sample >> 5). Doubles the per-
    #    sample drive into the resonator ⇒ every magnitude/spectrum value changes.
    #    Anchored to the int32 `#else` recurrence BLOCK (the `#else\n  mult = ...`
    #    pair) so the regex is UNIQUE to k1_gdft_core.cpp — the orphan legacy copy
    #    audio/audio_transfer.h has the bare goertzel lines but NOT the
    #    `#if K1_GDFT_INT64_RECURRENCE_V1 / #else` wrapper, so a bare-line anchor
    #    would let the harness mutate the dead file instead of the live TU.
    (
        r"#else\n      mult = coeff_q14 \* \(int32_t\)q1;\n      q0 = \(sample >> 6\) \+ \(mult >> 14\) - q2;",
        r"#else\n      mult = coeff_q14 * (int32_t)q1;\n      q0 = (sample >> 5) + (mult >> 14) - q2;",
        "goertzel_input_shift_6_to_5 (doubles resonator drive)",
    ),
    # 2. Goertzel coeff Q-scale: (mult >> 14) -> (mult >> 13). Doubling the
    #    coefficient scale detunes every bin's recurrence ⇒ spectrum diverges.
    #    Same unique `#else`-block anchor (see #1).
    (
        r"#else\n      mult = coeff_q14 \* \(int32_t\)q1;\n      q0 = \(sample >> 6\) \+ \(mult >> 14\) - q2;",
        r"#else\n      mult = coeff_q14 * (int32_t)q1;\n      q0 = (sample >> 6) + (mult >> 13) - q2;",
        "goertzel_coeff_qscale_14_to_13 (detunes every bin)",
    ),
    # 3. Per-bin EMA attack: MAGNITUDES_AVG_ATTACK is the asymmetric attack coeff
    #    feeding magnitudes_normalized_avg -> magnitudes_final. Halving it slows the
    #    transient rise, changing magnitudes_final (hence mag-derived spec AND the
    #    novelty) on every tone frame — bites even where spec saturates because it
    #    moves the pre-clamp value AND the warm-up/transition frames (4-6) that are
    #    not yet at the 1.0 ceiling. (Constant lives in constants.h:349, referenced
    #    by name in the lifted EMA block — mutate the reference site in the .cpp by
    #    forcing a literal so the edit is local to k1_gdft_core.cpp.)
    (
        r"\? MAGNITUDES_AVG_ATTACK",
        r"? (MAGNITUDES_AVG_ATTACK * 0.25f)",
        "ema_attack_quartered (slows transient rise; shifts transition frames)",
    ),
    # 4. THE OVERFLOW MUTATION: compile the magnitude path with int64. Under the
    #    16000 tone, bin 24 (440 Hz) wraps the int32 magnitude-squared negative ⇒
    #    the legacy clamp zeroes it; int64 yields the true large magnitude. mag_i32
    #    (and the downstream spec) MUST diverge on the near-resonance bins.
    #    Applied as a source edit (the selftest mutates a firmware-tree COPY): turn
    #    the magnitude #if guard on by defining the flag at the top of the TU.
    (
        r"// Obscure audio magic happens here",
        r"#define K1_GDFT_INT64_MAGNITUDE_V1 1\n// Obscure audio magic happens here",
        "int64_magnitude_ON (un-wraps near-resonance under 16000 tone)",
    ),
    # 5 + 6. RED-TEAM HARDENING (2026-06-23): S2 promotes BOTH int64 flags, but the
    #    original four mutations only proved the MAGNITUDE half — leaving the oracle's
    #    coverage of the RECURRENCE fix unasserted. Backtest confirmed both diverge
    #    the golden (12 tone frames each); these lock that proof into Gate Fα so the
    #    safety net can never silently go blind to either half of the S2 delta.
    (
        r"// Obscure audio magic happens here",
        r"#define K1_GDFT_INT64_RECURRENCE_V1 1\n// Obscure audio magic happens here",
        "int64_recurrence_ON (the other S2 half — q-state overflow)",
    ),
    (
        r"// Obscure audio magic happens here",
        r"#define K1_GDFT_INT64_MAGNITUDE_V1 1\n#define K1_GDFT_INT64_RECURRENCE_V1 1\n// Obscure audio magic happens here",
        "int64_both_ON (the full S2 promotion delta)",
    ),
]

# ---------------------------------------------------------------------------
# Compile + run helpers (mirror oracle_render.py)
# ---------------------------------------------------------------------------

def _detect_compiler():
    for cand in _GPP_CANDIDATES:
        if shutil.which(cand):
            return cand
    return "g++"


def _compile(workdir: Path, firmware_root=None) -> Path:
    fw = Path(firmware_root) if firmware_root else FIRMWARE
    main_cpp = workdir / "oracle_gdft_driver.cpp"
    main_cpp.write_text(DRIVER, encoding="utf-8")
    binary = workdir / "oracle_gdft_bin"

    cc = _detect_compiler()

    sources = [str(fw / s) for s in COMMON_SOURCES]
    sources += [str(HOST_GLOBALS)]
    sources += [str(fw / s) for s in MODULE_CPPS]
    sources += [str(main_cpp)]

    cmd = [
        cc, "-std=c++17",
        # -O0 -fno-fast-math for strict, clean-IEEE determinism (the oracle locks
        # algorithm structure; -ffast-math is a separate ticketed concern).
        "-O0", "-fno-fast-math",
        "-Wno-unused-parameter", "-Wno-unused-variable", "-Wno-unused-function",
        *[f"-D{d}" for d in DEFINES],
        "-I", str(STUBS),
        "-I", str(FIXEDPOINTS),
        "-I", str(fw),
        *[arg for d in FW_SUBDIRS for arg in ("-I", str(fw / d))],
        *sources,
        "-o", str(binary),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"oracle_gdft compile failed (rc={r.returncode}):\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDERR:\n{r.stderr}\nSTDOUT:\n{r.stdout}"
        )
    return binary


def _run(binary: Path) -> str:
    r = subprocess.run([str(binary)], cwd=str(ROOT), text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"oracle_gdft run failed (rc={r.returncode}):\n{r.stderr}")
    return r.stdout


def capture(firmware_root=None) -> str:
    """Compile + run; return deterministic JSON-lines golden string."""
    with tempfile.TemporaryDirectory(prefix="oracle_gdft_") as td:
        binary = _compile(Path(td), firmware_root=firmware_root)
        return _run(binary)


# ---------------------------------------------------------------------------
# Mutation verification helper (used by __main__; harness_selftest.py has its own
# central mutator that edits a firmware-tree COPY and re-runs capture()).
# ---------------------------------------------------------------------------

def verify_mutations(baseline: str, firmware_root=None) -> list:
    fw_src = Path(firmware_root) if firmware_root else FIRMWARE
    results = []
    for pattern, replacement, desc in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="oracle_gdft_mut_") as td:
            fw_copy = Path(td) / "fw"
            shutil.copytree(fw_src, fw_copy)
            target = fw_copy / "audio" / "k1_gdft_core.cpp"
            original = target.read_text(encoding="utf-8")
            mutated = re.sub(pattern, replacement, original, count=1)
            if mutated == original:
                results.append({"desc": desc, "diverged_lines": 0, "caught": False,
                                "error": "regex did not match"})
                continue
            target.write_text(mutated, encoding="utf-8")
            try:
                mutant_out = capture(firmware_root=fw_copy)
            except RuntimeError as exc:
                results.append({"desc": desc, "diverged_lines": 0, "caught": False,
                                "error": str(exc)[:200]})
                continue
            base_lines = baseline.strip().splitlines()
            mut_lines = mutant_out.strip().splitlines()
            diverged = sum(1 for a, b in zip(base_lines, mut_lines) if a != b) \
                       + abs(len(base_lines) - len(mut_lines))
            results.append({"desc": desc, "diverged_lines": diverged, "caught": diverged > 0})
    return results


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GDFT golden-master oracle.")
    parser.add_argument("--verify-mutations", action="store_true")
    args = parser.parse_args()

    baseline = capture()
    print(baseline, end="")

    baseline2 = capture()
    if baseline != baseline2:
        print("DETERMINISM FAILURE: two runs differ.", file=sys.stderr)
        sys.exit(1)

    lines = baseline.strip().splitlines()
    print(f"\n# golden_record_count={len(lines)}", file=sys.stderr)
    print("# determinism=OK (two runs byte-identical)", file=sys.stderr)

    if args.verify_mutations:
        print("\n# --- Mutation verification ---", file=sys.stderr)
        all_caught = True
        for r in verify_mutations(baseline):
            status = "CAUGHT" if r["caught"] else "MISSED"
            err = f"  error={r.get('error','')}" if not r["caught"] else ""
            print(f"#  [{status}] {r['desc']} -> diverged_lines={r['diverged_lines']}{err}",
                  file=sys.stderr)
            all_caught = all_caught and r["caught"]
        print("# all mutations caught." if all_caught
              else "# WARNING: a mutation was not caught.", file=sys.stderr)
        sys.exit(0 if all_caught else 1)
