# Colour-job parity evidence — identities

Promoted 2026-08-27 from `_scratch/look-parity-rtrace-20260826/` byte-for-byte
(six hex dumps, `MEASURED.json`, `VERDICT.md`, capture/scorer scripts).
This file and `SHA256SUMS` are the tracked identity wrapper.

## Verdict block (do not inflate)

```text
COLOUR_JOB_PARITY = PASS_JOB_ONLY
WS2816_TRUE16     = PASS_TRUE16
PHOTON_PARITY     = NOT_CLAIMED
VISUAL_INSPECTION = NOT_USED_AS_EVIDENCE
TUNGSTEN_GREY     = NOT_RUN
```

Host pytest `tests/test_look_colour_job_parity.py` scores these dumps via
`tests/look_parity_rtrace.py` (copy of `score_parity.py`) and
`scripts/regression-harness/score_rtrace_occupancy.py`. Ceiling is JOB_ONLY.

## Devices

| Role | Chip ID | USB serial | Product env | Probe env |
|---|---|---|---|---|
| Main RPL | `9087A500` | `B4:3A:45:A5:87:90` | `k1_main_rpl_im69d` | `k1_main_rpl_rtrace_probe` |
| 150-LED bench | `B489A500` | `B4:3A:45:A5:89:B4` | `k1_bench_im69d_led150` | `k1_bench_im69d_led150_rtrace` |

Port names on the capture night (`/dev/tty.usbmodem1101` / `1401`) are **not**
identity. Chip ID + USB serial are.

## Probe / restore provenance (2026-08-26)

Both probe flashes and both product restores were rebuilt from the dirty
working tree at `9b48ce5f` (`feat/k1-usb-audio-input`).

| Device | Probe env | Product restore | Provenance class |
|---|---|---|---|
| 9087A500 | `k1_main_rpl_rtrace_probe` | `k1_main_rpl_im69d` | **dirty rebuild**, not archived `b625e89a` |
| B489A500 | `k1_bench_im69d_led150_rtrace` | `k1_bench_im69d_led150` | dirty rebuild; eight-print roster intact |

Canonical archived Main-RPL product (not installed after this cycle):

- commit `b625e89a`
- epoch `1787591762`
- factory SHA-256 `973084b464c8a22cab9b1db434a7e385a95c6b1755dc8946ac5af01633a69ce3`

Preferred end state after the next Main-RPL cycle: exact `b625e89a` **or** a
newer image from a clean committed SHA. Record whichever is actually installed.

## Stim and taps

- Stim: `:rtrace_arm=10,1,stim` — HSV hue 0→1, sat=1.0, val=0.55. No music.
- RPL tap: `rgb16hex` packed WS2816 (post-look, pre hardware-gamma). TRUE16.
- Bench tap: `rgb8hex` post-look post-`apply_gamma8`.

Tungsten grey is **NOT_RUN**: this stim has no grey inputs. Colour Lab
`paint=card` is the measurement surface that closes that gate.

## Scorer / test source hashes (at promote)

Computed from the working tree that first scored the promoted pack:

```text
tests/look_parity_rtrace.py           SHA-256 2bd8785a600389cc700291b2ad4e684e2d7f3699fd30f95be316e348da5de558
tests/test_look_colour_job_parity.py  SHA-256 70a9135ae4d32e9d995ba42633bed5ba94dc96501bf24ec1a706c711cc63507f
git hash-object look_parity_rtrace.py e0fe5d47e6414716574fb95e6905c8351c1552f0
git hash-object test_look_colour_job_parity.py e18c1024af138e0472613f508f3e49d2d145d2d8
working-tree HEAD                     9b48ce5fa00d2bde50e83edb952864db5f5a8e85
```

`score_parity.py` in this directory is byte-identical to
`tests/look_parity_rtrace.py` (same SHA-256 `2bd8785a…`).
