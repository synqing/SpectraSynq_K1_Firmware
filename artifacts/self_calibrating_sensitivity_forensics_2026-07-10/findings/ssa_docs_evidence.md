# SCS-DOCS-01 Docs Evidence

## Verdict

FORMAL DISCUSSION VERIFIED; FORMAL PRODUCTION FEATURE NOT VERIFIED.

On-disk docs prove a prior auto-sensing/self-adjusting mic sensitivity design
lane existed, but the strongest authority describes it as a research/design
handoff, telemetry-first, default-off, runtime-only, no calibration firing, and
no persistence writes. I did not find on-disk authority that a production/default
self-calibrating sensitivity feature was accepted, implemented, or Captain
ratified.

## Search Scope

Read-only search was limited to `docs/`, `artifacts/`, `_scratch/`, `scratch/`,
`progress.md`, and `.claude/handoff.md`. Repo guard passed:
`git rev-parse --show-toplevel` -> `/Users/spectrasynq/SpectraSynq_K1_Firmware`.

Note: `docs/agent/AGENT_EXECUTION_STANDARD.md` is referenced by AGENTS but is not
present in this checkout.

## Key Evidence

1. `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md`
   is the central formal-looking artifact. It says Captain's idea was an
   "auto-sensing, self-adjusting mic sensitivity supervisor" at lines 9-13, but
   also says the document "does not implement firmware, flash devices, play
   audio, or run calibration" at lines 15-16. Its boundaries are explicit:
   never auto-fire `start_noise_cal`/`N`/`Y`, keep raw measurement modes able to
   bypass auto-sensing, do not persist auto-scale changes to NVS, keep Core 0
   safe, and gate behaviour behind default-off `K1_MIC_AUTO_SENSE_V1` until host,
   bench, and Captain eyes-on gates are complete (`:20-34`). It also requires
   telemetry before control (`:127-150`), default-off/no-config-save rules
   (`:410-418`), shadow proof with no persistence writes (`:420-432`), and says
   production/main-K1 consideration must wait until raw/purity gates are not
   using auto-sense (`:450-455`). Its handoff prompt says "telemetry first, no
   auto-scale control ... no persistence writes ... default-off flag" (`:536-545`).

2. `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md` is the
   stronger refutation source for hidden self-calibration claims. It says AP,
   APCAP, AGC debug, and semantic metrics are conditioned, not raw microphone
   measurements (`:21-31`), and records continuous raw telemetry added as
   `raw_i16_abs_peak`, `raw_i16_rms`, and `raw_i16_near_pct` (`:33-39`). It
   records live bench sensitivity `CONFIG.SENSITIVITY: 0.870005` with
   `CAL_SOURCE: persisted_profile` (`:52-71`), classifies sensitivity and
   calibration as state that affects measurements (`:75-102`), and says
   comparable production measurements must pin or record `CONFIG.SENSITIVITY`,
   `AUDIO_RESPONSE_GAIN`, `input_trim`, `gdft_trim`, `CAL_SOURCE`, `CAL_VALID`,
   `SWEET_SPOT_MIN_LEVEL`, and `DC_OFFSET` (`:120-123`). Schema hardening is
   present: `K1_SENSITIVITY_MIN/MAX` canonicalise `0.10..20.0`, `global.sensitivity`
   shares that range (`:103-118`), `stream_agc_data()` now separates legacy
   `floor` from active `active_floor` (`:219-223`), and
   `tests/test_audio_telemetry_schema_static.py` exists (`:233-240`).

3. `docs/spec-index.md:7` is current-lane synthesis: sensitivity/telemetry schema
   hardening is in progress; bench read-only proof includes
   `CONFIG.SENSITIVITY: 0.870005`, `CAL_SOURCE: persisted_profile`, and
   `CAL_VALID: 1`; raw pre-conditioning telemetry exists; DSR16 is rejected; and
   `global.sensitivity`/`:stream_agc active_floor` hardening is recorded.
   `docs/spec-index.md:39` says restored bench validation is green at usable
   levels and current blocker is env-specific device proof plus Captain eyes-on,
   not an auto-sense feature.

4. `docs/hardware/im73d-restored-bench-validation-2026-07-07.md` records the
   restored bench IM73D proof. Safety boundary says no `start_noise_cal` and no
   `N`/`Y` (`:31-42`). Raw pre-conditioning metrics are the decision basis
   (`:55-59`); volumes 45/60 were usable, volume 75 was a front-end stress/fail
   condition (`:60-79`). `:stream_agc` headroom is green at usable music levels:
   all gains under 10, max observed `1.99` (`:81-91`).

5. `docs/hardware/im73d122-productionization-handover-2026-07-03.md` proves
   calibration persistence and Waveform-Fast tuning existed before the auto-sense
   design. It says IM73D selection was Captain-ratified and closed (`:19-30`),
   bench state had `cal_valid=1 cal_source=persisted_profile SSL=979 DC=10`
   (`:32-37`), and the chain includes PDM cal persistence plus
   Waveform-Fast margin change `1.10 -> 0.95` (`:39-44`, `:132-142`). This is
   PDM-gated tuning/persistence, not a general self-calibrating sensitivity
   feature.

6. `docs/hardware/device-build-registry.md` is deployed-state evidence. Current
   main SPH row records `CONFIG.SENSITIVITY: 2.400000` and `CAL_SOURCE: config`
   with paired passive AP capture against bench IM73D (`:92-97`). Current bench
   row records `CONFIG.SENSITIVITY: 0.870005`, `CAL_SOURCE: persisted_profile`,
   `CAL_VALID: 1`, DSR16 rejection, and no `start_noise_cal` during recovery
   (`:97`). Historical rows prove R1 knob persistence and PDM cal persistence
   (`:99`, `:105-106`), plus Waveform-Fast quiet-music duty trim at `3e06f9d`
   (`:105`).

7. `_scratch/im73d_bringup/snappiness/ssa2_vp_waveform.md` directly addresses
   snappiness/Waveform-Fast. It says the only calibration-domain-coupled Fast
   term is the SSL-proportional raw floor (`:27-35`), refutes that this is a
   response-speed/latency term, and classifies it as trigger duty/selectivity
   instead (`:48-54`). `docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md`
   identifies Waveform Fast, Waveform, and Waveform Tempo as VME sandbox targets
   (`:41-55`, `:70-74`) and names the Waveform-Fast reactive floor fields
   `max_waveform_val_raw`, `WAVEFORM_REACTIVE_RAW_MARGIN`, and
   `WAVEFORM_REACTIVE_PEAK_FLOOR` (`:136-160`).

8. `docs/hardware/im73d122-ap-vp-migration-plan.md` records IM73D/SPH sensitivity
   domain matching, not adaptive sensitivity. SPH default stays unchanged and
   IM73D is flag-gated (`:5-10`); the strategy is domain-match, not downstream
   retune (`:15-19`); `INPUT_GAIN` is pre-sensitivity and effective gain is
   `G * SENSITIVITY(2.4)` (`:21-30`, `:223-231`); default downstream thresholds
   should stay unchanged unless bench A/B proves no single `G` works (`:219`).

9. `docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md` and
   `docs/hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md` discuss
   IM73D sensitivity/DSR evidence. Controlled audio rejects DSR16 (`:1-12`),
   uses no calibration commands (`:26-37`), and relies on raw pre-conditioning
   metrics (`:63-88`). Recovery proof records bench
   `CONFIG.SENSITIVITY: 0.870005`, `CAL_SOURCE: persisted_profile`, `CAL_VALID: 1`
   and no calibration/write commands (`:134-145`). Quiet-only evidence says it
   cannot prove DSR16 music/SNR benefit or justify default flip (`:1-12`, `:78-103`).

10. `docs/prd/ve-auto-loop/03-effects-archaeology-synthesis-2026-06-04.md:173-190`
    contains the phrase "v3 self-calibrating asymmetric max-follower", but it is
    about an effects archaeology/kernel mechanism for bass tracking, not K1 mic
    sensitivity persistence or an authorised firmware auto-sense feature.

## Timeline

- 2026-06-04: PRD/effects archaeology mentions a "self-calibrating asymmetric
  max-follower" in an effects/oracle context, not a K1 mic sensitivity feature.
- 2026-06-07: VME Level 1 Waveform sandbox targets Waveform Fast/8/18 and names
  the Waveform-Fast raw-gate fields; hardware VMEWT proof is frozen pending
  fail-closed transport proof.
- 2026-07-02/03: IM73D graft/productionization docs establish PDM/SPH domain
  matching, Captain-ratified IM73D selection, PDM calibration persistence, and a
  PDM-gated Waveform-Fast margin trim.
- 2026-07-06: Purity audit separates raw vs conditioned telemetry, records live
  sensitivity/calibration state, lands schema hardening, and rejects hidden
  comparisons without pinned sensitivity/calibration. Separate auto-sensing doc
  proposes telemetry-first, default-off, runtime-only design with no calibration
  firing and no persistence writes.
- 2026-07-07/08: Restored bench validation and spec-index record raw telemetry,
  `stream_agc` headroom, DSR16 rejection, persisted-profile state, and
  sensitivity/telemetry schema hardening in progress.

## Refutation Summary

The on-disk record verifies discussion of an auto-sensing/self-adjusting
sensitivity idea and a formal research/design plan. It does not verify a
Captain-ratified production feature, default flip, calibration automation, or
persistent learned sensitivity profile. The strongest docs explicitly require
telemetry first, auto-sense disabled/bypassed for purity measurements, no
`start_noise_cal`, no `N`/`Y`, no config/NVS writes from controller updates, and
Captain decisions before production enablement.

## Re-run Commands

```bash
git rev-parse --show-toplevel

/opt/homebrew/bin/rg -n -i --hidden --glob 'docs/**' --glob 'artifacts/**' --glob '_scratch/**' --glob 'scratch/**' --glob 'progress.md' --glob '.claude/handoff.md' 'self[-_ ]calibrat|auto[-_ ]calibrat|self-adjusting|auto-sensing|auto-sense'

/opt/homebrew/bin/rg -n --hidden --glob 'docs/**' --glob 'artifacts/**' --glob '_scratch/**' --glob 'scratch/**' --glob 'progress.md' --glob '.claude/handoff.md' 'CONFIG\.SENSITIVITY|SWEET_SPOT_MIN_LEVEL|CAL_SOURCE|persisted_profile|K1_SENSITIVITY|global\.sensitivity|sensitivity schema|schema hardening|sensitivity model'

/opt/homebrew/bin/rg -n --hidden --glob 'docs/**' --glob 'artifacts/**' --glob '_scratch/**' --glob 'scratch/**' --glob 'progress.md' --glob '.claude/handoff.md' 'snappiness|Waveform-Fast|Waveform Fast|WAVEFORM_REACTIVE_RAW_MARGIN|active_floor|stream_agc'

/opt/homebrew/bin/rg -n --hidden --glob 'docs/**' --glob 'artifacts/**' --glob '_scratch/**' --glob 'scratch/**' --glob 'progress.md' --glob '.claude/handoff.md' 'IM73D|SPH0645|SPH|DSR_8S|DSR16|DSR_16S'

nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '1,110p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '120,190p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '245,290p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '323,355p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '400,455p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '480,548p'

nl -ba docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md | sed -n '1,130p'
nl -ba docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md | sed -n '145,242p'
nl -ba docs/spec-index.md | sed -n '1,45p'
nl -ba docs/hardware/im73d-restored-bench-validation-2026-07-07.md | sed -n '1,180p'
nl -ba docs/hardware/im73d122-productionization-handover-2026-07-03.md | sed -n '1,50p'
nl -ba docs/hardware/im73d122-productionization-handover-2026-07-03.md | sed -n '132,145p'
nl -ba docs/hardware/device-build-registry.md | sed -n '92,108p'
nl -ba _scratch/im73d_bringup/snappiness/ssa2_vp_waveform.md | sed -n '1,80p'
nl -ba docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md | sed -n '1,140p'
nl -ba docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md | sed -n '136,165p'
nl -ba docs/prd/ve-auto-loop/03-effects-archaeology-synthesis-2026-06-04.md | sed -n '170,190p'
nl -ba docs/hardware/im73d122-ap-vp-migration-plan.md | sed -n '1,32p'
nl -ba docs/hardware/im73d122-ap-vp-migration-plan.md | sed -n '219,231p'
nl -ba docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md | sed -n '1,90p'
nl -ba docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md | sed -n '120,156p'
nl -ba docs/hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md | sed -n '1,110p'
```
