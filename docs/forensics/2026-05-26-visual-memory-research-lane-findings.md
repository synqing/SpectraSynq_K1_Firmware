---
abstract: "Read-only research-lane findings for the Level 1 Visual-Memory Engine workstream. The pass consolidates six SSA lane reports, local source evidence, and external analogues into a perception-first primitive catalogue, final-byte probe contract, LUT feasibility matrix, and sandbox handoff packet."
---

# Visual-Memory Research Lane Findings

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Mode | Read-only research execution. No firmware edit, serial, upload, build, commit, branch, or tag. |
| Governing skill | `/Users/spectrasynq/.agents/skills/perception-first-engineering/SKILL.md` |
| Input plan | `docs/forensics/2026-05-26-visual-memory-research-lane-plan.md` |
| Downstream plan | `docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md` |
| Agent lanes | R1 primitive taxonomy, R2 mechanism map, R3/R7 collapse and simplification, R4/R8 materiality and probe contract, R5 LUT feasibility, R6 cross-domain analogues |

## 1. Executive Result

[FACT] K1 final LED output is 8-bit per channel. `CRGB16` is three `SQ15x16` channels in `SPECTRASYNQ_K1_FIRMWARE/constants.h:141-144`; `SQ15x16` aliases `SFixed<15,16>` in `libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h:20-22`; final `leds_out[]` bytes are written in `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:280-338`; FastLED `CRGB` channels are `fl::u8` in `.pio/libdeps/k1_hardware/FastLED/src/crgb.h:85-107`.

[INFERENCE] The broad claim "16-bit colour is valuable" is overclaimed for WS2812 output. The value-bearing claim is narrower and stronger: **fractional visual memory can alter final byte sequences over time**.

[FACT] Bloom transports previous `CRGB16` state through fractional `draw_sprite()` with alpha, then inserts at centre indices `79/80` and snapshots history before display-only edge fade/mirror. Sources: `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp:7-14`, `:82-89`, `:93-112`, and `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:1586-1628`.

[FACT] Waveform Fast and Hybrid preserve live state through fades, `dt`-bounded shift accumulators, centre/upper-half source placement, and mirrored output. Sources: `SPECTRASYNQ_K1_FIRMWARE/light_mode_waveform_fast.cpp:7-21`, `:129-168`; `SPECTRASYNQ_K1_FIRMWARE/light_mode_waveform_hybrid.cpp:101-128`, `:130-214`.

[INFERENCE] Do not globally remove `CRGB16` or Pharap `SQ15x16` during Level 1. Also do not preserve them as ideology. The correct next move is a sandboxed final-byte paired probe that proves which primitives survive to WS2812 bytes and which are internal churn.

Highest-confidence next action:

```text
Build VPAB final-byte shadow probe first.
Target Bloom first.
Target Waveform Fast second.
Compare current CRGB16 history against compact/Q0.16 and RGB8 adversarial baselines.
Judge only after final-byte metrics and Captain-visible A/B agree.
```

## 2. Perception-First Gate Output

```text
Mechanism:
  Pharap SQ15x16, K1 CRGB16 buffers, temporal dithering, Bloom/Waveform state history,
  palette/HSV round-trips, soft clip, secondary channel render state.

Perceived output:
  Centre-origin motion, trail strength, low-light persistence, colour clarity,
  musical causality, dual-channel richness, and responsiveness on the K1 LGP.

Collapse points:
  WS2812 8-bit output, FastLED CHSV/CRGB 8-bit source generation, ColorFromPalette()
  returning CRGB, pre-output VP hashes, dormant gamma/FastLED dither toggles.

Survival paths:
  Stateful history before quantisation, fractional transport, temporal dither,
  centre-origin insert/shift, live secondary channel state, hue-preserving soft clip.

Simpler alternative:
  Compact Q0.16 state, RGB8 adversarial baseline, fixed/LUT decay and shift kernels,
  FastLED-native palette/HSV source paths, soft-clip scale LUT, explicit render context.

Materiality thresholds:
  Final 8-bit byte deltas, trail half-life, low-light tail integral, COM/COM slope,
  saturation floor, hue continuity, flicker score, render time, heap, and Captain A/B.

Evidence:
  Source lines cited throughout this document. No runtime capture was performed in this lane.

Decision:
  Preserve the primitive, not the inherited implementation. Build proof machinery before
  replacing or defending the dependency.

Next experiment:
  VPAB final-byte probe in a sandbox, then Bloom compact-memory shadow path.
```

## 3. Core Evidence

| Topic | Evidence | Interpretation |
|---|---|---|
| Fixed-point type | `SQ15x16` is `SFixed<15,16>` in `SFixedCommon.h:20-22`; `SFixed` internal type is sized from logical integer/fraction bits in `SFixed.h:31-45`. | Useful for live fractional state, not proof of final colour precision. |
| CRGB16 buffer cost | Root static buffers include `leds_16`, primary/secondary history, snapshots, FX, temp, UI in `globals.h:153-160`. | Compact state could save DRAM, but only if final-byte trails survive. |
| Source colour collapse | `hsv()` converts to `CHSV(uint8_t(...))` then `CRGB` before lifting to `CRGB16` in `led_utilities.h:76-90`. | Stateless HSV precision is mostly gone before CRGB16. |
| Palette collapse | `palette_manual_colour()` calls FastLED `ColorFromPalette()` and lifts `CRGB` to `CRGB16` in `lightshow_modes.h:113-125`. | Palette sampling itself is not a reason to keep CRGB16 globally. |
| Chroma vector live state | `palette_chroma_colour()` computes live chroma vector with `cosf`, `sinf`, `atan2f`, and energy weighting in `lightshow_modes.h:128-172`. | Precompute unit vectors, not the whole function. |
| Soft clip | `clip_led_values()` scales all channels together above `SOFT_CLIP_KNEE` in `led_utilities.h:92-127`; constants at `constants.h:306-313`. | Strong LUT candidate, but must preserve peak colour clarity. |
| Temporal dither | Default `TEMPORAL_DITHERING=true` in `globals_config.cpp:70-76`; dither table in `constants.h:334-338`; final writes in `led_utilities.h:280-338`. | Real sub-byte survival path; do not remove without low-light/flicker proof. |
| Output gamma | Gamma LUT exists but `ENABLE_OUTPUT_GAMMA=0` in `constants.h:251-287`. | Dormant experiment hook, not current product value. |
| FastLED dither | `ENABLE_FASTLED_DITHER=0` in `constants.h:229-237`; `show_leds()` disables FastLED dither in `led_utilities.h:874-878`. | Keep disabled unless one-toggle A/B proves value. |
| Final output boundary | `show_leds()` applies brightness, clip, scale, secondary prep, quantise, optional reverse, dither mode, then `FastLED.show()` in `led_utilities.h:739-882`. | VPAB must measure after this equivalent final-byte boundary. |
| Current probe gap | `vp_probe_hash_leds()` hashes pre-output `CRGB16` after 16-bit quantisation in `lightshow_modes.h:352-389`; `frame_dump_tick()` samples before `show_leds()` in `lightshow_modes.h:406-423`. | Existing VP probes cannot prove visible WS2812 equivalence. |
| Performance probe | `VPF,ver=1` reports render, prep, quant, show, frame, heap, over-budget, dropped in `serial_menu.h:2916-2988`. | Timing guard only; not perception proof. |
| Dual-channel state | Primary is rendered, then secondary snapshots/restores runtime and channel buffers in `SPECTRASYNQ_K1_FIRMWARE.ino:541-583`. | Protected primitive: simplify ownership, do not merge state. |

External analogues used as hypotheses, not product proof:

- [W3C Compositing and Blending Level 1](https://www.w3.org/TR/compositing-1/) formalises compositing, Porter-Duff operators, blending, and isolated groups. K1 analogue: layer priority and alpha budget before final bytes.
- [ETC Eos Manual Timing](https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/07_Setup/02_User/Manual_Timing.htm) separates timing for intensity up, intensity down, focus, colour, and beam. K1 analogue: split timing lanes for attack, release, width, colour, and diffusion.
- [MusicDSP envelope detector notes](https://www.musicdsp.org/_/downloads/en/latest/pdf/) describe attack/release coefficients for envelope following. K1 analogue: event-class visual envelopes.
- [FastLED ColorFromPaletteExtended docs](https://fastled.io/docs/d1/dfb/colorutils_8h_a6a2c1ac508cdebdb083137793e219560.html) show a `u16` palette index variant. K1 analogue: palette-source shadow test, not a justification for global CRGB16.

## 4. Primitive Catalogue

Priority key:

- P0: must be in the Level 1 proof path.
- P1: strong candidate for Level 1 or immediate follow-up.
- P2: research candidate; needs final-byte and Captain-visible evidence before implementation.

| Priority | Primitive | Perceived value | Current mechanism | Final-output metric | Simpler alternative | Falsification |
|---|---|---|---|---|---|---|
| P0 | Trail half-life | Hits leave intentional residue without mush. | Bloom alpha/history; Waveform fade. | Last nonzero frame, tail integral, decay curve. | RGB8 or compact fade buffer. | Simpler path within 2 frames and no A/B loss. |
| P0 | Fractional movement | Motion reads smooth and outward, not stair-stepped. | Bloom `draw_sprite()` fractional mix; Waveform `dt` accumulator. | COM slope, byte step jerk, changed channel %. | Integer shift only. | Integer path preserves COM and smoothness. |
| P0 | Centre-origin propagation | K1 reads as edge-injected centre-out object, not a generic strip. | Bloom indices `79/80`; Hybrid centre seed; outward shift helpers. | Origin, left/right parity, centre-to-edge transfer. | Single-side sweep or full-strip pulse. | Non-centre path is not worse in A/B. |
| P0 | Low-level persistence | Quiet tails remain alive without immediate byte visibility. | CRGB16 state plus dither. | Low-light nonzero duration, low-light tail integral. | Drop/clamp below 1 byte. | Tail integral delta <=10% and no A/B loss. |
| P0 | Byte-sequence smoothness | No low-light sparkle/stutter. | K1 4-step temporal dither. | p95 byte delta/frame, flicker score. | Truncation or FastLED-only dither. | No visible flicker or byte smoothness loss. |
| P0 | Final-byte probeability | Decisions do not preserve invisible churn. | Missing today; current VPO/FDUMP are pre-output. | VPAB final-byte metrics. | Reuse upstream hash. | Upstream hash must not be accepted as visual proof. |
| P1 | Saturation preservation | Colours stay vivid at peaks. | Hue-preserving soft clip. | Saturation floor, white-bias score. | Hard clamp or LUT scale. | Clamp/LUT matches peak clarity. |
| P1 | Hue continuity | Colour evolves intentionally, no popping. | Chroma vector palette path; Waveform chroma blend. | p95 hue delta, hue-pop count. | Instant palette lookup or fixed fallback. | No visible colour intelligence loss. |
| P1 | Attack shape | Hits feel immediate and weighty. | Audio smoothing and mode-specific inserts. | Onset-to-first-byte, first 3-frame energy slope. | Fixed one-frame impulse. | No loss of snap or impact. |
| P1 | Release shape | Decay feels graceful, not dead or smeared. | Waveform idle fade; Bloom alpha; candidate envelope lanes. | Decay tau, tail integral, zero-crossing. | Linear fade. | Linear fade matches byte and A/B. |
| P1 | Layer priority | Overlapping memories remain readable. | Today mostly implicit/additive. | Layer dominance, local contrast after overlap. | Always additive/max. | Additive-only does not create mush. |
| P1 | Cross-channel independence | Dual-strip richness survives. | Separate primary/secondary state and snapshots. | Channel correlation, COM/energy divergence. | Mirrored single buffer. | Mirroring is preferred or indistinguishable. |
| P1 | Silence posture | Silent passages look intentional. | `silent_scale`, ambient-floor hook. | Idle energy, stale memory, idle motion. | Blackout. | Blackout is preferred in real capture. |
| P2 | Refractory behaviour | Fast rhythms stay readable. | Present in v3 references; not proven active in root monolith. | Retrigger recovery, event separation. | Trigger every peak. | Unguarded path is not mushier. |
| P2 | Beat-phase memory | Visuals feel locked to music. | v3 musical grid references; not proven active in root monolith. | Beat phase error, beat-aligned tail energy. | Amplitude-only response. | Amplitude-only feels equally locked. |
| P2 | Event salience ranking | Important musical events win visual budget. | v3 salience references; not proven active in root monolith. | Saliency-to-byte-energy correlation. | Equal weighting. | Equal weighting is not less musical. |
| P2 | Gesture identity | Modes remain recognisable. | Distributed mode-specific history and colour paths. | COM/width/hue/trail bundle plus Captain label match. | Shared generic envelope. | Shared envelope preserves recognisability. |
| P2 | Temporal history rejection | Useful trails remain; stale ghosts are rejected. | Not explicit today. | Ghost energy after direction/colour change. | Current fade only. | Current fade has equal or lower ghost energy. |
| P2 | Exposure debt | Peaks do not damage the following moment. | Soft clip and brightness path. | Saturation/luma recovery after peak. | Stateless clamp. | No post-peak dullness or washout difference. |
| P2 | Locality preservation | The viewer can track where an event came from. | Dot inserts and centre seeds. | Footprint COM variance, footprint IoU. | Global pulse. | Global pulse is equally readable. |
| P2 | Surprise bandwidth | Repetition stays engaging without chaos. | Hue shift, palette shifts, possible narrative systems. | Novelty rate, entropy window. | Deterministic loop. | Deterministic path stays equally captivating. |

## 5. Mechanism-To-Decision Map

| Mechanism | What it is doing | Collapse/survival | Decision |
|---|---|---|---|
| Bloom history | Shifts previous state fractionally, decays by alpha, inserts centre colour, mirrors for display. | Survival path: trail half-life, fractional movement, centre-origin propagation. | Protected until VPAB proves compact equivalent. |
| Bloom colour source | Builds chroma/palette colour, then may round-trip through `CRGB` for saturation/hue forcing. | Collapse point: 8-bit colour source before CRGB16 history. | Simplification candidate after history probe. |
| Waveform Fast history | Fades state, accumulates real-time shift, inserts reactive dot, mirrors. | Survival path: trail memory and dt-correct transport. | Protected; compact-state adversarial test second. |
| Waveform Hybrid seed | Builds centre-origin bilateral radius from waveform history and VU/peak gates. | Survival path: impulse width and audio causality. | Candidate after Bloom/Fast. |
| Temporal dither | Carries fractional values into final bytes via 4-step threshold pattern. | Survival path: low-level persistence and byte smoothness. | Protected; separate low-light flicker lane. |
| Soft clip | Compresses all channels proportionally above knee. | Colour-clarity survival path, not visual-memory state. | LUT candidate with saturation proof. |
| Palette/HSV helpers | Produce 8-bit colour then lift to CRGB16. | Mostly source-side collapse. | Keep or simplify FastLED-native; do not defend as precision. |
| Output gamma | Existing 256-entry LUT but disabled. | Dormant. | A/B hook only, not current value. |
| FastLED binary dither | Explicitly disabled. | Dormant. | A/B hook only, with washout stop condition. |
| Secondary channel render | Uses separate state, snapshots, temporary config mutation, restore. | Survival path: cross-channel independence; architecture is fragile. | Preserve behaviour; simplify ownership later. |
| `vp_probe` / `frame_dump` | Pre-output CRGB16 hash/energy/COM. | Evidence collapse: proves internal state, not final bytes. | Keep for Tier A/B, but add VPAB. |

## 6. LUT And Simulation Feasibility

| Candidate | LUT/simulation viability | Must remain live | Risk | Recommendation |
|---|---|---|---|---|
| Soft-clip scale table | High. 256 or 1024-entry scale table can replace per-pixel division. | Current max channel and channel ratios. | Peak hue/saturation error near knee. | First low-risk LUT candidate. |
| Bloom edge fade table | High. Edge fade is deterministic by index. | Display buffer and `NATIVE_RESOLUTION`. | Low; must preserve edge falloff. | Good mechanical cleanup. |
| Palette expansion cache | Medium. Active palette can be expanded to RGB888 table. | Palette index, secondary index, hue phase, palette changes. | Stale cache, palette transition errors. | Shadow-test only. |
| Chroma unit-vector table | High. Precompute 12 `cos/sin` pairs. | Live chromagram weights and energy. | Low. | Good CPU cleanup, no behaviour change intended. |
| Temporal dither thresholds | Medium. Thresholds already tabled. Integerise possible. | Dither phase/noise origins and current fractional values. | Low-light flicker, `*254` brightness behaviour. | Treat as separate proof lane. |
| Bloom compact state | Medium. Q0.16 or Q8.8 state plus two-tap shift/alpha table is plausible. | History buffer, centre insert, live alpha/shift, edge display. | High; may kill long tails. | Sandbox after VPAB. |
| Waveform compact state | Medium-low. Fade table possible, state must remain live. | `dt`, shift accumulator, last colour, reactive gates. | High; can alter musical causality. | Second prototype after Bloom. |
| RGB8 state | Low as production candidate, high as adversarial baseline. | None if deliberately quantised early. | Kills low-level persistence. | Use only to falsify value claims. |
| Static LUT for chromagram colour | Low. Chroma vector and energy are live. | Chroma bins, max/average weight, fallback brightness. | High; would erase harmonic intelligence. | Do not LUT whole function. |
| Full visual-memory static LUT | Not viable. | Music input, time, state history, channel state. | Would create fake proof disconnected from perception. | Reject. |

## 7. VPAB Final-Byte Probe Contract

[INFERENCE] The research lane should hand the sandbox team a probe contract before any implementation experiment. Existing `vp_probe` and `frame_dump` are useful, but they are pre-output `CRGB16` instruments.

Required boundary:

```text
current path A and shadow path B
  -> equivalent brightness / clip / scale / dither / gamma / reverse handling
  -> final CRGB leds_out-style 8-bit bytes
  -> metrics only
  -> no displayed LED change unless explicitly armed later
```

Initial packet sketch:

```text
VPAB,ver=1,mode=7,channel=primary,scenario=trail,frame=42,t_ms=350,dt_ms=8.3,seed=1234,stimulus=single_hit,phase=decay,event_id=1,mae8=0.42,p95_abs8=1,max_abs8=6,changed_pct=1.8,energy_a=812,energy_b=806,energy_delta_pct=-0.7,com_a=79.2,com_b=79.1,com_delta_leds=0.1,com_slope_delta_pct=2.3,trail_half_a=135,trail_half_b=133,tail_integral_delta_pct=-3.1,hue_delta_p95=1.4,sat_delta_p95=2.0,flicker_score=0.02,render_us=740,quant_us=62,show_us=5600,frame_us=8100,heap=123456,over=0,dropped=0
```

Rules:

- `ver` is mandatory and append-only.
- Pre-output and final-byte metrics must not be mixed.
- Primary and secondary final bytes should be explicitly labelled.
- Shadow path must not alter displayed LEDs in Level 1.
- `:vp_probe=all` remains a Tier A internal determinism guard.
- `:frame_dump=all,<mode>,dur,every` remains a live COM/energy/FPS transport guard.
- `:vp_perf` remains timing/heap proof only.

Minimum metrics:

| Metric | Purpose |
|---|---|
| `mae8`, `p95_abs8`, `max_abs8` | Final-byte equivalence. |
| `changed_pct` | How much of the final strip differs. |
| `energy_delta_pct` | Brightness/energy shift. |
| `com_delta_leds`, `com_slope_delta_pct` | Motion preservation. |
| `trail_half_life_delta_frames`, `tail_integral_delta_pct` | Visual memory preservation. |
| `hue_delta_p95`, `sat_delta_p95`, `white_bias_score` | Colour clarity preservation. |
| `flicker_score` | Low-light stepping/dither artefacts. |
| `render_us`, `quant_us`, `frame_us`, `heap` | Runtime safety. |
| `channel_corr`, `channel_energy_delta`, `channel_com_delta` | Dual-channel independence. |

## 8. Falsification Thresholds

These are Level 1 starting thresholds, not product truth:

| Claim | Falsify if simpler path meets all of these |
|---|---|
| CRGB16 state is needed for a primitive | `mae8 <= 0.5`, `p95_abs8 <= 1`, `max_abs8 <= 8`, `changed_pct <= 2%`, trail zero-crossing delta `<= 2 frames`, low-light tail integral delta `<= 10%`, p95 COM delta `<= 1 LED`, no timing/heap regression, no Captain-visible loss. |
| Compact state is safe | Same final-byte thresholds, plus centre-origin parity and dual-channel independence remain within baseline bands. |
| Soft-clip LUT is safe | Saturation floor, white-bias score, energy, and peak hue remain within final-byte thresholds; Captain does not see more washout. |
| Palette/HSV simplification is safe | Final centre insert bytes and subsequent trail bytes match under thresholds; no loss of colour clarity or musical colour causality. |
| Temporal dither change is safe | Flicker score does not increase; low-light tails do not die earlier; no visible sparkle/stair-step. |
| Beat/refractory/salience primitives matter | They must change final bytes in event-labelled scenarios and Captain-visible A/B must read as more musical, not merely different. |

## 9. Sandbox Handoff Packets

### Packet A: VPAB Probe Spec

Goal: build a read-only final-byte paired probe contract.

Inputs:

- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:280-338`
- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:739-882`
- `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:352-423`
- `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:2916-2988`

Exit evidence:

- Packet schema documented.
- Offline parser contract documented.
- No displayed-output mutation.
- No serial dependency in sandbox.

### Packet B: Bloom Compact Visual-Memory Prototype

Goal: compare current Bloom `CRGB16` state against compact Q0.16 and RGB8 adversarial baselines.

Inputs:

- `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp:7-14`
- `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp:82-112`
- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:1586-1628`

Required scenarios:

- Single centre impulse.
- Rapid repeated impulses.
- Low-level tail.
- Strong peak into edge falloff.
- Silence-to-onset and onset-to-silence.

Pass condition:

- Final-byte thresholds pass and Captain-visible A/B shows no loss.

### Packet C: Waveform Fast Compact Visual-Memory Prototype

Goal: compare current Waveform Fast history against compact/early-quantised state.

Inputs:

- `SPECTRASYNQ_K1_FIRMWARE/light_mode_waveform_fast.cpp:7-21`
- `SPECTRASYNQ_K1_FIRMWARE/light_mode_waveform_fast.cpp:129-168`
- `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:308-338`

Required scenarios:

- Slow sine-like waveform.
- Sudden transient.
- Dense roll/repeated peaks.
- FPS-varied replay to prove `dt` behaviour.

Pass condition:

- Trail speed, COM slope, tail integral, flicker, and final bytes stay within thresholds.

### Packet D: Colour-Source Simplification

Goal: shadow-test stateless HSV/palette/force-saturation simplification without touching history buffers.

Inputs:

- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:76-90`
- `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp:60-71`
- `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:113-172`
- FastLED `ColorFromPaletteExtended()` as optional source-only experiment.

Pass condition:

- Centre insert bytes and subsequent trails are equivalent; no colour clarity loss.

### Packet E: Low-Risk LUT Lane

Goal: test LUTs that should not change product behaviour.

Candidates:

- Soft-clip scale table.
- Bloom edge-fade table.
- 12-entry chroma unit-vector table.
- Active palette expansion cache.

Pass condition:

- Final bytes equivalent, render time no worse, no heap introduced, no visible washout.

### Packet F: Secondary State Ownership Audit

Goal: map secondary state and config mutation into an explicit render-context proposal.

Inputs:

- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:541-583`
- `SPECTRASYNQ_K1_FIRMWARE/globals.h:153-170`

Pass condition:

- Proposal only. No behaviour change. Must preserve cross-channel final-byte divergence.

## 10. Additional Exploration Vectors

These did not emerge directly from the original CRGB16 question, but are now viable research vectors:

| Vector | Why it may matter | First proof |
|---|---|---|
| Split timing lanes | Stage lighting separates intensity-up, intensity-down, colour, focus, and beam timing. K1 may need separate intensity, colour, width, and diffusion timing. | Event-class final-byte replay; compare single envelope vs split lanes. |
| Layer alpha budget | Compositing theory treats overlap explicitly; K1 additive histories can become visual mush. | Synthetic overlap scenario with saturation and layer-dominance metrics. |
| Event-class envelopes | DSP attack/release models can distinguish onset, sustain, and release. | Single hit, roll, and decay scenarios with first-3-frame slope and tail metrics. |
| Temporal history rejection | Trails are useful until they become stale ghosts after direction/colour changes. | Direction-change and hue-change scenarios with ghost-energy score. |
| Refractory/grace windows | Fast repeated events may need controlled merge/split behaviour. | Dense percussion replay; event separation and mush score. |
| Beat-phase memory | Groove lock may be more valuable than raw amplitude response if it does not add lag. | Beat-labelled replay; phase error and Captain A/B. |
| Perceptual low-light curve | Low code values may matter more as duration/distribution than as peak byte. | Low-light tail A/B with flicker score. |
| Exposure debt | Peaks should not leave later frames dull or white-recovering. | Strong peak followed by weak detail; saturation/luma recovery. |
| Gesture identity | A mode must remain recognisable after simplification. | Captain label-match A/B using metric bundle. |
| Locality preservation | Event origin should remain trackable through decay. | Footprint IoU and centroid drift. |

## 11. Decisions For The Refactor Team

| Decision | Status | Rationale |
|---|---|---|
| Do not globally remove Pharap FixedPoints or `CRGB16` in Level 1. | Accepted research recommendation. | Bloom/Waveform stateful trails are plausible survival paths. |
| Do not defend broad precision claims. | Accepted research recommendation. | Final output is 8-bit WS2812; many sources collapse to 8-bit before CRGB16. |
| Build VPAB before implementation experiments. | Accepted research recommendation. | Current probes are upstream and can preserve invisible churn. |
| Prototype Bloom first. | Recommended. | It is the cleanest centre-origin fractional-history mechanism. |
| Use RGB8 as adversarial baseline, not target architecture. | Recommended. | It is useful to falsify value, but likely kills low-level persistence. |
| Treat soft clip as colour-clarity primitive, not visual-memory primitive. | Recommended. | It protects hue ratios at peaks but does not store trail history. |
| Keep dormant gamma/FastLED dither disabled unless A/B proves value. | Recommended. | They are not current runtime value and previously sit in washout-risk territory. |
| Preserve secondary independence. | Recommended. | Dual-channel richness is product value; simplify ownership only after byte proof. |

## 12. Open Questions

- Should VPAB include secondary final bytes from day one, or start primary-only and add secondary before promotion?
- Is Bloom definitely the first Captain-visible A/B target, or should Waveform Fast come first because it is more musically explicit?
- Does K1's `*254` temporal dither path intentionally trade peak code range for smoother low-light tails, or is it a brightness bug to isolate?
- Can `ColorFromPaletteExtended()` improve hue continuity after final quantisation, or does it only move internal numeric churn?
- Should chromagram `max_peak *= 0.999` be dt-normalised before visual-memory work adopts colour afterimage as a primitive?
- What capture format is acceptable for Captain-visible A/B: serial-derived replay, side-by-side firmware, video, or physical eyes-on judgement plus metrics?

## 13. Stop Conditions

Stop a future implementation lane if:

- It proves only pre-output `CRGB16` equivalence.
- It cannot show final `leds_out[]` byte metrics.
- It changes default visual output without explicit approval.
- It removes centre-origin propagation, dual-channel independence, temporal dither, or stateful trails before falsification.
- It improves CPU or architecture while weakening perceived musicality, colour clarity, motion memory, or captivation.
- It treats a green build as visual proof.

## Changelog

| Date | Change |
|---|---|
| 2026-05-26 | Initial research-lane findings after six read-only SSA lanes and local source verification. |
