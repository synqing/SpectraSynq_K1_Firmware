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

**Canon:** `docs/canon/SESSION_CANON_2026-08-13_colour_forensics_config_poison.md` (HF-41..49)
· `docs/canon/SESSION_CANON_2026-08-14_colour_fix_twitch_instrumentation.md` (HF-50..62)
**Verdict:** `docs/forensics/colour-nuance-regression-verdict-2026-08-13.md`
**Lane ledger:** `docs/forensics/colour-fix-lane-2026-08-13.md` · Promotion:
`docs/forensics/colour-fix-promotion-plan-2026-08-13.md`

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
- The RANGE=1 writer is IDENTIFIED (2026-08-13): the Aug-9 full71 harness stimulus
  (`1.37` → truncated 1 → persisted; NO restore step; no load-time clamp exists) —
  `docs/forensics/chromagram-range-poison-writer-2026-08-13.md`. Guard: any control-writing
  harness MUST `:dump`-snapshot before and restore+verify after.

## The second five hard rules (HF-50..62, paid for 2026-08-13/14)

6. **Gate every colour fix on the FULL perceptual axis set** — coverage · temporal
   stability (hue velocity) · silence rest · music coupling · brightness dynamics.
   Optimising one axis regressed another twice in one night (HF-50). Windowed
   histograms cannot see twitch.
7. **Firmware identity is FOUR-way**: bin × config blob × knob store × cal profile
   file. Boot restores CHROMA/MOOD from the knob store and SSL from the profile
   file OVER the blob — re-apply and re-verify measurement config per leg after any
   reboot; full-dump diff vs era, never remembered knobs. (HF-58/59)
8. **Assert the mode NAME and the palette PROPERTY, never the number/annotation** —
   `get_mode_name` per leg; live palette authority via the HUEAUD `pal=/pmode=/hd0=`
   fields (boot palette lock is overridden by show-state restore; oob index clamps
   to 0). (HF-54/60)
9. **A value-fingerprint match is not provenance** — conviction needs the generating
   mechanism (file:line) PLUS a live single-variable kill on the device. Live kills
   (`:edge_enabled=off`-class) and dose-response curves are the sharpest attribution
   instruments; use them before code archaeology. (HF-55, methods §3)
10. **Flash verification = script EXIT CODE + NEW epoch in the post-flash identity.**
    Never grep-filter a gated script in a `&&` pipeline (the before-flash identity
    line will match). After merging SSA work, grep the gated symbols in YOUR tree —
    merge the NAMED branch from the return contract, not the worktree default.
    (HF-56/57)

Drive-design corollaries: scale-blind (equalised) drives need an explicit structural
rest mechanism (ring spikiness — never a bare constant, never only a calibration-
dependent gate flag) (HF-51/52/53); per-channel multiplicative/nonlinear ops preserve
pure hues and destroy mixed ones — gold dies first, blue survives (methods §3.6);
before any cal, pre-check the mic's raw int16 floor — raw-quiet + processed-loud =
processing artefact, not acoustics (HF-61/62).

## Fix-lane status (2026-08-14)

Writer found · five colour layers fixed and measured · consolidated candidate
`k1_bench_im69d_colourfix` at 3/4 authored deployment in product config · twitch
decomposed, colour-side fixed (sweep rest v3 structure detector PROVEN: silence
0.00000/s, music alive). **OPEN: HF-61 cal self-lock (stale DC → phantom ~4k
baseline → visual response still wrong) — implement cal partial-commit, two
Captain-gated cal passes, then full-axis legs → promotion gates → the ONE golden
side-by-side.** Bench port drifted to `cu.usbmodem12401` (env pins 12201; use
`--upload-port`); SSL manually 6000 pending the DC fix.
