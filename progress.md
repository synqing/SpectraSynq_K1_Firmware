# K1 SensoryBridge Rolling Progress

**Started:** 2026-05-25
**Current focus:** (2026-07-25) **Production-shipping hardening lane** (branch `feat/prod-shipping-hardening`, off `origin/main accc5f0`) — three audit items landed gate-green: LED-index OOB hardening (M1.3), GDFT int64 overflow promotion to the shipping env (M1.1, with pre-merge perf/eyes-on gates), and CI/gate completion (M0.1/M0.2). Wireless-security lane DEFERRED (verified latent — off in every shippable env). See the 2026-07-25 section below. Prior focus (2026-07-07): **IM73D controlled-audio DSR lane complete; DSR_16S rejected; restored bench validation green at usable levels; R2/R3 corrected after LED-map incident** — `k1_prod_im73d` main/prod build path shipped (`4b95e60`, byte-identical-OFF, guard-mapped to main K1). R1 knob persistence is CLOSED. Raw pre-conditioning AP telemetry landed (`67ae693`) and the DSR harness/compare path landed (`bc53ceb`). Controlled speaker playback showed DSR16 raises the quiet raw-RMS floor and does not improve raw-RMS-over-quiet response at matched playback levels, so production default remains `DSR_8S`. Bench K1 proves the IM73D mic/PDM path on the ratified `13/12/14` pins and is now validated on restored `k1_bench_im73d @ f2f7c45`: quiet/volume 45/volume 60 AP/raw captures are usable and AGC gains stay below 2.0 on all four bands. Volume 75 is a front-end stress/fail condition (`clip_pct`, `near_pct`, input trim), not acceptance evidence. Captain confirms both K1s are identical hardware; existing envs encode configuration choice (`k1_bench_im73d` = LED `4/5`, `k1_prod_im73d` = LED `6/7`). Main K1 remains the SPH reference/control on `k1_hardware @ 67227da`. See `docs/hardware/im73d-restored-bench-validation-2026-07-07.md`, `docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md`, `docs/hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md`, `docs/hardware/im73d-r2-main-k1-swap-decision-handoff-2026-07-06.md`, `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md`, and `docs/hardware/device-build-registry.md`.

## 2026-07-25 Production-Shipping Hardening Lane

Branch `feat/prod-shipping-hardening` off `origin/main accc5f0` (NOT the parked `bench/ws2816-split`). Captain deferred the wireless-security lane — verified LATENT: wireless is compiled out of every shippable env (`K1_WIRELESS_ENABLED` only in non-shippable `k1_wireless_ab_probe`), the shared control token was scrubbed from production 2026-06-27, and the audit's own tag is "[High — latent until wireless ships]". He then directed all three shipping-binary audit items to completion. All four commits gate-green; full host suite 716 passed / 1 skipped.

- **M1.3 LED-index OOB hardening** (`c877cfd` + corrections `4521015`): unconditional bounds guards in `lerp_led_16`, `unmirror`, `shift_leds_up/down` (`visual/led_utilities.h`). Real OOB class (`index_right → NATIVE_RESOLUTION`; unsigned `offset` underflow) that is LATENT in ALL current configs (SECONDARY_LED_COUNT hardcoded == NATIVE_RESOLUTION so the lerp caller's else-branch is dead; shift callers ≤ NR/2; unmirror has no callers) → defensive hardening, byte-identical at 160/160. Host proof `tests/test_led_index_bounds_static.py` (fuzz + statement-anchored source regex). Fully autonomous.
- **M1.1 GDFT int64 overflow promotion** (`a7dfe3a` + corrections `4521015`): enabled `K1_GDFT_INT64_MAGNITUDE_V1 + K1_GDFT_INT64_RECURRENCE_V1` in `[env:k1_hardware]` (= `default_envs`/shipping; `k1_prod_im73d` inherits). Fixes the int32 Goertzel overflow that zeroes near-resonance bins on loud audio. Host proof: `oracle_gdft` mutations 4–6 diverge the int32 golden (un-zero) + `test_gdft_int64_*` parity (clean-signal identical); shipping `k1_prod_im73d` compiles. **PRE-MERGE-TO-MAIN GATES (not closed autonomously, per authors' contract `config_types.h:95-96,101-112):** Core-0 perf/cadence pass (int64 in the hottest per-sample loop; the int32 AP loop is already p95-tight at 16k/120 — measure the 12.8k/96 delta) + Captain eyes-on real music. Revert = delete the two `-D` lines. Note: the host suite proves divergence + parity but does NOT golden-lock the int64 output (freeze that only after on-device acceptance).
- **M0.1/M0.2 CI + gate** (`da78aa0` + corrections `4521015`): `.github/workflows/ci.yml` widened to a matrix building `k1_hardware` + shipping `k1_prod_im73d` + the host golden gate + full suite; the pre-commit gate is proven to BLOCK a bad commit (negative test: a deliberately-failing test → `GATE BLOCKED`, HEAD unchanged) and pass good; classifier + `requirements-dev.txt` verified. CI is the committed enforcement gate (runs on every push regardless of local hooks); the local gate is a per-clone convenience (`scripts/hooks/install.sh`). Green-on-push needs a Captain-authorized push to the public `origin`.

Verified by a 3-skeptic adversarial pass (Lane A/B/C), each verdict re-run by the orchestrator; the accuracy/completeness corrections (reachability framing, `unmirror` guard, test hardening, default_envs, perf evidence, no-int64-golden) are folded into `4521015`.

**Update (2026-07-25, later — Captain-directed Push+Merge+bench A/B):** all lanes **merged to `main`** (`b26e235`); **CI ran green** on the branch push (host suite + both firmware envs). GDFT int64 (M1.1): on-device the int64-ON build runs **healthy at the shipping 12.8k/96** on bench `B489A500` (clean boot, full AP pipeline, tempo tracking, no WDT/bootloop) — a qualitative no-cadence-catastrophe pass; the QUANTIFIED cadence (`gdft_elapsed_us`) was NOT obtained (the AP stage-profiler is a main-K1-GPIO env, and the bench `apcad_*` dispatch needs the full `ap_frontend_probe` surface). Bench then flashed `k1_bench_im73d_ble` @ `6077f6e` (int64 fix + demo effects) and **Captain eyes-on PASS** ("It's good, looks/feels right") — **M1.1 fully closed.** Residual low-priority items only: the quantified cadence number (needs the main-K1 profiler or a bench profiler env-chain) and freezing an int64 golden.

## 2026-07-07 Restored Bench Validation

- **Verdict:** restored `k1_bench_im73d @ f2f7c45` is green for IM73D validation at usable playback levels on the bench-reference firmware LED map (`4/5`). This is not a `k1_prod_im73d` proof because `k1_prod_im73d` is the main/prod LED map (`6/7`).
- **AP/raw:** quiet, volume 45, and volume 60 bench runs were usable with `raw_i16_near_pct=0.000`. Volume 75 failed quality via `clip_pct_nonzero`, `near_pct_nonzero`, and `input_trim_reduced`.
- **AGC:** `:stream_agc` at volumes 45 and 60 stayed far below the `<10` gate; bench max gains were `[1.49, 1.72, 1.99, 1.57]` and `[1.47, 1.62, 1.84, 1.55]`.
- **Evidence:** `docs/hardware/im73d-restored-bench-validation-2026-07-07.md`; `artifacts/im73d_bench_ledproof_2026-07-07/20260707T170922_restored_bench_full_music/summary.json`; `artifacts/im73d_bench_ledproof_2026-07-07/20260707T171507_stream_agc_vol45/summary.json`; `artifacts/im73d_bench_ledproof_2026-07-07/20260707T171632_stream_agc_vol60/summary.json`.

## 2026-07-07 Bench LED-Pinmap Incident

- **Cause:** `k1_prod_im73d` extends `k1_hardware`, so it drives GPIO `6/7`; restored bench-reference firmware drives GPIO `4/5`. Treating the restored bench IM73D unit as a `k1_prod_im73d` proof unit conflated mic-pin equivalence with env/LED-map choice. Captain confirms both K1s are identical hardware.
- **Observed effect:** flashing `k1_prod_im73d @ f2f7c45` to bench K1 `B489A500` made both LED channels dark while serial/audio proof still appeared alive.
- **Immediate recovery:** bench was MAC-verified (`B4:3A:45:A5:89:B4` on `/dev/cu.usbmodem1401`) and uploaded back to `k1_bench_im73d @ f2f7c45`; read-only `:build`/`:dump` proved `env=k1_bench_im73d`, chip `B489A500`, `CONFIG.CHROMA: 0.100000`, `CONFIG.SENSITIVITY: 0.870005`, `AUDIO_RESPONSE_GAIN: 1.000000`, `CAL_SOURCE: persisted_profile`, `CAL_VALID: 1`, and `CAL_PROFILE_LOADED: 1`.
- **Guard correction:** `k1_prod_im73d` is restored as the main/prod IM73D env and guard-mapped to the main K1 MAC. Bench proof remains `k1_bench_im73d`.

## 2026-07-07 R2 Main-Swap Blocker Superseded

- **Correction:** bench K1 carries IM73D on the ratified mic pin map (`clk13/din12/LR14`). It is therefore a valid IM73D mic/PDM proof unit.
- **Superseded blocker:** main-K1 SPH0645->IM73D physical swap is not required to prove the mic path; it is optional product-unit conversion work, not the current proof blocker.
- **Next mechanical step:** use the existing env that matches the intended configured unit: `k1_bench_im73d` for LED `4/5`, or `k1_prod_im73d` for LED `6/7`.
- **Doc updated:** `docs/hardware/im73d-r2-main-k1-swap-decision-handoff-2026-07-06.md` is retained for link stability but now explicitly marks the old swap handoff as superseded.

## 2026-07-07 Bench Recovery Proof

- **Bench identity:** MAC `B4:3A:45:A5:89:B4` on `/dev/cu.usbmodem1401`; read-only `:build` proved `git=9d14463 env=k1_bench_im73d`; `:dump` proved chip `B489A500`, `CONFIG.CHROMA: 0.100000`, `CONFIG.SENSITIVITY: 0.870005`, `CAL_SOURCE: persisted_profile`, `CAL_VALID: 1`, `CAL_PROFILE_LOADED: 1`, `raw_i16_near_pct=0.000`, `input_trim=1.000`, `clip_pct=0.000`, `near_pct=0.000`.
- **Main identity:** MAC `B4:3A:45:A5:87:F8` on `/dev/cu.usbmodem12401`; read-only `:build` proved `git=67227da env=k1_hardware`; `:dump` proved chip `F887A500`, `CONFIG.SENSITIVITY: 2.400000`, `CAL_SOURCE: config`, `CAL_VALID: 1`.
- **Evidence:** `artifacts/im73d_recovery_2026-07-07/readonly_build_dump_20260707.json`.
- **Safety:** no `start_noise_cal`, no `N`/`Y`, no flash, no erase, no non-read-only serial command. Pyserial opened with DTR/RTS low; native USB still emitted benign `rst:0x15` reset banners on open.

## 2026-07-06 Controlled-Audio DSR_16S Evidence

- **Verdict:** `DSR_16S` is rejected; keep `DSR_8S`.
- **Controlled stimulus:** `/Users/spectrasynq/Downloads/Tiësto-TheBusiness.mp3`, offset `35 s`, duration `30 s`, volumes `45,60,75`, 2 repeats per music condition plus 2 quiet repeats. No `start_noise_cal`, `N`, or `Y`.
- **Bench DSR8 baseline:** `artifacts/im73d_dsr_audio_eval_2026-07-06/20260706T175119_dsr8_controlled_audio/summary.json`, build line `git=bc53ceb env=k1_bench_im73d`, bench repeatability PASS.
- **Bench DSR16 candidate:** `artifacts/im73d_dsr_audio_eval_2026-07-06/20260706T180529_dsr16_controlled_audio/summary.json`, build line `git=9d14463 env=k1_bench_im73d_dsr16`, bench repeatability PASS for all bench groups. Overall repeatability was false only because main-SPH volume 45/60 groups exceeded the CV threshold; main is not the DSR promotion target.
- **Comparison:** `artifacts/im73d_dsr_audio_eval_2026-07-06/dsr8_vs_dsr16_controlled_audio_compare.json`; write-up `docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md`.
- **Result:** quiet raw RMS p90 mean rose from `25.45` to `34.00` under DSR16. Music raw-RMS-over-quiet fell at every tested playback volume: volume 45 `2.153 -> 1.422`, volume 60 `4.161 -> 2.771`, volume 75 `6.692 -> 4.729`. Raw near-rail remained zero, `input_trim=1.000`, `clip_pct=0.000`, and `near_pct=0.000`; the rejection is not a rail-safety failure, it is an SNR/response-value failure.
- **Bench recovery caveat:** same-HEAD restored DSR8 proof failed after post-upload CDC/app serial failure. The bench still enumerates as MAC `B4:3A:45:A5:89:B4`, but low-DTR/RTS serial probes and esptool `chip_id` under `usb_reset`, `default_reset`, and `no_reset` all returned no serial data. Treat the bench as requiring physical reset/replug before further runtime proof.

## 2026-07-06 No-Speaker DSR_16S Evidence + Harness Hardening

- **Commit:** `bc53ceb test(im73d): add no-speaker dsr harness` on `lane/im73d-pdm-eval`.
- **Harness:** `scripts/regression-harness/im73d_audio_eval.py` now supports `--quiet-only` / `--no-speaker-playback`, refuses nonzero volumes in that mode, and adds `--compare` / `--compare-output` for DSR reports built from `summary.json` files.
- **Comparison truth:** DSR comparison now treats `raw_i16_rms`, `raw_i16_abs_peak`, and `raw_i16_near_pct` as required inputs. Conditioned `max_raw` is retained as context only.
- **Validation:** focused harness/static tests PASS (`15 passed`); harness self-test PASS; full host suite PASS (`647 passed, 1 skipped`). The earlier interrupted pytest PTY is not the verification result; the clean rerun is.
- **Device proof:** bench MAC `B4:3A:45:A5:89:B4` on `/dev/cu.usbmodem101` was guard-verified, flashed to `k1_bench_im73d_dsr16 @ bc53ceb`, captured quiet-only 3x, then restored to `k1_bench_im73d @ bc53ceb` and captured matching quiet-only 3x. Main K1 was present but not flashed.
- **Evidence:** DSR16 `artifacts/im73d_dsr_eval_2026-07-06/20260706T162130_dsr16_quiet_only/summary.json`; restored DSR8 `artifacts/im73d_dsr_eval_2026-07-06/20260706T162406_dsr8_quiet_only_restored/summary.json`; compare report `artifacts/im73d_dsr_eval_2026-07-06/dsr8_vs_dsr16_quiet_compare.json`; write-up `docs/hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md`.
- **Result:** no raw near-rail evidence (`raw_i16_near_pct=0` for both), `input_trim=1.000`, `clip_pct=0.000`, `near_pct=0.000`, all bench runs usable. Quiet DSR16 raw RMS was lower than quiet DSR8 (`raw_i16_rms` p90 mean ratio 0.788), but no signal stimulus was present, so **DSR_16S remains unpromoted**.
- **R2 handoff superseded:** `docs/hardware/im73d-r2-main-k1-swap-decision-handoff-2026-07-06.md` now records that the bench IM73D unit proves the mic/PDM path, Captain confirms both K1s are identical hardware, and the remaining blocker is firmware LED pin-map reconciliation rather than a main-K1 swap.

## 2026-07-06 Audio Pipeline Purity Audit

- **Verdict:** normal `[AP]`, `[APCAP]`, `agc_debug`, onset/tempo/chord, and `AudioSemanticState` surfaces are conditioned production-behaviour signals, not raw microphone-purity signals. The one existing pre-conditioning sample surface is `:dump_raw`, which prints DMA samples before IM73D gain, sensitivity, clip limiting, and DC correction. Authority: `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md`.
- **Sensitivity finding:** factory default is `CONFIG.SENSITIVITY=2.4`, but live bench IM73D preflight after reset proved `CONFIG.SENSITIVITY: 0.870005`, `AUDIO_RESPONSE_GAIN: 1.000000`, `CAL_SOURCE: persisted_profile`, `CAL_VALID: 1`; main SPH proved `CONFIG.SENSITIVITY: 2.400000`, `AUDIO_RESPONSE_GAIN: 1.000000`, `CAL_SOURCE: config`, `CAL_VALID: 1`. Ratio claims between devices are invalid unless this state is pinned/recorded.
- **Harness hardening:** `scripts/regression-harness/im73d_audio_eval.py` now records `front_end_lines` from `:dump` and treats downstream `peak_pin` as `conditioned_peak_pin_high` warning, not raw clipping. Hard rejects remain too-few rows, `clip_pct`, `near_pct`, reduced `input_trim`, and raw-domain near-rail `max_raw >= 30000`.
- **Machine gate:** `tests/test_im73d_audio_purity_static.py` locks the current source truth: `dump_raw` is before conditioning; AP `max_raw` is after IM73D gain, sensitivity, clamp, and DC correction; sensitivity control surfaces are inconsistent and must stay visible until intentionally reconciled.
- **Validation:** focused pytest `tests/test_im73d_audio_eval_harness.py tests/test_im73d_audio_purity_static.py -q` PASS (8/8); full host suite PASS (`640 passed, 1 skipped`); `im73d_audio_eval.py --self-test` PASS.
- **Live read-only sanity:** `_scratch/im73d_audio_eval/20260706T144515_purity_conditioned_readiness/summary.json` captured both MAC-verified K1s with no hard front-end failures at quiet + Mac volume 20. This is explicitly conditioned readiness evidence, not raw mic purity evidence. No `start_noise_cal`, `N`, `Y`, erase, flash, or DSR flip was run.
- **Supersession:** raw continuous telemetry landed after this audit as `raw_i16_abs_peak`, `raw_i16_rms`, and `raw_i16_near_pct`. The no-speaker DSR run used those fields and kept DSR_16S unpromoted pending controlled acoustic stimulus.

## 2026-07-06 R4 Real-Audio Harness + Bench CDC Blocker

- **Superseded by Captain reset + purity audit:** the bench-silent blocker below was real at the time of `c6c40d4`, but after Captain reset both K1s, live `pio device list` and the 2026-07-06 `purity_conditioned_readiness` capture proved bench `B489A500` and main `F887A500` both enumerate and stream again. The current blocker is raw/pre-conditioning purity evidence, not USB recovery.
- **Harness shipped:** `c5d2399` added `scripts/regression-harness/im73d_audio_eval.py` + `tests/test_im73d_audio_eval_harness.py`; `c6c40d4` hardened it to keep one serial session open per device, wait for runtime `[AP]` readiness before commands/capture, restore Mac output volume on exit, and fail closed on missing rows, clipping/near-rail, peak pinning, input trim, and repeatability drift.
- **Validation:** harness self-test PASS; focused pytest `tests/test_im73d_audio_eval_harness.py` PASS; both commits passed the pre-commit pyharness tier (`python3 -m pytest tests/ -q`); compile-only `bash scripts/agent/pio-build.sh k1_bench_im73d` PASS; compile-only `bash scripts/agent/pio-build.sh k1_hardware` PASS.
- **Dry-run result:** first real-audio dry run proved Mac volume/playback control and main-SPH capture but exposed a bench failure. Final committed harness repro: `_scratch/im73d_audio_eval/20260706T141749_bench_blocker_final/preflight_bench_im73d.log` (0 runtime lines, fail-closed before measurement).
- **Bench blocker:** bench `B489A500` still enumerates as `B4:3A:45:A5:89:B4` on `/dev/cu.usbmodem101`, but passive CDC reads produce 0 lines; guarded uploads to both `/dev/cu.usbmodem101` and `/dev/tty.usbmodem101` fail at esptool connect with `Failed to connect to ESP32-S3: No serial data received`; direct esptool `chip_id` also fails the same way; `lsof` shows no port owner.
- **Next mechanical step:** Captain physically presses RESET on the bench K1; if still silent, hold BOOT, tap RESET, release BOOT. Then rerun upload guard + radio-free `k1_bench_im73d` upload, run the DSR_8S baseline with the harness, add the temporary DSR_16S eval flag, flash bench only, and repeat the same volume/track windows. No `start_noise_cal` was run.

## 2026-07-06 Two-K1 Live Refresh

- **Main K1 used:** guard-verified `F887A500` on `/dev/cu.usbmodem1101`, built and uploaded `k1_hardware @ 67227da`; post-upload read-only `:build`/`:dump` proved `env=k1_hardware`, `I2S STD INIT: PASS`, `CAL_SOURCE: config`, `CAL_VALID: 1`.
- **Bench K1 used:** guard-verified `B489A500` on `/dev/cu.usbmodem101`; left on radio-free `k1_bench_im73d @ 6f2f1ec`, `I2S PDM RX INIT: PASS`, `CAL_SOURCE: persisted_profile`, `CAL_VALID: 1`.
- **Paired passive AP capture:** `_scratch/im73d_bringup/snappiness/dual_ap_capture.py 30` with zero command bytes. Current envelope: bench IM73D `max_raw p50=1224 p90=1851 max=2282`; main SPH `p50=1906 p90=3063 max=3600`; both cal-valid, input_trim 1.000, no clamp risk.
- **Evidence:** `_scratch/im73d_r1_knob_persistence_20260706/two_k1_readonly_build_dump_20260706.log`, `_scratch/im73d_r1_knob_persistence_20260706/two_k1_post_main_flash_readback_20260706.log`, `_scratch/im73d_bringup/snappiness/dual_main_sph.log`, `_scratch/im73d_bringup/snappiness/dual_bench_im73d.log`.

## 2026-07-06 R1 Knob-Persistence Device Capture (radio-free bench)

- **Live truth:** branch `lane/im73d-pdm-eval`, HEAD `6f2f1ec`; bench `B489A500` = `/dev/cu.usbmodem101` (`B4:3A:45:A5:89:B4`), main `F887A500` = `/dev/cu.usbmodem1101` (`B4:3A:45:A5:87:F8`). Existing unrelated untracked skill/config artefacts were left untouched.
- **Host/identity gates:** `session-bootstrap` PASS; upload guard PASS for `k1_bench_im73d` on bench MAC; `bash scripts/agent/pio-build.sh k1_bench_im73d` PASS; `bash scripts/regression-harness/mic_stable_byte_gate.sh k1_bench_im73d` PASS.
- **Device proof:** flashed radio-free `k1_bench_im73d @ 6f2f1ec` to bench. Read-only `:build` proved `git=6f2f1ec env=k1_bench_im73d`; `:dump` proved `CAL_SOURCE: persisted_profile`, `CAL_VALID: 1`. `:chroma=0.150` echoed, waited >6 s, `:reset`, then `:dump` proved `CONFIG.CHROMA: 0.150000` survived reboot with `CAL_SOURCE: persisted_profile` still intact. No `start_noise_cal` was run.
- **Restore proof:** `:chroma=0.100` echoed and waited >6 s, then `:reset` was issued to prove restoration. After Captain BOOT/RESET recovery, final read-only `:build` + `:dump` on the bench MAC proved `git=6f2f1ec env=k1_bench_im73d`, `CONFIG.CHROMA: 0.100000`, and `CAL_SOURCE: persisted_profile`.
- **Evidence:** `_scratch/im73d_r1_knob_persistence_20260706/r1_knob_persistence_serial.log` and `_scratch/im73d_r1_knob_persistence_20260706/r1_restore_after_bootreset_read_serial.log` (ignored scratch artefacts). Prior blocked read/upload attempts are retained in the same scratch directory. Registry top row updated to the current deployed state.

## 2026-07-06 IM73D Productionization Phase 1 (autonomous execution)

- **Context:** Captain ratified D1 (production IM73D pin map = identical bench-proven `clk13/din12/LR14`, all K1s same ESP32-S3 devboard) and withdrew the D2 "PCB rev" framing (IM73D already on the bench since bringup). Then authorised autonomous completion of all outstanding Phase-1 phases. Planned harness-first (`/autonomous-agentic-build`, `/planning-with-files`): `docs/hardware/im73d-productionization-execution-plan-2026-07-06.md`.
- **Lane consolidation first:** merged `lane/palette-vibrancy-v1` into `lane/im73d-pdm-eval` (`55c536b`; registry + platformio conflicts resolved, vibrancy row → eyes-on PASSED); forensic doc `32bc384`; §10 audit `741a40f`; §10.3 decision `a82c1d9`.
- **UA — `k1_prod_im73d` main/prod build path SHIPPED (`4b95e60`).** `constants.h` production `#else` pinmap now defines `K1_PDM_CLK/DIN/LR = 13/12/14` under the flag; `[env:k1_prod_im73d]` extends `k1_hardware` and uses the main/prod LED map `6/7`; drift-catcher + guard + production-pin static tests. **Byte-identical-OFF proven** (3 stable sections) + source-level OFF-gated. pytest 629.
- **UB — MicFrontend runtime dispatch REJECTED (decision).** Un-byte-verifiable (build not bit-reproducible in `.flash.text`/`.flash.rodata` — the known `K1_BUILD_EPOCH` timestamp) + Core-0 cost + `sensorybridge-doctrine`. Compile-time selection retained; 6-interface seam map delivered instead (handover §11.2). This is the correct trade, not skipped work.
- **UC — `mic_stable_byte_gate.sh` SHIPPED (`d1ecc10`).** Formalises the stable-section oracle the graft used manually: hashes ONLY the 3 reproducible sections (`.dram0.data`/`.iram0.text`/`.iram0.vectors`), committed references for k1_hardware/k1_bench_reference/k1_bench_im73d, static contract test. Additive — `registry_byte_gate.sh` (flaky, 5 sections) left as trust root.
- **UD/UE — docs (`6bfc702`):** DSR_16S enable recipe + SNR protocol; production-flip red-team (pre-mortem + 7-step checklist).
- **UF — knob-persistence device-proof CLOSED (`d9f53d6` → `67227da`).** Radio-free bench proved `:chroma=0.150` persistence across reset, then final restored `CONFIG.CHROMA: 0.100000` after Captain BOOT/RESET recovery; cal profile stayed `persisted_profile`. No `start_noise_cal` was run.
- **Superseded blocker note:** this older absolute-blocker list is superseded for main-K1 mic swap and DSR_16S. DSR_16S was rejected by controlled-audio evidence; main-K1 swap is optional because the bench IM73D unit is identical production-shape K1 hardware. Remaining gates are selected-env device proof, eyes-on, and `k1_hardware` default flip.

## 2026-07-04 IM73D + BLE-MIDI Demo Build (`k1_bench_im73d_ble`)

## 2026-07-04 IM73D + BLE-MIDI Demo Build (`k1_bench_im73d_ble`)

- **Goal (Captain):** a bench K1 running the IM73D122 mic PLUS BLE-MIDI so the **K718 Remoted dial controls it live** for investor demos. **Separate workstream** from IM73D eval/tuning — do NOT measure mic SNR on this radio build (Core-0 BLE task; interference A/B open).
- **Composition:** new `[env:k1_bench_im73d_ble]` = `extends k1_bench_im73d` + 3 BLE deltas (`network/ble_remoted_central.cpp` + `k1_ble_midi_decoder.cpp`, `-DSB_K1_BLE_REMOTED`, `NimBLE-Arduino@^2.5.0`); does NOT extend the harness → zero instrumentation, production byte-identical. Guard tuple line added. **Revert** = delete env block + guard line.
- **4-SSA injection-point investigation** (ssa-management launch/return contracts; orchestrator re-ran the decisive claims): **linkage VERIFIED** (`sb_k1_control_apply()` at `sb_k1_control_facade.cpp:468` unconditional; `.ino:675/812` calls under `#ifdef SB_K1_BLE_REMOTED`); **RT/RF VERIFIED** (BLE app task `central.cpp:229` **and** NimBLE host both default Core-0 → confound real for *measurement*, moot for *demo*); **K718 protocol byte-exact match**; **device/gate VERIFIED**.
- **Host gate GREEN:** `pio run -e k1_bench_im73d_ble` `[SUCCESS]` (RAM 38.0% / Flash 13.9%); `test_dev_instrumentation_boundary` + `test_token_scrub_static` = **13/13**.
- **Flashed bench `B489A500` (2026-07-04):** guard-verified on `/dev/cu.usbmodem1101` (ports re-scrambled — `2101`=main, `101`=K718; identity by USB serial, not port); hash-verified. Runtime (passive read-only serial): boots clean, 0 crash markers, BLE central **`linked=1`** to the live K718 "SpectraSynq Remoted" peripheral (`JC3636_K718_REMOTED_BLE_V1`), `notify=0` → **control-proof (dial-turn) pending**. `linked=1` overrides SSA-3's provisional "K718 never flashed" (runtime > static audit).
- **Outstanding:** (1) turn the K718 dial → confirm `notify/decoded/apply_ok` climb + `CONFIG.*` change; (2) K718-linked+streaming cal repro (crash condition); (3) Core-0 demo-robustness if glitching; (4) **this flash replaced the bench's `3e06f9d k1_bench_im73d` state → IM73D Phase 1.1 device-proof needs a radio-free reflash.**
- **2026-07-05 update:** bench reflashed to `d32770d` (`1ac840a` cal-abort guard + `:ble_stream` telemetry). Captain silence-go cal **ACCEPTED** with 0 abort (K718 unlinked) — fix device-proven for light load; K718-linked repro still owed.
- **Detail:** `docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md`.

## 2026-07-02 IM73D122 PDM Mic Graft (bench-only, flag-gated)

- **Branch:** `lane/im73d-pdm-eval` (off `26eebb1`). **Flag:** `K1_MIC_IM73D_PDM_V1` — defined in EXACTLY ONE env: `[env:k1_bench_im73d]` (extends `k1_bench_reference`). SPH0645 (`i2s_std`) stays the byte-identical product default when the flag is OFF.
- **Commits:** `545d331` (the graft, 11-point spec) + `c3584fa` (gain `K1_MIC_IM73D_INPUT_GAIN` 3.0→16.0) + `49b0393` (registry/device-proof). All flag-gated `#ifdef K1_MIC_IM73D_PDM_V1 … #else <verbatim SPH0645> … #endif` across 6 firmware files (i2s_audio.h, constants.h, globals.h, system.h, noise_cal.h, bridge_fs.h).
- **Host gate GREEN:** pytest 619 pass / 1 skip; `pio run -e k1_bench_im73d` clean (RAM 32.8% / Flash 9.8%); flag-OFF byte-identity PROVEN for `k1_hardware` AND `k1_bench_reference` (identical section sizes + `.dram0`/`.iram0` SHAs; `.text`/`.rodata` churn is only `K1_BUILD_EPOCH`).
- **Device-proven on bench `B489A500`:** boots; PDM RX reads the mic on the LIVE AP+VP (`onset`/`bass`/`bpm` firing, `lock=1`); boot force-invalidate `SSL=120 DC=0`, no NaN; gain `g=16` in-band (loud `max_raw` ~4339, non-railed); silence-go recal PASSED (`cal_valid=1 SSL=710 DC=-13`); failed-cal path restored `SSL=120` (fallback, not 0). NVS frozen under the flag → cal is RAM-only, re-cal each power-up.
- **Remaining acceptance (both need Captain):** (1) per-band AGC `:stream_agc` all 4 gains <10; (2) eyes-on A/B vs SPH0645 across genres incl. VU modes.
- **Do NOT bump `g=16`** (silence cals to `SSL=710`, top of valid `[50,720]`). Rollback = delete `[env:k1_bench_im73d]` + guard tuple line; `#ifdef` blocks are inert with the flag undefined.
- **Authority docs:** `docs/hardware/im73d122-ap-vp-migration-plan.md` (canonical design) · `docs/hardware/im73d122-graft-handover-2026-07-02.md` (session handover + 7 gotchas) · `docs/hardware/device-build-registry.md` (deployed-state table, bench row).

## 2026-06-21 AP Measurement-Honesty Lane (Chapter-6 DFT/STFT)

Goal: make the Goertzel AP path measurement-honest without redesigning DSP. Two stacked branches off `feat/effect-registry-rewire` (not on main; windowing flag DEFAULT-OFF so production is byte-identical). No coefficient change, no VP-by-default change, no tempo change.

- `feat/ap-measurement-honesty` (`4bcd538`, pushed): new `k1_spectral_honesty.h` — DFT honesty primitives (true_resolution tied to per-bin `block_size`, NOT bin count; endpoint-mismatch leakage_risk; correct shared Hann). Gated `K1_SPECTRAL_WINDOW_V1` Hann windowing on the GDFT spectral path with explicit coherent-gain compensation. Fixed the dead `window_lookup` Hann table (was `0.54*(1-cos)`, int16-overflowing at centre). Endpoint index mapping (`window_mult=4095/(block_size-1)` + round-to-nearest) verified to hit both Hann zero endpoints (0/4095) for every block size; pure truncation undershot to 4094 on 287/1999.
- `feat/ap-bin-frequency-honesty` (`24f95a3`, stacked): `k1_goertzel_*` target vs actual_center vs target_error metadata (each bin resonates at integer DFT index k, so |error| <= half its resolution cell). Also renamed the whole honesty surface `sb_`->`k1_` per Captain naming order (inherited `sb_` heritage untouched).

Status: host gate **550 passed**; `pio k1_hardware` clean with `K1_SPECTRAL_WINDOW_V1` OFF (Flash 649382 B = byte-identical to baseline) and ON (649426 B). Device eyes-on is needed ONLY if/when the windowing flag is enabled for an A/B — tracked, non-blocking.

## 2026-06-15 Effects Lane Supersession / Partial VP Smoke

- Superseded the stale 2026-06-11 effects recovery blockers in `docs/handover/2026-06-11-effects-lane-claude-mem-recovery.md`: current source no longer remaps persisted modes 24/25 to retired SAT aliases, and the production AP stream no longer reads `SBAudioSnapshot` or emits chord telemetry.
- Guarded source facts: `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:82-88`, `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:157-160`, `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:563-573`, `tests/test_snapwave_pulse_static.py:129-139`, and `tests/test_chord_hue_consumer_static.py:72-79`.
- Focused host/static gate passed: `python3 -m pytest tests/test_chord_hue_consumer_static.py tests/test_new_effects_batch_static.py tests/test_snapwave_pulse_static.py tests/test_palette_authority_static.py tests/test_impact_lane_static.py -q` -> `38 passed`.
- Build gate passed for `pio run -e k1_hardware` and `pio run -e k1_bench_reference` with the known `system.h:48` volatile warning only.
- Partial live VP smoke evidence: `docs/forensics/runtime-evidence/20260615T222315-new-effects-mode24-29-vp-smoke/`. Modes 24-27 produced VP rows on both devices with `failure=null`, production tuple `12800/96`, and zero crash-marker matches. Closeout doc: `docs/forensics/2026-06-15-new-effects-mode24-27-partial-vp-smoke.md`.
- Boundary: this is not a full 24-29 product gate. Modes 28-29 were not completed after Captain stopped the playback window.

## 2026-06-15 Response Profile Gate

- Closed the buffered tempo-lock follow-up: main `F887A500` at labelled diagnostic `response_gain=3.0` and bench `B489A500` at `response_gain=1.0` both locked every emitted warm APCAD row at 120 BPM under the buffered probe surface. Verdict: downstream V2 tempo path is healthy under matched response provenance, not a remaining blocker.
- Restored both devices from non-shippable AP front-end probe firmware to shippable envs: main `/dev/cu.usbmodem12201` -> `k1_hardware`, bench `/dev/cu.usbmodem12401` -> `k1_bench_reference`. Post-restore proof: `docs/forensics/runtime-evidence/20260615T074307-snappiness-manifest.json`.
- Ran production-env response-profile A/B without calibration, flash, reset, sample-rate change, mode change, or scene change:
  - default run: main `1.0`, bench `1.0` -> `_scratch/main-dc-anomaly-20260615/captures/20260615T075243-production-default-gain-1p0-paired-response-runner-manifest.json`;
  - candidate run: main `3.0`, bench `1.0` -> `_scratch/main-dc-anomaly-20260615/captures/20260615T075436-production-main-gain-3p0-paired-response-runner-manifest.json`.
- Interim decision before the eyes-on window: do **not** persist or productionise a per-device response profile yet. Scalar production-stream telemetry showed only modest main `peak_scaled_mean` improvement (`0.534016 -> 0.593125`) and no confidence/lock improvement (`conf_mean 0.225156 -> 0.193281`, `lock_mean 0.125 -> 0.0`). That decision was superseded by the later eyes-on window and Captain-directed production fix below.
- Both devices were explicitly restored to `response_gain=1.0`; final proof manifest: `docs/forensics/runtime-evidence/20260615T075637-snappiness-manifest.json`.
- Executed the labelled 120 s eyes-on A/B window: main `response_gain=3.0`, bench `response_gain=1.0`, fixed `wireless_ab_stimulus.wav`, no calibration/reset/flash/mode/scene changes. Evidence: `_scratch/main-dc-anomaly-20260615/orchestrator/13-eyes-on-response-ab-window.md` and `_scratch/main-dc-anomaly-20260615/captures/20260615T080607-eyes-on-main-3p0-bench-1p0-paired-response-runner-manifest.json`. Scalar result was stable (`main conf_mean=0.681789`, `lock_mean=0.658537`; bench `conf_mean=0.663171`, `lock_mean=0.593496`). Both devices were then restored to `response_gain=1.0` in `docs/forensics/runtime-evidence/20260615T080849-snappiness-manifest.json` before the production fix was implemented.
- Promoted the response profile into firmware source commit `5f69377 fix(audio): promote main response profile`: `k1_hardware` compiles with `DEFAULT_AUDIO_RESPONSE_GAIN=3.0f`; `k1_bench_reference` explicitly overrides to `1.0f`. Static guard added in `tests/test_audio_response_gain_static.py`.
- Verified and flashed exact commit `5f69377`: full host gate `458 passed, 39 subtests passed`; `pio run -e k1_hardware` and `pio run -e k1_bench_reference` succeeded with the known `system.h:48` volatile warning only; main flashed on `/dev/cu.usbmodem12201`; bench flashed on `/dev/cu.usbmodem12401`.
- Post-flash 75 s paired proof: `docs/forensics/runtime-evidence/20260615T084548-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, main `response_gain=3.0`, bench `response_gain=1.0`, both `12800/96`, main AP/VP rows `94/79`, bench AP/VP rows `95/79`, and zero crash-marker matches in both soak logs. Closeout note: `_scratch/main-dc-anomaly-20260615/orchestrator/14-response-profile-production-fix.md`.
- Hardened the deployed response-profile firmware after the production fix:
  - `67dc0e4 test(audio): expose response profile in boot guard` prints `response_gain` in `RUNTIME_TIMING_GUARD` and keeps the AP regression parser compatible with archived logs.
  - `81d8c6f test(calibration): lock noise cal model to firmware constants` prevents host calibration-quality constants drifting from firmware constants.
  - `50063f4 test(audio): block unsafe 32k upload path` blocks `k1_sample_rate_32k_spike` uploads even on the correct main identity and removes inherited tuple macros from sample-rate probe envs before declaring candidate timing.
- Verified the hardened source: `.venv/bin/python -m pytest tests/ -q` -> `461 passed, 43 subtests passed`; `pio run -e k1_hardware`, `pio run -e k1_bench_reference`, `pio run -e k1_ap_frontend_probe_matrix_16000_120_d3`, `pio run -e k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1`, and build-only `pio run -e k1_sample_rate_32k_spike` all succeeded with only known warnings.
- Flashed exact commit `50063f4` to both registered K1s: main `/dev/cu.usbmodem12201` -> `k1_hardware`; bench `/dev/cu.usbmodem12401` -> `k1_bench_reference`. Post-flash 75 s paired proof: `docs/forensics/runtime-evidence/20260615T091247-snappiness-manifest.json` with `timing_parity=true`, both `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `98/79`, bench AP/VP rows `93/79`, valid config calibration on both devices, and zero crash-marker matches.
- Ran the first controlled BCLK-safe candidate probe on main only: `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1` on `/dev/cu.usbmodem12201`. Verdict: **NO-GO as run**. The probe booted with `RUNTIME_TIMING_GUARD timing_ok=1`, `sample_rate=16000`, `samples_per_chunk=120`, AP core `0`, VP core `1`, then repeatedly hit task-watchdog resets on CPU0/`loopTask` before any APCAD rows were captured. Evidence: `docs/forensics/2026-06-15-16k120-live-probe-verdict.md` and `docs/forensics/runtime-evidence/20260615T0920-sample-rate-16k120-probe/`.
- Immediately restored main to `k1_hardware` and ran paired production proof: `docs/forensics/runtime-evidence/20260615T092202-snappiness-manifest.json` with `timing_parity=true`, both `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, valid config calibration on both devices, and zero crash-marker matches in restore logs.
- Added a non-shippable acquisition-only `16000/120/d3` probe and repeated the main-unit test before GDFT/onset/novelty/tempo work. First isolated run produced `1358` clean rows and then WDT'd during APCAD serial dump; addr2line resolved the backtrace to `HWCDC::write` / `Print::printFloat` inside `ap_cad_capture_dump()`. Added a serial-dump yield every 16 APCAD rows.
- Superseding acquisition-only run: `docs/forensics/runtime-evidence/20260615T0937-sample-rate-16k120-acq-probe-yield/c1_16000_120_d3_acq_probe_yield_20260615_093634__summary.json` captured `2000` rows with active `16000/120`, AP core `0`, VP core `1`, `i2s_status_counts={"0": 2000}`, `i2s_not_ok_count=0`, `bytes_mismatch_count=0`, `frame_gap_count=0`, `APCAD_CAPTURE_DONE,count=2000,dropped=0`, and zero crash-marker matches in the superseding logs.
- New sample-rate boundary: 16 kHz acquisition is viable enough to move the investigation forward, but full AP 16 kHz is still not promotable. The next blocker is AP DSP compute/yield budget at 16 kHz, not microphone/DMA byte integrity. Verdict doc: `docs/forensics/2026-06-15-16k120-acquisition-isolation-verdict.md`.
- Restored main to `k1_hardware` again and ran paired production proof: `docs/forensics/runtime-evidence/20260615T093738-snappiness-manifest.json` with `timing_parity=true`, both `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, valid config calibration on both devices, and zero crash-marker matches.
- Committed the acquisition-isolation slice as `533003a test(audio): add 16k acquisition isolation probe`; focused static gate passed (`57 passed, 29 subtests`), full host gate passed (`463 passed, 43 subtests`), and `pio run` passed for `k1_hardware`, `k1_bench_reference`, and `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe` with only known warnings.
- Flashed committed `533003a` to both registered K1s: main `/dev/cu.usbmodem12201` -> `k1_hardware`, bench `/dev/cu.usbmodem12401` -> `k1_bench_reference`. Post-flash paired proof: `docs/forensics/runtime-evidence/20260615T094608-snappiness-manifest.json` with `timing_parity=true`, both `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `99/79`, bench AP/VP rows `90/79`, valid config calibration on both devices, and zero crash-marker matches.
- Added 16 kHz AP stage profiling (`SB_AP_STAGE_PROBE_STOP_STAGE`) and captured live main-unit probes. GDFT, novelty, snapshot, onset, and saliency stage probes held ~`133.3 Hz` AP cadence with clean I2S and zero crash markers; `stage_tempo` dropped to `123.149 Hz` AP / `41.044 Hz` accepted novelty with `i2s_status=0`, `bytes_mismatch_count=0`, and p95 loop `11265.7 us`. Verdict: the first hard 16 kHz full-AP blocker is `sb_tempo_update()` / ACF update cost, with GDFT as a large but survivable steady budget item. Evidence: `docs/forensics/2026-06-15-16k120-ap-stage-profile-verdict.md`.
- Committed the AP stage profiler as `6d5b476 test(audio): profile 16k AP stage budget`, flashed it to both registered production envs, and recorded paired proof: `docs/forensics/runtime-evidence/20260615T101430-snappiness-manifest.json` with `timing_parity=true`, both `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `98/79`, bench AP/VP rows `88/79`, valid config calibration on both devices, and zero crash-marker matches.
- Added tempo-internal diagnostic fields under `ENABLE_TEMPO_STREAM` and captured `stage_tempo` again at `16000/120/d3`. Verdict: `sb_compute_acf_salience()` is the dominant blocker (`4736 us` median, `4876 us` p95; `87.3%` of tempo emit median), with AP cadence at `120.124 Hz`, accepted novelty at `40.056 Hz`, clean I2S, and zero crash-marker matches. Evidence: `docs/forensics/2026-06-15-16k120-tempo-internal-profile-verdict.md` and `docs/forensics/runtime-evidence/20260615T1020-sample-rate-16k120-tempo-internal/`.
- Restored main 1401 to `k1_hardware` after the non-shippable probe and ran paired production proof: `docs/forensics/runtime-evidence/20260615T102502-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both devices at `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, valid config calibration on both devices, and zero crash-marker matches.
- Committed the tempo-internal profiler as `a255ab4 test(audio): profile 16k tempo internals`, flashed it to both registered production envs, and recorded paired proof: `docs/forensics/runtime-evidence/20260615T103636-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `98/79`, bench AP/VP rows `93/79`, valid config calibration on both devices, and zero crash-marker matches.
- Added a non-shippable ACF amortisation probe (`SB_TEMPO_ACF_REFRESH_DECIMATION=8`) and captured `stage_tempo` again at `16000/120/d3`. Verdict: mean AP/novelty cadence recovered (`133.280 Hz` AP, `44.451 Hz` novelty), I2S stayed clean, and crash scan was clean, but p95 loop time remained over budget (`9137 us`) because heavy ACF refresh frames still exist. Evidence: `docs/forensics/2026-06-15-16k120-acf-amortisation-probe-verdict.md` and `docs/forensics/runtime-evidence/20260615T1045-sample-rate-16k120-tempo-acf-d8/`.
- Restored main 1401 to `k1_hardware` after the ACF-d8 probe and ran paired production proof: `docs/forensics/runtime-evidence/20260615T104510-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both devices at `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, valid config calibration on both devices, and zero crash-marker matches.
- Committed the ACF amortisation probe as `c32cd25 test(audio): probe 16k tempo acf amortisation`, flashed it to both registered production envs, and recorded paired proof: `docs/forensics/runtime-evidence/20260615T105035-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `98/79`, bench AP/VP rows `89/79`, valid config calibration on both devices, and zero crash-marker matches.
- Wrote the next implementation plan for ACF work-spreading: `docs/forensics/2026-06-15-16k120-acf-work-spreading-plan.md`. Decision: ACF-d8 proves amortisation is the right lever for mean cadence, but the next production-relevant probe must spread lag-table work so worst-frame/p95 loop time falls below the 7.5 ms AP period instead of merely reusing stale ACF most frames.
- Implemented and captured the non-shippable ACF spread-16 probe as `401599e test(audio): spread 16k tempo acf work`. Live main-unit result at `16000/120/d3`: AP cadence `133.340 Hz`, accepted novelty `44.447 Hz`, `i2s_not_ok_count=0`, `bytes_mismatch_count=0`, `frame_gap_count=0`, zero timestamp regressions, zero crash markers, `tempo_acf_elapsed_us` p95 `1028 us`, but total AP loop p95 `9591 us` against the `7500 us` AP period. Verdict: ACF work-spreading is real progress, but `16000/120/d3` remains research-only; next blocker is GDFT/I2S/full-frame p95, not ACF alone. Evidence: `docs/forensics/2026-06-15-16k120-acf-spread16-probe-verdict.md` and `docs/forensics/runtime-evidence/20260615T1149-sample-rate-16k120-tempo-acf-spread16/`.
- Verified the committed ACF spread slice: `.venv/bin/python -m pytest tests/ -q` -> `467 passed, 57 subtests passed`; `pio run -e k1_hardware -e k1_bench_reference -e k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread16` succeeded with known warnings only.
- Flashed exact commit `401599e` back to both registered production envs: main `/dev/cu.usbmodem12201` -> `k1_hardware`, bench `/dev/cu.usbmodem12401` -> `k1_bench_reference`. Final paired proof: `docs/forensics/runtime-evidence/20260615T115934-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both devices `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `98/79`, bench AP/VP rows `95/79`, valid config calibration on both devices, and zero crash-marker matches.
- Added active AP work metrics to the APCAD capture summary and captured two finer non-shippable ACF spread probes at `16000/120/d3`. Spread12 improved the row budget but still failed emitted active-work p95 (`7528 us`) with `27` emitted rows over `7500 us`; spread8 passed the 10 s stage-tempo active-work gate with AP `133.353 Hz`, novelty `44.449 Hz`, clean I2S, zero frame gaps, zero timestamp regressions, `tempo_acf_elapsed_us` p95 `524 us`, active-work p95 `7050.75 us`, emitted active-work p95 `7213.8 us`, active max `7451 us`, and `0` active/emitted rows over `7500 us`. Evidence: `docs/forensics/2026-06-15-16k120-acf-spread8-active-budget-verdict.md`, `docs/forensics/runtime-evidence/20260615T1214-sample-rate-16k120-tempo-acf-spread12/`, and `docs/forensics/runtime-evidence/20260615T1218-sample-rate-16k120-tempo-acf-spread8/`.
- Committed the active-budget slice as `c89e576 test(audio): prove 16k spread8 active budget`. Verification: focused timing/upload/Nyquist/rate gate `62 passed, 40 subtests passed`; full host gate `.venv/bin/python -m pytest tests/ -q` -> `467 passed, 57 subtests passed`; `pio run -e k1_hardware -e k1_bench_reference -e k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread12 -e k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread8` passed with known warnings only.
- Restored both registered K1s to exact committed production envs after the non-shippable probe work: main `/dev/cu.usbmodem12201` -> `k1_hardware`, bench `/dev/cu.usbmodem12401` -> `k1_bench_reference`. Final paired proof: `docs/forensics/runtime-evidence/20260615T122639-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both devices `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `99/79`, bench AP/VP rows `89/79`, valid config calibration on both devices, and zero crash-marker matches. This does not promote 16 kHz; it closes the current slice with both K1s back on production firmware.
- Ran the next live spread8 proof phase. Main-only 17 s no-drop APCAD at `16000/120/d3` captured `2267/2304` rows, `dropped=0`, AP `133.325 Hz`, novelty `44.448 Hz`, clean I2S, no frame gaps, no timestamp regressions, `tempo_acf_elapsed_us` p95 `540.4 us`, active-work p95 `6940 us`, emitted active-work p95 `7133 us`, active max `7407 us`, and `0` active/emitted rows over `7500 us`. Then ran a 75 s mixed AP/VP soak with main on the non-shippable spread8 probe and bench on production: `failure=null`, expected `timing_parity=false`, main `16000/120`, bench `12800/96`, both AP/VP rows `79/79`, and zero crash-marker matches. Evidence: `docs/forensics/2026-06-15-16k120-spread8-extended-runtime-verdict.md`, `docs/forensics/runtime-evidence/20260615T123733-sample-rate-16k120-tempo-acf-spread8-17s/`, and `docs/forensics/runtime-evidence/20260615T123849-sample-rate-16k120-spread8-apvp-75s/`.
- Restored both registered K1s again to production envs after the spread8 extended runtime phase. Production proof: `docs/forensics/runtime-evidence/20260615T124154-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both devices `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `98/79`, bench AP/VP rows `91/79`, valid config calibration on both devices, and zero crash-marker matches.
- Added and committed the full-AP spread8 probe as `ea12acd test(audio): add full ap 16k spread8 probe`. The new env is non-shippable (`k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread8`), extends the AP0/VP1 `16000/120/d3` candidate without a stage stop, and leaves production envs unchanged. Verification: focused static/rate gate `62 passed, 40 subtests passed`; new env build passed; full host gate passed after runtime (`467 passed, 57 subtests passed`).
- Full-AP spread8 runtime passed the next gate on main K1. The 17 s no-drop APCAD run at `16000/120/d3` captured `2267/2304` rows, `dropped=0`, AP `133.341 Hz`, novelty `44.444 Hz`, clean I2S, no frame gaps, no timestamp regressions, `tempo_acf_elapsed_us` p95 `549.8 us`, active-work p95 `6932.7 us`, emitted active-work p95 `7121.2 us`, active max `7474 us`, and `0` active/emitted rows over `7500 us`. The 75 s mixed AP/VP soak with main on full-AP spread8 and bench on production had `failure=null`, expected `timing_parity=false`, both AP/VP rows `79/79`, and zero crash-marker matches. Evidence: `docs/forensics/2026-06-15-16k120-full-ap-spread8-runtime-verdict.md`, `docs/forensics/runtime-evidence/20260615T124922-sample-rate-16k120-full-ap-acf-spread8-17s/`, and `docs/forensics/runtime-evidence/20260615T125136-sample-rate-16k120-full-ap-spread8-apvp-75s/`.
- Restored both registered K1s again to production envs after the full-AP spread8 probe. Production proof: `docs/forensics/runtime-evidence/20260615T125550-snappiness-manifest.json` with `failure=null`, `timing_parity=true`, both devices `12800/96`, main `response_gain=3.0`, bench `response_gain=1.0`, main AP/VP rows `98/79`, bench AP/VP rows `90/79`, valid config calibration on both devices, and zero crash-marker matches.

## 2026-06-15 Phase 3/4/5 Runtime Deployment

- Implemented and committed `03b7cdf fix(firmware): prove phase345 runtime controls`: safe `:event_status` percussion readout, palette-offset colour authority, explicit-channel `:slot_save`, and the paired runtime proof harness.
- Verified host gate: `python3 -m pytest tests/ -q` -> 441 passed; `pio run -e k1_hardware` and `pio run -e k1_bench_reference` -> success with the known `system.h:48` volatile warning only.
- Flashed the exact commit to both registered devices: 1401 main K1 (`F887A500`) on `k1_hardware` via `/dev/tty.usbmodem12201`; 12201 bench K1v2 (`B489A500`) on `k1_bench_reference` via `/dev/tty.usbmodem12401`.
- Runtime proof manifest `docs/forensics/runtime-evidence/20260615T024851-phase345-runtime-proof-manifest.json`: failure null, both devices restored mode 8 after slot-save/load/queue commit, and complete percussion-event fields were observed.
- Post-flash 75 s soak manifest `docs/forensics/runtime-evidence/20260615T024954-snappiness-manifest.json`: failure null, timing parity true, both devices at `sample_rate=12800` and `samples_per_chunk=96`, AP/VP cadence present, and zero crash/reset markers in soak logs.
- No noise calibration, erase, reset, factory reset, restore defaults, or destructive commands were run in this phase. Preset slots 1-3 are now valid on both devices because the proof attempts saved captured primary-mode presets.

## 2026-06-10 VPML Host-Authoring / Workbench Slice — CLOSED

Captain closeout of the host-side VPML authoring slice (no device access — bench K1 explicitly blocked).

- **Completed:** VPML compiler; parameter editor; preset A/B recall; host-only recipe-deck authoring; save/load/compile recipe variants; hard command-length gate against the firmware parser limit; workbench defaults to **Device Disabled** (no K1 access unless restarted with `--allow-device`).
- **Verified (Captain):** Python syntax clean; workbench home `200`; compile-recipe action `200`; UI shows Device Disabled; recipe compile reports `host_manual`, `device_sequencing=false`; saved variants within parser cap (66/93, 85/93); host server responding at `http://127.0.0.1:8766`.
- **Closeout boundary:** closes the host-side authoring/workbench slice ONLY — does **NOT** close visual acceptance, VPAB proof, production promotion, or live-K1 recipe-run proof, because bench K1 access was explicitly Captain-blocked.
- **Landed:** source + recipe evidence + 12201 snappiness device-capture logs committed and merged to `main` (`5c96cad`, `f0c6808`); tree clean.

## 2026-06-10 Weekly Closeout Audit + Gate/Ledger Repair

- Ran a 4-agent closeout audit of 2026-06-03..2026-06-10 (git / on-disk docs / test-gate / memory). Canonical report: `docs/forensics/2026-06-10-weekly-closeout-audit.md`.
- **Verdict (at audit time):** the week's work was NOT closed out — unmerged (0/208 to main), partly uncommitted (~78 paths), eyes-on-pending. No feature meets the full closeout bar.
- **Update (same day, post-audit — Captain-directed):** working tree committed in 6 scoped units and **merged to main** (fast-forward, `main` @ `1ad084e`); `wip` + `main` pushed to origin. Gates run on the merged state: host pytest **310 passed**, `pio run -e k1_hardware` **SUCCESS** (RAM 40.4% / Flash 18.7%), `pio run -e tab5` **SUCCESS**. This integrates **source** only — main is now a host-green + compiles baseline. **Device eyes-on remains THE open gate** for the forward-graft, effect modes 18/19/20/21, WS control / noise-cal-arm path, and VPML. Quarantine branch `wip/2026-06-07-unfinished-lanes-quarantine` (6 dirty lanes) was deliberately **NOT** merged. *(main has since advanced to `f0c6808` with Codex's recipe-deck compiler + 12201 snappiness evidence; tree clean.)*
- **Host gate was RED → restored GREEN.** Two static tests went stale after the dual-channel boot-intro rewrite (`cd832fa`) + VPML render-params refactor: `test_boot_intro_static` (secondary bounce now parameterised via `params.secondary_phase`) and `test_vp_motion_lab_static` (frame count now dynamic via `vpml_frame_count_for_program`). Both assertions updated to match; firmware logic unchanged. `.venv` test deps repaired (installed pytest + scipy; numpy/yaml already present). Re-run: `.venv/bin/python3 -m pytest tests/ -q` → **309 passed, 20 subtests passed**.
- **Containment baseline corrected.** The 2026-06-07 "empty diff above `13ffe00`" check (below) is point-in-time and **superseded** — 7 firmware commits have since landed legitimate feature work above it (boot-intro rewrite `cd832fa`, AP WebSocket `k1.*` protocol `59b6023`/`b748678`, hardened wireless `e6a1954`, WS control facade `e6a6fbb`, framed VPAB transport gate `d915c60`, VPML `88a1bc3`). These are NOT the VME-incident forbidden edits; `13ffe00` is simply no longer a valid empty-diff reference.
- **Three lanes registered in spec-index** that had landed 2026-06-09 but were unrecorded: K1 wireless control (WS v2), Tab5 wireless controller (separate ESP32-P4 PIO project), VP Motion Lab (VPML, non-shippable dev env). `.claude/handoff.md` re-pointed.
- **Still Captain-gated (unchanged by this pass):** device eyes-on batch (forward-graft + modes 18/19/20/21 + Dense Forge exact-source); quarantine disposition (6 dirty lanes); merge-to-main strategy; VME reopen + 1401 firmware restore; Scene Policy v2 / AV Regression promotion.
- No firmware behaviour changed, no device touched, no commit/push in this pass — test-assertion + doc reconciliation only.

## 2026-06-07 VMEWT Transport Incident Containment

- Canonical incident report: `docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md`.
- Verdict: attempted VMEWT hardware capture is `FAILED / TRANSPORT INVALID / NOT RUNTIME PROOF`.
- Reported failed captures had nonzero rejected records, ignored fragments, malformed-token issues, secondary-only coverage, and weak-confidence-only scenario coverage. Survivor rows are not proof.
- Canonical containment check: firmware/platformio diff above the VME docs baseline remains empty with `git diff --name-status 13ffe00..HEAD -- SPECTRASYNQ_K1_FIRMWARE platformio.ini`. **> Superseded 2026-06-10 — this diff is no longer empty; legitimate WS/VPML/boot-intro feature commits have since landed firmware above `13ffe00`. See the 2026-06-10 section above. `13ffe00` is no longer a valid empty-diff containment reference.**
- Failed VMEWT edits/captures were sandbox-only under `/tmp/k1_vme_waveform_BloAgX/SensoryBridge-main 9`; do not import them into canonical.
- K1 1401 was flashed with non-shippable VME probe builds during the failed lane. Restore or verify normal `k1_hardware` on exact device identity before product testing; do not run calibration as part of that restore.
- VME hardware capture is frozen. Reopen only from corrupt-log red tests, fail-closed parser gates, bounded deferred diagnostic records with sequence/length/CRC, zero dropped/corrupt/overflow, and paired current-vs-VME final-byte records for modes 7/8/18 primary and secondary.
- Do not patch Dense Forge, Scene Policy, Smart Director, Phase 2B, `led_utilities.h`, AGC, calibration, brightness, silence thresholds, or production Waveform effects from this incident.

## 2026-06-07 VME L1 Waveform Sandbox Start

- Preserved all unfinished June 7 dirty work on quarantine branch `wip/2026-06-07-unfinished-lanes-quarantine` at `a40bdb8 wip: quarantine unfinished June 7 lanes`.
- Returned `wip/audio-saliency-recovery` to a clean `13ffe00` firmware-source baseline before VME planning, then committed VME handover docs above it. Verify current branch HEAD live before using the handover.
- Created `docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md` as the next-agent authority.
- VME L1 target effects are now Waveform Fast (mode 7), Waveform (mode 8), and Waveform Tempo (mode 18).
- VME L1 scope is sandbox/shadow only: final-byte proof, no production behaviour change, no L2 Memory, no Smart Director, no calibration/AGC/Phase 2B, and no quarantine-branch merge.

## 2026-06-07 Secondary dark-state + Dense Forge

- Dense Forge mode 21 recovery accepted by Captain eyes-on. Committed `a5ce32e fix(vp): restore Dense Forge transport`; source-scoped closeout: `docs/handover/2026-06-07-dense-forge-closeout.md`.
- Exact `a5ce32e` `k1_hardware` build PASS from a clean detached worktree. Evidence: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-build.log`.
- Exact `a5ce32e` flash to 1401 PASS after Cursor released the serial port. Evidence: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-upload.log`, `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-post-upload.log`.
- 1401 configured for locked Dense Forge mode 21 with Smart Scene off and AP/VP streams off. Evidence: `docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-mode21-setup.log`.
- Primary silence creep materially fixed (Phase 1B envelope-fall + Phase 2 VP normalization); Captain eyes-on PASS on primary going dark in quiet room. Evidence: `docs/forensics/runtime-evidence/2026-06-07-silence-anti-creep-verdict.md`.
- Secondary dark-state root-caused: mode 18 (Waveform Tempo) repainted from persistent history every frame. Verdict: `docs/forensics/runtime-evidence/2026-06-07-secondary-dark-state-last-writer-verdict.md`.
- Secondary fix implemented in `light_mode_waveform_tempo.cpp` (dark gate + history drain) and flashed to 1401 (`F887A500`). Captain eyes-on re-test **pending**.
- Handover authority: `docs/handover/2026-06-07-secondary-dark-state-handover.md`. Spec routing: `docs/spec-index.md`, session pointer: `.claude/handoff.md`.
- Scene Policy v2 lane **continues in parallel** (not superseded by secondary-dark work).

## 2026-06-07 Scene Policy v2 Start

- Deferred production promotion of the K1 AV Regression v2 RC evidence package. The tree is evidence-assembled, not release-promoted: weak-lock confidence evidence still needs matrix reconciliation, and product fit is deferred to Scene Policy v2 A/B validation.
- Reclassified current Smart Auto evidence as mode-safety only: bounded switching and no disabled/deprecated modes are proven, but product fit, musical relevance, and two-K1 perceptual A/B are deferred to Scene Policy v2.
- Created `docs/forensics/scene_policy_v2/2026-06-07-scene-policy-v2-handover.md` as the next-phase source of truth for named 20-30 second trajectories, beat/onset event gates, and promotion criteria.
- Uploaded post-Scene-Policy-v2 `k1_hardware` to the main K1 and reran the production-smoke AV pack. Fresh device matrix is `PARTIAL`, not production-green: runtime guard passed and hard generated-80 BPM fixture failures were blocked from required gates, but weak-lock classifications remain and `silence_noise` still reports false onset activity.
- Ran the next weak-lock probe slice under non-shippable APCAD/NOV diagnostics, added gain-normalised `ffplay` support to the APCAD runner, recaptured weak-lock controls, and restored `k1_hardware`. `slow_84_syncopated`, `click_127`, and `fast_127_fourfloor` now have declared-rate NOV replay proof with target lock; `loreen_127` has healthy cadence and near-target timing but remains weak-lock because bounded replay still has zero high-confidence/locked warm rows.
- Closed the targeted silence/open-quiet P1 with a post-floor VU permission gate in onset and tempo paths. Device proof at `3295c435bb45d7c34612b8466707afaafbec1fcd`: `silence_noise` reports `PASS_no_false_tempo_lock_under_verified_taped_mic`, `PASS_event_layer_quiet`, and `0.0` onsets/minute in `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-silence-open-quiet-vu-gate.md`.
- Ran the Scene Policy v2 two-K1 serial A/B state gate across the expanded nine-clip corpus. Evidence: `docs/forensics/runtime-evidence/2026-06-07-scene-policy-v2-serial-ab-state-gate.md`; manifest/logs: `docs/forensics/runtime-evidence/2026-06-07T073758-smart-auto-ab-*`. State gate passed, but visual product judgement remains open because no camera/video device was attached.
- Reconciled weak-lock matrix policy: `slow_84_syncopated`, `click_127`, and `fast_127_fourfloor` are closed by declared-rate NOV replay proof; only `loreen_127` remains a scoped P2 confidence residual. Harness: `WEAK_LOCK_NOV_RECONCILED_FIXTURES` in `k1_av_layer_classifier.py`. Evidence: `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-weak-lock-matrix-reconciliation.md`.
- Recovered main K1 primary channel on `/dev/tty.usbmodem12201`: `:clear_noise_cal`, N→Y recal, `:smart_scene=l1`. Root cause was SSL overshoot + intermittent VP chroma gate collapse, not a firmware regression. Evidence: `docs/forensics/runtime-evidence/2026-06-07-stuck-primary-12201-swarm-verdict.md`, serial log `2026-06-07T12201-recovery-serial.log`.

## Session Log

- Started read-only investigation for the Pharap FixedPointsArduino dependency in `/Users/spectrasynq/SensoryBridge-main 9`.
- Checked current repo state: branch `refactor/main`; unrelated untracked files were already present.
- Searched memory index for `FixedPoints`, `SQ15x16`, native VP, and refactor lane evidence.
- Created `task_plan.md`, `findings.md`, and `progress.md` as recovery checkpoints.
- Read `.claude/CLAUDE.md`, `.claude/skills/sensorybridge-doctrine/SKILL.md`, refactor handover/audit/matrix/hardware-gate docs, and current hardware definition.
- Confirmed active `AGENTS.md` reference-doc paths are missing in this repo; located reference copies in the WLED/Lightwave-Ledstrip workspace and treated them as reference-only.
- Mapped current `SQ15x16` usage and current include state across the split multi-TU tree.
- Ran `pio run -e k1_hardware_harness`: PASS in 4.36 s, flash 584902, RAM 83496, known `system.h:48` volatile warning.
- Ran `pio run -e k1_hardware`: PASS in 3.91 s, flash 562662, RAM 83120, same known warning.
- Searched current external sources for fixed-point and DSP options: Pharap FixedPointsArduino, CNL, libfixmath, fpm, FR_Math, and Espressif ESP-DSP.
- Read the named skills enough to apply the relevant guardrails: API boundary protection, testing strategy, architecture/ADR framing, build-system constraints, file-backed planning, and Superpowers planning/worktree/subagent rules. Did not spawn subagents because this was a read-only single-lane analysis, not an explicit parallel-agent execution request.
- Added Espressif IQMath to the candidate set after checking the ESP Component Registry.
- Wrote `docs/forensics/2026-05-25-fixedpoints-modernisation-options.md`.
- Updated `task_plan.md` phases 2-5 to complete.
- Emitted PIP-40 `ready` event after correcting the command from unsupported `--value` to `--detail`.
- Started Phase 6 parallel SSA Level 1 research pass at Captain request.
- Dispatched six read-only scouts: usage inventory, ecosystem candidates, ESP32-S3 performance/toolchain, regression gates, architecture/API boundary, and licence/governance.
- Ran local source synthesis while scouts worked: config/public API boundary, render colour path, VP Tier A/Tier B gates, GDFT/AGC numeric path, harness scripts, and FixedPoints vendoring files.
- Created draft `docs/forensics/2026-05-25-fixedpoints-level1-research-vectors.md` for scout merge.
- Merged Scout A inventory findings into the Level 1 dossier and marked Scout A complete.
- Merged Scout C performance/toolchain findings into the Level 1 dossier and marked Scout C complete.
- Received Scout B ecosystem shortlist and rechecked current external sources for `fpm`, FR_Math, ESP-DSP, IQMath, libfixmath, CNL, and Pharap.
- Received Scout D regression/parity gate report and merged FP-0 approval evidence into the Level 1 dossier.
- Received Scout F licence/governance report and merged vendoring, NOTICE, SBOM, and candidate-governance findings.
- Interrupted Scout E for an immediate return after two waits; no usable architecture/API report returned before synthesis cutoff, so the dossier records that limitation.
- Updated `docs/forensics/2026-05-25-fixedpoints-level1-research-vectors.md`, `task_plan.md`, and `findings.md` with the final Phase 6 synthesis.

## 2026-05-27 Codex Agent Continuation / Parallel Lane Triage

- Restored existing planning files and confirmed they describe a completed FixedPoints/SQ15x16 research lane.
- Searched memory index for `feat/gdft-harness`, `GDFT`, Smart Visual Engine, and related prior-work entries.
- Checked live git state: branch `feat/gdft-harness`, HEAD `e63e5be`, dirty tree with Smart Visual Engine modules untracked.
- Read `.claude/CLAUDE.md`, `k1-firmware-change-gate`, `sensorybridge-doctrine`, perception-first guidance, refactor matrix, freeze baseline, and Smart Visual Engine plan/strategy docs.
- Confirmed AGENTS reference-doc paths are absent in this checkout.
- Spawned three read-only side agents: prior-work summariser, safe-parallel-lane architect, and manual/show ownership seam scout.
- Ran static-only verification: smart visual static tests PASS, dev-instrumentation boundary tests PASS, trace-dev static tests PASS.
- Appended Phase 7 recovery/triage state to `task_plan.md`, `findings.md`, and `progress.md`.
- Received prior-work scout summary: last committed stack ended at `e63e5be`; uncommitted lanes are calibration/profile hardening, trace-dev attribution, Smart Visual Engine strategy/source, and current VP/AP smart-control scaffolding.
- Received architecture scout summary: safest product lane is EdgeMixer-lite core only, with `.ino` integration and hook modulation waiting for current-agent reconciliation.
- Received ownership scout summary: active source has no global owner enum; current smart owner helper covers queued transitions, fallback-mode drift, and recent encoder activity, but not all serial/typed/preset/palette/auto-colour mutation surfaces.
- Marked Phase 7 triage phases complete in `task_plan.md`.

## 2026-05-28 Safe Sidecar Development

- Applied the doctrine/change-gate boundary for a disjoint sidecar pass: no `.ino`, mode-selection, Smart Director, onset/beat, visual hooks, serial, calibration, upload, or trace-dev production promotion.
- Added EdgeMixer-lite static tests first, then implemented fail-closed enum sanitisation in `SPECTRASYNQ_K1_FIRMWARE/sb_edgemixer_lite.cpp`.
- Added offline Smart Visuals parser tests first, then implemented `scripts/regression-harness/smart_visuals_gate.py`.
- Wrote `docs/forensics/2026-05-28-smart-assist-ownership-merge-checklist.md` with source-truth ownership facts, merge gates, runtime-proof inputs, and current no-touch boundaries.
- Ran focused static/unit verification: EdgeMixer-lite static tests PASS, Smart Visuals parser tests PASS, Smart Visual Engine static tests PASS, developer-instrumentation boundary tests PASS, trace-dev static tests PASS.
- Ran offline parser smoke against `docs/forensics/runtime-evidence/2026-05-27-k1-smart-edge-vpabb-music-v2.log`; parsed 162 `VPABB` rows and wrote `/tmp/k1_smart_visuals_gate_summary.json`.
- Ran compile-only verification with `PLATFORMIO_BUILD_DIR=/tmp/k1_sidecar_pio_build_20260528 pio run -e k1_hardware`: PASS, with the existing `system.h:48` volatile increment warning.

## 2026-05-28 Highest-Value Next Lane Planning

- Confirmed `.Codex/harness/` is absent, so no agent-progress-harness boot script is available in this checkout.
- Spawned three read-only scouts for product value, firmware pipeline, and evidence reality-check review.
- Refreshed Smart Visual source truth after the checkout changed: Smart Edge and Onset/Beat Stage A now have 2026-05-28 evidence docs and plans.
- Re-ran focused local verification: Onset/Beat replay tests PASS, Onset/Beat metrics tests PASS, Smart Visual Engine static tests PASS, replay script PASS, and existing main/bench v5 runtime logs parse valid.
- Initial local selection was Visual Event Bus L1 Accent because Onset/Beat Stage A has become a proven producer while `sb_visual_hooks.*` remains a merged one-pulse consumer.
- Reconciled subagent feedback: product scout preferred Smart Assist validation, firmware scout required validation hardening before tuning, and reality-check scout rejected any onset/beat or hook quality claim without stronger evidence.
- Updated `docs/forensics/2026-05-28-next-highest-value-lane-visual-event-bus-l1.md` to select Smart Assist / Onset validation hardening first, with L1 Accent as the likely implementation follow-up after the gate is trustworthy.

## 2026-05-28 OnsetDetector / BeatTracker-Lite E2E Plan

- Restored existing `task_plan.md`, `findings.md`, and `progress.md`; confirmed they were carrying older FixedPoints and Smart Visual Engine phases.
- Searched memory for Smart Visual Engine, shared AP snapshot, Onset/Beat, donor audio, and MusicAware/SongAware reference decisions.
- Spawned three read-only plan-review SSAs: firmware-seam scout, test/harness scout, and architecture/donor-algorithm scout.
- Created `docs/superpowers/plans/2026-05-28-onset-beat-lite-e2e-execution.md`.
- Updated `task_plan.md` with Phase 9 for the OnsetDetector / BeatTracker-lite plan.
- Updated `findings.md` with Stage A source-truth and architecture findings.
- Received all three read-only SSA plan reviews and integrated the material deltas into the plan: O(1) AP constraint, no extra spectrogram scans, real-event-only beat flag for Stage A, stronger replay scenarios, and stronger parser/event-quality metrics.
- Did not edit firmware source, open serial, upload, or run calibration in this planning phase.

## 2026-05-28 OnsetDetector / BeatTracker-Lite E2E Execution

- Deployed three SSAs: replay harness, event-metrics parser, and read-only risk review.
- Implemented the Stage A native onset/beat refinement in `sb_onset_beat.cpp` without importing donor `OnsetDetector`, `BeatTracker`, `TempoTracker`, `MusicalGrid`, or `ControlBusFrame`.
- Added host replay and parser tooling:
  - `scripts/regression-harness/onset_beat_replay.py`
  - `tests/test_onset_beat_replay.py`
  - `scripts/regression-harness/onset_beat_event_metrics.py`
  - `tests/test_onset_beat_event_metrics.py`
- Tightened Smart module static purity checks to forbid serial, WiFi, and FastLED tokens inside `sb_*` smart modules.
- Ran full host suite: `python3 -B -m unittest discover -s tests` -> 74 tests OK.
- Built production, bench, harness, and trace-dev envs successfully.
- Uploaded production firmware to main K1 `/dev/tty.usbmodem101` and bench K1 `/dev/tty.usbmodem2101`.
- Ran iterative hardware tuning captures v1-v5. Accepted v5: main `143.36 events/min`, bench `91.99 events/min`, both `max beat_confidence=1.0`, both storm guards false.
- Flashed non-shippable harness to the main K1 for VPABB proof, captured 146 VPABB rows, saw zero drops/overflows, no visual-safety failures, and Smart Assist primary mode switching `3 -> 8` while secondary stayed `7`.
- Restored main K1 to production firmware and captured final production restore evidence.
- Wrote `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md`.

## 2026-05-28 Visual Event Bus L1 Accent Execution

- Reviewed Captain's v0.3 Visual Event Bus / L1 Accent handoff and identified must-fix corrections before execution: `k1_hardware_dev` env mismatch, setter typo, exact trace-proof contradiction, missing tests, and beat-only boundary runtime risk.
- Dispatched three read-only SSAs: firmware hazard review, test/verification review, and adversarial evidence review. They are data-only reviewers; canonical source edits remain PM-owned.
- Created `docs/superpowers/plans/2026-05-28-visual-event-bus-l1-accent-execution.md`.
- Appended Phase 11 state to `task_plan.md` and recorded initial L1 findings in `findings.md`.
- Integrated SSA deltas into the L1 plan: producer-owned `event_age_ms`, host `visual_hooks_replay`, no immediate silence reset claim, explicit EdgeMixer A/B preconditions, `consumer-trace-only` status, and no full verified claim without producer trace expansion.
- Added failing-first host/static proof for the L1 hook contract:
  - `scripts/regression-harness/visual_hooks_replay.py`
  - `tests/test_visual_hooks_replay.py`
  - strengthened `tests/test_smart_visual_engine_static.py`
  - strengthened `tests/test_trace_dev_static.py`
- Implemented the L1 Accent consumer in `sb_visual_hooks.*`: independent onset/bass/beat pulses, per-band watermarks, per-band tau/coefficient config, clamped scalar outputs, beat-only switch-boundary confirmation, and producer-owned `event.event_age_ms` freshness.
- Updated the render call site to initialise the four-field `SBVisualHookOutput` and added trace-dev scopes for `vp_bus_read` and `vp_visual_hooks_tick`.
- Ran focused red/green checks: visual-hook replay PASS, L1 static contract PASS, and trace-dev static scope PASS.
- Ran full local regression suite: `python3 -B -m unittest discover -s tests` -> 75 tests OK.
- Built firmware environments successfully: `k1_hardware`, `k1_hardware_trace_dev`, and `k1_hardware_harness`.
- Ran production shippability audit: no `mabutrace` symbols linked in `k1_hardware` or `k1_hardware_harness`.
- Did not upload or open serial in this pass. Hardware trace-dev and visual A/B evidence remain pending Captain capture / explicit runtime-test lane.
- Captain then made two K1s available on `/dev/tty.usbmodem1101` and `/dev/tty.usbmodem1401` for unrestricted runtime testing.
- Serial-ROM upload failed on both named devices with esptool `Failed to connect to ESP32-S3: No serial data received`.
- Verified USB-JTAG identity with OpenOCD adapter serials:
  - 1101: `B4:3A:45:A5:87:F8`
  - 1401: `B4:3A:45:A5:89:B4`
- Flashed `k1_hardware_trace_dev` to 1101 by OpenOCD `program_esp`; all verify steps passed.
- Trace capture then failed because the USB CDC command surface timed out while enabling L1 Accent state.
- Restored 1101 to production `k1_hardware` by OpenOCD `program_esp`; all verify steps passed.
- Flashed/restored 1401 to production `k1_bench_reference` by OpenOCD `program_esp`; all verify steps passed.
- Post-restore `:version` probes on both named devices wrote successfully but returned zero response lines, so runtime trace/serial evidence is blocked by the current USB CDC command surface.
- Wrote blocked runtime attempt log: `docs/forensics/runtime-evidence/2026-05-28-k1-l1-accent-trace-attempt-blocked.log`.
- Continued runtime recovery after Captain challenged the stop condition.
- Killed a stale OpenOCD server on port 3333; after that, main K1 `/dev/tty.usbmodem1101` USB-JTAG flash and USB CDC typed commands recovered.
- Verified main K1 production and trace-dev command surface with `:version` returning `VERSION: 40103`.
- Captured trace-dev L1 Accent run v3 and Smart Assist control run v1 on main K1; each produced 5,465 MabuTrace events.
- Updated `scripts/regression-harness/sb_trace_l1_gate.py` to implement the plan's baseline P99 widening criterion instead of only an absolute hook P99 threshold, and added `tests/test_sb_trace_l1_gate.py`.
- Ran full Python regression suite: `python3 -B -m unittest discover -s tests` -> 77 tests OK.
- Ran baseline-aware L1 trace gate: PASS, `vp_visual_hooks_tick` p99 `172us` vs Smart Assist control `186us` (`-7.53%`, threshold `+10%`); `vp_bus_read` p99 `38us`.
- Rebuilt `k1_hardware` and `k1_hardware_harness`; both passed with known warnings only.
- Re-ran production instrumentation boundary audit; `nm ... | grep -i mabutrace` returned no matches for `k1_hardware` and `k1_hardware_harness`.
- Restored main K1 to production `k1_hardware` by USB-JTAG flash/verify, confirmed `:version`, then disabled AP/VP streams.
- USB CDC recovery experiment found `USB.begin()` is the wrong fix under `ARDUINO_USB_MODE=1`; that bad source change was reverted. Bench K1 `/dev/tty.usbmodem1401` stopped enumerating after the bad bench flash and likely needs physical power-cycle or BOOT-mode recovery before reflashing.

## 2026-05-28 Smart Scene Runtime Preset Control

- Treated Captain's 1101-vs-1401 L1 pass verdict as new source truth for the scoped L1 Accent lane.
- Updated `docs/forensics/2026-05-28-visual-event-bus-l1-accent-runtime-evidence.md` to record the scoped Captain visual A/B pass and keep broader autonomy/quality claims out of scope.
- Added a failing-first static contract for a new typed `smart_scene` command in `tests/test_smart_visual_engine_static.py`.
- Implemented `smart_scene=[off/assist/l1]` plus aliases `control` and `accent` in `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`.
- Kept the feature default-off and runtime-only. It does not touch calibration, AP/GDFT, render buffers, palette persistence, upload, or L1 hook/director internals.
- Ran focused verification: `python3 -B -m unittest tests.test_smart_visual_engine_static tests.test_serial_hotkeys_static tests.test_edgemixer_lite_static tests.test_visual_hooks_replay tests.test_smart_visuals_gate` -> 33 tests OK.
- Ran compile-only verification: `env PLATFORMIO_BUILD_DIR=/tmp/k1_smart_scene_pio_build_20260528 pio run -e k1_hardware` -> PASS with the existing `system.h:48` volatile warning.
- Wrote `docs/forensics/2026-05-28-smart-scene-preset-runtime-control.md` with the runtime-proof boundary.

## 2026-05-28 Smart Director Autonomy Execution

- Implemented Smart Director autonomy as a frame-local overlay: `SBSmartDirectorOutput` now carries palette overlay state, palette index, and auto-colour overlay intent.
- Kept the autonomy primitive out of persistent `CONFIG`: palette mode/index/auto-colour are applied only to `RenderParams` inside `sb_smart_director_apply_render_params()`.
- Added `smart_scene=auto` / `autonomy` / `demo` for bounded bench/demo autonomy: switching on, director autonomy on, hooks on, EdgeMixer complementary `0.350`, confidence floor `0.055`, dwell `6000ms`, cooldown `9000ms`, max `4` switches per minute.
- Routed Smart-selected modes that are in the current allow-list through RenderParams palette helpers: Bloom, Waveform, Waveform Fast, Waveform Hybrid, and VU.
- Added host replay proof for Smart Director autonomy:
  - `scripts/regression-harness/smart_director_replay.py`
  - `tests/test_smart_director_replay.py`
- Ran verification:
  - `python3 -B -m unittest tests.test_smart_visual_engine_static` -> 21 tests OK
  - `python3 -B -m unittest tests.test_smart_director_replay` -> PASS
  - `python3 -B -m unittest discover -s tests` -> 81 tests OK
  - `pio run -e k1_hardware`, `k1_hardware_harness`, `k1_bench_reference`, `k1_hardware_trace_dev` -> PASS with existing warnings only
  - `nm` production/harness MabuTrace audits -> no matches
- Uploaded the new production firmware to `/dev/tty.usbmodem1101` and the bench-reference firmware to `/dev/tty.usbmodem1401`; both uploads passed.
- Configured A/B:
  - `1101`: `smart_scene=l1` reference, autonomy off
  - `1401`: `smart_scene=auto` candidate, autonomy on
- Captured scalar/status runtime evidence in `docs/forensics/runtime-evidence/2026-05-28-k1-smart-autonomy-ab-config-v1.log`, parsed `...status-summary.json`, and took final status `2026-05-28-k1-smart-autonomy-final-status-v1.log`.
- Wrote `docs/forensics/2026-05-28-smart-director-autonomy-runtime-evidence.md`.

## 2026-05-29 Smart Auto Product Validation Planning

- Restored file-backed plan context from `task_plan.md`, `findings.md`, and `progress.md`.
- Ran planning catchup script: no additional output.
- Read `docs/forensics/2026-05-29-workstream-closeout-audit.md`.
- Read `docs/forensics/runtime-evidence/2026-05-29-k1-smart-autonomy-visible-orbit-v2.md`.
- Checked git state: branch `feat/gdft-harness` at `98d03af`, clean against `origin/feat/gdft-harness`.
- Used source-command-recall: `claude-mem` returned no direct hit for the exact Smart Auto/visible-orbit query; local memory registry provided adjacent Smart Visual and FixedPoints/VPAB context.
- Promoted the next lane in the root tracker: Smart Auto v2 product validation outranks VME, FixedPoints FP-0, donor FFT/CBSS, and L2 Memory.
- Recorded fallback decision rule: if Smart Auto v2 is not clearly more musically/perceptually impactful than L1, move to Scene Policy v2 with deliberate 20-30s trajectories controlled by music events.
- Recorded VPAB `render_us` semantics repair as the parallel unblocker for VME/final-byte experimentation, not the primary product lane.
- Updated `task_plan.md`, `findings.md`, and `progress.md` to include the 2026-05-29 visible-orbit v2 correction and closeout audit.
- Received Product Manager read-only review: validation should use 1101 L1 reference vs 1401 auto candidate, steady groove / kick-drop / sparse-build clips, status fields plus side-by-side video, and a 2-of-3 perceptual win threshold.
- Received Embedded Firmware read-only review: VPAB `render_us` semantics are mixed and should block VME/final-byte promotion, but should not block Smart Auto product validation when the evidence is status plus Captain/video judgement.
- Integrated both subagent deltas into `task_plan.md` and `findings.md`.

## 2026-05-29 Smart Auto Product A/B Runtime Log Review

- Selected three local music windows from `/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs`: `Regard_Ride_It.mp3` steady groove, `Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3` kick/drop-heavy, and `Carte-Blanche-Mixed.mp3` sparse/breakdown-to-build.
- Verified and used the intended runtime devices: 1101 as L1 reference (`F887A500`, `:smart_scene=l1`) and 1401 as Smart Auto candidate (`B489A500`, `:smart_scene=auto`).
- Played all three local windows through `ffplay`; all clip subprocesses exited `0`.
- Captured runtime logs:
  - `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-1101.log`
  - `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-1401.log`
  - `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-manifest.json`
- Wrote the runtime evidence review: `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-runtime-evidence.md`.
- No calibration, erase, upload, firmware source edit, commit, tag, branch, or push was performed in this pass.

## 2026-06-01 Smart Auto Closeout Execution

- Re-read Superpowers execution/verification guidance plus K1 firmware gate, SensoryBridge doctrine, perception-first engineering, and the repo Reasoning Protocol.
- Re-checked live repo state: branch `feat/gdft-harness`, HEAD `3dd402f`, dirty tree with governance, Spec Kit, and Smart Auto runtime-evidence files.
- Integrated Captain's current bench map: main K1v2 on `/dev/tty.usbmodem12201`, second bench K1 on `/dev/tty.usbmodem1401`.
- Verified OS-visible USB identities before serial control: Espressif serials `B4:3A:45:A5:87:F8` and `B4:3A:45:A5:89:B4`; I/O Registry exposes both requested `/dev/tty.usbmodem*` nodes.
- Added failing-first tests for a reusable Smart Auto product A/B capture helper and the VPAB `render_us` semantics split.
- Implemented `scripts/regression-harness/smart_auto_product_ab_capture.py` for two-device serial/status capture, three fixed music windows, optional AVFoundation video capture, and extracted frame generation.
- Updated `scripts/regression-harness/vpab_gate.py` so `render_us` is reported as `render_budget` warning by default and as a hard failure only with strict render-budget mode.
- Ran focused verification: `python3 -B -m unittest tests.test_smart_auto_product_ab_capture tests.test_vpab_gate` -> 16 tests OK.

## 2026-06-01 K1 Upload Guard / Cross-Flash Recovery

- Recovered from the wrong-GPIO-pinmap flash by swapping the PlatformIO
  environments back to the physical devices:
  - `/dev/tty.usbmodem12201` / `B489A500` -> `k1_bench_reference`
  - `/dev/tty.usbmodem1401` / `F887A500` -> `k1_hardware`
- Verified both devices came back over serial with `VERSION: 40103`, Smart
  Assist off, Smart autonomy off, hooks off, and EdgeMixer off.
- Updated `platformio.ini` default `upload_port` / `monitor_port` values to
  encode the recovered physical mapping.
- Added `scripts/platformio/k1_upload_guard.py`, installed through
  `extra_scripts = pre:scripts/platformio/k1_upload_guard.py`.
- Added `tests/test_k1_upload_guard.py` so cross-flash attempts are rejected in
  tests before another hardware run can repeat the incident.
- Verified the guard:
  - `python3 -B -m unittest tests.test_k1_upload_guard` -> 5 tests OK
  - `python3 scripts/platformio/k1_upload_guard.py --env k1_hardware --upload-port /dev/tty.usbmodem1401` -> accepted
  - `python3 scripts/platformio/k1_upload_guard.py --env k1_bench_reference --upload-port /dev/tty.usbmodem12201` -> accepted
  - `python3 scripts/platformio/k1_upload_guard.py --env k1_hardware --upload-port /dev/tty.usbmodem12201` -> rejected
- Verified continuation gates after the guard:
  - focused Smart/VPAB/guard tests -> 43 tests OK
  - `pio run -e k1_hardware` -> PASS with existing warning
  - `pio run -e k1_bench_reference` -> PASS with existing warning
  - `python3 -B -m unittest discover -s tests` -> 92 tests OK
  - `pio run -e k1_hardware_harness` -> PASS with existing warnings
  - `pio run -e k1_hardware_trace_dev` -> PASS with existing trace-dev/MabuTrace warnings
  - production and harness `nm ... | grep -i mabutrace` checks -> no matches

## 2026-06-01 Smart Auto Product Verdict

- Ran the post-guard Smart Auto A/B capture:
  `python3 -B scripts/regression-harness/smart_auto_product_ab_capture.py --main-port /dev/tty.usbmodem12201 --bench-port /dev/tty.usbmodem1401`.
- Captured manifest and serial logs:
  - `docs/forensics/runtime-evidence/2026-06-01T203320-smart-auto-ab-manifest.json`
  - `docs/forensics/runtime-evidence/2026-06-01T203320-smart-auto-ab-main-k1v2.log`
  - `docs/forensics/runtime-evidence/2026-06-01T203320-smart-auto-ab-bench-k1-2nd.log`
- Captain live visual judgement: Smart Auto passed at least two of three clips.
- Wrote closeout:
  `docs/forensics/runtime-evidence/2026-06-01-smart-auto-product-ab-closeout-v2.md`.
- Current Smart Auto status:
  `product-validation-passed-for-current-demo`.

## 2026-06-01 Parallel K1 Closeout Wave

- Created five isolated sandboxes under `/tmp/k1_parallel_20260601211146` for
  tracker/evidence, VPAB closeout, manual-owner audit, Smart Auto corpus prep,
  and calibration/FixedPoints hygiene.
- Locked hardware access to the orchestrator lane only; subagents were
  instructed not to open serial, upload, erase, or run calibration.
- Dispatched VPAB, manual-owner, Smart Auto corpus, and calibration/FixedPoints
  workers with load-bearing output contracts and disjoint write scopes.
- Reconciled stale root tracker labels:
  - Phase 15 Smart Auto closeout is complete.
  - Phase 16 upload guard / cross-flash recovery is complete.
  - Smart Auto status is `product-validation-passed-for-current-demo`.
  - VPAB status is `substrate-ready-render-us-semantics-split-closeout-pending`.
- Wrote dirty-tree classification:
  `docs/forensics/2026-06-01-parallel-closeout-dirty-tree-classification.md`.
- Integrated reviewed Smart Auto corpus prep:
  - added `--clip-manifest` support to
    `scripts/regression-harness/smart_auto_product_ab_capture.py`;
  - added manifest parser tests;
  - added nine-clip expanded corpus manifest and rubric under
    `docs/forensics/runtime-evidence/`.
- Integrated VPAB closeout:
  `docs/forensics/2026-06-01-vpab-proof-closeout.md`.
- Integrated calibration/FixedPoints hygiene:
  `docs/forensics/2026-06-01-calibration-fixedpoints-hygiene.md` and root
  `NOTICE`.
- Manual-owner source audit returned no firmware behaviour patch; existing
  canonical static coverage already covers the worker's proposed assertion set.
- Focused canonical verification after integration:
  `python3 -B -m unittest tests.test_smart_auto_product_ab_capture
  tests.test_vpab_gate tests.test_smart_visual_engine_static
  tests.test_k1_upload_guard tests.test_calibration_profile_static` -> 50 tests
  OK.
- Manifest verification after integration:
  `python3 -m json.tool` passed and `load_clip_manifest(...)` returned 9 clips.
- Hardware identity preflight passed for both current bench devices:
  `/dev/tty.usbmodem12201` -> `B489A500`; `/dev/tty.usbmodem1401` ->
  `F887A500`.
- First manual-owner runtime audit showed the second bench K1 was running stale
  firmware where `secondary_status` still marked manual owner.
- Guarded upload of current `k1_hardware` to `/dev/tty.usbmodem1401` exited 0,
  then post-upload identity returned `VERSION: 40103` and `F887A500`.
- Repeated manual-owner runtime audit passed on the flashed second bench K1 and
  wrote:
  `docs/forensics/runtime-evidence/2026-06-01-manual-owner-runtime-audit.md`.
- First expanded Smart Auto video capture run exposed a harness bug: AVFoundation
  `ffmpeg` could ignore terminate long enough for the second `communicate()` to
  time out and abort the run.
- Added a failing-first unit test and fixed the harness with
  `finish_video_capture()` so stuck video capture is killed and recorded instead
  of aborting the whole A/B run.
- Re-ran the nine-clip expanded Smart Auto capture. Serial/state gate passed;
  product visual verdict is `review` pending Captain/video judgement.
- Closed the expanded Smart Auto visual review autonomously from the five
  captured frame sets: captured subset passed the no-flood/no-strobe/no-washout
  failure screen, Scene Policy v2 is not triggered, and full 9/9 expanded-video
  promotion is not claimed because four camera captures failed.
