---
title: Phase 6 — agent stack promotion scorecard
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/PHASED-ROLLOUT.md Phases 0–6
  - docs/agent-stack/ACTIONABLE-TASKS.md P6-01
  - knowledge/research/phase1-* through phase5-exit-gate-summary.md
owner: provenance-auditor
---

# Phase 6 scorecard — tool promotion matrix

**Task:** P6-01 — compile phase scorecards (Phases 1–5)  
**Manifest:** [`docs/agent-stack/STANDARD-STACK.md`](../../docs/agent-stack/STANDARD-STACK.md)  
**Decision:** [`agent-stack-standard-stack-2026-07-13.md`](../decisions/agent-stack-standard-stack-2026-07-13.md)

## Legend

| Verdict | Meaning |
|---------|---------|
| **PASS (adopt)** | Promoted to standard stack v1 |
| **PASS (pilot closed)** | Phase gate met; **not** in standard stack |
| **DEFERRED** | Evidence partial or follow-up trigger defined |
| **REJECT** | Permanent unless Captain reopens |

---

## Per-tool matrix

| Tool / capability | Phase | Verdict | Standard stack v1 | Primary evidence |
|-------------------|-------|---------|-------------------|------------------|
| **Authority contract** | 0 | **PASS** | Governance (not a tool) | [`agent-stack-authority-ratified-2026-07-13.md`](../decisions/agent-stack-authority-ratified-2026-07-13.md) |
| **Herdr** | 1 | **PASS (adopt)** | **Yes** — 0.7.3 | [`phase1-herdr-proof.md`](./phase1-herdr-proof.md) |
| **Codex plugin (manual)** | 1 | **PASS (adopt)** | **Yes** — 1.0.6; stop-gate OFF | [`phase1-codex-plugin-audit.md`](./phase1-codex-plugin-audit.md) |
| **sqlite-utils** | 1 | **PASS (adopt)** | **Yes** — 3.39 read-only | [`phase1-sqlite-utils-proof.md`](./phase1-sqlite-utils-proof.md) |
| **Codex adversarial (P1-08)** | 1 | **PASS (pilot closed)** | N/A — Captain usefulness **not assessed**; contract remediation archived | [`phase1-p1-08-codex-adversarial-result.md`](./phase1-p1-08-codex-adversarial-result.md) |
| **OpenKnowledge MCP** | 2 | **PASS (adopt)** | **Yes** — `@inkeep/open-knowledge@0.29.1` | [`phase2-openknowledge-mcp-proof.md`](./phase2-openknowledge-mcp-proof.md) |
| **`knowledge/` scaffold** | 2 | **PASS (adopt)** | **Yes** | [`knowledge/index.md`](../index.md) |
| **Manual git / no OK auto-sync** | 2 | **PASS (adopt)** | Policy | [`openknowledge-manual-git-policy.md`](../runbooks/openknowledge-manual-git-policy.md) |
| **Claude-mem compact injection** | 2 | **PASS (adopt)** | Budget policy | [`claude-mem-compact-injection.md`](../runbooks/claude-mem-compact-injection.md) |
| **Routing skill** | 3 | **PASS (adopt)** | **Yes** | [`phase3-test1-retest.md`](./phase3-test1-retest.md), Tests 2–3 |
| **Promote-learning skill** | 3 | **PASS (adopt)** | **Yes** | [`promote-learning.md`](../runbooks/promote-learning.md); P3-07 audit |
| **Claude-mem coexistence** | 3 | **PASS (adopt)** | **Yes** — episodic only | [`phase3-exit-gate-summary.md`](./phase3-exit-gate-summary.md) |
| **Auto-sync Claude-mem → OK** | 3 | **REJECT** | **No** — forbidden | [`phase3-p3-07-auto-sync-audit.md`](./phase3-p3-07-auto-sync-audit.md) |
| **Entire CLI** | 4 | **PASS (pilot closed)** | **No** — debt documented | [`phase4-entire-pilot-proof.md`](./phase4-entire-pilot-proof.md) |
| **Entire `rewind` lineage** | 4 | **PASS (pilot closed)** | **No** | [`agent-stack-entire-cli-limitation-2026-07-13.md`](../decisions/agent-stack-entire-cli-limitation-2026-07-13.md) — npm `0.0.3` hook surface gap |
| **Ruflo orchestration-only** | 4 | **PASS (pilot closed)** | **No** — no main init | [`phase4-ruflo-pilot-proof.md`](./phase4-ruflo-pilot-proof.md) |
| **Ruflo full init** | 4 | **REJECT** | **No** | Authority contract § Ruflo boundaries |
| **Headroom compression** | 5 | **PASS (pilot closed)** | **No** — compression benchmark PASS; **operational qualification pending** | [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md) |
| **Headroom memory/learn/shaping** | 5 | **REJECT** | **No** — out of benchmark scope | [`phase5-headroom-benchmark-plan.md`](./phase5-headroom-benchmark-plan.md) |
| **pxpipe** | — | **REJECT** | **No** | Authority contract |
| **OmniRoute primary** | — | **REJECT** | **No** | Authority contract |
| **Codex auto stop-gate** | 1 | **REJECT** | **No** | P1-05 audit |

---

## Phase exit gate summary

| Phase | Theme | Exit | Promotion outcome |
|-------|-------|------|-------------------|
| **0** | Authority | **PASS** | Contract ratified |
| **1** | Herdr, Codex, sqlite-utils | **DONE** | All three **adopted** |
| **2** | OpenKnowledge pilot | **DONE** | OK + `knowledge/` **adopted** |
| **3** | Coexistence | **DONE** | Routing + promote **adopted**; auto-sync **rejected** |
| **4** | Entire + Ruflo pilots | **PASS (debt)** | Pilots **closed**, not adopted |
| **5** | Headroom benchmark | **PASS** | Compression benchmark closed — **not in stack**; operational qualification pending |
| **6** | Standard stack | **DONE** | Manifest v1 published |

---

## Verification asset inventory (P0-05)

Maps repo verification harness to agent-stack gate types.

| Asset | Path / command | Gate type | Firmware | Agent stack |
|-------|----------------|-----------|----------|-------------|
| Host regression | `pytest tests/` (427+ tests) | Static/replay | **Yes** | Indirect (no firmware coupling) |
| PIO build wrapper | `scripts/agent/pio-build.sh <env>` | Build | **Yes** | No |
| Lane / doc freshness | `scripts/agent/repo-truth.sh` | Lane integrity | **Yes** | Dual-track docs allowed |
| Session bootstrap | `scripts/agent/session-bootstrap.sh` | Ritual | **Yes** | **Yes** |
| Pre-commit | `scripts/hooks/pre-commit` | Commit gate | **Yes** | Docs-only exempt paths |
| Phase 3 coexistence tests | `phase3-test*.md` | Routing | No | **Yes** |
| Phase 4 pilot proofs | `phase4-*.md` | Isolation | No | **Yes** |
| Phase 5 A/B harness | `scripts/agent/phase5-headroom-ab.py` | Benchmark | No | **Yes** (closed; not promoted) |
| Phase 6 scorecard | This file | Promotion | No | **Yes** |

---

## Monitoring targets (post-promotion)

| Metric | Target | Owner |
|--------|--------|-------|
| Authority collision incidents | 0 | Provenance auditor |
| Auto-sync pipeline count | 0 | Provenance auditor |
| Codex unapproved intercepts | 0 | Captain |
| Fresh-agent handoff without re-brief | ≥1 per major lane change | Knowledge curator |
| Stale `last_verified` in `knowledge/decisions/` | Flag monthly | Knowledge curator |

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-07-13 | agent:cursor | P6-01 initial scorecard; closes P0-05 inventory |
