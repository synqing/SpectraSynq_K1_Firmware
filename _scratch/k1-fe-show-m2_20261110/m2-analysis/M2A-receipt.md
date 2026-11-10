---
abstract: "M2 lane A receipt (10 Nov 2026): locked Trinity e271af39 analysed the full Loreen recording; retained, keyed cache; artefacts validate against Trinity's schema; the PRISM adapter and locked compiler accept the passage view and the full track once one disclosed 10 ms segment clamp is applied; second run is a byte-identical cache hit."
---

# M2A — real-track Trinity analysis (Loreen), receipt

Asset: `/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3`, sha256 `a62e1f095de9c3e06563b40d0842acf64ca1bf6fece341a15190cb1c11ab9b0f` (verified). Label: **repo-approved regression fixture, not a Captain show sign-off.**

## Problems first

1. **Raw Trinity contract is rejected by the PRISM adapter.** allin1 puts the last segment end at 223.92 s; the decoded track is 223.910023 s (9,874,432 samples). Adapter rule: segment times must be ≤ `track.duration_sec`. Fix used here: a separate, disclosed correction layer `out/loreen/consumer/` (one clamp, 9.98 ms; `corrections.json`). The raw `contract.json` is untouched. Upstream defect: `export_contract.py` does not clamp allin1 boundaries to the duration.
2. **Stems are not reproducible from source.** Trinity `analyze_track.py:312` only passes `--shifts` when it is > 0, so `--demucs-shifts 0` is dropped and Demucs runs its default of one unseeded random shift of 0–0.5 s (`demucs/apply.py:214`). Two independent cold runs gave identical beats, downbeats and segments, but every stem and every stem feature differed (vocals RMS up to 0.064 apart; `raw/cold_vs_cold_stems.log`). The retained cache is the only reproducible copy. The first run's cache is kept at `cache/prior/<key>.run1` for comparison only. It is not the reference copy.
3. **Stem levels carry unrecorded gain changes.** Demucs `clip-mode rescale` scaled vocals, drums and other down. Their peaks are exactly 1/1.01 = 0.9901; bass was not scaled. Absolute RMS and band energy are therefore not comparable across stems. Least-squares estimates of the undone gains are vocals 1.023, drums 1.113, bass 1.021 and other 1.071. These are estimates, not recorded facts (`raw/stem_check.json`). Stems are sample-aligned with the mix (best lag 0, equal lengths). The sum of the stems leaves a residual of −21.7 dB relative to the mix.
4. **Rhythm metadata is coarse.** `bpm` = 125.0 comes from the median inter-beat interval on Beat This!'s 20 ms grid. The mean interval gives 127.27 BPM, which matches Lane A's 127. `time_signature` = 6/4 because `export_contract` takes max(beat_positions), and four bars with missed downbeats reach positions 5 and 6. The track is 4/4. Twenty-nine intervals of 0.36–0.38 s suggest extra beats. Do not drive anything from `bpm` or `time_signature` without checking.
5. **The shared Trinity environment cannot run Trinity.** `~/miniforge3/envs/trinity-music-intent-v0_1` has three faults:
   - natten 0.21.7 fails to import with torch 2.2.2 (`custom_bwd`).
   - torch was overwritten by the pip wheel, which bundles its own OpenMP. With numpy imported first, Beat This! segfaults. Two OpenMP runtimes load even when torch is imported first.
   - allin1 is installed editable from an old tree (`SpectraSynq.trinity/Trinity_v0.1`).
   
   Fix used, following Trinity's own install docs, in a lane-local prefix `conda-env/`:
   - cloned the env, removed the pip leftovers, and force-reinstalled pytorch 2.2.2 and torchaudio 2.2.2 from the pytorch channel (no OpenMP);
   - replaced natten with natten 0.15.1 plus `patch_natten_cpu.py`;
   - imported allin1 from the locked checkout via `PYTHONPATH`.
   
   Exactly one OpenMP runtime is loaded (`raw/env_openmp_check.log`). The shared env was not modified.
6. **Other limits.**
   - Rhythm runs on CPU, because torch 2.2.2 MPS lacks `aten::_fft_r2c` (Trinity's macOS default of MPS fails).
   - natten 0.15.1 came from the cached wheel compiled against the pip build of torch 2.2.2. It is the same version and links only libtorch, and allin1 output was identical across runs, but it was not rebuilt against the conda build.
   - allin1 warns that the filterbank produced 83 bins where 81 were expected and truncates them (fork's madmom replacement).
   - Trinity's own guards are broken: `guard_deps.py` has an unpack error and `check_versions.py` cannot parse "2.2.2" (`raw/env_gates.log`).

## What ran

`conda-env/bin/python tools/run_m2a.py` runs these stages:

1. Decode with ffmpeg 9.0.2 to s16 WAV: 44,100 Hz, 2 channels, 9,874,432 frames, a delta of 0 against the brief; no resample, trim or normalisation.
2. Trinity `analyze_track.py`: Demucs htdemucs, then Beat This! final0 (dbn off, CPU), then allin1-trinity harmonix-all (8 folds, CPU).
3. Trinity `stem_features.write_stem_features`: 50 frames per second, n_fft 2048.
4. Trinity `export_contract` at tier k1-lite.

Settings: `HF_HUB_OFFLINE=1` and no network; all weights came from local caches. Downloads: natten 0.15.1 sdist (PyPI, 1.9 MB), torchaudio-2.2.2-py311_cpu (conda.anaconda.org/pytorch, 4.9 MB, sha256 `dfc00f8f…25db3`), and jsonschema 4.23.0 for the validator venv. In total about 10 MB, within the 3 GB allowance.

Trinity checkout `/Users/spectrasynq/Workspace_Management/Software/Trinity` is at **e271af39, which matches the lock**, and its working tree is clean. Model sha256 values are in `out/loreen/identity.json`:

| Model | sha256 prefix |
|---|---|
| beat_this final0 | `8c328b45…` |
| htdemucs 955717e8 | `8726e21a…` |
| allin1 folds 0–7 | listed in `identity.json` |

## Artefacts (`out/loreen/`)

| File | sha256 |
|---|---|
| contract.json (raw Trinity) | 18581f4c34cd59db80fa79ecda2dfb81172f13087111de96f2e54f62e396fe56 |
| stem_features.json | 9053c7ad7e62e92b88b684b5daff07818039f46fdc46b0623a9ce60d31386052 |
| analysis.json | 85373cbb317bd05e793b620c080787148f4decf60c63d707b21a45d29e78e0a3 |
| identity.json | a9e53f64a3cc0a948db29104470aaa721c73b4f9d5a8218705df379dee0f2ada |
| evidence_semantics.json | 5cf857b39c3b9065e8e782e3078009aecaa1333af12e9536d9107903d497cc02 |
| consumer/contract.json (clamped) | f17a0c052f6ba03b51d6820a596df6f55a06ce3f42e1e59e7cf06a705909e793 |
| consumer/corrections.json | 818e6ba8a93c8c7d81db692e459bc317629f0a15d2f2bbd395b3f96c25617304 |
| passage_75_155/contract.json | c15659a743ffd58f9101ff91c72e11f31a91f5fa2ee140bacf57dd41e0803e6f |
| passage_75_155/stem_features.json | 01f3e7c2c63049d95f07e406c2c960a0497619019b43e75748c53e3167d0e603 |

Content:
- Full track: 462 beats, 131 downbeats and 15 segments; the chorus to bridge boundary is at 136.39 s, against the designated transition at 137 s. The stem features have 11,194 frames.
- Passage view: a slice of 4,000 frames (frames 3750–7750, asset-anchored, 75 s = frame 3750 exactly) with times rebased to −75 s. Onset scaling stays at the whole-track scale.
- `evidence_semantics.json` records, for each feature, units, range, resolution, normalisation scope, smoothing and delay. It also lists every feature that was not produced, so none appears as zeros.
- Time-alignment flag for M2-compose: a stem-feature frame is stamped at its start sample but covers the next 46.4 ms. No compensation is applied anywhere.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| Full artefacts exist | PASS | `out/loreen/` |
| Contract against Trinity `contract_schema.json` (sha `3d521f5d…`, equal to the Spine pin) | PASS (raw, consumer and passage) | `M2A-validation.json` |
| Contract semantic facts | FAIL on the raw contract (segment end beyond duration); all other facts PASS | `M2A-validation.json` |
| PRISM adapter (`.g5r-clean/PRISM.studio` 07eb8227) | raw: FAIL; consumer: PASS; passage: PASS | `raw/compile/*/consumer_check.json` |
| Locked compiler CLI v0.3, profile prim8_natural_v1 1.0.0 | raw: FAIL; consumer: PASS (showbundle `cae4fbc1…`); passage: PASS (showbundle `f1ce28a2…`) | `raw/compile/*/` |
| Second invocation is a cache hit | PASS (HIT, 0.5 s, no analysis) | `raw/run5_warm.log`, `raw/run6_warm_*.log` |
| Byte-identical artefacts, cold to warm and warm to warm | PASS (all `out/` files) | `raw/hashes_run4_cold.txt` = `raw/hashes_run5_warm.txt`; `raw/hashes_run6_1.txt` = `raw/hashes_run6_2.txt` |
| A13: cold preparation at most 2× real time | PASS: 347.3 s for 223.9 s of audio = **1.55×**; peak RSS 3.23 GB; cache 391 MB | `identity.json` timing, `raw/run4_cold.log` |
| Same result from source on a second cold run | FAIL for stems and stem features (Problem 2); PASS for rhythm and structure | `raw/cold_vs_cold_stems.log` |

## Organ identity notes

- Spine `organs.lock.json` pins PRISM `cc00556d`. Spine `c1_qualify.mjs` hard-codes `07eb8227`, and the `.g5r-clean/PRISM.studio` checkout it resolves is at `07eb8227`. That checkout's git alternates point at a missing `PRISM.studio/.git/objects`, so ancestry cannot be checked.
- Spine `organs.local.json` resolves Trinity to `.g5r-clean/Trinity`, which is also at e271af39.
- Nothing was repinned or edited in Trinity, Spine or PRISM.

## Reuse

- Warm call: `conda-env/bin/python tools/run_m2a.py` (cache hit), then `venv-validate/bin/python tools/validate_m2a.py`, then `node tools/consumer_check.mjs consumer|passage_75_155`.
- The cache key covers the asset hash, decoder and its arguments, the Trinity commit, every model sha256, package versions, torch/natten/libomp binary hashes and every parameter. Key material: `cache/trinity/<key>/key.json`.
- A palette or curve edit downstream touches none of these, so it reuses the cache.

| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (m2-analysis) | Created. |
