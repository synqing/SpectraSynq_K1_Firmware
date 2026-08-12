---
name: k1-colour-truth
description: >-
  HARD-FAIL discipline from the 2026-08-13 colour-forensics session (HF-41..49).
  Use BEFORE any K1 colour/palette/vibrancy investigation, any "colours look
  wrong/washed/single-colour" report, any firmware A/B judged by eyes, any config
  knob change on a bench unit, or the colour fix lane. Encodes: config is half
  the firmware identity; diff live :dump vs era dumps FIRST; the golden oracle
  pair; one variable per Captain look; no cross-era config porting.
---

# K1 Colour Truth — load-bearing rules

**Canon:** `docs/canon/SESSION_CANON_2026-08-13_colour_forensics_config_poison.md`
**Verdict:** `docs/forensics/colour-nuance-regression-verdict-2026-08-13.md`

## The five hard rules

1. **A firmware identity is (bin sha × persisted config × calibration).** An A/B that pins
   only the binary is VOID. Byte-exact era firmware on today's NVS misled Captain three
   times in one night. (HF-41)
2. **Config-diff FIRST, code archaeology second.** On any colour/behaviour regression:
   read the live `:dump`, diff it against an era dump (`_scratch/*/preflight_*.log` files
   are full config snapshots). One field — `CHROMAGRAM_RANGE` 60→1 — impersonated a code
   regression and burned a five-agent excavation. (HF-42)
3. **Eyes-on PASS ⇒ take the state.** Whenever Captain approves anything visually:
   flash readback (`esptool read_flash 0x10000 <size>`) + full `:dump` + `wip/*` checkpoint
   of the tree. Approval without provenance evaporated once already (the Aug 6-7 richness
   died uncommitted within 3 days). (HF-43, HF-45)
4. **One pre-registered variable per Captain look — never a ladder.** Captain's eyes are a
   scarce instrument; prefer a numeric metric (hue-coverage/palette-entropy) with a single
   final eyes-on. "Firmware roulette" is a STOP phrase. (HF-44)
5. **No cross-era config porting.** A knob value is only valid with a matching-era receipt
   (sensitivity 0.87 was July/IM73D truth; the August/IM69D truth was 2.40). Same law as
   the P2.B floors rule, extended to ALL config. (HF-47)

## The golden oracle (colour reference state — Captain-approved 2026-08-13)

- **Bin:** `_scratch/deck16_backend_b1b2_20260808/flash_readback_k1.bin`
  sha256 `04215afb279af9f63b833a2304d2fda8975db37f9d1cb0cc5d6a2ada814124ad` → app @ `0x10000`
- **Config:** `_scratch/im69d_vs_main_20260805/20260805T201538_im69d_vs_sph_ab/preflight_bench_im69d.log`
  Key values: `CHROMAGRAM_RANGE=60` · `SENSITIVITY=2.40` · `SWEET_SPOT_MIN=253` ·
  `CHROMA=0.05` · `MOOD=0.05` · `PHOTONS=1.0` · mode 32.
- Replay recipe: flash bin (needs explicit Captain esptool GO), then
  `:chromagram_range=60 :sensitivity=2.40 :sweet_spot_min=253 :chroma=0.05 :mood=0.05 :set_mode=32`.

## Known truths (do not rediscover)

- Main (as of `a66b0588`) has a REAL colour-path regression vs the golden bin with identical
  config: gold→white on 18/32 (suspect `b643b8d6` knob fallback), single colour on mode 3.
- The collapse chain (AGC→flatness→sparseness→held-hue freeze) is documented at
  platformio.ini ~L185 since 2026-07-02; `K1_PALETTE_ENERGY_EXCURSION_V1` is the measured,
  parked coverage fix (ON in no env).
- `:stream_agc` is a dead toggle on current builds (no emitter); era binaries lack the
  incandescent commands — verify command + consumer exist ON THE FLASHED BUILD. (HF-48)
- On mid-experiment builds SSL is drive normaliser AND gate input — don't knob-tune hybrids;
  change era. (HF-49)
- Cursor's serial monitor auto-reconnects and steals/resets the port — `lsof
  /dev/tty.usbmodem*` before calling a device dead; coordinate the port with Captain. (HF-46)
- The RANGE=1 writer is UNIDENTIFIED (Tab5/Deck16 write or load-clamp) — find it before
  shipping any fix or it re-poisons.

## Fix-lane contract (defined, not started)

Hue-coverage metric on the matrix-audit machinery → golden bin sets the oracle number →
check RANGE clamp/writer on main → bisect main's colour path against the metric
(fallback bound · gate-thinning · held-centroid attractor · ENERGY_EXCURSION tuning) →
ONE final side-by-side eyes-on.
