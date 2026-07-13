---
title: Phase 1 P1-06 — sqlite-utils proof
status: verified
last_verified: 2026-07-13
executor: agent:cursor
---

# P1-06 sqlite-utils — autonomous install verification

## Install status

| Item | Result |
|------|--------|
| Binary | **Already present** (no install required this session) |
| Path | `/Users/spectrasynq/miniforge3/bin/sqlite-utils` |
| Version | `sqlite-utils, version 3.39` |
| Install method | Pre-existing miniforge3/pip environment (not brew this session) |

## Read-only snapshot (claude-mem)

Per [`knowledge/runbooks/sqlite-snapshots.md`](../runbooks/sqlite-snapshots.md):

- **Source DB:** `$HOME/.claude-mem/claude-mem.db`
- **Snapshot copy:** `/tmp/claude-mem-20260713-104159.db` (file copy before query; live DB not mutated)
- **Tables (sample):** `observations`, `session_summaries`, `sdk_sessions`, FTS aux tables, etc.
- **Row count:** `observations` → **78,963** rows
- **Recent IDs (metadata only):** ids 79799–79803 with `created_at` timestamps 2026-07-13T01:48–01:53Z

No snapshot DB or row content committed to git (authority contract).

## Commands executed

```bash
sqlite-utils --version
cp "$HOME/.claude-mem/claude-mem.db" "/tmp/claude-mem-$(date +%Y%m%d-%H%M%S).db"
sqlite-utils tables "$SNAP"
sqlite-utils query "$SNAP" "SELECT COUNT(*) AS n FROM observations"
sqlite-utils query "$SNAP" "SELECT id, created_at FROM observations ORDER BY id DESC LIMIT 5"
```

## Task linkage

- **P1-06:** DONE
- **P1-07:** Runbook exists at `knowledge/runbooks/sqlite-snapshots.md` (updated for autonomous default)
