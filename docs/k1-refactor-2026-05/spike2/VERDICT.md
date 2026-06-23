---
abstract: "Spike #2 verdict: aggregate-init relocation byte-identity proof for the K1 SensoryBridge Phase B refactor. VERDICT = PASS — CONFIG (108B) and a_weight_table (104B) initialiser bytes are byte-identical before/after moving their definitions from globals.h into globals_config.cpp behind extern declarations; CONFIG_DEFAULTS stays BSS/zero-init. The mechanism is SAFE for Rows 3/4 BUT requires a slim-declarations-header + include-hygiene prerequisite: the .ino-only lightshow_modes enum, the FixedPointsCommon include-order defect, and the strings.h POSIX-shadowing ODR trap all surfaced. Read before scheduling Row 3/Row 4 execution."
---

# Spike #2 — Aggregate-Init Relocation Byte-Identity Proof

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Worktree | `/Users/spectrasynq/SensoryBridge-main 9/.claude/worktrees/agent-a0b332d904b690d68` |
| Branch | `worktree-agent-a0b332d904b690d68` (off `feat/pio-core-bump`) |
| Baseline HEAD | `92cfa74` |
| Toolchain | xtensa-esp32s3-elf (gcc 14.2.0), PIO 6.1.19, arduino-esp32 3.2.0, `-O3 -ffast-math` |
| **VERDICT** | **PASS — relocated aggregate-init initialiser bytes are byte-identical.** |

## What was relocated

Definitions moved from `globals.h` into a new translation unit `globals_config.cpp`,
with `extern` declarations left in `globals.h`:

| Object | Size | Section | Role |
|---|---|---|---|
| `conf CONFIG` | `0x6c` (108 B) | `.dram0.data` | factory defaults: PHOTONS / CHROMA / MOOD / LIGHTSHOW_MODE / MIRROR / palette / sample-rate / ... |
| `float a_weight_table[13][2]` | `0x68` (104 B) | `.dram0.data` | A-weighting LUT (mutated at runtime in system.h, so `.data` not `.rodata`) |
| `conf CONFIG_DEFAULTS` | `0x6c` (108 B) | `.dram0.bss` | runtime reset target — zero-init, `memcpy`'d from CONFIG in system.h:333 |
| `set_led_count_from_define()` | — | constructor | `__attribute__((constructor))` pinning `CONFIG.LED_COUNT = LED_COUNT_VALUE` |

The `struct conf` TYPE definition moved to a new slim header `config_types.h` (see below).

## Byte-identity result (the proof)

Per-symbol `objdump -s` over `[VMA, VMA+size)`, comparing payload bytes only
(whole-section VMAs shift legitimately — `a_weight_table` `3fc954dc`→`3fc95518`,
`CONFIG` `3fc95544`→`3fc95580` — and are excluded from the comparison):

```
=== CONFIG ===          BYTE-IDENTICAL (7 payload rows, 108 bytes)
=== a_weight_table ===  BYTE-IDENTICAL (7 payload rows, 104 bytes)
=== CONFIG_DEFAULTS === BSS/zero-init in both builds (no initialiser bytes); same size 0x6c, same section .dram0.bss
```

Spot-decode confirms the defaults are intact: CONFIG bytes `0000803f` = 1.0 (PHOTONS),
`00000000` = 0.0 (CHROMA), `cdcc4c3d` = 0.05 (MOOD), `0001` = LIGHTSHOW_MODE 0
(LIGHT_MODE_GDFT) + MIRROR_ENABLED true. Artifacts: `baseline.symbol-bytes.txt` vs
`after.symbol-bytes.txt` (per-symbol), `*.dram0.data.txt` / `*.flash.rodata.txt`
(full sections), `*.symbols.txt` (nm). Reproduce with `dump.sh`.

## Build results

| Env | Baseline | After | Notes |
|---|---|---|---|
| `k1_hardware` (release, `-O3`) | RAM 83064 / Flash 559314 | RAM 83064 / Flash 559298 | links clean; Flash −16 B from the relocated constructor + inline-var/comment churn, NOT from the data |
| `k1_hardware_harness` | (not built) | RAM 83448 / Flash 581506, links clean | only pre-existing `-Wvolatile` warning at system.h:48 |

## The two failure classes hit en route (findings — required prerequisites for Rows 3/4)

The relocation is NOT a clean lift-and-shift. Three latent single-TU-only defects had
to be resolved to make a second TU link. These are the real cost of the mechanism and
MUST be folded into the Row 3 / Row 4 / Row 7 scope.

### Finding #1 — `.ino`-only `lightshow_modes` enum (Class C include-order)
`enum lightshow_modes { ... NUM_MODES }` was defined INLINE in
`SPECTRASYNQ_K1_FIRMWARE.ino:58`, before `#include "globals.h"`. It is referenced by
`globals.h` (CONFIG init uses `LIGHT_MODE_GDFT`; `mode_names[NUM_MODES*32]`) and by
`led_utilities.h` / `serial_menu.h` / `encoders.h` — all of which compiled ONLY because
the single-TU `.ino` include order placed the enum first. (The comments at `globals.h:12`
and `encoders.h:12` falsely claimed it lived in `constants.h`.) A second TU cannot see it.
**Resolution:** moved `enum lightshow_modes` (+ `enum led_types`, `DEFAULT_SAMPLE_RATE`,
`LED_STRIP_MODE`/`LED_COUNT_VALUE`) into `config_types.h`; `.ino` enum deleted; `constants.h`
includes `config_types.h`. Enumerator order unchanged → `LIGHT_MODE_GDFT==0`, `NUM_MODES==13`.

### Finding #1b — FixedPoints include-order defect
`constants.h` / `globals.h` reference `SQ15x16` but only `#include <FixedPoints.h>`. The
`SQ15x16` alias actually lives in `<FixedPointsCommon.h>` (`SFixedCommon.h:22`). The `.ino`
includes `<FixedPointsCommon.h>` (line 73) before them, so it works single-TU; a fresh TU
sees `'SQ15x16' does not name a type` + cascading `too many initializers for 'CRGB16'`.
This is the same Class-C defect Spike #1 flagged. **Resolution:** the slim `config_types.h`
uses only POD types and pulls in no FixedPoints; the definition TU avoids constants.h/globals.h
entirely (see Finding #2).

### Finding #2 — ODR: header object definitions multiply across TUs
Including `globals.h` from the second TU re-emitted its ~277 non-`extern` globals + free
functions (`vp_perf_*`, `lock_leds`, `palette_owns_colour_source`, the SECONDARY_* block, ...)
→ mass "multiple definition". Falling back to `constants.h` re-emitted ITS header-defined
objects (`incandescent_lookup`, `note_colors`, `hue_lookup`, `notes`, `gamma8_lut`,
`dither_table`). **Resolution:** the definition TU includes ONLY `config_types.h` (the slim
declarations header the matrix §8 Q2 prescribes) — `struct conf` + the ODR-safe enums/macros —
plus `<FastLED.h>` for the `GRB` enumerator. This is exactly the matrix's
"slim declarations header + one compiled definition unit" pattern.

### Finding #2b — `strings.h` shadows POSIX `<strings.h>` (ODR via system include)
`SPECTRASYNQ_K1_FIRMWARE/strings.h` (defines non-`extern` `sharps`, `notes_chromatic`, guarded
only by `#pragma once`) shares a name with the POSIX `<strings.h>`. Some IDF/FastLED system
header does `#include <strings.h>` (strncasecmp/bzero); because the firmware src dir is on the
include path ahead of the system paths, the PROJECT header shadows the system one and is pulled
into the second TU → duplicate objects. **Resolution:** marked the two objects `inline` (C++17
inline variables — single definition, identical bytes). Proper Row 7 fix: rename the header so
it stops shadowing POSIX.

## Recommendation for Phase B (Rows 3/4)

**The "move aggregate-init data to a `.cpp` behind `extern`" mechanism is SAFE — it produces
byte-identical initialiser data — PROVIDED the three prerequisites above are honoured.** No
`constexpr` / designated-init / keep-in-header workaround is required; plain `extern` + a slim
declarations header is sufficient and byte-exact.

Concrete guidance for Row 3 (globals minimal partition) and Row 4 (led_utilities defs→cpp):

1. **Use a slim declarations header, never include the fat header from the definition TU.**
   The definition `.cpp` must NOT `#include "globals.h"` or `#include "constants.h"` — it must
   include only a slim header carrying the TYPES + ODR-safe enums/macros it needs. `config_types.h`
   is the prototype. Row 3's `globals.cpp` will need an analogous slim `globals_decls.h` (extern
   declarations) and the type/enum definitions factored out of the object sea.
2. **Row 2's include-hygiene sub-task (matrix §5) is confirmed mandatory, not optional.** Each
   per-mode `.cpp` will hit Findings #1, #1b, #2b. Budget the FixedPointsCommon include-order fix
   and the `strings.h` rename into Row 4 (the first multi-TU commit), not Row 2.
3. **`strings.h` rename should be pulled forward** from Row 7 (deferred) into the first dual-TU
   commit, OR keep the `inline`-variable fix applied here. The shadowing is a real latent defect
   that bites every future TU.
4. **CONFIG_DEFAULTS needs no special handling** — it is zero-init BSS, memcpy-populated at runtime;
   relocating it is trivially byte-safe.
5. **Verification recipe is reusable:** `dump.sh <tag>` + the VMA-stripped per-symbol diff. Compare
   by symbol (nm address+size → objdump byte range), never by whole-section address.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) [Embedded Firmware Engineer] | Created. Spike #2 verdict = PASS. CONFIG (108B) + a_weight_table (104B) byte-identical after relocation to globals_config.cpp; CONFIG_DEFAULTS stays BSS. Documented 4 latent single-TU defects (lightshow_modes .ino-only enum, FixedPointsCommon include order, header ODR, strings.h POSIX shadow) that the mechanism forces resolution of. Recommendation: mechanism SAFE for Rows 3/4 with slim-declarations-header + include-hygiene prerequisites. |
