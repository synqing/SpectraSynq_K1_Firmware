# Tab5 button ON/OFF + zero-stagger sheet redraw — remediation plan

> **For agentic workers:** Execute only after optical gate rules below.  
> Do **not** flash devices without Captain go. Do **not** edit look/chrome until optical PASS (or Captain waiver).  
> British English. Evidence: `_scratch/tab5_button_ux_audit_20260810/`.

**Date:** 2026-08-10  
**Goal:** Make every Operator glass control honest about enablement at a glance, and eliminate staggered section paint on soft-key → sheet open so motion is smooth and crisp on silicon (PARTIAL path).  
**Non-goal this plan:** New effects, Mirror, STANDBY_DIMMING, C6 flash, chroma/sat resurrection without Captain order.

## Authority / gates

| Gate | Rule |
|------|------|
| Host bootstrap | `bash scripts/agent/session-bootstrap.sh` exit 0 |
| Optical | `/spectrasynq-ui-router` → `/spectrasynq-ui-precode-optical-gate` — **BLOCKED** for look/type/geometry/chrome/colour-as-hierarchy until `OPTICAL_GATE_RECEIPT.md` + SHA-pinned `MEASURED.json` PASS or Captain waiver |
| Implementation after PASS | `/k1-tab5-lvgl-dashboard` |
| Wireless/ACK honesty | `/k1-tab5-wireless-control` for SNAPSHOT/DELTA lamp truth — may proceed as **non-look** wiring if no chrome change |
| Redraw / buffer mode | May change `lvgl_bridge` / `tab5_config` flags with **measured** A/B; treat as render-path, still prove on device |
| Flash | Explicit Captain approval + MAC verify (`30:ED:A0:E0:C1:A0` for Tab5) |
| Host/static | pytest for any shared map/manifest tests; `pio run -e native_sdl` for layout dumps; device PARTIAL eyes-on for redraw claims |

## Current truth (audit)

- Surface: `tab5_firmware` `deck_ui` / env `tab5_p4`.
- Wiring: **52** controls scored → 21 WIRED_OK / 29 PARTIAL / 2 DEAD — **not 100%**.
- ON/OFF: sheet tiles hue-only; no selected state; soft-key lamps SNAPSHOT-blind.
- Redraw root: PARTIAL 64-line FB + full-screen sheet/scrim anim (`deck_ui.cpp:692–721`, `lvgl_bridge.cpp:78–81`).
- VIVID: dead on glass (false affordance).

## Phase 0 — Freeze + optical pack (BLOCK look edits)

**Owner:** UI orchestrator  
**Done when:** Optical tier declared; evidence pack skeleton exists; Captain knows look is blocked.

- [ ] Declare gate tier **T1** (ON/OFF tiles + lamps + sheet material) or **T0** if type/geometry also moves.
- [ ] Capture stills (native_sdl **and** note sim DIRECT ≠ device): soft-key lamps, EDGE ON/OFF row, sheet open mid-frame.
- [ ] Write crops list into optical pack under `_scratch/tab5_button_ux_audit_20260810/optical/` (or successor lane folder).
- [ ] No `deck_theme.h` / soft-key geometry / type token edits until PASS.

**Verification:** `OPTICAL_GATE_RECEIPT.md` exists with verdict PASS or BLOCKED (BLOCKED is success for Phase 0 if honest).

## Phase 1 — Host/static honesty (non-look wiring)

**Owner:** firmware + protocol  
**May run while optical BLOCKED** if zero chrome/colour/geometry changes.

### Task 1.1 — Soft-key paths in SNAPSHOT

- [ ] Extend `k1_deck_state_tx` snapshot inventory to include at least: `edge.enabled`, `director.enabled`, `scene.smart`, `vp.profile` (and any other lamp sources).
- [ ] Confirm Tab5 `apply_value` still drives `deck_ui_set_key_lamp` (`deck_state_rx.cpp:150–158`).
- [ ] Host test: snapshot encode includes those map indices; reconnect simulation leaves lamps correct after HELLO+SNAPSHOT (unit/replay as available).

**Files:** `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_tx.cpp`, Tab5 `deck_state_rx.cpp`, tests under `tests/` for deck identity/map if present.

**Done when:** Reconnect path can light EDGE/DIRECTOR/SMART/RENDER lamps without requiring a fresh apply DELTA.

### Task 1.2 — Sheet bool selected state (logic-only if styles deferred)

- [ ] Track selected bool per path in sheet ctx; on `bool_btn_cb` set local pending selection **before** TX.
- [ ] On remote DELTA for that path, reconcile selection (confirmed / reject → snap back).
- [ ] If visual fill/outline requires theme tokens → **stop** and wait for optical PASS; otherwise use existing pressed/idle tokens only if already measured.

**Files:** `tab5_firmware/src/deck_ui_sheets.cpp`, optionally `deck_state_rx.cpp` hooks.

### Task 1.3 — VIVID false affordance

- [ ] Captain decision: remove soft-key, grey/disable with non-open, or keep with explicit dead chrome.
- [ ] Implement chosen option; update `ui/spec/deck_softkey_manifest.json` note if status changes.
- [ ] Static test: no chroma/sat TX from glass (`glass_path_forbidden` remains).

### Task 1.4 — Manifest ack note hygiene

- [ ] Update `deck_softkey_manifest.json` backend note if SNAPSHOT now covers lamp paths (do not invent `CONFIRMED_REMOTE` without true apply ACK UX).

**Verification Phase 1:** pytest green for touched protocol/static tests; no flash required.

## Phase 2 — Optical PASS then ON/OFF chrome

**Blocked until Phase 0 PASS.**

### Task 2.1 — Optical PASS for ON/OFF + lamp crops

- [ ] Complete MEASURED.json optical heights / contrast notes for selected vs unselected tiles and lamp ON vs OFF.
- [ ] Receipt PASS signed.

### Task 2.2 — ON/OFF chrome per Emil Before/After

Implement from `APPLE_EMIL_EVAL.md` table:

- Selected = filled / high-contrast; unselected = outline or empty.
- Soft-key lamp OFF = unlit/outline; ON = solid (glow optional, short, not continuous pulse).
- Pending vs confirmed visual if wiring Phase 1 landed.

**Files:** `deck_ui_sheets.cpp`, `deck_ui.cpp` (`set_lamp_visual`), `deck_theme.h` (tokens only after PASS).

**Verification:** native_sdl stills + vision-Read; optical re-Observe; **no** Captain claim from sim alone for redraw (Phase 3).

## Phase 3 — Zero-stagger screen/sheet swap (CRITICAL)

**Primary RCA:** PARTIAL 64-line banded flush of full-screen dirty (`REDRAW_ROOT_CAUSE.md` H1–H3).

### Task 3.1 — Reveal contract (must-fix)

- [ ] Keep sheets built HIDDEN (already true).
- [ ] Before first visible frame: `lv_obj_update_layout(sheet)`; set sheet `bg_opa` to **COVER** for open; avoid whole-object `style_opa` anim on scrim/sheet under PARTIAL.
- [ ] Suppress `refresh_all_controls` while sheet open/animating.
- [ ] Prefer single clear-HIDDEN reveal; if slide remains, only after opaque cover + render path can sustain full dirty without multi-frame bands.

**Files:** `tab5_firmware/src/deck_ui.cpp` (`sheet_animate_open` / close), tick path `:1492–1522`.

### Task 3.2 — Render path choice (measure, then pick one)

Option A — **Enable full-frame DIRECT dual FB** when PSRAM/panel allow (`TAB5_LVGL_FULL_DIRECT_FB`), retire PARTIAL for MAIN, measure FPS/mem.  
Option B — Keep PARTIAL but **increase buffer lines** to cover dirty height for sheet opens, or freeze flush until one composite ready.  
Option C — Snap open (0 ms motion) until A/B proven — Captain may prefer zero jank over decorative slide.

- [ ] Document chosen option + silicon FPS during open in evidence pack.
- [ ] Align `native_sdl` render mode with device for this class of bugs **or** label sim NON-AUTHORITY for redraw.

**Files:** `tab5_firmware/src/lvgl_bridge.cpp`, `include/tab5_config.h`, sim `lv_conf.h` if aligning.

### Task 3.3 — Device proof (Captain go)

- [ ] Flash Tab5 only with approval; MAC `30:ED:A0:E0:C1:A0`.
- [ ] Eyes-on: soft-key open EDGE/DIRECTOR — no horizontal band paint; ON/OFF selected state obvious; lamps match K1 after SNAPSHOT.
- [ ] Optional: timed open with motion=0 vs COVER opa A/B to separate H1 vs H2/H3.

**Done when:** Captain accepts glass as smooth crisp; inventory DEAD/PARTIAL counts drop for in-scope keys; VERDICT updated.

## Phase 4 — Closeout

- [ ] Update `docs/hardware/device-build-registry.md` Tab5 port/MAC after any flash.
- [ ] Append evidence to `_scratch/tab5_button_ux_audit_20260810/` (or dated successor).
- [ ] Fill `scripts/agent/post-session-report.md` skills/specialists used.
- [ ] Do **not** claim 100% wired until inventory recount shows zero PARTIAL/DEAD for in-scope Operator controls (or Captain explicitly scopes VIVID out).

## Out of scope / forbid

- Reintroduce Mirror ON/OFF, STANDBY_DIMMING, chroma/sat on glass without Captain order.
- High-frequency lamp pulse / decorative animation spam.
- Treating native_sdl DIRECT screenshots as zero-stagger proof.
- Look edits without optical PASS.
- `start_noise_cal` / noise cal on device without Captain silence confirmation.

## Success criteria

1. Soft-key lamps reflect remote truth after SNAPSHOT (no dark-after-reconnect lie).
2. Sheet ON/OFF selected state legible without hue alone.
3. Soft-key → sheet open shows **no** staggered section paint on Tab5 PARTIAL/DIRECT as configured.
4. VIVID does not present as a working function key unless resurrected with real controls.
5. Optical gate PASS on file before chrome merge; host tests green for wiring/map changes.
