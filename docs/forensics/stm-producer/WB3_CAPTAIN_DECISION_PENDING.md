# WB-3 Captain decision — dual-track test (comparative gate deferred)

**Captain directive 2026-07-29:** Do **not** lock in Path A vs Path B before bench evidence. **Test both tracks** on bench with mutually exclusive build flags; record a **comparative** decision only after both evidence packets exist (or a track is formally abandoned).

**Agents must not** infer a product winner from silence or from partial Track A / Track B results.

## Dual-track policy

| Track | Meaning | Bench flag / branch |
|-------|---------|---------------------|
| **A** | Native 40-bin re-derivation on reconciled `origin/main` | `K1_STM` / `k1_bench_im73d_stm` |
| **B** | True 512-point FFT producer spike (bench-only) | Mutually exclusive with `K1_STM` (e.g. `K1_STM_FFT512_BENCH`) |
| **C** | Drop modes 7–8 | **Only after** both tracks fail H2/H3/H5 or Captain formally abandons both |

**Still forbidden:** `k1_hardware` promotion, dual producers in one product image, VP self-shadow as parity, flash without MAC/rollback, playback without exact Captain approval.

## Upstream facts (decidable prerequisites)

1. **Implementation authority:** Native 40-bin STM + EdgeMixer modes 7–8 exist on `origin/main` behind `K1_STM` (bench env `k1_bench_im73d_stm`); **not** on `lane/dual-sync-phase0` checkout. `f6cf78f` is historical on `lane/stm-producer` only; integration base is `d40114f` + `a9ff00c`.
2. **512-point comparator validity:** **INDETERMINATE** — no independently attested 512-point reference (`WB3_REFERENCE_ATTESTATION.md`). Track B bench work proceeds on reference build + spike; comparative FFT vs native waits on attestation.
3. **H1 host mechanism:** Harness `k1_stm_replay.py` + `test_k1_stm_replay.py` on `origin/main`; run on clean main worktree (see `artifacts/stm-track-a/`).
4. **H2 visual VP:** `stm_vp_compare.py` host gate exists; per-track hardware/host matrix → `artifacts/stm-track-{a,b}/`.
5. **H3 Core-0 safety:** No measured treatment/baseline distributions → **INDETERMINATE** until per-track bench runs (`WB3_CORE0_BENCH_PROCEDURE.md`).
6. **H4 true-FFT feasibility:** Bounded fact sheet + bench spike steps (`WB3_FFT512_FEASIBILITY.md`).
7. **H5 captivation:** No Captain eyes-on verdict for modes 7/8 on K1 STM builds in this session.
8. **Integration defects:** Audit items remain **hypotheses** until clangd Gate 0 (`GATE0_CLANGD_BLOCKER.md`).
9. **Device scope:** Registry dual-sync / donor conflict — **no WB-3 hardware evidence** until Captain allocates bench K1.
10. **INDETERMINATE gates:** E2, E4–E7 in `WB3_EVIDENCE_MATRIX.md` (per-track columns).

## Comparative record template (fill **after** both track packets)

```yaml
policy: dual-track-test-2026-07-29
track_a_status: not-started | in-progress | packet-complete | abandoned
track_b_status: not-started | in-progress | packet-complete | abandoned
track_a_artifact_dir: artifacts/stm-track-a/<run-id>/
track_b_artifact_dir: artifacts/stm-track-b/<run-id>/
selected_path: A | B | C | bench-only-both | null
rejected: []
evidence_hashes: []
rationale: ""
production_intent: bench-only | promote-later | absent
sign_off_date: YYYY-MM-DD
captain_attestation: ""
```

## Convergence

Per-track bench convergence is **authorised** on separate branches/flags. Production promotion (Phase 9) remains **skipped** until this comparative record exists. See `WB3_CONVERGENCE_CONDITIONAL.md` and `WB3_COMPARATIVE_DECISION_RECORD.md`.
