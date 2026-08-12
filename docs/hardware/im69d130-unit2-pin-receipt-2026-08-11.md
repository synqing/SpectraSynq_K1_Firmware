---
abstract: "Device-proof pin receipt for K1 Bench Unit 2 (0C54FC00): PDM CLK=39 / DATA=38 with RIGHT slot selection is FUNCTIONAL, and the unit has since been RETARGETED off its IM73D-compiled misflash onto env k1_unit2_im69d_right @ git 1249286. Carries the pre-retarget tempo-lock proof, the post-retarget music/quiet-room verification (quiet-room darkness 70.8%, NOT ~100%), and the explicit statement that the dual-capsule topology remains UNPROVEN — only one capsule path is evidenced. Satisfies the CAPTAIN_PIN_AUTH precondition in device-build-registry.md §1."
---

# Unit 2 — PDM Pin Receipt (CLK 39 / DIN 38, RIGHT slot)

**Device:** K1 Bench Unit 2
**Chip ID:** `0C54FC00`
**ESP MAC / USB serial:** `AC:A7:04:FC:54:0C`
**Port at capture:** `/dev/cu.usbmodem1101`
**Date:** 2026-08-11 (AWST)
**Authorisation:** `CAPTAIN_PIN_AUTH=GO` and `CAPTAIN_FLASH_AUTH=GO` — both granted 2026-08-11.

## Why this receipt exists

The device registry held Unit 2's PDM CLK/DATA assignment as **TBD**, with the explicit
instruction: *"do not treat DIN=38/CLK=39 or IM73D inheritance as authoritative."* That gate
required a pin receipt before the assignment could be trusted.

This receipt supplies the missing evidence, and records the retarget that followed it.

## Claim

**PDM CLK = GPIO 39, DIN = GPIO 38, with the PDM slot mask set to RIGHT, produces a
functional audio front-end on Unit 2's dual IM69D130 microphone.**

Firmware truth for that assignment lives under `K1_UNIT2_IM69D_V1` in
`SPECTRASYNQ_K1_FIRMWARE/system/constants.h`; the env that sets it is
`[env:k1_unit2_im69d_right]` in `platformio.ini` (extends `k1_bench_im69d`,
adds `-DK1_UNIT2_IM69D_V1 -DK1_MIC_IM69D_SLOT_RIGHT`).

**SELECT is static hardware truth and is never driven by firmware** in either IM69D profile.
GPIO12 remains an escape-hatch pin only.

## Part 1 — Pre-retarget evidence (pin/slot functionality), 2026-08-11

Captured by passive serial read (DTR asserted, **zero bytes written to the port**), with the
device in its as-found state — i.e. still running the **IM73D-compiled misflash binary**.
Stimulus played through the host's default output (Bose Mini II SoundLink) via `afplay`.
Paired control: quiet → stimulus → quiet.

### Primary evidence — tempo lock on a known-tempo track

Stimulus: `control_127bpm_click_44k1.wav` — a **127 BPM** control fixture.

| Measure | Quiet | During stimulus |
|---|---|---|
| `silence` | 1 (100% of frames) | **0 (0% of frames)** |
| `silent_scale` | 0.00 | **1.00** |
| `bpm` | 68 (unlocked drift) | **126.06 mean, 128 max** |
| `conf` | 0.00 | **0.88 mean, 0.92 max** |
| `lock` | 0% of frames | **100% of frames** |

The device recovered the stimulus tempo to **within 1 BPM of ground truth** and held phase
lock across the entire capture. A tempo tracker cannot lock to a signal it is not receiving;
this is positive proof of a functioning acoustic path through the stated pins and slot.

### Secondary evidence — proportional response to real music

Stimulus: full-mix commercial track.

| Measure | Quiet | Music | Recovery |
|---|---|---|---|
| `silence` | 1.00 | **0.10** | 1.00 |
| `max_raw` (mean) | 50 | **2308** (max 5364) | 50 |
| `raw_i16_rms` (mean) | 10.9 | **119.0** | 11.7 |

Clean return to baseline on the recovery leg confirms the response tracked the stimulus rather
than drift.

### Independent acoustic witness

To exclude a starved playback path as an explanation, the room was recorded simultaneously with
the host's built-in microphone (`ffmpeg` / `avfoundation`, `volumedetect`):

| | mean | max |
|---|---|---|
| Quiet room | −61.8 dB | −41.7 dB |
| Music playing | **−35.1 dB** | **−19.1 dB** |

**+26.7 dB**, confirming the stimulus was genuinely present in the room and not an artefact of
the capture method.

### Slot discrimination

The reciprocal slot (LEFT) was previously measured at `max_raw` ≈ 45–67 against RIGHT's
700–1216 on the same hardware. RIGHT is the responsive capsule path.

## Part 2 — Retarget and post-retarget verification, 2026-08-11

With `CAPTAIN_PIN_AUTH` and `CAPTAIN_FLASH_AUTH` granted, the misflash was retargeted.

### Deployed firmware

| | |
|---|---|
| env | `k1_unit2_im69d_right` |
| git | `1249286` |
| silicon epoch | `1786444727` |
| build | RAM **33.6%** (110184 B), Flash **10.6%** (696530 B) |
| upload guard | *"verified as K1 Bench Unit 2 (AC:A7:04:FC:54:0C, chip 0C54FC00, bench IM69D130 PDM CLK=39/DATA=38, RIGHT slot; dual 206-px WS2812B on LED 4/5)"* |
| mic | dual IM69D130, PDM **CLK=39 / DATA=38**, **RIGHT** slot, input gain **G=8** |
| LEDs | 206 primary / 206 secondary, render canvas 160 |
| calibration | **inherited, not re-fired** — `SSL=103 DC=-117 cal_source=persisted_profile cal_valid=1` |

**No `start_noise_cal` was fired at any point.** Calibration is Captain-verbal-gated; the
device is running its persisted profile.

### Music — volume 70 (the level that previously never woke the device)

| Measure | Value |
|---|---|
| `silence` | **0.0** — awake on every frame |
| `silent_scale` | **1.00** |
| `conf` | mean **0.66**, max **0.96** |
| `lock` | **50%** of frames |
| `max_raw` | mean **2190**, max **5051** |
| `pky` (peakiness) | mean **2.31**, max **2.67** |

### Quiet room — 60 s, room confirmed at −59.4 dB mean on an independent witness mic

| Measure | Value |
|---|---|
| `silence` held | **70.8%** of frames (was **7.4%** with peakiness alone) |
| `silent_scale` | mean **0.30** |
| `pky` cleared the 2.10 break | **10 / 65** frames |
| …of which also cleared the 500 level floor | **1 / 65** frames |

The AND condition (level **and** peakiness, `git 1249286`) rejected **9 of 10** false triggers
that peakiness alone would have admitted.

## Residual — state this honestly

**Quiet-room darkness is 70.8%, not ~100%.** The remaining non-silence is attributable to:

1. **Real room transients** — the independent witness mic recorded a max of **−33.9 dB**
   during the "quiet" window. Some of what the gate admitted was genuinely there.
2. **Tempo-flywheel persistence** after music stops.
3. **Silence hysteresis decay.**

**Recommended next step (NOT yet implemented):** add a dwell/persistence requirement — N
consecutive frames above **both** axes — to reject isolated transients.

## Scope and limitations — read before extending this receipt

This receipt certifies **pin and slot functionality, and the retarget that followed**. It does
**NOT** certify:

1. **Dual-capsule topology.** No measured complementary SELECT states, no shared-DATA
   contention proof, no per-capsule VDD/ground/clock continuity record. **Only one capsule
   path (RIGHT) is evidenced here.** Nothing in this document may be read as certifying the
   full dual-mic topology.
2. **Quiet-room silence at product quality.** 70.8% is a large improvement, not a pass. See
   *Residual* above.
3. **Colour / lightshow perceptual quality.** No Captain eyes-on is recorded here.

**Resolved since the first draft of this receipt:** the mic-identity defect. The binary under
test in Part 1 was compiled with IM73D inheritance while the physical mic is dual IM69D130
(documented misflash). Part 2 retargets the unit onto `k1_unit2_im69d_right`, so the
mic-specific gain and calibration corridor now match the physical hardware.

## Method integrity

- Serial access was **read-only throughout capture**; no calibration, erase, reset, or write
  command was issued during any capture window.
- No `start_noise_cal` was fired. Calibration state is inherited (`SSL=103`, `DC=-117`,
  `cal_source=persisted_profile`, `cal_valid=1`).
- Device identity was confirmed from the **firmware's own report** (`CHIP ID: 0C54FC00`) and
  from the upload guard's identity line, not inferred from the port number — port assignments
  are known to drift on this bench.
- The flash was performed under an explicit `CAPTAIN_FLASH_AUTH=GO`, which lifted the standing
  flash freeze on this unit.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-11 | agent:claude-code | Created. Files the pin receipt required by `device-build-registry.md` §1 from live device evidence captured 2026-08-11, and adds Part 2 recording the retarget onto `k1_unit2_im69d_right` @ `1249286` with its music / quiet-room verification, the 70.8% residual, and the explicit UNPROVEN status of the dual-capsule topology. |
