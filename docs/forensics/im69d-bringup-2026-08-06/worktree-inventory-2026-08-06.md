# SpectraSynq_K1_Firmware worktree inventory (read-only)

Generated: 2026-08-06. Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`. Worktrees: 22 registered.  
Refs: `origin/main`, `origin/lane/k1-vj-ble-deck8` (fetched). Git `prunable` on `/tmp` paths ignored for recommendations.

| Path | HEAD | Branch | Dirty? | Unique vs `origin/main` (count; first 5) | Unique vs `origin/lane/k1-vj-ble-deck8` (count; first 5) | Branch on origin? | Recommendation |
|------|------|--------|--------|------------------------------------------|----------------------------------------------------------|-------------------|----------------|
| `/Users/spectrasynq/SpectraSynq_K1_Firmware` | `db300db` | `feat/ap-advice-phase0-im69d-gain8` | yes (27 files) | 0 | 0 | yes | **KEEP** (main checkout) |
| `/private/tmp/claude-501/.../scratchpad/vj-lane` | `7d37ab6` | `lane/k1-vj-ble-deck8` | yes (14) | 11; `7d37ab6` `7cc6c85` `248ec79` `af25309` `395116f` | 0 | yes | **KEEP** (mandatory vj-lane) |
| `/private/tmp/dual_sync_f2_newset.qq6WXo/src` | — | detached (broken) | no (dir exists, no `.git`) | 0 | 0 | — | **PRUNE_CANDIDATE** (stale registration; no repo) |
| `/private/tmp/k1-wb3-flash-39326` | — | detached (broken) | no (no `.git`) | 0 | 0 | — | **PRUNE_CANDIDATE** (stale registration) |
| `/private/tmp/k1-wb4-ship-winner` | — | `lane/wb4-ship-waveform-winner` (broken) | no (no `.git`) | 0 | 0 | unknown | **PRUNE_CANDIDATE** (stale registration) |
| `/private/var/tmp/probe-loop/runs/impl-k1-firmware/workspace` | `4fce15b` | detached | yes (1) | 54; `4fce15b` `2a51704` `a2a916d` `0d6b965` `d5e691e` | 54; same | detached | **NEEDS_HUMAN** (54 commits not on any origin branch; not in `main`) |
| `/private/var/tmp/probe-loop/runs/map-k1-firmware/workspace` | `32d511a` | detached | no | 49; `32d511a` `33de5ca` `91237b8` `2629a06` `57c49ba` | 49; same | detached | **NEEDS_HUMAN** (49 commits not on any origin branch; not in `main`) |
| `/private/var/tmp/spectrasynq-f2-sync-only-a582031.uymsOH` | `a582031` | detached | yes (2) | 0 | 0 | detached (`a582031` on `origin/main` / `origin/lane/dual-sync-phase0`) | **NEEDS_HUMAN** (dirty; else prune) |
| `/Users/spectrasynq/SpectraSynq_K1_Firmware-bleremote` | `65f5df8` | `feat/ble-remoted-71control-k1` | yes (4) | 1; `65f5df8` | 1; `65f5df8` | **no** | **NEEDS_HUMAN** (unpushed branch + dirty) |
| `/Users/spectrasynq/SpectraSynq_K1_Firmware_n7` | `d4a7824` | `feat/n7-ota-receiver` | yes (3) | 1; `d4a7824` | 1; `d4a7824` | yes | **NEEDS_HUMAN** (dirty; commit on origin) |
| `.../probe-loop-k1-worktrees/integrate-main` | `accc5f0` | detached | no | 0 | 0 | detached (`accc5f0` on `origin/delivery/p1-e2e`, `origin/delivery/p2-e2e`) | **PRUNE_CANDIDATE** |
| `.../probe-loop-k1-worktrees/p1-e2e` | `46b5d29` | `delivery/p1-e2e` | no | 0 | 0 | yes | **PRUNE_CANDIDATE** |
| `.../probe-loop-k1-worktrees/p1-phase1b-acc1` | `46b5d29` | `phase1b/acc1-reconsider` | no | 0 | 0 | no (same SHA as `origin/delivery/p1-e2e`) | **PRUNE_CANDIDATE** |
| `.../probe-loop-k1-worktrees/p1-rework` | `46b5d29` | `rework/p1-acc1-host` | yes (4) | 0 | 0 | no | **NEEDS_HUMAN** (dirty; SHA matches pushed `delivery/p1-e2e`) |
| `.../probe-loop-k1-worktrees/p1-tempo-anti-pin` | `9d2468f` | `probe/p1-tempo-anti-pinning` | no | 1; `9d2468f` | 1; `9d2468f` | yes | **PRUNE_CANDIDATE** (tip on origin) |
| `.../probe-loop-k1-worktrees/p1p3-stack` | `423d76f` | `delivery/p1p3-stack-local` | no | 3; `423d76f` `df8e916` `a137840` | 3; same | **no** | **KEEP** (3 unpushed commits) |
| `.../probe-loop-k1-worktrees/p2-e2e` | `ba3349c` | `delivery/p2-e2e` | no | 0 | 0 | yes | **PRUNE_CANDIDATE** |
| `.../probe-loop-k1-worktrees/p2-mic-auto-sense` | `b909ef2` | `probe/p2-mic-auto-sense` | yes (1) | 1; `b909ef2` | 1; `b909ef2` | yes | **NEEDS_HUMAN** (dirty; tip on origin) |
| `.../probe-loop-k1-worktrees/p2-rework` | `ba3349c` | `rework/p2-vol60-headroom` | no | 0 | 0 | yes | **PRUNE_CANDIDATE** |
| `.../probe-loop-k1-worktrees/p3-beat-aware-director` | `65e03bc` | `probe/p3-beat-aware-director` | no | 58; `65e03bc` `eb6ac79` `1e91546` `a7f132a` `797f4e0` | 58; same | yes | **KEEP** (active probe lane on origin; large ahead-of-main stack) |
| `.../probe-loop-k1-worktrees/p3-e2e` | `d206044` | `delivery/p3-e2e` | no | 0 | 0 | yes | **PRUNE_CANDIDATE** |
| `.../probe-loop-k1-worktrees/p3-rework` | `eb3b7bd` | `rework/p3-beat-q-hold` | yes (2) | 0 | 0 | no | **NEEDS_HUMAN** (dirty; branch not on origin) |

## Summary counts

| Recommendation | Count |
|----------------|-------|
| KEEP | 4 |
| PRUNE_CANDIDATE | 9 |
| NEEDS_HUMAN | 9 |

## Notes

- Broken `/private/tmp/*` worktrees: directory may exist but `.git` worktree link missing; objects for `f9bd28e` etc. remain in main repo; safe to prune registration only after confirming no needed dirty files in those folders.
- `impl-k1-firmware` and `map-k1-firmware` detached HEADs point to commit chains with **no** `origin/*` branch containing their tips (`4fce15b`, `32d511a`); do not prune until pushed or explicitly discarded.
- Short path `...` = `/Users/spectrasynq/Workspace_Management/Software/probe-loop-k1-worktrees`.
- vj-lane full path: `/private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/d02156cf-f33e-4d37-a6e6-cec9fd00f850/scratchpad/vj-lane`.
