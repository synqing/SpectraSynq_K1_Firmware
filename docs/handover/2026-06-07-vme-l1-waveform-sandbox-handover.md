---
abstract: "Handover for the VME Level 1 Waveform-family sandbox. Hardware VMEWT capture is frozen after the 2026-06-07 transport incident; restart from fail-closed transport proof, not survivor-row analysis."
---

# VME Level 1 Waveform Sandbox Handover - 2026-06-07

## Critical Update - VMEWT Hardware Capture Frozen

The first hardware-side VMEWT attempt failed at the transport layer. Canonical incident report:

```text
docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md
```

That report supersedes sandbox claims that VMEWT runtime capture was complete or proof-bearing. The failed lane produced partial survivor rows from a corrupted serial stream: nonzero rejected records, ignored fragments, malformed-token issues, secondary-only coverage, and weak-confidence-only scenarios. Those rows are not runtime proof.

The next valid VME action is not another hardware capture. Reopen VME from a fail-closed transport contract: corrupt-log red tests, strict parser gates, bounded deferred diagnostic records, sequence/length/CRC validation, zero dropped/corrupt/overflow, and paired current-vs-VME final-byte records for modes 7, 8, and 18 on primary and secondary.

## Current Source State

Start from:

- Branch: `wip/audio-saliency-recovery`
- Active handover docs: use the current branch HEAD and verify it with `git rev-parse --short HEAD` before acting.
- Handover creation commit: `0621c36 docs: hand off VME L1 waveform sandbox`
- Clean firmware-source baseline under the handover docs: `13ffe00 docs: record Dense Forge exact flash`
- Handover docs/pointer commits above `13ffe00` are documentation-only; verify with `git diff --name-status 13ffe00..HEAD -- SPECTRASYNQ_K1_FIRMWARE platformio.ini`.
- VMEWT incident authority: `docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md`
- Dense Forge recovery source commit: `a5ce32e fix(vp): restore Dense Forge transport`
- Dense Forge closeout authority: `docs/handover/2026-06-07-dense-forge-closeout.md`
- Working tree status must be rechecked before VME work. A dirty docs-only tree does not change the firmware baseline, but it means the handover file may differ from the committed copy.

The unfinished June 7 dirty lanes were checkpointed separately:

- Quarantine branch: `wip/2026-06-07-unfinished-lanes-quarantine`
- Quarantine commit: `a40bdb8 wip: quarantine unfinished June 7 lanes`
- Contents: primary silence anti-creep, `agc_gated` snapshot plumbing, secondary mode 18 dark-state patch, Tempo Comet guard, VP chroma Phase 2A/2B, trace-dev config flag, runtime evidence, and secondary/Dense Forge diagnostic scripts.

Do not merge or cherry-pick the quarantine branch into VME L1. It exists as recovery storage for unresolved lanes. If the next agent needs to inspect its content, use read-only `git show wip/2026-06-07-unfinished-lanes-quarantine:<path>` or a separate worktree.

## Mission

Continue the VME Level 1 sandbox for the Waveform family with no production behaviour change, but do not touch hardware until the VMEWT transport incident reopen gate is satisfied.

Primary targets:

| Target | Mode ID | Source |
|---|---:|---|
| Waveform Fast | 7 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp` |
| Waveform | 8 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform.cpp` |
| Waveform Tempo | 18 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp` |

The task is to prove whether the Waveform-family visual-memory primitive can be isolated behind a smaller explicit VME port without weakening final LED bytes, centre-origin motion, colour clarity, silence posture, or render timing.

Level 1 is a sandbox/shadow lane. It must not alter default displayed output.

## Why These Modes

These three modes are the right first VME target set because they share the same visual-memory contract:

1. Seed current frame from per-channel history.
2. Fade or drain existing `CRGB16` visual memory.
3. Transport history through a Waveform-family shift path.
4. Inject fresh audio-derived colour/position.
5. Mirror around the centre origin when enabled.
6. Store the result back to channel history.

The modes differ enough to prove generality:

| Mode | Why it matters |
|---|---|
| Waveform Fast | Current preserved fast behaviour, dt-correct transport, explicit idle/reactive fade, palette/chromagram blend. |
| Waveform | Simpler centre-origin Waveform baseline with fixed one-step transport and smoothed peak input. |
| Waveform Tempo | Tempo-phase-locked transport path and the mode 18 secondary-history surface. This must be included, but keep the quarantined secondary-dark patch out of the sandbox unless Captain separately accepts that lane. |

## Read First

Use this read order before any VME work:

1. `.claude/CLAUDE.md`
2. `progress.md`
3. `.claude/handoff.md`
4. `docs/spec-index.md`
5. `docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md`
6. `docs/architecture/visual-event-bus-stage-2-proposal-v0.1.md`
7. `docs/handover/2026-06-07-dense-forge-closeout.md`
8. This handover

On-disk handovers beat claude-mem for current lane state. Use claude-mem only for prior-session recall or if a source-history claim is unclear.

## Hard Boundaries

Do not:

- Patch production effect behaviour in Level 1.
- Touch Dense Forge.
- Touch Scene Policy v2.
- Touch Smart Director.
- Touch Phase 2B, `led_utilities.h`, AGC, calibration, global brightness, or silence thresholds.
- Pull the quarantine branch into the VME branch.
- Add L2 Memory or higher event-bus logic.
- Run serial, flash, erase, or calibration for the sandbox unless Captain explicitly changes scope.
- Run hardware VMEWT capture, tune VMEWT serial cadence/row length, or analyse survivor rows as proof before the incident reopen gate passes.
- Add new heap allocation, `String`, logging, or serial I/O in any render path. Existing `debug_mode` USBSerial paths are pre-existing debt; do not expand them or use them as timing proof.
- Use internal precision as proof. Final LED bytes and Captain-visible output are the proof surfaces.

Do:

- Keep default displayed output byte-identical unless a later promotion gate is explicitly approved.
- Keep all shadow/probe code gated as non-shippable or host-only.
- Preserve centre-origin behaviour at indices 79/80 outward.
- Preserve dual-channel independence.
- Preserve British spelling in docs/comments/logs.
- Write intermediate maps and probe specs to disk before implementation.

## Source Seams

Core dispatch and per-channel state:

- `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h`
  - `LIGHT_MODE_WAVEFORM_FAST == 7`
  - `LIGHT_MODE_WAVEFORM == 8`
  - `LIGHT_MODE_WAVEFORM_TEMPO == 18`
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
  - `RenderChannelState` carries per-channel history, Waveform last colours, smoothed peaks, shift accumulators, frame clocks, and a `ChannelEffectState* effect` pointer.
  - `render_channel()` seeds `leds_16` from `channel.history`, calls the selected effect, then stores `leds_16` back to history for Waveform-family modes.
- `SPECTRASYNQ_K1_FIRMWARE/visual/channel_effect_state.h`
  - Mode 18 per-channel tempo transport state lives in `ChannelEffectState::tempo_scroll_accum` and `ChannelEffectState::tempo_last_ms`.
  - This state is reached through `RenderChannelState::effect`; a VME map that tracks only `waveform_*_primary/secondary` globals misses the mode 18 transport seam.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h`
  - `leds_16_prev`, `leds_16_prev_secondary`
  - `waveform_fast_*_primary/secondary`
  - `waveform_*_primary/secondary`
  - `waveform_hybrid_*_primary/secondary`

Waveform memory operations:

- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp`
  - dt calculation and `VP_WAVEFORM_SHIFT_RATE`
  - reactive floor: `max_waveform_val_raw`, `WAVEFORM_REACTIVE_RAW_MARGIN`, `WAVEFORM_REACTIVE_PEAK_FLOOR`
  - dynamic fade: active fade vs `WAVEFORM_IDLE_FADE`
  - transport: `waveform_shift_upper_half_up()` or `shift_leds_up()`
  - injection: one dot at `waveform_upper_half_source_position()` or `waveform_full_strip_position()`
- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform.cpp`
  - smoothed peak memory
  - chromagram/failsafe colour path
  - dynamic fade
  - fixed one-step transport
  - centre-origin mirror
- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp`
  - tempo-phase transport variant
  - mode 18 history path
  - current baseline source contains older WIP/quarantine header comments; for VME L1, include baseline mode 18 but do not import the `a40bdb8` secondary-dark patch unless Captain reopens that lane.
- `SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h`
  - `waveform_full_strip_position()`
  - `waveform_upper_half_source_position()`
  - `waveform_shift_upper_half_up()`
  - `waveform_shift_outward()`
  - `vp_run_output_probe()` and `vp_probe_dispatch_and_hash()` as probe design precedents.
  - Existing `vp_run_output_probe()` covers Waveform Fast and Waveform, but excludes Waveform Tempo / mode 18. Phase 3 must add or design paired final-byte proof for mode 18 before any VME claim covers the full target set.

## Proposed VME L1 Phases

### Phase 0 - Baseline Packet

Create a disk checkpoint before reading deeply:

- Current git HEAD and branch.
- `git status --short --branch --untracked-files=all`.
- Quarantine branch and commit ID.
- Target mode IDs and source files.
- Statement that no serial, flash, calibration, or production behaviour change is in scope.

Suggested path:

```text
docs/forensics/vme_l1/2026-06-07-waveform-baseline.md
```

### Phase 1 - Read-Only Primitive Map

Map the current mechanism-to-perception chain for modes 7, 8, and 18.

For each mode, record:

- Input signals used: `waveform_peak_scaled`, `max_waveform_val_raw`, `audio_vu_level`, tempo phase/confidence if present, chromagram/palette data.
- Per-channel state touched.
- History seed path.
- Fade/drain path.
- Transport path.
- Injection/write path.
- Mirror/centre-origin path.
- History store path.
- Silence/open-quiet behaviour.
- Final-byte collapse point from `CRGB16` to WS2812 bytes.

Exit gate: no source edited; primitive map reviewed on disk.

### Phase 2 - Shadow VME Port Spec

Define the smallest VME port needed for the Waveform family. Do not implement production behaviour yet.

Candidate operations:

- `seed_from_history(channel_history)`
- `fade(amount)`
- `transport_upper_half(steps)`
- `transport_full_strip(steps)`
- `transport_outward(steps)`
- `inject(pos, colour)`
- `mirror_centre()`
- `store_history(channel_history)`
- `quantise_final_bytes()`

Candidate state formats to compare:

- Current `CRGB16` adapter.
- Compact fixed-state adapter, likely `uint16_t` channel state or `UQ4.12`/`UQ8.8` style storage.
- LUT-assisted fade/quantise adapter only if it keeps render cost below budget.

Exit gate: written spec with adapter contract, metrics, and rejection thresholds.

### Phase 3 - Paired Final-Byte Probe

Build proof before product changes.

Because the first hardware VMEWT lane failed, Phase 3 now starts with transport proof before payload proof:

- Add corrupt-log red tests before trusting any analyser output.
- Make the analyser fail nonzero on any rejected row, issue, unexpected ignored line, marker mismatch, sequence gap, missing coverage, or nonzero transport counter.
- Use a bounded deferred diagnostic pool with sequence, length, CRC, and dropped/corrupt/overflow counters.
- Do not emit CSV/text from render-reachable code.

The paired probe must compare:

```text
current Waveform path -> final GRB bytes
candidate VME path    -> final GRB bytes
```

Required metrics per mode and scenario:

- `mae8`
- `p95_abs8`
- `max_abs8`
- `changed_channel_pct`
- `energy_delta_pct`
- `com_delta_leds`
- `com_slope_delta_pct`
- `trail_half_life_delta_frames`
- `tail_integral_delta_pct`
- `hue_delta_p95`
- `sat_delta_p95`
- `flicker_score`
- `active_pixel_pct`
- `render_us`
- `quant_us`
- `frame_us`
- `heap_delta`

Scenarios:

- Quiet/silence.
- Low-level music.
- Strong kick/onset.
- Dense passage.
- Decay after music stops.
- Palette mode on/off.
- Primary and secondary render passes.

Exit gate: transport is clean, framed, complete, fail-closed, and displayed output remains unchanged. Parseable survivor rows alone are not an exit gate.

### Phase 4 - Sandbox Prototype

Prototype order:

1. Waveform Fast, because it has the clearest dt-correct transport and reactive/idle fade boundary.
2. Waveform, because it is the simpler baseline and should expose whether the port is too specialised.
3. Waveform Tempo, because tempo-locked transport and mode 18 history semantics must be covered before VME can be considered Waveform-family safe.

Implementation must stay in a sandbox/worktree. If concurrent agents are used, follow the VME plan's copy-to-`/tmp` sandbox rule and return data only.

Exit gate: sandbox build/test evidence and diff review. No production promotion.

### Phase 5 - Promotion Gate Package

Only after Phase 3/4 proof:

- Orchestrator applies a minimal reviewed patch to canonical source.
- `pio run -e k1_hardware` passes.
- Production instrumentation boundary passes.
- Captain-visible A/B proves equal or better motion memory.
- Sentinel confirms no regressions in Dense Forge, Waveform Tempo dark posture, and Smart Director routing.

Exit gate: keep/revise/reject. Do not silently promote.

## First Commands For The Next Agent

```bash
cd "/Users/spectrasynq/SensoryBridge-main 9"
git status --short --branch --untracked-files=all
git rev-parse --short HEAD
git log --oneline -8
git branch --list 'wip/2026-06-07-unfinished-lanes-quarantine'
git rev-parse --short wip/2026-06-07-unfinished-lanes-quarantine
git diff --stat -- .claude/handoff.md docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md docs/spec-index.md progress.md
git diff --name-status 13ffe00..HEAD -- SPECTRASYNQ_K1_FIRMWARE platformio.ini
rg -n "LIGHT_MODE_WAVEFORM_FAST|LIGHT_MODE_WAVEFORM|LIGHT_MODE_WAVEFORM_TEMPO" SPECTRASYNQ_K1_FIRMWARE
rg -n "waveform_shift|waveform_full_strip_position|waveform_upper_half_source_position|VP_WAVEFORM_SHIFT_RATE|WAVEFORM_IDLE_FADE" SPECTRASYNQ_K1_FIRMWARE
```

Optional isolated start:

```bash
BASE=$(git rev-parse HEAD)
git worktree add --detach /tmp/k1-vme-l1-waveform "$BASE"
```

For parallel SSA sandboxes, prefer the stricter VME plan rule:

```bash
TIMESTAMP=$(date +%Y%m%d%H%M%S)
cp -R "/Users/spectrasynq/SensoryBridge-main 9" "/tmp/k1_vme_waveform_${TIMESTAMP}"
```

## Expected Output From The Next Agent

The next agent should produce, in order:

1. Baseline packet path.
2. Primitive map for modes 7, 8, and 18.
3. Shadow VME port spec.
4. Paired final-byte probe design.
5. Decision: prototype Waveform Fast first or revise scope.

No firmware patch or hardware capture is expected before those artefacts and the VMEWT transport reopen gate exist.
