---
name: memory-authority-gate
description: Run when claude-mem seems empty, stale, offline, or contradicts launch docs. Executes memory-preflight, applies Decision Authority Firewall (DAF), and routes agents to Tier 0 docs instead of re-litigating locks from episodic memory.
---

# Memory Authority Gate

Use when claude-mem search returns zero, SessionStart warns about pipeline health, or memory contradicts `LAUNCH_TRUTH.md`.

## Automatic wiring

**SessionStart** (Claude Code + Codex): `~/.claude-mem/hooks/memory-authority-session-start.py`

**Mid-session (P2)** — debounced recheck + claude-mem tool failure detection:
- `UserPromptSubmit` → `memory-authority-user-prompt.py` (every 12 prompts NOMINAL / 3 DEGRADED; immediate on memory or launch keywords)
- `PostToolUse` / `PostToolUseFailure` → `memory-authority-post-mem-tool.py` when claude-mem tools fail or return suspicious empty results

Session state: `~/.claude-mem/state/memory-authority-{session_id}.json`

Cursor: rule `010-memory-authority.mdc` is always applied in this workspace.

## Manual preflight

```bash
~/.claude-mem/memory-preflight.sh
```

First line: `MEMORY_MODE=NOMINAL|DEGRADED|OFFLINE`

## Agent posture by mode

| Mode | Posture |
|------|---------|
| `NOMINAL` | Memory is Tier 2 clues; Tier 0 still binds launch locks |
| `DEGRADED` | `MEMORY_DEGRADED: true` — no launch decisions from memory alone |
| `OFFLINE` | Ignore claude-mem for authority; Tier 0 + Tier 1 only |

## Tier 0 reads (launch work)

1. `LAUNCH_TRUTH.md`
2. `docs/LAUNCH_LOCKS.yaml`
3. `docs/FE_AUTHORITY.md` (surface roles)
4. `DESIGN.md` (visual/copy locks)

Policy: `~/.claude/memory/spectrasynq/L1/MEMORY_AUTHORITY_CONTRACT.md`

## Common false alarms

- `/api/pending-queue` returns **404** on claude-mem 13.x — **expected**; use `/api/processing-status`
- Compound FTS queries return zero — run **single-term** searches separately
- `invalid_cwd` in logs — capture skipped for that cwd; not global outage

## Stop gate

Do not canonise a launch claim from claude-mem alone. Re-read Tier 0 first.
