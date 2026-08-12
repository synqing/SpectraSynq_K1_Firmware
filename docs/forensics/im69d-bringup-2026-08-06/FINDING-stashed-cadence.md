# FINDING: the IM69D lane's device-proven AP cadence promotion is parked in a stash

Orchestrator-verified (own re-run), 2026-08-06.

## What is true

- `config_types.h:41,59` at `db300db` compiles **`DEFAULT_SAMPLES_PER_CHUNK 96` / `K1_TEMPO_NOVELTY_DECIMATION 3U`**.
- The live bench reports `samples_per_chunk=96 tempo_decim=3` — source and device agree.
- `12800/128/d2` appears in committed `platformio.ini` ONLY in isolated probe envs (:853,:855,:1065).
- **But `stash@{0}` contains the promotion**:
  ```
  -#define DEFAULT_SAMPLES_PER_CHUNK 96      +#define DEFAULT_SAMPLES_PER_CHUNK 128
  -#define SB_TEMPO_NOVELTY_DECIMATION 3U    +#define SB_TEMPO_NOVELTY_DECIMATION 2U
  ```
  and stashed docs assert: *"Promoted the compiled AP tuple to `12800/128/d2`"*, *"runs use the same
  `12800/128/d2` source tuple ... same bench K1 identity"*, and a GDFT ×2 guard **validated under
  that tuple**.

## Why it matters

1. The lane's authority docs describe a **device-proven** AP cadence the bench is **no longer running**.
   The `pr40-unblock` stash silently reverted a proven AP change; nothing warns about it.
2. Any conclusion drawn from those docs about current bench behaviour is invalid until the stash
   is restored — including the bass/full cadence recovery, which was proven under 128/d2.

## Forward hazard: the stash may be un-poppable as-is

`git stash show --name-only stash@{0}` (64 files) targets **pre-rename** paths:
`audio/sb_onset_beat.cpp`, `audio/sb_tempo.cpp`, `audio/sb_semantic_state.{cpp,h}`.
`origin/main` renamed these to `k1_*` in `565b95f` (de-SB → K1 sweep). Popping onto `db300db` will
conflict or resurrect duplicate translation units. The parked lane work needs manual reconciliation
against the renames — it cannot simply be popped.

## Coupled risk if 128/d2 IS restored (SSA-2, spot-checked)

Hand-derived frame-count literals with no runtime recompute, baked for 133.33 Hz / dt=7.5 ms:
`K1V2_MEDIAN_WIN=14`, `K1V2_WARMUP_FR=14`, `K1V2_PRE_MAX/PEAK_WAIT=4`,
`K1V2_KICK/SNARE/HIHAT_REFR=6/5/3` (`audio/k1_onset_beat.cpp`), `STM_TEMPORAL_FRAMES=17`
(`audio/k1_stm.cpp`). At 128/d2 each silently gains ~+33 % real duration. No compile or test failure.
`K1_TEMPO_AP_FRAME_HZ` correctly self-derives — cleared, not at risk.

## Re-run commands

```
grep -n 'DEFAULT_SAMPLES_PER_CHUNK\|K1_TEMPO_NOVELTY_DECIMATION' SPECTRASYNQ_K1_FIRMWARE/system/config_types.h
git stash show -p stash@{0} | grep -nE '^[+-].*(DEFAULT_SAMPLES_PER_CHUNK|TEMPO_NOVELTY_DECIMATION)'
git stash show --name-only stash@{0} | grep 'audio/sb_'
```
