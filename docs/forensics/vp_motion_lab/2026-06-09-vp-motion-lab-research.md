---
abstract: "Research and architecture proposal for a standalone VP Motion Lab: a non-shippable K1 visual-pipeline development tool for live, bounded motion-programme testing without recompiling every motion iteration."
---

# VP Motion Lab Research - 2026-06-09

## Verdict

Captain's correction is right: this is not Tab5 wireless work and should not be framed as an AP control extension.

The feasible direction is a standalone **VP Motion Lab**: a non-shippable visual-pipeline harness that lets a host tool compile small motion descriptions into bounded K1 motion programmes, upload them through a dedicated fail-closed transport, render them from the LED task or a dev-gated channel-owned mode, and verify final bytes through VPAB.

The firmware must not parse arbitrary C++/JavaScript or unbounded "motion code" on-device. The safe version is:

1. Host-side authoring syntax.
2. Host compiler lowers that syntax into a compact bytecode or fixed-record `MotionProgram`.
3. K1 validates the programme outside the render path.
4. LED task renders one frame at a time through static state and canonical `show_leds()`.
5. VPAB proves primary and secondary final bytes.

## Current Truth

| Field | Source-backed state |
|---|---|
| Branch | `wip/audio-saliency-recovery`, checked 2026-06-09 |
| HEAD | `a6415f8`, checked 2026-06-09 |
| Worktree | Dirty; many existing firmware, protocol, Tab5, hook, and test changes are present. Treat them as protected. |
| Change class | Research / architecture proposal only. No firmware implementation in this pass. |
| Runtime proof | None in this pass. This document is source research, not a build/upload/device result. |
| Active lane caution | VME hardware capture is frozen by the VMEWT transport incident until fail-closed transport proof exists. See `docs/spec-index.md:21-33` and `.claude/handoff.md:13-20`. |

## Source Authority And Gaps

Required reference docs were checked first where present. Two requested reference files are absent in this checkout:

- `firmware-v3/docs/reference/codebase-map.md` - not found.
- `firmware-v3/docs/reference/fsm-reference.md` - not found.

Protocol docs are present:

- `docs/protocol/k1-ws-contract.yaml:1-17` defines the AP WebSocket transport as `/ws`, with `max_rx_bytes: 384`, `max_tx_bytes: 512`, queue depth 8, and only `hello`, `state.get`, and `control.set`.
- `docs/protocol/k1-rest-contract.yaml:1-9` has `paths: {}` and says REST is not implemented for this control slice.

Therefore AP/REST is not the correct first-class Motion Lab path.

## SSA Consumption Ledger

Subagents were used as context sidecars only. Per `ssa-management`, subagent prose is not proof; decision-critical claims in this document were checked against local source reads.

| SSA | Task | Status | Evidence | Consumed as | Decision impact |
|---|---|---|---|---|---|
| Lagrange | Firmware seams | Received late | `evidence/ssa/vp-motion-lab-20260609/firmware-seams.md` | Provisional context | Added the channel-owned mode option and render-seam tradeoff. |
| Peirce | Harness precedents | Received late | `evidence/ssa/vp-motion-lab-20260609/harness-precedents.md` | Provisional context | Reinforced motion-probe, GDFT, VPAB, and VMEWT transport lessons already checked locally. |
| Meitner | Transport and DSL | Missing at final document pass | `evidence/ssa/vp-motion-lab-20260609/transport-dsl.md` absent | Not consumed | No transport/DSL claim depends on this SSA. |

No subagent output was consumed as verified evidence in this pass because no decisive re-run command was provided and no build/device test was run.

## Existing Firmware Seams

### Main Loop And Render Task Split

The current `.ino` keeps AP/main-loop work separate from the LED render task:

- `.ino:77-79` enforces that AP loop and VP/render task must not share a core for K1 hardware unless a probe override is explicitly defined.
- `.ino:447-480` runs `check_serial(t_now)`, then `sb_k1_wireless_poll(t_now)`, then audio acquisition.
- `.ino:640-664` shows the existing motion-probe pattern: when `mp_active` is true, the LED task calls `motion_probe_render_frame()`, then `show_leds()`, updates `LED_FPS`, yields, and skips the shipping visual roster for that frame.

This is the strongest local precedent for VP Motion Lab: the render task owns frame output while the control path only arms or loads state.

### Effect Dispatch

The normal visual roster flows through:

- `.ino:198-297` `render_lightshow_for_channel(uint8_t mode, RenderChannelState& channel)`.
- `.ino:299-303` `store_render_channel_output(...)`.

That dispatch handles production effects and their per-channel state. VP Motion Lab should not wedge arbitrary programme execution into each existing effect.

There are two valid insertion seams:

1. **Frame-owner harness branch** - best for a volatile standalone lab that must avoid persisted mode IDs and prove upload/render/capture first.
2. **Dev-gated channel-owned light mode** - best once the lab needs normal primary/secondary dispatcher semantics, `RenderChannelState`, `RenderParams`, and channel history.

The wrong seam is AP/serial directly mutating render buffers. Control ingress should load/validate programmes only; the LED task or normal channel dispatcher should render them.

### Show Path

The canonical output path is already reusable:

- `led_utilities.h:757-915` `show_leds()` applies brightness, base coat/UI, clipping, strip scaling, secondary output, quantisation, optional VPAB tick, reverse, and `FastLED.show()`.
- `led_utilities.h:1958-2064` `show_secondary_leds()` handles secondary strip scaling, brightness, incandescent path, quantisation, base coat, reverse, and perf tracking.

VP Motion Lab should render into `leds_16` and `leds_16_secondary`, then call `show_leds()` rather than inventing another output path.

### Current Intro Animation

The current intro animation is useful as a motion-language donor but is not itself live-safe:

- `led_utilities.h:1137-1151` `intro_draw_centre_band(...)` correctly draws mirrored centre-origin bands around indices 79/80.
- `led_utilities.h:1178-1245` `intro_animation()` is a blocking 112-frame loop. It writes sweet-spot PWM, draws both primary and secondary buffers, calls `show_leds()`, and calls `FastLED.delay(2)`.

For live Motion Lab use, the intro must be split into a per-frame renderer. A blocking loop inside the main firmware is the wrong shape for live development.

## Existing Harness Precedents

### Motion Probe

`diag/motion_probe.h` is directly relevant:

- `motion_probe.h:3-11` states it is non-shipping, compile-gated instrumentation for controlled spatio-temporal stimuli without audio input and without touching shipping effects.
- `motion_probe.h:21-32` says it draws directly into `leds_16[]`, reuses `show_leds()`, snapshots contamination-control config, and restores it on exit.
- `motion_probe.h:46-52` records achieved timing rather than trusting requested timing.
- `motion_probe.h:397-407` exposes `motion_probe_render_frame()` as a one-frame-per-call render function called by the LED task.

Shortcoming: the probe currently draws un-mirrored full-strip stimuli (`motion_probe.h:43-44`) and only primary channel. VP Motion Lab must be centre-origin and dual-channel by construction.

### VPAB Capture

VPAB is the correct proof substrate:

- `vpab_capture.h:61-75` defines `VPABBytesPayload`, including final `bytes[LED_COUNT_VALUE * 3]`.
- `vpab_capture.h:77-88` defines `VPABRenderContext`, including primary mode, secondary mode, smart/hook/edge state, and manual owner state.
- `diagnostic_capture.h:24-38` defines bounded diagnostic record slots.
- `constants.h:36-49` bounds diagnostic record count, payload bytes, VPAB cadence, and perf budgets.
- `tests/test_diag_capture_static.py:31-70` asserts render-reachable VPAB functions have no serial, heap, file-system, delay, or `vTaskDelay` calls.
- `tests/test_diag_capture_static.py:81-103` asserts diagnostic capture uses critical sections and preflight checks.

VP Motion Lab should add capture context so lab programme id/version/slot can be associated with VPAB rows. Do not treat host replay as final truth.

### Strict Deferred Transport

The VPAB frame transport is a useful precedent for the new upload protocol:

- `vpab_frame_capture.py:1-6` documents that the capture script sends only colon-framed runtime commands and never sends calibration, erase, factory reset, restore defaults, or noise-cal commands.
- `vpab_frame_capture.py:65-71` enforces colon-framed commands.
- `vpab_frame_gate.py:1-6` explicitly says the parser is fail-closed and that survivor frames plus unexpected fragments are invalid evidence.
- `vpab_frame_gate.py:14-20` defines strict begin/record/chunk/end/error tags.

The same philosophy should be used in reverse for programme upload.

## Why The Existing Serial Gate Is Too Small For Motion Programmes

The normal serial command surface is deliberately conservative:

- `serial_menu.h:2049-2077` defines safety classes and command flags such as `SC_TYPED_ONLY`, `SC_ARM_REQUIRED`, `SC_FORBIDDEN_SINGLE_BYTE`, `CMD_IRREVERSIBLE`, `CMD_DISRUPTIVE`, and `CMD_HARNESS`.
- `serial_cmd_table.def:31-61` is a typed-command safety table, with destructive commands typed-only and no direct hotkeys.
- `serial_menu.h:2426-2446` statically asserts that dangerous/typed-only rows cannot be bound to a single-byte hotkey or both surfaces.
- `serial_menu.h:4328-4383` processes input every 10 ms, reads at most 32 bytes per tick, enters command mode with `:`, and has a 128-byte line buffer.
- `serial_menu.h:2491-2560` parses one command line into a 32-byte command type and 94-byte command data.

This is good for runtime controls. It is too restrictive for uploading full motion programmes if those programmes are sent as one text command.

### Redesign Direction

Do not weaken the existing serial gate.

Add a **separate VPML transport gate** compiled only under a new non-shippable env. The existing `parse_command(...)` should only see small typed commands that operate the transport state machine:

- `:vpml=begin,<session>,<version>,<total_bytes>,<crc32>,<op_count>,<duration_ms>`
- `:vpml=chunk,<session>,<seq>,<offset>,<hex_payload>,<chunk_crc32>`
- `:vpml=commit,<session>`
- `:vpml=play,<slot>`
- `:vpml=stop`
- `:vpml=status`
- `:vpml=capture,<slot>,<seconds>,<every_n>,<bytes|both>`

The line parser remains small because each chunk is small enough to fit the existing 94-byte command-data body. Programme size comes from a validated sequence of chunks, not a single command.

If the 94-byte value limit still proves too tight, introduce a compile-gated raw frame mode entered by a small typed command, for example `:vpml_rx=begin,...`, after which `check_serial(...)` hands bytes to `vpml_transport_feed(...)` until an explicit end frame. That raw mode must be non-shippable, bounded, timeout-protected, and fail-closed. It should not run through the legacy metadata parser.

## Proposed Architecture

### Layers

| Layer | Responsibility | Firmware shape |
|---|---|---|
| Host authoring | Human-friendly motion syntax, examples, preview helpers | Python CLI under `scripts/regression-harness/` |
| Host compiler | Validates syntax, lowers to fixed records/bytecode, calculates CRC | No firmware dependency beyond schema constants |
| VPML transport | Chunked, sequenced, CRC-protected programme upload over USB CDC | Compile-gated serial ingest, no AP dependency |
| Programme validator | Bounds ops, duration, channel targets, colour policy, centre-origin semantics | Runs outside render path |
| Render engine | Executes static `MotionProgram` one frame at a time | LED-task branch or dev-gated channel mode, no heap, no serial, no blocking |
| Evidence | VPAB final bytes and perf telemetry | Existing `ENABLE_VPAB_PROBE` and `ENABLE_VP_PERF_AUDIT` |
| Promotion path | Convert proven programme into native effect code | Separate explicit implementation task |

### Recommended PlatformIO Env

Add a new non-shippable env later:

```ini
[env:k1_vp_motion_lab]
; NON-SHIPPABLE: VP Motion Lab authoring and programme-preview harness only.
extends = env:k1_hardware_harness
build_flags =
    ${env:k1_hardware_harness.build_flags}
    -DENABLE_VP_MOTION_LAB=1
```

This should extend `k1_hardware_harness`, not production. The reason is simple: Motion Lab needs VPAB/perf evidence surfaces and must never land in `k1_hardware`.

### Firmware File Shape

Likely files for a later implementation:

- `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h`
- `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.cpp`
- Optional `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab_protocol.h`
- Optional `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_motion_lab.cpp` for the channel-owned phase.
- `scripts/regression-harness/vp_motion_lab.py`
- `tests/test_vp_motion_lab_static.py`
- `tests/test_vp_motion_lab_protocol.py`

### Render Insertion Options

#### Option A - Frame-Owner Harness Branch

This branch mirrors the motion-probe ownership pattern:

```cpp
#ifdef ENABLE_VP_MOTION_LAB
if (vpml_active()) {
  vpml_render_frame();     // writes primary and secondary working buffers
  vpml_set_vpab_context();  // required because normal render context is skipped
  show_leds();             // canonical output path
  LED_FPS = ...;
  vTaskDelay(1);
  continue;
}
#endif
```

Strengths:

- No new persisted mode ID for the first proof slice.
- Volatile and isolated.
- Directly suitable for intro/motion preview.
- Closest to existing `ENABLE_MOTION_PROBE` harness ownership.

Risks:

- Bypasses `render_lightshow_for_channel(...)`, `RenderChannelState`, and normal primary/secondary copy/restore logic.
- Must set VPAB context explicitly before `show_leds()`.
- Must implement its own primary/secondary contamination snapshot/restore.

Recommendation: use this only for the first built-in preview and transport proof slice.

#### Option B - Dev-Gated Channel-Owned Light Mode

This option adds a Motion Lab mode to the normal dispatch path:

```cpp
} else if (mode == LIGHT_MODE_MOTION_LAB) {
  light_mode_motion_lab(channel.history, *channel.effect);
}
```

Strengths:

- Exercises the real primary/secondary channel dispatcher.
- Reuses channel history and `RenderParams`.
- VPAB context naturally follows the normal render path.
- Better seam for testing candidate effects that might graduate into native effects.

Risks:

- Requires careful append-only mode registration and persisted-mode sanitation.
- Could accidentally leak into Smart Director or production if not guarded.
- Needs static tests to prove production exclusion and mode-table safety.

Recommendation: use this after the frame-owner MVP proves upload, validation, and final-byte capture.

## Motion Programme Model

### Do Not Parse Arbitrary Runtime Code

Parsing arbitrary C++/JS/Lua-style code on the ESP32 would violate the spirit of this firmware:

- Unbounded execution risk.
- Harder 2 ms render-budget proof.
- Heap/parser pressure.
- Harder static testing.
- Easier accidental production leakage.

The firmware should parse a compact bounded programme, not a general language.

### Programme Header

Recommended fixed header:

```cpp
struct VpmlProgramHeader {
  uint32_t magic;          // "VPML"
  uint8_t version;
  uint8_t op_count;
  uint8_t flags;
  uint8_t reserved;
  uint16_t duration_ms;
  uint16_t loop_start_ms;
  uint32_t total_bytes;
  uint32_t crc32;
};
```

### Operation Types

MVP operations should be deliberately small:

| Op | Purpose | Safety rule |
|---|---|---|
| `CLEAR` | Clear primary, secondary, or both | No heap, O(N) bounded |
| `CENTRE_BAND` | Centre-origin band at radius/width | Radius 0..79, mirrored 79/80 outward |
| `EDGE_IMPACT` | Edge hit pulse from both edges | No left-to-right sweep |
| `CENTRE_CATCH` | Return/catch glow at centre | Centre radius only |
| `SWEET_PWM` | Sweet spot PWM envelope | Bounded 0..4096 |
| `FADE` | Apply fixed fade to channel buffer | dt-correct or time-positioned |
| `BLEND_CHANNELS` | Cross-feed primary/secondary with scalar | Static bounded loops |

Later operations can include audio modulation, but only after the pure-motion path is proven.

### Curves

Use curve enums, not user code:

- `LINEAR`
- `SMOOTHSTEP`
- `BOUNCE_OUT_BACK`
- `BOUNCE_EDGE_RETURN`
- `PULSE`
- `HOLD`

The K1 renderer evaluates known curves only. Host syntax can be expressive, but firmware execution stays bounded.

### Colour Policy

Allowed:

- Fixed RGB triples in 0..255 or fixed 0..1000 milli units.
- Named SpectraSynq palette tokens.
- Warm-orange/yellow/cyan/violet brand-aligned schemes.

Rejected:

- Hue-wheel animation.
- Rainbow cycling.
- Any operation that sweeps hue across the strip by default.

### Geometry Policy

All geometry should be centre-relative:

- Radius `0` means centre pair 79/80.
- Radius `79` means physical edges 0/159.
- Draw helpers write both sides symmetrically unless explicitly using an inward edge-converge primitive.

Absolute LED indices should be absent from the MVP authoring language.

## Serial Transport Redesign

### Why A New Gate

The existing gate is optimised for human runtime commands and safety-critical hotkey discipline. VP Motion Lab needs bulk-ish data transfer, resumability, and proof.

The new gate should be designed as a protocol, not as another ad-hoc `else if` command.

### Requirements

| Requirement | Rationale |
|---|---|
| Compile-gated by `ENABLE_VP_MOTION_LAB` | Production exclusion |
| Typed-only command entry | No accidental hotkey upload/play |
| Session id | Reject stale chunks from old attempts |
| Monotonic sequence numbers | Detect drops/reorder |
| Offset and total length | Detect truncation and duplicate writes |
| Per-chunk CRC and final CRC | Detect corruption |
| Static receive buffer | No heap |
| Programme size cap | RAM and parser bound |
| Timeout | Avoid getting stuck in receive mode |
| Explicit commit | Do not render partial programmes |
| Explicit play/stop | Loading is separate from visual output |
| Error state is terminal until reset | Fail-closed |

### Suggested Limits For MVP

These are starting points, not final values:

- Max programme bytes: 1024 or 2048.
- Max ops: 16.
- Max slots: 2.
- Max chunk payload: 32 raw bytes, hex encoded to 64 chars, fits current command-data limit.
- Max programme duration: 5000 ms.
- Max receive session age: 10 seconds.
- Max render loops: bounded repeat count or manual stop.

### Protocol Sketch

```text
:vpml=begin,7,1,384,9A30C2EF,8,1800
VPML_ACK begin sid=7 max_chunk=32

:vpml=chunk,7,0,0,001122...,A1B2C3D4
VPML_ACK chunk sid=7 seq=0 offset=0 bytes=32

:vpml=chunk,7,1,32,8899AA...,A8F0C001
VPML_ACK chunk sid=7 seq=1 offset=32 bytes=32

:vpml=commit,7
VPML_ACK commit sid=7 slot=0 ops=8 duration_ms=1800 crc=9A30C2EF

:vpml=play,0
VPML_ACK play slot=0
```

Any missing chunk, wrong CRC, wrong offset, wrong session, oversize, unsupported version, or validation failure moves the receiver to error state. It should not try to render.

## Host Tool Shape

Create `scripts/regression-harness/vp_motion_lab.py` later.

Responsibilities:

- Compile a small authoring file to VPML bytecode.
- Emit a JSON manifest with programme hash, ops, duration, and safety checks.
- Optionally produce host preview bytes using the same VPAB byte layout.
- Verify K1 identity before upload, following the existing capture script discipline.
- Upload chunks over USB CDC.
- Run `play`, optionally run VPAB capture, then gate captured frames.

Existing host precedent:

- `render_replay.py:1-44` host-compiles real K1 render maths and emits VPABBytesPayload byte layout, but explicitly marks host output as mechanism proof, not measured device proof.
- `render_replay.py:700-750` already supports primary and secondary frame byte outputs.

VP Motion Lab should reuse that proof boundary: host preview is useful for fast iteration, but device VPAB is the truth surface.

## API Design Notes

This is an API even if the transport is USB CDC. Treat it as such:

- Version every programme and wire frame.
- Use nouns and states: `program`, `slot`, `session`, `capture`.
- Keep load, validate, play, stop, and capture as separate verbs.
- Make every response parseable and correlated by session/slot/sequence.
- Never make `play` imply `commit`.
- Never make `commit` imply `play`.
- Never make upload imply persistence.

## Systems / TRIZ / Risk Synthesis

### System Archetype

Current effect development is showing a "fixes that fail" risk: recompiling/flashing for every motion adjustment gives short-term progress but makes iteration slow and encourages broad changes when small motion trials are needed. There is also a "shifting the burden" risk if the answer becomes a pile of one-off serial commands instead of a proper Motion Lab substrate.

### TRIZ Contradiction

Contradiction:

- Need runtime flexibility and fast motion iteration.
- Must preserve deterministic firmware, no heap in render, centre-origin geometry, no rainbows, and strict timing.

Resolution:

- Separate in space: rich authoring on host, bounded execution on K1.
- Separate in time: parse/validate during loading, render only prevalidated records.
- Use an intermediary: bytecode/record compiler.
- Local quality: non-shippable env has capabilities production does not.

### Steel-Man Against VP Motion Lab

The strongest objection is that VP Motion Lab could become a second effect engine that bypasses proper native effects, expands testing burden, and leaks diagnostic complexity into production. It could also make bad visual ideas easier to produce quickly.

The answer is not to make it more powerful. The answer is to make it bounded:

- Non-shippable only.
- Small operation vocabulary.
- Centre-origin DSL.
- No arbitrary code.
- Static tests for production exclusion.
- VPAB capture required before promotion.
- Native effect implementation remains the promotion path.

### Circle Of Competence

Source-backed confidence:

- The LED-task override seam exists.
- The normal primary/secondary dispatch seam exists.
- The canonical show path can be reused.
- VPAB can prove final primary/secondary bytes.
- Current AP WebSocket is not the right transport.
- Current serial line parser is too small for single-command programme upload.

Unproven:

- Exact maximum programme size that can be loaded without AP/audio disturbance.
- Device-side serial throughput under live audio and VPAB capture.
- Whether USB MSC can be safely repurposed for programme staging on this hardware. Current K1 build compiles firmware-update MSC out via `SB_ENABLE_USB_MSC_UPDATE=0`, and LittleFS is persistence/config storage, not a live lab inbox.
- Actual visual quality of a generated programme. Captain eyes-on remains final.

## MVP Slices

### Slice 0 - ADR / Research Closeout

Deliver this document and an implementation ADR. No firmware changes.

Acceptance:

- Captain agrees this is a VP Motion Lab, not Tab5/AP.
- Captain agrees arbitrary code parsing is out of scope for MVP.
- Captain agrees serial transport should be redesigned as VPML-specific ingress instead of weakening the existing safety parser.

### Slice 1 - Per-Frame Intro Renderer Extraction

Refactor the current blocking intro into a pure one-frame function:

```cpp
void vp_intro_render_frame(uint16_t frame, uint16_t frame_count);
```

Rules:

- No blocking loop in the render function.
- No `FastLED.delay(...)` in live preview path.
- Draw primary and secondary buffers.
- Preserve centre-origin bands.
- Keep sweet-spot PWM bounded.

Acceptance:

- Static test proves no delay/blocking in the per-frame renderer.
- Existing boot intro behaviour remains available.
- `pio run -e k1_hardware` passes before any harness upload.

### Slice 2 - Fixed Built-In VPML Programme

Before transport, hardcode one built-in programme equivalent to the intro bounce. Use the frame-owner harness branch first, because it avoids persisted mode registration while proving the Motion Lab control plane.

Acceptance:

- `k1_vp_motion_lab` env builds.
- `:vpml=play_builtin,intro_bounce` or equivalent starts preview.
- LED task branch owns frames while active.
- Primary and secondary both render.
- VPAB context is explicitly set for lab preview frames.
- VPAB capture produces primary and secondary final bytes.

### Slice 3 - Chunked VPML Transport

Add `begin/chunk/commit/play/stop/status`.

Acceptance:

- Unit/static tests cover truncation, wrong CRC, wrong seq, wrong offset, oversize, unsupported version, and timeout.
- Existing serial hotkey safety tests still pass.
- Production env excludes `ENABLE_VP_MOTION_LAB`.
- No heap/serial/filesystem/delay calls in render-reachable VPML functions.

### Slice 4 - Channel-Owned Mode Decision

Move from pure frame-owner preview into a dev-gated channel-owned mode only if the lab needs to test candidate effect behaviour under normal primary/secondary channel semantics.

Acceptance:

- Append-only mode registration is statically tested.
- Smart Director does not auto-select the lab mode.
- Production env excludes lab command surfaces and sources unless Captain explicitly approves a separate path.
- `render_lightshow_for_channel(...)` dispatches the lab mode only under the dev flag or rejects it cleanly in production.

### Slice 5 - Host Compiler

Add Python compiler and uploader.

Acceptance:

- Host compiler rejects absolute LED sweeps and rainbow/hue-wheel operations.
- Host compiler emits manifest and binary/hex programme.
- Device upload verifies chip identity before sending.
- Host tool writes capture evidence and runs strict gates.

### Slice 6 - Audio Modulation And Programme Promotion

Only after pure motion is stable:

- Add bounded audio modulation inputs such as beat phase, onset strength, and tempo confidence.
- Promote successful programmes into native effects or intro variants.

Acceptance:

- Runtime proof separates host preview, device final bytes, and Captain eyes-on judgement.

## Tests And Gates

### Static Tests

Required:

- Production env excludes `ENABLE_VP_MOTION_LAB`.
- New env is labelled `NON-SHIPPABLE`.
- VPML command surface is compile-gated.
- VPML commands are typed-only and carry `CMD_HARNESS`.
- No heap, `String`, filesystem, serial, delay, or `vTaskDelay` in render-reachable VPML functions.
- Programme validator rejects absolute sweeps, oversized ops, unsupported versions, bad CRCs, and hue-wheel/rainbow primitives.
- Centre-origin helpers write mirrored indices around 79/80.

### Host Tests

Required:

- Compile one programme to deterministic bytes.
- Recompile same programme to identical hash.
- Invalid programmes fail closed.
- Chunked upload stream model catches missing chunks, duplicate seq, reorder, CRC mismatch, and truncated final commit.

### Device Gates

Required before calling the tool usable:

- Verify port and chip id.
- Build `k1_vp_motion_lab`.
- Upload intended non-shippable env.
- Load programme.
- Play programme live.
- Capture VPAB bytes for both primary and secondary.
- Gate zero dropped/corrupt/overflow.
- Record perf budget with `ENABLE_VP_PERF_AUDIT`.
- Captain eyes-on confirms the motion feels useful.

## Open Decisions For Captain

1. Authoring syntax preference: minimal JSON, compact YAML, or small purpose-built `.vpml` syntax.
2. Whether MVP programmes should be volatile-only. Recommendation: volatile-only.
3. Whether live preview pauses the normal visual roster. Recommendation: yes for MVP.
4. Whether to include audio modulation in MVP. Recommendation: no.
5. Whether to target only intro/motion development first or general effect sketching. Recommendation: intro/motion first, then broaden.

## Recommendation

Proceed with VP Motion Lab as a strategic VP tool, but keep the first implementation boring and bounded:

1. Do not touch Tab5/AP.
2. Do not loosen the existing serial safety gate.
3. Add a non-shippable `k1_vp_motion_lab` env.
4. Extract the intro bounce into a per-frame renderer.
5. Prove a built-in dual-channel programme first.
6. Then add chunked USB CDC upload with sequence/CRC/commit.
7. Decide whether the second phase should be a channel-owned `LIGHT_MODE_MOTION_LAB`.
8. Use VPAB as the measured device proof path.

This gives Captain fast visual iteration without turning the ESP32 into an unsafe runtime interpreter.
