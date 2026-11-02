---
abstract: "One-page G5 bring-up kit for the K1 Founders' Edition board: how to flash release fe-1.0.0-rc1 (env k1_fe), the serial lines to expect in order, and the three pass/fail checks per board. For the HW and Build leads."
---

# K1 FE board — G5 bring-up (firmware `fe-1.0.0-rc1`, env `k1_fe`)

Source: `system/k1_fe_board.*` (board support), `audio/k1_pcm1808_input.*` (line-in), env `[env:k1_fe]` in `platformio.ini`. Board truth: `~/Workspace_Management/Software/K1-FE-Board/FE-BOARD-BRIEF.md`.

## 1. Flash (per board)

1. Plug the board into the Mac with USB-C. Hold BOOT, tap RESET, release BOOT only if it does not enumerate.
2. Read its MAC: `python3 -m esptool --port /dev/cu.usbmodemXXXX read_mac`.
3. Add the board to `scripts/platformio/k1_device_identities.json` → `authorized`: `chip_id` (from `:dump` → `CHIP ID:` after first boot), `usb_serial` (the MAC), `role` "K1 FE board #n", `envs` `["k1_fe"]`. The upload guard refuses any board not listed.
4. Flash the tagged release: `git checkout fe-1.0.0-rc1 && bash scripts/agent/k1-flash-verified.sh k1_fe --port /dev/cu.usbmodemXXXX`. Pass = exit 0 and `IDENTITY OK: … env=k1_fe`.
5. Record the flash in `docs/hardware/device-build-registry.md` §2.

## 2. Serial lines to expect, in order (115200, `pio device monitor`)

| # | Line (prefix) | Pass when |
|---|---|---|
| 1 | `INIT_SERIAL: PASS`, `INIT FILESYSTEM: PASS`, `INIT_LEDS: PASS` | all PASS |
| 2 | `I2S PDM RX INIT: PASS slot=RIGHT`, `I2S ENABLE: PASS` | microphone driver up |
| 3 | `[PCMCLK] lrck_hz=` … `[PCMCLK] mode=48K_MASTER_I2S24`, `[PCMCLK] gate=PASS` | LRCK ≈ 48 000, BCLK ≈ 3 072 000, ratio ≈ 64 (7 Sep proof: 47 985.9 / 3 069 048.5 / 63.957) |
| 4 | `[PCM1808] init=PASS i2s=1 pins=10,13,14`, `[PCMRATE] … gate=PASS`, `[PCM_RATE_PROOF] PASS` | DMA rate 45–52 kHz (proof: 47 997.9) |
| 5 | `[PCMING] source=im69d line=pcm1808 switch=jack canonical_hz=12800 hop=96` | present |
| 6 | `[FEBOARD] stusb4500=present addr=0x28 device_id=0x.. fe_board=1` | `present`. `absent` = PD chip or its I2C (GPIO41/42) dead: board fails |
| 7 | 20 V PD supply: `[FEPWR] input=20V permit=1 led_enable=1`. 5 V-only: `[FEPWR] input=5V_only led_enable=0 … LEDs stay dark` | matches the supply used |
| 8 | `[FEPWR] PD_FAULT_N=1` | 1 (0 = STUSB4500 fault) |
| 9 | `[FEAUD] source=mic reason=jack_out jack=out` (no cable) | present |
| 10 | `[FEPD] sink_pdo_count=3 pdo1=5000mV/500mA pdo2=20000mV/3000mA pdo3=20000mV/5000mA` | after `:pd_nvm_write` and a replug; before it, ST factory values print |
| 11 | `[FEPD] contract=PD source_pdo=n op_ma=… input_20v_pg=1` | on a 20 V supply |
| 12 | `SYSTEM INIT COMPLETE!`, `RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96 …` | `timing_ok=1` |
| 13 | `[FEPWR] LED_PG_A=1 LED_PG_B=1 banks=OK` (20 V only, ~150 ms after enable) | both 1 |
| 14 | `[AP] SSL=… DC=… cal_source=… cal_valid=… raw_i16_rms=…` once a second | see check B |

Useful commands (type with the leading colon): `:fe_status`, `:pd_status`, `:pd_nvm_write`, `:audio_src=auto|mic|line`, `:build` (reports `tag=fe-1.0.0-rc1`).

## 3. Three pass/fail checks per board

**A. Power and PD (20 V USB-C PD supply).** Run `:pd_nvm_write` once → last line `[PDNVM] PASS readback=match profile=5V0.5A/20V3A/20V5A`. Unplug, replug. `:pd_status` shows the three PDOs above; boot shows `input=20V permit=1 led_enable=1` and `LED_PG_A=1 LED_PG_B=1 banks=OK`; status LEDs 3V3, VBUS, PD 20 V, rail A, rail B lit; heartbeat (D_S9) blinks at 1 Hz. Then on a 5 V-only charger: LEDs dark and the `5V_only` line printed. Fail = any line missing or `FAIL`.

**B. Microphone (no music, room quiet).** `[AP]` lines show `raw_i16_rms` in the same range as the Main RPL quiet-room receipt (6.9–20.9, `docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/live-dump-preflight.txt`) and move when you clap. A new board starts `cal_source=default_invalid cal_valid=0`: the noise calibration runs only after someone confirms the room is silent (Calibration Command Policy; never with music playing). After it, expect `cal_source=measured` (then `persisted_profile` on later boots), `cal_valid=1`, SSL of the order of Main RPL's 157. Fail = `raw_i16_rms` 0 or frozen, or no change on a clap.

**C. Line-in (3.5 mm).** Insert a cable playing music: `[FEAUD] source=line reason=jack_in jack=in`, then `[PCMCAN] rms=… peak=… mono=MID` every 2 s with rms > 0 that follows the music, and `[PCMOVF] ovf=0 … ring_drop=0`. Pull the cable: `[FEAUD] source=mic reason=jack_out` and `[AP]` lines return. Fail = no switch, `rms=0.0`, or `UNAVAILABLE` (PCM1808 clock gate failed: check the 24.576 MHz oscillator and MD0/MD1 straps).

## Not proven before G5 (needs a real FE board)
LED_ENABLE / POWER_PERMIT sequencing, LED_PG readback, jack detect on GPIO40, the STUSB4500 NVM write and contract read-out, the heartbeat, and the FE line-in trim (the release carries the 7 Sep module's −24.08 dB; the FE divider is −9 dB, OI-05, so set the trim at G5).

---
| Date | Author | Change |
|------|--------|--------|
| 2026-11-03 | agent:claude (FW lead) | Created for G5 (charter LEAD-FW-FE-RELEASE deliverable 5). |
