---
abstract: "Expanded Smart Auto product A/B clip corpus and pass/fail rubric for broader local-song validation."
evidence_tier: "prep-manifest-no-hardware"
date: "2026-06-01"
---

# Smart Auto Expanded Corpus Rubric

## Scope

This is a prep artefact for the Smart Auto product A/B capture lane. It does not
claim runtime behaviour, visual quality, serial proof, upload success, or
hardware state.

[FACT] Existing Smart Auto runtime evidence used a three-clip corpus:

- `Regard_Ride_It.mp3`, `125s-150s`, steady groove.
- `Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3`, `75s-100s`, kick/drop-heavy.
- `Carte-Blanche-Mixed.mp3`, `20s-45s`, sparse/build.

[FACT] The local AceStep song directory available to this lane contains five
candidate audio files:

- `/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Carte-Blanche-Mixed.mp3`
- `/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Ian Asher - Touch Me.mp3`
- `/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Lavern_InMyMind.mp3`
- `/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Regard_Ride_It.mp3`
- `/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs/Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3`

[FACT] Duration bounds were checked with `ffprobe`; no audio was played.

## Machine Manifest

Use:

`docs/forensics/runtime-evidence/2026-06-01-smart-auto-expanded-corpus-manifest.json`

Example capture command:

```sh
python3 -B scripts/regression-harness/smart_auto_product_ab_capture.py \
  --clip-manifest docs/forensics/runtime-evidence/2026-06-01-smart-auto-expanded-corpus-manifest.json \
  --out-dir docs/forensics/runtime-evidence
```

The harness still sends only colon-framed status/scene/stream commands. The
manifest extension does not add calibration, erase, upload, reset, or
factory-default command surfaces.

## Selected Corpus

| ID | Coverage | Track | Window |
|---|---|---|---|
| `steady-groove-regard-late` | steady groove | `Regard_Ride_It.mp3` | `125s-150s` |
| `steady-groove-lavern-mid` | steady groove | `Lavern_InMyMind.mp3` | `45s-70s` |
| `drop-heavy-shelter-main` | drop-heavy | `Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3` | `75s-100s` |
| `drop-heavy-touchme-late` | drop-heavy | `Ian Asher - Touch Me.mp3` | `96s-121s` |
| `sparse-build-carte-early` | sparse/build | `Carte-Blanche-Mixed.mp3` | `20s-45s` |
| `sparse-build-shelter-early` | sparse/build | `Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3` | `10s-35s` |
| `vocal-chorus-touchme-mid` | vocal/chorus | `Ian Asher - Touch Me.mp3` | `48s-73s` |
| `vocal-chorus-lavern-late` | vocal/chorus | `Lavern_InMyMind.mp3` | `70s-95s` |
| `high-density-carte-finale` | high-density | `Carte-Blanche-Mixed.mp3` | `55s-80s` |

## Pass/Fail Rubric

### Run Validity

The run is invalid if any of these occur:

- Either device identity is missing from the manifest or serial logs.
- Any clip reports non-zero `ffplay_rc`.
- Any path in the clip manifest is missing at run time.
- Any serial log contains panic, Guru Meditation, WDT, assertion, unexpected
  reboot during clip playback, calibration invalidation, or persistent silence
  classification under music.
- Any calibration, erase, upload, reset, or factory command appears in the run
  logs.

### Smart Auto State Gate

Smart Auto candidate passes the state gate only if all of these are true:

- `SMART_DIRECTOR_AUTONOMY` stays `on` for every clip.
- `SMART_PALETTE_OVERLAY` stays enabled or has an explicitly documented reason
  for being disabled in a specific clip.
- `SMART_MANUAL_OWNER_ACTIVE` stays `0`.
- `cal_source=config`, `cal_valid=1`, and `silence=0` remain stable under music.
- Mode switching stays bounded by the current scene-policy limits; any
  `SMART_SWITCHES_IN_WINDOW` value above the configured max is a fail unless
  the policy changed and the evidence document cites the new source.

### Product Visual Gate

Captain/video review passes the expanded corpus only if:

- At least six of nine clips are judged a clear musical/perceptual win over L1.
- At least one clip passes in each coverage class: steady groove, drop-heavy,
  sparse/build, vocal/chorus, and high-density.
- No more than one clip fails for flooding, strobing, colour washout, or
  arbitrary mode thrash.
- Drop-heavy clips must feel energetic without hitting uncontrolled switch
  churn.
- Sparse/build clips must show restraint during low-density moments and grow
  visibly when the track builds.
- Vocal/chorus clips must preserve colour clarity and avoid distracting mode
  changes over the hook.
- High-density clips must remain legible rather than collapsing into white,
  noisy sparkle, or constant palette churn.

### Evidence Labels

Use `[FACT]` for parsed manifest, serial log, ffplay return code, device
identity, and direct video-frame observations. Use `[INFERENCE]` for product
quality interpretations. Do not label Smart Auto as product-final from this
corpus alone; this is an expanded validation gate, not permanent release proof.

## Integration Recommendation

Use the new `--clip-manifest` option for the next Smart Auto A/B run. Keep the
three original windows in the corpus as anchors, then compare the six new
windows against the same state and product visual gates. If the expanded run
passes, write a follow-up runtime-evidence document beside this prep artefact
that cites the generated manifest and both serial logs.

## Changelog

| Date | Change |
|---|---|
| 2026-06-01 | Added expanded nine-clip Smart Auto corpus and pass/fail rubric. |
