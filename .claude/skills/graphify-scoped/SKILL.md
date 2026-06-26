---
name: graphify-scoped
description: |
  Scoped AST symbol-cluster orienter for Tab5/K1 firmware only. Use when orienting
  across sb-tab5-wireless-controller and SENSORY_BRIDGE_FIRMWARE before broad greps —
  not for whole-repo architecture, not for session history (use claude-mem/spec-recall).
allowed-tools: Read, Grep, Glob, Bash
---

# Graphify Scoped (Tab5 + K1 firmware)

## When to invoke

- Orienting on Tab5 ↔ K1 wireless control, WebSocket, UI handlers, or K1 network/control code
- You have (or can grep) exact symbol/function names and want the file neighborhood fast
- Before a broad grep across `sb-tab5-wireless-controller/` or `SENSORY_BRIDGE_FIRMWARE/`

Do **not** invoke for:

- Current lane status → read `progress.md`, `.claude/handoff.md`, `docs/spec-index.md`
- Prior session decisions → claude-mem / spec-recall
- Whole-repo or docs/forensics questions

## Refresh (session start only)

Run when Graphify will be used this session, or after Tab5/K1 source edits:

```bash
./tools/graphify-scoped-refresh.sh
```

Do not rebuild before every individual query.

## Query

```bash
GRAPH="evidence/graphify-trial-20260609/stage2-scoped/scoped-ast-graph.json"

graphify query "sym1 sym2 sym3" --graph "$GRAPH" --budget 1500
graphify explain "functionName()" --graph "$GRAPH"
```

## Rules

**Allowed:** exact-symbol `query`; `explain` on functions/methods (`Name()`); narrow source reads after.

**Banned:** whole-repo graph; broad "what connects X to Y?" oracle questions; `path` as coupling proof; `explain` on class names without checking `Source:` path; hooks; treating graph output as evidence.

## Examples

COLOUR slider → K1 chroma:

```bash
graphify query "harnessSetSlider sendCurrent sendK1NumberControl primary.chroma" --graph "$GRAPH"
graphify explain "sendK1NumberControl()" --graph "$GRAPH"
```

FPS header telemetry:

```bash
graphify query "applyK1EdgeState fps_from_float refreshStatus" --graph "$GRAPH"
```

WS reconnect backoff:

```bash
graphify query "increaseReconnectBackoff attemptReconnect handleDisconnected" --graph "$GRAPH"
graphify explain "increaseReconnectBackoff()" --graph "$GRAPH"
```

Prove every claim with `Read` or harness serial (`tools/tab5_k1_dashboard_harness.py`).

Canonical law: `.claude/skills/spec-recall/SKILL.md` § Graphify.
