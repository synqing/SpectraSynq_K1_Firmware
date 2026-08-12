# SSA-2-CADENCE-TUPLE — AP cadence tuple migration audit

Repo: /Users/spectrasynq/SpectraSynq_K1_Firmware @ db300db (branch feat/ap-advice-phase0-im69d-gain8)

## HEADLINE — the premise is false: NO migration has landed in any shipping/bench env

`env:k1_hardware` (= `default_envs`, platformio.ini:15,75-77) and every env that
extends it (`k1_prod_im73d`, `k1_bench_reference`, `k1_bench_im73d`, `k1_bench_im69d`,
...) still compile:

```
-DDEFAULT_SAMPLE_RATE=12800
-DDEFAULT_SAMPLES_PER_CHUNK=96
-DK1_TEMPO_NOVELTY_DECIMATION=3U
```

`git diff HEAD -- platformio.ini` is empty on these lines — working tree matches
HEAD, so this is not an uncommitted-change artifact. The **only** place
`12800/128/d2` exists is the isolated dev-only probe-matrix env
`k1_ap_frontend_probe_matrix_12800_128_d2` (platformio.ini:798-814), one of ~12
one-off A/B cadence-matrix harness envs, none of which is `default_envs`, none
of which any bench/prod env extends.

`docs/forensics/2026-08-05-note-offset-oob-and-bass-mode-budget.md:99` confirms
this reads forward, not backward: *"It strengthens the case for the AP hop
change (96 → 128, ...)"* — future tense, a **proposal**, not a completed
migration.

**Conclusion: the live device's `RUNTIME_TIMING_GUARD` line reporting
`samples_per_chunk=96 tempo_decim=3` is CORRECT and matches what
`env:k1_hardware`/`env:k1_prod_im73d` actually compile.** `progress.md` does not
contain a "promoted to 128/d2" claim anywhere (grepped; no hit). If any doc
implies the tuple already shipped, that doc is stale/wrong, not the device.

## Consequence for the audit question

Since production is still 96/d3, nothing is *currently* silently mistuned by a
hop change that hasn't happened. The real finding is **forward risk**: several
onset/beat/STM constants in `audio/` are hand-derived literals baked for
133.33 Hz (dt=7.5 ms) with **no runtime recomputation from
`DEFAULT_SAMPLE_RATE`/`DEFAULT_SAMPLES_PER_CHUNK`**. If the proposed 128/d2
(100 Hz, dt=10 ms) hop ever ships, these will silently retune to the wrong
real-world duration with no compile error and no test failure (a frame-count
`constexpr` is valid at any hop). One constant (`K1_TEMPO_AP_FRAME_HZ`) *does*
correctly self-derive and is NOT at risk — verified by reading its initialiser,
not assumed.

## Evidence table

| SYMBOL | file:line | units | value | real duration @ 96/d3 (133.33 Hz, dt=7.5ms) | real duration @ 128/d2 (100 Hz, dt=10ms) | migrated? | risk |
|---|---|---|---|---|---|---|---|
| `K1_TEMPO_AP_FRAME_HZ` | `audio/k1_tempo.cpp:38-39` | derived (`#ifndef`, `= DEFAULT_SAMPLE_RATE/DEFAULT_SAMPLES_PER_CHUNK`) | 133.333f (compiled) | 133.33 Hz | would auto-become 100 Hz if the two DEFAULT_* flags moved | **YES — self-recomputing, not hardcoded** | NONE (confirmed by reading the initialiser, per the failure-mode warning) |
| `K1V2_MEDIAN_WIN` | `audio/k1_onset_beat.cpp:49` | frames (literal `constexpr uint8_t`) | 14 | 14×7.5ms = 105 ms (matches intended 104 ms) | 14×10ms = **140 ms** (+33% vs. intended 104 ms) | NO — hardcoded | HIGH — median-adaptive onset threshold window silently lengthens |
| `K1V2_WARMUP_FR` | `audio/k1_onset_beat.cpp:87` | frames (literal `constexpr uint32_t`) | 14 | 105 ms | 140 ms | NO — hardcoded | LOW/MED — only extends onset-emission suppression at boot |
| `K1V2_PRE_MAX` / `K1V2_PEAK_WAIT` | `audio/k1_onset_beat.cpp:66-67` | frames (literal) | 4 / 4 | 4×7.5=30 ms (matches intended ~30ms) | 4×10=**40 ms** (+33%) | NO — hardcoded | MED — peak-pick dead-zone/refractory grows, caps max detectable onset rate |
| `K1V2_KICK_REFR` / `K1V2_SNARE_REFR` / `K1V2_HIHAT_REFR` | `audio/k1_onset_beat.cpp:73-75` | frames (literal) | 6 / 5 / 3 | 45/37.5/22.5 ms (exact match to intent) | **60/50/30 ms** (+33% each) | NO — hardcoded | MED — per-band retrigger latency grows ~33%, throttles fast/dense hits (hi-hat 16ths at high BPM) at the new hop |
| `K1V2_KICK_ALPHA` / `SNARE_ALPHA` / `HIHAT_ALPHA` | `audio/k1_onset_beat.cpp:78-80` | EMA coefficient (literal `float`, derived by hand for dt=7.5ms via `a=dt/(tau+dt)`) | 0.0141 / 0.0094 / 0.0047 | tau ≈ 525/792/1592 ms (intended) | same literal `a` reused at dt=10ms implies tau ≈ **699/1054/2123 ms** (+33% each) — envelope smoothing silently slows | NO — hardcoded, formula not re-run | MED — changes the 2026-06-30 N6 per-band AGC/envelope pacing tuned specifically for 133.33 Hz |
| `STM_TEMPORAL_FRAMES` | `audio/k1_stm.cpp:23` | frames (literal `constexpr uint8_t`) | 17 | 17×7.5=127.5 ms (matches intended, donor-derived) | 17×10=**170 ms** (+33%) | NO — hardcoded | MED — STM spectrotemporal modulation window duration drifts (feeds EdgeMixer STM_DUAL/STM_SPECTRAL_MAP modes 7/8, bench env `k1_hardware_stm` only, not default `k1_hardware`) |
| `K1_CONF_V2_WARMUP_UPDATES` | `audio/k1_tempo.cpp:319` | update-count (literal `#define`, counts novelty-rate emits, NOT raw AP frames) | 512 | novelty_rate=44.44Hz → 512/44.44=**11.52 s** | novelty_rate=50Hz (100/2) → 512/50=**10.24 s** (−11%) | PARTIAL — the *rate* it counts against self-derives correctly (via `K1_AP_FRAME_HZ`/`K1_NOVELTY_DECIMATION`), but the 512 threshold itself is not retuned, so real warmup duration still drifts ~11% | LOW — smaller drift than the frame-literal class above, self-adjusts via decimation, only the absolute threshold is stale |
| `K1V2_FLUX_RING` / `K1V2_ENV_RING` | `audio/k1_onset_beat.cpp:48,62` | frame capacity (literal) | 16 / 16 | ring holds ≥ MEDIAN_WIN(14)/PRE_MAX+PEAK_WAIT(≤8) frames, no overflow | still holds 16 frames worth (now 160ms/160ms of history) — **no overflow risk**, just more physical time captured per ring | NO — hardcoded, but harmless class | NONE/LOW — capacity constants, not duration-critical (the *contents'* window constants above are the actual risk) |

## Re-run commands (one per row)

```bash
# headline / shipping-env cadence
grep -n "DEFAULT_SAMPLE_RATE\|DEFAULT_SAMPLES_PER_CHUNK\|K1_TEMPO_NOVELTY_DECIMATION" platformio.ini | sed -n '1,20p'
git diff HEAD -- platformio.ini | grep -A3 -B3 "SAMPLES_PER_CHUNK\|NOVELTY_DECIMATION"
grep -n "promot\|128" progress.md docs/spec-index.md
grep -n "AP hop change" docs/forensics/2026-08-05-note-offset-oob-and-bass-mode-budget.md

# self-recomputing (no risk)
grep -n "K1_TEMPO_AP_FRAME_HZ" -B2 -A2 SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp

# hardcoded frame-literal rows
grep -n "K1V2_MEDIAN_WIN\|K1V2_WARMUP_FR\|K1V2_PRE_MAX\|K1V2_PEAK_WAIT\|K1V2_KICK_REFR\|K1V2_SNARE_REFR\|K1V2_HIHAT_REFR\|K1V2_KICK_ALPHA\|K1V2_SNARE_ALPHA\|K1V2_HIHAT_ALPHA\|K1V2_FLUX_RING\|K1V2_ENV_RING" SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.cpp
grep -n "STM_TEMPORAL_FRAMES" SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.cpp
grep -n "K1_CONF_V2_WARMUP_UPDATES\|k1_v2_updates" SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp
```

## Method / failure-mode check performed

Per the brief's warning ("counting a constant as frame-dependent when it is
actually recomputed from sample rate at init"): I read every initialiser before
judging. `K1_TEMPO_AP_FRAME_HZ` (k1_tempo.cpp:38-39) IS a derived `#ifndef` macro
(`DEFAULT_SAMPLE_RATE/DEFAULT_SAMPLES_PER_CHUNK`) — cleared, not counted as a
defect. Every other row above is a literal `constexpr`/`#define` integer or
float with no recomputation path — confirmed by reading the declaration site,
not inferred from the name.

## Scope note

Searched `audio/*.cpp`, `audio/*.h`, and `system/constants.h` for `*_FR`,
`*_FRAMES`, `*_WIN`, warmup, median window, EMA alpha/decay constants, ring
sizes, ACF lag/spread constants, and `133`/`0.0075`-style literals. No hits in
`system/constants.h` itself for cadence-scale constants (that file's `133`
hits are unrelated: `DIAG_FRAME_CHUNK_BYTES` and a note-offset lookup table).
`K1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=16U` (k1_tempo.cpp:66) was checked — it is a
work-spreading batch size (lags processed per emit), not a duration constant;
independent of hop.
