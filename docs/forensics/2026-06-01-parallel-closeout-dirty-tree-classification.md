---
abstract: "Dirty-tree classification for the 2026-06-01 parallel K1 closeout wave."
evidence-tier: "repo-truth"
created: "2026-06-01"
---

# Parallel Closeout Dirty-Tree Classification

## Canonical State

- Branch: `feat/gdft-harness`
- HEAD at wave start: `476e310`
- Remote delta: ahead of `origin/feat/gdft-harness` by 5 commits
- Sandbox root: `/tmp/k1_parallel_20260601211146`
- Hardware lock: orchestrator-owned only

## Classification

| Class | Paths | Action |
|---|---|---|
| Governance edits | `.claude/CLAUDE.md`, `AGENTS.md`, root `CLAUDE.md`, `docs/forensics/2026-05-29-parallel-agent-orchestration-timeout-incident.md` | Leave unstaged until Captain confirms governance bundle scope |
| Spec Kit install | `.agents/skills/speckit-*`, `.claude/skills/speckit-*`, `.specify/**` | Leave unstaged; treat as separate Spec Kit deployment bundle |
| Historical Smart Auto runtime evidence | `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-*`, `2026-06-01T195050-*`, `2026-06-01T200332-*`, `capture-probe/` | Preserve; stage only if a closeout doc explicitly references the artefact set |
| Current committed Smart Auto evidence | `docs/forensics/runtime-evidence/2026-06-01T203320-*`, `docs/forensics/runtime-evidence/2026-06-01-smart-auto-product-ab-closeout-v2.md` | Already committed in `f135e1a` |
| Upload guard and runbook | `platformio.ini`, `scripts/platformio/k1_upload_guard.py`, `tests/test_k1_upload_guard.py`, `docs/forensics/2026-06-01-k1-bench-upload-and-smart-auto-runbook.md` | Already committed in `5e9a969` and `476e310` |

## Commit Policy

Parallel closeout commits must stage only the lane-owned files. Do not sweep the
Spec Kit install, governance edits, or older runtime evidence into unrelated
commits.

## Changelog

| Date | Change |
|---|---|
| 2026-06-01 | Created before merging parallel closeout lane outputs. |
