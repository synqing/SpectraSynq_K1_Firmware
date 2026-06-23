# SB-TAB5-V2-PAGE-FLOW-ESCAPE-STATES

Task ID: `SB-TAB5-V2-PAGE-FLOW-ESCAPE-STATES`

Evidence question: What revised page model should replace the four-screen proposal, and how should secondary pages, escape paths, popups/dropdowns, and error/failure states behave?

Verdict: `PARTIAL_VERIFIED`. The revised page graph and behaviour contract below are source-backed and should replace the current four-screen proposal. Final product acceptance remains `NOT_VERIFIED` until an exact `1280x720` pixel lab, on-device Tab5 proof, real touch paths, and a live serial-bridge or AP-facade round trip exist.

Scope: Read-only inspection of reset docs, current proposal, SB control maps, donor Tab5/PIPDeck flow rules, and acceptance docs. This file is the only write.

## Source Spine

- Reset plan rejects the current HTML as an implementation baseline because it has inert widgets, undersized controls, fake-live labels, an explainer architecture page, and calibration/reset too close to the operator surface: `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md:7-21`.
- Reset plan already narrows the next artefact to two operator pages plus validation overlays: `Home / Show Control` and `Diagnostics / Recovery`: `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md:141-160`.
- Pixel contract requires exact `1280 x 720`, one home per parameter, documented bounding boxes, no widget without failure state, journey mapping, and on-device validation before final proof: `docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md:50-76`.
- Current SB has USB CDC serial only, no active HTML/REST/WS backend; live-looking UI must be labelled `API-needed` or bridge-backed until implemented: `docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md:15-26`, `docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md:63-72`.
- Current proposal exposes four prototype pages, `01 Light Composer`, `02 Show Mix`, `03 Smart + Health`, `04 Architecture`: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html:1305-1312`.
- Current proposal only wires side-rail page buttons and Composer surface buttons; in-screen Back is a styled `div`, non-Composer segmented controls are inert, and action-looking cards are not buttons: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html:1001`, `:1119`, `:1177`, `:1253`, `:1377-1442`; red-team summary at `docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md:21-40`, `:91-104`.
- Donor PIPDeck navigation rules define the usable destination taxonomy: inline expansion, bottom sheet, modal, drill-down page, tab switch, and full-screen critical alert; detail-heavy content gets drill-down pages, quick actions use bottom sheets, confirmations use one modal maximum, no modal stacking, and bottom nav persists except for critical alerts: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/03_NAVIGATION_AND_WIDGET_RULES.md:3-21`.
- Donor PIPDeck acceptance requires real structural checks, bound callbacks, fixed command queue, bounded command result delay, and visible or serial result updates: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/04_PROTOTYPE_ACCEPTANCE.md:16-53`.
- Donor hard UI rules forbid widgets without data sources, actions without second-order destinations, tap behaviour without failure behaviour, tiny touch regions, hidden side effects, and fake live MQTT in the first prototype: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/01_STAGE_1_1_STATS_SPEC.md:30-37`.

## Refuted Current Page Model

The four-screen proposal should not be promoted.

| Current page | Verdict | Reason |
|---|---|---|
| `Light Composer` | Keep as visual grammar only; replace as Home structure | It has the correct centre-origin motif and selected-surface idea, but the LGP field is too small, live labels are unproven, Back is not wired, and parameter cards are display widgets rather than controls. |
| `Show Mix` | Fold into Home / Show Control | It duplicates show controls, shows inert action tiles, and has no independent operational job. |
| `Smart + Health` | Split into Home status plus Diagnostics / Recovery | Smart Scene is a show control; health, streams, calibration validity, and recovery belong in Diagnostics. Noise calibration/reset must not sit in a casual page. |
| `Architecture` | Cut from device UI | It is a design-review explainer, not an operator page. Architecture rationale belongs in docs or validation overlays, not on the Tab5 controller. |

## Proposed Page Graph

```text
ROOT
  -> Home / Show Control                         [primary, default]
      -> Mode Picker                             [bottom sheet or drill-down list]
      -> Palette Picker                          [bottom sheet or drill-down list]
      -> Channel Detail                          [secondary drill-down: Secondary Edge + EdgeMixer]
      -> Advanced Look                           [secondary drill-down: saturation/base/mirror/reverse/prism]
      -> Command Result Sheet                    [transient bottom sheet]
      -> Confirmation Modal                      [one modal max, only for guarded actions]

  -> Diagnostics / Recovery                      [primary tab]
      -> Stream Detail                           [secondary drill-down; includes Stop Streams]
      -> Device Identity Detail                  [secondary drill-down; read-only unless bridge supports reconnect]
      -> Admin Recovery                          [guarded secondary drill-down]
      -> Critical Alert                          [full-screen only for connection/safety-critical states]
```

Primary navigation has exactly two operator tabs:

1. `Home / Show Control`: the default operational surface. It owns current mode, enabled-mode picker/cycle, primary photons/chroma/mood, palette mode/index, Smart Scene, manual-owner indicator, read-only hearing/silence/beat/onset/calibration trust, and the centre-origin dual-edge preview.
2. `Diagnostics / Recovery`: the deliberate non-performance surface. It owns version/chip/reset reason, FPS/LED FPS, VP/smart/edge status, stream toggles with `Stop Streams`, connection repair, stale/failure detail, and guarded admin recovery.

Secondary pages are allowed only as drill-downs from one primary page. They must not appear in primary navigation until they have an operational job, a source-backed data/action seam, an explicit failure state, and a tested return path.

## Secondary Page Rules

Every secondary page must declare:

- `parent_page`: `Home` or `Diagnostics`.
- `entry_affordance`: the exact button/card that opens it.
- `back_target`: the exact page or sheet it returns to.
- `primary_job`: one sentence, action-oriented.
- `source_truth`: serial bridge, API-needed, simulated, runtime-only, persisted, or read-only.
- `failure_state`: disconnected, stale, timeout, rejected, queue full, unsafe, or unavailable.
- `escape`: Back, Cancel, Home, Stop Streams, Reconnect, or Acknowledge.

If a secondary page cannot fill those fields, it is not a page. It becomes read-only context, a validation overlay, or a documentation note.

Approved secondary-page roles:

| Secondary page | Parent | Allowed job | Not allowed |
|---|---|---|---|
| `Channel Detail` | Home | Secondary Edge plus EdgeMixer controls where the user can see why the second strip matters. | Hidden duplicate homes for primary controls; pretending secondary persists like primary config. |
| `Advanced Look` | Home | Low-frequency source-backed controls such as saturation, base coat, auto-colour, mirror/reverse, prism. | Audio tuning, rebooting controls, calibration, backend selection, zones/SynqMatrix. |
| `Mode Picker` | Home | Source-backed enabled-mode selection with disabled/unavailable states. | Hard-coded attractive mode list without source/version guard. |
| `Palette Picker` | Home | Palette mode/index selection with source-backed names if available. | Firmware-v3 `setPalette` semantics as if implemented in current SB. |
| `Stream Detail` | Diagnostics | Start/stop diagnostic streams and show active state. | Product-home stream controls or non-shippable probes as normal UI. |
| `Device Identity Detail` | Diagnostics | Show available identity truth: bridge source, chip ID/version when read, AP/IP/BSSID when implemented, age/stale state. | `USB ID OK` unless a serial bridge actually verified USB identity. |
| `Admin Recovery` | Diagnostics | Guarded recovery only after explicit prerequisites. | One-tap noise calibration, reset, restore defaults, or clear calibration. |

## Back / Escape Contract

1. `Home` has no Back button. Back/Escape on `Home` closes an open overlay; otherwise it does nothing visible and never blanks the app.
2. Primary tabs are persistent: `Home` and `Diagnostics` stay reachable except during a critical full-screen alert.
3. Secondary pages have a real `<button>` Back control and a persistent `Home` escape. A styled `div` is not accepted.
4. Back from a secondary page returns to its parent page with state preserved. It must not jump to an arbitrary default route unless the parent no longer exists.
5. Cancel closes pending edits without sending a command. Apply/Commit sends one command envelope and transitions to `pending`.
6. Escape closes bottom sheets and non-critical modals with no side effect. For confirmation modals, Escape means `Cancel`, not `Confirm`.
7. Critical alerts are the only full-screen takeover. They must show the reason, affected controls, and at least one recovery action: `Reconnect`, `Stop Streams`, `Disable Controls`, `Home Read-Only`, or `Acknowledge`.
8. Any page that starts a stream, diagnostic mode, or pending command must expose its stop/cancel path before the action is sent.
9. Navigation state must be testable in the harness: page id, parent id, overlay id, active command id, and stale age must be observable.

## Popup / Dropdown Policy

Popups are not a layout escape. Use the smallest destination type that preserves touch reliability and source truth.

| Destination | Use | Rules |
|---|---|---|
| Inline expansion | Small read-only context, no command side effect. | Must not resize the page enough to hide the original control. |
| Bottom sheet | Quick non-destructive choices, command result, mode/palette list if the list fits large touch rows. | One sheet at a time; Back/Escape closes; no hidden command on dismiss. |
| Drill-down page | Detail-heavy control groups or lists too large for a sheet. | Must have parent/back contract and persistent primary nav. |
| Modal | Confirmation or small error detail. | One modal maximum; no stacking; confirm button disabled until prerequisites are satisfied. |
| Full-screen critical alert | Device/safety state where normal controls must be blocked. | Blocks unsafe actions but still provides recovery/read-only escape. |
| Dropdown | Rare; low-risk enum with few options and large hit rows. | Never for core performance controls, never for >8 useful options, never to hide cramped layout. |

Control-type mapping:

- Mode and palette index: large list, stepper, or picker sheet; not tiny dropdown.
- Smart Scene: segmented control (`off`, `assist`, `l1`, `auto`).
- EdgeMixer mode: segmented/list, strength as slider or stepped values.
- Photons/chroma/mood: large sliders with explicit hit box and pending/result state.
- Calibration/reset/admin: no dropdown; guarded workflow only.

## Failure-State Matrix

| State | Trigger | UI behaviour | Escape / recovery |
|---|---|---|---|
| `API_NEEDED` | No implemented bridge/facade backs a visible control. | Badge the surface `API NEEDED` or `SERIAL BRIDGE NEEDED`; disable live-looking green state. | Home stays usable as prototype; no command send. |
| `SIMULATED` | Prototype data is local/mock. | Show `SIMULATED` at the data group and timestamp; never show as `LIVE`. | Switch to read-only or bridge-backed mode when available. |
| `DISCONNECTED` | Serial bridge/AP facade not connected. | Disable write controls; keep read-only cached state visibly stale. | `Reconnect`, `Home Read-Only`, `Diagnostics`. |
| `STALE_STATUS` | Last status exceeds freshness threshold. | Grey live badges, show age, block high-risk writes if state age makes safety ambiguous. | `Refresh`, `Reconnect`, `Diagnostics`. |
| `WRONG_DEVICE_OR_UNKNOWN_ID` | Device identity unavailable or mismatched. | Block writes; show exact missing/mismatched identity source. | Reconnect/reselect; no hidden override. |
| `COMMAND_PENDING` | Command sent, ack/result not received. | Show spinner/countdown on originating control; disable duplicate destructive sends. | `Cancel` only if transport supports cancellation; otherwise wait/timeout. |
| `COMMAND_TIMEOUT` | Ack/result misses bounded window. | Show failed state at originating control and command result sheet. | `Retry`, `Dismiss`, `Diagnostics`. |
| `COMMAND_REJECTED` | Device/bridge rejects payload, disabled mode, invalid value, or safety class. | Show exact reject reason; do not silently clamp unless UI shows resulting value. | `Choose different value`, `Dismiss`. |
| `QUEUE_FULL` | Fixed command queue cannot accept command. | Show queue full/backpressure; coalesce continuous slider updates, reject non-coalescable actions. | Wait, retry, or stop stream/noisy source. |
| `UNSAFE_CALIBRATION` | Noise cal requested without confirmed silence/readiness. | Keep confirm disabled; show silence prerequisite and current hearing/silence status. | Cancel, return Home, or wait for valid silence. |
| `ADMIN_CONFIRM_ARMED` | Guarded admin action entered. | Show one modal max with typed/explicit confirmation and timeout. | Cancel/Escape disarms; timeout disarms. |
| `PERSIST_PENDING` | Primary config delayed save queued. | Mark primary persisted state as pending/queued; do not apply same label to runtime-only secondary/Smart state. | Wait or navigate; failure appears in Diagnostics. |
| `RUNTIME_ONLY` | Secondary/Smart/EdgeMixer state has no primary-style persistence. | Label as runtime-only near the control, not in a footnote. | No save promise; if persistence is added later, require proof. |
| `STREAM_ACTIVE` | Diagnostic stream toggled on. | Persistent stream-active chip plus `Stop Streams` on Diagnostics and any relevant alert. | `Stop Streams`; leaving page must not hide active stream state. |
| `CRITICAL_ALERT` | Connection/device/safety issue blocks normal operation. | Full-screen alert; primary nav hidden only while critical state is active. | `Reconnect`, `Disable Controls`, `Home Read-Only`, or `Acknowledge` if safe. |

## Required Acceptance Additions

Before any implementation-ready verdict, the next artefact must prove:

1. Page graph invariant: every page has a parent or is one of the two primary pages.
2. Back invariant: every secondary page has a wired Back button and Home escape.
3. Overlay invariant: at most one sheet/modal/alert is active.
4. Control invariant: every action-looking element is a real button/control or visibly read-only.
5. Failure invariant: every command-capable control exposes pending, success, timeout/reject, disabled, and stale/disconnected states.
6. Source-truth invariant: no green/live state without live source, freshness age, and stale/error fallback.
7. Pixel invariant: all interactive hit boxes meet the Tab5 touch band and are emitted in the bounding-box table.

## Required Re-run Commands Used

```bash
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '1,180p' firmware-v3/docs/reference/codebase-map.md
sed -n '1,160p' firmware-v3/docs/reference/fsm-reference.md
command rg --files | command rg -i '(^|/)(AGENTS\.md|progress\.md|handoff\.md|codebase-map\.md|fsm-reference\.md|k1-ws-contract\.yaml|k1-rest-contract\.yaml)$|sb-tab5-control|pipdeck|tab5|control|acceptance|flow|reset'
rg -n "SB-TAB5|Tab5|TAB5|tab5|PIPDeck|PipDeck|PIPdeck|page flow|page model|four-screen|reset|acceptance|escape|dropdown|popup|secondary page|back path|dead" docs .claude progress.md README.md
rg -n "PIPdeck|PIPDeck|PipDeck|Tab5|tab5|page flow|acceptance" /Users/spectrasynq/.codex/memories/MEMORY.md
rg -n "screen|page|tab|nav|data-screen|view|Show|Diagnostics|Recovery|Home|Control|Architecture|Protocol|Health|Mix|Composer|onclick|addEventListener|modal|popup|popover|dropdown|select|dialog|overlay|back|escape|Escape|error|failure|timeout|offline|stale|loading|retry" docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/local/2026-06-07-pipdeck-tab5-source-pass.md | sed -n '1,240p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '980,1125p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '1125,1265p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '1265,1455p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html | sed -n '340,520p'
nl -ba docs/forensics/sb-tab5-control/agents/pipdeck-tab5-dashboard-pattern-audit.md | sed -n '1,260p'
nl -ba docs/forensics/sb-tab5-control/agents/tab5-sb-ui-adversarial-review.md | sed -n '1,280p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-control-map.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-k1-control-journey-map.md | sed -n '1,260p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/03_NAVIGATION_AND_WIDGET_RULES.md | sed -n '1,160p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/04_PROTOTYPE_ACCEPTANCE.md | sed -n '1,140p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/01_STAGE_1_1_STATS_SPEC.md | sed -n '1,120p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/docs/product/VISUAL_CONSTITUTION.md | sed -n '1,220p'
nl -ba docs/forensics/sb-tab5-control/agents/tab5-controller-map.md | sed -n '1,240p'
nl -ba docs/forensics/sb-tab5-control/agents/zone-composer-design-history.md | sed -n '1,240p'
nl -ba docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md | sed -n '1,180p'
nl -ba docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md | sed -n '1,260p'
```

## Method Risk

This pass did not build, flash, open a browser, run Playwright, touch a Tab5 panel, or exercise a live serial/AP bridge. It answers the page-flow evidence question from source and donor docs only. The revised page graph is suitable as the next design contract, not as final UI acceptance.
