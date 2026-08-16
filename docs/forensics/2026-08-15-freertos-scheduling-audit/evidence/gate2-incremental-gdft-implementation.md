# Gate 2 hop-incremental GDFT implementation verdict

Date: 2026-08-15
Task: FRTOS-26
Inspected checkpoint: `2c0db532`
Disposition: **RED — candidate removed; direct cross0 backend retained**

## Decision

```text
K1_GDFT_HOP_INCREMENTAL_PROBE       = REJECT
PRODUCTION_GDFT_PATH                = UNCHANGED
CURRENT_CROSSOVER                   = KEEP_0
ONE_CODE_ARBITRARY_INPUT_PARITY     = FAIL
IMPULSE_WINNER_PARITY               = FAIL
DEVICE_UPLOAD                       = NOT_RUN
GATE_3                              = STILL_BLOCKED_BY_GATE_2
```

The smallest sliding candidate was implemented behind one non-shippable flag,
host-differenced against the current corrected direct recurrence, compiled for
the B489A500 bench environment, and then removed when the frozen numerical stop
rule fired. No production flag, task, priority, hop, rate, window, coefficient,
safe-bin or publication change remains.

## Why exact equivalence is unavailable

The direct backend resets `q1/q2` for every bin and frame, then applies:

```text
q0 = (sample >> 6) + ((coeff_q14 * q1) >> 14) - q2
```

at every sample. The arithmetic right shift discards a state-dependent remainder
on every recurrence step. The transform is therefore not linear over the input
window: a previous output state cannot be decomposed into independently removable
expiring-sample and addable entering-sample contributions with arbitrary-input
one-code equivalence.

The rounded Q14 coefficient adds a second mismatch. A sliding complex rotation
derived from `coeff_q14 / 32768` does not generally satisfy the integer-bin
root-of-unity property over the existing block size. Using the labelled rounded-k
angle instead would preserve phase closure but cease to represent the actual Q14
coefficient. If `K1_SPECTRAL_WINDOW_V1` were enabled, every retained sample would
also change its age-dependent Hann weight on every hop, requiring `O(N-H)`
reweighting. Production currently keeps that branch off, but the probe correctly
refused it rather than silently weakening the contract.

## Candidate exercised

The temporary candidate retained the exact cross0 block sizes, all 71 safe bins,
the 80-bin output canvas, 96 entering samples, 96 corresponding expiring samples
for every long-window bin, direct recomputation for windows `<=96`, one staged
whole-spectrum commit, and fixed static state. It added no task, mutex, queue,
heap, priority, hop or rate change.

The first/config/discontinuity frame used the exact corrected direct recurrence
as a visible reseed output. Sequence gaps, duplicate sequences, short/error
captures, coefficient/window/config changes, explicit reset and numeric bounds
all invalidated private state and incremented counters. This machinery proved
the proposed ownership/fault model was implementable, but it could not repair
the numerical non-equivalence.

The source-derived work opportunity count was reproduced exactly:

```text
direct cross0 recurrence steps on reseed = 34254
hybrid opportunities per next frame      = 6134
long-bin entering samples                 = 5088
long-bin expiring samples                 = 5088
```

## Differential result

The host driver fed identical full histories and capture sequences to the real
direct-reference arithmetic and the temporary sliding backend.

| Fixture | Frames | Compared frames | Maximum raw-magnitude error | Winner mismatches |
|---|---:|---:|---:|---:|
| silence | 12 | 12 | 0 | 0 |
| impulse | 24 | 24 | 18 | 15 |
| deterministic broadband | 48 | 48 | 30 | 0 |
| 440 Hz tone | 48 | 48 | 22 | 0 |
| loud rounded-centre resonance | 48 | 48 | 29 | 0 |
| long tone/noise drift | 1,200 | 61 sampled comparisons | 27 | 0 |

The allowed boundary was no looser than one downstream spectral code with stable
safe-bin winner/ordering. Five non-silent fixture classes exceeded it, and the
impulse fixture changed the winning bin on 15 of 24 frames. This is a semantic
failure, not an optimisation shortfall. Loud resonance remained finite, but
overflow safety alone cannot admit a spectrally different backend.

The fault exercise also reconciled two sequence discontinuities, one duplicate,
one capture fault, one configuration change, one explicit reset, one direct
fault fallback and zero partial publications. Those green ownership checks do
not override the RED numerical result.

## Commands and validation

```bash
python3 -m pytest -q tests/test_scheduling_gdft_incremental_probe.py
# 4 passed in 0.68s

pio run -e k1_bench_scheduling_gdft_incremental_probe
# firmware.elf produced for the non-shippable candidate
```

The focused test intentionally passed only when the differential exposed the
known non-equivalence and every fault remained visible. The candidate build was
compile/link proof, not product admission. Nothing was uploaded.

## Boundary and next legal decision

FRTOS-26 does not prove that every possible incremental spectral algorithm is
impossible. It proves that the contained hop/sliding decomposition permitted by
the current Gate-2 contract cannot preserve this particular per-step-truncated
direct Goertzel mapping within one code on the required fixtures.

Per the pre-registered stop rule, the candidate was removed instead of relaxing
window length, bin count, input samples, publication rate or event acceptance.
The next legal path is an explicit Gate-0 product/feature contract decision about
changing the spectral arithmetic, cadence or acceptance surface. Priority,
Core-1 DSP, a larger hop, partial spectra and GDFT stage actors remain rejected.
