# WB-3 Core-0 bench — INDETERMINATE bundle

**Run ID:** `stm-core0-20260729-indeterminate`  
**Decision:** **INDETERMINATE** (insufficient hardware authority)

## Blockers

| ID | Blocker | Evidence |
|----|---------|----------|
| D1 | Bench K1 (`B489A500`) committed to `k1_sync_probe_bench` dual-sync FOLLOWER | `device-build-registry.md` §2 current row |
| D2 | Main K1 (`F887A500`) on deprecated donor firmware, not K1 STM tree | Registry 2026-07-29 donor flash |
| D3 | No bench timing macro in firmware at this commit on active branch | `lane/dual-sync-phase0` lacks `k1_stm.*` |
| D4 | clangd Gate 0 not cleared — insertion points unverified | `GATE0_CLANGD_BLOCKER.md` |
| D5 | Captain playback approval not granted for active fixtures | audio-playback safety rule |

## What was not done

- Flash `k1_bench_im73d_stm`
- Capture p50/p95/p99 STM producer spans
- Ratify incremental Core-0 budget from measured baseline

## Next actions (Captain / hardware)

1. Release bench from dual-sync **or** allocate spare K1 with explicit rollback.
2. Restore main to `k1_hardware` when product STM eyes-on needed.
3. Land instrumentation on clean `origin/main` worktree; re-run procedure.

## Related

- Spec: `WB3_CORE0_INSTRUMENTATION_SPEC.md`
- Procedure: `WB3_CORE0_BENCH_PROCEDURE.md`
