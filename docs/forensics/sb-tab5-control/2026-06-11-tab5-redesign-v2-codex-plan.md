# Tab5 Redesign v2 → Firmware: Codex Offload Plan

Date: 2026-06-11
Status: Captain-approved design direction (redesign v2 mockup). This plan decomposes the firmware translation into bounded `codex exec` runs per `.claude/skills/codex-offload/SKILL.md`.

## Design contract (source of truth)

| Artefact | Role |
|---|---|
| `docs/forensics/sb-tab5-control/2026-06-11-tab5-k1-control-redesign-v2.html` | Visual contract — geometry, hierarchy, colour semantics, copy |
| `docs/forensics/sb-tab5-control/2026-06-09-tab5-phase-0-page-flow-spec.md` | Page topology + field-source matrix (unchanged) |
| `evidence/ssa/tab5-execution-plan-20260609/product-ux-validator.md` | Product locks (see Deviations) |

### Approved deviations from prior locks (Captain, 2026-06-11)

1. **Header pills collapse**: `RSSI`, `K1 AP`, `WS`, `FPS` pills are replaced by one `LINK` chip + tap popover. Battery pill stays. This supersedes validator lock #5's "current header structure" clause; the underlying fields all remain in `UI_STATUS` and on the Health page (no truth is lost, only relocated).
2. **Mode grid leaves the composer**: 16-chip grid → picker overlay becomes the only mode browse surface. Composer shows current mode name + BROWSE.
3. Colour semantics: deck slider fills follow selected surface (cyan/green); per-row decorative neon (gold/purple/blue) removed.

### Hard locks that still bind every run

- User-facing labels stay `MODE / PALETTE / BRIGHTNESS / COLOUR / SPEED`; never `PHOTONS/CHROMA/MOOD` on glass.
- `LOCKED` text never becomes another word.
- No new K1 controls; no calibration/reset/OTA surfaces; K1 stays AP-only.
- Applied state requires matching `k1.control.result` or fresh `k1.state` (result-backed truth).
- v2 wire only — no `k1.ws` protocol bump.
- Fonts: use existing assets only (`BEBAS_BOLD_40` is the largest Bebas). 56px mockup mode-name renders as `BEBAS_BOLD_40` on device; optional new font asset is Phase G (orchestrator-side, needs `lv_font_conv` + network — NOT a codex task).

## Division of labour (fixed)

| Codex (sandboxed, his tokens) | Orchestrator/Claude (real env) |
|---|---|
| Read bounded source, write the C++/test/harness edits as in-repo files | `pio run -e tab5` build verification (codex build RED ≠ broken — no network in sandbox) |
| Update static-test tokens in the same run as the code they gate | `pytest tests/` real run, commits, device flash (MAC-verified), smoke harness |

Every codex brief inherits: `< /dev/null`, no commit, no flash, no exploration outside the read budget, write deliverables in-repo, final message ≤ 10 lines.

## Run decomposition

Each run leaves the tree green (code + matching test-token updates together), because the commit gate requires pytest + build per commit.

### Run A — Header consolidation (LINK chip + popover)

**Goal:** Replace `_rssiPill`, K1 AP pill, WS pill, FPS pill with one `LINK` chip (state colour = health summary: LIVE/DEGRADED/OFFLINE/PROBING/FAULT, reusing `computeHealthSummary()`); tap opens a popover card (AP, WS, protocol, k1_age, pending, rssi + OPEN HEALTH button). Battery pill unchanged. Title cluster gains the ▾ chevron + crumb (`SHOW`/`CHOOSE`/`HEALTH`/`EDGES`/`MORE`) replacing `> SHOW` style subtitles.

- **Read budget:** `src/ui/LightComposerUI.h` (whole), `src/ui/LightComposerUI.cpp` lines 420–620 + 830–1100, `src/ui/LightComposerUI_pages.cpp` lines 640–700 (refreshHeaderNav), `src/ui/DesignTokens.h`, mockup HTML header/link-popover sections only.
- **Deliverables:** edits to `LightComposerUI.{h,cpp}`, `LightComposerUI_pages.cpp`; updated tokens in `tests/test_sb_tab5_wireless_controller_static.py` (the header test currently requires `_rssiPill`, `RSSI: --.-` etc. — relocate those assertions to popover/health symbols, keep `rssi_dbm=%.1f` in `UI_STATUS` untouched).
- **Must not change:** `harnessWriteStatus()` field set; battery logic; `LOCKED`.
- **Acceptance:** popover state struct + `refreshLinkChip()` exist; no `_rssiPill` symbol; UI_STATUS output identical.

### Run B — Now-playing band + context row

**Goal:** Composer top restructure. `state-band` (PRIMARY/SECONDARY/SCENE buttons) becomes: (1) now-band y=0 h=124 — mode name (`BEBAS_BOLD_40`), palette name + − /+ steppers, perf chips FPS/BPM/LOCKED (relocated from mode panel); (2) context row y=136 h=64 — surfaces segmented (ink-on-cyan / ink-on-green active) + scene segmented OFF/ASSIST/L1/AUTO (ink-on-purple active). Existing callbacks (`surfaceCb`, `sceneCb`, `paramMinusCb/paramPlusCb` for palette) rewire — no new K1 controls.

- **Read budget:** `LightComposerUI.cpp` lines 560–760 (state panel + parameter panel + mode panel creation), 820–1010 (refresh paths), `LightComposerUI.h` member block, mockup now-band/context-row sections.
- **Deliverables:** code edits + static-test token updates (`now-band` symbols, scene segmented; remove `_sceneStateLabel` pill assertions if retired).
- **Acceptance:** scene is a 4-button segmented (sends same `scene.smart` values), BPM/LOCKED/FPS chips live in now-band, geometry constants documented at top of file.

### Run C — Control deck (3 sliders, surface-coloured, result acks)

**Goal:** Parameter panel becomes full-width deck y=212 h=436: three rows (BRIGHTNESS/COLOUR/SPEED), 56px tracks, label 27px-equivalent (RAJDHANI_BOLD_32), mono value right, ack glyph per row — `✓` when last matching `k1.control.result` ok (reuse `_pendingControls` + `applyK1ControlResult()`), pulsing `…` while pending, `✕` on failure. Fill colour = selected surface accent (cyan/green) — single `deckAccent()` helper.

- **Read budget:** `LightComposerUI.cpp` lines 628–714 (createParameterPanel), 743–810 (adjust/setSlider), 937–1010 (sendCurrent), 1303–1365 (applyK1ControlResult), mockup deck section.
- **Deliverables:** code edits; static-test updates; palette row REMOVED from deck (palette lives in now-band per Run B).
- **Acceptance:** slider hit areas ≥56px; ack state machine has explicit pending→applied/failed transitions with the existing 4000ms timeout; no protocol words on glass.

### Run D — Mode grid removal + picker promotion

**Goal:** Delete the 16-chip grid from the composer (the right panel disappears entirely; deck takes full 1240 width — already done in Run C). Picker overlay becomes the browse surface: 4-col grid of 96px cards (name + mono id), MODE/PALETTE tabs (active = ink-on-cyan; inactive = cyan outline), wired from BROWSE button in now-band. `UI_OPEN_PICKER` unchanged.

- **Read budget:** `LightComposerUI_pages.cpp` picker sections (createOverlays, refreshPickerGrid, pickerItemCb), `LightComposerUI.cpp` mode tables lines 40–210, mockup picker section.
- **Deliverables:** code edits; static tests drop mode-panel tokens (`createModePanel` etc. as `assertNotIn`), add picker-card tokens.
- **Acceptance:** mode selection only via picker; selection still gated by `mode_enabled()`; applied state result-backed.

### Run E — Hub previews, health anomaly highlight, edges/more polish

**Goal:** (1) Hub rows show live preview column (mode+brightness / rssi+age / P:S modes / vol+mute) refreshed on `showPage(PAGE_HUB)`. (2) Health page: keep 3-column layout, add per-field threshold colouring — only out-of-threshold values get warning style (thresholds mirror `tools/tab5_k1_dashboard_harness.py` constants; duplicate them as named constants with a comment pointing at the harness). (3) Edges: scene segmented reuses Run B widget style; kv-grid layout per mockup. (4) More: action grid 2×2 + status card.

- **Read budget:** `LightComposerUI_pages.cpp` (whole file — it is the page file), `tools/tab5_k1_dashboard_harness.py` lines 28–40, mockup hub/health/edges/more sections.
- **Deliverables:** code edits + static-test token updates.
- **Acceptance:** hub previews use existing state only (no new K1 reads); health colours match harness thresholds.

### Run F — Harness + smoke + gate hardening

**Goal:** Serial harness parity with the new UI: `UI_STATUS` gains `link=LIVE|DEGRADED|OFFLINE|PROBING|FAULT` and `ack_pending=<n>`; smoke sequence exercises BROWSE (`UI_OPEN_PICKER`, `UI_CLOSE_OVERLAY`), hub previews (`UI_PAGE HUB` → status), deck acks (slider → expect `ack` transition). Static tests assert retirement of all removed symbols (`createModePanel`, `_rssiPill`, old per-row colour constants) and presence of new ones.

- **Read budget:** `src/harness/Tab5SerialHarness.cpp` (whole), `tools/tab5_k1_dashboard_harness.py` (whole), `tests/test_sb_tab5_wireless_controller_static.py` Tab5 sections, `tests/test_tab5_dashboard_harness.py`.
- **Deliverables:** harness firmware + host harness + tests.
- **Acceptance:** `pytest tests/test_tab5_dashboard_harness.py tests/test_sb_tab5_wireless_controller_static.py` green in real env.

### Phase G (optional, orchestrator-only — NOT codex)

Generate `bebas_neue_bold_56px.c` via `lv_font_conv` (needs network/node), register in `bebas_neue_fonts.h`, bump now-band mode name. Defer until after device eyes-on confirms the 40px version reads well at arm's length.

## Codex invocation template (per run)

```bash
codex exec -s workspace-write --skip-git-repo-check \
  -C "/Users/spectrasynq/SensoryBridge-main 9" \
  -o /tmp/codex_tab5_runA_last.txt \
  "$(cat docs/forensics/sb-tab5-control/briefs/runA-brief.md)" \
  < /dev/null > /tmp/codex_tab5_runA_run.log 2>&1
```

Each brief file contains: goal, exact read budget (files + line ranges, 'do not explore'), deliverable file list, the hard locks above, 'do not commit / do not flash / a failing pio run in your sandbox is expected — do not chase it', and 'final message ≤10 lines: files touched, symbols added/removed, test tokens updated, anything you could not do'.

## Orchestrator gate after every run (Claude, real env)

1. Read only `/tmp/codex_tab5_run<X>_last.txt`; `grep -E "context_length_exceeded|ERROR"` the run log (bounded).
2. `pio run -e tab5` + `pytest tests/ -q` — real env, with network.
3. Review the diff (especially test-token edits — codex must not weaken gates to pass them).
4. Commit (`feat(tab5): …`) on `wip/audio-saliency-recovery`.
5. Flash cadence: after Run C (first visual milestone) and after Run F (full slice) — `pio run -e tab5 --target upload` to `usbmodem12401`, then `python tools/tab5_k1_dashboard_harness.py --smoke --require-health --expect-protocol 2`.
6. Device eyes-on against the mockup per screen — the final gate; Codex output is never proof of visual correctness.

## Sequencing & risk

- Order A→B→C→D→E→F; B and C touch adjacent geometry — do not parallelise them. A and (E-hub-copy) are independent of B/C but serialising is cheaper than merge pain in one 1400-line file.
- Biggest risk: static-test token churn. Mitigation: every run's brief enumerates the exact assertions to move/retire so codex edits tests deliberately, not to "make green".
- Second risk: `LightComposerUI.cpp` size (~1.5k lines) blowing the codex context. Mitigation: line-ranged read budgets above; brief instructs `sed -n 'A,Bp'` excerpting, never whole-file reads of the .cpp.
