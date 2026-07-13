---
title: Agent stack rollout — closure (standard stack v1)
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/STANDARD-STACK.md
  - knowledge/decisions/agent-stack-standard-stack-2026-07-13.md
  - knowledge/research/phase6-scorecard.md
owner: knowledge-curator
---

# Agent stack rollout COMPLETE (v1)

Phases 0–6 closed 2026-07-13. **Canonical manifest:**
[`docs/agent-stack/STANDARD-STACK.md`](../../docs/agent-stack/STANDARD-STACK.md).

## Session bootstrap (hygiene pass)

```bash
bash scripts/agent/session-bootstrap.sh
```

| Field | Value |
|-------|-------|
| Date | 2026-07-13 |
| Exit code | **0** |
| Branch | `lane/gem-port-beat-pulse` |
| HEAD | `168c096` (closure commit) |
| repo-truth | WARN (uncommitted `device-build-registry.md`; non-blocking for docs-only hygiene) |

## What ships

- **Adopted:** Herdr, Codex plugin (manual), sqlite-utils, OpenKnowledge MCP, `knowledge/` scaffold, routing + promote-learning skills, Claude-mem coexistence policy
- **Closed unpromoted:** Entire CLI (npm `0.0.3`), Ruflo orchestration-only pilot
- **Headroom:** compression benchmark PASS; **operational qualification pending** — not in standard stack
- Onboarding: [`knowledge/runbooks/agent-onboarding.md`](../runbooks/agent-onboarding.md)
- Promotion decision: [`agent-stack-standard-stack-2026-07-13.md`](../decisions/agent-stack-standard-stack-2026-07-13.md)

Firmware lanes remain governed by [`AGENT_OS.md`](../../AGENT_OS.md) and active handoff — agent-stack rollout is lane-orthogonal.


## Final commit

| Field | Value |
|-------|-------|
| `final_commit_sha` | `7f6f1ba44ed749c73d1bf45286b4e0fc19833aff` |

## Post-commit verification (2026-07-13)

*(Captured after closure commit — see parent handoff.)*

### Entire smoke (local only)

```text
npm view entire-cli version → 0.0.3 (latest on registry 2026-07-13)
entire status → Enabled; Agents: claude-code; skipPushSessions via .entire/settings.local.json
entire doctor → No stuck sessions
```

Official enable path (upstream README): `entire enable --agent claude-code`. npm `0.0.3` hook CLI gap documented in [`agent-stack-entire-cli-limitation-2026-07-13.md`](../decisions/agent-stack-entire-cli-limitation-2026-07-13.md).

### Verification matrix

| Check | Result |
|-------|--------|
| `git status` after closure commit | **PASS** — rollout paths clean; firmware/registry/platformio remain dirty/untracked (excluded by design) |
| `bash scripts/agent/session-bootstrap.sh` | **PASS** exit 0; repo-truth WARN (device-build-registry dirty); ok-scope PASS |
| `bash scripts/agent/ok-scope-check.sh` | **PASS** exit 0 |
| `herdr --version` | **PASS** 0.7.3 |
| `sqlite-utils --version` | **PASS** 3.39 |
| `headroom --version` | **PASS** 0.31.0 (benchmark reference; not standard stack) |
| `entire --version` | **PASS** 0.0.3 (npm latest 2026-07-13) |
| `entire status` / `entire doctor` | **PASS** enabled, claude-code agent, no stuck sessions; skipPushSessions local |
| `npx @inkeep/open-knowledge@0.29.1 --version` | **PASS** (GPL banner; package resolves) |
| `claude plugin` codex | **PASS** `codex@openai-codex` installed |
| No `.claude-flow/` in repo | **PASS** |
| No ruflo daemons / `/tmp/ruflo-pilot-k1` | **PASS** |
| User-global open-knowledge MCP | **PASS** ok-scope-check |
| Hook duplication | **PASS** — pre-commit sole commit gate; Entire git hooks dormant; settings.json Entire hooks fail on 0.0.3 (no double fire) |

### Hook duplication

See [`agent-stack-entire-hooks-dual-path.md`](../decisions/agent-stack-entire-hooks-dual-path.md) § Hook duplication audit — `scripts/hooks/pre-commit` authoritative; Entire git hooks dormant; `.claude/settings.json` Entire hooks non-functional on npm 0.0.3.
