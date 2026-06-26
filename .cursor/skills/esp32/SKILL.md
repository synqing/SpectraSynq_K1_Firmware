---
name: esp32
description: |
  Configures ESP32-S3 microcontroller and peripherals for the SensoryBridge K1 firmware.
  Use when: working with ESP32-S3 peripheral setup (I2S, RMT, GPIO, DMA), core affinity assignments, hardware-specific build flags, IDF/Arduino HAL interactions, or diagnosing platform-specific crashes and timing issues.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# ESP32 Skill

ESP32-S3-N16R8 running dual-core at 240 MHz. Core 0 owns the audio pipeline; Core 1 owns visual rendering. The hardware DMA + RMT peripheral model is fundamentally different from a microcontroller with blocking I/O — every peripheral decision has a timing consequence. Misassigning work to the wrong core or blocking on Core 1 will manifest as dropped LED frames or audio glitches.

## Before You Code (REQUIRED)

This skill's content was captured at generation time and MAY be stale. For ANY non-trivial change involving esp32, verify against current docs FIRST:



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

## Key Concepts

| Concept | Usage | Notes |
|---------|-------|-------|
| Core affinity | `xTaskCreatePinnedToCore(..., 0)` audio, `1` visual | Mixing stalls both pipelines |
| I2S DMA buffer | Circular, non-blocking, hardware-driven | Never `memcpy` inside ISR |
| RMT5 | FastLED LED output peripheral | Claimed by FastLED — do not reassign |
| PSRAM (8MB) | Diagnostic pools, effect state | Access via `ps_malloc` / `PSRAM_ATTR` |
| Flash (16MB QIO) | Full firmware + persistent config | OPI mode required for full bandwidth |

## Common Patterns

### Core Pinning

```cpp
// new code to add — audio task pinned to Core 0
xTaskCreatePinnedToCore(
    audio_pipeline_task,
    "AudioPipeline",
    8192,         // stack size — profile before reducing
    nullptr,
    configMAX_PRIORITIES - 1,  // highest priority
    &audio_task_handle,
    0             // Core 0
);
```

### PSRAM Allocation for Large Buffers

```cpp
// new code to add
float* spectrum_history = (float*)ps_malloc(HISTORY_LEN * sizeof(float));
if (!spectrum_history) {
    // PSRAM exhausted — abort, do not fall back to SRAM silently
    ESP_LOGE(TAG, "PSRAM alloc failed for spectrum_history");
    abort();
}
```

### I2S Non-Blocking Read Pattern

```cpp
// new code to add
size_t bytes_read = 0;
i2s_read(I2S_NUM_0, dma_buf, DMA_BUF_LEN * sizeof(int32_t), &bytes_read, 0);
// bytes_read == 0 is normal if DMA buffer not yet filled — never block-wait
```

## See Also

- [patterns](references/patterns.md)
- [workflows](references/workflows.md)

## Related Skills

- **platformio** — build environments, upload guard, flash/erase procedures
- **cpp** — C++17 patterns, RAII in ISR-safe contexts
- **arduino** — Arduino HAL wrappers over IDF primitives
- **fastled** — RMT5 LED pipeline, palette rendering, frame timing
- **cmake** / **ninja** — underlying build toolchain invoked by PlatformIO