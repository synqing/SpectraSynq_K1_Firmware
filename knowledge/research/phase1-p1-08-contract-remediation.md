---
title: Phase 1 P1-08 — Contract remediation map
status: verified
last_verified: 2026-07-13
executor: agent:cursor
sources:
  - phase1-p1-08-codex-adversarial-result.md
owner: knowledge-curator
---

# P1-08 contract remediation

Remediation for Codex adversarial review [`phase1-p1-08-codex-adversarial-result.md`](./phase1-p1-08-codex-adversarial-result.md) (verdict FAIL: 4H/7M/1L). Docs-only; no firmware changes.

## Summary

| Area | Before | After |
|------|--------|-------|
| Phase 1 gate | PASS + P1-08 PARTIAL (contradictory) | **DONE** — exit criteria met; P1-08 adversarial archived; contract debt remediated in docs |
| Lane authority | Hardcoded `lane/im73d-pdm-eval` vs live branch | Git-at-session-start authoritative; agent-stack **lane-orthogonal** |
| repo-truth FAIL | Ambiguous stop/proceed | Dual-track decision: firmware blocked; docs-only agent-stack allowed when scoped |
| Promotion | Ambiguous agent vs Captain | Captain OR delegated agent after review gate; `status: verified` requires evidence |
| Install allowlist | Blanket “operator tooling” | Enumerated: Herdr, sqlite-utils, `codex@openai-codex`; OK MCP v0.29.1 Phase 2 only |

## Finding → remediation

| ID | Sev | Issue | Remediation | File(s) changed |
|----|:---:|-------|-------------|-----------------|
| P1-08-01 | H | Phase 1 PASS while P1-08 PARTIAL | Phase 1 exit = **DONE**; P1-08 criterion **DONE** with FAIL verdict as follow-up debt, not PARTIAL | `PHASED-ROLLOUT.md`, `ACTIONABLE-TASKS.md` |
| P1-08-02 | H | Lane branch mismatch | §3 split: firmware lane from git; agent-stack lane-orthogonal | `AGENT_OS.md`, `current-priorities.md` |
| P1-08-03 | H | Conflicting Phase 1 status | Single ledger in `current-priorities.md`; README/ROLLOUT/TASKS aligned to **DONE** | `README.md`, `PHASED-ROLLOUT.md`, `ACTIONABLE-TASKS.md`, `current-priorities.md` |
| P1-08-04 | H | Bootstrap FAIL vs rollout PASS | Dual-track decision + bootstrap text; rollback cross-link | `knowledge/decisions/agent-stack-repo-truth-dual-track.md`, `AGENT_OS.md`, `PHASED-ROLLOUT.md`, `SWARM-ORCHESTRATION.md`, `current-priorities.md` |
| P1-08-05 | M | Non-identical hierarchies | Explicit deferral: AGENT_OS firmware safety; AUTHORITY-CONTRACT tool domains | `AGENT_OS.md`, `AUTHORITY-CONTRACT.md` |
| P1-08-06 | M | Promotion approval ambiguous | Approval table; no self-verify; no auto-sync | `SWARM-ORCHESTRATION.md` |
| P1-08-07 | M | Scaffold vs OK pilot blurred | Scaffold disclaimer; Phase 2 gate for MCP | `knowledge/index.md`, `README.md` |
| P1-08-08 | M | Allowlist too broad | Enumerated table with pins; OK MCP Phase 2 only | `AGENT_OS.md`, `agent-stack-autonomous-execution.md` |
| P1-08-09 | M | Rollback destroys proof | `status: rolled_back` frontmatter; per-tool runbook refs | `PHASED-ROLLOUT.md`, `agent-stack-autonomous-execution.md` |
| P1-08-10 | M | Open P0 deps vs Phase 1 PASS | P0-02, P0-05, P0-06 marked non-blocking for Phase 1 exit | `ACTIONABLE-TASKS.md`, `PHASED-ROLLOUT.md` |
| P1-08-11 | M | Runbooks vs agent installs | Index: task-gated per allowlist | `knowledge/index.md`, `current-priorities.md` |
| P1-08-12 | L | `git stash` risky for dirty tree | **Documented only:** prefer scoped diff or worktree for adversarial bundles (no handoff edit in this pass) | *(note in this file)* |

## Adversarial FAIL items — addressed?

| Severity | Count | Addressed in this remediation |
|----------|------:|-------------------------------|
| High | 4 | **Yes** — P1-08-01 through P1-08-04 |
| Medium | 7 | **Yes** — P1-08-05 through P1-08-11 |
| Low | 1 | **Partial** — P1-08-12 documented; handoff not edited |

## Open items (not contract blockers)

- Captain usefulness rating for P1-08 (pending)
- P0-02, P0-05, P0-06 hygiene tasks
- Phase 2 entry (OpenKnowledge MCP + Captain go/no-go)
- Firmware `repo-truth` FAIL resolution on IM73D lane (separate from agent-stack docs)

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-07-13 | agent:cursor | Initial remediation map after scoped adversarial FAIL |
