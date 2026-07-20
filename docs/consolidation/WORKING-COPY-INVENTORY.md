# Working-Copy Inventory & Dedup Plan

Captured 2026-07-21. **Report only — no deletions performed, and none will be
without explicit owner approval.**

> ## Preservation policy (non-negotiable)
> 1. **Nothing is deleted without the owner's explicit, per-item approval.**
> 2. **Consolidation is backup-first.** Before any working copy is retired, its unique
>    state (branches, uncommitted diffs, untracked files) must be preserved to an
>    approved backup (pushed branch/tag on origin AND/OR a bundle in cold storage).
> 3. **Archive, don't delete.** The default retirement action is *archive* (GitHub
>    archive for repos; move to `~/_archive/` cold storage for working copies) — always
>    reversible. Deletion is a separate step that only happens after (a) backup verified
>    and (b) owner approval.

Second-layer fragmentation: beyond repo sprawl, the same repos are cloned across many
locations. Goal: designate the canon primary as the working copy; every other copy is
**preserved then archived**, never deleted implicitly.

## Canon — `SpectraSynq_K1_Firmware`

| Path | Branch | Notes |
|---|---|---|
| `~/SpectraSynq_K1_Firmware` | `bench/ws2816-split` (dirty, 95) | **PRIMARY** — keep. In-flight WS2816 work. |
| `~/SpectraSynq_K1_Firmware_n7` | `feat/n7-ota-receiver` | Feature worktree — land via PR, then archive (backup-first). |
| `~/SpectraSynq_K1_Firmware-bleremote` | `feat/ble-remoted-71control-k1` | Feature worktree — land via PR, then archive (backup-first). |
| `/private/tmp/k1-*` (7 worktrees) | various (3 prunable) | Ephemeral agent worktrees. `git worktree prune` clears only admin refs to already-gone dirs (non-destructive); live ones need branch backup before removal. |

## Lightwave-Ledstrip (reference-of-record — all local copies are STALE vs origin @ 2026-07-12)

| Path | Branch | Head | Dirty | Recommendation (backup-first, approval-gated) |
|---|---|---|---|---|
| `~/Workspace_Management/Software/Lightwave-Ledstrip` | main | 2026-05-19 | 48 | **Preserve the 48 diffs first** (commit to a `wip/` branch pushed to origin, or `git stash` + bundle). Then archive the copy. Do NOT discard. |
| `~/Downloads/Lightwave-Ledstrip` | experimental/light-guide-plate | 2025-09-28 | 2 | Ancient. Confirm the branch + 2 diffs are pushed/bundled, then archive. |
| `~/SensoryBridge-main 9/Lightwave-Ledstrip` | feat/dual-vp-recovery | 2026-05-21 | 0 | Clean. Confirm `feat/dual-vp-recovery` exists on origin, then archive. |
| `~/WLED/k1-fe-sprint-workspace/Lightwave-Ledstrip` | feature/fe-blocker-sprint-2026-05-20 | 2026-05-20 | 0 | Clean. Confirm branch on origin, then archive. |
| `~/_archive/Lightwave-Ledstrip`, `~/_archive/Session-Graph/…`, `~/.{cursor,claude-worktrees,omnara,trae}/…/Lightwave-Ledstrip` | — | — | — | Non-git snapshots / dead worktree dirs. **Leave as-is** — these already ARE the cold-storage backups. No action without approval. |

**Truth source:** none of the local copies is at the true tip. Origin
`main @ 60009324` (2026-07-12) is authoritative and is now frozen at tag
`reference-of-record/v3-final`.

## Dedup procedure (backup-first, approval-gated)

1. **Inventory unique state.** For every non-canon copy, capture branch + uncommitted
   diffs + untracked files. Nothing proceeds until this exists.
2. **Back up.** Push each unique branch to origin; for uncommitted/untracked state,
   commit to a `wip/<copy>` branch pushed to origin OR create `git bundle` archives in
   `~/_archive/consolidation-backups/2026-07-21/`.
3. **Verify backups** (branch visible on origin / bundle restores cleanly).
4. **Owner approval** — present the verified list; retire only approved items.
5. **Archive (reversible).** Move retired copies to `~/_archive/`; `git worktree prune`
   for admin cleanup.
6. **Deletion is a separate, later, explicitly-approved step** — never bundled with archiving.
