---
abstract: "Colour-nuance regression forensic VERDICT (2026-08-13, Captain-driven live A/B on bench B489A500). TWO defects proven: (1) CONFIG POISONING — CHROMAGRAM_RANGE 60→1 in persisted config collapses palette deployment to a single colour on ANY firmware (era config replay restored richness, Captain-confirmed); (2) FIRMWARE REGRESSION on main — with identical era config, the Aug-8 resident build renders rich gold where main renders WHITE (modes 18/32) and a single colour (mode 3), so main's shared colour path regressed vs the Aug 6-7 dirty-tree work. Golden oracle = the Aug-8 flash readback (04215afb…) + the Aug-5 20:15 preflight config. Bench left in the Captain-approved state. Fix lane: hue-coverage metric harness with the golden bin as oracle — no more eyes-on roulette."
---

# Colour-nuance regression — forensic verdict (2026-08-13)

**Method:** 5 parallel SSA excavations (`_scratch/colour_forensics_20260813/SSA1..5`) + prior
audit `_scratch/colour_corruption_audit_20260810/` + live Captain-eyes A/B ladder on bench
`B489A500` (esptool writes under explicit Captain GO).

## The A/B ladder (all with music, config controlled from step 4)

| Build on bench | Config | Captain verdict |
|---|---|---|
| recovered Aug-11 snapshot `b09d032f` | today's | single colour |
| Aug-5 pre-gate `9013ed90` | era-ish | single colour |
| **Aug-8 readback `04215afb…` (resident bin of the rich week)** | today's | richer, but gold→white |
| **Aug-8 readback** | **era config (Aug-5 20:15 preflight)** | **"yes yes yes — much closer to what I remember"** |
| current main `a66b0588` | era config | **gold renders WHITE** (mode 32); mode 3 = single colour |

## Defect 1 — CONFIG POISONING (proven, fixed live)

`CONFIG.CHROMAGRAM_RANGE` was **60** in the rich era (Aug-5 20:15 preflight,
`_scratch/im69d_vs_main_20260805/20260805T201538_im69d_vs_sph_ab/preflight_bench_im69d.log`)
and is **1** in today's persisted config. Range 1 folds the note range into one bucket →
one colour, on any firmware. Era values restored live: range 60, SENSITIVITY 2.40,
SWEET_SPOT_MIN 253, CHROMA 0.05, MOOD 0.05. **Open sub-question: WHAT wrote 1** —
candidates: Tab5/Deck16 control write, a default reset, or a load-time clamp added in a
commit (if a clamp, the poison re-applies on reboot — must be checked before any fix ships).

## Defect 2 — FIRMWARE REGRESSION on main (proven, unfixed)

With identical era config: Aug-8 bin = rich gold; main = white (18/32) / single colour (3).
So the regression is in main's **shared colour path**, not only the mode-18/32 fallback.
Ranked suspects (SSA1/SSA3/SSA5, static): `b643b8d6` mono-hue knob fallback (18/32 white),
the joint-gate cluster thinning chroma (fallback trigger), `97276b3a` boot palette lock,
the held-centroid attractor (+`K1_PALETTE_ENERGY_EXCURSION_V1` implemented-but-off),
`024591dd` Nyquist bin remap, and the `isfinite`/`-fno-finite-math-only` NaN-hue correction.
Note: the richness was **created by the Aug 6-7 VJ dirty-tree work** (pre-gate Aug-5 is also
single-colour) — the golden bin is the only complete artefact of it, and its exact source is
NOT reconstructible (`db300db` + unrecorded dirty state; the Aug-11 snapshot already lost it).

## Golden oracle (preserve these two artefacts)

- **Bin:** `_scratch/deck16_backend_b1b2_20260808/flash_readback_k1.bin`
  (sha256 `04215afb279af9f63b833a2304d2fda8975db37f9d1cb0cc5d6a2ada814124ad`, app @0x10000)
- **Config:** the Aug-5 20:15 preflight dump (path above)

## Bench state at close (registry-relevant)

`B489A500` runs the **golden readback** (`git=db300db epoch=1786214500 env=k1_bench_im69d_ble`,
non-main, Captain-approved eyes-on) with the era config INCLUDING `SWEET_SPOT_MIN_LEVEL=253`
— **the measured-2026-08-12 cal value 187 was overwritten**; restore 187 (or recal) before any
current-main measurement work on this unit.

## Fix lane (next session — no Captain eyes until the metric passes)

1. Build a **hue-coverage metric** (distinct-hue histogram / palette-coverage entropy per
   minute) on the VPAB/matrix-audit machinery; run it on the golden bin = the oracle number.
2. Check the CHROMAGRAM_RANGE load path on main for a clamp; find and guard the writer of 1.
3. Bisect main's colour path against the metric (fallback bound, gate-thinning, attractor,
   `ENERGY_EXCURSION` tuning per the existing palette-coverage gate).
4. Captain sees exactly ONE eyes-on: golden vs fixed-main, side by side.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Created at excavation close — Captain-confirmed A/B ladder, two proven defects, golden oracle, fix-lane contract. |
