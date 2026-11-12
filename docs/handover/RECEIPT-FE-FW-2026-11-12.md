---
abstract: "FW lead receipt, 12 Nov 2026 07:47–08:20 AWST. The release lane now holds the accepted prepared-show fixes (fast-forward to c949151c). The Captain's FE board is K1-FE-S31-G01 (ESP32-S31), not the S3 the course still names; a compile-only probe shows the FE firmware builds and links for the S31 with two small FastLED patches and one mic guard lifted, and that BLE-MIDI on the S31 must use arduino-esp32 4.0's own BLE library. Nothing flashed: the only board on USB was the K1-FE-SHOW lead's Main RPL."
---

# Receipt — FW lead, K1 FE firmware (12 Nov 2026, AWST)

Charter: `~/K1_Launch_Planning/00-Governance/team/LEAD-FW-FE-RELEASE.md`. Read first: `COURSE-2026-11-02.md`, `team/OPERATIONS.md`, the charter, `RECEIPT-FE-FW-2026-11-10.md`, the K1-FE-SHOW handovers S3–S6 (`docs/handover/K1-FE-SHOW/` on `fe/k1-afe2-s4`), `K1-FE-S31W-Rebase/{README,DIRECTIVES,EVIDENCE}.md`, `K1-FE-Board/RECEIPT-BUILD-G5.md`, `reports/DAILY-2026-11-11.md`, the Compliance QC sheet and cert plan.

## What happened, in plain English
- **The FE release lane now has the prepared-show fixes.** The K1-FE-SHOW lead judged them on 11 Nov (all checks passed, and on the real Main RPL a show survived 28 dropped frames without restarting). I moved `lane/k1-fe-release` forward to them. No code changed in that step.
- **The FE board has changed chip, and the course has not caught up.** On 10 Nov at 17:00 the Captain ruled "G01 is the only board we are concerned about" (`K1-FE-S31W-Rebase/DIRECTIVES.md`, D2). K1-FE-S31-G01 carries an ESP32-S31 module. The course still says ESP32-S3, and the 11 Nov daily report still lists the chip as undecided.
- **The FE firmware can be built for the S31.** I tried it in a scratch copy. With three missing lines added to the LED library (FastLED 3.10.3) and one deliberate microphone safety check switched off, the whole FE firmware compiles and links for the S31. It uses about the same memory as on the S3 (RAM 45.7 %; the S3 `k1_fe` at rc2 was 45.4 %, an older commit) and the same LED driver.
- **What still stands in the way of an S31 firmware:** the LED library needs that patch (its newest version does not know the S31 at all); the microphone check can only be lifted after the mic is proven on a real S31; the Bluetooth library the K1 uses today does not build for the S31, but the S31's own Bluetooth library does (a BLE-MIDI test build passed); the S31 needs a pre-release toolchain; the web flasher needs a newer flashing library to talk to an S31.
- **BLE-MIDI:** a phone-facing BLE-MIDI receiver for the K1 was already written on 7 Sep and never committed (it sits in `stash@{3}`). It is written for the S3's Bluetooth library, so on the S31 it needs rewriting against the new library; the decoder and the control map carry over.
- **Nothing ran on hardware.** The only board on USB was the Main RPL (`B4:3A:45:A5:87:90`), which the K1-FE-SHOW lead is using; I identified it from the USB list without opening its port. The bench K1 B489 was not plugged in. No S31 exists on the bench.

## Done this session
| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Merge the accepted show fixes into the release lane (ship path (b) of the 10 Nov receipt) | `lane/k1-fe-release` 8b202f46 → **c949151c**, fast-forward, local ref only | K1-FE-SHOW handover S4 §0 ("rc3 judged": pytest 2,091/0, gates ×3, live regression 22/22, receiver 913,580 losses with 0 applied; bench epoch 1 → 2 under load); `git log lane/k1-fe-release` |
| 2 | S31 compile probe | builds and links with patches; four blockers named | `docs/forensics/runtime-evidence/20261112-s31-port-probe/README.md` and the files beside it |
| 3 | BLE on the S31 | NimBLE-Arduino 2.5.2 fails; arduino-esp32 4.0 `BLE` library builds a BLE-MIDI peripheral | same folder: `errors-6-ble.txt`, `ble-peripheral-s31-compile.txt` |
| 4 | Web flasher on the S31 | bundled esptool-js 0.6.1 has no S31; 0.7.1 has `esp32s31` | same folder: `webflash-esptool-js.txt` |

The S31 probe image (not a product image; Gx LED pins, mic guard off): `firmware.bin` 834,016 bytes, sha256 `eef6ceb5dcb4b65752466dc5cb6173e0800b0ed517a6d06395c95d53d0e11903`, kept at `_scratch/20261112-fw-lead-s31-port-probe/images/k1_fe_s31_probe/`.

## My method error this session (recovered)
Adding a third probe env to the scratch `platformio.ini` made PlatformIO clear every build folder in that copy, including the first S31 image (sha256 `826e6998…`). I rebuilt it; sizes are identical, the hash differs only by build time. The trap is now written in the probe README.

## Could NOT be proven (named, not claimed)
- Anything on an S31 at run time: boot, mic, line-in, LEDs, Core 0 timing, BLE pairing, USB serial, web flashing.
- Mic and line-in at `fe-1.0.0-rc2` on B489 (charter "Done when" items) — B489 was not plugged in. These matter only if the FE stays on the S3.
- The S31-G01 pin map in firmware: not written. The board lane changed pin order twice on 11 Nov (`S31-GPIO.csv`, sha256 `7a3918ac…074f`, modified 11 Nov 04:48).

## Findings for the Operations Manager
1. **Update COURSE decisions 1 and 2 to the Captain's ruling** (S31-G01, 10 Nov 17:00). Until then this lane cannot start the real S31 port without contradicting the course, and the 11 Nov daily report wrongly shows the chip as open.
2. **The S31 port plan, in order** (FW lead, once finding 1 is recorded): (a) new env `k1_fe_s31` on pioarduino `61.04.00-RC1` with FastLED 3.10.3 plus the three-line patch; (b) S31-G01 board profile from the frozen pin map; (c) BLE-MIDI peripheral on the arduino-esp32 4.0 `BLE` library, reusing the decoder and `k1-ble-midi-map.json`; (d) web flasher to esptool-js 0.7.1; (e) on the first S31 board: mic slot/order re-proof, then lift the guard; line-in, LEDs, Core 0 timing, BLE pairing. The PlatformIO on this Mac (6.1.19) is too old for the S31 platform; the probe used 6.2.0 in a private venv.
3. **BLE-MIDI role: the FW lead recommends K1 as a BLE-MIDI peripheral** (a phone or Mac pairs to the K1). That is what the QC sheet step 9, the cert plan and the regulatory notes all describe, and it is the only role that works without a remote in the box. The existing K1 BLE code is the opposite role (K1 connects out to the K718 dial / decks). This unblocks Compliance QC step 9 and the "BLE active" FCC test once it is built.
4. 10 Nov receipt finding 3 (web flasher refuses unregistered boards, so customers cannot update) still stands.
5. 10 Nov finding 4 (merge hazard from `wip/rpl-pins-20261110`) is contained: the show lead's bench build carries the Main RPL rewire in its own flag and leaves the shared pin map alone. `wip/rpl-pins-20261110` must never be merged.
6. The K1-FE-SHOW lead plans to merge AFE2 (`fe/k1-afe2-s4`) into the release lane (its task T6). It now merges onto `c949151c`, which `fe/k1-afe2-s4` already contains.

## Files touched
- `lane/k1-fe-release` ref (fast-forward only).
- New: this receipt; `docs/forensics/runtime-evidence/20261112-s31-port-probe/` (README, error lists, build summary, probe diffs, FastLED patch lines, BLE compile test, web flasher check, platform hash). Committed on `lane/k1-fe-release` as a docs-only commit made without touching the shared checkout.
- Scratch only (EXPIRE): `_scratch/20261112-fw-lead-s31-port-probe/` (export, platform, private PlatformIO venv and package folder, logs, probe image).

**Left alone:** the shared checkout stays on `mcpp/next-phase-fixes`. In it, `RECEIPT-FE-FW-2026-11-10.md` and `device-build-registry.md` show as modified and the two 10 Nov evidence folders as untracked; I checked both files are byte-identical to the committed versions in `c949151c`. Not touched: every stash (including `stash@{0}` and `stash@{3}`), `mcpp/next-phase-fixes`, all `fe/k1-afe2*` and `lane/k1-fe-show*` branches, the Main RPL, `~/K1_Launch_Planning`, the S31 board folders. Nothing pushed.

## Needs Captain
1. **An ESP32-S31 board on the bench** (an S31-Zero module or Espressif's ESP32-S31-Function-CoreBoard-1, with the IM69D mic wired). Every S31 run-time check waits on it. The S31-Zero was out of stock at Waveshare on 11 Nov; buying one is a money action.

## Ship path (what "shipped" means for this firmware)
1. **Already in source:** `lane/k1-fe-release` @ `c949151c` (`fe-1.0.0-rc2` + prepared-show fixes), S3 only. On silicon: only bench builds on the Main RPL.
2. **Remaining:**
   - (a) Operations Manager: record S31-G01 in COURSE (finding 1) and the BLE role (finding 3).
   - (b) K1-FE-SHOW lead: merge AFE2 into the release lane (its T6).
   - (c) FW lead: S31 port steps 2(a)–(d) above, in source, with host gates and S31 builds.
   - (d) Captain: an S31 board on the bench.
   - (e) FW lead: S31 run-time proof on that board (step 2(e)), then `fe-1.0.0-rc3` for S31-G01; G5 bring-up sheet rewritten for S31-G01.
3. **Who acts:** the Captain only for (d); everything else is agent work.
4. **Shipped =** a K1-FE-S31-G01 board running a tagged `fe-1.0.0` whose `:build` reports that tag, with the bring-up checks passing and recorded in `docs/hardware/device-build-registry.md`.

## Prompt for the next FW lead session (paste as is)
> You are the FW lead (charter `~/K1_Launch_Planning/00-Governance/team/LEAD-FW-FE-RELEASE.md`). Read `docs/handover/RECEIPT-FE-FW-2026-11-12.md` on `lane/k1-fe-release` first, then `docs/forensics/runtime-evidence/20261112-s31-port-probe/README.md`. Work only in `git archive` exports and private-index commits; the shared checkout `~/SpectraSynq_K1_Firmware` belongs to other sessions — never checkout, stash, add or reset there.
> 1. Check COURSE for an S31 entry. If it is recorded: build `k1_fe_s31` on a new branch from `lane/k1-fe-release` (pioarduino `61.04.00-RC1`, PlatformIO ≥ 6.2 from a private venv, FastLED 3.10.3 + the three-line patch in `fastled-3.10.3-probe-patches.txt`, board profile from the S31-G01 pin map only if its owner has frozen it), keep the mic guard on, register the env in the upload guard's blocked list, and add a BLE-MIDI peripheral on the arduino-esp32 4.0 `BLE` library reusing `network/k1_ble_midi_decoder.*` and `k1_control_apply`. Gate: `pytest tests/` + `pio run -e k1_hardware` on an export; `k1_fe_s31` builds.
> 2. If COURSE still says S3: do not start the port; check USB (`ioreg -p IOUSB -l -w0`, no port open) for B489 `B4:3A:45:A5:89:B4` and, if present, flash `k1_fe_bench_b489` at `lane/k1-fe-release` and capture mic and line-in (10 Nov receipt, Needs Captain 1 wiring).
> 3. Never flash the Main RPL `B4:3A:45:A5:87:90` (K1-FE-SHOW lead's unit). Write `docs/handover/RECEIPT-FE-FW-<date>.md` and stop.

| Date | Author | Change |
|---|---|---|
| 2026-11-12 | agent:claude (FW lead) | Created. |
