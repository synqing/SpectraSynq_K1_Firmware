---
abstract: "Build spec for the VE-Auto-Loop evaluation function — the loop's controller setpoint. Zero-context-buildable. Defines the proxy panel (motion presence, apparent-motion velocity/coherence, colour clarity, spatial spread/shape, persistence/decay, beat-correlation, no-NaN/overflow guard, perf-budget) with exact formula, VPABMetricPayload input field, and PASS/FAIL band per proxy; the DECIDE function ({keep, iterate, reject} + weighted rank score combining proxies, hard-reject guards, and the LEVERS-MATRIX rubric); the champion.json schema, seeding, regression-comparison, and Captain-verdict promotion rule; the beat-correlation proxy in full (sb_tempo novelty/onset stream xcorr against temporal_volatility — this is what makes effects born beat-reactive); and the anti-Goodhart safeguards (proxies are necessary-not-sufficient; the Captain eye is the terminal aesthetic gate; no proxy self-certifies aesthetics). The scorer measures peakiness/correctness PROXIES, never 'is it captivating'. Read before building the evaluator or its champion.json baseline. Numeric apparent-motion thresholds are CALIBRATE-pointers to docs/measurements/apparent-motion-on-k1.md, not transcribed values."
---

# VE-Auto-Loop — Evaluation & Scoring (the Controller Setpoint)

This is the **build spec for the evaluation function** of the Visual-Effects
Autonomous Loop. The evaluator is the loop's *controller setpoint*: it is the
sensor + reference + decide edge that turns a rendered candidate effect into a
machine verdict (`keep` / `iterate` / `reject`) and a weighted rank score, so
the autonomous inner loop can search the parameter/effect space and surface only
a shortlist to the human gate.

**Read first:** `docs/architecture/visual-effects-autonomous-loop-assessment.md`
(design source-of-truth). This spec implements the "evaluation problem & its
resolution (TB4/TB6)" section of that document.

**What this scorer does and does not judge — the load-bearing boundary.**
The evaluator scores **peakiness / correctness PROXIES** — measurable physical
properties of the rendered frame stream that *correlate with* a musically alive,
beat-reactive, colour-clear effect. The evaluator **NEVER** scores "is it
captivating", "is it musically alive", or "promote to champion". Those are
answered exactly once per batch by the **Captain's eye (the terminal aesthetic
gate)**, never by a number. The proxies are *necessary-not-sufficient*: they can
reject a dead/broken/Goodharted effect, and they can rank survivors for review
order, but a green proxy panel is a **ticket to the human gate, not a pass**.
This is the doctrine that compile/render ≠ visual proof, applied to scoring.

---

## 0. Inputs, units, determinism

### 0.1 Frame set (the unit of evaluation)

A candidate is evaluated against a **fixed audio-fixture corpus**: a small set of
canned drive scenarios (default: `steady-groove`, `kick-drop-heavy`,
`sparse-breakdown-build`, reusing the scenario stimulus already captured under
`docs/forensics/runtime-evidence/`). For each scenario the loop produces a
**frame set**:

```
FrameSet := {
  scenario_id : str,                 # e.g. "kick-drop-heavy"
  channel     : 0|1,                 # dual-channel; scored per-channel then aggregated
  frames[t]   : {
      leds      : uint8[LED_COUNT*3]    # VPABBytesPayload.bytes layout, post-quant
      metrics   : VPABMetricPayload     # the 40-field eval vector, per-frame
      t_ms      : uint32                # from metrics.t_ms
  },
  drive[t]    : DriveSnapshot,        # the stimulus that produced frame t (see §6.1)
  render_ctx  : VPABRenderContext,    # primary_mode, secondary_mode, smart_enabled…
  source_tier : "host" | "device"     # which tier rendered (driver-agnostic)
}
```

Both tiers (host `render_replay` stdout, device `vpab_capture` serial) emit the
**identical `leds[N*3]` + `VPABMetricPayload` layout**; the scorer is
tier-agnostic. `source_tier` is recorded in the panel for provenance only — it
does **not** change any formula, only which confidence label the result carries
(`[MECHANISM]` for host-sim, `[MEASURED]` for device).

### 0.2 Determinism contract

Given the same FrameSet input, the scorer **MUST** emit a byte-identical proxy
panel and rank score. No wall-clock, no RNG, no thread-order dependence in the
scorer. (The *renderer's* determinism — same input+seed ⇒ identical frames — is
the loop's responsibility, not the scorer's; the scorer simply must not add
non-determinism on top.) This is required for the regression comparison in §5 to
be meaningful.

### 0.3 Field provenance

Every proxy below names its **exact input**: either a `VPABMetricPayload` field
(per the 40-field struct in `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.h`) or a
**frame-buffer computation** over `frames[t].leds`. Where a proxy is derivable
either from a payload field *or* recomputed from the buffer, prefer the **payload
field** (it is what the device actually measured post-quant; recomputing from
`leds` is the host-tier fallback when a device field is absent). The struct
fields this spec relies on:

```
changed_led_pct, changed_channel_pct      # aliveness / spatial activity
energy_a, energy_b, energy_delta_pct       # frame energy + its frame-to-frame delta
com_a, com_b, com_delta_leds               # centre-of-mass (apparent-motion position)
com_slope_delta_pct                        # COM velocity change (apparent-motion coherence)
hue_delta_p95, sat_delta_p95               # per-frame colour deltas
white_bias_score                           # colour-clarity / desaturation toward white
flicker_score                              # mechanical / chaos signal
mae8, p95_abs8, max_abs8                    # frame-diff magnitude (regression vs reference)
render_us, frame_us, show_us, over, dropped # perf budget
heap                                        # leak / OOM guard
truncated                                  # capture integrity
```

---

## 1. The Proxy Panel

The panel is **eight proxies** in three classes:

* **HARD-REJECT GUARDS** (binary, veto power): `no-NaN/overflow guard`,
  `perf-budget`. A failure here is an unconditional `reject` regardless of every
  other score — the candidate is broken or unshippable, not merely weak.
* **PROXY SCORES** (continuous, 0–1, contribute to rank): `motion presence`,
  `apparent-motion velocity`, `apparent-motion coherence`, `colour clarity`,
  `spatial spread/shape`, `persistence/decay`, `beat-correlation`.
* Each proxy emits `{value, normalised_0_1, band: PASS|WEAK|FAIL, confidence:
  [MEASURED]|[MECHANISM]|[INFERENCE]}`.

> **Threshold convention.** Where a band edge depends on an apparent-motion
> number that is empirically measured on K1, this spec does **NOT** transcribe a
> value. It writes:
> **`[CALIBRATE — pull [MEASURED] thresholds from
> docs/measurements/apparent-motion-on-k1.md; tune empirically via the digital
> real-music validation pipe]`**.
> The builder pulls the live number from the motion canon at build time. This
> prevents a stale hand-copied threshold silently becoming the controller
> setpoint. Thresholds that are dimensionless / structural (e.g. "energy must be
> non-zero", "NaN count must be 0") are stated inline as `[INFERENCE]` and
> calibrated against the champion baseline, not the motion canon.

Aggregation across frames within a FrameSet, and across scenarios/channels, is
defined in §1.10.

---

### 1.1 Motion presence

*Is the effect alive at all, or a static/near-static frame?* The cheapest
liveness gate; catches dead effects and frozen buffers before the more
expensive proxies run.

* **Input:** `changed_led_pct` (primary), `energy_delta_pct`,
  `temporal_volatility` (derived — see below). Frame-buffer fallback: fraction
  of LEDs whose value changed by > Δ between consecutive frames.
* **Derived `temporal_volatility`:** per-LED standard deviation of brightness
  across the frame window, averaged over LEDs:
  `temporal_volatility = mean_i( std_t( luma(leds[t][i]) ) )`
  where `luma = 0.299R + 0.587G + 0.114B`. This is the same signal the
  testbed's `vis/metrics.py` exposes and is the carrier for beat-correlation
  (§6). Compute it once; reuse.
* **Formula:**
  `motion_presence = clamp01( w1 * mean_t(changed_led_pct/100)
                             + w2 * mean_t(|energy_delta_pct|/100)
                             + w3 * norm(temporal_volatility) )`
  with default `w1=0.5, w2=0.2, w3=0.3` ([INFERENCE], tune against champion).
* **Band:**
  * `FAIL` if `mean_t(changed_led_pct) ≈ 0` over the window (static buffer) — a
    static effect is rejected outright as a candidate (see DECIDE §3). Threshold
    `[INFERENCE — near-zero; default < 0.5% changed LEDs/frame sustained]`.
  * `WEAK` if alive but below the champion's motion presence.
  * `PASS` if ≥ champion motion presence band.
* **Confidence:** `[MEASURED]` when sourced from device `changed_led_pct`;
  `[MECHANISM]` when recomputed from host frames.

### 1.2 Apparent-motion velocity

*Does the centre-of-luminance travel at a perceptually meaningful speed — not
imperceptibly slow, not strobing past the eye?* This is the proxy most directly
tied to the motion canon.

* **Input:** `com_delta_leds` (primary — frame-to-frame centre-of-mass shift in
  LED units). Convert to velocity:
  `velocity_px_per_s = com_delta_leds * (1000 / dt_ms)` where
  `dt_ms = (t_ms[t] - t_ms[t-1])`.
* **Formula:** `am_velocity = robust_median_t( |velocity_px_per_s| )` (median, not
  mean, to resist single-frame jumps from beat hits).
* **Band:** PASS when `am_velocity` lands inside the **[MEASURED] apparent-motion
  velocity band** for K1.
  **`[CALIBRATE — pull [MEASURED] min/max apparent-motion velocity (px/frame
  and/or px/s) from docs/measurements/apparent-motion-on-k1.md; tune empirically
  via the digital real-music validation pipe]`.**
  * Below band → `WEAK` (sluggish / imperceptible drift).
  * Above band → `WEAK` (too fast to track as coherent motion; may read as
    flicker — cross-checks against §1.10 flicker guard).
* **Confidence:** `[MEASURED]` (device `com_delta_leds` + `dt_us`).

### 1.3 Apparent-motion coherence

*Is the motion smooth/directional or jittery/incoherent?* Velocity alone does not
distinguish smooth travel from chaotic centre-of-mass thrash.

* **Input:** `com_slope_delta_pct` (primary — change in COM velocity, i.e. the
  acceleration/jerk signal). Frame-buffer fallback: variance of the COM
  trajectory's second difference.
* **Formula:**
  `am_coherence = 1 - clamp01( norm( robust_std_t(com_slope_delta_pct) ) )`
  High coherence = low velocity-change variance = smooth directional motion.
* **Band:** PASS when coherence ≥ the **[MEASURED] coherence floor**.
  **`[CALIBRATE — pull [MEASURED] coherence/jerk threshold from
  docs/measurements/apparent-motion-on-k1.md; tune empirically via the digital
  real-music validation pipe]`.**
  * Note the *intended* interaction: a beat-reactive effect SHOULD show
    coherence dips synchronised to onsets (the kick *should* punch the COM).
    Coherence is therefore scored **between** onsets (gate on the §6 onset
    stream) so that musical punches are not penalised as incoherence. This is a
    deliberate coupling to the beat-correlation proxy.
* **Confidence:** `[MEASURED]`.

### 1.4 Colour clarity

*Are colours saturated and note-distinct, or washed toward white/grey?* Directly
attacks the known AGC colour-damage failure mode (saturation flattening, fixed
bass tilt).

* **Input:** `white_bias_score` (primary — higher = more desaturated toward
  white), `sat_delta_p95`, `hue_delta_p95`. Frame-buffer derived
  `channel_divergence`: mean per-frame spread across R/G/B channels
  (`mean_t( std(channelEnergy_R, channelEnergy_G, channelEnergy_B) )`) — high
  divergence = chromatic, low = greyscale.
* **Formula:**
  `colour_clarity = clamp01( w1 * (1 - norm(white_bias_score))
                            + w2 * norm(channel_divergence)
                            + w3 * norm(sat_delta_p95) )`
  default `w1=0.5, w2=0.3, w3=0.2` ([INFERENCE]).
* **Band:**
  * `FAIL` (doctrine regressor) if `white_bias_score` exceeds the champion's by
    a hard margin — colour-clarity regression is one of the named doctrine
    hard-rejects. `[INFERENCE — margin calibrated against champion white_bias_score]`.
  * `WEAK` if below champion clarity.
  * `PASS` if ≥ champion clarity band.
* **Confidence:** `[MEASURED]` from `white_bias_score`; `[MECHANISM]` for the
  recomputed `channel_divergence`.

### 1.5 Spatial spread / shape

*Does the effect use the strip with deliberate shape, or smear/clump?* Catches
both degenerate cases: a single hot LED (no spread) and a flat wash (no shape).

* **Input:** frame-buffer derived `spatial_width` (luma-weighted standard
  deviation of lit position across the strip) and `edge_energy_ratio` (energy in
  the spatial high-frequency band / total energy — proxies crispness of edges).
  `com_a`/`com_b` give the centre; `spatial_width` gives the spread about it.
* **Formula:**
  `spatial_shape = clamp01( w1 * inside_band(spatial_width)
                          + w2 * norm(edge_energy_ratio) )`
  where `inside_band()` returns 1 when width is within a healthy range and decays
  outside it (penalising both pinpoint and full-wash).
  default `w1=0.6, w2=0.4` ([INFERENCE]).
* **Band:** PASS when `spatial_width` ∈ healthy range AND `edge_energy_ratio`
  above floor.
  **`[CALIBRATE — if a [MEASURED] spatial spread / structure threshold exists in
  docs/measurements/apparent-motion-on-k1.md use it; else tune empirically via
  the digital real-music validation pipe against champion]`.**
* **Confidence:** `[MECHANISM]` (frame-buffer derived) unless a device field
  backs it.

### 1.6 Persistence / decay

*Do features have motion memory — do peaks bloom and trail, or pop and vanish?*
Directly scores the "motion memory" doctrine property; loss of persistence is a
named regressor.

* **Input:** derived `energy_half_life` — fit the post-peak decay of frame energy
  (`energy_a`/`energy_b` sequence, or per-LED luma trails) and report the time
  for a peak to fall to half. Per-LED variant: the autocorrelation decay time of
  `luma(leds[t][i])`.
* **Formula:**
  `persistence = norm(energy_half_life)` mapped so that a too-short half-life
  (instant pop) and an absurdly long one (smear that never resets) both score
  low; healthy trailing scores high.
* **Band:**
  * `FAIL` (doctrine regressor) if `energy_half_life` collapses below the
    champion's — motion-memory regression is a hard-reject class.
    `[INFERENCE — calibrated against champion energy_half_life]`.
  * `WEAK`/`PASS` relative to champion.
* **Confidence:** `[MECHANISM]`/`[MEASURED]` per source.

### 1.7 Beat-correlation

*Is the effect actually locked to the music, or merely busy?* The proxy that makes
new effects **born beat-reactive** — directly consuming the just-built
`sb_tempo` novelty/onset stream and closing the "beat/onset stream unused"
#1-lane gap. **Full detail in §6.**

* **Input:** `temporal_volatility` (the per-frame visual-change carrier, §1.1)
  cross-correlated against the **novelty/onset stream** obtained from `sb_tempo`
  for the *same* drive (§6.1).
* **Formula (summary):**
  `beat_corr = max_lag( normalised_xcorr( temporal_volatility[t],
                                          novelty[t] ) )`
  over a bounded lag window; report the peak correlation **and** the lag at which
  it occurs (a beat-reactive effect peaks at a small, stable, non-negative lag —
  render trails the onset by a frame or two).
* **Band:** PASS when `beat_corr ≥` the **[MEASURED]/[INFERENCE] correlation
  floor** AND the peak lag is within a small stable window.
  **`[CALIBRATE — correlation floor + acceptable lag window tuned empirically via
  the digital real-music validation pipe; seed the floor from the champion's
  beat_corr]`.**
* **Confidence:** `[MECHANISM]` (host, synthetic novelty) → `[MEASURED]` (device,
  real-music drive).

### 1.8 No-NaN / overflow guard *(HARD-REJECT)*

*Is the frame stream numerically sane?* A broken effect can score "interesting"
on noise; this guard vetoes before any score is trusted.

* **Input:** scan of `frames[t].leds` (uint8 — overflow shows as saturation
  clusters or impossible patterns), plus every float field of
  `VPABMetricPayload` (`mae8`, `changed_led_pct`, `energy_delta_pct`, `com_*`,
  `white_bias_score`, `flicker_score`), plus `truncated`, `dropped`, `over`,
  `heap`.
* **Checks (ALL must hold, else `reject`):**
  1. No `NaN`/`Inf` in any float metric.
  2. No metric outside its physical domain (e.g. `*_pct ∈ [0, sane_max]`,
     `com_* ∈ [0, LED_COUNT]`, `white_bias_score`/`flicker_score` finite and in
     range).
  3. `truncated == 0` (capture integrity — a truncated frame set cannot be
     scored; this is a *capture* failure, surfaced distinctly from an *effect*
     failure).
  4. `heap` non-decreasing-leak check: `heap` must not trend downward across the
     frame set beyond a noise margin (leak guard). `[INFERENCE]`.
  5. `over`/`dropped` within budget (see §1.9; the perf guard owns the hard
     edge).
* **Band:** binary `PASS` / `FAIL(reject)`. No partial credit.
* **Confidence:** `[MEASURED]` (device) — overflow/leak only fully provable on
  device; host catches NaN/Inf and domain violations.

### 1.9 Perf-budget (µs/frame) *(HARD-REJECT)*

*Will it hold the frame rate on K1?* An effect that blows the render budget is
unshippable regardless of beauty.

* **Input:** `render_us`, `frame_us`, `show_us`, `over`, `dropped` (device);
  host `render_replay` reports its own `render_us` analogue (advisory only — host
  timing is `[MECHANISM]`, not `[MEASURED]`).
* **Formula / checks:**
  * `frame_budget_us` derived from the K1 main render rate.
    **`[CALIBRATE — pull the frame-budget µs ceiling from the K1 render-rate
    constant (main loop / SAMPLE_RATE-linked); do NOT change SAMPLE_RATE — see
    project memory]`.**
  * `FAIL(reject)` if `p95_t(frame_us) > frame_budget_us` OR `over > 0` OR
    `dropped > 0` on the **device** tier.
  * On **host** tier, perf is **advisory** (a soft warning that flags likely
    budget risk for Tier-2 attention); host timing must never be the thing that
    gates a ship decision.
* **Band:** binary on device; advisory on host.
* **Confidence:** device `[MEASURED]`; host `[MECHANISM]`.

### 1.10 Cross-frame, cross-scenario, cross-channel aggregation

1. **Within a FrameSet (per scenario, per channel):** each continuous proxy
   aggregates over frames using a **robust statistic** (median or trimmed mean)
   plus a dispersion term, so a single beat-spike frame cannot dominate. Guards
   aggregate as "ANY frame fails ⇒ guard fails".
2. **Across channels (dual-channel):** the two channels are scored
   **independently** then combined; **independent dual-channel behaviour is a
   doctrine property**, so a candidate whose two channels are near-identical when
   the drive differs is penalised (a `channel_independence` sub-term feeds
   spatial_shape / motion_presence). Do not average the channels into one and
   lose this.
3. **Across scenarios:** the candidate's per-scenario panels are combined with the
   **worst-scenario-weighted** rule — an effect that is great on steady-groove
   but dead on sparse-breakdown is not "70% good", it has a hole. Default:
   `proxy_final = 0.5 * mean_scenarios + 0.5 * min_scenarios` ([INFERENCE]).
4. A global `flicker_score` sanity term (from `VPABMetricPayload.flicker_score`):
   excess flicker is the mechanical/chaos signal — it caps `am_velocity` and
   `motion_presence` credit so that "busy noise" cannot masquerade as motion.

---

## 2. The LEVERS-MATRIX rubric coupling

The proxy panel measures *outcomes*. The **LEVERS-MATRIX**
(`docs/architecture/effect-decomposition/LEVERS-MATRIX.md` +
`00-the-method.md`) maps an effect's *levers* (the knobs an edit/sweep moves) to
the *outcomes* they are expected to produce. The evaluator uses the rubric in two
ways:

1. **Expectation check (diagnostic, not veto):** when a candidate is produced by
   moving a known lever, the rubric predicts which proxy *should* move and in
   which direction. The DECIDE function compares the realised proxy delta against
   the rubric's predicted direction. A lever that moved the *wrong* proxy (or
   moved nothing) is a signal the edit did not do what it claimed — it biases the
   verdict toward `iterate` and is recorded in the panel as a
   `lever_expectation_mismatch` annotation. This is how the rubric makes the
   search legible rather than a black-box sweep.
2. **Rank-weight prior:** the rubric's outcome priorities (which outcomes matter
   most for "musically compelling, beat-reactive, colour-clear") seed the default
   proxy weights in the rank score (§3.3). When the matrix and the empirical
   champion disagree on a weight, the **champion regression baseline wins**
   (empirical floor > predicted prior), and the disagreement is logged for the
   Captain batch review.

The rubric is **advisory to the score, never a hard gate** — only the guards
(§1.8–1.9) and the named doctrine regressors (colour-clarity §1.4,
motion-memory §1.6) carry veto power.

---

## 3. The DECIDE function — {keep, iterate, reject} + rank score

`DECIDE(panel, guards, champion, rubric) -> Verdict{ decision, rank_score, reasons[] }`

### 3.1 Order of evaluation (short-circuit)

```
1. HARD-REJECT GUARDS  (§1.8 no-NaN/overflow, §1.9 perf-budget on device)
      any FAIL  -> decision = REJECT  (reason = guard id);  rank_score = 0;  STOP.
2. DOCTRINE REGRESSORS  (colour-clarity FAIL §1.4, motion-memory FAIL §1.6,
                         dual-channel-collapse §1.10.2)
      any FAIL  -> decision = REJECT  (reason = doctrine regressor);  STOP.
   (Doctrine-regressor band edges are frozen vs champion; a new carve-out
    requires Captain ratification + a tombstone of the old edge — gates do not
    self-relax. See anti-Goodhart §7.)
3. LIVENESS  (§1.1 motion_presence FAIL = static buffer)
      FAIL  -> decision = REJECT  (reason = dead effect);  STOP.
4. SCORE     compute rank_score (§3.3) from the continuous proxies.
5. DECIDE keep vs iterate:
      rank_score >= champion.rank_score (within margin)   -> KEEP   (shortlist)
      rank_score in [iterate_floor, champion)             -> ITERATE
      rank_score < iterate_floor                          -> REJECT (too weak)
```

* **KEEP** = "good enough to spend a Captain-eye slot on" — it enters the
  shortlist (capped, §3.4) for the human terminal gate. KEEP is **not**
  "promote"; promotion is Captain-only (§5.4).
* **ITERATE** = "promising but below champion / has a fixable mismatch" — feed
  back into the search (e.g. another sweep step, lever nudge per the rubric
  mismatch). Bounded by the loop's hard iteration cap (no infinite churn — the
  88%-churn precedent is the reason this cap exists).
* **REJECT** = guard/doctrine/liveness failure or below `iterate_floor`. Rejects
  are **deleted, not archived** (one canonical results file; reject-and-delete).

`iterate_floor` is `[INFERENCE]`, seeded as a fraction of the champion score
(default 0.6) and tuned so the iterate band is neither empty nor a churn trap.

### 3.2 Why this scores proxies, never aesthetics — explicit

`DECIDE` can output `KEEP` for a candidate the Captain will *reject* as
uncaptivating, and that is **correct behaviour**: `KEEP` means "passes the
peakiness/correctness proxies, worth a human look", not "is good". `DECIDE` can
**never** output "promote", "ship", "captivating", or "musically alive" — those
strings are reserved for the Captain verdict (§5.4). If a future change makes any
proxy emit an aesthetic judgement, that is a spec violation (anti-Goodhart §7).

### 3.3 Weighted rank score

```
rank_score = clamp01(
      W_motion       * motion_presence
    + W_am_velocity  * am_velocity_score      # band-scored, not raw velocity
    + W_am_coherence * am_coherence
    + W_colour       * colour_clarity
    + W_spatial      * spatial_shape
    + W_persistence  * persistence
    + W_beat         * beat_corr
)   *  flicker_penalty
```

* **flicker_penalty** ∈ (0, 1] derived from `flicker_score` — multiplicative so
  that excess flicker cannot be out-weighted by any single high proxy.
* **Default weights (`[INFERENCE]`, seeded from the LEVERS-MATRIX outcome
  priorities; the beat-reactivity north-star is weighted high):**
  `W_beat = 0.25, W_motion = 0.15, W_am_velocity = 0.15, W_am_coherence = 0.10,
  W_colour = 0.15, W_spatial = 0.10, W_persistence = 0.10` (sum = 1.0). These are
  **tunable and must be version-stamped in `champion.json`** so a score is always
  reproducible against the weights that produced it.
* Weights are **frozen per cycle**. Changing weights mid-cycle invalidates the
  regression comparison; a weight change is a new baseline epoch (§5).

### 3.4 Shortlist cap

`KEEP` survivors are ranked by `rank_score` descending; only the top **N (default
5, hard max 6)** advance to the Captain batch gate as a side-by-side contact
sheet + proxy panel. This is the separation-in-time discipline: search is
per-iteration and autonomous; the human eye is a periodic batch over a bounded
shortlist, never per-iteration, never on rejects.

---

## 4. The proxy panel artefact (scorer output)

For every candidate the scorer emits a deterministic, machine- and
human-readable panel:

```json
{
  "candidate_id": "…",
  "effect_id": 7,
  "params_hash": "…",
  "weights_version": "…",
  "scenarios": {
    "kick-drop-heavy": {
      "ch0": { "motion_presence": {"value":…, "norm":…, "band":"PASS", "confidence":"[MEASURED]"},
               "am_velocity":     {"value":…, "norm":…, "band":"WEAK", "confidence":"[MEASURED]"},
               "am_coherence":    {…}, "colour_clarity": {…}, "spatial_shape": {…},
               "persistence":     {…}, "beat_corr": {"value":…, "lag":…, "band":…, "confidence":…},
               "guards": { "nan_overflow": "PASS", "perf_budget": "PASS" },
               "annotations": [ "lever_expectation_mismatch: W_colour lever moved persistence" ] },
      "ch1": { … }
    },
    "steady-groove": { … },
    "sparse-breakdown-build": { … }
  },
  "aggregate": {
    "rank_score": 0.0,
    "decision": "KEEP|ITERATE|REJECT",
    "reasons": [ "…" ],
    "vs_champion": { "champion_id":"…", "champion_rank":…, "delta":…, "regressed_proxies":[…] }
  },
  "source_tier": "host|device",
  "deterministic_input_digest": "…"
}
```

`deterministic_input_digest` is a hash of the FrameSet inputs; identical digest
⇒ identical panel (the determinism contract, §0.2, made checkable).

---

## 5. `champion.json` — the regression floor

`champion.json` is the **frozen reference** the loop scores against: the
current-best effect-instance whose proxy panel defines the floor every new
candidate must clear. It is the loop's `DeltaReport` reference, made persistent
and promotable.

### 5.1 Schema

```json
{
  "champion_version": 3,
  "promoted_utc": "2026-06-03T…Z",
  "promoted_by": "captain",
  "effect_id": 7,
  "effect_source_ref": "git:SPECTRASYNQ_K1_FIRMWARE/light_mode_X.cpp@<sha>",
  "params": { "...": "RenderParams snapshot (the mutable knob surface)" },
  "params_hash": "…",
  "weights_version": "ve-eval-w1",
  "weights": { "W_beat":0.25, "W_motion":0.15, "...": "…" },
  "fixture_corpus": ["steady-groove","kick-drop-heavy","sparse-breakdown-build"],
  "fixture_corpus_hash": "…",
  "tier_of_record": "device",          // promotion requires device [MEASURED] evidence
  "panel": { "...": "the full per-scenario/per-channel proxy panel that earned promotion" },
  "rank_score": 0.0,
  "doctrine_floors": {                  // the hard regressor edges, frozen at promotion
     "white_bias_score_max": …,
     "energy_half_life_min": …,
     "channel_independence_min": …
  },
  "evidence_ref": "docs/forensics/runtime-evidence/…",   // the on-device A/B that justified it
  "supersedes": 2,
  "changelog": [ { "version":3, "utc":"…", "by":"captain", "note":"…" } ]
}
```

### 5.2 Seeding (champion v0)

The first champion is **not** synthetic. Seed it from a **currently-shipping K1
effect** that Captain already endorses (one of the whitelisted director modes),
captured on **device** via `vpab_capture` across the fixture corpus, scored, and
written as `champion_version: 0, promoted_by: "captain"`. This anchors the floor
to a real, Captain-blessed look so that "beat champion" means "beat a thing we
actually ship", not "beat a number we invented". If no single mode is the clear
floor, seed per-effect-id champions (the schema keys on `effect_id`).

### 5.3 Regression comparison

A candidate is compared against the champion **of the same `effect_id`** (or the
global champion for net-new effects), under the **same `weights_version` and
`fixture_corpus_hash`** — comparing across different weights or fixtures is
invalid and the scorer must refuse it (emit `INCOMPARABLE`, not a number).

```
vs_champion = {
  delta            = candidate.rank_score - champion.rank_score
  regressed_proxies = [ p for p in proxies if candidate[p] < champion[p] - margin ]
  doctrine_breach   = any candidate doctrine-floor worse than champion.doctrine_floors
}
```

* `doctrine_breach == true` ⇒ forced `REJECT` (cannot promote a doctrine
  regressor even if rank_score is higher — §1.4/§1.6 are hard).
* `delta >= 0 && no doctrine_breach` ⇒ eligible for `KEEP`/shortlist.
* The comparison also uses the per-frame `mae8`/`p95_abs8`/`max_abs8` diff fields
  as a **bit-level regression cross-check** for *parameter-identical* re-renders
  (a re-render of the champion's own params MUST reproduce the champion within
  the frame-diff tolerance, or the renderer/tier has drifted — this is the
  sim-drift tripwire, and it must be fp-tolerant per the accepted mode-11
  resolution, not bit-exact across `-ffast-math` reassociation).

### 5.4 Promotion rule — Captain verdict only

**Promotion is a human act.** No proxy, no rank_score, no `KEEP` decision ever
promotes a champion. The flow:

1. Loop emits the shortlist (≤ N) + contact sheet + proxy panels to the Captain
   batch gate.
2. Captain reviews on the **terminal aesthetic question** ("is it captivating /
   musically alive / promote?") and issues a verdict.
3. **On a Captain "promote" verdict**, and only then, the candidate's
   device-tier (`tier_of_record: "device"`) panel becomes the new
   `champion.json`: `champion_version += 1`, `promoted_by: "captain"`,
   `supersedes` set, `doctrine_floors` re-frozen from the new champion, old
   champion tombstoned in the changelog. **The new champion is the new
   regression floor** — every subsequent candidate must clear it.
4. A promotion **requires on-device `[MEASURED]` evidence** (`evidence_ref`) — a
   host-sim-only candidate cannot become champion (sim ranks, device certifies;
   R3/R4 in the assessment risk register).

Promotion is the *only* way the floor moves up; the floor never moves down
autonomously (no self-relaxing gates, §7).

---

## 6. Beat-correlation proxy — full detail (the born-beat-reactive lever)

This proxy is the reason the loop produces beat-reactive effects by construction
rather than by luck. It correlates **what the eye sees changing** against **what
the music is doing**.

### 6.1 Obtaining the novelty / onset stream from `sb_tempo`

The drive that renders the candidate must carry, per frame, a **novelty value**
and **onset markers** aligned to the visual frames. Two equivalent build paths
(the harness uses `scripts/regression-harness/tempo_replay.py` as the donor):

* **Path A — drive through `sb_tempo` (preferred, host tier):** feed each fixture
  scenario's audio-feature stimulus through the same `sb_tempo` host-replay that
  `tempo_replay.py` exercises (the decoupled **50 Hz novelty clock**, per project
  memory — *do not* change the main `SAMPLE_RATE`). Capture the per-tick
  `novelty` scalar and the onset/beat-phase markers. Resample the 50 Hz novelty
  onto the visual frame timeline (`frames[t].t_ms`) by nearest/linear
  interpolation, producing `novelty[t]` and `onset_mask[t]` co-indexed with the
  frames.
* **Path B — import its output (device tier / when re-running sb_tempo is
  unavailable):** ingest the novelty/onset stream `tempo_replay.py` already dumps
  for that fixture and align it to `frames[t].t_ms`. Provenance recorded in the
  panel.

The fixture corpus and its novelty streams are **hashed into
`fixture_corpus_hash`** so a score is always tied to the exact stimulus that
produced it.

### 6.2 The correlation

* **Carrier signal:** `temporal_volatility[t]` (§1.1) — the per-frame visual
  activity. Optionally also run the xcorr against `|energy_delta_pct[t]|` and
  `changed_led_pct[t]` and take the best-aligned of the three (an effect may
  express the beat as energy pulses, as motion, or as recolouring; the proxy
  credits whichever channel carries it).
* **Normalisation:** zero-mean, unit-variance both signals over the window before
  correlating (so loud sections do not dominate).
* **Cross-correlation:**
  `xc(lag) = (1/N) * Σ_t  z(volatility)[t] * z(novelty)[t - lag]`
  over a **bounded lag window** (default: 0…+K frames, where the render is
  expected to *trail* the onset by a small render latency; small negative lags
  allowed for tolerance).
* **Output:**
  `beat_corr = max_{lag∈window} xc(lag)` and `beat_lag = argmax_{lag} xc(lag)`.
* **A genuinely beat-reactive effect** shows a **high `beat_corr` at a small,
  stable, non-negative `beat_lag`**. A busy-but-unsynced effect shows a low or
  smeared peak; an effect that fires *before* the onset (negative lag beyond
  tolerance) is suspect (it cannot be reacting to a beat it hasn't heard) and is
  flagged.
* **Onset-locked variant (stronger):** additionally compute the mean
  `temporal_volatility` in a short window *after* each `onset_mask` tick vs the
  inter-onset baseline; the ratio (`onset_response_ratio`) is a Goodhart-resistant
  cross-check — it is hard to fake by being globally busy.

### 6.3 Band & confidence

* **Band:** PASS when `beat_corr ≥ floor` AND `beat_lag ∈ window` AND
  `onset_response_ratio > 1 + ε`.
  **`[CALIBRATE — correlation floor, lag window, and onset_response_ratio ε tuned
  empirically via the digital real-music validation pipe; seed the floor from the
  champion's beat_corr]`.**
* **Confidence:** `[MECHANISM]` on host with synthetic-stimulus novelty;
  promoted to `[MEASURED]` only when the drive is real-music on device. This is
  the proxy most exposed to sim-drift, so its device confirmation is
  load-bearing for any beat-reactivity claim.

---

## 7. Anti-Goodhart safeguards

The single largest risk (R2, CRITICAL) is that the loop optimises the proxies
into lifeless, technically-green effects. The following are **non-negotiable
structural defences**, not advice:

1. **Proxies are necessary-not-sufficient.** A full-green panel is a *ticket to
   the human gate*, never a pass. No combination of proxy values authorises
   "ship" or "promote". The scorer's vocabulary literally cannot emit those
   verdicts (§3.2).
2. **The Captain's eye is the terminal aesthetic gate.** "Captivating / musically
   alive / promote" is answered exactly once per batch by the human, over a
   bounded shortlist (≤ N), with evidence attached. It is the *only* edge that
   moves the champion floor up (§5.4). Compile/render/green-panel ≠ visual proof
   — the project doctrine, encoded.
3. **No proxy self-certifies aesthetics.** Each proxy measures one physical
   property and outputs a band + confidence; none claims to measure beauty. The
   rank score orders the *review queue*, it does not rank *quality*.
4. **Frozen gates; ratified carve-outs only.** Guard, doctrine-floor, and band
   definitions are frozen per cycle. A new carve-out (e.g. a `frame > 10`
   exception) requires explicit Captain ratification **and** a tombstone of the
   superseded edge in the changelog. Gates never self-relax — the "amend broken
   gates" rule (fix-as-a-class then re-run, never run-while-broken) applies.
5. **The floor only moves up, and only by a human.** Autonomous code can never
   lower `champion.json`. A regression below the champion is `REJECT`, full stop.
6. **Multiplicative flicker penalty + worst-scenario weighting + onset-response
   cross-check.** Three structural terms that specifically defeat the easiest
   Goodhart strategies: "be globally busy" (flicker penalty + onset-response
   ratio), and "be great on one easy scenario" (worst-scenario weighting,
   §1.10.3).
7. **Sim ranks, device certifies.** Host-tier `[MECHANISM]` scores prune and
   rank; only device-tier `[MEASURED]` evidence is admissible for promotion. A
   green sim is explicitly necessary-not-sufficient (R3/R4).
8. **Bounded iteration + reject-and-delete + one canonical results file.** Hard
   iteration and shortlist caps (the 88%-churn precedent), rejects deleted not
   archived, results kept in a single canonical file — so the loop cannot churn
   or exhaust attention.

---

## 8. Acceptance criteria

The evaluator is **done** when, given a FrameSet (the frame set + co-indexed
drive for the fixture corpus, either tier):

1. It emits a **deterministic proxy panel** — the §4 artefact — byte-identical on
   re-run for an identical `deterministic_input_digest`. *(Test: score the same
   FrameSet twice; assert identical panels.)*
2. It emits a **pass/fail vs champion** — a `vs_champion` block with `delta`,
   `regressed_proxies`, and `doctrine_breach`, refusing (`INCOMPARABLE`) when
   `weights_version` or `fixture_corpus_hash` differ. *(Test: compare a known
   regression and a known improvement against a seeded champion; assert correct
   REJECT / KEEP-eligible.)*
3. It emits a **rank score** in `[0,1]` per §3.3, with the hard-reject guards
   short-circuiting to `rank_score = 0, decision = REJECT`. *(Test: inject a NaN
   metric and a budget-blown `frame_us`; assert both REJECT with the correct
   reason and zero score.)*
4. It produces the **beat-correlation proxy** with `beat_corr` + `beat_lag` from
   the `sb_tempo` novelty stream xcorr against `temporal_volatility`. *(Test:
   feed a beat-locked synthetic effect and a beat-agnostic one through the same
   drive; assert the locked one scores materially higher `beat_corr` at a small
   stable lag.)*
5. It **never** emits an aesthetic verdict — no "captivating", "ship", or
   "promote" string is reachable from any code path. *(Test: grep the verdict
   enum; assert it is exactly `{KEEP, ITERATE, REJECT, INCOMPARABLE}`.)*
6. A Captain "promote" verdict on a device-tier shortlist candidate **rewrites
   `champion.json`** (version bumped, supersedes set, doctrine floors re-frozen,
   old tombstoned) and the new champion becomes the floor for the next
   comparison. *(Test: simulate a promote; assert the next candidate is compared
   against the new floor.)*

---

## 9. Proxy → threshold → source table

| Proxy | Class | Formula (summary) | Primary input | Threshold / band | Confidence | Source for the number |
|---|---|---|---|---|---|---|
| Motion presence | score | `w·changed_led_pct + w·|energy_delta_pct| + w·temporal_volatility` | `changed_led_pct`, `energy_delta_pct` + derived `temporal_volatility` | FAIL if ≈0 (static); else WEAK/PASS vs champion | `[MEASURED]`/`[MECHANISM]` | static edge `[INFERENCE <0.5%/frame]`; PASS band = champion floor |
| Apparent-motion velocity | score | `median |com_delta_leds·1000/dt_ms|` | `com_delta_leds`, `dt_us` | PASS inside [MEASURED] velocity band | `[MEASURED]` | **[CALIBRATE — `docs/measurements/apparent-motion-on-k1.md`; digital real-music validation pipe]** |
| Apparent-motion coherence | score | `1 − norm(std(com_slope_delta_pct))`, scored between onsets | `com_slope_delta_pct` | PASS ≥ [MEASURED] coherence floor | `[MEASURED]` | **[CALIBRATE — `docs/measurements/apparent-motion-on-k1.md`; digital real-music validation pipe]** |
| Colour clarity | score (+doctrine veto) | `w·(1−white_bias) + w·channel_divergence + w·sat_delta_p95` | `white_bias_score`, `sat_delta_p95`, `hue_delta_p95` + derived `channel_divergence` | FAIL if white_bias regresses vs champion (doctrine); else WEAK/PASS | `[MEASURED]`/`[MECHANISM]` | doctrine margin `[INFERENCE]` vs champion `white_bias_score` |
| Spatial spread / shape | score | `w·inside_band(spatial_width) + w·edge_energy_ratio` | derived `spatial_width`, `edge_energy_ratio`, `com_a/com_b` | PASS width ∈ healthy range + edge floor | `[MECHANISM]` | **[CALIBRATE — `docs/measurements/apparent-motion-on-k1.md` if present; else champion + digital real-music pipe]** |
| Persistence / decay | score (+doctrine veto) | `norm(energy_half_life)`, penalise too-short & too-long | derived `energy_half_life` from `energy_a/energy_b` | FAIL if half-life collapses vs champion (motion-memory doctrine) | `[MEASURED]`/`[MECHANISM]` | `[INFERENCE]` calibrated vs champion `energy_half_life` |
| Beat-correlation | score | `max_lag normalised_xcorr(temporal_volatility, sb_tempo novelty)`; + onset_response_ratio | derived `temporal_volatility`; `sb_tempo` novelty/onset stream (§6.1) | PASS `beat_corr ≥ floor` ∧ `beat_lag ∈ window` ∧ ratio>1+ε | `[MECHANISM]`→`[MEASURED]` | **[CALIBRATE — floor/lag/ε via digital real-music validation pipe; seed from champion `beat_corr`]** |
| No-NaN / overflow | guard (veto) | scan all floats + `leds` + `truncated`/`heap`/`over`/`dropped` | all float metrics, `leds`, `truncated`, `heap`, `over`, `dropped` | binary; any violation ⇒ REJECT | `[MEASURED]` (device) | `[INFERENCE]` domain ranges + non-leak `heap` margin |
| Perf-budget (µs/frame) | guard (veto, device) | `p95(frame_us) ≤ frame_budget_us ∧ over=0 ∧ dropped=0` | `frame_us`, `render_us`, `over`, `dropped` | device: REJECT if over budget; host: advisory | device `[MEASURED]`; host `[MECHANISM]` | **[CALIBRATE — frame budget from K1 render-rate constant; do NOT change `SAMPLE_RATE`]** |
| flicker_score (global) | penalty term | multiplicative `flicker_penalty ∈ (0,1]`; caps motion credit | `flicker_score` | n/a (scales rank_score) | `[MEASURED]` | `[INFERENCE]` penalty curve calibrated vs champion `flicker_score` |
| channel_independence | sub-term (doctrine) | divergence of ch0 vs ch1 panels when drive differs | per-channel panels (§1.10.2) | FAIL if channels collapse to identical (doctrine) | `[MEASURED]`/`[MECHANISM]` | `[INFERENCE]` vs champion `channel_independence_min` |

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus (PRD2-eval) | Created — build spec for the VE-Auto-Loop evaluation function (controller setpoint). Defines the 8-proxy panel (formula + VPABMetricPayload input + PASS/FAIL band each), the DECIDE function ({keep,iterate,reject} + weighted rank score, hard-reject short-circuit, LEVERS-MATRIX coupling), champion.json schema/seeding/regression/Captain-promotion rule, the beat-correlation proxy in full (sb_tempo novelty xcorr vs temporal_volatility), anti-Goodhart safeguards, acceptance criteria, and the proxy→threshold→source table. Per Captain instruction, unverified apparent-motion numeric thresholds are written as [CALIBRATE — pull [MEASURED] from docs/measurements/apparent-motion-on-k1.md; tune via digital real-music validation pipe] citation-pointers rather than transcribed values. DECIDE / champion.json / beat-correlation / anti-Goodhart written fully from the design SOT. |
