---
abstract: "Dual-K1 sync research: full inventory of user-visible K1 control state (CONFIG struct + SECONDARY_* globals + director/edge/VP RAM state), every runtime mutation path (typed serial, hotkeys, M5ROTATE8 encoders, Tab5 WebSocket, BLE-MIDI Remoted, GPIO buttons), residual divergence between two K1s on the same mode (esp_random hue walk, per-device AGC/cal/tempo phase), and persistence truth: LittleFS files only — NO NVS anywhere; sync-role storage options identified."
---

# Dual-K1 Sync — Control-Surface Evidence (state inventory, mutation paths, divergence, persistence)

Research lane: `artifacts/k1_dual_sync_eval_2026-07-08`. Read-only pass over
`system/`, `persistence/`, `serial/`, `network/`, `control/` in
`SPECTRASYNQ_K1_FIRMWARE/`. All paths below are relative to
`/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/` unless
stated otherwise.

## Headline corrections to the brief

1. **Persistence is LittleFS, not NVS.** A repo-wide grep for `Preferences`
   and `nvs_` returns zero hits. Config, calibration profile and preset slots
   are all LittleFS files (`persistence/bridge_fs.h:92,164,315,411`;
   `control/sb_effect_queue.cpp:360,384`). The root `CLAUDE.md` claim of "ESP-IDF
   NVS" does not match the code.
2. **LED count verified:** render canvas `NATIVE_RESOLUTION 160`
   (`system/constants.h:109`), default strip `LED_COUNT_VALUE 160`
   (`system/config_types.h:139`), plus a second 160-LED channel
   (`SECONDARY_LED_COUNT = 160`, `system/globals.h:825`). Each K1 is 2×160
   physical LEDs on a 160-px mirrored canvas (mirror anchor at 80,
   `system/constants.h:108`). A two-K1 widened surface is 320 px per channel
   pair — the brief's ~320 figure holds per channel, not per device total.
3. **Production `k1_hardware` is radio-free today.** `SB_K1_WIRELESS_ENABLED`
   (Tab5 WebSocket AP) appears only in env `k1_wireless_ab_probe`
   (`platformio.ini:361` under `[env:k1_wireless_ab_probe]` at `:353`);
   `SB_K1_BLE_REMOTED` appears only in `k1_bench_im73d_ble` (`platformio.ini:299`)
   and `k1_ble_remoted_probe` (`platformio.ini:387`). The BLE-MIDI TU states
   "GATED / NON-SHIPPABLE … Production (k1_hardware) never sees this TU"
   (`network/ble_remoted_central.cpp:6-8`).

## (a) Inventory of user-visible state

### Persisted primary-channel + global state — `struct conf` (`system/config_types.h:243-285`)

| Item | Field | Notes |
|---|---|---|
| Brightness | `CONFIG.PHOTONS` (`:245`) | 0.05–1.0 |
| Colour range | `CONFIG.CHROMA` (`:246`) | 0–1; <0.95 leaves chromatic mode (`persistence/knobs.h:60-65`) |
| Smoothing/energy | `CONFIG.MOOD` (`:247`) | drives smoothing follower (`persistence/knobs.h:68-85`) |
| Mode | `CONFIG.LIGHTSHOW_MODE` (`:248`) | enum of 30 modes, 22 enabled (`config_types.h:155-209`) |
| Mirror | `CONFIG.MIRROR_ENABLED` (`:249`) | |
| Audio gain | `CONFIG.SENSITIVITY` (`:260`) | 0.10–20.0 (`config_types.h:55-56`) |
| Cal baselines | `CONFIG.DC_OFFSET` (`:264`), `CONFIG.SWEET_SPOT_MIN_LEVEL`/`MAX_LEVEL` (`:262-263`) | per-device, learnt by noise cal |
| Chromagram | `CONFIG.NOTE_OFFSET` (`:253`), `CHROMAGRAM_RANGE` (`:265`), `CHROMA_PROFILE` (`:266`) | global analysis preset |
| Look controls | `SQUARE_ITER`, `SATURATION`, `PRISM_COUNT`, `INCANDESCENT_FILTER/MODE`, `BULB_OPACITY`, `BASE_COAT(+_INTENSITY)`, `AUTO_COLOR_SHIFT`, `TEMPORAL_DITHERING`, `STANDBY_DIMMING`, `REVERSE_ORDER`, `MAX_CURRENT_MA` (`:254-280`) | |
| Palette | `CONFIG.PALETTE_INDEX`, `CONFIG.PALETTE_MODE_ENABLED` (`:283-284`) | |
| Spare byte | `CONFIG.RESERVED_CONFIG_BYTE` (`:269`) | unused bool INSIDE the persisted blob |

### RAM-only secondary-channel state (`system/globals.h:827-847`) — NOT persisted

`SECONDARY_LIGHTSHOW_MODE` (boots to mode 18, `:827`), `SECONDARY_MIRROR_ENABLED`,
`SECONDARY_PHOTONS/CHROMA/MOOD/SATURATION/PRISM_COUNT`,
`SECONDARY_INCANDESCENT_*`, `SECONDARY_BASE_COAT(_INTENSITY)`,
`SECONDARY_REVERSE_ORDER`, `SECONDARY_AUTO_COLOR_SHIFT`,
`SECONDARY_PALETTE_INDEX` (boot 28) / `SECONDARY_PALETTE_MODE_ENABLED` (boot true)
(`:840-841`), `ENABLE_SECONDARY_LEDS` (force-assigned `true` at boot,
`SPECTRASYNQ_K1_FIRMWARE.ino:672`, unless `K1_CUSTOM_LED_V1`). A legacy
`save_configuration()/load_configuration()` pair that would persist secondary
palette exists (`persistence/bridge_fs.h:564-648`) but has **zero callers**
(grep) — dead code. Secondary state resets on every reboot.

### Other RAM-only user-visible state

- `MASTER_BRIGHTNESS` (`system/globals.h:781`) — set by `global.master_brightness`
  control and boot ramp; not persisted.
- `secondaryMode` channel-target toggle for serial/encoders (`system/globals.h:850`).
- SmartDirector config (enabled/assist/autonomy/confidence floor/dwell),
  visual hooks, EdgeMixer mode+strength, `scene.smart` composite
  (`control/sb_k1_control_facade.cpp:162-235`).
- VP profile + ~20 VP tuning scalars (`system/globals.h:478-503`).
- Effects queue: queue mode, armed pending presets, transition style
  (DIP/XFADE), dip/xfade ms, beat quantise (`control/sb_effect_queue.h:104-141`) — RAM-only.
- Calibration status: `noise_samples[80]`, `noise_complete`,
  `calibration_source/valid` (`system/globals.h:186-220`).
- `audio_response_gain` (`system/globals.h:54`) — RAM-only.

## (b) Runtime mutation paths per item

Five input surfaces exist; all mutate the SAME globals:

1. **Typed serial `:cmd` surface** — Row-1 dispatch table
   (`serial/serial_cmd_table.def:32-71`: version/reset/factory_reset/
   restore_defaults/start_noise_cal/get_mode/commit/slot_list …) plus the large
   key=value parser in `serial/serial_cmd_handlers.cpp` (e.g. `CONFIG.CHROMA`
   `:119`, `MOOD` `:133`, `PALETTE_MODE/INDEX` `:147-165`, `CHROMAGRAM_RANGE`
   `:342-350`, `SATURATION` `:514-521`) and `preset=<name>` →
   `system/presets.h:1-86` (five look presets + four dual-edge pairing presets
   that set BOTH channels' modes, `:55-85`).
2. **Single-byte hotkeys** (`serial/serial_menu.h:1337-1766`):
   space toggles primary/secondary target (`:1544-1548`); `[`/`]` mode step;
   digits load preset slots 1–10, shift+digit saves slots; `\` queue commit;
   `U` queue mode; `i/I o/O p/P j/J k/K l/L` step photons/chroma/mood/
   saturation/prism/base-coat on the ACTIVE channel; `q/Q w/W` square_iter/
   sensitivity; `e/E r/R t/T` VP scalars; `N`/`Y` noise-cal arm/confirm.
   Hotkeys mark manual control to the director (`:1539-1542`).
3. **M5ROTATE8 encoders** (`persistence/encoders.h`): enc0 photons
   (`:334-372`), enc1 chroma (`:384-394`), enc2 mood (`:466-476`), enc3
   mode-cycling `CONFIG.LIGHTSHOW_MODE = (…+1) % NUM_MODES` (`:504-516`) and
   mood/saturation (`:593-625`), palette stepping (`:705-712`), enc6 button
   incandescent toggle (`:727`); all respect `secondaryMode`.
4. **Tab5 WebSocket** (`network/sb_k1_wireless.cpp`, env-gated): K1 runs a
   soft-AP (`WiFi.softAP`, `:883`), JSON `k1.control.set` with token
   `"k1-tab5"` (`:36-37,669`), queued and drained
   `MAX_REQUESTS_PER_AP_TICK` per tick through
   `k1_wireless_control_apply()` (`:930`) → thin wrapper
   (`control/sb_wireless_control.cpp:10`) → **`sb_k1_control_apply()`**.
   `k1.state.get` returns a full state snapshot (`:679`; snapshot fields at
   `control/sb_k1_control_facade.cpp:1046-1074` incl. tempo bpm/locked).
5. **BLE-MIDI Remoted remote** (`network/ble_remoted_central.cpp`, env-gated):
   K1 is BLE **CENTRAL only**, subscribing to the "SpectraSynq Remoted"
   peripheral (`:38-40`); notifications decode via the generated 71-control map
   (`network/k1_ble_midi_map.h:9,40-112` — PC=mode, CC14 pairs=continuous,
   CC7=bool/enum, NRPN=preset/scene/cal commands) into
   `K1WirelessControlRecord`s, queued (capacity 16, `:44`) and applied from the
   main-loop poll via `sb_k1_control_apply()` (`:246`). K1→knob feedback:
   confirmed mode ordinals on CC 0x20/0x21 (`:42-43`).
6. **GPIO buttons** (`persistence/buttons.h`): mode button short-press queues
   mode increment (`mode_transition_queued`, `:74`), long-press toggles
   `CONFIG.MIRROR_ENABLED` (`:53`); noise button short=cal, long=clear.

**Common funnel:** WS + BLE converge on `sb_k1_control_apply()`
(`control/sb_k1_control_facade.cpp:468-1044`), a 71-path allowlist
(`:379-452`) covering primary.\*, secondary.\*, global.\*, director.\*, edge.\*,
scene.smart, vp.\*, calibration.noise.\* (arm/confirm two-step; direct
`start_noise_cal` is rejected, `:471-479`). Mode changes are applied via
`mode_transition_queued`/`mode_destination` consumed by Core 1 at a frame
boundary (`:490-493`); most primary/global setters call `save_config_delayed()`
(5 s debounce, `persistence/bridge_fs.h:200-206`); **secondary.\* setters,
master_brightness, director/edge/vp setters do NOT persist** (e.g. `:645-745`).

## (c) Two K1s manually set to the same mode — what still diverges

Even with identical CONFIG on both devices, these diverge:

1. **Hardware RNG hue walk.** With `AUTO_COLOR_SHIFT` on,
   `hue_destination = random_float()` (`visual/led_utilities.h:1815`) where
   `random_float()` uses `esp_random()` (`system/utilities.h:79`) — true RNG,
   unsynchronisable by state copy; each K1 wanders its own hue path. Speed is
   also driven by the local novelty curve (`led_utilities.h:1779-1799`).
2. **Per-device audio → all render input.** Two mics hear different signals:
   spectrogram, chromagram, novelty, VU, onset, silence detection all differ.
   Same-room ≠ same-samples.
3. **AGC/normalisation state.** `agc_envelope`, `agc_noise_floor`, `agc_gated`
   (`system/globals.h:704-706`), zone followers `max_mags(_followers)`
   (`:643-644`), `min_silent_level_tracker` (`:662`) — converge on local audio
   history, never shared.
4. **Cal baselines.** `CONFIG.DC_OFFSET`, `SWEET_SPOT_MIN/MAX_LEVEL` and the
   80-bin `noise_samples[]` profile are per-device/per-room measurements
   (`persistence/bridge_fs.h:394-460`); copying them between units would be
   wrong, not sync.
5. **Tempo/beat phase.** Beat-locked modes (Tempo River/Comet etc.) follow the
   local PLL (`sb_tempo_read()`, `control/sb_k1_control_facade.cpp:1069-1071`);
   two flywheels lock to the same music with independent phase error → visible
   left/right drift exactly on the modes that matter most.
6. **Frame clocks + transition timing.** Independent ~100 FPS render loops with
   graceful frame drop; queue commits quantise to the LOCAL beat
   (`control/sb_effect_queue.h:150-154`); mode fades land at each device's own
   frame boundary.
7. **Effect internal memory.** `waveform_history`, per-channel effect state,
   `dots[]`, spectral history (`system/globals.h:153-157,377-378,751`) are
   seeded by local audio timing; framework TransitionEngine also uses
   `random8/random16` (`effects/framework/TransitionEngine.cpp:203-238`).
8. **SmartDirector autonomy.** In `scene.smart=auto`, each director makes
   independent mode-switch decisions on local confidence/dwell windows
   (`control/sb_k1_control_facade.cpp:211-223`).

Conclusion: mirroring the CONFIG-level control surface makes two K1s "same
programme", not "one display". A widened display additionally needs a shared
beat phase (or one leader's AudioSemanticState), a shared/disabled hue walk,
and a spatial split contract — otherwise items 1, 5 and 6 alone visibly split
the halves.

## (d) Preset storage and where a sync role could persist

- **Config blob:** `/CONFIG_PDM_<ver>.BIN` (or `/CONFIG_<ver>.BIN`), 512-byte
  file = 12-byte header (magic `K1CF`, version 1, `length=sizeof(conf)`,
  crc32) + raw `CONFIG` bytes (`persistence/bridge_fs_config_codec.h:36-53`;
  writer `bridge_fs.h:151-197`). Loader decides LOAD/MIGRATE/FALLBACK; a
  header whose version or length mismatches falls back to compiled defaults in
  RAM (`bridge_fs_config_codec.h` decision table; `bridge_fs.h:256-278`) — so
  **appending a field to `conf` invalidates existing on-disk configs** unless a
  version-migration path is added.
- **Preset slots:** `/PRESETS_V1.BIN`, magic `'SBPS'`, version 1, 10 slots of
  the 15-field per-channel `SBChannelPreset` (`control/sb_effect_queue.h:53-75`;
  IO `sb_effect_queue.cpp:360-397`). Slots deliberately contain NO audio/cal
  fields and no device-role concept.
- **Cal profile:** `/cal_profile_pdm.bin`, magic+version header pattern
  (`bridge_fs.h:24-29,394-460`).
- **Sync-role options (fact-finding, not a decision):**
  1. `CONFIG.RESERVED_CONFIG_BYTE` (`config_types.h:269`) is an existing bool
     INSIDE the persisted blob — a role could occupy it with zero layout change
     and zero migration cost, but it is a single bool (leader/follower yes;
     left/right + leader/follower needs more than one bit unless packed).
  2. A new field in `conf` — clean, but triggers CFG_FALLBACK on every
     existing device until version/migration handling is extended.
  3. A dedicated small LittleFS file following the `cal_profile` magic+version
     pattern — lowest-risk precedent, survives config-format churn, matches
     how every other durable artefact in this firmware is stored.
  `factory_reset()` deletes config+cal (+ preset slots on non-PDM builds)
  (`bridge_fs.h:86-126`) — any role file's reset behaviour must be decided.

## Numbers

| Quantity | Value | Source |
|---|---|---|
| Render canvas | 160 px | `system/constants.h:109` |
| Physical LEDs per channel | 160 (61/91/224 variants) | `system/config_types.h:123-140`; `system/globals.h:825` |
| Channels per K1 | 2 (primary + secondary) | `system/globals.h:818-826` |
| Lightshow modes | 30 enumerated / 22 enabled | `system/config_types.h:155-209` |
| Wireless control paths | 71 (BLE map + facade allowlist agree) | `network/k1_ble_midi_map.h:9`; `control/sb_k1_control_facade.cpp:379-452` |
| BLE text values | 21 | `network/k1_ble_midi_map.h:10` |
| Preset slots | 10 × 15 fields | `control/sb_effect_queue.h:56-75` |
| Config file size | 512 B (12 B header + `sizeof(conf)`) | `persistence/bridge_fs.h:174-186` |
| Config save debounce | 5000 ms | `persistence/bridge_fs.h:204` |
| BLE record queue | 16 records | `network/ble_remoted_central.cpp:44` |
| WS token | `"k1-tab5"` compile-time constant | `network/sb_k1_wireless.cpp:36-37` |

## Risks

- Production build has no radio: a dual-K1 sync over BLE MIDI requires
  promoting a currently non-shippable, bench-only stack (NimBLE central on
  Core 0) into production — internal-RAM pressure already bites there
  (`bridge_fs.h:31-44` fopen-abort incident under BLE).
- K1 BLE role today is CENTRAL-only toward a knob peripheral; K1↔K1 needs one
  unit to expose a peripheral/advertiser role that does not exist in firmware.
- Secondary-channel state is RAM-only and boot-forced; any sync contract that
  assumes persisted per-channel state on the follower is wrong today.
- Beat-phase drift is architectural (independent PLLs), not a control-state
  gap — control-state mirroring alone cannot deliver "one widened display".
- `sizeof(conf)` change wipes user config to defaults on load (CFG_FALLBACK)
  without added migration.

## Open questions

- Which unit owns tempo truth in a widened display — leader broadcasts beat
  ticks (3× republish already exists in SB_TEMPO_FLYWHEEL_V2), or both run
  free and only control state is mirrored?
- BLE MIDI throughput/latency budget for continuous CC14 mirroring at
  encoder-turn rates (not measured in this pass; decoder handles multi-message
  packets, `k1_ble_midi_decoder.cpp:259-320`).
- Is the widened surface split at the canvas level (each unit renders half of
  a 320-px virtual canvas — breaks the centre-origin mirror anchor at 80) or
  at the content level (mirror-left/mirror-right of the same 160-px render)?
- Whether the Tab5 WS lane (also env-gated) is a candidate transport instead
  of/alongside BLE — same facade, JSON, already has state snapshot + seq.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (SSA research) | Created: control-surface inventory, mutation-path map, divergence analysis, persistence findings for dual-K1 sync evaluation |
