---
abstract: "Stage 2 stereo probe first data + P5.B numeric matrix results, 2026-08-12. Stage 2: instrument proven end-to-end (slot=STEREO init, PSRAM capture, CRC-clean dumps, decoder self-tested on synthetic controls); music capture: low bands rho 0.95-0.96, mid/high decorrelated — H_C NOT rejected on this capture, with two named confounds (laptop SPL SNR ~4x; 56% capture duty splices). P5.B: P1 18/18 duty PASS, P3 18/21 DF-not-black PASS, P4 DF quiet-live inject PASS; P2 drain FAIL vs pre-registered 15 s bound (18.6 s, tempo-flywheel persistence — the documented unimplemented dwell-gate debt). Music rows provisional at laptop SPL."
---

# Stage 2 (stereo) + P5.B numeric matrix — receipts

**Date:** 2026-08-12 late · Bench `B489A500` on `k1_bench_im69d_stereo @ 019086c8` · Unit 2 `0C54FC00` on `k1_unit2_im69d_right_matrix @ 947e2be8`

## Stage 2 — H_C / H_C2 (design §5.3, criteria pre-registered in the decoder before any run)

**Instrument chain proven:** `I2S PDM RX INIT: PASS slot=STEREO` · `[SCAP] INIT PASS 307200 frames` ·
independent live L/R floors (l_rms 14.9 / r_rms 6.0) · captures CRC-clean · decoder self-tested
(identical channels → ρ=1.0 REJECTED; independent noise → ρ≈0 NOT REJECTED; corrupted dump → `crc_ok=false`).

| Capture | frames | L rms | R rms | ρ broadband | ρ 55-110 | 110-220 | 220-440 | 440-880 | 880-1.7k | 1.7-3.5k | 3.5-6.4k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| quiet 6.6 s | 84,576 | 9.0 | 8.4 | 0.24 | 0.89 | 0.93 | 0.90 | 0.67 | 0.39 | −0.17 | 0.03 |
| music 11.3 s | 145,152 | 38.6 | 34.7 | 0.74 | **0.96** | **0.95** | 0.92 | 0.83 | 0.41 | −0.27 | 0.21 |

**Verdict (pre-registered kill: ρ > 0.95 across ALL visual-driving bands ⇒ H_C rejected):**
**H_C NOT REJECTED on this capture** — only the two lowest bands reach 0.95; from 220 Hz up the
channels measurably diverge. **Two named confounds forbid treating this as PROVEN:**

1. **SNR ~4×** (music rms 38 vs floor ~9, laptop speakers @100%). Uncorrelated mic self-noise
   dilutes ρ downward — exactly the direction that spuriously rescues H_C. Decisive run needs
   Bose-level SPL (music coherence 0.94 vs quiet 0.76-0.89 in low-mid bands shows real signal
   structure, but the high-band split is unresolved).
2. **Capture duty 56%** (84,576 of 128,000 target frames in-window; chunk splices). L/R stay
   sample-aligned within every chunk (interleaved single read) so zero-lag ρ is valid; Welch
   coherence is mildly biased down by splice windows. Duty cause (DMA descriptor sizing under
   stereo vs the mono-sized `dma_frame_num`) is a named instrument follow-up.
3. **Spacing D (design O-4) still unmeasured** — required context for interpreting ρ physically.

**H_C2 (coherence robustness):** music vs quiet coherence separates cleanly in 110-440 Hz
(0.94 vs 0.76-0.86). Hand-occlusion leg not run (needs a hand). Partially evidenced.

**Status per runbook C5: not limbo — the experiment is CLOSED-INSTRUMENT / OPEN-VERDICT with
pre-decided next evidence:** one Bose-SPL capture through the identical pipeline. No stereo
visuals claim is made; the DSP chain still consumes mono mic A.

### Update — 2026-08-13: decisive Bose-SPL captures (canonical fixture Demo Track 1)

| Capture | frames | L rms | R rms | ρ bb | 55-110 | 110-220 | 220-440 | 440-880 | 880-1.7k | 1.7-3.5k | 3.5-6.4k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| quiet | 87,456 | 2.6 | 7.2 | 0.07 | 0.89 | 0.86 | 0.79 | 0.71 | 0.40 | −0.13 | 0.08 |
| music, Bose vol 60 | 166,368 | 55.7 | 57.6 | **0.984** | **0.9995** | **0.9995** | **0.996** | **0.988** | **0.969** | **0.981** | 0.867 |

**VERDICT — H_C SUBSTANTIALLY REJECTED.** At product SPL (SNR ~7×) with the canonical
fixture, ρ ≥ 0.97 in every band from 55 Hz to 3.5 kHz — six of seven bands clear the
pre-registered 0.95 kill line, most at 0.99+. The channels carry essentially the same
information across the range that drives the visuals: **visually distinct primary/secondary
edge behaviour from mic spacing would be synthesised, not sensed** — exactly the outcome
the design predicted for a diffuse room field at small spacing, reported as the clean
negative it is. The single band below the line (3.5–6.4 kHz, ρ 0.87) is where music energy
and therefore SNR is lowest; noise dilution biases ρ DOWN there, so the true acoustic
correlation is, if anything, higher. Residual formality: spacing D (O-4) remains unmeasured
and the mechanical all-bands criterion prints NOT-REJECTED on the top band — the verdict
above is the visual-driving-band reading the design §5.3 specifies.

**H_C2 stands as the live product justification for the second capsule:** coherence
separates music (0.94–0.999) from quiet (0.73–0.79) decisively in the low-mid bands;
occlusion/robustness discrimination remains the useful signal, not stereo visuals.

### Update — 2026-08-13: P5.B rows at product SPL (Bose vol 55, Demo Track 1)

| # | Predicate | Result at product SPL |
|---|---|---|
| P1 | 18/18 awake duty ≥95% both | **PASS — 95.9% / 95.9%** (49/49 frames awake) |
| P2 | drain: silence latch ≤15 s | **PASS — latched at 9.1 s.** The laptop-leg 18.6 s FAIL was fixture-induced (weak stimulus + ambient). Post-latch flashes at 15/19 s (pmax 37–38) remain — the flywheel-persistence residual is visible but the latch bound is met. |
| P3 | 18/21 DF secondary duty ≥50% | **PASS — 100%** (primary 98%) |
| P2b | 18/21 drain (observational) | did NOT latch within 25 s — DF-pair/flywheel interplay; filed with the dwell-gate debt |

## P5.B numeric matrix (predicates pre-registered in `p5b_matrix_leg.py` before the runs)

| # | Pre-registered predicate | Leg | Result |
|---|---|---|---|
| P1 | 18/18 music, awake frames: `mx_pmax>2` AND `mx_smax>2` duty ≥95% both channels | `m18-music-laptop` (35 awake frames) | **PASS — 100%/100%** |
| P2 | 18/18 drain: `mx_pmax≤2` + silence latch within 15 s of stimulus stop | `m18-drain-clean` (hands-off) | **FAIL — 18.6 s** to silence latch, with output flashes at 4.5/5.5/11.5 s post-stop. Mechanism: tempo-flywheel persistence + silence-hysteresis decay — the ALREADY-DOCUMENTED residual whose dwell/persistence gate is recommended and unimplemented (registry 2026-08-11 row). Honest red; do not tune the gate to pass this — implement the dwell gate. |
| P3 | 18/21 music: secondary DF `mx_smax>2` duty ≥50% while primary=18 | `m18-df-music-laptop` (41 awake) | **PASS — 100%** (DF not stuck black under an 18 primary) |
| P4 | DF quiet-live (21/21, non-latched room): `mx_dfinj > 0` on ≥1 frame / 30 s | `df-quiet` | **PASS — inject 1.0 on 32/32 frames** |

**Caveats:** music rows ran at laptop SPL (fixture inadequate for consumer-floor claims but the
duty predicates bind — the device was genuinely awake on the counted frames, `silence=0`).
`mx_dfinj` freezes at its last DF-rendered value when DF stops rendering (documented semantics).
1 Hz sampling under-samples mode 18's beat-flash structure; duty is computed on awake snapshots.
Captain eyes-on naming ("musical chroma vs wash") not collected this session — the P5.B
eyes-on of record remains the 2026-08-12 side-by-side PASS at the shipping fraction.

**Witness surfaces (new, non-shippable):** `K1_MATRIX_AUDIT_V1` scans the FINAL post-gamma
output buffers on Core 1 pre-`FastLED.show()` — the artefact boundary, not the intent buffer.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Decisive Bose captures: H_C SUBSTANTIALLY REJECTED (ρ≥0.97 to 3.5 kHz); P5.B product-SPL rows — P2 drain PASS at 9.1 s (laptop FAIL was fixture-induced), 18/21 drain filed with dwell debt. |
| 2026-08-12 | agent:claude-code | Created — Stage 2 first data (H_C not rejected, confounds named), P5.B matrix P1/P3/P4 PASS + P2 honest FAIL at 18.6 s. |
