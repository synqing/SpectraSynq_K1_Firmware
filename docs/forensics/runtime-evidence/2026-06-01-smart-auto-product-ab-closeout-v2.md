---
abstract: "Smart Auto product A/B closeout evidence after K1 upload-guard recovery."
evidence_tier: "runtime-serial-product-review-pending"
date: "2026-06-01"
---

# Smart Auto Product A/B Closeout v2

## Status

`product-validation-passed-for-current-demo`

Serial/runtime proof is captured. Captain live visual judgement passed Smart
Auto for at least two of the three clip classes in this run.

## Device Mapping

| Role | Port | PlatformIO env | USB serial | Chip ID | Scene |
|---|---|---|---|---|---|
| L1 reference / main K1v2 | `/dev/tty.usbmodem12201` | `k1_bench_reference` | `B4:3A:45:A5:89:B4` | `B489A500` | `:smart_scene=l1` |
| Smart Auto candidate / second bench K1 | `/dev/tty.usbmodem1401` | `k1_hardware` | `B4:3A:45:A5:87:F8` | `F887A500` | `:smart_scene=auto` |

## Evidence Files

| Artefact | Path |
|---|---|
| Manifest | `docs/forensics/runtime-evidence/2026-06-01T203320-smart-auto-ab-manifest.json` |
| L1 reference serial log | `docs/forensics/runtime-evidence/2026-06-01T203320-smart-auto-ab-main-k1v2.log` |
| Auto candidate serial log | `docs/forensics/runtime-evidence/2026-06-01T203320-smart-auto-ab-bench-k1-2nd.log` |

## Clip Corpus

| Clip class | Track | Window |
|---|---|---|
| steady groove | `Regard_Ride_It.mp3` | `125s-150s` |
| kick/drop-heavy | `Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3` | `75s-100s` |
| sparse/breakdown-build | `Carte-Blanche-Mixed.mp3` | `20s-45s` |

## Runtime Findings

### L1 Reference

- `[FACT]` Device identity: `VERSION: 40103`, chip ID `B489A500`.
- `[FACT]` Smart autonomy stayed off for all clips.
- `[FACT]` Palette overlay stayed off for all clips.
- `[FACT]` Auto-colour shift stayed off for all clips.
- `[FACT]` Palette index stayed `29`.
- `[FACT]` Manual owner stayed inactive.
- `[FACT]` AP calibration stayed valid: `cal_source=config`, `cal_valid=1`,
  `silence=0`.
- `[FACT]` VP stream render telemetry exceeded the nominal 2.0ms render ceiling
  on this serial stream. Max observed `render_us` was `3426us`; status
  `render_max` reached `3647us`.

### Smart Auto Candidate

- `[FACT]` Device identity: `VERSION: 40103`, chip ID `F887A500`.
- `[FACT]` Smart autonomy stayed on for all clips.
- `[FACT]` Palette overlay stayed on for all clips.
- `[FACT]` Auto-colour shift stayed off for all sampled status frames.
- `[FACT]` Scene Policy v2 bounds were present: confidence floor `0.070`,
  dwell `12000ms`, cooldown `12000ms`, switch window `90000ms`, max switches
  `3`.
- `[FACT]` Steady groove used applied modes `3`, `10`, and `11`, ending at
  `11`; switch window count ended at `2`.
- `[FACT]` Kick/drop-heavy used applied modes `11` and `10`, ending at `10`;
  switch window count ended at `3`.
- `[FACT]` Sparse/build held applied mode `10`; intent continued to report
  `3`, `10`, and `11`; switch window count stayed at `3`.
- `[FACT]` Palette indices were bounded to `22` and `11` in this run.
- `[FACT]` Manual owner stayed inactive.
- `[FACT]` AP calibration stayed valid: `cal_source=config`, `cal_valid=1`,
  `silence=0`.
- `[FACT]` VP stream render telemetry exceeded the nominal 2.0ms render ceiling
  on this serial stream. Max observed `render_us` was `2786us`; status
  `render_max` reached `3826us`.

## Interpretation

- `[FACT]` The Auto candidate is product-visible and materially different from
  L1 in runtime state: autonomy on, palette overlay on, bounded palette
  movement, and bounded mode transitions.
- `[FACT]` The earlier over-busy `SMART_SWITCHES_IN_WINDOW=8` behaviour is no
  longer present in this run; Scene Policy v2 capped the candidate at `3`.
- `[INFERENCE]` The candidate is safer than the prior Smart Auto orbit because
  switching pressure is lower and palette movement is bounded.
- `[INFERENCE]` This serial evidence does not prove perceptual superiority. The
  promotion gate still requires a live visual verdict or usable video/frame
  evidence across the three clip classes.

## Product Verdict

`product-validation-passed-for-current-demo`

Captain live judgement:

- steady groove / kick-drop-heavy / sparse-build set: `pass 2+ clips`

Promotion rule: Smart Auto passes only if at least two of three clips show a
clear musical/perceptual win without flooding, strobing, colour washout, or
arbitrary mode thrash.

Result: pass for current demo. This does not claim permanent product-final
status across a larger corpus.

## Doctrine Notes

- `[FACT]` No calibration command was issued.
- `[FACT]` No erase command was issued.
- `[FACT]` No upload command was issued during this A/B capture.
- `[FACT]` No firmware source edit was made by the capture script.
- `[FACT]` Camera/video evidence is intentionally absent for this run because
  the prior AVFoundation capture was too dark to support a product verdict.
