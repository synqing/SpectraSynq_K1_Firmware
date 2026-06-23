---
abstract: "Oracle calibration GROUND TRUTH: the Captain's verbatim 2026-06-04 on-device eyes-on verdicts for the 14-effect wall (modes 18-30, plus mode 31 unscored), captured from wf/integration. Structured score sheet (mode_id | effect | score | tag | one-line verdict) for STEP 0 of the 'Living Plate, Liquid Grammar, Faithful Eye' build plan. Top score = beat_phase_scroll 5.5/10 (praised-partial). Dead 0/10 cluster (modes 19-25 region) + flash-BANNED (kick_flash_overlay) + sparkle-near-banned (flux_sparkle) + sterile-reject (pitch_contour -20, timbre_reach -20, structure_arc -4000). Two promising: harmonic_split 3/10, beat_comet_quantise 4/10. Tags: dead/flash-BANNED/sparkle-near-banned/sterile/promising/praised-partial/unscored. This is the leave-one-out calibration target for the faithful-plate oracle (NOT in-sample Spearman). Read before calibrating render_replay or scoring any of the 14 effects."
---

# Effect Verdict Sheet — Captain Eyes-On Ground Truth (2026-06-04)

> **Purpose:** This is the **oracle calibration ground truth** required by STEP 0
> of the "Living Plate, Liquid Grammar, Faithful Eye" build plan (see companion
> `03-effects-archaeology-synthesis-2026-06-04.md`). It is the Captain's verbatim
> on-device verdict from a 2026-06-04 eyes-on of `wf/integration`. The
> faithful-plate oracle (Layer D / `render_replay.py`) must be calibrated against
> these scores with **leave-one-out**, never in-sample Spearman.
>
> **Scoring nature:** The scores are the Captain's verbatim figures, including the
> deliberately hyperbolic negative values (e.g. -4000, -50,000,000) which encode
> *class severity* (sterile-reject vs flash-BANNED vs sparkle-near-banned), not a
> linear scale. For oracle calibration, treat them ordinally + by tag, not as
> linear regression targets — the tag column is the load-bearing signal.

## Verdict table

| mode_id | effect | score | tag | one-line verdict |
|---------|--------|-------|-----|------------------|
| 18 | BEAT PHASE SCROLL | 5.5/10 | praised-partial | Visual not bad; NO semantic association with the music; "magical" when it appears to match (bloom shapes + palette); "full bloom" reads like ground mist at the bottom edge; but when it locks → sterile single blobs pulsing from the middle, no life, no meaning. (TOP score of the sweep.) |
| 19 | DOWNBEAT BLOOM | 0/10 | dead | No idea what it does; 100% unusable; no consistency; no fallback. |
| 20 | ONSET RIPPLE | 0/10 | dead | Same — unusable. |
| 21 | ONSET PALETTE STEP | 0/10 | dead | Same — unusable. |
| 22 | BEAT MIRROR FLIP | 0/10 | dead | Marginally better but 100% unreliable; ALL onset/beat effects MUST have a low-confidence fallback. |
| 23 | PITCH CONTOUR | -20/10 | sterile | Utter dog shit; no idea what it's doing. |
| 24 | SPECTRO WATERFALL | 0/10 | dead | Promising name; no idea what's going on. |
| 25 | TIMBRE REACH | 0/10 | dead | Not working. |
| 26 | STRUCTURE ARC | -4000/10 | dead | Dead. |
| 27 | KICK FLASH OVERLAY | -50000000/10 | flash-BANNED | All flash-class effects are BANNED. |
| 28 | HARMONIC SPLIT | 3/10 | promising | Fails, but looks promising. |
| 29 | FLUX SPARKLE | -200000000000/10 | sparkle-near-banned | Sparkle = flash's cousin; not fully written off but dog shit. |
| 30 | BEAT COMET QUANTISE | 4/10 | promising | Comet-class needs an audio-coupling overhaul; supposed to be bass-tuned but can't track bass; the trail looks visually impactful when it does respond. (promising-form / broken-coupling) |
| 31 | PHASE BREATHE | UNSCORED | unscored | Not in the Captain's list — untested, or possibly conflated with BEAT PHASE SCROLL (mode 18). No verdict given. |

## Tag legend

| Tag | Meaning |
|-----|---------|
| `dead` | Scored 0/10 (or hyperbolic-negative as "dead") — illegible / unusable / no fallback. |
| `flash-BANNED` | Whole-strip flash class; categorically banned. |
| `sparkle-near-banned` | Sparkle = flash's cousin; not fully written off but rejected. |
| `sterile` | Sterile / "no idea what it's doing" / reject. |
| `promising` | Fails as shipped but the form/intent is worth pursuing. |
| `praised-partial` | Has a "magical" moment but no consistent semantic music association. |
| `unscored` | Not in the Captain's verbal list. |

## Calibration notes for the oracle

- **Tag is the load-bearing target**, not the raw number. The faithful-plate
  oracle's gate (per the build plan) is: rank praised/promising effects top AND
  the dead/flash/sparkle/sterile cluster bottom-quartile.
- **Top effect = mode 18 (beat_phase_scroll, 5.5/10).** Any oracle that does not
  rank this above the 0/10 cluster is mis-calibrated. Note this directly
  contradicts the archaeology brief's `evidence_trail` claim that
  beat_phase_scroll "scored 0/10 despite having a fallback" — see the
  Orchestrator note in the companion brief.
- **The two `promising` effects** (harmonic_split 3/10, beat_comet_quantise
  4/10) are the next-best below the praised one; an oracle should place them
  between the praised top and the dead cluster.
- **Hyperbolic negatives encode CLASS, not magnitude.** -4000 (structure_arc,
  dead), -50,000,000 (kick_flash_overlay, flash-BANNED), -200,000,000,000
  (flux_sparkle, sparkle-near-banned). The flash/sparkle class is the most
  severely rejected — the oracle's flicker/temporal-frequency penalty must drive
  these to the absolute bottom.
- **All onset/beat effects MUST have a low-confidence fallback** (Captain, on
  mode 22). This is the always-alive requirement restated on-device.
- **Mode 30's verdict is the canonical "tracks bass" falsification target:**
  "supposed to be bass-tuned but can't track bass." The oracle's
  `Pearson(|dRMS|, |dBright|)` band-coupling metric must catch exactly this.

## Cross-reference: brief vs verdict-sheet inconsistencies

| Item | Brief claims | Verdict sheet (ground truth) | Resolution |
|------|--------------|------------------------------|------------|
| beat_phase_scroll | "always-alive floor, STILL scored 0/10" (used as falsification anchor) | 5.5/10 — TOP score, praised-partial | Brief OVERSTATED. The "0/10 despite fallback" anchor is wrong for this effect. |
| timbre_reach | "has TR_SILENCE_VU 0.05 floor, STILL scored 0/10" | -20/10 (sterile) — or 0/10-class "not working" | Thesis (floor ≠ sufficient) HOLDS on timbre_reach alone. |
| flash/sparkle in-tree | kick_flash_overlay banned; flux_sparkle near-banned (Open Decision #4 framed as open) | -50,000,000 / -200,000,000,000 — emphatic ban | Strengthens de-registration; not merely "near-banned." |
| phase_breathe (mode 31) | not named in brief | UNSCORED | No claim made; flagged as untested/conflated. |

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:orchestrator | Created — Captain verbatim 2026-06-04 eyes-on verdicts captured as oracle calibration ground truth (STEP 0 of wf_f423b1c3-749 build plan) |
