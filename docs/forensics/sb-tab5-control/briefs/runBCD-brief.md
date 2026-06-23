# Run B+C+D — Tab5 composer restructure (now-band, context row, deck, picker promotion)

You are implementing the merged composer-restructure run of the Tab5 redesign v2 plan
(`docs/forensics/sb-tab5-control/2026-06-11-tab5-redesign-v2-codex-plan.md`, Runs B, C, D —
merged because the intermediate geometries are not independently consistent).
Run A (LINK chip header) is already committed — do not touch the header, link chip, popover,
battery, or title cluster.

Design contract: `docs/forensics/sb-tab5-control/2026-06-11-tab5-k1-control-redesign-v2.html`.

## Goal

Rebuild the COMPOSER page body (everything inside `_pageComposer` content area, 1240×648):

1. **Now-playing band** (y=0, h=124, full width): current mode name loud, palette name + steppers, BROWSE button, FPS/BPM/LOCKED chips.
2. **Context row** (y=136, h=64): surface segmented control + scene segmented control.
3. **Control deck** (y=212, h=436, full width): three large slider rows (BRIGHTNESS / COLOUR / SPEED) with surface-coloured fills and per-row result-ack dots.
4. **Mode grid deleted** from the composer; the picker overlay becomes the only mode/palette browse surface, with larger cards.

## Read budget (do NOT explore beyond this; locate functions with `grep -n`, excerpt with `sed -n 'A,Bp'`)

- `sb-tab5-wireless-controller/src/ui/LightComposerUI.h` — whole file
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp` — locate and read ONLY these functions/blocks: the anonymous-namespace constants + helpers at top of file (first ~340 lines); `createStatePanel`; `createParameterPanel`; `createModePanel`; `refreshAll`; `refreshStatus`; `updateSurfaceButtons`; `updateModeButtons`; `updateParamRow`; `updateSceneButtons`; `updateStatePanel`; `adjustParam`; `setSliderParam`; `sendCurrent`; `applyK1ControlResult`; `expirePendingControls`; the static callbacks at end of file (`surfaceCb`, `sceneCb`, `modeCb`, `paramMinusCb`, `paramPlusCb`, `paramSliderCb`)
- `sb-tab5-wireless-controller/src/ui/LightComposerUI_pages.cpp` — locate and read ONLY: `createContentPages`, `createPickerGrid`, `refreshPickerGrid`, `pickerItemCb`, `pickerTabCb`, `apply_button_label_contrast`, `showOverlay`, `harnessOpenPicker`
- `sb-tab5-wireless-controller/src/ui/DesignTokens.h` — whole file
- `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp` — `grep -n "UI_PRESS\|UI_MODE\|UI_PALETTE\|UI_SCENE\|UI_SLIDER"` and read ±30 lines per match (these commands must keep working)
- `tests/test_sb_tab5_wireless_controller_static.py` — whole file (you will edit it; understand which assertions describe the composer)
- Mockup HTML: `grep -n "now-band\|nowband\|context-row\|deck\|picker" docs/forensics/sb-tab5-control/2026-06-11-tab5-k1-control-redesign-v2.html` and read ±40 lines per match for exact geometry/typography values.

## Specification

### 1. Now-playing band (replaces `createStatePanel` top strip)

New `createNowBand(lv_obj_t* parent)` building a full-width card (1240, h≈124) at y=0:

- **Mode name**: `BEBAS_BOLD_40`, `FG_PRIMARY`, left-aligned, updated from `mode_name(selectedState().mode)` (new `refreshNowBand()` called from `refreshAll()` composer branch).
- **Palette block** right of the mode name: palette name label (`RAJDHANI_BOLD_24`), flanked by `-` / `+` text buttons (≥66px tall touch targets) reusing `paramMinusCb`/`paramPlusCb` with user_data index 1 (palette). Keep palette behaviour identical to today.
- **BROWSE button**: gold accent (`BRAND_PRIMARY`) text button → opens picker: `showOverlay(OVERLAY_PICKER)` with the picker tab set to MODE for the currently selected surface (reuse the same path `harnessOpenPicker` uses).
- **Perf chips** on the far right: re-create an FPS chip (text `"%u FPS"` / `"-- FPS"`, active when `_k1StateSeen && fps>0`), move `_bpmPill` and `_lockedPill` here from the deleted mode panel (same `set_pill` truth conditions; `LOCKED` text NEVER changes). Use the existing `pill`/`set_pill` helpers. Update `refreshStatus()` to set all three.

### 2. Context row — new `createContextRow(lv_obj_t* parent)` at y≈136, h≈64

- **Surface segmented** (left): two buttons PRIMARY / SECONDARY, identical send/select behaviour (`surfaceCb`). Active style = ink-on-accent: bg cyan `0x00FFFF` (primary) or green `0x00FF99` (secondary) with BLACK label; inactive = `SURFACE_BASE` bg, accent border, `FG_PRIMARY` label. Reuse `apply_button_label_contrast` pattern.
- **Scene segmented** (right): FOUR buttons OFF / ASSIST / L1 / AUTO replacing the old cycle button + `_sceneStateLabel`. Each button calls `setSmartScene(SMART_SCENES[i], true)` — wire via a new static cb with user_data index. Active = ink-on-purple (`0xBF00FF` bg, black label); inactive as above. New `updateSceneButtons()` body highlights `_smartSceneIndex`.
- DELETE `createStatePanel`, `_statePanel`, `_sceneButton`, `_sceneButtonLabel`, `_sceneStateLabel`, and the old `sceneCb` cycle behaviour (the harness `UI_SCENE NEXT` path goes through `harnessSetScene`, which must keep working — it calls `setSmartScene` directly; verify).

### 3. Control deck — new `createControlDeck(lv_obj_t* parent)` at y≈212, h≈436, full width 1240

Three rows (BRIGHTNESS index 2, COLOUR 3, SPEED 4), each row ~128px tall:

- Label `RAJDHANI_BOLD_32` left; slider track ≥56px tall filling the middle (keep the existing `lv_bar` + `paramSliderCb` press/pressing/released wiring and `touch_bar_value` mapping, and the primary-brightness 5% floor logic); mono value (`JETBRAINS_MONO_REG_24`) right.
- **Surface-coloured fill**: indicator colour = cyan when `_selectedSurface == SURFACE_PRIMARY`, green when SECONDARY. Single helper `uint32_t deckAccent() const`. Applied in `updateParamRow()` so it flips on surface change. The old per-row PARAM_COLOURS for rows 2–4 are no longer used for the deck (keep the array if other code indexes it, but the deck must not use gold/purple/blue fills).
- **Ack dot** per row (right of the value): 14px dot object.
  - PENDING (amber `STATUS_WARNING`): a control matching this row for the current surface (`primary|secondary` + `photons|chroma|mood`) is active in `_pendingControls`.
  - APPLIED (green `STATUS_SUCCESS`): not pending, and `_lastControl` equals this row's control name with `_lastControlOk == true` and `millis() - _lastControlResultMs < 4000`.
  - FAILED (red `STATUS_ERROR`): same recency window with `_lastControlOk == false`.
  - IDLE: `FG_DIMMED`.
  Implement as `refreshDeckAcks()` called from `refreshAll()` composer branch AND from `loop()`'s 250ms status tick path (acks must decay without user input). Dots only — do NOT add glyph characters (✓/✕ are not in the converted fonts).
- DELETE `createParameterPanel` (the palette row moves to the now-band; rows 2–4 move to the deck). Keep `updateParamRow` working for indices 1–4 with the new widget homes (palette label in now-band, deck rows).

### 4. Mode grid removal + picker promotion

- DELETE `createModePanel`, `_modeButtons`, `_modeButtonLabels`, `updateModeButtons` grid styling, and `modeCb` IF its only users were the grid buttons (verify with grep; `harnessSetMode` must keep working — it does not use `modeCb`).
- `refreshAll`/`updateParamRow(0)` callers of `updateModeButtons` → replace with `refreshNowBand()`.
- **Picker**: enlarge items to ~4 columns × ~96px tall cards. Each card: mode/palette NAME (`RAJDHANI_BOLD_24`) + mono id line (`JETBRAINS_MONO_REG_24`, e.g. `#18`). Active card = ink-on-cyan (cyan bg, black labels) via `apply_button_label_contrast`; keep `mode_enabled()` gating and existing `pickerItemCb` send path. Tabs keep current behaviour.
- Geometry constants: replace `STATE_Y/STATE_H/BODY_Y/BODY_H/LEFT_X/LEFT_W/RIGHT_X/RIGHT_W` usage in the composer with new named constants (`NOW_Y/NOW_H/CTX_Y/CTX_H/DECK_Y/DECK_H`) — document each with a comment. Other pages (health/edges/hub/more) must be untouched.

### 5. Harness + host smoke

- `UI_MODE`, `UI_PALETTE`, `UI_SLIDER`, `UI_SCENE`, `UI_PRESS`, `UI_OPEN_PICKER` serial commands must all still work. If `UI_PRESS` references deleted widgets, repoint it to the nearest equivalent new widget and say so in the final message.
- `tools/tab5_k1_dashboard_harness.py`: no sequence changes required unless a command above changed semantics; if so, adjust minimally and report.

### 6. Static tests (`tests/test_sb_tab5_wireless_controller_static.py`)

Update deliberately — never delete a truth-assertion without an equivalent new-design replacement:

- RE-ADD `'"%u FPS"'` and `'"-- FPS"'` to `test_light_composer_fps_uses_k1_primary_strip_state` (FPS chip is back on glass) and remove the interim comment.
- ADD required tokens: `"createNowBand"`, `"createContextRow"`, `"createControlDeck"`, `"refreshNowBand"`, `"refreshDeckAcks"`, `"deckAccent"`.
- RETIRE (assertNotIn): `"createStatePanel"`, `"createParameterPanel"`, `"createModePanel"`, `"_modeButtons"`, `"_sceneStateLabel"`, `"LIGHT FUNCTIONS"`.
- Update any other composer-structure assertions that now fail, keeping their intent (e.g. scene/surface button assertions point at the segmented controls).
- Run `python3 -m pytest tests/test_sb_tab5_wireless_controller_static.py -q` and iterate until green. List EVERY test change in the final message.

## Guardrails

- Do NOT commit. Do NOT flash or open serial ports. Leave all edits on disk.
- A failing `pio run` in your sandbox is expected (no network) — do not chase toolchain/download errors.
- User-facing labels stay MODE/PALETTE/BRIGHTNESS/COLOUR/SPEED; `LOCKED` never renamed; no protocol words (photons/chroma/mood) on glass.
- No new K1 controls; send paths (`sendCurrent`, `setSmartScene`, control names) byte-identical.
- `harnessWriteStatus` format string byte-identical (no field changes at all this run).
- No non-ASCII glyphs in any label.
- Do not touch the header, link chip/popover, hub/health/edges/more pages, or `K1WebSocketClient`.
- If you cannot do something, report it honestly — do not fabricate. Do not wait for stdin.

## Final message (≤12 lines)

Files touched; symbols added/removed; every static-test assertion changed; status of the static pytest run; anything repointed (e.g. UI_PRESS) or not implemented and why.
