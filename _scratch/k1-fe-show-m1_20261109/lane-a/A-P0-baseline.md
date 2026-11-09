---
abstract: "K1-FE-SHOW-M1 Rev 2, Lane A (P0 baseline and authored-path consumer map), 9 November 2026. The PRSM (Prim8) consumer is compiled into k1_fe and k1_fe_bench_b489 (symbols in both ELFs built from 407fdf6f); the bench K1 actually runs ed0aa984 k1_fe_bench_b489, epoch 1793984825 (read back by the lead on 9 Nov; the registry still says 407fdf6f), and the ed0aa984 bench ELF also contains the path. No admitted effect is fully driven by the authored stream: every one keeps a live or frozen input (live mic peak, live colour-shift phase, frozen spectrum, zeroed chroma). Malformed PRSM bytes fall through to persisting and calibration hotkeys. Three change requests filed. Track: Loreen (emulator-approved fixture), passage 75–155 s, transition 137 s. No retained byte-identical copy of the resident image exists. Bench evidence surfaces without a firmware change: rtrace captures the primary edge only (RGB8, post-gamma); the [AP] line prints live Core-0 values plus authored-derived tempo/onset, never the authored snapshot."
---

# Lane A — P0 baseline and authored-path consumer map

Every row is **FACT** (observed; file:line, command output or sha256) or **UNKNOWN**. Inferences are labelled **[INFERENCE]** and never stand as fact. Source facts are from HEAD `407fdf6f503f92441f1d529276de017495f20ef3` unless stated. **Revision 9 Nov (lead read-back): the resident source is `ed0aa984`** — all `audio/`, `serial/` and `visual/led_utilities.h` files are identical between `407fdf6f` and `ed0aa984` (`/usr/bin/git diff --quiet 407fdf6f ed0aa984 -- …` → identical), so every PRSM/authored/serial citation holds for the resident image; the differences are listed in §A1 and mapped in §A7/§A8. `.ino` line numbers in this file are `407fdf6f`'s unless marked; at `ed0aa984` lines after 415 are +30 (the FX dispatch insertion); the clean export used was `lane-a/export-407fdf6f/` (`/usr/bin/git archive 407fdf6f`; 684 MB, deleted after use — its built images are kept in `raw/images/`; recreate with the same command). Abbreviations: AP = audio pipeline (Core 0), VP = visual pipeline (Core 1), PRSM = the 34-byte Prim8 frame, ELF = linked firmware image, CR = change request, THE LAW = Captain's law of impactful light-show modes.

Skills: `spectrasynq-audio-pipeline` and `cpp` loaded. `platformio-mcp` is not installed; the PlatformIO command-line tool (`pio` 6.1.19) was used instead. Nothing installed. No serial port opened, no esptool, no flash, no reset (device contact belongs to Lane D).

## Gates

| Gate | Status | Evidence |
|---|---|---|
| A1 identity record | **PASS** — device read-back (lead, read-only `:build`, 2026-11-09T11:43:42Z): `git=ed0aa984 env=k1_fe_bench_b489 epoch=1793984825` — **registry is stale** (last recorded `407fdf6f`) | §A1 |
| A2 control-path table | **PASS** (desk); every round-trip **UNKNOWN** | §A2 |
| A3 persistence check | **PASS** for well-formed PRSM frames; **FAIL** for malformed or truncated PRSM bytes (reach persisting and calibration hotkeys); typed show commands persist | §A3, `CR-A3-prsm-hotkey-fallthrough.md` |
| A4 emulator command→ack latency | **NOT RUN** | §A4 |
| A5 asset | **PASS** — `ASSET.json` | §A5 |
| A6 rollback material | **PARTIAL** — no retained copy of the resident `ed0aa984` image; nearest material = clean `ed0aa984` rebuild (807,568 B, `c08bb61d…`, not byte-identical, wrong stamp); M1 plans no flash, live-baseline restore = stop stream + restore changed settings | §A6 |
| A7 authored consumer map | **FAIL** for "fully authored-driven": 0 of 28 admitted modes; CR filed | §A7, `CR-A7-wfhyb-authored-drive.md` |
| A8 PRSM compiled in | **PASS** (`k1_fe`@407fdf6f, bench@407fdf6f, bench@ed0aa984 = resident source); authored-state read-back **absent** → CR; rtrace **compiled, primary edge only**; `[AP]` line **does not show the authored snapshot** | §A8, `CR-A8-authored-status-readout.md` |
| A9 timing facts | **PASS** (desk); device-side latency **UNKNOWN** (not measured) | §A9 |

## A1 — Identity record

| Item | Value | Status / evidence |
|---|---|---|
| Repo, branch | `/Users/spectrasynq/SpectraSynq_K1_Firmware`, `lane/k1-fe-release` | FACT, session git status |
| HEAD | `407fdf6f503f92441f1d529276de017495f20ef3` "docs(fe): same-conditions results and effect decision pack" | FACT `/usr/bin/git rev-parse HEAD` |
| Dirty (staged, another session) | `effects/light_mode_waveform_hybrid_k1.cpp` (+13/−8: silence now requires live-inclusive `peak < floor`; quiet/colour gain no longer zeroed by `silence`), `system/globals.h` (bench `K1_SILENCE_DWELL_DEFAULT_MS` 1000→5000) | FACT `/usr/bin/git diff --cached --stat` and diff. Every other file cited here is identical to HEAD (`git diff --quiet 407fdf6f` on the PRSM/authored/serial/.ino/led_utilities files → identical). |
| Env chain | `k1_hardware` → `k1_main_rpl_im69d` → `k1_fe` → `k1_fe_bench_b489` | FACT `platformio.ini:18,291–292,480–481,505–506` |
| `k1_fe` adds | src: `+audio/k1_pcm1808_input.cpp`, `+system/k1_fe_board.cpp`; flags `K1_FE_BOARD_V1`, `K1_PCM1808_LINE_SWITCH=1`, `K1_PCM1808_MONO_POLICY=K1_PCM1808_MONO_MID`, `K1_PCM1808_CANON_TRIM_Q15=2048` | FACT `platformio.ini:480–492` |
| `k1_fe` full flag list (55, resolved) | see `raw/env_resolved_407fdf6f.json` (from `pio project config --json-output`, `raw/pio_project_config_407fdf6f.json`) | FACT |
| `k1_fe_bench_b489` vs `k1_fe` | unflags `K1_MAIN_RPL_PINMAP_V1=1`, `K1_WS2816_LEVER2_V1`, `K1_LOOK_LIB_V1`; adds `K1_FE_BENCH_B489_V1`, `K1_TEMPO_CONSUMER_BANDS_V1`, `K1_BENCH_REFERENCE_PINMAP=1`, `K1_LOOK_LIB_WS2812_V1`, `K1_PCM1808_DIN_PIN=10`, `_BCLK_PIN=11`, `_LRCK_PIN=9`, `_NFC_CS_HOLD_PIN=-1`, `K1_AP_SUBSONIC_HPF_V1`, `K1_RENDER_TRACE_V1` | FACT resolved diff; `platformio.ini:505–536` |
| Emulator env `k1_main_rpl_emu` vs `k1_fe` | adds `K1_RENDER_TRACE_V1`, `K1_EMU_FIXTURE`, `K1_EMU_SKIP_EMIT`, `K1_EMU_UART0`, `-include k1_emu_clock_force.h`; **lacks** `K1_FE_BOARD_V1` and the three `K1_PCM1808_*` flags and their two sources. Render/audio-behaviour flags otherwise identical. `K1_EMU_FIXTURE` replaces the loop clock with the hop-end clock (`.ino:910–914`) and injects PCM. | FACT resolved diff; `platformio.ini:719–731` |
| FE emulator env `k1_fe_emu` vs `k1_fe` | all `k1_fe` flags plus the four adapter flags and `K1_EMU_FE_MIC_ONLY`, `K1_EMU_ONSET_TRACE`, `K1_EMU_SPECTRUM_TRACE` | FACT `platformio.ini:733–747`. Closer to the product than `k1_main_rpl_emu`. |
| Flags that matter for authored mode, all OFF in both FE envs | `K1_EFFECT_REGISTRY_V1` (so `set_mode` takes the raw ordinal), `K1_EFFECT_FRAMEWORK_V1`, `K1_HUE_DRIVE_EQ_V1`, `K1_FALLBACK_HELD_U_V1`, `K1_AP_DRIVE_CONTRACT_V1`, `K1_TEMPO_NOVELTY_LINEAR_V1`, `K1_STM`, `K1_BLE_REMOTED` | FACT resolved flags |
| Toolchain | PlatformIO Core 6.1.19; platform Espressif 32 54.3.20; framework-arduinoespressif32 3.2.0; -libs 5.4.0+sha.2f7dcd862a; toolchain-xtensa-esp-elf 14.2.0+20241119; tool-esptoolpy 4.8.9; FastLED 3.10.3 | FACT `raw/build_k1_fe_bench_b489.log:18–29`; `platformio.ini:20,232`. No PlatformIO lockfile exists (`ls *.lock` → none). |
| Emulator tool lock | esp-emu 0.49.0, git `017d587c…`, executable sha256 `dea564e3…d84a0` | FACT `tools/esp_emulator/tool-lock.json` |
| Clean-export build of the resident source | `k1_fe_bench_b489` @ `ed0aa984`: SUCCESS 33 s, RAM 59.5 %, flash 807,162 B, `firmware.bin` 807,568 B sha256 `c08bb61d…f75f`. **Its provenance stamp is wrong** (`git=407fdf6f`, `raw/build_k1_fe_bench_b489_ed0aa984.log:16`): the provenance script read the enclosing repository HEAD because the export sits inside the repo tree. Do not flash this image; it is evidence only. | FACT `raw/build_k1_fe_bench_b489_ed0aa984.log:16,361–362`, `raw/images/SHA256SUMS.txt` |
| Clean-export builds @ 407fdf6f (this lane) | `k1_fe_bench_b489` SUCCESS 62 s, RAM 48.2 %, flash 759,502 B, `firmware.bin` 759,904 B sha256 `41696ad1…988c`; `k1_fe` SUCCESS, `firmware.bin` sha256 `86433545…deb7`; provenance stamp `git=407fdf6f epoch=1794224987` (correct only by coincidence: the stamp reads the enclosing repository HEAD, see the `ed0aa984` row) | FACT `raw/build_k1_fe_bench_b489.log:16,347–348`, `raw/build_k1_fe.log`, `raw/images/SHA256SUMS.txt` |
| Bench device on USB (passive) | `/dev/cu.usbmodem11301`, "USB JTAG_serial debug unit", serial `B4:3A:45:A5:89:B4` (= chip `B489A500`); no process holds the port | FACT `ioreg -p IOUSB -l`, `lsof` (empty), 2026-11-09T19:59+0800 |
| Resident build on B489A500 (**read back**) | `BUILD: version=40103 git=ed0aa984 epoch=1793984825 env=k1_fe_bench_b489` read by the lead with `:build` only, port `/dev/cu.usbmodem11301`, 2026-11-09T11:43:42Z. Epoch 1793984825 = 2026-11-06T17:07:05Z. `ed0aa984` (2026-11-06 02:17 +0800, "fix(fe): restore mode 32 silence behaviour") = `407fdf6f` + 51 commits: the bench-only motion battery (`K1_FX_BATTERY=1` on `k1_fe_bench_b489` only, modes 38–51, 14 new `effects/light_mode_fx_*.cpp`, `visual/motion/*`, `visual/easing.h`), the mode-32 silence change, and `globals.h` bench dwell 1000→5000 ms. The staged working-tree diff equals `ed0aa984` for `light_mode_waveform_hybrid_k1.cpp` (`git diff --cached --quiet ed0aa984 -- …` → equal) and for `globals.h` (`git diff ed0aa984` empty). | FACT `lane-d/raw/D0_build_20261109T114342Z.txt`; `/usr/bin/git log 407fdf6f..ed0aa984`, `git diff --stat` |
| Registry vs device (**registry stale**) | Registry last recorded flash: `407fdf6f` (normal capture source `8accab34`), epoch `1793869517` (2026-11-05T09:05:17Z), app sha256 `7f2fd430…4be5` (`device-build-registry.md:221`, `final-build-handshake.json`). The `ed0aa984` flash (about 32 h later) is **not recorded**: no registry commit after `407fdf6f` on any branch (`git log --all -- docs/hardware/device-build-registry.md`), and `ed0aa984` does not appear in `docs/`. Its app sha256 is **UNKNOWN**. | FACT |
| Resident primary mode at read-back | `lightshow=22` (Snapwave) in every `[AP]` line of the read-back window, not 32 as last recorded | FACT `D0_build_20261109T114342Z.txt` (trailing `lightshow=` field = `CONFIG.LIGHTSHOW_MODE`, `i2s_audio.h:1676`) |
| Settings at the last registry-recorded state (5 Nov, `407fdf6f` / capture `8accab34`; **stale** — the read-back shows primary mode 22) | primary mode 32 (Waveform Hybrid K1), secondary mode 18 (Waveform Tempo), `CHROMA 0.100`, `MIRROR 1`, `AUTO_COLOR_SHIFT 1`, secondary palette mode on, palette 35 (K1_Chameleon_Flare_gp), look `1 GOLD_LIFT`, SSL 108 / DC 57, `SYSTEM_FPS 137.41`, `LED_FPS 200.43`. Primary palette mode is not in `:dump`; compiled default is ON (`system/globals_config.cpp:97`) → **UNKNOWN** for the saved value. | FACT `_scratch/s3-repair-20261105/followup/post-doc-restoration-state.txt:10–128` (5 Nov record, superseded by the 9 Nov read-back) |

## A2 — Control paths for M1

| Path | Parameters | Range | Edge addressability | Acknowledgement | Persistence side effect | Measured round-trip |
|---|---|---|---|---|---|---|
| **PRSM ingress** (USB-Serial-JTAG, `check_serial` scanner) — accepted today | 34 B: `PRSM`, version 1, hz, seq u32, t_us u64, 8 × u16 Prim8 (`audio/k1_prsm.h:14–27`). Used: pressure[0], impact[1], mass[2], momentum[3], texture[6]; heat[4], space[5], gravity[7] unused (`audio/k1_authored_source.cpp:31–45`) | hz 30–240 (`k1_authored_source.h:17–18`); u16 → [0,1] (`:21–23`) | **Both edges together**: one snapshot feeds both (`.ino:1144–1158`); no per-edge field | **None.** No print, no counter (`serial_menu.cpp:4154–4163`). Indirect: `:smart_status` shows snapshot novelty/energy (`serial_menu.cpp:568,621–624`) | None for well-formed frames (A3) | UNKNOWN |
| **Typed serial**, `:set_mode=<n>` (primary) | mode ordinal (registry flag off) → `light_mode_next_enabled()` | 0–37, disabled IDs skipped (`config_types.h:265–290`) | primary only | `CONFIG.LIGHTSHOW_MODE: <n>` (`serial_cmd_handlers.cpp:1641–1645`) | **Yes**: `save_config_delayed()` (`:1638`) although the table row declares flags 0 (`serial_typed_cmd_table.def:141`) — metadata disagrees with code | UNKNOWN |
| `:secondary_mode=<n>` | ordinal | 0–37 | secondary only | `SECONDARY_MODE: n (name)` (`serial_cmd_handlers.cpp:1695–1704` non-registry branch) | none in handler | UNKNOWN |
| `:palette_index=<n>` / `:palette_mode=` | palette index; also forces palette mode on | 0…`gGradientPaletteCount-1` | primary | `PALETTE …` line (`serial_cmd_handlers.cpp:181–191`) | **Yes** `save_config_delayed()` (`:188`); table `CMD_PERSISTS` (`.def:147–148`) | UNKNOWN |
| `:photons=`, `:chroma=`, `:mood=`, `:saturation=`, `:auto_color_shift=` … (23 pure setters) | float/bool | e.g. photons 0.05–1.0 (`:119`) | primary | `CONFIG.X: value` | **Yes** (`:123` photons; table `CMD_PERSISTS` `.def:144–165`) | UNKNOWN |
| `:secondary_photons/_chroma/_mood/_palette_*` … | float/int | per setter | secondary | `SECONDARY_X:` | table `CMD_PERSISTS` (`.def:200–213`) | UNKNOWN |
| `:queue_mode`, slot load/save, `:save_show`, `:preset` | — | — | per target | text | **Yes** (table `CMD_PERSISTS`, `.def:188–197`); primary commit → `save_config_delayed()` (`control/k1_effect_queue.cpp:137–141`) | UNKNOWN |
| **BLE-MIDI** CC map | 68 controls, channels primary/secondary/global/director/hooks/edge/scene/vp/calibration (`docs/protocol/k1-ble-midi-map.json`, schema `k1.ble-midi-map/1`) | per entry | primary/secondary per channel | — | — | **Not compiled into `k1_fe` or `k1_fe_bench_b489`** (`K1_BLE_REMOTED` absent from resolved flags; present only in bench BLE envs, `platformio.ini:1195,1222,1310`). Not the show transport. |
| **Emulator, scheduled command** | text ≤ 88 B at hop *h* | hop index; applies at sample `h*96` before hop *h* (`tools/esp_emulator/README.md:127–131`) | as the typed command | `EMU_CMD`/`EMU_CMD_DONE` | as the typed command; `EMU_SAVE` reports LittleFS writes (`README.md:169`) | lockstep; not physical |
| **Emulator, PRSM injection** | — | — | — | — | — | **Adapter needed for hop-exact injection**: scheduled records are text through `parse_command()` (`emu_blob.py` `COMMAND_TEXT = 88`, `CMD_SCHEDULED`), which never reaches the PRSM scanner. Client transport reaches `check_serial()` but its gate counts parsed `:` lines, not frames (`README.md:206–215`). Lane C-emu is building this (`lane-c-emu/`, `build-k1_fe_emu-adapter.log`); its result is theirs. |

Physical mapping of "primary"/"secondary" to top/bottom edge: **UNKNOWN** (bench wiring records only GPIO4 = primary, GPIO5 = secondary, `platformio.ini:496–503`).

## A3 — Persistence (hard check)

**Typed commands.** `save_config_delayed()` (`persistence/bridge_fs.h:280–293`) sets `next_save_time = millis()+5000`, `settings_updated = true` and pushes a persist request; each call re-arms the 5 s timer, and the eventual LittleFS write stalled the dispatch for 18,641 µs in the 5 November capture (`device-build-registry.md:222`). Callers in the show-relevant set: `set_mode` (`serial_cmd_handlers.cpp:1638`), `photons` (`:123`), `palette_index` (`:188`), all 23 pure setters (`:123–532`), primary queue commits (`k1_effect_queue.cpp:139`), hotkeys `q Q w W` (`serial_menu.cpp:2154–2172`). Immediate `save_config()` in the reboot setters (`serial_cmd_handlers.cpp:551–723`). **No non-persisting primary mode or palette path exists** in the typed table; `secondary_mode` does not save in its handler. T1 (timed typed commands) would write flash.

**PRSM, well-formed frames: PASS.** Call tree: `check_serial()` → `k1_prsm_scanner_push()` (`k1_prsm.cpp:50–84`, calls only `k1_prsm_parse` and `memset`) → `k1_authored_on_frame()` (`k1_authored_source.cpp:63–88`, calls only `k1_authored_map_prim8` → `memset`). `k1_authored_tick()`, `k1_authored_intent()` call nothing. The `.ino` consumer calls only `k1_audio_snapshot_publish()` (`.ino:1159`). No `save_config*`, `k1_persist_request_push`, LittleFS or NVS call on the path.

**PRSM, malformed or truncated bytes: FAIL.** Bytes that break a partial magic, and the tail of a frame after a truncation, return `K1_PRSM_SCAN_NONE` and go to the immediate-hotkey handler (`serial_menu.cpp:4155–4178`; `k1_prsm.cpp:63–67`). The FE hotkey set includes `N`/`Y` (noise-calibration arm/confirm, `:2014–2019`), `!`…`)` (preset-slot saves, `:2078–2108`), `S` (show save, `:2231–2246`) and `q Q w W` (delayed config save). Bad-version and bad-hz frames are consumed whole and are safe. Details, bench rule and fix: `CR-A3-prsm-hotkey-fallthrough.md`.

## A4 — Serial command→ack latency on the emulator

**NOT RUN.** Reasons: (1) the emulator is lockstep; client lines are applied at hop gates, so wall-clock acknowledgement time there is host and emulator speed, not device behaviour (`README.md:148–151`, `:206–215`) — it cannot stand in for the hardware figure; (2) the M1 transport is PRSM, which has no acknowledgement; (3) Lane C-emu is actively using the emulator (`lane-c-emu/runs/c4-probe-002`, `c5-pty-*`), and a second competing run would violate the no-wasted-verification rule. Lane C-emu's host pacing measurement of a 120 Hz PRSM stream to a pseudo-terminal exists (`lane-c-emu/stream/probe-analysis.json`: 7,032 frames, send error p95 0.31 ms, p99 3.1 ms, max 27.7 ms, 0 stray bytes) — theirs to report.

## A5 — Asset

`ASSET.json` written early and sent to Lane C-emu. Track `/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3`, sha256 `a62e1f09…b9b0f` (matches `tools/esp_emulator/s3_music_regression.json` `assets.loreen_src.source_sha256`), MP3 44,100 Hz stereo, 9,874,432 frames, 223.910023 s. Passage 75.0–155.0 s (80 s); designated transition 137.0 s (chorus → breakdown: about −18 dB in 2 s, kick out). Excerpt coordinates 19.0–99.0 s, transition 81.0 s. Method: `raw/asset_envelope.py`, output `raw/asset_envelope_loreen.txt`. Label: **APPROVED (source: emulator maintained fixture `loreen_src` real_music; inventory `loreen_127` active/required)** — a regression-fixture approval, not a Captain show-content sign-off. Genre: dance-pop/EDM at 127 BPM, not trance. BOOM (`~/Downloads/Tiësto-&-Sevenn-MrBlack-BOOM.mp3`, sha256 `3d60c58e…8e4d`) found, used before as a B489 room fixture (`_scratch/b489-ws2816-reference-20261013/resume-20261014/CHECKPOINT.md:287`), not in the emulator scenario: UNAPPROVED for M1, comparison only. Dopex found under `YT_Saver`, Titan-lane only. song-0 not used.

## A6 — Rollback material for B489A500

| Item | Finding | Status |
|---|---|---|
| Retained copy of the resident app image | **None found** for either the resident `ed0aa984` image (hash UNKNOWN) or the last registry-recorded `407fdf6f` image (sha256 `7f2fd430…4be5`). No `*.bin` of 700–820 KB under `_scratch`, `evidence`, `docs`, `artifacts`, `build`, `~/K1_Rollback_Images`; no file mentions `7f2fd430…` except the handshake receipt. `~/K1_Rollback_Images/` holds only `Unit2/unit2-pre-128d2-20260811-fullflash.bin` (another device). | FACT (find/hash search, 9 Nov) |
| Pinned saved-app restore image for B489 | `_scratch/b489-ws2816-reference-20261013/original-app-app0.bin`, sha256 `3d3b929e…c226` = old `k1_bench_im69d_led150` at `eff9bf47` (`recovery-contract.md:53,97–118`). Wrong build for today; only useful as an emergency boot image. | FACT |
| Nearest rollback material (this lane) | **Resident source `ed0aa984`**, clean export, detached build: `raw/images/k1_fe_bench_b489-ed0aa984-firmware.bin`, **807,568 B, sha256 `c08bb61d13652ae46457ff4639c1e10200e1a3cc885986fbee155070cba6f75f`** (ELF `fe254a39…c91c8b`). Not byte-identical to the resident image: the build epoch is embedded (this build `1794226126` vs resident `1793984825`), and its stamped git is wrong (`git=407fdf6f`, because the stamping script reads the enclosing repository HEAD and has no override, `scripts/platformio/k1_build_provenance.py:34–43`) — so it is a reference for size/symbols, not a flashable restore image. A correctly stamped image needs a build from a real `ed0aa984` checkout (contingency, Build/FW lead). The earlier `407fdf6f` rebuild (`41696ad1…988c`, 759,904 B) is the **wrong source** for the resident image and is kept only as the 5 Nov reference. | FACT |
| Settings baseline to restore against | `_scratch/s3-repair-20261105/followup/post-doc-restoration-state.txt` (45 compared fields, `post-doc-restoration-result.json` differences `{}`) | FACT |
| Documented restore route | Rebuild-and-flash from a clean checkout of `ed0aa984` (branches `lane/k1-fx-battery`, `fix/k1-fe-gx-repair-20261108`; tag `pre-gx-adc-header-20261108-pinmap`): `bash scripts/agent/k1-flash-verified.sh k1_fe_bench_b489 --port <verified B489 port>` (`platformio.ini:504`). The script builds the **current checkout** and refuses a dirty `SPECTRASYNQ_K1_FIRMWARE`/`platformio.ini` (`k1-flash-verified.sh:68–75`); the shared tree is on `407fdf6f` + staged edits, so it would neither run nor rebuild `ed0aa984` in place. Pinned-image route: `k1-flash-verified.sh --restore-saved-app …` (`:22–38`); pins exist only for the old `eff9bf47` image. Settings: replay the 45-field comparison used in the 5 November follow-up (that baseline predates `ed0aa984`; the read-back shows primary mode 22, not 32, so the settings baseline is also stale). | FACT |

**Scope for M1.** M1 plans no flash, so firmware rollback is contingency only. The M1 live-baseline restore is: (1) stop the PRSM stream — the device returns to live analysis on its own: the first `k1_authored_tick` more than 50 ms after the last frame moves AUTHORED→RECOVERY and the live snapshot update resumes in that same AP tick; the next tick moves RECOVERY→STANDALONE (`k1_authored_source.cpp:96–105,111–121`; `.ino:1144–1162` at `407fdf6f` = `:1174–1192` at `ed0aa984`), i.e. live within ≈ 50 ms + 1–2 AP ticks (≈ 7.5 ms each); (2) restore every mode/config changed during the session (at minimum primary mode back to 22 if `:set_mode=32` was used; `:set_mode` persists via `save_config_delayed()`), verified against a `:dump` + `:secondary_status` taken at session start. Contingency only (not planned): before any flash, Lane D reads back and hashes the app partition (esptool `read_flash 0x10000 <size>`) so the resident `ed0aa984` image itself becomes the rollback image.

## A7 — Authored-path consumer map

### What changes when the stream is AUTHORED

| Input | Under AUTHORED | Evidence |
|---|---|---|
| Snapshot `vu_level`, `peak_scaled`, `spectral_energy` | Prim8 pressure | `k1_authored_source.cpp:39–41`; `.ino:1150–1153` |
| `novelty` / `low_energy` / `mid_energy` / `high_energy` | impact / mass / momentum / texture | `:42–45` |
| `silence` | pressure, impact and mass all 0 | `:46–47` |
| `chroma_strength`, `spectrum[]`, `chroma_pc[]`, `chord`, `nyquist_safe_bin_hi` | **0** (`K1AudioSnapshot next = {}`, only scalars copied) | `.ino:1148–1158`; struct `k1_audio_snapshot.h:64–100` |
| Legacy onset `onset`, `bass_onset` | derived from authored novelty, low_energy, peak | `k1_onset_beat.cpp:498–516` |
| V2 `transient/kick/snare/hihat` | computed from `spectrum[]` flux (zeroed) → **no events** [INFERENCE: zero flux cannot pass the threshold; not executed] | `k1_onset_beat.cpp:239,286–289` |
| Tempo `bpm/phase01/confidence/beat_tick` | derived from authored novelty (tracker re-locks to impact; lock time UNKNOWN) | `k1_tempo.cpp:1614–1621` |
| Chord / semantic chord | 0 | `k1_semantic_state.cpp:64–68`; `k1_musical_saliency.cpp:130–137` |
| `chromagram_smooth` | **zeroed every render frame** | `.ino:1565–1567` |
| `spectrogram_smooth` | **frozen** at last live value (update skipped) | `.ino:1568–1569`; `lightshow_modes.h:53–69` |
| `chromagram_pregate` (palette anchor) | **frozen** (written only in `make_smooth_chromagram`) | `led_utilities.h:2581` |
| `hue_position` (auto colour shift) | **live** — Core 0 from live `novelty_curve` | `.ino:1290–1292`; `led_utilities.h:2413`; added in `palette_manual_colour` `lightshow_modes.h:291–295` |
| `waveform_peak_scaled`, `max_waveform_val_raw`, `waveform_history`, `audio_vu_level(_average)` | **live** | `globals.h:228–235,1090–1092` |
| `silent_scale` | pinned 1.0 (no leak) | `i2s_audio.h:1499–1500` |
| Drop-cut | forced 1.0 while authored | `led_utilities.h:559–561` |

Colour authority: palette mode is the compiled default for both channels (`globals_config.cpp:97`); bench secondary is on (dump `:126`), bench primary saved value UNKNOWN. In palette mode every colour helper samples the palette at (frozen anchor, or the CHROMA knob, plus any effect offset) + live `hue_position`. In chromatic mode the colour sum is built only from `chromagram_smooth` (`lightshow_modes.h:584–603`, `light_mode_bloom.cpp`), so it goes **black** under authored.

### Per admitted mode (28 enabled in `k1_fe` and `k1_fe_bench_b489`: `config_types.h:265–290` with `K1_WFHYB_M32_VARIANTS_V1` on)

Class: 1 = fully driven by the authored stream; 2 = partially, live/frozen leak named; 3 = unaffected by the authored stream. Scan output: `raw/a7_scan_part1.txt`, `raw/a7_scan_part2.txt`, `raw/a7_scan_helpers_lightshow_modes.txt` (lexical scan of the clean export, each hit read by hand).

| Mode | Authored inputs read | Live / frozen / zeroed inputs read | Class | THE LAW under authored |
|---|---|---|---|---|
| 3 Bloom | none | frozen palette anchor + brightness (`light_mode_bloom.cpp:31–87` → `palette_chroma_colour`), live `hue_position` | 3 | FAIL — constant injection scrolling at MOOD rate; nothing tracks the show |
| 9 Bloom Fast | none (Bloom ×2 shift, `light_mode_bloom.cpp:116–117`) | as Bloom | 3 | FAIL |
| 7 Waveform Fast | none | live `waveform_peak_scaled`, `max_waveform_val_raw` (`light_mode_waveform_fast.cpp:48–53,152`), zeroed chroma (`:63,106`), `hue_position` (`:95`) | 3 | FAIL — follows the room microphone only |
| 8 Waveform | none | live peak, `audio_vu_level` (`light_mode_waveform.cpp:9,49–51,74`), zeroed chroma | 3 | FAIL |
| 11 Waveform Hybrid | none | live peak, `audio_vu_level_average`, `max_waveform_val_raw`, `waveform_history` (`light_mode_waveform_hybrid.cpp:22–34,155–179`), zeroed chroma | 3 | FAIL |
| 12 Aurora | none | `effect_palette_or_chroma_colour` at full scale (`light_mode_aurora.cpp:20`): frozen anchor + `hue_position`; black in chromatic mode | 3 | FAIL |
| 13 Comet | `bass_onset` (authored-derived) (`light_mode_comet.cpp:98`) | colour: frozen anchor + `hue_position` | 2 | PARTIAL — gesture authored; colour does not track harmony or authored energy |
| 14 Spectrum River | none | **frozen** `spectrogram_smooth` (`light_mode_spectrum_river.cpp:81–85`) | 3 | FAIL — stale spectrum replayed outward (stale replay) |
| 15 Spectrum River v2 | `low_energy` (`light_mode_spectrum_river_v2.cpp:55–56`) | frozen `spectrogram_smooth` (`:90–94`) | 2 | FAIL — content is stale; only breathing is authored |
| 16 Ember | `spectral_energy` (`light_mode_ember.cpp:44–45`) | centroid hue (frozen) + `hue_position` | 2 | PARTIAL — intensity authored; colour static/live drift |
| 18 Waveform Tempo (bench secondary) | `peak_scaled`, `vu_level`, `silence`, `spectral_energy`, `novelty`, tempo (authored-derived) (`light_mode_waveform_tempo.cpp:84–88,174–219`) | **live `waveform_peak_scaled`** OR-ed in (`:215`), colour helper | 2 | PARTIAL — live amplitude leak |
| 19 Tempo River | tempo (authored-derived) (`light_mode_tempo_river.cpp:95`) | frozen `spectrogram_smooth` (`:139–143`) | 2 | FAIL — stale content on an authored clock |
| 20 Tempo Comet | tempo, `bass_onset` (`light_mode_tempo_comet.cpp:85,174`) | colour | 2 | PARTIAL — best motion candidate; colour static/live drift |
| 21 Dense Forge | `novelty`, `spectral_energy`, `silence`, legacy `onset`, tempo (`light_mode_dense_forge.cpp:110–118`) | V2 `transient_level` (dead), frozen `spectrogram_smooth` (`:64,258,310,317`), centroid hue | 2 | PARTIAL |
| 22 Snapwave | `peak_scaled`, tempo (`light_mode_snapwave.cpp:55–60`) | motion oscillator built only from **zeroed** `chromagram_smooth` (`:68–79`) → `osc = 0`; dot sits at centre ± 0.10 tempo wobble (`:85`), brightness ×0.35 (`:112`) | 2 | FAIL — the gesture is lost |
| 23 Pulse Prism | `vu_level`, `low_energy`, `bass_onset`, tempo (`light_mode_pulse_prism.cpp:68–74`) | V2 `kick`/`transient` (dead), colour | 2 | PARTIAL — kick-primary rings lose their V2 trigger |
| 24 Dense Forge Chord | as 21 | `snap.chord` zeroed → `chord_ok` false (`light_mode_dense_forge_chord.cpp:253–272`) | 2 | PARTIAL — chord anchor dead |
| 25 Chroma Constellation | `spectral_energy` (drift), `silence` (`light_mode_chroma_constellation.cpp:95–99`) | star brightness = `snap.chroma_pc` (zeroed) (`:104–107`, `:149`) → stars fade to black | 2 | FAIL — plate goes dark (a gap) |
| 26 Percussion Burst | legacy `bass_onset` (`light_mode_percussion_burst.cpp:129–132`) | V2 kick/snare/hihat (dead) | 2 | FAIL — snare/hi-hat lanes silent |
| 27 Tempo Comet Anticipate | tempo, `bass_onset`, `silence` (`light_mode_tempo_comet_anticipate.cpp:93–117,214`) | colour | 2 | PARTIAL |
| 28 River Surge | `low_energy`, `spectral_energy`, `silence` (`light_mode_river_surge.cpp:105–118,168`) | frozen `spectrogram_smooth` (`:205–209`) | 2 | FAIL — stale content |
| 29 Tempo River Walk | tempo (`light_mode_tempo_river_walk.cpp:116`) | frozen `spectrogram_smooth` (`:188–192`) | 2 | FAIL — stale content |
| 32 Waveform Hybrid K1 — **mapped at `ed0aa984` (resident; = staged tree)** | `peak_scaled`, `vu_level`, `silence` (`light_mode_waveform_hybrid_k1.cpp:115–117,167`) | **live `waveform_peak_scaled`** OR-ed into `peak` (`:116`) → dot position (`:336`), trail decay (`:299`), colour walk (`:181`); and at `ed0aa984` **authored silence is overridden by live sound**: `silence = snap.silence && (peak < WFHYB_PRESENCE_FLOOR)` (`:117`), presence/seed no longer test silence (`:121,170`), quiet/colour gain no longer zeroed by silence (`:283–285`). Chroma zeroed → blend 0 → palette fallback at `CHROMA + hue_walk` (`:158,211`) + live `hue_position`. At `407fdf6f` (registry state) silence was authored-only (`:117` `silence = snap.silence`). | 2 | PARTIAL → acceptable after CR-A7. Note: with room audio the dot follows the mic even through authored silence |
| 33–37 WFHYB variants (Flux, Note, Wide, Sum, Step) | as 32 (`light_mode_wfhyb_k1_variants.cpp:151–190`) | live peak (`:152`); Flux/Note/Step/Sum colour logic reads zeroed chroma → never moves; Wide walks with peak (`:237`) | 2 | Flux/Note/Step/Sum FAIL (colour logic dead); Wide PARTIAL |

**Verdict.** No admitted mode is class 1. Seven are class 3 and ignore the stream entirely (Bloom, Bloom Fast, Waveform Fast, Waveform, Waveform Hybrid, Aurora, Spectrum River); the other 21 are class 2. Every mode becomes **palette-only hue** under authored mode: harmony is not carried by Prim8, `chromagram_smooth` is zeroed and the palette anchor is frozen; the only colour motion left is the live `hue_position` drift (room sound, not the show) and, in modes 32 and 35, the authored-pressure walk. Against THE LAW (colour must track harmony or energy, never a clock; one gesture; never a gap): a frozen anchor plus room-driven drift does not track the show, so it fails unless an effect walks the palette with authored energy; Constellation and Snapwave lose their gesture or go dark. Smallest change: `CR-A7-wfhyb-authored-drive.md` (mode 32 + 18 + 33–37, about 8 lines) makes the bench's current primary/secondary pair authored-driven with colour tracking authored energy. Without firmware change, mode 32 is authored-driven in practice only when the microphone hears near-silence (original audio on headphones).

Not escalated: one admitted mode (32) can be driven acceptably — conditionally today, properly after CR-A7.

**Resident primary at read-back is mode 22, Snapwave** (`lightshow=22`, §A1), which fails under authored mode (gesture lost). Lane D must set the intended mode before T2 (`:set_mode=32` persists via `save_config_delayed()`, §A3) and restore mode 22 afterwards.

### Bench-only motion battery at `ed0aa984` (modes 38–51)

`K1_FX_BATTERY=1` is set only on `k1_fe_bench_b489` (`platformio.ini:520` at `ed0aa984`; commit `753441a0` "restrict battery flag to the two audition environments"); the modes are enumerated at `config_types.h:257–272` and are selectable on the resident bench image (not filtered by `light_mode_is_enabled`). They are not in `k1_fe` and not in the acceptance set, so they are listed for Lane D only. All colour via `palette_manual_colour` (+ live `hue_position`). Scan: `raw/a7_scan_ed0aa984_fx_and_m32.txt`.

| Mode | Authored inputs | Live / zeroed inputs | Class |
|---|---|---|---|
| 38 lob_return | `vu_level`, `peak_scaled`, `silence`, legacy `onset`/`bass_onset` | gated on **live `max_waveform_val_raw` > floor** (`light_mode_fx_lob_return.cpp:37`) → dark when the mic hears silence | 2 |
| 39 accumulate_cascade | `vu_level`, `peak_scaled`, `low/mid/high_energy`, `silence` | same live raw gate (`light_mode_fx_accumulate_cascade.cpp:37–39`) | 2 |
| 40 front_refractory | `vu_level`, `peak_scaled`, `novelty`, `silence`, legacy `onset` | V2 `transient` (dead); colour phase | 2 (motion authored) |
| 41 reverse | `vu_level`, `peak_scaled`, `novelty`, `silence`, legacy `onset` | V2 `transient` (dead); colour phase | 2 (motion authored) |
| 42 scan | `vu_level`, `low/mid/high_energy`, `silence`, tempo | colour phase | 2 (motion authored) |
| 43 chain | `vu_level`, `low/mid/high_energy`, `silence`, `bass_onset` fallback, tempo | V2 `kick` (dead, falls back to `bass_onset`, `light_mode_fx_chain.cpp:68–75`); colour phase | 2 (motion authored) |
| 44 dilate_recoil | `vu_level`, `peak_scaled`, `silence`, legacy `onset` | **live `waveform_peak_scaled`** OR (`light_mode_fx_dilate_recoil.cpp:64–65`); `chroma_strength`, `chord` zeroed (`:68–74`) | 2 |
| 45 infall | `vu_level`, `peak_scaled`, `low/mid_energy`, `silence`, `bass_onset` fallback | **live `waveform_peak_scaled`** OR (`light_mode_fx_infall.cpp:61–62`) | 2 |
| 46 bounce | `vu_level`, `low/mid/high_energy`, `silence` | colour phase | 2 (motion authored) |
| 47 split_merge | `vu_level`, `mid_energy`, `silence` | `chroma_strength`, `chord` zeroed → harmonic term 0 (`light_mode_fx_split_merge.cpp:33–39`) | 2 |
| 48 stretch | `vu_level`, `low_energy`, `novelty`, `silence`, legacy onset/`bass_onset`, tempo | V2 `kick` (dead); frozen anchor colour | 2 (motion authored) |
| 49 pass_through | `vu_level`, `low/mid/high_energy`, `novelty`, `silence`, tempo | frozen anchor colour | 2 (motion authored) |
| 50 front_ca | `vu_level`, `peak_scaled`, `novelty`, `spectral_energy`, bands, `silence` | live raw gate (`light_mode_fx_front_ca.cpp:68`) | 2 |
| 51 orbit | `vu_level`, `peak_scaled`, bands, `silence` | live raw gate (`light_mode_fx_orbit.cpp:75`) | 2 |

Motion fully authored (colour aside) on the bench image: 40, 41, 42, 43, 46, 48, 49. These are the cleanest bench candidates for a T2 causation test, but they are audition modes, not admitted FE effects.

## A8 — Is the PRSM path compiled in?

| Check | Result | Evidence |
|---|---|---|
| Guards around PRSM/authored code | **None.** No `#if`/`#ifdef` around `audio/k1_prsm.*`, `audio/k1_authored_source.*`, the scanner branch in `check_serial` (`serial_menu.cpp:4154–4163`; only `K1_LOOK_LIB_V1` look-load capture precedes it, `:4139–4151`), the `.ino` publish (`:1144–1162`), the chroma zeroing (`:1565–1570`) or drop-cut (`led_utilities.h:558–566`, inside `K1_DROP_CUT_V1`, which is on) | FACT (read) |
| Source filter | `+<audio/k1_*.cpp>` and `+<serial/*.cpp>` in the inherited filter (`platformio.ini:43`), unchanged by `k1_fe`/bench additions | FACT `raw/env_resolved_407fdf6f.json` |
| Compiled | `Compiling …/audio/k1_authored_source.cpp.o`, `…/audio/k1_prsm.cpp.o` (bench log); same in `docs/forensics/runtime-evidence/20261103-fe-rc1/build_k1_fe.log:40,48` | FACT |
| Linked (symbols) | Both ELFs contain `k1_authored_on_frame`, `k1_authored_tick`, `k1_authored_intent`, `k1_authored_map_prim8`, `k1_authored_suppresses_live_update`, `k1_prsm_parse`, `k1_prsm_scanner_push`, and `check_serial::prsm_scanner` | FACT `raw/nm_prsm_symbols.txt` (`xtensa-esp32s3-elf-nm -C`) |
| Linked at the resident source | `k1_fe_bench_b489` @ `ed0aa984` (clean export): `k1_authored_on_frame`, `k1_authored_tick`, `k1_authored_intent`, `k1_authored_map_prim8`, `k1_authored_suppresses_live_update`, `k1_prsm_parse`, `k1_prsm_scanner_push`, `check_serial::prsm_scanner`, plus `k1_render_trace_on_frame`, `k1_render_trace_dispatch`, `rtrace_drain_task` | FACT `raw/nm_prsm_symbols.txt` (third block) |
| History | Added `3fc8cd8f` (16 Aug 2026, "PRISM-authored runtime ingress + B489A500 silicon proof"), ancestor of `407fdf6f` | FACT `/usr/bin/git merge-base --is-ancestor` |
| Resident image | read back `git=ed0aa984 env=k1_fe_bench_b489 epoch=1793984825`; PRSM sources identical to `407fdf6f`; the `ed0aa984` bench ELF links them → resident image contains the path **[INFERENCE from source identity + same-source build; the resident binary itself was not hashed]** | §A1 |
| Device read-back of authored state / PRSM counters | **None exists.** Indirect only: `:smart_status` `SMART_AUDIO_NOVELTY`/`SMART_AUDIO_ENERGY` from the snapshot (`serial_menu.cpp:568,621–624`); prior harness `scripts/agent/k1_authored_silicon_proof.py` uses this. ACQUIRE is never observable (`k1_authored_source.cpp:70–87`). | FACT → `CR-A8-authored-status-readout.md` |

### Device-side evidence surfaces Lane D can read without a firmware change (resident `ed0aa984`, env `k1_fe_bench_b489`)

**1. `:rtrace_arm` / `:rtrace_status` / `:rtrace_dump` — compiled in, primary edge only.**

| Property | Fact | Evidence |
|---|---|---|
| Gate | Commands exist only under `#ifdef K1_RENDER_TRACE_V1` (`serial_typed_cmd_table.def:67–71`, flag `CMD_HARNESS`); the whole TU is gated (`visual/k1_render_trace.cpp:5`). `K1_RENDER_TRACE_V1` is in `k1_fe_bench_b489` (`platformio.ini:535` at `ed0aa984`) and **not** in `k1_fe`. Symbols present in the `ed0aa984` bench ELF. | FACT |
| What it captures | One tap: `k1_render_trace_on_frame((const uint8_t*)leds_out, CONFIG.LED_COUNT, CONFIG.LIGHTSHOW_MODE)` in `show_leds()` (`visual/led_utilities.h:1519–1524`) = the **final post-gamma, post-brightness primary buffer, RGB8**. The dual-edge layout needs `K1_B489_WS2816_V1` or `K1_EMU_FIXTURE` (`k1_render_trace.h:39–41`), neither in this env, so storage is single-edge and a secondary buffer is refused (`k1_render_trace.cpp:117–119`). **The secondary edge is not captured on the bench image.** | FACT |
| Frames, cadence | PSRAM ring, capacity 3,000 frames × 960 B (`k1_render_trace.cpp:33–37`), allocated with `ps_malloc` on first arm from the command path (`:93–95`). `:rtrace_arm=<seconds 1..600>[,<every_n 1..100>][,stim]`, default 30 s, every 4th shown frame (`:46,209–234`); stops at capacity or deadline (`:123–126`). Each record: `millis()` and the primary mode (`:140–141`). At the recorded `LED_FPS ≈ 200`, every 4 ≈ 50 frames/s for up to 60 s; every 1 ≈ 15 s. `stim` overwrites the buffer with a test ramp — never use it for show evidence (`k1_render_trace.h:53–55`). | FACT (rates are arithmetic on the recorded `LED_FPS`) |
| Dump format | `[RTRACE-BEGIN frames=N every=E px=P fmt=rgb8hex bpp=8 crc32=XXXXXXXX]`, then one line per frame `F,<index>,<millis>,<mode>,<hex RGB8 × px>`, then `[RTRACE-END]` (`:252–310`); CRC-32 over the stored frames (`:258–261`). Decoder named in the header: `hue_coverage.py` (rgb8). | FACT |
| Perturbation | Per shown frame while armed: one `memcpy` of ≤ 480 B + `memset` inside a `portENTER_CRITICAL` spinlock on the Core-1 show path (`:57–63,109–145`); no print on the render path. The dump drains on an idle-priority task pinned to Core 0 with `vTaskDelay(1)` every 64 frames (`:65–89,307`) so audio keeps running; arming is rejected while a drain is busy; the header requires stopping other serial streams and sending no commands until `[RTRACE-END]` (`k1_render_trace.h:27–30`). Cost of the capture on render timing: **UNKNOWN** (not measured). A 3,000-frame dump is ≈ 2.9 MB of hex on USB. | FACT (code); timing cost UNKNOWN |
| Use for T2 | Captures the primary edge reaching the LEDs with `millis()` stamps → can score authored vs live vs rejected runs on the primary edge. It does **not** show authored state and does **not** capture the secondary edge; the second edge needs the camera or a firmware change. During the dump, do not stream PRSM (the drain shares USB). | INFERENCE from the above |

**2. The `[AP] … peak_scaled= … silence=` line — compiled in everywhere, runtime-switched, shows live Core-0 values, not the authored snapshot.**

| Property | Fact | Evidence |
|---|---|---|
| Where / when | `acquire_sample_chunk()` (`audio/i2s_audio.h:500`), Core 0, once per `K1_AP_STREAM_INTERVAL_MS` (default 1,000 ms, `:1539–1541`) when the runtime flag `AP_STREAM_ENABLED` is true (`:1542`). No compile-time gate around it. `AP_STREAM_ENABLED` defaults to `AP_STREAM_DEFAULT_ON`, which is 1 (`system/globals.h:599–602`) — on at every boot; toggled by `:ap_stream=on|off` (`serial_typed_dispatch.cpp:217`), by the **hotkey `a`** (`serial_menu.cpp:2221–2225` — one more byte a broken PRSM frame can flip, CR-A3), and cleared by the stream-stop path (`serial_tx.cpp:75`). The bench was left with `:ap_stream=on` (restoration log). | FACT |
| Live fields (Core-0 globals; **unchanged by authored mode**) | `SSL` (`CONFIG.SWEET_SPOT_MIN_LEVEL`), `DC`, `max_raw` (`max_waveform_val_raw`), `follower`, `peak_scaled` (= global **`waveform_peak_scaled`**, the live mic peak — not `K1AudioSnapshot.peak_scaled`), `response_gain`, `silent_scale`, `silence` (the global live classifier), `sil_pk`, `rms_raw`, `pky`, `dim`, `cal_*`; the IM69D raw block; the trailing `k1_loud … agc_gain … lightshow=` block (`:1676`, `lightshow` = `CONFIG.LIGHTSHOW_MODE`) | FACT `i2s_audio.h:1543–1557,1561–1565,1676` |
| Authored-derived fields | `bpm conf lock phase beat bstr` from `k1_tempo_read()` and `onset bass ostr` from `k1_onset_beat_read()` (`:1543–1544,1556–1557`). Both producers are fed the published snapshot (`.ino:1210,1243` at `ed0aa984`), so under AUTHORED they reflect the authored stream (impact/mass/pressure) **one hop late** (the print runs inside `acquire_sample_chunk`, before that loop publishes: `.ino:1013` vs `:1174–1243` at `ed0aa984`). The legacy `bass_onset` is printed; V2 kick/snare/hihat are not. | FACT (code order) |
| Not printed | No snapshot field (`vu_level`, `novelty`, `low/mid/high_energy`, snapshot `silence`), no authored state, no PRSM counters | FACT |
| Use for T2 | Shows that live audio is (or is not) present at the mic while authored mode runs, and lets tempo/onset be compared against the stream at 1 Hz. It cannot by itself show the authored snapshot; `:smart_status` can (`SMART_AUDIO_NOVELTY/ENERGY`, `serial_menu.cpp:621–624`), polled, and only between PRSM frames (a `:` line must be sent whole, §A3). | INFERENCE from the above |

Net: without firmware, Lane D can (a) confirm identity (`:build`), (b) sample the authored snapshot by polling `:smart_status`, (c) capture the primary edge with rtrace, (d) watch live mic level and authored-derived tempo/onset on `[AP]`. It cannot read the authored state, ACQUIRE/RECOVERY transitions, frame counters, or the secondary edge’s pixels. CR-A8 closes the first three; the secondary-edge capture would need a separate change (dual-edge rtrace exists only behind `K1_B489_WS2816_V1`/`K1_EMU_FIXTURE`).

## A9 — Authored-mode timing facts

| Fact | Value | Evidence |
|---|---|---|
| Nominal rate | 120 Hz is a host default, not a device constant: `tools/intent_cdc_stream.js:35` (`--hz` default "120"), `prism_minimal_editor/server.js:238,336` (`payload.hz ?? "120"`), `public/app.js:448,786,843` (`hz: 120`). `PlaybackEngine` takes `opts.hz` with no default (`src/playback.js:54–60`). Host accepts 1–1000; device rejects < 30 or > 240 (`k1_authored_source.h:17–18`); the hz byte is `hz & 0xff` (`src/cdc.js:28`). | FACT (PRISM.studio read-only, `~/Workspace_Management/Software/.g5r-clean/PRISM.studio`) |
| Host scheduling | Drift-corrected `setTimeout` against `performance.now()`: `const elapsedUs = t_us - this.#bundleStart; const targetWall = this.#wallStart + elapsedUs / 1000.0; const now = performance.now(); const delay = Math.max(0, targetWall - now); this.#timer = setTimeout(…)` (`src/playback.js:199–205`). Wall clock, not an audio clock; `playback.js` plays no audio. | FACT |
| Host seq on play / seek | `play()` resets `seq = 0` (`playback.js:92`); `seek()` keeps seq incrementing and sends one immediate frame (`:119–154`) → the device sees a continuous seq on seek and **never enters ACQUIRE from a PRISM.studio seek**; a seq-gap test must be synthesised by the test harness | FACT |
| Host comment vs device | `playback.js:210–211` says "K1's 250ms freshness timeout"; device freshness is 50 ms and the header says "Do not copy the USB-bridge 250 ms" (`k1_authored_source.h:12–16`) | FACT (stale host comment) |
| Partial-write risk | `writeCdcPort` loops `fs.writeSync` and throws after 5 zero-byte retries, possibly mid-frame (`src/cdc.js:131–142`) | FACT → CR-A3 |
| Freshness | 50 ms (`k1_authored_source.h:16`); AUTHORED→RECOVERY on the first `k1_authored_tick` with age > 50 ms, RECOVERY→STANDALONE on the next (`k1_authored_source.cpp:96–105`); live update resumes as soon as the state is RECOVERY, because `k1_authored_intent()` returns false outside AUTHORED/ACQUIRE/DRAIN (`:111–121`) | FACT |
| Seq gap | `K1_AUTHORED_SEQ_GAP_MAX 3`: forward gap ≤ 3 continuous; larger, backward or reset → ACQUIRE then AUTHORED in the same call; never rejected (`:54–61,70–87`) | FACT |
| Device clock | Arrival time: `k1_authored_on_frame(&prsm_frame, t_now)` with `t_now = millis()` of the AP loop (`serial_menu.cpp:4160`; `.ino:911`); `t_us` is stored (`:50`) but never used for scheduling | FACT |
| Drain rate | `check_serial()` once per AP loop (`.ino:959`), ≤ 128 bytes per call (`serial_menu.cpp:4135`). AP loop measured 137.41 Hz on the bench (`SYSTEM_FPS`, restoration dump). Capacity ≈ 128 × 133 ≈ 17 kB/s vs 120 × 34 = 4,080 B/s (≈ 4.2× headroom); ≈ 30.6 B per loop on average. | FACT (arithmetic on cited values) |
| Receive buffer | USB-Serial-JTAG RX queue 256 B; the interrupt drops bytes when full (Arduino-ESP32 3.2.0 `HWCDC.cpp:123,309`); firmware never enlarges it in FE (`setRxBufferSize` only in excluded `k1_usb_audio_input.cpp:262`). 256 B ≈ 63 ms of stream: a loop stall longer than that loses bytes (the 18.6 ms autosave stall is inside the margin). | FACT |
| Device quantisation | Frame read at `check_serial` (`.ino:959`) → same loop publishes the snapshot after `acquire_sample_chunk` (`:983`) waits for the next 96-sample hop (7.5 ms at 12.8 kHz) → render thread (≈ 200 FPS, `LED_FPS 200.43`) picks it up next frame → LED write. **[INFERENCE]** arrival-to-render ≈ 0–7.5 ms (wait for loop) + up to 7.5 ms (hop wait) + ≈ 5 ms (render) + strip write; not measured, physical latency **UNKNOWN**. With 120 Hz frames and a ≈ 133 Hz loop, some loops get no frame and some get two (only the last is kept). | Code order FACT; durations INFERENCE |

Implication: alignment of light to the recording is the host's job (start offset and pacing of PRSM frames against the audio actually heard); the device adds an unmeasured, roughly one-to-three-frame quantisation and never corrects with `t_us`.

## Files

- `lane-a/ASSET.json`, `lane-a/A-P0-baseline.md` (this file)
- `lane-a/CR-A7-wfhyb-authored-drive.md`, `lane-a/CR-A8-authored-status-readout.md`, `lane-a/CR-A3-prsm-hotkey-fallthrough.md`
- `lane-a/raw/`: `asset_envelope.py`, `asset_envelope_loreen.txt`, `a7_scan.py`, `a7_scan_part1.txt`, `a7_scan_part2.txt`, `a7_scan_helpers_lightshow_modes.txt`, `a7_scan_wfhyb_k1_DIRTY_TREE.txt`, `build_k1_fe_bench_b489.log`, `build_k1_fe.log`, `pio_project_config_407fdf6f.json`, `env_resolved_407fdf6f.json`, `nm_prsm_symbols.txt`, `images/` (both envs' bin/elf/bootloader/partitions + `SHA256SUMS.txt`)

Changelog
- 2026-11-09 Lane A: created (A1–A9, three CRs, asset).
- 2026-11-09 Lane A: revised for the lead's read-back (resident `ed0aa984`, epoch 1793984825, registry stale, primary mode 22); mode 32 mapped at `ed0aa984`; bench motion battery 38–51 mapped; A8 adds rtrace and `[AP]` evidence surfaces; A6 restore route corrected.
- 2026-11-09 Lane A: lead correction applied — A1 read-back PASS with the `ed0aa984` line, registry stale (`407fdf6f`/`8accab34`); A6 nearest rollback material = clean `ed0aa984` rebuild (807,568 B, `c08bb61d…`, not byte-identical), M1 plans no flash, live-baseline restore = stop stream + restore changed settings; `.ino`/mode-32 citations re-checked against `ed0aa984` (PRSM, serial, led_utilities identical; mode 32 differs by the silence change, mapped in §A7).
