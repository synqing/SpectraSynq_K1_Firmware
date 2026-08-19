---
abstract: "S9 design review of the proposed K1_WS2816_DEGAMMA_V1 inverse-gamma stage in k1_lever2_pack_frame. Verdict: implementable, but the 256-entry uniform LUT+lerp is numerically unfit (worst error 1493 codes = 5.8 LSB of an 8-bit-effective scale, ALL of it in v<257 where the darks live); the repo already disabled output gamma in 2026-05 (ENABLE_OUTPUT_GAMMA 0) as a washout suspect, so the 'de-gamma is missing vs the 8-bit path' premise is FALSE; and the secondary strip on Main RPL is WS2816 too, not 8-bit. Read before implementing or flashing."
---

# S9 — Feasibility review of the proposed de-gamma fix (WS2816 Lever-2)

**Scope:** design review only. No firmware edited, no flag added, no flash.
**Conditional:** this review assumes S1–S8 establish a real root cause. It does
not itself assert one.

**Verdict:** the fix is **implementable as a mechanism** but is **wrong as
specified** on four counts. Worst defect: the 256-entry uniform LUT + lerp
resolves the darks so badly that it introduces a visible dark-crush of its own —
every bit of the error lands in the bottom 0.4 % of the domain.

---

## 0. What the code actually does (read before judging)

`SPECTRASYNQ_K1_FIRMWARE/visual/k1_lever2_emit.h:42-58` — `k1_lever2_pack_frame`:

1. `k1_lever2_sq_to_u16(ch, inc)` — SQ15x16 `ch * inc` → u16 via `(raw*65535)>>16`.
2. Sum all `n*3` u16 into `total`.
3. `s = k1_lever2_scale_q16(total, budget_proxy)` — Q16 limiter.
4. Per pixel: `apply_q16(...)` then `ws2816_pack_pixel` → 48-bit GRB wire bytes.

Call sites, both under `#ifdef K1_WS2816_LEVER2_V1`:

- **Primary** `visual/led_utilities.h:1086-1107` (returns before `quantize_color`)
- **Secondary** `visual/led_utilities.h:2600-2620` (returns before the 8-bit path)

Stages preceding the primary call, in order:
`apply_brightness()` (L969) → `render_ui()` → `apply_vivid_precomp_count()` →
`clip_led_values()` → optional ambient floor → `scale_to_strip()` (L944-963,
linear lerp resample only) → incandescent mix folded into `inc_r/g/b` (L1091-1098)
→ **pack**. Nothing between `scale_to_strip` and the pack applies a power curve.

<!-- british-english-guard: ignore — verbatim quotes from constants.h source comments retain their original US spelling -->

**Load-bearing correction to the fix's implied premise.** The 8-bit path's
`apply_gamma8()` is a **pass-through**: `system/constants.h:571` sets
`#define ENABLE_OUTPUT_GAMMA 0`, rolled back 2026-05-20 with the comment
*"SUSPECT #2 for washout. Crushes midtones; firmware color math likely already
perceptually-tuned."* So there is **no gamma asymmetry** between the 8-bit path
and Lever-2 — both are ungamma'd. Any argument of the form "Lever-2 skipped the
gamma the 8-bit path has" is **[FACT] false**. The `// post-gamma` comments
throughout `led_utilities.h` name a stage that is compiled out.

**Second load-bearing finding.** `budget_proxy = LED_COUNT * 3 * 65535`
(L1099-1100, L2613-2614) is the arithmetic **maximum** `total` can reach, so
`total <= budget` always and `s == 65535` on every frame. The Q16 limiter is
currently a **structural no-op**. This matters for §2.

---

## 1. Numerical correctness — the LUT is unfit as specified

256 uniform nodes over `[0, 65535]` ⇒ node spacing 257. `v^(1/2.2)` has infinite
slope at 0, so a straight chord across `[0, 257]` is a catastrophic
approximation exactly where the darks live.

Error of `lerp(LUT_N)` vs exact `65535·(v/65535)^(1/2.2)`, over all 65536 inputs
(`worst` and `RMS` in 16-bit output codes; `eff-8b` = worst ÷ 257, i.e. LSBs of
an 8-bit-effective PWM scale):

| N entries | γ | worst (codes) | at v | RMS | eff-8b LSB | bytes (u16) |
|---|---|---|---|---|---|---|
| **256** | 2.2 | **1492.8** | **61** | 68.19 | **5.81** | 512 |
| 512 | 2.2 | 1088.4 | 30 | 35.12 | 4.24 | 1 K |
| 1024 | 2.2 | 793.9 | 15 | 18.10 | 3.09 | 2 K |
| 4096 | 2.2 | 422.3 | 4 | 4.79 | 1.64 | 8 K |
| 16384 | 2.2 | 224.8 | 1 | 1.20 | 0.88 | 32 K |
| 65536 | 2.2 | 0.0 | 0 | 0.00 | 0.00 | 128 K |
| 256 | 2.8 | 3286.1 | 52 | 148.27 | 12.79 | 512 |
| 4096 | 2.8 | 1218.1 | 3 | 13.62 | 4.74 | 8 K |

**Where the error is.** For N=256, γ=2.2, per-segment worst error:

| segment | v range | worst err (codes) | eff-8b LSB |
|---|---|---|---|
| 0 | 0–257 | **1492.8** | 5.81 |
| 1 | 257–514 | 91.5 | 0.36 |
| 2 | 514–771 | 40.3 | 0.16 |
| 3 | 771–1028 | 23.8 | 0.09 |
| 8 | 2056–2313 | 6.0 | 0.02 |
| 32 | 8224–8481 | 0.8 | 0.00 |
| 128 | 32896–33153 | 0.1 | 0.00 |
| 254 | 65278–65535 | 0.0 | 0.00 |

**99.99 % of the total error is in segment 0.** Worked example at the worst
point v=61: exact output ≈ 2740 codes; the chord gives ≈ 1254. The LUT
**undershoots by ~54 %** — a fix intended to lift the darks *crushes them
further* over the first 0.4 % of the domain, and does so with a visible
straight-line ramp (a hard slope discontinuity at v=257) where the true curve is
steepest. On a light-guide plate this is exactly the region that shows banding.

**Minimum entry counts (uniform spacing, computed not estimated):**

- error < **1 LSB of the wire's 16 bits** → **N = 65536**, i.e. a uniform
  LUT+lerp **cannot** reach it below a full 128 KB direct table. Not achievable
  as specified.
- error < **1 LSB of an 8-bit-effective PWM** (257 codes) → **N = 16384**
  (32 KB as u16).
- If the chip's effective PWM is the 4-bit piecewise curve the brief cites, the
  meaningful quantum is far coarser than 1 LSB16 and *any* of these tables would
  pass a naive 1-LSB test **while still being visibly wrong in segment 0** —
  because the defect is a *shape* error concentrated in the darks, not an
  amplitude error spread across the range. Do not gate on max-|err| alone.

**The correct fix is node spacing, not table size.** Same 256 entries, nodes
placed non-uniformly (index the LUT by a cheap monotone warp of `v`):

| node spacing | worst (codes) | eff-8b LSB | RMS |
|---|---|---|---|
| uniform | 1492.8 | 5.81 | 68.19 |
| `x = (k/255)^2 · 65535` (sqrt-spaced) | 32.9 | 0.13 | 0.40 |
| `x = (k/255)^2.2 · 65535` | 23.4 | 0.09 | 0.30 |
| `x = (k/255)^3 · 65535` (cube-spaced) | **2.5** | **0.01** | 0.27 |

Cube-spaced nodes give a **597× reduction in worst-case error at identical table
size**. Recommendation: 256-entry LUT on a cube- or square-spaced index (integer
index derivable from the top bits of a cheap `isqrt`/`icbrt`), **or** a
two-region scheme (dense uniform LUT over `v < 1024`, coarse uniform above).
A runtime `powf` is also viable on the S3 FPU (~480 calls/frame primary +
secondary ≈ 96 k/s, low single-digit % of one core) but is the wrong tool when a
correctly-spaced 512-byte table is exact to 2.5 codes.

**Re-run command (reproduces every number above):**

```
python3 /private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/8554209d-fce0-4e9a-9146-f9e87e83f641/scratchpad/lut_err.py
```

Self-contained equivalent:

```
python3 -c "
import numpy as np
e=lambda v,g:65535.0*np.power(v/65535.0,1.0/g)
v=np.arange(65536,dtype=float)
for name,xs in (('uniform',np.linspace(0,65535,256)),('sqrt',(np.linspace(0,1,256)**2)*65535),('cube',(np.linspace(0,1,256)**3)*65535)):
    a=np.abs(np.interp(v,xs,e(xs,2.2))-e(v,2.2))
    print(name,'worst=%.1f codes at v=%d  RMS=%.2f  eff8b=%.2f'%(a.max(),a.argmax(),np.sqrt((a**2).mean()),a.max()/257))"
```

---

## 2. Domain correctness — insertion point and ordering

**Is the value linear-light at the insertion point?** [INFERENCE, high
confidence] **No — it is already perceptually shaped, at least in part.** Three
stages upstream are non-linear or perceptually motivated: `apply_brightness()`
(PHOTONS curve, `PHOTONS_CURVE_MODE`), `apply_vivid_precomp_count()` (a
chroma/luma vivid pre-compensation explicitly described in `constants.h:574-584`
as a *substitute* for output gamma), and the palettes themselves, which
`visual/Palettes.cpp` documents as *"converted for FastLED with gammas
(2.6, 2.2, 2.5)"* — i.e. the palette tables are **already gamma-encoded**.
Applying `v^(1/2.2)` on top of gamma-encoded palette data double-lightens, which
is the precise failure mode the brief warns about. The 2026-05-20 rollback note
("firmware color math likely already perceptually-tuned") is a prior,
independent statement of the same conclusion.

This does **not** prove the fix is wrong — the WS2816's own chip curve is a real
physical stage downstream of everything the firmware does, and cancelling it is
a coherent goal. But the exponent that cancels *the chip* is not 2.2 by
assumption, and the value entering the pack is **not** linear light, so the
composite transfer function is unknown. **Correct framing: this is a tuning
lever against an uncharacterised chip curve, not a "restore missing gamma" fix.**
Label it as such or it will be defended as a correctness fix when it is a taste
knob.

**BEFORE or AFTER the Q16 limiter?** The spec says only "applied to both
channels", which is ambiguous. The correct order is **de-gamma BEFORE the
limiter**, i.e. the `total` accumulation must sum the *post-de-gamma* values:

- De-gamma **after** `apply_q16` would take a value the limiter just scaled to
  fit a budget and push it back up (`v^(1/2.2) ≥ v` for all `v` in `[0,1]`,
  with up to ~4.4× gain at low `v`), silently voiding the budget. **This is a
  defect if implemented that way.**
- Today it is *masked*: `budget_proxy` is the arithmetic maximum, so `s` is
  always 65535 and the limiter never fires (§0). The bug would be latent, and
  would detonate the first time anyone tightens `budget_proxy` to a real power
  budget — which is the entire point of that parameter existing.
- Also note `k1_lever2_sq_to_u16` is called **twice per channel** (once in the
  accumulate loop L47-49, once in the emit loop L53-55). A de-gamma inserted in
  only one of the two loops produces a limiter that measures a different signal
  than it scales. Insert it inside `k1_lever2_sq_to_u16` (single site, both
  loops consistent) or in both loops identically.

**Recommended insertion point:** `SPECTRASYNQ_K1_FIRMWARE/visual/k1_lever2_emit.h:39`
— the return of `k1_lever2_sq_to_u16`, i.e. `return k1_degamma_u16(v);` under the
flag. One site; both loops; before the limiter; after the incandescent mix.

---

## 3. Channel coverage — "both channels" is wrong on the facts

The canon line *"secondary strip stays 8-bit"* is **stale for this build**. On
Main RPL under `K1_WS2816_LEVER2_V1`, `init_secondary_leds()`
(`led_utilities.h:2492-2513`) allocates `ws2816_wire_secondary` and registers two
`WS2812B ... RGB` controllers over it, and `show_secondary_leds()` (L2600-2619)
calls the **same** `k1_lever2_pack_frame`. The source says so explicitly at
L2495-2497: *"Both Main RPL PCBs are WS2816. Apply the same packer... (skill's
'secondary stays 8-bit' is the single-strip eval default; it does not apply
here)."*

**Correct per-strip policy:**

| path | strip | de-gamma? |
|---|---|---|
| `led_utilities.h:1101` primary, `K1_WS2816_LEVER2_V1` + `K1_MAIN_RPL_PINMAP_V1` | WS2816, 48-bit | **yes** |
| `led_utilities.h:2615` secondary, same flags | WS2816, 48-bit | **yes** |
| `led_utilities.h:2508-2512` `#else` branch — native `WS2816` FastLED controller fed from 8-bit `leds_out_secondary` | WS2816 via FastLED's own path | **no** (not this pack path) |
| any env without the flag → `quantize_color()` → `leds_out` 8-bit WS2812-class | 8-bit | **no** |

Because both call sites share one function, putting the de-gamma inside
`k1_lever2_sq_to_u16` covers both automatically and cannot drift. But note the
ambiguity in the spec is real and must be resolved in writing before coding:
"both channels" could mean primary+secondary **strips** or the R/G/B **channels**
(of which there are three, not two). Neither reading is safely inferable.

---

## 4. Flag and gate mechanics

**Where `-DK1_WS2816_DEGAMMA_V1` goes:** `platformio.ini` `[env:k1_main_rpl_im69d]`
build_flags block only (currently platformio.ini:282-300; the existing
`-DK1_WS2816_LEVER2_V1` is at line 299).

**Envs that must NOT get it.** `tests/test_lever2_flag_isolation_static.py`
already encodes `SHIPPABLE_ENVS = {k1_hardware, k1_prod_im73d, k1_bench_reference}`
and resolves `extends =` transitively. Because `k1_main_rpl_im69d` **extends
`env:k1_hardware`**, the flag must be added to the child env only — it inherits
downward, never upward, so this is safe — but the isolation test does **not**
currently know about `K1_WS2816_DEGAMMA_V1`. **Extend that test with the new flag
name** or the ratchet is blind to it (an indicator that cannot go red).

**Serial-safety obligation: YES, if and only if a runtime-tunable exponent is
added.** Any new `SERIAL_TYPED_CMD` row in
`SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def` changes that file's
git blob SHA, and `tests/test_k1_serial_safety.py::test_recorded_def_blob_shas_are_current`
asserts the recorded SHA in `scripts/regression-harness/k1_serial_safety.py`
matches. Exact steps, before commit:

1. Add the row to `serial/serial_typed_cmd_table.def` (classify it correctly —
   an exponent setter is a **destructive/persisting setter** if it writes CONFIG
   or reboots; it must not land in `SAFE_READONLY_COMMANDS`).
2. Re-derive the command literals in `scripts/regression-harness/k1_serial_safety.py`
   (the module's `TYPED_*` sets) to match a fresh parse of the `.def`.
3. `git hash-object SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def`
   → update `TYPED_DEF_BLOB_SHA` in that module.
4. `python3 -m pytest tests/test_k1_serial_safety.py -q` → must pass.
5. Then the full host gate: `pytest tests/` and `pio run -e k1_main_rpl_im69d`.

**Recommendation: do not add a serial command in the first cut.** A compile-time
`K1_WS2816_DEGAMMA_EXP_X100` (e.g. `220`) selecting a build-time-generated table
keeps the whole change inside one header + one platformio line and avoids the
entire serial-safety surface. Exponent sweeps then cost a reflash, which is the
same cost as the eyes-on A/B anyway.

---

## 5. Test strategy — what a host test can and cannot prove

**It can be falsified on the host, at the artefact boundary.** The machinery
already exists:

- `tests/lever2_host.py` — a Python mirror of `ws2816_pack.h` / `k1_lever2_emit.h`
  (`pack_pixel`, `scale_q16`, `apply_q16`, `pack_frame_u16`).
- `tests/test_lever2_packer_golden.py` — asserts on the **packed wire bytes**
  (walking-bit and boundary goldens). **This is the file to extend.**

Concrete falsifiable host test (extend `test_lever2_packer_golden.py`, or add
`tests/test_lever2_degamma_curve.py` beside it):

1. Mirror the C LUT in `lever2_host.py` — **generated by the same procedure as
   the C table, not hand-copied**, or the mirror encodes your bug (differential
   oracle: two implementations, diffed in emitted order).
2. Feed a known ramp (e.g. `v = 0, 1, 2, 4, …, 65535`, plus a dense sweep of
   segment 0) through `pack_frame_u16` and **reassemble the u16 back out of the
   emitted wire bytes** (`r16 = (wire0[2]<<8) | wire1[0]`, etc.).
3. Assert reassembled `≈ 65535·(v/65535)^(1/γ)` within a stated tolerance in
   codes — and **assert the segment-0 tolerance separately and tightly**, since
   that is where a uniform LUT fails and a mid-range-only tolerance would pass it
   vacuously.
4. Assert **monotonicity** (`out[i] ≥ out[i-1]`) and the endpoints
   (`0→0`, `65535→65535`). A non-monotone or non-anchored curve is a bug class
   a tolerance band alone will not catch.
5. **Fault battery — mandatory.** Include cases expected to go RED and watch them
   go red: (a) the uniform-256 LUT must FAIL the segment-0 tolerance; (b) γ=1.0
   (identity) must FAIL the curve assertion; (c) de-gamma applied only in the
   emit loop and not the accumulate loop must FAIL a limiter-consistency
   assertion under a deliberately tightened `budget_proxy`. Without (a)–(c) the
   suite proves only that you are self-consistent.
6. Extend `tests/test_lever2_emit_header_static.py` and
   `tests/test_lever2_flag_isolation_static.py` for the new flag name.

**What a host test CANNOT prove:** the chip's real optical response. The whole
premise is that the WS2816 applies an unknown 4-bit piecewise curve in hardware;
a host test can only prove *the firmware emits the curve we intended*, never that
*the intended curve is the right one*. Exponent choice is decidable **only** by
side-by-side eyes-on (or an external witness — a camera/luxmeter sweep against a
known ramp, which would be the honest instrument if eyes-on disagrees between
sessions).

---

## 6. Revert and blast radius

**Is it "one -D line"?** **Almost, and only if built that way.** Conditions:

- The LUT table, the de-gamma function, and its call must all sit **inside**
  `#ifdef K1_WS2816_DEGAMMA_V1` in `k1_lever2_emit.h`. `k1_lever2_emit.h` is
  included by `led_utilities.h` (line 33), which compiles in **every** env — a
  table declared outside the ifdef lands in every shippable binary's `.rodata`
  and breaks byte-identity (`scripts/.../mic_stable_byte_gate.sh` compares
  `.dram0.data` / `.iram0.text` / `.iram0.vectors`). Verify with a
  before/after section compare on `k1_hardware`, not by inspection.
- **Files that must also change** (so it is not literally one line):
  `tests/test_lever2_flag_isolation_static.py` (add the flag to the isolation
  ratchet), and the new/extended curve test. Those are test-side and do not
  affect any binary.
- `docs/hardware/device-build-registry.md` deployed-state row for 9087A500 must
  be stamped after the flash (per project rule, not optional).

**Nothing shippable is touched** provided the above holds: `k1_hardware`,
`k1_prod_im73d`, `k1_bench_reference` do not define `K1_WS2816_LEVER2_V1` (per
the existing isolation ratchet) and would not define the new flag. The device
target `9087A500` / `k1_main_rpl_im69d` is correct per
`scripts/platformio/k1_device_identities.json` (Main RPL, advisory port
`/dev/tty.usbmodem1401`).

---

## 7. Ranked defect list — the fix AS SPECIFIED

1. **[BLOCKER] 256-entry uniform LUT + lerp is numerically unfit.** Worst error
   1493 codes (5.81 LSB of an 8-bit-effective scale) at v=61, ~54 % undershoot,
   with 99.99 % of all error inside `v < 257` — the darks the fix exists to
   lift. Introduces a visible slope discontinuity at v=257. Fix: non-uniform
   node spacing (cube-spaced 256 entries → worst 2.5 codes, 597× better at the
   same size), or ≥16384 uniform entries (32 KB) for < 1 eff-8-bit LSB. A
   uniform LUT can **never** reach < 1 LSB16 below a full 128 KB table.
2. **[BLOCKER] The stated premise is false: there is no missing gamma to
   restore.** `ENABLE_OUTPUT_GAMMA 0` (`system/constants.h:571`) makes
   `apply_gamma8()` a pass-through on the 8-bit path too, rolled back
   2026-05-20 as a washout suspect. The palettes are themselves documented as
   gamma-encoded (`Palettes.cpp`), and `apply_vivid_precomp_count()` is an
   explicit stand-in for output gamma. The insertion point is **not** linear
   light. This must be reframed as a chip-curve tuning lever with an
   uncharacterised target, or it will be defended as a correctness fix it is not.
3. **[MAJOR] Ordering vs the Q16 limiter is unspecified, and one of the two
   readings voids the power budget.** De-gamma after `apply_q16` raises values
   the limiter just capped (up to ~4.4× at low `v`). Currently masked because
   `budget_proxy = LED_COUNT*3*65535` makes the limiter a no-op (`s` always
   65535) — a latent bug that detonates the moment the budget is tightened.
   Also: `k1_lever2_sq_to_u16` is called in **two** loops; applying the curve in
   one and not the other desynchronises the limiter's measurement from its
   action. Fix: apply inside `k1_lever2_sq_to_u16`
   (`visual/k1_lever2_emit.h:39`), before the limiter, one site.
4. **[MAJOR] "Applied to both channels" is ambiguous and the accompanying canon
   is stale.** There are three colour channels and two strips. The canon line
   "secondary strip stays 8-bit" is **false for Main RPL** — the source
   explicitly overrides it (`led_utilities.h:2495-2497`); the secondary is
   WS2816 through the same packer. Correct policy in §3.
5. **[MODERATE] γ = 2.2 is an unjustified first cut.** The brief itself concedes
   the chip's curve is uncharacterised; 2.2 is inherited from sRGB, not from the
   WS2816. Given §2 (input already partly perceptual), the composite exponent
   that is actually wanted is plausibly well below 2.2. Make the exponent a
   **compile-time** constant with a documented sweep plan; a runtime serial
   tunable buys little and drags in the whole serial-safety surface (§4).
6. **[MODERATE] No falsifier is specified.** The plan goes host-gate → flash →
   eyes-on, which cannot distinguish "the curve I emitted is the curve I
   intended" from "the exponent is right". Add the wire-byte curve test with a
   tight segment-0 tolerance **and a fault battery that goes red** (§5). Without
   the red cases the suite is documentation.
7. **[MINOR] The isolation ratchet will not see the new flag.**
   `tests/test_lever2_flag_isolation_static.py` hard-codes `K1_WS2816_LEVER2_V1`
   / `K1_PALETTE_HD_V2`. `K1_WS2816_DEGAMMA_V1` must be added or the gate that
   keeps eval flags off shippable envs is blind to it.
8. **[MINOR] "One -D line to revert" only holds if the table is inside the
   ifdef.** `k1_lever2_emit.h` compiles into every env via `led_utilities.h:33`;
   a table outside the guard breaks byte-identity on shippable builds. Verify by
   section compare, not by reading the diff.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:claude-code (S9) | Created — design review of proposed K1_WS2816_DEGAMMA_V1; LUT error table computed; insertion point, channel policy, flag/gate, test strategy, revert, ranked defects. |
