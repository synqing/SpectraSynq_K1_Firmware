# DEVICE Audio-Semantic Gate Closeout

## Verdict

[FACT] **GATE CLOSED** on 2026-07-15 for the five production flags:
`K1_TEMPO_CONF_V2`, `K1_TEMPO_FLYWHEEL_V2`, `K1_ONSET_V2`,
`K1_CHORD_V2`, and `K1_SEMANTIC_STATE`.

[FACT] The measured firmware identified itself as commit
`52a21db5d235cf3afeb946185c1043cbaed59d35`; the pinned session source
fingerprint was `caacb24bf26a47cd63095a63bf91b23a8d6a0d2b21e2330f0ec7c7cdb001b818`.

[FACT] Every device operation targeted bench chip `B489A500` on explicit
capture port `/dev/cu.usbmodem112401`. The main K1 was not targeted.

[FACT] The repository was dirty during the run. The source fingerprint, runtime
build banner, track hashes, raw captures, and exact commands are therefore the
reproduction authority; the git SHA alone is not represented as a clean-tree
binary identity.

## Truthumbers

[FACT] Six device-novelty EDM tracks at 126-135 BPM produced Acc1 **100.0%**,
Acc2 **100.0%**, octave-error **0.0%**, and mean raw locked fraction **47.0%**.

[FACT] All six tracks are in the load-bearing **120-140 BPM** bucket, where the
device results are Acc1 **100.0%**, Acc2 **100.0%**, octave-error **0.0%**, and
raw locked fraction **47.0%**. The cross-corpus host-clean reference for that bucket
is Acc1/Acc2 **16.7%**.

[FACT] These figures supersede the earlier **83.3% / 50.4%** aggregate and the
earlier Dreams **73 BPM** result. The scorer incorrectly treated absolute device
uptime as trajectory-relative time when selecting the final half. The corrected
cutoff is `first_timestamp + 0.5 * (last_timestamp - first_timestamp)` and is
regression-tested with a non-zero timestamp origin.

[INFERENCE] The positive delta does not prove that device GDFT novelty is better
than clean spectral flux because the device and host rows use different corpora.
It proves the requested device behaviour on this six-track EDM set.

[FACT] The complete all-scope, in-range, per-bucket, and per-track delta table is
[`2026-07-14-device-novelty-tempo-delta.md`](2026-07-14-device-novelty-tempo-delta.md).

## Paired Novelty-Source Result

[FACT] On the same six tracks through the same compiled detector, host-clean
spectral flux scored Acc1 **33.3%** and Acc2 **50.0%** while IM73D device novelty
scored Acc1/Acc2 **100.0%**. Therefore the hypothesis that device novelty reduces
tempo correctness is **NOT_SUPPORTED** by this corpus.

[FACT] Raw lock occupancy was higher for clean novelty (**94.9%**) than device
novelty (**47.0%**), but clean wrong-lane lock was **42.7%** versus device
**1.8%**. Acc1-correct lock occupancy was **44.2%** clean versus **43.8%** device.

[INFERENCE] Raw lock occupancy alone is not a useful success metric here because
the clean arm frequently locks with confidence to an incorrect tempo. The IM73D
front-end is more conservative on this set, and Dreams remains weak at only
**7.5%** Acc1-correct lock occupancy.

[FACT] The paired table, per-track trajectories, limitations, and exact rerun are
in [`2026-07-15-im73d-paired-novelty.md`](2026-07-15-im73d-paired-novelty.md).

## Five-Flag Evidence

| Flag | DEVICE evidence | Verdict |
|---|---|---|
| `K1_TEMPO_CONF_V2` | Six-track device-novelty replay plus same-track V1-off/V2 A/B; V2 median confidence 0.796 and final-half lock 67.8% on Animals | PASS |
| `K1_TEMPO_FLYWHEEL_V2` | Same-track V1-off/V2 A/B; 128 BPM V1-off and 129 BPM V2, both Acc1 at 128 BPM, with no frame gap, I2S fault, or crash signature | PASS |
| `K1_ONSET_V2` | Same-track V1-off/V2 AP samples plus corrected stable-key Percussion Burst eyes-on; V2 onset-positive 41/125 and bass-onset-positive 42/125 | PASS |
| `K1_CHORD_V2` | Corrected stable-key Dense Forge Chord V1-off/V2 eyes-on, matching raw ordinal 24, no crash, and Captain no-regression verdict | PASS |
| `K1_SEMANTIC_STATE` | V2 production flag present in runtime build; V1-off control removes it; corrected semantic-consumer eyes-on set ran without crash or Captain-observed regression | PASS |

[FACT] Production AP telemetry does not expose a chord field. The chord verdict
is therefore a correctly labelled device eyes-on result, not a fabricated
numeric chord metric.

[FACT] The complete same-track V1-off/V2 table is
[`2026-07-14-device-audio-semantic-v1-v2.md`](2026-07-14-device-audio-semantic-v1-v2.md).

[FACT] The corrected eight-window effect A/B is
[`2026-07-15-device-effect-eyes-on-corrected.md`](2026-07-15-device-effect-eyes-on-corrected.md).

## Adversarial Findings

[FACT] The first focused effect captures were invalid: raw ordinals 12, 16, 18,
and 23 rendered Aurora, Ember Field, Waveform Tempo, and Pulse Prism rather than
the claimed effects. They remain `MISLABELLED_INVALID` and are superseded by
stable-key captures at ordinals 20, 24, 26, and 32.

[FACT] The final corrected capture left mode 32 selected after playback. Its
silence-gated behaviour made the primary appear dead. Live readback proved full
brightness and mode 32; primary was restored to mode 18 and Captain confirmed it
visible. The capture harness now restores the pre-test mode by default and
requires `--leave-effect-selected` to opt out.

[FACT] The mode-numbering and residual-state incident is recorded in
[`2026-07-14-device-eyes-on-mode-numbering-incident.md`](../forensics/2026-07-14-device-eyes-on-mode-numbering-incident.md).

[FACT] AP active-time p95 was 6.016 ms on V1-off and 6.912 ms on V2; observed
maxima were 9.483 ms and 10.121 ms. No frame gaps or I2S faults were recorded.
This lane reports the known frame-budget pressure and does not modify it.

## Exact Re-runs

[FACT] Re-run the six-track device corpus and regenerate every tempo number:

```bash
python3 scripts/regression-harness/device_novelty_corpus_run.py docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-corpus.json --preflight-report docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/edm-ground-truth-preflight.json --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_ap_frontend_probe --duration-ms 120000 --out-dir docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/captures --score-manifest docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/device-corpus-manifest.json --commands-out docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/rerun-commands.json --out-json docs/measurements/2026-07-14-device-novelty-tempo-delta.json --out-md docs/measurements/2026-07-14-device-novelty-tempo-delta.md --resume
```

[FACT] Re-score the same-track V1-off/V2 comparison and five-flag verdict:

```bash
python3 scripts/regression-harness/device_semantic_ab_score.py --v1-summary docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/eyes-on-ab/v1-off-animals-128_nov_buffered_20260714_225608__summary.json --v2-summary docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/eyes-on-ab/v2-animals-128_nov_buffered_20260714_225907__summary.json --expected-bpm 128 --captain-eyes-on PASS --eyes-on-evidence docs/measurements/2026-07-15-device-effect-eyes-on-corrected.json --out-json docs/measurements/2026-07-14-device-audio-semantic-v1-v2.json --out-md docs/measurements/2026-07-14-device-audio-semantic-v1-v2.md
```

[FACT] Re-score the corrected stable-key effect eyes-on set:

```bash
python3 scripts/regression-harness/device_effect_eyes_on_score.py --input-dir docs/forensics/runtime-evidence/20260715-device-eyes-on-corrected --tempo PASS --chord PASS --onset PASS --waveform PASS --out-json docs/measurements/2026-07-15-device-effect-eyes-on-corrected.json --out-md docs/measurements/2026-07-15-device-effect-eyes-on-corrected.md
```

[FACT] Literal per-track capture/replay child commands are stored in
`docs/forensics/runtime-evidence/20260714-device-eyes-on-resume/rerun-commands.json`;
literal corrected effect capture commands are stored in the eyes-on measurement
document above.
