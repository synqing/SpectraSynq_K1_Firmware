---
title: Entire CLI — Local pilot (Phase 4)
status: draft
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - docs/agent-stack/PHASED-ROLLOUT.md Phase 4
  - knowledge/research/phase4-entire-pilot-proof.md
  - knowledge/decisions/agent-stack-entire-hooks-dual-path.md
  - knowledge/decisions/agent-stack-entire-cli-limitation-2026-07-13.md
owner: knowledge-curator
---

# Entire CLI — Local pilot

Controlled **commit/session provenance** pilot for AI agent work. Entire does **not** replace git, pytest/PIO gates, or `knowledge/` authority.

## Install

```bash
npm install -g entire-cli@0.0.3   # pin: registry latest = 0.0.3 (verified 2026-07-13)
entire --version                    # expect entire-cli 0.0.3
```

Requires Node.js ≥ 18 and Git.

**Version policy:** Stay on `0.0.3` until `npm view entire-cli version` reports a newer release **and**
`entire hooks claude-code session-start` succeeds on a probe payload (see limitation ADR below).

## Enable (authority-pinned flags)

Run from the **pilot repo root** only:

```bash
entire enable --agent claude-code --local --skip-push-sessions --telemetry=false
```

| Flag | Intent |
|------|--------|
| `--agent claude-code` | Session hooks in `.claude/settings.json` |
| `--local` | Local settings under `.entire/` (sensitive paths gitignored) |
| `--skip-push-sessions` | **No** Entire session branches pushed to remote |
| `--telemetry=false` | No Entire telemetry |

Verify:

```bash
entire status
entire doctor
```

Proof log: [`phase4-entire-pilot-proof.md`](../research/phase4-entire-pilot-proof.md).

## Entire vs git vs OpenKnowledge vs Claude-mem

| Need | Use | Do not use |
|------|-----|------------|
| Merged code truth, CI, releases | **Git** + normal PR workflow | Entire as sole record |
| Ratified decisions, runbooks | **`knowledge/`** (markdown pilot; MCP optional later) | Entire transcripts as ADR |
| Episodic recall across sessions | **Claude-mem** (search budget per `claude-mem-compact-injection.md`) | Entire instead of mem for “what did we try last week?” |
| Agent session lineage, rewind to checkpoint | **Entire** (pilot repo) | Remote session push; replacing git log |

Promotion path unchanged: Claude-mem → human review → `knowledge/decisions/` → git commit (manual).

## K1 firmware hook collision (critical)

**Verified ADR:** [`agent-stack-entire-hooks-dual-path.md`](../decisions/agent-stack-entire-hooks-dual-path.md) — dual-path model, collision mitigation, P4-E05 go record.

This repo sets:

```bash
git config core.hooksPath   # → scripts/hooks
```

The K1 **pre-commit gate** lives at `scripts/hooks/pre-commit`. Entire installs git hooks under **`.git/hooks/`**, which Git **does not run** while `core.hooksPath` is set.

| Symptom | Cause |
|---------|--------|
| `entire status` says git hooks installed | Files exist under `.git/hooks/` |
| No checkpoint on commit | Entire git hooks never invoked |

**Pilot stance (ratified 2026-07-13):** Session capture via **Claude Code hooks** in `.claude/settings.json`. Entire `.git/hooks` stubs remain **inactive**; K1 gate wins. For git-native checkpoints, chain Entire into `scripts/hooks` (future optional — not required for pilot go).

## Operator commands

| Command | When |
|---------|------|
| `entire status` | Confirm enabled, branch, agents |
| `entire rewind` | Browse/restore checkpoints |
| `entire explain` | Session or commit detail |
| `entire disable` | End pilot / rollback hooks |
| `entire reset` | Clear shadow branch + session state (destructive — use with care) |

## Forbidden (Phase 4)

- Pushing Entire session branches (`--skip-push-sessions` must stay true)
- Treating Entire as firmware or AP/VP source of truth
- Enabling Entire on production release branches without Captain go/no-go — **P4-E05 PASS** (autonomous go 2026-07-13; lane pilot only)
- Auto-sync from Entire into `knowledge/`

## Claude Code hooks (known limitation — blocks P4-E03 rewind)

**Verified ADR:** [`agent-stack-entire-cli-limitation-2026-07-13.md`](../decisions/agent-stack-entire-cli-limitation-2026-07-13.md).

`entire-cli@0.0.3` enables `--agent claude-code` and writes `.claude/settings.json` dispatchers, but the CLI
**does not implement** `entire hooks claude-code`:

```bash
entire hooks claude-code --help   # no hooks tree; prints top-level help
echo '{}' | entire hooks claude-code session-start
# → Unknown hooks subcommand: claude-code (exit 1)
```

| Expectation (enable output) | Runtime on 0.0.3 |
|-----------------------------|------------------|
| SessionStart/End, prompt/tool hooks | **Broken** — subcommand missing |
| Session store + `entire rewind` | **Deferred** — no agent hook persistence |
| P4-E03 five-session proof | **DONE (methodology)** — see [`phase4-entire-session-log.md`](../research/phase4-entire-session-log.md) |

`entire hooks git <hook>` commands exist (e.g. `post-commit` exit 0) but with `core.hooksPath=scripts/hooks`
they are **not** invoked on commit and **do not** alone create rewind points in pilot evidence.

**Retest:** After upgrading past 0.0.3, log results in `knowledge/research/phase4-entire-upgrade-retest.md`.

## Codex (known limitation)

`entire-cli@0.0.3` has **no Codex agent integration** — no `--agent codex`, no Codex hook installer.
Upstream README lists Claude Code, Cursor, Gemini CLI, and OpenCode only. **Do not attempt** Codex Entire enable.

Codex remains **manual** per [`codex-plugin-manual-only.md`](./codex-plugin-manual-only.md). Recorded in
[`agent-stack-entire-hooks-dual-path.md`](../decisions/agent-stack-entire-hooks-dual-path.md) § Known limitation.

## 5-session pilot checklist (P4-E03)

**Status (2026-07-13):** Methodology + five shell capture cycles **complete**; **live rewind checkpoints deferred**
until `entire hooks claude-code` ships. See limitation ADR and [`phase4-entire-lineage-proof.md`](../research/phase4-entire-lineage-proof.md).

1. Enable Entire (above).
2. Run five distinct Claude Code sessions on the pilot branch *(blocked on 0.0.3 — hooks subcommand missing)*.
3. After each session, `entire status` and note session id.
4. Make at least one normal git commit per session where applicable; confirm checkpoint branch appears when git hooks are active (or document agent-only capture if hooks remain dormant).
5. `entire rewind` — confirm at least one retrievable checkpoint *(deferred on 0.0.3)*.
6. `git push` — confirm **no** Entire session refs pushed (policy).

Record results in [`phase4-entire-pilot-proof.md`](../research/phase4-entire-pilot-proof.md) and session rows in
[`phase4-entire-session-log.md`](../research/phase4-entire-session-log.md).

## Rollback

```bash
entire disable
entire doctor
```

Confirm `.claude/settings.json` no longer dispatches to `entire hooks claude-code *` if pilot ends.
