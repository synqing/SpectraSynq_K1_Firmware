---
title: Agent stack docs work vs firmware repo-truth FAIL
status: verified
last_verified: 2026-07-13
sources:
  - phase1-p1-08-codex-adversarial-result.md
  - AGENT_OS.md § Session bootstrap
  - scripts/agent/repo-truth.sh
owner: knowledge-curator
---

# Decision: dual-track bootstrap when repo-truth FAIL

## Context

`scripts/agent/repo-truth.sh` can report **FAIL** (lane-integrity: IM73D env, guard manifest, migration plan) while
agent-stack **docs-only** governance work is in scope on a different git branch
(e.g. `lane/gem-port-beat-pulse`). These are separate concerns; conflating them
produced contradictory rollout narratives (P1-08-04).

## WARN vs FAIL semantics (2026-07-13)

`repo-truth.sh` classifies **OVERALL** as `PASS`, `WARN`, or `FAIL`. `session-bootstrap.sh` maps that to exit policy:

| OVERALL | Bootstrap exit | Meaning |
|---------|----------------|---------|
| **PASS** | 0 | Lane integrity OK; no blocking warnings |
| **WARN** | 0 | Non-fatal hygiene (e.g. uncommitted `docs/hardware/device-build-registry.md`, stale doc mentions). Firmware and docs work may proceed; do not ignore printed `WARN:` lines |
| **FAIL** | 1 | Lane-integrity problem (missing IM73D env, upload-guard/manifest wiring, migration plan, etc.). Firmware track blocked per tables below |

**Guard fix (2026-07-13):** IM73D upload-guard check had been a false **FAIL** (manifest authorization probe). Scripts fix recorded as `81e28887`; after fix, IM73D env/guard/plan report **PASS** when wired correctly. Dual-track policy applies only when OVERALL is **FAIL**, not **WARN**.

Evidence snapshot: [`research/repo-truth-fix-evidence.md`](../research/repo-truth-fix-evidence.md).

## Decision

### Firmware track (blocked on FAIL)

When `session-bootstrap.sh` exits nonzero because `repo-truth` is **FAIL**:

| Action | Allowed |
|--------|---------|
| Read source, docs, git history | Yes |
| Edit **firmware** source or `platformio.ini` | **No** |
| `pio-build.sh` / firmware commits | **No** |
| Flash, upload, erase, serial monitor | **No** (unchanged) |

Resolve the FAIL (lane integrity, missing env/guard/plan) before any firmware lane work or shippable commits.

### Agent-stack docs track (may proceed under FAIL)

| Action | Allowed when… |
|--------|----------------|
| Edit `docs/agent-stack/`, `knowledge/`, `AGENT_OS.md` governance | Explicitly scoped docs-only task (e.g. P1-08 remediation) |
| Install enumerated operator tools | Per [`agent-stack-autonomous-execution.md`](./agent-stack-autonomous-execution.md) only |
| Archive research / adversarial results | Yes; no firmware dependency |

**Requirements for docs track under FAIL:**

1. Task scope states **docs-only**; no firmware or `platformio.ini` edits.
2. Bootstrap FAIL is **acknowledged** in handoff or research artifact (not ignored).
3. `repo-truth` FAIL is **not** treated as agent-stack phase PASS — it is a parallel firmware blocker.

### Lane orthogonality

- **Firmware lane** = git branch + HEAD at session start (`AGENT_OS.md` §3).
- **Agent-stack rollout** = cross-cutting docs/tooling; **does not** override firmware lane verification.
- A branch named in §3 as the IM73D reference is **historical default**, not a mandate that all work use that branch.

## Rollback

If dual-track policy causes agents to ship firmware under FAIL, revert to strict interpretation:
bootstrap FAIL → stop all work until PASS.

## Cross-links

- [`docs/agent-stack/PHASED-ROLLOUT.md`](../../docs/agent-stack/PHASED-ROLLOUT.md) — Phase 1 rollback
- [`knowledge/research/phase1-p1-08-contract-remediation.md`](../research/phase1-p1-08-contract-remediation.md)
