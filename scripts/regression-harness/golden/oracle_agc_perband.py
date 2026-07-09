#!/usr/bin/env python3
"""Characterisation oracle for the broadband-vs-per-band AGC gain behaviour.

Lane N6 (perceptual finalize), Class C — PREPARE ONLY. This is NOT a frozen
golden-master oracle (it is deliberately absent from harness_selftest.ORACLE_MODULES
so it never touches tests/golden/ or the MANIFEST). It is a *property /
characterisation* harness: it host-compiles the REAL firmware
audio/k1_gdft_core.cpp twice — once with the production broadband AGC (flag OFF)
and once with the candidate per-band AGC (-DK1_AGC_PERBAND_V1, flag ON) — drives
both with the SAME deterministic two-tone stimulus, and emits per-band AGC gains
plus per-band post-AGC output so a test can assert the "louder -> dimmer" defect
(OFF) and its fix (ON).

The defect (grounded — eyes-on-verdict.md 2026-06-21, spike obs #72837):
k1_gdft_core.cpp computes ONE global agc_gain = effective_target/(agc_envelope+EPS)
and applies that single scalar to EVERY bin. Loud broadband energy collapses the
single gain and dims the whole field, including quiet tonal detail in other bands.

Stimulus: a CONSTANT moderate treble tone (4000 Hz, BAND_TREBLE) plus a bass tone
(100 Hz, BAND_BASS) whose amplitude RAMPS from silence to loud. As the bass gets
louder:
  - OFF (single scalar): the one global gain collapses -> the treble tonal output
    dims even though the treble content never changed  (the "louder -> dimmer"
    inverse).
  - ON  (per-band): only the bass band's gain collapses; the treble band keeps its
    gain -> the treble tonal output is retained.

Compile machinery is inherited from oracle_gdft.py (same TU, same substrate) so
the two stay in lockstep. NON-SHIPPING. Host-only.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Inherit the proven compile substrate (single source of truth for how
# k1_gdft_core.cpp is host-compiled).
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import oracle_gdft as _g  # noqa: E402

NAME = "agc_perband"

# Production-matching defines (same audio contract as oracle_gdft). The per-band
# candidate flag is appended per-capture, never baked here.
BASE_DEFINES = list(_g.DEFINES)
PERBAND_DEFINE = "K1_AGC_PERBAND_V1"

# ---------------------------------------------------------------------------
# C++ driver. Self-contained: the 5 cross-TU cal/flash no-op stubs, a VERBATIM
# lift of precompute_goertzel_constants() (int32 path) + the spectral-tilt LUT
# init + the freq_to_band_map init (all three are boot-time inits the host cannot
# run from system.h). Emits one JSON record per frame:
#   {"f":int, "bass":float,                # relative bass drive 0..1
#    "g":[g0,g1,g2,g3],                    # per-band agc gains (agc_bands[b].gain)
#    "o":[o0,o1,o2,o3]}                    # per-band mean post-AGC output (spectrogram)
# bands: 0=BASS 1=LOW_MID 2=HIGH_MID 3=TREBLE.
# ---------------------------------------------------------------------------
DRIVER = r"""
#include "globals.h"
#include "constants.h"
#include "k1_gdft_core.h"
#include "k1_spectral_honesty.h"   // k1_hann_window_mult

#include <cstdio>
#include <cmath>

// --- host no-op stubs for the cross-TU cal/flash symbols (never executed) ----
void clear_spectral_noise_samples() {}
void noise_cal_restore_previous_or_invalidate() {}
void save_config() {}
void save_ambient_noise_calibration() {}
bool save_calibration_profile(uint8_t) { return true; }

// --- VERBATIM lift of precompute_goertzel_constants() int32 path -------------
// (statement-identical to system.h non-true-centre #else; identical to oracle_gdft)
static void host_precompute_goertzel_constants() {
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    int16_t n = i;
    frequencies[i].target_freq = notes[n + CONFIG.NOTE_OFFSET];
    float neighbor_left, neighbor_right;
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
    float nld = fabs(neighbor_left - frequencies[i].target_freq);
    float nrd = fabs(neighbor_right - frequencies[i].target_freq);
    float max_distance_hz = 0;
    if (nld > max_distance_hz) max_distance_hz = nld;
    if (nrd > max_distance_hz) max_distance_hz = nrd;
    frequencies[i].block_size = CONFIG.SAMPLE_RATE / (max_distance_hz * 2.0);
    if (frequencies[i].block_size > 2000) frequencies[i].block_size = 2000;
    if (frequencies[i].block_size > 0)
      frequencies[i].inv_block_size_half = 2.0 / frequencies[i].block_size;
    else
      frequencies[i].inv_block_size_half = 0.0;
    frequencies[i].block_size_recip = 1.0 / float(frequencies[i].block_size);
    float k = (int)(0.5 + ((frequencies[i].block_size * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE));
    float w = (2.0 * PI * k) / frequencies[i].block_size;
    frequencies[i].coeff_q14 = (1 << 14) * (2.0 * cos(w));
    frequencies[i].window_mult = k1_hann_window_mult(frequencies[i].block_size);
  }
}

// --- VERBATIM lift of init_cochlear_agc()'s freq_to_band_map + tilt LUT -------
// Source: system.h:570-646. The host cannot run system.h; reconstruct the two
// boot-time inits the AGC needs. Statement-identical to the source loops.
static void host_init_agc_state() {
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    float freq = frequencies[i].target_freq;
    if (freq < BAND_BASS_HIGH)          freq_to_band_map[i] = BAND_BASS;
    else if (freq < BAND_LOW_MID_HIGH)  freq_to_band_map[i] = BAND_LOW_MID;
    else if (freq < BAND_HIGH_MID_HIGH) freq_to_band_map[i] = BAND_HIGH_MID;
    else                                freq_to_band_map[i] = BAND_TREBLE;

    float tilt;
    if (freq < 200.0f)        tilt = 1.30f;
    else if (freq > 3000.0f)  tilt = 0.85f;
    else                       tilt = 1.00f;
    spectral_tilt_lut[i] = SQ15x16(tilt);
  }
  agc_envelope = SQ15x16(0.0);
  agc_noise_floor = SQ15x16(0.001);
  agc_gated = true;
}

int main() {
  CONFIG.SAMPLE_RATE = 12800;
  CONFIG.NOTE_OFFSET = 12;
  CONFIG.MOOD = 0.5f;
  CONFIG.LIGHTSHOW_MODE = 0;
  host_precompute_goertzel_constants();
  host_init_agc_state();
  noise_complete = true;

  // Stimulus = loud BROADBAND energy (BASS+LOW_MID+HIGH_MID tones, RAMPING from
  // silence to loud) + a sparse, QUIET, CONSTANT tonal peak in the TREBLE band.
  // This is the eyes-on failure shape: a loud full-low/mid field that should NOT
  // be allowed to crush the isolated quiet treble detail.
  const int    WARMUP    = 6;       // all tones present; let envelopes settle
  const int    RAMP      = 30;      // broadband ramps silence -> loud
  const int    TOTAL     = WARMUP + RAMP;
  const double wb1       = 2.0 * M_PI *  100.0 / 12800.0;  // BAND_BASS
  const double wb2       = 2.0 * M_PI *  420.0 / 12800.0;  // BAND_LOW_MID
  const double wb3       = 2.0 * M_PI * 1500.0 / 12800.0;  // BAND_HIGH_MID
  const double wt        = 2.0 * M_PI * 5000.0 / 12800.0;  // BAND_TREBLE (tonal peak)
  const double BROAD_MAX = 5000.0;  // per broadband tone at full loudness
  const double TONAL_AMP = 1200.0;  // constant quiet treble peak

  for (int f = 0; f < TOTAL; f++) {
    const double load = (f < WARMUP) ? 0.0
                      : (double)(f - WARMUP + 1) / (double)RAMP;
    const double broad = load * BROAD_MAX;
    const long base = (long)f * 96;
    for (int s = SAMPLE_HISTORY_LENGTH - 1; s >= 0; s--) {
      double t = (double)(base + (SAMPLE_HISTORY_LENGTH - 1 - s));
      double v = broad * (sin(wb1 * t) + sin(wb2 * t) + sin(wb3 * t))
               + TONAL_AMP * sin(wt * t);
      if (v >  32767.0) v =  32767.0;
      if (v < -32768.0) v = -32768.0;
      sample_window[s] = (short)v;
    }

    process_GDFT();
    calculate_novelty((uint32_t)f);

    // Per-band mean post-AGC output from the real spectrogram[].
    double osum[NUM_AGC_BANDS] = {0,0,0,0};
    int    ocnt[NUM_AGC_BANDS] = {0,0,0,0};
    for (uint16_t i = 0; i < NUM_FREQS; i++) {
      uint8_t b = freq_to_band_map[i];
      osum[b] += (double)(float)spectrogram[i];
      ocnt[b] += 1;
    }

    std::printf("{\"f\":%d,\"load\":\"%.4f\",\"g\":[", f, load);
    for (int b = 0; b < NUM_AGC_BANDS; b++)
      std::printf("%s\"%.5f\"", (b ? "," : ""), (float)agc_bands[b].gain);
    std::printf("],\"e\":[");
    for (int b = 0; b < NUM_AGC_BANDS; b++)
      std::printf("%s\"%.5f\"", (b ? "," : ""), (float)agc_bands[b].energy);
    std::printf("],\"o\":[");
    for (int b = 0; b < NUM_AGC_BANDS; b++) {
      double mean = ocnt[b] ? (osum[b] / ocnt[b]) : 0.0;
      std::printf("%s\"%.5f\"", (b ? "," : ""), mean);
    }
    std::printf("]}\n");
  }
  return 0;
}
"""


def _compile(workdir: Path, perband: bool) -> Path:
    fw = _g.FIRMWARE
    main_cpp = workdir / "oracle_agc_perband_driver.cpp"
    main_cpp.write_text(DRIVER, encoding="utf-8")
    binary = workdir / "oracle_agc_perband_bin"

    cc = _g._detect_compiler()
    defines = list(BASE_DEFINES) + ([PERBAND_DEFINE] if perband else [])

    sources = [str(fw / s) for s in _g.COMMON_SOURCES]
    sources += [str(_g.HOST_GLOBALS)]
    sources += [str(fw / s) for s in _g.MODULE_CPPS]
    sources += [str(main_cpp)]

    cmd = [
        cc, "-std=c++17", "-O0", "-fno-fast-math",
        "-Wno-unused-parameter", "-Wno-unused-variable", "-Wno-unused-function",
        *[f"-D{d}" for d in defines],
        "-I", str(_g.STUBS),
        "-I", str(_g.FIXEDPOINTS),
        "-I", str(fw),
        *[arg for d in _g.FW_SUBDIRS for arg in ("-I", str(fw / d))],
        *sources,
        "-o", str(binary),
    ]
    r = subprocess.run(cmd, cwd=str(_g.ROOT), text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"oracle_agc_perband compile failed (perband={perband}, rc={r.returncode}):\n"
            f"CMD: {' '.join(cmd)}\nSTDERR:\n{r.stderr}\nSTDOUT:\n{r.stdout}"
        )
    return binary


def _run(binary: Path) -> str:
    r = subprocess.run([str(binary)], cwd=str(_g.ROOT), text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"oracle_agc_perband run failed (rc={r.returncode}):\n{r.stderr}")
    return r.stdout


def capture(perband: bool = False, firmware_root=None) -> str:
    """Compile + run the AGC characterisation driver. perband toggles the flag."""
    with tempfile.TemporaryDirectory(prefix="oracle_agc_perband_") as td:
        binary = _compile(Path(td), perband=perband)
        return _run(binary)


def frames(perband: bool = False) -> list:
    """Parsed per-frame records. Floats kept as strings in JSON -> cast here."""
    out = []
    for line in capture(perband=perband).splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        out.append({
            "f": int(d["f"]),
            "load": float(d["load"]),
            "g": [float(x) for x in d["g"]],
            "e": [float(x) for x in d["e"]],
            "o": [float(x) for x in d["o"]],
        })
    return out


if __name__ == "__main__":
    off = frames(perband=False)
    on = frames(perband=True)
    BASS, TREBLE = 0, 3
    last = off[-1]
    print(f"# OFF last frame: load={last['load']:.2f} "
          f"gains={['%.3f' % x for x in last['g']]} "
          f"out={['%.4f' % x for x in last['o']]}", file=sys.stderr)
    lon = on[-1]
    print(f"# ON  last frame: load={lon['load']:.2f} "
          f"gains={['%.3f' % x for x in lon['g']]} "
          f"out={['%.4f' % x for x in lon['o']]}", file=sys.stderr)
    print(f"# OFF gain spread (max-min) @loud = {max(last['g'])-min(last['g']):.4f}",
          file=sys.stderr)
    print(f"# ON  gain spread (max-min) @loud = {max(lon['g'])-min(lon['g']):.4f}",
          file=sys.stderr)
