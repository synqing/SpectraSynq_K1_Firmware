---
title: Agent stack — npm entire-cli@0.0.3 vs upstream Entire enable path (P4 unpromoted)
status: verified
last_verified: 2026-07-13
sources:
  - knowledge/research/phase4-entire-lineage-proof.md
  - knowledge/research/phase4-entire-session-log.md
  - knowledge/runbooks/entire-local-pilot.md
  - npm registry entire-cli (2026-07-13)
owner: knowledge-curator
---

# Decision: Accept Entire pilot closed (unpromoted); npm `0.0.3` hook surface gap vs upstream `entire enable --agent`

## Context

Phase 4 enable used the documented operator path:

```bash
entire enable --agent claude-code --local --skip-push-sessions --telemetry=false
```

(per [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md); matches upstream [entireio/cli README](https://github.com/entireio/cli) — non-interactive agent registration via `entire enable --agent <name>`.)

Repo-local `.claude/settings.json` also lists `entire hooks claude-code <event>` dispatchers (pilot template). On **npm `entire-cli@0.0.3`**, that hook CLI surface is **not implemented** — see verification table (captured output, not assumption).

Dual-path ADR still applies: K1 `core.hooksPath=scripts/hooks` keeps Entire `.git/hooks` dormant relative to K1 pre-commit; `entire hooks git post-commit` can be invoked manually but did not populate `entire rewind` in pilot evidence.

## Verification (2026-07-13)

| Check | Result |
|-------|--------|
| `npm view entire-cli version` | `0.0.3` (registry **latest**) |
| Published versions | `0.0.1`, `0.0.3` only |
| `npm install -g entire-cli@latest` | Reinstalled; still `entire-cli 0.0.3` |
| `entire --help` | No top-level `hooks` command listed |
| `entire hooks --help` / `entire hooks claude-code` | No `hooks` in `entire --help` command list; `entire hooks claude-code` → `Unknown hooks subcommand: claude-code` (exit 1) |
| `echo '{}' \| entire hooks claude-code session-start` | `Unknown hooks subcommand: claude-code` (exit 1) |
| `entire hooks git post-commit` | exit 0 (git hook path exists but does not satisfy Claude session store) |

Global binary: `/opt/homebrew/bin/entire` → `entire-cli@0.0.3`.

## Decision

1. **Pilot continues** under existing P4-E05 flags (`--local`, `--skip-push-sessions`, `--telemetry=false`).
2. **P4-E03** remains **DONE (methodology + shell evidence)** per
   [`phase4-entire-lineage-proof.md`](../research/phase4-entire-lineage-proof.md); five capture cycles logged in
   [`phase4-entire-session-log.md`](../research/phase4-entire-session-log.md).
3. **Unpromoted / retest later:** live Claude Code session store + **`entire rewind` checkpoints** after Entire CLI upgrade beyond npm `0.0.3` (Homebrew/install.sh channel may differ from npm package).
4. **Do not** disable `core.hooksPath=scripts/hooks` or claim git-native Entire checkpoints as PASS without ADR update.
5. **Re-test trigger:** when installed Entire version > npm `0.0.3` **and** `entire enable --agent claude-code` + session capture populate rewind (or documented hook surface succeeds), run
   [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md) § P4-E03 retest and record in
   `knowledge/research/phase4-entire-upgrade-retest.md` (create on first successful hook surface).

## Operator implications

- `.claude/settings.json` `entire hooks claude-code *` entries are **non-functional on npm 0.0.3** (see hook probe). Upstream may register agents via `entire enable --agent claude-code` without requiring manual hook JSON.
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
