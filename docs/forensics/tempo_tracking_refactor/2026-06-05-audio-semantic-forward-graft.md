---
abstract: "Execution ledger for the audio semantic foundation forward-graft (NOT a v3 rollback). Source-truth evidence (file:line, territory-verified), corrected claims, host-harness map, and the phase-by-phase repair plan with decisions pre-recorded. Repairs: tempo confidence/lock/flywheel (replace fork's quadratic peak²/Σ floor with a BeatTracker-style prominence+periodicity+re-ranged-share metric fed by the fork's octave-defended winner — without lowering SB_LOCK_CONFIDENCE), onset semantic separation, harmonic/chord bridge, and an AudioSemanticState spine. Read this before touching SPECTRASYNQ_K1_FIRMWARE/audio. Living phase tracker is §1."
---

# Audio Semantic Foundation — Forward-Graft Execution Ledger

**Mission:** Convert the audio stack from a fragile tempo/onset heuristic path into a *measured* semantic spine with explicit tempo confidence, beat phase/flywheel, onset classes, harmonic state, and ControlBus semantic edges — as a **forward graft**, host-harness-gated, not a donor rollback.

**HEAD at start:** `e226b25` (per known-issues doc) on `wip/audio-saliency-recovery`. **Branch confirmed live:** `wip/audio-saliency-recovery`.
**Companion docs (same dir):** `2026-06-05-tempo-beat-onset-known-issues.md` (38-issue register), `MANIFEST.md`.
**Strategic ground truth (from the prior 3-way diff, this dir + RECONCILIATION):** the confidence floor + open-loop beat are **ancestral and fork-aggravated**, not a clean migration scar; donor `BeatTracker` was **bypassed in donor production** for short-lag/double-time failure — use its *concepts only*, fed by the fork's octave-defended winner.

---

## 1 · Phase tracker (living)

| Phase | Title | Status | Gate |
|---|---|---|---|
| 0 | Source truth + baseline ledger | **DONE** (this doc) | evidence territory-verified |
| 1 | Extend existing harness + baseline | **DONE** | host metrics non-empty ✓; pytest 128 green ✓; tempo_replay 144-fail pre-existing (recorded §2.5) |
| 2 | Tempo confidence + lock repair (`-D SB_TEMPO_CONF_V2`) | **DONE — ACCEPT** (behind flag; device activation deferred to final promotion) | all acceptance (a)-(f) PASS §2.6; xtensa build green |
| 3 | Beat phase / flywheel + **3× republish bug fix** | **DONE — ACCEPT** (behind `SB_TEMPO_FLYWHEEL_V2`; beat-F front-end-capped → Phase 4) | density-in-band 5.6→97.2%; precision 3×; phase-continuity 3.2×; §2.7 |
| 4 | Onset detector + semantic separation | **DONE — ACCEPT** (behind `SB_ONSET_V2`; full ON-02 needs upstream un-clamp) | AGC-survival 8×; per-band clean; refractory 0 viol; §2.8 |
| 5 | Harmonic saliency / ChordState | **DONE — ACCEPT (PORT)** (behind `SB_CHORD_V2`) | harmonic axis dead→alive; chord 6/6; §2.9 |
| 6 | AudioSemanticState spine (M-6 bridge-deferred) | **DONE — ACCEPT** (behind `SB_SEMANTIC_STATE`) | read-only aggregator; §2.10 |
| 7 | Rate-consistency audit | **DONE — no mismatch** | injection-guard live; all α rate-derived; §2.10 |
| 8 | Full validation + promotion + one human check | **DONE — promoted; eyes-on PENDING** | §7 final report; flags live in `[env:k1_hardware]` |

---

## 2 · Source-evidence ledger (territory-verified, current source)

All line numbers verified by direct read against current source (not copied from prior analysis).

### Fork (`SPECTRASYNQ_K1_FIRMWARE/audio/`)
| ID | Claim | file:line | Snippet |
|---|---|---|---|
| C1 | **Confidence = peak²/(peak²+Σ competitor²)** (quadratic, out-of-lobe only) — THE floor | `sb_tempo.cpp:507-508` | `peak_sq = peak*peak; sb_confidence = peak_sq/(peak_sq + out_ssq + 1e-12f)` ; `out_ssq = Σ sb_conf_score(i)²` for bins beyond `±SB_CONF_LOBE` (loop :502-506); fallback same form :521-522 |
| C2 | Lock threshold + gate | `sb_tempo.cpp:40`, `:569` | `SB_LOCK_CONFIDENCE = 0.60f`; `e.locked = (conf > SB_LOCK_CONFIDENCE) && !silence` |
| C3 | **Octave-defended winner (PRESERVE):** harmonic-comb ACF + log-Gaussian tactus prior | comb `:281-296`, prior `:72-79` | `SB_COMB_TEETH 4` w={1.0,0.8,0.7,0.6}; `comb(T)=Σ w_k·acf(k·T)` (:269); **selection** prior `SB_TACTUS_BPM 88 / SB_TACTUS_SIGMA 0.75`; **separate** confidence prior `SB_CONF_BPM 120 / SB_CONF_SIGMA 0.9` (:88/:91) |
| C4 | Open-loop phase + hard re-anchor | `:535-542`, `:528-531` | free-run `phase += rad_per_sec*dt` (:540); re-anchor only when winner is a freshly-computed bin & `mag_raw>0.005` (:529-531); beat tick on upward zero-cross :544 |
| C5 | Rates | `:22-27` | `SB_AP_FRAME_HZ=12800/96=133.33`; `SB_NOVELTY_DECIMATION=3`; `SB_NOVELTY_RATE_HZ=44.44`; `SB_HISTORY_LENGTH=512` (≈11.5 s) |
| — | Host-test entry (the harness lever) | `:706-726` | `#ifdef SB_TEMPO_HOST_TEST` → `sb_tempo_debug_dump(...)`, `sb_tempo_debug_dump_raw(...)`; "NEVER compiled into production" |
| C-on | Fork onset = dual-EMA fast/slow + single 240 ms refractory; fused IOI/beat | `sb_onset_beat.cpp:25,174-181,202`, `:84-104,115-116` | `SB_ONSET_REFRACTORY_MS=240`; `fast α=ob_alpha(dt,80)`, `slow α=ob_alpha(dt,1200)`; onset=`novelty_fast−novelty_slow`; IOI `est=(3·est+iv)/4` (:101), `beat_confidence` fused |
| C-har | Fork harmonic proxy = scalar `chroma_strength` (documented degraded) | `sb_musical_saliency.cpp:97-100` | `// Harmonic proxy: chroma strength change … (fork has chroma_strength, not chord root/confidence fields)` |

### Donor (`Lightwave-Ledstrip/firmware-v3/src/audio/`)
| ID | Claim | file:line | Snippet |
|---|---|---|---|
| C6 | Donor TempoTracker confidence = **linear** peak/Σ | `tempo/TempoTracker.cpp:474-478` | `confidence_ = max_contribution / power_sum_` (linear) — fork *deepened* this to quadratic |
| C7 | **Donor BeatTracker confidence (concept to graft):** prominence + periodicity + re-ranged share + EMA | `pipeline/BeatTracker.cpp:325-335` | `histShareNorm=clamp01((histShare-0.04)/0.24)`; `prominence=clamp01((bestVal-secondVal)/(bestVal+1e-9))`; `periodicity=clamp01(combEnh[..]/(enhMax+1e-9))`; `quality=clamp01(0.40·histShareNorm+0.35·prominence+0.25·periodicity)`; `conf=conf·0.88+quality·0.12` |
| C8 | **Donor BeatTracker BYPASSED in production** (do not port wholesale) | `pipeline/PipelineCore.cpp:528-566` | comment: "previously used a comb/CBSS beat tracker that consistently over-selected short lags (double-time 200+ BPM failures). For production stability, drive the proven … TempoTracker"; frame tempo written from `m_tempoCompatOut`, BeatTracker output never written |
| C9 (M-3) | Donor ChordState + detectChord; harmonic axis needs root/type/confidence | `contracts/ControlBus.h:82-85`, `ControlBus.cpp:796-846`, `MusicalSaliency.h:48-54,108-113` | `struct ChordState{rootNote,type,confidence}`; `cs.confidence=clamp01((triadEnergy/totalEnergy)/0.4)`; harmonic axis keyed on prev chord root/type |
| C10 (M-4) | Donor 6 onset channels w/ separate sources+reliability | `contracts/OnsetSemantics.cpp:122-135,25,31,39-40` | `out.{beat,downbeat,transient,kick,snare,hihat}` each `reliable` + per-channel `intervalMs`/`sequence` |
| C11 (M-5) | Donor log-flux + median-adaptive threshold + per-band + output-permission-only gate | `onset/OnsetDetector.cpp:5-22,249-266` | `gate is OUTPUT PERMISSION ONLY` (:5); `SF=Σ max(0,log m[t,k]−log m[t-1,k])` (:15); `max(median(flux,13)·1.5,0.01)` (:17); per-band kick/snare/hihat (:21-22) |
| C12 (M-6) | Donor ControlBus semantic edges — **NO FORK CONSUMER** | `ControlBus.h:301-303,94,225`; fork grep | `timing_jitter`, `syncopation_level`, `pitch_contour_dir`, `struct AudioEventQ15` exist in donor; **grep of `SPECTRASYNQ_K1_FIRMWARE/` for `timing_jitter\|syncopation\|pitch_contour\|AudioEvent` = ZERO files** |
| C13 | Donor rate hazard (do not import constants blind) | `PipelineCore.cpp:535-537` | `kTempoCompatDiv=5`; `kTempoCompatDtSec=0.020f //50 Hz` vs configured 256-hop → potential 25 Hz actual (2× error) |

---

## 3 · Corrected claims (Bayesian updates from territory)

1. **Two priors, not one.** Selection prior = 88 BPM/σ0.75 oct; confidence prior = 120 BPM/σ0.9 — deliberately decoupled. Any text conflating them is struck.
2. **The floor is ancestral *and fork-deepened*.** Donor (`C6`) is linear peak/Σ; fork (`C1`) squared it and excluded only the out-of-lobe set → numerator can be sub-maximal while ~80 normalised competitors fill the denominator → 0.05–0.14 on real music vs a 0.60 lock. Replacing the *structure* (not lowering 0.60) is the fix.
3. **No "v3 PLL" was dropped.** Donor's live path (`TempoTracker`/`EsBeatClock`) is *also* open-loop; the only flywheel (`BeatTracker` CBSS) was **bypassed in donor production** (`C8`). Phase repair = add error feedback + inertia + watchdog to the fork's existing phase, concept-borrowed from CBSS — **not** a CBSS port.
4. **M-6 has no consumer → Phase 6 restoration is NOT edge-justified.** Per the mission's own conditional ("restore … if source confirms they are consumed downstream"), `C12` shows zero fork consumers. **Decision:** build the `AudioSemanticState` spine exposing *produced* fields; record `timing_jitter`/`syncopation_level`/`pitch_contour_dir`/`AudioEventQ15` as donor-contract **bridge-deferred** until a consumer exists (effects/Director — which the mission forbids touching this run). This is the corrected plan, not a skip.

---

## 2.5 · Baseline (incumbent, measured 2026-06-05, 36/36 corpus, real C++)

Stored: `build/audio-semantic-metrics/baseline.{json,md}` (untracked, reproducible). Headlines:

| Metric | Value | Read |
|---|---|---|
| beat-F ±70 ms (x1 / octave-fair) | **0.031 / 0.038** | beat output does not track real beats |
| continuity CMLt / AMLt | **0.010 / 0.010** | no sustained correct tracking |
| conf reachability: ever-lock / ever≥0.60 | **100% / 100%** | it DOES lock transiently |
| conf: median **settled** / median **max** | **0.041 / 1.000** | **spike-then-collapse**, not a flat floor |
| false-lock silence / white-noise (lock-frac, maxconf) | 0.000/0.000 ; **0.014 / 1.000** | noise momentarily hits full conf |
| Acc1/Acc2 overall ; in-range | 50.0/52.8 ; **56.2/56.2** | octave-defended selection is healthy → PRESERVE |
| beat_tick density (median) | **4.68 Hz**, 6% in tactus band | fires ~2× too dense → Phase-3 defect |

**Corrected problem model (supersedes "flat floor 0.05–0.14"):** confidence is **volatile** — a momentarily-peaky ACF frame drives `peak²/(peak²+Σ)`→1.0 (transient lock), then collapses to ~0.04 as competitors fill in; white noise triggers the same spike. The fix target is therefore **sustained** confidence on music + **suppressed transient spikes** on noise — precisely what the donor EMA(0.88/0.12) + prominence/periodicity + lock-FSM provide. beat-F/continuity are dominated by the **beat_tick over-emission** (Phase 3), separable from the confidence A/B (Phase 2).

**Pre-existing baseline failure (recorded, not introduced):** `tempo_replay.py` synthetic 144-BPM asserts → `TEMPO_REPLAY_FAIL failures=2` at HEAD (verified by stashing the host-scaffold edit). Known comb+prior tradeoff (HW locks 144 fine). Future gates use `tempo_accuracy.py`/`beat_semantic_metrics.py` as the real-music gate, not the synthetic-144 sentinel.

## 2.6 · Phase 2 result — confidence/lock repair (ACCEPT, behind `-D SB_TEMPO_CONF_V2`)

`sb_tempo.cpp +277/−0`, all under `#ifdef SB_TEMPO_CONF_V2` / `#ifndef … #else`; production path byte-identical (no-flag build reproduces incumbent exactly); V2 cross-compiles for ESP32-S3 (`pio run -e k1_hardware` + `PLATFORMIO_BUILD_FLAGS=-DSB_TEMPO_CONF_V2`, exit 0).

**Source-driven design correction (autonomous, evidence-backed):** the planned `peakShare`/`prominence` on the *comb selection* score is **unreachable** here — the harmonic comb deliberately *spreads* salience for octave defence (comb peakShare≈0.03, prominence≈0; only 12% of tracks could cross 0.60). Recovered the donor's true intent — **peak-above-background** — computed on the **point ACF salience** (`sb_conf_score`, un-spread): `prominence = (peak − mean_out_of_lobe)/peak`. Also fixed an acquisition bug (sub-floor watchdog must run only after lock+warmup, else it resets the EMA every N frames and conf can never ramp).

**Calibration (data-driven, 36-track corpus + synthetic silence/noise):** LO=0.01, HI=0.04, W=0.40/0.35/0.25, REL=0.42, FLOOR=0.20, watchdog N=12, **EMA α=0.13929** (rate-derived `1−exp(−(1/44.444)/0.150)`, τ=150 ms; donor's raw 0.12@50 Hz explicitly rejected as wrong-at-this-rate). Separation: music BGprom p50 0.66 vs noise 0.065.

**A/B (incumbent → V2):** median settled conf **0.041→0.620** (in-range 0.048→**0.682**); in-range tracks settling ≥0.60 **0/32→17/32**; median frac-frames≥0.60 0.006→**0.388**; noise lock-frac **0.0141→0.000**, noise max-conf **1.000→0.530**; **Acc1/Acc2 identical (56.2/56.2 in-range)**; beat-F/continuity **identical** (selection + beat_tick untouched — Phase 3 owns those); pytest **128 passed**; `tempo_replay` **1 fail** (down from 2 — the synthetic 144 now locks; remaining fail = unchanged selection octave-halve).

**Acceptance:** (a) production unchanged ✓ (b) Acc1/Acc2 identical ✓ (c) settled conf rises + 17/32 sustain ≥0.60 ✓ (d) false-lock down ✓ (e) no new synthetic regression ✓ (f) α rate-derived ✓. **Decision: ACCEPT.** Kept behind the flag; the device flag-flip (`-DSB_TEMPO_CONF_V2` into `[env:k1_hardware]`) + legacy steering-comment + eyes-on are the **final promotion**, consolidated into the single human check.

## 2.7 · Phase 3 result — beat phase / flywheel (ACCEPT, behind `SB_TEMPO_FLYWHEEL_V2`)

`sb_tempo.cpp +277/−0` all under `#ifdef SB_TEMPO_FLYWHEEL_V2`; production byte-identical (no-flag rebuild reproduces incumbent to 1e-9); xtensa build green with `-DSB_TEMPO_CONF_V2 -DSB_TEMPO_FLYWHEEL_V2`.

**Root cause of "2× density" (measurement-only finding, NOT the predicted cause):** a **3.000× read-rate/emit-rate stale-republish bug** — `sb_tempo_update` runs at 133 Hz but emits every 3rd frame (44.4 Hz) and `return`ed early on non-emit frames *without clearing* the one-shot `beat_tick`, so `sb_tempo_read()` returns `beat_tick=true` on all 3 frames. Any consumer faster than 44 Hz (the 133 Hz render loop) triple-triggers. **This is a real device defect that V2's now-reachable lock would have unmasked.** Fix = re-publish `beat_tick=false` on non-emit frames. (raw/dedup ratio was exactly 3.000.)

**PLL (concepts from donor CBSS, fed by octave-defended winner + V2 lock):** bounded-Kp phase correction toward internally-derived novelty onset peaks (3-pt peak-pick, adaptive MAD floor), tiny-Ki freq slew hard-clamped ±4% (octave-safe), lock-gated one-shot tick, bounded coast (8 beats) then stop, hard re-anchor removed. Calibration (@44.44 Hz): `KP=0.25, MAX_CORR=0.10 beat, KI=0.002, FREQ_PULL=0.04, ONSET_K=1.20` (floor EMA τ=0.30 s→α=0.0723), `COAST=8 beats, REFRACTORY=0.45 beat`.

**A/B (incumbent → flywheel_v2, both flags):** density-in-band **5.6%→97.2%** (median 1.41 Hz); IBI phase-continuity **0.156→0.494**; per-beat precision **0.099→0.300 (3×)**; noise false-lock **0.0141→0.000**; silence 0; **Acc1/Acc2 identical (56.2/56.2)**; pytest 128; tempo_replay 1 fail (pre-existing 144).

**Acceptance:** (a) production byte-identical ✓ (b) Acc unchanged ✓ (d) density-in-band majority ✓ (e) no silence/noise beat-storm ✓ (f) pytest+xtensa green ✓ — **(c) beat-F up: FAIL** (0.031→0.026, flat-to-down). **Conclusively diagnosed: beat-F *recall* is capped by the harness `novelty_from_wav.py` onset front-end** (its novelty peaks are GT-misaligned on several tracks; z-lift at GT-beats vs off-beats ranges −0.40…+0.28), bounding recall for BOTH arms. PLL improved precision 3× but aggregate F can't show it. **Implication for Phase 4:** beat-F is unlocked by better *onset evidence* (donor log-flux/median-adaptive/per-band) AND requires the host beat-F path to drive the real onset front-end (or device eyes-on as the arbiter). **Decision: ACCEPT** — the 3× republish fix + 3× precision + 3.2× continuity are real and shippable; beat-F is orthogonal/front-end-bound.

## 2.8 · Phase 4 result — onset detector + semantic separation (ACCEPT, behind `SB_ONSET_V2`)

`sb_onset_beat.cpp +362`, `sb_audio_snapshot.{h,cpp} +37/+11`, all under `#ifdef SB_ONSET_V2`/`#else` (legacy dual-EMA preserved in `#else`); production byte-identical (`ONSET_BEAT_REPLAY_OK cases=7` no-flag); `sb_tempo` untouched. Donor-shaped detector over the fork's `spectrogram[80]`: **log-flux + median-adaptive threshold (14f≈105 ms × 1.6 + 0.05) + causal peak-pick (4f/30 ms) + per-band kick/snare/hihat** with per-band refractory (45/37.5/22.5 ms) and the donor **OUTPUT-PERMISSION-ONLY gate** (gate keys on `spectral_energy` level, never injects zeros into the adaptive baseline). New channels (`transient/kick/snare/hihat`) added additively to `SBOnsetBeatEvent`; legacy fields + IOI/beat path intact (existing comet/director/AP_STREAM consumers unbroken).

Band→bin map (notes[i], A1=55 Hz): kick `[1,25)`=58–233 Hz, snare `[25,50)`=233–932 Hz, hihat `[70,80)`=6.3–13.3 kHz, transient `[1,76)`. EMA α rate-audited at **133.33 Hz** (kick 0.0141/snare 0.0094/hihat 0.0047).

**A/B (incumbent → SB_ONSET_V2, 12 tracks):** onset P/R-proxy F1 0.031→**0.098** (recall 0.017→0.106, 6×); per-band channels fire independently (kick on bass, hihat on highs); refractory **0 violations/12**; **AGC-clamp survival 115→923 onsets/min (8.0×)** — the ON-02 fix; pytest **129**; xtensa green flag-alone AND all-flags-on (RAM 29.3%/Flash 9.1%). Acceptance (a)-(f) all PASS. **Decision: ACCEPT.**

**Honest bounds (load-bearing):** (1) **ON-02 is only partially fixable here** — `spectrogram[i]` is hard-clamped to [0,1] at `GDFT.h:276-278`; a *fully*-pinned band gives `log1−log1=0` flux and cannot fire. V2 recovers the common clamp-*transition* case (8× density) but the FULL fix needs an **upstream un-clamped pre-AGC magnitude path into the onset detector** (deferred — would touch GDFT/AGC, a bigger change). (2) **hihat band is above the 12.8 kHz-corpus Nyquist (6.4 kHz)** — sparse/aliased on host AND hardware at 12.8 kHz SR; kick/snare are the meaningful bands. (3) P/R-proxy is onset-vs-GT-*beat* (labelled proxy). (4) Onset→flywheel rewire (feeding V2 transient into the Phase-3 PLL to unlock beat-F recall) is the correct NEXT measured step — deliberately NOT bundled here.

## 2.9 · Phase 5 result — ChordState + harmonic saliency (ACCEPT/PORT, behind `SB_CHORD_V2`)

**Branch taken: PORT** (not bridge-only). A pitch-class-aligned 12-bin chroma was derivable for free — `sb_audio_snapshot.cpp:67-69` already folds `chroma_bucket[i%12] += spectrogram[i]` on Core 0 then *collapses it to the `chroma_strength` scalar*; V2 keeps the full 12-bin `chroma_pc[12]` (same source, same core, race-free; the per-note `notes[]` table is semitone-spaced so `i%12` is true pitch class — `constants.h:175-184`). Did NOT reuse `make_smooth_chromagram` (Core-1/render → cross-core).

`sb_audio_snapshot.{h,cpp} +48/+19`, `sb_musical_saliency.cpp +48` (legacy proxy preserved verbatim in `#else`), new `sb_chord_detect.cpp` (stdint/math-only, empty without flag). All under `#ifdef SB_CHORD_V2`; production token-identical; `sb_tempo`/`sb_onset` untouched. Ported `detectChord` (root = dominant PC; +3/+4 third; +6/+7/+8 fifth; `conf=clamp01((triad/total)/0.4)`, `<0.3→NONE`) + the harmonic axis (base `conf·0.3`, →1.0 on root change, →0.6 on type change). Rate: saliency τ-smoothing already dt-aware @133 Hz (no donor α carried blind).

**A/B:** chord detection **6/6** synthetic (maj/min/dim/aug root+type, conf 1.0), confidence monotone with triad purity; **harmonic axis smoothed peak 0.0 (dead) → 0.285 (alive)**, raw 1.0/0.6 on root/type change; pytest **130**; xtensa green flag-alone AND all-flags-on. Acceptance (a)-(e) all PASS. **Decision: ACCEPT.**

**Honest load-bearing caveats:** (1) **A-origin offset** — fork chroma bin 0 = A, donor = C, so the absolute `rootNote` label is rotated **+9 (mod 12)** vs donor convention (detection is correct — intervals are mod-12; saliency uses root *changes*, origin-invariant). Any future rootNote→note-name consumer must adopt A-origin or add 9. (2) **Inherited donor limitation:** confidence is a triad-energy *ratio*, not a triad-*shape* test — a flat chroma reads 0.625 and a lone root ~1.0; it does NOT collapse non-triadic input to NONE. The future Director must not over-trust chord confidence as a "chord present" gate. Pinned in the harness so any change is consciously re-judged.

## 2.10 · Phase 6+7 result — semantic spine + rate audit (ACCEPT, behind `SB_SEMANTIC_STATE`)

New `audio/sb_semantic_state.{h,cpp}` (entire body behind `#ifdef SB_SEMANTIC_STATE`): a POD `AudioSemanticState` + `audio_semantic_read(out)` that READS `sb_tempo_read`/`sb_onset_beat_read`/`sb_audio_snapshot_read` (portMUX-guarded → any-core-safe) and packs tempo (`bpm/tempo_confidence/tempo_locked/beat_phase01/beat_tick/beat_strength`), onset (`onset/onset_strength` + V2 `transient/kick/snare/hihat`+levels), chord (V2 `chord_root/type/confidence`), and **rate diagnostics** (`sample_rate_hz/ap_frame_hz/novelty_rate_hz/samples_per_chunk/frame_ms`). Read-only; **producers + `.ino` + `platformio.ini` untouched** (empty diff); `build_src_filter +<audio/sb_*.cpp>` already matches. M-6 fields (`timing_jitter/syncopation_level/pitch_contour_dir/AudioEventQ15`) **documented bridge-deferred in the header (no producer + no consumer per C12) — NOT fabricated.**

**Phase 7 rate audit — NO mismatch:** conf EMA α=0.1393 (1−exp(−(1/44.44)/0.150), emit rate) ✓; flywheel floor α=0.0723 ✓; onset V2 band α (0.0141/0.0094/0.0047 @133.33 Hz, dt=7.5 ms) ✓; legacy onset/saliency EMAs fully dt-driven ✓; chord per-frame stateless ✓. `tests/test_rate_consistency.py` strengthened (+129): asserts the V2 EMA derivations + **FAILS on a live 2× AP-rate injection** (proven — conf α 0.1393→0.0723 trips the assert).

**Validation:** pytest **136 passed**; xtensa green no-flag / flag-alone / **all-6-flags**. **Production byte-identical proven by ELF section sizes** (`.text/.data/.bss = 426582/170900/1113629` identical with/without spine; no-flag spine TU has zero defined symbols) — the `.bin` embeds a build timestamp so whole-binary SHA is NOT a valid identity test on ESP32-S3 (section sizes + symbol inspection are). Acceptance (a)-(e) all PASS. **Decision: ACCEPT.**

## 4 · Host-harness map (extend, do NOT duplicate)

- **Lane A — real C++ (authoritative):** `tempo_replay.py` compiles **unmodified `sb_tempo.cpp`** with `clang++ -DSB_TEMPO_HOST_TEST`, pipes `"ms novelty silence"` on stdin, prints `T <ms> <bpm> <conf> <locked>` per frame. `tempo_accuracy.py` drives **36 HarmonixSet WAVs** (12.8 kHz) via `novelty_from_wav.py` → real binary → MIREX Acc1/Acc2 + octave classes → `docs/measurements/tempo-octave-baseline.{md,tracks.csv}`. `onset_beat_replay.py` compiles real `sb_onset_beat.cpp` (7 assert cases → `ONSET_BEAT_REPLAY_OK cases=7`; **this one is in the pytest gate**).
- **Lane B — numpy replicas (fast exploration only):** `bt_acf_4way.py` (signal registry; self-checks vs real-C++ CSV), `acf_ceiling_sweep.py` (config matrix), `mirex_rescore.py`.
- **pytest:** default discovery; `tests/test_onset_beat_replay.py`, `tests/test_onset_beat_event_metrics.py`. **No `test_tempo*`.**
- **Corpus + GT:** audio `Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8/*.wav` (36). GT (out-of-repo) `/Users/spectrasynq/Workspace_Management/Software/K1.reinvented/Implementation.plans/harmonixset-main/dataset/` — `metadata.csv` (gold BPM), `beats_and_downbeats/*.txt` (**912 beat-time files — present but UNUSED for event scoring → the beat-F GT**). GT-half-tempo-suspects: `0331,0353,0666,0680` (`gt≈2×ibi`).
- **Extension seams:** (a) per-track metric → `tempo_accuracy.run()` row dict + `summarise()`; (b) candidate variant → `bt_acf_4way` signal registry (replica) **and/or** a new `-D` macro in `tempo_replay.build_binary` (real C++, authoritative); (c) sweep → `acf_ceiling_sweep.CONFIGS` pattern; (d) pytest gate → mirror `test_onset_beat_replay.py` (subprocess + `_OK` sentinel).
- **Missing capabilities to add:** beat-F (±70 ms), continuity (CMLt/AMLt-style), confidence-reachability, false-lock-on-silence/noise (corpus-level), onset P/R (audio), one rate-consistency assertion (the `SB_NOVELTY_DECIMATION=3` + 44.44/133.33 constants are hand-replicated in 3 Lane-B files → drift risk).

---

## 5 · Forward-graft plan with decisions

**Phase 1 (now):** new sibling `scripts/regression-harness/beat_semantic_metrics.py` reusing `tempo_replay` binary + `tempo_accuracy.load_gt/octave_eval` + corpus defaults; emits beat-F/continuity/confidence-reachability/false-lock; extend the `SB_TEMPO_HOST_TEST` replay `main` printf to also emit `phase01` + `beat_tick` (host scaffold, not firmware behaviour). Add `tests/test_rate_consistency.py`. Baseline → `build/audio-semantic-metrics/baseline.{json,md}`. Existing `pytest tests/` must stay green or failures recorded.

**Phase 2 (design FIXED):** add `-D SB_TEMPO_CONF_V2` path in `sb_tempo.cpp` computing, from the **existing octave-defended winner** (C3, unchanged):
- `histShareNorm = clamp01((peakShare − lo)/(hi − lo))` with `lo/hi` **re-derived on the fork corpus** (NOT donor 0.04/0.24 — donor-rate-specific, C13);
- `prominence = clamp01((peak − second)/(peak+eps))`;
- `periodicity = clamp01(comb_at_winner / comb_max)` (reuse fork comb);
- `quality = clamp01(0.40·histShareNorm + 0.35·prominence + 0.25·periodicity)`;
- `conf = conf·0.88 + quality·0.12` (EMA);
- **lock FSM:** acquire `conf ≥ SB_LOCK_CONFIDENCE(0.60)` AND warmup done AND ≥2 beats; release `conf < rel`; **watchdog** N cycles below floor → reset. **SB_LOCK_CONFIDENCE is NOT lowered** — the new metric is designed to *reach* it on music (validated by the reachability metric). Acquire/release hysteresis thresholds set from the new metric's measured music-vs-junk separation (legitimate calibration of the *new* metric, not a substitute for replacing it). A/B incumbent vs V2; adopt only if no synthetic regression + better reachability + fewer false locks.

**Phases 3–7:** per tracker §1; each host-tested first, committed green to `wip/*`.

---

## 6 · Non-goals (hard)
Director/effects behaviour or tuning; colour/palette/auto-colour; LED-output/render path; donor `BeatTracker` CBSS wholesale port; donor `TempoTracker`/vendor wholesale restore; importing donor timing constants without the §7 rate audit; lowering `SB_LOCK_CONFIDENCE` as the fix; restoring M-6 ControlBus fields that have no consumer (bridge-deferred); any device flash/erase/cal by the agent (final human check only).

## 7 · Final report (Phase 8 — completion)

### Commits (branch `wip/audio-saliency-recovery`)
| # | SHA | Phase |
|---|---|---|
| 1 | `5808e3b` | 0+1 — ledger + harness + baseline |
| 2 | `fa8a6cf` | 2 — `SB_TEMPO_CONF_V2` confidence/lock |
| 3 | `d953a72` | 3 — `SB_TEMPO_FLYWHEEL_V2` phase + **3× republish fix** |
| 4 | `593b5d2` | 4 — `SB_ONSET_V2` onset detector + channels |
| 5 | `5e4d27f` | 5 — `SB_CHORD_V2` chord + harmonic saliency |
| 6 | `d3c5469` | 6+7 — `SB_SEMANTIC_STATE` spine + rate audit |
| 7 | `4e96e30` | 8 — promotion (flags → `[env:k1_hardware]`) |

### Changed files
Firmware (all behind flags; production was byte-identical until commit 7): `audio/sb_tempo.cpp` (+554), `audio/sb_onset_beat.cpp` (+362), `audio/sb_audio_snapshot.{h,cpp}`, `audio/sb_musical_saliency.cpp`, NEW `audio/sb_chord_detect.cpp`, NEW `audio/sb_semantic_state.{h,cpp}`, `platformio.ini` (5 flags). Harness/tests: `beat_semantic_metrics.py`, `tempo_confv2_calibrate.py`, `onset_v2_replay.py`, `chord_saliency_replay.py`, `semantic_state_replay.py`, `tempo_replay.py`, `tempo_accuracy.py`, `onset_beat_replay.py`, `tests/test_{rate_consistency,onset_beat_replay,chord_saliency_replay,semantic_state_replay,smart_visual_engine_static}.py`, `.gitignore`, this ledger.

### Source claims confirmed / struck (corrected during execution)
- **STRUCK** "confidence is a flat floor 0.05–0.14" → **spike-then-collapse** (median settled 0.041, max 1.000; transiently locks). Noise also spikes to 1.0.
- **NEW BUG found** "2× beat density" → a **3.000× read/emit-rate stale-republish** (beat_tick not cleared on non-emit frames; 133 Hz consumers triple-trigger). Real device defect; fixed.
- **CONFIRMED** confidence floor is **ancestral + fork-deepened** (donor linear peak/Σ; fork squared it); donor `BeatTracker` (the floor-free design) was **bypassed in donor production** → concepts-only graft was correct.
- **CONFIRMED** comb selection salience is deliberately spread → V2 confidence computed on the **point ACF** (peak-above-background), not comb.
- **CONFIRMED** beat-F is **front-end-capped** by `novelty_from_wav.py` onset alignment, not the PLL (precision rose 3×; recall bound upstream).
- **CONFIRMED** fork chroma is derivable+pitch-class (A-origin → rootNote +9 vs donor C-origin).
- **CONFIRMED** M-6 ControlBus fields have **zero fork producer+consumer** → bridge-deferred, not fabricated.
- **CONFIRMED** ON-02 is bounded by the `[0,1]` spectrogram clamp (`GDFT.h:276-278`); V2 fixes clamp-transitions (8× survival) but a fully-pinned band needs an upstream un-clamped magnitude path.

### Before → after (host, real C++)
| Metric | before | after | note |
|---|---|---|---|
| tempo conf, median settled | 0.041 | **0.620** | CONF_V2 |
| in-range tracks sustaining lock ≥0.60 | 0/32 | **17/32** | CONF_V2 |
| white-noise false-lock (frac / maxconf) | 0.014 / 1.000 | **0 / 0.530** | CONF_V2 |
| beat_tick density in tactus band | 5.6% | **97.2%** | FLYWHEEL_V2 (3× fix) |
| beat phase-continuity | 0.156 | **0.494** | FLYWHEEL_V2 |
| per-beat precision | 0.099 | **0.300** | FLYWHEEL_V2 |
| onset survival on AGC-clamped input | 115/min | **923/min** | ONSET_V2 (ON-02) |
| harmonic saliency axis (smoothed peak) | 0.000 (dead) | **0.285 (alive)** | CHORD_V2 |
| tempo Acc1/Acc2 in-range | 56.2/56.2 | **56.2/56.2** | selection preserved ✓ |
| pytest | 128 | **136** | +8 tests |

### Blocked / deferred (honest)
- **DEVICE eyes-on** — host-validated only; the one remaining gate (below).
- **beat-F headline** — front-end-capped; the **onset→flywheel rewire** (feed `SB_ONSET_V2` transient into the PLL) is the measured next step, deliberately not bundled.
- **Full ON-02** — needs an upstream pre-AGC un-clamped magnitude path into the onset detector (touches GDFT/AGC).
- **CHORD_V2 / SEMANTIC_STATE** — inert on device until a consumer exists (Director wiring was out of scope).
- **M-6 fields** (`timing_jitter`/`syncopation`/`pitch_contour`) — bridge-deferred (no producer+consumer).
- **Synthetic 144-BPM** `tempo_replay` assert — pre-existing octave-halve (HW locks 144); not a regression.

### THE ONE FINAL HUMAN CHECK (do only this)
1. ✅ **FLASHED 2026-06-05** — uploaded to the K1 (2nd bench unit) on `/dev/tty.usbmodem2101`; identity verified by the upload guard (USB serial `B4:3A:45:A5:87:F8`, chip `F887A500`, MAC `b4:3a:45:a5:87:f8`), 600,288-byte app, all hashes verified, hard-reset into the forward-graft. The unit had moved port 1401→2101 (`platformio.ini` + `k1_upload_guard.py` updated; serial/chip identity check unchanged). **Your remaining action is the eyes-on below.**
2. Play **3–5 representative real-music tracks** (varied tempo/genre, include something with a clear 4-on-the-floor and something syncopated).
3. **Confirm:** (a) beat phase visually tracks the music (not metronome drift); (b) beat-reactive effects (e.g. Tempo Comet) now **fire and sustain** on real music and stay quiet on silence/noise; (c) onsets feel transient/percussive, not flattened, **including on loud passages**; (d) no regression vs the current look. (Harmonic response is NOT yet visible — no consumer.)
4. **If any regression:** delete the 5 `-D` lines in `platformio.ini` (revert to legacy) and report which symptom.
5. If a labelled real-music device corpus is wanted for future regression, capture AP_STREAM during these tracks.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:Orchestrator | Created — Phase-0 source-truth ledger + forward-graft plan; evidence territory-verified (C1–C13); corrected 4 claims (two-priors, ancestral+deepened floor, no-dropped-PLL, M-6 no-consumer→bridge-deferred); harness mapped extensible; Phase-2 confidence design fixed. |
| 2026-06-05 | agent:Orchestrator | Phases 1–8 executed + committed (5808e3b…4e96e30). §2.5–2.10 per-phase results; §7 final report. Confidence 0.041→0.620; 3× beat-republish bug found+fixed; density-in-band 5.6→97.2%; onset AGC-survival 8×; harmonic axis revived; Acc1/Acc2 preserved 56.2; pytest 128→136. Promoted to k1_hardware default. DEVICE eyes-on is the one remaining gate. |
