---
abstract: "Dual-K1 sync timing analysis (SSA evidence, 2026-07-08): what defines visual phase per frame (44.4 Hz PLL beat phase, free-running ~185 FPS render clock, ChannelEffectState particle pools, global hue drift); which effects carry irreproducible internal motion state; latency/bandwidth maths for three sync schemes (semantic-state streaming ~9.6 KB/s, tempo-corrections ~0.3 KB/s, pixel streaming 48–96 KB/s = 384–768 kbit/s); seam-mismatch perceptibility budget derived from the measured apparent-motion envelope (fusion 36–60 ms, correspondence 28–32 px). Verdict: BLE-MIDI cannot carry pixels; semantic streaming alone does not reproduce particle effects."
---

# Dual-K1 Sync — Timing / Synchronisation Evidence

SSA lane: `k1_dual_sync_eval_2026-07-08` · READ-ONLY research pass · all claims cite file:line or a named document actually read. Labels: **[FACT]** = cited repo evidence, **[DERIVED]** = arithmetic from cited facts, **[EXTERNAL]** = general engineering / vision-science knowledge, not repo-verified.

## 0 · Corrected baseline numbers (brief said "~160 LEDs, verify")

- Render canvas is `NATIVE_RESOLUTION 160` px per channel, with the frequency field mirror-filled about the centre anchor at `NATIVE_RESOLUTION/2` (centre-origin confirmed) — `system/constants.h:106-109`. **[FACT]**
- Each K1 drives **two** physical 160-LED channels: primary buffers `CRGB leds[160]` etc. (`system/globals.h:287-303`) and `SECONDARY_LED_COUNT = 160` with `leds_16_secondary[160]` (`system/globals.h:818-825`). A "320-LED widened surface" is 160+160 **per channel**; if both channels widen, the shared surface is 2×320. **[FACT]**
- Audio pipeline: AP frame rate 133.33 Hz, tempo novelty emit rate 44.444 Hz (`audio/sb_semantic_state.h:88-89`; `audio/sb_tempo.cpp:43`). **[FACT]**
- Render loop (`led_thread`, Core 1) is **free-running**: `while(true)` with `vTaskDelay(1)` per iteration and no FPS target; `LED_FPS` is only a measured EMA (`SPECTRASYNQ_K1_FIRMWARE.ino:1084`, `:1400-1403`). Measured cadence ~5.4 ms/frame ≈ ~185 FPS (`docs/measurements/apparent-motion-on-k1.md` §8; `.claude/skills/k1-motion-canon/SKILL.md:109`). The "100 FPS" in root CLAUDE.md is nominal, not enforced. **[FACT]**

## 1 · (a) What defines "visual phase" each frame

Per-frame visual output on one K1 is a function of ALL of the following state, each with its own clock domain:

| State | Source | Rate / clock | Cross-device behaviour |
|---|---|---|---|
| Wall clock `t_now_us = micros()` | `SPECTRASYNQ_K1_FIRMWARE.ino:779-780` | device-local µs | independent, drifts |
| Render frame boundary | free-running `led_thread` (`ino:1084`, `vTaskDelay(1)` `ino:1403`) | ~5.4 ms, unsynchronised | frame phases never align |
| Beat phase `phase01` [0,1) | `SBTempoEvent` from PLL flywheel (`audio/sb_tempo.h:22-29`) | advanced per novelty EMIT at 44.444 Hz (`sb_tempo.cpp:328-329`, `:43`) → **22.5 ms phase quantisation** | each device runs its own PLL |
| PLL correction dynamics | Kp=0.25/onset, correction cap 0.10 beat, freq pull ±4%, coast 8 beats (`sb_tempo.cpp:352-378`) | onset-driven | converges independently; bounded per-onset movement |
| `AudioSemanticState` (bpm, tempo lock, beat_tick, onset/kick/snare/hihat events + levels, chord root/type/conf) | `audio/sb_semantic_state.h:47-91` | published per AP frame, read per render frame | mic/AGC-dependent → differs per device |
| Effect-internal state | `visual/channel_effect_state.h:30-172` (two instances: primary/secondary, `:176-177`) | integrated per render frame with local-`millis()` dt | **diverges** (see §2) |
| Global colour phase `hue_position` / `hue_shift_speed` | `system/globals.h:754-755` (auto colour-cycling state) | free-running per frame | drifts apart continuously |
| Mode / transition engine (crossfade, effects queue frame tick) | `ino:1167-1175`; `director/beat_aware_director.h:47-85` (beat-quantised switches, tempo-derived xfade_ms) | event-driven | switch instants differ unless commanded together |
| AGC / noise-cal / sweet-spot brightness | per-device calibration state (noise cal is per-device, `calibration/noise_cal.h`) | slow | brightness/colour gain differs across the seam |

Key structural fact: there is **no global frame counter or shared timebase** anywhere in the render path — visual phase is the union of (i) device-local wall clock, (ii) the 44.4 Hz PLL beat phase, and (iii) accumulated effect-internal state. **[FACT]**

## 2 · (b) Effect-internal stateful motion — what independent devices cannot reproduce

`ChannelEffectState` (`visual/channel_effect_state.h`) is the authoritative inventory. Effects whose motion is **integrated over frames** (position += velocity × local-dt) and/or seeded by device-local events:

| Effect | Irreproducible state | Lines |
|---|---|---|
| Comet | 6-slot pool: `comet_pos/vel/hue/size/life`, onset edge-detect `comet_last_event_id`, salience running-max gate | `channel_effect_state.h:45-52` |
| Tempo Comet | own 6-slot pool `tcomet_pos/vel/size/life` + **internal beat flywheel** (`tcomet_beat_phase`, `tcomet_locked_bpm`, coast counter) — a second, per-effect PLL layered on the tracker | `:75-88`; integration `effects/light_mode_tempo_comet.cpp:163` (`pos += vel*dt`), spawn at centre `:150` |
| Tempo Comet Anticipate | own pool + own flywheel copies (`tcanta_*`) | `:143-152` |
| Pulse Prism | 6-ring shockwave pool `prism_r/vel/life/hue`, kick edge-detect id | `:113-119` |
| Percussion Burst | 8-particle pool with per-class hue, kick/snare/hihat event-id cursors, deterministic alternating hihat side flag | `:127-139` |
| River Surge | drop wavefront position/life + 0.5 s/20 s/4 s macro-dynamics envelopes + 4 s refractory | `:154-164` |
| Dense Forge | 8 spring-lattice agents (`dforge_lat_pos/vel/last`), carrier phase; chord→hue **debounce (250 ms hold) + slewed anchor** — two devices can hold different chord roots | `:91-104` (flicker note `:98-99`) |
| Waveform Tempo / Tempo River / River Walk | fractional scroll accumulators, bar-step counters (`trwalk_beats`), palette-walk offsets | `:64-74`, `:166-171` |
| Snapwave / Ember | free-running oscillator phases (`snap_*`, `ember_shimmer_phase`) | `:106-110`, `:62` |
| Quantum Collapse | **true RNG**: `random_float()` per frame in velocity and collapse decisions — irreproducible even with identical inputs and clocks | `effects/light_mode_quantum_collapse.cpp:85-99` |

Divergence mechanics (why "same music, two mics" does not converge): **[DERIVED]**
1. **Event-seeded pools.** Spawns are edge-detected on device-local onset/kick/snare event ids. One missed or extra onset on either mic creates a particle that exists on one half only — a *structural* mismatch, not a phase error.
2. **Local-dt integration.** `pos += vel*dt` with dt from the device's own frame clock (~5.4 ms, jittering) accumulates positional drift between resets; velocities set from device-local beat period differ when the two PLLs disagree.
3. **Debounced/hysteretic state.** Chord-hue hold (250 ms), coast counters, refractory windows: small input differences select different discrete branches that persist for seconds.
4. **RNG.** Quantum Collapse cannot be reproduced without a shared seeded PRNG driven by a shared frame index.
5. **Free-running colour phase.** `hue_position` drifts at `hue_shift_speed` from power-on; two devices' palettes rotate apart without correction.

Continuous field effects driven directly from the spectrum (GDFT/spectrum display, chromagram, VU) carry little or no integrated state and would track closely from similar audio — the seam problem concentrates in the particle/flywheel effects above. **[DERIVED]**

## 3 · (c) Candidate sync schemes with latency/jitter maths

### Transport ground truth in this repo

- **BLE-MIDI exists but K1 is a CENTRAL RECEIVER only**: NimBLE-Arduino ^2.5.0 central scans for the "SpectraSynq Remoted" knob and subscribes to its MIDI NOTIFY characteristic (`network/ble_remoted_central.h:12-19`). Compiled only under `-DSB_K1_BLE_REMOTED` in envs `k1_bench_im73d_ble` (`platformio.ini:291-302`) and `k1_ble_remoted_probe` (`platformio.ini:378-390`); header declares it GATED / NON-SHIPPABLE (`ble_remoted_central.h:5-7`). **There is no K1-side BLE transmit path today** — "piggyback BLE MIDI" requires new peripheral/advertise/notify code or a second central link. **[FACT]**
- Decoder limits: `K1_BLE_MIDI_MAX_PACKET 247` bytes, ≤16 records/packet, CC14 + NRPN state machine (`network/k1_ble_midi_decoder.h:10-32`). **[FACT]**
- **Wi-Fi softAP WebSocket exists** (`LightwaveOS-AP`, WS port 80, `network/sb_k1_wireless.cpp:19,24,74`) but only the wireless-enabled bench env links it (`platformio.ini:71`), and `sb_k1_wireless_poll()` runs **on the Core-0 audio loop** (`ino:816`; BLE poll likewise `ino:819`). Any heavy sync traffic on these paths executes next to the hard-real-time audio pipeline. **[FACT]**

### Scheme 1 — leader streams semantic state every audio frame; follower renders from it

- Payload: packed `AudioSemanticState` ≈ 72 B (14 floats + 7 bools + 2 uint8 + timestamps; `sb_semantic_state.h:47-91`). **[DERIVED]**
- Bandwidth: @133.3 Hz = **9.6 KB/s**; a reduced beat/tempo-only record (~24 B) at the 44.4 Hz tempo cadence = **1.1 KB/s**. Both fit BLE comfortably. **[DERIVED]**
- Latency chain (follower behind leader): BLE connection-interval scheduling 7.5–30 ms **[EXTERNAL]** + follower render-frame quantisation 0–5.4 ms (`ino` free-run) + WS2812 wire-out ~4.8 ms for 160 LEDs at 30 µs/LED **[EXTERNAL]**. One-way lag ≈ **12–40 ms**, jitter ≈ ±1 connection interval.
- Mitigation: beat phase is *extrapolatable* — `phase_rx + Δt·bpm/60` cancels mean transport delay if the pair maintains a clock-offset estimate (needs a ping/timestamp exchange; nothing in repo does this today). Residual phase error achievable ~±5–10 ms. **[DERIVED/EXTERNAL]**
- **Limitation (decisive):** streaming semantic state does NOT make the follower's render deterministic. All §2 divergence mechanics except mic disagreement remain (local-dt integration, RNG, free-running hue). Scheme 1 is only sufficient if paired with either (i) a deterministic-replay refactor (shared frame index, shared seeded PRNG, dt from the shared timeline) or (ii) restriction of dual-mode to the stateless spectrum-field effects. **[DERIVED]**

### Scheme 2 — both devices analyse own mics; link carries tempo-phase / mode / palette corrections

- Bandwidth: one correction record (bpm, phase01, mode, palette, hue_position, seq ≈ 24–32 B) at 5–10 Hz = **≤0.3 KB/s** — trivially fits the existing BLE-MIDI record framing (16 records/packet). **[DERIVED]**
- Phase convergence: both PLLs hear the same music (acoustic path difference across a desk <1 ms **[EXTERNAL]**); with periodic phase corrections capped like the PLL's own onset corrections (≤0.10 beat/step, `sb_tempo.cpp:362-365`) the pair's beat phases can be held to roughly ±1 novelty emit (±22.5 ms) — near but not clearly inside the seam budget (§4). Half-beat/octave disagreement between the two winner bins is a real failure mode the corrections must arbitrate. **[DERIVED]**
- **Limitation (decisive):** per-mic onset/kick/snare events, per-device AGC/noise-cal gain, and chord-root debounce all still differ → particle spawns, brightnesses, and hue anchors mismatch across the seam. Scheme 2 yields *coherent* twin displays (same mode, same palette, same tempo feel) — good for a "party sync" feature — but cannot deliver one seamless widened surface for moving patterns. **[DERIVED]**

### Scheme 3 — leader renders all 320 px, streams the follower's 160-px half as pixels

- Bandwidth: 160 LED × 3 B = **480 B/frame**. @100 FPS = **48.0 KB/s = 384 kbit/s**; at the measured ~185 FPS = **88.8 KB/s ≈ 710 kbit/s**; both channels widened (2×160 px to the follower) doubles this to **96–178 KB/s (768 kbit/s–1.42 Mbit/s)**. **[DERIVED]**
- **BLE-MIDI: infeasible.** Pixel bytes must be 7-bit-safe (SysEx encoding ×8/7 → ~549 B/frame + framing = ≥3 packets/frame at the 247 B ceiling, ~300 packets/s at 100 FPS). Practical ESP32 NimBLE application throughput is ~20–90 KB/s under ideal interval/DLE/PHY settings **[EXTERNAL]** — the single-channel stream saturates the link with zero headroom and the BLE-MIDI timestamp/status framing overhead on top; dual-channel is beyond the medium. Even raw GATT notify at 2M PHY is marginal. **[DERIVED/EXTERNAL]**
- **Wi-Fi (existing softAP + WebSocket): bandwidth-feasible, jitter-hostile.** 384–768 kbit/s sits inside practical ESP32 softAP TCP throughput (~2–10 Mbit/s **[EXTERNAL]**), but Wi-Fi contention produces 10–100 ms latency spikes → needs per-frame timestamps + a jitter buffer of ≥2–3 frames, so the follower half renders **≥20–40 ms behind** the leader half unless the leader delay-matches its own half (rendering the leader's own output through the same buffer — total added audio-to-LED latency then eats most of the <50 ms budget). RX/decode must move OFF the Core-0 loop (today's wireless poll is on Core-0, `ino:816`). **[DERIVED]**
- Note: leader rendering 320 px also requires widening the render canvas beyond `NATIVE_RESOLUTION 160` and breaking the mirror-fill assumption (`constants.h:106-109`) — a render-architecture change, not just transport. **[FACT→DERIVED]**
- Not-in-repo alternative worth flagging for the design phase: ESP-NOW (connectionless 802.11, ~1–2 ms typical latency, 250 B v1 / ~1470 B v2 payloads **[EXTERNAL]**) — nothing in the repo uses it; unverified here.

### Scheme comparison snapshot

| Scheme | Link load | Seam phase error (achievable) | Reproduces particle effects? | New firmware surface |
|---|---|---|---|---|
| 1 semantic stream | 1.1–9.6 KB/s | ±5–10 ms (with extrapolation + clock sync) | **No** — needs deterministic-replay refactor or effect subset | BLE TX role OR WS client mode; clock sync |
| 2 own-mic + corrections | ≤0.3 KB/s | ±22.5 ms (one novelty emit), half-beat risk | **No** — structural event mismatch | smallest; fits existing BLE-MIDI records |
| 3 pixel stream | 48–178 KB/s | 0 (single renderer) after delay-matching | **Yes** — trivially, one renderer | largest: 320 px canvas, jitter buffer, delay-match, Wi-Fi TX off Core-0 |

## 4 · (d) Perceptible left-right seam mismatch for moving patterns

**Repo authority first** (measured on-device, single observer, 2026-06-02 — `docs/measurements/apparent-motion-on-k1.md` §5/§8; restated in `.claude/skills/k1-motion-canon/SKILL.md:109-118`):

- Motion↔blink fusion is an **inter-step interval threshold ≈36–60 ms**, not a px/s limit. **[FACT]**
- Correspondence limit (one object vs two flashes): **≈28–32 px** separation at ~54 ms ISI; fused-motion ISI window ~50–90 ms. **[FACT]**
- Live effects scroll ~100–185 px/s stepping every ~5.4 ms — deep in the smooth regime. **[FACT]**
- Canon rule: tempo corrections must modulate **continuous velocity, never jump** — a per-beat jump reads as a blink (`SKILL.md:116-118`; measurements doc §8). Any seam-correction slewing must obey the same rule. **[FACT]**

**Seam arithmetic** (an object crossing the seam with inter-device timing offset Δt at velocity v displaces by v·Δt): **[DERIVED]**

| Δt between halves | offset @100 px/s (Spectrum River) | offset @185 px/s (Waveform) |
|---|---|---|
| 5.4 ms (one frame) | 0.5 px | 1.0 px |
| 10 ms | 1.0 px | 1.9 px |
| 22.5 ms (one novelty emit) | 2.3 px | 4.2 px |
| 50 ms | 5.0 px | 9.3 px |

Interpretation:
- The measured **correspondence limit (28–32 px)** bounds when a crossing object *splits into two objects*: even a 50 ms offset (9 px) stays well inside it, so the object will still *bind* across the seam. **[DERIVED from FACT]**
- But binding ≠ seamless. A sustained positional kink at a known, fixed location is detected by displacement/vernier sensitivity, which vision science puts **far below** the correspondence limit — on the order of a fraction of the stimulus blur width **[EXTERNAL — no repo measurement exists for displacement detection through the LGP]**. The LGP's mandatory diffusion (measurements doc §6) blurs per-pixel detail and raises this threshold, but by an unmeasured amount.
- Temporal asynchrony of *discrete events* (beat pulses, drop-cut going dark on both halves): visual-visual simultaneity/asynchrony detection is roughly **20–40 ms** for adjacent fields **[EXTERNAL]**; the repo's fused-motion ISI ceiling (~80–90 ms) is the harder limit beyond which paired events stop reading as one.
- **Proposed budget (for the design phase, not a decision):** hold inter-device timing offset **≤ ~10 ms** so fast-effect seam displacement stays ≤ ~2 px (plausibly under the LGP blur) and event asynchrony stays comfortably under the 20–40 ms window; treat ±22.5 ms (one tempo emit) as the outer bound acceptable only for beat-synchronous global events, not for objects crossing the seam. Scheme 2's achievable ±22.5 ms therefore fails moving-pattern seams; Schemes 1 (with extrapolation) and 3 (single renderer + delay-match) can meet ≤10 ms. **[DERIVED, budget provisional pending an on-device seam measurement]**

## 5 · Numbers

| Quantity | Value | Source |
|---|---|---|
| Canvas px per channel | 160 (mirror anchor at 80) | constants.h:106-109 |
| Physical channels per K1 | 2 × 160 LEDs | globals.h:287, 825 |
| AP frame rate | 133.33 Hz | sb_semantic_state.h:88 |
| Tempo novelty emit rate / beat-phase quantisation | 44.444 Hz / 22.5 ms | sb_tempo.cpp:43 |
| Render frame period (measured) | ~5.4 ms (~185 FPS), free-running | apparent-motion doc §8; ino:1084,1403 |
| PLL gains | Kp 0.25, Ki 0.002, corr cap 0.10 beat, pull ±4%, coast 8 beats | sb_tempo.cpp:352-378 |
| Semantic-state stream | ~72 B/frame → 9.6 KB/s @133 Hz | derived, sb_semantic_state.h |
| Pixel stream, one 160-px half | 480 B/frame; 48 KB/s (384 kbit/s) @100 FPS; 88.8 KB/s (710 kbit/s) @185 FPS | derived |
| Pixel stream, both channels | 96–178 KB/s (768 kbit/s–1.42 Mbit/s) | derived |
| BLE-MIDI packet ceiling | 247 B, ≤16 records | k1_ble_midi_decoder.h:10-11 |
| Fusion / correspondence / ISI window | 36–60 ms / 28–32 px / 50–90 ms | apparent-motion doc §8 [FACT] |
| Seam displacement | v·Δt: 1.9 px @10 ms & 185 px/s; 4.2 px @22.5 ms | derived |

## 6 · Risks

- **BLE-MIDI transmit path does not exist on K1** (central-receiver only, non-shippable envs); "piggyback" understates the work — role inversion or a parallel link is new firmware surface (ble_remoted_central.h:5-19).
- **Wireless polling lives on the Core-0 audio loop** (ino:816,819): any sync transport scaled up naively threatens the hard-real-time audio contract.
- **Semantic streaming without deterministic replay silently fails**: both halves look "synced" on field effects, then visibly split the moment a particle/flywheel effect (Tempo Comet, Percussion Burst, Pulse Prism) is selected. Quantum Collapse is RNG-driven and can never match without a shared seeded PRNG.
- **Per-device AGC/noise-cal gain mismatch** shows as a brightness/colour step at the seam even with perfect timing sync — a calibration-transfer problem no timing scheme fixes.
- Half-beat/octave disagreement between two independent PLLs (Scheme 2) produces an anti-phase seam that corrections capped at 0.10 beat/step take many beats to heal.
- The ≤10 ms seam budget in §4 rests partly on external vision science; the LGP displacement-detection threshold is unmeasured (motion-probe harness could measure it, env k1_motion_probe).

## 7 · Open questions

1. Physical pixel pitch and LGP blur width (px→mm) — needed to firm up the seam displacement budget; no repo measurement found.
2. Does the widened surface cover one channel or both (2×320)? Doubles Scheme-3 bandwidth.
3. Clock-sync mechanism (none exists in repo): BLE conn-event timestamps vs application ping — accuracy bound needed for Scheme-1 extrapolation.
4. ESP-NOW as a transport (not present in repo) — latency/jitter claims here are external and unverified.
5. Whether the effects roster for dual mode may be restricted to stateless field effects in v1 (removes the deterministic-replay refactor from the critical path).
6. Seam geometry under the centre-origin mirror mandate: today every effect radiates from the per-device centre (constants.h:107-108); a left/right widened surface either re-centres the virtual origin at the physical seam or abandons mirror-fill — a render-architecture decision upstream of any transport choice.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (SSA sync-timing) | Created — read-only timing/sync evidence: visual-phase inventory, effect-state divergence census, three sync-scheme latency/bandwidth analyses, seam perceptibility budget from the measured apparent-motion envelope. |
