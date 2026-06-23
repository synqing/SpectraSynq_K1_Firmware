---
abstract: "PRD/BoM Tier-2 of the Visual-Effects Autonomous Loop (VE-Auto-Loop) for K1. Covers (1) the on-device confirmation bridge that promotes a host-sim survivor to [MEASURED] — arm vpab_capture over serial, capture frames+metrics, parse via vp_capture/vp_diff, drift-check against the host-sim prediction, and flash only through a MAC-verified k1_upload_guard PlatformIO wrap (HUMAN-INITIATED + gated, never autonomous); (2) the audio-fixture corpus (steady-groove / kick-drop-heavy / sparse-breakdown + octave-trap reggae/dub/DnB/hip-hop) at AP 133 Hz / decoupled 50 Hz novelty rate; (3) governance/doctrine constraints from the project .claude/CLAUDE.md (Developer Instrumentation Boundary, calibration policy, hardware-target + git discipline, frozen gate defs); (4) the R1-R8 risk register translated to build constraints; (5) phasing MVP-0 → MVP-1 → Ext-2 → Ext-3 → Tier-2 bridge with a per-milestone test plan and a milestone→acceptance table. Zero-context-buildable. Read before building the Tier-2 bridge, the fixture corpus, or wiring any loop write-scope to firmware."
---

# VE-Auto-Loop — Tier-2 Confirmation Bridge, Audio-Fixture Corpus, Governance & Test Plan

*PRD/BoM document 04 of the Visual-Effects Autonomous Loop (VE-Auto-Loop) for K1 hardware.*

> **Design source of truth:** `docs/architecture/visual-effects-autonomous-loop-assessment.md` — the feasibility assessment (two-tier cascade, risk register R1-R8, proxy panel, MVP phasing, the minimal API contract). This document operationalises Tier-2, the fixtures, the governance, and the test plan; it does not restate the inner-loop design (that is documents 01-03 of this PRD set). Read the assessment first if you have not.
>
> **Authority hierarchy (load-bearing).** Repository instructions (`.claude/CLAUDE.md`, `AGENTS.md`), current source, runtime evidence, and hardware proof outrank this PRD. Where a token, flag, or env var below is marked `[CONFIRM AGAINST SOURCE during build: ...]`, the source file is canonical — do not ship a value invented from this document; read the named file and bind the real token at build time.

---

## 0. Scope, non-goals, and the one-sentence shape

**In scope (this document):** the *outer* loop — the Tier-2 on-device confirmation bridge, the audio-fixture corpus that drives both tiers, the governance/doctrine rails, the R1-R8 build constraints, and the phased milestone + test plan.

**Out of scope (this document):** the Tier-1 host-sim inner loop mechanics (`render_replay` host-compile, `loop.py` driver, `champion.json` schema, the proxy-metric maths) — those are owned by PRD documents 01-03. This document references them as upstream dependencies but does not specify them.

**Hard non-goals (never built by this loop):**
- Autonomous firmware flashing or uploading. The loop's write-scope **stops at host/testbed artefacts.** Firmware integration and any device write are a **separate, human-initiated, gated step** (`/k1-firmware-change-gate`).
- Autonomous calibration. The loop never fires `start_noise_cal` or any silence-assuming command.
- Production firmware that depends on the capture/replay/probe instrumentation. Those are dev-only, compile-gated, and must compile out of any shippable build.

**One sentence:** the inner loop (Tier-1, fast, deterministic, host-sim) ranks effect variants and emits a `≤5-6` shortlist; the Tier-2 bridge (slow, human-initiated, MAC-verified) takes a shortlist survivor, captures the **real post-quant K1 output** via `vpab_capture`, checks it against the host-sim prediction (sim→hardware drift), and attaches an on-device evidence artefact that lets the Captain's eye promote it to `champion` (= the new `[MEASURED]` regression floor).

---

## 1. Tier-2 on-device confirmation bridge

### 1.1 Why Tier-2 exists (R3, R4)
Tier-1 is a **model.** It models effect maths only — it does **not** model the LGP optics, FastLED colour-correction, temporal dithering, gamma, or dual-channel interaction. A green Tier-1 sim is *necessary but not sufficient*. Tier-2 is the only tier permitted to gate a ship decision, because it observes the bytes the LEDs actually receive. This directly discharges R3 (sim→hardware divergence) and R4 (deterministic-but-wrong confidence): the sim *ranks*, the device *certifies*.

### 1.2 The confirmation flow (HUMAN-INITIATED, gated, never autonomous)

Tier-2 is invoked **by a human operator** (Captain or a Captain-authorised agent under an active firmware-change lane), one shortlist survivor at a time. There is no scheduler, no auto-trigger, no "promote-all". The flow:

```
PRECONDITION  Tier-1 shortlist exists; survivor S has a host-sim prediction
              (predicted leds[t] + predicted VPABMetricPayload[t]) under a named fixture.

STEP 0  HUMAN GATE — operator opens /k1-firmware-change-gate for survivor S.
        No device is touched before this gate is opened.

STEP 1  BUILD (host-side, no device) — integrate S's effect/params into a
        dev-instrumented firmware build with the capture lane compiled IN
        (see §3 Developer Instrumentation Boundary): PlatformIO build of the
        dev/trace environment. Build must be clean (no warnings-as-errors trip,
        no missing-symbol). This artefact is NON-SHIPPABLE and labelled so.

STEP 2  TARGET IDENTITY VERIFY (mandatory, pre-flash) — resolve the intended K1
        by port + stable hardware identity (USB MAC). Wrap the upload in
        k1_upload_guard.py so the flash aborts if the MAC on the port does not
        match the declared target.
        [CONFIRM AGAINST SOURCE during build: scripts/platformio/k1_upload_guard.py]
        — confirm the env var that declares the expected MAC (e.g. K1_EXPECTED_MAC
        or the env→MAC mapping the guard reads) and the exact upload-wrap invocation.

STEP 3  FLASH (human-initiated) — only after STEP 2 passes, run the guarded
        PlatformIO upload to the verified device. Record the verified identity
        (port + MAC + chip ID + firmware version banner) in the evidence.

STEP 4  ARM CAPTURE — over the serial monitor, send the vpab_capture arm command
        for the chosen mode/channel, frame budget, and (bytes | metrics | both).
        [CONFIRM AGAINST SOURCE during build: SPECTRASYNQ_K1_FIRMWARE/vpab_capture.{h,cpp}]
        — confirm the exact arm token, its arguments, the stop/disarm token, and
        whether arm is bounded-by-frame-count or stop-terminated.

STEP 5  DRIVE — play the SAME named audio fixture (§2) used for the Tier-1
        prediction, so the comparison is like-for-like. Capture runs over a
        bounded frame window. (Calibration is NOT touched here — see §3.2.)

STEP 6  STOP + DRAIN — send the stop/disarm command; drain the VPAB records from
        the serial buffer.
        [CONFIRM AGAINST SOURCE during build: SPECTRASYNQ_K1_FIRMWARE/vpab_capture.{h,cpp}]

STEP 7  PARSE — feed the captured serial log to vp_capture.py to extract the
        per-frame VPABBytesPayload (leds[LED_COUNT*3]) and the ~40-field
        VPABMetricPayload, writing a .vpab.json (same family as the existing
        docs/forensics/runtime-evidence/*.vpab.json artefacts).
        [CONFIRM AGAINST SOURCE during build: scripts/regression-harness/vp_capture.py]
        — confirm the input/output flags, the VPAB record prefix it matches
        (assessment cites records of the form `VPAB,ver=1,...`), and the
        strict/smoke/proof JSON variants it can emit.

STEP 8  DRIFT CHECK — run vp_diff.py to compare (a) the captured device frames
        against the Tier-1 host-sim PREDICTED frames for the same survivor+fixture,
        AND (b) the captured device frames against the current champion's device
        capture (regression floor). Produce a drift report: per-metric delta and a
        bytes-level frame delta.
        [CONFIRM AGAINST SOURCE during build: scripts/regression-harness/vp_diff.py]
        — confirm the two-input invocation, the tolerance/threshold flags, and the
        bit-hash vs fp-tolerant comparison mode. NOTE the project rule: a
        discovered gate failure on benign reassociation (e.g. -ffast-math) is fixed
        as a class with an fp-tolerant gate, NOT chased per-mode (see MEMORY:
        "Amend broken gates" / mode-11 resolution). Use the fp-tolerant comparison
        for cross-tier drift; reserve bit-hash for host-only same-build regression.

STEP 9  EVIDENCE ARTEFACT — assemble the on-device [MEASURED] artefact:
        verified identity, fixture name, arm parameters, captured .vpab.json,
        the sim→hw drift report, the regression-vs-champion report, perf
        (µs/frame), and the NaN/overflow guard result. This is what the Captain's
        eye reviews. Compile/flash/capture is NOT visual proof on its own — the
        artefact carries the proxy evidence; the Captain's eye is the terminal
        aesthetic verdict.

STEP 10 PROMOTE (Captain's eye only) — if the Captain promotes S, S's device
        capture becomes the new champion (= the new [MEASURED] regression floor).
        If rejected, S is dropped; the artefact is retained as evidence, not
        re-iterated autonomously.
```

### 1.3 Sim→hardware drift check (the core Tier-2 value)
The drift check is the reason Tier-2 is not just "re-run on hardware". It quantifies how far the host-sim prediction was from the device truth, per metric and per frame:
- **Pass-band (sim trustworthy):** drift within a frozen tolerance on the canon-mapped metrics (`com_delta_leds`, `com_slope_delta_pct`, `flicker_score`, `energy_delta_pct`, `changed_led_pct`). The sim model is validated for this effect class; future variants of this class may be pruned at Tier-1 with higher confidence.
- **Fail-band (sim drifted):** drift exceeds tolerance → the survivor is NOT certified, AND the drift is logged as a **sim-model defect** to feed back into Tier-1 calibration (the testbed `calibration/` pattern is the donor). A persistently drifting effect class downgrades Tier-1's authority for that class until the model is re-fit.

The tolerance is a **frozen gate definition** (R5): it is set once, ratified, and may only be loosened by Captain ratification with a tombstone of the old value. No silent carve-out.

### 1.4 What Tier-2 explicitly does NOT do
- It does **not** flash autonomously. Every flash is preceded by STEP 0 (human gate) and STEP 2 (MAC verify).
- It does **not** run calibration. It assumes the device is already in a known-good calibrated reference state; if calibration is suspect, that is a separate human-gated procedure under the calibration policy (§3.2).
- It does **not** promote to champion. Promotion is the Captain's eye verdict only.
- It does **not** ship the captured build. The dev-instrumented build used for capture is non-shippable by construction.

---

## 2. Audio-fixture corpus

### 2.1 Purpose and invariants
Both tiers must be driven by the **same** canned audio-feature stimulus so that (a) Tier-1 runs are deterministic and reproducible, and (b) Tier-2 device captures are like-for-like comparable to the Tier-1 prediction (§1.2 STEP 5). A fixture is a **feature stream**, not a raw audio file: it is the per-frame drive vector the firmware's render path consumes.

**Drive vector per frame** (mirrors `SBAudioSnapshot` / `sb_onset_beat` / `sb_tempo`, per the assessment API contract):
```
drive[t] = { novelty, silence, spectrum[NUM_FREQS], vu, chromagram[12], beat_phase }
```

**Rate invariants (load-bearing — do NOT change the main sample rate):**
- The **audio-pipeline (AP) rate is 133 Hz** (12800/96; *not* 39 Hz). The spectrum/VU/chromagram fields are produced at this rate.
- The **novelty/onset/beat clock is a decoupled 50 Hz** (Emotiscope-pattern decoupled novelty clock; `sb_tempo` provisional). `novelty` and `beat_phase` are emitted on this clock.
- Fixtures must encode BOTH rates correctly. A fixture stores its AP-rate fields at 133 Hz and its novelty-rate fields at 50 Hz (or stores both at a common high rate with the source-rate tagged), and the replay driver resamples/holds to whatever the render path expects. Do not collapse the two rates into one — the beat-correlation proxy depends on the 50 Hz novelty clock being faithful (this is the #1-lane "beat stream unused" gap the loop is built to attack).
- Changing the main `SAMPLE_RATE` is explicitly out of scope (HIGH blast-radius; deliberately punted). Fixtures adapt to the firmware, never the reverse.

### 2.2 Canned drive set — scenario names (reuse runtime-evidence)
Fixtures reuse the scenario names already present in `docs/forensics/runtime-evidence/` so that captures, manifests, and rubrics line up across the existing evidence base. Canonical seed set:

| Fixture name | Character | Source/analogue in runtime-evidence |
|---|---|---|
| `steady-groove` | constant 4/4 mid-tempo, stable energy, clear downbeat | `2026-06-01T195050-frames-steady-groove`, `...regard-late` |
| `kick-drop-heavy` | sparse verse → hard drop, big transient onsets | `2026-06-01T195050-frames-kick-drop-heavy`, `...drop-heavy-shelter-main` |
| `sparse-breakdown-build` | low-density breakdown rising into a build | `2026-06-01T195050-frames-sparse-breakdown-build`, `...sparse-build-carte-early` |
| `high-density-finale` | dense, high-energy, sustained | `2026-06-01T213207-frames-high-density-carte-finale` |
| `vocal-chorus-mid` | vocal-led, mid-density, melodic | `2026-06-01T213207-frames-vocal-chorus-touchme-mid` |

### 2.3 Octave-trap genres (mandatory for beat-reactive effects)
Beat/tempo trackers commonly mis-octave (lock to half/double tempo) on genres with strong off-beat or syncopated low end. Because the loop's headline value is *born-beat-reactive* effects, the corpus MUST include octave-trap genres so that beat-correlation proxies are stress-tested, not just validated on the easy `steady-groove` case:

| Fixture name | Genre | Octave-trap stressor |
|---|---|---|
| `reggae-offbeat` | reggae | skank on the off-beat, sparse downbeat — invites half-tempo lock |
| `dub-halftime` | dub | heavy delay/space, half-time feel — invites double-tempo lock |
| `dnb-amen` | drum & bass | ~170 BPM breakbeat — invites half-tempo lock to ~85 |
| `hiphop-boombap` | hip-hop / boom-bap | swung kick/snare, syncopation — invites phase/octave error |

A beat-reactive effect that scores well on `steady-groove` but collapses on `reggae-offbeat` or `dnb-amen` is a Goodhart failure (R2) and must NOT be promoted on the strength of the easy fixtures alone. The shortlist proxy panel reports beat-correlation **per fixture**, and the octave-trap fixtures are weighted into the promotion decision.

### 2.4 Generation, storage, and provenance
- **Generation:** fixtures are generated by extracting the drive vector from reference music captures (the existing `*-frames-*` evidence dirs and `ap_capture_leg.py` / `parse_serial.py` / `onset_beat_replay.py` paths are the donor mechanism), OR synthesised analytically for clean stressors (e.g. a metronomic `steady-groove` with known ground-truth BPM for beat-correlation calibration). Each fixture records HOW it was generated.
- **Storage:** one fixture = one versioned, deterministic artefact under a dedicated fixtures dir (e.g. `scripts/regression-harness/fixtures/` or `docs/prd/ve-auto-loop/fixtures/` — confirm location against PRD-01 inner-loop layout). Binary feature streams stay out of git unless small and explicitly required (workspace build-artifact hygiene); large binaries are referenced by manifest + checksum, mirroring the existing `*-corpus-manifest.json` pattern.
- **Provenance manifest:** a single canonical `fixtures-manifest.json` (one file, append-on-change, changelog-tracked) lists each fixture: name, genre/character, AP-rate, novelty-rate, frame count, ground-truth BPM (where known), generation method, source evidence path, and checksum. This mirrors `2026-06-01-smart-auto-expanded-corpus-manifest.json` and `2026-06-01-smart-auto-expanded-corpus-rubric.md` already in runtime-evidence.
- **Determinism:** a fixture + a seed must yield bit-identical Tier-1 frames (host) and metric-identical Tier-2 frames (device), per the API contract invariant. A fixture whose replay is non-deterministic is a defect, not a fixture.

---

## 3. Governance & doctrine (load-bearing — cite project `.claude/CLAUDE.md`)

These are not advisory. They are build constraints. Each is quoted from the project `.claude/CLAUDE.md` (and global rules where noted) and translated into what the build must do.

### 3.1 Developer Instrumentation Boundary
Project `.claude/CLAUDE.md` states verbatim:

> "Developer, harness, trace, benchmark, probe, and diagnostic code **never ships with production firmware**. Production build environments must not include MabuTrace, trace-dev dependencies, developer-only feature flags, implementation sources, storage, command surfaces, or behaviour that relies on instrumentation being present. Production may contain only audited no-op macro declarations required to keep shared source buildable."

**Build constraint.** `vpab_capture`, `render_replay`, `motion_probe`, and any trace-dev hook are **dev-only and compile-gated.** They live behind a build-time flag (PlatformIO dev/trace environment) and must compile **out** of the production environment to no-ops. The production firmware must build and run with zero dependency on any of them — no probe symbols, no capture command surface, no instrumentation-conditioned behaviour. The Tier-2 capture build is, by definition, a non-shippable dev build and must be labelled non-shippable in build config, docs, and evidence.

> "MabuTrace is not optional lore. ... If the unknown is nested frame timing, audio-to-render causality, counter disagreement, frame-drop causality, race/reorder proof, diagnostic harness perturbation, or another timeline/causality trigger, MabuTrace dev-trace is mandatory. SB-native scalar diagnostics may detect or quantify the symptom; they do not close causal attribution."

**Build constraint.** The VE-Auto-Loop proxy panel and VPAB metrics are **scalar/aesthetic evidence**, not timeline/causality evidence. They may rank, prune, and certify *visual* outcomes. They may NOT be used to make a timing/causality claim (e.g. "this effect causes a frame drop", "render is winning the race"). If a Tier-2 capture surfaces a timing/causality question (perf-budget blown, dropped frame, cross-core ordering), that is a MabuTrace dev-trace question, and the answer is `blocked`/`approval` until the trace-dev lane runs it — never "verified" from scalar VPAB metrics alone.

### 3.2 Calibration command policy
Project `.claude/CLAUDE.md` states verbatim:

> "`start_noise_cal` and any other calibration command that assumes silence is **NEVER auto-fired by the agent**. The agent MUST wait for Captain to confirm the silence window verbally (e.g. 'music paused, go') before sending the command, and MUST wait for Captain to say 'resume' before assuming normal acoustic conditions again. Violation = STOP-and-rollback."

**Build constraint.** No path in the loop — Tier-1 or Tier-2 — emits `start_noise_cal` or any silence-assuming calibration command. Tier-2 captures run against an already-calibrated device in a known reference state. If calibration is suspect, the operator handles it manually under the silence-window protocol *outside* the loop. The loop has no calibration command surface at all. (Origin: 2026-05-24 Stage 7 incident — auto-`start_noise_cal` during music poisoned `SWEET_SPOT_MIN_LEVEL` 281→745.)

### 3.3 Hardware-target discipline
Project `.claude/CLAUDE.md` states verbatim:

> "Before opening a serial monitor, flashing/uploading firmware, erasing flash, or sending any device-write command, verify the exact target by port plus stable hardware identity: USB MAC, adapter serial, chip ID, board role, or another captured identity signal. If identity is missing, ambiguous, stale, or mismatched, stop and resolve the target before touching the device. Record the verified identity in the evidence."

**Build constraint.** Tier-2 STEP 2 is mandatory and gating: `k1_upload_guard.py` resolves the device by port + USB MAC and **aborts the flash on mismatch.** The arm/stop serial commands (STEP 4/6) only run after identity is confirmed. The verified identity (port + MAC + chip ID + firmware banner) is recorded in the STEP 9 evidence artefact. There is no "trust the only device on the bus" path.
`[CONFIRM AGAINST SOURCE during build: scripts/platformio/k1_upload_guard.py]` — bind the actual env→MAC variable name and the abort behaviour.

### 3.4 Git discipline
Project `.claude/CLAUDE.md` states verbatim:

> "Never commit untested or unreviewed work. Before committing, inspect the actual diff, stage only the intended files, run the relevant tests/builds, and record the evidence. Do not commit known-broken code just because a task is 'finished.' Remote pushes, destructive history changes, and public release tags require Captain's explicit instruction or an active lane that clearly includes that publication step."

**Build constraint.** The loop commits only host/testbed artefacts (fixtures, `champion.json`, results, drift reports) and only when built+tested-clean. Firmware integration commits go through `/k1-firmware-change-gate`. **No push, no force-push, no tag, no destructive history op** without explicit Captain instruction or an active lane that names the publication step. Champion promotion is a commit of the new regression floor — it is gated by the Captain's-eye verdict, not by the loop.

### 3.5 Loop write-scope STOPS at host/testbed (R7)
The loop's autonomous write-scope is: fixtures, `champion.json`, shortlist/contact-sheet artefacts, drift/regression reports, results files. **Firmware source integration and any device write are NOT autonomous** — they are the human-gated `/k1-firmware-change-gate` step. An agent operating the loop may *prepare* a firmware integration diff, but landing it and flashing it require the gate to be opened by a human and the MAC verify to pass. This is the structural mitigation for R7 (doctrine breach via autonomous firmware write/upload).

### 3.6 Gate definitions are frozen — no silent carve-outs (R5)
All gate thresholds — the sim→hw drift tolerance (§1.3), the regression floor, the perf budget (µs/frame), the NaN/overflow guard, the proxy-panel accept bands, the iteration/shortlist caps — are **frozen definitions.** A new carve-out (e.g. the existing `frame>10` carve-out) requires **Captain ratification + a tombstone of the prior definition.** The loop may not relax its own gates to let a candidate through. Self-relaxing gates are the R5 failure mode and are forbidden by construction: gate definitions live in one canonical, changelog-tracked location, and any change is a reviewed diff, never a runtime mutation.

### 3.7 Founder Execution Boundary (reporting)
Per global rules, the loop reports decision-grade evidence to the Captain (shortlist contact sheet + proxy panel + on-device artefact), not logs/file-dumps/test spam. The Captain is the terminal aesthetic gate and the promotion authority — the Captain is NOT in the per-iteration execution loop. Routine validation (builds, captures, parses, drift checks) is executed autonomously within the host/testbed write-scope and surfaced only as the batched evidence artefact.

---

## 4. Risk register → actionable build constraints

Each risk from the assessment's R1-R8 register, translated into the concrete mitigation baked into THIS build.

| # | Risk | Build constraint (what the code/process does) |
|---|---|---|
| **R1** | Testbed models the WRONG firmware lineage (firmware-v3 BeatPulse, not `SPECTRASYNQ_K1_FIRMWARE`) | The loop is built on **THIS repo's seams** — `vpab_capture` (real post-quant output port) + a `render_replay` host-compile of the real `light_mode_*.cpp` + `render_params.cpp`. The PyTorch testbed is a **pattern donor only** (loop architecture, metric scaffolding, gradient-recovery harness) — its frozen `core/` is never in the scoring path. Every fixture and every capture targets `SPECTRASYNQ_K1_FIRMWARE`. Acceptance of any milestone requires that the effect under test is a real shipping-lineage `lightshow_modes` effect. |
| **R2** | Goodhart — physics/scalar metrics cannot judge musical compulsion | The loop is a **generator + pruner, never the aesthetic judge.** The Captain's eye is the **terminal, non-negotiable** gate (§3.7), reviewing a batched contact sheet, never per-iteration. Beat-correlation is reported **per fixture incl. octave-trap genres** (§2.3); a candidate strong only on easy fixtures is not promoted. No metric or weighted score auto-promotes a champion. |
| **R3** | Sim→hardware divergence (uint16/LGP/gamma/dither/dual-channel) | **Tier-2 is mandatory before "shipped".** The sim ranks; the device certifies. STEP 8 drift check quantifies divergence per metric and per frame; fail-band blocks certification AND logs a sim-model defect. Tier-1 confidence for an effect class is downgraded when its drift persists. |
| **R4** | Deterministic-but-wrong confidence (flakiness engineered out, green ≠ correct) | A green Tier-1 sim is **necessary, not sufficient.** Promotion requires an on-device `[MEASURED]` evidence artefact (STEP 9). Determinism is a correctness property of the harness, not evidence about the effect. The artefact, not the green run, is what the Captain reviews. |
| **R5** | Self-relaxing gates (a `frame>10` carve-out already exists) | **Gate definitions frozen** (§3.6). One canonical changelog-tracked location for all thresholds. Any new carve-out = Captain ratification + tombstone of the old definition. The loop cannot mutate its own gates at runtime. |
| **R6** | Churn amplification (88% churn precedent; doc/checkpoint exhaust) | **Hard caps:** iteration cap and shortlist cap (≤5-6 candidates/cycle). **Reject-and-delete** rejected variants (no graveyard of dead variants). **One canonical results file** per cycle (append dated sections, changelog footer) — no `cycle-1.md`/`cycle-2.md` proliferation. Fixtures and champion are single canonical artefacts. |
| **R7** | Doctrine breach via autonomous firmware write/upload | **Loop write-scope stops at host/testbed** (§3.5). Firmware integration + flash = human-gated `/k1-firmware-change-gate` + MAC verify. No autonomous flash path exists in the code. |
| **R8** | Unconverged surrogate (`gru_incomplete`) standing in for truth in the scoring path | **No unvalidated surrogate in the scoring path.** Any ML surrogate (Ext-3) is gated by its OWN green validation gate before it may influence pruning. Until then, scoring uses the defensible analytic proxies + on-device VPAB metrics only. |

---

## 5. Phasing & milestones

Phasing follows "owned means first" (model-router): close the loop with no generative machinery, then add proxies, then mutation, then surrogate-driven proposal, with the Tier-2 bridge built in parallel so survivors can be certified as soon as there are survivors.

### MVP-0 — close the loop (no generative machinery)
**Build:** `render_replay` for ONE real K1 mode (host-compile `light_mode_X.cpp` + `render_params.cpp` against the `Arduino.h`/FastLED/`SQ15x16` stub set; dump `leds_16` in the `VPABBytesPayload` byte layout) + a `loop.py` driver + a `champion.json` regression baseline + 3-5 canned fixtures from §2.2 (`steady-groove`, `kick-drop-heavy`, `sparse-breakdown-build`). "Edit" = a parameter sweep over existing `RenderParams` knobs. Prefer a mode already reading `active_render_params()` (easiest first target).
**Proves:** the host-sim inner loop is deterministic, reproducible, and regression-gated against a frozen champion, on the RIGHT firmware lineage (R1).

### MVP-1 — beat-correlation + guards + Captain gate artefact
**Build:** the beat-correlation proxy tied to `sb_tempo`'s 50 Hz novelty clock (xcorr of `temporal_volatility` vs the novelty/onset stream), reported per fixture; the NaN/overflow guard; the perf-budget guard (µs/frame); the **batch-review contact-sheet artefact** (side-by-side ≤5-6 candidates + proxy panel) that IS the Captain gate. Add the octave-trap fixtures (§2.3) to the corpus.
**Proves:** the loop produces born-beat-reactive candidates, stress-tested on octave-trap genres, and emits a decision-grade artefact the Captain can verdict in one pass (R2, R6).

### Ext-2 — effect-template / operator mutation
**Build:** mutation beyond parameter sweeps — effect-template/operator composition (the testbed `experimental/` operator engine is the pattern donor), still scored by the MVP-1 proxy panel + guards, still capped (R6).
**Proves:** the generator can propose structurally novel effects (not just retuned knobs) while staying inside the frozen gates and caps.

### Ext-3 — optimiser / surrogate-driven proposal
**Build:** optimiser- or surrogate-driven proposal (the testbed `training/` DIFNO/FiLM pattern is the donor). **Gated by R8:** any surrogate must pass its OWN validation gate before it enters the scoring/proposal path; until then it is an offline experiment, not part of the loop.
**Proves:** proposal efficiency improves without an unvalidated surrogate ever judging a candidate.

### Tier-2 bridge (built in PARALLEL, from MVP-0 onward)
**Build:** wrap the PlatformIO dev/trace build + `k1_upload_guard.py` (MAC-verified) + the `vpab_capture` arm/stop serial flow + `vp_capture.py`/`vp_diff.py` parse + the sim→hw drift check + the `vpab→tensor` adapter, as the §1.2 flow. Human-initiated and gated end to end.
**Proves:** a Tier-1 survivor can be promoted to on-device `[MEASURED]`, sim→hardware drift is quantified, and no flash happens without a human gate + MAC verify (R3, R4, R7).

---

## 6. Test plan (what proves each milestone)

| Milestone | Test (what is run) | Pass condition (what proves it) |
|---|---|---|
| **MVP-0** | (a) Host-compile `render_replay` for the chosen real mode; (b) replay each of the 3-5 fixtures twice with the same seed; (c) sweep ≥3 `RenderParams` values; (d) regression-compare against `champion.json` | Build clean; same-seed runs are **bit-identical** (host); sweep produces distinct `leds[]` per param; regression gate runs and reports pass/fail against the frozen champion; all artefacts in ONE canonical results file. Effect under test is a real `SPECTRASYNQ_K1_FIRMWARE` mode (R1). |
| **MVP-1** | (a) Run the corpus incl. octave-trap fixtures; (b) compute beat-correlation per fixture; (c) inject a NaN and an overflow into a synthetic variant; (d) inject a perf-blown variant; (e) generate the contact-sheet artefact for a ≤5-6 shortlist | Beat-correlation reported per fixture and discriminates `steady-groove` from `reggae-offbeat`/`dnb-amen` (no silent half/double-tempo lock passing as good); NaN/overflow variant is **rejected** by the guard; perf-blown variant is **rejected** by the budget guard; contact sheet renders ≤6 candidates with the full proxy panel; no candidate auto-promoted (Captain gate required) (R2). |
| **Ext-2** | (a) Generate ≥1 structurally-mutated effect (not a sweep); (b) score it through the MVP-1 panel; (c) confirm iteration + shortlist caps hold | Mutated effect is scored and ranked with no gate relaxation; caps enforced (iteration count, ≤5-6 shortlist); rejected variants deleted, not archived (R6). |
| **Ext-3** | (a) Stand up the surrogate offline; (b) attempt to route it into the scoring path WITHOUT its validation gate green | The loop **refuses** to use the surrogate in scoring until its own gate is green (R8); with the gate green, surrogate-proposed candidates still pass through the full proxy panel + guards + Tier-2 before any promotion. |
| **Tier-2 bridge** | (a) Open `/k1-firmware-change-gate`; (b) build dev/trace firmware for a survivor; (c) attempt flash with a WRONG declared MAC; (d) flash with the correct MAC; (e) arm `vpab_capture`, drive the matching fixture, stop, parse via `vp_capture.py`; (f) `vp_diff.py` against the host-sim prediction AND against champion | Wrong-MAC flash is **aborted** by `k1_upload_guard.py` (R7/§3.3); correct-MAC flash proceeds and verified identity is recorded; `vpab_capture` produces `.vpab.json` parseable by `vp_capture.py`; drift report produced with per-metric + per-frame deltas; fail-band blocks certification and logs a sim-model defect (R3); dev build is labelled non-shippable and the production build still compiles with the capture lane gated OUT (R4/§3.1); no calibration command was ever emitted (§3.2); promotion happens only on the Captain's-eye verdict (R2). |

---

## 7. Bill of materials (build inventory)

| Item | Status | Path / source |
|---|---|---|
| Real output port (post-quant LED bytes + ~40-field metrics over serial) | **Exists** | `SPECTRASYNQ_K1_FIRMWARE/vpab_capture.{h,cpp}` |
| VPAB serial-log parser → `.vpab.json` | **Exists** | `scripts/regression-harness/vp_capture.py` |
| VPAB diff / regression comparator (fp-tolerant + bit-hash) | **Exists** | `scripts/regression-harness/vp_diff.py` |
| MAC-verified PlatformIO upload guard | **Exists** | `scripts/platformio/k1_upload_guard.py` |
| Host-compile replay pattern (donor → generalise to `render_replay`) | **Exists (donor)** | `scripts/regression-harness/tempo_replay.py` |
| Onset/beat replay + event metrics (fixture-gen donor) | **Exists (donor)** | `scripts/regression-harness/{onset_beat_replay.py, onset_beat_event_metrics.py, ap_capture_leg.py, parse_serial.py}` |
| VPAB gate / runtime matrix (gate-pattern donor) | **Exists (donor)** | `scripts/regression-harness/{vpab_gate.py, vpab_runtime_matrix.py}` |
| Existing scenario captures (fixture sources) | **Exists** | `docs/forensics/runtime-evidence/2026-06-01T*-frames-*`, `*-corpus-manifest.json`, `*-corpus-rubric.md` |
| `render_replay` (host-compile real `light_mode_*` + `render_params`) | **NET-NEW (MVP-0)** | PRD-01 inner loop |
| `loop.py` driver + `champion.json` baseline | **NET-NEW (MVP-0)** | PRD-01 inner loop |
| Fixture corpus + `fixtures-manifest.json` (incl. octave-trap genres) | **NET-NEW (MVP-0/1)** | §2 |
| Beat-correlation proxy + NaN/overflow + perf guards | **NET-NEW (MVP-1)** | §2.3, §6 |
| Contact-sheet / proxy-panel Captain-gate artefact | **NET-NEW (MVP-1)** | §3.7, §6 |
| Tier-2 bridge: build+guard+arm+parse+drift+`vpab→tensor` wrap | **NET-NEW (parallel)** | §1.2 |
| `/k1-firmware-change-gate` integration step | **Exists (skill)** | human-gated firmware-change gate |

> All `[CONFIRM AGAINST SOURCE during build: ...]` items in §1 and §3.3 must be bound to real tokens/flags/env-vars by reading the named source files at build time. Do not ship a value invented from this PRD.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus (PRD4-tier2) | Created — Tier-2 confirmation bridge (arm vpab_capture → capture → vp_capture/vp_diff parse → sim→hw drift check → MAC-verified guarded flash, human-initiated + gated), audio-fixture corpus (steady-groove/kick-drop-heavy/sparse-breakdown + octave-trap reggae/dub/DnB/hip-hop, AP 133 Hz / decoupled 50 Hz novelty), governance/doctrine constraints cited verbatim from project .claude/CLAUDE.md, R1-R8 risk register → build constraints, MVP-0→MVP-1→Ext-2→Ext-3→Tier-2 phasing + test plan + milestone→acceptance table + BoM. Exact serial arm/stop tokens, vp_capture/vp_diff flags, and k1_upload_guard env→MAC var flagged [CONFIRM AGAINST SOURCE during build]; doctrine clauses cited from session context, not re-read. |
