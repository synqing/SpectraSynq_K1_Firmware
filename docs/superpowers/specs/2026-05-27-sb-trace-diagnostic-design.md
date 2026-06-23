---
abstract: "Design spec for a production-clean SensoryBridge trace and diagnostic architecture: SB-native diagnostics remain canonical, while MabuTrace is a mandatory developer-only escalation tool for timeline/causality questions and never ships in production firmware."
---

# SB Trace Diagnostic Design

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Source precedent | `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3` |
| Status | Approved design direction by Captain; implementation guardrails in progress, not committed. |
| Production invariant | Developer and instrumentation code never ships with production firmware. |
| MabuTrace invariant | Mandatory developer-only escalation for timeline/causality questions; never a production dependency. |
| First implementation target | Trace/diagnostic architecture and enforcement guards, not visual behaviour. |

## Doctrine Gate

Relevant doctrine rules:

- Product success is judged at the far end of the chain: what the K1 owner perceives musically and visually.
- Architecture, tracing, and diagnostics are subordinate to perceptual impact and musical relevance.
- Compile/upload is not runtime proof.
- No heap, blocking serial, `String`, or unbounded work is allowed in render-path code.
- Calibration and silence-window commands are out of scope for this lane.
- Developer code and instrumentation must never ship in production firmware.

K1 evidence touched:

- [FACT] firmware-v3 wraps MabuTrace behind `FEATURE_MABUTRACE`; disabled builds compile `TRACE_*` macros to no-op stubs in `firmware-v3/src/config/Trace.h`.
- [FACT] firmware-v3 isolates MabuTrace to trace-specific PlatformIO environments in `firmware-v3/platformio.ini`.
- [FACT] firmware-v3 documents MabuTrace as GPL-3.0 and explicitly forbids release distribution of trace-enabled binaries in `docs/DEPENDENCY_LICENSES.md`.
- [FACT] SensoryBridge currently has a static `diagnostic_capture` substrate with critical-section protected pool state and overflow counters.
- [FACT] SensoryBridge currently has VPAB deferred capture and drain through `vpab_capture`, with render-adjacent capture separated from serial output.

North-star impact:

- Protects visual/musical output from diagnostic distortion.
- Gives agents a repeatable way to prove whether a mechanism materially contributes to perceived value.
- Lets future visual-memory experiments isolate timing, byte output, and perceptual evidence without turning the production firmware into a lab build.

Re-test triggers crossed:

- Build configuration and release/harness separation.
- Render-adjacent diagnostic capture.
- Serial command tooling.
- Runtime performance gates.
- Developer-only trace dependency management.

Proof required:

- `pio run -e k1_hardware` is necessary compile proof only.
- Production exclusion requires static build-graph proof plus artifact inspection: resolved source filter, resolved `lib_deps`, resolved build flags, `default_envs`, and binary/symbol/string scans must show no MabuTrace, trace-dev, `diagnostic_capture`, `vpab_capture`, `SB_TRACE` runtime bridge, trace command surface, or developer-only instrumentation payload.
- Harness build proves diagnostic code remains bounded and compile-gated.
- Static guard tests prove MabuTrace cannot enter production build configuration unnoticed.
- Static tests prove no serial/heap/String in render-reachable diagnostic functions.
- K1 runtime matrix proves diagnostic pool health: dropped/corrupt/overflowed all zero.
- K1 runtime matrix separates diagnostic overhead from visual-pipeline budget.

Explicit non-goals:

- No visual engine change in this design.
- No CRGB16, SQ15x16, FastLED, or visual-memory replacement in this design.
- No calibration, NVS, WiFi, AP/STA, API, or effect-behaviour change.
- No production dependency on MabuTrace.
- No treatment of MabuTrace as optional lore that agents may ignore when scalar diagnostics are insufficient.
- No git checkpoint is required for this design-only task. Implementation work may create tested/reviewed branches, commits, or tags as rollback checkpoints.

## Decision

Adopt a **production-clean hybrid trace architecture**:

1. SensoryBridge-native diagnostic capture remains canonical.
2. MabuTrace is a mandatory developer-only escalation tool for timeline/causality questions.
3. MabuTrace is not a default dependency and never enters a shippable firmware binary.
4. The production environment must exclude developer trace dependencies and must not depend on diagnostic code for product behaviour.

This rejects a direct MabuTrace port as the canonical substrate. The reason is not capability; for nested timeline profiling, MabuTrace is superior to scalar counters. The reason is product and release hygiene: MabuTrace is GPL-3.0 in the firmware-v3 precedent, trace binaries are not shippable, and product-proof diagnostics must not depend on a developer-only library.

## Canonical Vs Escalation Tool

SB-native diagnostics are canonical for:

- product-proof evidence;
- VPAB and final-byte payloads;
- visual-memory candidate gates;
- diagnostic pool health;
- parser-compatible forensic logs;
- any evidence surface that should survive as a reusable internal harness.

MabuTrace is mandatory for escalation when the unknown is:

- nested timing inside a frame;
- cross-core or audio-to-render causality;
- disagreement between scalar counters such as `render_us`, `frame_us`, `over`, and stage timers;
- frame-drop causality;
- whether a diagnostic harness is perturbing the runtime it is measuring;
- proof that two events overlap, race, or reorder in time.

This is not optional. Before any timing, performance, dropped-frame, race, ordering, audio-to-render, or cross-core diagnostic claim, the agent must classify the question as timeline/causality or non-causal scalar evidence. If any listed timeline/causality trigger applies, MabuTrace dev-trace is required. SB-native scalar diagnostics may detect or quantify the symptom; they do not close causal attribution. If the trace-dev lane is unavailable, the correct status is `blocked` or `approval`, not verified, complete, or scalar-equivalent.

## Architecture

### Build Lanes

| Lane | Purpose | Diagnostic code | MabuTrace | Shippable |
|---|---|---|---|---|
| `k1_hardware` | Production firmware | No implementation sources, storage, command surfaces, dependencies, or feature flags | Forbidden | Yes |
| `k1_hardware_harness` | Internal diagnostic harness | Enabled by explicit flags | Forbidden | No |
| `k1_hardware_trace_dev` | Mandatory escalation lane for internal timeline questions | Enabled by explicit flags | Allowed only in this non-shippable lane | No |

Release rule:

- Any build that includes MabuTrace or trace-only instrumentation is non-distributable.
- Any build whose visual behaviour relies on diagnostic code is invalid.
- Production firmware must not compile or link developer, harness, trace, benchmark, probe, VPAB, diagnostic-capture, or MabuTrace implementation sources. Production may contain only audited no-op macro declarations required to keep shared source buildable; no instrumentation object file, serial command surface, storage, dependency, feature flag, or behaviour may be present in the production build graph.
- `k1_hardware_harness` must not include MabuTrace by flag, dependency, include, or inherited environment. Use `k1_hardware_trace_dev` for timeline/causality escalation.
- If a trace-dev env is introduced, its comments and tests must label it `non-shippable`.

### Timing Domains

| Domain | Allowed | Forbidden |
|---|---|---|
| Render/audio hot path | Fixed-size record push, timestamp read, one-frame toggle snapshot, integer counters | Serial I/O, heap allocation, `String`, file I/O, unbounded loops, blocking waits |
| Command/drain path | Serial formatting, parser-compatible dumps, reset/status, host-readable summaries | Visual mutation, calibration, hidden NVS persistence |
| Host tooling | Parsing, gating, JSON/CSV/Markdown reports, comparisons, Perfetto handoff for dev traces | Runtime product dependence |

## Components

### `sb_trace.h`

Purpose:

- Provide a single local macro surface for trace instrumentation.
- Compile to no-ops in production.
- Avoid direct MabuTrace imports outside the wrapper.

Proposed primitives:

```cpp
SB_TRACE_SCOPE("name")
SB_TRACE_COUNTER("name", value)
SB_TRACE_INSTANT("name")
SB_TRACE_MARKER(kind, value)
SB_TRACE_IS_ENABLED()
```

Production behaviour:

- All macros compile to `do {} while (0)` or equivalent.
- Counter arguments may be consumed only enough to avoid warnings.
- No storage, serial, or dependency is linked.

Harness behaviour:

- `SB_TRACE_*` can push compact diagnostic records into `diagnostic_capture`.
- Text formatting remains command-path only.

Trace-dev behaviour:

- `SB_TRACE_*` may bridge to MabuTrace only inside `k1_hardware_trace_dev`.
- No other source file may include `<mabutrace.h>` directly.
- The trace-dev lane is mandatory when timeline/causality evidence is required and SB-native diagnostics cannot answer it.

### `diagnostic_capture`

Purpose:

- Remain the canonical static capture pool.
- Store typed binary records.
- Track health counters for proof gates.

Required properties:

- Fixed compile-time capacity.
- Critical-section protected pool state.
- No dynamic allocation.
- No serial output in push functions.
- Explicit states: stopped, capturing, frozen, draining.
- Failure counters: captured, dropped, corrupt, overflowed, high-water.

This component is already partially present and should be hardened rather than replaced.

### `bench_registry`

Purpose:

- Port firmware-v3's useful A/B toggle pattern into SB without importing firmware-v3's product architecture.
- Let experiments switch mechanisms at runtime while preserving hot-path safety.

Rules:

- Toggle descriptors live in a fixed-size registry.
- Backing values are static `volatile bool`.
- String lookup happens only on the serial command path.
- Render/audio consumers read the toggle once per frame/tick into a local bool.
- Production defaults must equal shipping behaviour.
- Any toggle that can alter visible output must be harness-only until promoted by perceptual evidence.

Initial candidate toggles:

| Toggle | Default | Scope |
|---|---:|---|
| `diag.vpab` | off | Enable VPAB capture path in harness only |
| `diag.trace_counters` | off | Enable compact trace counters in harness |
| `vp.memory_candidate` | off | Future visual-memory A/B candidate, not part of first implementation |
| `vp.fastled_native_path` | on | Future FastLED comparison switch, not part of first implementation |

### Serial Commands

All machine-driven commands must remain colon-framed.

Initial command surface:

| Command | Meaning |
|---|---|
| `:diag=status` | Print diagnostic pool health |
| `:diag=clear` | Clear diagnostic pool |
| `:trace=status` | Print trace layer status and build lane |
| `:trace=reset` | Clear trace records |
| `:trace=start[,N]` | Capture every Nth eligible event/frame |
| `:trace=stop` | Freeze trace capture |
| `:trace=dump` | Drain trace records after capture stops |
| `:bench=list` | List registered toggles |
| `:bench=toggle,<name>,<on|off>` | Change a registered toggle |
| `:bench=reset` | Restore defaults |

Serial policy:

- No calibration command is introduced or called by this lane.
- No raw hotkey automation is used by host tooling.
- Dump commands must fail if capture is still active unless a command explicitly freezes first.

### Host Tooling

Required scripts:

- `scripts/regression-harness/sb_trace_capture.py`
- `scripts/regression-harness/sb_trace_gate.py`

Capture tool requirements:

- Opens serial exclusively.
- Sends only colon-framed commands.
- Refuses calibration/silence-window commands.
- Writes raw logs plus parsed summaries.
- Records command sequence in the output file.

Gate tool requirements:

- Separates diagnostic substrate health from visual-pipeline performance.
- Fails on diagnostic dropped/corrupt/overflowed.
- Treats self-shadow records as instrumentation smoke unless an explicit smoke flag is passed.
- Does not conflate visual-memory proof with byte-identity proof.
- Emits JSON for machine comparison.

## Data Flow

```text
render/audio code
  -> SB_TRACE_* or VPAB capture hook
  -> diagnostic_capture fixed record pool
  -> frozen by serial command
  -> command-path drain
  -> host capture script
  -> offline gate/analyser
  -> forensic evidence file
```

No production visual output may depend on any step after the first arrow.

## Error Handling

Firmware-side:

- Full pool increments `dropped` and `overflowed`; it does not block.
- Invalid payload increments `dropped` and `overflowed`; it does not write partial records.
- Drain while capturing returns an error packet and leaves capture state unchanged.
- Unknown commands go through the existing bad-command path.

Host-side:

- Missing diagnostic summaries fail the gate when a diagnostic run was requested.
- Nonzero dropped/corrupt/overflowed fails the diagnostic substrate gate.
- Missing VPAB rows fail only the VPAB-specific gate, not generic trace capture.
- A port-open failure reports the owning process when possible.

## Verification Gates

### Static Gates

- Production build graph has no diagnostic implementation sources, storage, serial command surfaces, developer-only feature flags, MabuTrace dependency, or trace-dev bridge.
- No direct `<mabutrace.h>` include outside `sb_trace.h`.
- Render-reachable trace/diagnostic functions contain no `USBSerial`, `Serial`, `String`, `malloc`, `new`, `delete`, or filesystem calls.
- Toggle hot-path use is a single static/volatile read or local snapshot.

### Build Gates

Required:

```bash
pio run -e k1_hardware
pio run -e k1_hardware_harness
```

These builds prove compilation only. They do not prove production exclusion without the static build-graph and artifact-inspection gates above.

Mandatory when the active investigation requires timeline/causality proof and the trace-dev lane has been implemented:

```bash
pio run -e k1_hardware_trace_dev
```

### Runtime Gates

Diagnostic substrate gate:

- Capture window emits no live trace/VPAB rows.
- Deferred dump emits parser-compatible rows.
- `dropped=0`, `corrupt=0`, `overflowed=0`.
- `VPF over=0`, `VPF dropped=0`.
- Frame time remains under the 120 FPS envelope.

Visual-pipeline budget gate:

- Stage-level render timing is evaluated separately from diagnostic health.
- `render_us` must be named according to what it measures: primary effect only, secondary effect only, or dual-channel pre-show aggregate.
- Any `<= 2.0 ms` claim must identify the measured stage and source field.

Visual-memory proof gate:

- Self-shadow byte identity is smoke only.
- Candidate-vs-current proof requires real memory metrics: trail half-life, tail integral, fractional movement, centre-origin propagation, low-level persistence, and byte-sequence smoothness.
- Proof must link metric movement to plausible perceived benefit before promotion.

## Rollout Slices

### Slice 1: Spec and Guards

- Add this spec.
- Add static guard tests for production/developer separation.
- Do not alter firmware behaviour.

### Slice 2: SB Trace Wrapper

- Add `sb_trace.h` no-op wrapper.
- Add tests proving production no-op behaviour and direct MabuTrace include ban.
- No MabuTrace dependency.

### Slice 3: Bench Registry

- Add fixed toggle registry.
- Wire serial command path only.
- Add one inert diagnostic toggle to prove mechanics.
- No visible behaviour changes.

### Slice 4: Trace Records

- Add generic trace record kinds to `diagnostic_capture`.
- Add `:trace=*` command surface.
- Add host capture/gate scripts.

### Slice 5: MabuTrace Dev Escalation Env

Implement when a timing/causality investigation first requires it, or when Captain explicitly asks for the trace-dev lane:

- Add `k1_hardware_trace_dev`.
- Add MabuTrace dependency to that env only.
- Add licence warning comments beside the env.
- Add gate proving production env remains dependency-clean.
- Add capture/runbook instructions that tell agents exactly when to escalate to this lane.

## Acceptance Criteria

This design is complete when:

- The spec is reviewed by Captain.
- A follow-on implementation plan exists.
- The implementation plan keeps production, harness, and mandatory-but-dev-only trace lanes separate.
- Every diagnostic feature has a proof gate showing it cannot ship by accident.
- No production behaviour is changed without separate perceptual-impact approval.

## Changelog

| Date | Change |
|---|---|
| 2026-05-27 | Initial approved design spec written from firmware-v3 trace precedent and current SB diagnostic substrate evidence. |
| 2026-05-27 | Tightened MabuTrace from optional developer tool to mandatory developer-only escalation lane for timeline/causality questions. |
