# Firmware difference catalogue — effects and visual files

Main RPL now = commit `2a620f7e`, build env `k1_main_rpl_im69d` ("R" below).
Previous bench K1 B489A500 = commit `ed0aa984`, build env `k1_fe_bench_b489` ("B" below).
Subject: `git diff 2a620f7e ed0aa984 -- SPECTRASYNQ_K1_FIRMWARE/effects/ SPECTRASYNQ_K1_FIRMWARE/visual/` — 54 files, +3400 / −75 lines.
"+" lines exist only in the bench source; "−" lines exist only in the Main RPL source.
"In build" means the code is actually compiled into that device image, checked against the real `-D` sets (`build_defines_diff.json`) and the compiled function/object lists (`compiled_image_diff.json`).
Refs: `B:n` = line n of the file in `ed0aa984`; `R:n` = line n of the file in `2a620f7e`.

## Summary (10 lines)

1. The biggest difference: the bench build has 14 extra light-show effects (the "FX battery", modes 38–51) plus 17 support headers (`visual/motion/*.h`, `visual/easing.h`). None of these exist in the Main RPL source or build.
2. Comet (13) on the bench fires a comet for every confirmed kick; on Main RPL weak kicks (strength under 0.06) are still ignored.
3. Tempo Comet (20) and Tempo Comet Anticipate (27) on the bench only draw beat-timed comets once the tempo tracker reports a real lock; before that, real bass hits launch free-flying comets. Main RPL keeps the older "confidence over about 0.45" rule.
4. On the bench, Tempo Comet Anticipate (27) also goes dark straight away when the line input is the source and reports silence. Waveform Fast (7) and Waveform Hybrid (11) use a fixed line-input "is there sound" threshold when the line input is active. Main RPL has no line input code.
5. Waveform Tempo (18) on the bench keeps the two halves mirror-matched while its trail drains in quiet passages. The bench's warm "incandescent" filter on the secondary edge also cuts green as intended; on Main RPL the green cut is always zero.
6. Changes meant to give the same picture with less work are compiled into the bench only: 9 river/forge/ember/constellation effects skip work on the half of the strip they throw away, and Dense Forge (21, 24) computes its shimmer texture faster. The over-bright clamp gives an identical result using faster maths.
7. LED output path (WS2816 packer and "reverse order"): these hunks only matter in builds that use the WS2816 packer. That is Main RPL, running the older code. The bench build drives its LEDs through the WS2812 path, so the bench's reverse-order fix reaches neither device. On the Main RPL build, turning "reverse order" on skips setting up the primary LED outputs.
8. The LED-capture diagnostic (`:rtrace_arm`/`:rtrace_dump`) is compiled into the bench only. There the dump is sent from a low-priority background task.
9. The following are compiled into neither device: all "lite" bench variants (`K1_BENCH_FX_LITE_*`), all timing-trace markers (MabuTrace is off in both), all emulator-only code, and the Waveform Hybrid K1 (32) saturation-memory fix (its guard `K1_POSITION_SMOOTH_V1` is off in both).
10. Nothing in this file set exists only in the Main RPL source except the old versions of the changed lines listed below.

## How these modes are reached

- Modes 0–37 have the same numbers and the same enabled/disabled rules in both builds. Only the FX battery enumerators 38–51 are added, under `K1_FX_BATTERY`, so the bench has `NUM_MODES` 52 and Main RPL has 38. Source: `config_types.h`, owned by the other agent; ref `B:system/config_types.h:257-272`.
- Every effect named below is called from the per-channel dispatcher in `SPECTRASYNQ_K1_FIRMWARE.ino`, which belongs to the other agent. The FX battery calls appear at `B:SPECTRASYNQ_K1_FIRMWARE.ino:419-446`. The FX modes are not on the disabled list, so normal mode cycling reaches them on the bench.
- On Main RPL, a saved mode of 38 or higher is above `NUM_MODES`, so it is replaced by Bloom at load (`light_mode_sanitize_persisted`, `config_types.h`).
- Mode numbers used below: Waveform Fast 7, Waveform Hybrid 11, Comet 13, Spectrum River 14, Spectrum River v2 15, Ember 16, Waveform Tempo 18, Tempo River 19, Tempo Comet 20, Dense Forge 21, Dense Forge Chord 24, Chroma Constellation 25, Tempo Comet Anticipate 27, River Surge 28, Tempo River Walk 29, Waveform Hybrid K1 32.

## Note on compiled size changes in effects whose source did not change

- Aurora (12) and Ember v2 (17) have no source change in this file set, yet each compiled function is 120 bytes smaller on the bench (`compiled_image_diff.json` size_changed: aurora 394→274, ember_v2 505→385). [INFERENCE] The cause is the changed shared over-bright clamp `clamp_crgb16_preserve_sat`. Both effects use it through `finalize_additive_frame` (B:visual/lightshow_modes.h:141-143), and it is compiled inline. The picture is the same; see the lightshow_modes.h entry.

---

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_chroma_constellation.cpp (+1 / −1)

- Chroma Constellation (25): the step that carries last frame's stars outward now writes only to the upper half of the strip, instead of both halves. The lower half was already wiped before anything read it (B:159-163) and is then rebuilt by mirroring, so the picture is the same with less work per frame. Direction: changed. [in Main RPL build: yes (old full-strip version)] [in bench build: yes (new upper-half version)] guard: none. ref: R:135 `draw_sprite`, B:135 `draw_sprite_upper`.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_comet.cpp (+8 / −1)

- Comet (13): on the bench, every fresh bass kick that the onset detector has already confirmed launches a comet. The old minimum strength of 0.06 is no longer applied, so weaker but genuine kicks now produce comets. Main RPL still drops any kick below 0.06. The older rule is kept only for builds without the V2 onset detector, and both builds have V2. Direction: changed. [in Main RPL build: yes (old 0.06 rule)] [in bench build: yes (any confirmed kick)] guard: `K1_ONSET_V2` (defined in both). ref: R:105, B:105-112.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp (+131 / −5)

- Dense Forge (21): there is an optional bench-only "lite" design, in which neighbouring bands are joined by local springs and the shimmer texture is drawn in five coarse 16-pixel cells. It is switched on only by `K1_BENCH_FX_LITE_21`, which neither build sets. A compile-time stop prevents it outside a trace-enabled B489 build. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_BENCH_FX_LITE_21` (undefined → 0). ref: B:6-13, B:166-180, B:243-276.
- Dense Forge (21): there are timing-trace markers (`df21_setup`, `df21_lattice`, `df21_transport`, `df21_moire`, `df21_streak`, `df21_finalise`) and the extra braces that hold them. They compile to nothing because MabuTrace is off in both builds, and they do not change the light. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code (empty markers)] guard: `FEATURE_MABUTRACE` (=0 in both, `diag/k1_trace.h:5-7`) / `K1_TRACE_SCOPE` (no-op). ref: B:90-92, B:152-157, B:187, B:206-210, B:221-225, B:235-239, B:331-335, B:351-354, B:364-366.
- Dense Forge (21): moving last frame's picture outward now writes only to the upper half, which is the half kept and mirrored. The lower half is wiped before it is read (B:355-359), so the picture is the same with less work. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:188, B:231.
- Dense Forge (21): the shimmering interference texture ("moiré") is now computed step by step from pixel to pixel, restarting from an exact value every 8 pixels, instead of using two full sine calculations per pixel. Pixels whose source energy is too low to pass the unchanged brightness floor are now skipped early. With gain 0.48 and floor 0.008, a pixel skipped this way could never have been drawn. The pattern is intended to be the same. The step-by-step sine can differ from the old one by tiny rounding amounts, which no one would see. Direction: changed. [in Main RPL build: yes (old per-pixel sine)] [in bench build: yes (new stepwise version)] guard: `#else` of `K1_BENCH_FX_LITE_21` (the default path). ref: R:198-200, B:278-315.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge_chord.cpp (+131 / −5)

- Dense Forge Chord (24): this file has the same four changes as Dense Forge (21), applied to the chord-coloured variant. The lite variant uses `K1_BENCH_FX_LITE_24`, and the trace marker names start with `df24_`.
- Lite variant. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_BENCH_FX_LITE_24` (undefined → 0). ref: B:6-13, B:172-186, B:193, B:296-329.
- Trace markers. They compile to nothing. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code] guard: `FEATURE_MABUTRACE` (=0). ref: B:96-98, B:158-163, B:212-216, B:227-231, B:241-245, B:384-388, B:404-407, B:417-419.
- Upper-half-only transport. The picture is the same. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:194, B:237.
- Faster shimmer texture with early skip of pixels below the floor. It is intended to look the same. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: `#else` of `K1_BENCH_FX_LITE_24`. ref: R:251-253, B:331-368.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_ember.cpp (+1 / −1)

- Ember (16): the drift step now writes only to the upper half. The lower half is wiped on the next line (B:57), so the picture is the same with less work. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:56, B:56.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_river_surge.cpp (+39 / −3)

- River Surge (28): there is an optional "lite" design that pairs neighbouring frequency bins into 2-pixel filaments, with the stronger bin setting the colour. It is switched on only by `K1_BENCH_FX_LITE_28`, which neither build sets, and it needs a trace-enabled B489 build. With it off, the colour comes from the same bin as before, so the picture is unchanged. Direction: only in bench source. [in Main RPL build: no] [in bench build: no (the lite path is off; the default path is identical)] guard: `K1_BENCH_FX_LITE_28` && `FEATURE_MABUTRACE` && `K1_FE_BENCH_B489_V1`. ref: B:2-7, B:198-217, B:222, B:228-234; R:189, R:195.
- River Surge (28): there are timing-section markers (`RiverEffectSections`, `river28_*`). They are empty in both builds. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code] guard: `FEATURE_MABUTRACE` (inside the class, `visual/lightshow_modes.h`). ref: B:90, B:183, B:188, B:237, B:268.
- River Surge (28): upper-half-only transport. The lower half is wiped on the next line (B:186), so the picture is the same. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:177, B:185.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_spectrum_river.cpp (+40 / −3)

- Spectrum River (14): the optional paired-filament "lite" design, off in both builds. The default path is unchanged. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_BENCH_FX_LITE_14` && `FEATURE_MABUTRACE` && `K1_FE_BENCH_B489_V1`. ref: B:2-7, B:73-93, B:98, B:104-110; R:63, R:69.
- Spectrum River (14): timing-section markers (`river14_*`) and an added include of the trace header. Both are empty in both builds. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code] guard: `FEATURE_MABUTRACE`. ref: B:8, B:40, B:49, B:61, B:113.
- Spectrum River (14): upper-half-only transport. The lower half is cleared straight after (B:57-59), so the picture is the same. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:43, B:52.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_spectrum_river_v2.cpp (+39 / −3)

- Spectrum River v2 (15): the optional paired-filament "lite" design, off in both builds. The default path is unchanged. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_BENCH_FX_LITE_15` && `FEATURE_MABUTRACE` && `K1_FE_BENCH_B489_V1`. ref: B:2-7, B:82-102, B:107, B:113-119; R:73, R:79.
- Spectrum River v2 (15): timing-section markers (`river15_*`). They are empty in both builds. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code] guard: `FEATURE_MABUTRACE`. ref: B:47, B:68, B:73, B:122.
- Spectrum River v2 (15): upper-half-only transport. The lower half is wiped on the next line (B:71), so the picture is the same. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:62, B:70.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet.cpp (+35 / −0)

- Tempo Comet (20): the beat-timed comet train now runs only when the tempo tracker reports a real lock. On Main RPL it runs whenever tempo confidence passes the midpoint of its 0.30–0.60 ramp, which is about 0.45, even without a lock. So on the bench, comets that are predicted from an unlocked tempo stop. Direction: only in bench source; the old rule stays as the `#else` branch, and that is what Main RPL compiles. [in Main RPL build: no (old rule compiled)] [in bench build: yes] guard: `K1_TEMPO_CONSUMER_BANDS_V1` (bench only). ref: B:98-105, B:107; R:98.
- Tempo Comet (20): this case is new. While the tempo is only tentative (confidence above 0.30 but not locked) and no beat train is running, each fresh bass hit launches a comet from the centre. The tentative tempo sets the comet's speed, and the hit strength sets its size and reach. Music with an unsure tempo therefore still shows comets on real kicks, but never on guessed beats. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_TEMPO_CONSUMER_BANDS_V1`. ref: B:170-195.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet_anticipate.cpp (+87 / −0)

- Tempo Comet Anticipate (27): when the line input (the PCM1808 converter) is the active source and the audio analysis reports silence, the mode immediately clears the strip and removes all comets. It also forgets the tempo, so a coasting beat cannot repaint during silence. While the line input carries sound, real bass hits count as valid launch triggers even while the tempo tracker is still warming up. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_PCM1808_LINE_SWITCH` (=1 bench only). ref: B:5, B:90-105, B:137.
- Tempo Comet Anticipate (27): as in mode 20, comets launched on the beat train, which ease in to land exactly on the next beat, now need a real tempo lock instead of confidence of about 0.45 or more. Direction: only in bench source; the old rule is the `#else` that Main RPL compiles. [in Main RPL build: no (old rule)] [in bench build: yes] guard: `K1_TEMPO_CONSUMER_BANDS_V1`. ref: B:130-140, B:200-202.
- Tempo Comet Anticipate (27): new "free" comets. While the tempo is tentative and no beat train is running, a fresh bass hit launches a comet that travels outward at constant speed, paced by the tentative tempo. It does not slow down to land on a predicted beat. It fades or leaves the strip like an ordinary Tempo Comet head. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_TEMPO_CONSUMER_BANDS_V1`. ref: B:209-236, B:253-281.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river.cpp (+38 / −3)

- Tempo River (19): the optional paired-filament "lite" design, off in both builds. The default path is unchanged. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_BENCH_FX_LITE_19` && `FEATURE_MABUTRACE` && `K1_FE_BENCH_B489_V1`. ref: B:2-7, B:132-151, B:155, B:159-165; R:123, R:128.
- Tempo River (19): timing-section markers (`river19_*`). They are empty in both builds. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code] guard: `FEATURE_MABUTRACE`. ref: B:70, B:116, B:124, B:168.
- Tempo River (19): upper-half-only transport. The lower half is wiped straight after (B:122), so the picture is the same. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:110, B:118.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river_walk.cpp (+38 / −3)

- Tempo River Walk (29): the optional paired-filament "lite" design, off in both builds. The default path is unchanged, and the colour still includes the per-bar palette walk. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_BENCH_FX_LITE_29` && `FEATURE_MABUTRACE` && `K1_FE_BENCH_B489_V1`. ref: B:2-7, B:181-200, B:204, B:209-215; R:172, R:177.
- Tempo River Walk (29): timing-section markers (`river29_*`). They are empty in both builds. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code] guard: `FEATURE_MABUTRACE`. ref: B:91, B:164, B:172, B:218.
- Tempo River Walk (29): upper-half-only transport. The lower half is wiped straight after (B:170), so the picture is the same. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none. ref: R:158, B:166.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp (+2 / −1)

- Waveform Fast (7): the "is there real sound" threshold that decides whether the waveform reacts now comes from a shared helper. With the microphone as source, the threshold is the same as before: the sweet-spot minimum × margin. On the bench with the line input active, it switches to a fixed line-input threshold, 13 counts at the bench's trim setting of 2048. Main RPL always uses the microphone threshold. Direction: changed. [in Main RPL build: yes (old, microphone only)] [in bench build: yes (new; the line-input branch is live because `K1_PCM1808_LINE_SWITCH`=1)] guard: none at the call site; inside the helper, `K1_PCM1808_LINE_SWITCH` (`audio/k1_audio_input_state.h`, other agent's file). ref: R:51, B:2, B:52.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid.cpp (+2 / −1)

- Waveform Hybrid (11): the same sound-threshold change as Waveform Fast (7). The microphone threshold is unchanged, and a fixed line-input threshold applies when the bench's line input is active. Direction: changed. [in Main RPL build: yes (old)] [in bench build: yes (new)] guard: none at the call site; `K1_PCM1808_LINE_SWITCH` inside the helper. ref: R:32, B:2, B:33.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp (+2 / −4)

- Waveform Hybrid K1 (32): the running "colour saturation memory" would move from a hidden per-edge store that never resets into the channel's own effect memory, which is cleared when that memory is reset. The colour would then restart cleanly instead of starting from a value left over from earlier. This code sits inside `K1_POSITION_SMOOTH_V1`, and neither build defines it, so it is compiled into neither device. Direction: changed. [in Main RPL build: no] [in bench build: no] guard: `K1_POSITION_SMOOTH_V1` (off in both). ref: R:246-247, R:251-252, B:246, B:250.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp (+3 / −0)

- Waveform Tempo (18): during the quiet "drain" phase, the trail keeps scrolling and fading with no new colour added. When Mirror is on, the bench now copies the upper half onto the lower half before returning, so the two halves stay symmetrical while the trail drains. On Main RPL they can drift out of mirror during quiet passages. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none. ref: B:256-258.

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_lob_return.cpp (+140 / −0)

- New effect "Lob Return", mode 38 (`LIGHT_MODE_FX_LOB_RETURN`). It throws glowing blobs (up to 24) outward from the centre. Each flies out 18–72 px, slows, falls back to the centre and leaves a short fading trail behind it. Landing at the centre makes a small flash there. The pattern is mirrored both ways from the centre. Launches come in a near-continuous stream while music plays, faster when louder, with extra launches on each fresh onset. Brightness follows loudness (VU 65% + peak 35%), rising over about 35 ms and falling over about 350 ms. Launches are set off by bass onsets and general onsets. Colour comes from 8 shades at the low end of the selected palette, nudged by loudness. The effect stays dark when audio is silent or below the microphone or line presence floor, and clears completely after 1.2 s of quiet. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes (object compiled, `light_mode_fx_lob_return` 2015 bytes)] guard: `K1_FX_BATTERY`. ref: B:1-143 (entry B:136).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_accumulate_cascade.cpp (+140 / −0)

- New effect "Accumulate Cascade", mode 39. It works like a sandpile running from the centre to the edge, with 80 cells. Music drops "grains" into the cells at a rate set by loudness (VU 75% + peak 25%). A cell holding 4 grains topples and passes 2 grains to each neighbour, so avalanches ripple along the strip. The light shows where grains have just moved: a bright moving avalanche over a faint texture. Two fixed darker seams sit about 26 px and 57 px from the centre. Colour comes from 8 palette shades, picked by local activity and by the low/mid/high band energy, which is assigned in a repeating 8-pixel pattern. In silence the grains drain away, and everything clears after 1.2 s of quiet. It uses the microphone or line presence floor. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1-140 (entry B:133).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_front_refractory.cpp (+132 / −0)

- New effect "Front Refractory", mode 40. Each fresh transient (the V2 onset detector's transient event) starts a wave at the centre that runs outward cell by cell. Behind it, cells pass through a short recovery and cannot fire again until it ends. The waves move at about 32–92 cells per second, faster when louder, over a faint, slowly moving grain texture. Brightness = VU 55% + peak 30% + novelty 15%. Colour comes from 8 palette shades with the white part removed, so the colours are purer, and shifts with cell age, a slow clock and the density of recent hits. The effect stops in silence and clears after 1.2 s. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY` (the onset source is chosen by `K1_ONSET_V2`, defined in both). ref: B:1-132 (entry B:34).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_reverse.cpp (+141 / −0)

- New effect "Reverse", mode 41. Groups of three rings start at the outer edge, travel in to the centre, bounce once, travel back out to the edge and disappear. A new group starts on each fresh transient, and also whenever fewer than three rings are left. The rings sit over a gently moving wave background. Brightness = VU 50% + peak 30% + novelty 20%. Louder music makes the rings last longer. Colour comes from 16 palette shades with the white part removed, and a ring changes shade after it turns. The effect clears after 1.2 s of silence. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1-141 (entry B:41).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_scan.cpp (+111 / −0)

- New effect "Scan", mode 42. The strip is filled with a textured palette field in 16 colour bands of 5 px each. The low, mid and high energies brighten their own bands. A single dark gap about 12 px wide sweeps back and forth between the centre and the edge at roughly 140–300 px/s. It moves faster with loudness and mid energy, and also with tempo (BPM) when tempo confidence is 0.30 or more. Level = 65% overall loudness + 20% low + 10% mid + 5% high. In silence the sweep stops and the field fades out. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1-111 (entry B:32).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_chain.cpp (+148 / −0)

- New effect "Chain", mode 43. Sixteen beads, 5 px apart from the centre to the edge, are linked like a springy chain. A push wave runs along the chain at a musical rate set by loudness, mid energy and (when tempo confidence is 0.30 or more) BPM. The bass-versus-treble balance pushes the inner and outer halves in opposite directions. Each fresh kick (V2 kick event) jolts the first link, and the jolt ripples outward. The whole chain also bends by up to ±3 px. Each bead's brightness comes from how much it is stretched against its neighbour. Colour comes from the palette, set by the bead's position, its stretch and the treble. Level = 55% VU + 25% low + 15% mid + 5% high. The chain freezes and fades in silence. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1-148 (entry B:28).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_dilate_recoil.cpp (+195 / −0)

- New effect "Dilate Recoil", mode 44. Sixteen "membrane" cells reach out from the centre. Their reach springs outward on each fresh transient and springs back. At rest the reach is about 38 px, and loudness adds up to 12 px more. Each cell is drawn as a streak between where it was and where it is now. The upper half, the lower half and the two edges move differently: one stretches, one gathers, one has a wider shoulder and one forms narrow ribs, so the halves are not mirror copies. The drive is mostly harmonic: chroma strength, plus chord confidence and chord-root strength when chord confidence is 0.30 or more. Loudness supplies 24%, and the peak level acts as a floor. Colour comes from 4 shades taken from the palette around the CHROMA setting. When the palette is not in charge of colour, or a palette stop is grey or black, a fixed colour at the CHROMA hue is used instead. The effect is dark when peak and loudness are both at or below 0.02, or when the silence flag is set. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY` (the harmonic mix uses `K1_CHORD_V2`, defined in both). ref: B:1-195 (entry B:179).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_infall.cpp (+204 / −0)

- New effect "Infall", mode 45. Particles start at the outer edge and fall inward to the centre, speeding up as they go, each with a short tail pointing back towards the edge. At least 14 are kept moving while music plays, and there can be up to 24, with extra launches on fresh kicks (V2 kick event). Brightness = 56% loudness + 27% low + 17% mid, with the peak level as a floor. The upper and lower halves get slightly different brightness patterns, and the secondary edge runs its pattern at 3:2 the speed of the primary edge. Colour comes from 4 shades taken from the palette around the CHROMA setting, with a fixed fallback colour as in mode 44. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1-204 (entry B:182).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_bounce.cpp (+130 / −0)

- New effect "Bounce", mode 46. At least 8 balls bounce back and forth between the centre and the edge at about 250–298 px/s. Each loses 6% of its speed per bounce and is retired after 3 edge bounces or about 4 s. New balls keep arriving on an internal clock that runs faster when louder; kicks are not used. Each ball has a short two-sided trail of 2.2–4.4 px, which gets shorter when louder. Brightness = 68% loudness + 32% band mix (50% low, 32% mid, 18% high). Colour comes from 8 evenly spaced palette shades. The effect fades in silence and clears after 1.2 s. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY == 1`. ref: B:1-130 (entry B:60).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_split_merge.cpp (+124 / −0)

- New effect "Split Merge", mode 47. Four pairs of soft blobs sit evenly along the half, 20 px apart. Each pair keeps splitting apart (up to 12 px) and merging back into one, at 64–72 px/s. A slow music-driven clock bends and stretches the whole layout by up to ±14 px. Brightness is mostly harmonic: 62% harmony (chroma strength mixed with chord confidence) + 28% loudness + 10% mid. Colour comes from 10 palette bands fixed by position, 8 px each. The effect fades in silence and clears after 1.2 s. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY == 1`. ref: B:1-124 (entry B:75).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_stretch.cpp (+177 / −0)

- New effect "Stretch", mode 48. Elastic streaks shoot outward from the centre. Each launch sends two heads out at 145–218 px/s, each with a springy tail that catches up behind it and two visible "knots" along the stretch. Launches come on fresh onsets or bass onsets (and V2 kicks), and on an internal clock in between. Launches go to the edges in a repeating pattern: primary only, secondary only, then both. Six faint wandering dots fill the background. Drive = 48% low + 37% loudness + 15% novelty, and tempo (BPM) speeds up the background clock when tempo confidence is 0.30 or more. Colour comes from 4 palette shades, or from the live chroma/palette colour when the palette is not in charge. The effect clears after 1.2 s of silence. The visible work happens in helper functions that are compiled only into the bench (`stretch_update`, `stretch_render`). Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1-177 (entry B:170).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_pass_through.cpp (+177 / −0)

- New effect "Pass Through", mode 49. Pairs of dots launch together, one from the centre and one from the edge, and run towards each other at 155–238 px/s. They cross once, leaving a brief spark at the crossing point, and then exit at the far end. At most three pairs are moving at once. A launch happens when the sound's character changes (a jump in spectral novelty or a shift in the low/mid/high balance), no more often than every 0.1 s, and also on a steady internal clock. Six faint wandering dots fill the background. Drive = 36% novelty + 29% mid + 20% high + 15% loudness. Colour comes from 4 palette shades, or from the live chroma colour when the palette is not in charge. The effect clears after 1.2 s of silence. The work happens in bench-only helpers (`through_update`, `through_render`). Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1-177 (entry B:170).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_front_ca.cpp (+150 / −0)

- New effect "Front CA", mode 50. It shows a branching triangle pattern, a cellular automaton in which each cell takes the exclusive-or of its two neighbours at every tick. The pattern starts from a fixed scattered row when music begins. It ticks faster with loudness, from about 5 to 19 ticks per second. Sixteen coarse cells (about 5 px each) span the half, with smooth cross-fades between ticks and a gentle sway. Drive = 36% loudness + 24% spectral energy + 40% novelty (spectral flux). Colour comes from 16 palette shades, made fully saturated with the white part removed. The shade is picked by each cell's colour, a slow wave and the bass-to-treble balance. The effect uses the microphone or line presence floor to decide silence, and clears after 1.2 s. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY == 1`. ref: B:1-150 (entry B:44).

## SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_orbit.cpp (+161 / −0)

- New effect "Orbit", mode 51. Eight glowing bodies swing back and forth across the half, centred about 40 px from the middle, with swings of ±31–37 px. Each swings at a different but related speed (2:3:4:5:6) and has a lagging tail. A body brightens as it "comes towards you" and dims as it moves away. The swinging speeds up with loudness. Brightness = 64% loudness + 12% band total, and each body is also tied to the low, mid or high band. Colour comes from the palette, fully saturated with the white part removed. The effect uses the microphone or line presence floor for silence. In silence the orbits freeze, and the strip clears after 1.2 s. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY == 1`. ref: B:1-161 (entry B:47).

---

## SPECTRASYNQ_K1_FIRMWARE/visual/channel_effect_state.h (+5 / −0)

- Two new per-edge memory fields support the Tempo Comet Anticipate (27) changes: "last bass hit seen" and a per-comet flag meaning "this comet flies free and does not land on the beat". They exist only when the tempo-band feature is on. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_TEMPO_CONSUMER_BANDS_V1`. ref: B:153-156.
- A new per-edge field holds the Waveform Hybrid K1 colour saturation memory. The field exists in the bench build's effect memory, but the only code that uses it is switched off in both builds (see light_mode_waveform_hybrid_k1.cpp), so it has no visible effect. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes (field present, never used)] guard: none on the field; the user is behind `K1_POSITION_SMOOTH_V1` (off). ref: B:186.

## SPECTRASYNQ_K1_FIRMWARE/visual/easing.h (+64 / −0)

- New shared smoothing toolkit (`k1ease`). It gives a safe frame-time step, a "fast up, slow down" follower, a plain smoother, an exponential fade and a peak follower. It is used only by the FX battery effects (modes 38–51) for their brightness easing. Nothing else includes it. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes (through the FX battery files only)] guard: none in the file; reached only through `K1_FX_BATTERY` files. ref: B:1-64.

## SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.cpp (+18 / −10)

Background: this whole file compiles to nothing unless `K1_RENDER_TRACE_V1` is set (B:5). The bench build sets it and Main RPL does not. Every item below is therefore absent from the Main RPL build.

- LED-capture diagnostic (`:rtrace_arm` / `:rtrace_dump`): on the bench, a dump is now sent from a low-priority background task, so music analysis and the lights keep running while megabytes are sent over USB. Arming a new capture is refused while a dump is still sending. In the Main RPL source this background path existed only for the separate `K1_B489_WS2816_V1` image. The bench gets it through `K1_FE_BENCH_B489_V1`. Direction: changed. [in Main RPL build: no (file empty)] [in bench build: yes (`rtrace_drain_task`, `rtrace_init_drain` present only in the bench image)] guard: `K1_RENDER_TRACE_V1` && (`K1_RTRACE_DUAL` || `K1_FE_BENCH_B489_V1`). ref: R:61, R:191, R:305, R:314; B:65, B:199, B:313, B:322.
- Two-edge capture storage (frame count 2000, both edges per frame) is now switched by `K1_RTRACE_DUAL` instead of `K1_B489_WS2816_V1`. Neither device build sets either one, so the bench keeps the single-edge layout with 3000 frames. This is a rename with no device effect. Direction: changed. [in Main RPL build: no] [in bench build: yes, but the single-edge branch as before] guard: `K1_RTRACE_DUAL`. ref: R:25, R:109, R:124, R:153; B:29, B:117, B:132, B:161.
- Emulator-only code: the trace output port is redirected to the emulator log port, and frames are captured only inside the emulator scenario window. Not in either device build. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_EMU_FIXTURE` / `K1_EMU_UART0`. ref: R:17-18; B:17-22, B:112-115.

## SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.h (+10 / −2)

- New switch `K1_RTRACE_DUAL`, defined when `K1_B489_WS2816_V1` or `K1_EMU_FIXTURE` is set. Neither device build sets either one, so there is no device effect. The two-edge capture entry point is now declared under this switch. Direction: changed. [in Main RPL build: no] [in bench build: no (switch not set)] guard: `K1_RENDER_TRACE_V1` && (`K1_B489_WS2816_V1` || `K1_EMU_FIXTURE`). ref: R:43; B:38-44, B:51.
- Emulator-only documentation note (comment only). Not in either device build. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: n/a (comment). ref: R:25; B:25-26.

## SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h (+84 / −28)

- WS2816 packed output, primary edge, "reverse order" setting. On the Main RPL build, if the saved reverse-order setting is on, the primary edge skips the 48-bit packer every frame and drops to the older 8-bit output path. At start-up it also skips registering the primary WS2816 outputs. The bench source instead always packs and then flips the packed pixels end-to-end. This code exists only in builds that use the WS2816 packer. Main RPL runs the old version; the bench build uses the WS2812 path and does not compile this block. So with the default setting (reverse off) there is no difference. With reverse on, Main RPL does not drive the primary WS2816 outputs as normal. Direction: changed. [in Main RPL build: yes (old version)] [in bench build: no] guard: `K1_WS2816_LEVER2_V1` (Main RPL only); the start-up hunk also needs `K1_MAIN_RPL_PINMAP_V1` and the `#else` of `K1_LED_I2S_DIRECT_V1`. ref: R:1244-1248, R:1315-1319, R:1602-1608; B:1247, B:1314-1316, B:1611.
- Same "reverse order" change in the direct-I2S start-up path. That path is compiled into neither build. Direction: changed. [in Main RPL build: no] [in bench build: no] guard: `K1_WS2816_LEVER2_V1` && `K1_LED_I2S_DIRECT_V1`. ref: R:1586-1592; B:1601.
- WS2816 packed output, secondary edge. On Main RPL the secondary edge also skips its packer when the primary edge's reverse-order setting is on. The "reverse secondary" setting has no effect on the packed secondary output, because the packed path returns before the reverse step. The bench source always packs the secondary edge and flips it when "reverse secondary" is on. The build status is the same as above: only Main RPL compiles this block, and it compiles the old version. Direction: changed. [in Main RPL build: yes (old version)] [in bench build: no] guard: `K1_WS2816_LEVER2_V1`. ref: R:2946-2950; B:3003, B:3044-3046.
- Secondary edge warm "incandescent" filter (`SECONDARY_INCANDESCENT_FILTER` above 0). In the Main RPL source, a number-size overflow makes the green reduction always zero, so the filter only cuts blue. The bench source uses a wider number, so green is reduced as intended and the tint is warmer. On the bench build this is the normal secondary output path. On Main RPL it runs only when the packed path is skipped, which happens only with reverse order on. Direction: changed. [in Main RPL build: yes (old, green cut always 0)] [in bench build: yes (fixed)] guard: none (after the `K1_WS2816_LEVER2_V1` block). ref: R:3026; B:3082.
- New `draw_sprite_upper`: a copy of the existing "move last frame's picture" routine that writes only to pixels 80–159. The nine effects 14, 15, 16, 19, 21, 24, 25, 28 and 29 use it in place of `draw_sprite`. Each of them wipes the lower half before reading it, so the arithmetic and the picture are unchanged and the work is roughly halved. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes (`draw_sprite_upper` present only in the bench image)] guard: none. ref: B:2676-2725.
- Emulator-only code. It includes the emulator fixture header, captures both packed edges in the emulator, records the power-limit scale at the point where output would be sent, and swaps the intro animation's `FastLED.delay(2)` for a plain `delay(2)` when output is suppressed. Not in either device build. Direction: only in bench source. [in Main RPL build: no] [in bench build: no] guard: `K1_EMU_FIXTURE` / `K1_EMU_SKIP_EMIT`. ref: B:22-24, B:1338-1351, B:1377-1380, B:2060-2064.

## SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h (+101 / −1)

- Over-bright clamp (`clamp_crgb16_preserve_sat`). When a pixel goes over full brightness, it is scaled back while keeping its colour. The scale is now worked out with an exact whole-number method instead of a slower division. The result is identical (both equal floor(2³²/d)), so the picture does not change. This clamp runs inside `finalize_additive_frame`, which most effects use. Direction: changed. [in Main RPL build: yes (old division)] [in bench build: yes (new method)] guard: none. A counter of saturated pixels in the same hunk is diagnostic only (`FEATURE_MABUTRACE && FEATURE_TRACE_RENDER`, off in both). ref: R:96; B:126-133.
- Declarations of the 14 FX battery effects (modes 38–51). Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:800-816.
- The built-in mode self-test is a serial diagnostic (`vp_probe_dispatch_and_hash` / `vp_run_output_probe`) that renders each mode once and prints a fingerprint. It now also covers the 14 FX battery modes. Direction: only in bench source. [in Main RPL build: no] [in bench build: yes] guard: `K1_FX_BATTERY`. ref: B:1128-1157, B:1284-1299.
- Timing-section helper class (`RiverEffectSections`) and an include of the trace header. Both are empty unless MabuTrace is on, and it is off in both builds. No effect on the light. Direction: only in bench source. [in Main RPL build: no] [in bench build: no code] guard: `FEATURE_MABUTRACE`. ref: B:11, B:24-52.

## SPECTRASYNQ_K1_FIRMWARE/visual/ws2816_pack.h (+13 / −0)

- New helper that reverses the order of packed 48-bit pixels end-to-end. It is called only from the WS2816 packed-output code in led_utilities.h. The Main RPL source does not contain it, and the bench build does not compile that output path. So it generates no code in either device build. Direction: only in bench source. [in Main RPL build: no] [in bench build: no (defined but never called)] guard: none on the helper; its callers are behind `K1_WS2816_LEVER2_V1`. ref: B:61-73.

## Shared motion kit for the FX battery — SPECTRASYNQ_K1_FIRMWARE/visual/motion/

All 17 files are new, exist only in the bench source, and are included only by the 14 FX battery effect files. Each is therefore [in Main RPL build: no] [in bench build: yes, through `K1_FX_BATTERY` files only], guard: none in the header itself. Refs are whole files in B.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/common.h (+66 / −0)
- Shared building blocks: a body (position, speed, life, age), a pool of up to 24 bodies, and a loudness envelope that goes fully dark after 1.2 s of silence. It also has the launch trigger (on a rising kick or on a loudness-paced clock) and the conversion of bodies into "distance from centre / brightness / colour position" samples. ref: B:1-66.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/drive.h (+31 / −0)
- Shared timing helpers. It holds a music-paced clock that stops in silence, an edge router that cycles primary → secondary → both (used by Stretch, 48), and a rational speed ratio (used by Infall's 3:2 secondary, 45). It also defines a four-arm role (upper/lower × primary/secondary, used by Dilate Recoil, 44). ref: B:1-31.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/render.h (+36 / −0)
- Shared drawing helpers. It has a soft dark notch (used by Scan, 42 and Accumulate Cascade, 39) and a lifespan curve: ignite, hold, fade (used by Lob Return, 38). It also has trail shapes, edge-bounce handling and a bend/repeat warp; the bend warp is used by Chain, 43 and Split Merge, 47. ref: B:1-36.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/accumulate_cascade.h (+17 / −0)
- Sandpile maths for mode 39. Grains are deposited at a loudness-set rate and a cell holding 4 grains topples. The centre reflects grains and the outer edge lets them go. Grains drain in silence. ref: B:1-17.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/bounce.h (+20 / −0)
- Ball maths for mode 46. Balls launch at 250–298 px/s, reflect at the edge and the centre losing 6% speed per bounce, and retire after 3 edge bounces or a 4 s life. ref: B:1-20.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/chain.h (+20 / −0)
- Chain maths for mode 43. It models 16 spring-linked links with damping, keeps each link within 3.5 px of its neighbour, and gives the first link a jolt on each rising kick. ref: B:1-20.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/dilate_recoil.h (+19 / −0)
- Membrane maths for mode 44. Sixteen cells have springy reach around a 38 px rest. Each transient kicks them outward, and loudness raises the rest reach by up to 12 px. ref: B:1-19.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/front_ca.h (+13 / −0)
- Cellular automaton maths for mode 50: each cell becomes the exclusive-or of its two neighbours at each tick. The tick rate follows the music, and the pattern clears after 1.2 s of silence. ref: B:1-13.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/front_refractory.h (+13 / −0)
- Excitable-wave maths for mode 40. A cell fires when a neighbour fires, then passes through 4 recovery steps before it can fire again. A rising kick fires the centre cell. ref: B:1-13.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/infall.h (+16 / −0)
- Infall maths for mode 45. Bodies start at the edge moving inward, accelerate at 18 px/s², and retire on reaching the centre. ref: B:1-16.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/lob_return.h (+16 / −0)
- Thrown-and-returning body maths for mode 38. Bodies launch outward under gravity and retire on returning to the centre. Mode 38 replaces the launch speed (120–240 px/s) and adds extra gravity in its own file. ref: B:1-16.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/orbit.h (+12 / −0)
- Orbit maths for mode 51: 16 bodies with their own phases, whose speed is set by the music. Mode 51 draws 8 of them, using its own larger swing. ref: B:1-12.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/pass_through.h (+20 / −0)
- Opposed-pair maths for mode 49. Paired bodies start one at the centre and one at the edge, moving towards each other. Each pair records a single crossing, and the bodies retire at the far end. ref: B:1-20.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/reverse.h (+19 / −0)
- Ring maths for mode 41. Bodies start at the edge moving inward, turn once at the centre, and retire on reaching the edge again. ref: B:1-19.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/scan.h (+20 / −0)
- Sweep maths for mode 42. A single point sweeps back and forth between the centre and the edge at 120 px/s plus 60 px/s per unit of rate (capped), and stops in silence. ref: B:1-20.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/split_merge.h (+21 / −0)
- Blob-pair maths for mode 47: four pairs, 20 px apart, whose separation swings between 0 and 12 px, with a smooth merge between the two blobs of a pair. ref: B:1-21.

### SPECTRASYNQ_K1_FIRMWARE/visual/motion/stretch.h (+16 / −0)
- Elastic body maths for mode 48. The head moves at constant speed, and a spring-damped tail chases it. The body retires when the tail reaches the edge. ref: B:1-16.

## File index (all 54 files in this set, one per line)

SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_chroma_constellation.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_comet.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge_chord.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_ember.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_accumulate_cascade.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_bounce.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_chain.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_dilate_recoil.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_front_ca.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_front_refractory.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_infall.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_lob_return.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_orbit.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_pass_through.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_reverse.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_scan.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_split_merge.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_fx_stretch.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_river_surge.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_spectrum_river.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_spectrum_river_v2.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet_anticipate.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river_walk.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp
SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp
SPECTRASYNQ_K1_FIRMWARE/visual/channel_effect_state.h
SPECTRASYNQ_K1_FIRMWARE/visual/easing.h
SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.cpp
SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.h
SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h
SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/accumulate_cascade.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/bounce.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/chain.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/common.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/dilate_recoil.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/drive.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/front_ca.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/front_refractory.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/infall.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/lob_return.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/orbit.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/pass_through.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/render.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/reverse.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/scan.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/split_merge.h
SPECTRASYNQ_K1_FIRMWARE/visual/motion/stretch.h
SPECTRASYNQ_K1_FIRMWARE/visual/ws2816_pack.h
