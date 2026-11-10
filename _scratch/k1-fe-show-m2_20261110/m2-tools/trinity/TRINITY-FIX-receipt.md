---
abstract: "TRINITY-FIX receipt (10 Nov 2026): Trinity branch fix/reproducible-contract (0cfa247 on e271af3) makes the Loreen analysis reproducible from source, so two cold runs are byte-identical on the excerpt and on the full track. The raw contract passes Trinity's schema and PRISM cc00556d's adapter and compiler with no correction layer. Tempo now reads 126.99 BPM and the metre 4/4, and the unsteady intro is flagged. A pinned environment spec was proven by creating a new env from it. Network use went over budget (about 86 MB)."
---

# TRINITY-FIX — receipt

## Problems first

1. **Network budget overrun.** Building the new environment downloaded about 86 MB against the 50 MB cap. The `cmake 3.20.3` pip wheel alone was 70.8 MB; pip did not use its HTTP cache on the first attempt. Every item is listed under "Network" below. `cmake` is only a natten build tool. It stays in the lock because the working env had it, and the wheel is now in the local pip cache.
2. **Beat This! can no longer be installed from its URL.** The working env came from `github.com/CPJKU/beat_this/archive/main.zip` with sha256 `dae12218…4734`. Today that URL serves `917267cf…dca0`, and the hash-pinned install failed (`raw/env_create_attempt2_failed_beat_this_hash.log`). Fix: `rebuild_beat_this_wheel.py` rebuilds the wheel from the installed files after checking each one against its RECORD hash. The result is `wheels/beat_this-0.1-py3-none-any.whl` with sha256 `e55b64a1…8937`, and two rebuilds were identical. Both supplied wheels (this one and natten) live in this lane folder, not in git.
3. **Tempo is 126.99 BPM, not the brief's 127.27.**
   - 127.27 is the mean of all 461 intervals. That mean is pulled up by the intro's extra beats (intervals of 0.34–0.40 s).
   - The steady runs measure 126.99 BPM: 401 beats over 3 runs, pooled slope.
   - Other measures for comparison: the mean of the in-tolerance intervals alone is 127.08, and the 20 ms-grid median is 125.0.
   - Lane A heard 127. The field states `method`, `reliable` and `median_ibi_bpm`.
4. **The 18–30 s downbeats are flagged, not repaired.**
   - The drums stem is near-silent from 8 to 30 s (RMS 0.001, against 0.10 after 31 s). Beat This! follows the vocal and pad onsets there, at about 0.37 s per beat (158 BPM), not the song's 0.472 s.
   - The beats themselves are wrong in that span. A rule that only respaces downbeats to bar length would just lay out bars of wrong beats, so I did not implement one.
   - The flagged regions are 0.36–6.0 s, 7.9–30.58 s and 147.76–149.64 s. The last is one 3-beat bar after a missed beat.
   - All 17 downbeats in 18–30 s are inside a flag, and 97 of 131 downbeats lie outside any flag. Downbeats are emitted unchanged.
   - Note: these "downbeats" come from Beat This!, not allin1.
5. **Stems differ from the M2A cache.** Expected: the M2A stems were made with an unseeded random shift. Beats and downbeats are identical to M2A. Four segment boundaries moved by 10 ms (one allin1 frame), because allin1 runs on the stems. The chorus-to-bridge boundary stays at 136.39 s.
6. **Latent defect, reported and not fixed:** `export_contract` takes the WAV path from `analysis.json` ahead of `--audio`. If that file has moved, the duration silently falls back to the last segment end and no clamp happens. `reexport.sh` works around it.
7. **Contract version stays 1.0.0,** although Trinity's CLAUDE.md asks for a bump on contract edits. PRISM's adapter accepts only `1.0.0`, and every addition is optional under the unchanged schema (sha256 `3d521f5d…`, equal to the Spine pin).

## What is true now

- **Branch** `fix/reproducible-contract` in `/Users/spectrasynq/Workspace_Management/Software/Trinity`. Commits `144b29a` (the fixes), `14f207d` (metre counts only steady bars) and `0cfa247` (changelog). Not pushed. `main` is untouched. The `.g5r-clean` copy, Spine, PRISM and the shared conda env were not touched.
- **Defect 1 (stems).** Demucs always gets an explicit `--shifts N` and runs through `analysis/demucs_seeded.py`, which seeds Python, NumPy and torch (`--demucs-seed`, default 0) and refuses an implicit shift count. Two cold runs, each decoding from the MP3 and analysing from source, gave byte-identical files:

  | View | Time per run | Identical files (sha256) |
  |---|---|---|
  | 0–45 s excerpt | 79 s | decode, 4 stems, stem_features `664aee70…`, analysis, contract |
  | Full track | 460–500 s | decode (= M2A's `b3fafd33…`), vocals `b65567fe…`, drums `208a617a…`, bass `2ddfdac0…`, other `c5a1cd1d…`, stem_features `1e5d954c…`, analysis, contract |

- **Defect 2 (segment end).** The last segment end of 223.92 s is clamped to 223.910023 s at export and recorded in `structure.clamps` (delta −9.98 ms). An overrun larger than 0.05 s raises an error.
  - Raw full contract with final code: `runs/full_A/contract_14f207d.json` (sha256 `23c345c2…`, the same from run B).
  - Trinity schema: PASS.
  - PRISM cc00556d adapter: PASS (462 beats, 131 downbeats, 15 segments, last end 223,910,023 µs).
  - Locked compiler v0.3 with profile prim8_natural_v1: PASS (showbundle `bab35502…`).
  - Control: the old raw M2A contract still FAILS the same adapter with "segments[14] times must lie within".
- **Defect 3 (tempo and metre).** `bpm` 126.985 (rounded 127). `time_signature` 4/4, basis steady_bars, support 0.98 over 100 bars, `reliable: true`. The old export gave 125 and 6/4. On the excerpt alone, the old median method would have said 136 BPM; the new code says 127.17 and 4/4.
- **Defect 4 (downbeats).** Diagnosed and flagged in `rhythm.low_confidence_regions` (see problem 4).
- **Defect 5 (environment).**
  - Committed spec in `analysis/environment/`: a conda explicit list (187 packages, URL plus md5), `pip-lock.txt` (`--no-deps`), `create_env.sh`, `check_env.py` and `README.md`.
  - A NEW env `m2-tools/trinity/env-trinity-repro-20261110` was created from the spec. Its check passed: torch, torchaudio and natten at the pinned versions, torch not a pip wheel, exactly one OpenMP runtime with numpy imported first, and allin1 from the checkout.
  - Every test and every cold run above used this new env.
- **Tests.**
  - Branch: 76 passed (`raw/pytest_branch_final.log`).
  - The same new test file against an e271af3 export: 9 of its 10 tests fail, each for the defect it targets (`raw/pytest_e271af3_with_new_tests.log`). The tenth guards that contract version 1.0.0 is kept.

## Evidence (all under `m2-tools/trinity/`)

| What | Where |
|---|---|
| Cold-run records (head, clean tree, hashes, timing, RSS) | `runs/{excerpt,full}_{A,B}/run.json`, `raw/cold_runs.log` |
| Byte comparisons and schema checks | `raw/compare_excerpt.json`, `raw/compare_full.json`, `raw/contract_facts_14f207d.log` |
| Consumer checks | `runs/full_A/consumer_contract_14f207d/consumer_check.json`, `raw/consumer_full_A_14f207d.log`, `raw/consumer_excerpt_A_14f207d.log`, `raw/consumer_control_m2a_raw.log` |
| Re-export with final code | `reexport.sh`, `raw/reexport_14f207d.log` (contract is a pure function of analysis.json and the WAV) |
| Environment build | `raw/env_create.log` (success), `raw/env_create_attempt2_failed_beat_this_hash.log` |
| PRISM files used | `prism_cc00556d/` (`git archive cc00556d` of the locked clone; read-only copy) |

## Re-run commands

```bash
T=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-tools/trinity
E=$T/env-trinity-repro-20261110/bin/python
V=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-analysis/venv-validate/bin/python
cd /Users/spectrasynq/Workspace_Management/Software/Trinity/analysis && PYTHONPATH=vendor/allin1/src:. $E -m pytest -p no:cacheprovider
cd $T && $E run_cold.py excerpt C && $E run_cold.py excerpt D && $V compare_runs.py runs/excerpt_C runs/excerpt_D
cd $T && $E run_cold.py full C && node consumer_check.mjs runs/full_C     # ~8 min; compare to runs/full_A with compare_runs.py
# New env from the spec (refuses an existing prefix):
TRINITY_CONDA_EXTRA_PKGS=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-analysis/cache/conda-pkgs \
  /Users/spectrasynq/Workspace_Management/Software/Trinity/analysis/environment/create_env.sh <new-prefix> $T/wheels
```

Labels in `run_cold.py` are single-use. Runs made with a later commit write that commit's contract directly.

## Network (each item)

- **Attempt 2, PyPI, about 80 MB:** cmake 3.20.3 (70.8 MB), Cython 3.2.4 (3.0 MB), hf_xet (2.7 MB), demucs sdist (1.2 MB), huggingface_hub (0.53 MB), plus about 1.4 MB of small wheels and sdists.
- **GitHub:** beat_this main.zip (5.0 MB), rejected on hash.
- **Attempt 3:** pytest, pygments, pluggy and iniconfig (1.6 MB). Everything else came from cache.
- **Conda:** offline, from local caches.
- **Models:** Hugging Face offline (`HF_HUB_OFFLINE=1`).

## Ship path

1. Done: the branch and its evidence, listed above.
2. The lead decides whether to merge `fix/reproducible-contract` into Trinity `main`. An agent never repins: the Captain or the lead repins `organs.lock.json`'s Trinity entry if wanted.
3. M2A can then drop its `consumer/` clamp layer and point at a raw contract from this branch. New stems mean new stem_features hashes for M2-compose.

| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (trinity-fix) | Partial receipt (defects 1–2). |
| 2026-11-10 | agent:claude (trinity-fix) | Final receipt: all five defects, full-track runs, consumer acceptance. |
