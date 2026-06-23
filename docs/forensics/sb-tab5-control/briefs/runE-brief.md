# Run E — Tab5 hub previews, health anomaly highlight, edges/more polish

You are implementing Run E of the Tab5 redesign v2 plan
(`docs/forensics/sb-tab5-control/2026-06-11-tab5-redesign-v2-codex-plan.md`).
Runs A and B+C+D are committed. The composer layout hotfix (now-band label centre,
context-row button inset) is in the working tree — do not regress it.

Design contract: `docs/forensics/sb-tab5-control/2026-06-11-tab5-k1-control-redesign-v2.html`
(hub/health/edges/more sections).

## Goal

1. **Hub** — each destination row gains a live preview column (right side) refreshed on `showPage(PAGE_HUB)` and in `refreshAll()` when `_activePage == PAGE_HUB`.
2. **Health** — replace the monolithic `_healthDetailLabel` dump with a 3-column kv grid per mockup; per-value threshold colouring (warning only when out of range).
3. **Edges** — scene segmented band at top (same ink-on-purple active style as composer context row); dual edge **cards** with kv rows per mockup (not monolithic wrap labels).
4. **More** — 2×2 action button grid + right-side status card kv grid per mockup.

## Read budget (do NOT explore beyond this)

- `sb-tab5-wireless-controller/src/ui/LightComposerUI.h` — whole file
- `sb-tab5-wireless-controller/src/ui/LightComposerUI_pages.cpp` — whole file (page file; primary edit surface)
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp` — `grep -n "refreshAll\|showPage\|refreshHealth\|refreshDual\|refreshMore"` and read ±40 lines per match only
- `sb-tab5-wireless-controller/src/ui/DesignTokens.h` — whole file
- `tools/tab5_k1_dashboard_harness.py` lines 28–36 only (health threshold constants)
- Mockup HTML: read lines 566–870 and 1194–1368 of `docs/forensics/sb-tab5-control/2026-06-11-tab5-k1-control-redesign-v2.html`

## Hard locks

- User-facing labels stay MODE/PALETTE/BRIGHTNESS/COLOUR/SPEED; never PHOTONS/CHROMA/MOOD on glass.
- `LOCKED` text never changes.
- No new K1 controls; no protocol bump.
- `harnessWriteStatus()` field set unchanged.
- Do not touch composer now-band / context row / deck / picker (Run BCD territory).
- Do not touch header / link chip (Run A).

## Specification

### 1. Health thresholds (duplicate harness — comment points at host file)

In `LightComposerUI_pages.cpp` anonymous namespace, ensure these exist (some may already):

```cpp
// Keep in sync with tools/tab5_k1_dashboard_harness.py HEALTH_* constants
static constexpr int32_t HEALTH_MAX_K1_AGE_MS = 7500;
static constexpr float HEALTH_MIN_RSSI_DBM = -67.0f;
static constexpr int32_t HEALTH_MAX_WS_LOOP_MS = 250;
static constexpr int32_t HEALTH_MAX_LVGL_HANDLER_MS = 250;
static constexpr int32_t HEALTH_MAX_LVGL_FLUSH_MS = 50;
```

### 2. Hub live previews

Add per-row preview widgets (badge optional, big line, sub line) stored in new members e.g.
`_hubPreviewBadge[4]`, `_hubPreviewBig[4]`, `_hubPreviewSub[4]`.

Implement `refreshHubPage()`:

| Row | Badge | Big | Sub |
|-----|-------|-----|-----|
| SHOW | `CURRENT` when `_activePage == PAGE_COMPOSER` (gold/warning colour), else hidden or dim | `mode_name(selectedState().mode)` | `bright N% · BPM` (use `_tempoBpm`, `percent_from_float(photons)`) |
| HEALTH | health summary word (`LIVE`/`DEGRADED`/etc. from `computeHealthSummary`) with semantic colour | — | `%.0f dBm · age %lu ms` |
| EDGES | — | `P:%u · S:%u` (primary/secondary mode ids) | `scene ASSIST` style — uppercase scene label from `smartSceneName()` |
| MORE | — | — | `vol N · muted` or `vol N · unmuted` from `AudioFeedback` |

Call `refreshHubPage()` from `showPage()` when `page == PAGE_HUB` and from `refreshAll()` hub branch (replace the duplicate `refreshHeaderNav()`-only path).

Preview column aligns right within each hub row (~280px wide), matching mockup hierarchy.

### 3. Health page — 3-column grid

Keep: back button, `HEALTH: <summary>` banner title, `RETRY LINK` button.

Add `_healthHintLabel` under the banner title with one-line hint derived from summary
(e.g. LIVE → "Joined to K1 AP, handshake ready, state fresh.").

Replace `_healthDetailLabel` with three columns (`Connection`, `K1 proof`, `RF & runtime`), each a panel with heading + kv rows (key left, value right). Store value labels in `_healthKvValues[18]` (6 per column) or equivalent structured array.

`refreshHealthPage()` sets each value text and colour:

- **Default/neutral**: `FG_PRIMARY` or `FG_SECONDARY` for keys, `FG_PRIMARY` for in-range values.
- **ok style** (`STATUS_SUCCESS`): boolean goods — AP joined, WS connected, handshake ready, k1_seen=1, pending=0, last_ok=1, probe done, tx_dropped=0.
- **warn style** (`STATUS_WARNING`): out of threshold — k1_age > HEALTH_MAX_K1_AGE_MS, rssi < HEALTH_MIN_RSSI_DBM, ws_loop_max > HEALTH_MAX_WS_LOOP_MS, lvgl_handler_max > HEALTH_MAX_LVGL_HANDLER_MS, lvgl_flush_max > HEALTH_MAX_LVGL_FLUSH_MS, pending > 0, tx_dropped > 0.

Fields (match mockup):

- Connection: AP, WS, protocol, handshake, reconnects, ws_error
- K1 proof: k1_seen, k1_age, pending, last_ok, caps, tx_dropped
- RF & runtime: rssi, antenna, probe, ws_loop_max, lvgl_max (handler), fps

Remove `_healthDetailLabel` member if fully replaced.

### 4. Edges page

Layout per mockup:

- Back + title row unchanged.
- **Scene band** at top (below title): label `SCENE` + 4-button segmented control (reuse `_dualSceneButtons` / `dualSceneCb` / `refreshDualEdgePage` highlight logic; ink-on-purple active). Use same inner-box sizing discipline as composer context row (pad relative to content area, not double-padded).
- **Two edge cards** side by side below scene band. Each card: coloured border (cyan primary, green secondary), title `PRIMARY`/`SECONDARY`, kv grid:
  - Primary: mode, palette, bright, colour, speed, fps
  - Secondary: mode, palette, bright, enabled, speed, fps
- `Tap → focus in Show` hint at card bottom; whole card clickable → `dualFocusCb` (existing surface focus behaviour).

Replace `_dualPrimaryLabel` / `_dualSecondaryLabel` monolithic labels with `_edgeKvValues[2][6]` (or separate key/value arrays). `formatEdgeSnapshot` may be retired if unused.

`refreshDualEdgePage()` populates kv values from `_primary` / `_secondary` EdgeState (mode id + name, palette id + name via `palette_name()`, percents, fps, enabled).

### 5. More page

Layout per mockup:

- Left: `LOCAL SETTINGS` title, short description paragraph ("Tab5 comfort controls only…"), **2×2 action grid** — MUTE TOGGLE, VOL +, TEST CUE, OPEN HEALTH (existing callbacks: `settingsMuteCb`, `settingsVolCb`, `settingsTestCb`, `settingsHealthCb`).
- Right: **Status card** with heading `Status` and kv: audio, muted, volume, battery, charging, usb.

Replace `_moreDetailLabel` mono dump with `_moreStatusValues[6]`. `refreshMorePage()` fills them (ok colouring for enabled/charging/usb when true).

### 6. Static tests

Update `tests/test_sb_tab5_wireless_controller_static.py`:

- ADD required: `refreshHubPage`, `_hubPreviewBig`, `HEALTH_MAX_K1_AGE_MS`, `HEALTH_MIN_RSSI_DBM`, `HEALTH_MAX_LVGL_HANDLER_MS`, `_healthKvValues` (or your array name), `_edgeKvValues` (or card kv symbol), `Tap → focus` or `focus in Show`
- RETIRE assertNotIn: `_healthDetailLabel` if removed
- Add test that health threshold constants comment references `tab5_k1_dashboard_harness.py`

Do not weaken harness or UI_STATUS assertions.

## Deliverables

- `LightComposerUI.h`
- `LightComposerUI_pages.cpp`
- `LightComposerUI.cpp` (minimal — showPage/refreshAll hooks only)
- `tests/test_sb_tab5_wireless_controller_static.py`

## Do not

- Commit, flash, or run device commands
- Change `Tab5SerialHarness.cpp` or smoke sequence (Run F)
- Chase `pio run` failures in sandbox (expected blocked)
- Touch composer/header code paths

Final message ≤10 lines: files touched, symbols added/removed, test tokens updated, anything blocked.
