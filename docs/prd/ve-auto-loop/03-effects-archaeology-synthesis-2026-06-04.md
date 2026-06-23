---
abstract: "CTO/CPO decision brief from the v3 archaeology + synthesis fleet (wf_f423b1c3-749, 36 agents, 144 hunt pieces). Recommends 'Living Plate, Liquid Grammar, Faithful Eye': Perception-Bus SBPerceptualFrame substrate (Layer A) + proven Liquid-Light visual grammar (Layer B) + recovered v3 degradation semantics (Layer C) gated by the K1Optics faithful-plate oracle (Layer D). Self-qualifying insight: the 0/10 wall is FORM + a blind oracle, NOT 'gate-and-die' (timbre_reach/beat_phase_scroll already have always-alive floors and still failed). Includes 7-step build plan (STEP 0-6), runner-up (Perception Bus #3), full evidence trail with v3 source anchors, candidates-and-verdicts table, and 4 open Captain decisions. Read before any VE-auto-loop effect-library or oracle build."
---

# CTO/CPO Decision Brief — Recovering v3's Solutions to the 14-Effect Wall

> **Provenance:** Faithful capture of the archaeology + synthesis fleet result
> `wf_f423b1c3-749` (36 agents; hunt returned 24/24 lanes, 144 total pieces;
> synthesis produced 5 candidate solutions). This document captures the brief
> as produced; it does not re-adjudicate it. Source workflow output:
> `/private/tmp/claude-501/-Users-spectrasynq-SensoryBridge-main-9/61900a42-5843-4454-b58a-69413f73f0a7/tasks/wzidd9dmb.output`.

---

> ## Orchestrator note — score/claim inconsistencies flagged on capture (read before acting)
>
> While capturing this brief faithfully, the following mismatches were found
> between the brief's evidence and the Captain's verbatim 2026-06-04 on-device
> verdicts (see the companion ground-truth file
> `effect-verdict-sheet-2026-06-04.md`). They are flagged, not silently corrected:
>
> 1. **`beat_phase_scroll` falsification anchor is OVERSTATED.** The brief's
>    evidence trail and self-qualified insight repeatedly assert that
>    `beat_phase_scroll` "has a graceful always-alive floor (BPS_UNLOCKED_DRIFT)
>    and STILL scored 0/10," using it as a co-equal proof that "add a fallback"
>    is insufficient. The Captain actually scored `beat_phase_scroll` **5.5/10
>    — his TOP score of the entire sweep** (praised-partial: "magical when it
>    locks; sterile single blobs when it doesn't"). So that *specific* "0/10
>    despite a fallback" anchor is factually wrong for this effect.
> 2. **The underlying point still stands on a different effect.**
>    `timbre_reach` carries a real always-alive floor (`TR_SILENCE_VU 0.05`,
>    line 52) and the Captain scored it **-20/10 (sterile/reject)** — well
>    below the 0/10 dead effects. So the load-bearing claim *"an always-alive
>    base is necessary-but-not-sufficient; FORM is the real killer"* is correct;
>    only the choice of `beat_phase_scroll` as the second exhibit is wrong.
>    `timbre_reach` alone fully supports the thesis.
> 3. **The brief implies the 7 "dead" effects gated-and-went-dark; the Captain's
>    verdicts say the dead 0/10 cluster (downbeat_bloom, onset_ripple,
>    onset_palette_step, beat_mirror_flip, spectro_waterfall, timbre_reach[=-20],
>    structure_arc[=-4000]) read as "no idea what it does / unusable," i.e. a
>    LEGIBILITY + FORM failure, not necessarily a darkness failure.** This is
>    consistent with the brief's reframe but worth stating plainly: the wall is
>    not "the strip is black," it is "the strip is doing something illegible or
>    sterile."
> 4. **`phase_breathe` (mode 31) is UNSCORED.** It does not appear in the
>    Captain's verbal list and was either untested or conflated with
>    `beat_phase_scroll`. The brief does not name it; no claim is made about it.
> 5. **Two flash/sparkle-class effects scored catastrophically negative**
>    (`kick_flash_overlay` -50,000,000/10 flash-BANNED; `flux_sparkle`
>    -200,000,000,000/10 sparkle-near-banned), which *strengthens* the brief's
>    Open Decision #4 (de-register the flash/sparkle class) rather than leaving
>    it merely "near-banned."
>
> No other material score/claim mismatches were found. The architecture,
> evidence anchors, and build plan below are captured verbatim from the brief.

---

## Self-qualified insight (read this first)

The board's center of gravity is wrong by one move: every candidate (and the
Captain's high prior) treats the 0/10 wall as **"effects gate on beat and
die,"** but the committed source falsifies that — `timbre_reach` already floors
at `TR_SILENCE_VU 0.05`, `beat_phase_scroll` already does graceful
`UNLOCKED_DRIFT`, and they STILL scored 0/10. So an always-alive base is
**necessary-but-not-sufficient**; the actual killers are **FORM** (sterile
blobs, whole-strip flash like `kick_flash_overlay`) and a **BLIND ORACLE** that
crowned the wrong effects.

The self-qualifying answer is therefore a layered single recommendation: take
the Living Plate / Perception-Bus SUBSTRATE (one perceptual frame,
confidence-as-blend, always-alive product) as the contract, render it ONLY in
the proven Liquid-Light visual grammar (bloom-mist advection + comet trail +
dark-anchored palette traversal — the language the Captain already called
magical), and run BOTH in lockstep with the K1Optics faithful-plate oracle as
the gate — because no amount of substrate or grammar unblocks autonomous
iteration while the host scorer still judges the raw strip and rewards the
flash/sparkle it was supposed to ban.

> **Self-qualified caveat (per Orchestrator note above):** the
> `beat_phase_scroll` half of the "already had a floor and STILL scored 0/10"
> exhibit is overstated — the Captain scored it 5.5/10. The thesis survives on
> `timbre_reach` alone.

### From the brief_markdown — the insight expanded

The board, the candidates, and the Captain's high prior all locate the failure
as **"effects gate on beat and go dark."** The committed source says otherwise,
and this reframes the whole recommendation:

- `light_mode_timbre_reach.cpp:52` already carries `TR_SILENCE_VU 0.05` ("a warm
  core survives true silence"); `light_mode_beat_phase_scroll.cpp:28-64` already
  does graceful `BPS_UNLOCKED_DRIFT` ("the river keeps flowing — it never
  freezes"). **These have always-alive floors and STILL scored 0/10.**
  *(Orchestrator correction: beat_phase_scroll actually = 5.5/10.)*
- A repo-wide grep for the gate-and-die early-return pattern (`confidence < thr`,
  `if(!beat) return`) across `SPECTRASYNQ_K1_FIRMWARE/effects/*.cpp` returns
  **EMPTY**. The disease Candidate 5 proposes to "delete" does not exist in the
  committed tree.

So **"add an always-alive base" is necessary-but-not-sufficient.** The real
killers, in priority order: (1) **FORM** — sterile disconnected blobs and
whole-strip flash (`kick_flash_overlay.cpp:7` literally fills "the WHOLE
strip"); (2) **arbitrary coupling** — a "bass" comet that doesn't read bass;
(3) the **blind oracle** that ranked sparkle/ripple top. The fix is not one
candidate — it is the **best layer from three of them, gated by the fourth.**

---

## RECOMMENDED — "Living Plate, Liquid Grammar, Faithful Eye"

A **forced synthesis, not a pick**: a single layered build that takes the
strongest, source-verified piece from each survivor candidate and discards the
parts the verdicts falsified.

### Layer A — Perceptual contract (from Perception Bus #3, the cleanest substrate framing)

Promote the structs the fork ALREADY computes into one `SBPerceptualFrame` read:
**LOUDNESS / PITCH / TIMBRE / RHYTHM**. Three laws:

1. Effects read only the frame, never raw bins or raw beat bools.
2. Confidence is ALWAYS a blend weight `out = base + conf*lift`, never an `if`.
3. Every axis has an always-alive fallback (RMS-tau persistence + a 128bpm
   self-clock when `beat_confidence < 0.25`).

Verified-buildable: `low/mid/high_energy` are TRUE band thirds
(`sb_audio_snapshot.cpp:36-52`, NOT the R6 broadband trap), `beat_confidence` is
a real continuous scalar separate from `locked` (`sb_tempo.cpp:362-364`), the
frame is already wired into the single AP loop (`.ino:573-575`).
**Correction applied:** rate is **133.33Hz** (`sb_tempo.cpp:22`, `12800/96`), not
the ~100/120Hz several candidates stated; author all tau in seconds so this is
moot.

### Layer B — Liquid-Light visual grammar (from Liquid-Light Spine #2, the proven look)

This is the layer that fixes FORM, which the substrate alone cannot. Every new
effect is authored as **"a palette-coloured field that advects and remembers,
which energy LIFTS"** — built on `light_mode_bloom.cpp` (verified gate-free
advection of `leds_prev` + chromagram colour at the two centre LEDs + quadratic
edge fade + mirror — no silence/beat branch anywhere) plus the
`light_mode_comet.cpp` trail grammar seeded onto the SAME advecting buffer (a
palette wake, never a bare dot). Colour routes exclusively through
`effect_palette_or_chroma_colour()` / `chromagram_centroid_hue()`
(`lightshow_modes.h:213/266`, the verified circular-mean — the named fix for
"responds to who knows what"), on the Captain's dark-anchored 7-palette sequence
so energy = traversal into a bright core on a black floor = **structurally
anti-flash**.

### Layer C — Recovered degradation SEMANTICS (from the Jigsaw board / Substrate #1's port plan)

Port v3's *semantics, not its estimator* (the board's own thesis correction;
fork `sb_tempo.cpp:50` measures ~14% Acc2, WORSE than the WALL's 28% — which
only strengthens always-alive). Header-only, dt-correct drops:
`AudioReactivePolicy.h` metronome cascade, `AudioGatedDecay.h` RMS-linear tau,
`beatMod = 0.4 + 0.6*beat_strength` (40% floor), Emotiscope confidence-dimmer.
All physically present at `Lightwave-Ledstrip/firmware-v3/` (verified on disk).

### Layer D — The faithful-plate oracle (from K1Optics #4) as the GATE, run in PARALLEL from day one

This is the declared unblock and the only thing that lets autonomous iteration
resume without the Captain's bench. Extend
`scripts/regression-harness/render_replay.py` (which self-declares
pre-gamma/pre-optics linear quantise) with:

- (a) the LGP diffused-plate gaussian BEFORE scoring,
- (b) the real firmware onset/beat feed (the harness already has
  `novelty_from_wav.py` at native 133.33Hz),
- (c) the inverted CLOSED_LOOP weights (`beat_align 0.25`, `dynamic_range`
  DEMOTED to `0.05`, geometric mean so one flicker/clip axis collapses the
  score),
- (d) the Rule #9 empty-allowlist lint as a cheap pre-screen.

### How this specifically resolves each named failure (using RECOVERED v3 mechanisms)

- **No-fallback / dark-at-low-confidence** → Layer A law-3 fallback engine +
  Layer B bloom advection base (gate-free in source) + `beatMod 0.4` floor. The
  base is structural, not per-effect-optional.
- **Sterile disconnected blob** → Layer B: one continuously advecting optical
  field with 5-bin gaussian centre injection (not a needle); accents ride ON it.
  This is the layer the verdicts proved the substrate alone misses —
  `timbre_reach` had a floor and was still rejected because its FORM was wrong.
- **Arbitrary coupling ("bass comet didn't track bass")** → Layer A binds named
  sources to real bands at config time; the v3 self-calibrating asymmetric
  max-follower (the actual "tracks bass" kernel, `LGPAiryCometAREffect`) makes it
  read across volume; the oracle's `Pearson(|dRMS|,|dBright|)` makes it
  FALSIFIABLE.
- **Blind oracle** → Layer D judges the diffused PLATE not the strip, feeds real
  onset/beat not a chroma proxy, and inverts the reward (penalises flicker =
  flash/sparkle). **Critical guard the verdicts surfaced:** calibrate on a
  STRUCTURED 14-verdict set with leave-one-out, never in-sample Spearman (the
  exact way v3's deferred Track-A predictor failed), and add a guard so a flat
  dim "sterile wash" cannot score high.

### Blockers from the #1 candidate that this synthesis ROUTES AROUND (all source-verified)

1. **`vp_probe_dispatch_and_hash` is the wrong function.** Verified: it is the
   bit-identity DETERMINISM probe that "renders primary only" and EXPLICITLY
   EXCLUDES the 14 new modes as non-deterministic (`lightshow_modes.h:680-763`).
   A runtime post-scale there would not touch the device and would corrupt the
   probe. The real global gate is `silent_scale` at `led_utilities.h:197` — use
   that.
2. **`bass_onset_flux` does not exist.** Verified: `SBOnsetBeatEvent` exposes
   `bass_onset_strength` (event-only) and `bass_onset` (bool), no continuous flux
   (`sb_audio_snapshot.h:32-38`). The `KICK_LEVEL = bass_onset ? 1.0 :
   bass_onset_flux` idiom needs a flux signal DERIVED first — scope it, don't
   assume it.
3. **The oracle is net-new, not an "extension."** Verified: grep of
   `scripts/regression-harness/` + `tests/` for `lgp|diffus|gaussian|blur`
   returns EMPTY; `render_replay.py` covers only 5 modes (bloom / waveform /
   waveform_fast / spectrum_river / comet), none of the 14. Wiring the 14 + the
   optics + calibration is the real critical path.

---

## Build plan (STEP 0 – STEP 6)

**STEP 0 (Captain input, one-time):** capture the 2026-06-04 verbal verdicts into
a STRUCTURED per-effect score sheet (effect name → 0..10 + tag:
dead/flash/sparkle/sterile/praised). This is the oracle's calibration ground
truth and the only required founder input. Branch all work on `wip/*` per the
commit gate.
*(Status: DONE — captured in the companion file `effect-verdict-sheet-2026-06-04.md`.)*

**STEP 1 (Layer A contract, additive, zero behaviour change):** create
`SPECTRASYNQ_K1_FIRMWARE/audio/sb_perceptual_frame.h` composing the live
`SBAudioSnapshot` + `SBTempoEvent` + `SBOnsetBeatEvent` + `SBMusicState` into one
read with named axes (LOUDNESS/PITCH/TIMBRE/RHYTHM), each carrying an
always-alive fallback computed inline (RMS-tau persistence + 128bpm self-clock
when `beat_confidence<0.25`). Author ALL tau in seconds (rate-agnostic; the loop
is 133.33Hz, `sb_tempo.cpp:22` — do NOT hardcode frame counts). Wire one call
after `.ino:575`. `pytest tests/` green, commit.

**STEP 2 (Layer C semantics + Layer B shared spine, header-only):** port the v3
degradation primitives as `sb_graceful.h` (`beat_lift=0.4+0.6*beat_strength`,
confBlend, `jnd_floor>=0.08`, AudioGatedDecay RMS-tau) citing each
Lightwave-Ledstrip/firmware-v3 anchor in-comment; and extract
`light_mode_bloom`'s advection+centre-injection into `sb_bloom_field.h`, guarded
byte-identical by the existing VP bloom bit-hash gate. Host unit-test the
primitives (confBlend monotonic, floor holds). Commit each green.

**STEP 3 (Layer D oracle, host-only, the unblock — run in parallel with 1-2):**
extend `scripts/regression-harness/render_replay.py` with (a) an LGP
diffused-plate gaussian pre-pass (ported-shader v1 values, flagged provisional),
(b) the real onset/beat feed via the existing `novelty_from_wav.py` @133.33Hz
(not a chroma proxy), (c) the inverted CLOSED_LOOP geometric-mean weights
(beat_align 0.25, dynamic_range 0.05), (d) a Rule#9 empty-allowlist static lint.
Add a guard so a flat dim wash cannot score high.

**STEP 4 (wire the 14 + calibrate):** add the 14 effects to `render_replay` MODES
(per-effect C fragments — this is the bulk of the real work, ~1-2 days, not
"reuse"). Calibrate the oracle against Step-0 sheet with LEAVE-ONE-OUT, never
in-sample Spearman. Gate = oracle ranks praised bloom/holographic top AND the 7
dead/flash/sparkle effects bottom-quartile. That passing test
(`tests/test_oracle_calibration.py`) is the autonomous-iteration unblock signal.

**STEP 5 (proof-of-concept retrofit, ONE effect):** build
`light_mode_perceptual_bloom` on the spine — continuous advecting base via
`sb_bloom_field` (gate-free, JND-floored), `brightness=LOUDNESS x geometry x
breathing`, `hue=chromagram_centroid_hue`, beat enters ONLY as `beat_lift` +
`bass_onset` centre-injection accent, colour via
`effect_palette_or_chroma_colour`, dual-channel via
`vp_render_secondary_channel`. Confirm it out-scores the rejected
sparkle/ripple in the now-faithful oracle. Commit host-green; Captain eyes-on as
tracked NON-blocking follow-up per commit gate.

**STEP 6 (retrofit the comet R1 gap, then scale):** pair `light_mode_comet`'s
spawn with the `sb_bloom_field` base so kick-less material shows the living
field (fixes the verified "intentionally quiet" gap). Once the oracle is
calibrated-faithful, the remaining 12 effects adopt the same 3-layer pattern
incrementally, each a separate green commit, with the oracle (not the Captain)
as the per-effect screen.

---

## Runner-up

**Perception Bus (#3) standalone** — highest single score on the board (**78**)
and the cleanest architecture, but as a standalone it under-delivers on FORM (it
permits but does not guarantee the narrative look — the same gap that sank
`timbre_reach`) and shares the same unbuilt-oracle dependency. It is **not the
runner-up to BEAT but to ABSORB**: its `SBPerceptualFrame` contract IS Layer A
of the recommendation.

If a single-candidate path is mandated, **Liquid-Light Spine (#2, score 71)** is
the true alternative because it leads with the proven look and is the lowest
firmware blast radius — but it must not claim unblock until its Step-3 oracle
demonstrably ranks bloom above ripple.

---

## Candidates and verdicts

| # | Candidate | Verdict | Score |
|---|-----------|---------|-------|
| 1 | SUBSTRATE: The Living Plate — fork-native AliveBase + AudioBus coupling substrate (two drop-in headers + one global post-scale + per-effect refactor) | conditional | 72 |
| 2 | Liquid-Light Spine: bloom-mist + comet-trail + palette engine as the LOOK library, beat as seasoning | conditional | 71 |
| 3 | Perception Bus: the `SBPerceptualFrame` as the single audio-to-pixel contract | conditional | **78** |
| 4 | K1Optics Oracle — The Faithful Plate (the eye-predictor that unblocks autonomous iteration) | conditional | 58 |
| 5 | Graceful-Blend Retrofit: the smallest v3 recovery that kills the 0/10 gate disease | conditional | 52 |

> Note: candidate #5's premise ("kill the 0/10 gate disease") is the one the
> source falsified — the per-effect early-return gate it proposes to delete
> greps EMPTY in the committed tree. This is reflected in its lowest score (52).

---

## Evidence trail (load-bearing anchors, all verified this session — VERBATIM)

> Captured verbatim from the workflow `evidence_trail` array. This is the proof;
> it is reproduced in full.

1. **Falsifies the shared diagnosis:**
   `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_timbre_reach.cpp:52`
   (`TR_SILENCE_VU 0.05` 'warm core survives true silence') +
   `light_mode_beat_phase_scroll.cpp:28-64` (`BPS_UNLOCKED_DRIFT` graceful drift,
   'the river keeps flowing, never freezes') — both have always-alive floors and
   STILL scored 0/10; grep of `effects/*.cpp` for `confidence<thr` /
   `if(!beat)return` = EMPTY.
   *(Orchestrator note: beat_phase_scroll actually scored 5.5/10, not 0/10 — see
   note at top. timbre_reach scored -20/10, which still supports the thesis.)*
2. **Real always-alive targets:** `light_mode_comet.cpp:39-40` ('intentionally
   quiet... Deferred: continuous baseline') and `light_mode_onset_ripple.cpp:14-15`
   ('Between onsets nothing is injected — HONEST silence behaviour (a still pond)').
3. **Banned form in-tree:** `light_mode_kick_flash_overlay.cpp:7` ('a dim baseline
   fills the WHOLE strip; on every kick a flash').
4. **Proven spine + authorities:** `light_mode_bloom.cpp` (gate-free advection
   base, no silence/beat branch); `led_utilities.h:197` `silent_scale` (the REAL
   global gate, NOT the probe); `lightshow_modes.h:213/266`
   `effect_palette_or_chroma_colour` + `chromagram_centroid_hue` circular-mean.
5. **Fork facts that correct candidate errors:** `sb_tempo.cpp:22`
   `SB_AP_FRAME_HZ=12800/96=133.333Hz` (not ~100/120); `sb_tempo.cpp:50`
   host-measured Acc2 ~14% (not 28% — strengthens always-alive);
   `sb_tempo.cpp:362-364` confidence separate from locked;
   `sb_audio_snapshot.cpp:36-52` true band thirds (R6 trap absent);
   `sb_audio_snapshot.h:32-38` exposes `bass_onset_strength` only — NO
   `bass_onset_flux`.
6. **Candidate-1 blocker confirmed:** `lightshow_modes.h:680-763`
   `vp_probe_dispatch_and_hash` is the bit-identity determinism probe ('renders
   primary only', 'EXPLICITLY EXCLUDED ... non-deterministic') — wrong place for
   a runtime post-scale.
7. **R12 gap confirmed:** `scripts/regression-harness/render_replay.py:7-26`
   self-declares pre-gamma/pre-optics linear quantise, MODES covers only
   bloom/waveform/waveform_fast/spectrum_river/comet (5 of 14); grep of
   `scripts/regression-harness` + `tests` for `lgp|diffus|gaussian|blur` = EMPTY.
8. **Recovery substrate is real and portable:**
   `Lightwave-Ledstrip/firmware-v3/` present with `AudioReactivePolicy.h`,
   `AudioGatedDecay.h`, `PerceptualJND.h`, `check_effect_contracts.py:436` (empty
   `SILENCE_GATE_ALLOWLIST`), `CLOSED_LOOP_QUALITY_SYSTEM.md`,
   `GOOD_LIGHT_SHOW_TAXONOMY.md`.

### Strongest anchors (from the jigsaw board — supplementary, verbatim)

These 15 anchors back the board's recovered recipes (fallback / coupling /
visual / palette / beat / perceptual-law / oracle). Reproduced verbatim because
they are the load-bearing proof for the build plan.

1. `tools/check_effect_contracts.py:436` `SILENCE_GATE_ALLOWLIST=set()` + `:954`
   `check_local_silence_gate` + `:1082` invoked as rule #9 (VERIFIED live) — the
   lint that hard-fails any per-effect silence/beat early-return; the
   architectural cure for the ~7 dead-on-low-confidence effects.
2. `src/audio/AudioActor.cpp:965-989` (VERIFIED live) — the confidence-envelope
   SEAM FIX: `musicPresent=rmsPresent&&noveltyPresent`, instant-attack/hold/
   exp-release `audioConfidence`, `tempoBeatTick` passed unconditionally (deletes
   the 0.35-0.5 dead zone that killed BLOOM/RECOIL).
3. `src/effects/ieffect/AudioReactivePolicy.h:50-137` (VERIFIED metronomeFallback
   + kTempoConfMin present) — confidence-gated trigger cascade + free-running
   metronome fallback; THE R7 graceful-degradation primitive, header-only,
   rate-agnostic.
4. `docs/EFFECT_DEVELOPMENT_STANDARD.md:454-509` — `beatMod=0.4+0.6*beatStrength()`
   (40% always-alive floor), `isOnBeat()` BANNED for brightness/colour (use
   spawn-only); the proven flash replacement.
5. `src/effects/ieffect/ChromaUtils.h:38-126` (commit d943101a) —
   `circularChromaHueSmoothed` (circular mean not argmax) consumed by ~40 v3
   effects; the named fix for hue-flip/'responds to who knows what'; fork has
   native `effect_palette_or_chroma_colour()` equivalent (VERIFIED across ~10
   fork effects).
6. `src/audio/contracts/AudioEffectMapping.cpp:440-471` (`getAudioValue
   BASS=bands[0..1]`) + `:621-637` (audio-absent decay-to-outputMin, never zero)
   — the semantic source ground truth + graceful-decay routing; the
   'trigger?1.0:continuous_flux' idiom.
7. `docs/GOOD_LIGHT_SHOW_TAXONOMY.md` (VERIFIED present 7.8K) 8-axis 0-3 rubric +
   Rejection Patterns — the codified Captain-eye scoring spec naming
   metronome-blink/random-flash/fragmented-dots/graph-look as the exact modes the
   broken oracle rewarded.
8. `docs/design/CLOSED_LOOP_QUALITY_SYSTEM.md §4.1/§7.3` (VERIFIED present 33.8K)
   — L0-L4 metric hierarchy + composite weights (beat_align 0.25, dynamic_range
   DEMOTED to 0.05, geometric-mean so one bad axis collapses the score) +
   Centre-edge gradient & Strip-symmetry L0 metrics.
9. `src/metrics/VRMSBenchmark.h` (VERIFIED temporalFreq/symmetryScore/
   audioVisualCorr present) — on-device 8-metric perceptual oracle scoring the
   REAL rendered buffer in 214-266us; INVERTS the broken oracle (reward LOW
   temporalFreq, HIGH audioVisualCorr).
10. `src/effects/PerceptualJND.h:23-57` + `test_perceptual_jnd.cpp` (VERIFIED
    present) — K1 LGP 8% perceptual floor (byte 1) as the hard always-alive bound
    + `isBelowK1LgpJnd` anti-sub-JND-churn predicate.
11. `docs/measurements/apparent-motion-on-k1.md §5/§8` — measured motion-fusion
    thresholds (inter-step ~36-60ms, fuse only <=28-32px & 50-90ms ISI); the
    anti-blink law: beat must modulate continuous scroll velocity, never per-beat
    position jumps.
12. `src/effects/ieffect/BeatParitySpriteEffect.cpp:121-236` (commit 39406e6b) —
    kick (tempo-independent) = sole spawn, tempo->accent only, parity->trace-only:
    'a kick always spawns so chord-only music with no tempo lock still produces
    visible sprites' = canonical 28%-tracker-as-modulation.
13. `src/effects/persistence/AudioGatedDecay.h` (VERIFIED present) — RMS-linear
    persistence tau (0.1s quiet->2.0s loud), always-alive motion memory in ~5
    lines, dt-correct drop-in.
14. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_comet.cpp:58/98-104` (VERIFIED
    current fork) — comet class-grammar + event_id dedup ('every comet==a kick');
    NOTE absolute-only floor `COMET_MIN_STRENGTH=0.06` 'no relative gate'
    (contradicts mem 'v4' dual-gate claim) + open gap: still goes quiet with no
    kick (needs always-alive base pairing).
15. `tools/liquid_light_palette_sequence.py:54-62` +
    `lp_hero_liquid_light_captain_palette_2026-05-09.md` (commit 627b0b14) — the
    Captain's hand-curated 7-palette dark-anchored sequence (31->28->24->22->19->
    16->10) = the proven 'magical' liquid-light colour DNA; brightness=181
    speed=14 dwell=7s.

---

## Open decisions for the Captain

1. **SEQUENCING (the one genuine strategic fork):** ship effect cures (Layers
   A-C) FIRST on host-green + non-blocking eyes-on while building the oracle (D)
   in PARALLEL — **RECOMMENDED**, fixes the 7 dead effects this week and generates
   the verdict data the oracle needs — OR hold all generation until the oracle
   gates it (purist, but leaves the wall standing while you build a scorer).
   *(The cures fix the 7 dead effects this week AND generate the better verdict
   data the oracle must calibrate against; holding everything for the oracle
   redecorates the control room while the room is on fire.)*

2. **ORACLE CALIBRATION GROUND TRUTH:** does a structured 14-effect verdict sheet
   already exist (point me at it), or must your 2026-06-04 verbal verdicts be
   captured once into a per-effect score sheet? This is the only Captain input
   the oracle genuinely cannot proceed without, and the one legitimate
   founder-in-the-loop touch (defining the target, not iterating the harness).
   *(Status: RESOLVED — the verdict sheet now exists at
   `effect-verdict-sheet-2026-06-04.md`, captured from the 2026-06-04 verbal
   verdicts.)*

3. **LGP GAUSSIAN FIDELITY:** accept the ported web-shader diffusion constants as
   oracle v1 (fast, good enough to rank-order) with a measured plate-PSF capture
   as a tracked follow-up — **RECOMMENDED** — or block oracle trust on a hardware
   PSF measurement first (slower, higher fidelity).

4. **FLASH/SPARKLE EFFECTS IN-TREE:** `kick_flash_overlay.cpp` (whole-strip flash,
   banned) and `flux_sparkle.cpp` (sparkle, near-banned) physically exist.
   De-register them from the director now, or keep them only as labelled oracle
   negatives until the oracle is proven to reject their class?
   *(Orchestrator note: the Captain's 2026-06-04 verdicts scored these
   -50,000,000/10 and -200,000,000,000/10 respectively — i.e. an emphatic ban
   signal that argues for de-registration now, retaining them only as labelled
   oracle negatives.)*

---

## Delegation ledger (from the workflow, verbatim)

This synthesis dispatched no sub-agents; the load-bearing inputs (5 candidates,
adversarial verdicts, the v3 jigsaw board) were supplied as closed inputs, and
the CTO/CPO pass independently re-verified every load-bearing anchor against
current source. Four self-verification lanes were recorded:

- `SELF-VERIFY-01` | re-verify the three disputed Candidate-1 blockers
  (vp_probe output-stage misplacement, bass_onset_flux existence, R12 optics
  gap) | load-bearing | direct grep/read of `SPECTRASYNQ_K1_FIRMWARE` +
  `scripts/regression-harness` | **received** | all three CONFIRMED.
- `SELF-VERIFY-02` | test whether the 'dead' effects already have floors
  (does 'add a base' suffice?) | load-bearing | grep of
  timbre_reach/onset_palette_step/structure_arc/beat_phase_scroll | **received**
  | floors and graceful drift ALREADY PRESENT yet 0/10 → self-qualifying insight.
- `SELF-VERIFY-03` | confirm AP rate and tempo accuracy (133 vs 100Hz; 14 vs
  28%) | load-bearing | `sb_tempo.cpp:22/50` | **received** | 133.33Hz and ~14%
  Acc2 confirmed.
- `SELF-VERIFY-04` | confirm v3 recovery tree and port-source files are on disk
  | load-bearing | `ls` + grep of `Lightwave-Ledstrip/firmware-v3` |
  **received** | all 6 cited port sources + empty-allowlist lint PRESENT.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:orchestrator | Created — capture of archaeology+synthesis fleet wf_f423b1c3-749 |
