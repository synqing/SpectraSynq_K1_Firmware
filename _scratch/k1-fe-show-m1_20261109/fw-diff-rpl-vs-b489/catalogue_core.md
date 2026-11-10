# Firmware differences, core files: Main RPL now vs previous bench K1 (B489A500)

- **Main RPL now** = commit `2a620f7e`, built as env `k1_main_rpl_im69d`.
- **Bench build** = commit `ed0aa984`, built as env `k1_fe_bench_b489` (chip B489A500).
- Net source diff `git diff 2a620f7e ed0aa984` over: audio/, system/, serial/, persistence/, diag/, control/, the sketch, platformio.ini, scripts/platformio/. Effects and visual/ are catalogued separately.
- Shared starting point 68a684dc. Main RPL = that point plus one commit (LED pins, constants.h). Bench = that point plus 172 commits. So nearly every item below is **only in bench source**; one is **only in Main RPL source**; a few are **changed**.
- `ref` uses `B:` for the bench commit and `R:` for the Main RPL commit; paths are under `SPECTRASYNQ_K1_FIRMWARE/` unless a top-level file is named.
- "yes/no" = whether the code is compiled in and running in that device image. Checked against the lead's `build_defines_diff.json` (exact -D flags) and `compiled_image_diff.json` (functions in each image). `guard` = the #if/#ifdef switch that controls it ("none" = always compiled when the file is).

## Summary by subsystem

1. **Build setup.** The bench build is the Main RPL setup plus Founders' Edition (FE) board support and the bench pin map. It drops the Main RPL's two-wire WS2816 16-bit LED packer and look library. It adds 14 extra test effects, the sub-110 Hz rumble filter, LED-level capture and a tempo-effect repair. The Main RPL env definition is identical in both commits.
2. **Pins.** Main RPL LEDs use GPIO2/3 (primary) and GPIO5/6 (secondary), with the mic on DATA 8 / CLK 9. Bench LEDs are single-wire on GPIO4/5, the mic is on CLK 14 / DATA 13, and the PCM1808 line-in chip is on 10/11/9.
3. **Audio input.** The bench adds a switchable line-in path (PCM1808) beside the mic, with its own silence test, its own level floor and a background capture task. On the bench it stays on the mic unless `:audio_src=line` is typed, because there is no jack sensor. Main RPL has the mic only.
4. **Quiet and rumble.** The bench removes sub-110 Hz rumble from the drive peak and, newly, from the VU and silence measurement. Main RPL does neither.
5. **Beat and tempo.** The bench treats sound returning after exact digital zero as a restart, not a drum hit. The tempo maths gives the same numbers, using a cheaper shared calculation, and its constants now live in one file with the same values. Every other tempo experiment is switched off in both builds.
6. **Saving settings.** The bench keeps the settings file open, writes it in one go and retries failed writes. During music it waits for a quiet moment, or at most 60 s, before saving. Main RPL saves 5 s after the last change and opens and closes the file each time.
7. **Main loop.** The bench uses a millisecond clock that does not wrap every 71 minutes. In the normal path it takes one snapshot of the primary settings per frame. It also has FE power, jack and heartbeat housekeeping, which stays passive on the bench.
8. **Between the two processor cores.** Main RPL marks the "new audio frame ready" flag as shared between the cores. The bench has a plain flag again.
9. **Serial commands.** The bench adds `:fe_status`, `:pd_status`, `:pd_nvm_write` and `:audio_src=auto|mic|line`. The render-trace flag also adds `:rtrace_arm` and `:rtrace_dump`, which is existing code.
10. **In neither device build.** The emulator replay fixture (the largest change), MabuTrace timing counters, performance-audit prints, the tempo lane R1 experiments, mic wiring diagnostics, release-tag stamping and 16 new non-device envs (emulator, probe and diagnostic).

---

## platformio.ini (+256 / −0)

All 256 lines are new envs. No existing env line changed, and the `[env:k1_main_rpl_im69d]` block is the same in both commits. Everything that differs between the two device builds comes from the new `k1_fe` → `k1_fe_bench_b489` chain (only in bench source).

- **New `[env:k1_fe]`, the FE shipping env and the bench build's parent.** It is the Main RPL setup plus two extra source files (`audio/k1_pcm1808_input.cpp`, `system/k1_fe_board.cpp`). It also adds the flags `K1_FE_BOARD_V1`, `K1_PCM1808_LINE_SWITCH=1`, `K1_PCM1808_MONO_POLICY=K1_PCM1808_MONO_MID` (line-in left+right averaged) and `K1_PCM1808_CANON_TRIM_Q15=2048` (line-in level cut to 1/16, −24 dB). The image confirms both files are compiled only in the bench build. [in Main RPL build: no] [in bench build: yes, inherited] guard: env chain ref: B:platformio.ini:480-492
- **Bench env `[env:k1_fe_bench_b489]`: upload/monitor port `/dev/tty.usbmodem101` and an empty release-tag prefix.** This is flashing convenience only; the firmware is unchanged. [in Main RPL build: n/a] [in bench build: n/a] guard: none ref: B:platformio.ini:505-511
- **Bench removes `K1_MAIN_RPL_PINMAP_V1` and adds `K1_BENCH_REFERENCE_PINMAP=1`.** The bench uses the bench-reference pin map: primary LED data GPIO4, secondary GPIO5, IM69D mic CLK 14 / DATA 13. Main RPL uses GPIO2/3 + GPIO5/6 and mic DATA 8 / CLK 9. The image confirms: LED drivers on pins 2, 3 and 6 exist only in Main RPL; drivers on pins 4 and 5 exist in the bench. [in Main RPL build: Main RPL map] [in bench build: bench map] guard: build_unflags / build_flags ref: B:platformio.ini:512-523
- **Bench removes `K1_WS2816_LEVER2_V1`.** The bench has no 16-bit WS2816 two-wire packing. LEDs are driven as ordinary 8-bit single-wire WS2812. `k1_lever2_pack_frame` and `k1_ws2816_degamma_u16` exist only in the Main RPL image. [in Main RPL build: yes] [in bench build: no] guard: K1_WS2816_LEVER2_V1 ref: B:platformio.ini:512-517
- **Bench swaps `K1_LOOK_LIB_V1` for `K1_LOOK_LIB_WS2812_V1`.** Main RPL runs the full "look" colour-curve library on every pixel (`k1_look_apply_u16`). At boot it also loads user look slot 15 from flash inside `load_config` (existing code at R:persistence/bridge_fs.h:360-367). The bench has only the WS2812 look printout (`k1_look_ws2812_apply_u8`). This is the reason `load_config` is 1716 vs 867 bytes. [in Main RPL build: full library] [in bench build: WS2812 variant] guard: K1_LOOK_LIB_V1 / K1_LOOK_LIB_WS2812_V1 ref: B:platformio.ini:516,526
- **Bench adds `K1_FE_BENCH_B489_V1`.** This turns on bench-only source: single-wire LED type and GRB colour order forced at every boot (system.h), a build check against the wrong pin map (constants.h) and the silence-dwell constant (globals.h, still 5 s). [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BENCH_B489_V1 ref: B:platformio.ini:519
- **Bench adds `K1_FX_BATTERY=1`.** It adds 14 extra effects as modes 38–51 (lob return, accumulate cascade, front refractory, reverse, scan, chain, dilate recoil, infall, bounce, split merge, stretch, pass-through, front CA, orbit). The image has 14 effect objects only in the bench. Effect code is in the effects catalogue; their selection lives in the sketch and config_types.h below. [in Main RPL build: no] [in bench build: yes] guard: K1_FX_BATTERY ref: B:platformio.ini:520
- **Bench adds `K1_TEMPO_CONSUMER_BANDS_V1`.** Tempo Comet and Tempo Comet Anticipate draw beat-grid cues only on a confirmed tempo lock. Otherwise they react to real bass onsets. Effect code is in the effects catalogue. Image: `light_mode_tempo_comet` 1615 → 1834 bytes, anticipate 1864 → 2517. [in Main RPL build: no] [in bench build: yes] guard: K1_TEMPO_CONSUMER_BANDS_V1 ref: B:platformio.ini:522
- **Bench adds PCM1808 line-in wiring flags.** `K1_PCM1808_DIN_PIN=10`, `BCLK=11` and `LRCK=9` set the line-in chip pins. `K1_PCM1808_NFC_CS_HOLD_PIN=-1` means no NFC chip-select pin is held high. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_* ref: B:platformio.ini:527-530
- **Bench adds `K1_AP_SUBSONIC_HPF_V1`.** This turns on the existing filter that stops sub-110 Hz rumble from setting the drive peak (brightness scaling). That code is already in both sources but switched off in Main RPL. It also turns on the new VU/silence use of the filtered signal (see i2s_audio.h). [in Main RPL build: no] [in bench build: yes] guard: K1_AP_SUBSONIC_HPF_V1 ref: B:platformio.ini:533
- **Bench adds `K1_RENDER_TRACE_V1`.** This adds LED-level capture (`:rtrace_arm` / `:rtrace_dump`) and a background drain task. The source is unchanged and existing. Functions `rtrace_drain_task`, `k1_render_trace_dispatch` and `k1_render_trace_on_frame` exist only in the bench image. [in Main RPL build: no] [in bench build: yes] guard: K1_RENDER_TRACE_V1 ref: B:platformio.ini:535
- **New non-shippable bench envs `k1_fe_bench_b489_perf_probe`, `k1_fe_bench_b489_scalar_probe` and `k1_fe_bench_b489_trace_dev`.** These are performance counters, the shared-window off switch, MabuTrace and lite effect variants. They affect neither device build. [in Main RPL build: no] [in bench build: no] guard: separate envs ref: B:platformio.ini:539-579
- **New emulator and probe envs, for replay and tempo lane R1 only:** `k1_main_rpl_emu`, `k1_fe_emu`, `k1_main_rpl_im69d_position_smooth_probe`, `k1_main_rpl_emu_position_smooth_probe`, `k1_main_rpl_emu_tempo_probe`, `k1_main_rpl_emu_tempo_r1`, `k1_main_rpl_emu_tempo_r1_probe`, `k1_main_rpl_emu_tempo_r1_spec`, `k1_main_rpl_emu_tempo_r1_lockoff`, `k1_main_rpl_emu_tempo_r1_lockoff_unrepaired` and `k1_main_rpl_emu_tempo_r1_lockoff_probe`. They affect neither device build. [in Main RPL build: no] [in bench build: no] guard: separate envs ref: B:platformio.ini:716-838
- **New mic wiring diagnostic envs `k1_bench_im69d_wirediag_pullup` and `k1_bench_im69d_wirediag_swap`.** They affect neither device build. [in Main RPL build: no] [in bench build: no] guard: separate envs ref: B:platformio.ini:921-938

## scripts/platformio/k1_build_provenance.py (+41 / −9)

- **Build script can stamp a release tag (`K1_BUILD_TAG`, from git tags such as `fe-*`) into envs that set `custom_release_tag_prefix`, i.e. `k1_fe` only.** The bench env clears the prefix, so no tag is added. The lead's define lists show no `K1_BUILD_TAG` in either build, so this changes neither image. Only in bench source. [in Main RPL build: no] [in bench build: no] guard: custom_release_tag_prefix ref: B:scripts/platformio/k1_build_provenance.py:53-100

## scripts/platformio/k1_device_identities.json (+19 / −0)

- **Upload-guard allow-list (which env may be flashed onto which chip).** Main RPL (9087A500) is now also allowed `k1_fe`. B489A500 is allowed `k1_fe_bench_b489` and its three probes, plus the two wirediag envs. Eleven new envs are listed as never-flash: `k1_fe_emu` and ten Main RPL emulator/probe envs. This is flashing safety data, not firmware. Only in bench source. [in Main RPL build: n/a] [in bench build: n/a] guard: none ref: B:scripts/platformio/k1_device_identities.json:66-68,116-121,183-196

---

## SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino (+107 / −35)

- **Mode dispatcher routes modes 38–51 to the 14 extra test effects.** Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FX_BATTERY ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:418-447
- **Main loop's millisecond clock (`t_now`) changed.** It now comes from the board's millisecond counter, which wraps after 49 days. It used to be microseconds ÷ 1000, which jumps back to zero every ~71.6 minutes. That `t_now` feeds settings save timing, FE polling, loud guard and the other loop timers. In the Main RPL it resets every 71.6 minutes of uptime. Changed. [in Main RPL build: µs-derived] [in bench build: ms counter] guard: none ref: R:SPECTRASYNQ_K1_FIRMWARE.ino:901 / B:SPECTRASYNQ_K1_FIRMWARE.ino:941
- **Settings file opened once at boot, before the LED task starts (`prepare_config_save_file()`).** See persistence/bridge_fs.h. Only in bench source. [in Main RPL build: no] [in bench build: yes, confirmed in image] guard: none ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:733
- **FE board housekeeping is called every main-loop pass (jack switch, 20 V power policy).** On the bench it only re-checks the audio-source choice, because no STUSB4500 power chip answers. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:997-999
- **Loud guard (automatic mic trim) is skipped while line-in is the active source.** On the mic it runs as before. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_LINE_SWITCH (inside K1_AUDIO_SOURCE_MIC + K1_LOUD_GUARD_V1) ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:1080-1084
- **Published audio frame now carries capture timestamps measured at the moment the sound was read** (sequence number, read time, newest and oldest sample time). Main RPL fills these with the publish time and a fixed estimate. "Last onset/beat time and strength" now persist between frames instead of resetting to 0 on frames without an onset or beat. Nothing in either device build reads these fields; only the emulator does. Changed. [in Main RPL build: old metadata] [in bench build: new metadata] guard: K1_AUDIO_FRAME_V1 (on in both) ref: R:SPECTRASYNQ_K1_FIRMWARE.ino:1202-1230 / B:SPECTRASYNQ_K1_FIRMWARE.ino:1251-1282
- **In the normal path (smart director and visual hooks off), the primary edge's settings are snapshotted once per frame before drawing.** Main RPL leaves the settings stack empty, so each lookup rebuilds from the live settings. Values are the same unless a setting changes mid-frame. The only reader of the stack depth is a diagnostic print (`rp_source=live_config` vs `stack:primary`). Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:1688-1689,1695
- **FE heartbeat LED tick (1 Hz on GPIO5) from the render task.** It returns immediately when no FE board is detected, as on the bench, so the bench strip on GPIO5 is not touched. Only in bench source. [in Main RPL build: no] [in bench build: yes, no-op without FE board] guard: K1_FE_BOARD_V1 ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:1476-1478
- **MabuTrace counters and scopes in the render path:** per-channel mode, effect body, saturated-pixel count, frame start. They compile to nothing without MabuTrace. Only in bench source. [in Main RPL build: no] [in bench build: no] guard: FEATURE_MABUTRACE (0 in both) / K1_TRACE_* no-op macros ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:457-464,474-478,1475
- **Performance-audit timing guarded against a zero start time.** Only in bench source. [in Main RPL build: no] [in bench build: no] guard: ENABLE_VP_PERF_AUDIT (0 in both) ref: B:SPECTRASYNQ_K1_FIRMWARE.ino:1710,1809
- **Emulator replay hooks: not in either device build.** These cover scenario start in setup, hop-end clock, publication/wait-shown handshake, render-loop start, consumed-frame record, per-hop frame clock and LED_FPS seam. The framework clock seam is also emulator-only and sits inside the unused K1_EFFECT_FRAMEWORK_V1. The bench also removes the Main RPL source's emulator-only overrides (boot animation off, mode 18, full master brightness, current cap 65535). [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: R:SPECTRASYNQ_K1_FIRMWARE.ino:786-801 / B:SPECTRASYNQ_K1_FIRMWARE.ino:512-516,704-708,839-841,943-946,1285-1289,1433-1436,1494-1501,1863-1870

## SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h (+166 / −5)

- **Line-in hand-over at the start of every audio hop (96 samples).** When line-in is selected, the hop is taken from the PCM1808 chip through the canonical 12.8 kHz path and the mic read is skipped. The mic's and the line's peak followers are kept separately, so unplugging returns the mic to its earlier level. Line-in silence uses its own test (k1_audio_input_state.h), and the 2-second line-in telemetry stream is off (on demand via `:fe_status`). Noise calibration holds the mic. On the bench this happens only after `:audio_src=line`. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_CANONICAL + K1_PCM1808_LINE_SWITCH ref: B:audio/i2s_audio.h:540-608
- **On mic hops, the PCM1808 buffer is emptied every hop,** so switching to line-in starts without a backlog. The bench therefore always runs the line-in capture task in the background. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_LINE_SWITCH ref: B:audio/i2s_audio.h:762-766
- **Each hop records when its samples were read** (sequence, read-return time, estimated oldest and newest sample time). It feeds the audio-frame metadata above; no device-build reader. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none (mic part inside K1_AUDIO_SOURCE_MIC) ref: B:audio/i2s_audio.h:122-123,501-503,572-578,704-724
- **VU level, and so the silence loudness check, measured on the rumble-filtered copy of the mic hop instead of the full-band signal.** This means sub-110 Hz drift the plate cannot show no longer holds the VU above the "music present" floor in a quiet room. The source comment cites B489 on 4 Nov: 30 % of LED frames lit while the peak read 0. Line-in hops keep full band. It adds a 4 KB buffer, and `audio_response_gain_apply_sample` appears only in the bench image. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_AP_SUBSONIC_HPF_V1 ref: B:audio/i2s_audio.h:1044,1057-1059,1897-1910
- **On line-in, the VU "music present" floor is a fixed line-in value (13 counts at −24 dB trim) instead of the mic's saved calibration.** The saved mic floor is never overwritten. The mic path's maths is unchanged. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_LINE_SWITCH ref: B:audio/i2s_audio.h:1931-1950
- **Build check: line-in switching requires FE board support.** Header include only. Only in bench source. [in Main RPL build: no] [in bench build: yes, compile-time only] guard: K1_PCM1808_LINE_SWITCH ref: B:audio/i2s_audio.h:36-41
- **Mic wiring diagnostics:** pull-up/pull-down pin test before start, DATA pull-up, live toggle count. Only in bench source. [in Main RPL build: no] [in bench build: no] guard: K1_IM69D_WIREDIAG_PULLUP_V1 ref: B:audio/i2s_audio.h:307-331,409-414,477-495

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_agc_dt_clock.h (+4 / −3)

- **Emulator-only: the AGC time step reads the replay's microsecond hop clock instead of its millisecond one.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:audio/k1_agc_dt_clock.h:82-85

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_frame.cpp (+6 / −9)

- **The "a new audio frame is ready" flag, shared by the audio core and the render core.** In Main RPL it is marked volatile, so each core re-reads it every time; that was added 20 Oct in 48719913, before the shared starting point. The bench source turns it back into a plain true/false (bench commit ba756b4e). Both builds compile this file. Changed. [in Main RPL build: volatile flag] [in bench build: plain flag] guard: K1_AUDIO_FRAME_V1 (on in both) ref: R:audio/k1_audio_frame.cpp:25-28,146-147,157,179,219 / B:audio/k1_audio_frame.cpp:25,143-144,154,176,216

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_ingress.h (+5 / −0)

- **The first line-in hop no longer zeroes the mic's calibrated sweet-spot floor (`SWEET_SPOT_MIN_LEVEL`)**, so the mic keeps its calibration after unplugging. In Main RPL this code path is not used: there is no line-in or USB audio. Only in bench source. [in Main RPL build: n/a] [in bench build: yes] guard: !K1_PCM1808_LINE_SWITCH ref: B:audio/k1_audio_ingress.h:45-47
- **Line-in hops mark the rumble-filtered copy as stale,** so line-in VU stays full band. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_AP_SUBSONIC_HPF_V1 ref: B:audio/k1_audio_ingress.h:122-124

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_input_state.h (+84 / −0, new file)

- **Holder for the per-hop capture timestamps (`K1AudioCaptureTiming`).** Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none ref: B:audio/k1_audio_input_state.h:8-14
- **Line-in "music present" floor (`K1_LINE_PRESENCE_FLOOR`),** computed from the measured idle of the illuminated line input. It is 13 counts at the bench trim. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none (used only under K1_PCM1808_LINE_SWITCH) ref: B:audio/k1_audio_input_state.h:23-38
- **Line-in silence test.** A hop is quiet when its loudness is at or below the floor. Silence is declared after the normal dwell (5 s) of continuous quiet. Isolated converter spikes do not restart the count; real music clears silence on the same hop. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none (called under K1_PCM1808_LINE_SWITCH; its trace counters are MabuTrace-only) ref: B:audio/k1_audio_input_state.h:44-84

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp (+3 / −0)

- **Tempo-lane experiment: publishes a pre-square-root novelty value to the tempo tracker.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_TEMPO_NOVELTY_LINEAR_V1 ref: B:audio/k1_audio_snapshot.cpp:34-36

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.h (+3 / −0)

- **Same experiment: an extra `tempo_novelty` field in the audio snapshot.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_TEMPO_NOVELTY_LINEAR_V1 ref: B:audio/k1_audio_snapshot.h:69-71

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_source.h (+12 / −2)

- **New audio-source mode, line switch (`K1_PCM1808_LINE_SWITCH`).** The mic is the default and the PCM1808 can take over at run time. It defines when the PCM1808 hardware counts as present and when its canonical path may feed analysis. A build check rejects mixing it with other source modes. Only in bench source. [in Main RPL build: no (value 0)] [in bench build: yes (value 1)] guard: K1_PCM1808_LINE_SWITCH ref: B:audio/k1_audio_source.h:19-28,48-50

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_emu_fixture.cpp (+930 / −105)

- **Emulator replay fixture, rewritten and extended.** Changes: scenario read from the ota_1 partition; scheduled production commands; hop-end application clock; publication and wait-shown handshake; render-loop start; power-limit, save and reject notes; host-command observation; seeded random numbers; selectable log port; onset/spectrum/tempo probe traces. The whole file is inside `#ifdef K1_EMU_FIXTURE`. Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:audio/k1_emu_fixture.cpp:3

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_emu_fixture.h (+74 / −21)

- **Emulator fixture interface:** new hooks for begin, wait-shown, render-loop, frame-based publication and consumption, power limit, save, reject, host command, application clock, seeded random, and log-port selection. Only the emulator calls it. Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:audio/k1_emu_fixture.h:13

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp (+3 / −0)

- **Tempo-lane experiment: stores novelty before its square root.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_TEMPO_NOVELTY_LINEAR_V1 ref: B:audio/k1_gdft_core.cpp:738-740

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.cpp (+13 / −1)

- **When the spectrum goes from completely empty (exact digital zero) back to sound, that first frame is treated as a restart, not as a drum hit.** Before this change the jump registered as a giant false attack, which skewed the per-band averages and suppressed the next real attacks. This happens even before the silence classifier has declared silence. Image: `sbv2_run` is 1138 → 1214 bytes. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_ONSET_V2 (on in both) ref: B:audio/k1_onset_beat.cpp:115,240-245,252-257

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_input.cpp (+44 / −5)

The whole file is compiled only in the bench build. The image lists `audio/k1_pcm1808_input.cpp` among objects only in the bench build. So every item here is [in Main RPL build: no].

- **Line-in compiled in "jack-switch" form.** The 96-sample line-in reader and its timing are available whenever the line switch is built. The buffer drain is shared with the old shadow mode. The boot log reads `[PCMING] source=im69d line=pcm1808 switch=jack`. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_CANONICAL / K1_PCM1808_LINE_SWITCH ref: B:audio/k1_pcm1808_input.cpp:473-475,527,622-624,636-638
- **The periodic 2-second line-in telemetry print was split into an on-demand print, used by `:fe_status`.** In the bench build the periodic call is not made. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_LINE_SWITCH ref: B:audio/k1_pcm1808_input.cpp:690-710,745
- **NFC chip-select hold skipped when its pin is −1, as on the bench.** On the bench, GPIO4 is the primary LED strip. Only in bench source. [in Main RPL build: no] [in bench build: yes (hold skipped)] guard: K1_PCM1808_NFC_CS_HOLD_PIN >= 0 ref: B:audio/k1_pcm1808_input.cpp:251-263,426
- **Build checks: line-in pins may not share a GPIO with the mic, and the NFC hold pin may not share one with an LED data line.** Compile-time only. Only in bench source. [in Main RPL build: no] [in bench build: yes, compile-time] guard: K1_PCM1808_PRESENT ref: B:audio/k1_pcm1808_input.cpp:27-34,242-249
- **Emulator-only early return (FE mic-only replay).** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FE_MIC_ONLY ref: B:audio/k1_pcm1808_input.cpp:397-403

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_input.h (+7 / −2)

- **Declarations for the jack-switch build:** the on-demand telemetry print, the canonical reader available under line switch, and the buffer drain available under line switch. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_PCM1808_PRESENT / K1_PCM1808_LINE_SWITCH / K1_PCM1808_CANONICAL ref: B:audio/k1_pcm1808_input.h:36-38,40,54,56-57

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_ring.h (+6 / −4)

- **Line-in sample buffer read and write positions now use explicit cross-core-safe loads and stores**, so the capture task and the audio loop always see each other's latest position. It is included only by k1_pcm1808_input.cpp, so it is compiled only in the bench build. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none (file used only under K1_PCM1808_PRESENT) ref: B:audio/k1_pcm1808_ring.h:24-26,60,75,98

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp (+312 / −112)

- **The tempo strength of the two frequencies checked per update is now computed from one shared copy of the recent-novelty history** instead of gathering it twice. It gives the same numbers: same samples, same order, same 4.0 clamp. It is cheaper and uses 2 KB more RAM. Default on (`K1_TEMPO_SHARED_WINDOW_V1` defaults to 1 in bench source). The image confirms `k1_compute_magnitude` only in Main RPL and `k1_compute_magnitude_from_window` only in the bench. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_TEMPO_SHARED_WINDOW_V1 (=1 default) ref: B:audio/k1_tempo.cpp:79-82,209-211,604-662,1148-1151
- **Every fixed tempo constant was moved into the new k1_tempo_spec.h with the same values.** That covers decay 0.999, lock 0.60, lobe 6, tactus 88/0.75, confidence prior 120/0.9, comb 4/0.8/0.7/0.6, CONF_V2 set, flywheel set, and winner switch 1.1 × for 5 emits. The literals 128, 0.5, 2, 1.1 and 5 are now named. There is no change in the numbers used. Changed (no behaviour change). [in Main RPL build: inline constants] [in bench build: header constants, identical] guard: none ref: B:audio/k1_tempo.cpp:6,91,105,110,137,151,161,282-298,306,367-380,548,557,1062,1122-1123
- **Tempo lane R1 experiments:** producer-owned silence with veto bits, spectral rhythm-presence test, pre-square-root novelty input, the lock-off fallback (locked and beat ticks withheld, confidence capped at 0.5999), the geometric/min comb and the 3:2 anti-comb. Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_TEMPO_SILENCE_FROM_PRODUCER_V1 / K1_TEMPO_SPECTRAL_PRESENCE_V1 / K1_TEMPO_NOVELTY_LINEAR_V1 / K1_TEMPO_LOCK_OFF_V1 / K1_TEMPO_COMB_PRODUCT_V1 / K1_TEMPO_COMB_ANTI32_V1 ref: B:audio/k1_tempo.cpp:8-10,404-469,534-541,565,732-773,785-816,964-973,1068-1078,1414-1419,1443-1470,1575-1588,1616-1633,1677-1680,1789-1802
- **Tempo stream probe timers for the presence test.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: ENABLE_TEMPO_STREAM (0 in both) ref: B:audio/k1_tempo.cpp:488-493,1605-1608,1673-1676,1921-1934

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.h (+37 / −1)

- **Comment-only description of confidence bands** (none below 0.30, tentative to 0.60, locked from 0.60). No code change. Only in bench source. [in Main RPL build: n/a] [in bench build: n/a] guard: none ref: B:audio/k1_tempo.h:22-28,32
- **Tempo lane R1 veto bits, gate readout and probe fields.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_TEMPO_SILENCE_FROM_PRODUCER_V1 / ENABLE_TEMPO_STREAM ref: B:audio/k1_tempo.h:38-60,138-140,144-146

## SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo_spec.h (+194 / −0, new file)

- **New single home for every tempo-tracker constant, with where each value came from.** The values active in the bench build are identical to the Main RPL's inline values (checked one by one). The new rhythm-presence constants (70 bins, 0.9, 0.05, 0.40, 267 frames, 2 events), the tentative band edges and the comb log-floor and anti-comb constants are read only by the switched-off experiments. Only in bench source. [in Main RPL build: no] [in bench build: yes (same values)] guard: none (experiment constants unused) ref: B:audio/k1_tempo_spec.h:20-194

## SPECTRASYNQ_K1_FIRMWARE/control/k1_show_state.cpp (+6 / −0)

- **Emulator-only note when a show is saved.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:control/k1_show_state.cpp:18-20,270-272

## SPECTRASYNQ_K1_FIRMWARE/diag/k1_trace.h (+30 / −3)

- **MabuTrace only:** saturated-pixel counter, and the trace export now retries a busy serial port for up to 1 s and reports failure instead of dropping bytes. Not in either device build. [in Main RPL build: no] [in bench build: no] guard: FEATURE_MABUTRACE (0 in both) ref: B:diag/k1_trace.h:14,18-20,26-52

## SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h (+74 / −16)

- **Settings file kept open from boot and reused for every save,** instead of opened and closed each time. It is recreated if it is not exactly 512 bytes. Factory reset and restore-defaults close it first. Image: `prepare_config_save_file` exists only in the bench. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none ref: B:persistence/bridge_fs.h:99-117,127,179
- **Each settings save writes the 512-byte record in one call and then flushes, instead of 512 one-byte writes and a close.** The record is prepared before the LEDs are paused, so the pause is shorter. The bytes on flash are identical. Changed. [in Main RPL build: byte-by-byte] [in bench build: one write] guard: none ref: R:persistence/bridge_fs.h:174-218 / B:persistence/bridge_fs.h:200-274
- **A failed open, seek or short write now re-queues the save for 5 s later.** Main RPL gives up until the next settings change. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: none ref: B:persistence/bridge_fs.h:233-234,237-243,256-261
- **MabuTrace scope markers around save stages** (no-ops) and a whitespace-only edit in `save_config_delayed`. Not in either device build (markers). [in Main RPL build: no] [in bench build: no] guard: K1_TRACE_* no-op macros ref: B:persistence/bridge_fs.h:22,212-224,249-252,269-272,284
- **Emulator-only save note and log port.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:persistence/bridge_fs.h:23-25,274-276,700

## SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp (+6 / −0)

- **Emulator-only report of the LED power limit when `max_current` is set.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:serial/serial_cmd_handlers.cpp:25-27,418-420

## SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp (+79 / −3)

- **FE commands accepted:** `:fe_status`, `:pd_status` and `:pd_nvm_write` work without a value, and `:audio_src=auto|mic|line` is routed to FE board support. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:serial/serial_menu.cpp:122-124,2915-2927,3189-3193
- **Performance-audit start prints flash chip ID, flash size, CPU speed and PSRAM once.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: ENABLE_VP_PERF_AUDIT (0 in both) ref: B:serial/serial_menu.cpp:37-40,1168-1203
- **`:build` prints a release tag.** Not in either device build, because no `K1_BUILD_TAG` is set in either. [in Main RPL build: no] [in bench build: no] guard: K1_BUILD_TAG ref: B:serial/serial_menu.cpp:2326-2329
- **Trace dump reports "Export failed" on a failed export.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: FEATURE_MABUTRACE ref: B:serial/serial_menu.cpp:2666-2668
- **Emulator-only host-command observation and log port.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:serial/serial_menu.cpp:80-82,2653,4186-4207

## SPECTRASYNQ_K1_FIRMWARE/serial/serial_tx.cpp (+4 / −5)

- **Emulator-only: the rejected-command note moved into the fixture.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:serial/serial_tx.cpp:9-11,62

## SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def (+6 / −0)

- **Four typed commands registered:** `fe_status`, `pd_status`, `pd_nvm_write` (marked as writing to a chip) and `audio_src` (marked as disruptive). Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:serial/serial_typed_cmd_table.def:243-248

## SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_dispatch.cpp (+8 / −0)

- **Wrapper that sends those four commands to FE board support.** Image: `serial_typed_wrap_fe_board` exists only in the bench. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:serial/serial_typed_dispatch.cpp:57-59,176-180

## SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_dispatch.h (+3 / −0)

- **Declaration of that wrapper.** Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:serial/serial_typed_dispatch.h:131-133

## SPECTRASYNQ_K1_FIRMWARE/system/config_types.h (+17 / −0)

- **Mode list gains 14 entries, 38–51, for the extra test effects.** The mode count is 52 on the bench vs 38 on the Main RPL. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FX_BATTERY ref: B:system/config_types.h:257-272

## SPECTRASYNQ_K1_FIRMWARE/system/constants.h (+17 / −16)

- **Main RPL LED pins rewired:** primary data GPIO2 / second line GPIO3, secondary GPIO5 / GPIO6. Without that commit the branch falls back to 15/16/17/18. The bench build does not use this branch at all; it takes the bench-reference branch (LEDs GPIO4/5). Only in Main RPL source (the pin commit). [in Main RPL build: yes] [in bench build: no (different pin-map branch)] guard: K1_MAIN_RPL_PINMAP_V1 ref: R:system/constants.h:449-462 / B:system/constants.h:449-452
- **Build check that stops the bench env from compiling against the Main RPL WS2816 pin map.** Compile-time only, and that branch is not entered in either build. Only in bench source. [in Main RPL build: no] [in bench build: no] guard: K1_FE_BENCH_B489_V1 inside the Main RPL pin-map branch ref: B:system/constants.h:455-457
- **Comment only: GPIO10 is PCM1808 data on the FE board.** No value change. Only in bench source. [in Main RPL build: n/a] [in bench build: n/a] guard: none ref: B:system/constants.h:490
- **Mic wiring diagnostic that swaps the CLK and DATA pins.** The normal bench mic pins (CLK 14 / DATA 13) are unchanged. Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_IM69D_WIREDIAG_SWAP_V1 ref: B:system/constants.h:533-541

## SPECTRASYNQ_K1_FIRMWARE/system/globals.h (+18 / −1)

- **4 KB buffer holding the rumble-filtered copy of each mic hop, plus its "fresh" flag**, used by the VU/silence change in i2s_audio.h. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_AP_SUBSONIC_HPF_V1 ref: B:system/globals.h:260-265
- **Silence dwell (continuous quiet before the plate darkens) is now set through a bench-switchable default.** The value is 5000 ms in both branches, so there is no value change. Changed (no behaviour change). [in Main RPL build: 5000 ms] [in bench build: 5000 ms] guard: K1_FE_BENCH_B489_V1 ref: R:system/globals.h:830 / B:system/globals.h:840-847
- **Tempo-lane experiment: pre-square-root novelty history.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_TEMPO_NOVELTY_LINEAR_V1 ref: B:system/globals.h:106-109

## SPECTRASYNQ_K1_FIRMWARE/system/k1_fe_board.cpp (+627 / −0, new file)

The whole file is compiled only in the bench build (image: `system/k1_fe_board.cpp` is among the objects only in the bench build). On the B489 bench no STUSB4500 answers, so the board reports `stusb4500=absent fe_board=0 outputs=passive`.

- **FE board detection at boot.** It looks for the STUSB4500 USB-C power chip on I2C (GPIO41/42). If found, it sets up the FE power, jack and status pins. If absent, as on the bench, it releases I2C and drives none of them, and the source stays on the mic. Only in bench source. [in Main RPL build: no] [in bench build: yes (absent path)] guard: K1_FE_BOARD_V1 ref: B:system/k1_fe_board.cpp:471-533
- **20 V power policy.** LED power is allowed only while the 20 V "power good" signal is high: power permit first, LED enable 20 ms later, both off the moment it drops. If 20 V drops 3 times within 10 s while lit, the LEDs latch off until the board is replugged. It reads back the LED bank eFuse status and the PD fault, and repeats a "why dark" line every 60 s on 5 V only. Inactive on the bench (no FE board). Only in bench source. [in Main RPL build: no] [in bench build: compiled, inactive] guard: K1_FE_BOARD_V1 ref: B:system/k1_fe_board.cpp:325-402
- **Audio source choice.** With an FE board, a plugged 3.5 mm jack (100 ms debounce) selects line-in. `:audio_src=line|mic|auto` overrides until reboot. Line-in is refused if the PCM1808 clock check failed at boot. On the bench, auto means mic, and `:audio_src=line` switches to line-in. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:system/k1_fe_board.cpp:405-446,555-569,609-622
- **1 Hz heartbeat LED on GPIO5.** Only with an FE board, so it is not driven on the bench. Only in bench source. [in Main RPL build: no] [in bench build: compiled, inactive] guard: K1_FE_BOARD_V1 ref: B:system/k1_fe_board.cpp:542-553
- **Serial tools.** `:fe_status` prints power, source, jack and line-in telemetry. `:pd_status` prints the negotiated USB-C contract. `:pd_nvm_write[=golden]` programs the STUSB4500 to 5 V 0.5 A / 20 V 3 A / 20 V 5 A once, with read-back verify. Without an FE board, as on the bench, the PD tools answer "not detected". Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:system/k1_fe_board.cpp:30-91,124-322,571-608

## SPECTRASYNQ_K1_FIRMWARE/system/k1_fe_board.h (+86 / −0, new file)

- **FE board pin defaults and interface:** LED_ENABLE 1, POWER_PERMIT 2, heartbeat 5, LED_PG_A/B 6/7, 20 V PG 38, PD fault 39, jack 40, I2C 41/42, chip address 0x28. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:system/k1_fe_board.h:25-86

## SPECTRASYNQ_K1_FIRMWARE/system/system.h (+38 / −9)

- **When settings are saved (`check_settings`).** Main RPL saves 5 s after the last change, even during music, and each save briefly pauses the LEDs. The bench saves when the room is silent and 5 s have passed, or after 60 s of unsaved changes whatever is playing. It retries a failed write no sooner than every 5 s and uses a wrap-safe time compare. Image: `check_settings` is 47 → 150 bytes. Changed. [in Main RPL build: 5 s rule] [in bench build: quiet-or-60 s rule] guard: none ref: R:system/system.h:681-694 / B:system/system.h:692-723
- **At every boot the LED type is forced to single-wire and the colour order to GRB,** so settings saved by earlier WS2816 images cannot bring back the 80/80 split or a packed colour order. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BENCH_B489_V1 ref: B:system/system.h:481-486
- **FE board start-up runs after the PCM1808 start,** so line-in availability is known first. Only in bench source. [in Main RPL build: no] [in bench build: yes] guard: K1_FE_BOARD_V1 ref: B:system/system.h:639-641
- **Header includes for FE board and trace.** No behaviour change. Only in bench source. [in Main RPL build: no] [in bench build: yes, include only] guard: K1_PCM1808_PRESENT / none ref: B:system/system.h:11,20

## SPECTRASYNQ_K1_FIRMWARE/system/utilities.h (+7 / −0)

- **Emulator-only seeded random numbers, so replays repeat exactly.** Not in either device build. [in Main RPL build: no] [in bench build: no] guard: K1_EMU_FIXTURE ref: B:system/utilities.h:79-86

---

## Index of files covered (38, one section each above)

- SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
- SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_agc_dt_clock.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_frame.cpp
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_ingress.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_input_state.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_source.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_emu_fixture.cpp
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_emu_fixture.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.cpp
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_input.cpp
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_input.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_ring.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.h
- SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo_spec.h
- SPECTRASYNQ_K1_FIRMWARE/control/k1_show_state.cpp
- SPECTRASYNQ_K1_FIRMWARE/diag/k1_trace.h
- SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h
- SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp
- SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp
- SPECTRASYNQ_K1_FIRMWARE/serial/serial_tx.cpp
- SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def
- SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_dispatch.cpp
- SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_dispatch.h
- SPECTRASYNQ_K1_FIRMWARE/system/config_types.h
- SPECTRASYNQ_K1_FIRMWARE/system/constants.h
- SPECTRASYNQ_K1_FIRMWARE/system/globals.h
- SPECTRASYNQ_K1_FIRMWARE/system/k1_fe_board.cpp
- SPECTRASYNQ_K1_FIRMWARE/system/k1_fe_board.h
- SPECTRASYNQ_K1_FIRMWARE/system/system.h
- SPECTRASYNQ_K1_FIRMWARE/system/utilities.h
- platformio.ini
- scripts/platformio/k1_build_provenance.py
- scripts/platformio/k1_device_identities.json
