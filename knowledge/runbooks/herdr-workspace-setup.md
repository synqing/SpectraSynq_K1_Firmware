---
title: Herdr Workspace Setup (Manual Install)
status: draft
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - docs/agent-stack/PHASED-ROLLOUT.md Phase 1
owner: knowledge-curator
---

# Herdr Workspace Setup

**Phase 1 tasks P1-01, P1-02.** Agents **execute** install and workspace creation on the operator machine (autonomous default). Captain is only needed for org-wide AGPL fleet decisions (P0-06).

## Role

Herdr is the **human supervision console** — fleet visibility and checkpoint
sign-off. It is **not** execution authority for agent work.

## Preconditions

- [ ] Phase 0 exit gate PASS ([`agent-stack-authority-ratified-2026-07-13.md`](../decisions/agent-stack-authority-ratified-2026-07-13.md))
- [ ] AGPL review complete for org deploy scope (P0-06) — defer org-wide if unresolved

## Install (autonomous default)

```bash
brew install herdr
herdr server &   # or: brew services start herdr
herdr workspace create --cwd "$(git rev-parse --show-toplevel)" \
  --label "SpectraSynq_K1_Firmware" --no-focus
herdr workspace list
```

1. **One workspace** per git repository (K1: label `SpectraSynq_K1_Firmware`, cwd repo root).
2. Do **not** route firmware builds, PIO uploads, or agent execution through Herdr.

Live proof: [`knowledge/research/phase1-herdr-proof.md`](../research/phase1-herdr-proof.md).

## Verification checklist

| Check | Expected |
|-------|----------|
| Workspace path | Points at K1 Firmware repo root |
| Agent execution | Agents still run in Cursor/Claude Code/Codex directly |
| Human checkpoints | Captain can review lane status in Herdr when configured |

## Evidence for Phase 1 exit gate

- [`knowledge/research/phase1-herdr-proof.md`](../research/phase1-herdr-proof.md) (`herdr workspace list`, server status).

## Rollback

Close or delete the Herdr workspace. No agent dependency — safe to remove anytime.

## Forbidden

- Using Herdr as primary agent orchestrator (use Ruflo pilot worktree only, Phase 4)
- Org-wide Herdr deploy without AGPL review (P0-06)
