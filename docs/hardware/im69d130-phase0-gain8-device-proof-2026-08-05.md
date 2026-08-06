# IM69D130 Phase 0 — Gain 4 DEVICE PROOF (2026-08-05)

**Task ID:** `ap-advice-phase0-im69d-gain8` (behavior-change ticket; gain stepped 16→8→**4**)  
**Branch:** `feat/ap-advice-phase0-im69d-gain8`  
**Env / device:** `k1_bench_im69d` → bench `B489A500` / USB `B4:3A:45:A5:89:B4`  
**Port (this session):** `/dev/cu.usbmodem112401`  
**Plan:** `~/.cursor/plans/ap_advice_audit_8a197b6a.plan.md` — Phase 0 only  
**Evidence pack:** `_scratch/ap_advice_phase0_20260805/`

---

## STATUS

| Field | Value |
|---|---|
| STATUS | **DEVICE_PROOF — Phase 0 GATE PASS on `silence=1`** (G=4 + re-cal) |
| Gain | `K1_MIC_IM69D_INPUT_GAIN = 4.0f` (tree; flashed) |
| Flash | **SUCCESS** — guard-verified bench only; esptool hash verified; hard reset |
| Silicon | `:build → version=40103 git=9013ed9 epoch=1785942368 env=k1_bench_im69d` |
| Chip | `:chip_id → B489A500` |
| Noise cal | **ACCEPTED** — `ssl_p50=38 ssl_p90=67` → **SSL=74** |
| `cal_valid` | 1 (`measured`) |
| `raw_i16_near_pct` | 0.000 throughout |
| Quiet `silence=1` | **PASS** — 100% of 30 s re-latch window; earlier 50 s window 58%+ with long streak |
| Music / stimulus drive | Alive — stimulus `max_raw` up to **528** ≫ SSL=74; `peak_scaled` max **1.714** |
| Phase 1/2 | **Not started** |

---

## Root cause (Captain rage-valid)

At G=8, post-cal ambient self-noise / gain floor (`max_raw` mean ~214–296) sat **above SSL×1.2** (~133 with SSL=111). Loud-break cleared the 10 s silence latch forever. Quieter room was never the primary fix — mic gain put electrical/self-noise above the latch threshold. Music still had headroom (`max_raw`~1785, near-rail 0), so gain was lowered again to **4.0f**, then SSL re-learned on the actual quiet floor.

---

## Silence latch path (code)

`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` (runtime, non-cal branch):

1. `threshold_loud_break = CONFIG.SWEET_SPOT_MIN_LEVEL * 1.20` (~L640)
2. Sweet-spot silent candidate when smoothed raw ≤ AGC floor threshold (`sweet_spot_state = -1`, ~L717–728)
3. `silence = true` only after **≥10 s** continuous in that state (~L795–801)
4. Any `max_waveform_val_raw > threshold_loud_break` **immediately** clears silence and resets the timer (~L786–794)

SSL learn (cal Phase-B): `SSL = round(ssl_p90 * 1.10)` with window `[50,720]` (~L601–634).

---

## Before / after numbers

| | G=8 (prior proof) | G=4 (this proof) |
|---|---|---|
| Gain | 8.0f | **4.0f** |
| Cal SSL | 111 (`ssl_p90`≈101) | **74** (`ssl_p90`=67) |
| Loud-break (SSL×1.2) | ~133 | **88.8** |
| Quiet `max_raw` mean | ~214–296 | **~21–45** |
| Quiet vs loud-break | always above → latch impossible | **100% below** |
| Quiet `silence` | **0 forever** | **1** (latched) |
| Stimulus / music `max_raw` max | 1785 (track) | **528** (Mac `say`/Glass.aiff stimulus) |
| `raw_i16_near_pct` | 0 | **0** |

---

## Flash

| Item | Value |
|---|---|
| Guard | `k1_upload_guard.py --env k1_bench_im69d --upload-port /dev/cu.usbmodem112401` → bench `B489A500` |
| Upload | Direct esptool write_flash (PIO upload log truncated by host capture; esptool **SUCCESS**, all hashes verified) |
| Log | `_scratch/ap_advice_phase0_20260805/esptool_upload_gain4.log` |
| Main K1 | Untouched (`/dev/cu.usbmodem2101` = `F887A500`; guard rejects `k1_bench_im69d`) |
| Never | No `*im73d*` flash on this CLK=14/DATA=13 wiring |

---

## Noise cal (stable-floor)

| Attempt | Quality | Result | SSL |
|---|---|---|---|
| G=4 re-cal | `ssl_p50=38 ssl_p90=67` `dc_valid=1 ssl_valid=1` | **NOISE CAL ACCEPTED** | **74** |

Trigger: `N` arm → `Y` confirm (typed `start_noise_cal` is guidance-only). Log: `gain4_recal_and_quiet.log`.

---

## Phase 0 gate scorecard

| Criterion | Result |
|---|---|
| Gain under IM69D flag only (16→8→4) | PASS |
| Build `k1_bench_im69d` | PASS |
| Flash bench only | PASS |
| Quiet-eligible cal / stable-floor re-cal | PASS (ACCEPTED) |
| SSL in `[50,720]` | PASS (74) |
| `cal_valid=1` | PASS |
| `raw_i16_near_pct≈0` | PASS |
| Drive alive above SSL | PASS (stimulus max_raw 528 ≫ 74) |
| Quiet `silence=1` | **PASS** |
| Phase 1/2 | Not started |

**Phase 0 complete: YES** — silence latch greens at G=4 + SSL=74.

---

## Evidence files

- `esptool_upload_gain4.log` — flash
- `gain4_quiet_precal_summary.json` — stale SSL=111 still broken at G=4 before re-cal
- `gain4_recal_and_quiet.log` / `gain4_recal_quiet_summary.json` — cal accept
- `gain4_silence_wait50_summary.json` — first silence latch
- `gain4_music_stimulus_summary.json` — stimulus drive + silence break
- `gain4_quiet_relatch_summary.json` — **100% silence** for 30 s post-stimulus

---

## Commits / provenance

- Host gain constant: `K1_MIC_IM69D_INPUT_GAIN = 4.0f` in `system/constants.h` (working tree; flash provenance `git=9013ed9` + epoch embedded at build)
- Prior G=8 lane: `7741dd3` / flash `git=97276b3`
- This receipt supersedes the G=8 GATE FAIL conclusion for Phase 0 silence
