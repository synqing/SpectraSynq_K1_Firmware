---
abstract: "Sandboxed deployment plan for a Level 1 Visual-Memory Engine exploration. The plan applies the perception-first engineering gate to K1's CRGB16/SQ15x16 findings, decomposes the work into isolated agent lanes, defines probe-first proof gates, and expands the visual-memory primitive set beyond trail half-life, fractional movement, centre-origin propagation, low-level persistence, and byte-sequence smoothness."
---

# Level 1 Visual-Memory Engine Sandboxed Deployment Plan

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Mode | Plan only. No firmware edit, serial, upload, commit, or branch. |
| North star | Exceed Sensory Bridge's perceptual impact and musical relevance. |
| Governing skill | `/Users/spectrasynq/.agents/skills/perception-first-engineering/SKILL.md` |
| Required isolation | `parallel-agent-sandboxing` for any concurrent modify/build/test lane. |

## 1. Perception-First Frame

[FACT] The previous CRGB16/WS2812 backtest found that the broad "16-bit colour output" defence is overclaimed, because K1 drives 8-bit WS2812 GRB bytes. Source: `docs/forensics/2026-05-26-crgb16-ws2812-value-backtest.md`.

[FACT] The same backtest found that high-precision history can materially change final byte sequences in stateful trails. Bloom-like fractional shift stayed nonzero for 265 frames versus 48 in an 8-bit state path. Source: `docs/forensics/2026-05-26-crgb16-ws2812-value-backtest.md`.

[INFERENCE] The product primitive is not `CRGB16`, Pharap FixedPoints, or "precision". The primitive is **fractional visual memory**: visual state surviving below immediate byte visibility long enough to shape perceived motion, decay, persistence, and musical structure.

This plan explores whether fractional visual memory can be moved into a smaller, explicit Visual-Memory Engine with LUTs and in-house numeric types, without forcing that outcome or assuming the current implementation is wrong.

## 2. Non-Negotiables

- No default visual behaviour change in Level 1.
- No serial access by agents. Captain supplies captures if needed.
- No calibration command.
- No heap, `String`, logging, or serial I/O in render paths.
- No global `CRGB16` removal decision in this phase.
- No promotion without final-byte evidence and Captain-visible proof.
- All concurrent modify/build/test agents work in isolated sandboxes and return data only.

## 3. Candidate Visual-Memory Primitive Set

Already identified:

| Primitive | Meaning |
|---|---|
| Trail half-life | How long visual energy remains readable after an impulse. |
| Fractional movement | Sub-pixel/sub-LED motion that accumulates into smooth propagation. |
| Centre-origin propagation | Energy originates at the K1 centre and moves outward coherently. |
| Low-level persistence | Below-one-byte state survives until it becomes visible or meaningfully shapes decay. |
| Byte-sequence smoothness | Final output bytes change smoothly over time rather than stair-step or flicker. |

Additional vectors to explore:

| Primitive | Why it may matter perceptually | Possible metric |
|---|---|---|
| Attack shape | Determines whether onsets feel immediate and musical. | onset-to-light latency, first 3-frame energy slope |
| Release shape | Determines whether decay feels graceful or dead. | decay curve fit, tail integral |
| Impulse memory | Lets transient musical events leave recognisable visual afterimages. | post-onset energy half-life, spatial footprint duration |
| Motion coherence | Separates intentional motion from jitter. | COM slope variance, direction reversals |
| Spatial diffusion | Controls how light spreads through the LGP. | width over time, energy conservation by radius |
| Edge falloff | Prevents boundary artefacts or hard visual stops. | edge energy ratio, terminal fade slope |
| Hue continuity | Prevents colour popping during motion/decay. | p95 hue delta between active frames |
| Saturation preservation | Resists white/milky washout at peaks. | active-pixel saturation floor, white-bias score |
| Dynamic range shaping | Makes weak and strong events both visible. | low/high input visibility curve |
| Temporal masking control | Hides quantisation under motion or brightness. | low-light flicker score, dither phase artefacts |
| Layer priority | Keeps overlapping visual memories readable. | occlusion/layer dominance score |
| Refractory behaviour | Prevents repeated triggers from smearing into mush. | retrigger recovery time, event separation score |
| Beat-phase memory | Makes pulses feel locked to the music rather than merely reactive. | phase error over beat windows |
| Gesture identity | Preserves the recognisable shape/personality of a mode. | metric bundle plus Captain label match |
| Silence posture | Defines what the object does when music is absent or weak. | idle energy, idle motion, perceptual calm score |
| Colour afterimage | Carries harmonic/chromatic information after the sound changes. | chroma trail duration, hue drift |
| Energy routing | Decides where musical energy travels spatially. | source-to-edge energy transfer curve |
| Perceptual contrast memory | Keeps successive events distinguishable. | contrast recovery, local peak separation |

## 4. Architecture Direction

Recommended target is **probe-first hexagonal architecture**:

```text
Mode intent / AP state
  -> Visual Memory Port
      -> Current CRGB16 adapter
      -> Candidate compact-state adapter
  -> Final-byte probe
  -> FastLED transport
```

Boundaries:

- Domain core: visual-memory primitives and state transitions.
- Ports: impulse insert, decay, fractional shift, centre mirror, soft clip, quantise.
- Adapters: current `CRGB16` path; candidate LUT/fixed-state path.
- Probe adapter: paired final-byte metrics.
- Transport adapter: FastLED output, unchanged in Level 1.

[INFERENCE] This keeps the product primitive stable while allowing implementation experiments behind a port. It also avoids making FastLED, Pharap FixedPoints, or `CRGB16` the domain model.

## 5. Sandboxed Team Deployment

### Sandbox Rule

Before dispatching any concurrent modifying/building/testing agents:

```bash
TIMESTAMP=$(date +%Y%m%d%H%M%S)
cp -R "/Users/spectrasynq/SensoryBridge-main 9" "/tmp/k1_vme_<lane>_${TIMESTAMP}"
```

Every prompt must state:

```text
You are working ONLY in /tmp/k1_vme_<lane>_<timestamp>/.
Do not read or modify files outside this directory.
Return data only. Do not patch canonical source.
```

### Lanes

| Lane | Role | Scope | Output |
|---|---|---|---|
| A | Source cartographer | Bloom, Bloom Fast, Waveform Fast, Waveform Hybrid memory paths | ownership map and primitive mapping |
| B | Numeric architect | `UQ4.12`, `UQ8.8`, `uint16_t`, LUT hybrid options | fixed-format trade study |
| C | LUT specialist | decay, shift kernels, soft clip, quantise/dither, gamma/perceptual curves | LUT feasibility matrix |
| D | Probe engineer | final-byte paired probe contract and packet schema | `VPAB,ver=1` spec and metrics |
| E | Test strategist | offline, firmware, hardware, visual proof gates | test matrix and thresholds |
| F | Adversarial reviewer | attack every claimed primitive and simplification | risk register and falsification tests |
| G | Integration planner | sequence low-risk implementation tasks | phased implementation plan |

Token budget: 30K per agent. Split any lane that exceeds budget.

## 6. Phase Plan

### Phase 0: Freeze Inputs

- Record current git head.
- Record dirty tree before work.
- Read doctrine and existing forensics.
- Confirm no protected device or serial task is in scope.

Exit gate: baseline evidence packet exists.

### Phase 1: Read-Only Decomposition

- Map the current mechanism-to-perception chain.
- Classify every memory path as load-bearing, suspect, or unknown.
- Identify collapse points where high precision becomes 8-bit.

Exit gate: no code touched; primitive map reviewed.

### Phase 2: Shadow Specification

- Define `VisualMemoryState` candidate formats.
- Define supported operations: impulse, decay, fractional shift, mirror, diffuse, clip, quantise.
- Define adapter contract against current mode paths.
- Define final-byte paired probe schema.

Exit gate: spec approved before implementation.

### Phase 3: Sandbox Prototype

- Implement one candidate in a sandbox only.
- Target Bloom or Waveform Fast first.
- Keep canonical displayed output unchanged.
- Emit paired metrics only.

Exit gate: sandbox build/test evidence and diff review.

### Phase 4: Hardware-Ready Gate Package

- Orchestrator applies minimal reviewed patch to canonical source only if approved.
- Build gate: `pio run -e k1_hardware`.
- Runtime gate: Captain capture; agent reads files only.
- Visual gate: Captain A/B judgement plus metrics.

Exit gate: keep/revise/reject decision.

## 7. Metrics

| Metric | Purpose |
|---|---|
| `mae8`, `p95_abs8`, `max_abs8` | Final-byte equivalence. |
| `changed_channel_pct` | Scope of byte-level difference. |
| `energy_delta_pct` | Perceived brightness/energy shift. |
| `com_delta_leds` | Spatial motion preservation. |
| `com_slope_delta_pct` | Transport speed preservation. |
| `trail_half_life_delta_frames` | Memory preservation. |
| `tail_integral_delta_pct` | Low-level persistence. |
| `hue_delta_p95` | Colour continuity. |
| `sat_delta_p95` | Saturation preservation. |
| `flicker_score` | Quantisation/dither artefact detection. |
| `render_us`, `quant_us`, `frame_us` | Performance impact. |
| `heap_delta` | Render safety and memory budget. |

## 8. Packet Contract Sketch

Future probe packets should be versioned and final-byte explicit:

```text
VPAB,ver=1,mode=7,scenario=trail,frame=42,mae8=0.73,p95_abs8=2,max_abs8=13,changed_pct=4.6,energy_a=812,energy_b=764,com_a=79.2,com_b=78.9,tail_a=135,tail_b=71
```

Contract rules:

- `ver` is mandatory.
- Field meanings are append-only once used in captures.
- Pre-output metrics and final-byte metrics must not be mixed.
- Shadow path must not alter displayed LEDs unless explicitly armed.
- Packets must be parseable by offline harness scripts.

## 9. Decision Gates

Preserve the current implementation if:

- Candidate fails final-byte equivalence or perceptual thresholds.
- Candidate introduces timing, heap, flicker, or colour clarity regressions.
- Captain-visible output is weaker.

Promote the primitive but replace implementation if:

- Candidate matches or improves perception.
- Candidate reduces dependency/runtime complexity.
- Candidate preserves centre-origin motion and dual-channel behaviour.

Reject both current and candidate assumptions if:

- Neither produces materially better perception.
- The primitive itself does not survive final-byte/user-facing gates.

## 10. Open Questions

- Is Bloom or Waveform Fast the first prototype target?
- Should the first candidate numeric format be `UQ4.12`, `UQ8.8`, or dual-format?
- Should the first proof be firmware shadow probe or a more faithful offline simulator?
- What Captain-visible A/B capture setup is acceptable for perception proof?

## Changelog

| Date | Change |
|---|---|
| 2026-05-26 | Initial sandboxed deployment plan. |
