---
abstract: "Post-graft validation package for the audio semantic forward-graft (branch wip/audio-saliency-recovery, HEAD 3d16024). Deterministic reviewability surface: reproduced host metrics (baseline vs final), a notebook-first diagnostic workbook (notebooks/audio_semantic_diagnostics.ipynb) that consumes canonical harness artifacts only (NO DSP in notebook), exported HTML snapshots, an AP_STREAM ingestion path + exact capture procedure, and a single consolidated ONE FINAL HUMAN CHECK. No DSP behaviour changed. The forward-graft itself is recorded in 2026-06-05-audio-semantic-forward-graft.md (§7); this memo is reviewability + device-truth only."
---

# Audio Semantic Forward-Graft — Post-Graft Validation Package

**Purpose:** make the final human/device check happen **once**, with all evidence in one place. This is a validation/reviewability package — **not** more implementation. Hard scope: no DSP-constant tuning, no threshold lowering, no onset→flywheel rewire, no pre-AGC path, no Director wiring, no algorithm changes unless reproduction proves the ledger false. Host harness = source of truth; the notebook is a display-only diagnostic surface.

Companion (the graft itself): `docs/forensics/tempo_tracking_refactor/2026-06-05-audio-semantic-forward-graft.md`.

## Step-tracker (living)
| Step | Title | Status |
|---|---|---|
| 1 | Verify repo state | **DONE** (§1) |
| 2 | Reproduce host evidence | **DONE** (§2) — 136 pytest, build SUCCESS, all metrics reproduce |
| 3 | Notebook-first diagnostic workbook | **DONE** (§3) — 28-cell notebook, 12 sections, 12 trajectories |
| 4 | Export executed HTML snapshots | **DONE** (§4) — 3 HTMLs; notebook executes 0-error |
| 5 | AP_STREAM ingestion + procedure | **DONE** (§5) — ingester + full capture procedure |
| 6 | ONE FINAL HUMAN CHECK | **DONE** (§6) — consolidated; flash already done, eyes-on + AP_STREAM capture pending |

---

## 1 · Repo state (verified 2026-06-05)

- **Branch:** `wip/audio-saliency-recovery`
- **HEAD:** `3d16024` (`chore(bench): 2nd bench K1 moved port 1401->2101; flash forward-graft`)
- **Forward-graft commits present:** `5808e3b` (P0+1) · `fa8a6cf` (P2 conf) · `d953a72` (P3 flywheel+3× fix) · `593b5d2` (P4 onset) · `5e4d27f` (P5 chord) · `d3c5469` (P6+7 spine+rate) · `4e96e30` (P8 promotion) · `f794eb0` (ledger) · `3d16024` (port move + flash).
- **5 V2 flags LIVE in `[env:k1_hardware]`** (`platformio.ini:57-61`): `SB_TEMPO_CONF_V2`, `SB_TEMPO_FLYWHEEL_V2`, `SB_ONSET_V2`, `SB_CHORD_V2`, `SB_SEMANTIC_STATE`.
- **Device:** flashed 2026-06-05 to the 2nd bench K1 on `/dev/tty.usbmodem2101` (USB serial `B4:3A:45:A5:87:F8`, chip `F887A500`, MAC `b4:3a:45:a5:87:f8`), guard-verified, all hashes verified, hard-reset (see graft ledger §7).
- **Working tree:** clean w.r.t. graft/validation work. Pre-existing untracked/dirty unrelated to this task: `docs/measurements/tempo-octave-baseline.{md,tracks.csv}` (modified), `docs/_scratch/`, `SPECTRASYNQ_K1_FIRMWARE/light_mode_waveform_tempo.cpp.wip`, and the `docs/forensics/2026-06-04-*`/`tempo_tracking_refactor/*.h|cpp` snapshots — left untouched.
- **Rate facts (for notebook provenance):** AP frame rate `12800/96 = 133.33 Hz`; tempo novelty decimation `/3` → `44.44 Hz`; onset/saliency run every AP frame (133.33 Hz). Corpus: `Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8/*.wav` (36, 12.8 kHz). GT: `/Users/spectrasynq/Workspace_Management/Software/K1.reinvented/Implementation.plans/harmonixset-main/dataset/` (`metadata.csv` BPM, `beats_and_downbeats/*.txt`).
- **Tooling:** harness Python `/opt/homebrew/bin/python3` (numpy/scipy/matplotlib ✓; **pandas/soundfile ✗** — avoid). Jupyter+nbconvert in `~/miniforge3` (notebook execution kernel — see §4).

---

### 1.1 · Provenance reconciliation (HEAD-mismatch resolved 2026-06-05)
- **Validation base HEAD:** `3d16024` — the forward-graft + flash state the validation ran against (the memo skeleton + the first trajectory export were stamped here).
- **Final package HEAD:** `fb83bd1` — the commit that *added the validation package itself* (notebook + helpers + scripts + memo + guard-test fixture fix; 8 files, 2016 insertions, **zero firmware**). HEAD is currently `fb83bd1`.
- **DSP changed between them?** **NO.** `git diff 3d16024..fb83bd1 -- SPECTRASYNQ_K1_FIRMWARE/` is empty; the range touches only `notebooks/`, `scripts/regression-harness/`, this memo, and `tests/test_k1_upload_guard.py`.
- **Why report vs memo HEAD differed:** the final report cited the post-commit HEAD (`fb83bd1`); the memo skeleton's §1 was stamped at the pre-commit base (`3d16024`). Both correct, different reference points. The HTML snapshots were **regenerated at current HEAD**, so they now stamp `fb83bd1` — memo, manifest, report, and HTML all agree, with `3d16024` documented as the zero-DSP-delta base.

---

## 2 · Reproduced host evidence

**Tests/build:**
- **pytest: 136 passed.** This required a narrowest correction: 3 `tests/test_k1_upload_guard.py` fixtures still asserted the old port `usbmodem1401`, but the 2nd-bench K1 moved to `usbmodem2101` in commit `3d16024` (guard *config* was updated there, its *tests* were not). Fixed the test fixtures `1401→2101` (test-only; no guard-logic / no DSP change). Reconciles the ledger's "136 passed".
- **Production build `pio run -e k1_hardware`: SUCCESS** — RAM 29.4% (96232 B), Flash 9.2% (599890 B); V2 path confirmed (all 5 flags in `[env:k1_hardware]`).
- **No DSP/algorithm files changed** — `git diff --stat SPECTRASYNQ_K1_FIRMWARE/` empty.

**Reproduced metrics — baseline → final (all within tolerance of the graft ledger §7; `final.json/md` generated = CONF_V2+FLYWHEEL_V2):**

| Metric | Ledger | Reproduced | ✓ |
|---|---|---|---|
| tempo conf median settled | 0.041→0.620 | 0.0407→0.6204 | ✓ |
| in-range tracks sustaining lock ≥0.60 | 0/32→17/32 | 0/32→17/32 | ✓ |
| white-noise false-lock (frac@maxconf) | 0.014@1.0→0@0.530 | 0.0141@1.000→0.0000@0.5303 | ✓ |
| beat_tick density-in-band | 5.6%→97.2% | 5.56%→97.22% | ✓ |
| phase-continuity (ibi) | 0.156→0.494 | 0.1560→0.4939 | ✓ |
| per-beat precision (x1) | 0.099→0.300 | 0.0988→0.2982 | ✓ |
| tempo Acc1/Acc2 in-range | 56.2/56.2 unchanged | unchanged | ✓ |
| onset AGC-survival (onsets/min) | 115→923 | 115.4→923.1 | ✓ |
| harmonic axis (smoothed peak) | 0.0→0.285 | 0.000→0.2846 | ✓ |

**No material discrepancies.** Notes: `median_max_conf` 1.000→0.962 (expected — V2 EMA no longer transient-spikes); `beat_F_x1` flat 0.031→0.026 (the documented **front-end cap**, graft ledger §2.7 — novelty alignment bounds recall for both arms, not a regression). **Artifacts:** `build/audio-semantic-metrics/{baseline,final}.{json,md}`, `onset_v2_ab.json` (P/R-proxy F1 0.031→0.098; AGC-clamp 115→923/min), `chord_v2_ab.json` (chord 6/6; harmonic 0.0→0.285).

---

## 3 · Notebook-first diagnostic workbook

**Notebook:** `notebooks/audio_semantic_diagnostics.ipynb` (28 cells, nbformat 4). Display-only diagnostic surface — **reimplements no DSP**; every numeric field comes from the compiled, unmodified firmware (`sb_tempo.cpp`/`sb_onset_beat.cpp`) replayed through the existing harness, then loaded as artifacts. Only presentation is computed in-notebook (FP/miss markers, tolerance bands, novelty normalization, beat raw-vs-dedup). Helper: `notebooks/diag_helpers.py` (load+plot; numpy + matplotlib + stdlib `wave`/`json` only — no pandas/soundfile).

**12 sections (verified rendered):** 1 Provenance · 2 Track metadata + waveform · 3 Modelled front-end novelty · 4 AP_STREAM overlay · 5 Tempogram/ACF/comb heatmap (from the `RAWSPEC` tempogram artifact) · 6 BPM vs GT · 7 Confidence + lock overlay · 8 Predicted `beat_tick` vs GT (tolerance band, FP, miss, density) · 9 Onset channels (transient/kick/snare/hihat) · 10 Harmonic/chord state · 11 A/B comparison · 12 Interpretation.

**Controls (parameters cell, papermill-tagged):** `TRACK_ID`, `RUN_MODE ∈ {baseline,final,ab}`, `TIME_WINDOW_S`, `BEAT_TOL_MS`=70, `SHOW_GT`, `SHOW_BEAT_TICK`, `SHOW_APSTREAM`, `APSTREAM_PATH`, `CONF_RAW_VS_SMOOTH`, `BEAT_RAW_VS_DEDUP`, `NORMALIZE_NOVELTY`. **Forbidden tuning controls (confidence threshold, PLL Kp/Ki, onset threshold, refractory, prior width, scoring weights) are deliberately absent** — diagnostic surface, not a tuning playground. Mandatory caption present on every host-modelled plot (`MODELLED FRONT-END / HOST CEILING — not guaranteed to match device AP_STREAM.`); overlays label host-modelled vs device-AP_STREAM trace + match status (verified).

**Exporter:** `scripts/regression-harness/export_diagnostic_trajectories.py` → `build/audio-semantic-metrics/trajectories/<track>__<run>.json` (schema in `trajectories/SCHEMA.md`). 12 trajectories = 6 tracks × {baseline, final}, 3329 frames each; `final` carries the `RAWSPEC` tempogram (96 bins, 60–155 BPM) + V2 onset channels; `baseline` onset channels empty by design. **Curated subset (by gold genre/BPM/time-sig):** `7vevOMWY6MY` (Pop 128, clean control) · `T-sxSd1uwoU` (Dance 130, four-on-the-floor) · `c7tOAGY59uQ` (Hip-Hop 84, syncopated) · `Qa1AqKxakRM` (Pop 58, half-suspect + below-range) · `r9DBFTZTKPI` (Pop 80 6/8, half-suspect + compound) · `WxnN05vOuSM` (Metal 200, loud clamp-stress + super-octave).

**Documented limitation:** per-track chord *events* are `[]` — deriving per-track chords from audio would be DSP reimplementation (forbidden); section 10 sources harmonic/chord state from `chord_v2_ab.json` (clearly labelled synthetic-fixture A/B). Onset per-band channels are V2-only (populated for `final`, empty for `baseline`).

---

## 4 · Exported HTML snapshots

Three executed snapshots (each ~336 KB, 100 embedded base64 PNG figures), under `build/` (gitignored — on-disk, reproducible, not committed):
- `build/audio-semantic-visuals/baseline/index.html`
- `build/audio-semantic-visuals/final/index.html`
- `build/audio-semantic-visuals/ab_diff/index.html`

**Notebook executes end-to-end:** verified via `nbconvert --execute` → 0 error outputs, all 12 sections rendered.

**Export commands.** The two stock Python envs lacked a usable Jupyter kernel (miniforge base: no numpy/ipykernel; homebrew: no nbconvert), so the preferred path registers a numpy+matplotlib+ipykernel kernel (here the `nerfstudio` conda env as `nerf-diag`) and injects `RUN_MODE`/`TRACK_ID` by rewriting the `parameters` cell (papermill mechanism, no papermill dep):
```
~/miniforge3/bin/python3.12 scripts/regression-harness/render_via_nbconvert.py --kernel nerf-diag --track 7vevOMWY6MY
```
**Guaranteed-reproducible fallback** (no Jupyter kernel needed — runs the same `diag_helpers` logic under the harness Python and writes the 3 HTMLs directly):
```
/opt/homebrew/bin/python3 scripts/regression-harness/render_diagnostics.py
```
Both paths were exercised and produce the same 3 files. **For re-rendering on a clean machine, prefer the fallback** (`render_diagnostics.py`) — it only needs numpy+matplotlib (present in the harness Python) and no kernel registration.

---

## 5 · AP_STREAM ingestion + capture procedure

**Ingestion (exists):** `scripts/regression-harness/apstream_ingest.py` → `load_apstream(path, track_id=None)` returns a device trajectory `{source:'apstream', t_ms[], bpm[], conf[], lock[], phase[], beat[], bstr[], onset[], bass[], ostr[]}` in the same frame convention as the host trajectories, or `None` if the file is absent. Robust: per-token key=value parse; malformed lines skipped + counted (`n_skipped`); unknown/missing expected keys → non-fatal deduplicated `warnings`. The notebook (§3, section 4) overlays it on the host-modelled trajectory when `SHOW_APSTREAM=True` + `APSTREAM_PATH` is set, clearly labelling host vs device traces + match status.

**Source line** (`[AP]`, ~1 Hz, 115200 baud) — emitted by `i2s_audio.h`, runtime-gated by `AP_STREAM_ENABLED` (**default `true` in the production `k1_hardware` build — already flashed; no reflash needed**):
```
[AP] SSL=.. DC=.. max_raw=.. follower=.. peak_scaled=.. silent_scale=.. silence=.. cal_source=.. cal_valid=.. | bpm=.. conf=.. lock=.. phase=.. beat=.. bstr=.. | onset=.. bass=.. ostr=..
```
**Caveats (load-bearing):** the 1 Hz cadence under-samples the ~133 Hz beat phase — it is reliable for the **conf / lock / bpm / onset trend**, but NOT for per-beat phase alignment (the **host model remains the per-beat arbiter**). Chord and per-band onset (kick/snare/hihat) are **not** in the `[AP]` line.

### AP_STREAM capture procedure (the human runs this during the eyes-on; missing captures are not a blocker)
1. **Identify the target by stable identity, not port name.** `pio device list` → confirm the K1 shows `SER=B4:3A:45:A5:87:F8` (chip `F887A500`, MAC `b4:3a:45:a5:87:f8`). Note its current `/dev/cu.usbmodem*` port (was `2101`; re-verify — it may move again). Do **not** capture from a port whose serial you have not confirmed.
2. **Start capture** (production firmware already emits `[AP]`; the toggle just guarantees it). In one terminal:
   ```
   PORT=/dev/cu.usbmodem2101   # ← the port whose SER you confirmed == B4:3A:45:A5:87:F8
   mkdir -p build/audio-semantic-metrics/apstream
   ( printf ':ap_stream=on\r\n' > "$PORT" ) ; \
   pio device monitor --port "$PORT" -b 115200 --quiet \
     | grep --line-buffered '^\[AP\]' > "build/audio-semantic-metrics/apstream/<TRACK_ID>__device.aplog"
   ```
   Start this the moment the track begins; Ctrl-C when it ends.
3. **Save location:** `build/audio-semantic-metrics/apstream/` (gitignored; local evidence).
4. **Naming convention:** `<TRACK_ID>__device.aplog` (use the same `track_id` as the corpus/trajectory, e.g. `7vevOMWY6MY__device.aplog`). One file per track.
5. **Associate with `track_id`:** the filename IS the association; also note the played track + wall-clock start in the failure log (§6.8) if relevant.
6. **Load into the notebook overlay:** set `SHOW_APSTREAM=True`, `APSTREAM_PATH="build/audio-semantic-metrics/apstream/<TRACK_ID>__device.aplog"`, `TRACK_ID="<TRACK_ID>"`, then re-run the notebook (or `render_diagnostics.py`). Section 4 overlays the device trace on the host model with a `MATCHED`/`NOT matched` label.
7. **Minimum expected fields:** `bpm conf lock phase beat bstr onset bass ostr` (the tempo + onset groups). The SSL/DC front group is ignored.
8. **If the stream schema differs from expectation:** `apstream_ingest.load_apstream` will not crash — it parses what it recognises, drops unknown tokens, and emits `warnings`. If `bpm`/`conf`/`lock` are entirely missing (e.g. a firmware build without the V2 tempo fields), the overlay is skipped and the notebook shows "device capture present but schema mismatch — see warnings"; fall back to the host-modelled trajectory and record the mismatch in §6.8.

---

## 6 · ONE FINAL HUMAN CHECK

This is the **only** place human action is requested. Everything above is host-validated and reproducible; the remaining truth is on the device.

1. **Open the notebook** (live, interactive controls): `notebooks/audio_semantic_diagnostics.ipynb` — set `TRACK_ID`/`RUN_MODE` and explore. (Render a fresh copy any time: `python3 scripts/regression-harness/render_diagnostics.py`.)
2. **Open the executed snapshots:** `build/audio-semantic-visuals/final/index.html` and `build/audio-semantic-visuals/ab_diff/index.html`.
3. **Verify target identity** (not port name alone): `pio device list` → confirm `SER=B4:3A:45:A5:87:F8` (chip `F887A500`, MAC `b4:3a:45:a5:87:f8`); note its current `usbmodem` port.
4. **Flash** — *already done* 2026-06-05 (the device is running the forward-graft). Re-flash only if needed: `pio run -e k1_hardware -t upload` (the env builds the V2 path; the guard re-verifies the serial).
5. **Play 3–5 representative tracks:** one clear **4-on-the-floor**; one **syncopated**; one **loud passage** likely to stress onset/clamp; one **silence/noise** segment or quiet intro/outro. (The notebook's curated set covers these host-side: `T-sxSd1uwoU` 4-on-floor, `c7tOAGY59uQ` syncopated, `WxnN05vOuSM` loud.)
6. **Confirm:**
   - beat phase visually **tracks the music**, not metronome drift;
   - beat-reactive effects **fire and sustain** on real music;
   - beat-reactive effects **stay quiet** on silence/noise;
   - onsets feel **transient/percussive, including loud passages**;
   - **no obvious regression** versus the current look;
   - harmonic response is **not** expected to be visible (no consumer wired — `SB_CHORD_V2`/`SB_SEMANTIC_STATE` are inert).
7. **Capture AP_STREAM** during ≥1 representative track (procedure §5) → `build/audio-semantic-metrics/apstream/<track_id>__device.aplog`, then load it into the notebook (`SHOW_APSTREAM=True`, `APSTREAM_PATH=…`) to compare device conf/lock/bpm trend vs the host model.
8. **For any failure, record:** `track_id` · timestamp · symptom · whether AP_STREAM was captured · whether rollback was needed · category = {host/device-front-end · beat-emission · onset · consumer/effect}. (The category points at the fix lane: front-end → novelty/AGC path; beat-emission → flywheel; onset → SB_ONSET_V2; consumer/effect → Director wiring, out of scope here.)
9. **Rollback (one line, recoverable):** delete the 5 `-D SB_*` lines in `platformio.ini` `[env:k1_hardware]` (lines 57-61); `pio run -e k1_hardware -t upload` to restore legacy (legacy lives under `#ifndef SB_*_V2`). **Preserve the failing `.aplog` / serial log** for diagnosis before rolling back.

## 6.1 · DEVICE-TRUTH — live AP_STREAM on real music (2026-06-05)

Run live with Captain playing music; AP_STREAM captured on the flashed device (`/dev/cu.usbmodem2101`, SER `B4:3A:45:A5:87:F8`, 115200, ~1.6 Hz). **The host ceiling did NOT hold on device — a reproducible 3:2 tempo-selection error:**

| true BPM (external) | device bpm | ratio | device conf (med) | lock | level (peak) |
|---|---|---|---|---|---|
| 127 | 83 | ≈2/3 | 0.06 | 0% | low (~0.05–0.10) |
| 123 (4-on-floor) | 82 | ≈2/3 | **0.94** | **47%** | strong (0.48) |

**Finding:** both real tracks tracked **2/3 of the true tempo** (3:2 metrical error: 127→83, 123→82). On the loud 4-on-the-floor it was **confidently wrong** (conf 0.94, locks) → effects fire at the wrong tempo (82 vs 123).

**Attribution (diagnosed, NOT fixed — out of this validation's scope):**
- The error is in the **PRESERVED tempo selection** (harmonic-comb ACF + **88-BPM tactus prior**), which the graft deliberately did not change (Acc1/Acc2 56.2 held) → the graft did **not cause** it.
- 82 sits at the 88-BPM prior peak; 123 is ~0.5 oct away → the prior plausibly pulls fast dance tempos down to 2/3; the device's AGC-clamped novelty (ON-02) likely compounds it. 3:2 is NOT an octave, so the octave defence doesn't catch it.
- **Second-order:** the V2 confidence fix WORKED (asserts 0.94/locks on the clean 4-floor) and in doing so **unmasked** the pre-existing 3:2 selection error — floored incumbent confidence used to hide the wrong tempo by never firing. **The next constraint is device tempo SELECTION, not the confidence metric.**

**Step-9 classification:** device FAILURE = **tempo-selection / front-end** (3:2 on 120+ BPM). NOT a confidence-metric failure (V2 works). **Rollback would NOT fix it** (selection is identical in legacy). Fix = a NEW workstream (revisit 88-prior / device front-end / 3:2 handling), out of scope here. Captures: `build/audio-semantic-metrics/apstream/{_live_music,_4floor}__device.aplog`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:Orchestrator | Created — post-graft validation package skeleton; Step 1 repo state verified (HEAD 3d16024, 5 flags live, device flashed on 2101). |
| 2026-06-05 | agent:Orchestrator | Completed Steps 2–6. Reproduced all 9 ledger metrics within tolerance; pytest 136 (fixed 3 stale guard-port fixtures from the device move); build SUCCESS. Built notebook-first diagnostic workbook (`notebooks/audio_semantic_diagnostics.ipynb` + `diag_helpers.py`), trajectory exporter (12 trajectories, 6 tracks), AP_STREAM ingester + capture procedure, 3 executed HTML snapshots. No DSP changed. ONE FINAL HUMAN CHECK = eyes-on (device already flashed) + AP_STREAM capture. |
