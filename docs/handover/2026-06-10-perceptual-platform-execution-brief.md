# Execution Brief — Perceptual Wins + Tri-MCU Platform Investigation

**Date:** 2026-06-10
**Author:** CTO/CPO synthesis session (Cowork), commissioned by Captain
**Audience:** Executing agents (Codex / Claude Code)
**Status:** APPROVED FOR EXECUTION pending Captain sign-off on the Decision Points (§8)
**Parent evidence:** `docs/research/2026-06-10-audio-visual-resolution-investigation.md` (axes-over-bins investigation, delegation ledger inside)

---

## 0. Operating contract for executing agents (propagated — non-negotiable)

These propagate from the Captain's operating contract and the K1 load-bearing rules. They apply to every lane and every downstream agent.

1. **Questioning protocol.** Ask clarifying questions whenever strategic direction, hardware state, or domain context is genuinely needed. Batch questions; do not drip-feed. If proceeding without full clarity, state explicit, minimal, reversible Assumptions and include how to detect when an assumption is wrong. Never suppress questions in sub-agent prompts.
2. **Evidence labels.** [FACT] only for source/measurement-verified claims; otherwise [INFERENCE]/[HYPOTHESIS]. Compile/upload is never runtime proof. Host gate ≠ device proof.
3. **K1 load-bearing rules apply in full** (`.claude/CLAUDE.md`): doctrine gate before AP/VP edits; instrumentation boundary (MabuTrace mandatory for any timeline/causality claim; non-shippable); `start_noise_cal` NEVER auto-fired — Captain silence confirmation required; device identity (USB MAC + chip ID) verified before any flash/erase/monitor; commit gate per change class; no push without Captain instruction.
4. **Escalate, don't improvise**, on: any transport-corruption signal (see Lane F), any AP frame-time regression, any quarantined-lane file (`wip/2026-06-07-unfinished-lanes-quarantine` content is off-limits), any need to touch AGC/calibration/silence thresholds, and any result that contradicts this brief's assumptions.
5. **Failure accountability.** Two failures of the same type → stop, state mechanism, propose alternative. No workaround papering without logging root cause.
6. **Read order before starting:** `progress.md` → `.claude/handoff.md` → `docs/spec-index.md` → this brief → lane-relevant forensics.

---

## 1. Mission context

The product north star is perceptual: a music-to-visual instrument that exceeds Sensory Bridge's impact. The 2026-06-10 investigation established:

- [FACT] "Resolution" = independent perceptual axes delivered to the LEDs, not bin count. Two funnels exist: the AP publishes ~2–5% of what it computes; the VP consumes a fraction of what is published (chord state: zero consumers; snare/hihat: dark).
- [INFERENCE] The deepest unshipped lever is **time**: anticipation (rendering the *arrival* of a beat via locked PLL phase) and dramaturgy (impact economy, section-aware staging) — versus today's instantaneous reaction.
- [FACT] The K1's display is a diffused dual-edge LGP: its native axes are colour fields, intensity, mass-motion, and dual-field interference — not spatial detail.
- [FACT] A second hardware platform exists: Waveshare ESP32-P4-WIFI6 (P4-nano repo, `/Users/spectrasynq/Workspace_Management/Software/P4-nano/I2S_Audio_Demo-Waveshare_ESP32-P4-NANO`) with proven ES8311 codec capture (48 kHz/24-bit, CRC'd raw-PCM evidence, `read_errors=0`), A-weighting cascade, running FFT/Goertzel/chroma/onset/tempo lane, and actor-model telemetry.

**Target architecture (investigation track, not yet committed):**

```
aux TRS (line-in) ──► ES8311 ──► ESP32-P4 (AP: v2 semantic engine @ 400 MHz RISC-V ×2)
                                    │  AudioSemanticState over framed wire protocol
                                    ├──► ESP32-S3 (VP: render, FastLED/RMT5, dual-channel LGP)
                                    └──► ESP32-C6 (radio coprocessor via SDIO/esp-hosted: WiFi6 broadcast,
                                          future multi-unit subscribers)
```

[FACT] The C6 is the P4's radio coprocessor, not a peer compute node. Architect accordingly.

**Sequencing rule (Captain-aligned, enforce):** K1 perceptual lanes (A–E) run on the current S3-only build NOW. The tri-MCU platform (Lane F) is a parallel spike. Nothing in A–E may take a dependency on Lane F. The shared artefact is the semantic-state schema (§2), designed once.

---

## 2. Shared artefact: AudioSemanticState schema v1 (wire-ready)

All lanes touching the publish surface conform to one schema document, to be authored first (Lane C deliverable C0, consumed by Lane F):

- Versioned POD struct: explicit field order, types, units, ranges, update rates. Today's struct + Tier 2 additions (continuous per-band flux ×4, agc_envelope, agc_noise_floor, optional decimated tempo-spectrum surface).
- Dual use: (a) on-device volatile snapshot (existing frame-counter consistency, no mutexes on audio path), (b) wire payload.
- Wire framing (inherits the VMEWT incident reopen-gate contract, `docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md`): sync word, version byte, sequence number, length, payload, CRC32. **Fail-closed**: receiver discards any frame failing any check, counts it, and renders from last-good state with bounded staleness (>250 ms stale → graceful decay to autonomous idle, never garbage). Zero tolerance for "survivor row" reasoning — rejected frames are evidence of a broken transport, not noise to ignore.
- Budget: payload ≤ 256 B at 44–133 Hz. [INFERENCE, must be measured in F] UART @ 2 Mbaud or SPI gives ≤1 ms transport; total aux→LED latency budget remains <50 ms with ~20 ms headroom.

---

## 3. Lanes

Priority: P0 = start immediately, P1 = after its P0 dependency, P2 = design/investigation first. Every lane is **load-bearing** for its own verdict; none may silently downgrade.

### Lane A (P0) — Anticipatory beat rendering A/B — *the thesis falsification test*

- **Evidence question:** Does anticipation visibly beat reaction? Render the *arrival* of beats using locked PLL phase versus the same effect reacting on beat_tick.
- **Scope:** S3 only, one effect pair. Implement an anticipatory twin of one existing tempo effect (recommend Tempo Comet or Waveform Tempo): renderer extrapolates `beat_phase01` locally between AP updates using `bpm` + its own clock; begins a swell at phase ≈0.85 peaking exactly at the tick; falls back to reactive behaviour when `tempo_locked == false` or `tempo_confidence` below threshold.
- **Non-goals:** no AP changes, no new published fields, no director changes.
- **Deliverables:** the effect pair behind a toggle; host replay test asserting phase-extrapolation error <±1 frame at 100 FPS over fixture corpus; serial A/B switch for eyes-on.
- **Pass/fail:** host gate green; Captain eyes-on A/B on ≥3 tracks (4/4 electronic, live-drummer pop, weak-lock material). PASS = anticipatory variant preferred on locked material AND no regression on weak-lock (graceful fallback verified). FAIL = document and **stop Lane E item E2**; the time-thesis needs revision before further investment.
- **Escalate if:** phase extrapolation reveals beat-tick/phase01 disagreement (possible flywheel publish bug — do not patch sb_tempo without doctrine gate).

### Lane B (P0) — Tier 1 consumers (consume what is already published)

- **Evidence question:** Does adding the harmony axis and rhythm decomposition to existing effects produce a visible perceptual jump with zero AP risk?
- **Scope, three items:** B1 chord→colour (root→hue anchor, type→palette character, confidence→saturation) in 2–3 harmonic effects; B2 snare/hihat consumers as spatially/chromatically distinct gestures (recommend secondary-channel accents); B3 generalise `novelty` beyond Dense Forge as articulation modulator.
- **Non-goals:** no publish-surface changes; no new DSP; do not touch quarantined mode-18 secondary-dark code paths.
- **Deliverables:** effect edits + host replay checks (e.g. chord_confidence non-degenerate variance over harmonic fixtures — if chronically low on real material, that's a finding, report it before device time).
- **Pass/fail:** host gate green; eyes-on on harmonically rich material (jazz/soul, not just EDM). PASS = colour tracks harmony recognisably; snare/hihat visually distinct from kick.

### Lane C (P1, after C0 schema) — Tier 2 publish-surface additions

- **Evidence question:** Do the continuous-flux, dynamics, and parallel-tempo axes survive to the publish surface within frame-time and struct budgets?
- **Scope:** C0 author the schema doc (§2). C1 publish continuous pre-threshold per-band flux (4 floats, from `sbv2_band_flux()` values, `sb_onset_beat.cpp:133-141`). C2 publish `agc_envelope` + `agc_noise_floor` (`globals.h:575-576`). C3 publish decimated tempo-spectrum surface (`sb_tempi_smooth[]`/`sb_acf_salience[]` — start with 24-of-96 bins; full 96 only if budget proves trivial). Each behind its own `-D` flag, one commit each.
- **Non-goals:** no consumer work beyond a minimal proof effect for C3 (parallel-tempi visual is a Lane D/E follow-up); no AGC behaviour changes — C2 is read-only exposure.
- **Pass/fail per item:** replay test asserting range/rate/variance; rate-consistency test unchanged; `pio run -e k1_hardware` clean; struct growth documented against §2 budget. Any AP frame-time question → MabuTrace on trace_dev, never scalar inference.

### Lane D (P1) — True dual-channel independence

- **Evidence question:** Does rendering two different audio dimensions on the two edges (A harmonic/sustained, B rhythmic/transient) read as depth/layering on the diffused plate?
- **Scope:** extend `sb_edgemixer_lite`/director so primary and secondary can run different effect+source pairings, not parameter overrides of one state. Prototype pairing: primary = chromagram/chord-colour field, secondary = onset/flux-driven transients. Include the stereo hook: source field in the channel config so L/R can slot in post-Lane-F without rework.
- **Non-goals:** no stereo capture yet (mono mic / summed aux); no mode-18 secondary changes (quarantined fix unresolved).
- **Pass/fail:** host gate green; eyes-on judged specifically on the doctrine's "independent dual-channel behaviour" criterion. Escalate if architecture forces per-channel duplication of effect state that blows RAM budget (report numbers, don't squeeze).

### Lane E (P2, design-first) — Dramaturgy / impact economy

- **Evidence question:** Does a director that budgets impact (restraint + structure-aware staging) beat the current router on watchability over full tracks?
- **Scope:** E1 design doc + **host simulation first** (VPML workbench / replay harness over the fixture corpus): novelty budget (big gestures cost; budget refills with restraint), confidence-gated section re-staging (Foote-lite checkerboard novelty at ~2 Hz off the hot path per the research brief), transition craft. E2 (only if Lane A passes) build-up→drop anticipation staging. Firmware implementation only after Captain reviews the simulated behaviour traces.
- **Non-goals:** no Smart Director firmware edits before design sign-off; no ML.
- **Pass/fail:** design doc + host-sim traces showing measurably fewer effect-switches with higher gesture amplitude variance versus current director on the same fixtures; then Captain full-track eyes-on (3+ minutes continuous, not clips).

### Lane F (P1, parallel spike) — Tri-MCU platform investigation

- **Evidence question:** Can the P4 run the validated K1 v2 semantic engine on a line-in source and deliver fail-closed semantic state to the S3 within latency budget?
- **Scope, staged:**
  - F1 **Aux line-in path spec.** Verify against the Waveshare ESP32-P4-WIFI6 schematic how the ES8311 analogue input is wired and whether a line-level path is exposed. [FACT, spec-level] ES8311 is a single-ADC codec → v1 = passive summed L+R (AC-coupled, attenuated to codec input range) into one input; document the wiring (resistor sum network, coupling caps, mic-path handling). **Do not assert pin numbers without the schematic; escalate to Captain with the proposed wiring diagram BEFORE any soldering.** Record stereo upgrade path (ES7210 or second codec) as a costed future option.
  - F2 **Engine port decision + port.** Recommendation to validate: port the K1 v2 AP (sb_tempo/sb_onset_beat/sb_chord + GDFT front-end) onto the P4's conditioned float-mono DSP input lane (`p4_audio_dsp.c` decode path), replacing the P4's bring-up DSP scaffolding. The K1 engine is the validated IP (310-test host gate); the P4 DSP lane is scaffolding. If the port reveals the P4's existing lane is materially better in some dimension, report the conflict — do not average.
  - F3 **Transport contract implementation.** §2 framing over UART (then SPI if UART marginal), P4→S3. Fail-closed receiver shim on S3 behind a build flag (`SB_SEMANTIC_REMOTE`): when enabled, VP consumes wire state instead of local AP. Soak test: ≥1 hour sustained, **zero** dropped/corrupt/overflow frames accepted as the pass bar (the VMEWT standard).
  - F4 **Latency measurement.** Aux-in → LED first-photon, measured (logic analyser or MabuTrace-class instrumentation on dev builds), not estimated. Budget: <50 ms; target <30 ms.
  - F5 **C6 broadcast probe (stretch).** esp-hosted bring-up; one-way semantic-state UDP multicast; a second listener (laptop visualiser is sufficient) proving the one-analyser/N-renderer pattern.
- **Non-goals:** no production K1 dependency on any of this; no battery/enclosure work; no A2DP/Bluetooth audio in this spike.
- **Pass/fail:** F1 wiring approved by Captain; F2 P4-hosted engine reproduces K1 replay metrics on the same fixtures within tolerance (define per-metric tolerances in the port plan); F3 soak zero-defect; F4 measured number on record. Any one failing = report, not workaround.
- **Hardware discipline:** P4 bench port `/dev/tty.wchusbserial5AAF2781791` (verify live); K1 identity rules apply to any S3 flashing; 1401 remains non-product-trusted until restored (existing constraint).

### Lane G (P2) — Perceptual validation rig

- **Evidence question:** Can eyes-on be made repeatable and asynchronous — (audio, semantic state, video, verdict) tuples captured as a corpus?
- **Scope:** corpus schema + capture harness design: synchronised audio fixture playback, semantic-state log (existing diagnostic surfaces), camera capture of the plate, Captain verdict annotation. Investigate alignment strategy (sync flash/beep marker at start). Build the minimal harness; capture lanes A/B/D A/Bs as the first corpus entries.
- **Non-goals:** no automated perceptual metrics yet (corpus first, metrics later); no panel studies.
- **Pass/fail:** one complete A/B captured end-to-end with verdict attached and replayable.

---

## 4. Dependency graph & suggested order

```
A (P0) ──┬─► E2 (gated on A PASS)
B (P0) ──┤
C0 schema ─► C1/C2/C3 (P1) ─► D consumers richer
C0 schema ─► F3 transport (P1 spike, parallel track)
F1 wiring ─► F2 port ─► F3 ─► F4 ─► F5
D (P1) after B (shares effect surfaces)
E1 design (P2) anytime; E2 after A
G (P2) harness before the A/D eyes-on batch if feasible — it captures them as corpus seed
```

Captain's existing open gates (device eyes-on batch for the forward-graft, quarantine disposition) are **not** displaced by this brief; lanes A/B/D eyes-on can batch with them.

## 5. Global validation standards

- Host: `pytest tests/` green + `pio run -e k1_hardware` clean before any milestone commit (gate enforces this). New published fields each get a replay test (range, rate, non-degenerate variance).
- Timing/causality claims: MabuTrace dev-trace only; non-shippable; label builds.
- Device: eyes-on per doctrine criteria (musical responsiveness, dual-channel independence, colour clarity, motion memory, captivation). Compile/upload ≠ proof.
- Every lane closes with a short evidence note in `docs/forensics/` or `docs/handover/` and a progress.md entry.

## 6. Waste guards (reject on sight)

More Goertzel/chromagram bins; render-quantisation work without a demonstrated banding case; sone-model loudness (A-weighting table suffices); ML downbeat/structure; embedded syncopation metrics; treating the C6 as a compute peer; any Lane F "partial transport success" reasoning.

## 7. Known risks register

| Risk | Lane | Mitigation |
|---|---|---|
| Transport corruption (in-house precedent: VMEWT) | F3 | Fail-closed framing from day one; zero-defect soak bar |
| chord_confidence too weak on real material to drive colour | B1 | Replay-corpus check before device time |
| Phase extrapolation exposes flywheel publish bug | A | Escalate; doctrine gate before sb_tempo edits |
| Per-channel effect state blows S3 RAM | D | Report numbers; PSRAM spill is an option, not a default |
| P4 port diverges from validated K1 metrics | F2 | Per-metric tolerance table; conflict reported, not averaged |
| ES8311 line-in path not exposed on board | F1 | Schematic check first; external codec fallback costed |
| Brief sprawl stalls eyes-on throughput | all | A/B are deliberately small; eyes-on batched with existing gate |

## 8. Decision points for Captain (answer before the affected lane starts)

1. **Lane F1:** approve the proposed aux wiring diagram before hardware work (agent must present it).
2. **Lane F2:** confirm "port K1 v2 engine onto P4" over "evolve P4's own DSP lane" (brief recommends the former).
3. **Lane C3:** 24-bin decimated tempo surface acceptable for v1, or insist on full 96?
4. **Lane G:** camera hardware available/budgeted for the rig, or design-only for now?
5. **Batching:** fold lanes A/B/D eyes-on into the existing pending device eyes-on batch, or run separately?

---

*Propagation note: any sub-agent dispatched from this brief inherits §0 verbatim. Delegation contracts per `.claude/CLAUDE.md` parallel-agent discipline: classification, evidence question, checkpoint, fallback, and consumption rule declared before launch.*
