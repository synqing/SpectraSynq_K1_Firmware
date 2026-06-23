---
abstract: "Device A/B (bench K1 B489A500, 12201) of K1_GDFT_INT64_MAGNITUDE_V1 with GDFTP5 telemetry. Leg A baseline reproduces the int32 overflow collapse (440: bin24/25=0.00). Leg B (int64=1) REMOVES the 0.00 clamps and resolves the host-vs-device contradiction (440->bin25, matching the host replica). Leg C (int64+true-center) acceptance FAILED: 415.3->bin23 OK but 440->bin25 (want 24) and 466.16->bin26 (want 25) — PROVING the recurrence `mult=coeff_q14*(int32_t)q1` (GDFT.h:115) ALSO overflows int32 at large q and corrupts the resonator before the magnitude. int64 magnitude is necessary but NOT sufficient; recurrence widening is a SEPARATE pass. Flags stay default-OFF. STOPPED per the no-tuning rule."
---

# K1_GDFT_INT64_MAGNITUDE_V1 — device A/B (12201 / B489A500, 2026-06-21)

Raw GDFTP/GDFTP5 captures: `capture_A_baseline.txt`, `capture_B_int64.txt`, `capture_C_int64_truecenter.txt`.
Branch: `feat/gdft-int64-magnitude-ab`. Identity guard-verified `B489A500` before every flash; device restored to shippable `k1_bench_reference` after.

## Argmax summary (GDFTP `bin`)

| tone | A: int64=0,tc=0 | B: int64=1,tc=0 | C: int64=1,tc=1 | C required |
|---|---|---|---|---|
| 415.3 | 24 | 24 | **23** ✓ | 23 |
| 420.0 | 24 | 24 | 24 | — |
| 440.0 | 26 ⚠ | **25** | 25 ✗ | 24 |
| 466.16 | 25 | 26 | 26 ✗ | 25 |

## What the neighbour magnitudes proved

- **Leg A (baseline) = the int32 overflow collapse.** 440: `nbr bin24=0.00, bin25=0.00` → bin26 wins by default. Even nonzero leg-A values were overflow-WRAPPED (bin24@415.3 read 331; its true magnitude is ~6572, leg B).
- **Leg B (int64 magnitude) FIXES the magnitude.** No more `0.00` in the near bins (440: bin24=227, bin25=2205). Argmax becomes a clean rounded-k response: **440→bin25**, exactly what the bit-faithful host replica predicted — this RESOLVES the earlier host-vs-device contradiction (the device’s old `440→bin26` was an overflow artifact). int64 magnitude is **correct and necessary**.
- **Leg C (int64 + true-center) FAILS acceptance.** 415.3→bin23 (✓) but 440→bin25 and 466.16→bin26 are +1 bin. With the int64 magnitude faithful, the only remaining error source is **q itself**: the recurrence `mult = coeff_q14 * (int32_t)q1` (GDFT.h:115) overflows int32 once q1 > ~67k (coeff_q14≈32k × q1). At the harness’s sustained 16000-amplitude tone q reaches ~160k+, so the resonator is corrupted before the magnitude is taken. The corruption is frequency/coefficient-dependent (erratic), so some tones still land right (415.3) and some shift (440, 466).

## Conclusion

- The int32 **magnitude** overflow is real and the int64 fix is the right, byte-identical-when-OFF remedy for it.
- Device test C (the Captain-designated arbiter) PROVES the **recurrence** `mult` int32 overflow ALSO matters. The int64-magnitude pass alone does not deliver correct true-center argmax.
- **Recurrence widening is a separate future pass** (its own flag + decision). NOT done here. No tuning, no recurrence change this pass.
- `K1_GDFT_INT64_MAGNITUDE_V1` and `K1_GDFT_TRUE_CENTER_V1` both stay **default-OFF**. (int64 magnitude also changes the magnitude SCALE ~20× by un-wrapping — downstream AGC/normalization implications to assess before any default flip.)
