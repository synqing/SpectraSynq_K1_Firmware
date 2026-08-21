# K1 Look Library — full design

**Status:** Proposed (not on silicon, not approved)  
**Date:** 2026-08-21  
**Deciders:** Captain  
**Visual authority:** [`docs/research/k1-runtime-lut-look-library-SPEC.html`](../../research/k1-runtime-lut-look-library-SPEC.html)  
**Educational precursor:** [`docs/research/k1-runtime-lut-look-library.html`](../../research/k1-runtime-lut-look-library.html)

This document is the implementation contract for the entire look-library possibility space. Phases A–D are scheduled so later machines do not break the Phase A ABI. Nothing here is firmware until Captain GO.

---

## 1. One sentence

A look is a typed `RGB u16 → RGB u16` print applied on Core 1 after incandescent mix and before the 48-bit pack (Lever-2) or before 8-bit quantize (bench stub). Slot 0 is identity. Switching slots is a pointer publish at a frame boundary. Palettes stay the paint.

## 2. Problem this solves

Tonight’s `K1_WS2816_DEGAMMA_V1` is a build-time religion: one generated 1D curve, always on, RPL only. The bench cannot match it. Revert requires a flash. A library makes that curve slot 1, last-night Lever-2 slot 0, and leaves room for per-channel trim, 3×4 matrices, authored 3D cubes, measured LGP prints, and later Tab5/LittleFS load — without a second `#ifdef` per look.

S9 (2026-08-18) already proved the “8-bit path has gamma, Lever-2 does not” premise is false (`ENABLE_OUTPUT_GAMMA 0`). The library does not re-litigate that. Degamma is an optional print, not a missing restore.

## 3. Non-goals

- Not a palette remaster. Not Palette HD V2.
- Not an HSV runtime lens (forbidden for milk-fix).
- Not a replacement for incandescent mix, vivid, honour, or EdgeMixer.
- Not a noise-cal analogue. Looks are not learned from silence.
- Not I2S/LCD_CAM emit. PARKED.
- Not `k1_hardware` / F887 until a named production flash.
- Not applying a WS2816 print to WS2812B and calling it matched.

## 4. Possibility space (every axis)

| Axis | Values the architecture admits | Phase that may use them |
|---|---|---|
| Machine type | Identity fn · shared 1D · RGB 1D · 3×4 matrix · 3D cube · 1D-shaper+3D | A: first three. B: matrix. C: 17³. D: shaper+33³ |
| Node count | 256 (1D) · 17³ · 33³ | 65³ forbidden in SRAM |
| Domain | u16 after `sq_to_u16`, pre-pack | Never packed wire, never SQ15x16 in place |
| Interpolation | Linear (1D) · trilinear (3D) · tetrahedral (optional C+) | A: linear |
| Dual DIN | Shared slot · independent `secondary_look` | A: both commands, default inherit |
| Switch | Atomic · NVS persist · optional crossfade | A: atomic+persist. C: crossfade |
| Load | Compiled PROGMEM · LittleFS `/look/NN.klut` · serial blob · Tab5 WS | A: compiled only |
| Authorship | Generated (formula) · authored (file) · measured (chart) | A: generated identity + degamma. D: measured |
| Target env | `k1_main_rpl_im69d` first · bench stub identity · `k1_hardware` later | A: RPL only |
| Boot default | Slot 0 identity | Locked. Tonight’s plate is `:look=1` |

## 5. Locked decisions

1. **Flag** `K1_LOOK_LIB_V1`. First env: `k1_main_rpl_im69d` only. Isolation test: `k1_hardware` and `k1_bench_im69d` do not define it.
2. **Absorb** `K1_WS2816_DEGAMMA_V1`. When the library is on, that `#ifdef` is not a second path. Its table becomes compiled slot 1. Isolation tests update: degamma flag may remain as a *table generator* guard inside the look unit, not as a packer `#ifdef`.
3. **Insert** inside `k1_lever2_sq_to_u16` (or a renamed `k1_look_apply_u16` called from that site): after SQ→u16, after the Q16 limiter scale, before `ws2816_pack_pixel`. Same site, both primary and secondary pack calls.
4. **Limiter stays pre-look.** `budget_proxy` is still `n*3*65535` (identity today). Look may brighten the plate. Do not re-limit after the print in Phase A.
5. **Slot 0** is a function `return ch`, not a 256-entry ramp. No lerp dust.
6. **Boot** `CONFIG.LOOK = 0`, `CONFIG.SECONDARY_LOOK = 255` (inherit). Persist like `palette_index`.
7. **Switch** on Core 1 at the start of `k1_lever2_pack_frame` only. Serial/Tab5 write a `volatile uint8_t`. No mutex on the audio core. No mid-pixel swap.
8. **8-bit path** (`quantize_color`): when the flag is off, nothing changes. When someone later enables the library on a WS2812B env, apply is identity until an authored WS2812B look exists. Never ship the WS2816 degamma table onto B489 as a “match.”
9. **Max compiled slots Phase A:** 4. Max ABI slots: 16 (`0..15`). Loadable slots `8..15` reserved, unused until Phase B.
10. **File magic** `K1LT` (0x4B314C54), little-endian, CRC-32 of payload, version 1. Unknown type → refuse load, keep previous slot.
11. **No look IO on Core 0.** LittleFS open stays on the serial/loop core (existing heap-precondition law).

## 6. Type tags (ABI, do not renumber)

| `type` | Name | Payload | Phase |
|---:|---|---|---|
| 0 | `LOOK_IDENTITY` | empty | A |
| 1 | `LOOK_SHARED_1D_256` | 256 × u16 y-nodes, x implicit `i*257` **or** cube-spaced x+y as tonight | A |
| 2 | `LOOK_RGB_1D_256` | 3 × 256 × u16 | A |
| 3 | `LOOK_MATRIX_3x4` | 12 × i32 Q16 (3×3 + offset) | B |
| 4 | `LOOK_CUBE_17` | 17³ × 3 × u16 | C |
| 5 | `LOOK_CUBE_33` | 33³ × 3 × u16, PSRAM only | D |
| 6 | `LOOK_SHAPER_CUBE` | shared 1D + cube 17 | D |
| 7–15 | reserved | refuse | — |

Tonight’s degamma table (cube-spaced x[], y[], γ=2.2) is a legal `type=1` payload. Do not regenerate it as a uniform 256-node LUT (S9: 1493-code dark error).

## 7. Binary `.klut` (Phase B+)

```
offset  size  field
0       4     magic 'K1LT'
4       2     version (=1)
6       1     type (table above)
7       1     flags (bit0 = cube-spaced 1D abscissa present)
8       2     node_n (256 / 17 / 33)
10      2     reserved 0
12      4     payload_bytes
16      4     crc32(payload)
20      *     payload
```

Identity is never a file. Slot 0 cannot be overwritten.

## 8. Runtime objects

```
struct K1LookSlot {
  uint8_t type;
  const void *payload;   // PROGMEM or PSRAM, never packed wire
};

K1LookSlot k1_look_table[16];          // [0] type=IDENTITY, payload=null
volatile uint8_t k1_look_slot;         // 0..15
volatile uint8_t k1_look_slot_sec;     // 255 = inherit
```

`k1_look_apply_u16(r,g,b, slot) -> (r,g,b)` is the only hot call. Packer uses primary slot on DIN-A and `slot_sec==255 ? slot : slot_sec` on DIN-B.

## 9. Serial / Tab5 surface

| Command | Phase | Persist | Notes |
|---|---|---|---|
| `:look=N` | A | yes | N 0..15, unknown empty slot → NACK, stay |
| `:secondary_look=N` | A | yes | 255 inherit |
| `:look_status` | A | no | prints slot, type name, env, crc |
| `:look_load=N` | B | file | N 8..15 only, then wait for blob |
| `:look_clear=N` | B | file | N 8..15, revert that slot to empty |
| Tab5 wheel | B | via `:look=` | no new protocol until WS already used for palette |

Regen `serial_typed_cmd_table.def` + `k1_serial_safety` SHA. `CMD_PERSISTS` on the two selectors. Load is `CMD_DISRUPTIVE`, loop-core only.

## 10. Compiled Phase A roster

| Slot | Name | Type | Why |
|---:|---|---|---|
| 0 | Identity | 0 | Last-night Lever-2 / flag-off |
| 1 | Degamma 2.2 | 1 | Tonight’s table, now optional |
| 2 | Tungsten trim | 2 | Proves per-channel ≠ shared 1D |
| 3 | Reserved measured | 0 until file | Do not invent a film grade |

## 11. Interaction with existing machinery

| Existing | Relationship |
|---|---|
| Palettes / `:palette_index=` | Unchanged. Paint. Look is print. |
| `K1_EDGE_PALETTE_HONOUR_V1` | Unchanged. Runs before look. |
| Vivid / chroma / photons | Unchanged. Upstream. |
| Incandescent mix | Unchanged. Immediately before look. |
| Q16 limiter | Pre-look. Currently no-op. |
| `ENABLE_OUTPUT_GAMMA` | Stays 0. Not re-enabled. |
| Intro on `led_thread` | Uses `show_leds` → current look. Identity intro = classic bounce. |
| Preset / show-state LittleFS | Store look indices next to palette indices. Not the blobs. |
| I2S LED probe | PARKED. Look lib does not enable it. |

## 12. Threads, timing, memory

- Hot path: Core 1 only. Cost Phase A: 160×2 DINs × 3 channels × one lerp ≈ noise versus pack+show.
- Phase C 17³ trilinear: still Core 1; measure before promoting. If pack+look+show exceeds the VP budget, 3D stays off the default slot.
- SRAM: Phase A tables < 4 KB PROGMEM. Phase C 17³ = 29 478 B (flash or PSRAM). Phase D 33³ = 215 622 B PSRAM only.
- Audio core: zero new work. Freeze-guard / TWDT unchanged. Intro still runs before TWDT subscribe.

## 13. Failure law

| Event | Action |
|---|---|
| `:look=` empty/reserved slot | NACK, keep previous |
| CRC fail on load | Refuse, keep previous, serial reason |
| Unknown type | Refuse |
| Flag compiled out | Commands absent (typed table `#ifdef`) |
| PSRAM alloc fail (D) | Slot stays empty |
| Crash / brownout | Boot slot 0 unless NVS says otherwise; NVS is an index, not a blob |

## 14. Tests (host, before any flash)

- Isolation: look flag only on named env; `k1_hardware` has neither look nor a packer `#ifdef` degamma path.
- Identity: `apply(v, 0) == v` for all 65536 × 3.
- Slot 1 bit-identical to current `k1_ws2816_degamma_u16`.
- Slot 2: unequal channels; a grey in does not stay grey (WB proof).
- Switch: two-frame host replica, pointer change visible on frame N+1 only.
- Serial regen / safety blob.
- No Core-0 include of look apply.
- 8-bit env: look symbols absent or identity-only.

## 15. Forbidden (do not “just add”)

- Mid-frame or Core-0 apply.
- Look after pack / `nscale8` on wire bytes.
- Uniform 256-node 1D for γ-like curves (S9 dark crush).
- Runtime HSV “make it richer.”
- Uploading a 65³ cube into SRAM.
- Treating look as calibration.
- Flashing B489 or F887 with this env.
- Enabling I2S LED to “get more bits for the LUT.”
- Crossfading by mixing packed bytes.

## 16. Phases (full breadth, one ABI)

**A — compiled library (first GO).** Flag, slot 0–3, `:look=` / `:secondary_look=` / `:look_status`, absorb degamma, host tests, RPL flash. Default slot 0. Captain A/B 0 vs 1 vs bench.

**B — loadable slots.** `.klut` LittleFS, `:look_load=`, Tab5 send. Still no 3D required.

**C — 3D 17³.** Type 4, trilinear, one authored or generated split-look for proof, not default.

**D — measured LGP + 33³ / shaper.** Optical chart of this plate + this silicon. Slot 3 filled from measurement. Only then is “match the bench” a measurement problem rather than a curve argument.

## 17. Ship stamps

**Already on silicon:** `445c79ce` / `k1_main_rpl_im69d` on `9087A500` with compiled degamma always-on. Intro on Core 1. No look library.

**This spec shipped (docs only) when:** the HTML + this file exist. Not firmware.

**Phase A on silicon when:** `IDENTITY OK: git=<sha> env=k1_main_rpl_im69d` and `:look_status` reports `slot=0 type=IDENTITY` at boot, `:look=1` reproduces tonight’s plate, `:look=0` reproduces last night. No `start_noise_cal`.

**Who:** Captain approves this spec (or amends locked rows) → agent implements A → Captain flash GO for 1401 only → Captain eyes-on 0 vs 1 vs bench.

---

*Approve, amend a locked row, or reject. Do not implement on silence.*
