---
abstract: "FW lead receipt, 3 Nov 2026 AWST: K1 FE firmware release candidate fe-1.0.0-rc1 (env k1_fe) built, reviewed and tagged on lane/k1-fe-release; web-flasher FE bundle built and its customer mode checked in a browser; G5 bring-up sheet written. Nothing was flashed: no K1 was plugged into the Mac, so every on-device proof is still open."
---

# Receipt — FW lead, K1 FE firmware release (3 Nov 2026, 06:40 AWST)

Charter: `~/K1_Launch_Planning/00-Governance/team/LEAD-FW-FE-RELEASE.md`. Branch `lane/k1-fe-release`, commits `dc94f988` + `6b313500`, local tag `fe-1.0.0-rc1` → `6b313500`. Nothing pushed.

## What happened, in plain English
- The FE firmware exists. It is the shipping Main RPL build plus the FE board's needs: the 3.5 mm jack switches the show to line-in and back, the LED power is only switched on with a 20 V USB-C supply, a heartbeat LED blinks, and one serial command programs the USB-C power chip.
- An independent reviewer found no critical bugs and four real risks (unsafe NVM retry, possible full-plate flashing on a weak supply, probe logging shipping, calibration learning from line-in). All four are fixed in `6b313500`.
- The shipping Main RPL build is unchanged: its three reproducible code/data sections hash the same before and after this lane (independent verifier, see below).
- **Nothing has run on a K1 yet.** No board was attached to the Mac during this session (`/dev/cu.*` empty; `ioreg` showed only a USB billboard and a SidePulseDot). Line-in, mic, and web-flasher-on-hardware proofs are still to do.

## Read first
`COURSE-2026-11-02.md`, `team/OPERATIONS.md`, the charter; repo `CLAUDE.md`, `.claude/CLAUDE.md`, `docs/hardware/device-build-registry.md`; `K1-FE-Board/FE-BOARD-BRIEF.md` and `OPEN-ITEMS.md` (OI-02/03/05/06/07/08/09/11/15/19), `NETLIST-EXTRACT.md` (pull resistors on every FE control net); PCM1808 proof `docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/` (PCMCLK_RECEIPT, PREFLIGHT pin table, boot logs); ST `usb-c/STUSB4500` headers and SparkFun_STUSB4500 source (NVM sequence and field map).

## Deliverables

| # | Charter item | State | Evidence |
|---|---|---|---|
| 1 | Env `k1_fe` | **Done in source, builds clean.** Not run on hardware. | `platformio.ini [env:k1_fe]`, `system/k1_fe_board.*`, `audio/i2s_audio.h` switch block |
| 1a | PCM1808 line-in, MID policy, jack GPIO40, insert→line / remove→mic | Done (P6 canonical path, MID, −24.08 dB trim). Noise calibration holds the mic. | same |
| 1b | LED_ENABLE only after INPUT_20V_PG; LED_PG_A/B logged; 5 V-only dark with reason | Done. POWER_PERMIT rises first, both drop at once on PG loss. Three PG drops in 10 s while lit latch the LEDs off (strobe guard). | `k1_fe_board.cpp` power policy |
| 1c | Heartbeat GPIO5, 1 Hz, from render task | Done (`led_thread`, Core 1) | `.ino` render loop |
| 1d | RNG_SEED_PIN and GPIO4 NFC hold: one-line comment each | Done | `constants.h`, `k1_pcm1808_input.cpp` |
| 1e | FE device-identity entry | **Open (G5)**: no FE MAC exists. `k1_fe` added to Main RPL `9087A500` allowlist as the bench proof unit. | `k1_device_identities.json` |
| 2 | `:pd_nvm_write` 5 V 0.5 A / 20 V 3 A / 20 V 5 A, verify, PASS/FAIL | Done in source. Writes only over ST's factory image; `=golden` is the reviewed recovery. Also `:pd_status`, `:fe_status`, `:audio_src`. **Never run on a chip.** | `k1_fe_board.cpp` |
| 3 | Tag `fe-1.0.0-rc1`; `build` reports tag; SHA-256; bench control built at same commit | Done. `[k1-build-provenance] env=k1_fe git=6b313500 … tag=fe-1.0.0-rc1` | `docs/forensics/runtime-evidence/20261103-fe-rc1/` |
| 4 | Web flasher manifest for `k1_fe`, one variant, `?mode=simple` checked in a browser, bundle zip | Done on the host. Flashing a real K1 from a clean browser profile: **open**. | `webflash_*` files in the evidence folder |
| 5 | `docs/handover/FE-BRINGUP.md` | Done | file |

### Release images (built at the tag, clean firmware tree)
| Env | firmware.bin bytes | SHA-256 | RAM / flash |
|---|---|---|---|
| `k1_fe` | 753 216 | `5a05d2643d67752e38d08ebad75d3a25d933d51f66ee552c324f508e5cd75678` | 44.1 % / 11.5 % |
| `k1_main_rpl_im69d` (bench control) | 728 336 | `9ec1a40e3dd3227fdccca35e73456a3c59fe22aaaa6d417d030c867bd2d844e1` | 35.8 % / 11.1 % |

Bootloader `12c9a10f…8761` and partitions `bd0f7954…f6ce` are the same for both, and equal the pins recorded for B489 in the device registry. Each build stamps its own build time, so a rebuild gives a new firmware.bin hash. The three reproducible sections are in `stable_sections_at_tag.txt`. `k1_fe` uses 27 KB more RAM than Main RPL: the PCM1808 ring, snapshot and DMA buffers, as in the P6 probe.

### Web-flasher bundle
`_scratch/fe-rc1/k1-webflash-bundle-fe-1.0.0-rc1.zip` (not in git: it holds firmware binaries), SHA-256 `d9b6b5e47404043f89e447289f5b84e6956514fcd11fc0786f19d9a6f9d693db`, 12 files. Manifest: one variant `k1_fe` "K1 Founders' Edition", `simpleEnv=k1_fe`, git `6b313500`, not dirty. Offsets come from the real `partitions.bin`: 0x0 / 0x8000 / 0xE000 / 0x10000. Every image MD5 matches `.pio/build/k1_fe`. Headless Chromium: simple mode shows only "UPDATE K1" (`updateBtn_visible=True variantSelect_visible=False`); advanced mode lists exactly one variant; no console errors. Screenshots were read and checked: `webflash_simple_mode.png`, `webflash_advanced_mode.png`. The workflow `webflash-release.yml` is already in `.github/workflows/` (tracked before this lane); it was not edited. The bundle was assembled with its "Assemble bundle" steps run locally.

## Checks run
| Check | Command | Result |
|---|---|---|
| Host suite, first run (pre-commit tree) | `python3 -m pytest tests/ -q` | 1925 passed, 3 failed. Two failures were this change's new serial rows (re-recorded in `k1_serial_safety.py`); the third was another lane's uncommitted effect edit, set aside before committing. |
| Commit gate `dc94f988` | repo pre-commit (`pytest tests/` + `pio run -e k1_hardware`) | 1928 passed · k1_hardware SUCCESS |
| Commit gate `6b313500` | same | 1928 passed · k1_hardware SUCCESS |
| Release builds at tag | `pio run -e k1_fe`, `pio run -e k1_main_rpl_im69d` | both SUCCESS (logs in evidence folder) |
| Independent review | code-reviewer subagent on the full diff | no critical issues; 4 risks fixed in `6b313500`; nits listed below |
| Independent verification | verifier subagent, clean `git archive` exports in /tmp | see "Verifier" |

### Verifier
Fresh-context verifier subagent. It built from `git archive` exports in /tmp and did not touch the repo tree.
- **C1 PASS.** `fe-1.0.0-rc1` is an annotated tag on `6b313500`, contained only in `lane/k1-fe-release`; the chain is `6b313500 → dc94f988 → 59757c62`.
- **C2 PASS: shipping build unchanged.** `k1_main_rpl_im69d` built from `59757c62` and from the tag gives identical `.dram0.data` `8bed64b5…c1a5`, `.iram0.text` `ecc642b3…730d` and `.iram0.vectors` `0a38b8c1…7704`. Both builds exited 0.
- **C3 PARTIAL, my method error.** `k1_fe` builds from the export (exit 0). `.iram0.vectors` matches my in-repo value; `.dram0.data` and `.iram0.text` do not. Cause, found by the verifier: the provenance git-hash string lands in those two sections. An export stamps `git=unknown`, so 76 and 434 bytes differ at equal sizes. I had assumed it only reached flash rodata; that was wrong. The verifier hashed the repo's own ELFs read-only, and they match my recorded values exactly. So the numbers in `stable_sections_at_tag.txt` hold only for builds inside the git checkout.
- **C4 PASS.** No effect, GDFT, tempo, onset, AGC or chord file is in the diff. The `platformio.ini` change is only the new `[env:k1_fe]` block (no sample-rate, hop or fast-math line). Each build log has 2 `warning:` lines, the same count as the shipping envs, none from `k1_fe_board.cpp`.

## Could NOT be proven in this session (named, not claimed)
- **Line-in on the bench K1 (PCM1808 classifier PASS on `k1_fe`).** No K1 was connected. Needs the Main RPL `9087A500` with its PCM1808 module plugged in.
- **Mic path on silicon (CAL line and RMS in the Main RPL range).** Same reason. The host proof is the byte-identity of `k1_main_rpl_im69d`'s stable sections.
- **Web flasher flashing a K1 in ≤3 clicks.** The page's customer path is "Update K1", then the browser's port picker (pick and Connect): three clicks by design. Not exercised on a device.
- **G5 items that need an FE board:** LED_ENABLE/POWER_PERMIT sequencing, LED_PG readback, jack detect on GPIO40, STUSB4500 NVM write and contract read-out, heartbeat, the FE line-in trim (the FE divider is −9 dB, OI-05; the release carries the 7 Sep module's −24.08 dB), and the boot 20 V timing.
- **STUSB4500 factory image on JLC-fitted parts.** The tool assumes ST's published factory sectors. A part with a different image is refused, with its sectors printed, rather than written.

## Findings for the Operations Manager (decisions, not the Captain's)
1. **BLE-MIDI is not in the shipping Main RPL build.** The charter says `k1_main_rpl_im69d` carries the BLE-MIDI control plane; `platformio.ini` shows it does not. Only bench envs link `network/ble_remoted_central.cpp` (`K1_BLE_REMOTED`, the K1 as a BLE *central* to the VJ deck). COURSE decision 3 needs BLE-MIDI control, so `k1_fe` needs a decision: which BLE role, and whether to add it before G5.
2. **The web flasher refuses every unregistered MAC** (`identityPolicy.unknownMac: refuse`). That is fine for G5 (register each board), but no customer unit could update itself. The customer-update policy must change before G7. For example: allow unknown MACs only for `k1_fe`, when the board answers `build` with `env=k1_fe` or is blank.
3. **5 V-only behaviour conflicts between sources.** The charter says LEDs dark on 5 V-only; OI-07 says plain 5 V USB-C "can run the board and a dim LED show". I followed the charter.
4. **Reviewer nits left as they are:** a one-hop click from resampler state when line-in starts; the mic DMA backlog of about 3 hops on unplug; `:pd_nvm_write` blocks the audio loop for about 1 s (a QC-only command); no 1 ms delay after each I2C write (SparkFun has one).

## Files touched (commits `dc94f988`, `6b313500`)
`SPECTRASYNQ_K1_FIRMWARE/`: `SPECTRASYNQ_K1_FIRMWARE.ino`, `audio/i2s_audio.h`, `audio/k1_audio_ingress.h`, `audio/k1_audio_source.h`, `audio/k1_pcm1808_input.cpp`, `audio/k1_pcm1808_input.h`, `serial/serial_menu.cpp`, `serial/serial_typed_cmd_table.def`, `serial/serial_typed_dispatch.cpp`, `serial/serial_typed_dispatch.h`, `system/constants.h`, `system/system.h`, `system/k1_fe_board.cpp` (new), `system/k1_fe_board.h` (new). Repo: `platformio.ini`, `scripts/agent/pio-build.sh`, `scripts/platformio/k1_build_provenance.py`, `scripts/platformio/k1_device_identities.json`, `scripts/regression-harness/k1_serial_safety.py`, `tools/webflash/make_manifest.py`, `docs/handover/FE-BRINGUP.md`. This receipt and `docs/forensics/runtime-evidence/20261103-fe-rc1/` are in the follow-up docs commit.

## Workspace state left behind
- The checkout is on `lane/k1-fe-release`. Another lane's uncommitted work was found in the tree: mode-32 `wfhyb_sat_ema` edits, position-smooth probe envs, 22 deleted capture/deploy files, and a skill file. It was set aside only for the commits and release builds, then restored byte-for-byte (`cmp` against `_scratch/fe-rc1/foreign-backup/`). It is still uncommitted in the working tree. `lane/k1-tempo-lock-r1` is unchanged at `59757c62`.
- `tools/webflash/manifest.json` (git-ignored) was overwritten by the FE run. It was restored from the tracked `dist/webflash-deploy/manifest.json` (git `8ed45e9c`, three homes); all 12 image MD5s match the copies in `tools/webflash/firmware/`.
- No device was flashed, so `device-build-registry.md` §2 is unchanged.

## Needs Captain
1. **Plug the Main RPL bench K1 (chip `9087A500`, the unit with the PCM1808 line-in module) into this Mac with USB-C.** Physical action only; the agent does the rest. With it attached, the next FW session flashes `fe-1.0.0-rc1` with `bash scripts/agent/k1-flash-verified.sh k1_fe --port <port>`, captures the classifier, mic and line-in lines to `docs/forensics/runtime-evidence/<date>-fe-rc1/`, and drives the web flasher in Chrome by computer use. The Main RPL product restore afterwards is `k1_main_rpl_im69d`.

## Ship path (what "shipped" means for this firmware)
1. Already in source: `fe-1.0.0-rc1` on `lane/k1-fe-release` (local tag, not pushed).
2. Remaining: (a) bench proof on Main RPL once it is plugged in (FW lead); (b) Ops decisions 1–2 above (Operations Manager); (c) G5: flash each FE board, register its MAC, run the three checks in `FE-BRINGUP.md`, set the line-in trim, fix anything found (FW lead with the HW/Build leads); (d) merge to main on host gates and push the branch and tag (Operations Manager's call; nothing has been pushed).
3. Who acts: the Captain only for the plug-in in "Needs Captain"; everything else is agent work.
4. Shipped = an FE board running a tagged `fe-1.0.0` (no `-rc`) whose `:build` reports that tag, with all three checks in `FE-BRINGUP.md` passing and recorded in the device registry.

---
| Date | Author | Change |
|------|--------|--------|
| 2026-11-03 | agent:claude (FW lead) | Created. |
