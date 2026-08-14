---
abstract: "Promotion plan for the colour-fix candidate (lane/colour-fix-goldkiller, 2026-08-13). Splits the 8 colour-lane flags into 5 FIX (K1_HUE_DRIVE_EQ_V1, K1_FALLBACK_HELD_U_V1, K1_PALETTE_BRIGHT_EXCURSION_V1, K1_POSITION_SMOOTH_V1, K1_INCANDESCENT_OUTPUT_V1), 2 DIAG-never-ship (K1_HUE_AUDIT_V1, K1_RENDER_TRACE_V1) and 1 OBSOLETE (K1_PALETTE_ENERGY_EXCURSION_V1, superseded by BRIGHT_EXCURSION), with file:line for every location. Carries the per-palette S2 sanity table: bright-stop luminance — NOT coverage or entropy — is the discriminator for crescendo-pull harm; 13 of 44 palettes flagged (DARK-ATTRACTOR / NARROW-ARC), predicate proven against both controls. Names 4 open blockers that gate promotion, incl. an unguarded fix-flag set and an O(256)-per-frame scan in process_color_shift()."
---

# Colour-fix promotion plan — 2026-08-13

> **P0.0 quarantine notice (2026-08-15):** promotion is not authorised from the historical
> B489 metrics. Absolute-level, silence and quiet-normalised gates must be re-derived on
> verified IM1 under Rev B; static findings, palette references and programme-relative
> observations retain their narrower scope. See
> `docs/forensics/P0_0_AP_INPUT_QUARANTINE_MANIFEST_2026-08-15.md`.

**Status: NOT_VERIFIED per claim except where an explicit re-derivation is
recorded below.** This is an audit, not an approval. No source, `platformio.ini`,
commit or device action was taken. Branch audited: `lane/colour-fix-goldkiller`.

---

## 0. Instrument honesty note (read first)

The first sweep of this audit returned **zero hits for all eight flags** and
would have been reported as "these flags do not exist". That was a **broken
instrument, not an absent population**: `rg` on this host resolves to
`/opt/homebrew/bin/rg` but reports `grep (BSD grep, GNU compatible) 2.6.0`, so
it rejected `--glob` and the error was being swallowed by `2>/dev/null`. A
control probe on a known-present token (`K1_LOUD_GUARD`) exposed it. Every
location below was re-derived with plain `grep -rn` and absolute paths.

Corollary for whoever executes this plan: **do not accept a zero result from a
search you have not first proven can return non-zero.**

---

## 1. Flag inventory — FIX vs DIAG vs OBSOLETE

Classification is by **the content of each gated block**, not by which env
carries it. All line numbers are on `lane/colour-fix-goldkiller`.

### 1.1 FIX — candidates for production promotion (5)

| Flag | Locations (file:line) | What the gated block actually does |
|---|---|---|
| `K1_HUE_DRIVE_EQ_V1` | `platformio.ini:412`; `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1930` (inside `process_color_shift()`, defined at `led_utilities.h:1924`) | Replaces the legacy **absolute-novelty** sweep drive (strip-floor → cube → cap) with a **running percentile over the last 256 frames**, mid-rank on ties, linear in percentile. Fixes the measured frozen sweep (dominant hue bucket static for a full minute). Behaviour-changing render code. **FIX.** |
| `K1_FALLBACK_HELD_U_V1` | `platformio.ini:418`; `system/globals.h:205`; `visual/lightshow_modes.h:422`; `effects/light_mode_waveform_tempo.cpp:122`; `effects/light_mode_waveform_hybrid_k1.cpp:199` | Publishes the palette engine's live held musical anchor (`k1_palette_held_u` / `_valid`, Core-1 write / Core-1 read) and seeds the thin-chroma fallback from it instead of the CHROMA knob. The `globals.h` block is **state for a fix**, not telemetry — nothing prints it. **FIX.** |
| `K1_PALETTE_BRIGHT_EXCURSION_V1` | `platformio.ini:424`; `visual/lightshow_modes.h:124` (adds `bright_u` to `PaletteStopsHD`), `:152` (computes it at palette-switch time), `:454` (applies the pull) | S2 crescendo excursion: pulls the sampling coordinate toward the palette's **most luminous authored stop**, gain `energy² × 0.85`, composed after the sweep offset. **FIX** — and the flag with the largest per-palette risk surface (§3). |
| `K1_POSITION_SMOOTH_V1` | `platformio.ini:430`; `effects/light_mode_waveform_hybrid_k1.cpp:233` | Replaces the RGB EMA (which traverses grey/red between distant palette colours) with a **luminance-only EMA + renormalisation to the current frame's hue/sat ratios**. Same tau, hue preserved per frame. Mode 32 only. **FIX.** |
| `K1_INCANDESCENT_OUTPUT_V1` | `platformio.ini:1314`; `visual/led_utilities.h:453` (`#ifdef`, in `quantize_color()`), `visual/led_utilities.h:984` (`#ifndef`, suppresses the legacy call) | Applies the incandescent mix law **once at the output write** instead of in-place on the persistent render buffer, where it compounded ×(mix)ⁿ across show passes (dose-response measured 2026-08-13: gold dead at 0.25, alive at 0.10). **FIX** — and the only flag that is a paired `#ifdef`/`#ifndef`, so it both adds and removes a code path. |

### 1.2 DIAG — must NEVER reach a shippable env (2)

| Flag | Locations (file:line) | Why DIAG |
|---|---|---|
| `K1_HUE_AUDIT_V1` | `platformio.ini:402`; `system/globals.h:190`; `audio/i2s_audio.h:1089`; `visual/led_utilities.h:956`, `:1156`, `:1967`; `visual/lightshow_modes.h:185` | 24-bucket cumulative hue histogram of the final post-gamma buffer + HD-cache fingerprint, emitted as a 1 Hz `HUEAUD` serial line. Pure measurement surface; consumer is `scripts/regression-harness/hue_coverage.py`. Header comment states "Diag env only — never production". |
| `K1_RENDER_TRACE_V1` | `platformio.ini:403`; `visual/k1_render_trace.h:21`, `.cpp:5`; `visual/led_utilities.h:18`, `:1181`; `serial/serial_typed_dispatch.h:39`, `.cpp:34`, `.cpp:132`; `serial/serial_typed_cmd_table.def:48`; `serial/serial_menu.cpp:2805` | LED-level PSRAM frame capture with `rtrace_arm/status/dump` serial surface. Compiles to nothing without the flag (no global-ctor leak, per `k1_render_trace.cpp:3`). Non-shippable by construction. |

**These two are already guarded by a red-capable test.**
`tests/test_render_trace_static.py:61` (`test_rtrace_flag_only_in_the_hueaud_env`)
asserts each flag's carrier list is **exactly** `["env:k1_bench_im69d_hueaud]"`.
Any promotion that drags a diag flag into a prod env fails that test. Verified by
reading the assertion; it compares an exact list, so it can go red.

### 1.3 OBSOLETE — retire (1)

| Flag | Locations (file:line) | Disposition |
|---|---|---|
| `K1_PALETTE_ENERGY_EXCURSION_V1` | `visual/lightshow_modes.h:473` (code); `platformio.ini:185` (comment block only — **no `-D` line anywhere**) | Implemented 2026-06-11, measured, and deliberately **never enabled**: host A/B showed palette-dependent results (palette 7 entropy 0.18→1.51 bits, but **palette 3 distinct colours 48→25**). It is the **one-sided ancestor** of `K1_PALETTE_BRIGHT_EXCURSION_V1` and applies a second, independent `hue += energy*0.20` at `lightshow_modes.h:473`, immediately after S2's pull at `:454`. **Retire it** — see §4. |

> **Compounding hazard, load-bearing:** the S2 block (`:454`) and the ENERGY block
> (`:473`) are **sequential, not mutually exclusive**. If both flags were ever set
> in one env the arc position would be displaced twice per frame. Nothing in the
> source or the test suite prevents that today.

---

## 2. Env chain and what a promotion would add

### 2.1 Current bench chain (all NON-SHIPPABLE, bench `B489A500` only)

```
k1_bench_im69d                        (platformio.ini:317)
└── k1_bench_im69d_hueaud             (:398)   + K1_HUE_AUDIT_V1, K1_RENDER_TRACE_V1   [DIAG]
    └── k1_bench_im69d_hueaud_eq      (:408)   + K1_HUE_DRIVE_EQ_V1
        ├── k1_bench_im69d_hueaud_eqfb    (:414) + K1_FALLBACK_HELD_U_V1
        └── k1_bench_im69d_hueaud_s2      (:420) + K1_PALETTE_BRIGHT_EXCURSION_V1
            └── k1_bench_im69d_hueaud_s2ps   (:426) + K1_POSITION_SMOOTH_V1
                └── k1_bench_im69d_hueaud_s2psi (:1310) + K1_INCANDESCENT_OUTPUT_V1
```

Two structural observations:

1. **Every fix candidate is currently only reachable through the DIAG parent.**
   There is no env that carries the fix flags *without* `K1_HUE_AUDIT_V1` and
   `K1_RENDER_TRACE_V1`. So no build has ever exercised the fix set in a
   production-shaped configuration — the fixes are **mock-adjacent**, validated
   only alongside instruments that production will not have.
2. **`k1_bench_im69d_hueaud_s2psi` is orphaned at `platformio.ini:1310`**, ~880
   lines from its five siblings (`:398`–`:430`), wedged after the effect-registry
   envs. Cosmetic, but it is how a chain link gets missed during retirement.

### 2.2 Minimal production promotion set

Production envs: `k1_hardware` (`platformio.ini:18`), `k1_prod_im73d` (`:530`).

**Add to the production env(s) — fix flags only, exactly five `-D` lines:**

```ini
-DK1_HUE_DRIVE_EQ_V1
-DK1_FALLBACK_HELD_U_V1
-DK1_PALETTE_BRIGHT_EXCURSION_V1
-DK1_POSITION_SMOOTH_V1
-DK1_INCANDESCENT_OUTPUT_V1
```

**Never add:** `K1_HUE_AUDIT_V1`, `K1_RENDER_TRACE_V1` (guarded — see §1.2).
**Never add:** `K1_PALETTE_ENERGY_EXCURSION_V1` (retire instead — §4).

Revert for the whole promotion is deletion of those five lines; each gated block
retains its `#else` / `#ifndef` legacy path, so flag-OFF is the pre-promotion
behaviour. **NOT_VERIFIED that flag-OFF is byte-identical** — that is the
orchestrator's byte-inertness gate, not a claim this audit can make.

---

## 3. Per-palette S2 sanity table

Source: `scripts/regression-harness/results/palette_reference.json`
(44 palettes, 24 hue buckets). Bright-stop position `bright_u` and its luminance
were computed with the **firmware's own law** from `lightshow_modes.h:152`
(`lum = 0.30r + 0.59g + 0.11b`, strict `>` so the first maximum wins, stops
truncated at `PAL_HD_MAX_STOPS = 48` and at the `idx == 255` terminator), using
the shipped parser in `palette_reference.py` so the palette order is the real
`gGradientPalettes[]` registry order.

**Instrument proof (both run, both re-derived):**
- `python3 palette_reference.py self-test` → **PASS**, 6 checks including
  deliberate-RED cases (`malformed-rejected` raises, `black-authors-nothing`
  yields no buckets) and `real-source-count: count=44`.
- Regenerated from source in-memory and compared to the on-disk JSON → **MATCH**
  (the results file is current, not stale).

### 3.1 The discriminator is bright-stop LUMINANCE, not coverage or entropy

My first harm predicate used low coverage / low entropy and flagged **32 of 44
palettes** — a flag that fires on 73% of the population discriminates nothing.
Worse, it flagged **palette 40 `K1_Naberius_Gold_gp` (coverage 0.167, entropy
1.95)**, which is the palette S2 was explicitly designed *for* ("for Naberius
Gold: the gold", `lightshow_modes.h:125`). Coverage and entropy are therefore the
**wrong** instrument for this question.

The measured harm case — **palette 3 `rgi_15_gp`, distinct colours 48→25** — has
*healthy* coverage (0.333) and *healthy* entropy (2.71). What is anomalous about
it is that its **brightest authored stop is itself dark: luminance 0.242, the
lowest of all 44 palettes.** A crescendo pull toward that attractor moves the
render *into* darkness. That is the mechanism, so that is what the predicate must
measure.

**Predicate:** `DARK-ATTRACTOR` = bright-stop luminance < 0.45 · `NARROW-ARC` =
authored entropy < 1.20 bits.

**Controls (the predicate must discriminate, not merely fire):**
- Negative control, palette 3 `rgi_15_gp` (measured harm) → **flagged** ✅ required True
- Positive control, palette 40 `K1_Naberius_Gold_gp` (design target) → **not flagged** ✅ required False

### 3.2 Flagged palettes — 13 of 44

| idx | palette | coverage | entropy (bits) | bright_u | bright lum | flag |
|---|---|---|---|---|---|---|
| 2 | `es_ocean_breeze_036_gp` | 0.083 | 0.95 | 0.600 | 0.763 | NARROW-ARC |
| **3** | **`rgi_15_gp`** | 0.333 | 2.71 | 0.247 | **0.242** | **DARK-ATTRACTOR** (measured harm class) |
| 4 | `retro2_16_gp` | 0.125 | 1.11 | 0.000 | 0.534 | NARROW-ARC |
| 5 | `Analogous_1_gp` | 0.333 | 2.27 | 1.000 | 0.300 | DARK-ATTRACTOR |
| 8 | `es_ocean_breeze_068_gp` | 0.083 | 1.07 | 0.000 | 0.545 | NARROW-ARC |
| 16 | `gr64_hult_gp` | 0.333 | 2.20 | 0.510 | 0.430 | DARK-ATTRACTOR |
| 18 | `ib_jul01_gp` | 0.417 | 2.87 | 0.518 | 0.382 | DARK-ATTRACTOR |
| 21 | `Fuschia_7_gp` | 0.250 | 2.51 | 1.000 | 0.284 | DARK-ATTRACTOR |
| 22 | `es_emerald_dragon_08_gp` | 0.083 | 0.46 | 0.000 | 0.705 | NARROW-ARC |
| 26 | `Magenta_Evening_gp` | 0.083 | 0.81 | 0.298 | 0.329 | DARK-ATTRACTOR + NARROW-ARC |
| 30 | `BlacK_Magenta_Red_gp` | 0.208 | 1.92 | 0.498 | 0.410 | DARK-ATTRACTOR |
| 39 | `K1_Ultraviolet_Ascend_gp` | 0.292 | 2.64 | 0.808 | 0.360 | DARK-ATTRACTOR |
| 43 | `K1_Ultraviolet_Bright_gp` | 0.292 | 2.60 | 0.000 | 0.360 | DARK-ATTRACTOR |

Full 44-row table (all fields, unflagged rows included):
`/private/tmp/ssa-consolidate/bright.json`, generator
`/private/tmp/ssa-consolidate/bright_stop.py`.

### 3.3 What this implies for S2

S2's gain is **fixed** (`energy² × 0.85`, `lightshow_modes.h:454`) and takes no
account of whether the attractor it is pulling toward is bright. On the 9
DARK-ATTRACTOR palettes the crescendo pull is **anti-correlated with its own
purpose**: peaks drag the coordinate onto a dark stop, which is the exact
mechanism behind the palette-3 measurement that parked the ancestor flag.

Recommendation (design decision, not an audit finding): **gate or scale the S2
gain by bright-stop luminance** — e.g. attenuate the pull when `bright_lum` is
below the palette's own mean stop luminance, so a palette whose brightest stop is
dark simply keeps the anchor-plus-sweep behaviour. `bright_u` is already computed
once at palette-switch time (`lightshow_modes.h:152`), so carrying `bright_lum`
alongside it in `PaletteStopsHD` costs one float and no per-frame work.

**S2 must not be promoted on the strength of Naberius Gold alone.** The eyes-on
evidence to date is a palette that the predicate says is safe; the 13 flagged
palettes are unmeasured.

---

## 4. Retirement list

| Item | Location | Action | Rationale |
|---|---|---|---|
| `K1_PALETTE_ENERGY_EXCURSION_V1` code block | `visual/lightshow_modes.h:473` | **Delete the block** | Superseded by S2 at `:454`. Never enabled since 2026-06-11. Leaving it is a live compounding hazard if both flags are ever set (§1.3). |
| `K1_PALETTE_ENERGY_EXCURSION_V1` comment | `platformio.ini:185` | Rewrite as a one-line tombstone pointing at S2 | Per repo doctrine: tombstone on supersedence, do not append. |
| Stale references | `docs/handover/HANDOVER_2026-08-13_colour_fix_lane.md:58`; `docs/forensics/colour-nuance-regression-verdict-2026-08-13.md:38`; `docs/forensics/colour-fix-lane-2026-08-13.md:79`; `docs/canon/SESSION_CANON_2026-08-13_colour_forensics_config_poison.md:20,:84`; `docs/architecture/K1_PALETTE_COVERAGE_ENGINE_DESIGN_2026-08-13.md:27,:88`; `scripts/regression-harness/render_replay.py:588`; `.claude/skills/k1-colour-truth/SKILL.md:52` (+ `.cursor/`, `.codex/` mirrors) | Update on retirement | Describe it as *parked*/*measured*; all become wrong once the code is deleted. |
| Bench envs `k1_bench_im69d_hueaud_eq` / `_eqfb` / `_s2` / `_s2ps` / `_s2psi` | `platformio.ini:408, 414, 420, 426, 1310` | **Retire only after promotion is eyes-on-approved**, as one deletion | Single-variable bisect ladder; still the only way to attribute movement to one flag. Not dead yet. |
| Orphaned env placement | `platformio.ini:1310` | Move `_s2psi` up beside its siblings, or delete with the ladder | Structural hygiene; an 880-line-displaced chain link is how a retirement misses one. |

`k1_bench_im69d_hueaud` itself (`:398`) **stays** — it is the measurement build
and the registry (`docs/hardware/device-build-registry.md:101`) records it as the
current bench flash.

---

## 5. Blockers on promotion

1. **No fix-flag guard test exists.** `test_render_trace_static.py:61` pins the
   two DIAG flags to exactly one env. Nothing asserts anything about the five FIX
   flags — not that they land in production, not that they stay out of the diag
   env, and crucially **not that `K1_PALETTE_BRIGHT_EXCURSION_V1` and
   `K1_PALETTE_ENERGY_EXCURSION_V1` are mutually exclusive.** A promotion should
   ship with that guard, and the guard should be mutation-checked (neuter it,
   watch the right test go red).
2. **The fix set has never been built without the instruments.** Every env
   carrying a fix flag descends from `k1_bench_im69d_hueaud` (§2.1). A
   production-shaped build of the five fixes is a prerequisite, not a formality.
3. **`K1_HUE_DRIVE_EQ_V1` adds an O(256) linear scan per frame** inside
   `process_color_shift()` (`led_utilities.h:1930`, function at `:1924`) — a full
   256-element ring rescan every frame on Core 1. At the ~200 FPS the block's own
   comment assumes, that is ~51k float comparisons/second added to the render
   path. Almost certainly affordable; **NOT_VERIFIED** — it should be measured,
   not assumed, and an incremental rank would remove the question entirely.
4. **S2 is unmeasured on 13 of 44 palettes**, including 9 whose brightest
   authored stop is dark (§3.3). This is the largest correctness risk in the
   promotion set.

---

## 6. Verification ledger

| Claim | How re-derived | Result |
|---|---|---|
| Flag locations (all 8) | `grep -rn` per flag, absolute path, after control-probe proof | Table §1, file:line each |
| Fix vs diag split | Read every gated block's body | §1.1 / §1.2 |
| Diag flags already guarded | Read `tests/test_render_trace_static.py:61-75` | Exact-list assertion, red-capable |
| `ENERGY_EXCURSION` has no `-D` line | `grep -rn` — only `platformio.ini:185` comment + code block | Confirmed OBSOLETE |
| Env chain | `grep -n '^\[env'` + `sed` on `platformio.ini:380-440`, `:1300-1325` | §2.1 |
| Palette reference current | Regenerated in-memory, compared to on-disk JSON | MATCH |
| Palette instrument sound | `palette_reference.py self-test` | PASS, 6 checks incl. deliberate-RED |
| `bright_u` values | Firmware law replicated via shipped parser; `PAL_HD_MAX_STOPS=48` parsed from source, not assumed | §3.2 |
| Harm predicate discriminates | Negative control (palette 3) flagged, positive control (palette 40) clean | Both required outcomes met |
| Flag-OFF byte-inertness | **Not attempted** | **NOT_VERIFIED** — orchestrator's gate |
| On-device behaviour of any fix flag | **Not attempted** | **NOT_VERIFIED** — no device action in scope |

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code (SSA-CONSOLIDATE) | Created. Flag inventory with file:line, FIX/DIAG/OBSOLETE split, env chain, minimal promotion set, per-palette S2 sanity table with proven discriminator, retirement list, 4 blockers. |
