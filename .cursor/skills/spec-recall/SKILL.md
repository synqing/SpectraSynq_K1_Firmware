---
name: spec-recall
description: Route agents to active K1 specs and claude-mem recall conventions. Use when resuming a lane, asking "did we already solve this?", or before firmware/forensic work where handover authority matters.
---

# Spec Recall

## When to invoke

- Resuming work after context reset or new session
- "Did we already fix X?" or "what is the active lane?"
- Before firmware edits, device flash, or forensic investigation
- Before trusting claude-mem for **current** worker/queue/device status

## Read order (on-disk first)

1. [`progress.md`](../../../progress.md)
2. [`.claude/handoff.md`](../../handoff.md)
3. [`docs/spec-index.md`](../../../docs/spec-index.md) → Active Lanes table
4. Lane handover linked from that table
5. claude-mem (prior sessions only)
6. graphify scoped AST orienter (optional — after steps 1–5, Tab5/K1 firmware only)

**Rule:** On-disk handover beats claude-mem for **current lane status**.

## Graphify (scoped AST symbol-cluster orienter)

Graphify is allowed only as a scoped AST symbol-cluster orienter for:

- `sb-tab5-wireless-controller/`
- `SENSORY_BRIDGE_FIRMWARE/`

**Allowed:**

- Use the scoped Stage 2 graph only (`evidence/graphify-trial-20260609/stage2-scoped/scoped-ast-graph.json`; rebuild via [`tools/graphify-scoped-refresh.sh`](../../../tools/graphify-scoped-refresh.sh)).
- Use `graphify query` with exact symbol/function/control names.
- Use `graphify explain` for specific functions/methods.
- Use results only to narrow source reads.

**Banned:**

- Whole-repo Graphify graphs.
- Broad architecture/oracle questions.
- `graphify path` as coupling proof.
- `explain` on ambiguous class names unless the file path is verified.
- Hooks / always-on integration.
- `CLAUDE.md` or `.claude/CLAUDE.md` edits.
- Treating Graphify output as evidence without source reads.

**Refresh rule:**

- Rebuild the scoped graph at session start only when Graphify will be used, or after relevant Tab5/K1 source changes.
- Do not rebuild before every individual query.

Use **claude-mem** for prior session decisions, bugs, failed attempts, and workflow history. Read raw files to prove claims.

## claude-mem 3-layer workflow

1. `search(query, project="SensoryBridge-main 9", dateStart="YYYY-MM-DD")`
2. `timeline(anchor=ID)` or `timeline(query=...)`
3. `get_observations(ids=[...])` — only for filtered IDs

Use effect names (`Dense Forge`, `Waveform Tempo`, `mode 18`), not port shorthand. See spec-index §Recall conventions for symptom → query mapping.

## Operational memory guard

Worker health, queue routes, and API version claims in claude-mem are **historical** unless verified live in the current session. See `docs/agent-memory/claude-mem-pre-13.4-checklist.md` for upgrade steps.

## Corpus build

Deferred until claude-mem 13.4 upgrade. Do not rely on empty pre-upgrade corpora in `~/.claude-mem/corpora/`.
