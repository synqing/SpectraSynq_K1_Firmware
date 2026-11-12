---
abstract: "FW lead, 12 Nov 2026 AWST. Compile-only probe: can the shipping K1 FE firmware build for the ESP32-S31 (the chip on K1-FE-S31-G01, the Captain's board since 10 Nov 17:00)? Yes, with two small FastLED patches and one deliberate mic guard lifted. Nothing ran on an S31; no S31 exists on the bench."
---

# ESP32-S31 port probe (12 Nov 2026, AWST)

**Question.** Does the FE firmware (`k1_fe`) compile and link for the ESP32-S31, and what breaks?

**Source.** `git archive 8e8496e2` (`fe/k1-afe2-s4` tip: release lane + show fixes + AFE2 stages 1–4), exported to `_scratch/20261112-fw-lead-s31-port-probe/export/`. Nothing in the repo was changed for this probe; the probe envs exist only in that export (`probe-envs.diff`).

**Toolchain.** pioarduino platform `61.04.00-RC1` (pre-release) = arduino-esp32 `4.0.0-RC1` on ESP-IDF `6.1.0`, RISC-V GCC 15.2.0; board `esp32-s31-coreboard-1` (16 MB flash, OPI PSRAM). It needs PlatformIO Core ≥ 6.2.0; the Mac's `pio` is 6.1.19, so the probe used PlatformIO 6.2.0 in a private venv with its own package folder (`PLATFORMIO_CORE_DIR`), leaving `~/.platformio` untouched. Platform zip hash: `platform-sha256.txt`.

## Results

| Run | What was built | Result | File |
|---|---|---|---|
| 1 | `k1_fe` for S31, FastLED 3.10.3 (pinned today) | fails inside FastLED: 8 errors in its SPI LED-strip and audio-input code (headers moved in IDF 6.1). Every K1 file except the sketch compiled. The sketch stops at one deliberate K1 guard: the IM69D mic slot/order contract is frozen to ESP-IDF 5.4.1 (`audio/i2s_audio.h:91`). | `errors-3-k.txt` |
| 2 | same, newest FastLED (3.10.9) | worse: FastLED does not know the S31 ("Unknown ESP32 chip variant"), two more driver errors, and its colour-order type change breaks 8 K1 lines | `errors-4-fl.txt` |
| 3 | run 1 with the mic guard lifted (probe flag only) and FastLED 3.10.3 given three missing lines | **builds and links.** RAM 45.7 % (S3 `k1_fe` at rc2, an older commit: 45.4 %), flash 12.0 %. FastLED picks the same RMT5 LED driver the S3 uses. The mic's slot-number checks (`static_assert`) pass unchanged. | `build-patched-summary.txt`, `fastled-3.10.3-probe-patches.txt`, `probe-guard.diff` |
| 4 | run 1 plus the K1 BLE-MIDI code on NimBLE-Arduino 2.5.2 (the library the bench BLE builds use) | NimBLE-Arduino does **not** compile for the S31: its Bluetooth controller settings and OS port do not match IDF 6.1 | `errors-6-ble.txt` |
| 5 | minimal BLE-MIDI peripheral (MIDI service, write-without-response + notify) on arduino-esp32 4.0's own `BLE` library (IDF NimBLE host, enabled in the S31 build) | **builds** | `ble-peripheral-s31-compile.txt` |

## What this means for an S31 FE firmware
1. The K1 code itself is close to portable: no Xtensa assembly or S3-only peripheral calls in the FE build. The S31 has every peripheral the FE uses (PDM mic input with PDM-to-PCM on I2S0, RMT with DMA, the pulse counter used by the line-in clock check, BLE), read from its `soc_caps.h`.
2. FastLED is the main software risk. 3.10.3 works with three added lines; 3.10.9 does not know the chip. Either carry the patch (vendored copy or a pre-build patch) or wait for FastLED S31 support.
3. The mic guard stays until the IM69D slot/order contract is re-proven on S31 silicon. That needs an S31 board and a mic.
4. BLE-MIDI on the S31 must use arduino-esp32 4.0's `BLE` library, not NimBLE-Arduino. Its API is new (`BLE.h`), so the bench BLE code and the 7 Sep phone peripheral (`stash@{3}`, NimBLE-Arduino) do not carry over as-is; the decoder and control map do.
5. The S31 needs a pre-release framework (arduino-esp32 4.0.0-RC1) and PlatformIO 6.2. The S3 builds stay on 3.2.0, so the repo would build two framework versions side by side.
6. The web flasher bundles esptool-js 0.6.1, which has no S31 support; 0.7.1 (latest) does (`webflash-esptool-js.txt`).
7. The probe image still uses the Gx LED pins (15–18). The S31-G01 pin map (`K1-FE-S31-G03-routing-work/work/S31-GPIO.csv`) puts LED data on GPIO 22/23/24/25 and was still changing on 11 Nov (pin-order takeovers 6 and 7).

## Not proven (named, not claimed)
Anything at run time: boot, mic, line-in, LED output, timing on Core 0, BLE pairing, USB serial, web flasher. No S31 board or module exists on the bench (the S31-Zero was out of stock at Waveshare on 11 Nov, Build lead receipt).

## Re-run
```
S=_scratch/20261112-fw-lead-s31-port-probe   # venv/, platform/, pio-core/ live there
cd $S/export && SCONSFLAGS=-k PLATFORMIO_CORE_DIR=$S/pio-core $S/venv/bin/pio run -e k1_fe_s31_probe
```
Adding a new env to the export's `platformio.ini` makes PlatformIO clear every build folder in it; build the env you want last.

| Date | Author | Change |
|---|---|---|
| 2026-11-12 | agent:claude (FW lead) | Created. |
