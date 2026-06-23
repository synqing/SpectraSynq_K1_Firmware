---
abstract: "Zero-context build spec for the VE-Auto-Loop control driver (`loop.py`, in scripts/regression-harness/) plus the Captain batch-gate artefact. Defines the autonomous edit→render_replay→score→regression→rank→shortlist cycle, the candidate-generation surface (MVP-0 parameter sweep over RenderParams knobs; Ext operator/template mutation), the search strategies (grid/random/optimiser), the contact-sheet HTML/PNG human gate, the exact CLI, the exit-code contract, and the load-bearing churn governance (per-cycle iteration cap, shortlist cap ≤5, reject-and-delete, one canonical results file). Reads the design SOT (visual-effects-autonomous-loop-assessment.md) for the TRIZ separation-in-time resolution; depends on PRD-02 for the scorer and on `render_replay` (host-compile of a real light_mode_*.cpp) for frames. Read before implementing loop.py or wiring the Captain review gate."
---

# VE-Auto-Loop — Loop Driver and Human Batch-Gate (Build Spec)

*Build document 03 of the VE-Auto-Loop PRD set. Zero-context-buildable: an implementer should be able to write `loop.py` and the gate artefact from this file alone, reading only the named dependencies for their exact signatures.*

## 0. Scope and dependencies

This document specifies **two artefacts**:

1. **`loop.py`** — the control loop / driver. New file at
   `scripts/regression-harness/loop.py`. Owns the
   mutate → render_replay → score → regression → rank → shortlist cycle, the
   CLI, and the exit-code contract.
2. **The Captain batch gate** — a contact-sheet artefact (top-N≤5 side-by-side
   strip renders + a proxy panel under each) plus the verdict feedback path
   that promotes a chosen variant to `champion.json`.

It does **not** specify the renderer or the scorer themselves; those are
external dependencies the driver orchestrates:

| Dependency | Owned by | What `loop.py` consumes |
|---|---|---|
| **Design SOT** | `docs/architecture/visual-effects-autonomous-loop-assessment.md` | The TRIZ separation-in-time resolution (autonomous per-iteration scoring drives search; Captain's eye is a *periodic batch gate* over a ≤5–6 shortlist, never per-iteration, never on rejects); the candidate-shortlist gate; the churn risk that mandates §6. |
| **PRD-01 (corpus + render_replay)** | `01-*.md` | `render_replay(effect_id, params, drive, frames, seed) -> Frames` returning the canonical `leds[N*3]` + `VPABMetricPayload`-shaped metrics (see §1.3); the fixture corpus loader. |
| **PRD-02 (scorer)** | `02-*.md` | `score(frames, drive) -> ProxyPanel` (the defensible proxy vector) and `regress(candidate_panel, champion_panel) -> RegressionVerdict` (hard guards + relative-regression decision). |

Pattern donors (READ-ONLY; **do not re-point or import** — copy idiom only):

| Donor | Pattern borrowed |
|---|---|
| `scripts/regression-harness/tempo_replay.py` (this repo) | Host-`clang++` compile-against-stub idiom; deterministic synthetic drive; `--json`/exit-code contract; `ROOT`/`FIRMWARE` path resolution; `--keep-dir` for forensics. **This is the closest in-repo donor and `loop.py` MUST follow its CLI and exit conventions.** |
| `scripts/regression-harness/vp_capture.py` (this repo) | Exit-code semantics (`0`=full evidence captured, `2`=incomplete, `1`=error); stderr-summary-line idiom. |
| `SpectraSynq.K1_Testbed/scripts/experiment.py` | `_run_sweep_experiment` shape: build reference once → sweep one key → `compare_runs` each candidate → collect `results[]` → write one `sweep_summary.json`. Donor for the **sweep + canonical-results-file** pattern (§2, §6). |
| `SpectraSynq.K1_Testbed/scripts/batch_export.py` | Named-preset/library batching, `--list`, resolve-against-defaults. Donor for the **named-effect + RenderParams-defaults** resolution and `--list`/`--dry-run`. |
| `SpectraSynq.K1_Testbed/vis/renderers.py` | `strip_frame` (single-frame RGB strip, matplotlib Agg headless) and `comparison_view`. Donor for the **contact-sheet strip renders** in §4. |

> **Doctrine guard (load-bearing).** `loop.py` write scope is the host loop only:
> it compiles host code, renders, scores, and writes to **one** results
> directory. It MUST NOT flash, upload, erase, open a device serial port, or
> mutate any firmware source. On-device confirmation is a separate Tier-2 lane
> (PRD-tier-2-bridge) gated by `k1-firmware-change-gate`. The loop ranks; the
> device certifies; the Captain promotes.

## 1. `loop.py` — the control loop

### 1.1 Inputs (the search problem)

A single `loop.py` invocation is parameterised by:

| Input | Source | Meaning |
|---|---|---|
| `effect_id` | `--effect <name|uint8>` | The `lightshow_modes` mode under test. Resolves a real `light_mode_<name>.cpp`. One effect per invocation (one canonical lane). |
| **RenderParams space** | `--space <space.json>` | The mutation surface: which `RenderParams` fields vary and over what ranges (§2.1). |
| **fixture corpus** | `--corpus <dir>` (default: the canned audio fixtures from PRD-01) | The fixed set of drive scenarios every candidate is rendered against (e.g. `steady-groove`, `kick-drop-heavy`, `sparse-breakdown-build`, reused from `docs/forensics/runtime-evidence/`). |
| `champion` | `--champion <champion.json>` (default `results/<effect>/champion.json`) | The frozen regression floor — the current best, its `RenderParams`, its proxy panel. Bootstraps from the effect's shipped defaults on first run. |
| budget | `--max-iterations N` (hard cap, §6) · `--shortlist K` (≤5, §6) · `--seed S` (determinism) | Bounds the search. |

### 1.2 The cycle (one iteration)

```
for candidate in generator(space, strategy, seed)   # bounded by --max-iterations
    params      = champion.params  overlaid with  candidate.delta
    frames      = render_replay(effect_id, params, corpus_fixture, frames=F, seed=S)   # PRD-01
    panel       = score(frames, drive)                                                 # PRD-02
    verdict     = regress(panel, champion.panel)                                       # PRD-02: hard guards + relative
    if verdict.rejected:  REJECT-AND-DELETE (§6) ; continue
    survivors.append(Candidate(params, panel, verdict.score, per_fixture_panels))
rank survivors by composite score (desc)
shortlist = survivors[:K]                                                              # K ≤ 5
write canonical results file (§6) ; render contact sheet (§4)
```

Each candidate is rendered against **every** fixture in the corpus; the
composite score is the corpus aggregate (default: min across fixtures, so a
candidate must be good on *all* scenarios — Goodhart-resistant). The per-fixture
panels are retained for the shortlist only (rejects are deleted, §6).

**Hard guards run first and are absolute** (from PRD-02; the loop only routes
them): NaN/overflow → reject; perf-budget µs/frame blown → reject;
doctrine-regressor (motion-memory collapse, colour-clarity collapse) → reject.
A rejected candidate never reaches ranking and never persists.

### 1.3 Outputs (the frame/score contract the driver assumes)

The driver is schema-agnostic across tiers by design (Design SOT §"one frame
schema, two tiers"). It assumes `render_replay` returns, per fixture:

```
frames.leds[t]       : uint8[LED_COUNT*3]      # VPABBytesPayload byte layout
frames.metrics[t]    : VPABMetricPayload-shaped # the eval vector
```

The proxy panel (`score()` output, PRD-02) is built from those metrics. The
fields the loop and the gate panel surface (already present in
`vpab_capture.h` / testbed `vis/metrics.py`):

| Panel field | Source metric | Canon meaning |
|---|---|---|
| apparent-motion | `com_delta_leds`, `com_slope_delta_pct` | velocity / coherence vs the motion-canon px/frame band |
| aliveness | `energy_delta_pct`, `changed_led_pct` | is it doing anything |
| mechanical/chaos | `flicker_score` | jitter / strobe penalty |
| colour clarity | `channel_divergence` / `white_bias_score` | note-contrast vs wash-to-white |
| beat-correlation | xcorr(`temporal_volatility`, `sb_tempo` novelty/onset) | born beat-reactive (the #1-lane gap) |
| perf | µs/frame | budget guard |

INVARIANT (determinism): same `effect_id` + `params` + `corpus` + `seed`
⇒ bit-identical `leds` (host) and identical panel. The loop asserts this once
per run on the champion (a reproducibility self-check, mirroring
`experiment.py`'s reproducibility block); a mismatch is exit 1.

### 1.4 CLI

`loop.py` follows the `tempo_replay.py` argument/exit idiom.

```
loop.py run    --effect <name|id> --space <space.json> --corpus <dir>
               [--champion <champion.json>] [--max-iterations N] [--shortlist K]
               [--strategy grid|random] [--seed S] [--frames F]
               [--out <results_dir>] [--compiler clang++] [--keep-dir DIR]
               [--no-contact-sheet] [--json]

loop.py promote --effect <name|id> --candidate <rank|hash> [--results <dir>]
               # applies a Captain verdict: copies the chosen shortlist entry
               # into champion.json. The ONLY mutation of the regression floor.

loop.py list   --effect <name|id> --space <space.json>
               # enumerate the candidate grid WITHOUT rendering (cheap dry plan)

loop.py show   [--results <dir>]
               # print the current shortlist + champion summary; opens nothing
```

- `--strategy` defaults to `grid` for MVP-0 (deterministic, auditable),
  `random` (seeded) when the grid exceeds `--max-iterations`. Optimiser is an
  Ext strategy (§2.3), not MVP-0.
- `--json` emits the machine result (same shape as the canonical results file,
  §6) to stdout instead of the human summary, for harness chaining.
- `run` is fully autonomous end-to-end; `promote` is the single human-fed step.

### 1.5 Exit-code contract

| Code | Meaning | Mirrors |
|---|---|---|
| `0` | Ran the full budget, produced a ranked shortlist (≥1 survivor) + contact sheet + updated results file. | `vp_capture.py` `0` = full evidence |
| `2` | Ran, but **no survivor cleared the hard guards / regression floor** (empty shortlist). Results file written with `shortlist: []` and the rejection histogram. Not an error — a *negative result*, recorded. | `vp_capture.py` `2` = incomplete-but-clean |
| `3` | Determinism self-check failed (champion re-render not bit-identical). The loop is untrustworthy; no shortlist emitted. | new |
| `1` | Tooling error (compile failure in `render_replay`, missing corpus/space/champion, I/O). | `tempo_replay.py` `1` |

`promote` returns `0` on a clean champion update, `1` on a bad candidate
reference or write failure.

## 2. Candidate generation (phased)

### 2.1 MVP-0 — parameter sweep over existing knobs

The mutation surface is **`RenderParams` fields only** (`render_params.h` — the
heap-free, CONFIG-decoupled knob boundary; Design SOT §"minimal API contract").
No source edits. The `--space` JSON declares which fields vary and how:

```json
{
  "effect": "bloom",
  "fields": {
    "speed":        { "type": "float", "min": 0.5, "max": 3.0, "steps": 6 },
    "persistence":  { "type": "float", "min": 0.90, "max": 0.99, "steps": 5 },
    "palette_index":{ "type": "enum",  "values": [0, 1, 2, 3] }
  }
}
```

- A candidate is `champion.params` overlaid with one point in this space.
- The space MUST only name fields that exist in `RenderParams` for that effect;
  `loop.py list` validates field names against the effect's declared params and
  errors (exit 1) on unknown fields (mirrors `batch_export.py` unknown-preset
  rejection).
- Fields the space does not mention are pinned to the champion's value.

### 2.2 Search strategies (MVP-0)

| Strategy | When | Behaviour |
|---|---|---|
| `grid` (default) | grid size ≤ `--max-iterations` | full Cartesian product of `steps`/`values`. Deterministic, complete, auditable. |
| `random` (seeded) | grid size > `--max-iterations` | sample `--max-iterations` points with the seeded PRNG (Latin-hypercube-style stratified per field). Reproducible from `--seed`. |

If the requested grid exceeds the iteration cap and `--strategy grid` was
forced, `loop.py` refuses (exit 1) with the grid size and the cap — it never
silently truncates a grid (that would make the "complete" claim false).

### 2.3 Ext — operator / template mutation (post-MVP)

Beyond knob sweeps, the Ext phase mutates *structure*: insert/reorder/swap
render operators or instantiate effect templates (the testbed
`experimental/` operator engine is the pattern donor — `BiasedDiffuse`,
`GaussianInject` as parametric operators swapped into a pipeline). Ext adds:

- a `--strategy optimiser` (e.g. coordinate-descent or CMA-ES over the
  continuous fields, seeded; the testbed `training/` surrogate is the further
  pattern donor), and
- a template/operator catalogue in the `--space` schema (`"operators": [...]`).

Ext does not change the cycle, the gate, or the governance — only the
`generator()` source. **Ext is explicitly out of MVP-0 scope** and must not be
built until MVP-0 closes the loop on one effect.

## 3. The autonomous / human split (made concrete)

| Stage | Runs with **no human** | The single **batched human** touch |
|---|---|---|
| candidate generation (grid/random over RenderParams) | ✅ | |
| render_replay against the full fixture corpus | ✅ | |
| proxy scoring (PRD-02) | ✅ | |
| hard guards (NaN/overflow, perf, doctrine-regressor) | ✅ | |
| regression vs frozen champion | ✅ | |
| rank survivors, build shortlist (≤K) | ✅ | |
| reject-and-delete losers (§6) | ✅ | |
| write canonical results file | ✅ | |
| render the contact sheet | ✅ | |
| **review the ≤5 contact sheet, answer "captivating / promote?"** | | ✅ **Captain, once per cycle** |
| `loop.py promote` the chosen variant → `champion.json` | ✅ (mechanical, on Captain's verdict) | |

The human eye is engaged **exactly once per cycle**, over a ≤5-entry
side-by-side artefact, never per-iteration and never on rejects. This is the
TRIZ separation-in-time resolution of the human-eye contradiction (the eye is
the only valid aesthetic judge, but cannot be in a fast loop). The verdict is
the *only* signal that moves the regression floor.

## 4. The Captain batch gate — contact-sheet artefact

### 4.1 What it is

A single self-contained **HTML file** (with embedded PNG strips) written to
`<results_dir>/contact_sheet.html`, plus a fallback `contact_sheet.png`
(matplotlib small-multiple grid) for environments without a browser.

Layout — top-N≤5 candidates as a **side-by-side strip**, champion pinned as
column 0 for reference:

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  CHAMPION    │  #1  rank     │  #2  rank     │  #3  rank     │
│ ▓▓ strip ▓▓  │ ▓▓ strip ▓▓   │ ▓▓ strip ▓▓   │ ▓▓ strip ▓▓   │   ← strip_frame
│ (key frames  │ (key frames   │ (key frames   │ (key frames   │     per fixture,
│  per fixture)│  per fixture) │  per fixture) │  per fixture) │     stacked
├──────────────┼──────────────┼──────────────┼──────────────┤
│ proxy panel  │ proxy panel   │ proxy panel   │ proxy panel   │   ← bars/Δ vs
│ + Δvs champ  │ + Δvs champ   │ + Δvs champ   │ + Δvs champ   │     champion
│ params diff  │ params diff   │ params diff   │ params diff   │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

- **Strip renders:** reuse the `vis/renderers.py` `strip_frame` idiom — render
  each candidate's `leds` strip at a few representative frames per fixture
  (e.g. beat-aligned moments), stacked as a spacetime mini-heatmap so motion
  reads on a static page. Matplotlib `Agg`, headless.
- **Proxy panel under each:** the score vector (§1.3) as labelled bars, each
  annotated with Δ vs champion (green improve / red regress), plus the
  composite score and the per-field `RenderParams` diff from champion.
- **Generation:** the same exporter pattern as `batch_export.py` — iterate the
  shortlist, render each, write into one output dir. Generated automatically at
  the end of every `run` (unless `--no-contact-sheet`).

### 4.2 How the verdict feeds back

The contact sheet is **read-only evidence**; the Captain's verdict is applied
mechanically:

```
loop.py promote --effect bloom --candidate 2
```

This copies shortlist entry #2's `RenderParams` + proxy panel into
`champion.json` (atomic write: temp file + rename), appends a one-line entry to
the results-file changelog, and the new champion becomes the regression floor
for the next cycle. **`promote` is the only path that mutates `champion.json`.**
No promote = champion unchanged; the cycle's survivors are discarded on the next
`run` per §6. (Tier-2 on-device A/B confirmation, where required by the Design
SOT R3 mitigation, gates promotion to a *shipping* champion — out of scope for
this host loop; recorded here as the downstream hook.)

## 5. Why this is Goodhart-resistant (design rationale, brief)

Per Design SOT R2: the proxy metrics drive *search and pruning only*; they never
declare an effect good. The loop is a **generator + pruner**; the Captain's eye
is the terminal aesthetic gate. The corpus-min aggregation (§1.2) and the
beat-correlation proxy (§1.3) push candidates toward all-scenario,
beat-reactive behaviour rather than letting them overfit one metric on one
fixture. The champion-as-frozen-floor (§4.2) means scores can only ratchet up
under human verdict, not relax themselves (R5: gate defs are frozen; new
carve-outs need Captain ratification).

## 6. Churn governance (LOAD-BEARING)

This ecosystem had a ~88% churn window (Design SOT R6; the May27–Jun1 audit).
These controls are non-negotiable and are enforced **in `loop.py`**, not by
convention:

1. **Hard per-cycle iteration cap.** `--max-iterations` (default 64) is an
   absolute bound on candidates rendered per `run`. The loop counts and stops;
   it cannot be exceeded by config. No unbounded search.
2. **Shortlist cap ≤ 5.** `--shortlist K` is clamped to `K ≤ 5`. The Captain
   never sees more than 5 candidates per cycle (the human-attention budget).
3. **REJECT-AND-DELETE.** Rejected variants do **not** accrete as files,
   checkpoints, or docs. A rejected candidate's frames/intermediate renders are
   discarded immediately; only a *count* of rejections (by reason) is kept in
   the results file's `rejection_histogram`. Survivors beyond the shortlist are
   also discarded. Only the ≤5 shortlist entries persist any artefacts.
4. **One canonical results file per lane.** Each effect lane has exactly one
   `results/<effect>/results.json` (the canonical run record) and one
   `results/<effect>/champion.json`. A new `run` **overwrites** `results.json`
   for that effect (the previous shortlist is gone unless promoted); it does not
   create `results-2.json`, dated variants, or per-cycle directories. The file's
   embedded changelog is the version history (mirrors the global doc-versioning
   protocol and the testbed's single `sweep_summary.json`).
5. **No new docs per cycle.** The loop writes data files (`results.json`,
   `champion.json`, `contact_sheet.{html,png}`) only — never a markdown report
   per run. Findings live in the one results file.

`results/<effect>/results.json` canonical shape:

```json
{
  "effect": "bloom",
  "run": { "seed": 42, "max_iterations": 64, "strategy": "grid",
           "corpus": ["steady-groove","kick-drop-heavy","sparse-breakdown-build"],
           "rendered": 64, "wall_seconds": 38.2 },
  "champion": { "hash": "…", "params": { … }, "panel": { … } },
  "shortlist": [
    { "rank": 1, "hash": "…", "params": { … }, "panel": { … },
      "composite": 0.81, "delta_vs_champion": { … },
      "per_fixture": { "steady-groove": { … }, "kick-drop-heavy": { … } } }
  ],
  "rejection_histogram": { "nan_overflow": 0, "perf_budget": 3,
                           "motion_memory": 7, "colour_clarity": 2,
                           "below_floor": 41 },
  "changelog": [ { "date": "2026-06-03", "by": "loop.py", "note": "run 64 cands, 3 survivors, champion unchanged" } ]
}
```

## 7. Acceptance

A single `loop.py run` invocation, given an effect, a `--space`, and the fixture
corpus, MUST — **fully autonomously, within the iteration budget** — produce all
of:

1. a **ranked shortlist** (≤5, or empty with exit 2),
2. a **contact sheet** (`contact_sheet.html` + `.png`), and
3. an **updated canonical results file** (`results.json`),

with no human interaction during the run, and exit `0`. The reproducibility
self-check (§1.3) passes. No artefacts are written for rejected variants
(§6.3). Re-running with the same `--seed` reproduces the same shortlist
(determinism). The Captain's only touch is reviewing the contact sheet and, if
satisfied, running `loop.py promote`.

## 8. Loop pseudocode + CLI usage

### 8.1 Pseudocode

```python
# loop.py run  (scripts/regression-harness/loop.py)
ROOT     = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"          # tempo_replay.py idiom

def run(effect, space_path, corpus_dir, champion_path,
        max_iters=64, shortlist_k=5, strategy="grid",
        seed=42, frames=F, out_dir=None, make_sheet=True):

    assert shortlist_k <= 5                           # §6.2 hard clamp
    space    = load_space(space_path)                 # §2.1; validate fields exist
    corpus   = load_corpus(corpus_dir)                # PRD-01 fixtures
    champion = load_champion(champion_path, effect)   # §1.1; bootstrap from defaults

    # determinism self-check (§1.3): champion must re-render bit-identical
    if not bit_identical(render_replay(effect, champion.params, corpus, frames, seed),
                          render_replay(effect, champion.params, corpus, frames, seed)):
        return EXIT_DETERMINISM_FAIL                  # exit 3

    candidates = generator(space, strategy, seed, max_iters)   # §2; bounded
    if strategy == "grid" and grid_size(space) > max_iters:
        return EXIT_TOOLING_ERROR                     # exit 1; never truncate a grid

    survivors  = []
    rejections = Counter()                            # §6.3 — counts only, no files
    for cand in candidates:                           # <= max_iters, hard
        params = overlay(champion.params, cand.delta)
        panels, frames_by_fix = {}, {}
        for fix in corpus:
            fr = render_replay(effect, params, fix, frames, seed)   # PRD-01
            panels[fix.name] = score(fr, fix.drive)                 # PRD-02
            frames_by_fix[fix.name] = fr
        verdict = regress(panels, champion.panel)     # PRD-02: guards + relative
        if verdict.rejected:
            rejections[verdict.reason] += 1
            del frames_by_fix                         # §6.3 REJECT-AND-DELETE
            continue
        survivors.append(Candidate(params, panels, verdict.composite, frames_by_fix))

    survivors.sort(key=lambda c: c.composite, reverse=True)
    shortlist = survivors[:shortlist_k]               # §6.2
    for s in survivors[shortlist_k:]: s.discard()     # §6.3

    write_results_json(out_dir, effect, run_meta, champion, shortlist, rejections)  # §6.4 one file
    if make_sheet:
        render_contact_sheet(out_dir, champion, shortlist)          # §4 (strip_frame donor)

    return EXIT_OK if shortlist else EXIT_NO_SURVIVOR  # 0 / 2

def promote(effect, candidate_ref, results_dir):      # the single human-fed step
    sl = load_results(results_dir, effect).shortlist
    chosen = resolve(sl, candidate_ref)               # by rank or hash
    atomic_write(champion_path(effect),               # temp + rename
                 {"hash": chosen.hash, "params": chosen.params, "panel": chosen.panel})
    append_changelog(results_dir, effect, f"promoted #{candidate_ref} -> champion")
    return EXIT_OK
```

### 8.2 CLI usage

```bash
# Plan the grid without rendering (cheap dry-run, validates --space fields)
python3 scripts/regression-harness/loop.py list \
    --effect bloom --space scripts/regression-harness/spaces/bloom.json

# One fully-autonomous cycle: render 64 candidates over the fixture corpus,
# score, regress vs champion, rank, emit shortlist + contact sheet + results.json
python3 scripts/regression-harness/loop.py run \
    --effect bloom \
    --space scripts/regression-harness/spaces/bloom.json \
    --corpus docs/forensics/runtime-evidence \
    --max-iterations 64 --shortlist 5 --strategy grid --seed 42 \
    --out results/bloom
# exit 0 = ranked shortlist + contact_sheet.{html,png} + results.json written
# exit 2 = ran clean, no survivor cleared the floor (results.json has shortlist: [])
# exit 3 = determinism self-check failed (loop untrustworthy)
# exit 1 = tooling error (compile/corpus/space/IO)

# Captain reviews results/bloom/contact_sheet.html (the ONLY human touch), then:
python3 scripts/regression-harness/loop.py promote \
    --effect bloom --candidate 2          # promotes shortlist #2 to champion.json

# Inspect current champion + last shortlist without opening anything
python3 scripts/regression-harness/loop.py show --results results/bloom
```

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | Created — build spec 03 for VE-Auto-Loop: `loop.py` control driver (inputs, cycle, frame/score contract, CLI, exit codes), phased candidate generation (MVP-0 RenderParams sweep / Ext operator-template mutation), grid/random/optimiser strategies, the Captain contact-sheet batch gate (HTML/PNG via strip_frame donor) + `promote` verdict feedback, load-bearing churn governance (iteration cap, shortlist ≤5, reject-and-delete, one canonical results file), autonomous/human split table, acceptance, loop pseudocode + CLI usage. Donors: tempo_replay.py / vp_capture.py (this repo) + testbed experiment.py / batch_export.py / renderers.py. |
