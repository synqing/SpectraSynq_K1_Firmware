---
abstract: "Red-team (perceptual/product lens) attack on the dual-K1 sync draft plan v0.1. Verdict: FLAWED at the rendering/product layer — the plan conflates two incompatible mirror-split mechanisms (resample-upsample vs native-160-px arm), so either the '2x spatial detail' claim or the 'zero per-effect work' claim is false; every mode's focal origin relocates into the physical bezel gap; the cheapest kill test (zero-firmware physical seam trial) is sequenced last; v1 roster excludes every beat-locked showpiece; mirrored-twin sync is the buried roster-complete v1. Transport/topology core (leader feature-stream, pixel-stream rejection, Phase-0 measure-first) survives attack."
---

# Red-Team — Perceptual / Product Lens (dual-K1 sync draft v0.1)

Reviewer stance: adversarial. Every attack below was verified against source (file:line) or the lane's own evidence files. Steel-man honesty section at the end lists what survived.

## KILL — A1: The plan promises two incompatible rendering mechanisms; each falsifies one of its headline perceptual claims

**Claim attacked:** plan §1.1 "each K1 renders the same authoritative 160-px arm … 14/22 modes need zero geometry work" + §0.3 "unique content doubles from 80 px to 160 px per arm … perceptual upgrade" + findings.md §3 "2x spatial detail".

**The code facts:**
- Effects render ONLY into the upper half [80..159] of the 160-px canvas and rely on `mirror_image_downwards()` to fill [0..79] (`visual/led_utilities.h:1222-1232`). With mirror simply OFF, the lower half is stale residue on every mode except the waveform family, which alone has an explicit unmirrored full-strip path (`effects/light_mode_waveform_fast.cpp:160-177`).
- The plan's cited mechanism is the canvas→strip resample (`scale_to_strip`/`init_lerp_params`, `led_utilities.h:848-899`, REVERSE_ORDER at `:1014`). That mechanism can only take the EXISTING 80-px arm and upsample it 2x onto the 160-LED strip.
- `NUM_FREQS` stays 80 (`system/constants.h:106-110`, non-negotiable per the plan's own non-goals), so the information content of a frame is unchanged regardless of mechanism.

**Consequence — pick one, lose a headline:**
- **Mechanism 1 (resample window, zero per-effect work):** the widened surface is the SAME 80 px of information bilinearly stretched 2x, at 2x physical velocity, softened by 2x upsample plus LGP blur. "2x spatial detail" is FALSE — detail per LED *halves*. The customer-visible result is "one K1's picture, physically bigger and blurrier, with a bezel gap through the middle of it". The perceptual-upgrade premise of §0.3 collapses to "bigger", which must then compete honestly with the mirrored-twins alternative (A5).
- **Mechanism 2 (effects natively render a 160-px arm):** real position-resolution doubling for dot/particle modes (rivers still stretch 80 bins over 160 px — 2 px/bin, LESS dense, never "2x detail"), but "zero geometry work" is FALSE. Verified per-effect work beyond the plan's single "BLOOM mirror special-case": BLOOM's centre insert sits at px 79/80 (`light_mode_bloom.cpp:84-87`) and its edge fade darkens BOTH strip ends over NR/4 (`:95-109`) — under a seam-origin arm the fade puts a dark notch exactly at the virtual centre and the insert sits mid-arm; AURORA's stamp, EMBER's `reach·HALF` extent, and every HALF-anchored literal need the same origin/extent relocation. That is a per-effect pass over most of "class A", not one generic transform.

The census's class-A grading ("generic transform suffices") is only true of Mechanism 1; the "renders the arm at 160 px" language and the 2x-detail claim belong to Mechanism 2. The plan inherits the best claim of each. **Phase 2 as scoped and gated is built on this conflation and is invalid until the mechanism is pinned and re-costed.**

**Fix:** pin ONE mechanism in v0.2. If Mechanism 1: strike "2x spatial detail", restate the benefit as "one larger surface", and let that honest statement fight A5. If Mechanism 2: replace "zero geometry work" with a per-effect origin/extent/fade work item per mode (start with the verified BLOOM list) and re-cost Phase 2.

## MAJOR — A2: Every mode's focal origin relocates into the physical bezel gap, and no phase measures whether that reads as one origin

**Claim attacked:** "seam-centred mirror-split will look good"; §0.3 "the two-unit merge is a product moment".

All 22 enabled modes are centre-origin (census §2, verified). Seam-centred widening therefore moves the single most salient pixel of every mode — BLOOM/BLOOM_FAST's beat insert, AURORA's stamp, COMET/TEMPO_COMET/PULSE_PRISM spawns, EMBER's anchor — from the clean middle of one plate to the junction between two enclosures: the one location with no LEDs, two plate edges, and unmeasured LGP edge behaviour. Pixel pitch and LGP blur width are explicitly open (sync-timing §7.1); the plan never states the physical gap width in pixel-equivalents. A birth event straddling a dark gap can read as TWO simultaneous births (one per plate edge) — the correspondence data (28–32 px, `docs/measurements/apparent-motion-on-k1.md` §5/§8) bounds crossing objects, not paired onsets flanking a dark discontinuity, and bilateral-symmetry/vernier judgement at a fixed seam is more acute than motion correspondence. The ~10 ms budget was derived for objects *crossing* the seam; under centre-origin widening almost nothing crosses — content is born at the seam and departs both ways. The budget may be measuring the wrong percept.

**Fix:** state the physical gap in px-equivalents; add "origin-in-the-gap" and mirrored-pair symmetry-offset conditions to the Phase-0 two-device motion-probe protocol, not just crossing displacement.

## MAJOR — A3: The cheapest kill test is sequenced last; F4's HTML mockup cannot answer the question it is assigned

**Claim attacked:** phase ordering (Phase 0 = transport bake-off first) and F4 (HTML mockup as the seam-geometry eyes-on).

Panel-to-panel brightness/colour identity — WS2812 batch bins, LGP/diffuser variance — is a seam-visibility risk the plan's own evidence says NO timing scheme fixes (sync-timing §6), yet the first eyes-on of a real physical seam is the Phase-2 gate, after a bench-week of transport bake-off and the whole Phase-1 protocol build. A zero-firmware trial exists TODAY: flash both bench units with the same build, show a static colour and one simple pattern, butt them together, photograph the seam. That trial answers gap width, LGP edge hotspot/falloff, and batch variance before a single line of sync code — it is the cheapest possible way for the feature to die, and the plan defers it two phases. Separately, F4 hands the "will the seam look good" decision to an HTML mockup — HTML cannot represent light-guide optics, the dark gap, or panel variance; per the Captain's own visual-decision standard the artefact must be 1:1 accurate for the decision being made. HTML is legitimate ONLY for geometry semantics (what maps where), not for seam quality.

**Fix:** insert a day-zero physical seam trial (zero new firmware) at the top of Phase 0; add a brightness/colour delta measurement (photo, fixed exposure) as a Phase-0 output; re-scope F4 to geometry semantics and make the physical bench photo/video the seam-quality artefact.

## MAJOR — A4: v1 widened roster excludes every beat-locked showpiece, and mode-cycling shatters the merge

**Claim attacked:** "v1 roster = geometry-clean, non-stateful modes" as an acceptable product.

Class A ∖ S = {BLOOM, BLOOM_FAST, WAVEFORM, WAVEFORM_FAST, WAVEFORM_HYBRID, AURORA, EMBER, WAVEFORM_TEMPO, CHROMA_CONSTELLATION} ≈ 9 modes — and WAVEFORM_HYBRID must drop out because it samples raw `waveform_history` (`light_mode_waveform_hybrid.cpp:167`), which the semantic stream does not carry (census §6 says this; the plan's roster line ignores it). So v1 widening covers ~8/22 modes (~36%) and contains ZERO of the beat-locked modes (TEMPO_COMET, TEMPO_COMET_ANTICIPATE, TEMPO_RIVER, PERCUSSION_BURST, PULSE_PRISM, DENSE_FORGE x2, RIVER_SURGE, RIVER_WALK, COMET) — precisely the modes where "two units locked to the beat" is demonstrable and marketable. The v1 demo is ambient blooms and waveform trails. Worse: cycling 'm' mid-session toggles the pair between one 320-px surface and two independent mirrored displays as the user crosses roster boundaries — the largest possible visual jump, repeated every few presses, against the motion canon's spirit ("modulate, never jump"). The plan defines neither a paired-mode roster clamp nor the widen↔unwiden transition. The census tally itself is internally inconsistent (its own table sums to 15 A / 7 B, not the stated 14/8) and the plan repeats the wrong number — the roster has never actually been enumerated in the plan.

**Fix:** name the exact v1 roster in the plan (with WAVEFORM_HYBRID excluded and the tally corrected); clamp the paired-mode cycle to the roster; define the widen↔unwiden transition as a slewed cross-fade; state plainly to Captain that v1 widening has no beat-locked mode.

## MAJOR — A5: Mirrored-twin sync is the roster-complete, physically honest v1 the plan buries as a fallback

**Claim attacked:** widened display as the v1 product shape.

Phase 1's own deliverables (feature stream + control mirror + AGC/hue adoption + clock beacon) already produce two identical, beat-locked, mirrored K1s — ALL 22 modes, including every showpiece A4 excludes, with no per-effect geometry work and no retune. The perceptual budget also relaxes decisively: with twins, nothing crosses between devices and each unit keeps its own centre, so the requirement drops from the unproven ~10 ms crossing budget to event-simultaneity (~20–40 ms external estimate) — the transport bar gets easier by 2–4x, which may even change the Phase-0 bake-off outcome. The physical seam issues (A2, A3) vanish because there is no virtual surface spanning the gap. The plan's own evidence called this "coherent twin displays … good for a party sync feature" (sync-timing §3, Scheme 2 discussion) and then filed it under link-loss fallback. Given A1 shows the widened mode's headline benefit is overstated under the cheap mechanism, the twins product plausibly delivers MORE customer value (full roster, beat-locked pair) for a fraction of the risk.

**Fix:** restructure the plan so "twin sync, full roster" is the Phase-1/2 shippable milestone with its own (looser) measured budget, and widened mode becomes Phase 3+ contingent on A1's mechanism decision and A2/A3's physical evidence.

## MAJOR — A6: The retune the pre-mortem promises is scheduled nowhere

**Claim attacked:** Phase-2 scope/gate completeness.

Verified: speed constants are canvas-relative, tuned at NR=128-equivalent for an 80-px arm — `TR_PX_PER_BEAT = 22.0f` (`light_mode_tempo_river.cpp:43`), `TEMPO_PX_PER_BEAT = 24.0f` (`light_mode_waveform_tempo.cpp:67`), comet velocity, ember/river drift and aurora propagation all scale by `NATIVE_RESOLUTION/128` (grep: 20+ sites). Under Mechanism 1 physical velocity doubles (~185 → ~370 LED/s); under Mechanism 2 time-to-edge doubles (arm 80 → 160 px at unchanged px/s) and every mode reads half-speed. Either way the tuned character of EVERY v1-roster mode changes — the census flagged this explicitly (§7: "expect a retune pass even for class-A modes"). The plan cites "Phase-2 perceptual retune pass" as pre-mortem mitigation №1, but Phase 2's work items contain no retune line and its gate checks only "seam continuity … motion canon" — a plan whose mitigation exists only in the pre-mortem section ships untuned character through a gate not designed to catch it.

**Fix:** add per-mode speed/character retune to Phase-2 scope, and add "per-mode character parity vs single-K1 baseline" to the Phase-2 eyes-on gate checklist.

## MINOR — A7: Mode-change commit instants and cross-fade progress are not aligned by anything in the plan

The transition engine is beat-quantised with wall-clock dwell state and per-frame cross-fade ticks (`director/beat_aware_director.h:47-85`: `last_switch_ms`, `pending_switch`, tempo-derived `xfade_ms`). The control mirror carries the *command*, not the *commit instant*; devices with different dwell baselines can commit one beat apart, showing two different modes across the seam for ~a beat — at exactly the moment the user is watching (they just pressed the button). Softened by: director auto-rotation defaults OFF, and a ≤10 ms link makes user-commanded switches near-simultaneous. **Fix:** timestamped apply-at semantics for mode/param mirror records; align cross-fade start to the shared clock.

## MINOR — A8: User-facing MIRROR_ENABLED semantics undefined in paired mode

The waveform family has a real, user-reachable unmirrored full-strip path today (`light_mode_waveform_fast.cpp:160-177`); widened mode appropriates mirror-off semantics. What the user's mirror toggle does while paired (and after unpairing, and on the secondary channel with `SECONDARY_MIRROR_ENABLED`) is undefined. **Fix:** one paragraph in v0.2 defining toggle behaviour in paired mode.

## Steel-man honesty — what survived attack

1. **Pixel-streaming rejection is correct** — the bandwidth arithmetic (48–96 kB/s vs BLE envelopes) checks out and the conclusion is safe.
2. **One-authority leader topology is correct** — the 22.5 ms PLL phase quantisation (`sb_tempo.cpp:43`, 44.4 Hz emit) and anti-phase lock risk are real; dual-mic-plus-corrections genuinely cannot meet any plausible seam bar for a shared surface.
3. **The canvas-widening prohibition is correct** — `NUM_FREQS == NATIVE_RESOLUTION/2` coupling verified; composition-layer widening is the right family of mechanism.
4. **Phase-0 measure-before-commit is the right epistemics** — external latency numbers are properly quarantined as provisional.
5. **The v1 roster's state-safety logic holds** — I attacked free-scroll accumulator drift (clock skew → seam kink) and it dissolves: trail/transport history decays with alpha ~0.82–0.98, so skew-induced offset is bounded by (skew × trail lifetime) ≈ sub-pixel. The census's "frame-history modes self-heal; integrator modes do not" split is genuinely good analysis and the A∖S roster criterion is sound *as a state criterion* (its product adequacy is A4's separate attack).

## Missed considerations (not in the draft at all)

- **Viewing context is never stated** (desk, shelf, venue distance) — every perceptual budget in the lane is distance-dependent; the seam budget should be stated at a declared design viewing distance.
- **The seam-budget percept may be mis-specified**: derived from crossing-object displacement, but under centre-origin widening the dominant percepts are birth-event simultaneity at the gap and left/right mirror-symmetry offset (vernier-class acuity) — neither measured, both plausibly stricter.
- **Panel colour identity has no calibration story anywhere** (leader-adopted scalars equalise firmware gain, not LED bins or plate optics) — either a per-device colour-cal step exists in the product plan or the physical trial (A3) must prove it unnecessary.
- **Which physical unit is "left"?** Role/side persistence is designed, but nothing defines how the user establishes side (swap detection, or a visible test pattern at pairing) — a swapped pair renders the arm inward-facing on both units, a silently wrong picture the plan never checks.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (red-team SSA, perceptual/product lens) | Created — adversarial review of evaluation-and-plan.md v0.1: 1 KILL (mechanism conflation falsifies a headline claim either way), 5 MAJOR (origin-in-gap, kill-test sequencing, roster adequacy, buried twins product, unscheduled retune), 2 MINOR; steel-man section records what survived. |
