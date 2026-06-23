# SB Tab5 Zone Composer Proposal V2 - Element Rationale

Date: 2026-06-07
Status: Draft drawing-board spec before V2 HTML pixel lab.
Scope: Replaces the current `sb-tab5-zone-composer-proposal.html` as the design
source for the next visual artefact. The old HTML remains evidence, not a build
baseline.

## What Changes From V1

V1 was a four-screen visual proposal:

- Light Composer
- Show Mix
- Smart + Health
- Control Architecture

V2 changes the architecture:

- `Control Architecture` is cut from the Tab5 UI. It belongs in docs, not on a
  five-inch operator surface.
- Primary navigation is reduced to two pages: `Home / Show Control` and
  `Diagnostics / Recovery`.
- Mix, advanced look, mode/palette pickers, admin recovery, and controller
  settings become bounded drill-downs, not equal top-level pages.
- No screen may show `WS LIVE`, `AUDIO SEMANTIC LIVE`, `Connected`, or similar
  labels unless backed by a live source and stale-state handling.
- The centre-origin light field becomes the first-order visual object, not a
  64px decorative strip.
- Action-looking elements must be real controls or visibly read-only.
- Primary touch targets target `>=96px` height; `72px` is the floor for new
  finger targets.
- Calibration/reset actions leave the product surface and move behind a
  guarded recovery flow.
- Every screen gets the same persistent header/footer chrome and a working
  escape path.

## Global Pixel Contract

Logical panel: `1280 x 720`

Outer margin: `12px`.

Standard gap: `12px`.

Secondary/internal gap: `8px`.

Persistent header:

- `x=12`
- `y=12`
- `w=1256`
- `h=72`
- border `2px`

Persistent footer:

- `x=12`
- `y=636`
- `w=1256`
- `h=72`
- border `2px`

Main content:

- `x=12`
- `y=96`
- `w=1256`
- `h=528`

Why not full-width `1280` header/footer:

- A full-edge border risks clipping and makes it harder to visually prove the
  panel bounds.
- `12px` outer margin matches prior Tab5 region discipline and keeps the chrome
  visible on all four sides.
- The `2px` border is intentional. `1px` is treated as decorative until
  hardware proof says otherwise.

Why `72px` header/footer:

- `72px` is the absolute floor for new finger targets on this panel.
- Header controls are mostly read-only, but secondary pages need a working Back
  target, so the chrome cannot be a tiny desktop status strip.
- Footer navigation needs reliable page escape from every state.
- A `64px` read-only header can be tested later, but V2 starts at `72px`
  because exact pixel proof and escape-path proof are not yet complete.

## Type Scale

Initial HTML type roles:

| Role | Size | Purpose |
|---|---:|---|
| Display | `48px` | one dominant state or mode value |
| Title | `28-32px` | page title, section title, primary labels |
| Body | `22-24px` | normal labels and control values |
| Caption | `16-18px` | read-only metadata, never critical live action |
| Numeric | `22-28px mono` | BPM, FPS, percentage, mode ID |

Overshoot policy:

- No marquee for primary action labels.
- Primary labels must be short by design.
- Long mode/effect names use a single-line clamp with an explicit short alias,
  not hidden overflow.
- Numeric values align right or centre in monospace.
- Any label that cannot fit at the assigned role size forces either copy
  shortening or layout change, not font shrink below legibility.

## Persistent Header

Header element map:

| Element | Bounds | Type | Why it exists | Why placed there | Notes |
|---|---:|---|---|---|---|
| Device/transport block | `x=24 y=20 w=260 h=56` | read-only status | Confirms which K1/control path the screen represents. Prevents fake-live confusion. | Left is the first scan anchor and the source of authority before any action. | Shows `K1-SB`, firmware/chip when known, and `SERIAL BRIDGE`, `API NEEDED`, `SIM`, or `LIVE`. Never green unless stale-state proof exists. |
| Page/current mode block | `x=296 y=20 w=520 h=56` | read-only current state | The centre of the header should answer "what am I controlling right now?" | Centre is the highest visual authority in persistent chrome. | Home shows current mode. Secondary pages show page title plus inherited current mode in smaller text. |
| Command/fault summary | `x=828 y=20 w=428 h=56` | read-only status | Shows whether the last action can be trusted: pending, applied, failed, stale, offline, wrong target. | Right side is the conventional result/escalation edge after identity and current state. | Normal reassurance is hidden. This area appears when the operator needs to know a command or fault state. |

Header cuts:

- No backend selector.
- No WiFi network picker.
- No OTA/update.
- No reset/calibration.
- No architecture labels.

Back behaviour:

- Home has no Back button.
- Secondary pages replace the left device block with a `Back` target only when
  needed.
- Back target minimum: `112 x 72px`.
- Back always returns to Home. It never opens a menu and never depends on a
  hidden gesture.

## Persistent Footer

Footer element map:

| Element | Bounds | Type | Why it exists | Why placed there | Notes |
|---|---:|---|---|---|---|
| Show tab | `x=12 y=636 w=320 h=72` | nav button | Fast return to the main performance surface. | Left because it is the base state and the first escape path. | Active state is obvious by fill/border; tap always works unless app is in destructive confirmation. |
| `K1 Pulse` summary | `x=332 y=636 w=616 h=72` | read-only trust strip | Audio trust is high-value across every page. The user should always know if K1 is hearing, silent, stale, or beat-locked. | Centre because it is shared context, not a page destination or command. | Shows source and age. Never says live without proof. Detailed audio remains on Home/Diagnostics. |
| Diagnostics tab | `x=948 y=636 w=320 h=72` | nav button | Separates diagnostic/recovery truth from performance controls. | Right because it is lower-frequency escalation/recovery. | Includes recovery and controller-settings entry points, not one-tap recovery. |

Why footer has two tabs plus `K1 Pulse`, not four tabs:

- Two primary pages match the reset plan and avoid treating secondary concerns
  as peer workflow surfaces.
- `Mix` is important, but it is a Home drill-down because it modifies the show;
  it is not a persistent global destination.
- `Settings` is important, but it is a Diagnostics/controller drill-down because
  it configures the controller rather than the show.
- Two `320x72px` nav targets remain physically usable, while the centre strip
  gives audio trust real estate without creating another page.

Why footer is navigation plus audio trust, not a metric graveyard:

- Navigation is the escape path across every page.
- Audio trust changes operator decisions in a music visualiser; generic metrics
  do not.
- Command feedback uses a transient strip above the footer, not persistent
  footer real estate.

Footer cuts:

- No five-button action row.
- No mixed nav + destructive action row.
- No tiny status labels that are critical to operation.

## Screen 1 - Home / Show Control

Job: Start or judge a show quickly, make one safe visual adjustment, and see
whether the audio engine is trustworthy.

Layout:

- Header: persistent.
- Hero light field: `x=12 y=96 w=1256 h=220`.
- Control lower area: `x=12 y=328 w=1256 h=296`.
- Footer: persistent.

### Home Elements

| Element | Bounds | Type | Why it exists | Why this size | Why this position | Alternative rejected |
|---|---:|---|---|---|---|---|
| Centre-origin dual-edge hero | `12,96,1256,220` | read-only schematic, future live readback | It is the object being controlled. Without this, the page becomes generic sliders. | `220px` gives visual judgement priority while leaving enough space for controls. | Top content region, immediately below header; first thing seen after device identity. | `64px` strip from V1 is rejected as too small and decorative. |
| Centre marker `79|80` | inside hero, centred | read-only orientation | K1 centre origin is load-bearing. | Small marker, but high contrast; not a touch target. | Physical centre of hero. | Any linear-left-to-right visual language is rejected. |
| Primary/secondary edge labels | inside hero, left/right lanes | read-only orientation | Shows dual-edge relationship without importing zones. | Caption/body size; labels are not controls. | Near each edge lane so the user does not need a legend. | Zone labels rejected; SB does not have donor zone backend. |
| Mode stepper group | `12,328,392,136` | two large buttons + mode display | Mode changes are a high-frequency performance action. | Prev/Next buttons `120x96`; mode display gets remaining width. | Lower-left: after viewing hero, first action is show selection. | Dropdown rejected: too slow, fragile, and label-heavy on 5-inch glass. |
| Smart Scene segment | `12,476,392,136` | segmented control | Smart autonomy is a primary product decision: off/assist/L1/auto. | Four segments, each about `98x96`; meets primary touch height. | Under mode because it changes how mode responds. | Slider rejected because this is an enum. Toggle rejected because there are more than two states. |
| Photons slider | `416,328,392,88` | horizontal slider with large thumb | Brightness is continuous and high-frequency. | Row height `88`; touch rail `64`; thumb `64`. | Centre column first: this is the safest global visual intensity control. | Vertical slider rejected because finger occlusion and space cost are worse. Tiny meter rejected as non-operable. |
| Chroma slider | `416,432,392,88` | horizontal slider | Colour intensity is continuous and perceptually important. | Same geometry as Photons for alignment and muscle memory. | Stacked below Photons; same control class. | Knob rejected for touch because circular precision is poorer without encoder detents. |
| Mood slider | `416,536,392,88` | horizontal slider | Mood is a continuous feel control. | Same row height and track system. | Completes the three primary feel controls. | Stepper rejected unless future proof shows only a few useful values. |
| `K1 Pulse` audio detail panel | `820,328,448,136` | read-only metric panel | Audio is high value; it tells the user whether music response can be trusted. | Large enough for hearing/silence/beat/onset/cal rows without tiny labels. | Right column: status/result side, after controls. | Generic footer metrics and raw waveform/spectrum rejected; footer keeps only the compact `K1 Pulse` summary. |
| Palette control | `820,476,448,72` | button or compact picker entry | Palette is useful but less urgent than mode/photons/chroma/mood. | `72px` floor; opens a full picker page/list if needed. | Under audio trust because it is a secondary visual choice. | Dropdown rejected; use full-screen list/palette page later if palette browsing grows. |
| Manual-owner / command feedback strip | `820,560,448,64` | read-only + transient feedback | Shows whether manual control is overriding Smart and whether last command applied. | `64px` read-only; command feedback can overlay to `72px` when interactive. | Bottom-right, close to user action result path. | Persistent global command footer rejected to preserve navigation. |

Home cuts:

- No `SAVE NOW`.
- No `RESET`.
- No `NOISE CAL`.
- No architecture flow.
- No backend selector.
- No AP/VP capture toggles.

## Drill-Down 1 - Channel Detail / Mix

Job: Tune secondary edge behaviour and EdgeMixer deliberately, after the user
chooses to leave the Home loop.

Parent page: `Home / Show Control`.

Entry affordance: Home `Channel Detail` / `Open Mix` target.

Back target: `Home / Show Control`, state preserved.

Layout:

- Header with Back or persistent footer Show tab escape.
- Hero dual-edge preview: `12,96,1256,200`.
- Two-column control region: `12,308,1256,316`.
- Footer: persistent.

### Mix Elements

| Element | Bounds | Type | Why it exists | Why this size | Why this position | Alternative rejected |
|---|---:|---|---|---|---|---|
| Mix hero preview | `12,96,1256,200` | read-only schematic/readback | Shows primary and secondary relationship before controls. | Slightly shorter than Home because this page is detail-heavy. | Top content, consistent with Home hierarchy. | Card-only mix screen rejected; user must see what is being mixed. |
| Secondary enable | `12,308,184,96` | toggle | Binary state with high impact. | `184x96` is a confident touch target. | Top-left of detail controls; enabling precedes tuning. | Small switch rejected; too easy to miss or misread. |
| Secondary mode | `208,308,412,96` | stepper/display | Secondary mode is discrete and source-backed. | Same action height as Home mode. | Same row as enable because both define secondary identity. | Dropdown rejected; mode picker only if list becomes large. |
| Secondary photons | `12,416,608,88` | horizontal slider | Continuous brightness for secondary edge. | Mirrors Home feel controls. | Left column under secondary identity. | Shared primary/secondary target toggle rejected; touch should expose separate panels. |
| Secondary chroma/mood combined row | `12,516,608,108` | two compact sliders or segmented expand | Secondary feel is useful but not first-screen priority. | Split row only if labels fit; otherwise one-at-a-time expander. | Left column below brightness. | Three full sliders rejected if they crowd EdgeMixer. |
| EdgeMixer enable/mode | `632,308,636,96` | toggle + segmented mode | EdgeMixer changes channel relationship, not a raw effect. | `96px` height keeps mode segments operable. | Top-right: counterpart to secondary identity. | Plain text status rejected; this is a meaningful control when user entered Mix. |
| EdgeMixer strength | `632,416,636,88` | coarse stepper, slider only if proven | Strength is technically continuous but likely perceptually coarse in useful operation. | `88px` row gives enough room for decrement/value/increment without tiny targets. | Directly under EdgeMixer mode. | Fine slider rejected as baseline; knob rejected because there is no tactile encoder. |
| Palette secondary entry | `632,516,308,108` | large button/list entry | Palette may need its own picker. | Tall enough for label and current value. | Lower-right, detail action. | Tiny preset tiles rejected. |
| Mix reset-to-safe | `960,516,308,108` | guarded reversible button | Gives recovery without destructive reset. | Large because it changes multiple runtime controls. | Lower-right, separate from ordinary sliders. | Factory/reset/defaults rejected; safe mix reset only, with confirmation if state-changing. |

Channel Detail escape:

- Footer `Show` returns Home.
- Header Back returns Home if present.
- No page may rely on swipe gestures.

## Screen 2 - Diagnostics / Recovery

Job: Determine whether K1 is hearing/rendering correctly and start guarded
recovery only when the source state supports it.

Layout:

- Header with page title and high-level health.
- Diagnostic grid: `12,96,1256,256`.
- Audio detail: `12,364,608,260`.
- Recovery panel: `632,364,636,260`.
- Footer: persistent.

### Diagnostics Elements

| Element | Bounds | Type | Why it exists | Why this size | Why this position | Alternative rejected |
|---|---:|---|---|---|---|---|
| Device health grid | `12,96,1256,256` | read-only cards | Firmware/chip/FPS/render/reset/cal source are diagnostic truth surfaces. | Cards can use body/caption text without becoming tiny. | Top: before recovery, prove state. | Architecture diagram rejected; operational status only. |
| Audio detail panel | `12,364,608,260` | read-only waveform/metrics | Audio is high-value and explains visual behaviour. | Large enough for beat, onset, silence, calibration validity. | Left lower: diagnostic cause path. | Tiny header-only audio rejected. |
| Recovery entry | `632,364,636,120` | guarded button group | Recovery must be deliberate and visible. | Buttons `>=96px` where actionable. | Right lower: action follows diagnosis. | One-tap calibration/reset rejected. |
| Guarded calibration state | `632,496,636,128` | state machine panel | Shows why calibration is allowed/refused. | Enough room for silence requirement, countdown, cancel/confirm. | Below recovery entry so the user sees preconditions. | Popup-only calibration rejected; it is too dangerous for a transient overlay. |
| Controller settings entry | within recovery/utility area, `>=72px` target | drill-down button | Settings matter, but they are not show controls. | At least floor target; not primary height unless on-glass proof demands. | Diagnostics owns controller state and preferences. | Persistent Settings footer tab rejected as over-promoted chrome. |

Recovery rules:

- `Noise Cal` is not on Home.
- `Noise Cal` cannot be a one-tap button.
- Calibration requires visible silence/readiness, explicit arm, explicit
  confirm, cancel, timeout, and result.
- Reset/factory/defaults are not MVP product controls.

## Drill-Down 2 - Controller Settings / Feedback

Job: Configure the Tab5/controller interaction, not the K1 show itself.

Parent page: `Diagnostics / Recovery`.

Entry affordance: Diagnostics `Controller Settings` target.

Back target: `Diagnostics / Recovery`, with persistent footer Home escape.

Layout:

- Header with Settings title.
- Four settings groups: display, audio feedback, input feedback, profiles.
- Footer: persistent.

### Settings Elements

| Element | Bounds | Type | Why it exists | Why this size | Why this position | Alternative rejected |
|---|---:|---|---|---|---|---|
| Tab5 display brightness | `12,96,608,120` | horizontal slider | Screen brightness affects real-world usability and battery/comfort. | `120px` row supports confident adjustment. | First setting: it affects all screens. | Tiny system chip rejected. |
| UI audio feedback toggle/volume | `632,96,636,120` | toggle + slider | Audio feedback is a mature UX cue if it is controllable. | Large row; toggle and volume not crammed. | Top-right: paired with display feedback. | Always-on sounds rejected. |
| Touch feedback mode | `12,228,608,120` | segmented control | User should choose off/subtle/strong if hardware supports it. | Segments are easier than dropdown. | Second row, input behaviour. | Hidden global setting rejected. |
| Command acknowledgement style | `632,228,636,120` | segmented control | Lets the user pick visual/audio confirmation intensity. | Clear three-state control. | Paired with touch feedback. | No feedback rejected as immature; too much feedback rejected as annoying. |
| Profile slots | `12,360,1256,144` | large slot buttons | Profiles may be valuable, but only if they map to real controller settings first. | Four slots, each about `300x120`. | Lower wide row; profile action is less frequent. | Tiny preset grid rejected. |
| Network note/status | `12,516,1256,108` | read-only / future guarded page entry | K1 is AP-only and current SB lacks wireless backend. | Read-only note prevents fake network UI. | Bottom settings row. | WiFi network selection/password saving cut from MVP until transport exists; if added later, it gets a full-screen keyboard flow, not a dropdown. |

Settings cuts:

- No K1 STA network selection.
- No WiFi password saving for K1 MVP.
- No firmware update.
- No multi-K1 pairing.
- No hidden developer toggles.

## Popups, Overlays, And Dropdowns

Popups:

- Use only for command acknowledgement or destructive confirmation.
- Never stack popups.
- Dangerous actions prefer a full-page guarded flow over a small modal.

Dropdowns:

- Avoid on Tab5 for primary controls.
- Use segmented controls for small enums.
- Use full-screen list/picker for long lists such as modes or palettes.

Toasts:

- Allowed for command feedback.
- Must not hide primary controls for more than a short interval.
- Must include success/failure/stale state, not only animation.

## Input Feedback

Every control needs immediate feedback:

- touch down: depressed state within the local UI;
- queued: visible pending state if command is asynchronous;
- applied: brief success confirmation;
- refused: reason shown near the control;
- stale/disconnected: disable or mark controls, never pretend success.

Professional feedback choices:

- Visual: border/fill state, not only text.
- Audio: optional subtle click/confirm/error cue on Tab5, controlled in Settings.
- Haptic: optional only if the hardware path is verified; no visible haptic
  control ships on assumption.
- No destructive action may rely on sound alone.

## Alignment Rules

- All persistent chrome aligns to `x=12 w=1256`.
- All major content blocks align to the same x-grid.
- Standard section gap is `12px`.
- Internal compact gap is `8px`.
- Border width for structural regions is `2px`.
- Card border may be `1px` only for non-structural passive cards and only after
  pixel proof.
- Values align right or centre in monospace.
- Labels align consistently inside their group:
  - control labels left,
  - values right,
  - segmented option labels centre.

## Visual Hierarchy

V2 hierarchy is:

1. Device/control truth in the header.
2. Current visual output object in the hero.
3. Primary show actions.
4. Secondary/detail controls.
5. Read-only diagnostics.
6. Settings and rare recovery.

Anything that does not fit this hierarchy is cut, moved down a page, or rendered
read-only.

## Known Open Questions

- Exact LVGL font availability for the final Tab5 controller stack.
- Whether Tab5 audio/haptic feedback is reliable enough to ship.
- Whether profile slots should save Tab5 preferences only or also K1 show
  state after a real control protocol exists.
- Whether first transport proof should be serial bridge or native SB AP facade.
  Current recommendation remains serial bridge first.
