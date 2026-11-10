---
abstract: "FW lead receipt, 10 Nov 2026 AWST. The FE release now targets the board the Captain moved to, K1-FE-Gx (5 V USB-C, no STUSB4500): its pin map is on the release lane, tagged fe-1.0.0-rc2, built clean, shipping Main RPL build proven byte-unchanged, bring-up sheet rewritten for Gx. Nothing flashed: no FE board exists and no bench K1 was plugged in (only the parked lane's K1-S3). Web-flasher bundle for rc2 is held by the flasher's own safety rule until a Gx board is registered at G5. Evening update (22:35–23:50): sections \"K1-FE-SHOW fixes\" (candidate a6bad318, owed from the 16:18 session) and \"K1-FE-SHOW fixes, round 2\" (245ed510: a show no longer restarts on short stream loss; prepared shows reach full level) with checks, mapping, ship path and the judging prompt. Host and emulator only; nothing flashed."
---

# Receipt — FW lead, K1 FE firmware release (10 Nov 2026, AWST)

Charter: `~/K1_Launch_Planning/00-Governance/team/LEAD-FW-FE-RELEASE.md`. Read first: `COURSE-2026-11-02.md`, `team/OPERATIONS.md`, the charter, `RECEIPT-FE-FW-2026-11-03.md`, `docs/hardware/device-build-registry.md`, the Gx firmware repair package (`~/Downloads/K1-FE-Gx-Firmware-Repair/README.md`) and its board-side receipts (`K1-FE-Board/outputs/gx-adc-header-20261108/firmware-pinmap/`). Branch `lane/k1-fe-release`. Commits `c44172fa` (code), `545f00e4` (bring-up sheet, tagged), plus the docs commit holding this receipt. Nothing pushed.

## What happened, in plain English
- **The FE firmware now matches the FE board.** Since rc1 the Captain moved the board to K1-FE-Gx: 5 V USB-C, no STUSB4500 power chip, no 20 V input, an ADC test header, and 11 of its pins moved. The firmware for Gx existed only on a side branch (`fix/k1-fe-gx-repair-20261108`). I brought just that board-support commit onto the release lane, without the bench light modes 52–66 or the effect-performance work that sat under it on the same branch.
- **Release `fe-1.0.0-rc2` is tagged and builds clean.** It reports `tag=fe-1.0.0-rc2` with no "dirty" mark. Its LED outputs are GPIO 15/16/17/18, read from the compiled file.
- **The shipping Main RPL build is unchanged by this.** Built before and after, its three reproducible sections are byte-identical.
- **A cross-flash hazard is closed.** rc1 allowed `k1_fe` onto the Main RPL. The Gx image drives GPIO8 at boot; on the Main RPL GPIO8 is the microphone's data line. `k1_fe` is now blocked from every unit until the first Gx board is registered.
- **The bring-up sheet is rewritten for Gx.** It now has the Gx pin table, a USB-C power check that replaces the old 20 V check, and the new PCM1808 pins. Every line in it comes from the source; none has been seen on a board.
- **Nothing ran on hardware.** The only board on USB was `DC:54:75:EA:36:14`, the parked DualMCU lane's K1-S3 unit, which another lane marks read-only. I left it alone apart from one MAC read to identify it, which reset it once. No B489 and no Main RPL was attached.

## Deliverables (charter order)

| # | Charter item | State now | Evidence |
|---|---|---|---|
| 1 | Env `k1_fe` | **Done in source for K1-FE-Gx; builds clean. Not run on any board.** The charter's 20 V items (LED_ENABLE after INPUT_20V_PG, LED_PG readback) do not exist on Gx. Gx instead reads the USB-C CC lines and grants an LED current budget: 0 / 800 / 1900 mA estimated for plain USB / 1.5 A / 3 A, and sets POWER_PERMIT only on a stable 3 A source. The jack is now on GPIO42 and the heartbeat on GPIO8. The old 20 V profile is kept behind `#else`. | `system/k1_fe_board.*`, `system/k1_fe_gx_power_policy.h`, `visual/k1_fe_gx_led_power.h`, `tests/test_k1_fe_gx_contract.py`, fixture `tests/fixtures/k1_fe_gx_native_pin_map.json` |
| 1e | FE device identity | **Open (G5).** `k1_fe` is in `blocked_envs` until a Gx MAC exists; removed from the Main RPL allowlist. | `scripts/platformio/k1_device_identities.json` |
| 2 | `:pd_nvm_write` STUSB4500 tool | **Obsolete on Gx (no STUSB4500).** Still in source for the old profile only. The QC sheet should not reference it for Gx. | — |
| 3 | Release tag | **`fe-1.0.0-rc2` → `545f00e4`** (annotated, local). rc1 (`6b313500`) is for the old 20 V board; do not flash it to a Gx. | `docs/forensics/runtime-evidence/20261110-fe-rc2/tag.txt` |
| 4 | Web flasher for the release | **Held by design.** `make_manifest.py` refuses any image with no registered board ("refusing to ship an ungated webflash row"). It runs as soon as the first Gx MAC is registered at G5. No manifest was changed. | `20261110-fe-rc2/webflash_make_manifest.txt` |
| 5 | `docs/handover/FE-BRINGUP.md` | **Rewritten for Gx and rc2.** | file |

### Release images (built at `fe-1.0.0-rc2`, `545f00e4`)
| Env | firmware.bin bytes | SHA-256 | RAM / flash |
|---|---|---|---|
| `k1_fe` (release, K1-FE-Gx) | 764 832 | `ffeb3c65abaadb22a6e263a715218ac3aa58e71b3a9e9e4cfb63c1017de8e4ba` | 45.4 % / 11.7 % |
| `k1_fe_bench_b489` (bench FE image) | 759 888 | `83aaa1bc3795757991a53dab73e8c687e8a66faad37daaf3620c38a9c065a824` | 48.2 % / 11.6 % |
| `k1_main_rpl_im69d` (bench control) | 729 632 | `1bd4c9f4d952761ccd2e96ca49d47dd11579f847e21083827aaf4231d716a8e1` | 36.4 % / 11.1 % |

Bootloader `12c9a10f…8761` and partitions `bd0f7954…f6ce` are unchanged from rc1. Each build has the same two compiler warnings as the shipping build. `k1_fe` RAM (148 720 B) equals the Gx repair package's tested build. Each rebuild stamps a new build time, so `firmware.bin` hashes change on rebuild.

## Checks run
| Check | Result | Evidence |
|---|---|---|
| Gx contract tests before committing | 4 passed | `tests/test_k1_fe_gx_contract.py` |
| Commit gate, first attempt | **blocked**: 2 failed (my guard edit left `k1_fe` in no allowlist and no block list). Fixed by listing it in `blocked_envs`; both files then passed (34 tests). | `test_im69d_env_static.py`, `test_k1_upload_guard.py` |
| Commit gate `c44172fa` | 2074 passed, 2 skipped; `pio run -e k1_hardware` SUCCESS | gate output |
| Release builds at the tag | all three exit 0; `k1_fe` stamps `tag=fe-1.0.0-rc2` | `20261110-fe-rc2/build_*.log`, `release_sha256.txt` |
| LED pins in the compiled release | `ClocklessController<15,16,17,18>` in `k1_fe` and in `k1_main_rpl_im69d` | `nm` on both ELFs |
| Shipping build unchanged | `.dram0.data`, `.iram0.text` and `.iram0.vectors` are byte-identical between `aac13ff9` (before Gx) and the tag | `20261110-fe-rc2/shipping_sections_pre_vs_rc2.txt` |

## My method errors this session (recovered)
- The first commit attempt was killed mid-test when the previous session ended; the staged work was intact and was re-committed.
- The first two shipping-build comparisons were invalid: the first piped objcopy to `/dev/stdout` (permission denied, so both sides hashed nothing), and the second compared builds with different-length git stamps. Both are recorded in the evidence file; the valid comparison is the third.
- To compare in-repo I checked out `aac13ff9`. The in-repo build failed (PlatformIO's temporary `.ino.cpp` went missing), and switching back changed `platformio.ini`, so PlatformIO cleared every build folder, including the first rc2 images. I returned the checkout to `lane/k1-fe-release`, rebuilt all three at the tag, and re-recorded the hashes. The table above is the second build. The earlier hashes (`4ce6bbaa…` etc.) no longer correspond to any file.
- The refused web-flasher run copied the k1_fe images into the git-ignored `tools/webflash/firmware/k1_fe/` before refusing. I removed that folder (it did not exist before) after checking that it held only this build's images.
- An untracked evidence file I had written earlier in the session (`shipping_sections_pre_vs_rc2.txt`, the invalid comparison) was overwritten with the valid result. The hook backed up the old version.

## Could NOT be proven this session (named, not claimed)
- **Mic and line-in at the rc2 commit on silicon.** No bench K1 was on USB. The last silicon proof is on B489 at `bab7d528` / `2aa7422a` (4 Nov): line-in `[PCMCAN] rms` 110–118 on a 1 kHz tone, mic quiet level 1–13. `k1_fe_bench_b489` at rc2 has not been flashed.
- **Web flasher on a real K1 in ≤ 3 clicks.** Not possible until a Gx board is registered (deliverable 4 above).
- **Everything Gx-specific needs a Gx board (G5).** That covers CC ADC accuracy through the 100 kΩ resistors, the LED current model and 400 mA board reserve, eFuse trips at both POWER_PERMIT thresholds, GPIO45/46 strap levels, jack polarity on GPIO42, the heartbeat on GPIO8, the PCM1808 clocks and mic on the Gx pins, and the Gx line-in trim (the release still carries −24.08 dB). Full list in `FE-BRINGUP.md`.
- **External ADC on the Gx test header.** There is no capture driver; it stays in shutdown.
- **Whether the Gx pin map still matches the newest board files.** The firmware map is frozen against `K1-FE-Gx-Final` (PCB source `99452e42…`, 8 Nov). Later Gx files exist in `~/Downloads` (`K1-FE-Gx-Repaired.epro2` 8 Nov 23:37, `K1-FE-Gx-Rear-Artwork-R2.epro2` 9 Nov 03:37). The repair package says its artwork changes do not alter the net contract; I did not re-check those files' nets.

## Findings for the Operations Manager
1. **The board may be moving off the ESP32-S3.** Captain-led work on 9–10 Nov (`~/Downloads/K1-FE-S31-*`, `~/Workspace_Management/Software/K1-FE-S31-G03-routing-work`) builds the FE board around a **Waveshare ESP32-S31-Zero** module ("One S31 runs K1"). COURSE frozen decision 1 says FE = single ESP32-S3, and decision 2 says FE firmware = the S3 build. No K1 firmware exists for the S31. If S31 becomes the FE board, this lane needs a chip port, not a pin map, and G5's firmware readiness changes. Not started; it needs the course changed first.
2. **BLE-MIDI is still not in `k1_fe`** (rc1 finding 1, unchanged). COURSE decision 3 requires BLE-MIDI control; Wi-Fi is banned.
3. **Customer firmware updates are impossible as built.** The web flasher refuses every unregistered MAC, and now `k1_fe` has no registered board at all. G5 is fine (register each board). Before G7 the policy must let a customer's unregistered K1 update itself (rc1 finding 2).
4. **Merge hazard.** `wip/rpl-pins-20261110` (`2a620f7e`, Captain's Main RPL rewire) moves `K1_MAIN_RPL_PINMAP_V1` LED pins to 2/3/5/6. `k1_fe` inherits that macro. Merged as-is, it would put Gx LED data on I²C SDA (2), nav-right (3), CC2 sense (5) and LED OE B (6). Before that branch merges, Gx needs its own LED-pin block in `k1_fe_board.h`.
5. **rc2 is not "rc1 + board support only".** It includes everything on the lane since 3 Nov: the S3 repair and same-conditions work (4–5 Nov, other sessions), and the mode 32 and serial-input fixes (`e2e83e53`, `e28dd927`, 10 Nov). This session changed no AP/VP, effect or DSP code.
6. `stash@{0}` (the 9 Nov FW lead's set-aside `lane/k1-fx-battery` tree) is still in the stash. Its content appears to have been committed since as `c4c4f1b8` and `f4faf8a9` on `fix/k1-fe-gx-repair-20261108`. It is not mine to drop; check it against those commits before dropping it.

## Files touched
Commit `c44172fa`: the cherry-picked Gx set (`audio/k1_pcm1808_input.h`, `serial/serial_cmd_handlers.cpp`, `system/constants.h`, `system/k1_fe_board.cpp`, `system/k1_fe_board.h`, `system/k1_fe_gx_power_policy.h`, `visual/k1_fe_gx_led_power.h`, `visual/led_utilities.h`, `platformio.ini`, `tests/fixtures/k1_fe_gx_native_pin_map.json`, `tests/k1_fe_gx_board_host.cpp`, `tests/k1_fe_gx_output_host.cpp`, `tests/k1_fe_gx_power_host.cpp`, `tests/test_k1_fe_gx_contract.py`); conflict resolution `tools/esp_emulator/k1_lightshow_acceptance.json`; my edit `scripts/platformio/k1_device_identities.json`. Commit `545f00e4`: `docs/handover/FE-BRINGUP.md`. Docs commit: this receipt and `docs/forensics/runtime-evidence/20261110-fe-rc2/` (build logs, `release_sha256.txt`, `shipping_sections_pre_vs_rc2.txt`, `tag.txt`, `webflash_make_manifest.txt`). `device-build-registry.md` is unchanged because nothing was flashed. Left untouched: another lane's untracked `docs/plans/MODERNES-CPP-EXECUTION-PLAN.md`.

## Needs Captain
1. **Plug the bench K1 B489 into the Mac by USB**, with its 4 Nov wiring unchanged (mics DATA13/CLK14, PCM1808 LRCK9/DATA10/BCLK11, MacBook headphone output into the PCM1808 jack). The next FW session flashes `k1_fe_bench_b489` at rc2 and captures mic and line-in itself. Today only the K1-S3 unit was on USB.
2. **Which chip the FE ships on (ESP32-S3 Gx, or ESP32-S31).** See finding 1. It decides whether this lane ports the firmware.

## Ship path (what "shipped" means for this firmware)
1. **Already in source:** `fe-1.0.0-rc2` on `lane/k1-fe-release` (`545f00e4`, local tag), targeting K1-FE-Gx. Not on any silicon.
2. **Remaining:**
   - (a) Bench mic and line-in capture at rc2 on B489, once it is plugged in (FW lead).
   - (b) Board decision, Gx or S31 (Captain, through the Operations Manager).
   - (c) BLE-MIDI decision and the customer update policy (Operations Manager).
   - (d) G5: register each Gx board's MAC (move `k1_fe` from `blocked_envs` to that board), flash rc2, run the three checks in `FE-BRINGUP.md`, set the Gx line-in trim, generate the web-flasher bundle and flash one board from it in ≤ 3 clicks (FW lead with the HW/Build leads).
   - (e) Merge to main on host gates and push branch and tags (Operations Manager's call).
3. **Who acts:** the Captain only for the USB plug-in and the chip decision; everything else is agent work.
4. **Shipped =** a Gx board running a tagged `fe-1.0.0` (no `-rc`) whose `:build` reports that tag, with all three `FE-BRINGUP.md` checks passing and recorded in the device registry.

---

# K1-FE-SHOW fixes (candidate `a6bad318`, 10 Nov 2026 16:18–18:02 AWST)

Written late, on 10 Nov at 23:45 AWST, by the next FW lead session: the session that made `a6bad318` ended on a network error before it wrote this section. Everything below was re-read from the commit, the evidence files and the run folders tonight. Nothing here was re-run except where the round 2 section says so.

**What it is.** One commit, `a6bad31853b8c3a2535290e40ea36852dc4d4c05`, on `fe/k1-fe-show-fixes`, parent `8b202f46`, 44 files. It answers change requests revision 2 (`_scratch/k1-fe-show-m1_20261109/CHANGE-REQUESTS-FW-LEAD.md`), every item except priority 3.

| Change request | What the commit does |
|---|---|
| Receiver isolation | Every received byte goes through one gatekeeper (`audio/k1_prsm_rx`). Once show data is seen, single-key shortcuts and typed `:` commands stay off until the exact line `:prsm_exit` arrives after 200 ms of silence. A command line hit by show data, too long, or left unfinished for 5 s is thrown away. Frames cut short on the wire are dropped. A second frame format (v2) adds a length and a checksum. |
| Command list matches side effects | 36 rows corrected so that "this command saves to flash" is true for every row (`set_mode` saves). The safety list used by the bench tools is regenerated from the table. Audit: `docs/forensics/runtime-evidence/20261110-fe-show-fixes/serial-cmd-persist-audit.md`. |
| Prepared-source isolation (modes 32 and 18) | During a show the live microphone can no longer move the picture: its peak, its colour information, the room-silence dimming and the automatic colour drift are all kept out. |
| Deterministic colour start | The colour drift is parked at its rest value for the whole show and put back afterwards. |
| Seek | A jump in the stream starts a new "epoch": effect state and trails are cleared. Repeated frames are dropped. Declared settling time after a seek: 5.0 s (measured: 1.3 s). |
| Applied-state observation | New read-only command `:authored_status`. The LED capture names the show frame each captured frame used, and can record both edges. |
| Main RPL bench build | New build `k1_main_rpl_show_bench`, allowed on unit `9087A500` only, with that unit's 10 Nov wiring (LED data on GPIO 2/3 and 5/6) and two-edge capture. The shared pin map that `k1_fe` inherits is unchanged. |
| Emulator | The stream-replay adapter is now part of the normal emulator tooling. |

**Checks (all on `a6bad318`).**

| Check | Result | Where |
|---|---|---|
| Emulator gates G1–G4, FW lead's own runs | exit 0 on all three (FE mode 32, Main RPL mode 32, Main RPL mode 18) | `_scratch/k1-fe-show-m2_20261110/m2-emu/runs/fwlead-a6bad318-{fe-m32,rpl-m32,rpl-m18}-*/gates.json` |
| Same gates, K1-FE-SHOW lead's judging | exit 0 on all three | `_scratch/k1-fe-show-m2_20261110/fw-candidates/a6bad318/exits.txt` |
| The firmware's own receiver under packet loss | 913,580 loss cases on the M2 stream: 0 shortcuts, 0 commands, 0 damaged frames applied | `docs/forensics/runtime-evidence/20261110-fe-show-fixes/receiver-host-run.txt` |
| Live picture unchanged | modes 32 and 18, both edges, identical to `8b202f46`; the lead's 22-case run also identical | `20261110-fe-show-fixes/live-regression.txt`; `fw-candidates/a6bad318/live-regression/` |
| Same show after different prior room sound | identical from the first show frame, modes 32 and 18 | `20261110-fe-show-fixes/prior-live-state.txt` |
| Colour still follows the show's energy | mode 32 edge A hue spans 58.6°, tracks position (r = 0.91); measured on the working tree just before the commit | `20261110-fe-show-fixes/colour-diagnosis.txt` |
| Bench, by the K1-FE-SHOW lead | flashed to the Main RPL at 20:58; isolation and seek worked; two defects found (round 2 below) | `_scratch/k1-fe-show-m2_20261110/HANDOVER-K1-FE-SHOW-2026-11-10-S2.md` §6 |

**Builds retained** (`_scratch/fe-show-fixes-20261110/images/a6bad318/`, hashes in `20261110-fe-show-fixes/images-sha256.txt`): `k1_main_rpl_show_bench` `98ff5ff0…ee92`, `k1_main_rpl_im69d` `c28fa291…6f30`, `k1_fe` `6e8d1a29…0219`, `k1_hardware` `5e2eca36…a131`, `k1_fe_bench_b489` `9ac0367e…1dc0`. Recovery build of the image that was on the Main RPL before (`2a620f7e`): `8f96946e…4525`. The K1-FE-SHOW lead later took a full read-back of the board itself, which is the better recovery image (registry row).

**Could not be proven for `a6bad318`:** the previous session's own commit-gate output was not saved to a file, so the only record of it is the commit message. I did not re-run the gate on `a6bad318`; the round 2 gate below ran on its child.

# K1-FE-SHOW fixes, round 2 (R3-1 and R3-2; 10 Nov 2026 22:35–23:50 AWST)

## What happened, in plain English
- **A show no longer restarts when the computer stalls for a moment.** On the bench, a busy Mac held back the stream for 83 to 233 ms. The K1 gave the picture back to the microphone after 50 ms, then restarted the show when the stream returned. Now it holds the last show frame for up to 1 second, keeps the microphone out, and carries on in the same show when the stream returns.
- **Prepared shows now reach full brightness.** Mode 18 was almost black by construction: at full show level its brightest pixel reached only 6 to 12 % of full scale. Both modes also flipped to a colour that is not in the palette at low levels. Both are fixed for prepared shows only.
- **The live (microphone) picture is unchanged**: identical in all 22 emulator cases and in modes 32 and 18 on both edges.
- **Tested on the Mac and in the emulator only.** Nothing was flashed. No device was opened.
- **The picture:** `docs/forensics/runtime-evidence/20261110-fe-show-fixes-r3/r3-results.png` (on disk, not in git: the commit hook refuses images).

## The commit
`245ed510e30417933c97352abaa767d15b1a2d46` on `fe/k1-fe-show-fixes`, parent `a6bad318`, 12 files, +294 −26. Built without switching the shared checkout (it stays on `mcpp/next-phase-fixes`): private index, tested on a `git archive` export, then fetched into the branch. A trial merge with `mcpp/next-phase-fixes` @ `cfaad9dd` has no conflicts.

Its commit message points at `RECEIPT-FE-FW-2026-11-11.md`. That is my error: I expected the session to run past midnight. **This file is the receipt.**

## R3-1: frames lost on the way
What changed (`audio/k1_authored_source.*`):
1. No frame for more than 50 ms: the K1 holds the last show frame and keeps the microphone out, for up to `K1_AUTHORED_HOLD_MS` = 1000 ms. Only then does the microphone get the picture back. 1000 ms is four times the longest stall measured on the bench (233 ms).
2. A frame continues the same show when its sequence number moved forward by no more than 1 second of frames and its show time moved by the matching amount. The old limit was 3 frames.
3. Still a new start (state cleared): a backward step; a show time that does not match the sequence step (more than 50 ms off); a change of stream rate; a forward step longer than 1 second; a stream that returns after the 1 second hold ran out.
4. `:prsm_exit` now ends the show at once instead of waiting out the hold.
5. `:authored_status` has one new field at the END of its line, `holds=` (times the stream went quiet for more than 50 ms). Existing fields are unchanged. The emulator log has two new lines, `EMU_PREP` and `EMU_PREP_END`.

Measured in the emulator on `245ed510` (M1 stream 100–125 s, runs of 4, 12 and 60 frames removed, both edges):

| | Mode 32 | Mode 18 |
|---|---|---|
| Epoch at the end of the run | 1 (was a restart at every loss longer than 3 frames) | 1 |
| Lost frames counted | 76 of 76 | 76 of 76 |
| Identical to continuous play again after the 4-frame loss | 0.71 s after the stream returns | 1.09 s |
| … after the 12-frame loss | 0.91 s | 1.51 s |
| … after the 60-frame loss (508 ms quiet) | 1.01 s | 1.09 s |
| Same result with music or with silence on the microphone | yes, every captured frame | not run for mode 18 |

Seek run (mode 32): the epoch rose exactly at the backward jump, at the jump whose show time did not match, and at the 2-second forward jump (1 → 2 → 3 → 4).

Things the K1-FE-SHOW lead should know before the bench:
- **"Equal to continuous play" is true 0.7 to 1.5 s after the stream returns, not at once.** During the loss the effect keeps drawing from the held frame, and its trails need that long to forget it. The declared limit is the same 5.0 s as for seeks.
- **A forward seek shorter than 1 second, sent with truthful sequence numbers, now looks like lost frames**: the show continues without clearing. Seeks of 1 second or more, and every backward seek, still clear.
- **The 50 ms figure in the Spine note `docs/K1_SOURCE_ARBITRATION.md` (status "Proposed") is now out of date.** It lives outside this repo; I did not edit it.
- **End of a stream with no `:prsm_exit`:** the last frame is held for 1 second before the microphone returns (was 50 ms).

## R3-2: prepared-show level
**Diagnosis.** During a show there is no live colour information, so modes 32 and 18 take their colour from a fallback: the chosen palette, sampled at the position of the CHROMA knob (0.0 by default), multiplied by the show's level. The boot palette (Naberius Gold) starts almost black at that position: (2, 0, 20) out of 255. So:
- Mode 18 always sampled that one near-black colour. However hard the show drove it, the brightest pixel stayed at 6 % (edge A) to 12 % (edge B) of full scale.
- Mode 32 walks a short way up the palette with level, so it was less affected.
- Below a level of about 0.26 (mode 18) and about 0.11 (mode 32) the result fell under a "this palette colour is black" floor and the effect switched to a plain red that is not in the palette (measured: red channel only at levels 0.1 and 0.2), brighter than the palette colour above it. The level-to-brightness curve went up, then collapsed (left-hand lines in the picture).
- Before `a6bad318` the live microphone hid this: its level and colour were mixed in.

**Fix, prepared shows only** (`visual/k1_prepared_level.h`, one call in each of the two effects): the palette supplies the hue, the show supplies the level. The palette colour is scaled so that its strongest channel equals the show's level. Live rendering does not use it. `light_mode_waveform_tempo.cpp` is a frozen file; the test that guards it now admits exactly these two edits, under the same "All fixes now" approval as the round 1 edits.

**The mapping: show level (Prim8 pressure) to brightest pixel**, 16-bit output, steady level held 4 s, microphone silent, Main RPL build. Full table with edge means and lit-pixel counts: `20261110-fe-show-fixes-r3/r32-mapping-245ed510.md`; before the fix: `r32-mapping-a6bad318-level-code.md`.

| Level | Mode 32 edge A | Mode 32 edge B | Mode 18 edge A | Mode 18 edge B | Mode 18 edge A before |
|---|---|---|---|---|---|
| 0.00 | 0 | 0 | 0 | 0 | 0 |
| 0.05 | 4,124 | 4,264 | 0 (below this mode's presence floor) | 0 | 0 |
| 0.10 | 5,995 | 6,387 | 9,754 | 10,611 | 9,912 (red) |
| 0.20 | 15,119 | 16,971 | 17,772 | 21,093 | 19,487 (red) |
| 0.30 | 21,108 | 25,331 | 24,052 | 31,450 | 1,884 |
| 0.50 | 38,006 | 52,340 | 31,395 | 51,779 | 2,460 |
| 0.70 | 35,816 | 56,658 | 31,788 | 62,057 | 2,491 |
| 0.90 | 27,989 | 55,418 | 42,073 | 65,534 | 3,297 |
| 1.00 | 45,323 | 65,534 | 50,633 | 65,534 | 3,970 |

Reading it: mode 18 now rises with level all the way. Mode 32's zig-zag is the dot sitting between two pixels at a steady level; its edge mean rises smoothly to level 0.7 (table in the file). Edge B shows the palette's blue cleanly and reaches full scale (at level 0.8 its brightest pixel is red 4,830 / green 0 / blue 65,534). Edge A's output stage turns a strong blue paler and warmer and tops out at 77 % (same pixel: red 33,846 / green 10,516 / blue 29,376). Edge A did the same before the fix at its much lower level. That stage is after the effect and is not touched by this commit; I measured it and did not find its cause.

**The same shows, before and after** (whole-edge mean, 16-bit; `level-comparison.txt`):

| Show, mode | Old build with room music mixed in (`8b202f46`) | Isolated (`a6bad318`) | Now (`245ed510`) |
|---|---|---|---|
| M1 stream, mode 32, edge A | 3,075 | 2,094 | 2,989 |
| M2 stream, mode 32, edge A | 3,011 | 1,316 | 2,587 |
| M1 stream, mode 18, edge A | 590 | 163 | 1,376 |
| M2 stream, mode 18, edge A | 709 | 309 | 1,959 |

- Mode 32 is back to within 3 % (M1) and 14 % (M2) of the old level.
- **Mode 18 is now 2.3 to 2.8 times brighter than the old build ever was.** That is what "level 0.8 means 80 % brightness" gives. If the Captain finds it too bright at A18, lower the pressure in the show's mapping profile (host side); the firmware does not need to change.
- **Colour is unchanged in kind.** A prepared show still only uses the first quarter of the palette (blue to violet on Naberius Gold; mode 18 one palette position). The gold is never reached. That is change request priority 3 and stays the Captain's decision.

## Checks on `245ed510` (clean `git archive`, each run once unless stated)

| Check | Result | Evidence |
|---|---|---|
| Commit gate: `pytest tests/` | **2,074 passed, 9 skipped.** My first run failed 4 tests: I ran it before any build, so the export had no build libraries. Those 4 passed once the libraries were there; the full run was then repeated once. | `20261110-fe-show-fixes-r3/commit-gate.txt` |
| Commit gate: `pio run -e k1_hardware` | SUCCESS | same |
| Builds `k1_fe`, `k1_main_rpl_im69d`, `k1_main_rpl_show_bench` | SUCCESS, the usual two compiler warnings, stamped `245ed510` | same |
| `gates.py --profile fe --mode 32` | exit 0, G1–G4 PASS | `_scratch/k1-fe-show-m2_20261110/m2-emu/runs/fwlead-245ed510-fe-m32-20261110T225925/gates.json` |
| `gates.py --profile scenario --mode 32` | exit 0, G1–G4 PASS | `…/fwlead-245ed510-scenario-m32-20261110T231032/gates.json` |
| `gates.py --profile scenario --mode 18` | exit 0, G1–G4 PASS | `…/fwlead-245ed510-scenario-m18-20261110T231946/gates.json` |
| R3-1 and R3-2 emulator checks | exit 0, 8 of 8 | `20261110-fe-show-fixes-r3/r3-245ed510.json`, tool `tools/r3_emu.py` |
| The firmware's own receiver, M2 stream, every loss case | 913,580 cases: 0 shortcuts, 0 commands, 0 damaged frames | `20261110-fe-show-fixes-r3/receiver-m2-stream.txt` |
| New host test for lost frames, seeks and the hold | PASS (inside `tests/test_k1_prsm_rx_native.py` and `tests/test_authored_ingress_native.py`) | `tests/k1_prsm_rx_host.cpp` section 11 |
| Live picture, emulator default suite, against the accepted `a6bad318` run | **0 differing frames in 22 of 22 cases** | `20261110-fe-show-fixes-r3/live-default-compare.txt` |
| Live picture, modes 32 and 18, both edges | same hashes as `8b202f46` and `a6bad318` | `20261110-fe-show-fixes-r3/live-regression.txt` |
| Scope against `SHARED-TREE-OWNERSHIP-2026-11-10.md` | No Modernes-owned file touched. `serial_menu.cpp`: three lines in `cmd_authored_status` and the exit case. | `git show --stat 245ed510` |

The emulator default suite's own verdict is "SOFTWARE INCOMPLETE" (its checks SW07 and SW11 fail). The accepted `a6bad318` run has the same two failures; they come from running in an export without git. The list of verdicts is identical between the two runs.

**Candidate images** (`_scratch/fe-show-fixes-20261110/images/245ed510/`, all hashes in `20261110-fe-show-fixes-r3/images-sha256.txt`):

| Build | Bytes | SHA-256 of `firmware.bin` |
|---|---|---|
| `k1_main_rpl_show_bench` (LED pins 2/3/5/6 read from the compiled file) | 737,120 | `cf78708b4a98eded17acc7c297bf2522bac2ce8084586fab9d4966ebeb94f2e3` |
| `k1_main_rpl_im69d` | 733,168 | `1f5e537ce8f64428bc0b28b96b132f3fb8c1ae828031f7d1cf5ad08af59ff17e` |
| `k1_fe` (LED pins 15/16/17/18) | 768,480 | `d21e6ed37ceeed753276e166a5ffc05e05b1a3ba47c15b99488cbb08485a95dc` |
| `k1_hardware` | 723,600 | `c7e20695d546516fbbe38a10411783a38b55691445f8a9e7ce6bce800c81dc75` |

A rebuild stamps a new build time, so a fresh build of the same commit has a different hash.

## Could NOT be proven (named, not claimed)
- **Anything on the real K1.** The bench acceptance for R3-1 (`:authored_status` epoch rising by exactly 1 per run over at least 5 runs on a loaded Mac) is the K1-FE-SHOW lead's to run.
- **Real USB loss.** The emulator delivers whole frames at fixed times. Frames cut in half are covered only by the host receiver test.
- **How the brighter mode 18 looks, and what it draws from the supply.** The Main RPL build installs no LED current limit. Mode 18 lights 40 to 90 of each edge's 160 pixels, now much brighter. Watch the supply on the first bench run.
- **The Lane B oracle** against this commit (the K1-FE-SHOW lead owns that snapshot).
- **Modes other than 32 and 18.** The mode 32 variants (`light_mode_wfhyb_k1_variants.cpp`) did not get the level rule; they are not admitted for prepared shows.
- **Builds that carry `K1_FALLBACK_HELD_U_V1`** (bench colour-fix builds only, not the shipping ones) were not run.

## Findings for the Operations Manager and the K1-FE-SHOW lead
1. The same "palette is nearly black at the knob position, then a red that is not in the palette" behaviour exists in the LIVE picture whenever the room's colour information is thin. I did not touch it: live must stay identical. It is a shipping-look question for the Captain.
2. Receipt finding 4 of this morning (merge hazard from `wip/rpl-pins-20261110`) still stands.
3. Findings 1 to 3 and 5 to 6 of this morning's receipt are unchanged.

## Files touched this session
Commit `245ed510`: `audio/k1_authored_source.cpp`, `audio/k1_authored_source.h`, `audio/k1_emu_fixture.cpp`, `effects/light_mode_waveform_hybrid_k1.cpp`, `effects/light_mode_waveform_tempo.cpp`, `serial/serial_menu.cpp`, `visual/k1_prepared_level.h` (new) (all under `SPECTRASYNQ_K1_FIRMWARE/`); `scripts/regression-harness/k1_authored_ingress_probe.cpp`; `tests/k1_prsm_rx_host.cpp`, `tests/test_authored_ingress_native.py`, `tests/test_lever2_no_effect_retune_static.py`; `tools/esp_emulator/README.md`.

Docs commit on top of it (same branch): this receipt; `docs/forensics/runtime-evidence/20261110-fe-show-fixes/` (round 1 evidence that was left uncommitted); `docs/forensics/runtime-evidence/20261110-fe-show-fixes-r3/` (round 2, without the picture); `docs/hardware/device-build-registry.md` (the Main RPL row written by the K1-FE-SHOW lead and the previous FW session's changelog line).

On disk only: `_scratch/fe-show-fixes-20261110/images/245ed510/`; gate run folders under `_scratch/k1-fe-show-m2_20261110/m2-emu/runs/fwlead-245ed510-*`; `r3-results.png`.

**Left alone:** the shared checkout stays on `mcpp/next-phase-fixes` with nothing staged. In it, this receipt and the registry show as modified and the two evidence folders as untracked: they are the working copies of what the docs commit holds. Whoever next switches that checkout to `fe/k1-fe-show-fixes` will be told the untracked copies are in the way; they are identical to the committed ones and can be removed then. Not touched: every stash, `mcpp/next-phase-fixes`, `lane/k1-fe-release` (no merge), `~/K1_Launch_Planning`, the Spine repo. Nothing pushed.

## Needs Captain
Nothing new from this session. The two items in "Needs Captain" above (plug in the bench K1 B489; which chip the FE ships on) still stand.

## Ship path — prepared shows on the K1 FE
1. **In source now:** `fe/k1-fe-show-fixes` @ `245ed510` plus the docs commit. On silicon: only the older `a6bad318` bench build, on the Main RPL.
2. **Remaining:**
   - (a) K1-FE-SHOW lead: judge `245ed510` (prompt below), flash `k1_main_rpl_show_bench` to the Main RPL under the Captain's standing go, re-run the bench, update the registry.
   - (b) FW lead: merge `fe/k1-fe-show-fixes` into `lane/k1-fe-release` once the K1-FE-SHOW lead accepts it. The Modernes branch merges cleanly with it today.
   - (c) Captain: loud guard / AGC decision (R3-3), then A06 and A18 with the K1-FE-SHOW lead.
   - (d) FW lead and Operations Manager: tagged FE release containing these fixes; G5 steps as in the ship path above.
3. **Who acts:** agents for (a), (b), (d); the Captain only for (c) and the physical steps already listed.
4. **Shipped =** a tagged `fe-1.0.0` containing these fixes on a K1-FE-Gx board, passing every applicable M1 requirement on that one image, recorded in the device registry.

## Prompt for the K1-FE-SHOW lead (paste as is)
> Judge FW-lead candidate `245ed510e30417933c97352abaa767d15b1a2d46` (branch `fe/k1-fe-show-fixes`, parent `a6bad318`) in `~/SpectraSynq_K1_Firmware`. Read `docs/handover/RECEIPT-FE-FW-2026-11-10.md`, section "K1-FE-SHOW fixes, round 2", from `git archive` of the branch tip. Work only from `git archive 245ed510` exports; do not switch the shared checkout.
> 1. Scope: `/usr/bin/git show --stat 245ed510` against `_scratch/k1-fe-show-m2_20261110/fw-candidates/SHARED-TREE-OWNERSHIP-2026-11-10.md`.
> 2. `gates.py` ×3 on one export, one after another (fe/32, scenario/32, scenario/18, M2 stream and twin): expect exit 0 each. My runs: `m2-emu/runs/fwlead-245ed510-*`.
> 3. R3-1 and R3-2: `<venv python> docs/forensics/runtime-evidence/20261110-fe-show-fixes-r3/tools/r3_emu.py run <export> <new out dir>`: expect "failing checks: 0", epoch 1 across lost runs of 4, 12 and 60 frames, and the level table.
> 4. Live regression: `run.py --scenario tools/esp_emulator/s3_music_regression.json --suite default --profile scenario --output <new dir>`, then `tools/live_compare.py <a6bad318 run2 dir> <new dir> <export>`: expect 0 differing in 22 cases.
> 5. Receiver: `tests/test_k1_prsm_rx_native.py` and `tests/k1_prsm_rx_host.cpp <M2 stream>`: expect 0 / 0 / 0.
> 6. Commit gate and the three builds on the export. Run a build before pytest, or four tests fail for missing libraries.
> 7. If accepted: flash `k1_main_rpl_show_bench` @ `245ed510` to the Main RPL `9087A500` (your §10 method), then bench. Expect `:authored_status` epoch +1 per run on a loaded Mac, `holds=` counting the stalls, mode 18 clearly brighter than before (watch the supply: no current limit in this build), and `:prsm_exit` returning the live picture at once. `:authored_status` has one new field at the end of the line.
> Known and intended: after lost frames the picture matches continuous play 0.7 to 1.5 s later, not instantly; a forward seek shorter than 1 s with truthful sequence numbers does not clear the effect state; a stream that ends without `:prsm_exit` holds its last frame for 1 s.

---
| Date | Author | Change |
|------|--------|--------|
| 2026-11-10 | agent:claude (FW lead) | Created. |
| 2026-11-10 | agent:claude (FW lead, session 22:35) | Added "K1-FE-SHOW fixes" (the section owed for `a6bad318`) and "K1-FE-SHOW fixes, round 2" (`245ed510`: R3-1, R3-2), with checks, mapping, ship path and the judging prompt. |
