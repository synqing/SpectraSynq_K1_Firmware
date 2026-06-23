# SB-TAB5-V2-HEADER-FOOTER-RATIONALE

Task ID: `SB-TAB5-V2-HEADER-FOOTER-RATIONALE`

Evidence question: For a revised SB Tab5 controller based on the pixel-match
reset, what header/footer elements deserve fixed real estate, where should they
be placed, and what should be cut?

Verdict: `VERIFIED_WITH_LIMITS`

Limit: this is source-backed and physical-pixel-backed layout rationale only.
No Tab5 framebuffer, touch path, browser capture, serial bridge, or live K1
round-trip was run in this pass.

## Hard Pixel Contract

The Tab5 approval surface is `1280x720`, not a browser-scaled preview. Local
pixel-match contract lines require exact `1280 x 720` evidence, per-control
bounding boxes, millimetre sizes, one reason per visible element, one home per
parameter, and failure states for touch actions
(`2026-06-07-tab5-pixel-match-operating-contract.md:50-76`). The reset plan
rejects the existing HTML because it has inert action-looking controls,
`36-44px` apparent targets, `8px` bars, non-`1280x720` screenshots, fake-live
WS/status labels, architecture explainer content, and calibration/reset too
near the operator surface (`2026-06-07-tab5-ui-reset-plan.md:9-21`).

Physical model, using the 5-inch `1280x720` Tab5 panel: `1mm = 11.56px`,
`44px = 3.80mm`, `64px = 5.53mm`, `72px = 6.23mm`,
`96px = 8.30mm`, `120px = 10.38mm`, full panel `110.69mm x 62.26mm`.
The same source says primary finger actions prefer at least `96px`, `72px` is
the floor for new targets, and anything below `72px` must be secondary,
read-only, or explicitly extended (`tab5-physical-pixel-reality.md:21-78`).
Official Tab5 docs were checked live on 2026-06-07 and still list a 5-inch
`1280x720` IPS TFT display; they also flag the current ST7123 driver-change
risk, so final touch implementation still needs device-revision proof:
https://docs.m5stack.switch-science.com/en/core/Tab5

Fixed chrome budget recommendation:

| Region | Box | Physical height | Rule |
|---|---:|---:|---|
| Header truth strip | `x=0 y=0 w=1280 h=64` | `5.53mm` | Read-only or low-risk tap-to-detail only; no primary actions. |
| Main work area | `x=0 y=64 w=1280 h=584` | `50.49mm` | All primary show controls live here; primary actions `>=96px` high. |
| Footer nav/trust strip | `x=0 y=648 w=1280 h=72` | `6.23mm` | Navigation/status only; no destructive or high-risk command. |

This consumes `136px` of `720px` (`18.9%`) for persistent chrome. That is near
the local warning band for bottom chrome (`76px + 72px = 148px`, about 20%),
so every kept element below must alter an operator decision.

## Header Placement

Recommended header subdivision:

| Element | Verdict | Placement | Pixel box | Why left / centre / right | Source-backed reason |
|---|---|---|---:|---|---|
| Target + transport truth | KEEP | Header left | `x=16 y=8 w=320 h=48` (`27.67mm x 4.15mm`) | Left is the stable "what am I controlling?" origin before any command. | Current SB is USB CDC serial only, no current REST/WS/HTML backend; show `SERIAL BRIDGE`, `API NEEDED`, `SIMULATED`, or `LIVE age=<n>s`, not fake green. `sb-touch-control-map.md:17-31`, reset fake-live blocker `2026-06-07-tab5-ui-reset-plan.md:106-117`. |
| Current mode / palette / show surface | KEEP | Header centre | `x=340 y=0 w=520 h=64` (`44.97mm x 5.53mm`) | Centre is the primary glance target and should align with the K1 centre-origin mental model; it replaces static brand/title. | Donor audit cuts static brand and keeps effect/palette as the hero (`DESIGN_BRIEF.md:11-32`); reset keeps current enabled mode and primary show controls (`2026-06-07-tab5-ui-reset-plan.md:69-79`). |
| Command/fault/stale outcome | KEEP, conditional | Header right | `x=864 y=8 w=400 h=48` (`34.59mm x 4.15mm`) | Right is the conventional outcome/escalation side; it should show whether the last command can be trusted. | Prototype actions need visible state and failure behaviour; no widget without a data source/failure state (`touch-only-ux-critique.md:31-33`, `PipDeck-Firmware/docs/00_PRODUCT_FRAME.md:26-34`). Show `PENDING`, `STALE`, `FAILED`, `OFFLINE`, or critical FPS/render alert. Hide or demote normal `100 FPS`. |
| Static brand / page title | CUT | Do not reserve header chrome | n/a | It does not change operation. | Donor audit says static brand title carries zero operational information (`DESIGN_BRIEF.md:5-21`). |
| Back button | CUT from fixed header | Use footer/page nav instead | Current mock: `100x44` | `44px` is only `3.80mm`; fixed back is both too small and a poor use of top chrome. | Current HTML uses a `<div class="back">` at `100x44`, not a semantic button (`sb-tab5-zone-composer-proposal.html:190-198`, `:1000-1002`), and red-team flagged it as inert (`current-html-pixel-redteam.md:23-40`). |
| Normal health chips (`K1 AP`, `WS LIVE`, `100 FPS`) | CUT / replace | Only source-backed truth or exception state survives | Current status cards `44px` high | Status chips must not exist because they look reassuring. | Current mock shows `K1 AP`, `WS LIVE`, and `100 FPS` in header (`sb-tab5-zone-composer-proposal.html:1003-1006`) while current SB has no active WS/REST backend (`sb-touch-control-map.md:17-31`, `:63-71`). |

Header summary: keep the header as a `64px` truth strip, not as a control row.
The header may be tappable only for low-risk detail expansion with an extended
hit area; it must not contain mode next, calibration, reset, save, or primary
show actions.

## Footer Placement

Recommended footer subdivision:

| Element | Verdict | Placement | Pixel box | Why left / centre / right | Source-backed reason |
|---|---|---|---:|---|---|
| `SHOW` / Home tab | KEEP | Footer left | `x=0 y=648 w=320 h=72` (`27.67mm x 6.23mm`) | Left is the default return-to-show affordance. | Reset reduces the next artefact to operator pages: Home / Show Control and Diagnostics / Recovery (`2026-06-07-tab5-ui-reset-plan.md:141-148`). |
| Audio trust summary | KEEP, read-only | Footer centre | `x=320 y=648 w=640 h=72` (`55.35mm x 6.23mm`) | Centre is shared context, not a command; it should be glanceable from either page. | Donor Tab5 keeps footer BPM/key/mic as audio-reactive state critical to a visual instrument (`DESIGN_BRIEF.md:23-32`). Reset keeps read-only audio trust: hearing/silence, beat confidence, onset/bass onset, calibration validity/source (`2026-06-07-tab5-ui-reset-plan.md:76-77`). Must include source/stale state; never show fake `AUDIO SEMANTIC LIVE`. |
| `DIAGNOSTICS / RECOVERY` tab | KEEP | Footer right | `x=960 y=648 w=320 h=72` (`27.67mm x 6.23mm`) | Right is lower-frequency escalation/recovery, separated from show controls. | Reset puts diagnostics, `smart_status`, `edge_status`, `vp_status`, FPS/LED FPS, and stop-streams behind secondary/advanced (`2026-06-07-tab5-ui-reset-plan.md:81-89`). |
| Admin/calibration/reset entry | CUT from persistent footer | Diagnostics only, guarded | n/a | High-risk actions should not be thumb-adjacent to show navigation. | Noise calibration must not be one-tap and typed `start_noise_cal` is guarded/disabled guidance (`sb-touch-control-map.md:47`); reset plan cuts one-tap calibration/reset/defaults/clear-cal from product screen (`2026-06-07-tab5-ui-reset-plan.md:91-100`). |
| Queue/save/update normal strings | CUT unless abnormal | If abnormal, header right | Current footer `38px` | Normal reassurance does not alter decisions. | Current mock footer says `QUEUE EMPTY`, `SAVE DELAYED`, `AUDIO SEMANTIC LIVE` (`sb-tab5-zone-composer-proposal.html:1109-1114`) and `Last update: status.subscribe broadcast` (`sb-tab5-touch-mvp.html:477-480`), but reset requires fake-live blocker and explicit source labels (`2026-06-07-tab5-ui-reset-plan.md:106-119`). |
| Architecture/protocol page navigation | CUT from footer | Keep in docs/lab, not controller | n/a | An operator tab should not spend fixed glass on implementation explanation. | Reset explicitly rejects the architecture screen as a design-review explainer, not an operator page (`2026-06-07-tab5-ui-reset-plan.md:16-18`). |

Footer summary: use the footer for two-page navigation plus one source-backed
audio-trust summary. Do not use the footer as a status-chip graveyard. If the
audio summary cannot be backed by live/stale-aware readback, replace the centre
cell with `SIMULATED` / `SERIAL BRIDGE ONLY` rather than a green live claim.

## Element Cut List

Cut these from fixed header/footer chrome:

- Static `SB Controller`, `LIGHTWAVEOS`, or page-pitch branding.
- Fake `Connected`, `WS LIVE`, `AUDIO SEMANTIC LIVE`, `status.subscribe`, or
  unqualified green dots.
- Raw IP address as proof of target; use chip/version/source/age if available.
- Permanent `100 FPS` / `LED FPS` chips; show only when stale, below threshold,
  or in diagnostics.
- `QUEUE EMPTY`, `SAVE DELAYED`, and normal last-update strings unless pending,
  stale, failed, or about to change operator behaviour.
- Back buttons and right-side prototype rails outside the `1280x720` panel.
- Protocol/architecture tabs in the operator controller.
- Backend selector, STA/provision/network-management controls, firmware-v3
  `/ws` or `/api/v1` labels as if current SB implements them.
- Zones, SynqMatrix, camera mode, OTA, filesystem, multi-K1 pairing, and
  preset-bank machinery for the SB MVP.
- Physical knob/button/encoder status for current K1 hardware.
- `RenderParams` write controls.
- One-tap calibration, reset, restore defaults, clear calibration, and
  non-shippable capture/probe controls on fixed chrome or home screen.

## Placement Verdict

The revised V2 chrome should be:

```text
y=0..63      HEADER 64px:
             [LEFT target/transport truth] [CENTRE mode/palette/show state] [RIGHT command/fault/stale]

y=64..647    MAIN 584px:
             centre-origin LGP / primary show controls / secondary + Smart controls by page

y=648..719   FOOTER 72px:
             [LEFT Show] [CENTRE source-backed audio trust] [RIGHT Diagnostics/Recovery]
```

This preserves fixed real estate only for target truth, current show identity,
action trust/failure, page navigation, and audio trust. Everything else is
content, diagnostics, or cut.

## Required Re-run Commands Used

Run from `/Users/spectrasynq/SensoryBridge-main 9` unless an absolute path is
shown.

```bash
rg -n "SB[-_ ]?Tab5|Tab5|pixel-match|header|footer|controller|PIPdeck" /Users/spectrasynq/.codex/memories/MEMORY.md
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '1,220p' progress.md
sed -n '1,220p' .claude/handoff.md
command rg --files -g '!/.git/**' -g '!/.pio/**' -g '!/.claude/worktrees/**' -g '!libraries/_FastLED.disabled/**' -g '!Lightwave-Ledstrip/**' | command rg '(^|/)docs/forensics/sb-tab5-control|Tab5|tab5|control|\.html$|codebase-map\.md$|fsm-reference\.md$|docs/protocol/k1-(ws|rest)-contract\.yaml$'
command rg -n "header|footer|top|bottom|status|chip|tab|nav|bar|rail|\.app|\.tab5|1280|720|position|grid|Footer|Header|live|connected|serial|bridge|mode|Home|Diagnostics|Protocol|Health|Composer" docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
sed -n '1,220p' docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md
sed -n '1,240p' docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/tab5-controller-map.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/tab5-physical-pixel-reality.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md
sed -n '1,280p' docs/forensics/sb-tab5-control/agents/tab5-sb-ui-adversarial-review.md
sed -n '1,260p' docs/forensics/sb-tab5-control/agents/pipdeck-tab5-dashboard-pattern-audit.md
nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md | sed -n '22,90p'
nl -ba docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-reset-plan.md | sed -n '8,126p'
nl -ba docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md | sed -n '17,78p'
nl -ba docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md | sed -n '20,116p'
nl -ba docs/forensics/sb-tab5-control/agents/tab5-physical-pixel-reality.md | sed -n '15,94p'
nl -ba docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md | sed -n '3,48p'
nl -ba docs/forensics/sb-tab5-control/agents/tab5-controller-map.md | sed -n '17,66p'
nl -ba docs/forensics/sb-tab5-control/agents/pipdeck-tab5-dashboard-pattern-audit.md | sed -n '19,86p'
nl -ba docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md | sed -n '1,120p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '137,245p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '581,626p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html | sed -n '998,1118p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html | sed -n '152,204p'
nl -ba docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html | sed -n '401,480p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/01_STAGE_1_1_STATS_SPEC.md | sed -n '1,45p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5-A3.3-confirm-overlay/PipDeck-Firmware/docs/00_PRODUCT_FRAME.md | sed -n '20,40p'
nl -ba /Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/tab5-encoder/docs/DESIGN_BRIEF.md | sed -n '5,45p'
awk 'BEGIN{ppi=sqrt(1280*1280+720*720)/5; mm=25.4/ppi; for (i=1;i<ARGC;i++){px=ARGV[i]+0; printf("%dpx=%.2fmm\n", px, px*mm)}}' 38 44 48 54 56 60 64 72 80 88 96 112 120 128 144 256 360 420 520 1280 720
awk 'BEGIN{ppi=sqrt(1280*1280+720*720)/5; mm=25.4/ppi; for (i=1;i<ARGC;i++){px=ARGV[i]+0; printf("%dpx=%.2fmm\n", px, px*mm)}}' 12 16 20 24 48 56 64 72 96 300 320 360 400 416 420 424 480 520 640 1280
git status --short --branch --untracked-files=all
git rev-parse --short HEAD
```
