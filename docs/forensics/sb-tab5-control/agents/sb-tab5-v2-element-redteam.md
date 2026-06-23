# SB-TAB5-V2-ELEMENT-REDTEAM

Task ID: `SB-TAB5-V2-ELEMENT-REDTEAM`  
Evidence question: Attack the proposed drawing-board direction for every element: what is likely too small, too fake, misplaced, duplicated, visually weak, or missing failure handling?  
Default verdict: `NOT_VERIFIED`  
Classification: load-bearing  
Scope: read-only adversarial review of current docs, prototypes, screenshots, and evidence. This file is the only write.

## Verdict

`NOT_VERIFIED`.

The proposed direction is better than the rejected HTML pass because it names the right gates, but the next drawing board can still fail by carrying forward the same defects in subtler form: green live-looking status without live SB transport, 36-44px controls promoted from donor precedent into primary touch actions, fake sliders for enum/discrete controls, an LGP preview too small or too decorative to judge the product, safety/admin controls left too visible, and no hard failure-state matrix for touch actions.

## Evidence Boundary

- Current SB source-backed control plane is USB CDC serial, not REST/WS/HTML (`sb-touch-control-map.md:17`, `sb-touch-control-map.md:31`, `sb-control-map.md:33`).
- Current active SB has no AP/WiFi/WebSocket/REST task, route table, JSON parser, or command-response abstraction (`sb-control-map.md:49-51`).
- Existing screenshots are `1205x678` crops or `2110x984` full-page captures, not exact `1280x720` Tab5 evidence (`pixel-match-validation-pipeline.md:95-99`; `sips` command below).
- Physical target reality: `44px` is only `3.80mm`; primary finger actions should be at least `96px`, with `72px` the floor for new low-risk targets (`tab5-physical-pixel-reality.md:51`, `:71-73`).
- This pass did not run a browser, build LVGL, flash a Tab5, open serial, or touch K1 hardware. It is an adversarial source/evidence review only.

## Findings By Screen, Chrome, And Control

| ID | Severity | Screen / element | Attack | Evidence | Remediation |
|---|---|---|---|---|---|
| C-1 | Critical | Global status chrome: `WS LIVE`, `Connected`, `AUDIO SEMANTIC LIVE`, `WS LINK LIVE`, `USB ID OK` | Fake-live is still the most likely fatal defect. The drawing board can look operational while current SB is serial-only and the AP facade does not exist. `USB ID OK` is especially false for an AP controller unless a serial bridge verifies it. | Reset plan already calls fake-live out (`2026-06-07-tab5-ui-reset-plan.md:16`, `:113-144`). Prototype shows `WS LIVE` and `AUDIO SEMANTIC LIVE` (`sb-tab5-zone-composer-proposal.html:1003-1006`, `:1109-1113`), `WS LINK LIVE` and `USB ID OK` (`:1179-1196`), and the MVP shows `Connected` plus `status.subscribe broadcast` (`sb-tab5-touch-mvp.html:407-409`, `:477-480`). | Replace every green/live pill with one of `SERIAL BRIDGE ONLY`, `API NEEDED`, `SIMULATED`, `STALE`, or a real source plus age. Identity must show actual source: serial port + chip ID for bridge, or AP SSID/BSSID + firmware/chip readback for wireless. |
| C-2 | Critical | Touch sizing across headers, tabs, side rails, segmented controls | The next board is likely to inherit donor 36-44px controls and call them touch controls. On a 5-inch panel those are status-chip sizes, not reliable primary touch targets. | Existing CSS uses 44px back/status cards and 36px surface buttons (`sb-tab5-zone-composer-proposal.html:190-228`, `:245-263`). MVP rail buttons are 40px and segment buttons 36px (`sb-tab5-touch-mvp.html:210-214`, `:312-314`). Physical model rejects 44px as primary and sets 96px preferred / 72px floor (`tab5-physical-pixel-reality.md:51`, `:71-73`). | New board must draw effective hit boxes, not just visible pixels. Primary show actions: `>=96px` high. Normal action tabs: `>=72px` high. Anything below that is read-only or must have an explicit extended hit box and low error cost. |
| C-3 | Critical | Safety/admin controls: Noise Cal, Save Now, Reset, Blackout | The UI still puts dangerous or state-altering concepts close to ordinary operator surfaces. A card that says `ARM` is not a tested calibration safety gate. | Noise calibration is guarded and must not be one-tap (`2026-06-07-tab5-ui-reset-plan.md:55`; `sb-touch-control-map.md:47`). Health screen shows `NOISE CAL ARM`, `SAVE NOW OK`, `RESET LOCKED` as health cards (`sb-tab5-zone-composer-proposal.html:1223-1240`). Donor confirmation overlay is documentation-only, not implemented (`pipdeck-tab5-dashboard-pattern-audit.md:131-137`, `:208`). | Remove calibration/reset/save-now from the Home / Show Control board. Diagnostics / Recovery may show read-only state. Admin actions require explicit admin mode, silence readiness, typed confirmation text, timeout, refusal state under non-silent audio, and command result proof. |
| C-4 | Critical | Action-looking cards and presets | The current prototype uses `<div>` and `<article>` surfaces that look tappable but have no control path. A redrawn board can repeat that by styling cards as actions before target registry and failure states exist. | Show Mix action row is inert `div.action-tile` (`sb-tab5-zone-composer-proposal.html:1160-1164`). Health actions are `article.health-card` (`:1223-1240`). Presets are `div.preset` (`:1145-1150`). JS only wires screen nav and composer `data-surface` buttons (`:1377-1443`). Operating contract requires every widget to have a failure state (`2026-06-07-tab5-pixel-match-operating-contract.md:70`). | Every action-looking element must be in the control registry with bounds, data source, action, safety class, disabled state, pending, ack, timeout, failure, and stale behaviour. Otherwise render it as read-only telemetry. |
| H-1 | High | Light Composer hero strip / LGP preview | The product object is still visually weak. A 64px LGP field is too small to judge a 2x160 centre-origin light guide and too easy to read as decorative animation. | Current composer `.lgp-field` is 64px high inside a 130px strip (`sb-tab5-zone-composer-proposal.html:285-316`). Reset plan says increase the LGP/dual-edge preview to a first-order object (`2026-06-07-tab5-ui-reset-plan.md:151`). Zone Composer donor says the LED strip is the hero and centre marker is explicit (`zone-composer-design-history.md:21-28`). | Home board needs a large centre-origin light-field schematic, not a skinny metre. Allocate a materially larger first-order region, show both physical channels, 79/80 origin, stale/schematic/live mode, and avoid implying final-byte render truth unless backed by readback. |
| H-2 | High | Centre-origin mapping labels | The visual grammar risks becoming a fake zone backend: `PRIMARY EDGE`, `SECONDARY EDGE`, and `SMART STATE` are laid over one linear field, while SB source truth is dual-channel primary/secondary plus Smart/EdgeMixer runtime state, not zones. | Prototype labels three "surfaces" over the strip (`sb-tab5-zone-composer-proposal.html:1016-1020`). Zone donor is 2/3-zone centre-origin and must not be copied as an SB backend (`zone-composer-dimension-archaeology.md:96`, `:118-126`; `tab5-sb-ui-adversarial-review.md:57-66`). | Use `Primary Edge`, `Secondary Edge`, and `Smart/EdgeMixer` as distinct control/status surfaces. The light field should show dual-edge injection and centre-origin behaviour, not zone count, zone layout, or Smart as a physical strip segment. |
| H-3 | High | Parameter cards: Mode, Palette, Photons, Chroma, Mood | The cards duplicate readouts and fake controls. Mode and palette are discrete selectors but are drawn with 8px bars; photons/chroma/mood need real sliders or steppers with handles and hit boxes. | Param grid shows mode/palette/photons/chroma/mood with `span.bar` metres (`sb-tab5-zone-composer-proposal.html:1041-1071`), and bars are only 8px high (`:475-480`). MVP also draws `Mode`, `Palette mode`, and `Smart Scene` as sliders (`sb-tab5-touch-mvp.html:441-445`). Control precision must match useful value count (`2026-06-07-tab5-pixel-match-operating-contract.md:65-67`). | Use next/previous or picker for mode, segmented/toggle for palette mode, bounded picker for palette index/name, and large sliders/steppers only for continuous values. Do not use 8px bars as controls. |
| H-4 | High | Smart Scene and EdgeMixer controls | Smart Scene and EdgeMixer are duplicated in the MVP and ambiguously located across "safe actions", right rail, overview, and health. This creates multiple homes for the same state. | MVP draws Smart Scene as both a slider-like row and segmented buttons (`sb-tab5-touch-mvp.html:442-456`), and Edge strength as both a slider-like row and a metric under EdgeMixer (`:445`, `:459-467`). Operating contract requires one home per parameter (`2026-06-07-tab5-pixel-match-operating-contract.md:59`). | Give Smart Scene one canonical segmented control (`off`, `assist`, `l1`, `auto`) and one read-only status area. Give EdgeMixer one canonical enable/mode/strength module. Do not repeat the same control in Home and Diagnostics unless one is read-only. |
| H-5 | High | Mode list and preset strip | Hard-coded attractive modes/presets can become stale, unsafe, or unsupported. The board is likely to smuggle old visual favourites into production without source version guarding. | MVP hard-codes mode buttons (`sb-tab5-touch-mvp.html:413-420`). Show Mix hard-codes A1-A4 presets (`sb-tab5-zone-composer-proposal.html:1145-1150`). Source map says mode names/IDs should be source-backed and disabled modes are skipped (`sb-touch-control-map.md:32`); reset plan cuts preset-bank machinery (`2026-06-07-tab5-ui-reset-plan.md:91-95`). | Mode list must come from `get_num_modes` / `get_mode_name` / source snapshot with commit hash and disabled-state handling. Remove presets from MVP unless an SB preset contract exists; otherwise label as future/API-needed. |
| H-6 | High | Persistence labels: `SAVE DELAYED`, `SAVE NOW OK`, secondary runtime | Persistence semantics are muddy and can mislead Captain about what survives power cycle. | Primary has delayed persistence, secondary is runtime/global (`sb-touch-control-map.md:38`, `sb-control-map.md:27`, `:54`). Prototype shows `SAVE DELAYED` and `SAVE NOW OK` (`sb-tab5-zone-composer-proposal.html:1111-1113`, `:1233-1235`). | Split persistence by owner in the UI: `primary queued save`, `secondary runtime only`, `Smart runtime only`, `EdgeMixer runtime only`. Do not show `Save Now` until a command exists and failure/ack states are implemented. |
| H-7 | High | Transport/architecture direction | The drawing board may still bias implementation toward "native SB WS first" even though the reset plan says a serial bridge may be the fastest safe proof. This can turn UI discovery into network substrate work. | MVP recommends "Small AP-only WS facade inside SB" (`sb-tab5-touch-mvp.html:486-490`). Current SB has no network backend (`sb-control-map.md:33`, `:49-51`). Reset plan says fastest safe path is likely serial bridge proof first, then decide on native AP facade (`2026-06-07-tab5-ui-reset-plan.md:164-169`). | Treat `serial bridge first` as the default discovery path unless Captain explicitly re-scopes to firmware networking. If native AP facade is selected, make it a separate firmware lane with heap/timing/backpressure gates, not part of the visual board. |
| H-8 | High | Failure handling and command lifecycle | No current board shows the real failure matrix for touch actions: disconnected, stale, queue full, coalesced, pending, timeout, rejected, wrong target, disabled, or calibration refused. | Pixel pipeline requires touch targets, semantic harness commands, disabled-negative tests, and destructive confirmation (`pixel-match-validation-pipeline.md:140-163`, `:260-280`). Operating contract requires failure state per widget (`2026-06-07-tab5-pixel-match-operating-contract.md:70`). | Every control registry row must include `source`, `action`, `ack source`, `pending`, `success`, `timeout`, `failure`, `disabled`, `stale`, `queue full`, `rate limited`, and `wrong-device` behaviour before aesthetic polish. |
| M-1 | Medium | Header/back/nav chrome | Back controls are visually primary but only 44px and implemented as non-semantic `div` on the current HTML. Side rail screen nav exists outside the Tab5 panel, so the on-device back/page model is not proven. | `.back` is `100x44` and HTML uses `<div class="back">` (`sb-tab5-zone-composer-proposal.html:190-198`, `:1000-1002`, `:1117-1119`). Screen nav buttons are in the external aside (`:1305-1311`). | Decide the actual on-device navigation chrome. If back exists, make it a semantic button with `>=72px` effective height or demote it. If bottom tabs exist, implement actual page switching and bounds proof. |
| M-2 | Medium | Protocol / Architecture screen | This is a design-review explainer, not an operator page. Keeping it as a Tab5 screen wastes a scarce surface and encourages non-operator language on glass. | Reset plan already flags the architecture screen as not an operator page (`2026-06-07-tab5-ui-reset-plan.md:17`). Current protocol screen contains flow nodes and prototype contract rows (`sb-tab5-zone-composer-proposal.html:1251-1299`). | Move architecture to docs or validation overlay. Product UI should have `Home / Show Control` and `Diagnostics / Recovery`, not `Control Architecture`. |
| M-3 | Medium | Diagnostic cards: FPS, queue, heap, audio confidence | These are plausible but currently too terse and can become fake proof. `Queue 00` implies queue implementation; `100 FPS` implies live render truth. | Health screen shows `RENDER 100 FPS`, `AUDIO 0.72`, `QUEUE 00` (`sb-tab5-zone-composer-proposal.html:1192-1211`). MVP readback shows `Heap watch`, `WS rate coalesced`, `Manual owner active` (`sb-tab5-touch-mvp.html:469-473`). | Each diagnostic must show source and age: e.g. `serial fps`, `simulated`, `bridge queue`, `API needed`. Queue and WS rate must not appear green until the bridge/AP facade exists and has overflow/retry proof. |
| M-4 | Medium | Typography and long text | The fixed rows already crowd safety copy. The next board can fail if it keeps prose in compact cards rather than status/action labels. | Health safety card uses long prose in fixed cards (`sb-tab5-zone-composer-proposal.html:1218-1227`). Pixel contract requires text-fit against realistic runtime strings (`2026-06-07-tab5-ui-reset-plan.md:110`). | Use terse labels on glass and keep prose in docs/tooltips not primary screen. Run text-fit with long runtime strings and British-English spellings before acceptance. |
| M-5 | Medium | Borders/contrast/chrome weight | `1px` borders and dim footer/status text look polished in screenshots but are weak on a 5-inch panel, especially for structure and disabled states. | Operating contract says structural borders should be `2-3px`; `1px` is decorative only (`2026-06-07-tab5-pixel-match-operating-contract.md:60-61`). Current CSS uses shared `1px` borders on many cards (`sb-tab5-zone-composer-proposal.html:175-184`) and footer/status text is low contrast in screenshots. | Reserve `1px` for decoration. Use 2-3px borders for selected/focus/error/disabled structure. Prove contrast and legibility in exact 1280x720 and on-glass capture. |
| M-6 | Medium | Responsive/browser shell | The workbench scales the `.tab5` element to fit the browser shell; that is useful for viewing but toxic as approval evidence. | JS computes `--device-scale` from shell size (`sb-tab5-zone-composer-proposal.html:1368-1375`). Existing PNGs fail exact capture gate (`pixel-match-validation-pipeline.md:95-99`). | The next artifact must capture the `.tab5` element at device scale factor 1, exact `1280x720`, no transform, plus a separate diagnostic full-page screenshot. Approval must never use a scaled browser view. |

## Red-Team Element Cut List

Cut from the next drawing board unless backed by a new source/implementation gate:

- `WS LIVE`, `Connected`, `AUDIO SEMANTIC LIVE`, `status.subscribe broadcast`, and `USB ID OK`.
- Protocol / Architecture as an on-device page.
- Preset strip and preset-bank concepts.
- Zone count, zone layout, per-zone controls, camera mode, SynqMatrix, OTA, network management, STA/provisioning.
- `RenderParams` as a visible user concept or write target.
- One-tap or one-card calibration/reset/save actions.
- 8px bars as touch controls.
- Multiple homes for Smart Scene, EdgeMixer, mode, palette, or persistence.

## Minimum Remediation Before Another HTML Pass

1. Create a control registry before layout: target name, bounds, source, action, useful value count, one-home owner, safety class, stale state, and failure state.
2. Split screens to two operator surfaces only: `Home / Show Control` and `Diagnostics / Recovery`; keep architecture in docs or validation overlay.
3. Label all backend truth explicitly: `serial bridge only`, `API needed`, `simulated`, `runtime-only`, `persisted`, `stale`, or `live`.
4. Make the LGP/dual-edge centre-origin preview a first-order object, with schematic/live mode explicitly labelled.
5. Use control primitives by value type: mode picker/next-prev, segmented Smart Scene, toggle/segmented palette mode, sliders/steppers only for continuous controls.
6. Enforce touch geometry: primary `>=96px`, normal `>=72px`, visible compact controls read-only unless extended hit boxes are documented.
7. Remove safety/admin actions from the home surface; diagnostics must refuse dangerous actions by default.
8. Add a state matrix for every action before polish: disabled, pending, ack, timeout, failure, stale, queue full, reconnect, and wrong target.
9. Require exact `1280x720` capture plus hit-map overlay before visual sign-off.

## Required Re-Run Commands Used

Read-order and lane truth:

```bash
sed -n '1,220p' /Users/spectrasynq/.codex/skills/thinking-red-team/SKILL.md
rg -n "SB-TAB5|TAB5|tab5|drawing-board|drawing board|sb-tab5|Tab5|control" /Users/spectrasynq/.codex/memories/MEMORY.md
sed -n '880,930p' /Users/spectrasynq/.codex/memories/MEMORY.md
sed -n '1640,1720p' /Users/spectrasynq/.codex/memories/MEMORY.md
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '1,220p' progress.md
sed -n '1,220p' .claude/handoff.md
git status --short --branch --untracked-files=all
git rev-parse --short HEAD
```

Discovery:

```bash
find docs/forensics/sb-tab5-control -maxdepth 4 -type f -print
find docs -maxdepth 4 -type f -iname '*tab5*' -print
find evidence -maxdepth 5 -type f -iname '*tab5*' -print
find firmware-v3/docs/reference -maxdepth 1 -type f -print
find docs/protocol -maxdepth 1 -type f -print
```

Evidence documents:

```bash
sed -n '1,260p' docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md
sed -n '1,260p' docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md
sed -n '1,260p' docs/forensics/sb-tab5-control/local/2026-06-07-source-pass.md
sed -n '1,260p' docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md
sed -n '1,260p' docs/forensics/sb-tab5-control/local/2026-06-07-pipdeck-tab5-source-pass.md
sed -n '1,280p' docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md
sed -n '1,280p' docs/forensics/sb-tab5-control/agents/tab5-sb-ui-adversarial-review.md
sed -n '1,280p' docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md
sed -n '1,280p' docs/forensics/sb-tab5-control/agents/tab5-physical-pixel-reality.md
sed -n '1,280p' docs/forensics/sb-tab5-control/agents/tab5-controller-map.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/sb-control-map.md
sed -n '1,300p' docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/f3-api-map.md
sed -n '1,560p' docs/forensics/sb-tab5-control/agents/pixel-match-validation-pipeline.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/pipdeck-tab5-dashboard-pattern-audit.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/zone-composer-design-history.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/zone-composer-dimension-archaeology.md
```

Prototype and screenshot inspection:

```bash
sips -g pixelWidth -g pixelHeight sb-tab5-zone-composer-proposal-composer-final.png sb-tab5-zone-composer-proposal-composer-final2.png sb-tab5-zone-composer-proposal-composer-v2.png sb-tab5-zone-composer-proposal-composer.png sb-tab5-zone-composer-proposal-tab5-composer.png sb-tab5-zone-composer-proposal-tab5-health-final.png sb-tab5-zone-composer-proposal-tab5-health-v2.png sb-tab5-zone-composer-proposal-tab5-health.png sb-tab5-zone-composer-proposal-tab5-mix.png sb-tab5-zone-composer-proposal-tab5-protocol.png
grep -nE "tab5|screen|surface-button|action|health-card|preset|lgp-field|hero-strip|slider|bar|MODE|PHOTONS|CHROMA|MOOD|SMART|EDGE|NOISE|RESET|SAVE|WS|LIVE|API|SERIAL|simulated|Connected|data-action|data-screen|data-surface|addEventListener|button|role" docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
grep -nE "tab5|screen|surface|button|action|slider|range|MODE|PHOTONS|CHROMA|MOOD|SMART|EDGE|NOISE|RESET|SAVE|WS|LIVE|API|SERIAL|simulated|Connected|data-action|data-screen|addEventListener|role" docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '170,330p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '420,520p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '990,1168p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '1170,1312p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '1368,1448p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html | sed -n '140,330p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html | sed -n '400,490p'
```

Local image inspection was also performed with `view_image` on:

- `sb-tab5-zone-composer-proposal-tab5-composer.png`
- `sb-tab5-zone-composer-proposal-tab5-mix.png`
- `sb-tab5-zone-composer-proposal-tab5-health-final.png`
- `sb-tab5-zone-composer-proposal-tab5-protocol.png`

## Method Notes

- `rg --files` and one `find ... -print` path resolved through local wrappers unexpectedly; `find` still returned the target file inventory but emitted `rtk find: unknown flag '-print'`. This did not affect the evidence read because all files cited above were subsequently read directly.
- One grep pattern was re-run with single quotes after a shell backtick substitution artefact; the clean command is the one recorded here.
