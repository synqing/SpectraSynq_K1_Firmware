---
abstract: "Lane N6 (perceptual) Class-C PREPARE-ONLY package for the per-band AGC candidate that fixes the 'louder -> dimmer' broadband-AGC defect. Root cause (grounded): k1_gdft_core.cpp computes ONE global agc_gain (line ~376) and applies it to every bin (line ~384); agc_bands[] per-band scaffold is unused (line ~410). Fix: SB_AGC_PERBAND_V1 (DEFAULT OFF) replicates the proven envelope/gate/gain pipeline per perceptual band via freq_to_band_map[]. Host-proven: OFF byte-identical (gdft golden reproduces); a new RED->GREEN property test (test_agc_perband_independence) shows OFF=single-scalar 3.26x uniform collapse vs ON per-band gains (spread 0.617, 3.2x headroom kept). Builds clean xtensa OFF+ON (+56 B RAM / +284 B flash). The agent does NOT flip the default or pick the look. Captain step = device A/B on the main K1 (chip F887A500) with the SPH0645 mic; protocol below. STOP for Captain eyes-on."
---

# Lane N6 — Per-band AGC (SB_AGC_PERBAND_V1) — PREPARE-ONLY package

> **Class C (prepare-then-decide). DEFAULT OFF. The agent NEVER flips the perceptual default or picks the shipping look.** This package delivers: grounded root cause · a flag-gated, host-proven candidate · a host characterisation · a device A/B capture protocol for the Captain. The lane STOPS here for Captain eyes-on.

## 1 · Root cause (grounded — verified first-hand 2026-06-30)

The "louder music -> dimmer waveform effects" inverse (Captain's lead observation, `docs/forensics/runtime-evidence/2026-06-21-gdft-overflow-telemetry/eyes-on-verdict.md`) is the **broadband single-scalar AGC**, NOT the GDFT int32 overflow (independent code paths — DSP root-cause spike, claude-mem obs #72837; present in BOTH legs of the 2026-06-21 A/B).

In `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp` (`process_GDFT`):
- **line ~376** — one global target: `target_gain = effective_target / (agc_envelope + AGC_EPS)`, where `agc_envelope` follows the mean magnitude across **all** bins.
- **line ~384** — that single `agc_gain` scalar multiplies **every** bin: `out = magnitudes_final[i] * agc_gain * spectral_tilt_lut[i]`.
- **line ~410** — the per-band `agc_bands[]` scaffold (`agc_channel`, `NUM_AGC_BANDS=4`) is written **mirror-only** (the scalar copied into all 4 slots) — present in structure, unused in function.

Consequence: loud broadband energy collapses the one gain, crushing quiet tonal/waveform detail in every band simultaneously. Live evidence (eyes-on): `agc_gain` 0.067 @ `max_raw≈8221` (loud) vs 0.14–0.16 @ `max_raw≈1900` (moderate); `agc_env` -> 6.8.

## 2 · The fix (flag-gated, default OFF)

`SB_AGC_PERBAND_V1` wraps a per-band AGC path in `process_GDFT`; the existing broadband stage is the `#else`. **No production env defines the flag**, so `k1_hardware` compiles the broadband path **byte-identically** (the gdft golden reproduces — see §4).

The per-band path **reuses the existing scaffold**: it partitions the 80 bins into the 4 perceptual bands via the already-populated `freq_to_band_map[]` (BASS/LOW_MID/HIGH_MID/TREBLE) and runs the **same proven** envelope-follower + noise-floor tracker + hysteretic gate + smoothed target-gain pipeline **independently per band**, writing the real per-band gains into `agc_bands[]`. It deliberately reuses the broadband time-constants / `effective_target` / `AGC_MAX_GAIN` / `agc_gain_floor` — it is a behaviour-faithful **partition**, not a re-tune.

**Out of scope (separate Captain-gated tuning lane):** per-band max-gain / attack shaping (`AGC_*_MAX_GAIN`, `agc_bands[].attack_rate`, A-weighting), and re-seeding the per-band state on `noise_cal` completion (state is function-static; the A/B excludes the convergence transient, so initial settle is outside the measured window).

Footprint (xtensa, `pio run -e k1_hardware`): flag ON adds **+56 B RAM / +284 B flash** over OFF. Both build [SUCCESS].

## 3 · Host characterisation (mechanism proof — NOT perceptual proof)

Deterministic host harness `scripts/regression-harness/golden/oracle_agc_perband.py` compiles the **real** `k1_gdft_core.cpp` twice (flag OFF / ON) and drives both with the SAME stimulus: ramping loud broadband tones (100/420/1500 Hz across BASS/LOW_MID/HIGH_MID) plus a constant quiet treble tonal peak (5000 Hz).

| Metric (at the loud frame) | OFF (production) | ON (`SB_AGC_PERBAND_V1`) |
|---|---|---|
| Per-band gains (BASS,LOW_MID,HIGH_MID,TREBLE) | 0.272, 0.272, 0.272, 0.272 (**identical**) | 0.863, 0.770, 0.431, 0.246 |
| Cross-band gain spread | **0.000** (one scalar) | **0.617** (per-band independent) |
| Single-scalar collapse quiet->loud | **3.26×** uniform dimming | n/a (per band) |
| Headroom kept vs OFF scalar | — | best band **3.2×** above the OFF scalar |

**Reading:** the single scalar crushes *all* bands to 0.272 under load; per-band AGC lets the less-loud bands keep 1.6–3.2× more gain, so loud energy in one band no longer dims the others. This is the mechanism of the "louder -> dimmer" fix.

**Honest caveats (host limits):** (a) host g++ proves the *mechanism* (gains become per-band), not the *perceptual* result — that is the device gate. (b) The Goertzel leaks broadband energy into all bins, so under genuinely broadband content the bands partially equalise; the magnitude of perceptual benefit is exactly what the device A/B must measure. (c) The host run is a short transient; on device the steady-state matters (hence the transient-exclusion in §5).

**Test gate:** `tests/test_agc_perband_independence.py` (5 tests) — OFF tests characterise the defect (single-scalar + 3.26× collapse); ON tests are RED until the flag is implemented, then GREEN (proven RED->GREEN this session by reverting/restoring the source). This is a property/characterisation gate, deliberately NOT registered in `harness_selftest.ORACLE_MODULES` (it touches no frozen golden / MANIFEST).

## 4 · Production neutrality (default OFF)

`tests/test_golden_master.py` PASS (gdft golden reproduces byte-for-byte; MANIFEST integrity intact) — the OFF path is unchanged. Full host suite: **574 passed, 1 skipped**. `pio run -e k1_hardware` (flag OFF) [SUCCESS].

## 5 · DEVICE A/B CAPTURE PROTOCOL (Captain's hardware step)

> The agent does **not** flash, play audio, or pick the look. This is the Captain-run step. Honour the codified audio-A/B methodology: **same source per state · isolate the single variable (the flag) · exclude the first ~8–10 s convergence transient · report steady-state median AND mean.**

**Device & identity:** main K1 — USB `/dev/tty.usbmodem1401`, **chip-ID `F887A500`**, env `k1_hardware`. Verify chip-ID before every flash (the upload guard is the last line of defence, not the first). Do **not** use the bench 12201 (`B489A500`, different GPIO map).

**Audio source:** the **SPH0645 MEMS mic, live capture** (Captain plays the stimulus — the agent never plays or generates audio). Choose ONE fixed programme with the failure shape: sustained loud broadband sections (drops / full-spectrum) interleaved with quiet sustained tonal/waveform detail. Use the **identical** source, level, and routing for both states.

**The single variable — the flag:**
- **State A (OFF, current production):** `pio run -e k1_hardware -t upload` (no flag).
- **State B (ON, candidate):** `PLATFORMIO_BUILD_FLAGS="-DSB_AGC_PERBAND_V1" pio run -e k1_hardware -t upload`. (Do not commit the flag into `k1_hardware` build_flags for the A/B; the env override keeps the single variable clean and revertible.)
- Everything else identical: same effect/mode, brightness, palette, noise-cal state, mic gain, room, programme.

**Procedure per state:**
1. Flash the state; verify chip-ID `F887A500`.
2. Confirm/seed `noise_cal` under a **verbal silence window** (never auto-fire) so both states share a comparable floor.
3. Start the SAME programme. **Discard the first ~8–10 s** (AGC + per-band envelopes converge — outside the measured window).
4. Over the steady-state window, capture the AGC telemetry over serial (the **GDFTAGC** schema in `serial/serial_menu.h` exposes `agc_bands[b].gain`, `agc_envelope`, `agc_noise_floor`): record per-band gains during loud broadband sections vs quiet tonal sections.
5. Eyes-on the plate: does the quiet tonal/waveform detail **stay lit** when the broadband content gets loud (the inverse fixed), without introducing per-band pumping / colour imbalance?

**Report (steady-state only):** for each state, the **median AND mean** of (a) the per-band gains under loud broadband, (b) the tonal-band gain during the quiet-detail sections; plus the eyes-on verdict on the "louder -> dimmer" inverse and on any new per-band artefacts. Bar: **at least neutral, preferably better** than State A (the eyes-on gate standard), with the inverse measurably reduced.

## 6 · Captain decision (the lane STOPS here)

- **Current state:** per-band AGC candidate built, host-proven (mechanism), default OFF, production byte-identical, xtensa-green. Perceptual value is **unproven on device**.
- **Decision required:** after the §5 A/B — (a) reject (keep OFF), (b) accept-as-default (a perceptual default flip → its own ticketed track: device A/B sign-off + golden update for the new shipping spectrum), or (c) accept-but-tune (open the per-band max-gain/attack tuning sub-lane first).
- **Options NOT taken by the agent:** flipping the default, picking the look, tuning per-band constants, promoting the GDFT int64 flags (D5 — stays HELD; re-test may be coupled to this lane once AGC is fixed, per obs #72837).
- **Blast radius:** flag OFF = zero production change. Flag ON changes the shipping spectrum (behaviour change) — gated behind the device A/B + a golden update on any default flip.
- **Default if no override:** stays OFF; no merge of a default change.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:embedded-firmware (N6 prepare lane) | Created. Grounded root cause (k1_gdft_core.cpp:376/384/410), SB_AGC_PERBAND_V1 candidate (default OFF), host characterisation (oracle_agc_perband + test_agc_perband_independence, RED->GREEN), production-neutrality proof, and the device A/B capture protocol for the main K1 (F887A500) + SPH0645 mic. Class C — prepares only; Captain decides. |
