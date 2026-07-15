# Captivation A/B: Modes 32, 35, and 36

## Verdict

[FACT] The 2026-07-13 host gate for Shockwave and Iris originated at
`49ea369`. The effect implementations and their math cores are byte-identical
between `49ea369` and the device-tested source `f2257ef`.

[FACT] Captain's 2026-07-15 bench verdict is:

| Mode | Source identity | Mechanical device leg | Captain captivation verdict | Product decision |
|---:|---|---|---|---|
| 32 | Waveform Hybrid K1 | PASS | strongest of the three | RETAIN |
| 35 | Shockwave | PASS | FAIL | REJECT |
| 36 | Iris | PASS | FAIL | REJECT |

[FACT] `PASS` in the mechanical column means the intended build, chip, raw
ordinal, and source-derived mode name were read back before playback; the
30-second stimulus completed; no crash signature was observed; and the
pre-test mode was restored. It is not a captivation claim.

[FACT] The 32/35/36 product comparison is **CLOSED**. Shockwave and Iris ran
correctly but did not meet the Waveform captivation bar. This is a negative
product finding, not a hardware or host-test failure.

## Device And Artifact

| Field | Observed value |
|---|---|
| Role | bench K1 |
| USB serial | `B4:3A:45:A5:89:B4` |
| Chip ID | `B489A500` |
| Upload port | `/dev/tty.usbmodem112401` |
| Capture port | `/dev/cu.usbmodem112401` |
| Environment | `k1_bench_im73d` |
| Runtime build | `BUILD: version=40103 git=f2257ef epoch=1784118604 env=k1_bench_im73d` |
| Source fingerprint | `e045533d8f894a7816d36e79f48f1a5c99a5a6fae0fd5effdd750406282f43cb` |
| Flash used | `696,502 B` |
| Final flashed `firmware.bin` size | `696,896 B` |
| Final flashed `firmware.bin` SHA256 | `ee92b495a0c56bfb80994ec164cb600dee9d8fd9238d6539ff97965d43a5df50` |

[FACT] The earlier ledger SHA256
`a627476216dbd182bb826a9bca7ba9b2ee220abd39567f22896a323bea50c0b4`
belongs to the historical `k1_hardware @ 49ea369` host build. It is not the
IM73D bench artifact flashed for this A/B.

## Controlled Stimulus

| Field | Value |
|---|---|
| Track | Martin Garrix, `Animals` |
| Ground-truth BPM | `128.0` |
| File | `/Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3` |
| Track SHA256 | `174025b5ff4d326675cfb3b31b820e8448242d1b51d1a3b00e236e66373cc61a` |
| Playback | file start, `/usr/bin/afplay`, gain `1.0` |
| Leg duration | `30.0 s` |
| Eyes-on countdown | `5.0 s` after identity/mode preflight |
| Pre-test/restored mode | `18` |

## Mechanical Results

| Mode | Runtime name | Observed ordinal | Duration | Crash signatures | Restored mode | Result |
|---:|---|---:|---:|---:|---:|---|
| 32 | `WAVEFORM HYBRID K1` | 32 | 30.0 s | 0 | 18 | PASS |
| 35 | `SHOCKWAVE` | 35 | 30.0 s | 0 | 18 | PASS |
| 36 | `IRIS` | 36 | 30.0 s | 0 | 18 | PASS |

## Host Validation Boundary

[FACT] Targeted identity, upload-guard, session-safety, and effect-score tests
passed `38/38`:

```bash
python3 -m pytest tests/test_device_effect_eyes_on_score.py tests/test_k1_upload_guard.py tests/test_k1_upload_guard_identity_static.py tests/test_session_safety_guards.py -q
```

[FACT] The clean `f2257ef` full suite completed `762 passed, 1 skipped, 2
failed`. Both failures are inherited stale `k1_custom` topology assertions:
`test_led_count_224_is_flag_gated_only` and
`test_single_channel_secondary_is_flag_guarded`. This closeout changes neither
the custom-LED source nor those tests. Exact rerun:

```bash
python3 -m pytest tests/ -q
```

## Exact Re-runs

[FACT] Create the exact clean source worktree, pin only the bench target, build,
and flash the recorded source:

```bash
git worktree add --detach /private/tmp/k1-captivation-rerun-f2257ef f2257ef
cd /private/tmp/k1-captivation-rerun-f2257ef
python3 scripts/platformio/k1_session_target.py pin --chip-id B489A500 --upload-port /dev/tty.usbmodem112401 --capture-port /dev/cu.usbmodem112401 --env k1_bench_im73d --purpose 'Captivation A/B modes 32 35 36' --ttl-seconds 14400
python3 scripts/platformio/k1_session_target.py verify --env k1_bench_im73d --port /dev/tty.usbmodem112401
bash scripts/agent/pio-build.sh k1_bench_im73d
script -q /private/tmp/k1-captivation-rerun-f2257ef-upload.log pio run -e k1_bench_im73d -t upload --upload-port /dev/tty.usbmodem112401
```

[FACT] From the canonical repo checkout containing
`scripts/regression-harness/device_captivation_leg.py`, rerun each equal-condition
leg:

```bash
python3 scripts/regression-harness/device_captivation_leg.py --repo /private/tmp/k1-captivation-rerun-f2257ef --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_im73d --expected-git f2257ef --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --expected-track-sha256 174025b5ff4d326675cfb3b31b820e8448242d1b51d1a3b00e236e66373cc61a --mode 32 --duration-s 30 --countdown-s 5 --out-dir docs/forensics/runtime-evidence/20260715-captivation-32-35-36/rerun
python3 scripts/regression-harness/device_captivation_leg.py --repo /private/tmp/k1-captivation-rerun-f2257ef --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_im73d --expected-git f2257ef --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --expected-track-sha256 174025b5ff4d326675cfb3b31b820e8448242d1b51d1a3b00e236e66373cc61a --mode 35 --duration-s 30 --countdown-s 5 --out-dir docs/forensics/runtime-evidence/20260715-captivation-32-35-36/rerun
python3 scripts/regression-harness/device_captivation_leg.py --repo /private/tmp/k1-captivation-rerun-f2257ef --port /dev/cu.usbmodem112401 --expected-chip-id B489A500 --expected-build-env k1_bench_im73d --expected-git f2257ef --track /Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3 --expected-track-sha256 174025b5ff4d326675cfb3b31b820e8448242d1b51d1a3b00e236e66373cc61a --mode 36 --duration-s 30 --countdown-s 5 --out-dir docs/forensics/runtime-evidence/20260715-captivation-32-35-36/rerun
```

## Evidence

[FACT] Raw build, upload, serial, and per-leg JSON evidence is stored under
[`../forensics/runtime-evidence/20260715-captivation-32-35-36/`](../forensics/runtime-evidence/20260715-captivation-32-35-36/README.md).
