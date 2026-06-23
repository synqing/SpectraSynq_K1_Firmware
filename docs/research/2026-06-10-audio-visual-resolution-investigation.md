# Audio→Visual "Resolution" Investigation — 2026-06-10

**Question (Captain):** How do we extract more usable resolution from the audio pipeline, and how do we visualise more of the resolution already being fed into the visual pipeline? Increasing chromagram bins and Goertzel bins was already tried and judged a dead end.

**Method:** Three parallel load-bearing SSAs (AP information-loss audit, VP consumption audit, external DSP/visualiser research), cross-checked against live source. Doctrine gate read (`/sensorybridge-doctrine` skill file) before analysis. No firmware edited. Delegation ledger at end.

---

## 1. Core problem

"Resolution" in this system is not bin count — it is the number of **independent, perceptually orthogonal feature axes** that survive the journey from DSP to LED. The pipeline has two compounding funnels: the AP computes far more information than it publishes (~95–98% of internal richness is discarded at the publish surface), and the VP consumes only a fraction of what *is* published (chord state has **zero** consumers; snare/hihat channels are dark). Adding bins widens an axis the eye cannot resolve on a diffused 128-LED plate; adding orthogonal axes adds whole new perceptual channels. The Captain's bin-count instinct was correct to reject — cross-modal perception research and every acclaimed visualiser examined (MilkDrop runs on ~8 audio scalars) confirm axes-over-bins.

## 2. Constraints / root causes

**[FACT] The publish funnel (AP side) — information that exists but never reaches the VP** (SSA-AP-01, file:line verified):

| Internal signal | Exists as | Published as | Loss |
|---|---|---|---|
| Tempo spectrum | 96 BPM bins × (magnitude, phase, ACF salience) — `sb_tempo.cpp:126-137` | Winner's bpm/phase/confidence only | 95:1 |
| Per-band onset flux | Continuous log-flux @ 133 Hz per band — `sb_onset_beat.cpp:133-141, 220-257` | Binarised kick/snare/hihat + clamped strength | Continuous→bool |
| AGC dynamics | `agc_envelope`, `agc_noise_floor`, `agc_gain` — `GDFT.h:248-274`, `globals.h:575-577` | Binary `silence` only | Envelope→bool |
| Per-bin novelty | 80-bin frame-to-frame flux — `GDFT.h:332` | 1 summed scalar | 79:1 |
| Spectral history | 5×80 ring — `globals.h:86` | Nothing (novelty input only) | Total |
| Chroma detail | 12-bin vector + per-degree energies — `sb_chord_detect.cpp:40-90` | root/type/confidence + 3 strengths | Partial (chroma_pc[12] is published under SB_CHORD_V2 but unconsumed) |

**[FACT] The consumption funnel (VP side)** (SSA-VP-01, confirmed against source and platformio.ini):

- Chord state: computed, published, **zero effects read it**. `platformio.ini:89` literally annotates `SB_CHORD_V2` as "inert until a consumer exists".
- Snare/hihat V2 channels: published, no consumer.
- `novelty`: one consumer (Dense Forge).
- Tempo fields ARE wired — 6 effects consume them (`waveform_tempo`, `tempo_comet`, `tempo_river`, `dense_forge`, `pulse_prism`, `snapwave`). SSA-AP-01's "built-not-wired" claim came from a stale capability doc and is **corrected** here.
- Dual-channel is not two audio dimensions: primary/secondary run the same effect state with parameter overrides, reading identical audio data (`sb_edgemixer_lite`). The hardware supports two independent perceptual channels; the firmware currently delivers one.
- Render-path losses exist (hard clip, gamma shadow compression, dither floor, band→LED interpolation — `led_utilities.h:1518-1640`) but are second-order relative to the two funnels above.

**[FACT] All five v2 flags are ON in `k1_hardware`** (`platformio.ini:86-90`) — the publish surface is live in production builds.

**[FACT] NUM_FREQS = 80** (`system/constants.h:31`), not the "24 octave bands" stated in root CLAUDE.md. Doc inaccuracy; flagged for correction.

**[INFERENCE] Why more bins failed:** bins subdivide one axis (pitch/spectrum) that is already saturating the display's spatial resolution and the eye's discrimination on a diffused plate. The bottleneck was never within-axis precision; it is the axis count and the publish/consume funnels. This is consistent with MilkDrop's 8-scalar feature surface driving the most celebrated visuals in the genre (SSA-RES-01, geisswerks authoring guide).

**[FACT — external] Emotiscope (same author as Sensory Bridge) moved beyond the original design not with more bins but with:** a 96-bin tempo Goertzel bank rendered *in parallel* (magnitude+phase per BPM hypothesis, round-robin amortised at 2 bins/frame), a second novelty curve from amplitude (VU) alongside spectral novelty, and continuous silence-contrast. K1's v2 graft already has the tempo bank internally — it just doesn't publish or render the parallel hypotheses. (Sources: Emotiscope `tempo.h`, product page; SSA-RES-01.)

## 3. Decisive plan (ranked by leverage)

### Tier 1 — Consume what is already published (zero new DSP, zero AP risk)

1. **Chord→colour consumer.** Map `chord_root` to hue anchor, `chord_type` to palette character, `chord_confidence` to saturation, in 2–3 existing harmonic effects. Improves: harmonic relevance of colour. Removes: the single largest computed-but-invisible asset. Validation: host replay + eyes-on A/B on harmonically rich material.
2. **Snare/hihat channel consumers.** Kick already drives effects; route snare/hihat to spatially/chromatically distinct gestures (e.g. secondary-channel accents). Improves: rhythmic decomposition visibility.
3. **Generalise `novelty` beyond Dense Forge** as an articulation modulator (shimmer/transport speed).

### Tier 2 — Publish what is already computed (struct additions, no new algorithms)

4. **Continuous per-band flux** (4 floats, pre-threshold values from `sbv2_band_flux()`): distinguishes snappy vs swelling onsets; VP-side envelope followers replace binary on/off. +16 B.
5. **AGC envelope + noise floor** (2 values): a continuous loudness/dynamics axis → brightness arcs, scene black-level. +32 B.
6. **Parallel tempo surface**: publish `sb_tempi_smooth[]`/`sb_acf_salience[]` (decimate to e.g. 24 of 96 bins if budget-tight) → Emotiscope-class parallel-rhythm rendering instead of winner-takes-all. +≤768 B @ 44 Hz. This is the single richest unpublished signal in the firmware.

### Tier 3 — New cheap axes (O(80) scalar passes, trivial Core-0 cost)

7. **Spectral centroid + flatness** from existing magnitudes → brightness (colour temperature) and tonal/noisy (saturation/texture) axes. Strongest cross-modal research backing of anything on the list.
8. **Tonal centroid (6-D Harte projection) + HCDF** from existing chroma (72 MACs + smoother) → hue follows harmonic *trajectory*; harmonically near chords get near colours; HCDF = "harmony is moving" signal.
9. **Fast/slow asymmetric envelope pairs** (MilkDrop `bass`/`bass_att` idiom) + 20–30 s macro-dynamics arc → verse/chorus staging.

### Tier 4 — Structural (higher risk, confidence-gated)

10. **Bar-phase "downbeat-lite"** (beat counter mod 4, rotation scored by low-band accent on existing locked PLL) and **Foote-lite section-change** at ~2 Hz off the hot path. Non-ML downbeat accuracy is genre-dependent — ship behind a confidence gate or not at all.
11. **True dual-channel independence**: channel A = spectral/harmonic axes, channel B = rhythmic/transient axes. Doctrine names independent dual-channel behaviour as a north-star property; this is currently unrealised.

**Explicitly rejected as low-leverage:** more Goertzel bins, more chromagram bins (confirmed dead end — saturated axis); render-path quantisation fixes as a first move (real but second-order — fix only where an effect demonstrably shows banding); sone-model psychoacoustic loudness (A-weighting table captures ~90% at a fraction of cost); ML downbeat/structure models (off-budget on Core 0); embedded syncopation measures (no deployed precedent found — dead end for now).

**[HYPOTHESIS] Sequencing:** Tier 1 alone should produce a visible perceptual jump because it adds two whole axes (harmony→colour, rhythm decomposition) with no AP risk. Tiers 2–3 are where "more resolution" structurally lives. Treat Tier 1 as the cheapest falsification test of the axes-over-bins thesis itself: if a chord-colour consumer does not improve eyes-on impact, revisit the thesis before investing in Tiers 2–4.

## 4. Validation / pass-fail

- **Host gate:** each new published field gets a replay test asserting range, rate, and non-degenerate variance over the existing fixture corpus; `pytest tests/` green; `pio run -e k1_hardware` clean. Struct growth budgeted and asserted (snapshot remains a POD volatile read; frame-counter consistency unchanged — no mutexes on the audio path).
- **Timing:** Tier 2/3 additions are O(bands) scalar passes; assert AP frame time unchanged via existing rate-consistency test. Any timing/causality doubt → MabuTrace on `k1_hardware_trace_dev`, never scalar inference (instrumentation boundary applies).
- **Device:** eyes-on A/B per doctrine — same track, old vs new consumer, judged on musical responsiveness, dual-channel independence, colour clarity, motion memory. Compile/upload is not runtime proof. Note: device eyes-on is already THE open gate for the forward-graft; this lane queues behind or alongside it.
- **Assumption detection:** if chord_confidence is chronically low on real material (would make Tier 1 item 1 invisible), the replay corpus will show it before any device time is spent.

## Doctrine gate outputs (per skill contract)

1. **Doctrine rules:** architecture subordinate to perceptual impact; regression test = musical responsiveness, dual-channel independence, colour clarity, motion memory, captivation.
2. **Local evidence touched:** `sb_tempo.cpp`, `sb_onset_beat.cpp`, `GDFT.h`, `sb_audio_snapshot.*`, `sb_chord_detect.cpp`, `platformio.ini`, effects/ consumption scan.
3. **North-star impact:** Tiers 1–3 directly serve musical responsiveness and colour clarity; Tier 4 item 11 serves dual-channel independence.
4. **Re-test triggers:** any AP publish-surface change → host replay suite; any effect change → eyes-on follow-up (tracked, non-blocking per commit-gate doc).
5. **Runtime proof required:** eyes-on A/B for every consumer change; MabuTrace for any timing claim.
6. **Minimal edit plan:** Tier 1 first (effects-only, no AP edits), then Tier 2 struct additions one field at a time, each behind its own flag, each with a replay test.
7. **Non-goals:** no bin-count increases, no calibration/AGC tuning, no quarantined-lane edits, no ML.

## Delegation ledger

| ID | Task | Class | Type | Status | Evidence | Consumption |
|---|---|---|---|---|---|---|
| SSA-AP-01 | AP information-loss audit | load-bearing | Explore | received (self-declared partial: build flags unverified) | file:line inventory of all 6 AP stages | Loss table §2; flag escalation resolved by orchestrator via `platformio.ini:86-90`; its "tempo built-not-wired" claim **rejected** against live source (6 consumer effects found) |
| SSA-VP-01 | VP consumption matrix | load-bearing | Explore | received | 23-effect matrix, render bottleneck ranking | Consumption funnel §2, Tier 1 targets; tempo-consumer finding used to correct SSA-AP-01 |
| SSA-RES-01 | External DSP/visualiser research | load-bearing | general-purpose | received | Cited brief (Emotiscope/SB source fetched, MIR literature, WLED/LedFx/MilkDrop) | Tiers 2–4 technique selection; axes-over-bins framing; dead-ends list |

Conflicts between SSA-AP-01 and SSA-VP-01 were resolved by direct source verification, not averaged. SSA-AP-01's branch-state claim ("feat/gdft-harness @ f67054d") was not relied upon — current lane authority remains `.claude/handoff.md`.
