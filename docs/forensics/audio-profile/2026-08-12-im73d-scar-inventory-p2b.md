---
abstract: "P2.B quarantine inventory (runbook im69d_dual_resolution): every remaining K1_MIC_IM73D_PDM_V1 site in firmware classified keep-as-dead-code vs deleted. Verdict: ZERO IM73D consumer floors remain in executable source — the Aug-9 consumer scars (silence 0.001/0.003, tempo lock 0.28/REL 0.18, novelty ×4) were tombstone-deleted 2026-08-11; the ~30 surviving sites are driver/pins/cal-namespace/telemetry/guard infrastructure compiled only in deprecated archive envs. One live hazard closed alongside: k1_custom recomposed off the *im73d* inheritance."
---

# P2.B — Legacy IM73D scar inventory (quarantine record)

**Date:** 2026-08-12 · **Runbook:** `.cursor/plans/im69d_dual_resolution_d171d7f2.plan.md` §P2.B
**Authority:** `docs/hardware/CAPTAIN_CORRECTION_2026-08-10_unit2_im69d_im73d_deprecated.md`

## Verdict

**No IM73D-measured consumer value remains reachable in executable source.** The three
consumer-scar classes the runbook names were already deleted with tombstone comments on
2026-08-11 (`1bdf54d0` lineage). Every surviving `K1_MIC_IM73D_PDM_V1` site is
infrastructure that compiles **only** in the deprecated `*im73d*` archive envs and cannot
leak a measured IM73D number into an IM69D or SPH build.

## A — Consumer scars: DELETED (tombstoned 2026-08-11, do not resurrect)

| Scar | Where it lived | State |
|------|----------------|-------|
| Silence enter/exit `0.001 / 0.003` | `system/globals.h` (tombstone at ~706) | DELETED |
| Tempo lock `0.28` override | `audio/k1_tempo.cpp` (tombstone ~86, ~271) | DELETED |
| Tempo REL `0.18` override | `audio/k1_tempo.cpp` (tombstone ~296) | DELETED |
| Tempo short-circuit | `audio/k1_tempo.cpp` (tombstone ~496) | DELETED |
| `novelty *= 4.0f` boost | `audio/k1_tempo.cpp` (tombstone ~1346) | DELETED |
| IM73D audio-profile values | `audio/k1_audio_profile.h` (profile → `NOT_CHARACTERISED`, fail closed) | DELETED |
| Waveform-tempo peak\|vu / HSV FB | `effects/light_mode_waveform_tempo.cpp` | ABSENT (never merged; lived only in Unit 2's uncommitted `db300db` working tree) |

Provenance archive (record, never a seed): `docs/forensics/audio-profile/2026-08-11-im73d-profile-tombstone.md`.

## B — Infrastructure sites: KEEP-AS-DEAD-CODE (archive envs only)

| File | Sites | Class | Why kept |
|------|-------|-------|----------|
| `system/constants.h` 45–47 | 1 | **Guard** | `#error` mutual exclusion IM73D×IM69D — safety, applies to all builds |
| `system/constants.h` 52–54 | 1 | **Guard** | derives `K1_MIC_PDM_RX_ANY_V1` — shared PDM plumbing |
| `system/constants.h` 56ff, 606ff | 2 | Dead code | IM73D silence floor re-seed + quiet-duty trim (SSL=979 era) — archive-env only |
| `system/constants.h` 382ff, 429ff | 2 | Dead code | IM73D pin maps (bench 13/12/14 + prod D1) — archive-env only |
| `system/globals.h` 152–160 | 1 | Dead code | `im73d_samples_i16` landing buffer + raw telemetry — flag-gated |
| `audio/i2s_audio.h` | ~10 | Dead code | PDM driver init/read branches for IM73D — flag-gated driver |
| `audio/k1_mic_auto_sense.cpp` | 3 | Dead code | raw-telemetry source select; non-IM73D builds report `TELEMETRY_BYPASSED` honestly |
| `audio/k1_audio_profile.h` | 1 | **Quarantine itself** | forces `K1_AUDIO_PROFILE_NOT_CHARACTERISED` (fail closed) under IM73D |
| `persistence/bridge_fs.h` | ~7 | **Isolation** | cal namespace `/cal_profile_pdm.bin` split — prevents IM73D↔SPH/IM69D cal cross-poisoning |
| `system/system.h` 437 | 1 | Comment | cal force-invalidate rationale |

## C — Live hazard closed with this inventory

`[env:k1_custom]` extended `env:k1_bench_im73d_ble` (the false-authority inheritance that
caused the Aug-9 misflash cascade). Recomposed to extend `env:k1_bench_im69d_ble`
(runbook P1.A composition), still `-DK1_CUSTOM_LED_V1` (224/160 RGBIC rig), and it
**remains BLOCKED in the upload guard** until a physical device is nominated and its
mic identity is receipted.

## D — Binding rule (also in `.claude/handoff.md`)

**IM69D floors are measured on IM69D silicon.** No value from any section-A scar or
section-B dead-code block may be ported, seeded, bounded, or "sanity-checked" into an
IM69D (or any other mic) profile without a fresh measurement on the target unit,
calibrated at final placement. The Phase-4 floors cite
`_scratch/im69d_resolution_20260810/IM69D_CONSUMER_BASELINE.md` — nothing else.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Created — P2.B quarantine inventory; consumer scars verified deleted, infrastructure classified, k1_custom recompose recorded. |
