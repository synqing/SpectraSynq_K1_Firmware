# 2026-06-15 16k120 Spread4 Real-Corpus Verdict

## Verdict

`16000 / 120 / d3` with the full-AP ACF spread4 probe is **not production-promotable yet**, but the corrected software/runtime evidence is now substantially stronger than the earlier failing 16 kHz probes.

The original main-K1 corpus sweep had one active-work budget miss on the P4 music corpus:

```text
ziggyx-summer-rave-155bpm:
active_ap_work_over_7500_count = 1
emitted_active_ap_work_over_7500_count = 1
active_ap_work_max_us = 7779
```

2026-06-15 claude-mem follow-up: ZiggyX must be treated as a **cautionary stress lane**, not as a sole production oracle. Prior AceStep/P4 memory explicitly rejected ZiggyX layer-relationship evidence because of a missing `derived.layer_relationships` payload, a metronome artefact, a 17.735873 s metronome/full-mix duration mismatch, and high cross-stem leakage correlations. The K1 run below did not play the metronome stem (`all_musical_excluding_metronome`), so the original 7779 us row remains valid runtime evidence. The provenance warning means the row should drive targeted reproduction/mitigation, not a broad conclusion that Ziggy alone proves the tuple is unusable.

2026-06-15 targeted follow-up: the Ziggy exact repro passed cleanly, and the trusted four-reference subset passed cleanly. The original 7779 us row did **not** reproduce.

2026-06-15 second-device follow-up: the first bench K1 (`B489A500`) targeted subset failure was invalidated by a bench PlatformIO env inheritance bug. The child env inherited `-DARDUINO_RUNNING_CORE=0` in `build_unflags`, removing the intended AP-core override and producing a false ~104 Hz AP / ~34.7 Hz novelty collapse. After fixing the env, the corrected bench run passed the same five-reference targeted subset with 120 s compact soaks per reference.

The correct action is:

```text
keep production on 12800/96/d3
keep spread4 as a non-shippable 16k candidate
do not optimise from the single stale Ziggy spike unless it reproduces
do not use the invalidated first bench run as decision evidence
advance next work to physical I2S, matched calibration, and VP eyes-on gates
```

## What Was Tested

Target device:

```text
/dev/cu.usbmodem12201
SER=B4:3A:45:A5:87:F8
role=main K1 current live port
```

Second device:

```text
/dev/cu.usbmodem12401
SER=B4:3A:45:A5:89:B4
role=bench K1 current live port
```

Temporary probe:

```text
main env=k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4
bench env=k1_bench_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4
sample_rate=16000
samples_per_chunk=120
tempo_decim=3
expected AP=133.333 Hz
expected novelty=44.444 Hz
```

Final restored production state after probes:

```text
main K1:
FIRMWARE_VERSION: 40103
CHIP ID: F887A500
CONFIG.LIGHTSHOW_MODE: 8
CONFIG.SAMPLE_RATE: 12800
CONFIG.NOTE_OFFSET: 12
CONFIG.SAMPLES_PER_CHUNK: 96

bench K1:
FIRMWARE_VERSION: 40103
CHIP ID: B489A500
CONFIG.LIGHTSHOW_MODE: 8
CONFIG.SAMPLE_RATE: 12800
CONFIG.NOTE_OFFSET: 12
CONFIG.SAMPLES_PER_CHUNK: 96
AUDIO_RESPONSE_GAIN: 1.000000
```

No process was left holding `/dev/cu.usbmodem12201` or `/dev/cu.usbmodem12401`.

## Evidence

Primary evidence:

```text
docs/forensics/runtime-evidence/20260615T145158-k1-real-music-corpus/k1-real-music-corpus-summary.json
docs/forensics/runtime-evidence/20260615T154939-k1-real-music-corpus/k1-real-music-corpus-summary.json
docs/forensics/runtime-evidence/20260615T142351-k1-real-music-corpus/k1-real-music-corpus-summary.json
docs/forensics/runtime-evidence/20260615T-ziggy-repro-k1-real-music-corpus/k1-real-music-corpus-summary.json
docs/forensics/runtime-evidence/20260615T-trusted-subset-k1-real-music-corpus/k1-real-music-corpus-summary.json
docs/forensics/runtime-evidence/20260615T-bench-targeted-subset-k1-real-music-corpus/k1-real-music-corpus-summary.json
docs/forensics/runtime-evidence/20260615T-bench-corrected-targeted-subset-k1-real-music-corpus/k1-real-music-corpus-summary.json
```

The real-corpus runner used locally rendered P4 music stems and did not generate synthetic audio, run calibration, erase flash, tune tempo, or change production DSP constants. The corrected compact-soak harness loops the rendered real-music clip for the requested soak duration; the corrected bench gate used 120,000 ms per reference.

## Corpus Result

Clean references across the partial matrix and risk-set retry:

```text
arminvanbuuren-sonicsamba-142bpm
avicii-levels-126bpm
brennanheart-jonathanmendelsohn-imaginary-150bpm
charlottedewitte-sgadilimi-135bpm
collapz-the-valhalla-king-143bpm
davidguettamorten-dreams-128bpm
djkuba-neitanxravekings-renaissance-138bpm
eric-clapton-wonderful-tonight-95bpm
fisher-losingit-125bpm
hi-lo-poseidon-127bpm
i-malive-125bpm
kato-jon-turnthelightsoff-137bpm
lavern-inmymind-130bpm
maddix-activating-130bpm
martingarrix-animals-128bpm
subfocus-solarsystem-174bpm
tntrecords-skyfire-151bpm
deadmau5-ghosts-n-stuff-129bpm
```

Clean-reference envelope:

```text
AP Hz:              133.332 .. 133.337
novelty Hz:         44.444 .. 44.445
active-work p95:    7040 .. 7168 us
active-work max:    7369 .. 7458 us
I2S faults:         0
byte mismatches:    0
core faults:        0
frame gaps:         0
timestamp regress:  0
over-7500 rows:     0
```

Failing/cautionary reference:

```text
ziggyx-summer-rave-155bpm
AP Hz:                       133.334
novelty Hz:                  44.445
rows:                        16000
active-work p95:             7040 us
active-work max:             7779 us
active_over_7500_count:      1
emitted_active_over_7500:    1
hard_failures:
  - active_ap_work_over_7500_count
  - emitted_active_ap_work_over_7500_count
```

Ziggy provenance boundary:

```text
claude-mem observation 64094:
  ZiggyX layer-relationship evidence rejected
  metronome duration mismatch: 17.735873 s
  high leakage correlations present

P4 beat-grid files:
  selected-stem confidence:          0.497971
  steady-phase metronome confidence: 0.969845
  prior-free metronome confidence:   0.969925

K1 playback mix:
  all_musical_excluding_metronome
```

Targeted follow-up:

```text
ziggyx-summer-rave-155bpm exact repro:
  AP Hz:                    133.334
  novelty Hz:               44.444
  active-work p95:          7040 us
  active-work max:          7391 us
  over-7500 rows:           0

trusted subset:
  subfocus-solarsystem-174bpm:       max 7381 us, over-7500 rows 0
  tntrecords-skyfire-151bpm:         max 7438 us, over-7500 rows 0
  deadmau5-ghosts-n-stuff-129bpm:    max 7393 us, over-7500 rows 0
  martingarrix-animals-128bpm:       max 7397 us, over-7500 rows 0

invalidated bench K1 targeted subset:
  ziggyx-summer-rave-155bpm:         AP 104.193 Hz, NOV 34.731 Hz, p95 10496 us, max 13009 us
  subfocus-solarsystem-174bpm:       AP 103.964 Hz, NOV 34.655 Hz, p95 10624 us, max 11648 us
  tntrecords-skyfire-151bpm:         AP 103.965 Hz, NOV 34.655 Hz, p95 10624 us, max 11629 us
  deadmau5-ghosts-n-stuff-129bpm:    AP 103.924 Hz, NOV 34.641 Hz, p95 10624 us, max 11573 us
  martingarrix-animals-128bpm:       AP 104.446 Hz, NOV 34.815 Hz, p95 10368 us, max 11571 us

corrected bench K1 targeted subset, 120 s compact soaks:
  ziggyx-summer-rave-155bpm:         AP 133.334 Hz, NOV 44.444 Hz, p95 7040 us, max 7412 us, over-7500 rows 0
  subfocus-solarsystem-174bpm:       AP 133.335 Hz, NOV 44.445 Hz, p95 7168 us, max 7424 us, over-7500 rows 0
  tntrecords-skyfire-151bpm:         AP 133.332 Hz, NOV 44.444 Hz, p95 7168 us, max 7436 us, over-7500 rows 0
  deadmau5-ghosts-n-stuff-129bpm:    AP 133.334 Hz, NOV 44.444 Hz, p95 7040 us, max 7469 us, over-7500 rows 0
  martingarrix-animals-128bpm:       AP 133.335 Hz, NOV 44.444 Hz, p95 7168 us, max 7422 us, over-7500 rows 0
```

The earlier `martingarrix-animals-128bpm` `capture_command_failed` in `20260615T145158` was caused by aborting the broader sweep, not by a device-side runtime failure. The retry in `20260615T154939` passed cleanly.

## Engineering Conclusion

The compact APCAD soak fix is valid: long real-music soaks now avoid repeated serial reopen/dump pressure and can run multiple references without leaving `/dev/cu.usbmodem12201` or `/dev/cu.usbmodem12401` hung.

The 16 kHz spread4 probe is still a research candidate only. It clears the targeted P4 music stress lanes, including Ziggy, 174 BPM SubFocus, 151 BPM TNT, deadmau5, and Martin Garrix, on both the main K1 and the corrected bench K1 probe. The single 7779 us emitted active-work spike on Ziggy did not reproduce under exact main-K1 rerun, so it is now a stale tail-risk datapoint, not an active blocker. The first bench collapse is invalidated by the env inheritance bug and is retained only as process evidence for why bench-safe probe envs need explicit upload-guard and build-flag tests.

## Next Work

1. Keep K1 production on `12800/96/d3`.
2. Keep the single Ziggy 7779 us row as tail-risk evidence, but do not patch against it unless reproduced.
3. Preserve the bench-safe 16k probe env and upload-guard coverage so future second-device checks do not cross-flash or lose the AP-core override.
4. If any future repro produces active-work > 7500 us, reduce it with one of:
   - smaller ACF spread quantum,
   - stricter publish/update separation,
   - lower-cost tempo confidence update on emitted frames,
   - bounded skip/defer path for rare heavy emitted frames.
5. Continue with:
   - physical I2S BCLK/WS/DOUT capture for 12.8 kHz and 16 kHz,
   - matched no-music and music calibration provenance for 12.8 kHz versus 16 kHz,
   - eyes-on VP acceptance against production baseline.
