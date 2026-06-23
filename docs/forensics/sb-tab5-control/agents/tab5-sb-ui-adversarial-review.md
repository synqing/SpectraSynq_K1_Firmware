# TAB5-SB-UI-ADVERSARIAL-REVIEW

**Task ID:** TAB5-SB-UI-ADVERSARIAL-REVIEW  
**Evidence question:** Attack the whole proposed SB Tab5 UI programme: what assumptions, scope choices, control mappings, visual choices, and validation gates are likely to fail or waste time?  
**Default verdict:** NOT_VERIFIED  
**Classification:** load-bearing  
**Scope:** Read-only source/prototype/evidence review. This file is the only write.

## Verdict

NOT_VERIFIED. The programme has a viable donor grammar, but the current plan is still too willing to show live-looking controls for a firmware surface that does not exist, and too willing to promote a polished desktop HTML mockup into a Tab5/K1 programme before transport, touch, timing, safety, and truth-source gates exist.

## Red-Team Findings

### CRIT-1: The mockups already lie about live transport

**Severity:** Critical  
**Assumption attacked:** The UI can show WS/API/readback states while the backend is still "API-needed."  
**Evidence:** Current SB has USB CDC serial only, no active WiFi/REST/WS server or route table (`sb-touch-control-map.md:17-25`, `sb-control-map.md:31-35`, `sb-control-map.md:47-53`). The prototypes show "Connected", "WS LIVE", "AUDIO SEMANTIC LIVE", `status.subscribe broadcast`, "WS LINK LIVE", and AP/WS status as if those surfaces already exist (`sb-tab5-touch-mvp.html:406-409`, `sb-tab5-touch-mvp.html:477-479`, `sb-tab5-zone-composer-proposal.html:1003-1006`, `sb-tab5-zone-composer-proposal.html:1110-1113`, `sb-tab5-zone-composer-proposal.html:1193-1196`).  
**Attack scenario:** Captain sees the mockup and approves "wire it up"; an implementer spends cycles chasing `/ws`/status parity while the actual SB tree still has no network substrate.  
**Failure symptom:** Beautiful UI with fake green lights; no command path, no status truth, no way to tell stale/simulated from live K1. This repeats the known Tab5 stale-screen/System Pulse failure class.  
**Remediation:** Until a live facade exists, every live-looking pill must be replaced by `API NEEDED`, `SIMULATED`, or `SERIAL BRIDGE ONLY`. First proof must be a minimal status/control round-trip with stale-state detection, not a broader visual build.

### CRIT-2: "Native SB WebSocket MVP first" is probably the wrong first cut

**Severity:** Critical  
**Assumption attacked:** Adding a small AP-only JSON/WS facade to production SB is the fastest safe route.  
**Evidence:** SB production deps are only FastLED, FixedPoints, and M5ROTATE8; there is no ArduinoJson/AsyncTCP/WebSocket server in current SB (`local/2026-06-07-source-pass.md:12-13`, `sb-touch-control-map.md:24-25`). The proposed MVP says Tab5 joins K1 AP and talks to `/ws` through a compact facade (`sb-tab5-touch-mvp.html:360-390`, `sb-tab5-touch-mvp.html:486-490`). The firmware-v3 backend that has these features also carries rate limits, client caps, low-heap shedding, stream cadences, auth hooks, and actor-message seams (`f3-api-map.md:83-90`, `f3-api-map.md:39-68`, `f3-api-map.md:69-75`).  
**Attack scenario:** A "small" network facade grows into JSON parsing, broadcasts, queues, reconnect handling, auth/no-auth policy, heap pressure, and Core 0 WiFi/audio contention.  
**Failure symptom:** Firmware/UI time disappears into transport plumbing, AP jitter, heap regressions, or non-shippable diagnostic exceptions before any touch layout is proven useful.  
**Remediation:** Use a host serial bridge as the first physical UI proof unless the explicit goal is firmware-network substrate work. Prove the Tab5 UI on glass, command semantics, and stale/failure states through serial first; only then implement the smallest fixed-record AP facade with timing/heap gates.

### HIGH-1: Firmware-v3 and Tab5 donor surfaces are being treated as too transferable

**Severity:** High  
**Assumption attacked:** firmware-v3/Tab5 contract vocabulary can be reused without importing scope.  
**Evidence:** Current SB explicitly should not show firmware-v3 `setBrightness`, `setPalette`, `/ws`, `/api/v1`, `effects.*`, `parameters.*`, `zones.*`, or `synqMatrix.*` as implemented (`sb-touch-control-map.md:63-68`). firmware-v3 has REST/WS zones, SynqMatrix, debug, network, OTA, audio streams, and batch surfaces (`f3-api-map.md:21-38`, `f3-api-map.md:49-60`). The plan says "reuse firmware-v3 protocol vocabulary where it fits" while recommending a native WS facade (`sb-tab5-touch-mvp.html:360-390`).  
**Attack scenario:** The prototype starts with mode/photons/chroma/mood but quickly accretes zones, SynqMatrix, effect parameters, OTA, presets, and network management because they exist in donor docs.  
**Failure symptom:** MVP becomes a parity migration project; Captain gets no useful K1 controller while agents debate contracts.  
**Remediation:** Freeze the first protocol to SB-native intents only: status, current mode, set mode, primary/secondary photons/chroma/mood, palette mode/index, Smart Scene, EdgeMixer enable/mode/strength, and read-only health. Everything else is explicitly out of scope until a real K1 use case forces it.

### HIGH-2: Zone Composer is a visual donor, not a product backend

**Severity:** High  
**Assumption attacked:** Zone Composer grammar can be promoted into the SB controller without causing zone-scope creep.  
**Evidence:** The donor Zone Composer is LED-centric and strong, but its actual protocol is `zone.*`, `zones.setLayout`, 1-indexed wire zones, and up to three zones (`tab5-controller-map.md:35-38`, `tab5-controller-map.md:54-60`, `zone-composer-design-history.md:21-32`). Current SB prototype guidance says do not include zone composer controls or zone count as current SB firmware controls (`sb-touch-control-map.md:63-68`), and the local pass says zone protocol should not be copied unless SB actually gains a zone/layer backend (`local/2026-06-07-zone-composer-ui-pass.md:45-47`).  
**Attack scenario:** The team spends a week designing "Light Composer" as if SB has zone/layer state instead of dual edge channels and Smart/EdgeMixer runtime state.  
**Failure symptom:** UI feels conceptually impressive but controls nothing real or invents a backend that competes with current primary/secondary render semantics.  
**Remediation:** Keep the centre-origin hero strip and selected-surface pattern; rename the scope to `Primary Edge`, `Secondary Edge`, and `Smart Director` only. No zone count, zone layout, per-zone effect, zone blend, or zone preset controls in the SB MVP.

### HIGH-3: Discrete controls are drawn as sliders and duplicated

**Severity:** High  
**Assumption attacked:** Sliders are an acceptable generic touch primitive for all SB controls.  
**Evidence:** The MVP renders `Mode`, `Palette mode`, `Smart Scene`, and `Edge strength` as slider-like rows (`sb-tab5-touch-mvp.html:439-445`), then renders Smart Scene again as a segmented control and EdgeMixer again as mode buttons plus strength (`sb-tab5-touch-mvp.html:451-467`). Existing UX evidence says every parameter gets exactly one home, hidden/duplicate controls confuse source of truth, and control precision must match useful resolution (`touch-only-ux-critique.md:21-33`, `touch-only-ux-critique.md:41-45`).  
**Attack scenario:** A user tries to tap/drag "Mode" or "Smart Scene" and either nothing obvious happens or a discrete state jumps unpredictably.  
**Failure symptom:** Touch UI looks dense but behaves like a sketch; mode changes and Smart states become error-prone under performance conditions.  
**Remediation:** Use lists/segmented controls for enums, steppers or next/previous buttons for mode, toggle for palette mode, and one canonical home per control. Keep continuous sliders only for photons/chroma/mood/strength-style continuous values.

### HIGH-4: Noise calibration and reset are still too close to the operator surface

**Severity:** High  
**Assumption attacked:** A confirmation overlay is enough for calibration/destructive actions.  
**Evidence:** `.claude/CLAUDE.md` forbids auto-firing `start_noise_cal` without Captain-confirmed silence (`.claude/CLAUDE.md:41-47`). Current SB typed `start_noise_cal` prints guidance instead of firing, and the N/Y hotkey path is deliberately guarded (`sb-touch-control-map.md:47`). The proposal still places `NOISE CAL`, `SAVE NOW`, and `RESET` tiles in the health screen (`sb-tab5-zone-composer-proposal.html:1218-1247`).  
**Attack scenario:** A live UI exposes "ARM" during music, an operator confirms through muscle memory, and calibration state is poisoned.  
**Failure symptom:** K1 visual response degrades after a "successful" UI action; the artifact says gated, but the device state is damaged.  
**Remediation:** Remove calibration/reset from MVP. If later restored, require an explicit admin mode, live silence/readiness indicator, typed confirmation text, cooldown, visible result, and a tested refusal path under non-silent audio.

### HIGH-5: The validation gates are mostly paper gates

**Severity:** High  
**Assumption attacked:** Static source maps and desktop HTML are enough to choose implementation direction.  
**Evidence:** Every major input artifact says no build, flash, serial, AP, live WS, browser/device, or hardware-rendered proof was performed (`sb-touch-control-map.md:79-81`, `tab5-controller-map.md:127-130`, `f3-api-map.md:146-148`, `touch-only-ux-critique.md:49-51`, `local/2026-06-07-pipdeck-tab5-source-pass.md:51-66`). The prototype itself admits on-device Tab5 screenshot and SB runtime proof remain separate gates (`sb-tab5-zone-composer-proposal.html:1288-1290`).  
**Attack scenario:** The programme declares design direction "validated" because the artifacts are source-backed and screenshots look good.  
**Failure symptom:** First real Tab5 run exposes unreadable type, bad touch targets, stale UI, broken queue handling, or poor K1 behaviour after firmware work has already started.  
**Remediation:** Define promotion gates before coding: framebuffer/pixel dump, physical Tab5 screenshot, raw touch hit-map, stale-state test, disconnected/reconnect test, command round-trip test, queue overflow/coalescing test, K1 FPS/heap/timing test, and Captain eyes-on light-output judgement.

### MED-1: The mode list is hard-coded and can become unsafe or stale

**Severity:** Medium  
**Assumption attacked:** The first screen can hard-code attractive mode names.  
**Evidence:** The MVP hard-codes mode buttons including Waveform Tempo, Dense Forge, Snapwave, Pulse Prism, Spectrum River 2, Comet, and Bloom Fast (`sb-tab5-touch-mvp.html:413-420`). Current SB evidence says mode IDs/names should come from source-backed commands and disabled modes are skipped by `light_mode_next_enabled()`, so a prototype should not assume every numeric ID is selectable (`sb-touch-control-map.md:31-33`).  
**Attack scenario:** The UI offers modes that are disabled, experimental, renamed, or recently quarantined.  
**Failure symptom:** Touch command appears to work but K1 lands in the wrong mode, refuses the command, or creates a mismatch between UI and light output.  
**Remediation:** Generate mode list from current firmware readback or a checked source snapshot. Show disabled/unavailable states explicitly. No hard-coded production list without a version/hash guard.

### MED-2: Persistence semantics are muddy

**Severity:** Medium  
**Assumption attacked:** "Save delayed" and "persisted" can be shown generically across surfaces.  
**Evidence:** Primary config uses delayed persistence, but secondary state is runtime globals and should not be implied as primary-style persisted (`sb-control-map.md:22-27`, `sb-touch-control-map.md:37-39`, `sb-touch-control-map.md:69`). The proposal shows `SAVE DELAYED`, primary `persisted`, secondary `runtime`, and a `SAVE NOW` action without an implemented current wireless API (`sb-tab5-zone-composer-proposal.html:1074-1095`, `sb-tab5-zone-composer-proposal.html:1110-1113`, `sb-tab5-zone-composer-proposal.html:1229-1235`).  
**Attack scenario:** User changes secondary or Smart state, sees a save affordance, power-cycles K1, and loses the setting.  
**Failure symptom:** Trust breaks because the UI implied persistence that firmware never promised.  
**Remediation:** Split persistence labels by owner: primary delayed save, secondary runtime-only, Smart Scene runtime-only, EdgeMixer runtime-only unless a real persist path is added and tested.

### MED-3: "USB ID OK" is fake authority in a wireless controller

**Severity:** Medium  
**Assumption attacked:** Device identity can be shown with simple status labels.  
**Evidence:** The proposal shows `USB ID OK` on the Smart + Health page (`sb-tab5-zone-composer-proposal.html:1175-1183`). Project doctrine requires exact target identity before flash/upload/device-write operations, using port plus stable hardware identity (`.claude/CLAUDE.md:65-76`), but a Tab5 over AP does not have USB port truth.  
**Attack scenario:** UI suggests the operator is connected to the intended K1 when it only knows an AP IP or stale label.  
**Failure symptom:** Commands hit the wrong device in a multi-K1 or stale-AP environment, or the UI overstates safety.  
**Remediation:** Replace `USB ID OK` with the actual identity source available to the controller: AP SSID/BSSID, chip ID readback, firmware version/hash, and connection age. Never show USB identity unless a serial bridge actually verified it.

### MED-4: The hero strip can become decorative if it is not tied to render truth

**Severity:** Medium  
**Assumption attacked:** A centre-origin light-field visual is automatically operational.  
**Evidence:** The proposal correctly shows 0, 79|80, 159 and a centre marker (`sb-tab5-zone-composer-proposal.html:1016-1033`), but the rendered field is static HTML decoration with plate glow and pulse marker (`sb-tab5-zone-composer-proposal.html:1022-1028`, `sb-tab5-zone-composer-proposal.html:1138-1144`). Current UX evidence warns against decorative/fantasy widgets unless each has a control or state purpose (`touch-only-ux-critique.md:35-47`).  
**Attack scenario:** The visual field looks like live K1 output, but it is not final-byte, AP/VP, or render-state evidence.  
**Failure symptom:** Operator trusts an animation that does not correspond to the physical LGP; debugging light output becomes harder, not easier.  
**Remediation:** Treat the hero strip as one of two explicit modes: `schematic control map` or `live render readback`. If live, feed it from a real status/final-byte/diagnostic surface and show stale/error state.

### MED-5: Touch-only may remove the fast-control advantage the donor system had

**Severity:** Medium  
**Assumption attacked:** Omitting encoders has no interaction cost.  
**Evidence:** Existing Tab5 runtime uses dual M5ROTATE8 units for global, zone, control surface, and preset operations (`tab5-controller-map.md:42-50`, `tab5-controller-map.md:88-93`). Touch-reusable behaviours exist, but Zone Composer fine controls are currently bound to Unit-B deltas and would need replacement touch mappings (`tab5-controller-map.md:95-102`).  
**Attack scenario:** A performance controller becomes slower and less precise because every adjustment requires touch focus, drag, or page switching.  
**Failure symptom:** On-glass UX looks plausible in a static screen but feels worse than serial hotkeys or physical controls during music playback.  
**Remediation:** Prove touch-only with physical hit tests and time-to-action tasks. If it fails, reclassify encoders as optional acceleration rather than pretending touch-only is ergonomically free.

## Minimum Reopen / Promotion Gates

1. **Truth gate:** All live-looking UI labels must be backed by a real source, a stale/error state, and a test that proves fake data cannot look live.
2. **Physical UI gate:** On-device Tab5 framebuffer, screenshot/photo, raw touch hit-map, and text legibility at the real 1280 x 720 surface.
3. **Control gate:** One canonical home per control; enum controls are not sliders; safety-class matrix reviewed before implementation.
4. **Transport gate:** Host serial bridge or AP facade must prove request/response, queue overflow, stale-drop, reconnect, and rate/coalescing behaviour.
5. **Firmware gate:** If AP facade is pursued, prove no render/audio timing regression, no heap churn in render paths, no K1 STA mode, no calibration/destructive bypass, and no production diagnostic leakage.
6. **Product gate:** Captain eyes-on physical K1 judgement after UI commands, not just Tab5 screen proof.

## Required Re-run Commands

Commands used in this pass:

```bash
sed -n '1,220p' /Users/spectrasynq/.codex/skills/thinking-red-team/SKILL.md
sed -n '1,220p' '/Users/spectrasynq/SensoryBridge-main 9/.codex/skills/k1-firmware-change-gate/SKILL.md'
rg -n "sb-tab5-control|TAB5|Tab5|tab5|SB Tab5|control" /Users/spectrasynq/.codex/memories/MEMORY.md
find docs/forensics/sb-tab5-control -maxdepth 4 -type f -print
sed -n '1,220p' .claude/CLAUDE.md
sed -n '1,220p' docs/spec-index.md
sed -n '538,560p' /Users/spectrasynq/.codex/memories/MEMORY.md
sed -n '892,924p' /Users/spectrasynq/.codex/memories/MEMORY.md
/usr/bin/find . -path './.git' -prune -o -path './.pio' -prune -o -type f \( -name 'codebase-map.md' -o -name 'fsm-reference.md' -o -name 'k1-ws-contract.yaml' -o -name 'k1-rest-contract.yaml' -o -name 'progress.md' -o -name 'handoff.md' \) -print
sed -n '1,220p' progress.md
sed -n '1,220p' .claude/handoff.md
wc -l docs/forensics/sb-tab5-control/agents/f3-api-map.md docs/forensics/sb-tab5-control/agents/sb-control-map.md docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md docs/forensics/sb-tab5-control/agents/tab5-controller-map.md docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md docs/forensics/sb-tab5-control/agents/zone-composer-design-history.md docs/forensics/sb-tab5-control/local/2026-06-07-pipdeck-tab5-source-pass.md docs/forensics/sb-tab5-control/local/2026-06-07-source-pass.md docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
sed -n '1,180p' Lightwave-Ledstrip/firmware-v3/docs/reference/codebase-map.md
sed -n '1,180p' Lightwave-Ledstrip/firmware-v3/docs/reference/fsm-reference.md
sed -n '1,180p' Lightwave-Ledstrip/docs/protocol/k1-ws-contract.yaml
sed -n '1,180p' Lightwave-Ledstrip/docs/protocol/k1-rest-contract.yaml
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/agents/sb-control-map.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/agents/sb-touch-control-map.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/agents/tab5-controller-map.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/agents/touch-only-ux-critique.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/agents/zone-composer-design-history.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/agents/f3-api-map.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/local/2026-06-07-source-pass.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/local/2026-06-07-pipdeck-tab5-source-pass.md
awk '{printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/local/2026-06-07-zone-composer-ui-pass.md
/usr/bin/grep -nE '<title|<h[1-6]|button|input|select|textarea|onclick|addEventListener|fetch|WebSocket|api/v1|ws://|connected|offline|API|TODO|calibration|noise|reset|confirm|zone|Zone|Primary|Secondary|Smart|Edge|Palette|Photons|chroma|mood|mode|Mode|status|Status|demo|mock|slider|range|id=' docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html
/usr/bin/grep -nE '<title|<h[1-6]|button|input|select|textarea|onclick|addEventListener|fetch|WebSocket|api/v1|ws://|connected|offline|API|TODO|calibration|noise|reset|confirm|zone|Zone|Primary|Secondary|Smart|Edge|Palette|Photons|chroma|mood|mode|Mode|status|Status|demo|mock|slider|range|id=' docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
awk 'NR>=350 && NR<=510 {printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html
awk 'NR>=960 && NR<=1110 {printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
awk 'NR>=1110 && NR<=1245 {printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
awk 'NR>=1245 && NR<=1342 {printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
awk 'NR>=1380 && NR<=1448 {printf "%6d %s\n", NR, $0}' docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html
git status --short --branch --untracked-files=all
git rev-parse --short HEAD
/bin/ls -l docs/forensics/sb-tab5-control/agents/tab5-sb-ui-adversarial-review.md
```

No build, flash, serial monitor, AP/WS live test, browser screenshot, or physical Tab5 run was performed; this was a read-only adversarial evidence pass.
