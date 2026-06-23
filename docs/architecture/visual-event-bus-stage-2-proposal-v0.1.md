---
title: "Visual Event Bus — Stage 2 Proposal & L1 Implementation Handoff"
version: v0.3 (unified)
date: 2026-05-28
status: Working contract (advisory). L1 ratified for implementation. L2 design only.
target_implementer: Codex (or any agent with file/edit + build capability)
repo: /Users/spectrasynq/SensoryBridge-main 9
governing_doctrine: CLAUDE.md (Sensory Bridge Doctrine Bridge, Developer Instrumentation Boundary, Calibration command policy)
reference_doctrine: Lightwave-Ledstrip/firmware-v3/docs/audio-visual/* (informs, does not override)
predecessor_artefacts:
  - docs/forensics/2026-05-26-visual-memory-research-lane-findings.md
  - docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md
  - docs/forensics/2026-05-25-lightwave-v3-harvest-map.md
abstract: |
  Unified proposal for the Stage 2 Visual Event Bus, the Layer 1 Accent consumer
  upgrade (implementation-ready), and the Layer 2 Memory consumer (design only,
  gated on VME port ratification). This document is self-contained: it includes
  the architectural context, contract surface, code-level L1 specification,
  verification procedure, escalation rules, and out-of-scope boundaries needed
  for a single implementing agent to complete the L1 work without round-tripping
  to the project owner for context.
---

# Visual Event Bus — Stage 2 Proposal & L1 Implementation Handoff

# § 0. Codex handoff brief — read first

This document hands off the Layer 1 Accent consumer upgrade to you (Codex). You implement Layer 1 only. Layer 2 is design context, not work product. Do not modify L2 surfaces, do not invent VME port semantics, do not touch pixel buffers.

## 0.1 Your scope

**In scope.** Modify `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h`, `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp`, and the call-site initialiser at `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:584` to deliver the three-pulse Accent consumer with event-id watermarking as specified in § 4. Build the resulting firmware on the `k1_hardware` and `k1_hardware_trace_dev` PlatformIO environments. Run the verification procedure in § 7.

**Out of scope.** Anything else. Specifically:

- Do not modify `sb_onset_beat.cpp`, `sb_audio_snapshot.cpp`, or the producer lane at `SPECTRASYNQ_K1_FIRMWARE.ino:471–478`.
- Do not modify `sb_smart_director.*`. The L3/L4/L5 surfaces stay as they are.
- Do not modify FastLED, gamma, soft-clip, or any pixel-level state.
- Do not add MabuTrace calls outside `FEATURE_TRACE_RENDER` guards. MabuTrace must remain non-shippable per CLAUDE.md.
- Do not run `start_noise_cal` or any other calibration command. Calibration commands are Captain-only per CLAUDE.md.
- Do not promote a build labelled `verified` without trace-dev evidence. Scalar telemetry alone is `scalar-only`, not `verified`.

## 0.2 How to behave under uncertainty

You operate under the SpectraSynq Operating Contract. Specifically:

1. **Label your claims.** Use `[FACT]`, `[INFERENCE]`, or `[HYPOTHESIS]` for any non-trivial assertion. Do not present speculation as fact.
2. **Measure twice, cut once.** Read the existing code before editing. The specification in § 4 names the files and line numbers you need; verify them before writing.
3. **Ask, don't guess.** If something is ambiguous, escalate (§ 0.4). Do not silently choose between interpretations.
4. **Two failures of the same type = stop.** If your build fails the same way twice, do not retry a third time. Diagnose root cause, report mechanism, propose alternative.
5. **No workarounds for tool failures.** If trace-dev does not produce evidence, report `blocked`. Do not paper over with scalar-only and call it verified.
6. **Production builds never link instrumentation.** If `nm` on the `k1_hardware` build shows MabuTrace symbols, you have introduced a doctrine violation. Fix or escalate before declaring done.

## 0.3 Order of operations

Recommended execution order:

1. Read § 1–§ 3 of this document (architecture and contract context).
2. Read § 4 of this document (L1 implementation specification — your assignment).
3. Read the four source files cited in § 4.1 to verify the current code matches what this spec assumes.
4. Implement the changes in § 4.2–§ 4.6.
5. Run the build verification in § 7.1.
6. Run the trace-dev verification in § 7.2.
7. Run the visual A/B verification in § 7.3 (you may need Captain's help to obtain LED capture).
8. Run the production-shippability check in § 7.4.
9. Report results using the status labels in § 7.5.

## 0.4 When to escalate

Stop and ask Captain (do not silently decide) if any of the following:

| Trigger | Escalation prompt |
|---|---|
| The current code at any cited file:line does not match what this spec describes. | "The spec assumes X at file:line; the actual code is Y. Should I update the spec or update the code?" |
| Trace-dev evidence shows a timing regression above the §7.2 thresholds. | "Trace-dev shows tail latency widening by N%. Threshold is 10%. Should we proceed, tune, or roll back?" |
| Visual A/B is ambiguous (some clips improve, some regress). | "Clip A improved on metric X; clip B regressed on metric Y. Approval call needed." |
| Production build (`k1_hardware`) symbol audit shows MabuTrace symbols linked. | "Production build linked MabuTrace. Diagnosing leak; do not promote build until resolved." |
| A new test or build environment is needed that does not already exist in `platformio.ini`. | "Need build env X. Propose adding to platformio.ini? Captain decides." |
| Any change is needed outside `sb_visual_hooks.*` or the cited call sites. | "Implementation requires touching Z. Out of declared scope. Should I expand scope or split the work?" |
| You discover a behaviour the spec did not anticipate. | "Found behaviour W. Spec is silent. Stopping to clarify before committing to an interpretation." |

Asking is not a failure mode. Silently guessing is.

---

# § 1. Architectural context

## 1.1 What this is

The K1 audio pipeline today reads:

```
audio → onset/beat detection → individual visual consumers
```

with each consumer (visual modes, smart director, visual hooks) holding partial event interpretation. Result: inconsistent reaction to the same musical events across consumers, duplicated detection logic, no shared truth surface, twitchy LED behaviour during dense passages.

Stage 2 promotes the existing — but undocumented — `SBAudioSnapshot` + `SBOnsetBeatEvent` surface into a written contract (§ 3) and upgrades one consumer (`sb_visual_hooks`) into a meaning-preserving Layer 1 Accent (§ 4). It also defines Layer 2 Memory (§ 5) as a future render-local consumer that issues directives to the in-flight Visual Memory Engine.

[INFERENCE] The architectural work is documentation-and-discipline on existing code, not a greenfield build. The bus exists physically. Two consumers (`sb_visual_hooks`, `sb_smart_director`) already sit on it. What is new is making the discipline explicit and upgrading the partial consumers to honour their categories.

## 1.2 Layered picture

```
SBAudioSnapshot + SBOnsetBeatEvent          ← Bus (already in code)
        ↓
    [one read per render frame]             ← Shared bus state, immutable
        ↓                                     for the duration of the frame
L1 Accent consumer (sb_visual_hooks)        ← Short-lived per-channel emphasis
        ↓                                     into RenderParams
L2 Memory consumer (Stage 2, NEW)           ← Decides WHEN memory is excited /
        ↓                                     extended / reset / phase-locked /
                                              damped / boundary-policed
Visual Memory Engine port (VME, in flight)  ← Decides HOW memory exists
        ↓                                     physically: trail half-life,
                                              fractional movement, low-level
visual state / history                        persistence, byte smoothness,
        ↓                                     centre-origin propagation
final LED bytes                             ← FastLED transport
```

Layer-to-surface mapping:

| Layer | Surface targeted | Status today | This document scope |
|---|---|---|---|
| L1 Accent | `RenderParams` (PHOTONS, CHROMA, edge.strength) | Partial: single max-merged pulse, no event-id watermark | **Implementation-ready (§ 4)** |
| L2 Memory | VME port (directive vocabulary) | Greenfield design; placement and tick semantics TBD with VME | Design only (§ 5) |
| L3 Boundary | `SBModeIntent` + `confirm_switch_boundary` veto | Partial — `sb_smart_director` + `sb_visual_hooks` | Documented; not modified |
| L4 Modulation | `RenderParams` scalars (speed, photons, chroma, saturation) | Partial — `sb_smart_director` | Documented; not modified |
| L5 Autonomy | Mode selection, manual-owner gating | Partial — `sb_smart_director` | Documented; not modified |

L1 and L2 target **different write surfaces**: L1 writes to `RenderParams`, L2 writes to VME's port. They cannot conflict at the consumer chain because they write to different places.

## 1.3 L2 ↔ VME boundary (Codex: read but do not implement)

[FACT, from Captain 2026-05-28] The Visual Memory Engine workstream (2026-05-26) identified **fractional visual memory** as the real product primitive — not `CRGB16`, not Pharap `SQ15x16`, not "precision" as ideology. The engine boundary is defined at `docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md:71`:

```
Mode intent / AP state -> Visual Memory Port -> current CRGB16 adapter
                                              or compact-state adapter
                                            -> final-byte probe
                                            -> FastLED
```

The Stage 2 L2 Memory consumer is therefore **not** a new memory engine. It is the event-driven consumer that **feeds** the VME port. The bus contract is silent on memory semantics; the VME contract is silent on event semantics. L2 is the integration seam.

**Codex: do not implement L2. § 5 records design intent only. Implementation gates on VME port v1.0 + VME tick/consume semantics ratification, which are the VME workstream's deliverables, not yours.**

## 1.4 Doctrine status

[FACT] CLAUDE.md mandates `/sensorybridge-doctrine` invocation before any non-trivial audio-pipeline change. The slash-command file does not resolve in this workspace. This document is **doctrine-unverified at draft time**: it has been written against the doctrine principles encoded in CLAUDE.md (frame-timing rigour, developer-instrumentation boundary, visual impact subordinate to architecture) without the full reference doctrine artefact loaded.

[FACT] This document is **advisory**, not doctrine. It does not become a doctrine gate unless CLAUDE.md is amended to reference it.

[FACT] No firmware was edited in the production of this document. The L1 implementation is performed by you under the substantive gate in § 4.6.

---

# § 2. Lane anchors (where the bus already lives)

| Concern | File:line | Role |
|---|---|---|
| Producer composition | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:471–478` | `calculate_novelty(t_now)` → `sb_audio_snapshot_update(t_now)` → `sb_onset_beat_update(sb_audio_snapshot_read())` |
| Producer publish | `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp:52` | `sb_publish_event` under `portMUX` critical section |
| Consumer read (audio) | `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.h:42` | `SBAudioSnapshot sb_audio_snapshot_read()` |
| Consumer read (event) | `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp:259` | `SBOnsetBeatEvent sb_onset_beat_read()` |
| Single per-frame bus read | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:591–595` | Snapshots read into locals once per render frame, passed by value into consumer ticks |
| Consumer chain | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:590–612` | Smart Director tick → Visual Hooks tick → `RenderParams` apply |
| Veto handshake | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:596–598` | `confirm_switch_boundary` gates `mode_intent.wants_switch` |
| Edge config application | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:674` | `sb_visual_hooks_apply_edge_config` modifies edge mixer strength |
| L1 module | `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h`, `sb_visual_hooks.cpp` | Layer 1 consumer (current partial implementation) |
| L3/4/5 module | `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.*` | Documented, not modified |
| Trace lane | `platformio.ini:117` | `[env:k1_hardware_trace_dev]` — non-shippable |
| Serial config setter | `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:2115–2125` | Currently only toggles `hooks.enabled` — new fields default-set, no new serial commands required unless Captain requests them |

---

# § 3. Bus Contract v0.2 (advisory)

## 3.1 Purpose

One truth surface for music-derived event meaning so multiple render-local consumers act on the same facts within the same render frame. The bus exists to preserve event meaning long enough for consumers to act in sync. It does not exist to add work to the render loop, nor to be a generic message queue.

## 3.2 Surface (frozen as of v0.2)

Two readonly structs published by the producer lane and read by render-local consumers.

**`SBAudioSnapshot`** — ground state, snapshot-replace semantics. Defined in `sb_audio_snapshot.h:15–26`.

- `frame_ms`, `peak_scaled`, `vu_level`, `novelty`
- `spectral_energy`, `low_energy`, `mid_energy`, `high_energy`
- `chroma_strength`, `silence`

**`SBOnsetBeatEvent`** — event meaning, snapshot-replace semantics with age-based decay. Defined in `sb_audio_snapshot.h:28–39`.

- `event_id`, `event_ms`, `event_age_ms`
- `onset_strength`, `bass_onset_strength`
- `beat_phase`, `beat_confidence`
- `onset`, `bass_onset`, `beat`

**Closed for v0.2.** No `spectral_centroid`, no key estimate, no per-band onset breakdown, no genre tag, **no consumer-derived state** (no `accent_energy`, no `memory_energy`, no `groove_pressure`, no `boundary_score` — those are consumer-local).

## 3.3 Lanes

- **Producer lane.** `SPECTRASYNQ_K1_FIRMWARE.ino:471–478`. The bus publishes on this lane, never on the render thread.
- **Consumer lane.** `SPECTRASYNQ_K1_FIRMWARE.ino:590+` reads bus structs **once per render frame** into local immutable copies, then passes those copies into consumer ticks.
- **Cross-lane sync.** `portMUX` critical sections in `sb_publish_event` and `sb_onset_beat_read`. Snapshot-replace. No queue, no allocation, no dynamic dispatch.

## 3.4 Producer-side rules

1. **Snapshot composition is atomic.** Producer fills a local `SBOnsetBeatEvent`, then `sb_publish_event` replaces the published copy under critical section. Consumers never see a torn snapshot.
2. **Coalescing is producer-internal.** Multiple onset candidates inside one producer tick compose one event, not many. The producer enforces a refractory window — current implementation uses `SB_ONSET_REFRACTORY_MS = 240ms` — but the constant is **not part of the contract surface**. It is an implementation parameter subject to perceptual tuning.
3. **Event ageing is producer-owned.** `event_age_ms` is computed by the producer against `frame_ms`. Consumers must not derive event freshness from any other clock.
4. **Silence is a stop-the-world primitive.** `silence == true` zeros all event flags and strengths in the next snapshot. Consumers honour this without their own silence detection.

## 3.5 Consumer-side rules

1. **One bus read per render frame, shared across consumers.** The render lane reads `sb_audio_snapshot_read()` and `sb_onset_beat_read()` once per frame into local immutable copies (currently at `ino:591–592`). Those copies are passed by value into every consumer tick. **No consumer calls bus read APIs inside its own tick.** Enforced by signature: consumer ticks accept `const SBAudioSnapshot&` and `const SBOnsetBeatEvent&`.
2. **No reach-around.** Consumers never call into AP code paths to "freshen" state.
3. **Arbitration is render-side, not bus-side.** When two consumers want to modify the same `RenderParams` field, the chain order at `ino:606–608` is the arbitration rule. This order is part of the contract and must be documented when changed.
4. **Veto/handshake pattern is sanctioned.** `confirm_switch_boundary` from `sb_visual_hooks_tick` gating `smart_output.mode_intent.wants_switch` (`ino:596–598`) is the canonical pattern for consumer-to-consumer coordination.
5. **Layer-local memory is allowed; cross-layer memory is not.** Each consumer holds its own decayed pulses, event-id watermarks, last-event-ms, etc. No consumer reads another consumer's internal state.
6. **One event → one primary visual consequence.** Each bus event drives one principal behaviour per consumer. Secondary consequences must be smoothed, gated, or refused. This rule exists primarily to constrain L4 Modulation against parameter soup.

## 3.6 Latency budget

- Producer publish: **≤200 µs typical, ≤500 µs tail** (single critical section + struct copy).
- Per-frame bus read (once at the top of the render frame): **≤100 µs**.
- Per-consumer tick: **≤50 µs** under nominal load.
- Audio-to-render perceptual budget: **≤1 render frame** from event onset to first render application.

## 3.7 Instrumentation boundary

- Bus implementation contains **no MabuTrace calls and no trace-dev feature gates** by default. Production builds (`k1_hardware`, `k1_hardware_harness`) link only audited no-op macro declarations.
- Trace points exist under `FEATURE_TRACE_RENDER=1` only, in the `k1_hardware_trace_dev` environment (`platformio.ini:117`).
- Timing claims must cite a trace-dev artefact. Scalar diagnostics may corroborate but do not close causal attribution.

## 3.8 Non-goals

- The bus is not a pub/sub framework.
- The bus does not own consumer scheduling.
- The bus does not enforce arbitration (that is chain order).
- The bus does not own visual memory (that is VME's port).
- The bus does not carry consumer-derived state.

---

# § 4. L1 Accent consumer — implementation specification

This is your assignment, Codex. Everything below is at code-edit fidelity. Verify file:line citations before editing.

## 4.1 Files touched

| File | Edit type |
|---|---|
| `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h` | Replace `SBVisualHookConfig` and `SBVisualHookOutput` struct definitions. Public function signatures unchanged. |
| `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp` | Replace `sb_hook_config` default initialiser, replace all three function bodies (`sb_visual_hooks_tick`, `sb_visual_hooks_apply_render_params`, `sb_visual_hooks_apply_edge_config`). Replace internal static `sb_hook_pulse` with three pulses + three watermarks. Update setter clamp logic in `sb_visual_hooks_set_config`. |
| `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:584` | Update initialiser: `SBVisualHookOutput visual_hook_output = { 1.0f, 1.0f, 1.0f, false };` (four fields instead of three). |

**Do not touch** `serial_menu.h`. The only serial reference (`serial_menu.h:2118–2120`) toggles `config.enabled` only, which remains a field of the new `SBVisualHookConfig`. Other fields default-initialise via `sb_visual_hooks_set_config`.

## 4.2 Header changes (`sb_visual_hooks.h`)

Replace the existing struct definitions with:

```cpp
struct SBVisualHookConfig {
  bool     enabled;
  uint32_t event_window_ms;       // retained — defensive ageing window on top of event_id watermarks

  // Per-pulse decay time constants (ms). Smaller = snappier decay.
  uint32_t onset_tau_ms;          // proposed default 100
  uint32_t bass_tau_ms;           // proposed default 180
  uint32_t beat_tau_ms;           // proposed default 250

  // Per-channel coefficients applied as 1 + pulse * coeff to RenderParams.
  float    onset_to_photons;      // proposed default 0.16
  float    bass_to_edge;          // proposed default 0.20
  float    beat_to_chroma;        // proposed default 0.12

  // Hard upper bound on any (1 + pulse * coeff) scalar before it is applied.
  float    scalar_ceiling;        // proposed default 2.0
};

struct SBVisualHookOutput {
  float photon_scalar;             // 1.0 baseline; >1.0 emphasises PHOTONS
  float chroma_scalar;             // 1.0 baseline; >1.0 emphasises CHROMA
  float edge_scalar;               // 1.0 baseline; >1.0 emphasises edge mixer strength
  bool  confirm_switch_boundary;   // true only on fresh beat event (beat-only veto)
};
```

Public function signatures at `sb_visual_hooks.h:21–25` remain unchanged:

```cpp
SBVisualHookConfig sb_visual_hooks_config();
void sb_visual_hooks_set_config(const SBVisualHookConfig& config);
SBVisualHookOutput sb_visual_hooks_tick(const SBOnsetBeatEvent& event, uint32_t now_ms);
void sb_visual_hooks_apply_render_params(const SBVisualHookOutput& output, RenderParams* params);
SBEdgeMixerConfig sb_visual_hooks_apply_edge_config(const SBVisualHookOutput& output, SBEdgeMixerConfig config);
```

## 4.3 Implementation changes (`sb_visual_hooks.cpp`)

### 4.3.1 Internal state

Replace the existing line `static float sb_hook_pulse = 0.0f;` (at `sb_visual_hooks.cpp:8`) with:

```cpp
static float sb_accent_onset_pulse = 0.0f;
static float sb_accent_bass_pulse  = 0.0f;
static float sb_accent_beat_pulse  = 0.0f;

static uint32_t sb_accent_last_onset_event_id = 0;
static uint32_t sb_accent_last_bass_event_id  = 0;
static uint32_t sb_accent_last_beat_event_id  = 0;
```

Retain `static uint32_t sb_hook_last_ms = 0;` and the `sb_hook_config_mux` portMUX.

### 4.3.2 Default config initialiser

Replace the existing `sb_hook_config` initialiser (at `sb_visual_hooks.cpp:10–15`) with the new struct's field order:

```cpp
static SBVisualHookConfig sb_hook_config = {
  /* enabled            */ false,
  /* event_window_ms    */ 80UL,
  /* onset_tau_ms       */ 100UL,
  /* bass_tau_ms        */ 180UL,
  /* beat_tau_ms        */ 250UL,
  /* onset_to_photons   */ 0.16f,
  /* bass_to_edge       */ 0.20f,
  /* beat_to_chroma     */ 0.12f,
  /* scalar_ceiling     */ 2.0f
};
```

### 4.3.3 `sb_visual_hooks_set_config` clamp logic

Update the setter (currently at `sb_visual_hooks.cpp:38–48`) to clamp the new fields:

```cpp
void sb_visual_hooks_set_config(const SBVisualHookConfig& config) {
  SBVisualHookConfig next;
  next.enabled          = config.enabled;
  next.event_window_ms  = config.event_window_ms;
  next.onset_tau_ms     = config.onset_tau_ms == 0 ? 1 : config.onset_tau_ms;   // avoid div-by-zero
  next.bass_tau_ms      = config.bass_tau_ms  == 0 ? 1 : config.bass_tau_ms;
  next.beat_tau_ms      = config.beat_tau_ms  == 0 ? 1 : config.beat_tau_ms;
  next.onset_to_photons = sb_hook_clamp(config.onset_to_photons, 0.0f, 1.0f);
  next.bass_to_edge     = sb_hook_clamp(config.bass_to_edge,     0.0f, 1.0f);
  next.beat_to_chroma   = sb_hook_clamp(config.beat_to_chroma,   0.0f, 1.0f);
  next.scalar_ceiling   = sb_hook_clamp(config.scalar_ceiling,   1.0f, 4.0f);

  portENTER_CRITICAL(&sb_hook_config_mux);
  sb_hook_config = next;
  portEXIT_CRITICAL(&sb_hook_config_mux);
}
```

### 4.3.4 `sb_visual_hooks_tick` — replace function body

Replace the body of `sb_visual_hooks_tick` (currently at `sb_visual_hooks.cpp:50–87`) with the three-pulse, watermarked version. Required semantics:

1. Compute `dt_ms` against `sb_hook_last_ms` (existing pattern).
2. Decay each of `sb_accent_onset_pulse`, `sb_accent_bass_pulse`, `sb_accent_beat_pulse` by `dt_ms / tau_ms` per pulse (clamped to [0,1]).
3. If `!config.enabled`, return output with all scalars = 1.0 and `confirm_switch_boundary = false`. **Do not** skip the decay step in this case — pulses should continue decaying even when disabled, so toggling enabled mid-event does not produce stale state.
4. Compute event freshness: `age_ms = (event.event_ms != 0 && now_ms >= event.event_ms) ? (now_ms - event.event_ms) : UINT32_MAX`. An event is **eligible for injection** if `age_ms <= config.event_window_ms`.
5. For each band:
   - **Onset.** If `event.onset && eligible && event.event_id != sb_accent_last_onset_event_id`: set `sb_accent_onset_pulse = max(sb_accent_onset_pulse, event.onset_strength)`; set `sb_accent_last_onset_event_id = event.event_id`.
   - **Bass.** If `event.bass_onset && eligible && event.event_id != sb_accent_last_bass_event_id`: set `sb_accent_bass_pulse = max(sb_accent_bass_pulse, event.bass_onset_strength)`; set `sb_accent_last_bass_event_id = event.event_id`.
   - **Beat.** If `event.beat && eligible && event.event_id != sb_accent_last_beat_event_id`: set `sb_accent_beat_pulse = max(sb_accent_beat_pulse, event.beat_confidence)`; set `sb_accent_last_beat_event_id = event.event_id`; also set `output.confirm_switch_boundary = true` (beat-only veto).
6. Compute output scalars, clamped to `[1.0, config.scalar_ceiling]`:
   - `output.photon_scalar = clamp(1.0 + sb_accent_onset_pulse * config.onset_to_photons, 1.0, ceiling)`
   - `output.chroma_scalar = clamp(1.0 + sb_accent_beat_pulse  * config.beat_to_chroma,  1.0, ceiling)`
   - `output.edge_scalar   = clamp(1.0 + sb_accent_bass_pulse  * config.bass_to_edge,    1.0, ceiling)`
7. Return `output`.

**Important — `max` not assignment.** When injecting, use `max(pulse, strength)` rather than `pulse = strength`. This handles the edge case where a stronger event arrives while a weaker one is still decaying — the weaker pulse should not overwrite the stronger one if the stronger is still in the air. (Practically rare because event_id watermarking already prevents same-event re-injection, but defensible against producer-side strength jitter on close events.)

**Decay formula.** Use `decay = clamp(dt_ms / tau_ms, 0.0f, 1.0f); pulse *= (1.0f - decay);` for each pulse with its own tau. This is the same one-pole IIR pattern as the current code, just with three independent decays.

### 4.3.5 `sb_visual_hooks_apply_render_params` — replace function body

Replace the body (currently at `sb_visual_hooks.cpp:89–96`) with:

```cpp
void sb_visual_hooks_apply_render_params(const SBVisualHookOutput& output, RenderParams* params) {
  SBVisualHookConfig config = sb_visual_hooks_config();
  if (params == nullptr || !config.enabled) {
    return;
  }
  params->PHOTONS = sb_hook_clamp(params->PHOTONS * output.photon_scalar, 0.0f, 2.0f);
  params->CHROMA  = sb_hook_clamp(params->CHROMA  * output.chroma_scalar, 0.0f, 2.0f);
}
```

The current code applies the same scalar to both PHOTONS and CHROMA. The new code applies the onset-driven `photon_scalar` to PHOTONS and the beat-driven `chroma_scalar` to CHROMA — that is the meaning-preserving move.

### 4.3.6 `sb_visual_hooks_apply_edge_config` — replace function body

Replace the body (currently at `sb_visual_hooks.cpp:98–105`) with:

```cpp
SBEdgeMixerConfig sb_visual_hooks_apply_edge_config(const SBVisualHookOutput& output, SBEdgeMixerConfig config) {
  SBVisualHookConfig hook_config = sb_visual_hooks_config();
  if (!hook_config.enabled) {
    return config;
  }
  config.strength = sb_hook_clamp(config.strength * output.edge_scalar, 0.0f, 1.0f);
  return config;
}
```

The edge mixer strength is now driven by the bass-pulse-derived `edge_scalar`, separating bass response from primary brightness response.

## 4.4 Call-site change (`SPECTRASYNQ_K1_FIRMWARE.ino:584`)

The current line:

```cpp
SBVisualHookOutput visual_hook_output = { 1.0f, 1.0f, false };
```

becomes (three scalars + boolean):

```cpp
SBVisualHookOutput visual_hook_output = { 1.0f, 1.0f, 1.0f, false };
```

No other call sites need changes. `ino:474`, `ino:586`, `ino:595`, `ino:608`, `ino:674` all use the public functions, whose signatures are unchanged.

## 4.5 Non-goals (do not introduce)

- No new bus primitives (no new fields in `SBOnsetBeatEvent` or `SBAudioSnapshot`).
- No reads of any state outside the bus copies passed in via parameters (`event`, plus the per-frame `audio` read by the caller). Specifically: no direct calls to `sb_audio_snapshot_read()` or `sb_onset_beat_read()` from inside `sb_visual_hooks_tick`.
- No new MabuTrace calls. Existing tracing in the render loop already covers consumer-tick budget if `FEATURE_TRACE_RENDER=1`.
- No serial commands added or removed. `serial_menu.h:2118–2120` continues to toggle `enabled` only.
- No changes to `sb_smart_director.*`. The L3/L4/L5 surfaces stay where they are.
- No changes to FastLED, gamma, soft-clip, or `leds_16`.

## 4.6 Substantive gate

L1 implementation passes when **all** of the following hold. None require a paperwork ratification cycle.

1. Adds no new bus primitive (event surface unchanged from v0.2).
2. Reads only the existing `SBAudioSnapshot` and `SBOnsetBeatEvent` structs through the per-frame copies passed in by the caller.
3. Does not touch VME, FastLED, gamma, soft-clip, or any pixel-level state.
4. All output scalar multipliers are clamped (no unbounded amplification).
5. Pulses decay to zero under sustained `silence == true`.
6. Pulses do not re-inject from the same `event_id` (event-id watermarks held per band).
7. `confirm_switch_boundary` opens only on a fresh `beat` event (not on stray `onset` or `bass_onset`).
8. Visual A/B (§ 7.3) passes on three labelled clips.
9. Trace-dev timing sanity (§ 7.2) passes — no widening of consumer-tick tail by more than 10%.
10. Production build (`k1_hardware`) symbol audit shows no MabuTrace symbols linked (§ 7.4).

---

# § 5. L2 Memory consumer — design (do not implement)

This section records design intent so the L2 surface is visible to other workstreams. **Codex: do not implement any of § 5.** L2 implementation gates on VME port v1.0 + tick semantics ratification.

## 5.1 Inputs

- `SBOnsetBeatEvent`: full event surface from contract v0.2.
- `SBAudioSnapshot`: full snapshot surface from contract v0.2, used for `silence` and for sustained-energy detection.

## 5.2 Output directive vocabulary (precision-neutral)

| Directive | Fires on | VME primitive(s) targeted |
|---|---|---|
| `impulse(strength, band, shape)` | fresh `onset` / `bass_onset` event_id | Impulse memory, attack shape, trail half-life |
| `extend(envelope)` | continued energy in a band post-onset | Release shape, low-level persistence |
| `reset(scope)` | `silence == true` for ≥ silence_hold_ms | Silence posture, idle state |
| `boundary_policy(policy)` | mode-switch boundary confirmed; `policy ∈ {soft_reset, redirect, compress_tail, phase_reseed, hard_reset}` | Layer priority, phrase handoff |
| `phase_lock(beat_phase, confidence)` | `beat_confidence >= floor` | Beat-phase memory |
| `damp(rate)` | sustained noise or low-confidence churn | Refractory behaviour, event salience |

**Boundary-policy default = `soft_reset`** (preserves direction, reduces magnitude). Not `hard_reset`. Phrase boundaries are the moment when memory handoff matters most.

**Doctrinal constraint.** L2 directives are precision-neutral: the vocabulary does not name `CRGB16`, `SQ15x16`, byte width, or any storage format. VME owns precision; L2 owns event-to-memory translation only.

## 5.3 Build order (constrained by VME priority)

VME's primitive catalogue at `docs/forensics/2026-05-26-visual-memory-research-lane-findings.md:120` ranks primitives P0/P1/P2. L2's build order is derived from this ranking — L2 cannot exercise P2 primitives until VME proves them via final-byte evidence.

| VME priority | VME primitive | L2 directive | L2 wave |
|---|---|---|---|
| P0 | trail half-life, low-level persistence | `impulse`, `extend` | **Wave 1** |
| P1 | attack shape, release shape, layer priority | `impulse` (shape param), `extend` (envelope), `reset` (on silence) | **Wave 1** |
| P2 | refractory behaviour, beat-phase memory, event salience | `damp`, `phase_lock`, salience-weighted impulse, non-default boundary policies | **Wave 2** |

## 5.4 L2 chain placement (unratified)

The candidate placement is between `sb_visual_hooks_apply_render_params` and `push_render_params` (around `ino:608–609`), but this assumes VME consumes directives synchronously and applies them to the current frame. If VME is queue-based, applies on the next frame, or ticks at a different point in the render pipeline, the placement is wrong.

**Open questions to VME workstream:**

1. What is the exact port surface? Are the six directives plausible names for VME-owned operations, or does VME want a different vocabulary?
2. Does VME want event metadata (`event_id`, `event_ms`) carried with each directive for traceability, or should L2 keep that internally?
3. What is VME's tick/consume model? Synchronous (directives applied within current frame) or asynchronous (next frame)? Queued, latched, or snapshot-replaced?
4. Where in the chain does VME tick — before or after `RenderParams` commit at `ino:609`?
5. Does L2 plug into the existing `CRGB16` adapter for proof-of-concept, or must it wait for the compact-state adapter?
6. What is VME's refractory tolerance for `impulse` directives?

---

# § 6. Parallel-branch plan

| Branch | Implementation gating | Notes |
|---|---|---|
| Bus contract v0.2 commit | Captain has ratified L1 readiness; v0.2 is the working advisory contract | This document. Advisory, not doctrine. |
| **L1 Accent upgrade** | **§ 4.6 substantive gate (no contract sign-off blocker)** | **Your assignment, Codex.** |
| L2 Memory consumer | Design only until VME port v1.0 + tick semantics ratified | Implementation gated on VME. |
| VME Level 1 | Out of scope of this document | Continues under its existing sandbox plan. |

L1 and L2 cannot conflict at the consumer chain because L2 writes to VME's port, not to `RenderParams`.

---

# § 7. Verification procedure

Codex: execute steps in order. Report results using the status labels in § 7.5.

## 7.1 Build verification

Build the firmware on two environments. Both must succeed.

```bash
cd "/Users/spectrasynq/SensoryBridge-main 9"
pio run -e k1_hardware
pio run -e k1_hardware_trace_dev
```

Pass = both environments build with no errors and no new warnings (relative to a pre-change baseline). If a new warning appears, escalate.

Do **not** run `pio run -t upload` without Captain's explicit go-ahead. Uploading writes firmware to the device.

## 7.2 Trace-dev timing verification

Required for any timing claim. Scalar diagnostics alone do not close causal attribution.

Procedure:

1. Build `k1_hardware_trace_dev` (already done in § 7.1).
2. Capture trace timelines for the following events, with the firmware running on hardware. **Captain owns hardware capture** — coordinate with Captain to obtain trace runs.
3. Compute the metrics below against a **pre-change baseline** captured on the same hardware before your changes landed.

Metrics and thresholds:

| Metric | Method | Pass threshold |
|---|---|---|
| Producer publish latency (typical, P99) | Trace `sb_publish_event` enter/exit | Typical ≤200 µs; P99 ≤500 µs |
| Per-frame bus read latency | Trace `ino:591–595` block | ≤100 µs |
| Consumer-tick latency for `sb_visual_hooks_tick` | Trace function enter/exit | P99 widening ≤10% vs baseline |
| Audio-to-render causality | Trace `sb_publish_event` → corresponding `RenderParams` write | ≤1 render frame across all test clips |

If any metric fails its threshold, **stop** and escalate. Do not proceed to § 7.3.

## 7.3 Visual A/B verification

Perceptual evidence on three labelled clips. **Captain owns hardware capture and clip selection.** Coordinate accordingly.

Clips:

1. **Kick-heavy electronic track** — proves `bass_pulse` separation. Pass = edges respond to kicks without flooding the primary channel.
2. **Snare-and-hat acoustic track** — proves `onset_pulse` separation, no plateau on dense hits. Pass = each snare hit produces a distinct accent that decays cleanly; hi-hat patterns do not produce a held plateau.
3. **Locked-tempo track with a tempo change** — proves `beat_pulse` + boundary handshake + event-id watermarking. Pass = beat-locked sections show subtle colour breathing; tempo change produces a clean phrase boundary; the same beat does not re-inject the pulse across multiple frames.

Pass overall = all three clips show perceptibly distinct band responses; pulses decay cleanly without plateau or stutter; beat-locked sections show colour breathing absent in the pre-change build.

If any clip is ambiguous, escalate (§ 0.4).

## 7.4 Production-shippability check

After L1 lands, confirm no MabuTrace symbols are linked into the production build.

```bash
cd "/Users/spectrasynq/SensoryBridge-main 9"
pio run -e k1_hardware -t size
nm .pio/build/k1_hardware/firmware.elf | grep -i mabutrace
```

Pass = `nm` returns no matches. If matches appear, you have introduced a doctrine violation (CLAUDE.md Developer Instrumentation Boundary). Diagnose and fix before declaring L1 done.

Repeat for `k1_hardware_harness`:

```bash
pio run -e k1_hardware_harness -t size
nm .pio/build/k1_hardware_harness/firmware.elf | grep -i mabutrace
```

Same pass condition.

## 7.5 Status labels (per doctrine)

Report L1 status using exactly one of these labels:

- **verified** — all four verification phases (§ 7.1, § 7.2, § 7.3, § 7.4) passed.
- **scalar-only** — § 7.1 + § 7.3 + § 7.4 passed but § 7.2 was not run (or trace-dev unavailable). May merge to a branch but **not** to a production tag.
- **blocked** — § 7.1, § 7.2, or § 7.4 failed and root cause is not within scope to fix. Captain notified.
- **approval** — § 7.3 evidence ambiguous; requires Captain judgement.

Do not use any other label. Do not modify these definitions.

---

# § 8. Named risks the contract exists to prevent

Three failure modes recur in audio-reactive systems. Each layer has a named risk; each consumer-side rule maps to one or more.

1. **Cheap strobe (L1 failure).** Whole-device flashes on every kick. Mitigated by per-band separation (onset/bass/beat → PHOTONS/edge/CHROMA), spatial differentiation, clamped scalars, and event-id watermarking. Rules cited: § 3.5.5, § 3.5.6.
2. **Parameter soup (L4 failure).** Every event modulates every visual parameter. Mitigated by the "one event → one primary visual consequence" rule (§ 3.5.6) and by explicit consumer surface boundaries.
3. **Autonomy ownership conflicts (L5 failure).** Smart Assist or director becomes a god-object that overrides L1–L4 by reading their internal state or by writing the same render fields outside the chain. Mitigated by § 3.5.5 (layer-local memory) and § 3.5.4 (veto/handshake as the only cross-consumer coordination pattern).

L1's accent intent: **pressure moving through the light field, not a nightclub strobe.** Spatial differentiation matters. Treble onset → primary brightness. Bass onset → edge / secondary channel pressure. Locked beat → subtle chroma breathing. The K1 LGP physically supports this differentiation; the contract preserves the distinction so it can be felt.

---

# § 9. Open decisions

| # | Decision | Owner | Blocks |
|---|---|---|---|
| D1 | VME port v1.0 ratification | VME workstream | L2 implementation; contract v0.3 inlining of § 5 |
| D2 | VME tick/consume semantics defined | VME workstream | L2 chain placement ratification |
| D3 | Whether `/sensorybridge-doctrine` is reinstalled/regenerated in the workspace | Captain | Future audio-pipeline changes requiring doctrine gate |
| D4 | Whether reference doctrine in `Lightwave-Ledstrip/firmware-v3/docs/audio-visual/` should be cross-referenced into this contract | Captain | Strength of doctrinal anchoring; not blocking L1 |
| D5 | Whether L1 default coefficients (0.16 / 0.20 / 0.12) and taus (100/180/250 ms) need perceptual tuning | Captain after § 7.3 | Final L1 promotion |

L1 implementation is **not blocked** on any of these. L1 may proceed against the substantive gate in § 4.6.

---

# § 10. Cross-references

## 10.1 Local (K1) artefacts cited

- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:471–478` — producer composition lane.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:584` — `SBVisualHookOutput` initialiser (call-site change in § 4.4).
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:591–595` — single per-frame bus read.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:590–612` — consumer chain.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:674` — edge config application.
- `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.h:15–39` — `SBAudioSnapshot`, `SBOnsetBeatEvent` types.
- `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp:52, :259` — publish/read under `portMUX`.
- `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp:24–29` — refractory and event-window constants (implementation parameters, not contract).
- `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h`, `sb_visual_hooks.cpp` — L1 module (your target).
- `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.h` — L3/L4/L5 surfaces (not modified).
- `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:2115–2125` — serial config setter for `hooks.enabled`.
- `platformio.ini:117` — `k1_hardware_trace_dev` environment (non-shippable).
- `docs/forensics/2026-05-26-visual-memory-research-lane-findings.md` — VME primitive catalogue and P0/P1/P2 ranking.
- `docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md` — VME architecture, hexagonal port plan, non-negotiables.
- `docs/forensics/2026-05-25-lightwave-v3-harvest-map.md` — candidate primitives from reference doctrine.

## 10.2 Reference doctrine (informs, does not override)

- `Lightwave-Ledstrip/firmware-v3/docs/audio-visual/AUDIO_FEATURE_SURFACE_V2_CONTRACT.md`
- `Lightwave-Ledstrip/firmware-v3/docs/audio-visual/audio-visual-contract-surface.md`
- `Lightwave-Ledstrip/firmware-v3/docs/audio-visual/ADR_2026-03-25_FIRST_CLASS_ONSET_SURFACE.md`
- `Lightwave-Ledstrip/firmware-v3/docs/debugging/MABUTRACE_GUIDE.md`
- `Lightwave-Ledstrip/firmware-v3/docs/debugging/TRACE_INSTRUMENTATION_SPEC.md`
- `Lightwave-Ledstrip/firmware-v3/docs/debugging/trace_spec_sections/02_audio_render_handoff.md`

## 10.3 Source artefacts and reviews

- `uploads/onset-beat-leverage-map-v2.html` — original v2 architecture diagram.
- Independent review (2026-05-28, "MODE: EXPLORATION REVIEW") — directional approval, surfaced bus-surface bloat risk and arbitration concerns; informed § 3.5.6 and § 8.
- Independent review (2026-05-28, second round) — surfaced single-bus-read rule, event-id watermarking, L2 placement uncertainty, boundary-vs-silence distinction, refractory constant. Informed contract v0.1→v0.2 corrections.

---

# § 11. Codex completion report template

When you finish, return a report in this shape. Do not improvise the structure.

```
L1 Accent Upgrade — Completion Report
======================================

Status label: [verified | scalar-only | blocked | approval]

Files changed:
  - SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h
  - SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp
  - SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino  (line 584 only)

Build verification (§ 7.1):
  - k1_hardware:           [PASS / FAIL]
  - k1_hardware_trace_dev: [PASS / FAIL]
  Warnings introduced:     [count, list]

Trace-dev verification (§ 7.2):
  - Producer publish typical/P99: [µs / threshold pass/fail]
  - Per-frame bus read latency:    [µs / threshold pass/fail]
  - sb_visual_hooks_tick P99 widening: [% / threshold pass/fail]
  - Audio-to-render causality:      [frames / threshold pass/fail]

Visual A/B verification (§ 7.3):
  - Clip 1 (kick-heavy):      [PASS / FAIL / approval / notes]
  - Clip 2 (snare-and-hat):   [PASS / FAIL / approval / notes]
  - Clip 3 (locked tempo):    [PASS / FAIL / approval / notes]

Production-shippability check (§ 7.4):
  - nm k1_hardware mabutrace:           [no matches / matches list]
  - nm k1_hardware_harness mabutrace:   [no matches / matches list]

Escalations raised:
  [list of § 0.4 escalations, or "none"]

Open follow-ups:
  [anything you found that should be tracked but is out of scope]

Doctrine compliance:
  [FACT] Production builds (k1_hardware, k1_hardware_harness) link no MabuTrace symbols.
  [FACT] No calibration commands were issued during verification.
  [FACT] No changes outside declared scope (§ 0.1).
```

---

**End of unified proposal.** No firmware was edited in the production of this document. L1 implementation is your assignment, Codex. L2 implementation is gated and not part of this handoff. Escalate per § 0.4 if anything in this document does not match the code you find.
