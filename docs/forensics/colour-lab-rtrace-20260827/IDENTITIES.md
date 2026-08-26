# Colour Lab evidence — identities

Pack: `docs/forensics/colour-lab-rtrace-20260827/`.
Dump is the instrument. Ports are not identity.

## Verdict block

```text
COLOUR_JOB_PARITY      = PASS_JOB_ONLY
WS2816_TRUE16          = PASS_TRUE16
PHOTON_PARITY          = NOT_CLAIMED
TUNGSTEN_GREY          = PASS
COLOUR_LAB_PAINT_RPL   = PASS
COLOUR_LAB_PAINT_BENCH = PASS
RUNTIME_SLOT15_RPL     = PASS
WS2812_RUNTIME_SLOT15  = NOT_IMPLEMENTED
VISUAL_INSPECTION      = NOT_USED_AS_EVIDENCE
```

## Devices

| Role | Chip ID | USB serial | Product env | Probe env |
|---|---|---|---|---|
| Main RPL | `9087A500` | `B4:3A:45:A5:87:90` | `k1_main_rpl_im69d` | `k1_main_rpl_rtrace_probe` |
| 150-LED bench | `B489A500` | `B4:3A:45:A5:89:B4` | `k1_bench_im69d_led150` | `k1_bench_im69d_led150_rtrace` |

## Probe cycle

| Device | Probe git | Probe epoch | Probe firmware SHA-256 |
|---|---|---|---|
| 9087A500 | `f2014c29` | `1787771446` | `7612b7c0f9d44733ac25702bdf273693f5e015f6a9c18b806908392fee94c3ec` |
| B489A500 | `f2014c29` | `k1_bench_im69d_led150_rtrace` | `1f3f60b825396d7839a1737511da1e5e72c0ad3f540ce1946c9795cd8befcc48` |

RPL dumps used `paint=card` + `paint_target=primary` (full-scale card).
Bench dumps used the card on both channels.

Slot 15 persistence used a real esptool `hard_reset`, not a USB gadget reset.
After reboot: `LOOK: slot=15 type=RGB_1D_256`, `TUNE:` RAM identity, type=2.

## Product restore

| Device | Env | Git | Epoch | Provenance | Firmware SHA-256 |
|---|---|---|---|---|---|
| 9087A500 | `k1_main_rpl_im69d` | `acaecaa8` | `1787773671` | **clean commit** | `4bd481f8356055ff1ab728b93431f226d5361ac9492f397a25cb8965a383fd72` |
| B489A500 | `k1_bench_im69d_led150` | `f2014c29` | `1787771217` | **clean commit** | `6ebbb7536485b5f49c1ce1d764341b80f328b9d4a2b4349540271f80a11ed17b` |

`:rtrace_*` rejected on both product images. Calibration inherited.
Main RPL parked on look 0 after restore.

## Stim and taps

- Stim: Colour Lab `paint=card`. No HSV rtrace stim.
- RPL tap: `rgb16hex`, 160 px, packed WS2816 post-look.
- Bench tap: `rgb8hex`, 150 px, post-gamma `leds_out`.
