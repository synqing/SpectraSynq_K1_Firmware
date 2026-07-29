# WB-3 hypotheses, falsifiers, and result states

**Version:** 1.0.0 (2026-07-29)  
**Threshold set hash:** `sha256:provisional-v1` — calibrate from independent-reference repeatability before candidate evaluation (plan §6.4).

## Machine result states

| State | Definition |
|-------|------------|
| **PASS** | Mandatory controls valid; frozen thresholds met; confidence bounds clear |
| **FAIL** | Valid evidence crossing a frozen threshold |
| **INDETERMINATE** | Invalid or insufficient evidence — **never** coerced to PASS |

A machine PASS proves only the named claim, fixture set, build, device population, and capture method.

## Hypotheses

### H1 — Producer discrimination (host)

**Claim:** Native K1 STM (`k1_stm.cpp`, 80→40 re-derivation) distinguishes warm-up, steady energy, 4 Hz temporal modulation, spectral ripple localisation, and silence per `k1_stm_replay.py`.

| Falsifier | Evidence route |
|-----------|----------------|
| Warm-up emits non-zero or `ready=true` early | `tests/test_k1_stm_replay.py` |
| Steady ≥ modulated temporal energy | same |
| Ripple argmax ≠ bin (K−1) | same |
| Silence not exact zero when ready | same |

**Current status (2026-07-29):** **INDETERMINATE** on `lane/dual-sync-phase0` (sources absent). On `origin/main`: harness exists — host run required on clean main worktree.

### H2 — Visual-semantic equivalence

**Claim:** Native 40-bin STM produces acceptably equivalent EdgeMixer mode 7/8 behaviour vs a **named independent** 512-point reference under approved fixtures.

| Falsifier | Route |
|-----------|-------|
| Active comparison exceeds frozen thresholds | `stm_vp_compare.py` |
| Reference not independent | `WB3_REFERENCE_ATTESTATION.md` → **INDETERMINATE** |

**Current status:** **INDETERMINATE** (no independent 512 reference attested).

### H3 — Runtime safety (Core-0 + render)

**Claim:** Enabled STM stays inside ratified Core-0 budget without AP misses, WDT, stack collapse, frame drops, or render > 2.0 ms.

| Falsifier | Route |
|-----------|-------|
| Any deadline miss / WDT / drop / render breach | `WB3_CORE0_*` artefacts |

**Current status:** **INDETERMINATE** — no hardware timing capture; device not allocatable (dual-sync + main on donor firmware).

### H4 — True 512-point FFT feasibility

**Claim:** A separate 512-point producer path has bounded PCM seam, CPU, memory, latency, and implementation cost.

See `WB3_FFT512_FEASIBILITY.md` — **bounded fact sheet only**; no second producer integrated.

### H5 — Product value

**Claim:** Modes 7/8 are sufficiently captivating to retain.

**Owner:** Captain only. Agents **must not** accept or reject H5.

## Hard invariants (non-negotiable)

- Centre origin LEDs **79/80** for spatial STM mapping (when claimed).
- No heap / blocking I/O in `render()` path.
- No rainbow / full hue-wheel sweep introduced by STM modes.
- Per-frame effect work **< 2.0 ms** when STM enabled in convergence path.
- No self-shadow parity PASS (identical A/B hashes).
- Valid provenance on all VP runs.

## Provisional calibrated thresholds (VP)

**Not frozen for STM until reference repeatability run.** Plan provisional ceilings:

| Metric | Provisional ceiling |
|--------|---------------------|
| MAE8 | 0.5 |
| p95 abs error | 1.0 |
| max abs error | 8.0 |
| changed LEDs | 2% |
| centre-of-mass Δ | 1 LED |
| trail Δ | 2 frames |
| tail-integral Δ | 10% |

Post-hoc threshold edits invalidate prior verdicts (new experiment version).

## Claim boundary statements

1. Native 40-bin parity **does not** imply a true 512-point FFT product.
2. Host replay proves **mechanism** only — not optical parity, timing safety, or production readiness.
3. `STM_DUAL` and `STM_SPECTRAL_MAP` inherit spectral-axis debt from the substituted 80-note vector.
4. One device → device-scoped claims only.
