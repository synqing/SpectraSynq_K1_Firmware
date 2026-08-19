# FPS / AGC clock decoupling — execution handover (hybrid r1)

**Date:** 2026-08-19 · **Lane:** fps_agc_clock_fix (plan `21bb9c1b`) · **Executor:** Cursor agent
**Authority order:** Captain instruction → [`docs/hardware/device-build-registry.md`](../../hardware/device-build-registry.md) → `.claude/CLAUDE.md` → this document → the original plan. Where this document contradicts the original plan or the GPT second opinion, **this document wins** — the contradictions below are evidence-backed corrections, not preferences.

**Provenance:** synthesised from plan `fps_agc_clock_fix_21bb9c1b` + Claude source-verification pass (2026-08-18/19: staged files at HEAD `293b211c`, git checks of deployed commits `a6149b29` / `573206c0`, both 2026-08-19 dumps) + GPT second opinion. GPT amendments **2** (lock α→τ conversion) and **3** (baseline before behaviour change) are adopted; GPT amendment **1** is adopted only in residual form — its premise is refuted (§0-C1). Deterministic tests replace the stopwatch as the acceptance gate (GPT concurrence).

---

## 0. Corrections to inherited analyses — read first, do not re-import these errors

**C1 — The GDFT broadband AGC is LIVE, not inert.** The `[AP]` field `agc_gain` prints `agc_bands[0].gain` (`i2s_audio.h:1397`), which mirrors the broadband `agc_gain` (`k1_gdft_core.cpp:677`). Both 2026-08-19 dumps show it moving **bidirectionally** at 1 Hz sampling (RPL 3.20→2.94→3.28→…→2.09; bench 4.43→0.449→1.167). The code freezes gain while gated (`k1_gdft_core.cpp:641–647`); a permanently closed gate cannot produce that series, therefore the gate opens routinely and the alphas at `:482–485` are live behaviour on the shipped chain (`spectrogram[i] *= agc_gain`, `:651`). `agc_env=0.000` is a print artefact: `%.3f` at 1 Hz of an envelope with 500 ms release in a near-silent room (raw_i16_rms ≈ 1–16) decays below 0.0005 between transients, while the gate threshold is only 4 × 0.001. The "dead code on hardware" comments (`i2s_audio.h:632`, `k1_gdft_core.cpp:636–638`) are **stale — correct them in this lane**. Do not treat the GDFT alpha migration as dormant/optional, and do not gate acceptance on the claim that this block is inert.

**C2 — The i2s follower chain is ALSO live and wrong-clocked.** `max_waveform_val_follower` uses hard-coded per-frame alphas 0.25 (attack) / 0.005 (release) (`i2s_audio.h:941–946`), and `waveform_peak_scaled` smoothing uses 0.65 / 0.25 (attack branches) and 0.15 / 0.25 (release branches) (`:979–996`), all stepped once per AP chunk frame. Both blocks — GDFT AGC **and** follower chain — are clock-fix targets. Neither is "the single live path".

**C3 — Bench `LED_FPS 0.00` is NOT a first-sample seed bug.** The `:1698` writer is present in the deployed bench commit (`git grep` confirms 3 occurrences in `573206c0`; the writer has existed since the initial fork commit). Bench uptime at capture was ≈ 52 min (`next_save_time: 3129649`). A 0.95/0.05 EMA converges from any seed within seconds; a persistent 0.00 therefore means **the writer never executed** — the whole `if (led_thread_halt == false)` frame body (`.ino:1341→1700`) was not running on the bench at capture. Seeding `last_frame_us` cannot fix this. Treat as an open VP-liveness defect (§2, step 1.3).

**C4 — The 93-vs-139 comparison is not yet controlled.** The units run different commits (`a6149b29` vs `573206c0`), the bench VP may have been idle at capture (C3), and both dumps were taken in near-silence. Do not attribute the AP gap to Lever-2, wire time, or anything else until the probe (§2, step 2) says so.

---

## 1. Verified ground truth (checked against source/dumps/git this session)

| Fact | Where |
|---|---|
| `SYSTEM_FPS` = Core-0 AP loop rate, 10-frame average | `.ino:1217` → `system.h:603–615` |
| AP is chunk-gated: blocking `i2s_channel_read` of 96 samples @ 12 800 Hz → design 133.33 Hz / 7.5 ms budget | `i2s_audio.h:446–490`; dumps `SAMPLE_RATE 12800`, `SAMPLES_PER_CHUNK 96` |
| RPL 93.08 Hz ⇒ AP ~3.2 ms/frame over budget ⇒ chunk backlog/overflow ⇒ **audio being dropped**, Goertzel history spliced | arithmetic on dump + read semantics |
| `LED_FPS` = Core-1 VP EMA at `.ino:1698` (probe-only twins at `:1389`, `:1417`); RPL 202.60 ⇒ VP frame ≤ 4.94 ms ⇒ `show()` cannot be serialising ≥ 9.6 ms | `.ino`, dump |
| GDFT AGC alphas 0.28 / 0.02 / 0.001 / 0.05, comment "at SYSTEM_FPS ≈ 100 Hz" | `k1_gdft_core.cpp:482–485` |
| `low_pass_array` already Hz-compensated (`1−exp(−2πf_c/f_s)`), called with live `SYSTEM_FPS` — **never dt-warp it too** | `utilities.h:54–64`, `k1_gdft_core.cpp:441` |
| Lever-2 packer: `budget_proxy = LED_COUNT·3·65535` ⇒ pass 1 always yields `s = 65535` (identity); pass 2 recomputes `sq_to_u16` fresh (no cached intermediates) ⇒ guard skip is behaviour-identical and self-degrading under a future real budget | `led_utilities.h:1099`, `k1_lever2_emit.h:14–58` |
| Lever-2 path returns at `led_utilities.h:1105`, **before** the `vp_perf.show` timer at `:1235–1248` ⇒ per-stage pack/show split needs new timers inside the branch. (Frame total is still captured at `.ino:1692–1695`.) | verified |
| `ENABLE_VP_PERF_AUDIT` on exactly 3 probe/harness envs (ini lines 409 / 767 / 982), absent from `k1_main_rpl_im69d`; `vp_perf` is `CMD_HARNESS` | `platformio.ini`, `serial_typed_cmd_table.def:76` |
| `K1_WS2816_LEVER2_V1` is defined for `k1_main_rpl_im69d` (ini:299) and **not** for `k1_hardware` ⇒ a `k1_hardware`-only build gate cannot compile-check the packer guard | `platformio.ini:282–299` |
| `last_frame_us` has a second consumer: effect-framework dt (`ctx.deltaTime*`, 8 ms fallback) | `.ino:470` |
| FastLED's first `show()` runs in `setup()` on the AP core, before `led_thread` exists | `.ino:755`, `:758–759` (`K1_LED_TASK_CORE 1`) |
| Core-0 AP headroom is ≈ 22 µs post-int64-GDFT (active_p95 7168 µs of 7500 µs pre-int64; +~310 µs since) — **any per-frame cost added to the AP path must be measured, not estimated** | measurement lineage 2026-07-13, Captain-ratified |

---

## 2. Execution sequence — the order is load-bearing (GPT amendment 3)

### Step 0 — free checks, before any code

- **0.1 (Captain, ten seconds):** is the bench strip animating right now? Record yes/no. *Yes* → the frame tail is being skipped some other way, investigate in 1.3. *No / frozen* → bench VP is halted and the 93-vs-139 A/B collapses (bench AP may be fast because its VP does nothing; 138.9 ≈ the 133.3 chunk-gated ceiling supports this).
- **0.2 (Agent):** `git diff a6149b29..HEAD -- SPECTRASYNQ_K1_FIRMWARE/` scoped to the AP/VP files touched by measurement. If the measured paths differ materially, build the probe env from a branch at `a6149b29` so the baseline measures the silicon that produced the dumps.

### Step 1 — host-only preparation (no flash, **no behaviour change**)

- **1.1 Tests first:** (a) α→τ equivalence-at-reference test (red until step 3 lands — at the reference cadence, new dt-derived alphas must reproduce the old constants exactly); (b) 93 Hz vs 139 Hz wall-clock envelope equivalence test (tolerance per existing onset-dt test template); (c) keep `tests/test_lever2_power_q16.py::test_limiter_disabled_equals_packer` green throughout.
- **1.2 Observability:** widen the `[AP]` print `agc_env` from `%.3f` to `%.4f` (`i2s_audio.h:1393`). This one character would have prevented the entire "inert AGC" misread.
- **1.3 Bench VP liveness investigation (source-level, no flash):** enumerate every way the `.ino:1341` frame body can be skipped persistently (e.g. `led_thread_halt` latched with no `K1_LED_PARK_V1` self-heal compiled in; task death; boot-ratchet degradation). Deliver the mechanism + a fix proposal. Do **not** claim the LED_FPS todo fixed until the mechanism is named.
- **Explicitly deferred out of step 1:** the packer guard and all alpha changes. Nothing that alters DSP behaviour or VP load lands before the baseline is captured.

### Step 2 — baseline probe (Captain GO required; flash `9087A500` only; non-ship env)

New env extending `k1_main_rpl_im69d` + `-DENABLE_VP_PERF_AUDIT=1`, plus:

- **2.1** `pack_us` / `show_us` timers **inside the Lever-2 branch before the `:1105` return** (the existing `vp_perf.show` hooks are unreachable there — verified).
- **2.2** Dump the AP-side surfaces that already exist: `vp_perf.gdft` stage time (`.ino:961–995`) and the i2s read debug (`k1_audio_i2s_read_debug`, `i2s_audio.h:511–534` — read wait, elapsed, capture sequence). No new AP instrumentation code should be needed; add a serial dump hook only if one is missing.
- **2.3 Show-skip discriminator:** a harness-class serial toggle that skips `show_leds()` for ~5 s while the render loop keeps running. Watch `SYSTEM_FPS`: a jump 93 → ~133 convicts LED wire *servicing* (interrupts/bus contention) on Core 0 in a single observation. This tests the standing hypothesis (UNPROVEN, labelled): FastLED's RMT channels/ISRs may be allocated during the `setup()`-time `show()` on the AP core, putting four strips' refill IRQs at ~202 FPS onto Core 0 — order-of-magnitude 1.5–3.5 ms per AP frame, the size of the observed hole.

**Decision rules (amended from the plan):**

- `show_us` ≲ 1 ms (queued async, no wait) **or** ≈ 4.8 ms (VP outran the wire, waits previous frame) → both healthy. Only ≳ 9.6 ms convicts RMT serialisation — which the `LED_FPS 202.6` arithmetic says should not occur; if it does, distrust the counter before the driver.
- Show-skip jump in `SYSTEM_FPS` → open the AP-contention/ISR lane (RMT `mem_block_symbols` / channel-allocation-core / DMA become relevant **as an ISR-rate fix, not a wire-throughput fix**). No jump → hunt inside the AP stage data from 2.2.
- I2S/LCD_CAM LED driver remains **struck** regardless of outcome.

### Step 3 — clock fix lands (after the baseline capture)

- **3.1 GDFT block** (`k1_gdft_core.cpp:482–485`): replace the four constants with dt-derived alphas. **Formulation locked:** rational form `α = dt/(τ+dt)` (matches the `sb_onset_beat` precedent; no `expf` on the AP path). **τ derived, not guessed** (GPT amendment 2): `τ = dt_ref·(1−α_old)/α_old` at the chosen reference cadence, so the equivalence test in 1.1(a) passes exactly by construction.
  - **Reference cadence decision (Captain, before landing):** default **100 Hz** — the cadence the code comment declares the constants were tuned for; it also avoids anchoring to RPL's 93 Hz, which is itself a defect state that later AP work may remove. Alternative: 93 Hz to freeze current RPL feel exactly. Either way, state it in the commit.
  - τ at 100 Hz reference (rational form): attack **25.7 ms**, release **490 ms**, noise **9 990 ms**, gain **190 ms**.
  - `dt` = measured wall interval between GDFT frames, clamped to [4, 20] ms. Expected shift: RPL ≤ ~9 % (attack 32.7 → 30 ms-class), **bench ~1.4× slower attack** — expected convergence, not a regression; record this so nobody "fixes" it.
- **3.2 Follower chain** (`i2s_audio.h:941–996`): same treatment, same reference, same formulation. τ at 100 Hz reference (rational): follower attack **30 ms**, follower release **1 990 ms**; `waveform_peak_scaled` attack branches **5.4 ms** (0.65) / **30 ms** (0.25), release branches **56.7 ms** (0.15) / **30 ms** (0.25). Map the conditional branches at `:979–996` precisely before converting. **Blast radius:** silence gating, sweet-spot, WAVEFORM-family feel — this is the larger behavioural change of the two; eyes-on regression under music is mandatory for this block.
- **3.3 Budget guard:** Core-0 headroom is ≈ 22 µs. The rational form costs a handful of divides per frame (fine); no `expf` per frame; if any transcendental is needed, bucket dt (e.g. 0.5 ms quanta) and cache. Confirm the marginal AP cost with a measured number, not an op count.
- **3.4** `low_pass_array(..., SYSTEM_FPS, ...)` untouched. **3.5** LED_FPS seed hygiene may land here (RPL boot-transient only — per C3 it does not close the bench item), preserving the `last_frame_us > 0` semantics for the effect-framework dt at `.ino:470`.

### Step 4 — packer guard lands (after step 2's baseline)

`if (budget_proxy >= (uint64_t)n * 3ull * 65535ull)` → skip pass 1, `s = 65535`. Verified behaviour-identical; keep the `>=`-max form so a future real budget re-enables pass 1 automatically. Optional but cheap: re-run the step-2 probe afterwards — any `SYSTEM_FPS` delta is a free causality measurement of VP-load→AP coupling.

### Step 5 — regression and stamps

- **Deterministic gate (primary):** the 1.1 pytest suite green — equivalence at reference + wall-clock match at 93 vs 139 Hz + packer identity. The stopwatch/eyes-on language is demoted to a regression check (GPT concurrence).
- **Behavioural gate:** A/B **under music** — both existing dumps are near-silence and cannot exercise the AGC. Check `agc_gain` step response tracks consistently across units; eyes-on RPL vs bench same track.
- **Bench stamp dependency:** "both units dump non-zero `LED_FPS`" requires the 1.3 fix **plus a bench flash that no current phase authorises**. Captain must either authorise a bench flash gate or weaken the stamp to RPL-only for this lane.

---

## 3. Build and flash gates

- Compile gate for any firmware change in this lane: `pytest tests/` **and** `pio run -e k1_main_rpl_im69d -e k1_bench_im69d -e k1_hardware`. (`k1_hardware` alone cannot compile-check the `K1_WS2816_LEVER2_V1` guard — ini:295 "Not on k1_hardware".)
- Flash: `9087A500` only, per registry; consult `docs/hardware/device-build-registry.md` first, upload guard is the last line of defence. Update the registry's deployed-state table after every flash.
- Probe env is non-shippable; never promote from a probe build.

## 4. Do-not list

No RMT geometry changes in this lane (Phase-2 gate unchanged). No I2S/LCD_CAM LED driver (struck). No `low_pass_array` change. No `start_noise_cal` (Calibration Command Policy — silence confirmation only). No K1 STA fallback. No mutexes/blocking/allocation on Core 0. F887A500 remains OFFSITE. No promotion onto `k1_hardware` — separate Captain close.

## 5. Open / unverified ledger

- **RMT ISR core-affinity hypothesis** — plausible mechanism and magnitude, unverified in this repo's vendored FastLED; discriminator is 2.3.
- **FastLED `drawAsync`/`waitDone` reading and LCD_CAM↔I2S0 exclusivity** — SSA-attributed, not re-read this session; the I2S strike stands regardless (VP is not the gap).
- **Bench VP liveness mechanism** — open (1.3); step 0.1 branches it.
- **Bench `SYSTEM_FPS` 138.9 > 133.33 design ceiling** — gauge is a 10-frame instantaneous average; treat absolutes as ±5 %, gaps as real. Possible PDM clock-divider offset; note only.
- claude-mem obs `#55046` / `#57502`, G2 `RESULT.json` — cited by the plan, not re-verified this session.
- In-flight SSAs (CPP-CTRL-01, C-RMT-02, EXP-FPS-04, EMB-RMT-09, DBG-COMPETE-10) may refine §2 decision rules; they do not change the step ordering.
