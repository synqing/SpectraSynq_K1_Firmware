---
title: Phase 1 P1-01/P1-02 — Herdr proof
status: verified
last_verified: 2026-07-13
executor: agent:cursor
---

# Herdr — autonomous install and workspace proof

## License note (AGPL-3.0-or-later)

Herdr is **AGPL-3.0-or-later** (Homebrew formula `herdr` 0.7.3). For solo-dev / operator-machine use on Captain hardware, no separate sign-off is required to proceed with Phase 1 visibility tooling. Org-wide or multi-user fleet deploy remains subject to P0-06 scope review.

## Install

| Item | Result |
|------|--------|
| Prior state | **Not installed** (`which herdr` → not found) |
| Install | `brew install herdr` → **0.7.3** poured to `/opt/homebrew/Cellar/herdr/0.7.3` |
| Version | `herdr 0.7.3` |

## Server and workspace

```bash
herdr --version
# Started server (operator session): /opt/homebrew/opt/herdr/bin/herdr server
herdr status          # server: running, socket ~/.config/herdr/herdr.sock
herdr workspace create --cwd /Users/spectrasynq/SpectraSynq_K1_Firmware \
  --label "SpectraSynq_K1_Firmware" --no-focus
herdr workspace list  # workspace w1, label SpectraSynq_K1_Firmware, cwd K1 repo root
```

**Workspace mapping (live):**

| Herdr `workspace_id` | Label | `cwd` |
|----------------------|-------|-------|
| `w1` | `SpectraSynq_K1_Firmware` | `/Users/spectrasynq/SpectraSynq_K1_Firmware` |

Agents **do not** execute through Herdr; Herdr is Captain visibility / checkpoint console only.

## Non-interactive one-liner (repeatable)

```bash
brew install herdr
herdr server &   # or: brew services start herdr
herdr workspace create --cwd "$(git rev-parse --show-toplevel)" \
  --label "SpectraSynq_K1_Firmware" --no-focus
```

## Task linkage

- **P1-01:** DONE (workspace created, path verified)
- **P1-02:** DONE (layout documented in `docs/agent-stack/SWARM-ORCHESTRATION.md` + runbook)
