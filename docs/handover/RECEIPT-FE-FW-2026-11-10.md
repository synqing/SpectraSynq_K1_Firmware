---
abstract: "FW lead receipt, 10 Nov 2026 AWST. The FE release now targets the board the Captain moved to, K1-FE-Gx (5 V USB-C, no STUSB4500): its pin map is on the release lane, tagged fe-1.0.0-rc2, built clean, shipping Main RPL build proven byte-unchanged, bring-up sheet rewritten for Gx. Nothing flashed: no FE board exists and no bench K1 was plugged in (only the parked lane's K1-S3). Web-flasher bundle for rc2 is held by the flasher's own safety rule until a Gx board is registered at G5."
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
| Date | Author | Change |
|------|--------|--------|
| 2026-11-10 | agent:claude (FW lead) | Created. |
