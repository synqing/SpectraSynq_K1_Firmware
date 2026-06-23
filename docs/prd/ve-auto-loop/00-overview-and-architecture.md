---
abstract: "Foundational PRD section for VE-Auto-Loop — the autonomous visual-effects development loop for the K1. A zero-context fresh agent builds from here. Establishes the problem (the effect LIBRARY, not the director, is the #1 lane; remove Captain from the inner edit-render-stare-tweak loop; make new effects born beat-reactive), goals/non-goals, measurable MVP-done criteria, the [MECHANISM]→[MEASURED] confidence ladder with Captain's eye as the sole terminal aesthetic gate, a glossary, and — restated authoritatively — the two-tier cascade architecture (host-sim inner loop / on-device vpab_capture outer loop) plus the canonical API/frame contract (effect_id, RenderParams, AudioDrive[] → leds[N*3] + VPABMetricPayload, with determinism invariants). CRITICAL caveat at the top: SpectraSynq.K1_Testbed targets firmware-v3/BeatPulse, NOT this repo's SPECTRASYNQ_K1_FIRMWARE — testbed is a pattern donor only; we build K1-true on this repo's vpab_capture + render_replay seams. Ends with a build-order index (01 render_replay, 02 evaluation, 03 loop-driver, 04 tier-2/governance), the MVP-0→MVP-1→Ext milestone sequence, and a 5-bullet 'what a fresh agent does first'. Read this before any other ve-auto-loop PRD file."
---

# VE-Auto-Loop — Overview and Architecture (PRD §00)

*SensoryBridge K1 · the foundational section of the VE-Auto-Loop product requirements. Read this first.*

> **Design source of truth.** This PRD operationalises the feasibility verdict in
> [`../../architecture/visual-effects-autonomous-loop-assessment.md`](../../architecture/visual-effects-autonomous-loop-assessment.md).
> Where this document and the assessment disagree on facts, the assessment (and the firmware
> source it cites) wins; raise the conflict rather than papering over it. This section restates
> the architecture and the API/frame contract **authoritatively** so the sibling PRD files
> (§01–§04) can reference one canonical statement.

---

## 0 · THE CRITICAL CAVEAT — read before anything else

**The existing `SpectraSynq.K1_Testbed` targets the WRONG firmware lineage. Do not point the
VE-Auto-Loop at it as a renderer.**

The testbed at `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq.K1_Testbed` is a
PyTorch offline sim of **`lightwave-ledstrip firmware-v3` / BeatPulse** (its `config.toml`
sets `firmware.root → firmware-v3`). That is a *different* C++ effect tree from the firmware
this repository ships. **This repository ships `SPECTRASYNQ_K1_FIRMWARE/`** — the GDFT / Bloom /
Comet / Ember / Waveform lineage. An effect tuned against the testbed-as-is optimises a product
the K1 does **not** run. This single fact dwarfs every gamma / dither / colour concern, and it is
the reason VE-Auto-Loop is built the way it is.

**The consequence — the prime directive of this PRD:**

- **Build K1-true on THIS repo's own seams** — `vpab_capture.{h,cpp}` (the real post-quant
  output port) and a new `render_replay` host-compile harness generalised from the existing
  `tempo_replay.py` pattern.
- **The testbed is a PATTERN DONOR ONLY.** Lift its loop architecture, its metric/regression
  scaffolding, and its gradient-recovery harness shape. Do **not** lift its renderer, its
  frozen `core/` parity twin, or its 7 physics metrics as a scoring authority.

If a future agent is ever tempted to "just re-point the testbed at K1," stop: re-pointing the
frozen `core/` is a large rebuild that re-introduces the sim-sim-gap problem and starts from the
wrong tree. The lower-blast-radius path is the one in this PRD.

---

## 1 · Problem statement and why this is the #1 lane

The K1's perceptual edge is **not** its director and **not** its audio pipeline — both work. The
bottleneck, Captain-confirmed (2026-06-01), is the **effect LIBRARY**:

- The Smart-Director is whitelisted to ~6 modes (~2–3 distinct looks); KALEIDOSCOPE is locked
  out; the beat / onset stream the firmware already computes is consumed by **nothing**.
- The library over-invests pitch→colour (five live effects) and ignores three signals it already
  has: **beat / tempo-phase** (`sb_tempo` is built, consumed by nothing), song structure, and
  timbre.
- The largest single unused signal is **beat / tempo-phase-locked motion** — already computed,
  the most universally legible musical cue, and absent from every shipping effect.

Today, building one effect is a **Captain-in-the-loop** chore: *write effect → flash K1 → stare →
tweak → re-flash → stare again.* Every iteration burns founder attention at the bench. This is
the exact inner loop the Founder Execution Boundary says an agent should own.

**VE-Auto-Loop replaces that inner loop.** It turns *"write effect → flash → stare → tweak"* into
*"write effect → render 100 proxy-scored variants automatically → Captain reviews the top 5 once."*
Captain's eye is preserved as the **terminal aesthetic gate** — but it is consulted **once per
batch over a shortlist**, never per iteration, never on rejects.

**Why now.** `sb_tempo` (the 50 Hz decoupled novelty / onset clock) was just built and consumes
nothing. VE-Auto-Loop makes **beat-reactivity a born-in property** of every new effect by scoring
beat-correlation as a first-class proxy — directly wiring up the #1 unused signal as it generates.

**The honest prior.** The last comparable autonomous window in this ecosystem was ~88% churn. The
red-team Bayesian estimate is P(loop yields genuinely better *shipping* effects) ≈ **12–18% as
naïvely scoped** → **45–55% with the mitigations** baked into this PRD (Captain-eye terminal gate,
two-tier cascade, frozen gates, hard iteration / shortlist caps, on-device certification). Those
mitigations are requirements, not nice-to-haves.

---

## 2 · Goals, non-goals, out-of-scope

### 2.1 · Goals

1. **Remove Captain from the inner effect-development loop.** Captain is consulted only at a
   batched aesthetic gate, never per iteration.
2. **Make new effects born beat-reactive.** Beat / tempo-phase correlation is a first-class,
   always-scored proxy that biases the generator toward the #1 unused signal.
3. **Build K1-true.** Effects are rendered through this repo's real seams (`render_replay` host
   tier; `vpab_capture` device tier), not a foreign sim.
4. **Two-tier confidence.** A fast deterministic host inner loop searches and prunes at
   `[MECHANISM]` confidence; a slow on-device outer loop certifies survivors at `[MEASURED]`
   confidence. Only the device tier may gate a ship decision.
5. **Generator + pruner, not judge.** The loop generates and ranks; it never declares an effect
   "good." Aesthetic verdict is Captain's alone.
6. **Bounded, auditable, low-churn.** Hard iteration and shortlist caps, reject-and-delete, one
   canonical results file per cycle.

### 2.2 · Non-goals (explicitly NOT built in MVP)

- **No autonomous firmware write / flash / upload.** The loop's write scope stops at the host
  harness and the results directory. Promoting an effect into shipping firmware is a separate,
  human-gated step under `k1-firmware-change-gate`.
- **No replacement of Captain's aesthetic judgement.** No metric, surrogate, or model is ever the
  terminal "is this captivating?" authority.
- **No generative ML in the scoring path** until its own validation gate is green. MVP edits are
  **parameter sweeps over existing `RenderParams` knobs** — no blue-sky effect synthesis.
- **No re-pointing or rebuilding of the testbed `core/`.** Pattern donor only.
- **No new audio-pipeline or main-rate change.** The loop consumes existing signals
  (`SBAudioSnapshot` / `sb_onset_beat` / `sb_tempo`); it does not modify the audio pipeline. (The
  main `SAMPLE_RATE` / 133 Hz AP rate is not to be touched.)

### 2.3 · Out-of-scope (deferred or owned elsewhere)

- **Optics / LGP / gamma / dither / dual-channel hardware reality** beyond what `vpab_capture`
  already emits post-quant. The device tier captures these *as measured*; the loop does not model
  them in the host tier (and must not pretend to).
- **Effect-template / operator mutation** beyond parameter sweeps — that is Ext-2.
- **Optimiser / surrogate-driven proposal** — that is Ext-3 (the testbed `training/` lane is the
  pattern, not a dependency).
- **Director / mode-whitelist changes.** VE-Auto-Loop produces effects; wiring them into the
  Smart-Director whitelist is downstream product work.

---

## 3 · Success criteria

### 3.1 · What "MVP done" means (MVP-0 + MVP-1 — measurable)

MVP is complete when **all** of the following are demonstrably true (each backed by an artefact,
not an assertion):

1. **`render_replay` host-compiles ONE K1 mode** from `SPECTRASYNQ_K1_FIRMWARE` against the
   Arduino / FastLED / SQ15x16 stub set, drives it with synthetic audio drive, and dumps frames in
   the **exact `VPABBytesPayload` byte layout** — bit-identical across two runs with the same
   `(effect_id, params, drive, seed)`.
2. **A `loop.py` driver** runs *edit (parameter sweep) → render → score → rank* end-to-end with
   **zero Captain involvement** for at least one mode, producing a ranked shortlist of ≤5–6
   survivors and a **contact sheet** artefact.
3. **A frozen `champion.json`** baseline exists and is used as the regression floor; survivors are
   regression-compared against it, and doctrine-regressors (motion-memory loss, colour-clarity
   loss, NaN/overflow, perf-blown) are **rejected automatically**.
4. **The beat-correlation proxy** is wired to `sb_tempo`'s 50 Hz novelty / onset clock and scored
   on every candidate (MVP-1).
5. **3–5 canned audio fixtures** drive the loop (reuse the steady-groove / kick-drop-heavy /
   sparse-breakdown scenarios already captured under
   `docs/forensics/runtime-evidence/`), so scores are comparable across cycles.
6. **The Captain gate is exercised once per batch** over the shortlist contact sheet + proxy panel
   — and the gate's verdict sets the new `champion.json` (the new regression floor).

A green host loop is **necessary but not sufficient**: MVP does not claim an effect is shippable
until the device tier has certified at least one survivor (§3.3).

### 3.2 · The confidence ladder — `[MECHANISM]` vs `[MEASURED]` (and `[LIT]` / `[PERCEPTION]`)

VE-Auto-Loop inherits the motion-canon epistemic ladder (`k1-motion-canon` §0). Every claim the
loop makes is labelled, and a claim can only gate a decision appropriate to its rung:

| Label | Meaning | What it may gate |
|---|---|---|
| **`[MECHANISM]`** | What the code computes; `file:line`-grounded. The **host tier** produces this. | Search and pruning in the inner loop. **Never** a ship decision. |
| **`[MEASURED]`** | Measured **on the K1 itself**, via `vpab_capture`. The **device tier** produces this. | Certification of a survivor. The **only** rung allowed to gate a ship decision. |
| **`[LIT]`** | Established perceptual-science finding on the general visual system; not yet K1-confirmed. | A hypothesis for the bench; a strong prior. Never a constant to hard-code. |
| **`[PERCEPTION]`** | Unvalidated look/feel interpretation. Weakest. | Nothing automatic — flag for Captain's eye. |

**The discipline:** the host sim is a *model* and **will drift** from hardware. A green host score
is `[MECHANISM]`. It earns `[MEASURED]` only by passing through `vpab_capture` on the real K1.
Where a `[MEASURED]` number exists (e.g. the apparent-motion thresholds in §4.x of the canon), it
**overrides** any `[LIT]` prior.

### 3.3 · Captain's eye is the only terminal aesthetic gate (non-negotiable)

No proxy metric — not energy, not divergence, not beat-correlation, not any future surrogate —
answers *"is this captivating / musically alive / promote to champion?"* That question is
**answered by Captain's eye, once per batch, over an evidence-attached shortlist.** This is the
direct mitigation for **R2 (Goodhart): physics metrics cannot judge musical compulsion.** The loop
is a generator and a pruner; it manufactures a high-quality shortlist and the evidence to judge it,
and then it stops and waits. Scoring an effect only on autonomous proxies would Goodhart the loop
into technically-green, lifeless effects — the explicit failure this design forbids.

**The ship gate** additionally requires on-device `[MEASURED]` evidence (R3 / R4): the host sim
ranks, the device certifies. "Shipped" is never claimed from a host-only green run.

---

## 4 · Glossary

| Term | Definition |
|---|---|
| **`render_replay`** | The new **host-compile harness** generalised from `tempo_replay.py`: host-`clang++` a real `light_mode_*.cpp` + `render_params.cpp` against an `Arduino.h` / FastLED / `SQ15x16` stub set, drive it with synthetic audio, and dump `leds_16` in the **same `VPABBytesPayload` byte layout** the device emits. The Tier-1 (host) renderer. PRD §01. |
| **VPAB tap** | The **real on-device output port**, `vpab_capture.{h,cpp}`. Emits post-quant LED bytes (`VPABBytesPayload.bytes[LED_COUNT*3]`) plus a 40-field `VPABMetricPayload` over serial (`VPAB,ver=1,...`), self-describing via `VPABRenderContext`, armed by serial command, parsed by `vp_capture.py` / `vp_diff.py`. The Tier-2 (device) renderer and the source of `[MEASURED]` evidence. |
| **`champion.json`** | The **frozen regression baseline** — the current best effect/parameter set for a mode and its recorded proxy panel. Survivors are regression-compared against it; a Captain gate verdict promotes a new survivor to champion, which becomes the new regression floor. |
| **proxy panel** | The bundle of autonomous, machine-computable scores attached to each candidate: motion presence, apparent-motion (frame-Δ vs the canon px/frame band), colour clarity (`channel_divergence`), shape (`spatial_width` / `edge_energy_ratio`), persistence (`energy_half_life`), **beat-correlation**, plus the hard guards (NaN/overflow, perf-budget µs/frame). Drives search; never the terminal aesthetic verdict. PRD §02. |
| **two-tier cascade** | The architecture: a fast deterministic **host-sim inner loop** (Tier 1, `[MECHANISM]`) for wide search + prune, feeding a slow human-gated **on-device VPAB outer loop** (Tier 2, `[MEASURED]`) that certifies survivors. Neither tier alone suffices. §6. |
| **host-sim tier** | Tier 1. `render_replay` on the host: seconds/iteration, deterministic, gradient/sweep-friendly. Prunes at `[MECHANISM]` confidence. |
| **on-device tier** | Tier 2. `vpab_capture` on the real K1: ~1–3 min/iteration incl. build+flash+capture, human-gated. Certifies at `[MEASURED]` confidence. The only tier that may gate a ship decision. |
| **contact sheet** | The **batched-review artefact** shown to Captain: a side-by-side of the ≤5–6 shortlisted candidates (rendered frames / strips + their proxy panels), so the aesthetic verdict is made once per cycle with evidence attached, never per iteration. |
| **AudioDrive** | The synthetic per-frame stimulus vector fed to a rendered effect: `{ novelty, silence, spectrum[NUM_FREQS], vu, chromagram[12], beat_phase }` — mirrors the firmware's `SBAudioSnapshot` / `sb_onset_beat` / `sb_tempo`. |
| **firmware-lineage caveat** | §0: the testbed renders `firmware-v3` / BeatPulse, not this repo's `SPECTRASYNQ_K1_FIRMWARE`. Testbed = pattern donor; K1-true rendering = this repo's `vpab_capture` + `render_replay`. |

---

## 5 · The canonical API / frame contract (authoritative)

This is the **one canonical statement** of the contract. Sibling PRD files reference it rather than
restating it. It is deliberately identical across both tiers so the loop driver is renderer-agnostic.

```
INPUT
  effect_id : uint8         -- lightshow_modes enum (selects the light_mode_*.cpp)
  params    : RenderParams  -- render_params.h; the ONLY mutable knob surface
                               (heap-free, CONFIG-decoupled; modes read via
                                active_render_params(), never global CONFIG)
  drive[t]  : AudioDrive     -- per-frame synthetic audio stimulus, t = 0..frames-1
                                { novelty, silence, spectrum[NUM_FREQS], vu,
                                  chromagram[12], beat_phase }
                                (mirrors SBAudioSnapshot / sb_onset_beat / sb_tempo)
  frames    : uint32         -- number of frames to render
  seed      : uint32         -- determinism seed

OUTPUT  (per frame t)
  frame[t].leds    : uint8[LED_COUNT * 3]   -- VPABBytesPayload.bytes layout, post-quant
  frame[t].metrics : VPABMetricPayload      -- the 40-field eval vector (the proxy substrate)

DETERMINISM INVARIANTS
  I1  Same (effect_id, params, drive, seed) => BIT-IDENTICAL leds on the HOST tier.
  I2  Same input => METRIC-IDENTICAL VPABMetricPayload on the DEVICE tier
      (byte-level equality is not promised on-device; metric equality is).
  I3  Identical leds[N*3] byte layout on BOTH tiers — the driver MUST NOT know
      or care which tier rendered a frame.
  I4  No global-CONFIG reach-through: an effect's output is a pure function of
      (effect_id, params, drive, seed). Any mode reaching past RenderParams into
      global CONFIG breaks the contract and is a defect to fix, not to model.
```

**Why `RenderParams` is the knob boundary.** `render_params.h` is an immutable, heap-free
per-channel snapshot (the `build_primary_render_params()` / `active_render_params()` path). It is
the clean, CONFIG-decoupled surface that makes host replay feasible and makes MVP "edit =
parameter sweep" well-defined: the sweep is over `RenderParams` fields. Modes already reading
`active_render_params()` are the **easiest first `render_replay` targets**.

**Why `VPABMetricPayload` is the eval vector.** Its fields already map to the motion canon:
`com_delta_leds` / `com_slope_delta_pct` = apparent-motion velocity / coherence; `flicker_score` =
the mechanical/chaos signal; `energy_delta_pct` / `changed_led_pct` = aliveness;
`hue_delta_p95` / `white_bias_score` = colour clarity; `render_us` / `frame_us` / `over` /
`dropped` = the perf guard. The proxy panel (§4, PRD §02) is computed from this payload plus the
new beat-correlation proxy.

---

## 6 · The two-tier cascade architecture

```
                    ┌──────────────────────────────────────────────────────────┐
                    │  EDIT (MVP: parameter sweep over RenderParams knobs)        │
                    │  generate N candidate (effect_id, params) tuples            │
                    └───────────────────────────┬──────────────────────────────┘
                                                 │
   ╔═════════════════════════════════════════════▼══════════════════════════════════════════╗
   ║  TIER 1 — HOST-SIM INNER LOOP            [MECHANISM]      seconds/iter · deterministic    ║
   ║  ───────────────────────────────────────────────────────────────────────────────────── ║
   ║  render_replay (host-clang++ light_mode_*.cpp + render_params.cpp + stubs)               ║
   ║      │  drive[t] = canned audio fixture (steady-groove / kick-drop / sparse-breakdown)    ║
   ║      ▼                                                                                    ║
   ║  leds[N*3] (VPABBytesPayload layout) + VPABMetricPayload  ── per frame ──┐                ║
   ║      │                                                                    ▼               ║
   ║  PROXY PANEL + HARD GUARDS  (motion / apparent-motion / colour / shape /                  ║
   ║      persistence / beat-correlation ; NaN-overflow ; perf-budget µs/frame)               ║
   ║      │                                                                                    ║
   ║  REJECT  NaN / overflow / perf-blown / doctrine-regressors (motion-memory, colour-clarity)║
   ║      │                                                                                    ║
   ║  REGRESSION-COMPARE vs frozen champion.json  ──►  RANK survivors                          ║
   ║      │                                                                                    ║
   ║  EMIT shortlist (≤5–6) + CONTACT SHEET                                                    ║
   ╚═══════════════════════════════════════════════╤══════════════════════════════════════════╝
                                                    │  survivors only
   ╔═══════════════════════════════════════════════▼══════════════════════════════════════════╗
   ║  TIER 2 — ON-DEVICE VPAB OUTER LOOP      [MEASURED]      ~1–3 min/iter · human-gated       ║
   ║  ───────────────────────────────────────────────────────────────────────────────────── ║
   ║  PlatformIO build + k1_upload_guard.py (target-identity verified) ──► flash K1            ║
   ║      ▼                                                                                    ║
   ║  vpab_capture tap ──► real post-quant leds[N*3] + VPABMetricPayload (LGP/colour/dither/    ║
   ║      dual-channel reality, AS MEASURED)                                                   ║
   ║      ▼                                                                                    ║
   ║  CAPTAIN'S EYE  (batched, once per cycle, over contact sheet + proxy panel):              ║
   ║      "captivating / musically alive / promote to champion?"  ── TERMINAL AESTHETIC GATE   ║
   ║      ▼                                                                                    ║
   ║  verdict sets new champion.json (the new regression floor)  ·  ONLY tier that gates ship  ║
   ╚════════════════════════════════════════════════════════════════════════════════════════╝
```

**Why both tiers are required.** Host-sim alone repeats the sim-sim-gap problem (and, if pointed at
the testbed, on the wrong firmware) — it is a model and will drift. Device-alone is far too slow for
search. The cascade lets the fast tier search wide and the slow tier keep it honest: the sim
**ranks**, the device **certifies**. TRIZ separation-in-time: autonomous per-iteration scoring drives
the search; the human eye is a periodic batch gate over the shortlist, never per-iteration, never on
rejects.

**Write-scope boundary (doctrine, R7).** Tier 1's write scope stops at the host harness and the
results directory. Tier 2's build/flash is **human-gated** under `k1-firmware-change-gate` and
target-verified by `k1_upload_guard.py` — the loop never autonomously flashes the K1.

---

## 7 · Build-order index — the sibling PRD files

Build in this order. Each file owns one slice; this overview is the shared reference for all.

| File | Owns | Depends on |
|---|---|---|
| **`00-overview-and-architecture.md`** *(this file)* | Problem, goals, success criteria, glossary, the API/frame contract, the two-tier architecture. | — |
| **`01-render-replay.md`** | The Tier-1 host-compile harness: stub set, `clang++` build of `light_mode_*.cpp` + `render_params.cpp`, `AudioDrive` injection, `VPABBytesPayload`-layout frame dump, determinism invariants I1/I3/I4. The MVP-0 spine. | §00 contract |
| **`02-evaluation.md`** | The proxy panel + hard guards: the metrics drawn from `VPABMetricPayload`, the new beat-correlation proxy (xcorr vs `sb_tempo`), NaN/overflow guard, perf-budget, the `champion.json` regression compare, ranking, and the contact-sheet artefact. | §01 frames |
| **`03-loop-driver.md`** | `loop.py`: the controller (edit → render → score → rank → emit), parameter-sweep generation over `RenderParams`, hard iteration / shortlist caps, reject-and-delete, one canonical results file, the Captain-gate hand-off. | §01, §02 |
| **`04-tier2-and-governance.md`** | The on-device bridge (PlatformIO build + `k1_upload_guard.py` + `vpab→tensor` adapter), the `[MEASURED]` certification step, frozen-gate governance, the delegation ledger / churn caps, and the `k1-firmware-change-gate` boundary. | §01, §02, §03 |

### Milestone sequence

- **MVP-0** — `render_replay` for ONE K1 mode + a `loop.py` driver + a frozen `champion.json`
  baseline + 3–5 canned audio fixtures. Edit = parameter sweep over existing `RenderParams` knobs.
  Closes the loop with **no generative machinery**. (§01 + §03 + the §02 regression compare.)
- **MVP-1** — beat-correlation proxy tied to `sb_tempo`'s 50 Hz novelty clock; NaN/overflow + perf
  guards; the batch-review contact-sheet artefact (the Captain gate). (§02 completed + the §04
  Captain hand-off.)
- **Ext-2** — effect-template / operator mutation beyond parameter sweeps.
- **Ext-3** — optimiser / surrogate-driven proposal (the testbed `training/` lane is the *pattern*,
  not a dependency).
- **Tier-2 bridge (parallel track)** — wrap the PlatformIO build + `k1_upload_guard.py` + a
  `vpab→tensor` adapter so survivors get on-device `[MEASURED]` confirmation. (§04.)

---

## 8 · What a fresh agent does first

1. **Read the firmware-lineage caveat (§0) and internalise it.** Do not touch the testbed as a
   renderer. Build on `vpab_capture` + `render_replay`. If you find yourself re-pointing the
   testbed `core/`, stop.
2. **Read the design source of truth** —
   `docs/architecture/visual-effects-autonomous-loop-assessment.md` — then `tempo_replay.py`
   (`scripts/regression-harness/`), `vpab_capture.h`, and `render_params.h` to see the three real
   seams the host tier generalises and the device tier taps.
3. **Pick the easiest MVP-0 target mode** — one that already reads `active_render_params()` (so
   the `RenderParams` sweep boundary is clean) — and stand up `render_replay` for it per PRD §01,
   asserting determinism invariant I1 (two runs, same input ⇒ bit-identical `leds`).
4. **Wire `loop.py` (§03) and the regression compare against a frozen `champion.json` (§02)** so an
   edit→render→score→rank→shortlist cycle runs with **zero Captain involvement**, using the canned
   `docs/forensics/runtime-evidence/` fixtures.
5. **Stop at the gate.** Produce the contact sheet + proxy panel, label every claim on the
   `[MECHANISM]`→`[MEASURED]` ladder, and hand the batched shortlist to Captain's eye — the only
   terminal aesthetic gate. Never claim "shipped" without on-device `[MEASURED]` certification.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | Created — VE-Auto-Loop PRD §00 foundational section. Problem (#1 lane = effect library; remove Captain from inner loop; born-beat-reactive); goals/non-goals/out-of-scope; measurable MVP-done criteria + the [MECHANISM]→[MEASURED] confidence ladder with Captain's eye as the sole terminal aesthetic gate; glossary; the authoritative two-tier cascade diagram + canonical API/frame contract (effect_id, RenderParams, AudioDrive[] → leds[N*3] + VPABMetricPayload, determinism invariants I1–I4); the firmware-lineage CRITICAL caveat (testbed = firmware-v3/BeatPulse pattern donor, not SPECTRASYNQ_K1_FIRMWARE); build-order index (01 render_replay, 02 evaluation, 03 loop-driver, 04 tier-2/governance) + MVP-0→MVP-1→Ext sequence; 5-bullet fresh-agent start. Derived from docs/architecture/visual-effects-autonomous-loop-assessment.md. |
