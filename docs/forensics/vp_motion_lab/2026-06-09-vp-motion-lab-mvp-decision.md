---
abstract: "Decision record for the narrowed VP Motion Lab MVP implementation: non-shippable, frame-owner built-in preview first, no upload transport or runtime code execution."
---

# VP Motion Lab MVP Decision - 2026-06-09

## Status

Accepted for the first implementation pass.

This record narrows the broader research in `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md`. The research artefact remains preserved as the broader architecture map; this decision record is the implementation boundary for the current MVP.

## Decision

VP Motion Lab starts as a non-shippable K1 VP frame-owner harness, not as Tab5, AP, REST, WebSocket, wireless, Smart Director, audio, persistence, or production firmware work.

The first implementation pass is limited to:

1. Extracting the boot intro drawing body into `vp_intro_render_frame(frame, frame_count)`.
2. Keeping the existing blocking `intro_animation()` boot wrapper available.
3. Adding `k1_vp_motion_lab`, a `NON-SHIPPABLE` PlatformIO env extending `k1_hardware_harness`.
4. Adding a compile-gated LED-task frame-owner branch under `ENABLE_VP_MOTION_LAB`.
5. Adding one built-in dual-channel programme, `intro_bounce`.
6. Rendering through existing primary and secondary buffers.
7. Calling canonical `show_leds()`.
8. Setting explicit VPAB context before `show_leds()` so final-byte captures report VPML as the effective owner for primary and secondary.
9. Adding source-contract tests that prove production exclusion and render-path purity.

## Explicit Non-Goals

- No Tab5 changes.
- No AP, REST, WebSocket, or wireless changes.
- No weakening of the existing serial parser or safety gate.
- No chunked programme upload.
- No raw receive mode.
- No host compiler.
- No arbitrary runtime code, scripts, eval, or bytecode interpreter.
- No channel-owned production light mode.
- No audio modulation.
- No persistence or NVS programme storage.
- No Smart Director integration.

## Rationale

The first bottleneck is live visual iteration and proof, not a full programme language. A frame-owner built-in preview is the smallest slice that exercises the real K1 LED buffers, secondary output path, canonical `show_leds()`, and VPAB final-byte proof without opening a broad transport or code-execution surface.

This keeps the change reversible and reviewable. If the built-in preview proves useful on hardware, a later pass can design programme transport from the research document under a separate fail-closed protocol gate.

## Acceptance Boundary

- `k1_hardware` builds and does not resolve `ENABLE_VP_MOTION_LAB`.
- `k1_vp_motion_lab` builds and is labelled `NON-SHIPPABLE`.
- Existing boot intro behaviour remains available through `intro_animation()`.
- `vp_intro_render_frame()` has no blocking animation loop, `show_leds()`, `FastLED.delay`, heap allocation, `String`, serial output, filesystem access, or `vTaskDelay`.
- The VPML branch renders primary and secondary buffers, sets VPAB context, then calls canonical `show_leds()`.
- VPAB context uses an explicit VPML sentinel for both primary and secondary.
- Hardware proof, when run, must verify the exact device identity before upload or device-write commands.
