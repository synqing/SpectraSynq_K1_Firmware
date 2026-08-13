---
abstract: "Handover 2026-08-13 (session close, context-exhausted). Two arcs completed: (1) ALL four outstanding IM69D items landed (PRs #43-#46: gate merge, P2.B quarantine, Stage 1b/2, floors+profile 2, P5.B matrix — plus the Bose round); (2) the colour-nuance forensic excavation (PR #47): CHROMAGRAM_RANGE 60→1 config poisoning + a REAL main colour-path regression vs the Aug-8 golden bin. NEXT MISSION = the colour fix lane (metric-first, golden oracle, ONE final eyes-on). Bench B489 deliberately left on the NON-main golden state with era config; its measured SSL=187 cal is overwritten (era 253). Read order, device truth, pre-registered tests, and the complete pitfall catalogue inside."
---

# Handover — 2026-08-13 session close → the colour fix lane

**Repo tip at close:** `main` contains PRs #43, #44, #45, #46, #47 (all merged, CI green — every
red this session was the PlatformIO package-registry flake; rerun always cured it).
**Working worktrees:** `.worktrees/im69d_gate_fix` (docs branch, clean) · `.worktrees/golden_ab`
(detached @ `9013ed90`, disposable — `git worktree remove` when convenient).

## Read in this order (short on purpose)

1. **This file** — state, mission, pitfalls.
2. `docs/canon/SESSION_CANON_2026-08-13_colour_forensics_config_poison.md` — HF-41..49 + the
   full forensic timeline of the colour collapse. Non-optional.
3. `docs/forensics/colour-nuance-regression-verdict-2026-08-13.md` — the A/B ladder verdict +
   fix-lane contract.
4. Skill `k1-colour-truth` (auto-loads on colour work) — the five hard rules + golden replay recipe.
5. `docs/hardware/im69d130-dual-mic-learnings-2026-08-13.md` — the whole IM69D programme
   synthesis (published: https://claude.ai/code/artifact/405ee536-b0a1-4a2a-b746-970eb4327d57).
6. SSA evidence (only as needed): `_scratch/colour_forensics_20260813/SSA1..5` and the prior
   25-file audit `_scratch/colour_corruption_audit_20260810/` (its L4 predicted all of this).

## DEVICE TRUTH at close — verify by chip id before touching anything

| Device | Chip | Port (advisory) | Running | Config state | ⚠ |
|---|---|---|---|---|---|
| **Bench K1v2** | `B489A500` | `cu.usbmodem12201` | **GOLDEN readback** `git=db300db epoch=1786214500 env=k1_bench_im69d_ble` — **NON-main, Captain-approved eyes-on, LEAVE IT unless the lane needs it** | era config replayed: RANGE=60, SENS=2.40, **SSL=253**, CHROMA=0.05, MOOD=0.05, mode 32 | **measured SSL=187 cal OVERWRITTEN** — restore `:sweet_spot_min=187` (or recal under Captain silence-go) before ANY current-main measurement on this unit |
| **Unit 2** | `0C54FC00` | `cu.usbmodem1101` | `k1_unit2_im69d_right @ 2904c9b9` | SSL=167 `measured`, intact | untouched by the excavation |
| Main K1 | `F887A500` | `cu.usbmodem1401` | untouched all session | — | not yours unless told |
| Tab5 P4 | `30:ed:a0:e0:c1:a0` | `cu.usbmodem12401` | untouched | — | not a K1 |

**Main checkout** (`/Users/spectrasynq/SpectraSynq_K1_Firmware`) is ~60+ behind with FIVE dirty
Deck16/Tab5 files (`k1_claim_adv_v1.h` + 3 network files + a Tab5 registry row) — **another
lane's uncommitted work, predates this session, do not commit/stash/discard it.** Work from
`.worktrees/im69d_gate_fix` or a fresh worktree.

## THE MISSION — colour fix lane (contract already defined, not started)

Captain's product complaint (verbatim spirit): builds used to "intelligently deploy the full
spectrum of colours within each palette, every colour getting a fair chance — ALL modes";
current main is stifled. Proven causes: (1) config poisoning `CHROMAGRAM_RANGE` 60→1;
(2) main renders gold as WHITE (18/32) / single colour (mode 3) **with identical era config**
vs the golden bin — a real shared-colour-path regression.

**Execution order:**
1. **Build the hue-coverage metric** on the `K1_MATRIX_AUDIT_V1` machinery (post-gamma output
   buffers = artefact boundary): distinct-hue histogram / palette-coverage entropy per minute.
   Run it on the golden bin+config = **the oracle number**. No eyes until the metric matches.
2. **Find the RANGE=1 writer** BEFORE fixing anything: candidates = Tab5/Deck16 control write
   (the 68-control map may expose chromagram_range), a defaults reset, or a **load-time clamp
   added on main** (if a clamp: live `:chromagram_range=60` sticks but reboot re-poisons —
   test exactly that first: set 60 on a main build, reboot, re-read).
3. **Bisect main's colour path against the metric.** Ranked suspects (SSA1/3/5): `b643b8d6`
   mono-hue knob fallback (bound it: fire only on true-black, preserve saturation) · joint-gate
   chroma-thinning as its trigger · `97276b3a` boot palette lock (both channels pinned to 40,
   overrides persisted state every boot) · held-centroid attractor + `K1_PALETTE_ENERGY_EXCURSION_V1`
   (implemented, measured, OFF everywhere — the likely centrepiece; tune against the existing
   palette-coverage gate; prior measurement: helps palette 7, hurt palette 3) · `024591dd` bin
   remap · the `isfinite`/`-fno-finite-math-only` NaN-hue correction (part of the remembered
   "richness" was NaN chaos — if Captain wants that character, recreate it DELIBERATELY as a
   bounded hue-wander, never by re-breaking the maths).
4. **ONE final eyes-on**: golden vs fixed-main side by side. That is the only Captain look.
   P5.A colour policy (`COLOUR_POLICY_GO.md`, Kill1/Kill2, SAME_SCAR modes 3/9/12/13) is the
   formal frame for the mode-level fixes and has never run.

**Golden oracle replay recipe** (needs Captain "GO esptool" for the raw write — precedent set):
`esptool write_flash 0x10000 _scratch/deck16_backend_b1b2_20260808/flash_readback_k1.bin`
(sha256 `04215afb…`), then `:chromagram_range=60 :sensitivity=2.40 :sweet_spot_min=253
:chroma=0.05 :mood=0.05 :set_mode=32`. Era config source of truth:
`_scratch/im69d_vs_main_20260805/20260805T201538_im69d_vs_sph_ab/preflight_bench_im69d.log`.

## THE COMPLETE PITFALL CATALOGUE (every one bit us THIS session)

**Colour/measurement (HF-41..49, full text in the canon):**
- Firmware identity = **bin × persisted config × cal**. Era binary + today's NVS misled Captain 3×.
- **Config-diff FIRST**: live `:dump` vs an era preflight log, before any git archaeology.
- Captain eyes-on PASS ⇒ immediately take flash readback + full `:dump` + `wip/*` checkpoint.
  The Aug 6-7 richness died uncommitted in 3 days; the Aug-9 bin survives only as a hash.
- **One pre-registered variable per Captain look. "Firmware roulette" = STOP.** He said so.
- No cross-era config porting (I set July's 0.87 sensitivity on an August system — wrong; era was 2.40/1.99).
- Verify a serial command AND its consumer exist **on the flashed build**: `:stream_agc` is a
  dead toggle (no emitter since the SB→K1 fork); era bins lack `incandescent_*`.
- Don't knob-tune mid-experiment builds (SSL was drive-normaliser AND gate-input on the Aug-7/8
  tree — 1470 clipped white, 1100 killed the VP; no good value exists).

**Operational fuckery (will hit you again):**
- **Cursor's serial monitor auto-reconnects and steals the port** (4× tonight), and opens can
  reset USB-JTAG devices mid-observation. `lsof /dev/tty.usbmodem*` before declaring anything
  dead; ask Captain to close the tab ("Closed" means try again); expect to re-ask.
- **Raw esptool is classifier-blocked and doctrine-banned without explicit Captain GO** — ask
  with one line; the sanctioned path is `scripts/agent/k1-flash-verified.sh` (which **refuses
  dirty trees** — commit first; that guard saved provenance twice).
- `set_mode` takes the **DENSE menu index, not the ordinal** — probe and confirm via the AP
  `lightshow=` field (or `mx_*`/`mode=` on matrix builds). The AP stream is OFF after
  `p4_baseline_leg.py` runs (`:ap_stream=0` at exit) — witnesses go blind silently; re-enable.
- **CI reds this session were ALWAYS the PlatformIO package-registry IO flake** (both build
  jobs; the pure-Python job passes). Check `--log-failed` for `package-manager-ioerror`, rerun;
  don't debug your code first. But NEVER assume — one was a real serial-safety ratchet catch.
- The typed-command **table (.def) is safety metadata; live dispatch is the `parse_command`
  strcmp ladder** — a row without a ladder hop compiles clean and answers `Bad command`
  (caught live, ratcheted: `test_scap_dispatch_reaches_the_parse_command_ladder`).
- `_scratch/` is **gitignored** — decision-bearing artefacts need a tracked copy under
  `docs/forensics/`. The pre-commit hook classes changes (docs=free; tests=pytest;
  firmware/platformio=pytest+build) — run gates manually when using `--no-verify`.
- Byte-identity = the **3 stable ELF sections** (`.dram0.data/.iram0.text/.iram0.vectors`),
  never the .bin hash. Session-long reference for k1_hardware: `72417182/afa23c99/d383aa70`.
- pyserial here: `dtr=` is not a constructor kwarg (set `s.dtr=True` after open); grep with
  `/usr/bin/grep` (the shell's grep gets context-mode-wrapped and lies about matches).
- The lost-tree trap: `git diff` output in this repo indents deletions (`  -`), so `grep '^-'`
  is a dead oracle (SSA2 proved it with a positive control). Dangling snapshots exist —
  `b09d032f` is the full Aug-11 tree.

**Also inherited (older canons, still live):** cal is Captain-verbal-gated ALWAYS · identity by
chip-id never port · laptop speakers ≈5× too little SPL (numerically re-proven: Unit 2 stayed
silence-latched through 75% of laptop-music frames) · canonical music fixture =
`~/Music/PioneerDJ/Demo Tracks/Demo Track 1.mp3` (Captain personally corrected an ad-hoc pick).

## Open debt (beyond the mission)

Dwell/persistence gate (drain flashes; 18/21 no-latch) · lock DUTY 9–27% → tempo-FSM lane ·
stereo capture duty 56% (DMA sizing) · Unit 2 dual-capsule topology single-path evidenced ·
spacing D unmeasured · H_C2 occlusion leg needs a hand · `k1_custom` blocked pending device
nomination · LED_160_AB env keep-or-remove · AOP ladder (P3.D) unrun · bench SSL=187 restore
(above) · golden_ab worktree cleanup · main-checkout Deck16 dirt (not ours).

## What landed this session (for orientation, all merged)

PR #43 silence-gate lane (frac 1.75, IM69D scoping, transfer rule) · PR #44 P2.B quarantine +
Stage 1b/2 instrument + P4 floors + P5.B matrix · PR #45 profile 2 populated + Bose round
(floors closed, H_C substantially rejected — stereo visuals would be synthesised; H_C2
coherence is the second capsule's real value) · PR #46 IM69D learnings synthesis · PR #47
colour forensics verdict + canon + `k1-colour-truth` skill.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Created at context exhaustion — device truth, colour-fix-lane contract, complete pitfall catalogue, open debt. |
