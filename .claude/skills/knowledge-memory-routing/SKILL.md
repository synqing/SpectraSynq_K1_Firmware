---
name: knowledge-memory-routing
description: "Route agent queries to the correct authority source — code/tests for implementation truth, knowledge/ for durable decisions, Claude-mem for episodic history; promotion not sync"
---

# Knowledge & Memory Routing

Load this skill at session start for any task involving **prior decisions**, **runbooks**,
**architecture context**, or **"what did we do last time?"** questions.

Authority contract: [`docs/agent-stack/AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md)

## Golden rule

**Promotion, not synchronization.** Claude-mem observations enter `knowledge/` only
through the explicit promotion workflow in
[`SWARM-ORCHESTRATION.md`](../../docs/agent-stack/SWARM-ORCHESTRATION.md) § Promotion.
Never auto-dump session history into curated knowledge.

---

## Routing table

| Question type | Authority | Action |
|---------------|-----------|--------|
| What does the system **do** right now? | **Code + tests + git** | Read source; run pytest/PIO as needed; verify branch/HEAD |
| What are the **rules**? | `AGENT_OS.md`, `AGENTS.md`, `.claude/CLAUDE.md` | Follow safety gates; do not rewrite from memory |
| What did we **decide** (durable)? | **`knowledge/`** (OpenKnowledge pilot) | Check `decisions/`; require `status: verified` + fresh `last_verified` |
| What happened **last session** / prior bug? | **Claude-mem** | `search` → `timeline` → `get_observations` |
| What is the **active lane**? | **Git + AGENT_OS.md** | Verify branch; treat handoff/progress as stale if repo-truth WARN/FAIL |
| Human **checkpoint**? | **Herdr + Captain** | Supervision only; not execution authority |
| Second implementer? | **Codex plugin** | Manual handoff bundle only; auto stop-gate forbidden |
| Parallel lanes (pilot)? | **Ruflo isolated worktree** | Orchestration-only; Phase 4+ |

---

## Precedence when sources conflict

1. Git branch + HEAD + working tree
2. `platformio.ini` + upload guards
3. Lane-specific docs (if repo-truth fresh)
4. `AGENT_OS.md` + `.claude/CLAUDE.md` + `AGENTS.md`
5. OpenKnowledge (`knowledge/`, `status: verified`, recent `last_verified`)
6. Claude-mem (historical context only)
7. Session chat (lowest — never authoritative)

---

## Conflict reporting rule

When two sources disagree, **stop and report** before acting:

1. Name both sources and the specific conflict (quote paths/SHAs).
2. State which source wins per precedence above.
3. If `knowledge/` conflicts with code/tests → **code wins**; file bug or schedule knowledge update.
4. If Claude-mem conflicts with git lane → **git wins**; cite mem as historical hypothesis only.
5. If lane docs are stale per `repo-truth.sh` → report stale; do not silently "fix" governance docs.

Do not average contradictions. Do not pick the convenient source.

---

## Read paths (quick)

```
Implementation     → SPECTRASYNQ_K1_FIRMWARE/, tests/, git status
Process            → AGENT_OS.md, .claude/CLAUDE.md
Durable knowledge  → knowledge/index.md → decisions/ | runbooks/
Episodic history   → claude-mem MCP search/timeline
Agent stack plan   → docs/agent-stack/README.md
```

---

## Anti-patterns (forbidden)

- Treating Claude-mem as current lane truth
- Auto-syncing Claude-mem → `knowledge/`
- Treating `knowledge/` as override for implemented behavior
- Citing `status: draft` or stale `last_verified` decisions without flagging uncertainty
- Enabling Codex auto stop-gate

---

## Related skills (Phase 3+)

- `promote-learning` — step-by-step promotion workflow (`.claude/skills/promote-learning/SKILL.md`)
- `/spec-recall` — lane recall via spec-index + claude-mem
