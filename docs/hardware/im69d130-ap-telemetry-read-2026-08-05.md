# IM69D130 AP Telemetry Read — 2026-08-05

**Task ID:** `im69d130-ap-telemetry-read`  
**Env / device:** `k1_bench_im69d` @ bench `B489A500` (Captain live `[AP]` paste)  
**Scope:** READ-ONLY analysis. No flash, no `start_noise_cal` / `N` / `Y`.  
**Default verdict entering this note:** `NOT_VERIFIED`  
**Exit claim:** front-end is **alive but under-gained** at `K1_MIC_IM69D_INPUT_GAIN=1.0`; next action is gain seed, not cal, not hardware chase.

---

## 1) Raw-domain levels vs IM73D (G=16 era)

| Condition | IM69 (Captain, G=1, DSR_16S) | IM73D restored-bench 2026-07-07 (G=16, DSR_8S) |
|---|---|---|
| Quiet `raw_i16_rms` | 5.5 … 8.7 | p90 14.7 … 17.9 |
| Quiet `raw_i16_abs_peak` | 7 … 11 | p90 21 … 26 |
| Music `raw_i16_rms` | 11.8 … 13.3 | vol45 p90 185 … 303 |
| Music `raw_i16_abs_peak` | 28 … 31 | vol45 p90 378 … 572 |
| Music/quiet peak ratio | ~3× | ~15–20× (vol45) |
| `raw_i16_near_pct` | 0.000 | 0.000 (usable legs) |

**Absolute:** IM69 music peaks are ~12–20× below IM73D vol45 raw peaks.  
**Ratio:** music clearly rises over quiet (~3× peak, silence flag 0→1), but the dynamic range is much thinner than the IM73D restored-bench usable legs.  
**Post-gain consistency:** music `max_raw` 67–74 ≈ `raw_peak≈30 × G=1 × SENSITIVITY≈2.4` — extraction math is coherent; the seed is simply too low for the shared SSL/follower domain.

Comparator caveats (do not over-claim A/B yet): different DSR defaults (IM69 DSR_16S vs restored IM73D DSR_8S), different programme / level control, no same-session matched ladder. Raw triples remain the honest surface (`im69d130-dual-mic-eval-design` §6.2).

---

## 2) Why `peak_scaled≈0` / `SSL=120` / `cal_reason=ssl_range` / `DC=0`

| Field | Value | Meaning |
|---|---|---|
| `DC=0` | expected | PDM HPF + boot force-invalidate (`system.h` PDM scrub) |
| `SSL=120` | expected | `NOISE_CAL_SSL_BOOT_FALLBACK_RAW` for IM69; never 0 |
| `cal_source=default_invalid` `cal_valid=0` | expected | no accepted IM69 cal (`/cal_profile_im69d.bin`) |
| `follower=120` | expected | follower floored to SSL |
| `peak_scaled≈0` | mechanical | `max_waveform_val = max(0, max_raw − SSL)`; music `max_raw` 67–74 **and** quiet 16–26 are both **below SSL=120** → drive clamps to 0 |
| `cal_reason=ssl_range` | latent / prior-cal signature | reject latch only set in Phase-B when learned SSL ∉ `[50,720]` (`i2s_audio.h`). At **G=1**, quiet `max_raw`≈16–26 cannot produce a learned SSL ≥ `NOISE_CAL_SSL_MIN_VALID_RAW` (50) — any silence-cal at current gain will fail this way |

`peak_scaled≈0` is therefore **not** evidence of a dead mic; it is the SSL floor starving an under-scaled working domain.

---

## 3) Classification

| Hypothesis | Fit |
|---|---|
| **Alive but under-gained** | **PRIMARY.** Non-zero raw, music/quiet separation, `near_pct=0`, silence bit tracks, brief tempo lock (`bpm≈127 lock=1`) + onset/bass under music; gain seed still `1.0` by design. |
| Wrong slot / stereo half | **Unlikely primary.** LEFT-slot Stage 1 shows music elevation; a hard-wrong empty slot is usually near-floor with no programme response. Defer slot A/B until after a gain bump. |
| Clock/data weak | **Unlikely primary.** Not pinned at 0, not near-rail garbage, RMS stable, silence detection coherent. |
| Needs cal only | **False as next step.** Cal cannot fix `max_raw < SSL`; at G=1 cal is predicted to reject `ssl_range`. |

Gates G1–G3 from the design doc are directionally green (driver previously smoked; liveness + non-rail floor hold). Front-end health vs IM73D baselines: **live, clean rails, under-driven working domain.**

---

## 4) Recommended NEXT (one primary path)

**Raise `K1_MIC_IM69D_INPUT_GAIN` first** (host edit + rebuild + guarded flash of `k1_bench_im69d` only), then re-read `[AP]` music/quiet `raw_i16_*` + `max_raw`/`peak_scaled`.

Rationale:

1. Seed is explicitly bring-up `1.0f` — design forbids inheriting IM73D G=16 blindly, but **requires** deriving G from measured peaks.
2. Formula (same as IM73D graft): `G_next = G_cur × target_max_raw / observed_max_raw`. With music `max_raw≈70` and SPH-band target ~7000 → order-of-magnitude **G≈80–100** as a characterization starting point; a conservative first step **G≈16–32** is enough to clear SSL=120 and make `peak_scaled` move for a second measurement pass.
3. **Silence-cal is blocked until gain lands quiet working peaks into a learnable SSL window** (`≥50` after p90×1.10). Ask Captain silence-go only after that.
4. Stereo / RIGHT-slot check is Stage 1b — only if post-gain music still looks dead relative to IM73D raw expectations.

---

## 5) What NOT to do

- **Do not** `start_noise_cal` / `N` / `Y` during music (or at G=1 — predicted `ssl_range` fail).
- **Do not** flash any `*im73d*` env against CLK=14 / DATA=13 (output-vs-output contention on GPIO13).
- **Do not** copy `K1_MIC_IM73D_INPUT_GAIN=16` as a final value without a measured retune pass.
- **Do not** chase PCB/slot rework while G=1 keeps `max_raw < SSL`.
- **Do not** use post-gain `max_raw` alone for mic A/B — keep `raw_i16_*` as the comparator.

---

## Evidence sources

- Captain live `[AP]` paste (this task brief) — music vs quiet
- `docs/hardware/im69d130-env-implement-receipt-2026-08-05.md` — G=1 seed, no cal, post-flash raw 3..38
- `docs/hardware/im73d-restored-bench-validation-2026-07-07.md` — IM73D quiet/music raw p90 table
- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` — IM69 gain/SSL seeds; IM73D G=16
- `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` — SSL subtract → `peak_scaled`; `ssl_range` reject path

---

## SSA status

| Field | Value |
|---|---|
| STATUS | VERIFIED (telemetry-read claim only; gain retune not yet done) |
| CLAIM | Alive + under-gained; next = raise IM69 input gain seed |
| METHOD_RISK | Medium if someone cals at G=1 or flashes im73d on this wiring — both forbidden above |
