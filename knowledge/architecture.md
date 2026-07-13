---
title: SpectraSynq K1 — Architecture
status: draft
last_verified: 2026-07-13
sources:
  - CLAUDE.md
  - docs/architecture/
owner: knowledge-curator
---

# Architecture

## Canonical reference

The full firmware architecture overview lives in the repo root:

- **[`CLAUDE.md`](../CLAUDE.md)** — tech stack, audio-to-visual data flow, core timing, build environments, project structure
- **[`AGENTS.md`](../AGENTS.md)** — agent-facing summary (mirrors CLAUDE.md architecture sections)

## Data flow (summary)

```
I2S audio (12.8 kHz) → Goertzel GDFT (133 Hz)
  → AudioSemanticState (volatile, Core 0 publish)
  → Smart Director + effect render (Core 1, ~100 FPS)
  → FastLED RMT5 → dual-channel LGP
```

## Key invariants

- **Mutex-free cross-core:** Core 1 reads AudioSemanticState; never writes audio state.
- **No time-only effects:** Visuals are music-driven, not pure animation clocks.
- **Host gate ≠ device proof:** pytest + PIO validate compile/metrics; eyes-on validates perceptual quality.

## Deeper docs

| Topic | Path |
|-------|------|
| Spec index / lane handovers | [`docs/spec-index.md`](../docs/spec-index.md) |
| Architecture diagrams | [`docs/architecture/`](../docs/architecture/) |
| Audio forensics | [`docs/forensics/`](../docs/forensics/) |
| IM73D productionization | [`docs/hardware/`](../docs/hardware/) |

Implementation truth always defers to **code + tests** when this document drifts.
