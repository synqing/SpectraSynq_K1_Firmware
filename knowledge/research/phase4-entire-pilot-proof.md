---
title: Phase 4 — Entire CLI enable and hook audit proof
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/ACTIONABLE-TASKS.md P4-E01..E02
  - docs/agent-stack/AUTHORITY-CONTRACT.md § Entire pilot boundaries
  - docs/agent-stack/PHASED-ROLLOUT.md Phase 4
owner: implementer
---

# Phase 4 — Entire CLI pilot proof (2026-07-13)

Autonomous pilot workspace: **`/Users/spectrasynq/SpectraSynq_K1_Firmware`** on branch `lane/gem-port-beat-pulse` @ `61768ee`. No session branches pushed (`skipPushSessions: true`).

## Install outcome: **PASS**

| Step | Command | Result |
|------|---------|--------|
| Pre-check | `which entire` | not found |
| Install | `npm install -g entire-cli@0.0.3` | **PASS** → `/opt/homebrew/bin/entire` |
| Version | `entire --version` | `entire-cli 0.0.3` |
| Upstream | npm package README | Implements [entireio/cli](https://github.com/entireio/cli) session/checkpoint model |

**Codex agent:** `entire-cli@0.0.3` ships **claude-code** integration only (README lists Claude Code, Cursor, Gemini CLI, OpenCode — **no Codex**). Pilot used `--agent claude-code` per authority contract; Codex enable **not attempted**.

## Enable outcome: **PASS**

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
entire enable --agent claude-code --local --skip-push-sessions --telemetry=false
```

```
Entire enabled.
  Agent: claude-code
  Git hooks installed: 4
  Agent hooks installed: 7
```

| Check | Command output | Verdict |
|-------|----------------|---------|
| Enabled | `entire status` → `Enabled: true` | PASS |
| Strategy | `manual-commit` | PASS |
| Telemetry | `telemetryEnabled: false` in `.entire/settings.local.json` | PASS |
| Skip remote sessions | `skipPushSessions: true` in settings | PASS |
| Doctor | `entire doctor` → no stuck sessions | PASS |
| Checkpoints branch | `Checkpoints branch: not created` (until first checkpoint) | expected |

### Local config (gitignored)

Path: `.entire/settings.local.json`

```json
{
  "enabled": true,
  "strategy": "manual-commit",
  "skipPushSessions": true,
  "telemetryEnabled": false
}
```

Committed scaffold: `.entire/.gitignore` ignores `settings.local.json`, `tmp/`, `logs/`.

## Hook collision audit

### Git hooks — **K1 pre-commit wins; Entire git hooks dormant**

| Setting | Value |
|---------|--------|
| `git config core.hooksPath` | `scripts/hooks` (repo-local) |

When `core.hooksPath` is set, Git runs hooks from that directory **only**; `.git/hooks/*` is not invoked for normal git operations.

Entire still wrote four stubs under `.git/hooks/`:

| Hook | Behavior |
|------|----------|
| `prepare-commit-msg` | `entire hooks git prepare-commit-msg "$@"` (errors swallowed) |
| `commit-msg` | `entire hooks git commit-msg "$1"` (**exit 1 on failure**) |
| `post-commit` | `entire hooks git post-commit` (errors swallowed) |
| `pre-push` | `entire hooks git pre-push` (errors swallowed) |

**K1 gate** remains `scripts/hooks/pre-commit` (pytest + PIO tiered gate). Entire did **not** modify `scripts/hooks/pre-commit` (mtime unchanged 2026-07-11).

**Risk:** Operators may believe Entire git checkpoint hooks are active when they are **not**, until hooks are chained (e.g. Entire dispatcher from `scripts/hooks/pre-commit` / `prepare-commit-msg`) or `core.hooksPath` is redesigned.

**Mitigation for pilot:** Rely on **Claude Code agent hooks** for session capture; use `entire rewind` / `entire explain` after commits once checkpoint branch exists; document in [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md).

### Claude Code agent hooks — **ACTIVE (7)**

Entire merged hooks into **`.claude/settings.json`** (project-local):

| Event | Command |
|-------|---------|
> **Note (npm `entire-cli@0.0.3`):** rows below mirror `.claude/settings.json` pilot template; hook CLI returns `Unknown hooks subcommand: claude-code`. Operator enable path: `entire enable --agent claude-code`.

| SessionStart | `entire hooks claude-code session-start` (non-functional on 0.0.3) |
| SessionEnd | `entire hooks claude-code session-end` |
| UserPromptSubmit | `entire hooks claude-code user-prompt-submit` |
| Stop | `entire hooks claude-code stop` |
| PreToolUse (Task) | `entire hooks claude-code pre-task` |
| PostToolUse (Task) | `entire hooks claude-code post-task` |
| PostToolUse (TodoWrite) | `entire hooks claude-code post-todo` |

**Collision note:** Pre-existing project MCP / permissions in the same file were preserved; only `hooks` block added/updated by Entire enable.

### Session storage paths (local only)

| Path | Purpose |
|------|---------|
| `.git/entire-sessions/` | Session store (empty at enable time) |
| `.entire/metadata/` | Local metadata (empty at enable time) |

No remote push performed; `pre-push` Entire hook would be dormant anyway under `core.hooksPath`.

## Pilot repo selection (P4-E01)

| Criterion | Record |
|-----------|--------|
| Repo | `SpectraSynq_K1_Firmware` (private pilot on feature lane, not default `main` release workflow) |
| Branch | `lane/gem-port-beat-pulse` |
| Policy | `--skip-push-sessions`; no Entire session branches pushed |

Authority text prefers a repo outside default firmware workflow; this pilot accepts **lane branch + local-only Entire** with explicit hook-path caveat.

## Authority boundaries (summary)

| Layer | Role | Entire touches? |
|-------|------|-----------------|
| Git history / PR truth | Source of record | No replacement; optional checkpoint branch later |
| `knowledge/` markdown | OpenKnowledge pilot (MCP optional accelerator) | No auto-sync |
| Claude-mem | Episodic recall | Coexists; Entire does not ingest claude-mem |
| Entire | Session/checkpoint provenance | Pilot only; local |

See [`AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md) and runbook [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md).

## Open items

| ID | Item | Status |
|----|------|--------|
| P4-E03 | 5-session lineage + checkpoint retrieval | **DONE (methodology + shell evidence)** — [`phase4-entire-lineage-proof.md`](./phase4-entire-lineage-proof.md) + [`phase4-entire-session-log.md`](./phase4-entire-session-log.md); five shell capture cycles; `entire rewind` empty on npm 0.0.3; live CC checkpoint retrieval **unpromoted** |
| P4-E05 | Captain go/no-go | **DONE** — autonomous go (Captain ratified 2026-07-13); see [`agent-stack-entire-hooks-dual-path.md`](../decisions/agent-stack-entire-hooks-dual-path.md) |
| Hook chaining | Entire git hooks + `scripts/hooks` | **Open** — recommend explicit chain when git-native checkpoints required; blocked on Entire CLI upgrade beyond npm 0.0.3 hook surface |

CLI limitation ADR: [`agent-stack-entire-cli-limitation-2026-07-13.md`](../decisions/agent-stack-entire-cli-limitation-2026-07-13.md).

## Rollback (verified commands)

```bash
entire disable   # removes Entire hooks; restores prior agent hook state per CLI
# Optionally: git checkout -- .claude/settings.json if Entire-only hooks must be reverted manually
```

## Runbook

- [`knowledge/runbooks/entire-local-pilot.md`](../runbooks/entire-local-pilot.md)
