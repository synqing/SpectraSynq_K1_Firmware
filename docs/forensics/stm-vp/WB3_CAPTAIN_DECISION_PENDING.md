# WB-3 Captain decision — upstream facts (no path selected)

**RBDO:** GROUNDED for listed facts where cited to authority map and specs; **DECIDED** path is intentionally absent.

Agents **must not** select Path A (native 40-bin), Path B (true 512-point FFT), or Path C (drop modes 7–8).

## Upstream facts for the decision menu

1. **Implementation state:** `d40114f` + `a9ff00c` on `origin/main`; native **40-bin** STM and EdgeMixer modes 7–8 exist behind **`K1_STM`**; not promoted to `k1_hardware`.
2. **Historical prototype:** `f6cf78f` on `lane/stm-producer` only — not integration base.
3. **Donor dimensions:** reference semantics assumed **42 bins** / 512-pt FFT; K1 uses **40 bins** on 80-bin spectrogram — faithful transplant impossible without new FFT path.
4. **H1 mechanism:** host replay exists for native producer; does not prove visual parity.
5. **H2 visual parity:** **INDETERMINATE** — independent 512 reference unattested; VP tool spec + `stm_vp_compare.py` landed; no calibrated hardware matrix.
6. **H3 Core-0:** **INDETERMINATE** — estimates only (`~53 µs` commit message; Captain-attested `81–107 µs`); see `CORE0_MEASUREMENT_PROCEDURE.md`.
7. **H4 true FFT:** **INDETERMINATE** — see `TRUE_FFT_FEASIBILITY.md`.
8. **Known integration defects (verify at Gate 0):** dual `k1_stm_read()` per frame risk; adapter gap; LUT centre mapping; readiness doc drift; IM73D loudness gate; serial/mode bound mismatches — see authority map and conditional convergence doc.
9. **Device authority:** dual-sync / registry may block hardware until Captain allocates K1 and approves playback.
10. **Degenerate VP risk:** existing VPAB `self_shadow` path is smoke only — must not close WB-3.

## Paths (Captain records one)

| Path | Meaning |
|------|---------|
| **A — Native 40-bin** | Converge/fix flagged implementation; pursue H2/H3/H5 on native axis |
| **B — True 512-point FFT** | Fund separate producer programme per feasibility sheet |
| **C — Drop 7–8** | Remove STM product surface and producer from shipping path |

## Captain actions required

- [ ] Name integration base branch/commit for convergence work
- [ ] Ratify H5 (retain vs drop) with eyes-on hardware
- [ ] Approve or reject native path after H2/H3 evidence
- [ ] If B: authorise bench FFT spike budget
- [ ] If C: authorise surgical removal commit
- [ ] Sign decision record with date and evidence hashes

## Record template

```
Decision: [A|B|C|PENDING]
Rationale:
Evidence hashes:
Production intent: [bench-only|promote|absent]
Captain sign-off:
```
