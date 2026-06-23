# Lane 4 — docs/ root + migration prep + config snapshots K1v2 purge

Scope: docs/ root + docs/config-snapshots/** + docs/hardware/** (excl. k1-hardware-definition.md), docs/s3-migration-prep.md
Total hits: 13 (all in docs/s3-migration-prep.md)

Scope verification:
- docs/s3-migration-prep.md — 13 hits (sole file with K1v2 occurrences in scope)
- docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md — 0 hits (verified read-through)
- docs/hardware/k1-hardware-definition.md — 0 hits (canonical truth doc, verified via rg; not touched)

## Hits

| File:Line | Current Text | Proposed Replacement | Category |
|-----------|--------------|---------------------|----------|
| docs/s3-migration-prep.md:9 | `The K1v2 bring-up profile in this checkout is \`SB_K1V2_HARDWARE\`. Its GPIO map is taken directly from the active \`Lightwave-Ledstrip/firmware-v3\` K1v2 production build flags.` | `The K1 hardware bring-up profile in this checkout is \`SB_K1_HARDWARE\`. Its GPIO map is taken directly from the active \`Lightwave-Ledstrip/firmware-v3\` K1 hardware production build flags.` | Prose + code-fenced identifier (inline) |
| docs/s3-migration-prep.md:23 | `Re-run the K1v2 GPIO-profile compile-only check with:` | `Re-run the K1 hardware GPIO-profile compile-only check with:` | Prose |
| docs/s3-migration-prep.md:26 | `bash tools/compile-k1v2-arduino.sh` | `bash tools/compile-k1-arduino.sh` | Filename reference (in code fence) |
| docs/s3-migration-prep.md:31 | `## K1v2 Firmware-v3 GPIO Source` | `## K1 hardware Firmware-v3 GPIO Source` | Heading |
| docs/s3-migration-prep.md:39 | `The active K1v2 production environment is \`esp32dev_audio_esv11_k1v2\`. Its build flags set:` | `The active K1 hardware production environment is \`esp32dev_audio_esv11_k1v2\`. Its build flags set:` | Prose (preserve PIO env identifier — that lives in firmware-v3, out of repo scope) — see Ambiguities |
| docs/s3-migration-prep.md:49 | `The \`SB_K1V2_HARDWARE\` profile maps those into SB as:` | `The \`SB_K1_HARDWARE\` profile maps those into SB as:` | Code-fenced identifier (inline) |
| docs/s3-migration-prep.md:61 | `Do not use the stale K1v2 comment in \`Lightwave-Ledstrip/firmware-v3/platformio.ini\` that mentions I2S GPIO 37/38/39. The active K1v2 production build flags in that file use LED GPIO 6/7 and I2S GPIO 11/14/13.` | `Do not use the stale K1 hardware comment in \`Lightwave-Ledstrip/firmware-v3/platformio.ini\` that mentions I2S GPIO 37/38/39. The active K1 hardware production build flags in that file use LED GPIO 6/7 and I2S GPIO 11/14/13.` | Prose |
| docs/s3-migration-prep.md:66 | `SB_K1V2_HARDWARE compile-only passed.` | `SB_K1_HARDWARE compile-only passed.` | Code-fenced identifier (in code block — captured compile log line) — see Ambiguities |
| docs/s3-migration-prep.md:71 | `## K1v2 Upload Evidence` | `## K1 hardware Upload Evidence` | Heading |
| docs/s3-migration-prep.md:73 | `K1v2 appeared as:` | `K1 hardware appeared as:` | Prose |
| docs/s3-migration-prep.md:82 | `The SB K1v2 build was uploaded to that explicit port only. Upload proof:` | `The SB K1 hardware build was uploaded to that explicit port only. Upload proof:` | Prose |
| docs/s3-migration-prep.md:138 | `4. Use \`SB_K1V2_HARDWARE\` for the first SB-on-K1v2 attempt.` | `4. Use \`SB_K1_HARDWARE\` for the first SB-on-K1 hardware attempt.` | Code-fenced identifier + prose (combined line) |
| docs/s3-migration-prep.md:140 | `6. Pass \`--upload-port <K1V2_PORT>\` explicitly; do not rely on a stale default port.` | `6. Pass \`--upload-port <K1_PORT>\` explicitly; do not rely on a stale default port.` | Code-fenced placeholder identifier |

## File Renames Required

None — no .md files in scope contain "k1v2" in filename (verified via `find docs/ -iname '*k1v2*'`).

## External File References Needing Update

| Reference In | Referenced File | Proposed New Path |
|--------------|-----------------|-------------------|
| docs/s3-migration-prep.md:26 | `tools/compile-k1v2-arduino.sh` | `tools/compile-k1-arduino.sh` |
| docs/s3-migration-prep.md:9, 39, 49, 61 (context) | `Lightwave-Ledstrip/firmware-v3/platformio.ini` env name `esp32dev_audio_esv11_k1v2` | NO CHANGE — env lives in external `Lightwave-Ledstrip/firmware-v3` repo, out of this purge's scope. Captain to decide if cross-repo rename is in scope for a later lane. |

## Critical Doc-Drift Reconciliations Required (orthogonal to rename, but surface them)

**FOUND — confirmed drift:**

- docs/s3-migration-prep.md:14 inside the `Compile target used` code block records:
  `...,LoopCore=1,EventsCore=1,...`
  but the active script `tools/compile-k1v2-arduino.sh:8` (the FQBN it actually invokes) now uses:
  `...,LoopCore=0,EventsCore=0,...`

  Proposed correction (independent of K1v2 → K1 hardware rename): update line 14 to `LoopCore=0,EventsCore=0` so the doc reflects what the wrapper actually compiles with. Flag for Captain — the doc is currently stale relative to the active toolchain.

## Ambiguities Flagged for Captain Review

1. **Line 39 PIO environment name `esp32dev_audio_esv11_k1v2`** — this is a build environment identifier inside the *external* `Lightwave-Ledstrip/firmware-v3/platformio.ini`, not in this repo. The prose rename `K1v2` → `K1 hardware` is straightforward, but the literal env-name string `esp32dev_audio_esv11_k1v2` is documentation of an out-of-scope external identifier. Recommended: leave the inline literal intact (preserve forensic accuracy of what firmware-v3 currently advertises), only rewrite the surrounding prose. Captain to confirm whether external repo rename is in scope for a later lane.

2. **Line 66 compile log line `SB_K1V2_HARDWARE compile-only passed.`** — this is captured stdout from a compile run on 2026-05-22 when the identifier was still `SB_K1V2_HARDWARE`. Historical narrative quoting a prior session. Two options:
   - **Option A (forensic accuracy):** preserve `SB_K1V2_HARDWARE` literal as the compile-log text that was actually emitted that day; add a parenthetical `(identifier later renamed to SB_K1_HARDWARE)`.
   - **Option B (consistency):** rewrite the captured line to `SB_K1_HARDWARE compile-only passed.` to match the new identifier shape, losing forensic fidelity.

   Captain decision required. Default recommendation: Option A — this is a quoted historical artefact.

3. **Lines 73, 82 "K1v2 appeared as:" / "The SB K1v2 build was uploaded"** — historical narrative describing what happened on 2026-05-22. Pure prose rename to "K1 hardware" is safe; flagging only because these sit inside a section whose semantic intent is forensic (Upload Evidence). Recommendation: rename to "K1 hardware" — the noun describes the device, not a captured log token.

4. **Line 140 placeholder `<K1V2_PORT>`** — uppercase shell-style placeholder, not a real env var or identifier in any code. Renaming to `<K1_PORT>` is clean; flagging only because Captain may prefer a more descriptive placeholder like `<K1_HARDWARE_PORT>` for clarity.

## Notes

- The canonical K1 hardware doc is `docs/hardware/k1-hardware-definition.md`. Verified zero K1v2 occurrences via `rg -ni 'k1[_]?v2'` — file NOT touched (read-only verification only).
- The config snapshot `docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md` is K1v2-clean — confirmed via full file read. It contains only firmware identifiers (`FIRMWARE_VERSION=40102`, `CHIP_ID=763E7500`) and CONFIG/SECONDARY/VP runtime values; no hardware-platform naming.
- docs/s3-migration-prep.md is the sole file in scope requiring edits. Captain may want to handle the doc-drift `LoopCore=1` → `LoopCore=0` correction (Critical Doc-Drift section above) in the same pass to avoid a second write to this file.
- Tools-scope rename (`tools/compile-k1v2-arduino.sh` → `tools/compile-k1-arduino.sh`) is out of this lane (excluded scope), but docs/s3-migration-prep.md:26 will be wrong if that file is renamed in another lane and this doc is not updated in sync.
- All 13 hits are confined to docs/s3-migration-prep.md, so this is a single-file edit lane. No `find` rename operations needed.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:lane-4-sweep | Created Lane 4 K1v2 → K1 hardware purge findings for docs/ root + migration prep + config snapshots scope. 13 hits identified, all in docs/s3-migration-prep.md. Doc-drift LoopCore=1→0 flagged. Two historical-quote ambiguities surfaced for Captain. |
