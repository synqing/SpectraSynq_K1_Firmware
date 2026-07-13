---
title: SpectraSynq K1 — Knowledge Index
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
owner: knowledge-curator
---

# Knowledge Index

Project-scoped **durable curated knowledge** for SpectraSynq K1 Firmware.

**Pilot status (standard stack v1, 2026-07-13):** **DONE** — Phase 6 closed. Markdown in git is **authoritative**; OpenKnowledge MCP v0.29.1 is **optional accelerator** (`@inkeep/open-knowledge@0.29.1`; `.mcp.json` (Claude Code) + `.cursor/mcp.json` (Cursor, OK-only); no user-global). **Manifest:** [`../docs/agent-stack/STANDARD-STACK.md`](../docs/agent-stack/STANDARD-STACK.md). **Canonical Phase 2 summary:** [`research/phase2-openknowledge-mcp-proof.md`](./research/phase2-openknowledge-mcp-proof.md). Captain go — [`decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md`](./decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md). Do not treat `knowledge/` as overriding git/code for implementation truth.

## Minimum before acting

Every session — including **fresh agents with zero chat history** (Phase 3 Test 1):

1. Run `bash scripts/agent/session-bootstrap.sh` — must exit 0 for **firmware** work; if nonzero, acknowledge FAIL and scope per dual-track policy below.
2. **Verify git lane:** `git branch --show-current`, `git rev-parse --short HEAD`, `git status --short` — branch + HEAD beat handoff/progress for implementation truth.
3. Follow cold-start read order: [`runbooks/fresh-agent-handoff.md`](./runbooks/fresh-agent-handoff.md).

Bootstrap FAIL does **not** block docs-only agent-stack work when explicitly scoped — see [`decisions/agent-stack-repo-truth-dual-track.md`](./decisions/agent-stack-repo-truth-dual-track.md).

## Maturity disclaimer

OpenKnowledge tooling is **pre-1.0** (v0.29.1 pilot). See
[`decisions/agent-stack-openknowledge-maturity.md`](./decisions/agent-stack-openknowledge-maturity.md).

## Navigation

| Path | Purpose |
|------|---------|
| [`product.md`](./product.md) | Product context and north star |
| [`architecture.md`](./architecture.md) | System architecture pointers |
| [`current-priorities.md`](./current-priorities.md) | Active lane priorities (verify against git) |
| [`decisions/`](./decisions/) | Ratified ADRs and agent-stack decisions (incl. repo-truth dual-track) |
| [`runbooks/`](./runbooks/) | Operator procedures (incl. **fresh-agent cold-start**, manual git policy, claude-mem budget); installs are **task-gated** per `AGENT_OS.md` allowlist (not auto-executed from index alone) |
| [`runbooks/agent-onboarding.md`](./runbooks/agent-onboarding.md) | Standard stack v1 — new-agent cold start (P6-05) |
| [`runbooks/fresh-agent-handoff.md`](./runbooks/fresh-agent-handoff.md) | Phase 3 Test 1 — cold-start read order for agents without Captain re-brief |
| [`runbooks/promote-learning.md`](./runbooks/promote-learning.md) | Post-session promotion checklist (P3-03); Claude-mem read-only → `knowledge/` write path |
| [`runbooks/headroom-compression-benchmark.md`](./runbooks/headroom-compression-benchmark.md) | Phase 5 headroom compression benchmark — isolated venv, Kompress A/B metrics (P5-03) |
| [`research/`](./research/) | Verified research notes (promote when durable) |
| [`research/agent-stack-rollout-complete-2026-07-13.md`](./research/agent-stack-rollout-complete-2026-07-13.md) | Phase 6 closure — rollout COMPLETE (v1) |

## Ratified decisions

| Decision | Topic | `last_verified` |
|----------|-------|-----------------|
| [`agent-stack-standard-stack-2026-07-13.md`](./decisions/agent-stack-standard-stack-2026-07-13.md) | Phase 6 — standard stack v1 promotion (P6-06) | 2026-07-13 |
| [`agent-stack-openknowledge-pilot-go-2026-07-13.md`](./decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md) | Phase 2 exit — OpenKnowledge pilot go | 2026-07-13 |
| [`agent-stack-authority-ratified-2026-07-13.md`](./decisions/agent-stack-authority-ratified-2026-07-13.md) | Captain ratification of agent-stack authority contract | 2026-07-13 |
| [`agent-stack-autonomous-execution.md`](./decisions/agent-stack-autonomous-execution.md) | Phase 1–2 operator tooling + Phase 5 Headroom compression allowlist | 2026-07-13 |
| [`agent-stack-repo-truth-dual-track.md`](./decisions/agent-stack-repo-truth-dual-track.md) | Dual-track when `repo-truth` FAIL | 2026-07-13 |
| [`agent-stack-openknowledge-maturity.md`](./decisions/agent-stack-openknowledge-maturity.md) | OpenKnowledge v0.29.1 pre-1.0 maturity risk | 2026-07-13 |
| [`agent-stack-headroom-partial-2026-07-13.md`](./decisions/agent-stack-headroom-partial-2026-07-13.md) | Phase 5 partial exit — compression-only; P5-05 no promote | 2026-07-13 |
| [`agent-stack-phase4-exit-gate-2026-07-13.md`](./decisions/agent-stack-phase4-exit-gate-2026-07-13.md) | Phase 4 exit — Entire + Ruflo pilots PASS with debt (P4-08) | 2026-07-13 |
| [`agent-stack-phase3-exit-gate-2026-07-13.md`](./decisions/agent-stack-phase3-exit-gate-2026-07-13.md) | Phase 3 exit — coexistence PASS (P3-08) | 2026-07-13 |
| [`agent-stack-promotion-not-sync.md`](./decisions/agent-stack-promotion-not-sync.md) | Promotion-not-sync (no Claude-mem auto-sync) | 2026-07-13 |
| [`agent-stack-entire-hooks-dual-path.md`](./decisions/agent-stack-entire-hooks-dual-path.md) | Entire hooks dual-path; P4-E05 pilot go | 2026-07-13 |
| [`agent-stack-entire-cli-limitation-2026-07-13.md`](./decisions/agent-stack-entire-cli-limitation-2026-07-13.md) | npm `entire-cli@0.0.3` unpromoted; enable path vs hook CLI gap | 2026-07-13 |
| [`repo-truth-im73d-manifest-check-2026-07-13.md`](./decisions/repo-truth-im73d-manifest-check-2026-07-13.md) | Repo-truth IM73D guard — manifest-aware check (post grep fix) | 2026-07-13 |

## Authority

| Need | Source |
|------|--------|
| Implementation truth | Code + tests + git |
| Process / safety | [`AGENT_OS.md`](../AGENT_OS.md), [`.claude/CLAUDE.md`](../.claude/CLAUDE.md) |
| Durable decisions | `knowledge/decisions/` (`status` + `last_verified`) |
| Session history | Claude-mem (episodic only) |

**Promotion, not sync.** Load routing skill: `knowledge-memory-routing`.

## Agent stack docs

- [`docs/agent-stack/STANDARD-STACK.md`](../docs/agent-stack/STANDARD-STACK.md) — **v1 manifest**
- [`docs/agent-stack/README.md`](../docs/agent-stack/README.md)
- [`docs/agent-stack/AUTHORITY-CONTRACT.md`](../docs/agent-stack/AUTHORITY-CONTRACT.md)
- [`research/phase6-scorecard.md`](./research/phase6-scorecard.md) — promotion scorecard
- [`research/agent-stack-rollout-complete-2026-07-13.md`](./research/agent-stack-rollout-complete-2026-07-13.md) — rollout closure note
