---
title: Repo-truth IM73D guard check — manifest-aware validation
status: verified
last_verified: 2026-07-13
tags:
  - repo-truth
  - im73d
  - upload-guard
sources:
  - knowledge/research/phase3-test2-bug-resurrection.md
  - knowledge/research/repo-truth-fix-evidence.md
  - scripts/agent/repo-truth.sh
  - knowledge/runbooks/promote-learning.md
owner: knowledge-curator
---

# Decision: repo-truth IM73D guard check — manifest-aware validation

## Context

Phase 3 Test 2 resurrected a recurring **false FAIL** on `scripts/agent/repo-truth.sh`:
the IM73D guard check grepped `k1_upload_guard.py` for the literal string
`k1_bench_im73d`. After the N4a manifest refactor, env names live in
`scripts/platformio/k1_device_identities.json`; the guard loads the manifest via
`load_identities()` and does not embed env literals in source.

Bootstrap reported **FAIL** while upload protection for `k1_bench_im73d` was
functionally correct (`tests/test_k1_upload_guard.py` L155–157).

## Decision

`repo-truth.sh` IM73D guard validation **must not** grep for env literals in
`k1_upload_guard.py`. It **must** verify:

1. `k1_upload_guard.py` references `k1_device_identities.json` (guard wired to manifest).
2. `k1_device_identities.json` authorizes `k1_bench_im73d` for at least one identity row.

This aligns repo-truth with implementation truth: manifest is single source of env
authorization; guard enforces identity-by-serial from that manifest.

## Root cause (cited)

**Primary:** Stale grep check in `repo-truth.sh` after manifest migration — see
[`phase3-test2-bug-resurrection.md`](../research/phase3-test2-bug-resurrection.md) § Root cause.

**Not a guard regression:** `k1_bench_im73d` protection remained valid via manifest;
only the bootstrap linter was wrong.

## Fix (implementation pointer)

`scripts/agent/repo-truth.sh` L44–65 — replaces literal-env grep with:

- Manifest path + guard manifest reference check.
- Inline `python3` JSON parse confirming `k1_bench_im73d` ∈ authorized envs.

**Evidence snapshot:** [`repo-truth-fix-evidence.md`](../research/repo-truth-fix-evidence.md)
— IM73D guard **PASS**, OVERALL **WARN** (registry dirty only), `session-bootstrap.sh` exit **0**.

## Rollback

If manifest-based check is removed, restore dual-track policy
[`agent-stack-repo-truth-dual-track.md`](./agent-stack-repo-truth-dual-track.md) until
lane-integrity checks PASS again.

## Cross-links

- Dual-track when FAIL: [`agent-stack-repo-truth-dual-track.md`](./agent-stack-repo-truth-dual-track.md)
- Bug resurrection test: [`phase3-test2-bug-resurrection.md`](../research/phase3-test2-bug-resurrection.md)
- Promotion workflow: [`promote-learning.md`](../runbooks/promote-learning.md)

---

## Promotion workflow trace (P3-03 demonstration)

Delegated scope: autonomous docs-only promotion demo per Captain task row P3-03 /
parent agent instruction (2026-07-13).

| Step | Action | Gate |
|------|--------|------|
| **IDENTIFY** | Recurring bug pattern (grep staleness) + fix in `repo-truth.sh`; criteria #4 + #5 + #6 met | PASS |
| **DRAFT** | This document (initial `status: draft` path → verified at VERIFY) | PASS |
| **FRONTMATTER** | `title`, `status`, `last_verified`, `sources`, `owner`, `tags` | PASS |
| **REVIEW** | Cross-checked against `repo-truth.sh`, `k1_device_identities.json`, `k1_upload_guard.py`, phase3-test2 root cause | PASS |
| **VERIFY** | `status: verified`, `last_verified: 2026-07-13`; evidence paths linked | PASS |
| **COMMIT** | Manual git — curator/Captain (not auto) | Pending |
| **RETRIEVE** | Listed in [`knowledge/index.md`](../index.md) decisions table | PASS |

`openknowledge_promoted` candidate path: `knowledge/decisions/repo-truth-im73d-manifest-check-2026-07-13.md`

---

## Appendix: P3-07 auto-sync audit log (2026-07-13)

**Task:** Confirm zero auto-sync pipelines Claude-mem → OpenKnowledge / `knowledge/`.

**Method:** Repo grep + config/hook inspection (provenance auditor, delegated via promotion demo).

| Surface | Query / check | Result |
|---------|---------------|--------|
| `scripts/hooks/` | `claude-mem`, `open-knowledge`, `memory_add` | **0 matches** |
| `.github/` | `claude-mem`, `openknowledge` | **0 matches** |
| `scripts/` | sync hooks writing `knowledge/` | **0 pipelines** — bootstrap reads mem reachability only |
| `.mcp.json` | `open-knowledge` server | MCP read/write tools; **no** mem→OK bridge configured |
| `.ok/config.yml` | `content.dir: knowledge` | Editor CRDT root only; **no** sync jobs |
| `AGENT_OS.md` | `observation_add` / `memory_add` | Documented **error** if agents attempt direct write |
| Policy ADR | [`agent-stack-promotion-not-sync.md`](./agent-stack-promotion-not-sync.md) | **Forbidden** paths enumerated |

**Verdict:** **PASS** — zero auto-sync pipelines found. Promotion to `knowledge/` occurs only via
manual reviewed workflow ([`promote-learning.md`](../runbooks/promote-learning.md)).
