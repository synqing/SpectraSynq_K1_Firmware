<!-- british-english-guard: ignore — `artifacts/` is the literal on-disk directory name in this
     repo, so paths must spell it that way. Prose here uses "artefacts". -->
---
abstract: "DUAL-K1 SYNC IS DEAD. Captain decision 2026-08-05 — the dual-sync lane is deprecated and shelved, closed by instruction rather than by technical failure. Everything in this directory is historical evidence only. Do not resume, do not plan around it, and do not propose work depending on it. Supersedes every CURRENT/ACTIVE claim in recovery-plan.md, progress.md, phase0-plan.md and the rest of this tree."
---

# ⛔ DUAL-K1 SYNC — DEAD, DEPRECATED, SHELVED

**Captain decision, 2026-08-05: "Dual-Sync is dead. Put that to bed."**

This directory is **historical evidence only.** Every document inside it that
calls itself current, active, in-progress, or next — including
`recovery/recovery-plan.md`, `recovery/progress.md`, `phase0-plan.md`,
`evaluation-and-plan.md`, `findings.md` and `f2-transport-decision.md` — is
**superseded by this notice**. Read them as a record of what was attempted, never
as a work order.

## Status

| | |
|---|---|
| Closed by | Captain instruction |
| Closed because | a product/priority decision — **not** a technical failure, and **not** a failed gate |
| Reached | Phase-0 probes flashed to both K1s (2026-07-27); F2 image set frozen; F3 never ran |
| Reopening | requires an explicit new Captain decision, not an agent's judgement |

## What agents must not do

- Do not resume F0–F3, or treat `recovery-plan.md` as an authority.
- Do not propose features, experiments, or architecture that depend on two K1s
  being time-synchronised. If a proposal needs dual-sync, it is dead on arrival.
- Do not flash `k1_sync_probe_main`, `k1_sync_probe_bench`, or
  `k1_sync_probe_main_sync_only` as part of any lane. Both K1s have since been
  reflashed for other work (registry §2).

## What is retained, and why

Nothing is deleted. The evidence stays because it cost real bench time and
records genuine findings about BLE central/peripheral behaviour on this
hardware:

- `artifacts/k1_dual_sync_eval_2026-07-08/**` — plans, findings, F2 image sets,
  recovery notes, SSA returns.
- `SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.{cpp,h}` — the SyncLink source.
- `platformio.ini` `[env:k1_sync_probe_*]` — the non-shippable probe envs, and
  their tuples in `scripts/platformio/k1_upload_guard.py`.

These are **inert**: the probe envs are non-shippable and are not built by
`k1_hardware`, `k1_prod_im73d`, or any bench mic env. Leaving them costs nothing
and removing them would be churn on a branch already carrying unrelated
in-flight work. A later cleanup lane may delete them; that is optional tidying,
not a blocker.

## Branch note

The branch `lane/dual-sync-phase0` **no longer describes its own contents.** It
is now a container for unrelated in-flight work — the IM69D130 mic evaluation,
WB-3 STM, and edgemixer changes. Do not infer from the branch name that
dual-sync work is in progress. Current lane routing lives in
[`docs/spec-index.md`](../../docs/spec-index.md).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-05 | agent:claude-code | Created — records the Captain decision to kill and shelve the dual-K1 sync lane; supersedes all "current" claims in this directory. |
