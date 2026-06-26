---
name: cpp
description: |
  Develops firmware in C++17 with modern features for the SensoryBridge K1 ESP32-S3 platform.
  Use when: writing or modifying DSP modules, effects, audio pipeline components, or any .cpp/.h firmware file; refactoring existing C++ patterns; debugging undefined behavior, memory issues, or timing regressions; adding new light effects; integrating with FastLED, Goertzel, or the AudioSemanticState spine.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# C++ Firmware Skill

C++17 on ESP32-S3 Xtensa dual-core at 240 MHz with strict latency budgets (<50ms audio-to-LED). The architecture is subordinate to perceptual impact—audio correctness and visual responsiveness come before code elegance. Core 0 owns the audio pipeline; Core 1 owns rendering. Cross-core state passes through `AudioSemanticState` (published via `sb_audio_snapshot`), never through raw globals.

## Before You Code (REQUIRED)

This skill's content was captured at generation time and MAY be stale. For ANY non-trivial change involving cpp, verify against current docs FIRST:



Then:

1. **Match the installed version.** Cross-reference against the version installed in this repo. APIs change across minor versions; do not assume.
2. **Discover provider best practices.** If the task touches a production-sensitive capability, inspect the provider service catalog, official docs, and project docs before choosing an implementation.
3. **Respect explicit direction.** If the user explicitly asks for a specific mechanism, follow it. If project docs clearly mandate a mechanism, follow the project. In both cases, mention the provider-recommended alternative and make the chosen path safe.
4. **Prefer provider-native primitives by default.** If no explicit user/project override exists and the change involves caching, rate limiting, background work, scheduled jobs, shared state, queues, or secrets, use the provider-recommended binding/API. Do not hand-roll an in-memory or polyfill solution that "works" locally but breaks under the provider's execution model — derive the need→native-primitive mapping yourself from this provider's docs.

## Skill Advantage Protocol

Using this skill should produce a meaningfully better result than an unskilled baseline. Apply this loop before and during implementation:

1. **Clarify only when it changes the outcome.** Ask the smallest useful set of questions when the request is ambiguous, preference-heavy, or could change architecture, user-visible behavior, data shape, security posture, analytics, or external side effects. If the safe assumption is obvious, state it and proceed. When asked to surface data that no existing code path captures, state up front the assumption that capture starts now (no backfill) or ask if a backfill source exists — do not silently build net-new storage without surfacing this.
2. **Inspect the nearest real patterns.** Read adjacent files, routes, components, tests, schema, infra, copy, and analytics surfaces before inventing structure. Treat local conventions as the starting point.
3. **Optimize the task's highest-leverage axis.** Identify what would make the result win a review: user-visible correctness, integration quality, accessibility, security, reliability, maintainability, operability, or speed of future change.
4. **Reuse before reimplementing.** Prefer existing components, hooks, helpers, formatting/utility functions, data registries, metadata builders, analytics, pricing, checkout, auth, routing utilities, and API procedures/endpoints/data sources over local one-off clones. Before adding a new API procedure, query, or data fetch, search for one that already returns this data and extend it in place — a surface that fetches data and only logs or partially uses it is a reuse target, not an absent one; never author a parallel endpoint or leave the original orphaned. Before importing for a data fetch, grep the screen for the call it already makes and reuse that exact client/singleton import path and endpoint/procedure name; never create a second client, transport, or parallel endpoint for data an existing call returns, and confirm every imported path and symbol actually exists in the repo before writing it.
5. **Use semantic structures.** Tables, lists, forms, buttons, links, headings, and disclosure controls should use native/project accessible primitives instead of div-only lookalikes.
6. **Prevent drift by construction.** Centralize repeated facts, labels, claims, product defaults, and shared table cells in registries or helpers when multiple surfaces need the same answer.
7. **Synthesize, do not merely comply.** Combine this skill's guidance with repo evidence and the user's goal. When two good approaches exist, borrow the strongest parts of each instead of blindly choosing one.
8. **Check claims against code.** Product copy, docs, and comments must not imply automation, integrations, performance, security, refresh cadence, counts, or data flow that the implementation does not actually provide. Any claim that one component writes, records, updates, calls, or is the source of truth for another is allowed only if the edit performing it is in this same change; before finishing, check each such cross-component claim against the actual edits and downgrade unbacked ones to an explicit TODO or implement them now.
9. **Ship the complete slice.** Include every adjacent artifact needed for the change to be usable and maintainable: wiring, state handling, validation, analytics, tests, docs, migrations, or infra when those surfaces are part of the behavior. When the task shows, displays, or lists user data, deliver the full vertical slice and do not stop at an internal/API/CLI layer: the data-model/schema change AND its migration (a schema change without a migration is incomplete), the path that writes or populates the data, an authenticated endpoint scoped to the current user, and the primary user-facing surface wired through the project's typed data client. Before declaring done, trace one record end-to-end (triggering event → write → read → render); if any hop exists only in a comment or docstring rather than edited code, the slice is NOT done. Shipping only the persistence layer (a schema/migration with no writer, reader, or surface) is an incomplete slice, not a milestone.

## Capability Contract

Use this section when the user prompt touches production risk, even if the prompt does not name this technology explicitly.




Required wiring surfaces:
- provider/runtime configuration discovered during implementation
- nearest typed request/context boundary
- handler/procedure boundary before external side effects

Side-effect barrier:
- Place guards before external APIs, auth mutations, email sends, analytics events, storage writes, and database mutations.


Fallback policy:
- Prefer provider-native/platform-managed primitives by default when no explicit override exists.
- Follow clear user/project overrides, but mention the native alternative and tradeoff.
- Fallbacks must be durable, multi-instance safe, and atomic under concurrency.

Verification rules:
- [error] native-or-explicit-override: Use the provider-native primitive first unless the user/project explicitly overrides it.
- [error] atomic-fallback: Fallback counters must be atomic under concurrency.

## Quick Start

### Existing Pattern — Publishing Audio State

```cpp
// SENSORY_BRIDGE_FIRMWARE/audio/sb_audio_snapshot.cpp
// AudioSemanticState is the cross-core publish boundary
AudioSemanticState snapshot;
snapshot.tempo_bpm      = sb_tempo.bpm;
snapshot.beat_confidence = sb_tempo.confidence;
snapshot.chord_root     = chord_state.root;
publish_audio_snapshot(snapshot);  // atomic write, Core 1 reads
```

### New Effect Pattern

```cpp
// new code to add — SENSORY_BRIDGE_FIRMWARE/effects/light_mode_my_effect.cpp
#include "globals.h"
#include "sb_audio_snapshot.h"

void render_my_effect(CRGB* leds, uint16_t num_leds) {
    const AudioSemanticState& s = get_audio_snapshot();
    // SPATIAL beat reactivity only — motion through the strip, never global brightness pulse
    uint8_t phase = (s.beat_phase_norm * num_leds) & 0xFF;
    // ... fill leds based on phase
}
```

## Key Concepts

| Concept | Rule | Why |
|---------|------|-----|
| Core affinity | DSP only on Core 0; rendering only on Core 1 | Concurrent access to I2S DMA and RMT is undefined |
| AudioSemanticState | Only sanctioned cross-core boundary | Raw global sharing causes tearing at 133 Hz |
| The Strobe Law | Beat → spatial/transport motion, NEVER global amplitude pulse | Full-field flicker causes eye fatigue and disqualifies the effect |
| `#ifndef SB_*_V2` guards | Legacy paths kept under guards, V2 active by default | Rollback without revert; see forward-graft ledger |
| Gate discipline | Build + pytest must be green before commit | Never commit while gates are broken |

## Common Patterns

### Guard Clauses Over Deep Nesting

**When:** Any effect render function with multiple audio conditions.

```cpp
void render_tempo_river(CRGB* leds, uint16_t n) {
    const AudioSemanticState& s = get_audio_snapshot();
    if (s.beat_confidence < 0.60f) { fill_solid(leds, n, CRGB::Black); return; }
    if (s.tempo_bpm < 40.0f)       { return; }
    // confident beat path only
}
```

## See Also

- [patterns](references/patterns.md)
- [workflows](references/workflows.md)

## Related Skills

- See the **platformio** skill for build environments, flags, and upload guards
- See the **esp32** skill for peripheral configuration (I2S, RMT, GPIO)
- See the **fastled** skill for palette, colour math, and WS2812B rendering patterns
- See the **pytest** skill for the host regression harness