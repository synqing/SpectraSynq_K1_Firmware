# IM69D130 Env Implement Receipt — `k1_bench_im69d`

**Date:** 2026-08-05  
**Task ID:** `im69d130-env-implement`  
**Branch:** `lane/dual-sync-phase0` (additive IM69 work; no git commit)  
**Device:** bench K1 chip `B489A500` / USB MAC `B4:3A:45:A5:89:B4` @ `/dev/cu.usbmodem112401`

---

## Verdict

**HOST + DEVICE SMOKE: VERIFIED** for Stage-1 mono `k1_bench_im69d` (build, static locks, guarded flash, `:build`/`:chip_id`, live `raw_i16_*`).

Noise calibration was **not** run (forbidden without Captain silence-go). Stereo Stage 2 was **not** landed (mono-first by design).

---

## Pin / flag / cal summary (LOCKED as implemented)

| Item | Value |
|---|---|
| Env | `k1_bench_im69d` extends `k1_bench_reference` (LED 4/5) |
| Flag | `K1_MIC_IM69D_PDM_V1` (+ `K1_MIC_IM69D_DSR_16S_V1`) |
| Not used | `K1_MIC_IM73D_PDM_V1` (mutual `#error`; IM73D envs untouched) |
| CLK | GPIO **14** (`K1_PDM_CLK_PIN`) |
| DATA | GPIO **13** (`K1_PDM_DIN_PIN`) |
| SELECT | unused / not driven (`K1_IM69_PDM_SEL_PIN=12` escape hatch only) |
| DSR | `I2S_PDM_DSR_16S` (1.6384 MHz @ 12.8 kHz) |
| Slot | mono LEFT (Stage 1) |
| Cal file | `/cal_profile_im69d.bin` |
| Config ns | `/CONFIG_IM69_*.BIN` |
| Input gain seed | `K1_MIC_IM69D_INPUT_GAIN = 1.0f` (bring-up; not IM73D G=16) |
| Upload guard | `k1_bench_im69d` → bench `B489A500` / `B4:3A:45:A5:89:B4` only |

---

## What landed (files)

- `platformio.ini` — `[env:k1_bench_im69d]` (+ `k1_edgemixer.cpp` in src filter for dirty dual-sync `.ino` link)
- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` — IM69 pins/gain + mutual exclusion + `K1_MIC_PDM_RX_ANY_V1` helper
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` — separate IM69 PDM init (no LR GPIO drive) + mono acquire/telemetry
- `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h` — IM69 cal/config namespace
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h` — `im69d_samples_i16` + raw telemetry
- `SPECTRASYNQ_K1_FIRMWARE/system/system.h` / `calibration/noise_cal.h` — shared PDM boot/cal scrub via `K1_MIC_PDM_RX_ANY_V1`
- `scripts/platformio/k1_upload_guard.py` — bench env registration
- `scripts/agent/pio-build.sh` — allowlist
- `tests/test_im69d_env_static.py` — static locks
- `tests/test_k1_upload_guard.py` — bench binding case for new env

**Not modified:** `k1_bench_im73d` / `k1_prod_im73d` pin macros, flags, or cal path behaviour.

---

## What was NOT done

- No `start_noise_cal` / `N` / `Y`
- No stereo / `K1_MIC_IM69D_STEREO_V1`
- No flash of any `*im73d*` env against CLK=14/DATA=13 wiring
- No flash of main K1 (`F887A500`)
- No git commit

---

## Evidence paths

| Artefact | Path |
|---|---|
| Build log | `_scratch/im69d_env_20260805/pio_build_k1_bench_im69d.log` |
| Focused pytest | `_scratch/im69d_env_20260805/pytest_static.log` (18 passed) |
| Upload guard preflight | `_scratch/im69d_env_20260805/upload_guard_preflight.log` |
| Upload log | `_scratch/im69d_env_20260805/pio_upload_k1_bench_im69d.log` (`[SUCCESS]`) |
| Flash header readback | `_scratch/im69d_env_20260805/flash_app_header.bin` + `esptool_read_flash_header.log` |
| Post-flash serial | `_scratch/im69d_env_20260805/postflash_serial_final.log` |
| Post-flash summary | `_scratch/im69d_env_20260805/postflash_summary.json` |

### Device readback (excerpt)

```
:chip_id → B489A500
:build   → BUILD: version=40103 git=3b59794 epoch=1785926464 env=k1_bench_im69d
:dump    → CHIP ID: B489A500
[AP] … raw_i16_abs_peak=3..38 raw_i16_rms≈1.6..16.9 raw_i16_near_pct=0.000
       cal_source=default_invalid cal_valid=0  (expected; no cal)
```

PDM path is alive (non-zero raw, not near-rail). Gain seed still uncharacterised.

---

## Re-run commands

```bash
bash scripts/agent/pio-build.sh k1_bench_im69d
python3 -m pytest tests/test_im69d_env_static.py tests/test_k1_upload_guard.py -q
# Flash (bench only — identity-gated):
python3 scripts/platformio/k1_upload_guard.py --env k1_bench_im69d --upload-port /dev/cu.usbmodem112401
pio run -e k1_bench_im69d -t upload --upload-port /dev/cu.usbmodem112401
```

---

## NEXT

1. Captain silence-go before any IM69 noise cal (writes `/cal_profile_im69d.bin` only).
2. Characterise `K1_MIC_IM69D_INPUT_GAIN` from measured `raw_i16_*` (do not inherit G=16).
3. Stage 1b mono mic B (`slot_mask` RIGHT) then Stage 2 stereo if G1–G4 clear.
4. Optional: commit IM69-only files on a dedicated lane (not dual-sync commits).
