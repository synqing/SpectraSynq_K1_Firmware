# Measure once, expose slowly: rebuilding K1's front end

**Short answer: no, today's front end is not the right design for a music-to-light instrument.** It has thirteen stages that change level. Four of them are automatic normalisers, each working over 0.03 to 10 seconds. A musical section lasts longer than that. So every section, quiet or loud, gets pushed to the same level. In the emulator the loud chorus comes out at about half the brightness of the quiet section before it (ratio 0.51 in modes 22 and 18). Every beat hits full scale in every section. Most of these stages were not designed for the K1. They were added one at a time, each to fix a side effect of the one before: about fourteen patches in five months, with none ever removed. The front end was thought necessary for three reasons. First, an inherited maths shortcut throws away the bottom 6 bits of every sample, so a fixed gain was added to survive it, then a clamp, then a guard for the clamp. Second, Sensory Bridge had a person watching three "sweet spot" lights and adjusting the input; the K1 has no such lights, so automatic stages stood in for the person. Third, each later patch answered a symptom. Physics only asks for one automatic control: a slow "exposure" that fits the room's loudness to the plate's fixed range, much as a camera adjusts to a room. The research points to that design: full-precision capture; one loudness meter in decibels; one slow, gated exposure gain; a fixed loudness-to-brightness curve; and level-free detectors that live inside the detectors, not in the shared signal. This design is still a candidate. Its level path has been modelled on seven tracks and gives better results. Its spectrum and pitch paths are untested. Whether it looks right can only be settled by staged probes and the Captain's eye.

Labels used: [FACT] read in source, a capture, telemetry or a cited document; [INFERENCE] derived; [HYPOTHESIS] untested. Internal facts come from the lead's analysis of firmware a6bad318 (`system_first_principles.md`). External facts carry links.

## Thirteen stages, four normalisers, none designed for the job

### Why a front end was built at all

- **[FACT] The Goertzel analysis drops the bottom 6 bits of every sample** (`sample >> 6`, `audio/k1_gdft_lane4_exact.h:24`). A room-level peak of about 270 counts would be about 4 counts after the shift. The fixed gain of x21.6 exists to survive that loss. The shift comes from Sensory Bridge's 32-bit maths. The K1 moved to 64-bit state but kept the shift (lead analysis §1, stage A).
- **[FACT] Sensory Bridge relied on a person.** Its three "sweet spot" LEDs told the user when the input was "too quietly for the auto-ranger to account for, or if it's too loud" ([Sensory Bridge README](https://github.com/connornishijima/SensoryBridge/blob/main/README.md)). The K1 has no such indicator (lead analysis §1, stage D).
- **[FACT] Most later stages were patches for the side effects of earlier ones.** Static noise subtraction was disabled on 15 June because it zeroed chroma. The loud guard was added on 17–18 June. Response gain went from 3.0 to 1.0 on 18 June. The four-band AGC came back on 30 June after the single gain made "louder look dimmer". Palette vibrancy was added on 2 July. Silence thresholds were retuned in July and August. Microphone gain went 8 → 4 → 8 (lead analysis §3, `history/HISTORY-LEDGER.md` T1–T28).
- **[INFERENCE] This is the "fixes that fail" pattern.** No requirement or design document for the front end exists. The 2 September internal review concluded "nothing structural was removed" (lead analysis §3).

### What each stage does, why it exists, and what it destroys

| # | Stage | Why it exists | What it destroys |
|---|---|---|---|
| A | Fixed gain x21.6 (+26.7 dB) | Survive the `>> 6` truncation | Headroom: clipping starts at raw 1,517 instead of 32,767 |
| B | Hard clamp at 16 bits | Needed only because of A | Everything above the clamp |
| C | Loud-guard input trim (0.35–1.0) | Needed only because of B | Level. It cycles up and down at high input |
| D | Waveform follower: peak divided by its own 2 s peak | Auto-ranger (see conflict 1 below) | Any level change slower than about 2 s. Every beat peaks at 1.0 in every section |
| E | Four-band AGC, target 0.25, gain 0.1–10 | Added back on 30 June because "louder looks dimmer" | Section dynamics and spectral balance. Quiet passages get about 20x (26 dB) more gain than loud ones |
| F | Loud guard, spectrum side | Added 17–18 June for loud rooms. Never removed when E returned | It triggers on D's output, which carries no level. So it fires on dense music at any volume: active in 89–97 % of music lines on the real unit, deepest cut 0.34 |
| G | Chromagram divided by its own recent maximum (about 10 s fall) | Sensory Bridge | How strong each pitch class really is |
| H | Chroma "sparseness gate": zero the chromagram when the pitch profile is flat | Added to stop grey colour in chromatic modes | All pitch information during dense music. Its own code comment says it "fires on live dense music" |
| I | Floor subtraction plus silence classifier (RMS and crest, 5 s dwell) | Sensory Bridge calibration plus six K1 patches | It holds "silence" during loud, steady music (9 s of `silence=1` at `peak_scaled` 0.68–1.00). That resets onset and beat tracking |
| J | Noise calibration ritual | Sensory Bridge | Nothing by itself. But calibration done with music playing breaks I (the 281 → 745 incident, 24 May) |

All entries are [FACT] from the lead's stage table (lead analysis §1), which was re-checked against source where marked there.

- **[FACT] No signal tells any effect how loud the music is now, compared with the last minute.** Every value the effects receive (`peak_scaled`, `vu_level`, novelty, band energies, `chroma_strength`, spectrum, chroma) is taken after a normaliser (`audio/k1_audio_snapshot.h:65-91`).
- **[FACT] Mode 22 (Snapwave, the Captain's reference mode) depends on these stages.** 52 % of its brightness and all of its motion come from stages G and H. Another 26 % of its brightness comes from stage D (`effects/light_mode_snapwave.cpp:66-108`).

### Two conflicts in the record, left open

**Conflict 1: where stages D, E and F came from.**
- Firmware comments and internal records call the four-band AGC a "Cochlear AGC" structure from Sensory Bridge, from before the fork (lead analysis §1, stage E).
- The prior-art search found **no multi-band AGC and no loud guard in any upstream Sensory Bridge release from 1.0.0 to 4.1.1**. A regex scan for `agc`, `cochlear`, `auto gain` and `loud guard` at every release tag returned nothing ([SensoryBridge tags](https://github.com/connornishijima/SensoryBridge/tags)).
- **Upstream also does not use the waveform peak follower for output.** In 4.1.1 the only consumer of `waveform_peak_scaled` is a commented-out line ([lightshow_modes.h L165](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/lightshow_modes.h#L165)). The auto-ranger that actually drove upstream output was a single wideband spectrogram follower: 1.5 s to rise, 3 s to fall ([GDFT.h L169-L198](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L169-L198)).
- **Conclusion:** stages D (as a normaliser feeding output), E and F come from the K1 fork line. Where inside that line they started is not verified.

**Conflict 2: the microphone's clock mode.**
- The engineering note assumes the default PDM clock mode (`DSR_8S`). At 12.8 kHz that gives 819.2 kHz, the microphone's low-power mode: SNR 64 dB(A), noise floor about 29 dB(A) SPL ([ESP-IDF I2S guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/i2s.html); [IM69D130 datasheet](https://www.infineon.cn/content/dam/infineon/row/public/documents/24/49/infineon-im69d130-datasheet-en.pdf)).
- The lead's reading of the Main RPL build is that it sets `DSR_16S` for this microphone. That gives 1.6384 MHz: SNR 66 dB(A), about 28 dB(A) SPL. This reading was given in the brief for this report, not in the notes files.
- **Either way, sensitivity and overload point stay the same.** The datasheet gives −36 dBFS at 94 dB SPL and an overload point of 130 dB SPL in every mode. The clock mode moves the noise floor by 1–4 dB and never moves the clipping point.

## Quiet sections outshine loud ones because normalisers run faster than music

### What the measurements show

1. **Quiet looks brighter than loud.** [FACT] Emulator at room level, 128–143 s of the Loreen track. Brightness in the loud chorus divided by brightness in the quiet section:
   - guard on: 0.51 (mode 22), 0.51 (mode 18), 0.72 (mode 32);
   - guard off: 0.45, 0.41 and 0.61.

   The guard is therefore not the cause (`emu/analysis/matrix.md`).
2. **Every beat peaks at full scale in every section.** [FACT] A model of stage D matches the firmware trace (correlation 0.9999 over 2,000 frames). The 3 s average dips in breakdowns only because the music is sparser there; the peaks still reach 1.0 (lead analysis §2).
3. **The guard squashes chorus hits at ordinary volume.** [FACT] Final chorus, mode 22: with the guard off it is 25 % brighter and has 37 % more movement. At an input 24 dB hotter than the room, the guard helps: turning it off makes the picture 18–50 % dimmer.
4. **Nothing clips in the room.** [FACT] Raw peak is at most 273 of 32,767 on the bench.
5. **The dark chorus in mode 22 is NOT a front-end fault.** [FACT] At 130.5–133.3 s, edge brightness falls to 0.006 while `peak_scaled` reads 0.82. The lead ran two probes:
   - loud guard off: still dark (0.002);
   - chroma gate H off: still dark (0.0069, `emu/analysis-gate/gate.md`).

   [INFERENCE] Mode 22 draws its dot only on the positive side of its own oscillator, so a long negative swing shows nothing. The lead's first claim that gate H caused this was tested and withdrawn. This needs a separate look at mode 22.

Against the Captain's Light-Show Law (ratified 6 November 2026):
- Items 1 and 2 break law 7, "loud and quiet look different; a drop looks like a drop".
- Stage I breaks "the silence flag never zeroes a live signal".
- Mode 22 itself, not the front end, breaks law 4, "never a gap" (lead analysis §2).

### Why the physics says these stages are unnecessary

- **[FACT] The microphone does not clip in any real venue.** Digital full scale sits at about 130 dB SPL. Distortion stays below 1 % up to 128 dB SPL ([IM69D130 datasheet](https://www.infineon.cn/content/dam/infineon/row/public/documents/24/49/infineon-im69d130-datasheet-en.pdf)). Measured club averages are 82–106 dB LAeq, with a mean of 96 ([Frontiers in Psychology 2019](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00607/full)).
- **[INFERENCE] Plain 16-bit samples already cover the microphone's useful range.** A 16-bit word has a floor of about −98 dBFS, roughly 32 dB SPL. The microphone's own floor is 25–29 dB(A) SPL, so very little is lost. The x21.6 multiply adds no information: it scales the noise and the step size by the same amount. **It is the only thing in the chain that clips.** It clips at raw 1,517, a sine peak of about 103 dB SPL. For music with typical peaks, that means clipping starts at about 83–93 dB SPL average level: a loud party or a club. This is the "24 dB hotter" case where the guard helps. The guard is repairing damage done by the gain.
- **[FACT] The ESP32-S3 driver has no hardware high-pass filter.** That feature exists on the ESP32-P4 only ([esp32s3 soc_caps.h](https://github.com/espressif/esp-idf/blob/master/components/soc/esp32s3/include/soc/soc_caps.h)). So DC and rumble must be removed in software. If they are not, they can drive any wideband peak detector.

### Why the ear does not justify a "cochlear AGC"

- **[FACT] The cochlea's main level processor is a fixed, instant squeezing curve, not a gain that adapts over time.** Near its best frequency it gives about 0.2–0.3 dB of output per dB of input, squeezing a 120 dB range into 30–40 dB ([Robles & Ruggero 2001](https://pmc.ncbi.nlm.nih.gov/articles/PMC3590856)). Level differences are compressed, never removed.
- **[FACT] The ear's real slow gain controls are partial.** The auditory nerve shifts its range by only 0.05–0.47 dB per dB of mean-level change, "never 1 dB/dB" ([Wen et al. 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2774902)). The midbrain adapts in about 160 ms when sound gets louder and about 330 ms when it gets quieter ([Dean et al. 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC6670892)).
- **[INFERENCE] A front end that divides the signal by its own recent peak (1 dB per dB) removes more level information than the ear does.** "The loud chorus is no brighter than the quiet verse" is the expected result of such a chain. It contradicts what listeners hear.
- **[INFERENCE] Engineered "auditory" front ends are recognition tools.** They make level disappear on purpose. PCEN at its defaults removes about 98 % of a sustained level change within a few hundred milliseconds. It "discard[s] … slow changes in loudness" ([Lostanlen et al. 2019](https://www.justinsalamon.com/uploads/4/3/9/4/4394963/lostanlen_pcen_spl2018.pdf)). **The K1's four-band AGC, with its fixed target of 0.25 per band, behaves like a crude, full-strength version of PCEN with few bands.** Flattening is what it is designed to do. It is not a tuning fault.

## What the front end must actually do: five jobs, one automatic gain

The lead's analysis and the external research agree on the following jobs.

1. **Do not lose the signal in the arithmetic.** Keep full precision from the 16-bit samples onwards. Then nothing needs guarding below the microphone's own ceiling. Stages A, B, C and the input half of F exist only because of the truncation (lead analysis §4).
2. **Remove what is not music.** Remove DC, rumble below the lowest displayed frequency band (110 Hz), and the noise floor. This must be done in software on the ESP32-S3.
3. **Exposure: the one real need for automatic gain.** Room levels vary by about 50 dB, from a quiet home at about 55 dB SPL to the loudest measured club averages at about 106 dB SPL [INFERENCE from cited venue data]. The plate has a fixed range. Something must fit the music's range inside the plate's range. That something should move slowly, like the eye adjusting to a room.
4. **A fixed loudness-to-brightness curve.** Ear and eye both compress. So the link between them is a fixed curve, not an adaptive one.
5. **Level-free detectors, without a level-free brightness signal.** Onset, beat and pitch-class detection should work the same at any volume. That is achieved inside the detectors (ratios, logarithms, adaptive thresholds). It is not a reason to normalise the signal that also sets brightness and size (lead analysis §4).

**[INFERENCE] The core design fault:** one family of normalised signals answers two different questions, "what is happening" and "how much". It normalises on three time scales (0.03–0.5 s, 2 s, 10 s), all shorter than a musical section.

### The time scales the research says to keep

| Time scale | Musical meaning | Keep or discount | Evidence |
|---|---|---|---|
| 1–50 ms | Attack, onset | Keep | Loudness models use about 22 ms attack and 50 ms release per note ([Moore et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5318944)) |
| 50 ms–1 s | Beat and accent | Keep | Music's loudness rises and falls most strongly at about 2 beats per second (2 Hz) ([Ding et al. 2017](https://read.qxmd.com/read/28212857/temporal-modulations-in-speech-and-music)) |
| 2–60 s | Phrase and section (verse/chorus, breakdown/drop) | Keep | Pop, rock and EDM have about 3–10 LU of loudness range, measured on 3 s blocks; classical about 20 LU ([EBU Tech 3342](https://tech.ebu.ch/docs/tech/tech3342.pdf); [Production Expert](https://www.production-expert.com/home-page/2017/12/14/tutorial-in-music-mastering-what-is-loudness-range?format=amp)) |
| Minutes | Room volume, track mastering level | Discount | Broadcast normalises only the whole-programme loudness ([EBU R 128](https://tech.ebu.ch/docs/r/r128.pdf)) |

- **[INFERENCE] A section that is 3–10 dB louder sounds about 1.2 to 2 times as loud.** People hear level differences of about 1 dB, so this contrast is clearly audible. Absolute loudness, by contrast, can be judged in only about 7 categories ([Luce, Green & Weber 1976](https://link.springer.com/article/10.3758/BF03198705)). So the light should keep relative contrast accurate and may treat absolute level as a rough cue.

## Prior art has never shown drop-brighter-than-breakdown working unattended

- **[FACT] Most hobby systems divide by a recent peak that falls in 1–3 s, using one gain for all bands.** Examples: Sensory Bridge (1.5 s up, 3 s down), Emotiscope (about 1 s each way), LedFx (about 1.7 s release) and WLED "Vivid" (1.3 s peak decay) ([GDFT.h](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/GDFT.h#L169-L198); [Emotiscope goertzel.h](https://github.com/connornishijima/Emotiscope/blob/main/src/goertzel.h#L311-L333); [WLED audio_reactive.cpp](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L192-L204)). [INFERENCE] Any section longer than a few of those fall times is rescaled to full range. So a 30 s breakdown ends up as bright as the drop.
- **[FACT] No prior-art system puts more than one automatic gain in series on the same path.** WLED uses one wideband gain plus a separate speed limiter on volume only. Its automatic gain is off by default ([WLED readme](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/readme.md)).
- **[FACT] FastLED's port of WLED's gain control states the design aim the K1 needs:** it "adapts to source-level differences (MEMS mic vs line-in) rather than musical dynamics, avoiding cross-band coupling that plagues fast-tracking AGC designs" ([FastLED auto_gain.h](https://github.com/FastLED/FastLED/blob/master/src/fl/audio/auto_gain.h#L20-L25)).
- **[FACT] Per-band normalisation is rare.** MilkDrop divides each of three bands by its own roughly 4 s average, but uses the result for motion, not brightness ([projectM Loudness.cpp](https://github.com/projectM-visualizer/projectm/blob/master/src/libprojectM/Audio/Loudness.cpp)). WLED and LedFx balance bass against treble with a **fixed** tilt table or filter ([WLED L223](https://github.com/wled/WLED/blob/main/usermods/audioreactive_v1/audio_reactive.cpp#L223); [LedFx audio.py](https://github.com/LedFx/LedFx/blob/main/ledfx/effects/audio.py#L731-L743)).
- **[FACT] Professional tools have no automatic gain.** Resolume, grandMA and TouchDesigner give a manual gain plus a separate "fall" control ([Resolume](https://resolume.com/support/en/6/parameter-animation); [grandMA3](https://help.malighting.com/grandMA3/2.2/HTML/sound_viewer.html)).
- **[FACT] Long-memory examples exist only as minority options.** Sensory Bridge's VU-dot mode rises fast and falls over roughly a minute (inferred from the code) ([lightshow_modes.h L189-L197](https://github.com/connornishijima/SensoryBridge/blob/main/SENSORY_BRIDGE_FIRMWARE/lightshow_modes.h#L189-L197)). WLED "Lazy" has a 6.7 s peak fall and a 16 s slow follow, and its docs recommend it for "music with wide dynamic range" ([kno.wled.ge](https://kno.wled.ge/advanced/audio-reactive/)).
- **[INFERENCE] No reviewed system verifiably keeps section dynamics while running unattended across room volumes.** No published measurement of brightness against section loudness on real music was found for any of them. The K1 would be first, which also means there is no proven recipe to copy.

Adjacent fields reach the same pattern:
- **Hearing aids** use a dual loop. "Normally, the operation of the system is determined by the slow-acting control signal." A fast path acts only when the level jumps more than 8 dB above the running level, then hands back. A hold-off stops the gain rising when the input drops ([Moore 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC4111434/)). One aid design (ADRO) lets the gain fall at about 9 dB/s but rise at only about 3 dB/s. This stops gain rising in brief pauses, which would cause "pumping".
- **Broadcast processors** slow the gain change, then freeze it, as the programme gets quiet. A slow "return to zero" drift stops the gain getting stuck at a bad value ([Omnia](https://www.manualslib.com/manual/849874/Omnia-Omnia-9.html?page=49); [Telos Volt](https://docs.telosalliance.com/docs/adjusting-the-volts-wideband-agc-gating)).
- **Fast multi-band compression flattens the spectrum** ([Moore 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC4111434/)).
- **Cameras** provide exposure compensation that still works while exposure is locked ([Android Camera2](https://developer.android.com/reference/android/hardware/camera2/CaptureResult#CONTROL_AE_EXPOSURE_COMPENSATION)). One tone curve for the whole image keeps the order of brightness; local curves do not ([Reinhard et al. 2002](https://www.cs.utah.edu/docs/techreports/2002/pdf/UUCS-02-001.pdf)).

## The candidate: separate "what" from "how much", with one slow exposure

### The design (lead analysis §5)

1. **Capture with headroom.** Analyse the raw 16-bit samples at full precision. Remove the `>> 6` shift, the x21.6 gain, the clamp and the input trim.
2. **One loudness meter, in decibels,** limited to the frequencies the plate can show. It gives three readings:
   - beat level (tens of milliseconds);
   - section level (about 3 s);
   - a slow programme anchor.
3. **One exposure control: the only automatic gain in the system.** It follows the anchor:
   - quick to follow when the room gets louder;
   - slow to come back up when the room gets quieter;
   - frozen during silence;
   - locks on at once when music starts;
   - kept within fixed limits.

   The user control is exposure compensation, using the existing sensitivity setting.
4. **"What" stays level-free and fast.** That means today's 2 s beat signal, onset, beat phase, and pitch class as a pure ratio. **"How much"** is section level relative to the anchor, passed through a fixed curve with a floor. Effects multiply the two. The exponent GAMMA sets how much section contrast shows: **GAMMA 0 reproduces today exactly**, and GAMMA 1 makes the light follow sound pressure relative to the anchor.
5. **Spectrum.** Every frequency bin is divided by the same exposure gain. Add a fixed frequency tilt and a fixed soft ceiling. No per-band AGC.
6. **Pitch.** Hue comes from the pitch-class ratio. "How tonal is it" is its own number. Pitch is never gated to zero.
7. **Silence.** One absolute test: level below a floor for N seconds. It never zeroes a live signal and does not use crest.
8. **Removed:** the loud guard, the four-band AGC, the chroma gate, the calibration ritual, and the fixed gain with its clamp.
9. **Interface kept.** The effects receive the same signal names, plus one new "section intensity". Each change sits behind a build flag with a one-line revert.

**[INFERENCE] Today's follower already is an exposure control, but about thirty times too fast.** "Today's beat signal × (section level / anchor)" equals "peak divided by a slow reference" instead of "peak divided by a 2 s reference".

### What the model shows, and what it does not

[FACT] The lead modelled seven fixture tracks, each played at −10, 0 and +10 dB. The tracks covered pop, dense EDM, steady groove, kick-and-drop, sparse breakdown, film song and big room. Settings: GAMMA 1, floor 0.25, anchor 4 s up / 60 s down (`design/model.md`).

| Measure (0 dB playback) | Today | Candidate model |
|---|---|---|
| Section tracking (correlation of 3 s drive with section loudness), range across 7 tracks | −0.54 to +0.79 | +0.47 to +0.87 |
| Contrast: drive in loudest quarter divided by quietest quarter | 0.95 to 1.53 | 1.06 to 2.17 |
| Beat movement kept | 100 % | 88 to 97 % |
| Loreen contrast at −10 / 0 / +10 dB playback | 1.28 / 1.17 / 1.16 | 1.79 / 1.68 / 1.66 |

What the model does **not** cover:
- It models the level signal handed to modes 22 and 32, not LED output.
- It includes no microphone noise and no room noise.
- Most of the seven tracks are electronic music.
- **The spectrum and pitch paths (replacing stages E, G and H) are not modelled at all.**
- The parameters are starting values, not tuned.

**So the candidate is promising on its level path and unproven everywhere else.**

### Parameters: what the research supports, constrains, or leaves open

| Parameter | What the research says | Status |
|---|---|---|
| Analysis precision | 16-bit samples, 32-bit integer or float maths, no clamp. The 16-bit floor is within 3–7 dB of the microphone's floor | Supported. Equivalence must still be shown by probe |
| Rumble and DC removal | Must be software. Cut-off below the 110 Hz lowest displayed band | Needed. Cut-off value open |
| Meter domain | Decibels (logarithmic). Broadcast meters and camera "log-average" metering work this way | Supported |
| Meter windows | Note scale about 22 ms rise / 50 ms fall; section scale 3 s (EBU short-term); programme scale slow | Supported |
| Anchor fall rate (room gets quieter) | Keep contrast up to about a minute. The model used 60 s. WLED's 16 s still partly re-brightens 30 s breakdowns | Constrained to tens of seconds up to about a minute. Exact value open |
| Anchor rise rate (room gets louder) | The model used 4 s. Hearing aids let the slow loop govern and use a fast path only beyond about 8 dB of excess | **Open, and the key tension** (see red team) |
| Deadband (no gain change for small deviations) | Camera stability region. [INFERENCE] To keep pop and EDM section contrast, it would need to be about as wide as their 3–10 LU range | Width open |
| Gain rise speed limit | ADRO precedent: about 3 dB/s up against 9 dB/s down | Precedent only. Value open |
| Gain hold in pauses | Freeze in silence. Hold-off when the input drops. Slow "return to zero" drift so the gain cannot get stuck | Supported. Durations open |
| Lock-on at first music | Instant | From the lead's red team. No external value |
| Gain limits | WLED uses −36 to +30 dB. Room span is about 50 dB | Limits open |
| Loudness-to-brightness slope (GAMMA) | To make "twice as loud" look "twice as bright", luminance should rise 0.9–1.0 dB per dB of sound for a large glowing surface, or 0.6–0.67 dB per dB for a point of light ([Stevens's power law](https://en.wikipedia.org/wiki/Stevens%27s_power_law); [Stevens & Marks 1965](https://pmc.ncbi.nlm.nih.gov/articles/PMC219679)). The plate is probably the large-surface case [INFERENCE] | See note below. Open until measured at the LEDs |
| Plate range | A linear 8-bit range is about 24 dB of luminance. At about 1 dB per dB it can show only 24–27 dB of sound range | Constraint. Section contrast of 3–10 dB fits; quiet-to-club room range does not, which is why exposure is needed |
| Floor | 0.25 in the model, so breakdowns never go empty | Starting value. Open |
| Fast protection path | Optional on a light instrument, since there is no hearing risk. A soft ceiling may replace it | Open |
| Spectrum tilt | Fixed tilt, as in WLED's table and LedFx's filter | Values open. **Untested** |
| Pitch "tonalness" number | Replaces gate H | **Untested** |
| User control | Exposure compensation in dB, which still works while exposure is frozen | Supported. Step size open |

**[INFERENCE] Note on GAMMA.** GAMMA 1 means light follows sound *pressure*. If the drive maps straight onto LED duty, that is only 0.5 dB of light per dB of sound. That is below the 0.6–1.0 the research supports. So the model's contrast numbers are on the cautious side, and GAMMA may need to be about 1.2–2.0. But any brightness curves inside the effects or the LED output change the overall slope. **The real slope must be measured on the LED output, not set from the table.** The model's "contrast 2.17" is a drive ratio, not a brightness ratio, so it cannot be compared directly with the perception figures.

## Red team and pre-mortem: where the candidate could fail

### Strongest attacks first

| Attack | Finding | Response |
|---|---|---|
| The 2 s self-normalisation is part of the look the Captain approved (Snapwave is his reference) | True | Keep it unchanged as the "what" signal and add "how much" on top. GAMMA 0 = today |
| **A fast-rising anchor eats the drop** [new, from the research] | With a 4 s rise, a drop that is 6–10 dB louder looks brighter only for its first few seconds; then the anchor catches up. That keeps the dynamics this design exists to show for only a few seconds | Open. Options: a deadband as wide as typical section contrast; a rise speed limit; or the hearing-aid rule (slow loop governs, fast path only beyond about 8 dB, then hand back). Must be probed on drop tracks |
| A slow exposure is wrong for the first seconds and after a volume change | True for a slow tracker that moves at the same speed both ways | Instant lock-on at first music, quick when louder, slow when quieter, within limits. Plus a bench test: volume down 10 dB mid-song |
| Quiet evenings will look dead | The model gives the same results at −10, 0 and +10 dB playback, because the anchor follows the room. Floor 0.25 keeps breakdowns alive | Needs the Captain's eye during real quiet listening |
| Absolute calibration is not known | Raw-count to dB SPL through the ESP32 path is unverified. Quiet-room RMS reads 13–19 counts, far above the datasheet noise. [INFERENCE] If the path had unity gain, that would mean a "quiet" room at about 65–68 dB SPL, which is implausible. So either the assumption or the room reading is wrong | Exposure is relative, so only the silence floor needs an absolute number: one sound-level-meter reading beside the unit |
| One wideband gain lets bass dominate the spectrum (why the four-band AGC came back) | The 21 June failure was a *fast* single gain collapsing on drum hits. A slow gain does not collapse on hits | Fixed tilt and fixed logarithmic curve, as analysers use. **Must be shown, not assumed** |
| Full precision changes the scale of everything downstream [new] | [INFERENCE] Today's net scale is x21.6 then `>> 6`, about x0.34. Full precision is x1, about 9 dB higher. Any fixed threshold (silence floors, calibration values) shifts by that much | The stage 1 check compares outputs at matched scale |
| Lab science may not transfer [new] | Brightness exponents were measured on dark-adapted lab targets. The plate sits in lit rooms. No published study of loudness-to-brightness mapping for a light show was found | Treat the exponents as a starting range. Judge by eye |
| Effects were tuned on normalised signals | True for all 22 enabled modes | Migrate modes 22 and 32 first. Leave the rest on today's signals until each is re-tuned |
| A rewrite slips the release | Real risk | Staged probes, each behind a flag, each judged by the same metrics |
| The lead reversed its own advice within an hour ("retarget the guard") | True | That answer was to a narrower question. It remains a valid stop-gap (+25 % final chorus in mode 22) but leaves the "quiet looks brighter than loud" and "every beat at full scale" problems untouched |

### Pre-mortem: "it is February and the redesign failed"

| Failure | Guard against it |
|---|---|
| New controllers added, none removed | Every stage must delete a stage. The number of adaptive stages is tracked |
| Judged by eye only, argued about for weeks | Objective numbers first (section tracking, contrast, movement kept, same result at any room level). Then the Captain's four questions on the plate |
| Tuned on one track again | At least seven tracks of different genres |
| Emulator fed at the wrong level again (the old fixture is 24 dB hotter than the room) | Room-level fixtures (peak about 250 raw) now exist in `emu/`. Every result states its input level |
| A hidden user of an old signal broke (tempo, onset, director, palette) | Keep the interface names. The 22-case live regression must show which cases changed and why |
| Quiet passages looked dead, or the first minute after a volume change looked wrong | Floor, fast lock-on, asymmetric anchor, and the 10 dB volume-drop bench test |
| The release slipped because all 22 modes needed re-tuning | Only modes 22 and 32 migrate first |

## A staged probe plan in which every stage deletes a stage

**Cynefin framing (lead analysis §9):** the signal physics can be worked out by analysis. Whether the light then looks right can only be found by trying it. So: probe, sense, respond.

**Same yardstick for every stage:**
- emulator metrics on at least seven tracks, at −10, 0 and +10 dB, plus the +24 dB overload fixture;
- the 22-case live regression;
- then the Captain's four questions on the plate.

Each stage has its own build flag and a one-line revert. **The count of adaptive stages must fall or stay level at every step.**

| Stage | Deletes | Replaces it with | Pass test (beyond the common yardstick) |
|---|---|---|---|
| 1 | A, B, C (fixed gain, clamp, input trim) | Full-precision analysis of the raw 16-bit samples | Matches today's output at room level once scale is matched. No clipping on the +24 dB fixture. The input half of the guard has nothing left to do |
| 2 | F (loud guard, spectrum side) | Nothing | Final chorus at least as lively as guard-off today (+25 % brightness, +37 % movement in mode 22). **Re-check the +24 dB fixture**, where the guard used to help. After stage 1 that overload should no longer exist |
| 3 | E (four-band AGC) | The single slow exposure gain (the only automatic gain), fixed tilt, fixed log curve, soft ceiling. Freeze in silence, return-to-zero drift | Spectral balance survives. Bass does not take over. No collapse on drum hits. 10 dB volume-drop test |
| 4 | D as the brightness reference in modes 22 and 32 (it stays as the "what" signal) | "Section intensity" from the stage 3 anchor, through the fixed curve and floor. GAMMA steps from 0 upwards | GAMMA 0 reproduces today (control). Contrast and section tracking improve with beat movement mostly kept. **Measure the light-per-sound slope on the LED output.** Probe the anchor rise rate and deadband on drop tracks |
| 5 | H (chroma sparseness gate) | A separate "tonalness" number. Pitch never zeroed | Dense music keeps pitch-driven motion and brightness in the chroma-driven effects. No grey-colour regression in chromatic modes. (This does not fix mode 22's dark chorus, which is a mode matter) |
| 6 | G (chromagram self-normaliser) | Pitch-class ratio | Hue stable across sections. Strength carried by tonalness and section intensity |
| 7 | I and J (crest-based silence classifier, calibration ritual) | One absolute silence test from the exposure meter: level below a floor for N seconds | No `silence=1` during loud steady music. Beat tracking never reset by live music. Needs one sound-level-meter reading beside the unit for the floor |

## What is still not known

- **The ESP32-S3 path gain** from microphone full scale to 16-bit full scale (unity is assumed, not verified). Also why the quiet-room RMS is so high.
- **Which PDM clock mode the shipping build really runs** (conflict 2). This affects only the noise floor.
- **Where the K1's four-band AGC, loud guard and the use of the waveform follower as a normaliser started** inside the fork line (conflict 1).
- **The actual light-per-sound slope at the LEDs**, after the effects' own curves. Also whether the plate behaves as a large glowing surface or as a point of light for viewers in a lit room.
- **The anchor's rise rate, fall rate, deadband, limits, floor and hold times.** The research bounds them but does not fix them.
- **Whether the spectrum path works with one gain and a fixed tilt,** and whether the pitch path works without the gate. Neither has been modelled.
- **How the candidate behaves on acoustic, classical and spoken material.** The model's tracks are mostly electronic.
- **Whether listeners stop noticing a sustained level step in music,** and how fast. No study was found.
- **Typical home listening levels.** Only anecdotal reports, about 70–85 dB, were found.
- **Whether the K1 should tell the user when the input is outside the exposure range,** as Sensory Bridge's sweet-spot lights did. Prior art supports the pattern, but this is a product question, not a front-end finding.

## The Captain's decision: before or after fe-1.0.0

This report does not recommend an order. The trade-off:

- **Before release:** fe-1.0.0 would ship with "a drop looks like a drop" and the silence-flag rule addressed. But the spectrum and pitch paths are untested. Modes 22 and 32 need re-tuning. Each stage needs its probe and the Captain's eye, which is the risk the pre-mortem names as release slip.
- **After release:** fe-1.0.0 ships today's behaviour. That means loud choruses at about half the brightness of quiet sections, every beat at full scale, the guard cutting chorus hits by about a fifth at ordinary volume, and silence latching in steady loud music. A narrower stop-gap is available either way: retarget or remove the loud guard (+25 % on the final chorus in mode 22). It leaves the main problem untouched.

## Conclusion

The question was never "which AGC". It was "what is this front end for". Answered from first principles, it needs only one slow automatic decision: where the room's loudness sits on the plate. Everything faster than a musical section is the music itself and should reach the light. The ear does the same: it compresses level but never cancels it. The K1's stack treats loudness as noise to remove, as speech recognisers do. Prior art offers no proven unattended design that keeps drop-against-breakdown contrast. So the K1 is not behind a known answer; it would be the first to show one. The candidate is a sound starting point because it is reversible. GAMMA 0 equals today, every stage deletes a stage, and each sits behind a flag. The biggest unresolved risk is not bass dominance or quiet rooms. It is the anchor's rise speed: set it too fast and the design quietly undoes the very contrast it exists to show.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (report writer) | Created from the four research notes in `research_notes/K1 audio front end design/`. |
