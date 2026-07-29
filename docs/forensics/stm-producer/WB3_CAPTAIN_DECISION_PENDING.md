# WB-3 Captain decision — PENDING

**No Path A / B / C has been selected.** Agents must not infer a product choice from silence.

## Upstream facts (decidable prerequisites)

1. **Implementation authority:** Native 40-bin STM + EdgeMixer modes 7–8 exist on `origin/main` behind `K1_STM` (bench env `k1_bench_im73d_stm`); **not** on `lane/dual-sync-phase0` checkout. `f6cf78f` is historical on `lane/stm-producer` only; integration base is `d40114f` + `a9ff00c`, not a blind cherry-pick of `f6cf78f`.
2. **512-point comparator validity:** **INDETERMINATE** — no independently attested 512-point reference (`WB3_REFERENCE_ATTESTATION.md`). Source parity against donor STM is **not provable** without a new reference build.
3. **H1 host mechanism:** Harness `k1_stm_replay.py` + `test_k1_stm_replay.py` on `origin/main`; **not re-run** this session on dual-sync tree → **INDETERMINATE** here.
4. **H2 visual VP:** `stm_vp_compare.py` host gate exists; no valid reference-vs-candidate hardware/host parity run → **INDETERMINATE**.
5. **H3 Core-0 safety:** No measured treatment/baseline distributions → **INDETERMINATE** (`WB3_CORE0_BENCH_INDETERMINATE.md`).
6. **H4 true-FFT feasibility:** Bounded fact sheet only — technically plausible, cost **ESTIMATED**, not measured (`WB3_FFT512_FEASIBILITY.md`).
7. **H5 captivation:** No Captain eyes-on verdict for modes 7/8 on K1 STM builds in this session.
8. **Integration defects:** Audit items in plan §3.11 remain **hypotheses** until clangd verification (`GATE0_CLANGD_BLOCKER.md`).
9. **Device scope:** Main K1 on deprecated donor firmware; bench on sync probe — **no WB-3 hardware evidence** in this packet.
10. **INDETERMINATE gates:** E2, E4–E7 in `WB3_EVIDENCE_MATRIX.md`.

## Paths (Captain selects one — agent does not)

| Path | Meaning |
|------|---------|
| **A** | Accept native 40-bin re-derivation; converge/fix flagged implementation on reconciled `origin/main` tip |
| **B** | Fund separate 512-point FFT producer programme |
| **C** | Drop modes 7/8 and remove STM surface |

## Record template (fill on decision)

```yaml
selected_path: A | B | C
rejected: []
evidence_hashes: []
rationale: ""
production_intent: bench-only | promote-later | absent
sign_off_date: YYYY-MM-DD
captain_attestation: ""
```

## Convergence

Phase 8A/8B/8C execution is **skipped** until this record exists. See `WB3_CONVERGENCE_CONDITIONAL.md`.
