# STM independent reference authority

**RBDO:** DEGRADED-MODE — no independently attested 512-point reference executable is named in-repo at closure of this documentation pass.

## Upstream fact

The deprecated donor STM (`STMExtractor`) depends on a **512-point raw-PCM FFT** and `bins256` semantics that K1's Goertzel-only audio path does not provide. A **faithful transplant is impossible** without adding a separate FFT producer or accepting semantic re-derivation on the native 80-bin spectrogram.

The donor STM was **never hardware-validated** for visual parity even on the source lineage (colour modes 0–4 only in validation scope). Therefore **“equivalent to source” cannot be treated as perceptual ground truth** without a newly defined, independently identified reference.

## Valid comparator options

1. **Named 512-point reference build** — separate executable with structural attestation (`fft_size=512`, hop/overlap, magnitude pipeline, 42 published bins, temporal window, scaling, readiness). Provenance hash must differ from the K1 candidate build.
2. **Captain-owned product-value criterion** — if (1) cannot be named, WB-3 closure uses mechanism discrimination + Captain captivation verdict on K1 hardware, not asserted donor parity.

Until (1) is attested, machine VP runs that compare K1 against K1, blank data, or unlabelled self-shadow must return **`INDETERMINATE`** for parity claims.

## Required attestation fields (when reference exists)

- Source commit and build environment
- Executable hash
- Fixture hash (common raw PCM with candidate)
- Intermediate dimensions and algorithm identifiers
- Independent reviewer sign-off (human, not agent product decision)

## Revisit trigger

Captain names the authoritative reference commit/build **or** formally replaces source-parity language with product-value language in `WB3_CAPTAIN_DECISION_PENDING.md`.
