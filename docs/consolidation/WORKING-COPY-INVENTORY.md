# Working-Copy Inventory & Dedup Plan

Captured 2026-07-21. **Report only — no deletions performed.** Second-layer
fragmentation: beyond repo sprawl, the same repos are cloned across many locations.
Consolidate to the canon primary; treat everything else as disposable once confirmed.

## Canon — `SpectraSynq_K1_Firmware`

| Path | Branch | Notes |
|---|---|---|
| `~/SpectraSynq_K1_Firmware` | `bench/ws2816-split` (dirty, 95) | **PRIMARY** — keep. In-flight WS2816 work. |
| `~/SpectraSynq_K1_Firmware_n7` | `feat/n7-ota-receiver` | Feature worktree — fold in or drop when merged. |
| `~/SpectraSynq_K1_Firmware-bleremote` | `feat/ble-remoted-71control-k1` | Feature worktree — fold in or drop when merged. |
| `/private/tmp/k1-*` (7 worktrees) | various (3 prunable) | Ephemeral agent worktrees — `git worktree prune`. |

**Action:** `git worktree prune` on canon to clear the 3 prunable `/private/tmp`
worktrees; land `_n7` and `-bleremote` features via PR then remove.

## Lightwave-Ledstrip (reference-of-record — all local copies are STALE vs origin @ 2026-07-12)

| Path | Branch | Head | Dirty | Recommendation |
|---|---|---|---|---|
| `~/Workspace_Management/Software/Lightwave-Ledstrip` | main | 2026-05-19 | 48 | Stale+dirty. Review the 48 changes, then archive. |
| `~/Downloads/Lightwave-Ledstrip` | experimental/light-guide-plate | 2025-09-28 | 2 | Ancient. Delete after confirming 2 changes are noise. |
| `~/SensoryBridge-main 9/Lightwave-Ledstrip` | feat/dual-vp-recovery | 2026-05-21 | 0 | Clean, stale. Confirm branch pushed → delete. |
| `~/WLED/k1-fe-sprint-workspace/Lightwave-Ledstrip` | feature/fe-blocker-sprint-2026-05-20 | 2026-05-20 | 0 | Clean, stale. Confirm branch pushed → delete. |
| `~/_archive/Lightwave-Ledstrip`, `~/_archive/Session-Graph/…`, `~/.{cursor,claude-worktrees,omnara,trae}/…/Lightwave-Ledstrip` | — | — | — | Non-git snapshots / dead worktree dirs. Safe to remove. |

**Truth source:** none of the local copies is at the true tip. Origin
`main @ 60009324` (2026-07-12) is authoritative and is now frozen at tag
`reference-of-record/v3-final`.

## Dedup procedure (safe order)

1. Confirm every non-canon branch above is pushed to origin (`git status`, `git log origin/<branch>`).
2. For dirty copies, review/commit or discard the diffs deliberately — do not bulk-delete dirty trees.
3. `git worktree prune` on canon and Lightwave.
4. Remove confirmed-redundant clones; keep canon primary + origin only.
5. Leave `~/_archive/*` snapshots if they are intentional cold storage.
