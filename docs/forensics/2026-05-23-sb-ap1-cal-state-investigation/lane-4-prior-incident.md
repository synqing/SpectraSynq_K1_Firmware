---
abstract: "Lane 4 (AP-1 archaeology) — Documents the prior S3-port-AP incident Captain referenced. The closest match is the 2026-05-19..21 WAVEFORM/BLOOM calibration-mutex investigation (claude-mem obs 53406, 53433, 53447, 53469, 53470, 53940 + audit/understanding/01_waveform_kill_investigation.md + project_sb_audio_pipeline_debug_2026-05-20.md). Root cause then: mixed signal domains in i2s_audio.h (max_waveform_val_raw tracked DC-biased sample while SSL/follower math assumed AC-corrected). Fix landed in FIRMWARE_VERSION 40102 on the S2. Current K1 hardware (ESP32-S3, FIRMWARE_VERSION 40102 confirmed) reproduces a DIFFERENT but related failure mode — DC=-32767 saturation rather than DC=8800 SSL-inflation — likely because the S2 sample-conversion chain (`raw*0.000512+56000-5120 >> 2`) is still executing on S3 hardware where SPH0645 raw samples have a different magnitude/sign profile (S3 community port uses `rawSample >> 10` from a stereo-interleaved channel-right slot instead, which the K1.Lightwave fork already implements). Lane 4 evidence supports treating AP-2 as the *same bug family* (i2s_audio.h sample-domain mismatch ⇒ noise_cal pollution ⇒ pipeline collapse) but the *current saturation vector is new* and lives in the S2-vs-S3 conversion-chain delta, not in noise_cal.h arithmetic alone."
---

# Lane 4 — Prior "S3-Port-AP-At-The-Beginning" Incident Archaeology

## Search queries executed

| Query | Surface | Hits |
|-------|---------|------|
| `noise_cal S3 DC_OFFSET` | claude-mem (project=SensoryBridge-main 9) | 21 (10 obs + 10 sess + 1 prompt) |
| `MEMS DC negative -32767` | claude-mem | 14 (10 obs + 3 sess + 1 prompt) |
| `max_raw 0 noise calibration` | claude-mem | 10 obs |
| `S3 port audio pipeline beginning` | claude-mem | 5 obs |
| `calibration mutex signed unsigned i2s` | claude-mem | 8 (4 obs + 4 sess) |
| `SPH0645 S3 port DC bias sign` | claude-mem | 11 (10 obs + 1 prompt) |
| `K1v2 noise_cal first boot ESP32-S3` | claude-mem | 14 (10 obs + 3 sess + 1 prompt) |
| `dc_offset_sum overflow saturation INT16_MIN` | claude-mem | 10 obs |
| `SPH0645 32-bit shift 14 i2s sample conversion S3` | claude-mem | 0 hits |
| `firmware-v3 noise_cal Lightwave-Ledstrip DC fix` | claude-mem | 23 (10 obs + 5 sess + 8 prompt) — none directly on-topic |
| `audit/understanding/01_waveform_kill_investigation.md` | filesystem | 1 file (read in full) |
| `audit/understanding/02_agc_ssl_dc_follower_history.md` | filesystem | 1 file (read in full) |
| `~/.claude/projects/-Users-spectrasynq-SensoryBridge-main-9/memory/project_sb_audio_pipeline_debug_2026-05-20.md` | MEMORY | 1 file (read in full) |
| `/Users/spectrasynq/Workspace_Management/Software/K1.Lightwave/src/i2s_audio.h` | reference S3 port source | 1 file (sample chain read) |
| `/Users/spectrasynq/Workspace_Management/Software/K1.Lightwave/src/noise_cal.h` | reference S3 port source | 1 file (read in full) |
| `docs/forensics/2026-05-23-archaeology/` | filesystem | enumerated only (PROBLEMS_INVENTORY_2026-05-20.md + 20 audit files; not opened — coverage already obtained from L1 audit memos) |
| `.planning/k1-vp-drift/` | filesystem | enumerated 51 files; not directly relevant to AP arithmetic |
| Lightwave-Ledstrip / firmware-v3 CHANGELOG | filesystem | not present in this repo; references found only via claude-mem cross-project memory |

## Confirmed prior incidents

### Incident 1 — Waveform-stuck-at-edge (uncalibrated DC) — 2026-05-19

- **Source:** claude-mem `#53406` (bugfix); `system.h` `init_system()` DC_OFFSET=0 fallback stamp.
- **Date:** 2026-05-19 21:34 UTC.
- **Symptom:** With `CONFIG.DC_OFFSET == 0` (uncalibrated sentinel after factory reset or first boot), `waveform[]` carried ~8000 constant DC offset from SPH0645. `waveform_peak_scaled` collapsed to a stuck-at-edge value; WAVEFORM mode showed dot pinned at one end of the strip.
- **Root cause:** MEMS DC bias survives the full sample-conversion chain `(raw * 0.000512) + 56000 - 5120` then `>>2 * SENSITIVITY` as a ~8000 constant in `waveform[]`. Without DC_OFFSET subtraction the AC-domain math (`max - SSL`) degenerates.
- **Fix:** `system.h:328` — if `CONFIG.DC_OFFSET == 0` on boot, stamp `8304` and persist via `save_config()`. Subsequent `start_noise_cal()` refines to per-unit MEMS bias.
- **Status:** Landed. *But on K1 the bias is negative-signed (~-8767 per `project_sb_audio_pipeline_debug_2026-05-20.md` line 86), so the +8304 default is wrong by ~17K* on this hardware — Captain explicitly called this out as out-of-scope cleanup. (See "Cross-reference" below — this is the *AP-1 wrong-sign default* that the current 10-lane SSA is closing.)

### Incident 2 — WAVEFORM/BLOOM calibration mutex (mixed signal domains) — 2026-05-19 → 2026-05-21

- **Source:** claude-mem `#53433` (discovery), `#53447` (kill-vector confirmation), `#53469` (noise_cal.h state), `#53470` (i2s_audio.h root cause), `#53457` (full i2s_audio.h architecture), `#53940` (resolution); `~/.claude/projects/-Users-spectrasynq-SensoryBridge-main-9/memory/project_sb_audio_pipeline_debug_2026-05-20.md`; `audit/understanding/01_waveform_kill_investigation.md`; `audit/understanding/02_agc_ssl_dc_follower_history.md`.
- **Date:** 2026-05-19 → 2026-05-21 (FIRMWARE_VERSION bump 40101 → 40102 on 2026-05-20; hardware confirmation 2026-05-21).
- **Symptom:** Binary mutex on noise_cal state. Pre-cal: WAVEFORM visible, BLOOM was a flat uniform sheet. Post-cal: BLOOM rendered, WAVEFORM went completely dark. Reproducible across flashes; survived 18 prior fixes and a full Broadband AGC v2 rewrite.
- **Root cause:** Two signal domains were mixed in `i2s_audio.h`. (a) `max_waveform_val_raw = abs(sample)` tracked the DC-biased sample (sample was still BEFORE the `waveform[i] = sample - DC_OFFSET` subtraction). (b) During noise cal, `DC_OFFSET=0` for all 256 iterations, so SSL was sampled from DC-biased peaks (~8000 × 1.10 = 8800). (c) Post-cal, `max_waveform_val = max_waveform_val_raw - SSL = 8000 - 8800 = -800` permanently; the follower floor clamp at i2s_audio.h:132-134 pinned the follower to SSL=8800; `waveform_peak_scaled = neg/large ≈ 0` → WAVEFORM rendered black.
- **Fix:** FIRMWARE_VERSION 40102, four edits:
  1. `i2s_audio.h:82 (now 87)` — `uint32_t sample_abs = abs(waveform[i])` (was `abs(sample)`) — peak now tracked in AC-corrected domain.
  2. `i2s_audio.h:103-122 (now 108-136)` — two-phase cal. Phase A (iters 0..127) accumulates `dc_offset_sum` from DC-biased `waveform[0]`. At iter 128, `CONFIG.DC_OFFSET = dc_offset_sum / 128`. Phase B (iters 129..240) samples SSL from AC-corrected `max_waveform_val_raw`.
  3. `GDFT.h:147-156` — removed the obsolete end-of-cal `DC_OFFSET = dc_offset_sum/256.0` stamp and the post-hoc `SSL -= DC_OFFSET` correction (no longer needed; both quantities are now stamped in correct domain).
  4. `SPECTRASYNQ_K1_FIRMWARE.ino:53` — `#define FIRMWARE_VERSION 40102` (was 40101). `bridge_fs.h:209` uses FIRMWARE_VERSION as config filename suffix, orphaning `/CONFIG_40101.BIN` so persisted SSL/DC_OFFSET cannot poison the test.
- **Status:** Landed and verified on Captain's K1 on 2026-05-21. Confirmed telemetry `[AP] SSL=594 DC=-8767 max_raw=700..2400 follower=tracking peak_scaled=0.32..0.62 silent_scale=1.0 silence=0`. Captain's MEMS produces a **negative-signed** baseline (~-8767), not the +8000 the old +8304 fallback assumed. Mutex declared dead.

### Incident 3 — Waveform-After-Noise-Cal Kill (audit lane, pre-fix) — 2026-05-19

- **Source:** `audit/understanding/01_waveform_kill_investigation.md` (file in this repo, lines 9-14, 73-97, 126-138); claude-mem `#54235`.
- **Date:** 2026-05-19 (audit memo) → still open at audit write time.
- **Symptom:** "Waveform visually died immediately after `start_noise_cal()` completed: no moving dot, no trail, black until reset."
- **Root cause:** Documented as the same mechanism as Incident 2 above (i2s_audio.h waveform-peak pipeline + noise_cal/GDFT.h post-cal side-effects). The audit memo states `start_noise_cal()` zeroes DC_OFFSET / VU_LEVEL_FLOOR / SSL at start before recomputing, and the subsequent SSL re-derivation occurs in incoherent domains.
- **Fix:** Same fix as Incident 2 (FIRMWARE_VERSION 40102).
- **Status:** Audit memo was the *investigation surface* whose conclusions drove the FIRMWARE_VERSION 40102 fix. Landed.

### Incident 4 — P2P noise-cal propagation removed (refactor, unrelated to arithmetic) — 2026-05-22

- **Source:** claude-mem `#54049` (change).
- **Date:** 2026-05-22.
- **Symptom:** N/A — refactor.
- **Root cause:** N/A — code cleanup. `propagate_noise_reset()` and `propagate_noise_cal()` extern declarations and calls removed from `noise_cal.h` (clear path) and `led_utilities.h` (cal-transition handler).
- **Fix:** Local-only noise calibration; no network broadcast.
- **Status:** Landed. **Side note:** the current `noise_cal.h` (re-read in this lane) confirms `propagate_noise_reset()` is gone — no extern call.

### Incident 5 — K1v2 LEDC + PSRAM + watchdog boot crash (LED-layer, NOT AP) — 2026-05-23 first boot

- **Source:** claude-mem `#54168`.
- **Date:** 2026-05-23 first-boot session.
- **Symptom:** `ledc_set_duty: LEDC is not initialized` spam; PSRAM `0x00ffffff` read error; CPU 0 task watchdog after ~16 s.
- **Root cause:** Cited LEDC sweet-spot guard not firing, PSRAM driver mismatch, render loop blocking. **Listed here for completeness only — this is the LED-1 lane, NOT the noise_cal AP-2 lane.**
- **Fix:** Lane-LED-1 in the current 10-lane SSA owns this; LEDC sweet-spot wrapper landed; PSRAM error reclassified as runtime anomaly per claude-mem `#54245`.
- **Status:** LED-1 closed per current AP-2 narrative.

### Incident 6 — K1v2 first-boot performance + uint8_t button-pin wrap (AP-adjacent but not AP) — 2026-05-22

- **Source:** claude-mem `#54136`.
- **Date:** 2026-05-22.
- **Symptom:** First K1v2 boot showed `SYSTEM_FPS=30.21` / `LED_FPS=76.84` (far below S2's ~120), button pin `255` (uint8_t wrap of -1 sentinel), MAC-derived USB device name. AP telemetry was *working* (DC=8304, max_raw=24465, peak≈1.000).
- **Root cause:** S3 performance regression vs S2 (cause unknown — render loop, task pinning, I2S DMA), uint8_t storage truncating -1 sentinel.
- **Fix:** Not yet landed at memo time.
- **Status:** Adjacent issue. The `[AP] DC=8304 max_raw=24465 peak_scaled≈1.000` from this boot is the *exact pre-cal state* the current AP-2 sees before noise_cal is run — meaning the +8304 default is being stamped on K1 hardware where the true bias is negative, producing inflated max_raw (24465 = `(raw - DC_OFFSET) → (raw - 8304)` where raw is actually `raw + |bias|`).

### Incident 7 (referential, not local) — Sensory Bridge S2 → S3 forensic audit (cross-project) — 2026-05-23

- **Source:** claude-mem `#54196` (LightwaveOS_Official project, NOT this repo); written to `docs/agent-outputs/analysis/forensic-audit-s2-to-s3.html` in LightwaveOS_Official.
- **Date:** 2026-05-23 02:59 UTC.
- **Symptom:** 13-phase S2 → S3 migration history captured. Mentions AP-related items: I2S DMA buffer count 2 → 8 (commit `ed83a0f`) resolved 27 ms blocking, restored 120+ FPS. Float GDFT → integer GDFT (commit `62aa8b0`) restored single-core 120+ FPS. SPH0645 I2S configuration treated as a top-level migration concern but **no record of an INT16_MIN / -32767 saturation incident** in this S2→S3 forensic.
- **Root cause:** N/A — historical doc.
- **Status:** Reference only; this repo's K1 firmware does **not** track the LightwaveOS_Official S3 migration path. Cross-checked because Captain explicitly invoked "the S3 port at the beginning."

## Most-load-bearing finding

**Incident 2 (WAVEFORM/BLOOM calibration mutex, 2026-05-19..21) is the closest prior match — and the only fully-documented bug whose symptom space overlaps the current AP-2 vector.** The audit memo (`01_waveform_kill_investigation.md`) and the canonical resolution memo (`project_sb_audio_pipeline_debug_2026-05-20.md`) both explicitly call out:

1. `start_noise_cal()` zeroing `DC_OFFSET`, `VU_LEVEL_FLOOR`, `SWEET_SPOT_MIN_LEVEL` at the **start** of cal (still true in current `noise_cal.h` lines 7-9 — verified this lane).
2. Mixed signal-domain arithmetic between the DC-biased sample chain and the AC-corrected `waveform[]`.
3. The follower floor clamp at `i2s_audio.h:132-134` (now :157-159) as the latch point — a wrong SSL pins the follower for the rest of the session.
4. Captain's MEMS having a **negative-signed** baseline (~-8767) — the +8304 default in `system.h:359` is wrong by ~17K on K1.

**However, Incident 2's fix (FIRMWARE_VERSION 40102) is already shipped and verified on this firmware build (boot log confirms `FIRMWARE_VERSION=40102, CHIP_ID=F887A500` per `#54264`).** So the current AP-2 (`DC=-32767, max_raw=0`) is **a new failure mode in the same bug family**, not a regression of Incident 2.

The most likely structural cause of the **new** AP-2 vector — combining lane-4 evidence with the K1.Lightwave (S3-port-from-scratch) reference:

> The S2 sample-conversion chain `(raw * 0.000512) + 56000 - 5120 >> 2 * SENSITIVITY` is still executing on K1 (ESP32-S3) hardware, because the `#ifdef ARDUINO_ESP32S3_DEV` S3 branch that K1.Lightwave's port uses (`rawSample >> 10` from stereo right channel) was **never ported into this repo's `i2s_audio.h`**. The S2 chain has different overflow characteristics for the SPH0645's raw int32 magnitude when the bias sign flips negative — combined with `CONFIG.DC_OFFSET = +8304` (wrong-sign default) and `sample -= CONFIG.DC_OFFSET` at i2s_audio.h:77, the subtraction inflates `sample` magnitude, the `±32767` clamp engages, and during the noise-cal `dc_offset_sum += waveform[0]` accumulation across iterations 0..127 the running sum / 128 lands at INT16_MIN.

This is consistent with `#54269` noting "DC=-32767 is a saturation/clamp value during active calibration, not a settled bias reading" and with the K1.Lightwave port at `/Users/spectrasynq/Workspace_Management/Software/K1.Lightwave/src/i2s_audio.h:120-143` carrying an `#ifdef ARDUINO_ESP32S3_DEV` branch with `rawSample >> 10`, IIR DC-blocker, `RECIP_131072 * 32767.0f` normalization — none of which is present in the current K1 firmware tree.

## Cross-reference to current symptom

| Dimension | Incident 2 (2026-05-19..21, S2) | Current AP-2 (2026-05-23, K1/S3) |
|---|---|---|
| Hardware | ESP32-S2, K1 sister board with SPH0645 | ESP32-S3-DevKitC-1 N16R8, K1 with SPH0645 |
| Firmware version | 40101 → 40102 | 40102 (Incident 2 fix already present) |
| Pre-cal `[AP]` line | `SSL=750 DC=0 max_raw≈8000 peak_scaled≈stuck-edge` | `SSL=750 DC=8304 max_raw=24465 peak_scaled≈1.000` |
| Post-cal `[AP]` line | `SSL=8800 DC≈0 max_raw≈8000 follower=8800 peak_scaled≈0` (pre-fix) → `SSL=594 DC=-8767 max_raw=700-2400 peak_scaled=0.32-0.62` (post-fix) | First line during cal: `DC=0 max_raw=32767 rail` → next AP interval: `DC=-32767 max_raw=0 follower decaying` |
| Failure direction | SSL inflated positive (8800), follower clamped HIGH, peak_scaled → 0 | DC inflated negative (-32767, INT16_MIN saturation), max_raw → 0, follower decaying |
| MEMS bias on this unit | Negative-signed (~-8767 per project_sb_audio_pipeline_debug_2026-05-20.md:80, 86) | Implied same negative-signed bias (same SPH0645 family, K1 hardware) |
| Visible symptom | WAVEFORM dark; BLOOM rendered | All AP outputs silent (max_raw=0); both modes degraded |
| Mechanism class | Mixed-domain arithmetic (DC-biased vs AC-corrected) | Likely arithmetic saturation in S2-chain when running on S3 raw samples with wrong-sign +8304 default |
| Fix surface | `i2s_audio.h:82, 103-122`; `GDFT.h:147-156`; FIRMWARE_VERSION bump | TBD — Lane 1 owns noise_cal.h state-machine; Lane 4 evidence points to **i2s_audio.h sample-conversion chain S2-vs-S3 delta** and **system.h:359 wrong-sign default** as load-bearing |
| Resolution status | Closed | Open (AP-2 active investigation) |

## Open questions

1. **Sample-conversion chain question:** Is `i2s_audio.h:66` (`(raw * 0.000512) + 56000 - 5120`) numerically valid for ESP32-S3 + SPH0645 32-bit Philips raw samples? The K1.Lightwave port uses a completely different chain (`rawSample >> 10` from stereo channel-right slot, IIR DC-blocker, RECIP_131072 normalization). claude-mem `#52870` (Lightwave-Ledstrip canonical) specifies `>>14` shift for 32-bit Philips mode — neither the current S2 chain nor the K1.Lightwave `>>10` matches this exactly. Lane 1's noise_cal.h state-machine read is necessary but probably not sufficient — the upstream sample arithmetic in `acquire_sample_chunk()` lines 65-90 needs cross-validation against an S3-correct reference.

2. **`CONFIG.DC_OFFSET = +8304` default sign question:** `system.h:359` stamps `+8304` when uncal'd. Captain's measured bias on S2 was `-8767`. On K1/S3 first boot the AP shows `DC=8304` (the default fired) and `max_raw=24465` — the inflated max_raw is the smoking gun that `sample - CONFIG.DC_OFFSET` is doing the wrong arithmetic when both the sign of bias and the sample-conversion baseline are wrong for S3.

3. **`noise_cal.h` accumulator overflow question:** With wrong-sign default DC_OFFSET, `dc_offset_sum += waveform[0]` (i2s_audio.h:126, Phase A iterations 0..127) sums signed int32 values whose magnitude per-iteration could be ~20-30K post-clamp. Sum across 128 iters could reach ~3.8M (well within int32). `dc_offset_sum / 128` at iter 128 should produce a sane int32 quotient ∈ ±30K — **but is `dc_offset_sum` actually a 32-bit signed accumulator, or is it int16?** Lane 1 must verify the storage type in globals.h. If `dc_offset_sum` is int16, ~256 × ~250 = ~64K overflows to INT16_MIN = -32768; round to -32767 storage in CONFIG.DC_OFFSET — matches the observed saturation exactly.

4. **Lane 4 boundary question:** Lane 4 owned memory archaeology and is now complete. The most surgical follow-on for the SSA pod is to: (a) Lane 1 confirm `dc_offset_sum` storage type and inspect the iter-128 stamp arithmetic; (b) a new lane comparing `i2s_audio.h:65-90` (current S2-chain) vs K1.Lightwave's `#ifdef ARDUINO_ESP32S3_DEV` branch and the Lightwave-Ledstrip canonical I2S config (claude-mem `#52870`); (c) `system.h:359` `+8304` default must be flagged for sign-correction on K1 hardware (noted but explicitly out of scope per the 2026-05-21 resolution memo line 86).

## Document Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:ssa-lane-4 | Created — memory archaeology for AP-1 prior-incident lane. Surveyed 10+ claude-mem search queries, 4 audit memos, 2 reference source trees (current SB and K1.Lightwave), produced cross-reference table and ranked load-bearing finding. |
