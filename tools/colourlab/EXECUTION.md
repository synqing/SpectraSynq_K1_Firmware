---
abstract: "Live task ledger for the Colour Lab palette-bench lane (branch lane/colourlab-bench). One row per task with dependency, done-when condition, gate and evidence. Read this to know exactly what is done, what is in flight and what is blocked. Plan authority: ~/.claude/plans/create-a-detailed-phased-deep-penguin.md."
branch: lane/colourlab-bench
status: active
---

# Colour Lab — execution ledger

**Lane:** Colour Lab palette bench · **Branch:** `lane/colourlab-bench`
**Plan authority:** `~/.claude/plans/create-a-detailed-phased-deep-penguin.md`

The original incremental-remodelling recommendation is superseded by Captain's 2026-08-28
greenfield ruling. Preserve `colourlab-core.js`, the serial protocol, queue/safety behaviour,
fixtures and verification knowledge; do not preserve the old DOM or its interaction hierarchy.
Build `workbench.html` beside the current `index.html` oracle, prove parity, then cut over
deliberately. Device readback (`rtrace`) is capability-gated during the named two-device
programme; no diagnostic flash is authorised.

## 2026-08-28 controlling greenfield ruling

The operator jobs are **Source**, **Tune**, **Preview**, **Analyse**, **Test** and **Persist**.
Source and Tune are parallel authoring roles, not numbered steps in an atomic sequence. The
second authoring loop is **Reference → Author Palette → Compare Maths → Policy Check**.

Production invariants:

- no full hue-wheel, rainbow, spectrum sweep or wheel-spanning palette may be rendered, sent,
  saved or exported;
- the old page remains the functional oracle only until the replacement reaches parity;
- the mockup's illustrative `pow()` tune, curve and Secondary multiplier are prohibited;
- the real 17-region Card is 13 greys plus isolated Red, Green, Blue and K1 Gold;
- rich local authoring compiles visibly to at most eight uniformly sampled RGB Paint stops;
- RGB, shortest-arc HSV and OKLCH comparisons use real tested maths;
- one pure product-policy validator governs preview eligibility, device Test, Save and export;
- Device Safety FAIL makes Preview unavailable and preserves recovery only;
- Product Colour Policy FAIL keeps bounded local analysis visible, stamps it NON-PRODUCT, and
  blocks device Test, Save and product export;
- Source and Transform truth are independent per channel; drawing and inspection consume the
  same resolved `stageFrame()` object;
- Mode/Target/values are local-first and apply as one Source transaction; Gain/Gamma are one
  Tune transaction; one field's confirmation must never erase another unsent field.

Optical authority passed independently before production writes:
`_scratch/colourlab_workbench_r0_20260828/OPTICAL_GATE_RECEIPT.md` (T0 PASS, 43 cross-state
computed-text signatures, annotated-board SHA
`27955b9fa9efedabccbd58d76a90469ea3a7cb6b30e58df63064ed8086fdc3b6`).

## Greenfield cutover ledger

| id | task | status | done-when |
|---|---|---|---|
| GF-0 | T0 optical gate | DONE | Independent reviewer accepts the exact SHA-pinned 43-role pack |
| GF-1 | Freeze old `index.html` as oracle | DONE | Pre-cutover source SHA `e81fbd9a985e236fc33bc764ac953fffb990e226b209f2fdea1eaa78c532f052`; retained by git history after cutover |
| GF-2 | Permanent no-rainbow harness | DONE | Six selectable sources score 0/1/2/3/3/1 hue sectors; wheel-spanning stops fail the shared validator; output-boundary static gate passes |
| GF-3 | Tested authoring/policy module | DONE | Real RGB/shortest-arc HSV/OKLCH, uniform ≤8 compilation, approximation metrics and separate gates pass |
| GF-4 | Greenfield `workbench.html` | DONE | Production surface loads `colourlab-core.js`, `colourlab-authoring.js` and `colourlab-workbench.js`; no illustrative maths remains |
| GF-5 | Serial/local-first parity | DONE | Browser gate proves source `target→stops→mode`, tune `gain→gamma`, persistence, recovery and asymmetric per-channel Preview truth |
| GF-6 | Browser/a11y/responsive proof | DONE | `verify_workbench.py`: 0 failures, 13 stills; 1600/740/390/800, keyboard focus, diffusion, policy, safety, inheritance, slot-unknown, device-loss, failed-Resync and recovery attacks checked; Colour Lab 89 passed |
| GF-7 | Deliberate cutover | DONE | `COLOURLAB_WORKBENCH_R1_UI_CUTOVER=ACCEPT`; old oracle SHA pinned above; accepted Workbench is byte-identical at `index.html` and `workbench.html`; legacy UI is no longer shipped |
| GF-8 | Preview R1.1 production cutover | DONE | Core effective-look resolution, output/basis comparison and exact-frame inspection are live in the byte-identical production entries; Preview is read-only, the curve is under Tune, and post-build optical predicates pass |
| GF-9 | Remove false Source/Tune sequencing | DONE | `01` / `02` markers and `.step` styling removed from both byte-identical entries; static regression and refreshed 13-still browser gate pass |

Everything below this ruling is retained as historical implementation evidence. Any old TODO that
conflicts with the greenfield ruling (especially the planned `spectrum` stimulus) is cancelled.

## How to use this file

A row moves to `DONE` **only** when its gate has actually been run and the evidence column is
filled in. `WIP` means started. `BLOCKED` means it needs something named in the evidence column.
Never mark a row `DONE` on a self-assessment — the gate command must have been executed.

Status vocabulary: `TODO` · `WIP` · `BLOCKED` · `DONE`

Gates:
- `pytest` = `python3 -m pytest tests/ -k colourlab -q` (baseline: 34 passed)
- `browser` = `python3 tools/colourlab/verify_browser.py` (must print `CONSOLE=0 errors, 0 warnings`)
- `—` = no automated gate; done-when is checked by inspection

## Baseline — captured CL-0.2, 2026-08-27

Recorded before any change, so regression is detectable rather than assumed.

```text
branch                lane/colourlab-bench (off feat/k1-usb-audio-input @ acf1a0e1)
colourlab host gate   34 passed, 1601 deselected
screenshots           18 stills — NOT byte-deterministic, see Finding 5
verify_browser        SCRIPT_EXIT=0 · CONSOLE=0 errors, 0 warnings
  TAB_FOCUS           btnStop
  STOP_VISIBLE        True          STOP_TEXT   Stop Output
  IDENTITY            Set Identity
  BOTH_MAIN           True          BOTH_BENCH  False
  TUNE_BENCH_HIDDEN   True          N_BENCH     n=150
MEASURED.json         verdict WAIVED
  still_sha256        a2f4da99122d7d57…
  index.html          c042a1b12e69db74…
  colourlab-core.js   ea8c6f60e53379ef…
```

Note recorded during baseline: an orphaned `python -m http.server 8765` from the previous
session was holding the harness port and had to be cleared before `verify_browser.py` could
bind. If the browser gate fails to start, check port 8765 first.

## Ledger

### Phase 0 — Lane setup and baseline

| id | task | files | dep | done-when | gate | status | evidence |
|---|---|---|---|---|---|---|---|
| CL-0.1 | Branch `lane/colourlab-bench` | — | — | `git branch --show-current` returns the lane branch | — | DONE | branch created off `acf1a0e1` |
| CL-0.2 | Capture baseline numbers | this file | CL-0.1 | Baseline block written from real runs | pytest | DONE | see Baseline above |
| CL-0.3 | Create this ledger, all tasks seeded | this file | CL-0.1 | Every plan task id has a row | — | DONE | this file |
| CL-0.4 | Register the lane | `docs/spec-index.md`, `.claude/handoff.md` | CL-0.3 | Frontmatter points at this lane and branch | — | DONE | `active_lane: COLOUR_LAB_PALETTE_BENCH_20260827`; prior lane preserved as `previous_lane` |

### Phase 1 — Wire the draft loop

| id | task | files | dep | done-when | gate | status | evidence |
|---|---|---|---|---|---|---|---|
| CL-1.1 | Emit `DRAFT_TUNE` from gain/gamma inputs (reuse `tuneDraft()`) | `index.html` | CL-0.3 | Moving a gain control populates `state.draft.tune` and repaints | pytest | DONE | Paired control: pre-change `CURVE_CHANGED=False`, post-change `True` for both gain and gamma, `TX_EMITTED=0`. pytest 34 green |
| CL-1.2 | Emit `DRAFT_PAINT` from rgb/sv/stops inputs (reuse `paintDraft()`) | `index.html` | CL-1.1 | `state.draft.paint` populated on input | pytest | DONE | Dispatch added. See note below — paint already rendered live because `renderPreview` reads `paintDraft()` straight from the DOM; state now mirrors it |
| CL-1.7 | **Local draft simulation view** | `index.html` | CL-1.1 | Moving gain/gamma visibly changes the strip under an honest simulation label | browser | DONE | `#simDraft` opt-in, offered only while framing is pre-LUT. Label: "Simulating your local draft tune — not device state, not a hardware claim." Strip changed, `TX=0`, core untouched |
| CL-1.3 | Draft discard on resync / disconnect / device-confirm | `index.html` | CL-1.2 | Drafts empty after each of the three events | pytest | DONE | Centralised in `apply()`; `DISCONNECTED` already cleared via `emptyKnowledge()`. pytest 34 green, browser gate clean |
| CL-1.8 | **Harden the browser gate** — `allow_reuse_address` + `server_close()`; it leaked a listener and could not be re-run | `verify_browser.py` | — | Gate runs twice back to back, no leaked listener | browser | DONE | Two consecutive runs `SCRIPT_EXIT=0`, `CONSOLE=0 errors, 0 warnings`, no listener left on 8765 |
| CL-1.10 | **Rescope the firmware-clean assertion** to the staged set — unrelated dirty firmware was failing this lane | `tests/test_colourlab_static.py` | — | Red when firmware is staged, green when merely dirty-unstaged | pytest | DONE | Fault battery both directions; firmware restored clean |
| CL-1.9 | **Close the pre-commit gate hole** — `tools/colourlab/*` fell into the no-op `docs` tier and committed with no test at all | `scripts/hooks/pre-commit` | — | `classify_tier` returns `pyharness` for a Colour Lab path, `docs` for a doc, `firmware` for firmware | pytest | DONE | Classifier exercised in isolation with positive and negative controls — see Finding 6 |
| CL-1.4 | Per-control dirty indication, not colour-only | `index.html` | CL-1.3 | Every drafted control shows a non-colour-only dirty mark | browser | DONE | Dashed edge (shape, not colour) + `title` + `#draftChip` text list. `DRAFT_MARKED=True`, `DRAFT_CHIP=local draft, not sent: gainR` |
| CL-1.5 | Draft repaints and emits zero serial writes — **browser-level, so it lives in the harness**, not the node/core test file | `verify_browser.py` | CL-1.2 | Gate prints `DRAFT_REPAINTS=True` and `DRAFT_TX_COUNT=0` | browser | DONE | Both printed by the standing gate on every run |
| CL-1.6 | Draft never promotes without a reply | — | CL-1.5 | Covered | pytest | DONE | **Already covered** by existing `test_timeout_never_promotes_draft` (test_colourlab_state.py:142). Not duplicated |

**Phase gate.** Move Gain R, watch the picture change, confirm the session console shows no TX line.
Met for the transfer curve at CL-1.1. **Not yet met for the Stage strip** — see CL-1.7.

### Findings from CL-1.1 testing

Two things surfaced by testing rather than reading, both of which change the work:

1. **Paint and tune were broken differently.** `renderPreview` sources paint directly from the DOM
   via `paintDraft()`, but takes tune from `state.confirmed.tune` merged with `state.draft.tune`.
   So paint drafts always rendered live while tune drafts did nothing at all — the tune path was
   the real break. Paint state is now mirrored into `state.draft.paint` so dirty-marking and
   discard can see it; making state authoritative for the render happens at CL-3.2, where the
   Stage needs a genuine three-way reference/draft/confirmed comparison.

2. **The Stage strip is deliberately pre-LUT until slot-15 is known.**
   `CL.previewFraming()` returns `applyLut:false` unless `slot15Content.status ===
   "known-this-session"`, so the strip draws the pre-LUT stimulus and **tune changes cannot move
   it**. This is correct, honest behaviour — the tool refuses to show a LUT effect it cannot
   claim — but it means that on a fresh connection you cannot see what your tuning does, which is
   the opposite of a bench. CL-1.7 closes this with a clearly-labelled simulation of the
   operator's own draft. The vocabulary already exists in the core as `simulate_session`.

3. **`paintMode` / `paintTarget` are not local drafts.** They already send to the device through
   their own `onchange` handlers. A draft dispatch was briefly added to them and reverted; do not
   re-add one.

4. **The browser gate leaked its own server and could not be re-run.** `verify_browser.py` called
   `httpd.shutdown()` without `server_close()`, leaving a listener bound to 8765, and used
   `TCPServer` without `allow_reuse_address`. The very first baseline attempt failed on a
   78-minute-old orphan from the previous session, and the second attempt failed on the leftover
   from my own first run. Fixed at CL-1.8 and proved by two consecutive clean runs. If the gate
   ever refuses to start, check port 8765 before anything else.

5. **The screenshots are not byte-deterministic — the pinned hash cannot detect a real change.**
   Two consecutive runs with *identical code* produce different files:
   `sha 3bf108760873` vs `cef105f1ff7a`, differing in the same small region (46,761)–(255,888),
   765 pixels out of 1.7M (0.04%), sub-perceptual font anti-alias jitter in the tune-input area.
   Verified by before/after crop — the two are indistinguishable to the eye.

   **Consequence:** `MEASURED.json` pins `still_sha256`, and that pin will churn on every
   regeneration whether or not anything changed. It can never be used as evidence that the look is
   unchanged, and it will always look stale. It is a receipt measuring its own annotation rather
   than the property. CL-4.8 still refreshes it because it is the recorded pin, but **judging
   "did the look change" must use a thresholded perceptual diff, never byte equality** — a
   sensible gate is any difference exceeding roughly 0.5% of pixels, or any difference outside the
   known jitter magnitude. Do not chase a churning `still_sha256`.

6. **The commit gate did not cover this lane at all.** `classify_tier()` in
   `scripts/hooks/pre-commit` matched no pattern for `tools/colourlab/*`, so `tier` stayed at its
   default `"docs"` and a commit touching only the Colour Lab page ran **no tests and no build** —
   while `test_colourlab_static.py` asserts by reading `index.html` directly and the parity, state
   and protocol suites execute `colourlab-core.js` through node. Almost all of Phase 3 is
   `index.html`, so the lane would have committed unguarded.

   Closed at CL-1.9 by adding a `tools/colourlab/*` case to the `pyharness` tier. There was exact
   precedent: `tab5_firmware/*` was added earlier for the identical hole, with the same reasoning
   in its comment. Proved with positive and negative controls rather than assumed —
   `tools/colourlab/index.html` → `pyharness`, `README.md` → `docs`, firmware path → `firmware`.

7. **A new core export is not reachable by the tests on its own.** `tests/colourlab_node.py`
   spawns node and calls **`core.dispatch(req)`** as the sole entry point. Adding an exported
   function without a matching dispatch op leaves it untestable from Python, which would have
   silently broken the Phase 2 chain. The existing `curve` op already returns knots and validity,
   so the analytics extend it rather than adding new ops — see CL-2.9.

8. **The static gate fails on unrelated uncommitted firmware.**
   `test_colourlab_static.py` asserts `git diff --name-only HEAD -- SPECTRASYNQ_K1_FIRMWARE
   platformio.ini` is empty. Any uncommitted firmware edit anywhere in the tree turns the Colour
   Lab gate red for reasons that have nothing to do with Colour Lab. If the gate goes red
   unexpectedly, check for a dirty firmware tree before debugging this lane.

### Phase 2 — Curve analytics in the core

The static gate forbids this maths in the page. Each link of export → fixture → parity test is a
separate row on purpose; this chain is the most likely place to under-scope.

| id | task | files | dep | done-when | gate | status | evidence |
|---|---|---|---|---|---|---|---|
| CL-2.1 | Export audit — **largely a no-op, confirmed**: `curveU16`, `buildRgb1d`, `rgb1dValid`, `lutLerp1d`, `sqTruncToU16`, `satU16`, `renderChannel`, `renderBoth`, `pixel` are **all already exported** (`satU16` at colourlab-core.js:1281 — an earlier note calling it private was wrong) | `colourlab-core.js` | CL-0.3 | No new exports required for the Curve panel | pytest | DONE | Verified against the export object; nothing to add |
| CL-2.9 | **Extend the `curve` dispatch op** to carry the new analytics. `tests/colourlab_node.py` reaches the core **only** through `core.dispatch(req)` — a new exported function with no dispatch op is unreachable from the parity tests | `colourlab-core.js` | CL-2.4 | `dispatch({op:"curve",…})` returns knots plus deviation and analysis | pytest | TODO | Gap found by the explore pass; see Finding 7 |
| CL-2.2 | `curveKnots(tune)` built on `buildRgb1d` | `colourlab-core.js` | CL-2.1 | Knots identical to `buildRgb1d` output | pytest | TODO | |
| CL-2.3 | `curveDeviation(tune)` — peak LUT-vs-ideal gap and its location | `colourlab-core.js` | CL-2.2 | γ 4.00 → 7748; γ 1.00 → 0 | pytest | TODO | |
| CL-2.4 | `curveAnalysis(tune)` — first non-zero, crushed-to-black, worst dark step, clip onset, monotonicity | `colourlab-core.js` | CL-2.2 | γ 0.20 → 24 crushed; γ 4.00 → worst step ≈ 63.8 | pytest | TODO | |
| CL-2.5 | Python authority for expected vectors (numpy/scipy) | `tests/generate_colourlab_fixtures.py` | CL-2.4 | Generator emits the vector set deterministically | — | TODO | |
| CL-2.6 | Emit the fixture | `tests/fixtures/colourlab_curve_vectors.json` | CL-2.5 | Regenerates byte-identically | — | TODO | |
| CL-2.7 | Parity test executing the shipped core via node | `tests/test_colourlab_preview_parity.py` | CL-2.6 | Green, using existing `colourlab_node.py` invocation | pytest | TODO | |
| CL-2.8 | Confirm no banned token in page; core still environment-free | — | CL-2.7 | `test_colourlab_static.py` green | pytest | TODO | |

### Phase 3 — Stage and Curve as one composition

Target weights: Stage ~42% · Curve ~23% · Source ~15% · workflow ~10% · device bar ~7% · prose drawer.

| id | task | files | dep | done-when | gate | status | evidence |
|---|---|---|---|---|---|---|---|
| CL-3.0 | Gold usage rule — identity/state/labels only; neutral well around colour under test | `index.html` | CL-1.4 | No gold-family colour inside the Stage well | — | TODO | |
| CL-3.1 | Layout skeleton at target weights | `index.html` | CL-3.0 | Measured share within ±3% per band | — | TODO | |
| CL-3.2a | **Stage truth authority correction** — one pure per-channel frame resolves stimulus, tune, source, transform, selection, label and pixels; drawing and inspection share it | `colourlab-core.js`, `index.html`, tests, browser gate | CL-1.7 | Asymmetric channels remain independent; simulation label and hover values match the painted frame | pytest + browser | DONE | 4 state cases + static wiring gate; Colour Lab 39 passed; browser twice: `SIM_INSPECTOR_CANVAS_PARITY=True`, `LOCAL_STIMULUS_DRAFT_LABEL=True`, `ASYMMETRIC_STAGE_LABELS=True`, `ASYMMETRIC_STAGE_PIXELS=True`, zero console errors/warnings. Stills: `look-stage-local-stimulus-draft.png`, `look-stage-primary-known.png`, `look-stage-secondary-known.png` |
| CL-3.2 | Stage — reference / draft / device-confirmed, both channels, real LED counts | `index.html` | CL-3.1, CL-1.2 | Three states render; bench shows its own count | pytest | TODO | |
| CL-3.3 | Stimulus switcher — solid, neutral ramp, spectrum, stops, card | `index.html` | CL-3.2 | Each renders; only device-backed ones emit commands | pytest | TODO | |
| CL-3.4 | Curve panel — transfer + unity + knots + ideal-vs-actual shaded + analysis | `index.html` | CL-3.1, CL-2.4 | All four elements render; no maths in the page | pytest | TODO | |
| CL-3.5 | Protocol/model prose → disclosure; state chips on canvas | `index.html` | CL-3.4 | Both prose blocks behind disclosure | — | TODO | |
| CL-3.6 | Preserve harness contract — `?demo=`, `?paint=`, required ids | `index.html` | CL-3.5 | `verify_browser.py` prints all probe lines | browser | TODO | |
| CL-3.7 | Preserve `disconnect()` shape for the static regex | `index.html` | CL-3.5 | Static disconnect assertion green | pytest | TODO | |
| CL-3.8 | Fix corrupted subtitle glyphs | `index.html` | CL-3.1 | Subtitle renders as intended in a fresh still | browser | TODO | |

### Stage truth takeover finding — 2026-08-27

The previous Stage revision used Primary framing to choose both channel buffers and its one global
label. It also recomputed the inspector's pre/post choice without the local-simulation state. A
green browser run did not catch either defect because its semantic probe lines were informational.

`stageFrame()` is now the sole per-channel authority for the Stage stimulus, tune, source,
transform, pre/post selection, label and pixel buffer. Both canvas painting and hover inspection
consume the same cached frame. Source and transform remain separate facts, so a local stimulus can
truthfully coexist with a locally simulated draft tune. Device-confirmed wording is bounded to the
reported tune plus browser parity model; the page explicitly says the LUT nodes were not read back.
The browser gate now fails non-zero on draft-send, simulation-inspector or asymmetric-label errors.

### Phase 4 — Accessibility and browser verification

| id | task | files | dep | done-when | gate | status | evidence |
|---|---|---|---|---|---|---|---|
| CL-4.1 | Keyboard path and visible focus on every new control | `index.html` | CL-3.8 | Shared inspector and controls are keyboard reachable | browser | DONE | 13-state Workbench run |
| CL-4.2 | Canvas textual equivalents for Preview and Tune curve | `index.html` | CL-3.4 | Each canvas has an equivalent text summary | — | DONE | Persistent dual-channel inspector and curve details text |
| CL-4.3 | `prefers-reduced-motion` respected | `index.html` | CL-3.8 | No animation under the media query | — | DONE | Static Workbench contract |
| CL-4.4 | WCAG AA contrast; no colour-only status | `index.html` | CL-3.8 | Each new pairing measured and recorded | — | DONE | T0 production receipt |
| CL-4.5 | 740px viewport and 200% zoom usable | `index.html` | CL-4.1 | Both stills legible, no horizontal body scroll | browser | DONE | 740=740; 800=800 |
| CL-4.6 | Zero console errors and warnings | — | CL-4.5 | Browser gate has zero failures | browser | DONE | `FAILURES=0` |
| CL-4.7 | Regenerate every still | `screenshots/` | CL-4.6 | All stills show the new body | browser | DONE | `workbench-r1.1/`, 13 stills |
| CL-4.8 | Refresh pinned hashes and craft claim | `MEASURED.json`, `OPTICAL_GATE_RECEIPT.md` | CL-4.7 | Hashes match shipped files; claim matches the screen | — | DONE | Production HTML `ce023f21…`; 90 tests |

### Phase 5 — Targeted device verification

No flashing. Consult `docs/hardware/device-build-registry.md` first; identity is chip id, not port.
The exact browser slice may be committed and pushed to this lane before Phase 5. That branch
freeze is not a lane close and does not authorise a merge to `main`.

| id | task | files | dep | done-when | gate | status | evidence |
|---|---|---|---|---|---|---|---|
| CL-5.1 | Confirm both device identities against the registry | — | CL-4.8 | Chip id, env and build stamp recorded for both | — | TODO | |
| CL-5.2 | Targeted case list on 9087A500 and B489A500 | — | CL-5.1 | Every case passes or is recorded as a limitation | — | TODO | |
| CL-5.3 | Record results | `VERIFICATION.md` | CL-5.2 | Section present; carve-outs explicit | — | TODO | |

### Phase 6 — Close

| id | task | files | dep | done-when | gate | status | evidence |
|---|---|---|---|---|---|---|---|
| CL-6.1 | Update the contract reference for renamed surfaces | `README.md` | CL-5.3 | No stale panel or control names | — | TODO | |
| CL-6.2 | Close stamp | `progress.md` | CL-6.1 | Stamp block present | — | TODO | |
| CL-6.3 | Flip lane status | `docs/spec-index.md`, `.claude/handoff.md` | CL-6.2 | No stale active-lane pointer | — | TODO | |
| CL-6.4 | Commit final evidence through the pre-commit gate and push | — | CL-6.3 | Gate passes on a real run | pytest | TODO | |
| CL-6.5 | Merge gate | — | CL-6.4 | `COLOUR_LAB_WEB_UI_HARDWARE_PASS` exists for both named units before merge | — | TODO | **HOLD until Phase 5 passes** |

## Close stamp — fill at CL-6.2

```text
CL_DRAFT_LOOP        =
CL_CORE_CURVE_API    =
CL_STAGE_CURVE_LOOK  =
CL_BROWSER_VERIFY    =
CL_DEVICE_VERIFY     =
CL_WIRE_TRUTH        = NOT_CLAIMED
```

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-27 | agent:codex | Corrected per-channel Stage truth and made asymmetric/inspector browser probes fail closed. |
| 2026-08-27 | agent:claude-code | Created — ledger seeded from the approved plan; Phase 0 baseline captured. |
