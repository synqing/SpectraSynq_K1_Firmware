---
title: Agent stack — entire-cli@0.0.3 lacks Claude Code hooks (P4-E03 deferred)
status: verified
last_verified: 2026-07-13
sources:
  - knowledge/research/phase4-entire-lineage-proof.md
  - knowledge/research/phase4-entire-session-log.md
  - knowledge/runbooks/entire-local-pilot.md
  - npm registry entire-cli (2026-07-13)
owner: knowledge-curator
---

# Decision: Accept Entire pilot with methodology-only P4-E03; defer rewind until CLI ships `hooks claude-code`

## Context

Phase 4 enable wrote Claude Code dispatchers in `.claude/settings.json` that invoke
`entire hooks claude-code <event>`. P4-E03 closure (checkpoint `65f2233c` follow-up) required
re-testing after a global `entire-cli` upgrade in case upstream added the missing subcommand.

Dual-path ADR still applies: K1 `core.hooksPath=scripts/hooks` keeps Entire `.git/hooks` dormant;
the **intended** session capture path is Claude Code agent hooks, not git hooks.

## Verification (2026-07-13)

| Check | Result |
|-------|--------|
| `npm view entire-cli version` | `0.0.3` (registry **latest**) |
| Published versions | `0.0.1`, `0.0.3` only |
| `npm install -g entire-cli@latest` | Reinstalled; still `entire-cli 0.0.3` |
| `entire --help` | No top-level `hooks` command listed |
| `entire hooks claude-code --help` | Top-level help only; no `hooks` tree |
| `echo '{}' \| entire hooks claude-code session-start` | `Unknown hooks subcommand: claude-code` (exit 1) |
| `entire hooks git post-commit` | exit 0 (git hook path exists but does not satisfy Claude session store) |

Global binary: `/opt/homebrew/bin/entire` → `entire-cli@0.0.3`.

## Decision

1. **Pilot continues** under existing P4-E05 flags (`--local`, `--skip-push-sessions`, `--telemetry=false`).
2. **P4-E03** remains **DONE (methodology + shell evidence)** per
   [`phase4-entire-lineage-proof.md`](../research/phase4-entire-lineage-proof.md); five capture cycles logged in
   [`phase4-entire-session-log.md`](../research/phase4-entire-session-log.md).
3. **Deferred until upstream fix:** five live Claude Code sessions with session ids, `.entire/metadata/` /
   `.git/entire-sessions/` population, and **`entire rewind` retrievable checkpoints** via agent hooks.
4. **Do not** disable `core.hooksPath=scripts/hooks` or claim git-native Entire checkpoints as PASS without ADR update.
5. **Re-test trigger:** when `npm view entire-cli version` > `0.0.3` **and**
   `entire hooks claude-code session-start` exits 0 on probe JSON, run
   [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md) § P4-E03 retest and record in
   `knowledge/research/phase4-entire-upgrade-retest.md` (create on first successful hook surface).

## Operator implications

- `.claude/settings.json` Entire entries are **configured but non-functional** on 0.0.3; Claude Code sessions
  will not populate Entire session store until CLI implements `hooks claude-code`.
- Manual `entire hooks git post-commit` after commits does **not** produce rewind points under current pilot
  evidence (empty `entire rewind`; checkpoints branch not created).
- Codex limitation unchanged: no `--agent codex` in 0.0.3.

## Forbidden (unchanged)

- Pushing Entire session branches
- Treating Entire as `knowledge/` or firmware source of truth
- Auto-sync Entire → OpenKnowledge

## Evidence links

- Hook surface audit: [`phase4-entire-lineage-proof.md`](../research/phase4-entire-lineage-proof.md) § 8
- Dual-path ADR: [`agent-stack-entire-hooks-dual-path.md`](./agent-stack-entire-hooks-dual-path.md)
- Runbook pin: [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md)
