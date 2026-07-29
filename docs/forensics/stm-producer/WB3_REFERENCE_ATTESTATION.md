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

## Track B requirements (bench gate)

| # | Requirement | Owner | Status |
|---|-------------|-------|--------|
| TB-1 | Named reference executable + commit + algorithm spec (512-pt FFT → 42 bins) | Captain / DSP | **Missing** |
| TB-2 | No shared implementation with `k1_stm.cpp` (reviewer sign-off) | Independent reviewer | **Missing** |
| TB-3 | Fixture PCM from approved corpus only | Captain playback approval | **BLOCKED** |
| TB-4 | `stm_vp_compare.py` reference repeatability (≥3 runs) | VP tooling | **Not run** |
| TB-5 | Bench firmware flag exclusive with `K1_STM` | Firmware | **Not built** |
| TB-6 | Artefact manifest under `artifacts/stm-track-b/<run-id>/` | Agent | **Scaffold only** |

Track B **bench spike** may proceed on host/offline reference build while TB-1–TB-2 remain open; Track B **H2 parity closure** remains **INDETERMINATE** until TB-1–TB-4 pass.

## Decision criterion shift (Captain-visible)

Until attestation closes, H2 must be evaluated as:

1. **Mechanism discrimination** — host `k1_stm_replay` + synthetic fixtures (`H1`) on Track A.
2. **Captain-owned product value** — eyes-on modes 7/8 on K1 hardware (`H5`).
3. **Comparative decision** — only after both `artifacts/stm-track-a/` and `artifacts/stm-track-b/` packets (`WB3_COMPARATIVE_DECISION_RECORD.md`).

Do **not** require Captain to pick native vs FFT **before** both bench tracks are exercised.

## Track B explicit requirements (bench gate)

Track B bench work (`WB3_CONVERGENCE_CONDITIONAL.md`) **requires** closing this INDETERMINATE row **or** a Captain waiver recorded in `WB3_COMPARATIVE_DECISION_RECORD.md`.

| # | Requirement | Pass criterion |
|---|-------------|----------------|
| TB-1 | Named reference artefact | Path + commit hash + algorithm spec (512-pt real FFT → 256 mags → envelope → **42** STM bins) |
| TB-2 | Code independence | Reviewer attestation: reference does **not** call `k1_stm.cpp` / 80→40 native path |
| TB-3 | Input contract | Approved PCM corpus only; fixture list in manifest |
| TB-4 | Executable integrity | SHA-256 of reference binary/script + reviewer sign-off line |
| TB-5 | Repeatability | `stm_vp_compare.py` reference-vs-reference ≥3 runs, variance within spec |
| TB-6 | Bench flag exclusivity | Firmware image under test has FFT bench producer **without** `K1_STM` native producer |

## INDETERMINATE closure checklist (copy into `artifacts/stm-track-b/<run-id>/`)

- [ ] TB-1 artefact named and versioned
- [ ] TB-2 independence review recorded
- [ ] TB-3 fixture approval cites Captain playback order (if live audio used)
- [ ] TB-4 hashes in `manifest.json`
- [ ] TB-5 repeatability log attached
- [ ] TB-6 flash record: MAC, env name, rollback image

Until all applicable boxes are checked, E5 remains **INDETERMINATE** and Track B Core-0/VP matrix is **documentation-only**.

## Path to close INDETERMINATE

1. Build or name a **non-K1** reference implementation (e.g. offline Python/C++ on approved benchmark PCM) with structural attestation packet.
2. Independent reviewer confirms no shared code with `k1_stm.cpp`.
3. Record hashes in `artifacts/stm-vp/<run-id>/manifest.json` and mirror summary under `artifacts/stm-track-b/<run-id>/`.
4. Re-run `stm_vp_compare.py` reference-vs-reference repeatability (≥3 runs).

**Revisit trigger:** Captain supplies reference binary source + fixture approval, or formally waives 512 parity in the comparative decision record (Path A or C after dual-track bench).
