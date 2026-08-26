# K1 Look Library — full design

**Status:** Two-track Phase A is the implementation contract.

| Track | Env | Flag | Device |
|---|---|---|---|
| RPL Phase A | `k1_main_rpl_im69d` | `K1_LOOK_LIB_V1` | `9087A500` |
| WS2812 sibling Phase A | `k1_bench_im69d_led150` | `K1_LOOK_LIB_WS2812_V1` | `B489A500` |

Phase B `.klut` file loading is **HOLD** until the on-disk layout in §7 and `k1_look_file.h` are made identical. Later machines still must not break the Phase A ABI.

---

## 1. One sentence

A look is a typed `RGB u16 → RGB u16` print applied on Core 1 after incandescent mix and before the 48-bit pack (Lever-2) or before 8-bit quantize (bench stub). Slot 0 is identity. Switching slots is a pointer publish at a frame boundary. Palettes stay the paint. **Sibling amendment:** on `k1_bench_im69d_led150` the bench path is a **direct u8** apply after integer quantize and before `apply_gamma8`, not a u16 widen.

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
| Target env | `k1_main_rpl_im69d` (RPL) · `k1_bench_im69d_led150` (WS2812 sibling) · `k1_hardware` later | A: both tracks; never RPL env/flag on B489 |
| Boot default | Slot 0 identity | Locked. Tonight’s plate is `:look=1` |

## 5. Locked decisions

1. **Flag** `K1_LOOK_LIB_V1`. First env: `k1_main_rpl_im69d` only. Isolation test: `k1_hardware` and `k1_bench_im69d` do not define it.

   **§5.1a — later WS2812 bench (sibling, not RPL).** After an authored WS2812B roster exists on disk, `k1_bench_im69d_led150` may define `K1_LOOK_LIB_WS2812_V1`. `K1_LOOK_LIB_V1` remains `k1_main_rpl_im69d` only. Isolation: `k1_hardware`, `k1_bench_im69d` (parent), `k1_bench_reference`, and `k1_bench_im69d_led150` do **not** define `K1_LOOK_LIB_V1`. A led150 build must not compile `k1_ws2816_degamma.h`, `k1_look_tungsten.h`, or `k1_look_install_proof_cube`. Both flags at once is a compile error.
2. **Absorb** `K1_WS2816_DEGAMMA_V1`. When the library is on, that `#ifdef` is not a second path. Its table becomes compiled slot 1. Isolation tests update: degamma flag may remain as a *table generator* guard inside the look unit, not as a packer `#ifdef`.
3. **Insert** inside `k1_lever2_sq_to_u16` (or a renamed `k1_look_apply_u16` called from that site): after SQ→u16, after the Q16 limiter scale, before `ws2816_pack_pixel`. Same site, both primary and secondary pack calls.
4. **Limiter stays pre-look.** `budget_proxy` is still `n*3*65535` (identity today). Look may brighten the plate. Do not re-limit after the print in Phase A.
5. **Slot 0** is a function `return ch`, not a 256-entry ramp. No lerp dust.
6. **Boot** `CONFIG.LOOK = 0`, `CONFIG.SECONDARY_LOOK = 255` (inherit). Persist like `palette_index`.
7. **Switch** on Core 1 at the start of `k1_lever2_pack_frame` only. Serial/Tab5 write a `volatile uint8_t`. No mutex on the audio core. No mid-pixel swap.
8. **8-bit path** (`quantize_color`): when the RPL flag is off, nothing changes. **§5.8 hook (WS2812 sibling).** After incandescent mix, `quantize_color` / `quantize_color_secondary` produce an integer 0–255 (Bayer or `*255` cast). Apply is `k1_look_ws2812_apply_u8` on that integer **before** `apply_gamma8` writes `leds_out`. No u16 widen, no binary search, no lerp. `ENABLE_OUTPUT_GAMMA` stays 0. Latch primary and secondary slots once per `show_leds`, after `scale_to_strip` and before `show_secondary_leds`. Never ship the WS2816 degamma table onto B489 as a match.
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

**HOLD (Captain 2026-08-26):** this table places CRC at offset 16 and payload at offset 20. `k1_look_file.h` currently writes payload at offset 16 and appends CRC after the payload. Phase B file loading must not ship until one layout is selected and the contract, parser, and builder tests are identical. This mismatch does not block the compiled led150 sibling roster.

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
| `:look=N` | A | yes | RPL: N 0..15, unknown empty slot → NACK, stay. Sibling: N 0..3, slots 2 and 3 ACK as reserved identity |
| `:secondary_look=N` | A | yes | 255 inherit. Sibling range 0..3 or 255 |
| `:look_status` | A | no | prints slot, type name, env, crc. Live Phase-A control, not a dormant table row |
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

**Sibling roster (`K1_LOOK_LIB_WS2812_V1` on `k1_bench_im69d_led150` only):**

| Slot | Name | Machine | Why |
|---:|---|---|---|
| 0 | Identity | pass-through | flag-off equivalent |
| 1 | WS2812_PROOF | three `uint8[256]`, direct index | Locked `g[i]=(i*220)/255`; ≠ RPL; **not** a Main RPL match |
| 2 | Reserved measured | identity | Legal no-op. ACK. Not a grade. |
| 3 | Reserved | identity | Legal no-op. ACK. `z` wraps 0–3. |

Slots 0–3 ACK as reserved identity **only in this sibling roster**. The RPL roster still NACKs empty/reserved loadable slots. Do not NACK sibling 0–3 as empty.

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
| `:look=` empty/reserved slot | RPL: NACK, keep previous. Sibling slots 2 and 3 ACK as reserved identity |
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
- `K1_LOOK_LIB_V1` never effective on `k1_bench_im69d_led150`.
- `K1_LOOK_LIB_WS2812_V1` only on `k1_bench_im69d_led150`.
- Sibling slot 0 bit-identical to pre-look 8-bit replica; slot 1 ≠ identity and ≠ degamma/tungsten on the published sample set.

## 15. Forbidden (do not “just add”)

- Mid-frame or Core-0 apply.
- Look after pack / `nscale8` on wire bytes.
- Uniform 256-node 1D for γ-like curves (S9 dark crush).
- Runtime HSV “make it richer.”
- Uploading a 65³ cube into SRAM.
- Treating look as calibration.
- Flashing `k1_main_rpl_im69d` or `K1_LOOK_LIB_V1` onto B489A500. The authorised sibling flash is `k1_bench_im69d_led150` / `K1_LOOK_LIB_WS2812_V1` on B489 only.
- Flashing F887 / `k1_hardware` with either look flag until a named production flash.
- Enabling I2S LED to “get more bits for the LUT.”
- Crossfading by mixing packed bytes.

## 16. Phases (full breadth, one ABI)

**A — compiled library (first GO).** Two tracks, mutually exclusive flags.

- RPL Phase A: `k1_main_rpl_im69d` / `K1_LOOK_LIB_V1` / `9087A500`. Slots 0–3, absorb degamma, host tests, Main-RPL flash.
- WS2812 sibling Phase A: `k1_bench_im69d_led150` / `K1_LOOK_LIB_WS2812_V1` / `B489A500`. Direct u8 apply, slots 2 and 3 ACK as reserved identity, no RPL proof cube.

Default slot 0 on both. `:look=` / `:secondary_look=` / `:look_status` are live Phase-A controls on the compiled track.

**B — loadable slots.** `.klut` LittleFS, `:look_load=`, Tab5 send. Still no 3D required.

**C — 3D 17³.** Type 4, trilinear, one authored or generated split-look for proof, not default.

**D — measured LGP + 33³ / shaper.** Optical chart of this plate + this silicon. Slot 3 filled from measurement. Only then is “match the bench” a measurement problem rather than a curve argument.

## 17. Ship stamps

**Already on silicon (RPL):** look library on `k1_main_rpl_im69d` / `9087A500` (`K1_LOOK_LIB_V1`). Restore authority is the device-build registry, not this paragraph’s historic SHA.

**Already on silicon (WS2812 sibling):** `k1_bench_im69d_led150` / `K1_LOOK_LIB_WS2812_V1` / `B489A500` after a committed-source flash whose live `:build` git SHA **is** the look-library commit. A dirty-source bench bring-up is engineering only; app-image SHA-256 plus the dirty allowlist is provenance for that image, not the Task 10 ship stamp.

**This spec shipped (docs) when:** the HTML + this file exist and the two-track amendment is present.

**RPL Phase A on silicon when:** `IDENTITY OK: git=<sha> env=k1_main_rpl_im69d` and `:look_status` reports `slot=0 type=IDENTITY` at boot.

**WS2812 sibling Phase A on silicon when:** `IDENTITY OK: git=<source_commit_sha> env=k1_bench_im69d_led150` on `B489A500`, boot slot 0 IDENTITY, `:look=0..3` ACK with sibling type names, calibration unchanged, `LED_BUFFER_DIFF = NOT_RUN`. No `start_noise_cal`. Not a Main-RPL match claim.

**Who:** Captain approves this spec (or amends locked rows) → agent implements the named track → Captain flash GO for that device only.
