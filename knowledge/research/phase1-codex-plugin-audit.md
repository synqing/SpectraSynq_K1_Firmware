---
title: Phase 1 P1-03/P1-05 — Codex plugin audit
status: verified
last_verified: 2026-07-13
executor: agent:cursor
---

# Codex plugin (`openai/codex-plugin-cc`) — install and stop-gate audit

## Install status

| Step | Result |
|------|--------|
| Marketplace | Added: `claude plugin marketplace add openai/codex-plugin-cc` → marketplace id **`openai-codex`** |
| Plugin | Installed: `claude plugin install codex@openai-codex -s user` |
| Version | **1.0.6** (`codex@openai-codex`) |
| Enabled | **Yes** (`claude plugin list` → Status: enabled) |
| Prior state | Plugin was **not** installed before this session |

Upstream repo: https://github.com/openai/codex-plugin-cc

## Auto stop-gate / ReviewGate audit (P1-05) — CRITICAL

Audited via Codex companion setup (workspace = K1 firmware repo root):

```bash
node ~/.claude/plugins/marketplaces/openai-codex/plugins/codex/scripts/codex-companion.mjs setup --json
```

| Setting | Required | Observed |
|---------|----------|----------|
| `reviewGateEnabled` (stop-time review gate) | **OFF** | **`false`** |
| Auto enable attempted | **NO** | Did not run `--enable-review-gate` |
| Silent Codex takeover | FORBIDDEN | No ReviewGate config on disk for this repo |

**Explicit policy:** Do **not** run `/codex:setup --enable-review-gate` or `codex-companion.mjs setup --enable-review-gate` without Captain written approval.

## Codex CLI readiness (informational)

Setup JSON also reported: `codex-cli 0.142.5`, ChatGPT auth active — sufficient for **manual** `/codex:*` commands only.

## Task linkage

- **P1-03:** DONE
- **P1-05:** DONE (ReviewGate OFF verified via setup JSON)
- **P1-04:** Handoff contract already in `docs/agent-stack/SWARM-ORCHESTRATION.md` § Claude Code ↔ Codex
