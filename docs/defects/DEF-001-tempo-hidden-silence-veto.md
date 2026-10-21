# DEF-001 — Tempo tracker hidden silence veto (k1_tempo.cpp)

Status: FIX-IN-LANE (partial: A3 noise/drone/sweep/release open) · Opened: 2026-10-21 · Builds affected: k1_main_rpl_im69d (and any build where the
tracker's contrast silence gate runs on sqrt-domain novelty) · Owner lane: lane/k1-tempo-lock-r1

## Mechanism (FACT, source-verified)
- Producer `calculate_novelty()` (audio/k1_gdft_core.cpp:737) stores `sqrtf(novelty_now)`.
- Tracker `k1_check_silence()` (audio/k1_tempo.cpp ~509-535) autoranges, halves/doubles, applies a
  SECOND `sqrtf`, then declares silence when `1 - (max - min) > 0.5` over the last 128 emits.
- Output gates (`k1_build_output`, ~1306-1333): `locked && !silence`, `beat_tick && !silence`,
  `confidence *= (1 - silence_level)`.
- Result on the R3 music passage: internal `k1_locked_v2` true on 100 % of scored frames at 127 BPM,
  published lock 0, ticks 0, max published confidence 0.664, while the producer's `audio.silence` = 0.

## Reproduction
- Emulator: `tools/esp_emulator/run.py` music-a case on aaa1f307 → `PASS_timing_but_weak_lock`.
- Host: `_scratch/esp-emulator/next-phase-tempo-candidate-001/predicate-trace/` (ENABLE_TEMPO_STREAM
  replay of the captured N-lines shows v2_locked=1, silence_detected=1 on the same frames).
- Decisive input test (no model in loop): replay the captured novelty raised to power 2 → lock 1.00,
  21 ticks at 484 ms median (Step 3b, novelty-attribution/FINDINGS.md).

## History — why this record exists
- 2026-08-11 commit 7d932083 diagnosed this exact mechanism ("novelty-contrast 'silence' latch while
  AP silence=0 … force-clears lock/beat at the output — so conf can spike to 0.6+ with lock=0
  forever") and patched it under K1_MIC_IM73D_PDM_V1 (gate skipped, novelty ×4, lock floor 0.28).
- 2026-08-11 commit 1bdf54d0 tombstoned the patch (mic identity voided). The finding was lost with it.
- 2026-10-20 commit 05ace4cb re-diagnosed it from scratch. 70 days with the fault in the product build.
- Rule from this: a tombstone closes a FIX, never a DEFECT. Any future tombstone touching the silence
  gate, novelty scaling or lock thresholds must cite this DEF and leave it open or close it with evidence.

## Known non-fixes (do not repeat)
- Novelty ×N boost (symptomatic; level- and mic-dependent) — 7d932083, tombstoned.
- Lower lock threshold (0.28) — same.
- Disable the gate without replacing the silence source — breaks silence release (R7).

## Fix direction (ruled by Captain 2026-10-21, R7)
Silence decision moves to the producer's `audio.silence`; tracker keeps history decay on silence; drone
and noise rejection is confidence's job and must be proven by the synthetic tests. Flag:
K1_TEMPO_SILENCE_FROM_PRODUCER_V1. Pre-sqrt tempo-only input tap: K1_TEMPO_NOVELTY_LINEAR_V1
(patch sha256 76df3146…). Closure = DEF-001 acceptance in lane R1 (R3 music PASS_timing_and_tempo,
silence/drone/noise/release tests, off-flag byte-identical).

## Related
- DEF-002 (winner selection chooses 3:2 metrical level; confidence AUC ≈ 0.5) — separate defect,
  exposed, not caused, by fixing this one.
- docs/architecture/tempo-lock-hardening-plan.md (2026-10-20 update) · artefact "Tempo Fault Forensics".
- Lane R1 receipts: docs/receipts/tempo-lock-r1/ · draft AGENTS.md invariants (Captain applies):
  docs/patches/agents-md-tempo-invariants.patch.

## Status log
| Date | Status | Evidence |
|---|---|---|
| 2026-10-21 | OPEN — Phase 0 measured | R9 level sweep (docs/receipts/tempo-lock-r1/p0.1-level-sweep.json): clipping falls to 0 at -6 dB and below, tracker-internal silence stays 100 % and published lock 0 at every level → not a fixture-clipping artefact. |
| 2026-10-21 | FIX-IN-LANE (partial) | Phase 1 on lane/k1-tempo-lock-r1: R3 music PASS_timing_and_tempo, silence dark, M1/M2 green (p1.3-*, p1.4-*, p1.5-*). Still red: noise 0.46 / drone 0.52 confidence, log-sweep lock, release 5.94 s (p1.5-behaviour-lane.json). Not closable until A3 passes. |
| 2026-10-21 | FIX-IN-LANE (partial) | Spectral presence (K1_TEMPO_SPECTRAL_PRESENCE_V1): Phase 1.5 behaviour green on the emulator (p3-sp-p15-behaviour); known limit brown noise. M2 holds with the spectrum transformed, erased-spectrum control fails (p3-m2-l1sp-*). Cost 0.96x shipped incl. per-frame presence (a7-cost-lane-vs-shipped). Closure needs A1, which needs a lock: under rule 3.3 (K1_TEMPO_LOCK_OFF_V1) A1 cannot pass — Captain decision pending. |
