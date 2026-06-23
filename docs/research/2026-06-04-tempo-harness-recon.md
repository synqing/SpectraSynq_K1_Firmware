---
abstract: "T3 recon of the sb_tempo accuracy harness (2026-06-04). Documents the exact reproduce command, MEASURED current baseline (Step 2 committed state, 36-track HarmonixSet), documented pre-Step-2 baseline for reference, the ACF-ceiling target (~50% Acc2), and key gotchas (corpus path relative to repo root, clang++ build via tempo_replay.py, scipy/numpy required). Read before running or citing tempo accuracy numbers."
---

# Tempo Harness Recon — T3 (2026-06-04)

## Reproduce command

```
python3 scripts/regression-harness/tempo_accuracy.py
```

Run from the repo root (`/Users/spectrasynq/SensoryBridge-main 9`). Uses hardcoded defaults:
- **Corpus:** `Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8/` (36 WAV files, relative to repo root — verified present)
- **GT dataset:** `/Users/spectrasynq/Workspace_Management/Software/K1.reinvented/Implementation.plans/harmonixset-main/dataset/` (absolute — verified present: `index.jsonl`, `metadata.csv`, `beats_and_downbeats/`)
- Outputs: `docs/measurements/tempo-octave-baseline.md` + `.tracks.csv`

Optional flags: `--label "description"`, `--limit N` (smoke test), `--verbose`.

## Measured baseline (MEASURED — run 2026-06-04, Step 2 committed state)

| Metric | All scored (36) | In-range 60–155 BPM (32) |
|---|---|---|
| Acc1 (exact, ±4%) | 22.2% | **25.0%** |
| Acc2 (octave-tolerant, ±4%) | 27.8% | **28.1%** |
| Octave-error rate (Acc2 − Acc1) | 5.6% | **3.1%** |
| Autocorrelation ceiling (same novelty) | — | **~50% Acc2** |

Octave histogram (in-range): `off: 25, x1: 9, x1/2: 2` — dominant failure is low-bin pinning (`off`), not clean octave error.

## Documented pre-Step-2 baseline (DOCUMENTED — commit `684a547`, measured 2026-06-03)

| Metric | In-range 60–155 BPM |
|---|---|
| Acc1 | 9.4% |
| Acc2 | 15.6% |
| Octave-error rate | 6.2% |

Step 2 (log-Gaussian prior + Goertzel un-clamp to 4.0) delivered roughly 2× improvement; measured numbers above are consistent with the documented post-Step-2 values.

## Task #7 success target

**~50% in-range Acc2** — the autocorrelation ceiling on the same novelty. The ACF-salience + log-Gaussian prior hybrid (task #7) is the only architectural path the data shows reaching this ceiling. No harder numeric gate is documented in `docs/architecture/tempo-lock-hardening-plan.md` beyond "reach the ACF ceiling." The saliency uplift control cited elsewhere (+≥20 pp in-range Acc2) would also satisfy this (28% + 20 pp = 48%, near-ceiling).

## Key gotchas

1. **Build is automatic — no manual `clang++` needed.** `tempo_replay.py` compiles `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp` on first run via `subprocess`; it uses an Arduino stub header to satisfy `Arduino.h`. Rebuild triggers when the source is newer than the cached binary (in `/tmp` or similar).
2. **Dependencies:** `numpy` + `scipy` required; no `librosa`/`soundfile` (novelty_from_wav.py uses `scipy.io.wavfile` + hand-rolled spectral flux deliberately).
3. **Corpus path is RELATIVE to repo root**, not absolute — running the script from a different cwd will fail with "corpus not found".
4. **GT join is by `youtube_id`** (via `index.jsonl`), not by filename; all 36 tracks joined cleanly (`missing_gt=0`).
5. **In-range metric is the headline.** Tracks with gt BPM outside [60, 155] cannot be hit at the right octave by construction (range limit); the plan treats in-range Acc2−Acc1 as the load-bearing metric.
6. **Run time:** ~2–3 minutes for all 36 tracks on a dev machine (acceptable; no device needed).

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:T3 (claude-sonnet-4-6) | Created — recon of tempo harness, reproduce command, measured current baseline, pre-Step-2 reference, task #7 target, gotchas. |
