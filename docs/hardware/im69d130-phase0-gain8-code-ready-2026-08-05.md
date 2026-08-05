# IM69D130 Phase 0 — Gain 16→8 CODE_READY (2026-08-05)

**Task ID:** `ap-advice-phase0-im69d-gain8`  
**Branch:** `feat/ap-advice-phase0-im69d-gain8` (from `lane/dual-sync-phase0` @ `97276b3`)  
**Env / device target:** `k1_bench_im69d` @ bench `B489A500` / MAC `B4:3A:45:A5:89:B4`  
**Plan:** `~/.cursor/plans/ap_advice_audit_8a197b6a.plan.md` — Phase 0 only

---

## STATUS

| Field | Value |
|---|---|
| STATUS | **CODE_READY** |
| CLAIM | Host tree has `K1_MIC_IM69D_INPUT_GAIN = 8.0f` under `#ifdef K1_MIC_IM69D_PDM_V1`; `k1_bench_im69d` rebuild **SUCCESS** |
| NOT YET | Captain flash approval; Captain silence-go; quiet/music AP pair; silence=1 proof |
| Gate for Phase 0 complete | Device silence asserts (`silence=1` in quiet) + music drive alive + `raw_i16_near_pct≈0` |

---

## Gain change

| Item | Value |
|---|---|
| Before (live / prior retune) | `K1_MIC_IM69D_INPUT_GAIN = 16.0f` |
| After (this branch) | `K1_MIC_IM69D_INPUT_GAIN = 8.0f` |
| File | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` under `#ifdef K1_MIC_IM69D_PDM_V1` only |
| Why | At G=16 quiet `max_raw` 307–1190 overflowed SSL learn window `[50,720]`; silence never asserted. Halve so quiet projects into the learnable band while music still clears SSL. |

IM73D / SPH gain paths untouched.

---

## Build

| Check | Result |
|---|---|
| Command | `bash scripts/agent/pio-build.sh k1_bench_im69d` |
| Result | **SUCCESS** (~20 s) |
| Provenance | `env=k1_bench_im69d git=97276b3` |
| Size | RAM 32.9% (107792/327680); Flash 9.9% (650806/6553600) |
| Log | `_scratch/im69d_phase0_gain8_20260805/pio_build_k1_bench_im69d.log` |

No flash / upload / monitor / `start_noise_cal` in this pass.

---

## Files touched for Phase 0 readiness

Phase 0 gain line is in `constants.h`. Restoring the previously uncommitted `k1_bench_im69d` env (lost from dirty tree / not in stash) was a prerequisite so the env can build:

- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` — IM69D block + **G=8.0f**
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` — IM69 PDM path
- `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h` — `/cal_profile_im69d.bin` namespace
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h` / `system.h` / `calibration/noise_cal.h` — shared PDM helpers
- `platformio.ini` — `[env:k1_bench_im69d]`
- `scripts/agent/pio-build.sh` / `scripts/platformio/k1_upload_guard.py` — allowlist + bench binding
- `tests/test_im69d_env_static.py` / `tests/test_k1_upload_guard.py` — static locks

**Not committed** (Captain did not ask for commit).

---

## Forbidden / compliance

- No flash / upload / serial monitor
- No `start_noise_cal` / `N` / `Y`
- No `*im73d*` flash against CLK=14/DATA=13
- No Phase 1 (ghost bins) or Phase 2 (×2 formula)

---

## Exact next Captain actions

1. **Approve flash** of `k1_bench_im69d` to bench `B489A500` only (identity-gated; never `*im73d*` on this wiring).
2. **Silence-go** verbal confirmation, then noise cal → SSL inside `[50,720]`.
3. **Quiet / music AP pair** — gate: quiet `silence=1`; music `max_raw` ≫ SSL; `raw_i16_near_pct≈0`; lamp dark in quiet.
4. Only after that gate: mark Phase 0 complete and allow Phase 1.

---

## References

- Prior G=16 retune: [`im69d130-gain-retune-2026-08-05.md`](./im69d130-gain-retune-2026-08-05.md)
- Silence defect: [`im69d130-vs-main-k1-eval-2026-08-05.md`](./im69d130-vs-main-k1-eval-2026-08-05.md)
- Env implement receipt: [`im69d130-env-implement-receipt-2026-08-05.md`](./im69d130-env-implement-receipt-2026-08-05.md)
