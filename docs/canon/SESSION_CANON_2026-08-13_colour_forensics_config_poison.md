---
abstract: "SESSION CANON 2026-08-13 (colour forensics): HF-41..HF-49 failure taxonomy + full forensic timeline of the palette-colour collapse. Core truths: CONFIG IS HALF THE FIRMWARE IDENTITY (CHROMAGRAM_RANGE 60→1 poisoning impersonated a code regression); the richness was CREATED in the uncommitted Aug 6-7 VJ tree and survives ONLY as the Aug-8 flash readback + the Aug-5 20:15 preflight config dump (the GOLDEN ORACLE pair); main additionally has a real colour-path regression (gold→white with identical config); Captain's eyes are a scarce instrument — one variable per look, metric-first fix lane. Read with docs/forensics/colour-nuance-regression-verdict-2026-08-13.md and the k1-colour-truth skill."
---

# Session canon 2026-08-13 — the colour forensics session

**Companion:** `docs/forensics/colour-nuance-regression-verdict-2026-08-13.md` (the A/B ladder verdict)
· SSA evidence `_scratch/colour_forensics_20260813/SSA1..5` · prior audit `_scratch/colour_corruption_audit_20260810/`
· Skill: `k1-colour-truth`. HF numbering continues from `SESSION_CANON_2026-08-12_device_evidence_integrity.md` (HF-29..40).

---

## 1. Forensic timeline (the memory dump — what actually happened, in order)

- **2026-07-02 — the collapse chain was already canon.** Device-proven on main K1:
  loud music → AGC + loud-guard attenuate GDFT → chroma flatness sinks into the sparseness-gate
  band → gate-ZERO on real music → weak palette centroid → **held-hue hard freeze → "every
  palette renders a handful of auto-shift-swept colours"** (platformio.ini comment ~L185).
  Vibrancy v1 (07-03) softened the freeze to a proportional blend. The full fix —
  `K1_PALETTE_ENERGY_EXCURSION_V1`, which deliberately traverses the palette's authored arc —
  was implemented, measured (palette 7 entropy 0.18→1.51 bits GOOD; palette 3 distinct colours
  48→25 WORSE), and **left OFF in every env**. This documented chain then sat ignored for six weeks.
- **2026-08-05** — IM69D Phase 0 on the bench (G=8 flash `97276b3a` — same commit ships Mode 32
  and the boot palette lock — then G=4 reflash `9013ed90`, SSL=74).
  **20:15: a full `:dump` preflight of the bench is logged** —
  `_scratch/im69d_vs_main_20260805/20260805T201538_im69d_vs_sph_ab/preflight_bench_im69d.log` —
  capturing the golden config: **CHROMAGRAM_RANGE=60**, SENSITIVITY=2.40, SWEET_SPOT_MIN=253,
  CHROMA=0.05, MOOD=0.05, PHOTONS=1.0, MIRROR=1, mode 32. Nobody knew this file would matter.
- **2026-08-06/07 — the richness is CREATED, uncommitted.** The VJ session's dirty-tree work on
  `feat/ap-advice-phase0-im69d-gain8` @ `db300db` produces the colour behaviour Captain
  remembers ("every colour in each palette got a fair chance, ALL modes"). Bench flashed
  `db300db`+dirty (bin `c831687b`, 08-07, "the one that stuck"). **The exact source of the
  richness was never committed and is not reconstructible** — the clean Aug-5 build is
  single-colour (proven 2026-08-13), so the magic lived in that dirty delta.
- **2026-08-08** — extended-recovery proofs take a **full app-flash readback of the bench**:
  `_scratch/deck16_backend_b1b2_20260808/flash_readback_k1.bin` (sha256 `04215afb…`) —
  **the golden bin**, by accident.
- **2026-08-09** — Mirror-purge reflash (bin `21c9eb50…`, **hash retained, bytes NOT** — gone
  forever). Same day: Unit 2 gets the 206 `k1_custom` build (the IM73D misflash) — Captain's
  rich window closes. Colour looks destroyed on Unit 2 → the Aug-9 cascade "heals" (M18
  peak|vu + HSV fallback) are written under a poisoned mic premise.
- **2026-08-10** — a 25-file colour-corruption audit runs (`_scratch/colour_corruption_audit_20260810/`):
  layers L1–L3 closed, **L4 left OPEN** ("chromagram SAME_SCAR + dforge presence starve = why
  colour can still look destroyed"), the M18 heal's "glass PASS" explicitly **disputed as
  colour-identity**, and four Captain questions posed — never answered. P5.A (the colour-policy
  Kill fixes) never ran.
- **2026-08-11** — `b643b8d6` lands on main: `tempo_peak_fallback_colour()` re-seeds every pixel
  from the scalar CHROMA knob whenever chromagram colour runs thin (modes 18/32 → one knob-hue,
  near-white at low CHROMA). Same day: IM73D tombstone `1bdf54d0` (edits waveform_tempo), the
  Deck16 merge, and the full-tree snapshot `b09d032f` — **which already renders single-colour**:
  the richness was gone from the tree by 08-11.
- **2026-08-11/12** — the silence-gate lane (frac saga 1.25→2.50→1.75, recal SSL 167/187,
  IM69D scoping) — correct work, but it further thins chroma states that trigger the fallback.
- **2026-08-12/13 (this session)** — items 1–4 land (PRs #43–#46). Captain then reports the
  colour loss. Excavation: 5 parallel SSAs + the discovered 08-10 audit + a live A/B ladder on
  the bench under explicit esptool GO. Ladder results (music playing, config controlled from
  step 4): snapshot `b09d032f` = single colour · clean Aug-5 `9013ed90` = single colour ·
  **Aug-8 readback + today's config = richer but gold→WHITE** · **Aug-8 readback + era config =
  "yes yes yes, much closer"** · **main + era config = gold renders WHITE (18/32), single
  colour (mode 3)**. Verdict: **two defects** — config poisoning (`CHROMAGRAM_RANGE` 60→1) and
  a real main colour-path regression vs the golden bin. Bench left in the approved golden state.

## 2. Failure taxonomy — HF-41..HF-49 (each cost real time tonight)

| HF | Failure | Rule that prevents it |
|---|---|---|
| **HF-41** | **Config treated as background, not identity.** Three eyes-on verdicts were taken on era binaries running TODAY'S NVS — every one misleading. | A firmware identity is **(bin sha × persisted config × cal)**. Any A/B pins all three or is void. |
| **HF-42** | A one-field config poisoning (`CHROMAGRAM_RANGE` 60→1) impersonated a code regression and triggered a five-agent code excavation. | **Diff the live `:dump` against an era dump FIRST** — minutes, before any git archaeology. Era dumps live in `_scratch/*/preflight_*.log`. |
| **HF-43** | The Aug-9 bin survives only as a hash; the golden bin survives only by accident (a recovery-lane readback). | **At every Captain eyes-on PASS: take a flash readback + a full `:dump` and file both.** The pair IS the reproducible product state. |
| **HF-44** | "Firmware roulette" — an uncontrolled ladder run on Captain's eyes (5+ looks, variables changing between looks, including device resets from serial reconnects). | Captain's eyes are a scarce instrument: **one pre-registered variable per look**, or better, a numeric metric with eyes only at the end. |
| **HF-45** | The richness was created in UNCOMMITTED work and silently lost within 3 days (already dead in the 08-11 snapshot). | The moment Captain approves ANYTHING eyes-on, the exact tree gets a `wip/*` checkpoint or snapshot commit — approval without provenance is value evaporating. |
| **HF-46** | Cursor's serial monitor auto-reconnect stole the port 4× mid-operation and reset the device between Captain's looks. | `lsof /dev/tty.usbmodem*` before declaring a device dead or a probe failed; coordinate the port with Captain explicitly; know that opens can reset USB-JTAG devices. |
| **HF-47** | The agent "fixed" sensitivity 1.99→0.87 using a JULY (IM73D-era) baseline on an AUGUST (IM69D) system — cross-era porting, made things worse. | The P2.B rule generalises: **no config value ports across eras/mics without a matching-era receipt.** 1.99 was the era truth; 0.87 was a different machine's. |
| **HF-48** | Two dead surfaces misread: `:stream_agc` toggles a flag nothing consumes (emitter lost in the SB→K1 fork); `incandescent_mode` doesn't exist on the era binary. | Before interpreting a command's result, prove the command exists AND its consumer exists **on the flashed build** (grep the era tree, not HEAD). |
| **HF-49** | Knob-tuning a mid-experiment build: on the Aug-7/8 tree, SSL is simultaneously drive normaliser and silence-gate input — 1470 clipped white, 1100 gated the VP off; no good value exists. | On hybrid/mid-lane builds, don't tune — move to a coherent era (earlier or later). Knobs only mean what THAT build says they mean. |

## 3. Insights (what we now know that we didn't)

1. **The golden-oracle method works**: byte-exact readback + era config dump = a fully
   reproducible reference state, recovered tonight across 5 days and ~60 commits of drift.
2. The 07-02 collapse-chain comment, the 08-10 audit's open L4, and the never-run P5.A each
   *predicted* tonight's symptom. **Written doctrine did not prevent it — only this canon's
   mechanical rules and the metric-first fix lane will** (same conclusion as every prior canon).
3. `K1_PALETTE_ENERGY_EXCURSION_V1` is a measured, parked, palette-coverage feature — the fix
   lane's likely centrepiece, to be tuned against the existing palette-coverage gate.
4. Deck16/Tab5 wrote or clamped colour config — **WRITER IDENTIFIED 2026-08-13**: the Aug-9
   full71 control-map harness (stimulus `vmin+0.37` → `1.37` → `uint8_t`→1 → persisted, no
   restore step; no load-time clamp exists). Full proof + guard rule:
   `docs/forensics/chromagram-range-poison-writer-2026-08-13.md`.
5. The next agent's fix lane is contractually defined in the verdict doc §Fix lane:
   hue-coverage metric on the matrix-audit machinery, golden bin = oracle, bisect against the
   metric, ONE final eyes-on.

## 4. Bench state at canon time (do not "clean up" blindly)

`B489A500`: **golden readback** (`git=db300db epoch=1786214500 env=k1_bench_im69d_ble`,
NON-main, Captain-approved) + era config (RANGE=60, SENS=2.40, **SSL=253 — the measured
2026-08-12 cal value 187 is overwritten**; restore 187 or recal before current-main measurement
work). Unit 2: untouched tonight (`k1_unit2_im69d_right @ 2904c9b9`, SSL=167 intact).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Created at session close — timeline, HF-41..49, insights, bench state, fix-lane pointer. |
