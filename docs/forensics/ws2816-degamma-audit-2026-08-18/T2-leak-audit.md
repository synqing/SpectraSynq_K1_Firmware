---
abstract: "T2 default-path leak audit of the three WS2816-Testbed commits (07987bb1, 810846bc, 25bec114) PLUS the config-writer and factory-default hunt (§6-§7). Verdict: 07987bb1 and 810846bc are fully #ifdef-guarded; 25bec114 LEAKS — an UNGUARDED complementary+mirror→split EdgeMixer coercion, live on BOTH units, but hue-angle-only and channel-sum invariant. §7 is the decisive finding: no commit changed the CHROMA/MOOD/INCANDESCENT_FILTER/BASE_COAT factory defaults, and the Main RPL's live values match those defaults EXACTLY on all four — so the RPL is the virgin unit and the BENCH carries the written state. §6 names two harnesses that write NVS-persisted knobs with no restore (colour_baseline_capture.py, k1_trace_capture.py), neither of which produces the bench's exact values."
---

# T2 — Default-path leak audit (WS2816-Testbed commits)

Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`, branch `feat/k1-scheduling-generation-hardening`.
Audited: `07987bb1`, `810846bc`, `25bec114`. Read-only; no firmware edited, nothing flashed.

Default path = code compiled when **both** `K1_WS2816_LEVER2_V1` and `K1_PALETTE_HD_V2` are undefined.

## Verdict

| Commit | Firmware leak to default path? |
|---|---|
| `07987bb1` (Lever-2 emit backend) | **NO** — every hunk guarded |
| `810846bc` (Palette HD V2) | **NO** — every hunk guarded; flag is defined in **no** env at HEAD (dead code) |
| `25bec114` (EdgeMixer coerce) | **YES — worst offender.** Unguarded render-config change, live on both units |

## 1. Hunk table

### 07987bb1 — `feat: add flag-off WS2816 Lever-2 emit backend`

| File | Hunk | Guarded by | Affects default path |
|---|---|---|---|
| `system/globals.h` | `@@ -481` `inline CRGB *ws2816_wire;` | `#ifdef K1_WS2816_LEVER2_V1` | N |
| `visual/k1_lever2_emit.h` | whole file (new, 58 L) | only `#include`d inside `#ifdef` | N |
| `visual/ws2816_pack.h` | whole file (new, 60 L) | ditto | N |
| `visual/led_utilities.h` | `@@ -27` `#include "k1_lever2_emit.h"` | `#ifdef K1_WS2816_LEVER2_V1` | N |
| `visual/led_utilities.h` | `@@ -987` `#ifndef K1_INCANDESCENT_OUTPUT_V1` → `#if !defined(K1_INCANDESCENT_OUTPUT_V1) && !defined(K1_WS2816_LEVER2_V1)` | preprocessor condition itself | **N** — with `K1_WS2816_LEVER2_V1` undefined the added conjunct is `true`, so the expression is logically identical to the original `#ifndef`. Inert by construction. |
| `visual/led_utilities.h` | `@@ -1077` +21 L WS2816 pack + early `return` in `show_leds()` | `#ifdef K1_WS2816_LEVER2_V1` | N |
| `visual/led_utilities.h` | `@@ -1245` +18 L alternate `FastLED.addLeds` init + early `return` in `init_leds()` | `#ifdef K1_WS2816_LEVER2_V1` | N |
| `platformio.ini` | new `[env:k1_ws2816_lever2]` (later renamed to `k1_main_rpl_im69d`) | new section only | N — `k1_hardware` body untouched |

`led_utilities.h` (the +44 shared-render file) is clean: **zero unguarded lines**.

### 810846bc — `feat: add Palette HD V2 range expansion behind the Lever-2 eval flag`

| File | Hunk | Guarded by | Affects default path |
|---|---|---|---|
| `serial/serial_typed_cmd_table.def` | `@@ -59` `palette_hd` row | `#ifdef K1_PALETTE_HD_V2` | N |
| `serial/serial_typed_dispatch.cpp` | `@@ -34` include; `@@ -149` `serial_typed_wrap_palette_hd()` | `#ifdef K1_PALETTE_HD_V2` | N |
| `serial/serial_typed_dispatch.h` | `@@ -42` prototype | `#ifdef K1_PALETTE_HD_V2` | N |
| `visual/lightshow_modes.h` | `@@ -5` include | `#ifdef K1_PALETTE_HD_V2` | N |
| `visual/lightshow_modes.h` | `@@ -244` +24 L HD-V2 sample + early `return clamp_crgb16(hd_color)` in the palette sampler | `#ifdef K1_PALETTE_HD_V2` (and a second runtime gate `k1_palette_hd_v2_runtime_enabled`) | N |
| `visual/PalettesHD_RangeV2.{cpp,h}` | new (384 L) | `.cpp` added only via `build_src_filter` inside the eval env | N |
| `platformio.ini` | `+build_src_filter`, `-DK1_PALETTE_HD_V2` inside the eval env | new section only | N |
| `scripts/regression-harness/k1_serial_safety.py` | blob SHA + `palette_hd` allowlist | host tool | N |

`lightshow_modes.h` (the +27 shared-render file) is clean: **zero unguarded lines**.

**HEAD check:** `grep -n "K1_PALETTE_HD_V2\|K1_WS2816_LEVER2_V1" platformio.ini` returns **one** line — `299: -DK1_WS2816_LEVER2_V1`. `K1_PALETTE_HD_V2` is defined in **no env at HEAD**, so `PalettesHD_RangeV2.*` is dead on every unit including the RPL. Brief assumption confirmed.

### 25bec114 — `feat: coerce complementary+mirror EdgeMixer pairs to split` — **THE LEAK**

| File | Hunk | Guarded by | Affects default path |
|---|---|---|---|
| `director/k1_edgemixer.cpp` | `@@ -872` +10 L coercion block in `k1_edgemixer_set_config()` | **NOTHING** | **Y** |
| `director/k1_edgemixer.h` | `@@ -99` comment only | n/a | N |
| `serial/serial_cmd_handlers.cpp` | 3× rename `k1_edge_warn_if_collapsed` → `k1_edge_echo_if_coerced` | none | Y (serial text only) |
| `serial/serial_menu.h` | prototype rename | none | N |
| `serial/serial_menu.cpp` | `@@ -261` warn→echo rewrite | none | Y (serial text only) |
| `serial/serial_menu.cpp` | `@@ -356` `serial_edge_cycle_dual()` — `'y'` hotkey now **skips MIRROR** when mode is complementary; prints the *stored* dual instead of the *requested* one | none | **Y** (operator-visible hotkey behaviour) |
| `serial/serial_menu.cpp` | `@@ -2158` help text | none | N |

Decisive unguarded hunk, verbatim (`SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp:874-882`):

```cpp
  // Complementary rotation is fixed θ = π. Mirror applies +θ / −θ, and
  // cos(π) = cos(−π) with sin(π) = sin(−π) = 0, so both strips bake the
  // same matrix (zero edge separation while EDGE_DUAL still says mirror).
  // Coerce to SPLIT: complementary colour stays, both edges stay active,
  // separation becomes ±π/2. REVERT = delete this block.
  if (next.mode == K1_EDGE_MIXER_COMPLEMENTARY &&
      next.dualEdge == K1_EDGE_DUAL_MIRROR) {
    next.dualEdge = K1_EDGE_DUAL_SPLIT;
  }
```

No `#ifdef` anywhere in `k1_edgemixer_set_config()`. `K1_EDGE_PALETTE_HONOUR_V1` does not gate it either. It compiles into **every** env.

## 2. Reachability of the leak (is it dead code in practice?)

It is **not** dead. `k1_edgemixer_set_config()` has 20 call sites, including:

- `SPECTRASYNQ_K1_FIRMWARE.ino:702` — `k1_edgemixer_set_config(k1_edgemixer_config())`, a boot-time re-normalise pass. A persisted complementary+mirror pair is coerced **at boot**.
- `control/k1_control_facade.cpp:232` and `serial/serial_menu.cpp:1040` — the scene appliers. Both read the current config first (`K1EdgeMixerConfig edge = k1_edgemixer_config();`) and then set only `enabled` / `mode` / `strength`. **`dualEdge` carries forward.** Scenes `l1`/`accent` and `auto`/`autonomy`/`demo` set `edge.mode = K1_EDGE_MIXER_COMPLEMENTARY`. So: unit currently in MIRROR + operator/Tab5 selects scene `l1` or `auto` → complementary+mirror → **coerced to SPLIT**.
- `control/k1_show_state.cpp:176` — show/preset restore.
- 7 serial-hotkey helpers in `serial_menu.cpp`.

## 3. Quantifying the brightness relevance of the leak

Asked in the brief: does it change the number of lit LEDs, or per-channel content in a way that changes apparent brightness?

**Lit-LED count: UNCHANGED.** `primary_active = (next.dualEdge != K1_EDGE_DUAL_ONE_SIDED)` is `true` for both MIRROR and SPLIT. Both edges were active before and are active after. No strip is switched on or off.

**Per-channel content: CHANGED (hue angle only).**
- Before: MIRROR → `sec_factor = +1.0`, `pri_factor = -1.0`, and complementary fixes `theta = π`. `cos(π) = cos(−π)`, `sin(π) = sin(−π) = 0` → both strips bake the *identical* matrix.
- After: SPLIT → `sec_factor = +0.5`, `pri_factor = -0.5` → strips bake `+π/2` and `−π/2` matrices (two different hues).

**Apparent brightness: sum-invariant by construction.** In `k1_edge_recompute_matrix()` (`k1_edgemixer.cpp:214-231`) the rotation matrix is
`mat[0]=mat[4]=mat[8]=cosT+third`, off-diagonals `third∓sinTerm`, with `third=(1−cosT)/3`.
Every row and every column sums to `cosT + 3·third = cosT + (1−cosT) = 1`, **for any θ**. The desaturation matrix (`k1_edgemixer.cpp:239-243`) also has unit row sums (`satRetain + inv·(0.299+0.587+0.114) = satRetain + inv = 1`), and the product of two unit-row-sum matrices has unit row sums. Therefore **R+G+B per pixel is identical pre-clamp at θ=π and at θ=±π/2.** `satRetain` (217/255 for complementary) is explicitly *not* scaled by `angleFactor`, so desaturation is identical too.

Residual, and the only brightness-relevant channel: both matrices carry **negative** coefficients (θ=π → `−1/3`; θ=π/2 → `−0.244`), and `k1_edge_mix()` clamps through `k1_edge_clamp01()`. Clamping is what breaks exact sum invariance, and it bites differently at the two angles. Magnitude is bounded by the coefficient difference (−0.333 vs −0.244) applied at `strength` 0.350 (scene `l1`) or 0.650 (scene `auto`), further reduced by the centre-mask unless `spatialUniform`.

**Token scan (brief item 5).** `git show 25bec114 -- 'SPECTRASYNQ_K1_FIRMWARE/*' | grep -iE 'PHOTONS|brightness|nscale|scale|254|255|65535|incandescent|silent_scale'` on added lines returns **zero hits**. There is no gain, scale, or photon-budget change anywhere in this commit.

**Conclusion:** the leak changes *which hue lands on which edge*, not how much light comes out. It is a real unguarded shared-code behaviour change that hit both units together, but it is **not** a plausible cause of a brightness/degamma differential.

## 4. `platformio.ini` env flags at HEAD

| Env | `extends` | Lever-2 / Palette-HD flags |
|---|---|---|
| `k1_hardware` | — | none |
| `k1_main_rpl_im69d` | `env:k1_hardware` | `-DK1_WS2816_LEVER2_V1` |
| `k1_bench_im69d` | `env:k1_bench_reference` | none |
| `k1_ws2816_lever2` | — | section no longer exists (renamed) |

`k1_hardware` gained nothing. Brief's stated assumption confirmed on both counts.

**Flagged-path note (RPL only, not a default-path leak but brightness-relevant):** under `K1_WS2816_LEVER2_V1` the in-place `INCANDESCENT_FILTER` apply in `show_leds()` is **skipped** (`led_utilities.h:990`) and re-applied instead as a per-channel multiplier inside `k1_lever2_pack_frame()`, together with an integer Q16 power limiter against `budget_proxy = LED_COUNT * 3 * 65535`. That is a genuine RPL-vs-bench emit-path difference in the gain chain — it is correctly flag-isolated, but it is the RPL-only differential the parent lane is looking for.

## 5. Isolation-test verdict — the tests do NOT prove what their names claim

```
python3 -m pytest tests/test_lever2_flag_isolation_static.py tests/test_lever2_no_effect_retune_static.py -q
→ 6 passed in 0.04s
```

Green, but read the assertions:

- **`test_lever2_flag_isolation_static.py` (4 tests) never opens a single `.cpp` or `.h` file.** It parses `platformio.ini` env sections and `k1_device_identities.json` only. It asserts: `default_envs == k1_hardware`; `k1_main_rpl_im69d` exists, extends `k1_hardware`, has `K1_WS2816_LEVER2_V1`, lacks `K1_PALETTE_HD_V2`; the three shippable envs carry neither flag; `k1_ws2816_lever2` is gone from the manifest. **It would stay green against an arbitrarily large unguarded change to shared firmware source.** It is a *build-flag* ratchet mis-named as a *flag-isolation* ratchet. It did not, and structurally cannot, catch `25bec114`.
- **`test_forbidden_effect_files_untouched` is VACUOUS.** It runs `git diff --name-only HEAD -- <20 effect files>` — i.e. **working tree vs HEAD**. Once a retune is committed it is inside `HEAD` and the diff is empty forever. Verified: the exact command the test runs returns `''` right now. It can only ever fail on *uncommitted* edits; it survives deleting the feature entirely. It should diff against the branch point (e.g. `git diff --name-only $(git merge-base origin/main HEAD) HEAD -- …`).
- **`test_waveform_fast_hsv_call_count_frozen` is the one real assertion** in the pair — it counts 4 live `hsv(` call sites in `light_mode_waveform_fast.cpp` and can genuinely go red.

## Re-run commands

Decisive unguarded hunk:
```
git show 25bec114 -- SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp
```
Guard proof for the other two:
```
git show 07987bb1 -- SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h SPECTRASYNQ_K1_FIRMWARE/system/globals.h
git show 810846bc -- SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h
```
Env flags:
```
grep -n "K1_PALETTE_HD_V2\|K1_WS2816_LEVER2_V1" platformio.ini
```
Vacuous-test proof:
```
git diff --name-only HEAD -- SPECTRASYNQ_K1_FIRMWARE/effects/
python3 -m pytest tests/test_lever2_flag_isolation_static.py tests/test_lever2_no_effect_retune_static.py -q
```

## 6. Config-writer hunt — who wrote a device knob and never restored it?

**None of the three audited commits introduces a device-writing script.**

- `07987bb1` added `tests/lever2_host.py` + 5 test files — all host-only, no `serial`, no port.
- `810846bc` touched `scripts/regression-harness/k1_serial_safety.py` — a blob-SHA ratchet and command allowlist. It reads and asserts; it does not open a port.
- `25bec114` added `docs/forensics/runtime-evidence/20260817T-g2g3-e2e-ab-b489/evaluate_e2e_ab.py` — grep for `Serial|write(|mood|chroma|incandescent|base_coat|/dev/cu` returns **zero matches**. It is an offline evaluator over already-captured logs.

**The lane's `RESTORE.json` restores the ENV, not the CONFIG.** `.../20260817T-g2g3-e2e-ab-b489/RESTORE.json` records `restored_env`, `git`, `epoch`, `port`, `usb_serial`, `chip_id`, `f887_flashed`, `port_1101_flashed`, `start_noise_cal`. Every field is about **which firmware is on the device**. Not one field records a config knob value before or after. So for that A/B lane there is **no config snapshot/restore pair at all** — only a firmware-identity restore that *looks* like one.

**Repo-wide writer census.** Enumerating every `.py` under `scripts/`, `tools/`, `tests/` that opens a serial port and sends a knob-write command:

| Script | Knob writes | Restore? |
|---|---|---|
| `scripts/regression-harness/colour_baseline_capture.py` | `chromagram_range=60`, `sensitivity=2.40`, `chroma=0.05`, `mood=0.05`, `sweet_spot_min=<ssl>`, `edge_enabled=off` | **NO** |
| `scripts/regression-harness/k1_trace_capture.py` | `:mood=0.250`, `:palette_index=29`, `:palette_mode=on`, `:edge_enabled=on`, `:edge_mode=complementary`, `:edge_strength=0.350` | **NO** |
| `scripts/regression-harness/device_stm_telem_soak.py` | `:edge_enabled=on`, `:edge_mode=stm_dual`, `:edge_strength=…` | NO (edge only) |
| `scripts/regression-harness/smart_edge_runtime_capture.py` | same set as `k1_trace_capture.py` | **YES** — `restore_safe_runtime_state()` at `:105`, called `:188`, `:241` |
| `k1_paired_snappiness_capture.py`, `k1_phase345_runtime_proof.py`, `vpab_frame_capture.py`, `wireless_ab_bench.py`, `scripts/agent/k1_authored_silicon_proof.py` | `set_mode` only | YES |

Two named offenders:

1. **`scripts/regression-harness/colour_baseline_capture.py:110-115`** — the exact documented scar shape, and it writes **`chromagram_range`** by name:
```python
        leg.cmd_expect("chromagram_range=60", "CHROMAGRAM_RANGE: 60")
        leg.cmd_expect("sensitivity=2.40", "SENSITIVITY")
        leg.cmd_expect("chroma=0.05", "CHROMA")
        leg.cmd_expect("mood=0.05", "MOOD")
        leg.cmd_expect(f"sweet_spot_min={args.ssl}", "SWEET_SPOT")
```
   No `restore`, `snapshot`, `save_config` or `:dump` appears anywhere in the file. Note the file *does* label its one deliberate temporary write as "runtime-only" (`--edge-off`), which shows the author knew the distinction and did not apply it to the five knob writes.

2. **`scripts/regression-harness/k1_trace_capture.py:78`** — writes `:mood=0.250` plus palette and edge state, no restore. Its near-identical sibling `smart_edge_runtime_capture.py` writes the same set and **does** restore, so this is the un-restored fork of a script that already knows better.

**These writes PERSIST.** Every one of those knob handlers calls `save_config_delayed()` inside its branch in `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp` — verified for `photons` (`:116`), `chroma` (`:130`), `mood` (`:144`), `sensitivity` (`:274`), `sweet_spot_min` (`:326`), `chromagram_range` (`:356`), `incandescent_filter` (`:441`). A serial knob write is an NVS write. An unrestored harness write survives power cycles and reflashes until something overwrites it. That is the whole mechanism of the CHROMAGRAM_RANGE scar, still live in two scripts.

**But no repo script explains the bench's values.** No script in the repo writes `incandescent_filter` or `base_coat_intensity` to a device at all, and no script writes `chroma=0.100` or `mood=0.000`. The two offenders write `chroma=0.05` / `mood=0.05` / `mood=0.250` — none of which is on either unit now. So the bench's current state was **not** produced by any harness in this tree; the remaining candidates are hand tuning via encoder / serial hotkey / Tab5-BLE, or a script outside this repo.

## 7. Factory defaults — and the finding that inverts the framing

**Q: did anything change the factory defaults?** Commits touching `system/globals_config.cpp` or `system/config_types.h` since 2026-08-14: `1be4930a`, `573206c0`, `5fb237ae`, `31668e16` (all 2026-08-18, Main-RPL lane). **None of the three audited commits touches either file.**

Scanning every added/removed line in those diffs for `CHROMA|INCANDESCENT|BASE_COAT|MOOD|PHOTONS|SATURATION|SQUARE_ITER|LED_COUNT|LED_TYPE|MIRROR|BACKDROP|PALETTE|LIGHTSHOW_MODE|SENSITIVITY|REVERSE|BRIGHT` yields exactly **one** changed default — `LED_TYPE`, and it is guarded (`globals_config.cpp:60-64`):

```cpp
#ifdef K1_MAIN_RPL_PINMAP_V1
  LED_NEOPIXEL_X2,     // LED_TYPE — Main RPL: DIN-A leds 1-80, DIN-B leds 81-160
#else
  LED_NEOPIXEL,        // LED_TYPE
#endif
```

RPL-only by design, a topology field, not a look field. **No look-affecting factory default changed.**

**The decisive comparison.** Current factory defaults (`globals_config.cpp:48-92`):

| Field | Factory default | Main RPL live | Bench live |
|---|---|---|---|
| `PHOTONS` | `1.00` | 1.000000 | 1.000000 |
| `CHROMA` | `0.00` | **0.000 = default** | 0.100 |
| `MOOD` | `0.05` | **0.050 = default** | 0.000 |
| `INCANDESCENT_FILTER` | `0.00` | **0.00 = default** | 0.50 |
| `BASE_COAT_INTENSITY` | `0.00` | **0.000 = default** | 0.050 |

All four of the Main RPL's differing values are **exactly the shipped factory defaults**. All four of the bench's deviate from them.

**This inverts the hunt.** The question is not "what poisoned the RPL" — the RPL is unpoisoned, it is a freshly-provisioned unit running defaults. The written state is on the **bench**, and it is the reference the comparison was made against. A default-vs-tuned comparison was read as a hardware or code regression.

## Method risk

The reachability argument for the leak (§2) rests on static call-graph reading, not on a device capture: I have not observed a unit actually holding `dualEdge == MIRROR` with `mode == COMPLEMENTARY`. If neither unit has ever been put into MIRROR, the coercion never fires and `25bec114` is inert in practice despite being unguarded in source. The cheapest refutation is `:dump` / `k1_print_edge_status()` on each unit reading back `EDGE_DUAL`. The brightness argument (§3) is derived from the matrix algebra, not measured at the LED output; clamping interaction is bounded but not numerically simulated.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:T2-leak-audit | Created — hunk-by-hunk default-path leak audit of 07987bb1 / 810846bc / 25bec114; identified the unguarded EdgeMixer coercion and the two defective isolation tests. |
