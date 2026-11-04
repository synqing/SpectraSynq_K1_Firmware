# HANDOVER B — Differential vectors at 24 000 Hz / 180 and an Emotiscope tempo-field oracle

**Project folder:** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-K1-DualMCU-Firmware`
**Read-only input 1:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` — legacy S3 firmware. Read it, copy files out of it to scratch, never edit it.
**Read-only input 2:** `https://github.com/Lixie-Labs/Emotiscope` branch `2.0`, directory `main/`. Clone to a gitignored scratch path; do not vendor it.
**Agent:** Claude Code or Codex, one session, one branch (`lane/k1-dm-110-vectors-24k`).

---

You are the DSP verification engineer for the SpectraSynq K1 DualMCU firmware. The audio port at 12 800 Hz / 96-sample hop is already in this repo and parity-proven against the legacy oracle (K1-DM-020, BLOCKED only on a captured acoustic fixture). Your job is to produce the *differential* vectors for the rate the RT1062 (Teensy 4.1) will eventually run at, and to add a second oracle for a field the legacy firmware never publishes. You change no production behaviour.

## Rulings that shape this task (Captain, 2 Sep 2026)

- The legacy S3 stays at 12 800 / 96. Frozen.
- The RT1062 target is **24 000 Hz / 180 samples** — the same 133.33 Hz frame rate, so the novelty-driven tempo path is frame-identical. The switch itself is deferred until hardware exists; this task produces the evidence the switch will be gated on.
- Spectrogram values at 24 kHz are **not** expected to equal 12.8 kHz values (Goertzel block sizes scale with sample rate). Tolerances come from numeric behaviour, never from making a fixture green.

## Repo rules you must follow (they are the repo's, not mine)

- Run `.claude/harness/init.sh` before touching anything; it must be green at the end too.
- This brief names the active item: append **K1-DM-110 "Differential vectors at 24 000 Hz / 180 and Emotiscope tempo-field oracle"** to `.claude/harness/feature_list.json` (append-only, protected; validate with `python3 .claude/harness/harness.py validate`). Work it to `PASSING` or `BLOCKED`. `PASSING` needs commit hash, raw test output, proof.
- A behaviour change enters `docs/plans/deferred-upgrade-register.md` before code (`HARNESS_RULES.md` rule 12). The 24 kHz switch is one. Write the DUR entry first (see B0).
- `platformio.ini` is protected: pin versions, name every environment, keep the finite-math flag order, regenerate build evidence.
- Append your session to `.claude/harness/agent-progress.md`.

## Read first

1. `AGENTS.md`, `docs/agent/AGENT_EXECUTION_STANDARD.md`, `.claude/harness/HARNESS_RULES.md`, `.claude/harness/PROTECTED_FILES.md`, `harness/README.md`.
2. `core/audio/gdft_goertzel.cpp` (`kSampleRateHz`, block-size derivation lines ~150–185, `kGdftSampleHistoryLength`), `core/audio/tempo_tracker.cpp:18`, `core/audio/tempo_acf.cpp:25`, `core/visual/channel_render_state.h:34`, `hal/` for `kAudioCaptureSampleRateHz`.
3. How the existing parity vectors were made: `harness/gdft_harness_seed.h`, `test/fixtures/gdft_production_shell.golden.jsonl`, `test/fixtures/tempo_v2_flywheel.golden.jsonl`, the `native_*_parity` environments in `platformio.ini`, `docs/inventory/phase-0-source-inventory.md`.
4. Legacy: `SPECTRASYNQ_K1_FIRMWARE/diag/gdft_harness.h`, `tests/test_golden_master.py`, `tests/golden/gdft.golden.jsonl`, `tests/golden/MANIFEST.sha256`, and how `CONFIG.SAMPLE_RATE` / `CONFIG.SAMPLES_PER_CHUNK` reach the host build.
5. Emotiscope: `main/tempo.h`, `main/goertzel.h`, `main/global_defines.h`, `main/microphone.h` (constants only).

## Deliverables

### B0 — Deferred-upgrade register entry
One DUR entry: "RT1062 AP sample rate 24 000 Hz / 180-sample hop; frame rate unchanged." Fill every field the register's *Entry requirements* list demands. Status: deferred; this task supplies the differential evidence only.

### B1 — Legacy oracle run at 24 000 / 180
- Copy the legacy host-harness sources to a gitignored scratch path (for example `.cache/legacy-oracle-24k/`). Each copied file gets a provenance header: source path + legacy commit SHA.
- Sanity first: the copy at 12 800 / 96 reproduces the legacy `tests/golden/gdft.golden.jsonl` byte-for-byte. If not, stop and report; that is a finding.
- Run at 24 000 / 180 on the **same fixture definitions** the repo's parity vectors use (analytic fixtures — silence, impulse, sines, dual-tone, sweep — are re-synthesised at the new rate; any captured/authored audio fixture is resampled and the resampler + its parameters recorded). Emit `test/fixtures/*_24k180.golden.jsonl`: spectrogram, chromagram, onset, tempo (bin, BPM, phase, lock state) per frame.
- If the legacy code cannot run at 24 000 / 180 without change (hard-coded history length, block-size cap, `RUNTIME_TIMING_GUARD` equality), make the minimum change **in the copy only**, list each with a one-line reason, record them in the manifest.

### B2 — Parameterise the port, prove both rates
- Make sample rate and hop one configuration point in `core/audio/` (and the VP `samples_per_chunk` default that mirrors it) instead of scattered constants. Production configuration stays 12 800 / 96.
- Proof that nothing moved at 12.8 kHz: every existing `native_*_parity` environment stays green with unchanged golden files.
- New environment(s) run the port at 24 000 / 180 against the B1 goldens with a recorded per-feature tolerance and a one-line numeric justification for each tolerance.
- If `kGdftSampleHistoryLength` or any cap is exceeded by the longer 24 kHz block sizes, report the exact bins affected. Do not silently clamp.

### B3 — Emotiscope tempo-field oracle
- Compile Emotiscope 2.0 `tempo.h` + `goertzel.h` on the host with a shim header (in-tree, `harness/oracles/emotiscope/`) for the platform symbols they use: `dsps_memset_aes3`, `dsps_memcpy_aes3`, `dsps_mulc_f32_ae32`, `dsps_mulc_f32_ae32_fast`, `esp_timer_get_time`, `start_profile`/`end_profile`, `clip_float`, `window_lookup`, `shift_array_left`, `num_tempi_float_lookup`, `t_now_ms`/`t_now_us`. The generator clones the pinned Emotiscope commit into a gitignored path at run time; Emotiscope source is not committed here (the repo has no LICENSE file; Emotiscope is GPL-3.0 — vendoring is Captain's decision, not yours).
- Novelty source: Emotiscope's FFT path needs esp-dsp. Use esp-dsp's ANSI fallbacks or feed novelty from Goertzel spectrogram flux; state which.
- Drive it with the same fixtures (resampled to Emotiscope's 12 800 Hz / 128 chunk as needed) and emit per-novelty-tick goldens: 96 tempo magnitudes, 96 phases, `tempo_confidence`, `silence_level` → `test/fixtures/emotiscope_tempo_field.golden.jsonl`.
- This oracle exists because the legacy K1 never publishes the full tempo field and the RT1062 port will (`AudioFeaturesV1` has no tempo validity flag yet — do not add one; that is a protected-file change for a later item).

### B4 — Manifest, reproducibility, attribution
- One manifest per golden set: fixture SHA-256, oracle source commit, parameters, generator command, generator commit.
- Regenerating twice produces identical bytes. Make that a test.
- Add a top-level `NOTICE` attributing Emotiscope (GPL-3.0, Lixie Labs / Connor Nishijima) as a test-vector oracle not linked into any product image.

## Constraints

- No hardware. Host only. The replacement Teensy has not arrived.
- Do not edit the legacy repo. Do not change production sample rate, contracts, or existing golden files.
- Do not "improve" either oracle's DSP. Bugs you notice go in the report (Emotiscope's `unwrap_phase()` is a known no-op; leave it).
- No new guard macros, feature flags or timing instrumentation.
- British English.

## Acceptance

- DUR entry exists with every required field.
- Legacy copy reproduces `gdft.golden.jsonl` at 12.8 kHz exactly; 24 kHz goldens exist for every fixture with manifests.
- All pre-existing parity environments green, golden files unchanged (git diff empty on `test/fixtures/` except additions).
- Port at 24 000 / 180 matches B1 within recorded tolerances.
- Emotiscope tempo-field goldens exist with manifests.
- `.claude/harness/init.sh` green; one additional command runs both oracles and the identity test.

## Stop report (repo format)

Files changed; commands run; validation output; the copy-only changes for 24 kHz; the novelty source used; any bin/cap findings; blockers; exact next step. Nothing else.
