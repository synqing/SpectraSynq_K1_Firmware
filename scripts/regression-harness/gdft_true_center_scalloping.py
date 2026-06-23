"""Host reproduction of the K1_GDFT_TRUE_CENTER_V1 device A/B — root-cause sim.

Measurement-only. Replicates the EXACT firmware fixed-point Goertzel (GDFT.h
process_GDFT, K1_SPECTRAL_WINDOW_V1 OFF path) and the synthetic-sine harness
(gdft_harness.h) on the host, so the device argmax can be reproduced WITHOUT a
device. Purpose: confirm that the only cause of the true-centre A/B anomaly is the
coefficient (integer-k vs non-integer-k), and exhibit the scalloping mechanism.

Device A/B (bench K1 B489A500, 2026-06-21):
  OFF (rounded-k):   440 Hz -> bin 26, 415.3 -> bin 24, 420 -> bin 24
  ON  (true-centre): 440 -> bin 24 (PASS) BUT 415.3 -> bin 26 (FAIL, weak),
                     and an ON sweep had 405/410/466 -> above-Nyquist alias bin 78.

RESULT (2026-06-21): this host replica CONTRADICTS the device and REFUTES the two
mechanistic hypotheses it was built to test:
  * Phase-scalloping: REFUTED. Under ON the per-bin response peaks correctly at the
    tuned frequency (bin 23 @415.3 -> mag ~252, a clean win), not a null.
  * int32-overflow-at-resonance: REFUTED. Although q1^2+q2^2 exceeds INT32_MAX at
    resonance (~5e10), the final magnitude q1^2+q2^2-coeff*q1*q2 is CONGRUENT mod
    2^32 to the true value (~1.06e9, which fits int32) -> no net corruption
    (goertzel_debug: raw_mag2 == wrapped_mag2).
The host predicts true-centre LARGELY WORKS (415.3->bin 23 clean); the device showed
it failing (415.3->bin 26 collapse, alias bin 78 winning for 405/410/466). The host
also cannot reproduce device OFF 440->bin 26 (gets bin 25): adjacent-bin magnitudes
are within ~2%, so the sim's tiny float/fixed-point infidelities flip the exact
argmax and it CANNOT adjudicate the device result. ROOT CAUSE IS UNRESOLVED; the
device-vs-host contradiction needs on-device top-5/neighbour telemetry to settle.
Do NOT cite this as evidence that true-centre is "confirmed-negative" OR a clean win.

Firmware arithmetic mirrored (GDFT.h:86-139):
  coeff_q14 = (int32)((float32)16384 * (float32)(2*cos(w)))   # trunc toward zero
  loop n in [0,block_size): sample=sample_window[4095-n] (int32)
      mult = (int64) coeff_q14 * q1
      q0   = (int32)((sample>>6) + (mult>>14) - q2)
  mult = (int64) coeff_q14 * q1
  mag  = (int32)( q2*q2 + q1*q1 - (int32)(mult>>14)*q2 )   # int32 ops, may wrap
  if mag<0: mag=0 ; mag = sqrtf(mag)
  magnitudes_normalized = mag * inv_block_size_half   # inv = 2/block_size
Harness fill (gdft_harness.h:128-135): full 4096-sample window,
  sample_window[i] = lroundf( 16000 * sinf( ((2*PI*f)/fs) * (float)i ) )   # float32
"""

import importlib.util
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "scripts" / "regression-harness" / "gdft_center_honesty_model.py"

_spec = importlib.util.spec_from_file_location("gdft_center_honesty_model", MODEL_PATH)
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

FS = model.SAMPLE_RATE                 # 12800
NUM_FREQS = model.NUM_FREQS            # 80
NYQUIST = FS / 2.0                     # 6400
SAMPLE_HISTORY_LENGTH = 4096           # constants.h
AMP = 16000.0                          # GDFT_HARNESS_AMP

_BINS = model.compute_bins()           # block_size / target / above-Nyquist per bin


def _s32(x):
    return ((int(x) + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def _s64(x):
    return ((int(x) + (1 << 63)) & ((1 << 64) - 1)) - (1 << 63)


def _coeff_q14(target, block_size, above_nyquist, mode):
    """Mirror precompute_goertzel_constants(): integer Q14 coefficient.
    mode='off' -> rounded k. mode='on' -> exact target for representable bins,
    rounded k above Nyquist (the firmware ON path)."""
    if mode == "on" and not above_nyquist:
        w = (2.0 * math.pi * target) / FS                  # double
    else:
        k = int(0.5 + (block_size * target) / FS)          # (int) trunc toward zero
        w = (2.0 * math.pi * k) / block_size
    cosine = np.float32(math.cos(w))                       # float cosine = cos(w)
    coeff = np.float32(2.0 * float(cosine))                # float coeff = 2*cosine
    cq = np.float32(np.float32(16384.0) * coeff)           # (1<<14)*coeff in float32
    return int(cq)                                         # -> int32, trunc toward zero


def fill_sine_int16(f):
    """gdft_harness_fill_sine: full 4096 window, float32 sinf, lroundf -> int16."""
    w32 = np.float32((2.0 * math.pi * f) / FS)
    i = np.arange(SAMPLE_HISTORY_LENGTH, dtype=np.float32)
    s = np.float32(AMP) * np.sin(w32 * i, dtype=np.float32)
    # lroundf rounds half AWAY from zero (np.rint is half-to-even) -> emulate:
    rounded = np.sign(s) * np.floor(np.abs(s) + np.float32(0.5))
    return rounded.astype(np.int64)


def _goertzel_norm(sw, block_size, coeff_q14, inv_block_size_half):
    """Bit-faithful replica of the GDFT.h inner loop (window OFF)."""
    q1 = 0
    q2 = 0
    idx = SAMPLE_HISTORY_LENGTH - 1
    for _ in range(block_size):
        sample = int(sw[idx]); idx -= 1
        mult = _s64(coeff_q14 * q1)
        q0 = _s32((sample >> 6) + (mult >> 14) - q2)
        q2 = q1
        q1 = q0
    mult = _s64(coeff_q14 * q1)
    a = _s32(q2 * q2)
    b = _s32(q1 * q1)
    c = _s32(_s32(mult >> 14) * q2)
    mag = _s32(_s32(a + b) - c)
    if mag < 0:
        mag = 0
    magf = math.sqrt(mag)                       # sqrtf
    return magf * inv_block_size_half           # magnitudes_normalized


def magnitude2_int32_legacy(q1, q2, coeff_q14):
    """Replica of the legacy int32 magnitude-squared (GDFT.h #else, pre-sqrt, clamped):
        mult = coeff_q14 * (int32_t)q1;                  // int32 multiply (can wrap)
        m = q2*q2 + q1*q1 - ((int32_t)(mult>>14))*q2;     // all int32 ops (can wrap)
        if (m < 0) m = 0;
    Every operation wraps to int32 exactly as C does."""
    mult = _s32(coeff_q14 * q1)                           # coeff_q14*(int32)q1 in int32
    cross = _s32(_s32(mult >> 14) * q2)                   # ((int32)(mult>>14))*q2 in int32
    m = _s32(_s32(_s32(q2 * q2) + _s32(q1 * q1)) - cross)
    return 0 if m < 0 else m


def magnitude2_int64(q1, q2, coeff_q14):
    """Replica of the int64 magnitude-squared (GDFT.h #if K1_GDFT_INT64_MAGNITUDE_V1):
        coeff_term = ((int64)coeff_q14 * (int64)q1) >> 14;
        mag2 = (int64)q2*q2 + (int64)q1*q1 - coeff_term*(int64)q2;
        if (mag2 < 0) mag2 = 0;
    int64 holds q*q (~2.6e10) without overflow, so no wrap."""
    coeff_term = _s64(coeff_q14 * q1) >> 14
    mag2 = _s64((q2 * q2) + (q1 * q1) - (coeff_term * q2))
    return 0 if mag2 < 0 else mag2


def magnitude2_true(q1, q2, coeff_q14):
    """Full-precision reference (unbounded ints): q2^2 + q1^2 - ((coeff_q14*q1)>>14)*q2,
    clamped at 0. The int64 path should equal this for device-scale q (no >2^63 risk)."""
    m = q2 * q2 + q1 * q1 - ((coeff_q14 * q1) >> 14) * q2
    return 0 if m < 0 else m


def recurrence_mult_int32_legacy(coeff_q14, q1):
    """Legacy GDFT.h recurrence multiply: coeff_q14 * (int32_t)q1 computed in int32
    (wraps) before the int64 store -> overflows once coeff_q14*q1 > INT32_MAX."""
    return _s32(coeff_q14 * q1)


def recurrence_mult_int64(coeff_q14, q1):
    """ON path: (int64_t)coeff_q14 * (int64_t)q1 — full int64 product, no int32 wrap."""
    return _s64(coeff_q14 * q1)


def recurrence_mult_true(coeff_q14, q1):
    """Full-precision reference product."""
    return coeff_q14 * q1


def recurrence_max_abs_q0(f, bin_index, mode):
    """Max |q0| (pre int32-truncation) over the Goertzel loop for tone f at a bin,
    using the int64 recurrence multiply (K1_GDFT_INT64_RECURRENCE_V1 behaviour).
    q-STATE q0/q1/q2 stays int32; if this exceeds INT32_MAX the q range itself
    overflows and a SEPARATE wider-q pass is required."""
    b = _BINS[bin_index]
    bs = b["block_size"]
    cq = _coeff_q14(b["target_hz"], bs, b["target_above_nyquist"], mode)
    sw = fill_sine_int16(f)
    q1 = 0
    q2 = 0
    idx = SAMPLE_HISTORY_LENGTH - 1
    max_abs = 0
    for _ in range(bs):
        sample = int(sw[idx]); idx -= 1
        mult = _s64(cq * q1)                          # int64 product (no int32 wrap)
        q0_64 = (sample >> 6) + (mult >> 14) - q2     # pre-truncation int64
        if abs(q0_64) > max_abs:
            max_abs = abs(q0_64)
        q0 = _s32(q0_64)                              # q-state is int32
        q2 = q1
        q1 = q0
    return max_abs


def goertzel_debug(f, bin_index, mode):
    """Expose the raw (unbounded) vs int32-wrapped magnitude accumulator for one
    bin/tone, to test the int32-overflow-at-resonance hypothesis."""
    b = _BINS[bin_index]
    bs = b["block_size"]
    cq = _coeff_q14(b["target_hz"], bs, b["target_above_nyquist"], mode)
    sw = fill_sine_int16(f)
    q1 = 0
    q2 = 0
    idx = SAMPLE_HISTORY_LENGTH - 1
    qmax = 0
    for _ in range(bs):
        sample = int(sw[idx]); idx -= 1
        mult = _s64(cq * q1)
        q0 = _s32((sample >> 6) + (mult >> 14) - q2)
        q2 = q1
        q1 = q0
        qmax = max(qmax, abs(q1))
    mult = _s64(cq * q1)
    raw = q2 * q2 + q1 * q1 - (_s32(mult >> 14)) * q2          # true integer (no wrap)
    wrapped = _s32(_s32(_s32(q2 * q2) + _s32(q1 * q1)) - _s32(_s32(mult >> 14) * q2))
    INT32_MAX = 0x7FFFFFFF
    return {
        "bin": bin_index, "tone": f, "mode": mode, "block_size": bs,
        "q1": q1, "q2": q2, "qmax": qmax,
        "q1sq_plus_q2sq": q2 * q2 + q1 * q1,
        "over_int32": (q2 * q2 + q1 * q1) > INT32_MAX,
        "raw_mag2": raw, "wrapped_mag2": wrapped,
        "overflow_changed_result": raw != wrapped,
    }


def magnitudes_normalized(f, mode):
    """All-bin magnitudes_normalized[] for a synthetic tone f, like one process_GDFT()."""
    sw = fill_sine_int16(f)
    out = np.empty(NUM_FREQS, dtype=np.float64)
    for b in _BINS:
        i = b["bin"]
        bs = b["block_size"]
        cq = _coeff_q14(b["target_hz"], bs, b["target_above_nyquist"], mode)
        inv = 2.0 / bs
        out[i] = _goertzel_norm(sw, bs, cq, inv)
    return out


def argmax_bin(f, mode):
    """The harness argmax over magnitudes_normalized[] -> the bin the device reports."""
    mags = magnitudes_normalized(f, mode)
    i = int(np.argmax(mags))
    return i, float(mags[i])


def bin_response_curve(bin_index, freqs, mode):
    """magnitudes_normalized[bin_index] as the input tone sweeps -> shows scalloping."""
    return [magnitudes_normalized(f, mode)[bin_index] for f in freqs]


if __name__ == "__main__":
    # Reproduce the device A/B table.
    print(f"fs={FS} Nyquist={NYQUIST:.0f}  (bin23={_BINS[23]['target_hz']:.2f} "
          f"bin24={_BINS[24]['target_hz']:.2f} bin25={_BINS[25]['target_hz']:.2f} "
          f"bin26={_BINS[26]['target_hz']:.2f})")
    print("\n  tone   OFF(host)            ON(host)")
    for f in (400.0, 405.0, 410.0, 415.3, 420.0, 425.0, 430.0, 440.0, 450.0, 466.0, 480.0, 494.0):
        ob, om = argmax_bin(f, "off")
        nb, nm = argmax_bin(f, "on")
        print(f"  {f:>6} bin {ob:>2} (mag {om:7.1f})   bin {nb:>2} (mag {nm:7.1f})")

    # Scalloping: bin 23 (true-centre tuned to 415.30) response to a fine sweep.
    print("\nbin 23 response (tuned 415.30 Hz), ON true-centre — note the null AT 415.3:")
    fine = [405, 410, 413, 415.3, 417, 420, 425, 430]
    onc = bin_response_curve(23, fine, "on")
    offc = bin_response_curve(23, fine, "off")
    for f, a, b in zip(fine, onc, offc):
        print(f"  {f:>6} Hz  ON {a:8.1f}   OFF {b:8.1f}")
