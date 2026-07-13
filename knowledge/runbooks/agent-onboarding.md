---
title: Agent onboarding — standard stack v1
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/STANDARD-STACK.md
  - AGENT_OS.md
owner: knowledge-curator
---

# Agent onboarding runbook (standard stack v1)

**Audience:** New agents (Cursor, Claude Code, Codex) on SpectraSynq K1 Firmware.  
**Manifest:** [`docs/agent-stack/STANDARD-STACK.md`](../../docs/agent-stack/STANDARD-STACK.md)

---

## 1. Session start (mandatory)

```bash
bash scripts/agent/session-bootstrap.sh   # must exit 0 for firmware work
git branch --show-current && git rev-parse --short HEAD && git status --short
```

Read in order:

1. [`AGENT_OS.md`](../../AGENT_OS.md) — firmware safety, claude-mem policy
2. [`docs/agent-stack/STANDARD-STACK.md`](../../docs/agent-stack/STANDARD-STACK.md) — adopted tools + forbidden paths
3. [`knowledge/runbooks/fresh-agent-handoff.md`](./fresh-agent-handoff.md) — cold-start routing

If `repo-truth` FAIL: firmware blocked; docs-only agent-stack work allowed when explicitly scoped — [`agent-stack-repo-truth-dual-track.md`](../decisions/agent-stack-repo-truth-dual-track.md).

---

## 2. Knowledge routing

| Question type | Read first | Tool |
|---------------|------------|------|
| What does code do **now**? | Git + source | — |
| Ratified decision / runbook? | `knowledge/decisions/`, `knowledge/runbooks/` | OpenKnowledge MCP `search` (optional) |
| Prior session / bug history? | Claude-mem | `search` → `timeline` → `get_observations` |
| Lane / branch truth? | `git` | Never handoff alone |

**Skill:** `.cursor/skills/knowledge-memory-routing/SKILL.md` (`.claude/skills/` mirror).

**Rule:** Promotion, not sync. Never copy claude-mem into `knowledge/` without promote-learning workflow.

---

## 3. Promote a learning

When a session produces durable truth:

1. Draft Markdown under `knowledge/decisions/` or `knowledge/runbooks/`
2. Frontmatter: `status: verified`, `last_verified: YYYY-MM-DD`, `sources: [...]`
3. Run promote-learning checklist — [`promote-learning.md`](./promote-learning.md)
4. Set `openknowledge_promoted: <path|none>` in [`scripts/agent/post-session-report.md`](../../scripts/agent/post-session-report.md)

**Skill:** `.cursor/skills/promote-learning/SKILL.md`

---

## 4. Operator tools (Captain machine)

| Tool | Agent may install? | Agent may use? |
|------|-------------------|----------------|
| Herdr | Yes (allowlist) | Captain visibility only — do not route execution |
| sqlite-utils | Yes | Read-only snapshots — [`sqlite-snapshots.md`](./sqlite-snapshots.md) |
| Codex plugin | Yes | **Manual** `/codex:*` per SWARM handoff contract |
| OpenKnowledge MCP | Yes (project pin) | Search/read; writes via git promotion |

**Forbidden:** pxpipe, OmniRoute primary, Ruflo init on main lane, Headroom in agent path, auto-sync pipelines.

---

## 5. Multi-agent handoff (Codex)

Manual invoke only — see [`docs/agent-stack/SWARM-ORCHESTRATION.md`](../../docs/agent-stack/SWARM-ORCHESTRATION.md) § Codex.

Context bundle must include: branch/HEAD, `AGENT_OS.md` acknowledgment, scope boundary, artifacts to review.

**Never** enable `reviewGateEnabled: true`.

---

## 6. Session end

1. Record claude-mem observations (start, checkpoint, blocker, decision, end)
2. Fill post-session report
3. Promote durable learnings or set `openknowledge_promoted: none` with reason
4. Do not auto-commit `device-build-registry.md` or governance docs

---

## 7. Quick reference — rejected forever

- pxpipe
- OmniRoute as primary gateway
- Ruflo `--dual` / `--all-agents` / daemon / memory
- Claude-mem → OpenKnowledge auto-sync
- Codex auto stop-gate

Reopen only by Captain decision doc.
