---
title: Phase 3 P3-07 — Claude-mem → OpenKnowledge auto-sync audit
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/ACTIONABLE-TASKS.md P3-07
  - knowledge/decisions/agent-stack-promotion-not-sync.md
  - knowledge/decisions/repo-truth-im73d-manifest-check-2026-07-13.md § Appendix P3-07
owner: provenance-auditor
---

# P3-07 — Auto-sync pipeline audit

**Task:** Confirm **zero** auto-sync pipelines from Claude-mem → OpenKnowledge / `knowledge/`.  
**Execution date:** 2026-07-13  
**Method:** Repo grep + hook/CI/MCP/OK config inspection (provenance auditor, Phase 3 exit gate).

Binding policy: [`agent-stack-promotion-not-sync.md`](../decisions/agent-stack-promotion-not-sync.md)

---

## Surfaces audited

| Surface | Query / check | Matches | Verdict |
|---------|---------------|---------|---------|
| `scripts/hooks/` | `claude-mem`, `open-knowledge`, `openknowledge`, `memory_add`, `observation_add` | **0** | PASS |
| `.github/workflows/` | `claude-mem`, `openknowledge`, `open-knowledge`, `knowledge/` write | **0** | PASS |
| `.pre-commit-config.yaml` | `claude-mem`, `open-knowledge`, `knowledge/` | **0** | PASS |
| `scripts/` (excl. docs references) | sync hooks writing `knowledge/` | **0 pipelines** | PASS — `session-bootstrap.sh` reads mem reachability only; `ok-scope-check.sh` guards user-global OK scope |
| `.mcp.json` | `open-knowledge` server config | 1 MCP server | PASS — project-scoped OK MCP; **no** mem→OK bridge |
| `.ok/config.yml` | `content.dir`, `autoSync` | `dir: knowledge` only | PASS — CRDT content root; no sync jobs configured |
| `.entire/` | mem/OK/knowledge sync | **0** | PASS |
| `AGENT_OS.md` | `memory_add` / direct knowledge write | Documented **forbidden** | PASS — policy, not pipeline |

---

## Expected forbidden paths (confirmed absent)

Per promotion-not-sync ADR:

| Path | Status |
|------|--------|
| Claude-mem → OpenKnowledge MCP auto-write | **Not found** |
| Claude-mem → `knowledge/` hook or script | **Not found** |
| CI job syncing mem → `knowledge/` | **Not found** |
| Auto GitHub sync of `knowledge/` | **Not found** (manual-git policy) |

---

## Positive controls (allowed, not auto-sync)

| Mechanism | Role |
|-----------|------|
| Claude-mem MCP `search` / `timeline` / `get_observations` | Read-only episodic recall |
| OpenKnowledge MCP `search` / `config` | Read project `knowledge/` |
| Manual promotion workflow | [`promote-learning.md`](../runbooks/promote-learning.md) + `promote-learning` skill |
| `scripts/agent/ok-scope-check.sh` | **Prevents** user-global OK scope creep (fail-closed guard) |

---

## Verdict

**PASS** — zero auto-sync pipelines Claude-mem → OpenKnowledge / `knowledge/` found.

Promotion to `knowledge/` occurs only via manual reviewed workflow:
[`promote-learning.md`](../runbooks/promote-learning.md) and `.cursor/skills/promote-learning/SKILL.md`.

---

## Related

- Prior inline audit (promotion demo): [`repo-truth-im73d-manifest-check-2026-07-13.md`](../decisions/repo-truth-im73d-manifest-check-2026-07-13.md) § Appendix P3-07
- Phase 3 exit gate: [`agent-stack-phase3-exit-gate-2026-07-13.md`](../decisions/agent-stack-phase3-exit-gate-2026-07-13.md)
