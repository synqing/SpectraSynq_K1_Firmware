# Portable Core scaffold

## Role

`core/` holds the non-S3, platform-neutral logic that consumes the K1 audio contract and
produces frame commands for rendering.

## Immediate scope (Phase 0)
- Keep all API as pure data transforms and deterministic scheduling logic.
- Do not couple directly to `CRGB`, `FastLED`, WiFi, or board-specific SPI peripherals.
- Consume `contract/` types and call into `hal/` only through explicit interfaces.

## Source-backed seam anchor

- `audio/k1_audio_snapshot.h` defines the published snapshot frame shape.
- `effects/framework/K1AudioContext.h` defines the current read-only AP→VP projection surface.
- `diag/gdft_harness.h` and `serial/k1_ap_capture_telemetry.*` prove that capture/diagnostic paths can remain side-band and non-shipping.

## First file(s) to land under this folder

- Portable feature bus adapter (lifted from `K1AudioContext` projection behaviour).
- Testable, host-only harness entry point for AP frame updates.
- Timing policy stubs for 120 FPS/2.0 ms constraints and dt-correct smoothing.
