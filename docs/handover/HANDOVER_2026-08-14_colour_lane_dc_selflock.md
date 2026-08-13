---
abstract: "Handover 2026-08-14 (session close). The colour fix lane is DONE at the colour layer (five layers fixed; candidate k1_bench_im69d_colourfix at 3/4 authored deployment in full product config; twitch colour-side fixed and ratcheted) but the plate still looks wrong because of ONE open root cause: HF-61 — the noise cal self-locks on a stale DC (phantom ~4k waveform baseline in silence drives every mode). NEXT MISSION step 1 = cal partial-commit fix, two Captain-gated cal passes, then full-axis verification. All lessons canonised as HF-50..62; mechanical ratchets live in CI. Read order, device truth, mission contract, and traps inside."
---

# Handover — 2026-08-14 session close → the DC/cal fix + full-axis verification

**Repo tip at close:** PRs #48–#55 merged; **PR #56** (twitch fixes + canon + ratchets) was
merging on a watcher at close — VERIFY ITS STATE FIRST (`gh pr view 56`); if unmerged, the
lane branch `lane/colour-fix-goldkiller` carries everything and CI green = merge it.

## Read in this order (short on purpose)

1. **This file** — state, mission, traps.
2. `docs/canon/SESSION_CANON_2026-08-14_colour_fix_twitch_instrumentation.md` — **HF-50..62**
   + the positive methods canon. Non-optional; every trap below is detailed there.
3. `docs/forensics/colour-fix-lane-2026-08-13.md` — the full execution ledger (every leg,
   every number, every SSA return).
4. `docs/forensics/colour-fix-promotion-plan-2026-08-13.md` — flag inventory + the 5
   promotion gates (audited).
5. Skill `k1-colour-truth` (auto-loads) — ten hard rules + drive corollaries + status.
6. Prior canon `SESSION_CANON_2026-08-13_colour_forensics_config_poison.md` (HF-41..49)
   only if archaeology is needed.

## DEVICE TRUTH at close — verify by identity guard before touching anything

| Device | Chip | Port | Running | ⚠ |
|---|---|---|---|---|
| **Bench K1v2** | `B489A500` | **`cu.usbmodem12401`** (DRIFTED — env pins 12201; always pass `--upload-port`) | `k1_bench_im69d_colourfix` @ lane tip (wake-v3 build; run `python3 scripts/regression-harness/k1_device_identity_guard.py --port ...` on arrival) | SSL manually **6000** in RAM (phantom-baseline units); **every reboot re-loads 57 from the cal profile file** — reassert per leg. Era knobs applied (RANGE=60/NOTE_OFFSET=12/SENS=2.40/CHROMA=0.05/MOOD=0.05). Edge mixer ON. |
| Unit 2 | `0C54FC00` | `cu.usbmodem1101` (advisory) | `k1_unit2_im69d_right @ 2904c9b9` | untouched this session |
| Main K1 | `F887A500` | drifts | untouched | not yours unless told |

**Golden reference state** (for the final eyes-on only): bin
`_scratch/deck16_backend_b1b2_20260808/flash_readback_k1.bin` (sha `04215afb…`) + era config
recipe — re-establishing it needs explicit **Captain esptool GO**.

## THE MISSION — in this exact order

1. **HF-61: cal partial-commit fix.** The noise cal measures DC correctly (≈−1523, clean
   3×) but its all-or-nothing rollback discards it because SSL — evaluated under the STALE
   DC (persisted 91) — reads ~4k and rejects. Phantom baseline → every mode animates noise
   → Captain sees "nothing changed". Implement: when `dc_valid=1 && ssl_valid=0`, COMMIT the
   measured DC, keep prior SSL, report `NOISE CAL PARTIAL` loudly (calibration/noise_cal.h
   quality/rollback path). Gated flag, bench env only, pytest+build gates, byte-inert
   production (3 stable sections `72417182/afa23c99/d383aa70`).
   **[HYPOTHESIS caveat]**: stale-DC is strongly evidenced, not proven — if a partial-commit
   cal does NOT collapse the phantom baseline, re-open the raw→waveform scaling chain
   (raw int16 rms 43 vs max_raw ~6000, ×140 unexplained; SENSITIVITY=2.40 accounts for ×2.4).
2. **Two cal passes under Captain's verbal silence gate** ("silence confirmed" = the gate;
   N then Y within 5 s on serial; typed start_noise_cal is disabled). Pre-check the mic's
   OWN floor first (raw_i16_rms on the AP line) — one confirmed window had music in it.
3. **Re-verify the twitch axes**: silence leg (sweep rate must be ~0, silence must LATCH
   now), then music leg (sweep alive, corr(mic peak, lit px) — was 0.02, expect real
   coupling once DC is right). Driver: `scripts/regression-harness/colour_baseline_capture.py`
   (asserts mode NAME? no — asserts number + palette; READ get_mode_name in the log, HF-54).
4. **Full-axis metric legs** (HF-50): coverage + temporal hue-velocity + silence rest +
   music coupling + brightness dynamics, modes 32 and GDFT, ≥2 palettes incl. a flagged
   dark-attractor one (promotion plan §3.3).
5. **Promotion gates** (plan §5, all five) → **the ONE golden-vs-fixed side-by-side**
   (Captain esptool GO) → promotion per the plan.

## Traps that WILL bite (full text in the canon — these are the headlines)

- Flash verification = **script exit code + NEW epoch**; the pre-flash identity is now
  prefixed `BEFORE-FLASH:` but never grep-gate a `&&` pipeline anyway (HF-57).
- Merging SSA/worktree work: merge the **named branch** from the return contract, then
  grep the gated symbols in YOUR tree before building (HF-56).
- Identity is FOUR-way; reboot restores knobs + SSL from side stores (HF-58). Palette
  authority: trust only the HUEAUD `pal=/pmode=/hd0=` fields (HF-60).
- Mode NAME not number (HF-54). Serial: typed commands need `:`; N/Y are bare hotkeys.
- The percentile sweep needs its rest gate — ratcheted in CI
  (`tests/test_colour_fix_flags_static.py`), don't fight the ratchet, understand HF-51.
- Cursor steals/resets serial ports; device may re-enumerate on a NEW number — `ioreg` to
  confirm USB presence, `--upload-port` to override (HF-46 + this session).

## Open debt (beyond the mission)

Cal-profile-file SSL re-persist path (product call) · show-state vs boot-palette-lock
ordering (Captain product-truth call) · incandescent FILTER level taste lever ·
`process_color_shift` O(256) rank scan measure-or-incrementalise · S2 per-palette need term
(13 flagged palettes) · ENERGY_EXCURSION retirement (plan §4) · harness snapshot/restore
helper · registry deployed-state row refresh after next flash · `docs/architecture/
K1_STEREO_DSP_DECISION_2026-08-11.md` untracked at repo root of docs (another lane's).

## What landed this session (all merged or in PR #56)

PR #49 writer forensics + hue metric + HUEAUD tap · #50 render trace + palette references ·
#51 five-layer decomposition + EQ sweep + capture driver · #52 S2 + fingerprint telemetry ·
#53–54 gold-killer conviction + idempotent incandescent + position smoothing · #55 edge
side-door fix + consolidated candidate + promotion plan + SSA ledger · #56 twitch fixes
(rest v3/smoothing v2/S2 threshold) + canon HF-50..62 + flag ratchets + flash-script
hardening.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-14 | agent:claude-code | Created at session close — mission (HF-61 first), device truth, traps, debt, landed list. |
