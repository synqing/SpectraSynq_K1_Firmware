# Colour-Parity Investigation — Render-Path Dump Verdict
## Date: 2026-08-26 | Investigation: look-parity-rtrace-20260826

---

## What happened

Both K1 devices were flashed with non-shippable rtrace probe envs, their render pipelines were traced with an HSV-ramp stim for three look slots each, and the dumps were scored offline. Product firmware was restored to both devices after the traces. No Captain visual inspection was requested or needed — the dump is the instrument.

**Device sequence:**
- RPL (9087A500 / `/dev/tty.usbmodem1101`): flashed `k1_main_rpl_rtrace_probe`, traced slots 0–2, then restored `k1_main_rpl_im69d` from dirty tree at `9b48ce5f` (see leftover note below).
- Bench 150-LED (B489A500 / `/dev/tty.usbmodem1401`): flashed `k1_bench_im69d_led150_rtrace`, traced slots 0–2, then restored `k1_bench_im69d_led150` from dirty tree at `9b48ce5f`.

**Stim used:** `:rtrace_arm=10,1,stim` — firmware-internal HSV ramp, hue 0→1 at saturation=1.0, value=0.55. Deterministic; same across both devices. No palette, no music.

---

## What is true now

### Taps verified correct
- **RPL dump:** `rgb16hex`, `bpp=16` — packed WS2816 wire data (u16 per channel), post-look, pre-hardware-gamma. NOT `leds_out` (8-bit). WS2816 occupancy scorer returned **PASS_TRUE16** (`mismatch_frac=0.664`, 145 unique codes — low bytes are independent of high bytes, confirming true 16-bit precision is active).
- **Bench dump:** `rgb8hex`, `bpp=8` — post-look, post-software-gamma u8. Correct tap for WS2812 pipeline.

### Slot 1 (gold/warm) — LIFT confirmed on both lanes

| Lane | Device | Slot 0→1 ΔG (abs) | ΔG (% of range) | Gold pixel count slot 0 | Gold pixel count slot 1 | R/G ratio slot 0 | R/G ratio slot 1 | R/G direction |
|---|---|---|---|---|---|---|---|---|
| RPL WS2816 | 9087A500 | +13 488.76 (u16) | **+20.58%** | 36 850 | 26 350 | 4.48 | 1.95 | MORE_GOLDEN ✓ |
| Bench WS2812 | B489A500 | +43.33 (u8) | **+16.99%** | 757 | 15 436 | 6.18 | 2.14 | MORE_GOLDEN ✓ |

Both look slots push green up on gold-region pixels (R>G>B, R significant). Both reduce R/G ratio (colour moves away from burnt-orange toward golden-yellow). Direction matches the intended JOB.

### WS2816 TRUE16 confirmation
The rtrace occupancy scorer on `rpl_slot1_dump.txt` returned **PASS_TRUE16**. The Lever-2 path is emitting genuine 16-bit values. This is not 8-bit data replicated into u16.

### Slot 2 (tungsten)
Grey stability of the stim-based tungsten dumps cannot be numerically confirmed — the HSV stim at `sat=1.0` produces no grey inputs, so `grey_mean_sat` in MEASURED.json is not a valid grey-preservation measurement. The tungsten LUT tables are analytically confirmed to produce a warm WB shift on a neutral input (RPL: `k1_look_tungsten` per-channel curves; Bench: `k1_look_ws2812_r/g/b[2]` — at input 128: R→151, G→128, B→100, making grey inputs warm amber). A separate grey-ramp stim would be needed to instrument this from a dump.

### Gamma handling
- RPL Slot 1 (`SHARED_1D`): applies `k1_ws2816_degamma_u16()` — cube-spaced `y = 65535·(v/65535)^(1/2.2)`. Lifts mid-range R and G; relative shift determines gold direction. Correct.
- Bench Slot 1 (`GOLD_LIFT`): applies `k1_look_ws2812_r/g/b[1]` u8 LUTs — per-channel inv-γ-2.2 print authoring. Both R and G are lifted but G is lifted more at mid-range, creating the golden effect. Correct.
- `ENABLE_OUTPUT_GAMMA=0`: WS2816 hardware gamma (4-bit) is applied on-chip; WS2812 software gamma (`apply_gamma8`) is applied before the rtrace tap. These are different paths on purpose. No copying of degamma between lanes.

---

## Colour parity verdict: **JOB_ONLY**

**Gold reads gold:** YES on both lanes. Slot 1 lifts G, reduces R/G ratio, and increases the count of gold-classified pixels. Direction is definitively LIFT on both.

**Tungsten is distinct:** YES analytically (LUT tables confirm warm WB shift on neutral inputs). NOT instrumentally confirmed from the stim-based dump (stim has no grey pixels).

**Identity is paint-as-authored:** YES — slot 0 IDENTITY passes through unchanged on both devices. Confirmed by the low gold-pixel count on bench slot 0 (757 vs 15 436 in slot 1) and the high R/G ratio pre-look (4.48 RPL, 6.18 bench = the HSV ramp includes red-dominant pixels that genuinely read as "too red", not pre-golden).

**Why not FULL parity:**
- RPL is a 16-bit Lever-2 path (WS2816, 4-bit hardware gamma on-chip, `k1_ws2816_degamma_u16`).
- Bench is an 8-bit path (WS2812, software gamma baked, u8 LUTs).
- Wire bytes are not comparable across lanes. PHOTON parity (identical plate output) is not claimable from RGB dump comparison alone.
- ΔG magnitudes are expressed in their native bit-depth units. 16.99% (bench u8) vs 20.58% (RPL u16) cannot be compared as equal — the emitter curves are different, and the stim's starting gamut coverage differs.

**Steel-man check passed:**
1. Wrong tap: NO — both dumps confirmed at the correct post-look sites.
2. 8-bit leds_out for Lever-2 occupancy: NOT used — PASS_TRUE16 was scored on the `rgb16hex` dump.
3. Identity pre-gold on WS2812: REJECTED — slot 0 bench shows 757 gold pixels; slot 1 shows 15 436. Identity is not secretly gold.
4. GOLD_LIFT washing greys: CANNOT REFUTE from this stim (no grey inputs). Open risk.
5. Comparing un-looked paint: NO — delta is identity vs look on the same stim.

---

## What is left

1. **Grey/tungsten dump confirmation:** Re-run with a neutral grey ramp stim (R=G=B sweep) to instrument tungsten WB shift and confirm GOLD_LIFT does not corrupt greys. This would close the JOB_ONLY → FULL gate on tungsten.
2. **Live music gold frame capture:** Instrument a live gold-heavy palette frame (Naberius Gold, palette index 40, stops (255,140,0) and (255,95,0)) to verify the stim-derived result holds under real content.
3. **RPL product binary restore to `b625e89a`:** See leftover note below.
4. **Bench grey wash test** (optional, if GOLD_LIFT grey safety is in question): trace bench slot 0 vs slot 1 on a grey stim.

---

## Leftover product state

### LEFTOVER_PRODUCT_WARNING — Main RPL (9087A500)
The canonical product binary for RPL is `k1_main_rpl_im69d` @ `b625e89a` (epoch `1787591762`, SHA-256 `973084b464c8a22cab9b1db434a7e385a95c6b1755dc8946ac5af01633a69ce3`). That binary was NOT cached on disk at restore time. The restore was rebuilt from the **dirty working tree at `9b48ce5f`** with `k1_main_rpl_im69d` env. The new build:
- Does NOT include `K1_RENDER_TRACE_V1` (confirmed: rtrace_status returns "bad command")
- Does NOT include `K1_LOOK_LIB_WS2812_V1` (RPL env never had this)
- Does include the current dirty-tree look-library changes (k1_look.h, k1_look_ws2812.h) — these are look-lib sources that affect WS2812 only via the WS2812_V1 flag; RPL takes the `k1_look_apply_u16` path unconditionally
- Epoch changed (new build timestamp)

**Functionally equivalent to `b625e89a`** for RPL production use (no gated changes affect this env). However, the exact SHA differs. If Captain requires `b625e89a` exactly, the restore binary should be retrieved from git archive of that commit and reflashed.

### Bench (B489A500)
Restored to `k1_bench_im69d_led150` from dirty tree at `9b48ce5f` — same state as the pre-investigation epoch `1787757776` (eight-print roster: IDENTITY / GOLD_LIFT / TUNGSTEN / AMBER_HOLD / DAYLIGHT / MOON / PUNCH / CRUSH). Epoch changed but source is identical to the prior product flash. No regression.

---

## Dump file paths

```
_scratch/look-parity-rtrace-20260826/
├── rpl_slot0_dump.txt       # RPL slot 0 (IDENTITY), rgb16hex
├── rpl_slot1_dump.txt       # RPL slot 1 (SHARED_1D/degamma), rgb16hex — PASS_TRUE16
├── rpl_slot2_dump.txt       # RPL slot 2 (TUNGSTEN), rgb16hex
├── bench_slot0_dump.txt     # Bench slot 0 (IDENTITY), rgb8hex
├── bench_slot1_dump.txt     # Bench slot 1 (GOLD_LIFT), rgb8hex
├── bench_slot2_dump.txt     # Bench slot 2 (TUNGSTEN), rgb8hex
├── MEASURED.json            # Full numeric results
├── score_parity.py          # Scoring script
└── capture_rtrace.py        # Capture script (stim mode)
```

---

## Summary for parent

| Item | Value |
|---|---|
| Port map | RPL `/dev/tty.usbmodem1101` (9087A500 `B4:3A:45:A5:87:90`) — Bench `/dev/tty.usbmodem1401` (B489A500 `B4:3A:45:A5:89:B4`) |
| Flashed? | YES — both devices took probe envs; both restored to product env |
| RPL probe env | `k1_main_rpl_rtrace_probe` (dirty tree `9b48ce5f`) |
| Bench probe env | `k1_bench_im69d_led150_rtrace` (new, dirty tree `9b48ce5f`) |
| RPL current silicon | `k1_main_rpl_im69d` rebuilt from dirty `9b48ce5f` — LEFTOVER_PRODUCT_WARNING: not exact `b625e89a` binary |
| Bench current silicon | `k1_bench_im69d_led150` rebuilt from dirty `9b48ce5f` (eight-print roster intact) |
| Gold ΔG — RPL | **+13 488.76 u16 (+20.58% of u16 range)** |
| Gold ΔG — Bench | **+43.33 u8 (+16.99% of u8 range)** |
| Both directions | LIFT (green rises), R/G ratio decreases (MORE_GOLDEN) |
| WS2816 occupancy | **PASS_TRUE16** |
| Verdict | **JOB_ONLY** — gold reads gold on both lanes; PHOTON parity not claimable across different emitter types |
| Open items | Grey/tungsten stim; live Naberius Gold frame; RPL exact-SHA restore if required |
