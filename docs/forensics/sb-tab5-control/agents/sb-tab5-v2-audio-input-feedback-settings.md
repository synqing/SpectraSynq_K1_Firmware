# SB-TAB5-V2-AUDIO-INPUT-FEEDBACK-SETTINGS

Task ID: `SB-TAB5-V2-AUDIO-INPUT-FEEDBACK-SETTINGS`

Evidence question: Which audio, input-feedback, and user-settings elements are worth screen real estate in a professional SB Tab5 controller, and where should they live?

## Verdict

Status: `NOT_VERIFIED` as a final product layout. This pass did not run a Tab5, open a browser, flash K1, open serial, or observe live touch/audio behaviour.

Static allocation verdict: source-backed enough to separate high-value feedback from settings creep. Audio trust and command feedback deserve pixels; backend selectors, WiFi/settings theatre, one-tap calibration/reset, and raw diagnostic audio do not belong on the product screen.

## Source Scope

- Current SB source authority is `SPECTRASYNQ_K1_FIRMWARE`; the AGENTS-listed `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`, `docs/protocol/k1-ws-contract.yaml`, and `docs/protocol/k1-rest-contract.yaml` are absent in this checkout.
- Existing SB Tab5 scout artefacts were used as cross-checks, especially the journey map, control map, touch map, reset plan, adversarial review, physical pixel report, and PIPDeck source pass.
- Donor PIPDeck evidence was inspected for command acknowledgement, tone feedback, confirmation, settings, and harness patterns. Donor semantics were not treated as current SB implementation.

## Allocation Summary

| Element family | Keep | Test | Cut |
|---|---|---|---|
| Audio/readback | First-screen read-only `K1 Pulse`: hearing/not-hearing, silence, beat confidence, onset/bass onset, calibration validity/source, and optional compact audio energy. | Diagnostics drawer for AP fields: SSL, DC, max_raw, follower, peak_scaled, silent_scale, bpm/conf/lock/phase/beat, onset/bass. Tempo/BPM lock can be tested as a compact badge only if stale/error behaviour is implemented. | Audio backend selector, raw waveform/spectrum on Home, sample-rate/chunk-size/sensitivity/chroma-profile controls in product UI, any "audio live" badge without a real bridge/source age. |
| Input feedback | Every actionable control gets local touch-down, queued/pending, applied, refused, stale/disconnected states. Put a transient command feedback strip near the footer, not a permanent status wall. | Toasts and command result sounds if they never cover primary controls and include failure/stale results. Queue overflow/backpressure indication if the bridge is asynchronous. | Fire-and-forget controls, decorative pulses that look like state, green "live" pills from simulated data, hidden side effects, duplicate homes for the same control. |
| Haptic/audio cue | Reserve Settings/Feedback screen real estate for optional Tab5 UI audio feedback toggle/volume if the Tab5 audio path is verified. Visual feedback remains primary. | Subtle TAP/REQUEST/APPLIED/ERROR patterns, command acknowledgement style, and cue volume. Haptic/off/subtle/strong segmented control only if hardware support is proven. | Always-on sounds, sound as the only destructive confirmation, haptic controls without verified hardware path, cue controls on the show-control Home screen. |
| Brightness/loudness/settings | Home keeps K1 `Photons` as the show brightness control. Settings keeps Tab5 display brightness. Read-only loudness/VU belongs in `K1 Pulse`, not as a user gain control. | Secondary photons in Channel/Mix; UI audio cue volume in Settings; profiles only for controller settings that have real persistence. | K1 STA/WiFi network settings, firmware update, multi-K1 pairing, loudness/AGC tuning as casual controls, one-tap calibration/reset/defaults/clear-cal. |

## Recommended Placement

### Home / Show Control

Keep this page focused on the live show loop:

- Header: connection truth labelled `serial bridge`, `API needed`, `simulated`, or `live`; firmware/chip/status if actually read.
- Centre-origin LGP preview: schematic unless final-byte/render readback exists.
- Primary show controls: enabled mode, primary `Photons`, chroma, mood, palette mode/index, Smart Scene.
- `K1 Pulse` strip: read-only hearing/silence, beat confidence, onset/bass onset, calibration valid/source, optional compact energy/novelty.
- Command feedback strip: last command pending/applied/refused/stale with source age.

Evidence:

- `SBAudioSnapshot` carries `peak_scaled`, `vu_level`, novelty, spectral energy, low/mid/high, chroma strength, and silence: `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h:57-80`.
- `SBOnsetBeatEvent` carries onset, bass onset, beat phase/confidence, and V2 percussive channel fields: `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h:82-115`.
- `sb_audio_snapshot_update()` populates peak, VU, novelty, silence, band energy, spectrum, and chord/chroma data from live firmware state: `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp:28-104`.
- `smart_status` prints audio novelty/energy, event age, onset, bass onset, and beat confidence: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1052-1125`.
- AP instrumentation prints calibration, peak/silence/loudness-derived state, tempo lock, beat, onset, and bass fields when diagnostic stream is enabled: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:470-493`.
- Primary `PHOTONS`, `CHROMA`, `MOOD`, mode, palette mode/index are real config fields: `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:159-201`.
- Typed primary controls clamp and queue delayed persistence for photons/chroma/mood/palette: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3270-3338`.

### Channel / Mix

Use a secondary or advanced page for dual-strip behaviour:

- Secondary enable, mode, photons, chroma, mood, palette mode/index.
- EdgeMixer enable/mode/strength only when the UI visually explains primary/secondary interaction.
- Secondary persistence must be labelled runtime/global unless a real persist path is added.

Evidence:

- Secondary commands and `secondary_status` cover enable, mode, photons, chroma, mood, saturation, prism, mirror/reverse, base coat, palette mode/index: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3962-4220`.
- `edge_status` is compact: enabled, mode, strength: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1128-1138`.
- `smart_scene` applies Smart Director, hooks, and EdgeMixer runtime config and clears manual control; it does not become a settings page: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1140-1210`.

### Diagnostics / Recovery

Keep raw audio/status detail here, not on Home:

- AP stream and `smart_status`/`edge_status`/`vp_status`.
- Raw audio/frame dumps only for diagnostic lanes.
- Guarded calibration readiness and recovery flow.
- Explicit stop-streams action.

Evidence:

- Row-1 serial commands include safe status/readback rows and safety-classed reset/calibration/destructive rows: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:31-61`.
- Dangerous/calibration rows are statically blocked from immediate hotkeys: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2426-2446`.
- Typed `start_noise_cal` prints guidance; the N/Y silence-window path is the intended calibration trigger: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2262-2267`.
- The project rule forbids auto-firing calibration without Captain-confirmed silence: `.claude/CLAUDE.md:41-47`.

### Settings / Feedback

Settings should configure the controller, not turn into a hidden K1 engineering console:

- Tab5 display brightness.
- UI audio feedback toggle and volume.
- Touch feedback mode: off/subtle/strong only after hardware support is proven.
- Command acknowledgement style: visual-only/subtle/full, with visual always primary.
- Profiles only if they map to real controller settings and persistence.
- Read-only transport/network note: K1 is AP-only and current SB has no implemented wireless backend.

Evidence:

- The reset plan already assigns display, audio feedback, input feedback, profiles, and read-only network note to Settings/Feedback: `docs/forensics/sb-tab5-control/2026-06-07-zone-composer-proposal-v2-element-rationale.md:255-274`.
- The same rationale requires touch-down, queued, applied, refused, and stale/disconnected feedback for controls, and limits audio/haptic to optional feedback choices: `docs/forensics/sb-tab5-control/2026-06-07-zone-composer-proposal-v2-element-rationale.md:304-319`.
- PIPDeck has an active audio feedback module and harness category, but it is command/UI feedback, not SB show audio: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/product/BUILD_OF_MATERIALS.md:11-29`, `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/product/BUILD_OF_MATERIALS.md:40-46`, `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/product/BUILD_OF_MATERIALS.md:80-96`.
- PIPDeck tone feedback defines TAP/REQUEST/APPLIED/ERROR/ATTENTION/MODE patterns: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/audio_feedback.h:6-29`, `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/audio_feedback.cpp:23-31`.
- PIPDeck command simulation plays REQUEST on enqueue and APPLIED/ERROR on result: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/command_simulator.cpp:118-147`, `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/command_simulator.cpp:149-224`.
- PIPDeck visual constitution keeps motion/audio purposeful: one request cue, brief applied tone, and no ornamental animation: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs/product/VISUAL_CONSTITUTION.md:87-95`.

## Specific Keep / Test / Cut Decisions

| Candidate | Verdict | Placement | Rationale |
|---|---|---|---|
| Hearing / not hearing | Keep | Home `K1 Pulse` | Directly answers whether K1 is responding to room audio. Source fields exist through peak/VU/silence. |
| Silence | Keep | Home `K1 Pulse`, Diagnostics detail | Critical to avoid misreading quiet-room behaviour and to gate calibration readiness. |
| Beat confidence | Keep | Home compact badge | High-value product feedback; current `smart_status` prints `SMART_BEAT_CONFIDENCE`. |
| Onset / bass onset | Keep | Home compact pulse | Explains why lights are reacting or not reacting; source-backed through `SBOnsetBeatEvent`. |
| Calibration validity/source | Keep | Header or `K1 Pulse`; Recovery detail | Important trust/readiness state, but not a button. |
| BPM / tempo lock | Test | Home tiny badge or Diagnostics | Source-backed through AP/semantic fields, but can overclaim musical truth if stale/weak lock handling is poor. |
| Raw AP stream metrics | Test | Diagnostics only | Valuable for agents; too dense and lab-like for Home. |
| Loudness/VU history graph | Test | Home micro sparkline or Diagnostics | Could help trust audio input, but must not become a fake analyser or steal show-control pixels. |
| Primary `Photons` | Keep | Home primary control | This is the real SB show-brightness control; label as `Photons` or `Brightness (Photons)`. |
| Tab5 display brightness | Keep | Settings/Feedback | Separate controller comfort/battery from K1 light output. |
| UI audio cue toggle/volume | Test | Settings/Feedback | Donor has tone module, but SB controller needs on-glass verification; default should be subtle/off-controllable. |
| Haptic feedback | Cut for MVP / Test only after hardware proof | Settings/Feedback only | No current verified SB/Tab5 haptic path found in this pass. |
| Command acknowledgement style | Keep | Settings/Feedback plus command strip | Professional controller feedback needs pending/applied/refused/stale states. |
| Noise calibration | Cut from Home; guarded Recovery only | Diagnostics / Recovery admin | Known poison path during music; typed command itself only prints guidance. |
| Reset / factory / defaults / clear-cal | Cut from MVP product surface | Recovery only if explicitly required | Destructive or irreversible; must use confirmation and source-backed recovery playbook. |
| K1 WiFi/STA/network settings | Cut | Nowhere in SB MVP | Current SB has no network backend, and K1 remains AP-only. |
| Audio backend selector | Cut | Nowhere | No source-backed product selector exists; exposing it creates fake choice and support risk. |
| Sample rate / samples per chunk / sensitivity | Cut from product; Diagnostics/admin only if ever exposed | Diagnostics / engineering | These touch audio-analysis semantics and can damage behaviour if casual. |

## Failure Modes To Avoid

- Treating audio readback as frivolous. It is the main trust surface for a music visualiser: "K1 hears the room and has a beat/onset signal" is product feedback, not debug trivia.
- Treating every audio metric as first-screen material. The first screen needs a pulse, not an oscilloscope.
- Conflating K1 light brightness (`PHOTONS`) with Tab5 display brightness or UI cue volume.
- Making Settings a dumping ground for unsupported WiFi, backend, reset, calibration, or diagnostic controls.
- Letting sound/haptic feedback replace visible command result states.
- Showing any live-looking audio/WS/API state without source age, stale state, and failure behaviour.

## Required Re-run Commands Used

```bash
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '1,220p' progress.md
sed -n '1,180p' .claude/handoff.md
sed -n '1,220p' firmware-v3/docs/reference/codebase-map.md
sed -n '1,220p' firmware-v3/docs/reference/fsm-reference.md
sed -n '1,220p' docs/protocol/k1-ws-contract.yaml
sed -n '1,220p' docs/protocol/k1-rest-contract.yaml
rg -n "Tab5|PIPDeck|audio feedback|input feedback|haptic|settings|brightness|loudness|reset|journey|controller|status" /Users/spectrasynq/.codex/memories/MEMORY.md
rg -n "stream_audio|audio_vu|vu_level|loud|silence|sweet|noise_cal|calibration|brightness|BRIGHTNESS|sbs\\(|AP_STREAM|APCAP|VPAB|status|dump|smart_scene|secondary|palette|preset|WiFi|wifi|AP_ONLY|Access Point|settings|CONFIG" SPECTRASYNQ_K1_FIRMWARE docs tests scripts -g '!*.bin' -g '!*.png' -g '!*.jpg'
rg -n "audio|Audio|beep|BEEP|tone|buzzer|BUZZ|haptic|vibrat|click|cue|feedback|play|sound|speaker|success|error|confirm" /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/docs /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/tools -S
nl -ba docs/forensics/sb-tab5-control/agents/sb-k1-control-journey-map.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-control-map.md | sed -n '1,240p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md | sed -n '1,240p'
nl -ba docs/forensics/sb-tab5-control/agents/tab5-sb-ui-adversarial-review.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/tab5-physical-pixel-reality.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/2026-06-07-zone-composer-proposal-v2-element-rationale.md | sed -n '250,325p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h | sed -n '1,130p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp | sed -n '1,130p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/sb_semantic_state.h | sed -n '1,120p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '140,260p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '460,505p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1040,1220p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1600,1685p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2240,2275p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2420,2490p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '3230,3345p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '3960,4225p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def | sed -n '1,75p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/config_types.h | sed -n '150,205p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h | sed -n '60,110p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/system.h | sed -n '520,545p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/constants.h | sed -n '210,220p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/persistence/knobs.h | sed -n '1,95p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/audio_feedback.h | sed -n '1,180p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/audio_feedback.cpp | sed -n '1,240p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/audio_feedback.cpp | sed -n '237,330p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/command_simulator.cpp | sed -n '1,150p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/command_simulator.cpp | sed -n '149,235p'
```

Note: `rg --files` failed in this shell as a local grep/rtk ambiguity, so `/usr/bin/find` was used for file discovery where needed.

## Method Risk

This is a static/read-only allocation pass. It does not verify final Tab5 layout, touch target comfort, audio cue acceptability, haptic capability, serial bridge behaviour, AP facade behaviour, stale-state handling, or Captain eyes-on product fit.
