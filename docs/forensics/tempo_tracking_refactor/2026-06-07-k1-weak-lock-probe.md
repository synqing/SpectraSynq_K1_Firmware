# K1 Weak-Lock Probe Checkpoint

## Verdict

Status: **weak-lock cadence/replay evidence improved, no production promotion**.

This pass moved the next blocker from generic "weak lock" into two separate facts:

- `slow_84_syncopated` has healthy AP/NOV cadence and declared-rate buffered NOV replay locks near the expected `84 BPM`.
- `click_127` and `fast_127_fourfloor` have healthy AP/NOV cadence and declared-rate buffered NOV replay locks near the expected `127 BPM` after using gain-normalised `ffplay` capture.
- `loreen_127` has healthy AP/NOV cadence and declared-rate buffered NOV replay stays near the expected `127 BPM`, but remains weak-lock because there are no high-confidence or locked warm rows in the bounded 20s capture.
- The initial ungained `afplay`/`ffplay` captures for the 127 BPM click lanes were invalid as proof because their APCAD rows were marked silent throughout; the harness now exposes the playback path needed to avoid that false-negative capture setup.

No production DSP, tempo constants, AGC, GDFT, sample rate, or BPM range was changed.

## Device and Build

- Target: main K1 `/dev/cu.usbmodem1401`, serial `B4:3A:45:A5:87:F8`
- Probe env uploaded: `k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1`
- Production restore after probe: `pio run -e k1_hardware -t upload` **SUCCESS**
- Production restore after gain-normalised 127 BPM recaptures: `pio run -e k1_hardware -t upload` **SUCCESS**
- Probe warnings were the known `system.h` volatile warning and non-shippable `gdft_harness.h` IRAM attribute warning.

## Harness Change

`scripts/regression-harness/device_novelty_replay.py` now accepts generic expected-BPM scoring:

- `--expected-bpm`
- `--near-bpm-tolerance`

The replay summary keeps the historical near-127 fields for compatibility and adds target-relative fields such as `warm_high_or_locked_near_target_rows`. This is required because weak-lock proof now includes the required `84 BPM` slow lane, not only the historical 127 BPM click lane.

`scripts/regression-harness/device_ap_cadence_capture.py` now supports the AV-style playback path needed for level-controlled recaptures:

- `--player ffplay`
- `--start-ms`
- `--playback-gain-db`

Default `afplay` behaviour is preserved for existing probe commands.

Verification:

- `python -m py_compile scripts/regression-harness/device_ap_cadence_capture.py scripts/regression-harness/device_novelty_replay.py`: **PASS**
- `python -m pytest tests/test_k1_av_regression_static.py -q`: **PASS** (`28 passed`)

## Slow 84 Probe

APCAD capture:

- Summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_slow84_apcad_20260607_061427__summary.json`
- Raw log: `build/audio-semantic-metrics/weak-lock-probe/weaklock_slow84_apcad_20260607_061427__raw.log`
- APCAD log: `build/audio-semantic-metrics/weak-lock-probe/weaklock_slow84_apcad_20260607_061427__apcad.log`
- Measured AP rate: `133.37580355591592 Hz`
- Measured accepted NOV rate: `44.448307834955955 Hz`
- I2S status: clean
- Bytes mismatch count: `0`
- AP core: `[0]`
- VP core: `[1]`

Declared-rate replay:

- Replay summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_slow84__declared_rate_replay.json`
- Classification: `declared_rate_device_nov_replay_locks_near_target`
- Expected BPM: `84`
- Warm median BPM: `84`
- Warm near-target rows: `1288`
- Warm locked near-target rows: `148`
- Warm high-or-locked near-target rows: `148 / 148`

Interpretation: the slow required lane has cadence-replay proof. Its production AP-stream weak-lock label is not a cadence failure.

## 127 BPM Probe

### Invalid Baseline Captures

Before adding gain-normalised playback, `click_127` and `fast_127_fourfloor` showed healthy cadence but invalid all-silent input:

- `fast_127_fourfloor`: `2304 / 2304` APCAD rows marked silent; replay landed at `108 BPM`.
- `click_127`: `2203 / 2203` APCAD rows marked silent; replay landed at `108 BPM`.
- `click_127` with `ffplay` and no gain: `2236 / 2236` APCAD rows marked silent.

Those captures are retained as evidence of the harness playback-level failure and are not used as fixture proof.

### `click_127`

APCAD capture:

- Summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_click127_ffplay_gain18_apcad_20260607_062044__summary.json`
- Measured AP rate: `133.3658715148557 Hz`
- Measured accepted NOV rate: `44.44444444444444 Hz`
- I2S status: clean
- Bytes mismatch count: `0`
- AP core: `[0]`
- VP core: `[1]`
- Playback: `ffplay`, `+18 dB`
- Silence rows: `1074 / 2187`

Declared-rate replay:

- Replay summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_click127_ffplay_gain18__declared_rate_replay.json`
- Classification: `declared_rate_device_nov_replay_locks_near_target`
- Warm median BPM: `126`
- Warm near-target rows: `1521`
- Warm locked near-target rows: `453`
- Warm high-or-locked near-target rows: `1017 / 1017`

### `fast_127_fourfloor`

APCAD capture:

- Summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_fast127_ffplay_gain18_apcad_20260607_062155__summary.json`
- Measured AP rate: `133.32140300644238 Hz`
- Measured accepted NOV rate: `44.44975504839288 Hz`
- I2S status: clean
- Bytes mismatch count: `0`
- AP core: `[0]`
- VP core: `[1]`
- Playback: `ffplay`, `+18 dB`
- Silence rows: `50 / 2236`

Declared-rate replay:

- Replay summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_fast127_ffplay_gain18__declared_rate_replay.json`
- Classification: `declared_rate_device_nov_replay_locks_near_target`
- Warm median BPM: `127`
- Warm near-target rows: `1569`
- Warm locked near-target rows: `700`
- Warm high-or-locked near-target rows: `1569 / 1569`

Interpretation: 127 BPM weak-lock is not explained by AP/NOV cadence. With valid playback level, buffered NOV replay locks near target for both click and fast generated controls. The production AP-stream weak-lock label remains a one-Hz AP-stream confidence/lock-surface limitation, not a cadence failure.

### `loreen_127`

APCAD capture:

- Summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_loreen127_ffplay_apcad_20260607_062442__summary.json`
- Measured AP rate: `133.37199188170484 Hz`
- Measured accepted NOV rate: `44.44702332598352 Hz`
- I2S status: clean
- Bytes mismatch count: `0`
- AP core: `[0]`
- VP core: `[1]`
- Playback: `ffplay`, `0 dB`
- Silence rows: `1392 / 2301`

Declared-rate replay:

- Replay summary: `build/audio-semantic-metrics/weak-lock-probe/weaklock_loreen127_ffplay__declared_rate_replay.json`
- Classification: `declared_rate_device_nov_replay_timing_but_weak_lock`
- Warm median BPM: `129`
- Warm near-target rows: `1635`
- Warm locked near-target rows: `0`
- Warm high-or-locked near-target rows: `0 / 0`

Interpretation: the Loreen weak-lock lane is not a cadence failure and does not show a wrong tempo lane in this bounded probe, but it still lacks the confidence/lock evidence needed to treat the real-music lane as closed.

## Open Work

- Keep production promotion deferred until Captain/video Scene Policy v2 perceptual A/B judgement.
- Do not tune tempo constants from ungained APCAD captures.
- ~~Decide whether the AV matrix should distinguish "timing proven by probe replay" from "one-Hz production stream weak lock"~~ **Done** — see `2026-06-07-k1-weak-lock-matrix-reconciliation.md` and `WEAK_LOCK_NOV_RECONCILED_FIXTURES`.
- `loreen_127` remains a scoped P2 confidence residual: near-target timing, lock/confidence absent in bounded replay. Not a cadence failure; does not block Scene Policy v2 state gate.
- ~~Silence/open-quiet P1~~ **Closed** — `2026-06-07-k1-silence-open-quiet-vu-gate.md`.
