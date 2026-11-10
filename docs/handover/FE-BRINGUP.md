---
abstract: "One-page G5 bring-up kit for the K1 Founders' Edition board K1-FE-Gx (5 V USB-C, no STUSB4500): how to flash release fe-1.0.0-rc2 (env k1_fe), the serial lines to expect in order, and the three pass/fail checks per board. Every expected line is read from source; none has yet been seen on a Gx board. For the HW and Build leads."
---

# K1 FE board (K1-FE-Gx) — G5 bring-up (firmware `fe-1.0.0-rc2`, env `k1_fe`)

Source: `system/k1_fe_board.*` (board support, Gx profile under `K1_FE_BOARD_GX`), `system/k1_fe_gx_power_policy.h` (USB-C source to LED budget), `visual/k1_fe_gx_led_power.h` (shared LED current limiter), `audio/k1_pcm1808_input.*` (line-in), `[env:k1_fe]` in `platformio.ini`. Board truth: `K1-FE-Gx-Final`, PCB source SHA-256 `99452e42…8c26b25`, uuid `03c9e50bdc6872e1`; frozen pin fixture `tests/fixtures/k1_fe_gx_native_pin_map.json`.

**Gx is not the 3 Nov FE board.** It has no STUSB4500 and no 20 V input. `:pd_status` / `:pd_nvm_write` belong to the old 20 V profile and do nothing useful on Gx. The release `fe-1.0.0-rc1` targets the old board: do not flash it to a Gx.

## Gx pins the firmware uses (ESP32-S3 GPIO numbers, not module pad numbers)
| Function | GPIO | Function | GPIO |
|---|---|---|---|
| LED primary DIN-A / DIN-B (WS2816) | 15 / 16 | LED secondary DIN-A / DIN-B | 17 / 18 |
| Mic PDM CLK / DATA (IM69D130) | 48 / 41 | PCM1808 BCK / LRCK / DOUT | 47 / 14 / 21 |
| Jack detect (high = plug in) | 42 | Protected 5 V eFuse PG | 40 |
| POWER_PERMIT (eFuse threshold) | 39 | CC1 / CC2 sense (ADC) | 4 / 5 |
| LED buffer OE A / B (external pull-ups, not driven) | 38 / 6 | Heartbeat LED | 8 |
| I²C SDA / SCL (ADC header) | 2 / 1 | External ADC SHDNZ (held low) / ADC DOUT (input) | 46 / 45 |
| Nav right / press / left | 3 / 9 / 10 | User 1 / 2 / 3 (active low) | 12 / 13 / 11 |

## 1. Flash (per board)
1. Plug the board into the Mac with USB-C. Hold BOOT, tap RESET, release BOOT only if it does not enumerate.
2. Read its MAC: `~/.platformio/penv/bin/python -m esptool --port /dev/cu.usbmodemXXXX read_mac`.
3. Add the board to `scripts/platformio/k1_device_identities.json` → `authorized`: `chip_id` (from `:dump` → `CHIP ID:` after first boot), `usb_serial` (the MAC), `role` "K1 FE Gx board #n", `envs` `["k1_fe"]`. Never add `k1_fe` to the Main RPL (`9087A500`): Gx drives GPIO8, which is that unit's mic data line.
4. Flash the tagged release: `git checkout fe-1.0.0-rc2 && bash scripts/agent/k1-flash-verified.sh k1_fe --port /dev/cu.usbmodemXXXX`. Pass = exit 0 and `IDENTITY OK: … env=k1_fe`.
5. Record the flash in `docs/hardware/device-build-registry.md` §2.

## 2. Serial lines to expect, in order (115200, `pio device monitor`)
| # | Line (prefix) | Pass when |
|---|---|---|
| 1 | `INIT_SERIAL: PASS`, `INIT FILESYSTEM: PASS`, `INIT_LEDS: PASS`, `INIT_SECONDARY_LEDS: PASS` | all PASS |
| 2 | `I2S PDM RX INIT: PASS slot=RIGHT`, `I2S ENABLE: PASS` | mic driver up |
| 3 | `[PCMCLK] mode=48K_MASTER_I2S24`, `[PCMCLK] gate=PASS` | LRCK ≈ 48 000, BCLK ≈ 3 072 000, ratio ≈ 64 (bench proof: 47 985.9 / 3 069 048.5 / 63.957) |
| 4 | `[PCM1808] init=PASS i2s=1 pins=21,47,14 slot=24in32 philips` | pins print as DOUT,BCK,LRCK = 21,47,14 |
| 5 | `[FEBOARD] profile=Gx i2c=ready sda=2 scl=1 external_adc=held_shutdown` | `i2c=ready` |
| 6 | `[FEPWR] profile=Gx pg=1 cc1_mv=… cc2_mv=… source=3A permit=1 led_budget_est_ma=1900 board_reserve_est_ma=400` | on a 3 A USB-C supply. 1.5 A supply: `source=1.5A permit=0 led_budget_est_ma=800`. Plain USB / unknown: `source=default_usb` or `unqualified`, `led_budget_est_ma=0` (LEDs black by design) |
| 7 | `[FEAUD] source=mic reason=… jack=out` (no cable) | present |
| 8 | `SYSTEM INIT COMPLETE!`, `RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96 …` | `timing_ok=1` |
| 9 | `[AP] SSL=… DC=… cal_source=… cal_valid=… raw_i16_rms=…` once a second | see check B |

Useful commands (type with the leading colon): `:fe_status` (prints `[FESTATUS] profile=Gx … vbus_protected_pg=… power_permit=… source=… led_budget_est_ma=… cc1_mv=… cc2_mv=… adc_shdnz=0`, then `[FESTATUS] source=… jack=… pcm1808_gate=PASS`), `:audio_src=auto|mic|line`, `:build` (reports `tag=fe-1.0.0-rc2`).

## 3. Three pass/fail checks per board
**A. Power (USB-C).** On a 3 A USB-C source: line 6 shows `pg=1 source=3A permit=1 led_budget_est_ma=1900`; exactly one of `cc1_mv`/`cc2_mv` is 1310–2040 and the other ≤ 200; flip the cable and the other CC carries it. The heartbeat LED (GPIO8) blinks at 1 Hz; LEDs light. On a 1.5 A source: `source=1.5A permit=0 led_budget_est_ma=800`, LEDs light dimmer on bright scenes. On a plain USB port: `led_budget_est_ma=0`, LEDs black, board still runs and the mic still works. Fail = `pg=0` on a good supply, both CC readings high or both low, `i2c=FAIL`, no heartbeat, or the eFuse trips (board resets) on a 3 A supply with a bright scene.

**B. Microphone (no music, room quiet).** `[AP]` lines show `raw_i16_rms` in the Main RPL quiet-room range (6.9–20.9, `docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/live-dump-preflight.txt`) and move on a clap. A new board starts `cal_source=default_invalid cal_valid=0`: the noise calibration runs only after someone confirms the room is silent (Calibration Command Policy; never with music playing). After it: `cal_source=measured` (then `persisted_profile`), `cal_valid=1`. Fail = `raw_i16_rms` 0, frozen at one value (the B489 wiring fault read −30935 constant), or no change on a clap.

**C. Line-in (3.5 mm).** Insert a cable playing music: `[FEAUD] source=line reason=jack_in jack=in`, then `:fe_status` twice a few seconds apart: `[FESTATUS] source=line`, `[PCMCAN] rms=… peak=… mono=MID` with rms > 0 following the music, `[PCMOVF] ovf=0 … ring_drop=0`. Pull the cable: `[FEAUD] source=mic reason=jack_out`, `[AP]` lines return. Fail = no switch (if the switch is reversed, the jack polarity on GPIO42 is opposite to the firmware's "high = in"), `rms=0.0`, or `UNAVAILABLE` (PCM1808 clock gate failed: check the 24.576 MHz oscillator, MD0/MD1 straps and RN_C1).

## Not proven before G5 (needs a real Gx board)
Every line above is read from source, not observed. Still to measure on the first board: CC ADC accuracy through the 100 kΩ series resistors; board idle and peak current and the real WS2816 per-channel current (the limiter's 1 mA/LED idle, 20 mA/channel and 400 mA board reserve are estimates); eFuse trip behaviour at the two POWER_PERMIT thresholds; GPIO45/46 strap levels at reset; jack-detect polarity on GPIO42; heartbeat on GPIO8; the FE line-in trim (the release carries the 7 Sep module's −24.08 dB, `K1_PCM1808_CANON_TRIM_Q15=2048`; set it from the Gx divider at G5). The external ADC on the test header has no capture driver: it stays in shutdown.

---
| Date | Author | Change |
|------|--------|--------|
| 2026-11-03 | agent:claude (FW lead) | Created for G5 (charter LEAD-FW-FE-RELEASE deliverable 5). |
| 2026-11-10 | agent:claude (FW lead) | Rewritten for the K1-FE-Gx board and release `fe-1.0.0-rc2`: Gx pin table, USB-C CC power check replaces the STUSB4500/20 V check, PCM1808 pins 21/47/14. |
