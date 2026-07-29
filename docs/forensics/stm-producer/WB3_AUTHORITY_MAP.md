# WB-3 STM authority map

**Status:** VERIFIED (git topology, registry, preflight) + **DEGRADED-MODE** (symbol-level C++ claims — clangd unavailable this session; see `GATE0_CLANGD_BLOCKER.md`).

**Plan:** WB-3 Investigation-to-Convergence (`correct-wb3-state_dee68cf1`).  
**Ledger:** `Lightwave-Ledstrip/BACKLOG.md` § WB-3 (corrected 2026-07-29).

## Repository roles

| Repo | Role |
|------|------|
| `/Users/spectrasynq/SpectraSynq_K1_Firmware` | Canonical product firmware — all STM implementation and forensics artefacts |
| `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip` | Programme ledger (`BACKLOG.md`), lineage oracle, deprecated donor (`firmware-v3/` — **do not read/edit for WB-3**) |

**Preflight:** `./tools/k1-lineage-preflight.sh` run 2026-07-29 — canonical HEAD `1957e53`, `default_envs = k1_hardware`.

## Commit topology (re-proved 2026-07-29)

| Commit | Subject | Branch containment | Ancestor of `origin/main`? | Parent(s) |
|--------|---------|-------------------|---------------------------|-----------|
| `f6cf78f` | Core-0 STM producer re-derived onto 80-note spectrogram | **`lane/stm-producer` only** | **No** | `bb26563` |
| `d40114f` | WB-3 K1 STM producer + EdgeMixer modes 7–8 (flag-gated) | `origin/main` (+ many lanes) | **Yes** | `0a518e5` |
| `a9ff00c` | audio-reactive STM via live mic-RMS gate + delete orphaned per-band AGC | `origin/main` | **Yes** | (on main after `d40114f`) |

**Merge-base(`f6cf78f`, `d40114f`)** = `bb26563` — `f6cf78f` is **not** a linear ancestor of `d40114f`; treat as parallel historical prototype, **not** the integration cherry-pick base.

**Integration base for convergence:** `origin/main` tip containing `d40114f` + `a9ff00c` (currently `f9bd28e` merge at time of audit). **Do not** cherry-pick `f6cf78f` wholesale.

## Active checkout vs WB-3 work (VERIFIED)

| Field | Value |
|-------|-------|
| Path | `/Users/spectrasynq/SpectraSynq_K1_Firmware` |
| Branch | `lane/dual-sync-phase0` (tracking `origin/lane/dual-sync-phase0`, ahead 1) |
| Working tree | **Dirty** — dual-sync recovery artefacts; **not** an implicit WB-3 integration base |
| STM on this branch | **Absent** — `k1_stm.*` exist on `origin/main` only (grep at `origin/main`) |

**Rule:** WB-3 doc/tool work may land on a clean worktree from `origin/main`; hardware/STM C++ edits require isolated worktree after Captain allocation — not the active dual-sync checkout.

## Compile-time authority (`origin/main`)

| Symbol / flag | Location (main) | Notes |
|---------------|-----------------|-------|
| `K1_STM` | `platformio.ini` → `env:k1_bench_im73d_stm` | Bench-only; `-DK1_STM` |
| Producer | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.{h,cpp}` | 40 ripple bins; 80-note spectrogram input |
| Snapshot | `k1_audio_snapshot.{h,cpp}` | `K1StmResult` embedded when `K1_STM` |
| EdgeMixer modes 7–8 | `director/k1_edgemixer.{h,cpp}` | `K1_EDGE_MIXER_STM_DUAL`, `K1_EDGE_MIXER_STM_SPECTRAL_MAP` |
| Host replay | `scripts/regression-harness/k1_stm_replay.py` | H1 mechanism cases |
| Test | `tests/test_k1_stm_replay.py` | Invokes replay harness |

**Production default:** `k1_hardware` — `K1_STM` **undefined** (flag-off byte-identical claim per `d40114f` message; structural proof is Phase 4 gate).

## Historical → current naming

| Donor / prototype (`f6cf78f` / LightwaveOS) | K1 (`d40114f+`) |
|---------------------------------------------|-----------------|
| `stmSpectral[42]` | `spectral[40]` / `K1_STM_SPECTRAL_BINS` |
| `stmTemporalEnergy` | `temporal_energy` → consumer `stmTemporalEnergy` |
| `stmSpectralEnergy` | `spectral_energy` |
| `stmReady` | `ready` |
| `STMExtractor` / `bins256` FFT path | **Not ported** — re-derivation from `spectrogram[80]` per `k1_stm.h` header contract |

## Device registry and hardware allocation (VERIFIED 2026-07-29)

Source: `docs/hardware/device-build-registry.md`.

| Device | Chip ID | Current deployed role | WB-3 allocatable? |
|--------|---------|----------------------|-------------------|
| Main K1 | `F887A500` | **Deprecated donor** `esp32dev_audio_esv11_k1v2_32khz` @ `7bf8a40f` (2026-07-29 Captain order) | **No** — wrong lineage; restore `k1_hardware` or sync probe before K1 STM work |
| Bench K1 | `B489A500` | `k1_sync_probe_bench` @ `3a9724e` (dual-sync FOLLOWER) | **No** without destroying dual-sync Phase-0 evidence lane |

**USB (preflight):** `/dev/cu.usbmodem112401` — verify MAC before any future flash.

**Rollback before any WB-3 bench flash:** restore bench to `k1_sync_probe_bench` @ `3a9724e` or Captain-named image; main to `k1_hardware` / sync probe per registry — **no erase_flash**.

## Open audit hypotheses (file/git evidence until clangd)

These remain **hypotheses** until Gate 0 clangd verification on `origin/main`:

1. Two `k1_stm_read()`-class operations per render frame vs single snapshot.
2. No STM fields in `K1AudioContext` adapter path.
3. Lazy LUT / `powf()` below render.
4. Centre LEDs 79/80 → bin 1 instead of bin 0.
5. Serial mode bound 0–6 vs modes 7–8 on other surfaces.
6. `edge_stm` registration vs `K1_STM` guard mismatch.

See `WB3_HYPOTHESES_AND_CLAIMS.md` for falsifiers and result states.

## Cross-links

- Claims / thresholds: `WB3_HYPOTHESES_AND_CLAIMS.md`
- 512 reference: `WB3_REFERENCE_ATTESTATION.md` (**INDETERMINATE**)
- VP instrument: `../stm-vp/STM_VP_MEASUREMENT_SPEC.md`, `scripts/regression-harness/stm_vp_compare.py`
- Core-0 bench: `WB3_CORE0_INSTRUMENTATION_SPEC.md`, `WB3_CORE0_BENCH_INDETERMINATE.md`
- Captain gate: `WB3_CAPTAIN_DECISION_PENDING.md`
- Clangd blocker: `GATE0_CLANGD_BLOCKER.md`
