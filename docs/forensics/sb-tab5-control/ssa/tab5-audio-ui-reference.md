# SSA Evidence Note: Tab5 Audio/UI Reference

Task ID: `tab5-audio-ui-reference`  
Date: 2026-06-09  
Verdict: `VERIFIED_WITH_CAVEATS`  
Scope: read-only archaeology in `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5` plus adjacent PIPdeck examples. No build, upload, flash, serial monitor, or device audio proof was run.

## Commands Rerun

- Required command:
  `rg -n "Speaker|tone|beep|sound|audio|click|tap|feedback|wav|buzz" /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5 -S`
- High-signal result: 814 matches across 51 files. The active firmware hits converge on `prototype/tab5_stats_prototype/audio_feedback.*`, `command_simulator.cpp`, `stats_harness.cpp`, `tab5_stats_prototype.ino`, and `tools/tab5_stats_validate.py`.
- Adjacent examples checked:
  - `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay`
  - `/Users/spectrasynq/Workspace_Management/Software/PipDeck-Experiment-v2`

## Source State Caveats

- PIPdeck primary checkout is dirty on `feature/tab5-instrument-v0-port` at `2b72280`; `audio_feedback.cpp` is modified locally.
- The accepted PIPdeck `main` baseline still documents A1 audio as merged: deterministic M5Unified tone patterns, non-blocking scheduler, tones only, and no OGG/MP3 decode (`/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/CHANGELOG.md:73-78`, `docs/workstreams/ACTIVE_LANES.md:18-33`, `docs/workstreams/ACTIVE_LANES.md:83-88`).
- Current dirty PIPdeck adds an ESP32-P4 Tab5 codec/I2C bring-up block to `audio_feedback.cpp`; treat that as WIP hardware seam until separately compiled and heard on the Tab5 (`audio_feedback.cpp:42-130`, diff adds 98 lines).
- SensoryBridge current checkout is dirty at `b613de5`; AP/WebSocket files are local source truth in this worktree, not proven-current release state.

## PIPdeck Active Audio Implementation

Active prototype seam:

- `prototype/tab5_stats_prototype/audio_feedback.h:6-29` defines semantic patterns and the small API: `audio_feedback_init`, `audio_feedback_poll`, status/mute/volume, `audio_feedback_play_pattern`, name/parse helpers.
- `prototype/tab5_stats_prototype/audio_feedback.cpp:23-31` defines fixed tone patterns for `TAP`, `REQUEST`, `APPLIED`, `ERROR`, `ATTENTION`, and `MODE`.
- `prototype/tab5_stats_prototype/audio_feedback.cpp:151-155` plays tones through `M5.Speaker.tone(...)`.
- `prototype/tab5_stats_prototype/audio_feedback.cpp:158-188` initialises speaker state; current dirty P4 path configures Tab5 audio pins/codec first, non-P4 path calls `M5.begin(cfg)`.
- `prototype/tab5_stats_prototype/audio_feedback.cpp:191-219` is the non-blocking scheduler: poll checks elapsed `millis()`, advances fixed steps, and does not delay the LVGL loop.
- `prototype/tab5_stats_prototype/audio_feedback.cpp:237-269` implements volume, mute, stop, and pattern start; mute suppresses playback and clears the active pattern.
- `prototype/tab5_stats_prototype/tab5_stats_prototype.ino:19-25` warns that display/touch ownership is fragile and audio is initialised after the proven standalone M5GFX substrate.
- `prototype/tab5_stats_prototype/tab5_stats_prototype.ino:118-139` calls `audio_feedback_init()` in `setup()` and `audio_feedback_poll()` in `loop()`.

Call sites and event meaning:

- `prototype/tab5_stats_prototype/command_simulator.cpp:139` plays `APPLIED` on applied result and `ERROR` otherwise.
- `prototype/tab5_stats_prototype/command_simulator.cpp:151`, `:160`, and `:191` play `ERROR` on invalid request, queue full, and instrument lifecycle rejection.
- `prototype/tab5_stats_prototype/command_simulator.cpp:216` plays `REQUEST` after a command is accepted into the queue.
- `prototype/tab5_stats_prototype/stats_harness.cpp:244-265` polls audio while flushing LVGL and waiting for command results.
- `prototype/tab5_stats_prototype/stats_harness.cpp:1495-1550` exposes `AUDIO_STATUS`, `AUDIO_VOLUME`, `AUDIO_MUTE`, and `AUDIO_TEST`.
- `tools/tab5_stats_validate.py:567-585` validates audio serial commands, mute suppression, all six patterns, bad pattern rejection, and final `last_pattern=APPLIED`.
- `tools/tab5_stats_validate.py:1484-1491` records the intended policy: `request` on command queue accept, `applied` on applied result, `error` on rejection or explicit test, and `tap`/`attention`/`mode` only by explicit audio test to avoid double-fire.

## What To Avoid From PIPdeck

- Do not use `PipDeck-Firmware/prototype/stats_tab_skeleton/` as precedent. It is documented as an archive/delete candidate and a strict subset behind the live prototype (`docs/product/DEPRECATION_MANIFEST.md:18-21`).
- Do not treat `prototype/audio-files`, `manifests/*`, `audition/index.html`, or `tools/pipdeck_audio_manifest.py` as firmware playback precedent. The audio asset design explicitly says the current firmware remains fixed M5Unified tones, loads no assets, decodes no MP3/OGG, and uses no SD media (`docs/superpowers/specs/2026-05-29-pipdeck-audio-asset-library-design.md:209-219`).
- Do not add SD WAV, OGG, MP3, raw embedded cue playback, microphone, or AI-generated sound in the first SensoryBridge Tab5 slice; those are explicit non-goals or future options in the PIPdeck spec (`docs/superpowers/specs/2026-05-29-pipdeck-audio-asset-library-design.md:48-59`, `:221-230`).
- Do not let audio become command truth, validation truth, or CHECK truth. PIPdeck says this directly (`docs/superpowers/specs/2026-05-29-pipdeck-audio-asset-library-design.md:41-47`), and PIPdeck AGENTS says audio is UX only.
- Do not blindly import `M5.begin()` or the dirty ESP32-P4 codec block into SensoryBridge Tab5. PIPdeck's own lane notes record that M5 speaker initialisation previously broke or was deferred around the display/touch substrate (`docs/workstreams/ACTIVE_LANES.md:43-52`), and the current P4 block is dirty WIP.

## Adjacent Example Findings

- `PIPdeck-Tab5-A3.3-confirm-overlay` repeats the accepted baseline: `audio_feedback.*` fixed M5Unified tones, command-simulator request/applied/error hooks, serial audio harness, and no firmware audio-file playback.
- `PipDeck-Experiment-v2` produced no active M5/LVGL firmware speaker seam. Hits were mainly bundled web assets, React/node dependency text, a terminal beep in `shared/prompt-DYnaB1Nb.mjs`, and a Python hotkey harness. It is not a Tab5 audio firmware precedent.

## SensoryBridge API/Hardware Seam

Current SensoryBridge source seam:

- `docs/protocol/k1-ws-contract.yaml:1-27` defines AP-mode WebSocket `/ws`, token `k1-tab5`, `k1.hello`, `k1.state.get`, and `k1.control.set`.
- `docs/protocol/k1-ws-contract.yaml:29-77` defines the reusable controls: primary/secondary mode, palette, photons, chroma, mood, and `scene.smart`.
- `docs/protocol/k1-rest-contract.yaml:5-9` says REST has no paths and must not be added for this control slice.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:392-394` starts K1 wireless after secondary LED init.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:467-470` polls wireless adjacent to serial command handling, before the audio/GDFT work.
- `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:528-539` starts `WiFi.mode(WIFI_AP)`/SoftAP and WebSocket `/ws`.
- `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp:566-584` drains a bounded number of requests per AP tick and applies them through `k1_wireless_control_apply`.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.h:11-46` defines the fixed command/result/state records.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp:210-225` allowlists only the control fields in the contract.
- `SPECTRASYNQ_K1_FIRMWARE/control/sb_wireless_control.cpp:235-331` applies values via existing mode, palette, photons, chroma, mood, secondary, and Smart Scene semantics.

Recommended implementation seam:

1. Put UI sound on the Tab5 controller only, behind a PIPdeck-style `audio_feedback` module with semantic enum patterns, `init/poll/play/mute/volume/status`, and fixed static pattern tables.
2. Trigger `REQUEST` when the Tab5 has accepted a user action into its outbound queue, but treat it as UX only.
3. Trigger `APPLIED` or `ERROR` only from K1 `k1.control.result.ok`, not from touch down and not from local optimism.
4. Keep all SensoryBridge device control on the existing AP-only WebSocket contract. Do not add REST, audio commands, or speaker side effects to K1 firmware.
5. Preserve Tab5 display/touch ownership and timing first. Initialise speaker after the proven display/touch stack and poll audio from the UI loop; do not block LVGL or command transport.
6. If the target Tab5 is ESP32-P4, use the current dirty PIPdeck codec/I2C block only as a candidate hardware seam to verify, not as a proven baseline: I2C1 SDA 31/SCL 32, codec `0x10`, IO expander `0x43`, I2S MCK 30/BCK 27/WS 29/DOUT 26, `I2S_NUM_0`.

## Bottom Line

Reuse PIPdeck's semantic, non-blocking, UX-only tone scheduler shape. Avoid PIPdeck's asset-library future work, archived skeleton, web experiments, and unverified dirty ESP32-P4 codec code as active precedent. For SensoryBridge Tab5, audio belongs in the Tab5 UI client, while real state and command truth remain the K1 AP-only WebSocket `k1.control.result` seam.
