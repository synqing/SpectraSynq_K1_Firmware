---
name: plain-english-work-summaries
description: >-
  HARD FAIL — summary of agent work MUST be plain English. Captain standing
  order 2026-08-22, every agent surface, every workspace. Use whenever reporting
  what happened, what came of it, status, a blocker, a next step, or any
  Captain-facing summary. Do not lead with GROUNDED, READBACK, RBDO, or DSP jargon.
---

# Plain English work summaries

**HARD FAIL** if violated. Captain 2026-08-22.

Summary of agent work **MUST** be made in **plain English**.

This is separate from "Captain asks" (short imperative when you need Captain to do something). This rule is about **reporting work**.

## Required shape

First sentences, ordinary English:

1. What happened.
2. What is true now.
3. What is left.

Then evidence (paths, hashes, measurements, audit labels) if needed.

## Forbidden as the lead

- `GROUNDED` / `DEGRADED-MODE` / `READBACK` / `RBDO` as the summary
- Jargon-first (`pcm RMS`, `hop_seq`, `vTaskDelay`, env ids, `IDENTITY OK`)
- A log dump or file:line list standing in for "what happened"

Audit labels may exist **after** the plain summary. They must not replace it.

## Scar

Captain asked "What came of it?" The agent answered with labels and audio jargon. The plain fact was: nothing was fixed; diagnosis only.

## Cursor / Claude / Codex / Agents

Always-on rule: `~/.cursor/rules/plain-english-work-summaries.mdc`  
Ledger: `~/.claude/memory/spectrasynq/L1/CANONICAL_DECISIONS.md` §5
