# Self-Calibrating Sensitivity Forensic Synthesis

Date: 2026-07-10
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`

## Verdict

GROUNDED for the K1 current-source/doc finding:

- A formal K1 "auto-sensing, self-adjusting mic sensitivity" discussion exists.
- It is a docs-only research/design handoff from commit `92c70fc5d625d70930c2269f11f2d14c542c6864` (`docs(audio): design mic auto sensitivity scaling`, 2026-07-06 15:03 +0800).
- It was not implemented in current source at `HEAD 1f27096` on `lane/dual-sync-phase0`.
- The design explicitly required telemetry first, default-off behaviour, no automatic `start_noise_cal`, no persistence writes, and Captain gates before production enablement.

DEGRADED-MODE for the alternate-folder origin hypothesis:

- `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip` contains strong adjacent precursor evidence: audio parameter exposure research, measured mic-domain/silentScale envelope work, Zone AGC calibration acceptance, and auto-ranging/dynamic gain normalisation concepts.
- Exact `self calibrating sensitivity` / `self-calibrating` searches did not hit in Lightwave memory or the targeted current docs.
- The Lightwave SSA timed out and was closed before producing an artifact, so the Lightwave classification below is based on direct orchestrator reads plus claude-mem observations, not an independent returned SSA.

## Strongest K1 Evidence

| Evidence | Classification | Claim |
| --- | --- | --- |
| `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:9-16` | Formal design discussion | Captain's feature idea is named as an auto-sensing/self-adjusting mic sensitivity supervisor, but the document says it does not implement firmware or run calibration. |
| `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:20-34` | Safety boundary | No automatic calibration firing, no hidden adaptive scale during purity work, no v1 persistence, Core 0 safety, default-off flag. |
| `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:127-150` | Telemetry-first requirement | Required raw/pre-conditioning and controller telemetry before any automatic scaling. |
| `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:410-432` | Shadow/default-off gate | Default flag off; no config save; shadow mode computes recommendations while applied scale remains `1.0f`. |
| `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:536-546` | Handoff | Next phase is telemetry first only; no auto-scale control, no calibration firing, no persistence writes. |
| `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-117` | Current implementation | Effective sensitivity is `CONFIG.SENSITIVITY * k1_loud_input_trim` when loud guard is enabled. No auto-scale layer is present. |
| `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:141-193` | Adjacent mechanism | Loud guard continuously trims input/GDFT response from clip/near-rail/saturation evidence, but it is runtime protection, not learned persisted sensitivity. |
| `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:417-433` | Current implementation | IM73D fixed input gain is applied before sensitivity; then current sensitivity/loud-guard path is applied. |
| `rg "K1_MIC_AUTO_SENSE|k1_mic_auto|auto_scale|auto_state|auto_reason"` | Negative proof | Proposed symbols only appear in the design doc, not firmware/tests/scripts. |

## Lightwave Evidence

| Evidence | Classification | Claim |
| --- | --- | --- |
| `research/AUDIO_PARAMETERS_EXPOSURE_RESEARCH.md:12-20` | Research/design precursor | Surveyed WLED, Emotiscope, and K1 audio parameter exposure; identifies squelch/gain, naming, immediate effect, and persistence as product-control principles. |
| `research/AUDIO_PARAMETERS_EXPOSURE_RESEARCH.md:34-60` | Research/design precursor | WLED exposes squelch, gain, and AGC mode; AGC handles complexity internally. |
| `research/AUDIO_PARAMETERS_EXPOSURE_RESEARCH.md:72-88` | Research/design precursor | Emotiscope avoids low-level audio controls and aims for "no tuning required" behaviour. |
| `research/AUDIO_PARAMETERS_EXPOSURE_RESEARCH.md:217-359` | Proposal | Proposed K1 onset/silence controls, including `silenceThreshold`, `onsetSensitivity`, persistence, REST/WS/serial surfaces, and an implementation checklist. This is not the July K1 auto-sense controller. |
| `BACKLOG.md:91-100` | Measured-debt ledger | C-1 asks what mic-domain RMS/peak/silentScale-trip range firmware was tuned against and records 2026-05-06 measured-degraded hardware evidence. |
| `firmware-v3/docs/research/c1_mic_domain_envelope_audit_2026-05-06.md:50-79` | Measured evaluation | Separates raw-hop RMS from perceptual `frame.rms`; says C-1 needed a no-guesswork hardware pass. |
| `firmware-v3/docs/research/c1_mic_domain_envelope_capture_2026-05-06.md:18-55` | Measured evaluation | Captures idle/quiet/normal/dense raw-hop RMS, `frame.rms`, confidence, `silentScale`, and stop recovery on K1v2. |
| `BACKLOG.md:195-220` | Calibration quality gate | F-6.1 asks whether post-AGC normalised bands/chroma are visually acceptable or over-compressed; preferred fixes avoid blindly weakening Zone AGC. |
| `docs/node-composer-research.md:774-804` | Adjacent algorithm concept | Lists Goertzel pipeline with noise floor subtraction, auto-ranging/dynamic gain normalisation, smoothing, chroma, novelty, and tempo resonators. |

Lightwave therefore looks like the origin of the *evaluation vocabulary and calibration concerns* behind the later K1 design, not proof that a self-calibrating sensitivity function was implemented there.

## Timeline

- 2026-03-25: Lightwave audio parameter exposure research proposes user-facing silence/onset sensitivity controls and records WLED/Emotiscope patterns.
- 2026-05-01 to 2026-05-06: Lightwave C-1 microphone-domain envelope debt is surfaced, audited, then measured with K1v2 raw-hop RMS/silentScale evidence.
- 2026-05-19: Lightwave F-6.1 opens Zone AGC output intensity acceptance as a calibration quality gate.
- 2026-07-03 to 2026-07-05: K1 IM73D/PDM work proves persisted calibration/profile state and Waveform-Fast calibrated-floor duty tuning; this remains adjacent, not an autonomous sensitivity controller.
- 2026-07-06: K1 design doc formalises an auto-sensing mic sensitivity lane, explicitly telemetry-first/default-off/no-persistence.
- 2026-07-10 current checkout: no implemented `K1_MIC_AUTO_SENSE`/`k1_mic_auto_*`/`auto_scale` controller symbols exist outside the design doc.

## SSA Results

| Agent | Status | Result used |
| --- | --- | --- |
| SCS-SOURCE-01 | completed | Refuted live-source implementation; artifact `findings/ssa_source_evidence.md`. |
| SCS-DOCS-01 | completed | Verified formal design discussion and refuted production/default feature; artifact `findings/ssa_docs_evidence.md`. |
| SCS-MEM-01 | completed | No exact memory phrase; closest memory cluster is Waveform-Fast calibrated-floor/duty-cycle tuning, not auto sensitivity; artifact `findings/ssa_memory_evidence.md`. |
| SCS-LIGHTWAVE-01 | timed out, then closed | No artifact returned. Direct orchestrator Lightwave reads used instead. |

## Operational Next Step

If Captain wants this implemented next, do not implement the controller first. The repo-authorised next slice is telemetry only:

1. Add default-off read-only mic auto-sense telemetry fields (`raw_abs_peak`, `raw_rms`, raw near-rail/clip, `auto_scale`, `auto_state`, `auto_reason`, window age).
2. Keep applied scale at `1.0f`.
3. Do not fire calibration.
4. Do not write `CONFIG.SENSITIVITY` or NVS from the auto-sense path.
5. Gate proof with host/static tests, byte gate, bench shadow captures, and Captain eyes-on before any applied controller.

## Validation

- Completed three bounded SSAs and consumed their artifacts.
- Timed and reported the Lightwave SSA wait; closed it while still running after partial request.
- Ran direct `rg`, `nl -ba`, `git show`, `git log`, and claude-mem `search -> timeline -> get_observations` checks.
- No firmware source edits, builds, tests, serial monitor, flash, audio playback, or calibration commands were run.

## Blockers

- `docs/agent/AGENT_EXECUTION_STANDARD.md` is referenced by the K1 instructions but absent in the checkout.
- `firmware-v3/docs/reference/codebase-map.md` and `firmware-v3/docs/reference/fsm-reference.md` are absent in the K1 checkout.
- Lightwave SSA did not return before closeout; Lightwave conclusion remains DEGRADED-MODE pending an independent completed SSA if stronger certainty is required.
