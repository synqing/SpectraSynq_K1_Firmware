---
abstract: "AUTHORITATIVE correction for the 2026-06-04 audio-primitive session (saliency + tempo ACF). After adversarial back-testing AND the orchestrator's own re-runs, several SSA validator claims were WRONG and had propagated into chat/docs — once to the brink of reverting good work. This doc is the cross-confirmed final verdict per contested claim, with the re-runnable command for each, and names which SSA erred. SUPERSEDES the contradicting claims in V-OCTAVE.md (flat-ACF), the donor recon (v3 'Goertzel-only'), and the ceiling characterisation (53% 'ceiling'). Read this before trusting any single validator doc from this session."
---

# Audio-Primitive Session — Claim Reconciliation & Corrections (2026-06-04)

> **Why this exists.** During this session the orchestrator repeatedly relayed SSA validator
> *prose* as established fact (the load-bearing-edges meta-flaw, at the validation layer). Two of
> those relayed claims were flatly wrong (T2, V-OCTAVE) — and on the strength of V-OCTAVE the
> orchestrator recommended **reverting `0929814`**, which would have destroyed a real, large,
> now-hardware-validated gain. A forced back-test + the orchestrator's own re-runs caught it.
> This doc is the corrected record. **Every claim below carries the command that reproduces it.**

## 1 · Corrections — claims that were WRONG and are now overturned

| Wrong claim (source) | Corrected fact | Evidence (re-runnable) |
|---|---|---|
| "ACF salience is flat (std 0.029), barely functioning" — **V-OCTAVE** | ACF salience std ≈ **0.28** (min 0.18 / max 0.35); 0/32 tracks match 0.029. The "0.029" was a harness artefact on a non-firmware ACF. | `python3 scripts/regression-harness/bt_acf_4way.py` |
| "`0929814` (ACF) is a regression to revert" — **orchestrator chat, from V-OCTAVE** | The ACF is the **load-bearing signal**: `acf_only` 40.6% vs `prior_only` 15.6% Acc2 (+25pp), +15.6pp over the Step-2 signal it replaced. **KEEP it.** | `bt_acf_4way.py` (4-way ablation) |
| "octave-err is low-bin pinning + prior, not ACF harmonics; an arbiter won't fix it" — **V-OCTAVE** | octave-err **is** ACF harmonic 2×-peaks (sal@2×GT 0.95–1.0 vs sal@GT 0.07–0.69). The arbiter verdict was scored on the false flat-ACF premise and must be re-derived against the real peaked ACF. | `bt_acf_4way.py` |
| "v3 is Goertzel-only — no ACF, no prior, no octave arbiter" — **T2** | v3 has **both**: `esv11_pick_top_tempo_bin_octave_aware()` (octave arbiter, **called in production** `EsV11Backend.cpp:182,380`) AND autocorrelation in `BeatTracker.h` (`kMaxLag=256`). A portable arbiter donor exists. | `grep -rn esv11_pick_top_tempo_bin_octave_aware <v3>` (orchestrator-run) |
| "the arbiter is in `vendor/tempo.h`" — **V-RECON** | Wrong location — that file does not exist; it lives in the esv11 backend. (V-RECON was right it EXISTS, wrong on where.) | `ls <v3>/vendor/tempo.h` → no such file |
| "53% is the ACF ceiling (44 Hz/parab/raw)" — **T4** | True ceiling **56.2%** Acc2 (133 Hz); 53.1% is the **44 Hz-parabolic sub-ceiling**; 44 Hz-integer = 46.9%. | `python3 scripts/regression-harness/acf_ceiling_sweep.py` |
| "the 40.6 vs 53 *gap* is a peer comparison to close" — **orchestrator framing** | NOT comparable: 53% is a **non-causal whole-clip ACF oracle**; 40.6% is the **causal firmware** tracker. Same scorer, different detector. The direction (improve firmware) holds; the "peer gap" framing was wrong. | `scripts/regression-harness/acf_gap_ablation.py` |

## 2 · Cross-confirmed TRUE state (each verified by ≥2 independent methods or the orchestrator's own re-run)

| Claim | Grade | Basis |
|---|---|---|
| Tempo ACF (`0929814`) is a real gain: +15.6pp Acc2 over Step-2, +25pp over prior-alone | **CONFIRMED** | orchestrator re-ran `bt_acf_4way.py` + B-ACF (replica 32/32 per-track faithful to compiled firmware) |
| On hardware (1401, real mic/music): detects **128 BPM → 127–131** (±2.3%, exact-tempo Acc1 PASS) — N=1 | **CONFIRMED** | orchestrator's 35 s on-device capture, Captain's 128 BPM ground truth |
| Absolute numbers are NOT inflated by the wide forgiveness set (MIREX {½,1,2} ≡ wide on this corpus) | **CONFIRMED** | `mirex_rescore.py` |
| My `sb_compute_acf_salience()` is mathematically correct | **CONFIRMED** | V-ACFCODE synthetic test + B-ACF (correct code; some real novelty is just less periodic) |
| RC-4: instantaneous saliency is structure-blind → periodicity pivot justified | **CROSS-CONFIRMED (3×)** | orchestrator benchmark + V-RC4 + B-SAL's independent Foote-SSM (recall ≤ chance) |

## 3 · Genuinely OPEN (PROVISIONAL — not yet re-run/closed by the orchestrator)

- **Octave defence** — port v3's `esv11_pick_top_tempo_bin_octave_aware` (form known: magnitude-ratio 0.56/0.72 + persistence-50 gate; **constants to re-validate on port, not transcribe**).
- **Confidence/lock marginal** — on the *correct* 128 BPM hardware detection, `conf` settled ~0.30 (< 0.60 lock gate). Value right, confidence under-asserting. Task #6 (octave-aware confidence + Schmitt lock).
- **Ceiling gap = rolling-512 window** (B-ACF, single-source) — window length / accumulating-ACF is the lever toward the 53/56% host ceiling.

## 4 · The meta-lesson (binding, for every future session)
The failure was not the firmware — it was **canonising SSA prose as fact**. Two relayed claims were wrong (T2, V-OCTAVE); one nearly destroyed a real gain. The standing contract: **no claim reaches a decision or a doc as fact unless the orchestrator re-ran the territory itself.** Every row in §1–§2 carries that command; the §3 rows stay PROVISIONAL until run.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:CTO | Created — authoritative reconciliation of the audio-primitive session after adversarial back-test + own re-runs; overturns V-OCTAVE (flat-ACF), T2 (v3 Goertzel-only), T4 (53% ceiling), and the orchestrator's revert recommendation; pins the cross-confirmed true state + the still-open items. |
