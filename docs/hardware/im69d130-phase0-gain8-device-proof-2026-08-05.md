# IM69D130 Phase 0 — Gain 8 DEVICE PROOF (2026-08-05)

**Task ID:** `ap-advice-phase0-im69d-gain8` (behavior-change ticket)  
**Branch:** `feat/ap-advice-phase0-im69d-gain8`  
**Env / device:** `k1_bench_im69d` → bench `B489A500` / USB `B4:3A:45:A5:89:B4`  
**Port (this session):** `/dev/cu.usbmodem112401`  
**Plan:** `~/.cursor/plans/ap_advice_audit_8a197b6a.plan.md` — Phase 0 only  
**Evidence pack:** `_scratch/ap_advice_phase0_20260805/`

---

## STATUS

| Field | Value |
|---|---|
| STATUS | **DEVICE_PROOF — Phase 0 GATE FAIL on `silence=1`** |
| Gain | `K1_MIC_IM69D_INPUT_GAIN = 8.0f` (committed) |
| Flash | **SUCCESS** — guard-verified, hash verified, hard reset |
| Noise cal | **ACCEPTED** (Captain silence-go; twice) |
| `cal_valid` | 1 (`measured` → `persisted_profile`) |
| `raw_i16_near_pct` | 0.000 throughout |
| Music drive | Alive — pre-cal loud leg `max_raw` up to **1785** ≫ SSL |
| `silence=1` | **Never latched** in post-cal quiet windows |
| Phase 1/2 | **Not started** (STOP after Phase 0) |

---

## Flash

| Item | Value |
|---|---|
| Guard | `k1_upload_guard.py --env k1_bench_im69d --upload-port /dev/cu.usbmodem112401` → verified bench `B489A500` |
| Upload | `pio run -e k1_bench_im69d -t upload` → **SUCCESS** |
| Silicon | `:build → version=40103 git=97276b3 epoch=1785941235 env=k1_bench_im69d` |
| Chip | `:chip_id → B489A500` |
| Log | `_scratch/ap_advice_phase0_20260805/pio_upload_final.log` |
| Main K1 | Untouched (`/dev/cu.usbmodem2101` = `F887A500`; guard rejects `k1_bench_im69d`) |

---

## Noise cal (Captain silence-go)

Captain explicit: **"Room is quiet now"** — treated as silence-go (Phase 0 waiver of interactive theatre; telemetry used as corroboration).

| Attempt | Quality | Result | SSL |
|---|---|---|---|
| 1 | `ssl_p50=53 ssl_p90=91` `dc_valid=1 ssl_valid=1` | **NOISE CAL ACCEPTED** | **100** |
| 2 (re-cal for latch) | `ssl_p50=63 ssl_p90=101` | **NOISE CAL ACCEPTED** | **111** |

Both inside SSL learn window `[50,720]`. Logs: `noise_cal_and_quiet.log`, `recal_silence_latch.log`.

---

## Quiet / music metrics

### Post-cal quiet (representative)

| Metric | Value |
|---|---|
| SSL | 111 |
| cal_valid | 1 |
| max_raw | min≈63–177, mean≈214–296, max≈350–475 |
| silence | **0** (0% of AP rows) |
| raw_i16_near_pct | 0.000 |
| peak_scaled | typically 0.5–1.0 (drive still alive) |

### Music / loud contrast (same session, pre-cal loud ambient)

| Metric | Value |
|---|---|
| max_raw | min 115, mean ≈994, max **1785** |
| raw_i16_near_pct | 0.000 |
| vs SSL=111 | ≫ SSL — music/drive domain alive |

---

## Why `silence=1` did not close

Firmware (`i2s_audio.h`):

1. Sweet-spot silent state when smoothed raw ≤ AGC floor threshold.
2. **`silence=true` only after ≥10 s continuous** in that state.
3. Any `max_raw > SSL × 1.20` **immediately clears** silence (`loud_break`).

With **SSL=111**, loud-break ≈ **133**. Post-cal room `max_raw` mean **~214–296** continuously exceeds that, so the latch never arms.

Cal windows themselves saw quieter samples (`ssl_p90` 91–101); after accept, ambient sat higher. USB open also injects `rst:0x15` boot spikes (capture artifact, not a cal reject).

`STANDBY_DIMMING` is **off** in dump → even with `silence=1`, `silent_scale` stays 1.0; lamp-dark additionally needs `max_raw ≲ SSL` so drive clamps to ~0. Observed briefly during cal (`max_raw` 44–82 → `peak_scaled` ~0.05), not sustained in post-cal quiet.

---

## Phase 0 gate scorecard

| Criterion | Result |
|---|---|
| G=16→8 under IM69D flag only | PASS |
| Build `k1_bench_im69d` | PASS |
| Flash bench only | PASS |
| Quiet-eligible cal / Captain silence-go | PASS (ACCEPTED) |
| SSL in `[50,720]` | PASS (111) |
| `cal_valid=1` | PASS |
| `raw_i16_near_pct≈0` | PASS |
| Music `max_raw` ≫ SSL | PASS (1785 ≫ 111) |
| Quiet `silence=1` | **FAIL** |
| Lamp can go dark in quiet | **FAIL** (drive stays up; ambient > SSL) |

**Phase 0 complete: NO** — blocked on silence latch / quiet-floor vs SSL×1.2.

---

## Human-only follow-up (next order)

1. Confirm true room quiet with ears + AP: need sustained `max_raw` **below SSL×1.2** (≥10 s) after cal, **or** re-cal when the ambient floor that should count as silence is the one being learned (not a quieter dip).
2. Optional eyes-on: lamp dark once `max_raw ≲ SSL` holds.
3. Do **not** start Phase 1 (ghost bins) or Phase 2 (×2) until this gate is green.

---

## Commits / provenance

- Gain + code-ready note: `7741dd3` (and lane base).
- This receipt + registry update: follow-on commit on `feat/ap-advice-phase0-im69d-gain8`.
- Flashed binary provenance: `git=97276b3` embedded at flash time (working tree gain=8).
