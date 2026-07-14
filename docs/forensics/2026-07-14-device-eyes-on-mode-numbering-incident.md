# DEVICE Eyes-On Mode-Numbering Incident

## Verdict

[FACT] The 2026-07-14 focused effect captures under
`docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/focused-ap-matrix/`
and `clean-eyes-on-ab/` were labelled with an incorrect dense-index assumption.

[FACT] Both `k1_bench_ap_frontend_probe` environments omit
`K1_EFFECT_REGISTRY_V1`; their `set_mode` command therefore accepts the raw
append-only `lightshow_modes` enum ordinal.

[FACT] Every focused Waveform Hybrid K1, Tempo Comet, Dense Forge Chord, and
Percussion Burst eyes-on claim made from those captures is withdrawn. The
effect-level verdict remains `NOT_VERIFIED`.

## What Actually Rendered

| Command sent | Claimed effect | Actual raw-ordinal effect | Evidence status |
|---:|---|---|---|
| 12 | Tempo Comet | Aurora | `MISLABELLED_INVALID` |
| 16 | Dense Forge Chord | Ember Field | `MISLABELLED_INVALID` |
| 18 | Percussion Burst | Waveform Tempo | `MISLABELLED_INVALID` |
| 23 | Waveform Hybrid K1 | Pulse Prism | `MISLABELLED_INVALID` |

[FACT] Captain identified the visible mismatches: the claimed Percussion Burst
windows displayed Waveform Tempo, and the claimed Dense Forge windows displayed
Ember Field.

[FACT] Source audit then showed that the other two labels were also wrong:
ordinal 12 is Aurora and ordinal 23 is Pulse Prism.

## Failure Mechanism

[FACT] `serial_cmd_dispatch_mode()` maps a dense menu index only inside
`#ifdef K1_EFFECT_REGISTRY_V1`; otherwise it passes the numeric input through
the raw enum selection path.

[FACT] The capture harness described `--set-mode` as a dense index and checked
only that `MODE:` echoed the same number. In a legacy-numbered build, that echo
proved the wrong raw ordinal was selected rather than proving the intended
effect.

[INFERENCE] The failure survived repeated runs because the harness and scorer
shared the same false mode map, producing internally consistent but externally
false labels.

## Problems Resolved

[FACT] `device_novelty_buffer_capture.py` now provides stable `--set-effect`
selection. It resolves the effect key from the current `EffectRegistry.cpp` and
the append-only enum in `config_types.h`.

[FACT] Numeric `--set-mode` now requires `--expected-mode-ordinal` and playback
is blocked unless `CONFIG.LIGHTSHOW_MODE` matches that ordinal exactly.

[FACT] Stable-key selection is fail-closed to the two legacy-numbered bench AP
probe environments used by this lane.

[FACT] Tests pin the corrected source truth: Tempo Comet `20`, Dense Forge
`21`, Dense Forge Chord `24`, Percussion Burst `26`, and Waveform Hybrid K1
`32`.

[FACT] `device_effect_ap_matrix_score.py` now reports intended and actual
effects separately and marks all nine earlier focused captures
`MISLABELLED_INVALID`.

[FACT] The bench K1 was restored after the incident and read back as
`BUILD: version=40103 git=52a21db epoch=1784044874 env=k1_bench_im73d` with
chip `B489A500`.

[FACT] A corrected Dense Forge Chord attempt exposed a second workflow fault:
the operator announcement said the window had started while the capture tool
was still performing approximately 15 seconds of serial preflight. The attempt
was stopped before a capture artefact or playback progress marker existed.

[INFERENCE] The reported black plate was the effect's silence-gated state before
`afplay`, not evidence that Dense Forge Chord rendered black under music.

[FACT] The harness now emits `EYES_ON_ARMED` only after every preflight gate,
holds an explicit countdown, emits `EYES_ON_START` at the actual `afplay`
launch, and emits `EYES_ON_STOP` when the playback window ends.

[FACT] Effect captures now snapshot the pre-test primary mode and restore it in
`finally`, including runtime `get_mode` readback and a `MODE_RESTORE` raw-log
marker. Leaving a test effect selected requires the explicit diagnostic opt-in
`--leave-effect-selected`.

## 2026-07-15 Residual-State Incident

[FACT] The final corrected capture left primary mode 32, `WAVEFORM HYBRID K1`,
selected after audio playback stopped.

[FACT] `light_mode_waveform_hybrid_k1()` deliberately reduces its
signal-presence and silence envelopes towards zero; without playback the
primary rendered completely dark while the secondary remained visible.

[FACT] Live readback on the pinned bench K1 reported chip `B489A500`, build
environment `k1_bench_im73d`, primary `MODE: 32`,
`CONFIG.PHOTONS: 1.000000`, and `MASTER_BRIGHTNESS: 1.00`.

[FACT] Primary was restored to raw ordinal 18 and independently read back as
`MODE_NAME: WAVEFORM TEMPO`; Captain confirmed the primary became visible.

[INFERENCE] A capture harness that mutates live visual state without restoration
cannot be considered observational tooling; it changes the bench presented to
the operator and can create false hardware-failure reports.

## Durable Rules

1. [FACT] A numeric mode echo is not an effect-identity proof.
2. [FACT] Effect validation must record the raw persisted ordinal and the stable
   source key before playback.
3. [FACT] Dense numbering may be assumed only when the runtime build is proven
   to include `K1_EFFECT_REGISTRY_V1`.
4. [FACT] Captain visual identification overrides a contradictory harness label
   and triggers immediate evidence invalidation.
5. [FACT] A scorer must not infer effect identity from a filename or intended
   label when runtime ordinal evidence exists.
6. [FACT] An eyes-on window begins only at the harness `EYES_ON_START` marker;
   mode-selection preflight is not visual evidence.
7. [FACT] A capture must restore its pre-test mode and prove the restoration by
   readback unless the operator explicitly requests residual state.

## Corrected Re-run Commands

[FACT] These are low-telemetry eyes-on commands. Each derives and validates the
raw ordinal from the stable effect key before playback.

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/corrected-eyes-on-ab --label v1-tempo-comet --set-effect tempo_comet
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/corrected-eyes-on-ab --label v1-dense-forge-chord --set-effect dense_forge_chord
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/corrected-eyes-on-ab --label v1-percussion-burst --set-effect percussion_burst
python3 scripts/regression-harness/device_novelty_buffer_capture.py --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe_v1_off --duration-ms 30000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/corrected-eyes-on-ab --label v1-waveform-hybrid-k1 --set-effect waveform_hybrid_k1
```

[FACT] Repeat with `--expected-build-env k1_bench_ap_frontend_probe` after the
guarded V2 probe upload, then restore and read back `k1_bench_im73d`.
