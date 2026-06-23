# Run A — Tab5 header consolidation (LINK chip + popover)

You are implementing Run A of the Tab5 redesign v2 plan
(`docs/forensics/sb-tab5-control/2026-06-11-tab5-redesign-v2-codex-plan.md`).
Design contract: `docs/forensics/sb-tab5-control/2026-06-11-tab5-k1-control-redesign-v2.html` (header + link-popover sections only).

## Goal

Collapse the four header status pills (`_rssiPill`, `_apPill`, `_wsPill`, `_fpsPill`) into ONE
`LINK` chip on the right side of the header. Tapping the chip opens a diagnostic popover overlay.
Battery panel and title cluster stay. `_bpmPill` / `_lockedPill` are NOT header pills — do not touch them.

## Read budget (do NOT explore beyond this; use `sed -n 'A,Bp'` for excerpts)

- `sb-tab5-wireless-controller/src/ui/LightComposerUI.h` — whole file
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp` — lines 200–340 (helpers: `pill`, `set_pill`, `label_on`, `text_button`, `make_card`, `create()`); 420–600 (`harnessWriteStatus`, `createHeader`); 1040–1130 (`refreshAll`, `refreshStatus`, `updateBatteryStatus`). If a helper is not in 200–340, locate it with a single targeted `grep -n`, then read ±15 lines.
- `sb-tab5-wireless-controller/src/ui/LightComposerUI_pages.cpp` — lines 1–60 (file helpers); 229–260 (`computeHealthSummary`); locate `showOverlay`, `refreshHeaderNav`, `harnessCloseOverlay` with `grep -n` and read those functions ±10 lines only.
- `sb-tab5-wireless-controller/src/ui/DesignTokens.h` — whole file
- `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp` — `grep -n "UI_RETRY_LINK\|UI_TITLE_TAP\|UI_CLOSE_OVERLAY"` then read ±40 lines around matches (command parse table + processors + help string)
- `tests/test_sb_tab5_wireless_controller_static.py` — lines 280–470
- `tools/tab5_k1_dashboard_harness.py` — lines 1–80 (`SMOKE_COMMANDS`)
- Mockup HTML: `grep -n "link-chip\|link-popover\|linkPopover" docs/forensics/sb-tab5-control/2026-06-11-tab5-k1-control-redesign-v2.html` and read ±30 lines per match.

## Specification

### 1. Header (LightComposerUI.cpp `createHeader`, ~530–586)

- DELETE creation of `_rssiPill` (553–559), `_apPill`, `_wsPill`, `_fpsPill` (580–585) and their member declarations in the .h.
- ADD `_linkChip`: clickable pill-style container, right-aligned (`LV_ALIGN_RIGHT_MID, 0, 0`), size ~190×44, containing:
  - `_linkChipDot`: small 12×12 rounded square / circle (radius 6), colour set by health state
  - `_linkChipLabel`: `RAJDHANI_BOLD_24`
- Event: `LV_EVENT_CLICKED` → new static cb `linkChipCb` → `showOverlay(OVERLAY_LINK)` (toggle: if already `OVERLAY_LINK`, close).
- Battery panel and `_titleCluster` unchanged. Keep the existing `> SHOW` crumb format in `_titleSub` — do NOT introduce non-ASCII glyphs (chevrons/arrows); the converted fonts may not cover them.

### 2. Link chip state (`refreshLinkChip()`, called from `refreshStatus()`)

Reuse `computeHealthSummary()`. Mapping:

| summary | dot colour | label text |
|---|---|---|
| LIVE | `DesignTokens::STATUS_SUCCESS` | `LINK` |
| DEGRADED | `STATUS_WARNING` | `DEGRADED` |
| PROBING | `STATUS_WARNING` | `PROBING` |
| FAULT | `STATUS_ERROR` | `FAULT` |
| OFFLINE | `STATUS_ERROR` | `OFFLINE` |

Label colour: `FG_SECONDARY` when LIVE (quiet), state colour otherwise (status by exception).
In `refreshStatus()` (1068–1099): remove the four `set_pill` calls for the deleted pills (keep `_bpmPill`, `_lockedPill` lines untouched), remove the now-unused `rssi`/`fps` snprintf buffers if nothing else uses them, and call `refreshLinkChip()`.

### 3. Link popover (new overlay)

- Extend the overlay enum with `OVERLAY_LINK` (after `OVERLAY_SETTINGS`).
- Build in `createOverlays()`: card ~420×360 anchored top-right under the header, `SURFACE_RAISED` bg, `BORDER_SUBTLE` 1px, radius 14. Hidden by default; `showOverlay()` switching logic extended for it (it must also be dismissed by `showPage()` like the others — verify `showPage` calls `showOverlay(OVERLAY_NONE)` already; do not duplicate).
- Content: title `CONNECTION` (`RAJDHANI_BOLD_32`, `BRAND_PRIMARY`), then 6 kv rows (label `RAJDHANI_MED_18` `FG_MUTED`, value `JETBRAINS MONO 24` `FG_PRIMARY`), refreshed by new `refreshLinkPopover()` (call from `refreshAll()` when `_activeOverlay == OVERLAY_LINK`):
  - `K1 AP` → `JOINED` / `--` (same condition as old `_apPill`: `WiFi.status()==WL_CONNECTED && WiFi.SSID()=="LightwaveOS-AP"`)
  - `WEBSOCKET` → `_wsClient->getStatusString()` or `NONE`
  - `PROTOCOL` → `v%u` from negotiated version, `--` if 0
  - `K1 AGE` → `%lu ms` (same computation as harnessWriteStatus)
  - `PENDING` → `pendingControlCount()`
  - `RSSI` → `%.1f dBm` when AP joined else `--.-`
- Bottom: `OPEN HEALTH` text button (`RAJDHANI_BOLD_24`, gold `BRAND_PRIMARY` accent) → `showPage(PAGE_HEALTH)`.

### 4. Status surface (`harnessWriteStatus`, 425–528)

- `overlay=` value set gains `LINK` (when `_activeOverlay == OVERLAY_LINK`). NO other field changes — the format string and every existing field stay byte-identical.

### 5. Serial harness (`Tab5SerialHarness.cpp`)

- New command `UI_LINK_TAP` → new `LightComposerUI::harnessLinkTap()` (same toggle behaviour as `linkChipCb`). Add to parse table, processor, and the HELP command list alongside `UI_TITLE_TAP`.
- `UI_CLOSE_OVERLAY` must already close it via `showOverlay(OVERLAY_NONE)` — verify, don't rewrite.

### 6. Host harness (`tools/tab5_k1_dashboard_harness.py`)

- Insert into `SMOKE_COMMANDS` after the existing `UI_TITLE_TAP`-block: `"UI_LINK_TAP"`, `"UI_STATUS"`, `"UI_CLOSE_OVERLAY"` (keep the rest of the sequence intact).

### 7. Static tests (`tests/test_sb_tab5_wireless_controller_static.py`) — edit deliberately, exactly this

- `test_light_composer_header_uses_battery_bar_not_back_button` (~416): REMOVE required tokens `"_rssiPill"`, `"RSSI: --.-"`, `"RSSI: %.1f"`. ADD required tokens `"_linkChip"`, `"refreshLinkChip"`, `"OVERLAY_LINK"`, `"OPEN HEALTH"`, `"%.1f dBm"`. ADD a retired list asserting `assertNotIn` for `"_rssiPill"`, `"_apPill"`, `"_wsPill"`, `"_fpsPill"` in the combined source.
- Harness-command test (~300–330): add `"UI_LINK_TAP"` and `"harnessLinkTap"` to the required list.
- Host-harness smoke test: add `"UI_LINK_TAP"` to its required strings.
- Touch NOTHING else in the test file.

## Guardrails

- Do NOT commit. Do NOT flash or open serial ports. Leave all edits on disk.
- A failing `pio run` in your sandbox is expected (no network) — do not chase toolchain/download errors. You MAY run `pytest tests/test_sb_tab5_wireless_controller_static.py -q` if deps exist; if it errors on imports, report and move on.
- Do not rename `LOCKED`, do not touch `_bpmPill`/`_lockedPill`, do not add K1 controls, do not change any `k1.ws` protocol code.
- If you cannot do something, say so honestly in the final message — do not fabricate.
- Do not wait for stdin.

## Final message (≤10 lines)

Files touched; symbols added; symbols removed; test tokens added/removed; any spec point you could not implement and why.
