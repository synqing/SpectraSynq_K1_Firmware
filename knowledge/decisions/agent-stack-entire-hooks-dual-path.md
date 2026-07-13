---
title: Agent stack — Entire hooks dual-path (K1 pre-commit vs session capture)
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md § Entire pilot boundaries
  - docs/agent-stack/ACTIONABLE-TASKS.md P4-E02, P4-E05
  - knowledge/research/phase4-entire-pilot-proof.md
  - knowledge/runbooks/entire-local-pilot.md
  - Captain ratification 2026-07-13 (P4-E05 autonomous go)
owner: knowledge-curator
---

# Decision: Entire hooks dual-path on K1 firmware repo

## Context

`SpectraSynq_K1_Firmware` installs the **K1 commit gate** via `git config core.hooksPath scripts/hooks`
(`scripts/hooks/install.sh`). Entire CLI `entire enable --agent claude-code` also writes git hook stubs
under `.git/hooks/` and Claude Code agent hooks into `.claude/settings.json`.

Git invokes **only** the directory named by `core.hooksPath`. With `scripts/hooks` set, Entire's
`.git/hooks/*` stubs are **present but inactive** for normal git operations. Operators may misread
`entire status` ("Git hooks installed: 4") as proof that commit-time Entire checkpoints run.

Phase 4 pilot enable used authority-pinned flags: `--local --skip-push-sessions --telemetry=false`.

## Decision

1. **K1 pre-commit gate** — remains authoritative via `core.hooksPath=scripts/hooks`.
   - `scripts/hooks/pre-commit` runs pytest + PIO tiered gate; **must not** be replaced or disabled for Entire.
2. **Entire session capture (pilot)** — operator enable: `entire enable --agent claude-code` (see runbook). Repo `.claude/settings.json` lists `entire hooks claude-code *` — **non-functional on npm `entire-cli@0.0.3`** (`Unknown hooks subcommand: claude-code`).
   - Independent of `core.hooksPath`; does **not** duplicate `scripts/hooks/pre-commit` (different lifecycle: commit gate vs session hooks).
3. **Entire `.git/hooks` stubs** — treated as **dormant** while `core.hooksPath` points at `scripts/hooks`.
   - Do not assume git-native Entire checkpoints (`prepare-commit-msg`, `commit-msg`, `post-commit`, `pre-push`)
     fire until explicitly chained (future optional work).
4. **Pilot go (P4-E05)** — Captain ratified **continue** on 2026-07-13 with binding config:
   - `--local` (`.entire/` local settings; sensitive paths gitignored)
   - `--skip-push-sessions` (no Entire session branches pushed)
   - `--telemetry=false`
   - Pilot repo: `SpectraSynq_K1_Firmware` on feature lane `lane/gem-port-beat-pulse` (not default release workflow).

## Collision mitigation

| Layer | Active path | Inactive / dormant | Mitigation |
|-------|-------------|-------------------|------------|
| Commit gate | `scripts/hooks/pre-commit` | `.git/hooks/*` Entire stubs | Bootstrap + `session-bootstrap.sh` reports `git hooks: installed (scripts/hooks)` |
| Session lineage | `entire enable --agent claude-code` | `.claude/settings.json` hook JSON (dormant on npm 0.0.3) | No duplicate firing with pre-commit; settings hooks exit 1 if invoked |
| Git checkpoints | — (dormant until chained) | Entire `prepare-commit-msg` / `post-commit` | Use `entire rewind` after commits only once checkpoint branch exists; P4-E03 tracks 5-session proof |
| Remote exposure | — | Entire `pre-push` stub | `skipPushSessions: true`; no session ref push policy |

**Operator rule:** If `entire status` reports git hooks installed **and** `git config core.hooksPath` is
`scripts/hooks`, interpret session capture as **agent-hook primary**, not git-hook primary.

**Future chaining (optional, not in pilot):** Add thin dispatchers under `scripts/hooks/` that call
Entire git hook commands after the K1 gate (e.g. `post-commit` only), without moving `core.hooksPath`.

## Known limitation: Codex unsupported in entire-cli@0.0.3

`entire-cli@0.0.3` exposes `--agent claude-code` integration only. There is **no** `--agent codex` or
Codex-native Entire hook installer. Codex remains **manual** per
[`knowledge/runbooks/codex-plugin-manual-only.md`](../runbooks/codex-plugin-manual-only.md).
Do not attempt `entire enable --agent codex` until a future Entire release documents Codex support.

## Forbidden (unchanged)

- Pushing Entire session branches (`skipPushSessions` must stay true)
- Treating Entire transcripts as `knowledge/` ADR or firmware source of truth
- Auto-sync Entire → OpenKnowledge / `knowledge/`
- Disabling `core.hooksPath=scripts/hooks` to "fix" Entire git hooks without Captain + ADR update

## Rollback

```bash
entire disable
entire doctor
```

Confirm `.claude/settings.json` no longer dispatches `entire hooks claude-code *`. K1 pre-commit gate
unaffected (`core.hooksPath` remains `scripts/hooks`).

## Evidence

- Hook audit: [`phase4-entire-pilot-proof.md`](../research/phase4-entire-pilot-proof.md) § Hook collision audit
- Operator runbook: [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md)
- Task closure: `docs/agent-stack/ACTIONABLE-TASKS.md` P4-E05 **DONE**


## Hook duplication audit (closure 2026-07-13)

| Hook surface | Fires on commit? | Fires on Claude session? | Duplicate risk |
|--------------|------------------|--------------------------|----------------|
| `scripts/hooks/pre-commit` | **Yes** (pytest + PIO tier) | No | None — sole commit gate |
| Entire `.git/hooks/*` | **No** (`core.hooksPath=scripts/hooks`) | No | Dormant stubs |
| `.claude/settings.json` → `entire hooks claude-code *` | No | Would, if CLI supported | **No firing on 0.0.3** — commands fail before side effects |

**Verdict:** K1 pre-commit and Entire pilot hooks are **dual-path by design**; no double pre-commit execution observed.
