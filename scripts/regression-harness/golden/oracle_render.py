#!/usr/bin/env python3
"""Golden-master oracle for the K1 render path — Phase F firmware modernization.

Drives the REAL light_mode_bloom + light_mode_spectrum_river render path
(the two modes the existing render_replay.py harness already validates) through
host compilation, confirms byte-identical determinism, and proves that 4
mutations in distinct mechanisms each diverge the LED frame-buffer output.

Public interface (consumed by test_golden_master.py / harness_selftest.py):
    NAME        str   module tag
    MODULE_CPPS list  firmware source files (beyond COMMON) to compile
    DEFINES     list  production -D flags (matching [env:k1_hardware])
    DRIVER      str   C++ driver source (embedded; NOT read from disk)
    capture()   str   compile + run, return stdout (JSON lines); raise on failure
    MUTATIONS   list  [(regex_pattern, replacement, description), ...]

Design notes:
  - Reuses render_replay.py's proven compile machinery verbatim (same STUBS,
    FW_SUBDIRS, COMMON_SOURCES, HOST_GLOBALS, sb_render_host_dump, parse_frame,
    and RenderParams param-header protocol).  This oracle adds a self-contained
    capture() that does NOT import render_replay.py — it re-implements the
    narrow compile+run slice so the oracle is dependency-free.
  - Two modes in one driver: bloom (20 frames, chromagram-driven) followed by
    spectrum_river (20 frames, spectrogram-driven).  Per-mode sections are
    separated by a "MODE bloom" / "MODE spectrum_river" line so the JSON parser
    can label them.  Total: 40 golden records.
  - Determinism: -O0, fixed MOOD/SATURATION/PHOTONS params, no millis() drift
    (g_sb_host_millis advanced by a fixed 8 ms per frame), no random state.
  - Sensitivity: bloom inserts a strong non-zero chromagram at the centre (full
    bloom with motion memory); spectrum_river injects a ramp across all 80 bins.
    Both capture a CRC32 of all 160×3 bytes PLUS 10 sampled LED indices so any
    brightness-scale, fade-alpha, colour-lookup, or position-math change changes
    multiple fields.
  - LED_COUNT = 160 (NATIVE_RESOLUTION, K1 hardware).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — mirrors render_replay.py exactly
# ---------------------------------------------------------------------------
ROOT       = Path(__file__).resolve().parents[3]
FIRMWARE   = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
STUBS      = ROOT / "scripts" / "regression-harness" / "stubs"
FIXEDPOINTS = ROOT / "libraries" / "FixedPoints" / "src"
HOST_GLOBALS = ROOT / "scripts" / "regression-harness" / "render_host_globals.cpp"

LED_COUNT  = 160   # NATIVE_RESOLUTION (constants.h / config_types.h)
BYTE_COUNT = LED_COUNT * 3

# Firmware subdirs added to -I (mirrors render_replay.py FW_SUBDIRS)
FW_SUBDIRS = ("audio", "visual", "effects", "director", "serial", "system",
              "persistence", "calibration", "diag")

# Sources compiled for every mode (mirrors render_replay.py COMMON_SOURCES)
COMMON_SOURCES = [
    "visual/render_params.cpp",
    "visual/Palettes.cpp",
    "system/globals.cpp",
]

# Per-oracle mode sources (beyond COMMON)
_MODE_SOURCES = [
    "effects/light_mode_bloom.cpp",
    "effects/light_mode_spectrum_river.cpp",
]

# Compiler preference order (must be GCC for FixedPoints SQ15x16 compound-literal
# compat; mirrors render_replay.py GPP_CANDIDATES)
_GPP_CANDIDATES = ["g++-15", "g++-14", "g++-13", "g++-12", "g++"]

# ---------------------------------------------------------------------------
# Oracle identity
# ---------------------------------------------------------------------------
NAME = "render"

MODULE_CPPS = [str(FIRMWARE / s) for s in _MODE_SOURCES]

# Production-matching defines ([env:k1_hardware] build_flags, 2026-06-11).
# Only the flags that affect the render / LED path are included; audio-DSP
# flags (SB_TEMPO_*, SB_ONSET_*) have no effect on host-compiled render TUs.
DEFINES = [
    "SB_RENDER_HOST_TEST",     # enables sb_render_host_dump; non-shippable
    "SB_CHORD_HUE_V1",         # Tier-1 chord consumer (Dense Forge hue anchor)
    "SB_DROP_CUT_V1",          # musical silence -> dark; affects brightness
    "SB_SEMANTIC_STATE",       # AudioSemanticState spine (inert on host render)
    "SB_CHORD_V2",             # ChordState (inert on host render)
    "K1_LOUD_GUARD_V1",        # loud-guard brightness limiter
]

# ---------------------------------------------------------------------------
# C++ driver
#
# Self-contained: does NOT depend on any Python helper.  Compiles with the
# same -I / -D flags as render_replay.py build_binary().
#
# Protocol (stdin):
#   Line 1:  "P <mood> <sat> <sq_iter> <chroma> <pal_mode> <pal_idx>
#              <auto_shift> <hue_pos> <chroma_v> <chromatic>"
#   Lines 2+: "M <mode_name>"  — switch active mode (bloom / spectrum_river)
#             "F <ms> <c0..c11> <s0..s79> <wf_peak> <max_wf> <bass> <bass_str> <sil>"
#
# Output (stdout):
#   "MODE <name>"          — echoed when mode switches
#   "R <hex>"              — 160*3 bytes of the leds_16 buffer (pre-gamma linear)
#   "RENDER_DONE frames=N" — sentinel
#
# Emit format matches render_replay.py byte-for-byte so existing tooling can
# consume the oracle output directly.
# ---------------------------------------------------------------------------
DRIVER = r"""
// oracle_render_driver.cpp  (HOST-ONLY, -DSB_RENDER_HOST_TEST)
// Drives light_mode_bloom and light_mode_spectrum_river with a fixed
// deterministic audio-state sequence and dumps leds_16 per frame.
// Compiled by oracle_render.py capture() — NOT shipped in firmware.
#include "lightshow_modes.h"

#include <cstdio>
#include <cstring>
#include <cstdlib>

// ---- parsed-frame struct -----------------------------------------------
struct HostFrame {
  unsigned int ms;
  float chroma[12];
  float spectro[80];
  float waveform_peak_scaled;
  float max_waveform_val_raw;
  int   bass_onset;
  float bass_onset_strength;
  int   silence;
};

// ---- state: bloom needs a prev-buffer; spectrum_river manages its own ---
static CRGB16 g_bloom_prev[NATIVE_RESOLUTION];
static CRGB16 g_river_prev[NATIVE_RESOLUTION];

static void reset_all() {
  std::memset(g_bloom_prev, 0, sizeof(g_bloom_prev));
  std::memset(g_river_prev, 0, sizeof(g_river_prev));
  std::memset(leds_16,      0, sizeof(CRGB16) * NATIVE_RESOLUTION);
}

// ---- pre-gamma linear dump (mirrors render_replay.py sb_render_host_dump) --
static void sb_render_host_dump(unsigned char* out_bytes) {
  for (int i = 0; i < NATIVE_RESOLUTION; i++) {
    float ch[3] = { float(leds_16[i].r), float(leds_16[i].g), float(leds_16[i].b) };
    for (int c = 0; c < 3; c++) {
      float v = ch[c];
      if (v < 0.0f) v = 0.0f;
      if (v > 1.0f) v = 1.0f;
      int q = (int)(v * 255.0f + 0.5f);
      if (q < 0) q = 0; if (q > 255) q = 255;
      out_bytes[i * 3 + c] = (unsigned char)q;
    }
  }
}

// ---- frame parser (same field order as render_replay.py _frames_to_stdin) --
static bool parse_frame(const char* line, HostFrame& fr) {
  if (line[0] != 'F') return false;
  std::memset(&fr, 0, sizeof(fr));
  const char* p = line + 1;
  char* end = nullptr;
  fr.ms = (unsigned int)std::strtoul(p, &end, 10); p = end;
  for (int i = 0; i < 12; i++)  { fr.chroma[i]  = std::strtof(p, &end); p = end; }
  for (int i = 0; i < 80; i++)  { fr.spectro[i] = std::strtof(p, &end); p = end; }
  fr.waveform_peak_scaled = std::strtof(p, &end); p = end;
  fr.max_waveform_val_raw = std::strtof(p, &end); p = end;
  fr.bass_onset           = (int)std::strtol(p, &end, 10); p = end;
  fr.bass_onset_strength  = std::strtof(p, &end); p = end;
  fr.silence              = (int)std::strtol(p, &end, 10); p = end;
  return true;
}

int main(int /*argc*/, char** /*argv*/) {
  char line[4096];

  // ---- stdin line 1: render params (mirrors render_replay.py _params_line) --
  RenderParams rp;
  std::memset(&rp, 0, sizeof(rp));
  // Sensible production-like defaults so effects light the strip
  rp.MOOD        = 0.5f;
  rp.SATURATION  = 0.9f;
  rp.SQUARE_ITER = 1.0f;
  rp.CHROMA      = 1.0f;
  rp.PHOTONS     = 1.0f;   // full brightness so mutations affect real pixel values
  rp.PALETTE_MODE_ENABLED = false;
  rp.PALETTE_INDEX = 0;
  rp.AUTO_COLOR_SHIFT = false;
  rp.hue_position = SQ15x16(0.0f);
  rp.chroma_val   = SQ15x16(0.8f);
  rp.chromatic_mode = true;
  rp.hue_shifting_mix = SQ15x16(0.0f);
  rp.MIRROR_ENABLED = true;
  rp.INCANDESCENT_FILTER = 0.0f;
  rp.INCANDESCENT_MODE   = false;
  rp.SWEET_SPOT_MIN_LEVEL = 0;
  rp.SENSITIVITY = 1.0f;
  rp.SAMPLES_PER_CHUNK = 96;

  if (std::fgets(line, sizeof(line), stdin)) {
    if (line[0] == 'P') {
      float mood=0.5f, sat=0.9f, sq=1.0f, chroma=1.0f, hue_pos=0.0f, chroma_v=0.8f;
      int pal_mode=0, pal_idx=0, auto_shift=0, chromatic=1;
      std::sscanf(line + 1, "%f %f %f %f %d %d %d %f %f %d",
                  &mood, &sat, &sq, &chroma, &pal_mode, &pal_idx,
                  &auto_shift, &hue_pos, &chroma_v, &chromatic);
      rp.MOOD = mood; rp.SATURATION = sat; rp.SQUARE_ITER = sq; rp.CHROMA = chroma;
      rp.PALETTE_MODE_ENABLED = pal_mode != 0;
      rp.PALETTE_INDEX = (uint8_t)pal_idx;
      rp.AUTO_COLOR_SHIFT = auto_shift != 0;
      rp.hue_position = SQ15x16(hue_pos);
      rp.chroma_val   = SQ15x16(chroma_v);
      rp.chromatic_mode = chromatic != 0;
      hue_position  = SQ15x16(hue_pos);
      chroma_val    = SQ15x16(chroma_v);
      chromatic_mode = chromatic != 0;
      vp_render_secondary_channel = false;
    }
  }
  push_render_params(&rp);
  reset_all();

  unsigned char bytes[NATIVE_RESOLUTION * 3];
  unsigned long n = 0;
  HostFrame fr;

  // Active mode: 0=bloom, 1=spectrum_river
  int active_mode = 0;

  while (std::fgets(line, sizeof(line), stdin)) {
    if (line[0] == '\n' || line[0] == '\0') continue;

    // Mode-switch line: "M <name>"
    if (line[0] == 'M') {
      char mname[64] = {};
      std::sscanf(line + 1, "%63s", mname);
      if (std::strcmp(mname, "bloom") == 0)           active_mode = 0;
      else if (std::strcmp(mname, "spectrum_river") == 0) active_mode = 1;
      std::printf("MODE %s\n", mname);
      continue;
    }

    if (!parse_frame(line, fr)) continue;
    g_sb_host_millis = fr.ms;

    std::memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

    if (active_mode == 0) {
      // bloom: inject chromagram_smooth, call bloom_fast with its prev buffer
      for (int i = 0; i < 12; i++) chromagram_smooth[i] = SQ15x16(fr.chroma[i]);
      light_mode_bloom_fast(g_bloom_prev);
    } else {
      // spectrum_river: inject spectrogram_smooth, call with its prev buffer
      for (int i = 0; i < NUM_FREQS; i++) spectrogram_smooth[i] = SQ15x16(fr.spectro[i]);
      light_mode_spectrum_river(g_river_prev);
    }

    sb_render_host_dump(bytes);
    std::printf("R ");
    for (int i = 0; i < NATIVE_RESOLUTION * 3; i++) std::printf("%02x", bytes[i]);
    std::printf("\n");
    n++;
  }

  pop_render_params();
  std::printf("RENDER_DONE frames=%lu leds=%d\n", n, NATIVE_RESOLUTION);
  return 0;
}
"""

# ---------------------------------------------------------------------------
# Mutations — 4 real constants from distinct mechanisms.
# Each must produce output != the golden baseline (proven in __main__).
# ---------------------------------------------------------------------------
MUTATIONS = [
    (
        # 1. Bloom trail alpha: VP_BLOOM_ALPHA (globals.h inline, default 0.99f)
        #    controls how much history persists each frame via draw_sprite.
        #    Lowering it to 0.50f makes the trail fade aggressively — after 20
        #    frames accumulated brightness collapses, changing every bloom hex line.
        r"(VP_BLOOM_ALPHA\s*=\s*)0\.99f",
        r"\g<1>0.50f",
        "VP_BLOOM_ALPHA 0.99→0.50: bloom trail fades fast, accumulated pixels collapse",
    ),
    (
        # 2. Bloom shift scale: VP_BLOOM_SHIFT_SCALE multiplies the outward shift
        #    speed. Doubling it makes the bloom spread twice as fast per frame,
        #    changing LED positions of the transported history.
        r"(VP_BLOOM_SHIFT_SCALE\s*=\s*)1\.0f",
        r"\g<1>2.0f",
        "VP_BLOOM_SHIFT_SCALE 1.0→2.0: bloom spreads twice as fast, history positions change",
    ),
    (
        # 3. Spectrum river trail alpha: RIVER_TRAIL_ALPHA controls persistence of
        #    the flowing spectrum history. Lowering it to 0.50 makes the river fade
        #    very quickly, producing a much dimmer/emptier buffer.
        r"(RIVER_TRAIL_ALPHA\s*=\s*)0\.90f",
        r"\g<1>0.50f",
        "RIVER_TRAIL_ALPHA 0.90→0.50: river history fades fast, most LEDs near-black",
    ),
    (
        # 4. Spectrum river injection gain cap: RIVER_INJECT_GAIN caps each bin's
        #    additive contribution. Halving it cuts every injected spectral column
        #    brightness in half, propagating through all subsequent river frames.
        r"(RIVER_INJECT_GAIN\s*=\s*)0\.90f",
        r"\g<1>0.45f",
        "RIVER_INJECT_GAIN 0.90→0.45: spectrum injection brightness halved per bin",
    ),
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_compiler():
    for cand in _GPP_CANDIDATES:
        if shutil.which(cand):
            return cand
    return "g++"


def _build_driver_source():
    """Return the C++ driver source (the DRIVER string above)."""
    return DRIVER


def _compile(workdir: Path, firmware_root: Path) -> Path:
    """Write driver + compile; return Path to binary.  Raise RuntimeError on failure."""
    main_cpp = workdir / "oracle_render_driver.cpp"
    main_cpp.write_text(_build_driver_source(), encoding="utf-8")
    binary = workdir / "oracle_render"

    cc = _detect_compiler()

    sources = [str(firmware_root / s) for s in COMMON_SOURCES]
    sources += [str(firmware_root / s) for s in _MODE_SOURCES]
    sources += [str(HOST_GLOBALS), str(main_cpp)]

    defines_flags = [f"-D{d}" for d in DEFINES]

    compile_cmd = [
        cc, "-std=c++17",
        # -O0 for maximum determinism (no cross-platform float reassoc)
        "-O0",
        "-Wall", "-Wextra",
        "-Wno-unused-parameter", "-Wno-unused-variable", "-Wno-unused-function",
        *defines_flags,
        "-I", str(STUBS),
        "-I", str(FIXEDPOINTS),
        "-I", str(firmware_root),
        *[arg for d in FW_SUBDIRS for arg in ("-I", str(firmware_root / d))],
        *sources,
        "-o", str(binary),
    ]
    r = subprocess.run(compile_cmd, cwd=str(ROOT), text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError(
            f"oracle_render compile failed (rc={r.returncode}):\n"
            f"CMD: {' '.join(compile_cmd)}\n"
            f"STDERR:\n{r.stderr}\n"
            f"STDOUT:\n{r.stdout}"
        )
    return binary


def _make_stdin() -> str:
    """Build the deterministic stdin fed to the compiled driver.

    Fixed render params + 20 bloom frames (varied chromagram) + 20 spectrum_river
    frames (ramp spectrogram).  ms advances by 8 per frame (133 Hz → 7.5 ms,
    rounded to 8 for a clean integer clock with no millis-drift on host).
    """
    lines = []
    # Param line: mood=0.5 sat=0.9 sq=1.0 chroma=1.0 pal_mode=0 pal_idx=0
    #             auto_shift=0 hue_pos=0.0 chroma_v=0.8 chromatic=1
    lines.append("P 0.5 0.9 1.0 1.0 0 0 0 0.0 0.8 1")

    # --- bloom section (20 frames) ---
    lines.append("M bloom")
    for f in range(20):
        ms = f * 8
        # Chromagram: deterministic ramp based on frame index — wraps so every
        # bin gets a non-zero value (ensures the bloom actually lights the strip)
        chroma = [(((f + i) % 12) + 1) / 12.0 for i in range(12)]
        spectro = [0.0] * 80
        wf_peak = 0.5
        max_wf  = 0.4
        bass    = 1 if (f % 4 == 0) else 0
        bass_str = 0.7 if bass else 0.0
        sil     = 0
        chroma_str  = " ".join(f"{v:.6f}" for v in chroma)
        spectro_str = " ".join(f"{v:.6f}" for v in spectro)
        lines.append(
            f"F {ms} {chroma_str} {spectro_str} "
            f"{wf_peak:.6f} {max_wf:.6f} {bass} {bass_str:.6f} {sil}"
        )

    # --- spectrum_river section (20 frames) ---
    lines.append("M spectrum_river")
    for f in range(20):
        ms = (20 + f) * 8
        # Spectrogram: deterministic ramp across 80 bins, shifted by frame
        # index — all bins get meaningful energy so colour mutations are visible
        spectro = [((f + k) % 80 + 1) / 80.0 for k in range(80)]
        chroma  = [0.0] * 12
        wf_peak = 0.0
        max_wf  = 0.0
        bass    = 0
        bass_str = 0.0
        sil     = 0
        chroma_str  = " ".join(f"{v:.6f}" for v in chroma)
        spectro_str = " ".join(f"{v:.6f}" for v in spectro)
        lines.append(
            f"F {ms} {chroma_str} {spectro_str} "
            f"{wf_peak:.6f} {max_wf:.6f} {bass} {bass_str:.6f} {sil}"
        )

    return "\n".join(lines) + "\n"


def _run_driver(binary: Path) -> str:
    """Feed the deterministic stdin to the compiled binary and return stdout."""
    stdin_text = _make_stdin()
    r = subprocess.run(
        [str(binary)], cwd=str(ROOT), text=True, input=stdin_text,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"oracle_render runtime failed (rc={r.returncode}):\n"
            f"STDERR:\n{r.stderr}\nSTDOUT:\n{r.stdout}"
        )
    return r.stdout


def _parse_output(stdout: str) -> list:
    """Parse the 'R <hex>' lines + MODE switches into golden records.

    Each record:
      { "frame": int, "mode": str, "hex": str,
        "crc32": str,                       # 8-char hex of CRC32 over all 480 bytes
        "sampled_leds": [[r,g,b], ...] }    # 10 representative LED indices
    """
    records = []
    frame_global = 0
    current_mode = "unknown"
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("MODE "):
            current_mode = line[5:].strip()
        elif line.startswith("R "):
            hex_str = line[2:].strip()
            if len(hex_str) != LED_COUNT * 3 * 2:
                continue  # malformed
            raw = bytes.fromhex(hex_str)
            # CRC32 (using hashlib sha256 truncated to 32 bits for portability)
            crc = int(hashlib.sha256(raw).hexdigest(), 16) & 0xFFFFFFFF
            # 10 sampled LED indices spread across the strip (avoids black ends)
            sampled_indices = [8, 24, 40, 56, 72, 88, 104, 120, 136, 152]
            sampled = []
            for idx in sampled_indices:
                base = idx * 3
                sampled.append([raw[base], raw[base + 1], raw[base + 2]])
            records.append({
                "frame": frame_global,
                "mode": current_mode,
                "hex": hex_str,
                "crc32": f"{crc:08x}",
                "sampled_leds": sampled,
            })
            frame_global += 1
    return records


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def capture(firmware_root: Path = FIRMWARE) -> str:
    """Compile the render oracle driver and run it.

    Returns stdout as a newline-separated JSON string (one record per frame).
    Raises RuntimeError on compile or runtime failure.
    firmware_root may be overridden to point at a mutated firmware tree.
    """
    with tempfile.TemporaryDirectory(prefix="oracle_render_") as td:
        workdir = Path(td)
        binary  = _compile(workdir, firmware_root)
        stdout  = _run_driver(binary)
    records = _parse_output(stdout)
    if not records:
        raise RuntimeError(
            "oracle_render produced 0 records — driver may have failed silently.\n"
            f"Raw stdout:\n{stdout}"
        )
    return "\n".join(json.dumps(rec, sort_keys=True) for rec in records)


# ---------------------------------------------------------------------------
# __main__: prove determinism and each mutation diverges
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys as _sys

    print("oracle_render — determinism + mutation verification")
    print(f"  Firmware root : {FIRMWARE}")
    print(f"  LED_COUNT     : {LED_COUNT}")
    print(f"  Modes         : bloom (20 frames) + spectrum_river (20 frames)")
    print()

    # ---- determinism check -----------------------------------------------
    print("[1/2] Determinism: capture() twice → byte-identical")
    try:
        out1 = capture()
        out2 = capture()
    except RuntimeError as e:
        print(f"  BLOCKED: {e}")
        _sys.exit(1)

    records1 = [json.loads(l) for l in out1.splitlines() if l.strip()]
    records2 = [json.loads(l) for l in out2.splitlines() if l.strip()]

    if out1 != out2:
        print(f"  FAIL: outputs differ (run1={len(records1)} records, run2={len(records2)} records)")
        _sys.exit(1)
    print(f"  PASS: {len(records1)} records, byte-identical across two runs")
    print()

    # Mode breakdown
    bloom_recs  = [r for r in records1 if r["mode"] == "bloom"]
    river_recs  = [r for r in records1 if r["mode"] == "spectrum_river"]
    print(f"  bloom frames         : {len(bloom_recs)}")
    print(f"  spectrum_river frames: {len(river_recs)}")

    # Verify non-trivial output (sensitivity pre-check: at least some LEDs lit)
    all_nonzero = sum(
        1 for r in records1
        for rgb in r["sampled_leds"]
        if any(v > 0 for v in rgb)
    )
    print(f"  Non-zero sampled LEDs: {all_nonzero} / {len(records1) * 10}")
    if all_nonzero == 0:
        print("  WARNING: all sampled LEDs are black — mutations may not diverge!")
    print()

    # ---- mutation checks --------------------------------------------------
    print("[2/2] Mutations: each must diverge vs. baseline")
    baseline_hex = "\n".join(r["hex"] for r in records1)

    all_passed = True
    for idx, (pattern, replacement, description) in enumerate(MUTATIONS, 1):
        print(f"  Mutation {idx}: {description}")
        # Copy firmware tree to a temp dir, apply the mutation, recompile
        with tempfile.TemporaryDirectory(prefix=f"oracle_render_mut{idx}_") as td:
            fw_copy = Path(td) / "fw"
            shutil.copytree(str(FIRMWARE), str(fw_copy))

            # Find and patch the file containing the pattern
            patched = False
            for root_dir, dirs, files in os.walk(str(fw_copy)):
                for fname in files:
                    if not (fname.endswith(".cpp") or fname.endswith(".h")):
                        continue
                    fpath = Path(root_dir) / fname
                    try:
                        text = fpath.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    new_text, n = re.subn(pattern, replacement, text)
                    if n > 0:
                        fpath.write_text(new_text, encoding="utf-8")
                        print(f"    Patched: {fpath.relative_to(fw_copy)} ({n} replacement(s))")
                        patched = True

            if not patched:
                print(f"    WARN: pattern not found in firmware tree — mutation may be stale")
                print(f"      pattern: {pattern!r}")
                all_passed = False
                continue

            try:
                mut_out = capture(firmware_root=fw_copy)
            except RuntimeError as e:
                print(f"    BLOCKED (compile/run error): {e}")
                all_passed = False
                continue

        mut_records = [json.loads(l) for l in mut_out.splitlines() if l.strip()]
        mut_hex     = "\n".join(r["hex"] for r in mut_records)

        if mut_hex == baseline_hex:
            print(f"    FAIL: output identical to baseline (mutation has no effect)")
            all_passed = False
        else:
            # Count diverging frame lines for reporting
            base_lines = baseline_hex.splitlines()
            mut_lines  = mut_hex.splitlines()
            diverged = sum(
                1 for b, m in zip(base_lines, mut_lines) if b != m
            )
            print(f"    PASS: {diverged}/{len(base_lines)} frame hex lines diverged")

    print()
    if all_passed:
        print("oracle_render: ALL CHECKS PASSED")
        print(f"  Golden records : {len(records1)}")
        print(f"  Determinism    : PASS (byte-identical)")
        print(f"  Mutations      : {len(MUTATIONS)}/{len(MUTATIONS)} diverge")
    else:
        print("oracle_render: SOME CHECKS FAILED — review output above")
        _sys.exit(1)
