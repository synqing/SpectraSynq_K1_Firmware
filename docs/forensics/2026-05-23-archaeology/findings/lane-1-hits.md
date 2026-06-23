---
abstract: "Lane 1 read-only sweep of SPECTRASYNQ_K1_FIRMWARE/** for K1v2 textual occurrences. 10 hits across constants.h (5), system.h (3), globals.h (1) — wait, recount: constants.h has 5 lines (34, 42, 50, 165, 166, 167 = 6), system.h has 3 (168, 322, 397), globals.h has 1 (584). Total = 10. All hits cluster around the SB_K1V2_HARDWARE macro gate (8 sites) plus 2 comment-prose references. Proposed map: SB_K1V2_HARDWARE → SB_K1_HARDWARE (code), 'K1v2' → 'K1 hardware' (prose). One ambiguity flagged: PlatformIO env string 'esp32dev_audio_esv11_k1v2' is a vendor build identifier from Lightwave-Ledstrip firmware-v3 and may need to remain verbatim for traceability. No file renames required. No hits in SPECTRASYNQ_K1_FIRMWARE.ino main file."
---

# Lane 1 — SPECTRASYNQ_K1_FIRMWARE source K1v2 purge

Scope: SPECTRASYNQ_K1_FIRMWARE/** (firmware source only — .ino/.h/.cpp/.c)
Total hits: 10
Files affected: 3 (constants.h, system.h, globals.h)
Files clean: SPECTRASYNQ_K1_FIRMWARE.ino + all other .h files in scope

## Hits

| File:Line | Current Text | Proposed Replacement | Category |
|-----------|--------------|---------------------|----------|
| SPECTRASYNQ_K1_FIRMWARE/constants.h:34 | `#if defined(SB_K1V2_HARDWARE)` | `#if defined(SB_K1_HARDWARE)` | code-identifier (SB_HAS_ROTATE8 gate) |
| SPECTRASYNQ_K1_FIRMWARE/constants.h:42 | `#if defined(SB_K1V2_HARDWARE)` | `#if defined(SB_K1_HARDWARE)` | code-identifier (SB_USB_CUSTOM_DESCRIPTORS gate) |
| SPECTRASYNQ_K1_FIRMWARE/constants.h:50 | `#if defined(SB_K1V2_HARDWARE)` | `#if defined(SB_K1_HARDWARE)` | code-identifier (SB_ENABLE_USB_MSC_UPDATE gate) |
| SPECTRASYNQ_K1_FIRMWARE/constants.h:165 | `#if defined(SB_K1V2_HARDWARE)` | `#if defined(SB_K1_HARDWARE)` | code-identifier (GPIO PINS block gate) |
| SPECTRASYNQ_K1_FIRMWARE/constants.h:166 | `  // K1v2 production GPIO map from Lightwave-Ledstrip firmware-v3` | `  // K1 hardware production GPIO map from Lightwave-Ledstrip firmware-v3` | comment-prose |
| SPECTRASYNQ_K1_FIRMWARE/constants.h:167 | `  // env: esp32dev_audio_esv11_k1v2.` | `  // env: esp32dev_audio_esv11_k1v2.` (FLAG — vendor build identifier, see Ambiguities) | comment-prose-vendor |
| SPECTRASYNQ_K1_FIRMWARE/system.h:168 | `#if defined(SB_K1V2_HARDWARE)` | `#if defined(SB_K1_HARDWARE)` | code-identifier (init_usb TX buffer sizing) |
| SPECTRASYNQ_K1_FIRMWARE/system.h:322 | `#if defined(SB_K1V2_HARDWARE)` | `#if defined(SB_K1_HARDWARE)` | code-identifier (early init_usb call in init_system) |
| SPECTRASYNQ_K1_FIRMWARE/system.h:397 | `#if !defined(SB_K1V2_HARDWARE)` | `#if !defined(SB_K1_HARDWARE)` | code-identifier (negated — late init_usb fallback) |
| SPECTRASYNQ_K1_FIRMWARE/globals.h:584 | `#if defined(SB_K1V2_HARDWARE)` | `#if defined(SB_K1_HARDWARE)` | code-identifier (USBSerial alias selection) |

### Hit count by file

| File | Hits |
|------|------|
| SPECTRASYNQ_K1_FIRMWARE/constants.h | 6 |
| SPECTRASYNQ_K1_FIRMWARE/system.h | 3 |
| SPECTRASYNQ_K1_FIRMWARE/globals.h | 1 |
| **Total** | **10** |

### Hit count by category

| Category | Count |
|----------|-------|
| code-identifier (`SB_K1V2_HARDWARE` macro gate) | 8 |
| comment-prose | 1 |
| comment-prose-vendor (flagged) | 1 |

## File Renames Required

None. No `.ino`/`.h`/`.cpp`/`.c` filename in SPECTRASYNQ_K1_FIRMWARE/ contains `k1v2` (or any case variant).

## Ambiguities Flagged for Captain Review

- **SPECTRASYNQ_K1_FIRMWARE/constants.h:167** — `// env: esp32dev_audio_esv11_k1v2.` — This is a comment recording the upstream PlatformIO build-environment identifier from Lightwave-Ledstrip firmware-v3 (a vendor / sister-project string). Two defensible options:
  1. **Preserve verbatim** (recommended for source-traceability): keep `esp32dev_audio_esv11_k1v2` exactly as written — it is the actual external `env` name used in the cited upstream repo's `platformio.ini`, and renaming it locally would break grep-based provenance lookups against the upstream tree.
  2. **Rewrite to match local convention**: change to `esp32dev_audio_esv11_k1` if Captain intends to rebrand the upstream env identifier in lockstep with the SpectraSynq purge. This is only correct if the upstream env is also being renamed (likely out-of-scope for this firmware).
  Default unless overridden: option 1 (preserve).

## Notes

### Macro definition site
The `SB_K1V2_HARDWARE` macro is **not defined** inside SPECTRASYNQ_K1_FIRMWARE/ — it has no `#define SB_K1V2_HARDWARE` site in this scope. It is supplied externally (build flag from Arduino IDE compile script / PlatformIO env). The 8 `#if defined(...)` sites are **consumers only**. Renaming them to `SB_K1_HARDWARE` requires synchronized updates to the build-flag definition site, which lives outside this lane's scope (likely `tools/compile-k1v2-arduino.sh` or equivalent — owned by another lane).

**Apply-phase coordination required:** the 8 `#if defined(SB_K1V2_HARDWARE)` rewrites must land in the same commit / merge boundary as the build-flag rename, otherwise the K1 build target will silently fall through to the non-K1 branch (wrong GPIO map, wrong USB descriptor strategy, wrong init order, wrong USBSerial alias). This is a load-bearing capability gate, not a cosmetic rename.

### Semantic clusters of the 8 macro sites
The 8 `SB_K1V2_HARDWARE` consumers form 4 semantic groups, all expressing the same K1-hardware-vs-original-Sensory-Bridge gate:
1. **Capability flags** (constants.h:34/42/50) — gate `SB_HAS_ROTATE8=0`, `SB_USB_CUSTOM_DESCRIPTORS=0`, `SB_ENABLE_USB_MSC_UPDATE=0` for K1 hardware.
2. **GPIO pin map** (constants.h:165) — gate K1 production pinout block.
3. **USB init order + buffer** (system.h:168, 322, 397) — K1 calls `init_usb()` early with a 4KB TX buffer; original Sensory Bridge calls it late after `init_leds()`. The negated `!defined` at line 397 is the inverse gate.
4. **USBSerial typedef** (globals.h:584) — K1 aliases `USBSerial` to `Serial` (hardware UART path); original Sensory Bridge instantiates a `USBCDC USBSerial` object.

All 4 clusters describe the same K1-vs-not-K1 binary axis. The rename is purely cosmetic — no semantic restructuring needed.

### Search methodology
- `rg -niE 'k1[_]?v2'` against SPECTRASYNQ_K1_FIRMWARE/ → 10 hits.
- `rg -niF 'k1v2'` against SPECTRASYNQ_K1_FIRMWARE.ino → 0 hits (main .ino is clean).
- Broader regex `'k1.{0,2}v2|k1v2'` returns identical 10-hit set (no hyphenated/dotted variants like `k1-v2`, `k1.v2`, `K1.V2`).
- All hits are uppercase `K1V2` in macros and mixed-case `K1v2` / lowercase `k1v2` in prose. No `K1_V2` (with underscore) variant found.

### No surprises
No K1v2 surfaces discovered outside the predicted set. Captain's high-interest sites (constants.h, globals.h, system.h, .ino) were all enumerated; .ino was clean.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:lane-1-sweep | Created — exhaustive read-only sweep of SPECTRASYNQ_K1_FIRMWARE/** for K1v2 textual occurrences; 10 hits enumerated with proposed replacement map. |
