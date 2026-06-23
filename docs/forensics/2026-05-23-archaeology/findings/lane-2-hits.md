# Lane 2 — tools/ build scripts K1v2 purge

Scope: tools/** (build scripts)
Total hits: 4

## Hits

| File:Line | Current Text | Proposed Replacement | Category |
|-----------|--------------|---------------------|----------|
| tools/compile-k1v2-arduino.sh:6 | `BUILD_PATH="${BUILD_PATH:-/tmp/sb-k1v2-build}"` | `BUILD_PATH="${BUILD_PATH:-/tmp/sb-k1-build}"` | path variable default |
| tools/compile-k1v2-arduino.sh:9 | `K1V2_FLAGS="${K1V2_FLAGS:--DSB_K1V2_HARDWARE -DENABLE_VP_PERF_AUDIT=1 -DFASTLED_RMT_BUILTIN_DRIVER=0 -DFASTLED_RMT_MAX_CHANNELS=4 -DFASTLED_RMT_MAX_TICKS_FOR_GTX_SEM=100 -DFASTLED_ESP32_FLASH_LOCK=0 -DFASTLED_INTERRUPT_RETRY_COUNT=0 -DBOARD_HAS_PSRAM -O3 -ffast-math}"` | `K1_FLAGS="${K1_FLAGS:--DSB_K1_HARDWARE -DENABLE_VP_PERF_AUDIT=1 -DFASTLED_RMT_BUILTIN_DRIVER=0 -DFASTLED_RMT_MAX_CHANNELS=4 -DFASTLED_RMT_MAX_TICKS_FOR_GTX_SEM=100 -DFASTLED_ESP32_FLASH_LOCK=0 -DFASTLED_INTERRUPT_RETRY_COUNT=0 -DBOARD_HAS_PSRAM -O3 -ffast-math}"` | shell variable name + compiler flag (`-DSB_K1V2_HARDWARE` → `-DSB_K1_HARDWARE`) |
| tools/compile-k1v2-arduino.sh:16 | `  --build-property "compiler.c.extra_flags=${K1V2_FLAGS}" \` | `  --build-property "compiler.c.extra_flags=${K1_FLAGS}" \` | shell variable reference |
| tools/compile-k1v2-arduino.sh:17 | `  --build-property "compiler.cpp.extra_flags=${K1V2_FLAGS}" \` | `  --build-property "compiler.cpp.extra_flags=${K1_FLAGS}" \` | shell variable reference |

## File Renames Required

| Current Path | Proposed Path | Notes |
|--------------|---------------|-------|
| tools/compile-k1v2-arduino.sh | tools/compile-k1-arduino.sh | Captain-directed; downstream docs must update references |

## Internal References to Renamed Files

The following paths (outside Lane 2 scope) reference `compile-k1v2-arduino.sh` by name. Reported for cross-checking the master findings only — Lane 2 will not modify them:

- `docs/s3-migration-prep.md:26` — `bash tools/compile-k1v2-arduino.sh` (executable command line in migration docs)
- `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html:520` — `<li><code>tools/compile-k1v2-arduino.sh</code></li>`
- `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html:764` — `tools/compile-k1v2-arduino.sh` (within `<pre><code>` block)
- `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html:800` — `<code>tools/compile-k1v2-arduino.sh</code>` (table cell)
- `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html:841` — `current <code>tools/compile-k1v2-arduino.sh</code>` (prose reference)
- `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html:914` — `<code>tools/compile-k1v2-arduino.sh:8-21</code>` (line-range citation)
- `findings.md:13` — `tools/compile-k1v2-arduino.sh` (working scratch report at repo root)
- `findings.md:26` — `tools/compile-k1v2-arduino.sh` (working scratch report at repo root)

`findings.md` at repo root is a session scratch file (per `git status` it is untracked). Forensic HTML in `docs/forensics/` is historical evidence and may need a different policy (preserve verbatim vs. update to new name) — flag for Captain decision in the docs lane.

## Ambiguities Flagged for Captain Review

1. **Forensic HTML file under `docs/forensics/`** — convention for historical evidence docs is typically "preserve verbatim". Captain to decide whether the forensic HTML should retain the legacy `compile-k1v2-arduino.sh` name as a historical artifact, or be updated to current name with an editorial note. Lane 2 surfaces this; the docs lane owns the resolution.
2. **`findings.md` at repo root** — appears to be a prior session's working scratch file (untracked). Lane 2 flags it for the appropriate housekeeping lane; not in Lane 2 scope to delete or rewrite.
3. **No `compile-k1-arduino.sh` already exists** — verified: `tools/` currently contains only `compile-k1v2-arduino.sh` and `compile-s3-arduino.sh`. Rename target path is free.
4. **`compile-s3-arduino.sh` is unaffected** — read end-to-end; contains no `k1v2` references, no `SB_K1V2_HARDWARE` flag, no rename required. Build path `/tmp/sb-s3-build` is platform-named, not product-name-derived.

## Notes

- All 4 textual hits are confined to a single file: `tools/compile-k1v2-arduino.sh`. The file is 22 lines total.
- The `K1V2_FLAGS` shell variable is *both* used as the variable name (4 sites) and contains the compiler define `-DSB_K1V2_HARDWARE` (1 site embedded within the variable's default value at line 9). Renaming the variable to `K1_FLAGS` and the define to `-DSB_K1_HARDWARE` are independent edits that must both happen in the apply phase.
- Build path default `/tmp/sb-k1v2-build` → `/tmp/sb-k1-build` is purely cosmetic for build hygiene; no caller persists this path between builds (`rm -rf` runs at line 11 unconditionally).
- No Makefiles, .py, .js, .yml, .yaml, .json, .toml, or .mk files exist under `tools/`. Only the two `.sh` files. Lane 2 search surface is complete.
- No comments, echo strings, or error messages in `tools/compile-k1v2-arduino.sh` mention "K1v2" — all 4 hits are code identifiers / path strings.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:lane-2 | Created — Lane 2 read-only sweep of tools/ for K1v2 purge |
