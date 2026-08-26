# Colour Lab and tungsten grey — render-path dump verdict

Date: 2026-08-27. Instrument: rtrace dumps. Captain did not look at the plate.

## What happened

Both registered K1s ran a Colour Lab `paint=card` through the real look path.
The card is seventeen count-independent regions: greys
0, 1, 16, 32, 64, 96, 128, 160, 192, 224, 240, 254, 255, then red, green,
blue, and Naberius gold (255, 140, 0). Dumps were scored offline.

Main RPL (chip `9087A500`, USB `B4:3A:45:A5:87:90`) used the rtrace probe at
`f2014c29`. Dual-channel paint at the conservative solid grey (140) tripped
the Core 1 watchdog. Primary-only full-scale card held. All RPL measurement
dumps therefore used `paint_target=primary`. After the dumps, product
`k1_main_rpl_im69d` @ clean `acaecaa8` was restored. That image scales
both-target paint by 0.30 so a default `paint=card` no longer resets the unit.
Primary-target measurement stays full-scale.

The 150-LED bench (chip `B489A500`, USB `B4:3A:45:A5:89:B4`) took the rtrace
probe, then product `k1_bench_im69d_led150` @ `f2014c29`. Full card on both
channels held. No runtime slot-15 claim on this device.

## What is true now

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

Identity card on Main RPL is `k * 257` (grey 128 → 32895, 32895, 32895).
Tungsten (slot 2) mid-grey is 38816, 32895, 25658 — red up 1.18, blue down
0.78, warm. Red clips from input 224. Terminal blue jump 254→255 is 14618
(`0xC6E5` → `0xFFFF`). Those table traits are recorded; they did not block
the measurement.

Slot 15 on Main RPL used `tune_gain=1.00,0.70,0.40` and `tune_gamma=1.00`.
Mid-grey after the look is 32895, 23026, 13158 (exact 1.0 / 0.7 / 0.4).
`tune_save`, then a real esptool hard reset, then boot: look stayed 15,
tune RAM returned to identity, the `.klut` still applied. Reload dump delta
versus the pre-reboot slot-15 dump is 0.

Bench slot 0 card is grey in 8-bit (`rgb8hex`). Slot 1 is GOLD_LIFT. Paint
off is not a card.

## Power (measured, not assumed)

| Condition on 9087 dual WS2816 160+160 | Result |
|---|---|
| `paint=solid` both 8 / 40 / 80 | holds ≥4 s |
| `paint=solid` both 140 | TG1WDT then reset loop |
| `paint=card` primary (full scale) | holds; used for all RPL dumps |
| `paint=card` both on product `acaecaa8` (0.30 scale) | holds ≥5 s |

## Silicon after this cycle

| Device | Env | Git | Provenance | Firmware SHA-256 |
|---|---|---|---|---|
| 9087A500 | `k1_main_rpl_im69d` | `acaecaa8` epoch `1787773671` | clean commit | `4bd481f8356055ff1ab728b93431f226d5361ac9492f397a25cb8965a383fd72` |
| B489A500 | `k1_bench_im69d_led150` | `f2014c29` epoch `1787771217` | clean commit | `6ebbb7536485b5f49c1ce1d764341b80f328b9d4a2b4349540271f80a11ed17b` |

Calibration inherited on both (`cal_valid=1`). No `start_noise_cal`.
Rtrace commands are rejected on both product images. Main RPL is parked on
look 0.

## What is left

1. Photon / plate parity is still not claimed — the emitters differ.
2. WS2812 runtime slot 15 is a later RAM-slot lane.
3. Archived `b625e89a` is no longer the installed Main RPL image; the
   installed product is the newer clean SHA `acaecaa8`.
