---
abstract: "Receipt: palette_coverage_gate measures final leds_16 RGB, but render_replay has no mode 11 or 32 entries. Gate is not run. No new harness."
date: 2026-08-17
---

# Coverage gate — not a blocker for this fork

Checked 2026-08-17 against `feat/k1-scheduling-generation-hardening` @ `25bec114`.

## What the gate measures

`scripts/regression-harness/palette_coverage_gate.py` scores **final rendered LED frames** (`leds_16` RGB dumps from `render_replay`): hue entropy, distinct-colour counts, desaturated-lit fraction. Sampler-coordinate coverage is explicitly null. That *would* be able to test deposition vs source **if** the replay registry could drive the three modes.

## Why it cannot score this fork

`scripts/regression-harness/render_replay.py` mode registry:

- Default: `bloom` only.
- Parked behind `K1_RENDER_REPLAY_ALL_MODES=1`: `waveform`, `waveform_fast`, `spectrum_river`, `comet`.
- **No** `waveform_hybrid` (mode 11).
- **No** `waveform_hybrid_k1` (mode 32).

Grep of that file for `waveform_hybrid` / `LIGHT_MODE_WAVEFORM_HYBRID` returns no matches.

Wiring 11 and 32 would be a **new harness**. Plan rule: do not write it unless Captain asks after the A/B.

## Decision

- Gate **not run**.
- No new replay entries.
- Lever choice waits on Captain's mode-11 verdict, not on host metrics.
