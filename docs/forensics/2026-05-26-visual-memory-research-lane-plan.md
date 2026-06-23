---
abstract: "Standalone read-only research lane plan for the Level 1 Visual-Memory Engine workstream. This separates perception-first primitive discovery from sandboxed implementation, so the execution team can proceed while a parallel research team expands the candidate primitive set, tests materiality assumptions, and identifies non-obvious vectors before any firmware adoption decision."
---

# Visual-Memory Engine Research Lane Plan

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Mode | Read-only research plan. No firmware edit, serial, upload, commit, or branch. |
| North star | Exceed Sensory Bridge's perceptual impact and musical relevance. |
| Governing skill | `/Users/spectrasynq/.agents/skills/perception-first-engineering/SKILL.md` |
| Downstream plan | `docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md` |

## 1. Relationship To The Sandboxed Execution Plan

[FACT] The sandboxed execution plan already contains Phase 1 read-only decomposition lanes and Phase 3 sandbox prototype lanes. Source: `docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md`.

[INFERENCE] This research lane is the upstream discovery layer. It should feed the sandboxed execution plan with sharper primitives, metrics, and falsification tests, but it should not edit firmware or decide implementation.

Use this split:

```text
Research lane:
  What perceptual primitives exist?
  Which mechanisms plausibly create them?
  What metrics prove materiality?
  What would falsify the value claim?

Sandbox execution lane:
  Build/probe one approved candidate.
  Compare current vs candidate final-byte output.
  Measure timing.
  Prepare Captain-visible A/B evidence.
```

## 2. Research Questions

1. Which visual-memory primitives materially affect what a K1 owner perceives?
2. Which existing source mechanisms produce those primitives accidentally or intentionally?
3. Which primitives can be simulated, LUT-ised, compressed, or moved into an explicit engine?
4. Which primitives require live state and cannot be replaced by static tables?
5. Which current mechanisms are likely complexity without perceptual value?
6. What measurements separate visible product value from internal numeric churn?

## 3. Read-Only Research Lanes

| Lane | Focus | Inputs | Output |
|---|---|---|---|
| R1 | Primitive taxonomy | K1 forensics, current source, Captain observations | expanded primitive catalogue |
| R2 | Mechanism-to-perception map | Bloom/Waveform/GDFT/Kaleidoscope source | chain map: mechanism -> output -> perception |
| R3 | Collapse/survival audit | `CRGB16`, FastLED, quantisation, dither, gamma paths | table of where value dies or survives |
| R4 | Materiality thresholds | VP gates, final-byte metrics, visual characterisation ledger | threshold proposal |
| R5 | LUT/simulation feasibility | decay, shift, soft clip, dither, palette, temporal masks | LUT feasibility matrix |
| R6 | Cross-domain analogues | DSP, animation, video compositing, game feel, lighting control | candidate primitives not obvious from firmware |
| R7 | Adversarial simplification | all inherited mechanisms | remove/simplify challenge list |
| R8 | Test/probe contract | existing `vp_probe`, `frame_dump`, `vp_perf` | research-to-probe handoff schema |

Each lane returns data only:

```text
Files inspected:
Findings:
Confidence:
Open questions:
Recommended action:
Falsification test:
```

## 4. Expanded Primitive Search Space

Seed primitives already named:

- trail half-life
- fractional movement
- centre-origin propagation
- low-level persistence
- byte-sequence smoothness over time

Research should test these additional candidates:

| Primitive | Description | Why it might matter |
|---|---|---|
| Attack shape | How quickly light appears after musical onset. | Creates perceived responsiveness and impact. |
| Release shape | How light exits after energy falls. | Prevents deadness or smeared residue. |
| Impulse memory | Afterimage of transient events. | Makes musical hits feel consequential. |
| Motion coherence | Smoothness and intent of movement. | Separates designed motion from jitter. |
| Spatial diffusion | Spread of energy across the LGP. | Controls scale, bloom, and perceived physicality. |
| Edge falloff | How energy behaves near strip ends. | Avoids hard stops and boundary artefacts. |
| Hue continuity | Colour stability across movement and decay. | Prevents distracting colour popping. |
| Saturation preservation | Resistance to milky washout. | Maintains clarity and emotional colour. |
| Dynamic range shaping | Visibility across weak and strong inputs. | Makes quiet details and peaks both meaningful. |
| Temporal masking | Hiding quantisation under motion/brightness. | Reduces visible stepping and flicker. |
| Layer priority | Which memory wins when events overlap. | Prevents visual mush. |
| Refractory behaviour | Recovery between repeated triggers. | Keeps rhythm readable. |
| Beat-phase memory | Persistence aligned to musical pulse. | Makes visuals feel musically locked. |
| Gesture identity | Recognisable personality of each mode. | Protects memorable product character. |
| Silence posture | Behaviour in silence or weak input. | Keeps device intentional when music is absent. |
| Colour afterimage | Harmonic/chromatic residue after sound changes. | Supports perceived musical intelligence. |
| Energy routing | Spatial path from source to destination. | Creates directed, comprehensible motion. |
| Perceptual contrast memory | Separation between successive events. | Prevents flattening and over-smearing. |
| Surprise bandwidth | Controlled novelty without chaos. | Makes repeated listening stay engaging. |
| Event salience ranking | Prioritises musically important events. | Reduces random-looking reactions. |
| Locality preservation | Maintains where an event happened. | Keeps motion and causality readable. |
| Cross-channel independence | Keeps primary/secondary behaviour distinct. | Protects dual-strip richness. |
| Phase reset discipline | Controls when memory should reset. | Avoids stale trails and mode transition ghosts. |

## 5. Materiality Tests

Each primitive must define:

- final-output metric
- perceptual metric
- simpler alternative
- threshold for "material"
- threshold for "not worth carrying"
- falsification test

Example:

```text
Primitive: trail half-life
Final-output metric: nonzero final-byte tail duration, tail integral
Perceptual metric: Captain can identify smoother/stronger trail in A/B
Simpler alternative: 8-bit state fade
Material threshold: >10% half-life delta and >50 ms visible tail delta
Not worth carrying: <=2-frame tail delta and no visible A/B preference
Falsification: 8-bit state path passes final-byte thresholds and Captain A/B
```

## 6. Research Stop Conditions

Stop a lane if:

- It cannot connect the primitive to a final perceived surface.
- It only measures internal state.
- It assumes CRGB16, FastLED, LUTs, or a new engine must win.
- It cannot name a simpler alternative.
- It cannot define a falsification test.

## 7. Handoff Contract To Execution Team

The research lane may recommend a sandbox prototype only when it provides:

1. Primitive name.
2. Current mechanism.
3. Candidate replacement/simulation/LUT/engine mechanism.
4. Final-byte metrics.
5. Perceptual metrics.
6. Falsification test.
7. Risk to centre-origin, colour clarity, motion memory, responsiveness, or dual-channel behaviour.
8. Required sandbox lane owner.

## 8. Suggested First Research Packet

Start with:

```text
Primitive: fractional visual memory
Current mechanism: CRGB16/SQ15x16 state in Bloom and Waveform Fast
Candidate: compact fixed visual-memory state plus LUT decay/shift kernels
Final-byte metrics: byte delta, energy, COM, tail half-life, tail integral
Perceptual metrics: Captain A/B for smoother trail, stronger musical causality, lower mush
Falsification: 8-bit or compact candidate passes byte thresholds and Captain sees no loss
Execution target: Bloom first, Waveform Fast second
```

## Changelog

| Date | Change |
|---|---|
| 2026-05-26 | Initial standalone research lane plan. |
