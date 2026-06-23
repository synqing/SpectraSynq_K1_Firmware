---
abstract: "Feasibility assessment of an autonomous visual-effects development loop for the K1, from a 6-agent study of /Users/spectrasynq/Workspace_Management/Software/SpectraSynq.K1_Testbed + this repo's seams. VERDICT: the vision is real and ~70% built — BUT the existing testbed is a PyTorch sim of the WRONG firmware lineage (Lightwave-Ledstrip firmware-v3 BeatPulse, not the shipping SPECTRASYNQ_K1_FIRMWARE), uses physics metrics that cannot judge musical compulsion, and is sim-only (no LGP/colour/dither/dual-channel). Recommended path: don't re-point the testbed; use it as a pattern donor and build the K1-true loop on THIS repo's existing seams — vpab_capture (real post-quant frame+metric serial tap, whose metrics already map to the motion canon) + the tempo_replay.py host-compile pattern generalised to a 'render_replay'. Two-tier cascade (fast host-sim inner loop / on-device vpab_capture outer [MEASURED] gate), Captain's eye as the TERMINAL aesthetic gate (batched, not per-iteration), bounded iteration. Bayesian P(genuinely better effects): ~12-18% as-is → ~45-55% with the mitigations. Read before building any effects-dev loop."
---

# Autonomous Visual-Effects Development Loop — Feasibility Assessment

*From a 6-agent swarm study of `SpectraSynq.K1_Testbed` + the SensoryBridge K1 firmware seams, 2026-06-03. Lenses: TRIZ, first-principles, archetypes, model-router, systems, second-order, architecture/api, bayesian, effectuation, red-team.*

## Verdict
The Captain's vision — an autonomous **edit→render→capture→evaluate→iterate** loop for effects, with the human eye as a periodic gate — is **real, sound, and ~70% already built in pieces.** Three catches govern whether it produces value:
1. **The existing testbed targets the WRONG firmware** (dominant finding, 3 agents independently): `config.toml firmware.root → firmware-v3` (Lightwave-Ledstrip **BeatPulse** C++), not the shipping `SPECTRASYNQ_K1_FIRMWARE/` (GDFT/Bloom/Comet/Ember). An effect tuned on the testbed-as-is optimises a product the K1 doesn't run. This dwarfs every gamma/dither concern.
2. **It's a sim, not hardware capture, and its metrics are physics not aesthetics** — deterministic + machine-evaluable (great for *regression/search*), but it models effect maths only (no LGP optics, FastLED colour-correction, dither, gamma, dual-channel), and its 7 metrics measure energy/divergence, **not "musically compelling."** A green sim ≠ hardware-visual proof, and a loop scored only on those metrics will Goodhart into lifeless effects.
3. **No controller exists yet** — the sim has plant (engine), sensor (metrics), reference (DeltaReport) but **no decide/mutate edge and no perceptual setpoint.** That, plus a beat-correlation proxy, is the net-new build.

**Bayesian (red-team):** P(loop yields genuinely better *shipping* effects) ≈ **12–18% as currently scoped** → **45–55%** with the mitigations below. Base-rate anchor: the last comparable autonomous window in this ecosystem was ~88% churn.

## What the testbed is (TB1/TB2)
PyTorch **offline sim harness** porting firmware-v3 BeatPulse effects to vectorised Python (~20K fps, deterministic). Layers: `core/` (frozen parity twin) · `calibration/` (sim-sim gap gate) · `vis/` (5 renderers + 7 metrics) · `experimental/` (operator engine, 8 base + 6 fw effects) · `training/` (DIFNO ML: FiLM 1D-UNet surrogate) · **`workbench/`** = the "visual harness" (asyncio WS+HTTP on :8765, HTML/canvas, streams 80×3 LED frames live/burst, Playwright-tested). Consumes a captured binary `data/reference_pairs.bin` ("LWRF" v2: 576 pairs, 80 radial bins). **Audio-feature stimulus is NOT wired** (`single_inject`/`manual` only → `UNSUPPORTED_MODE`).

## The K1-TRUE path — build on THIS repo's seams, don't re-point the testbed (TB5)
Re-pointing the frozen `core/` to K1 is a large rebuild. Lower blast-radius: **use the testbed as a *pattern donor*** (its loop architecture, metric/regression scaffolding, gradient-recovery harness) and build the K1 loop on seams that already exist here:
- **`vpab_capture.{h,cpp}` — the real output port.** Emits post-quant LED bytes (`VPABBytesPayload.bytes[LED_COUNT*3]`) + a 40-field `VPABMetricPayload` over serial (`VPAB,ver=1,...`), self-describing via `VPABRenderContext`, armed by serial cmd, parsed by `vp_capture.py`/`vp_diff.py`. **Its metrics already map to the motion canon:** `com_delta_leds`/`com_slope_delta_pct` = apparent-motion velocity/coherence; `flicker_score` = the mechanical/chaos signal; `energy_delta_pct`/`changed_led_pct` = aliveness. This IS the eval vector.
- **`tempo_replay.py` host-compile pattern → generalise to `render_replay`.** Host-`clang++` a real `light_mode_*.cpp` + `render_params.cpp` against an `Arduino.h`/FastLED/SQ15x16 stub set, drive with synthetic novelty/spectrum, dump `leds_16` in the *same* `VPABBytesPayload` byte layout. `RenderParams` (heap-free, CONFIG-decoupled) is the clean param boundary that makes this feasible; modes already reading `active_render_params()` are the easiest first targets.
- **One frame schema, two tiers** — host stdout and device serial produce identical `leds[N*3]` + metrics; the driver doesn't know which tier rendered.

### Proposed minimal API contract
```
INPUT  effect_id : uint8 (lightshow_modes enum)
       params    : RenderParams (render_params.h — the only mutable knob surface)
       drive[t]  : { novelty, silence, spectrum[NUM_FREQS], vu, chromagram[12], beat_phase }  (mirrors SBAudioSnapshot/sb_onset_beat/sb_tempo)
       frames, seed (determinism)
OUTPUT frame[t].leds    : uint8[N*3]  (VPABBytesPayload layout)
       frame[t].metrics : VPABMetricPayload (the eval vector)
INVARIANTS  same input+seed ⇒ bit-identical (host) / metric-identical (device); identical leds layout both tiers; no global-CONFIG reach-through.
```

## The evaluation problem & its resolution (TB4/TB6) — the load-bearing design
**TRIZ separation-in-time:** autonomous per-iteration scoring drives search; the human eye is a **periodic batch gate** over a shortlist (≤5–6 candidates as a side-by-side contact sheet + proxy panel), never per-iteration, never on rejects.
- **Fully autonomous:** build twin → render against a fixed audio-fixture corpus → compute proxy panel + hard guards → reject NaN/overflow/perf-blown/doctrine-regressors (motion-memory, colour-clarity) → regression-compare vs frozen `champion.json` → rank survivors → emit shortlist + contact sheet.
- **Captain's eye ONLY:** "is it captivating / musically alive / promote to champion?" — answered once per batch, evidence-attached; the verdict sets the new champion (= regression floor). This honours the doctrine that compile/render ≠ visual proof.
- **Defensible proxies:** motion presence (`peak_position` drift + `temporal_volatility`), apparent-motion (frame-Δ vs canon px/frame band), colour clarity (`channel_divergence`), shape (`spatial_width`/`edge_energy_ratio`), persistence (`energy_half_life`) — all exist in `vis/metrics.py` / `VPABMetricPayload`; **add three:** beat-correlation (xcorr `temporal_volatility` vs the new `sb_tempo` novelty/onset stream — makes new effects born beat-reactive, attacking the "beat stream unused" #1-lane gap), NaN/overflow guard, perf-budget (µs/frame).

## Recommended architecture — two-tier cascade
- **Tier 1 (host-sim inner loop):** fast (seconds/iter), deterministic, gradient/sweep-friendly; wide search + prune at `[MECHANISM]` confidence. Where the testbed pattern + `render_replay` live.
- **Tier 2 (on-device vpab_capture outer loop):** slow (~1–3 min/iter incl. build+flash+capture), human-gated; promotes survivors to `[MEASURED]` and is the **only tier allowed to gate a ship decision**. Keeps the fast loop honest (the sim is a *model* and will drift).
Neither alone suffices: host-sim alone repeats the sim-sim-gap problem (and currently on the wrong firmware); device-alone is too slow for search.

## Risk register (red-team, condensed)
| # | Risk | Sev | Mitigation |
|---|---|---|---|
| R1 | Testbed models wrong firmware lineage (firmware-v3, not SENSORY_BRIDGE) | CRITICAL | Build K1 loop on `vpab_capture` + `render_replay`; testbed = pattern donor only |
| R2 | Goodhart — physics metrics can't judge musical compulsion | CRITICAL | Captain's eye = terminal aesthetic gate, non-negotiable; loop = generator+pruner |
| R3 | Sim→hardware divergence (uint16/LGP/gamma/dither/dual-channel) | HIGH | Mandatory on-hardware vpab A/B before "shipped"; sim ranks, device certifies |
| R4 | Deterministic-but-wrong confidence (flakiness engineered out) | HIGH | Green sim = necessary-not-sufficient; require on-device evidence artefact |
| R5 | Self-relaxing gates (frame>10 carve-out already exists) | MED-HIGH | Freeze gate defs; new carve-outs need Captain ratification + tombstone |
| R6 | Churn amplification (88% precedent; doc/checkpoint exhaust) | MED-HIGH | Hard iteration + shortlist cap (≤5/cycle); reject-and-delete; one canonical results file |
| R7 | Doctrine breach via autonomous firmware write/upload | MED | Loop write scope stops at testbed/host; firmware integration = human-gated `k1-firmware-change-gate` |
| R8 | Unconverged surrogate (`gru_incomplete`) standing in for truth | MED | No unvalidated surrogate in the scoring path until its own gate is green |

## MVP phasing (owned means first, model-router)
- **MVP-0:** `render_replay` for ONE K1 mode (host-compile light_mode_X + render_params + stubs, dump VPAB-layout frames) + a `loop.py` driver + `champion.json` regression baseline + 3–5 canned audio fixtures (reuse the steady-groove/kick-drop/sparse-breakdown scenarios already in `docs/forensics/runtime-evidence/`). Edit = parameter sweep over existing knobs. Closes the loop with no generative machinery.
- **MVP-1:** beat-correlation proxy tied to `sb_tempo`'s 50 Hz novelty clock; NaN/overflow + perf guards; the batch-review contact-sheet artefact (the Captain gate).
- **Ext-2:** effect-template/operator mutation beyond sweeps.
- **Ext-3:** optimiser/surrogate-driven proposal (testbed `training/` is the pattern).
- **Tier-2 bridge (parallel):** wrap PlatformIO build + `k1_upload_guard.py` + a `vpab→tensor` adapter so survivors get on-device [MEASURED] confirmation.

## Why this accelerates the #1 lane
The bottleneck is the effect *library*, not the director (whitelisted to ~6 modes, beat/onset stream unused). This loop turns "write effect → flash K1 → stare → tweak" (Captain-in-loop, minutes) into "write effect → 100 proxy-scored variants → Captain reviews top 5" (Captain at the gate only), and makes beat-reactivity a born-in proxy — directly consuming the tempo detector just built.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | Created — feasibility assessment from a 6-agent study of SpectraSynq.K1_Testbed (inventory, capture, loop, red-team, integration, MVP design). Verdict: real & ~70% built, but the testbed targets the wrong firmware lineage and uses physics-not-aesthetic metrics; recommended K1-true path = build on this repo's vpab_capture + a render_replay host-compile (testbed as pattern donor), two-tier cascade, Captain's eye as terminal gate. Full agent reports persist in the session task outputs. |
