# WB-3 independent 512-point reference attestation

**Result state:** **INDETERMINATE** — no independently attested 512-point STM reference executable exists in the allowed source route as of 2026-07-29.

## Structural attestation checklist (plan §7.1)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Named executable + commit + algorithm spec | **Missing** | — |
| Raw PCM → 512-pt FFT → 256 mags → 128-band envelope → **42** STM bins | **Not attested** | Donor `firmware-v3/` out of scope; no K1 512-path binary |
| Reference does not call K1 `k1_stm` 80→40 | **N/A** | No reference built |
| Executable hash + reviewer sign-off | **Missing** | — |

## Source-parity impossibility record (VERIFIED from `origin/main` header)

`k1_stm.h` on `origin/main` documents:

- Donor STM used `bins256` from 512-pt FFT; Goertzel-only donor **zeroes** `bins256` and sets `stmReady=false`.
- K1 is Goertzel-only at AP frame rate with **no** 512-sample raw-PCM FFT seam in the shipping audio path.
- K1 STM is an explicit **re-derivation** from `spectrogram[80]`, 40 ripple bins, 17-frame warm-up @ ~133.33 Hz.

Therefore **byte-level or oracle-level “source parity” against LightwaveOS STM without a newly built independent 512 pipeline is not provable** from repository facts alone.

## Decision criterion shift (Captain-visible)

Until attestation closes, H2 must be evaluated as:

1. **Mechanism discrimination** — host `k1_stm_replay` + synthetic fixtures (`H1`).
2. **Captain-owned product value** — eyes-on modes 7/8 on K1 hardware (`H5`).

Do **not** present a native-vs-512 product menu until row 1–2 above and `WB3_CAPTAIN_DECISION_PENDING.md` upstream facts are on record.

## Path to close INDETERMINATE

1. Build or name a **non-K1** reference implementation (e.g. offline Python/C++ on approved benchmark PCM) with structural attestation packet.
2. Independent reviewer confirms no shared code with `k1_stm.cpp`.
3. Record hashes in `artifacts/stm-vp/<run-id>/manifest.json`.
4. Re-run `stm_vp_compare.py` reference-vs-reference repeatability (≥3 runs).

**Revisit trigger:** Captain supplies reference binary source + fixture approval, or formally waives 512 parity in the decision record (Path A or C).
