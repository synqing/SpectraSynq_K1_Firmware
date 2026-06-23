---
abstract: "RE-Corpus excavation candidate register (delegation RECORP-EXCAV-01) — Synesthesia + Auto-BPM RE corpora → provenance/portability/gate-testability-graded AP candidate register for the K1 fork. STATUS: Synesthesia pass complete through host-only Stage 4 and partial Stage 5 ranking; Auto-BPM excavation remains blocked on Captain's Q2 canonical-source choice. Promotes NOTHING; promote-to-test means only a proposed test target for a later joint Captain session. Read the SynqMatrix inoculation (§A) before grading anything."
---

# RECORP-EXCAV-01 — RE-Corpus → K1 AP Candidate Register

**delegation_id:** RECORP-EXCAV-01 · **classification:** LOAD-BEARING · **status:** **WIP — Synesthesia pass complete; Auto-BPM blocked on Q2**
**Governing rule:** *excavate and grade; promote NOTHING.* Authority is Captain's, held in a later joint session. An agent that writes "X is reference-grade" has already failed.

---

## A · The SynqMatrix inoculation (do-not-repeat ledger — Stage 0)

> Source-grounded 2026-06-05 against `Lightwave-Ledstrip/firmware-v3/docs/research/SynqMatrix_Synesthesia_Authority_Audit_2026-05-16.md` (194 lines), `Lightwave-Ledstrip/firmware-v3/docs/MusicAware_Audit_And_Gap_Analysis.md`, `Lightwave-Ledstrip/firmware-v3/docs/research/SynqMatrix_Director_RFC_2026-05-15.md`, and `Lightwave-Ledstrip/firmware-v3/docs/SESSION_HANDOVER_20260515_SynqMatrix_RFC.md`.

1. **[FACT]** The chain "Synesthesia → Family B → reference-grade → authoritative" holds only at link one: the authority audit says Synesthesia is a real dated reference body, but "Family B" is bundling-layer NotebookLM metadata, original Synesthesia RE documents contain zero "Family A/B" strings, and the "reference-grade authoritative" language must be narrowed (`SynqMatrix_Synesthesia_Authority_Audit_2026-05-16.md:11`, `:70-72`, `:97-104`, `:118`; RFC reconciliation at `SynqMatrix_Director_RFC_2026-05-15.md:829-843`).
2. **[FACT]** The constants **Davies-3-promote / IBT-8-bad-demote / IBT ±46.4 ms / MIREX ±70 ms** are attributed to **Tier-2 academic compass-artifact**, **not Synesthesia**. The MusicAware table states Synesthesia Tier 1 is `NOT SPECIFIED` for lock, tolerance, and coast/reacquire while Tier 2 carries the Davies/IBT/MIREX material (`MusicAware_Audit_And_Gap_Analysis.md:61-65`; authority-audit ledger rows at `:66-68`, matrix at `:102`, RFC at `:790-803`). Any candidate carrying these gets `provenance = ACADEMIC-or-MISATTRIBUTED` unless it cites the academic source directly.
3. **[FACT]** The RE corpus exists and is useful, but its parameter authority is explicitly caveated: the authority audit records "Speculation vs. Fact Ratio: 70/30" and NotebookLM self-rating "Synesthesia Implementation: 75%; Parameter Values: 70% (Typical ranges, not Synesthesia-specific)" (`SynqMatrix_Synesthesia_Authority_Audit_2026-05-16.md:64`, `:91`, `:97`). Therefore **RE parameter values are `[INFERENCE]` by default**, never `[FACT]`, unless the source itself quotes measured/app-specific evidence.
4. **[FACT]** K1's implementation-tier ancestor is **Emotiscope**, not Synesthesia: the authority audit found zero Synesthesia / Davies / MIREX / IBT source hits in the inspected SynqMatrix implementation and cites `EsV11Backend.h` / vendor tempo as Emotiscope-derived (`SynqMatrix_Synesthesia_Authority_Audit_2026-05-16.md:77-79`, `:100`, `:103`). The RFC later restates Synesthesia and AutoBPM as Tier-1 reference bodies, not implementation authorities (`SynqMatrix_Director_RFC_2026-05-15.md:774`, `:835-841`).
5. **[INFERENCE]** Both RE corpora sit in the same broad algorithm family K1 already uses or has adjacent machinery for: onset/novelty → tempo induction → confidence/phase smoothing. This is a useful search map, not authority. The current device-truth pain is **tempo selection/front-end novelty**, not the now-working confidence magnitude: live validation shows 127→83 and 123→82 device 3:2 errors, with the loud 4-floor confidently wrong at median confidence 0.94 (`docs/forensics/tempo_tracking_refactor/2026-06-05-audio-semantic-post-graft-validation.md` §6.1). Grade candidates against that evidenced constraint.

**Open authority questions (Captain-only — surface, do NOT answer):**
- Q1. Is any specific RE parameter actually Synesthesia-measured vs RE-author-inferred? (per-candidate, Stage-2.)
- Q2. **[§8 ACCESS GAP — escalated 2026-06-05]** Canonical Auto-BPM doc is unconfirmed — 3 candidates found (see §C). Captain must designate before the Auto-BPM half excavates.
- Q3. Any promotion to canonical — the entire joint session; nothing here is live until then.

---

## B · Environment verification (Stage 0 — DONE 2026-06-05)

| Resource | Path | Status |
|---|---|---|
| Synesthesia RE corpus | `~/Workspace_Management/Software/Synesthesia/` (Docs/Synesthesia.RE, src, spec, artifacts) | **REACHABLE** |
| Authority audit (prior art) | `Lightwave-Ledstrip/firmware-v3/docs/research/SynqMatrix_Synesthesia_Authority_Audit_2026-05-16.md` | FOUND (194 ln) |
| MusicAware audit (extend its Tier table) | `Lightwave-Ledstrip/firmware-v3/docs/MusicAware_Audit_And_Gap_Analysis.md` | FOUND (brief's `/fidocs/` was a typo) |
| SynqMatrix RFC + handover | `…/docs/research/SynqMatrix_Director_RFC_2026-05-15.md`, `…/docs/SESSION_HANDOVER_20260515_SynqMatrix_RFC.md` | FOUND |
| Auto-BPM technical analysis | **3 candidates — canonical TBC by Captain (Q2)** | AMBIGUOUS |
| Synesthesia.RE algorithm specs | `…/Synesthesia/Docs/Synesthesia.RE/02_ALGORITHMS/05_Algorithm_Specifications.md` | FOUND |
| Harness (gate) | `scripts/regression-harness/` (tempo_accuracy.py, beat_semantic_metrics.py, novelty_from_wav.py, tempo_replay.py) | PRESENT |
| Write target | `docs/research/` | PRESENT (this file) |
| AGENTS reference docs named in pasted instructions | `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`, `docs/protocol/k1-ws-contract.yaml`, `docs/protocol/k1-rest-contract.yaml` | **ABSENT in this checkout** (`SPECTRASYNQ_K1_FIRMWARE` tree is the live local surface); do not silently import sibling-repo paths as local truth |

**Harness blind spot to stamp on every front-end candidate [FACT]:** the gate feeds `sb_tempo` a *modelled scipy novelty*, **not** the device GDFT/AGC front-end — so front-end candidates are **not fully testable** on the current gate. (Device-truth on real music already diverges from the host ceiling: see `docs/forensics/tempo_tracking_refactor/2026-06-05-audio-semantic-post-graft-validation.md` §6.1 — a reproducible 3:2 tempo-selection error, 127→83 / 123→82.)

## C · Auto-BPM canonical-path candidates (Q2 escalation detail)
1. `~/Workspace_Management/Software/Tab5.DSP/docs/Auto_BPM_Technical_Analysis.md`
2. `~/Workspace_Management/Software/hybrid-beat-tracker/docs/Auto_BPM_Technical_Analysis.md`
3. `~/Workspace_Management/Software/hybrid-beat-tracker/docs/tooling/notebooklm-bundles/hybrid_beat_tracker/docs_Auto_BPM_Technical_Analysis.md` *(the in-session upload)*

---

## C2 · MusicAware Tier-table extension (Stage-0-full)

> Extension of `MusicAware_Audit_And_Gap_Analysis.md:57-67` for this register. This table is a grading map only; it promotes nothing.

| AP element family | Synesthesia Tier 1 | AutoBPM Tier 1 | Academic Tier 2 | Register implication |
|---|---|---|---|---|
| Front-end novelty | [FACT] Spectral-flux family with adaptive median/std threshold and refractory, but desktop constants live in the Synesthesia context (`MusicAware_Audit_And_Gap_Analysis.md:59`). | [FACT] Log/complex-domain novelty with phase+magnitude components, numeric source still blocked on Q2 (`:59`). | [FACT] Complex spectral-difference family, multiple sample-rate/window variants (`:59`). | Candidate can be `PROMOTE-to-test` only as **structure** (log/whitened/adaptive novelty), not constants; current harness caveat applies because device GDFT/AGC is not modelled. |
| Tempo induction and candidate field | [FACT] IOI/median/histogram/autocorrelation examples, 60-200/60-180 ranges in source context (`:60`). | [FACT] ACF via Wiener-Khinchin, candidate generation, pulse-train scoring, musical priors (`:60`). | [FACT] six-second ACF/comb/observation-vector families with prior disagreements (`:60`). | High relevance to live 3:2 tempo-selection pain, but every prior/range/lag value must be rederived for 12.8 kHz, 96-hop, 133.3 Hz AP path. |
| Lock/demotion/tolerance | [FACT] Synesthesia does **not** specify hard lock/demotion or beat-alignment tolerance (`:61-62`). | [FACT] AutoBPM lock/tolerance numeric source is absent/unspecified in the prior table (`:61-62`). | [FACT] Davies/IBT/MIREX tolerance/lock ideas live here, with conflicting windows (`:61-62`). | Do not grade any Synesthesia lock/tolerance row as source-authoritative; `ACADEMIC-or-MISATTRIBUTED` unless it cites Tier 2 directly. |
| Confidence scoring | [FACT] Multiple Synesthesia confidence formulas conflict or differ by document family (`:63`; authority audit `:69`, `:101`). | [FACT] Per-band weighting and smoothed confidence are described but no numeric threshold is specified (`:63`). | [FACT] confidence patterns exist but no direct-port threshold (`:63`). | Adjacent relevance only: K1 V2 confidence magnitude now works enough to unmask selection error; candidates claiming to "fix confidence" need adversarial scrutiny. |
| Octave / metrical correction | [FACT] Synesthesia docs conflict: out-of-range multiply/divide vs clamp (`:64`). | [FACT] AutoBPM has OctaveCorrector/OctaveScorer structure with range, harmonic consistency, priors, temporal consistency (`:64`). | [FACT] prevention-by-prior / classifier / ambiguity approaches (`:64`). | Direct relevance to 120+ 3:2 device error, but Synesthesia itself mainly covers octave, not 3:2; AutoBPM remains parked until Q2. |
| Coast/reacquire | [FACT] Synesthesia and AutoBPM do not specify numerical coast/reacquire (`:65`). | [FACT] NOT SPECIFIED (`:65`). | [FACT] only qualitative recovery ideas (`:65`). | Candidate rows here should usually be `SPECIFY-and-defer`, not `PROMOTE-to-test`, unless host-only falsification is clear. |
| Downbeat/phrase/structure | [FACT] Synesthesia downbeat/phrase not specified; structural detector named without parameters (`:66-67`). | [FACT] downbeat/structure not specified; phrase-like constants are octave-related, not an extractor (`:66-67`). | [FACT] candidate academic downbeat/structure references are partial/offline or convention-level (`:66-67`). | Secondary AP candidates must clear a high relevance bar; vague architecture rows get `REJECT`. |

---

## D · Candidate register (Synesthesia rows — Stage 1–3 complete)

> One row per distinct AP element across both corpora; **no silent omissions** (skipped-after-reading still gets a `REJECT` row). British English. Never paste 44.1 kHz/2048-FFT/vDSP constants into the 12.8 kHz/GDFT/ESP32 pipeline — reference *structure* only.

| id | source (file:line) | ap_layer | what_it_is | provenance | portability | keystone_relevance | fork_current_state | betterment_hypothesis | gate_test (+front-end caveat) | recommendation | justification |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CAND-01 | [FACT] `Synesthesia.RE/02_ALGORITHMS/01_Beat_Detection_Complete.md:108-143`; `05_Algorithm_Specifications.md:58-70` | onset/front-end | [FACT] half-wave spectral flux plus flux-over-threshold onset confidence | RE-INFERRED | rederive | adjacent | [FACT] K1 already ships V2 log spectral flux/adaptive onset in the forward-graft path (`recorp_agents/k1_crosscheck.md`) | [HYPOTHESIS] Not a betterment by itself; K1's live issue is device novelty/selection, not absence of flux. | Existing host onset harness can compare trend; caveat: modelled novelty is not device GDFT/AGC. | REJECT | Direct Synesthesia flux is a weaker duplicate of K1 V2 structure and carries desktop-scale constants. |
| CAND-02 | [FACT] `01_Beat_Detection_Complete.md:149-181`; `beat_tracker_control_extraction.md:50-67` | onset decision | [FACT] adaptive median/std threshold, local-maximum peak pick, refractory guard | RE-INFERRED | rederive | adjacent | [FACT] K1 V2 onset already has median-adaptive threshold and per-band onset surfaces (`recorp_agents/k1_crosscheck.md`) | [HYPOTHESIS] Could only matter if K1's device-front-end thresholding differs materially from host. | Use onset/noise/latency fixtures; caveat: must replay through K1 AP capture or AP_STREAM trend, not Synesthesia magnitudes. | REJECT | Already-shipped capability; no Synesthesia-specific parameter is authority-grade. |
| CAND-03 | [FACT] `05_Algorithm_Specifications.md:72-83`; `01_Beat_Detection_Complete.md:202-238`; `src/main/main_tab5_es7210.cpp:263-309` | tempo induction | [FACT] IOI-derived BPM with median over recent intervals | RE-INFERRED | portable-as-shape | adjacent | [FACT] K1 has harmonic-comb/ACF tempo ranking and V2 confidence/flywheel surfaces (`recorp_agents/k1_crosscheck.md`) | [HYPOTHESIS] IOI median is unlikely to fix the observed 3:2 120+ device selection error. | Existing `tempo_replay.py`/`tempo_accuracy.py`; caveat: K1 onset source quality dominates IOI usefulness. | REJECT | Simpler estimator than K1's current selection path; likely regresses rather than improves. |
| CAND-04 | [FACT] `01_Beat_Detection_Complete.md:240-250`, `:538-553`; `05_Algorithm_Specifications.md:72-83` | tempo range/guard | [FACT] Synesthesia docs include 60-200 BPM valid range and explicit fast-music test expectations | RE-INFERRED | rederive | direct | [FACT] K1 known issue T1 records a 60-155 cap and unrepresentable fast tempi (`2026-06-05-tempo-beat-onset-known-issues.md` §2) | [HYPOTHESIS] Re-deriving range/guard handling may reduce fast-track aliasing and expose whether 120+ 3:2 errors are prior/range interactions. | Run host range sweeps through existing tempo harness; caveat: device front-end/AP_STREAM still required for final truth. | PROMOTE-to-test | This is not a constant port; it is a falsifiable range/guard experiment tied to evidenced K1 pain. |
| CAND-05 | [FACT] `05_Algorithm_Specifications.md:85-97`; `01_Beat_Detection_Complete.md:254-276`; `src/main/main_tab5_es7210_synesthesia_parity.cpp:869-873` | tempo smoothing | [FACT] attack/release EMA smoothing for BPM | RE-INFERRED | rederive | adjacent | [FACT] K1 already has V2 confidence/flywheel behaviour and doctrine requires dt-correct smoothing | [HYPOTHESIS] Frame/hop coefficient transfer would add no proven betterment. | Only acceptable gate is dt-sweep response under K1 timing; caveat: reject 60 fps / 48 kHz coefficient tests. | REJECT | Direct constants are frame/hop-bound and violate the no-desktop-constants rule. |
| CAND-06 | [FACT] `01_Beat_Detection_Complete.md:184-198`, `:278-308`; `beat_tracker_control_extraction.md:113-128` | confidence | [FACT] onset confidence, multi-factor beat confidence, and valid-IOI fraction confidence variants | RE-INFERRED | rederive | adjacent | [FACT] live validation says V2 confidence works enough to lock confidently on the wrong 82 BPM selection (`audio-semantic-post-graft-validation.md` §6.1) | [HYPOTHESIS] More confidence formula work will not solve the current constraint unless it prevents confident wrong locks. | Gate against false-lock, not just median confidence; caveat: AP_STREAM confidence trend is not per-beat truth. | REJECT | Tempting but mis-targeted; the current constraint is selection/front-end, not confidence magnitude. |
| CAND-07 | [FACT] `beat_tracker_control_extraction.md:87-98`, `:143-169`; `beat_tracker_discretization.md:149-156` | octave correction | [FACT] octave multiply/divide can flip, and the model names off/conservative/aggressive octave modes | RE-INFERRED | rederive | adjacent | [FACT] K1 real-music x2 octave failures are documented closed, while 3:2 errors remain (`known-issues.md` §6; validation §6.1) | [HYPOTHESIS] Conservative octave correction may prevent x2 regressions but will not catch non-octave 3:2 selection. | Use synthetic octave-boundary tests; caveat: add 3:2/2:3 classes or the gate misses the live failure. | SPECIFY-and-defer | Useful as guardrail, not a direct fix for the live metrical error. |
| CAND-08 | [FACT] `beat_tracker_control_extraction.md:99-112`, `:157-169`; `src/main/main_tab5_es7210_synesthesia_parity.cpp:890-897` | beat phase | [FACT] bounded PLL/phase-nudge concept for onset-aligned beat phase | RE-INFERRED | rederive | adjacent | [FACT] K1 V2 flywheel already has onset-fed soft PLL and beat_tick lock/coast gating (`recorp_agents/k1_crosscheck.md`) | [HYPOTHESIS] Could matter only if K1 beat-F/CMLt proves phase drift after selection is fixed. | Requires beat-F/CMLt/AMLt gate; caveat: current AP_STREAM cadence cannot prove phase alignment. | SPECIFY-and-defer | Already adjacent to shipped V2; missing measurement must come before design. |
| CAND-09 | [FACT] `beat_tracker_discretization.md:96-116`, `:239-278`; `tunings.json:40-60` | lock state/test contract | [FACT] explicit locked state, hold timer, false-lock, thrash, double-trigger, and reacquire metrics | RE-INFERRED | desktop-only/rederive | direct | [FACT] K1 known issues identify missing beat/onset/continuity harness coverage (`known-issues.md` §4, §7) | [HYPOTHESIS] These metrics could stop false "green" tempo work that still looks wrong. | Specify model/harness gate first; caveat: bucketed model is not firmware or device proof. | PROMOTE-to-test | Best Synesthesia-derived gate candidate: it tests failure modes instead of porting constants. |
| CAND-10 | [FACT] `05_Algorithm_Specifications.md:101-164`; `src/main/main_tab5_es7210.cpp:65-70`, `:311-329` | bass transient | [FACT] 120 Hz IIR/BPF + adaptive bass RMS hit detector | RE-INFERRED | rederive | adjacent | [FACT] K1 already exposes onset/bass/saliency surfaces and V2 onset survival improved in host metrics (`recorp_agents/k1_crosscheck.md`) | [HYPOTHESIS] Bass-only thresholding is unlikely to improve 3:2 tempo selection. | Sine-sweep/kick fixtures only after K1-native coefficients; caveat: do not paste 44.1/48 kHz filter coefficients. | REJECT | Duplicate/secondary and constant-heavy; no direct betterment against live pain. |
| CAND-11 | [FACT] `05_Algorithm_Specifications.md:361-390`; `02_Bass_Isolation_Complete.md:160-175` | event-age feature | [FACT] `syn_BassTime`-style event age resets on hit, advances by dt, and clamps | RE-INFERRED | portable | orthogonal | [INFERENCE] K1 effect/render layers already maintain temporal state; no current AP pain points name missing event-age fields | [HYPOTHESIS] Could support motion memory but not tempo/front-end correctness. | Host unit test is easy; caveat: value is VP/effect-contract dependent. | REJECT | Nice architecture, insufficient concrete AP betterment. |
| CAND-12 | [FACT] `03_Envelope_Tracking_Complete.md:9-95`; `05_Algorithm_Specifications.md:392-469` | energy envelope | [FACT] full-spectrum presence/fade envelopes with attack/release followers | RE-INFERRED | rederive | orthogonal | [FACT] K1 already has RMS/energy/audio-confidence/saliency surfaces in current AP path (`recorp_agents/k1_crosscheck.md`) | [HYPOTHESIS] No evidence this fixes confident wrong tempo or front-end novelty. | Step-response tests possible; caveat: K1 AGC/noise floor defines real normalisation. | REJECT | Duplicate broad energy features; no live-pain leverage. |
| CAND-13 | [FACT] `06_REFERENCE/01_Algorithm_Parameters.md:29-33`, `:98-105`, `:253-261` | spectral descriptors | [FACT] centroid, flatness, dominant-frequency descriptor family | RE-INFERRED | specify/rederive | orthogonal | [FACT] K1 saliency axes exist but harmonic/semantic consumer visibility is not proven (`recorp_agents/k1_crosscheck.md`) | [HYPOTHESIS] May improve colour/semantic clarity later, not tempo selection now. | Needs tonal/noise/brightness fixtures; caveat: descriptor input must be K1 spectrum/bands. | SPECIFY-and-defer | Potentially useful, but secondary and under-sourced for immediate AP register promotion. |
| CAND-14 | [FACT] `src/main/main_tab5_es7210_synesthesia_parity.cpp:1-20`, `:250-316`, `:977-1140` | feature bus/API | [FACT] source-only SynBus-style `syn_*` feature contract, 60 Hz frame latch, BPM oscillators, histories | RE-INFERRED | desktop/source-only | orthogonal | [FACT] K1 has ControlBus/EffectContext/AP_STREAM surfaces; local AGENTS reference protocol docs are absent in this checkout | [HYPOTHESIS] A wholesale bus clone would add memory/API risk without solving AP selection. | No Stage-4 gate; caveat: K1 120 FPS/no-heap/API ownership must be specified first. | REJECT | Source-only, heavy, and not active build authority. |
| CAND-15 | [FACT] `src/main/main_tab5_es7210_synesthesia_parity.cpp:57-60`, `:780-801`, `:1127-1135` | spectrum/history arrays | [FACT] 1024-bin raw/smooth/juiced spectra, 512 waveform, 100-sample histories | RE-INFERRED | desktop/source-only | orthogonal | [FACT] K1 no-heap/render budget and 120 FPS constraints are hard gates | [HYPOTHESIS] Could aid diagnostics/visual texture, not tempo robustness. | Requires memory/performance gate; caveat: no device/build action in this excavation. | REJECT | Too much AP/VP memory surface for no concrete current betterment. |
| CAND-16 | [FACT] `05_Algorithm_Specifications.md:476-616`; `beat_tracker_discretization.md:184-217`, `:324-331`; `README.md:176-183` | test/gate contract | [FACT] Synesthesia docs define silence/noise, fast music, tempo ramp, adaptive threshold, adversarial misses/false positives, and invariants | RE-INFERRED | portable-as-tests | direct | [FACT] K1 known issues call out missing beat-F/onset-F and red/limited tempo replay coverage (`known-issues.md` §4, §7) | [HYPOTHESIS] Better tests can expose confident wrong locks before firmware/device promotion. | Run existing host-only harness where possible; caveat: front-end candidates remain not fully testable without K1 AP/device capture. | PROMOTE-to-test | Strong leverage because it improves the validator rather than importing an RE mechanism. |

---

## E · Stage-4 host-only harness results (Synesthesia promote-to-test rows)

> Host-only, non-destructive. No firmware edits, no flash, no serial/device writes. These runs validate **candidate testability and current gaps**, not Synesthesia correctness and not device-front-end truth.

| Candidate(s) exercised | Command | Result | Register impact |
|---|---|---|---|
| CAND-04, CAND-16 | `/opt/homebrew/bin/python3 scripts/regression-harness/tempo_accuracy.py` | [FACT] `scored=36`, overall Acc1/Acc2 `50.0%/52.8%`, in-range Acc1/Acc2 `56.2%/56.2%`, `octaves={'off': 14, 'x1': 21, 'x1/2': 1}`; report wrote `docs/measurements/tempo-octave-baseline.md`. | Supports range/selection work as a host-testable lane, but leaves device 3:2 front-end truth open. |
| CAND-04, CAND-16 | `/opt/homebrew/bin/python3 scripts/regression-harness/tempo_replay.py` | [FACT] `TEMPO_REPLAY_FAIL failures=2`; 144 BPM clean train detected as 72 and did not lock. | Confirms current synthetic gate already catches a fast-range failure; CAND-04 remains `PROMOTE-to-test`. |
| CAND-09, CAND-16 | `/opt/homebrew/bin/python3 scripts/regression-harness/beat_semantic_metrics.py --label recorp_stage4_current` | [FACT] baseline-path beat-F(x1) `0.031`, CMLt-like `0.010`, IBI continuity `0.156`, settled confidence `0.041`, noise false-lock `0.014`. | Confirms the validator gap and weak beat-continuity surface; do not use BPM accuracy alone as product proof. |
| CAND-09, CAND-16 | `/opt/homebrew/bin/python3 scripts/regression-harness/beat_semantic_metrics.py --candidate-confv2 --label recorp_stage4_confv2` | [FACT] V2 confidence path keeps beat-F(x1) `0.031` / CMLt-like `0.010`, raises settled confidence to `0.620`, and drops noise false-lock to `0.000(maxc=0.530)`. | Confirms confidence magnitude improved while beat placement remains weak; confidence-formula candidates stay rejected. |
| CAND-16 | `/opt/homebrew/bin/python3 scripts/regression-harness/onset_v2_replay.py --out build/audio-semantic-metrics/recorp_stage4_onset_v2.json` | [FACT] onset proxy F1 incumbent `0.0312` → V2 `0.0983`; AGC-clamp survival incumbent `115.38` onsets/min → V2 `923.08` onsets/min. | Supports keeping front-end candidates under the device/front-end caveat: host V2 is better, but AP_STREAM already proved host ceiling can diverge on real device tempo selection. |

---

## F · Delegation ledger (sub-agent evidence consumption)

| ID | Task | Classification | Status | Evidence | Orchestrator consumption |
|---|---|---|---|---|---|
| RECORP-SYN-DOCS | Synesthesia RE docs candidate enumeration | load-bearing reading aid | received | `docs/research/recorp_agents/syn_docs_candidate_rows.md`; return `/tmp/codex_recorp_syn_docs_last.txt` | Consumed as provisional row draft only; source lines re-opened manually before §D rows. |
| RECORP-SYN-SRCSPEC | Synesthesia `src/main` + Quint source/spec candidate enumeration | load-bearing reading aid | received | `docs/research/recorp_agents/syn_srcspec_candidate_rows.md`; return `/tmp/codex_recorp_syn_srcspec_last.txt` | Consumed as provisional row draft only; source lines re-opened manually before §D rows. |
| RECORP-K1-CROSS | K1 fork capability/pain cross-check | load-bearing reading aid | received | `docs/research/recorp_agents/k1_crosscheck.md`; return `/tmp/codex_recorp_k1_cross_last.txt` | Consumed as provisional cross-check; decisive device 3:2 lines re-opened in `audio-semantic-post-graft-validation.md` §6.1 before use. |

**Method risk:** Codex logs contain a non-task system-skill install error (`failed to install system skills: Directory not empty`) but each offload wrote the required evidence artefact and final return. No sub-agent claim was treated as canonical without manual source re-read.

---

## G · Partial Stage-5 ranking (Synesthesia only; Auto-BPM blocked)

**Do-not-repeat ledger:** preserve §A. The core failure to avoid is provenance laundering: Synesthesia is a Tier-1 reference body, not an implementation authority; "Family B" is metadata; Davies/IBT/MIREX are Tier-2 academic; all RE constants are inference until rederived and tested on K1.

**Top Synesthesia-derived promote-to-test / specify targets:**
1. **CAND-16 — test/gate contract**: highest leverage because it improves the validator and directly catches fast tempo, false-lock, and front-end caveat failures.
2. **CAND-09 — lock/false-lock/continuity metrics**: keep as a gate lane; current host runs prove confidence can improve while beat-F stays poor.
3. **CAND-04 — tempo range/guard experiment**: host-testable and tied to the 60-155 cap plus 120+ selection pain; rederive, do not port 200 BPM as a constant.
4. **CAND-07 — conservative octave/metrical guard**: specify-and-defer; useful to prevent regressions, but insufficient for the live 3:2 error without new 3:2/2:3 scoring.
5. **CAND-08 — phase-nudge/PLL gate**: specify-and-defer until beat-F/CMLt/AMLt proves the post-selection phase problem.

**Top tempting rejects:**
1. **CAND-06 confidence formulas**: tempting because they look musical; rejected because V2 confidence works and selection is the constraint.
2. **CAND-03 IOI median BPM**: tempting because it is simple; rejected as weaker than K1's current ACF/comb path.
3. **CAND-01/CAND-02 spectral flux/adaptive onset**: tempting because source-backed; rejected as already-shipped structure in K1 V2 and still not device-proof.
4. **CAND-14 SynBus clone**: tempting API surface; rejected as source-only/heavy and not an AP selection fix.
5. **CAND-10 bass BPF/hit detector**: tempting impact primitive; rejected as duplicate/secondary with no live-pain leverage.

**Open authority questions for joint session:**
- Q1 remains per-candidate: is any RE parameter actually measured from Synesthesia, or only inferred?
- Q2 blocks Auto-BPM: Captain must designate the canonical Auto-BPM document among the three candidates in §C.
- Q3 remains absolute: no candidate becomes canonical outside the joint promotion session.
- Local environment caveat: pasted AGENTS reference docs under `firmware-v3/docs/reference` and `docs/protocol` are absent in this checkout; any future API/contract claim must re-anchor to the live local surface or the intended sibling repo explicitly.

---

## H · Continuation plan (remaining scope)

Stage 0, Stage-0-full, Synesthesia Stage 1–3, Synesthesia host-only Stage 4, and Synesthesia partial Stage 5 are complete. Remaining:

1. **Stage-0-full:** **DONE 2026-06-05** — prior-art audits read, §A source-grounded, MusicAware Tier table extended in §C2, local missing-reference-doc paths recorded.
2. **Stage 1–3 (Synesthesia):** **DONE 2026-06-05** — 16 rows in §D, all graded; promotes nothing canonical.
3. **Stage 1–3 (Auto-BPM):** same — **BLOCKED on Q2** (Captain picks canonical doc).
4. **Stage 4:** **DONE for Synesthesia rows** — host-only results in §E; anything requiring firmware/device remains deferred.
5. **Stage 5:** **PARTIAL DONE for Synesthesia rows** — §G; final cross-corpus ranking waits for Auto-BPM Q2.

**Checkpoints (per §10):** report at Stage-0-full-complete and Stage-2-complete (all graded) before Stage-4 tests. **Promote nothing.**

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:Orchestrator | Created — Stage-0 foundation: environment verified (all paths bar Auto-BPM canonical resolve), do-not-repeat ledger seeded from the brief (audit-text verification deferred), register skeleton, §8 Auto-BPM access-gap escalation (Q2), continuation plan. Stages 1–5 NOT run (context ceiling). Promotes nothing. |
| 2026-06-05 | agent:Codex | Stage-0-full update — reconciled §A against authority audit / MusicAware audit / RFC / handover, added missing-local-reference-doc environment caveat, extended the MusicAware Tier table as §C2, and left Auto-BPM blocked on Q2. No firmware/device/test/commit action. |
| 2026-06-05 | agent:Codex | Synesthesia pass — populated 16 graded §D rows, consumed three Codex offload scratch artefacts under `docs/research/recorp_agents/`, ran host-only Stage-4 harness commands, added delegation ledger and partial Stage-5 ranking. Auto-BPM remains blocked on Q2. No firmware/device/commit action. |
