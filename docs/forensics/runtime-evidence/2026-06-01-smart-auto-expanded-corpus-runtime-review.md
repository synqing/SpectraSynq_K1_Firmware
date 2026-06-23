---
abstract: "Expanded nine-clip Smart Auto A/B runtime review. Serial/state validity passed; captured-video subset passed autonomous visual review; full expanded-video promotion is not claimed because four camera captures failed."
evidence-tier: "hardware-runtime"
created: "2026-06-01"
---

# Smart Auto Expanded Corpus Runtime Review

## Scope

[FACT] This run used the expanded nine-clip corpus from
`docs/forensics/runtime-evidence/2026-06-01-smart-auto-expanded-corpus-manifest.json`.

[FACT] The capture command was:

```sh
python3 -B scripts/regression-harness/smart_auto_product_ab_capture.py \
  --clip-manifest docs/forensics/runtime-evidence/2026-06-01-smart-auto-expanded-corpus-manifest.json \
  --out-dir docs/forensics/runtime-evidence \
  --video-device "1:none"
```

[FACT] The capture script sends only colon-framed runtime status/scene/stream
commands. It does not upload, erase, reset, factory reset, or run calibration.

## Evidence Files

- Manifest:
  `docs/forensics/runtime-evidence/2026-06-01T213207-smart-auto-ab-manifest.json`
- Main K1v2 L1 reference log:
  `docs/forensics/runtime-evidence/2026-06-01T213207-smart-auto-ab-main-k1v2.log`
- Second bench K1 Smart Auto candidate log:
  `docs/forensics/runtime-evidence/2026-06-01T213207-smart-auto-ab-bench-k1-2nd.log`
- Local video/frame files:
  `docs/forensics/runtime-evidence/2026-06-01T213207-*`

## Device Identity

| Device | Port | Role | Version | Chip ID |
|---|---|---|---|---|
| Main K1v2 | `/dev/tty.usbmodem12201` | L1 reference | `40103` | `B489A500` |
| Second bench K1 | `/dev/tty.usbmodem1401` | Smart Auto candidate | `40103` | `F887A500` |

## Runtime State Gate

| Gate | Main K1v2 | Second bench K1 |
|---|---|---|
| Clip count | 9/9 clip ends | 9/9 clip ends |
| `ffplay_rc` | 9/9 zero | 9/9 zero |
| `SMART_DIRECTOR_AUTONOMY` | always `off` | always `on` |
| `SMART_PALETTE_OVERLAY` | always `0` | always `1` |
| `SMART_MANUAL_OWNER_ACTIVE` | always `0` | always `0` |
| Max `SMART_SWITCHES_IN_WINDOW` | `1` | `3` |
| Panic/WDT/assert scan | none found | none found |

[FACT] The state/log gate passed for the expanded run.

## Video Capture Health

[FACT] AVFoundation device `1:none` was available as `EiP Camera`, but did not
finish cleanly for every clip. The harness was repaired during this wave so a
stuck `ffmpeg` process is killed and recorded instead of aborting the full run.

| Video outcome | Clips |
|---|---|
| `video_rc=0`, frames extracted | `steady-groove-regard-late`, `drop-heavy-shelter-main`, `sparse-build-carte-early`, `vocal-chorus-touchme-mid`, `high-density-carte-finale` |
| `video_rc=-9`, `video_killed=True` | `steady-groove-lavern-mid`, `drop-heavy-touchme-late`, `sparse-build-shelter-early`, `vocal-chorus-lavern-late` |

## Product Verdict

`captured-video-subset-passed-full-expanded-video-promotion-not-claimed`

[FACT] The run proves expanded-corpus device identity, serial/state validity,
manual-owner non-interference, bounded Auto switching, and audio playback
success.

[FACT] Codex inspected contact sheets generated from the five extracted frame
sets under `docs/forensics/runtime-evidence/2026-06-01T213207-frames-*`.

| Clip | Video/frame outcome | Visual review |
|---|---|---|
| `steady-groove-regard-late` | captured | pass: visible bounded motion and colour variation; no observed flood, strobe, washout, or arbitrary mode thrash |
| `drop-heavy-shelter-main` | captured | pass: energy lift is visible with bounded green/blue/yellow roles; no observed flood, strobe, washout, or arbitrary mode thrash |
| `sparse-build-carte-early` | captured | pass: sparse/build section shows controlled green/magenta/pink trajectory; no observed flood, strobe, washout, or arbitrary mode thrash |
| `vocal-chorus-touchme-mid` | captured | pass: chorus capture shows varied colour accents and bounded intensity; no observed flood, strobe, washout, or arbitrary mode thrash |
| `high-density-carte-finale` | captured | pass: dense section remains bounded and readable; no observed flood, strobe, washout, or arbitrary mode thrash |

[FACT] Four expanded-corpus clips did not produce usable video/frame evidence
because AVFoundation capture was killed and recorded by the harness:
`steady-groove-lavern-mid`, `drop-heavy-touchme-late`,
`sparse-build-shelter-early`, and `vocal-chorus-lavern-late`.

[INFERENCE] The captured-video subset does not trigger Scene Policy v2: the
reviewed clips did not show the failure modes that would justify replacing the
current Smart Auto policy.

[INFERENCE] This is not a full expanded-corpus product promotion. The correct
status is: current three-clip Smart Auto demo gate remains passed; expanded
nine-clip state/log gate passed; expanded visual evidence is partially reviewed
and acceptable for the captured five clips, but incomplete for a 9/9 visual
promotion claim.

## Changelog

| Date | Change |
|---|---|
| 2026-06-01 | Added expanded Smart Auto runtime review after nine-clip capture. |
| 2026-06-01 | Closed autonomous visual review for captured frame subset and recorded incomplete-video boundary. |
