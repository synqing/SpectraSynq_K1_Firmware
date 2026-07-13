---
title: SQLite Snapshots — Read-Only Operator Recipes
status: draft
last_verified: 2026-07-13
autonomous_install: true
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - docs/agent-stack/PHASED-ROLLOUT.md Phase 1
owner: knowledge-curator
---

# SQLite Snapshots — Read-Only Operator Recipes

**Phase 1 tasks P1-06, P1-07.** Documents `sqlite-utils` usage for operator
inspection only. **Never write production state** via these commands.

## Install (autonomous default)

Agents **execute** install on the operator machine when Phase 1+ tasks require it. Captain is **not** asked to run `brew install` for this tool.

```bash
# Prefer Homebrew on macOS
brew install sqlite-utils
# Or: pip install sqlite-utils  (document path if used)

sqlite-utils --version
```

Evidence template: `knowledge/research/phase1-sqlite-utils-proof.md`.

## Principles

| Rule | Rationale |
|------|-----------|
| **Read-only queries** | Operator inspection and diff only |
| **Copy before query** | Snapshot DB file before ad-hoc experiments |
| **No production writes** | Authority contract forbids sqlite-utils writes to live stores |
| **Paths are machine-local** | Document actual paths at install time |

## Recipe: snapshot a database file

```bash
# Copy first — never mutate the live file
cp /path/to/source.db /tmp/source-$(date +%Y%m%d-%H%M%S).db
SNAP=/tmp/source-*.db  # use the copy path

sqlite-utils tables "$SNAP"
sqlite-utils schema "$SNAP" table_name
sqlite-utils query "$SNAP" "SELECT COUNT(*) FROM observations LIMIT 1"
```

## Recipe: export table to JSON (audit)

```bash
sqlite-utils query "$SNAP" "SELECT * FROM table_name LIMIT 100" --json > /tmp/table-export.json
```

## Recipe: schema diff (two snapshots)

```bash
diff <(sqlite-utils schema snap-a.db) <(sqlite-utils schema snap-b.db)
```

## Claude-mem database (example paths)

Claude-mem DB location varies by install. On operator machine, locate via:

- Claude Code / Cursor MCP config
- `~/.claude-mem/` or plugin documentation

**Do not commit** snapshot files or exports containing session content to git
without Captain review (may contain sensitive debugging notes).

## Common queries (adjust table names to live schema)

```bash
# Recent observations (example — verify schema first)
sqlite-utils query "$SNAP" \
  "SELECT id, created_at, substr(content,1,80) FROM observations ORDER BY id DESC LIMIT 20"

# Table row counts
sqlite-utils query "$SNAP" "SELECT name FROM sqlite_master WHERE type='table'" --json | \
  jq -r '.[].name' | while read t; do
    echo -n "$t: "; sqlite-utils query "$SNAP" "SELECT COUNT(*) AS n FROM \"$t\"" --json
  done
```

## Forbidden

- `INSERT`, `UPDATE`, `DELETE`, `DROP` against live production databases
- Automating sqlite-utils in agent bootstrap scripts
- Treating DB contents as implementation truth (code + git win)

## Phase 1 exit evidence

- [`knowledge/research/phase1-sqlite-utils-proof.md`](../research/phase1-sqlite-utils-proof.md)
- This runbook (P1-07)

## Rollback

Uninstall sqlite-utils from operator environment. No repo dependency.
