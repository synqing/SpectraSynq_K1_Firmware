---
title: Current Priorities
status: verified
last_verified: 2026-07-13
sources:
  - AGENT_OS.md § Current-lane verification
  - docs/agent-stack/PHASED-ROLLOUT.md
  - progress.md
owner: knowledge-curator
---

# Current Priorities

> **Verify lane before acting.** Git branch + HEAD + working tree beat this file.
> If `scripts/agent/repo-truth.sh` flags stale docs, treat handoff/progress as historical.

## Phase status ledger (agent stack)

| Phase | Status | Authority |
|-------|--------|-----------|
| 0 — Authority | **PASS** | [`decisions/agent-stack-authority-ratified-2026-07-13.md`](./decisions/agent-stack-authority-ratified-2026-07-13.md) |
| 1 — Herdr, Codex, sqlite-utils | **DONE** | [`docs/agent-stack/PHASED-ROLLOUT.md`](../docs/agent-stack/PHASED-ROLLOUT.md) |
| 2 — OpenKnowledge pilot | **DONE** | Exit gate PASS 2026-07-13 — [`decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md`](./decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md); MCP proof [`research/phase2-openknowledge-mcp-proof.md`](./research/phase2-openknowledge-mcp-proof.md) |
| 3 — Claude-mem + OpenKnowledge coexistence | **DONE** | Exit gate PASS 2026-07-13 — [`decisions/agent-stack-phase3-exit-gate-2026-07-13.md`](./decisions/agent-stack-phase3-exit-gate-2026-07-13.md); summary [`research/phase3-exit-gate-summary.md`](./research/phase3-exit-gate-summary.md) |
| 4 — Entire + Ruflo pilots | **DONE** | Exit gate PASS with documented debt 2026-07-13 — [`decisions/agent-stack-phase4-exit-gate-2026-07-13.md`](./decisions/agent-stack-phase4-exit-gate-2026-07-13.md); summary [`research/phase4-exit-gate-summary.md`](./research/phase4-exit-gate-summary.md) |
| 5 — Headroom compression benchmark | **DONE** | **Compression benchmark PASS; operational qualification pending** — not in standard stack; no further Headroom testing this rollout — [`research/phase5-exit-gate-summary.md`](./research/phase5-exit-gate-summary.md) |
| 6 — Standard stack promotion | **DONE** | v1 ratified 2026-07-13 — [`decisions/agent-stack-standard-stack-2026-07-13.md`](./decisions/agent-stack-standard-stack-2026-07-13.md); [`../docs/agent-stack/STANDARD-STACK.md`](../docs/agent-stack/STANDARD-STACK.md); scorecard [`research/phase6-scorecard.md`](./research/phase6-scorecard.md) |

P1-08 adversarial review: **DONE** — contract verdict was FAIL on first pass; remediation in [`research/phase1-p1-08-contract-remediation.md`](./research/phase1-p1-08-contract-remediation.md).

## Active firmware lane — IM73D122 productionization

**Authority:** git at session start (`AGENT_OS.md` §3). Docs below are reference only.

- **Reference branch:** `lane/im73d-pdm-eval` — confirm with `git branch --show-current`
- **Project:** `SPECTRASYNQ_K1_FIRMWARE`
- **Focus:** IM73D122 productionisation. Phase-1 firmware is done; bench IM73D R1/no-speaker
  DSR proof is closed; current blocker is **R2 production-shape hardware proof**
  (main K1 SPH0645 → IM73D on GPIO13/12/14, or dedicated production-shape IM73D unit).

### Lane authority docs

- [`docs/hardware/im73d-codex-resume-handover-2026-07-06.md`](../docs/hardware/im73d-codex-resume-handover-2026-07-06.md)
- [`.claude/handoff.md`](../.claude/handoff.md) — session pointer (may be stale; verify)
- [`progress.md`](../progress.md) — rolling status

## Parallel track — Agent stack rollout (lane-orthogonal)

**Phase 1 DONE** · **Phase 2 DONE** · **Phase 3 DONE** · **Phase 4 DONE** · **Phase 5 DONE** · **Phase 6 DONE** (standard stack v1 2026-07-13). Does **not** override firmware lane verification.
May run on any branch when scoped docs-only.

- **Manifest:** [`docs/agent-stack/STANDARD-STACK.md`](../docs/agent-stack/STANDARD-STACK.md)
- Authority: [`docs/agent-stack/AUTHORITY-CONTRACT.md`](../docs/agent-stack/AUTHORITY-CONTRACT.md) (ratified)
- Tasks: [`docs/agent-stack/ACTIONABLE-TASKS.md`](../docs/agent-stack/ACTIONABLE-TASKS.md)
- Onboarding: [`knowledge/runbooks/agent-onboarding.md`](./runbooks/agent-onboarding.md)
- Runbooks: [`knowledge/runbooks/`](./runbooks/) (task-gated install/verify per allowlist)

## Bootstrap / repo-truth

| `repo-truth` OVERALL | `session-bootstrap.sh` | Firmware work | Agent-stack docs work |
|----------------------|-------------------------|---------------|------------------------|
| **PASS** | Exit **0** | Allowed per scope | Allowed per scope |
| **WARN** | Exit **0** (warnings printed) | Allowed per scope; heed WARN lines (e.g. dirty [`device-build-registry.md`](../docs/hardware/device-build-registry.md) — do not auto-commit) | Allowed per scope |
| **FAIL** | Exit **nonzero** | **Blocked** | Allowed if explicitly scoped docs-only — see [`decisions/agent-stack-repo-truth-dual-track.md`](./decisions/agent-stack-repo-truth-dual-track.md) |

Lane-integrity checks (IM73D env / upload-guard manifest / migration plan) must be **PASS** for OVERALL to avoid FAIL. As of 2026-07-13 the IM73D guard false-positive is fixed in scripts (`81e28887`); typical WARN is registry dirty only. Evidence: [`research/repo-truth-fix-evidence.md`](./research/repo-truth-fix-evidence.md).

## Non-negotiables (both tracks)

- No flash/upload/erase without Captain approval
- No `start_noise_cal` without confirmed silence
- Build via `bash scripts/agent/pio-build.sh <env>` only
- Install allowlist: `AGENT_OS.md` §7 + [`STANDARD-STACK.md`](../docs/agent-stack/STANDARD-STACK.md) — Herdr, sqlite-utils, Codex plugin, OpenKnowledge MCP v0.29.1 project-scoped
