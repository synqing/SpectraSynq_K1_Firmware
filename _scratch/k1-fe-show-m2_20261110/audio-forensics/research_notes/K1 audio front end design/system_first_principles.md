---
abstract: "First-principles analysis of the K1 audio front end as it exists in firmware a6bad318 (Main RPL build), written by the K1-FE-SHOW lead on 10 Nov 2026 from the source, the bench telemetry and the emulator captures. It lists every level-controlling stage between the microphone and the effects, why each exists, what each destroys, the measured consequences, the jobs a front end must really do, a candidate design ('measure once, what x how much, one slow exposure'), a validated model of it on seven tracks, and the red-team and pre-mortem findings against it. Input for the research report; the external research notes sit beside this file."
---

# K1 audio front end: first-principles analysis of our own system (10 Nov 2026)

Labels: [FACT] read in source, a capture or telemetry; [INFERENCE] derived; [HYPOTHESIS] untested.
Source revision: a6bad318, env `k1_main_rpl_show_bench` (= `k1_main_rpl_im69d` + capture). Paths relative to `SPECTRASYNQ_K1_FIRMWARE/`.

## 1. What sits between the microphone and the effects today

Thirteen stages change level. Four are automatic normalisers, three are gates, one is a guard with five actions. [FACT, `audio-forensics/source/CHAIN-MAP.md` stage table, each line re-read by the lead where marked *]

| # | Stage | What it does | Time scale | Why it exists (origin) | What it destroys |
|---|---|---|---|---|---|
| A | Fixed gain x8 x SENSITIVITY 2.7 (= x21.6, +26.7 dB) | Multiplies raw samples before analysis | static | * The Goertzel takes `sample >> 6` (`audio/k1_gdft_lane4_exact.h:24`): it throws away the bottom 6 bits. At room level the raw peak is about 270 counts, which would be 4 counts after the shift. The gain exists to survive that truncation. Inherited from Sensory Bridge's 32-bit maths (internal review R4, `docs/research/2026-09-02-sensorybridge-architecture-review.md`); K1 moved to 64-bit state but kept the shift. | Headroom: clipping now starts at raw 1,517 instead of 32,767 |
| B | Hard clamp at 16 bits | Clips | static | Exists because of A | Everything above the clamp |
| C | Loud-guard input trim (0.35-1.0) | Cuts input when samples near the clamp | 0.08 s down, 1.8 s up | Exists because of B | Level, in a limit cycle at high input (emulator fixture) |
| D | Waveform follower: peak divided by its own 2 s peak envelope = `peak_scaled` | Self-normalises the waveform level | 30 ms up, 2 s down | Sensory Bridge's auto-ranger. The original product had three "sweet spot" LEDs telling the user too quiet / in range / clipping, so a person closed the loop (internal review P3). K1 has no such indicator. | Any level difference slower than about 2 s. Every beat peaks at 1.0 in every section |
| E | Four-band AGC (bass, low-mid, high-mid, treble), target 0.25, gain 0.1-10 | Normalises each band to the same level | 26 ms up, 0.49 s down, gain 0.19 s | The "Cochlear AGC" structure of Sensory Bridge. Replaced on 20-21 May by one broadband gain (three bugs), which made "louder look dimmer" (Captain, 21 June); brought back per band on 30 June | Section dynamics and spectral balance. Measured bass gain 0.086 in music against 1.5-2.0 in quiet: quiet passages get about 20x (26 dB) more gain than loud ones [FACT telemetry, CHAIN-MAP section 5] |
| F | Loud guard, spectrum side: lowers the AGC target, lowers the AGC floor, subtracts a floor, squeezes the ceiling, unpins colour | Cuts the spectrum when `peak_scaled` is often >= 0.92 | 0.3 s down, 0.8 s up | Added 17-18 June, in the single-gain period, for loud rooms. Never removed when the four-band AGC returned | * Trigger reads stage D's output, which is level-free, so it fires on dense music at any volume (`audio/i2s_audio.h:246, 272-279`). Guard active in 89-97 % of music lines on the real unit; deepest cut 0.34 |
| G | Chromagram normaliser: divide by its own recent maximum | Self-normalises pitch-class energy | fast up, about 10 s down | Sensory Bridge | Absolute pitch-class strength |
| H | Chroma "sparseness gate": if the pitch profile is flat (flatness <= 0.08) the chromagram is set to zero | Gate | per frame | * `VP_FIX_CHROMAGRAM_SPARSENESS`, added to stop grey colour in chromatic modes (`visual/led_utilities.h:2668-2686`). Its own comment: "flatness<=0.08 fires on live dense music, device-proven 2026-07-02". The palette path was patched round it on 2 July (`K1_PALETTE_VIBRANCY_V1`); the effects that use chroma for motion and brightness were not | All pitch information during dense music |
| I | SSL subtraction and the silence classifier | Subtracts a calibrated floor; declares silence from RMS and crest | 5 s dwell | Sensory Bridge calibration, then six K1 patches (July-August) | * Latches "silence" during loud, low-crest music: 9 s of `silence=1` at `peak_scaled` 0.68-1.00 on the real unit. That resets onset and beat tracking (`audio/k1_onset_beat.cpp:257, 547`) [FACT, CHAIN-MAP section 4] |
| J | Noise calibration ritual | Learns the floors for I | manual | Sensory Bridge | Nothing by itself, but it must be done in confirmed silence; a poisoned calibration breaks I (the 281 -> 745 incident, 24 May) |

Other facts:
- [FACT] No stage carries "how loud is the music, compared with the last minute" to any effect. `K1AudioSnapshot` exports `peak_scaled`, `vu_level`, `novelty`, band energies, `chroma_strength`, spectrum and chroma (`audio/k1_audio_snapshot.h:65-91`): every one is taken after a normaliser.
- [FACT] Effect consumers: 9 effect files read `peak_scaled`, 10 read `chromagram_smooth` (post-gate), 11 read `vu_level`, 11 read novelty (31 `light_mode_*.cpp` files).
- [FACT] Mode 22 (Snapwave, the Captain's reference mode): position = oscillator built from chroma notes above 0.10, times the level envelope; brightness = 0.18 + 0.52 x chroma peak + 0.26 x level envelope + 0.20 x beat strength, and x0.35 when the chroma sum is zero (`effects/light_mode_snapwave.cpp:66-108`). So 52 % of its brightness and all of its motion depend on stage G/H, and 26 % on stage D.

## 2. Measured consequences

1. **The loudest chorus goes dark in mode 22, and this is NOT a front-end fault.** Emulator, firmware a6bad318, room level, Loreen 130.5-133.3 s: edge brightness 0.006 of full scale against 0.10 two seconds earlier, while the firmware's own level signal `peak_scaled` reads 0.82. [FACT] Two probes by the lead: loud guard off -> still dark (0.002); chroma gate H off (`vp_chroma_gate=false`, 3 cases accepted, 0 commands rejected) -> still dark (0.0069; `emu/analysis-gate/gate.md`). In the dark frames no pixel at all is lit. [INFERENCE] Mode 22 draws its dot only on the positive side of its own oscillator (`effects/light_mode_snapwave.cpp`: pixels below the half-way index are skipped), so a long negative swing shows nothing. This is a mode-22 matter for a separate look. The lead's first attribution of it to gate H was wrong and is withdrawn.
2. **Quiet looks brighter than loud.** Emulator, room level, 128-143 s: mean brightness in the loud chorus divided by the quiet section = 0.51 (mode 22), 0.51 (mode 18), 0.72 (mode 32) with the guard on; 0.45, 0.41, 0.61 with it off. [FACT, `emu/analysis/matrix.md`, re-run by the lead.] This is with the guard on or off, so the guard is not the cause.
3. **The guard squashes chorus hits at ordinary volume.** Final chorus, mode 22: guard off is 25 % brighter with 37 % more movement (`emu/analysis-tail/tail.md`). At a genuinely overloaded input (24 dB hotter) the guard helps: off is 18-50 % dimmer.
4. **Nothing clips in the room.** Raw peak <= 273 of 32,767; clamp point 1,517 after stage A. [FACT, bench.]
5. **Every beat peaks at full scale in every section.** Model of stage D on seven tracks, checked against the firmware trace (correlation 0.9999, mean error 0.005 over 2,000 frames): the 3 s average of `peak_scaled` dips in breakdowns only because the signal is sparser, and the peaks still reach 1.0 (`design/frontend-model.png`).

Against the Captain's Light-Show Law (ratified 6 Nov 2026): law 7 "loud and quiet look different; a drop looks like a drop" is violated by 2 and 5; "the silence flag never zeroes a live signal" by stage I's reset of beat tracking in loud music. Law 4 "never a gap" is broken in mode 22's loud chorus, by the mode itself (item 1).

## 3. The pattern (systems archetype)

"Fixes that fail" stacked on "shifting the burden". Level-control changes since the fork, each answering the symptom of an earlier one, with no stage ever removed except standby dimming:
15 Jun static noise subtraction disabled (it zeroed chroma) -> 17-18 Jun loud guard added and made default -> 18 Jun response gain 3.0 -> 1.0 (AGC floor-pin) -> 30 Jun four-band AGC back ("louder looks dimmer") -> 2 Jul palette vibrancy (chroma collapse from AGC + guard + gate H) -> 10 Jul guard release retune -> 10 Jul silence threshold rebuilt -> 5-13 Aug mic gain 8 -> 4 -> 8 and five silence-threshold commits -> 14 Aug sub-110 Hz filter for the level reference (never shipped) -> 14 Aug calibration partial commit (never shipped) -> 19 Aug AGC clock correction -> 4 Nov VU moved to the filtered band (never shipped). Source: `history/HISTORY-LEDGER.md` T1-T28.
[INFERENCE] About fourteen patches in five months. The fundamental solution (decide what the front end is for, measure level once, control it once) was never attempted. No requirement or design document for the front end exists in the repository; the 2 Sept internal review concludes "K1 kept every architectural decision of 4.1.1 ... nothing structural was removed".

## 4. Why a front end at all: the jobs physics actually sets

1. **Do not lose the signal numerically.** The microphone's own ceiling is its acoustic overload point (datasheet: to be confirmed by the engineering research note). If the arithmetic keeps full precision there is nothing to guard below that ceiling. Stages A, B, C and the input half of F exist only because of the `>> 6` truncation.
2. **Remove what is not music.** DC, rumble below the lowest displayed bin (110 Hz), and the self-noise floor.
3. **Exposure.** Rooms differ by tens of dB (quiet evening to loud venue); the plate has a fixed range. Something must place the music's window inside the plate's window. This is the one genuine need for automatic gain. It is the camera auto-exposure problem: it should move slowly, like the eye adapting to a room, so that everything faster (beats, sections) stays visible.
4. **Perceptual scaling.** Ear and eye are both compressive, so a fixed curve between sound level and light output. Fixed, not adaptive.
5. **Detectors need level-free input; brightness does not.** Onset, beat and pitch-class detection should work the same at any volume. That is a property of the detectors (ratios, logs, adaptive thresholds inside them), not a reason to normalise the signal that also sets how bright and how big the light is.

[INFERENCE] The present design fails because it uses one family of normalised signals for both questions, "what is happening" and "how much", and normalises on three time scales (0.03-0.5 s, 2 s, 10 s) that are all shorter than a musical section.

## 5. Candidate design: measure once, "what x how much", one slow exposure

1. **Capture with headroom.** Analyse the raw 16-bit samples at full precision (no `>> 6`, no x21.6, no clamp, no input trim).
2. **One loudness meter in absolute units** (dB, band-limited to what the plate can show): beat level (tens of ms), section level (about 3 s), programme anchor (slow).
3. **One exposure control, the only automatic gain in the system.** Slow anchor on section level: quick to follow when the room gets louder (seconds), slow to come back up (about a minute), frozen during silence, locks on at once when music starts, bounded. One user control, exposure compensation (the existing sensitivity setting).
4. **"What" stays level-free and fast**: the present 2 s beat signal, onset, beat phase, pitch class as a pure ratio. "How much" = section level relative to the anchor, through a fixed perceptual curve with a floor so the plate never empties. Effects multiply the two. A single exponent GAMMA sets how much section dynamics show: 0 reproduces today exactly, 1 makes light proportional to sound pressure relative to the anchor.
5. **Spectrum**: every bin divided by the same exposure gain (spectral balance kept), fixed frequency tilt, fixed soft ceiling. No per-band AGC.
6. **Pitch**: hue from the pitch-class ratio; "how tonal is it" carried as its own number; never gated to zero.
7. **Silence**: one absolute test (level under a floor for N seconds). It never zeroes a live signal and does not depend on crest.
8. **Removed**: loud guard, four-band AGC, chroma gate, noise-calibration ritual, the fixed gain and its clamp.
9. **Interface kept**: the same signal names reach the effects, plus one new "section intensity", so effects migrate one at a time and each change sits behind a build flag with a one-line revert.

Note the equivalence: for the waveform path, "today's beat signal x (section level / anchor)" equals "peak divided by a slow reference" instead of "peak divided by a 2 s reference". Today's follower already is an exposure control. It is simply about thirty times too fast.

## 6. Model of the candidate on real music

Script `design/model_frontend.py`, figure `design/frontend-model.png`, table `design/model.md`. Seven tracks from the fixture library (pop, dense EDM, steady groove, kick-and-drop, sparse breakdown, film song, big room), all scaled by one factor so Loreen matches the microphone level measured on the Main RPL, each at -10, 0 and +10 dB playback. The model of today's `peak_scaled` reproduces the firmware trace (r = 0.9999). Proposed = GAMMA 1, floor 0.25, anchor 4 s up / 60 s down. Parameters are starting values, not tuned.

| Measure (0 dB playback) | Today | Proposed model |
|---|---|---|
| Section tracking (r between 3 s drive and section loudness), range over 7 tracks | -0.54 to +0.79 | +0.47 to +0.87 |
| Contrast: drive in the loudest quarter / quietest quarter | 0.95 to 1.53 | 1.06 to 2.17 |
| Beat movement kept | 100 % | 88 to 97 % |
| Same result at -10 / 0 / +10 dB playback (Loreen contrast) | 1.28 / 1.17 / 1.16 | 1.79 / 1.68 / 1.66 |

Limits: this models the level signal handed to modes 22 and 32, not LED output; no microphone or room noise is modelled; seven tracks, mostly electronic; the spectrum and chroma paths (stages E, G, H) are not modelled. The dark chorus (section 2, item 1) is a mode-22 matter, outside the front end.

## 7. Red team of the candidate (strongest attacks first)

| Attack | Finding | Response |
|---|---|---|
| The 2 s self-normalisation is part of the look the Captain approved (Snapwave is his reference) | True. Removing it would change the approved look | Keep it unchanged as the "what" signal; add "how much" on top; GAMMA 0 = today |
| A slow exposure is wrong for the first seconds and after a volume change | True for a symmetric slow tracker | Instant lock-on at first music, fast when louder, slow when quieter, bounded |
| Quiet evenings will look dead | Model: results at -10 dB playback equal those at 0 and +10 dB, because the anchor follows the room. Floor 0.25 keeps breakdowns alive | Needs the Captain's eye on real quiet listening |
| Absolute calibration is not known | The raw-count to dB SPL mapping through the ESP32 PDM path is unverified. Quiet-room raw RMS is 13-19 counts, far above what the datasheet noise would give; cause unknown (real room noise, sub-110 Hz drift, or path gain) | Exposure is relative, so only the silence floor needs an absolute number: one measurement with a sound-level meter beside the unit |
| One wideband gain lets bass dominate the spectrum display (the reason the four-band AGC came back) | The 21 June failure was a fast single gain collapsing on hits | A slow gain does not collapse on hits; spectral range is handled by a fixed tilt and fixed log curve, as analysers do. Must be shown, not assumed |
| Effects were tuned on normalised signals | True for all 22 enabled modes | Migrate modes 22 and 32 first; leave the rest on today's signals until each is re-tuned |
| It is a rewrite that slips the release | Real risk | Staged, each stage behind a flag, each judged by the same emulator metrics and the Captain's four questions before the next starts |
| The lead reversed its own recommendation within an hour ("retarget the guard") | True | The earlier answer was to a narrower question. It remains a valid stop-gap (mode 22 final chorus +25 %) but leaves consequences 1 and 2 untouched |

## 8. Pre-mortem: "it is February and the redesign failed. Why?"

| Failure | Guard against it |
|---|---|
| New controllers were added and none removed: now eight instead of seven | Rule: each stage must delete a stage; the count of adaptive stages is a tracked number |
| Judged by eye only, argued for weeks | Objective acceptance numbers first (section tracking, contrast, movement kept, room-level invariance), measured in the emulator on many tracks at three room levels; then the Captain's four questions on the plate |
| Tuned on one track again | At least seven tracks of different genres, never one |
| Emulator fed at the wrong level again (the old fixture is 24 dB hotter than the room) | Room-level fixtures (peak 250 raw) are now in `emu/`; every result states its input level |
| A hidden consumer of an old signal broke (tempo, onset, director, palette) | Interface names kept; the 22-case live regression must show which cases changed and why |
| Quiet passages looked dead, or the first minute after a volume change looked wrong | Floor, fast lock-on, asymmetric anchor; a specific bench test for "volume turned down by 10 dB mid-song" |
| The release slipped because all 22 modes needed re-tuning | Only modes 22 and 32 migrate before release; the rest keep today's signals |

## 9. What kind of problem this is (Cynefin)

- The signal physics (range, clipping, truncation, which stage destroys what) is **complicated**: analysable, and analysed above.
- Whether the picture then looks right to a person is **complex**: only visible after trying. So: probe, sense, respond. Small flag-gated probes in the emulator and on the bench, the Captain's eye as the sensor, keep or revert.
- [INFERENCE] The past five months treated a complex perceptual problem as a string of clear ones ("add a guard", "retune the release").

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (K1-FE-SHOW lead, session 3) | Created. |
