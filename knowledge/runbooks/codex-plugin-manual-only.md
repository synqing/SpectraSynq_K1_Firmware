---
title: Codex Plugin — Manual Invocation Only
status: draft
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - docs/agent-stack/SWARM-ORCHESTRATION.md
owner: knowledge-curator
---

# Codex Plugin — Manual Invocation Only

**Phase 1 tasks P1-03, P1-04, P1-05.** Agents **install and audit** the plugin autonomously; **invocation** of Codex remains manual (no auto stop-gate).

## Plugin

`openai/codex-plugin-cc` — Claude Code ↔ Codex transfer for review, adversarial
pass, rescue, and scoped handoff.

## Install (autonomous default)

```bash
claude plugin marketplace add openai/codex-plugin-cc
claude plugin install codex@openai-codex -s user
claude plugin list | rg codex
```

Audit log: [`knowledge/research/phase1-codex-plugin-audit.md`](../research/phase1-codex-plugin-audit.md).

## Configuration audit — CRITICAL

### DO NOT enable auto stop-gate

| Setting | Required value |
|---------|----------------|
| Auto stop-gate | **DISABLED / OFF** |
| Silent Codex takeover | **FORBIDDEN** |
| Codex flash/upload | **FORBIDDEN** |

**Auto stop-gate** means Codex intercepts Claude Code without Captain intent.
This is a **hard rejection** per authority contract.

Record audit evidence for P1-05 (agent-executed):

```bash
node ~/.claude/plugins/marketplaces/openai-codex/plugins/codex/scripts/codex-companion.mjs setup --json
# reviewGateEnabled must be false
```

See [`phase1-codex-plugin-audit.md`](../research/phase1-codex-plugin-audit.md).

## Allowed use cases (manual invoke only)

1. **Second-opinion / adversarial review** — docs or code PR review bundle
2. **Scoped implementation transfer** — rescue lane with explicit contract
3. **Cross-tool handoff** — context bundle per [`SWARM-ORCHESTRATION.md`](../../docs/agent-stack/SWARM-ORCHESTRATION.md)

## Handoff bundle minimum

Every manual Codex invocation must include:

- Git branch + HEAD SHA
- Lane scope statement
- Explicit acknowledgment of [`AGENT_OS.md`](../../AGENT_OS.md) firmware safety rules
- List of files in scope
- Success criteria

## Forbidden

- Enabling auto stop-gate (global or per-repo)
- Codex editing authority contract or gate scripts without Captain approval
- Codex flash/upload/erase on K1 hardware
- Bypassing pre-commit gate assumptions

## Rollback

Uninstall or disable the Codex plugin. Claude Code remains primary executor.

## First exercise (P1-08)

Run one **manual** adversarial review on a docs-only PR. Archive handoff artifact;
Captain rates usefulness 1–5.
