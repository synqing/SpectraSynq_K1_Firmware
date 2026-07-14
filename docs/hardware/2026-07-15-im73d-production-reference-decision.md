# IM73D Production and Reference Hardware Authority

## Decision

[FACT] Captain designated the IM73D as the K1 reference and production
microphone hardware on 2026-07-15.

[FACT] Any earlier document that describes the SPH0645 as the K1 reference,
canonical, default, or production microphone is superseded on that point.
Historical SPH deployment records remain valid only as records of what was
physically installed or flashed at that time.

## Canonical Environments

| Role | Environment | LED GPIO | Microphone GPIO | Authority |
|---|---|---|---|---|
| Shipping production | `k1_prod_im73d` | 6/7 | CLK 13, DIN 12, LR 14 LOW | Canonical |
| Bench reference | `k1_bench_im73d` | 4/5 | CLK 13, DIN 12, LR 14 LOW | Canonical |
| Bench novelty probe | `k1_bench_ap_frontend_probe` | 4/5 | CLK 13, DIN 12, LR 14 LOW | Non-shippable measurement derivative |
| Legacy compatibility base | `k1_hardware` | 6/7 | SPH0645 I2S | Non-canonical |
| Legacy bench base | `k1_bench_reference` | 4/5 | SPH0645 I2S | Non-canonical |

[FACT] `platformio.ini` defaults to `k1_prod_im73d`. The production commit gate
also builds `k1_prod_im73d`.

[FACT] Environment names do not prove physical hardware identity. Upload and
capture operations must pass an explicit port and verify the expected chip ID
through the repository upload/session guards.

## Current Device State Boundary

[FACT] A device registry row may show an older K1 currently running an SPH build.
That is a deployed-state observation, not permission to treat SPH as the current
hardware reference.

[FACT] The six-track DEVICE audio-semantic corpus was captured through
`k1_bench_ap_frontend_probe`, which inherits `k1_bench_im73d` and defines
`K1_MIC_IM73D_PDM_V1`. Those captures are therefore reference-hardware evidence.

## Exact Verification

```bash
python3 -m pytest tests/test_dev_instrumentation_boundary.py tests/test_device_novelty_capture_gate.py tests/test_paired_novelty_source_replay.py -q
bash scripts/agent/pio-build.sh k1_prod_im73d
bash scripts/agent/pio-build.sh k1_bench_im73d
```

[FACT] Paired clean/device-novelty evidence and its exact replay command are in
[`../measurements/2026-07-15-im73d-paired-novelty.md`](../measurements/2026-07-15-im73d-paired-novelty.md).
