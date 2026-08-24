# Master Plan v2 — Phase 0 inventory and portability seam scaffold

## Status and guardrails
- Source: `SpectraSynq_K1_Firmware` checkout.
- Objective: freeze a source-grounded Phase 0 boundary and put the portability skeleton in place.
- Constraint set: respect existing hard rules in `AGENTS.md` and `docs/agent/AGENT_EXECUTION_STANDARD.md`.
- Non-negotiables:
  - AP remains thinly coupled to VP via snapshot/read-only seams.
  - Portable Core and S3-Resident boundaries are explicit before any rewrite.
  - Portability work prioritises LED pixel/driver shim and SPI link seam.
  - No work on SPI transport in this phase; WiFi mode remains AP-only.

## Ratified correction to the plan (to keep)
- AP maths is **not** the high-risk coupling point.
- The DSP route is already behind mechanical wrappers and host-compilable shims:
  - GDFT/tempo/onset/saliency processing sits in a frame surface that can be called from host capture.
  - `diag/gdft_harness.h` injects synthetic input and calls `process_GDFT()` unmodified.
  - `audio/k1_audio_snapshot.h` declares `K1AudioSnapshot`, `K1OnsetBeatEvent`, and `k1_audio_snapshot_publish/read`.
- `effects/framework/K1AudioContext.h` already contains the AP→VP feature-vector seam as an adapter layer.
- The fast-math NaN guard risk is closed in-tree (`-fno-finite-math-only` is set in `platformio.ini` after `-ffast-math`).
- `network/k1_sync_link.*` is a BLE/NimBLE probe transport under `SB_K1_SYNC_PROBE`; it is not an inter-MCU VP link.
- Highest coupling risk in the VP lane is FastLED/CRGB propagation across effects/visual/control (89 occurrences), and the new SPI output seam.

## Source-grounded phase-0 inventory

### Portable-Core boundary (clean seam candidate)
**Feature vector contract (source-backed):**
- `audio/k1_audio_snapshot.h` defines production snapshot payload:
  - `K1AudioSnapshot`: `frame_ms`, `peak_scaled`, `vu_level`, `novelty`, `spectral_energy`, `low_energy`, `mid_energy`, `high_energy`, `chroma_strength`, `silence`, optional `spectrum[80]`, optional `chroma_pc[12]`, optional `chord`.
  - `K1OnsetBeatEvent`: `event_id`, `event_ms`, `event_age_ms`, `onset_strength`, `bass_onset_strength`, `beat_phase`, `beat_confidence`, beat/onset flags, optional transient/kick/snare/hihat channels.
  - Update/read API: `k1_audio_snapshot_publish(const K1AudioSnapshot&)`, `k1_audio_snapshot_read()`.
- `effects/framework/K1AudioContext.h` binds these snapshot types into effect accessors and performs the current 8-band/chroma rotation mapping.
- This file is explicit about read-only intent and that no DSP behaviour is added in the adapter.
- Build note: this path is mechanically safe to preserve and re-anchor in a portable core contract.

### S3-Resident lane (existing rendering surface)
- `core/`-side scheduling and audio ingest are thin from render perspective.
- Visual, effects, director, and control subsystems consume AP-provided contract values and pixel outputs.
- **Current centre of gravity for migration:** LED abstraction and pixel transport across CRGB/FastLED types.

### HAL-boundary risk map
| Area | Why it is high effort | Why it is bounded |
|---|---|---|
| FastLED/CRGB usage | pervasive `CRGB`/`FastLED` type usage, currently woven through VP render path | all instances are mechanical type-boundary replacements once a pure `hal` pixel contract exists |
| New SPI seam | unplanned for this phase and must be isolated from existing AP surface | greenfield by design; no coupling to existing WiFi/BLE transport |
| sync/link layer | `k1_sync_link.h/.cpp` are explicit phase-0 BLE probe transport | existing symbols are already feature-gated and parked under `SB_K1_SYNC_PROBE` |

## §6 scaffold decision and lane landing
Create the following tree under `SPECTRASYNQ_K1_FIRMWARE/` with initial handoff-ready files:
- `contract/` — source contract (lifted exactly from snapshot + context seam).
- `core/` — portable core seam notes and service contracts.
- `hal/` — pixel/transport HAL interfaces and migration notes.
- `harness/` — seeded harness entry points:
  - GDFT proof harness seed from `diag/gdft_harness.h`.
  - AP capture telemetry seed from `serial/k1_ap_capture_telemetry.h`.

## Lane plan from this checkpoint
1. **Lane A — Inventory lock (immediate).**
   - Create/normalise the scaffold tree and commit.
   - Keep this plan as the only source for AP→VP boundary assertions.
2. **Lane B — Portable core contract extraction (next).**
   - Translate `K1AudioContext.h` contract and snapshot structs into a language-neutral contract artifact in `contract/`.
3. **Lane C — HAL pixel abstraction (next).**
   - Introduce first-cut `hal` seam for pixel type and emit path.
4. **Lane D — Effect-path adaptation (next).**
   - Redirect VP consumers of `CRGB` through `hal` interfaces and migrate 89-file surface.
5. **Lane E — SPI seam (next).**
   - Add greenfield SPI lane in `hal/` with producer/consumer framing and bounded CI checks.

## Ship path required
1. Lock this plan and scaffold in git.
2. Bind Lane B and Lane C on one branch with contract tests for seam shape.
3. Only after Lane B + C are green, gate Lane D migration by file-count reduction.
4. Start Lane E after portable core + HAL boundaries are clean and measurable.
