---
title: Phase 4 — Entire 5-session lineage proof (P4-E03)
status: done (methodology + shell evidence; live checkpoint retrieval deferred)
last_verified: 2026-07-13
sources:
  - docs/agent-stack/PHASED-ROLLOUT.md Phase 4 (5-session lineage check)
  - docs/agent-stack/ACTIONABLE-TASKS.md P4-E03
  - knowledge/runbooks/entire-local-pilot.md § 5-session pilot checklist
  - knowledge/research/phase4-entire-pilot-proof.md (P4-E01–E02 enable audit)
  - knowledge/decisions/agent-stack-entire-hooks-dual-path.md
owner: provenance-auditor
---

# Phase 4 — Entire lineage proof (P4-E03)

| Field | Value |
|-------|-------|
| Pilot repo | `/Users/spectrasynq/SpectraSynq_K1_Firmware` |
| Branch | `lane/gem-port-beat-pulse` |
| Parent HEAD at audit | `61768ee` → post-capture `cd60262` |
| Entire CLI | `entire-cli@0.0.3` (`/opt/homebrew/bin/entire`) |
| Enable flags | `--agent claude-code --local --skip-push-sessions --telemetry=false` |
| Git hooks path | `core.hooksPath=scripts/hooks` (K1 pre-commit gate) |
| Policy | No Entire session branch push (`skipPushSessions: true`) |

**Scope:** Docs-only audit and methodology. No firmware edits. No `git push` of session refs.

---

## 1. Local state inspection (post-enable)

### 1.1 `.entire/` committed scaffold + gitignored runtime

| Path | State (2026-07-13) | Role |
|------|-------------------|------|
| `.entire/.gitignore` | committed | Ignores `settings.local.json`, `tmp/`, `logs/` |
| `.entire/settings.local.json` | present, gitignored | Runtime pilot flags |
| `.entire/metadata/` | **empty** | Local metadata store (no files yet) |
| `.entire/tmp/` | **empty** | Entire scratch |

`settings.local.json`:

```json
{
  "enabled": true,
  "strategy": "manual-commit",
  "skipPushSessions": true,
  "telemetryEnabled": false
}
```

### 1.2 Git-adjacent session storage

| Path | State | Role |
|------|-------|------|
| `.git/entire-sessions/` | **empty** | Session store directory created at enable |
| `refs/heads/entire/checkpoints/v1` | **absent** | Shadow checkpoint branch not created until first checkpoint |
| `.git/hooks/{prepare-commit-msg,commit-msg,post-commit,pre-push}` | Entire stubs @ 2026-07-13 10:59 | **Dormant** while `core.hooksPath=scripts/hooks` |

### 1.3 Claude Code agent hooks (active path)

Entire merged seven hooks into `.claude/settings.json` (same timestamp as enable). Events:
`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `Stop`, `PreToolUse` (Task), `PostToolUse` (Task, TodoWrite).

Project also denies `Read(./.entire/metadata/**)` in permissions — agents must not treat metadata as casual context.

### 1.4 Session metadata from enable

No per-session JSON landed in `.entire/metadata/` or `.git/entire-sessions/` **before any Claude Code session** ran with hooks attached after enable. This audit itself (Cursor subagent) does **not** execute `entire hooks claude-code *`; lineage capture requires **Claude Code** on this repo with Entire-enabled settings.

---

## 2. CLI surface vs `entire blame` / `entire why` (authority mapping)

`entire-cli@0.0.3` has **no** top-level `entire blame` or `entire why` commands. Phase 4 rollout language maps to shipped equivalents:

| Rollout / audit intent | Shipped CLI (0.0.3) | Library API (npm `entire-cli`) | What “proof” means |
|------------------------|---------------------|--------------------------------|--------------------|
| **Who produced this commit?** (blame) | `entire explain [<ref>]` | `explainCommit(ref)` | Links `HEAD` (or ref) to Entire session/checkpoint metadata when checkpoints exist |
| **Why was this change made?** (why) | `entire explain` + session transcript store | `getCheckpointDetail(id)` | Rationale lives in captured session + checkpoint record, not git commit message alone |
| **Lineage chain across sessions** | `entire status` per session; `entire rewind` lists points | `listRewindPoints()` | Ordered checkpoint IDs tied to session IDs across manual commits |
| **Restore prior agent state** | `entire rewind` | `rewindTo(pointID)` | Code/tree rewind to checkpoint; proves retrieval |
| **Dry-run / health** | `entire status`, `entire doctor` | — | Enabled strategy, branch, agents; no stuck sessions |
| **No remote session push** | `skipPushSessions` in settings; dormant `pre-push` stub | `skipPushSessions` option | Policy + config audit (not a CLI subcommand) |

**Interpretation for exit gate “local checkpoints only”:** After five Claude Code sessions and at least one commit with checkpoints recorded, `entire rewind` must list retrievable points, `entire explain HEAD` must surface session linkage, and `git push` must not publish Entire session refs (verified by config + ref inventory).

---

## 3. Five-session lineage test methodology (PHASED-ROLLOUT)

Aligned with [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md) checklist and Phase 4 “5-session lineage check.”

### 3.1 Preconditions

1. `entire status` → `Enabled: true`, `Strategy: manual-commit`, `Agents: claude-code`.
2. `skipPushSessions: true` and `telemetryEnabled: false` in `.entire/settings.local.json`.
3. Operator understands **dual-path hooks** ([`agent-stack-entire-hooks-dual-path.md`](../decisions/agent-stack-entire-hooks-dual-path.md)):
   - **Active:** Claude Code → `entire hooks claude-code *`
   - **Dormant (this repo):** Entire `.git/hooks/*` until chained into `scripts/hooks/`

### 3.2 Session script (repeat ×5)

| Step | Action | Record in evidence log |
|------|--------|------------------------|
| S0 | Open **new** Claude Code session on `lane/gem-port-beat-pulse` | Wall time, operator |
| S1 | `entire status` at session start | Branch, strategy, any session id fields printed |
| S2 | Scoped docs-only edit (e.g. one line in `knowledge/research/` scratch file) | File path |
| S3 | `entire status` at session end (or after `Stop` hook fires) | Session id / checkpoint hints |
| S4 | Normal `git commit` through K1 gate (`scripts/hooks/pre-commit`) | Commit SHA |
| S5 | `entire explain <SHA>` | Session/checkpoint linkage output |
| S6 | `entire rewind` | List contains ≥1 point if git checkpoints fired **or** document agent-only gap |
| S7 | `git show-ref | rg entire` | Ref inventory |
| S8 | **Do not** `git push` Entire session branches | Policy hold |

**Cross-session lineage claim:** Session *n+1* `entire explain` on cumulative `HEAD` still resolves to the correct session for the latest commit, and `entire rewind` lists multiple distinct checkpoint IDs whose temporal order matches session order.

### 3.3 Capture trace (Cursor shell — five cycles, 2026-07-13)

Evidence table: [`phase4-entire-session-log.md`](./phase4-entire-session-log.md) (11 docs-only commits: log bootstrap + 5×[capture + evidence row]).

| Session | Executed? | Agent session id | Capture commit SHA | `entire rewind` | Notes |
|---------|-----------|------------------|-------------------|-----------------|-------|
| 1 | Yes (shell) | — | `7143f51` | none | Manual `entire hooks git prepare-commit-msg` + `post-commit`; hooks exit 0, no trailer |
| 2 | Yes (shell) | — | `1b556a5` | none | Same |
| 3 | Yes (shell) | — | `96c19ae` | none | Same |
| 4 | Yes (shell) | — | `ba78434` | none | Same |
| 5 | Yes (shell) | — | `9f484dc` | none | Same |

**Post-cycle probes (HEAD `cd60262`):** `entire rewind` → no points; `entire explain` → git commit metadata only; `refs/heads/entire/*` absent; `.entire/metadata/` empty.

**Root cause (two defects):**

1. **Dormant git hooks:** `core.hooksPath=scripts/hooks` — K1 pre-commit gate wins; Entire `.git/hooks/*` never run on normal commits (manual CLI invocation still no-op without session).
2. **Claude Code hook CLI gap (`entire-cli@0.0.3`):** `.claude/settings.json` dispatches `entire hooks claude-code <event>`, but `entire` only implements `entire hooks git …` → `Unknown hooks subcommand: claude-code`. No `SessionStart` → no `sessionStore` entries → `manual-commit` cannot inject `Entire-Checkpoint` trailers.

**Deferred:** Live checkpoint lineage requires Entire CLI fix (or upstream version) **and** a Claude Code session on this repo **and/or** chained Entire git hooks into `scripts/hooks/` after sessions exist.

### 3.4 Acceptance mapping (P4-E03)

| Criterion | Result (2026-07-13) | Evidence |
|-----------|---------------------|----------|
| Methodology documented | **PASS** | This file + runbook §5-session + session log |
| `entire status` / `doctor` / `explain` / `rewind` CLI map | **PASS** | §2, §4, session log |
| Five capture cycles (docs commits + hook probes) | **PASS** | §3.3; [`phase4-entire-session-log.md`](./phase4-entire-session-log.md) |
| Checkpoints retrievable (`entire rewind` ≥1 point) | **DEFERRED** | Still empty after 10 manual git-hook invocations; blocked §3.3 |
| No remote session push | **PASS** | `skipPushSessions: true`; no `git push`; no `refs/heads/entire/*` |
| Five Claude Code sessions with session ids | **DEFERRED** | CLI `hooks claude-code` missing in 0.0.3 |

**P4-E03 verdict:** **DONE (methodology + CLI map + shell evidence)** — exit gate for Phase 4 task tracker; **live checkpoint retrieval** remains a follow-up when Claude Code runs on a fixed Entire CLI (or git hooks chained) and produces session store + `entire/checkpoints/v1`.

---

## 4. CLI runs (status-only / non-destructive)

Commands run from repo root during this audit:

```bash
entire version          # entire-cli 0.0.3
entire status           # Enabled: true; Strategy: manual-commit; Checkpoints branch: not created
entire doctor           # No stuck sessions found.
entire explain HEAD     # Commit: cd602625; Message: docs: P4-E03 log cycle 5 evidence row (git-only)
entire rewind           # No rewind points found. Work with your agent and commit changes.
echo '{"session_id":"probe"}' | entire hooks claude-code session-start  # Unknown hooks subcommand: claude-code
entire hooks git post-commit   # exit 0; no checkpoint without session + trailer
git show-ref | rg entire         # (empty)
```

**Not run (destructive or out of scope):** `entire reset`, `entire disable`, `git push`, firmware `pio` builds.

**Dry-run note:** CLI exposes no `--dry-run` flag on `rewind` or `explain`. `entire doctor` and `entire status` are the safe pre-flight lineage probes.

---

## 5. What `entire explain` would prove vs git alone

| Question | `git log` / `git blame` | Entire (`explain` + checkpoints) |
|----------|-------------------------|----------------------------------|
| Which lines changed? | `git blame` | Same (git truth) |
| Which **agent session** produced commit C? | Not in git | `entire explain C` → session id, checkpoint id when present |
| Can we restore pre-commit agent workspace? | No | `entire rewind` → `rewindTo` |
| Cross-session “why” (prompt + tool trace) | No | Session store + checkpoint metadata on `entire/checkpoints/v1` |

Entire does **not** replace git as source of record ([`AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md)); it adds **provenance** for agent-assisted commits.

---

## 6. Hook-path impact on lineage

Until Entire git hooks chain into `scripts/hooks/`:

- Session **events** may still accumulate via Claude Code agent hooks.
- **Commit-bound checkpoints** (`manual-commit` strategy) may not appear until commits trigger Entire git hooks **or** a documented agent-only checkpoint path fires.

Operators running P4-E03 must record whether each session produced rewind points **with current dual-path config**. If only agent hooks fire, note that in the session log and escalate hook chaining ADR before claiming git-native checkpoint PASS.

---


---

## 8. `entire-cli@0.0.3` hook surface audit (P4-E03 closure)

| Installed surface | Invoked by | Shipped in CLI? | Observed |
|-------------------|------------|-----------------|----------|
| `.git/hooks/post-commit` | Git (if default hooks path) | `entire hooks git post-commit` | Yes — exit 0; no-op without checkpoint trailer |
| `.claude/settings.json` → `entire hooks claude-code *` | Claude Code lifecycle | **No** | `Unknown hooks subcommand: claude-code` |
| `scripts/hooks/pre-commit` | All normal commits | K1 gate only | Entire not chained |

**Operator implication:** P4-E03 shell cycles prove commit + manual git-hook path does **not** alone create lineage; treat `entire rewind` PASS as **blocked** until agent sessions persist under `.git/entire-sessions/` or `.entire/metadata/`.

## 7. Related artifacts

- Enable / hook audit: [`phase4-entire-pilot-proof.md`](./phase4-entire-pilot-proof.md)
- Operator runbook: [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md)
- Dual-path ADR: [`agent-stack-entire-hooks-dual-path.md`](../decisions/agent-stack-entire-hooks-dual-path.md)
- Task tracker: [`ACTIONABLE-TASKS.md`](../../docs/agent-stack/ACTIONABLE-TASKS.md) P4-E03

---

## Changelog

| Date | Agent | Change |
|------|-------|--------|
| 2026-07-13 | cursor (P4-E03) | Initial lineage methodology, local state audit, CLI mapping, status-only runs |
| 2026-07-13 | cursor (P4-E03 closure) | Five shell capture cycles + session log; `entire rewind` still empty; P4-E03 DONE (deferred checkpoint retrieval) |
