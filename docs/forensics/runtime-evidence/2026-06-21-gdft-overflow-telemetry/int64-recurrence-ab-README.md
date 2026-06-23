---
abstract: "Device A/B (bench K1 B489A500, 12201) of K1_GDFT_INT64_RECURRENCE_V1 (the 2nd of the two fixed-point overflows). Leg A baseline collapse (440: bin24/25=0.00). Leg B (mag only) removes clamps but magnitudes are overflow-inflated (~6500) and rounded-k offset persists. Leg C (mag+rec, rounded-k) magnitudes drop to ~245 MATCHING the host replica to <1%, q0ovf=0. Leg D (mag+rec+true-center) PASSES acceptance: 415.3->bin23, 440->bin24, 466.16->bin25, all clean winners, q0ovf=0. CONCLUSION: the two int64 fixes (magnitude + recurrence multiply) fully resolve the GDFT fixed-point overflow; TRUE-CENTRE WAS NEVER BROKEN — it was masked by the overflows. q-state stays int32 (no wider-q pass needed). All flags remain default-OFF pending perf/AGC-scale + eyes-on review before any flip."
---

# K1_GDFT_INT64_RECURRENCE_V1 — device A/B (12201 / B489A500, 2026-06-21)

Raw GDFTP/GDFTP5 captures: `rec_A.txt`, `rec_B.txt`, `rec_C.txt`, `rec_D.txt`.
Branch: `feat/gdft-int64-recurrence-ab`. Identity guard-verified `B489A500` before every flash; restored to shippable `k1_bench_reference` after. `q0ovf` (q-state int32-overflow count) = **0** on every probe.

## Argmax + magnitude summary (GDFTP)

| tone | A (all 0) | B (mag) | C (mag+rec) | D (mag+rec+tc) | D required |
|---|---|---|---|---|---|
| 415.3 | 24 (331*) | 24 (6573†) | 24 (248) | **23 (252)** ✓ | 23 |
| 440.0 | 26 (156*) | 25 (2206†) | 25 (245) | **24 (249)** ✓ | 24 |
| 466.16 | 25 (347*) | 26 (2461†) | 26 (245) | **25 (247)** ✓ | 25 |

`*` leg-A values are int32-overflow-corrupted (wrapped/clamped). `†` leg-B values are overflow-INFLATED (the recurrence still grows q erratically without bound).

## What each leg proved

- **A (all OFF)** — the int32 overflow collapse: 440 nbr bin24=0.00, bin25=0.00 → bin26 wins. q0ovf=0 (recurrence flag off).
- **B (int64 magnitude only)** — clamps gone, but magnitudes are huge (~2000–6500) because the **recurrence** still overflows int32 and grows q erratically; rounded-k offset persists (440→bin25, 466→bin26).
- **C (int64 magnitude + recurrence, rounded-k)** — magnitudes collapse to **~245**, matching the bit-faithful host replica to <1% (host: 248/245/245; device: 247.8/245.4/244.6). The recurrence fix makes the device behave EXACTLY like exact-integer math. `q0ovf=0` → q-state never overflows int32; the proven bug was the MULTIPLY width, not q range.
- **D (int64 magnitude + recurrence + true-center)** — **ACCEPTANCE PASS**: 415.3→bin23, 440→bin24, 466.16→bin25, each a clean dominant winner (runner-up ~65% of peak), magnitudes 252/249/247 matching the host. `q0ovf=0`.

## Conclusion — the GDFT fixed-point overflow chain is resolved

1. int32 **magnitude** `q2²+q1²-(mult>>14)·q2` overflows at resonance → zeroed bins. Fixed by `K1_GDFT_INT64_MAGNITUDE_V1`.
2. int32 **recurrence** `coeff_q14 * (int32_t)q1` overflows at q1>~67k → corrupted q → wrong argmax. Fixed by `K1_GDFT_INT64_RECURRENCE_V1`.
3. With BOTH int64 fixes, the device matches the host replica, and **true-centre delivers exactly what it promised**: each note lands on its correctly-LABELED bin (415.3→A♯3's neighbour bin23=G♯4 label, 440→A4 bin24, 466.16→A♯4 bin25). The earlier "true-centre is broken / confirmed-negative / scalloping" framings were ALL the fixed-point overflows, now disproven.
4. **q-state needs no widening** (q0ovf=0 everywhere; max|q0|~1.6e5 ≪ INT32_MAX).

## What is NOT yet done (out of scope here)

- All three flags remain **default-OFF**. Before any production default-flip: (a) **perf/MabuTrace** Core-0 cost of the two int64 multiplies per bin; (b) the int64 magnitude un-wraps the magnitude **scale ~20×** vs the (corrupted) legacy values — downstream AGC/normalization/`magnitudes_normalized` consumers must be assessed; (c) **Captain eyes-on** of the resulting visual change (true-centre shifts which note lights which bin — a perceptual change, not just a measurement one); (d) no Hann/ACF/Nyquist-safe/VP coupling.
