---
title: Repo-truth bootstrap evidence (IM73D guard fix)
status: snapshot
captured: 2026-07-13
sources:
  - scripts/agent/session-bootstrap.sh
  - scripts/agent/repo-truth.sh
  - knowledge/decisions/agent-stack-repo-truth-dual-track.md
owner: knowledge-curator
---

# Repo-truth fix evidence (short)

**Context:** Follow-up to scripts fix `81e28887` — IM73D upload-guard check no longer false **FAIL**; lane integrity (env / guard manifest / plan) can **PASS** while OVERALL is **WARN** (e.g. dirty device-build-registry).

**Session:** `lane/gem-port-beat-pulse` @ `61768ee` (dirty + untracked working tree).

## `session-bootstrap.sh` (exit 0)

```
  repo-truth   : WARN
    WARN: docs/hardware/device-build-registry.md has uncommitted changes (do not auto-commit)
```

Bootstrap exit code: **0** (WARN is non-fatal per `session-bootstrap.sh` exit policy).

## `repo-truth.sh` excerpt

```
  IM73D env        : PASS
  IM73D guard      : PASS
  IM73D plan       : PASS
  registry dirty   : true
  OVERALL          : WARN
```

## Takeaway

| OVERALL | Bootstrap | Firmware lane |
|---------|-----------|---------------|
| WARN | Exit 0 | Not blocked by bootstrap |
| FAIL | Exit 1 | Blocked until lane-integrity FAIL resolved |

Dual-track docs work under **FAIL** only; **WARN** is acknowledge-and-continue.
