# Lane 5 — docs/forensics K1v2 purge

Scope: `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html`
Total hits: 62 occurrences across 51 lines
Forensic report meta: HEAD = `8b35022`, Report Mode = "Read-only firmware archaeology. No firmware source changes made for this report."

Casings observed: `K1v2` (predominant prose form), `K1V2` (macro identifier form `SB_K1V2_HARDWARE`), `k1v2` (lowercase in commit subjects and filename references).

This lane is READ-ONLY. The HTML was not modified. The tables below capture every textual hit, the classification verdict, and the proposed Path A action.

---

## Hits (subject to rename — non-citation text)

Naming rules applied:
- Prose / headings / table cells / `<time>` / `<strong>`: `K1v2` -> `K1 hardware`
- Code-fenced identifiers (`SB_K1V2_HARDWARE`): -> `SB_K1_HARDWARE`
- Filename references (`compile-k1v2-arduino.sh`): -> `compile-k1-arduino.sh`

| File:Line | Current Text | Proposed Replacement | Category |
|-----------|--------------|---------------------|----------|
| forensic-reconstruction.html:6 | `<title>SB Forensic Archaeological Reconstruction - Waveform/Bloom + S2-S3/K1v2</title>` | `<title>SB Forensic Archaeological Reconstruction - Waveform/Bloom + S2-S3/K1 hardware</title>` | HTML `<title>` prose |
| forensic-reconstruction.html:294 | `<h1>Forensic Archaeological Reconstruction: SB Waveform/Bloom Recovery + S2-S3/K1v2 Migration</h1>` | `<h1>Forensic Archaeological Reconstruction: SB Waveform/Bloom Recovery + S2-S3/K1 hardware Migration</h1>` | `<h1>` heading prose |
| forensic-reconstruction.html:326 (occurrence 1) | "...The S2-S3 work evolved into a K1v2 bring-up profile using firmware-v3 GPIOs..." | "...The S2-S3 work evolved into a K1 hardware bring-up profile using firmware-v3 GPIOs..." | `<p>` prose |
| forensic-reconstruction.html:326 (occurrence 2) | "...absent Rotate8, USB serial strategy, LEDC guard failures, and K1v2 compile flags." | "...absent Rotate8, USB serial strategy, LEDC guard failures, and K1 hardware compile flags." | `<p>` prose |
| forensic-reconstruction.html:346 | `<h3>K1v2</h3>` | `<h3>K1 hardware</h3>` | `<h3>` heading (see anchor note) |
| forensic-reconstruction.html:347 | "...moved from generic S3 compile prep to an explicit K1v2 profile..." | "...moved from generic S3 compile prep to an explicit K1 hardware profile..." | `<p>` prose |
| forensic-reconstruction.html:351 | "The latest dirty K1v2 hardening has compile/upload history nearby..." | "The latest dirty K1 hardware hardening has compile/upload history nearby..." | `<p>` prose |
| forensic-reconstruction.html:369 | "...K1v2 guards, USB serial, LEDC guards, compile script." | "...K1 hardware guards, USB serial, LEDC guards, compile script." | `<td>` table cell |
| forensic-reconstruction.html:374 (occurrence 1) | "...K1v2 GPIO profile..." | "...K1 hardware GPIO profile..." | `<td>` table cell |
| forensic-reconstruction.html:374 (occurrence 2) | "...K1v2 upload evidence." | "...K1 hardware upload evidence." | `<td>` table cell |
| forensic-reconstruction.html:379 | "...K1v2 USB/Rotate8/LEDC incidents." | "...K1 hardware USB/Rotate8/LEDC incidents." | `<td>` table cell |
| forensic-reconstruction.html:384 | "...S2-S3/K1v2 migration..." | "...S2-S3/K1 hardware migration..." | `<td>` table cell |
| forensic-reconstruction.html:389 | "...earlier K1v2 upload and serial sanity..." | "...earlier K1 hardware upload and serial sanity..." | `<td>` table cell |
| forensic-reconstruction.html:486 | "...then became K1v2-specific.</strong>" | "...then became K1 hardware-specific.</strong>" | `<strong>` prose |
| forensic-reconstruction.html:487 (occurrence 1, prose) | "...use firmware-v3 K1v2 GPIOs." | "...use firmware-v3 K1 hardware GPIOs." | `<p>` prose (SHA-adjacent; only the prose token "K1v2" is renamed — SHAs `32cbadf`, `f9f7278`, `5a2d050` are preserved verbatim) |
| forensic-reconstruction.html:487 (occurrence 2, identifier) | `<code>SB_K1V2_HARDWARE</code>` | `<code>SB_K1_HARDWARE</code>` | Code-fenced identifier |
| forensic-reconstruction.html:490 | `<code>docs/s3-migration-prep.md:31-61</code> records firmware-v3 K1v2 GPIO source and mapping.` | `<code>docs/s3-migration-prep.md:31-61</code> records firmware-v3 K1 hardware GPIO source and mapping.` | `<li>` prose |
| forensic-reconstruction.html:491 | `<code>SPECTRASYNQ_K1_FIRMWARE/constants.h:165-187</code> contains the current K1v2 profile.` | `<code>SPECTRASYNQ_K1_FIRMWARE/constants.h:165-187</code> contains the current K1 hardware profile.` | `<li>` prose |
| forensic-reconstruction.html:499 | "<strong>K1v2 compile/upload evidence landed..." | "<strong>K1 hardware compile/upload evidence landed..." | `<strong>` heading-prose |
| forensic-reconstruction.html:500 | "Commit `<code>8b35022</code>` records a K1v2 upload to explicit ESP32-S3 target identity..." | "Commit `<code>8b35022</code>` records a K1 hardware upload to explicit ESP32-S3 target identity..." | `<p>` prose (SHA `8b35022` preserved verbatim; only prose token "K1v2" renamed) |
| forensic-reconstruction.html:512 | "<strong>Uncommitted K1v2 hardening now addresses absent Rotate8..." | "<strong>Uncommitted K1 hardware hardening now addresses absent Rotate8..." | `<strong>` prose |
| forensic-reconstruction.html:513 (occurrence 1) | "...disable custom USB descriptors/MSC on K1v2..." | "...disable custom USB descriptors/MSC on K1 hardware..." | `<p>` prose |
| forensic-reconstruction.html:513 (occurrence 2) | "...map `<code>USBSerial</code>` to `<code>Serial</code>` for K1v2..." | "...map `<code>USBSerial</code>` to `<code>Serial</code>` for K1 hardware..." | `<p>` prose |
| forensic-reconstruction.html:513 (occurrence 3) | "...update the K1v2 compile wrapper." | "...update the K1 hardware compile wrapper." | `<p>` prose |
| forensic-reconstruction.html:520 | `<li><code>tools/compile-k1v2-arduino.sh</code></li>` | `<li><code>tools/compile-k1-arduino.sh</code></li>` | Filename reference inside `<code>` |
| forensic-reconstruction.html:653 | "...during source stabilisation and K1v2 bring-up." | "...during source stabilisation and K1 hardware bring-up." | `<td>` table cell |
| forensic-reconstruction.html:665 | `<h2>S2-S3/K1v2 Migration and Refactor Timeline</h2>` | `<h2>S2-S3/K1 hardware Migration and Refactor Timeline</h2>` | `<h2>` heading (see anchor note) |
| forensic-reconstruction.html:674 | "...flash only the dedicated S3/K1v2 device and pass explicit upload port." | "...flash only the dedicated S3/K1 hardware device and pass explicit upload port." | `<li>` prose |
| forensic-reconstruction.html:695 | "...specifically called for firmware-v3 K1v2 GPIOs, not S3-Zero assumptions." | "...specifically called for firmware-v3 K1 hardware GPIOs, not S3-Zero assumptions." | `<p>` prose |
| forensic-reconstruction.html:698 | "...records the correction to firmware-v3 K1v2 GPIOs." | "...records the correction to firmware-v3 K1 hardware GPIOs." | `<li>` prose |
| forensic-reconstruction.html:704 | `<time>K1v2 GPIO profile</time>` | `<time>K1 hardware GPIO profile</time>` | `<time>` element |
| forensic-reconstruction.html:706 | `<strong><code>SB_K1V2_HARDWARE</code> was added.</strong>` | `<strong><code>SB_K1_HARDWARE</code> was added.</strong>` | Code-fenced identifier |
| forensic-reconstruction.html:707 | "K1v2 maps the SB firmware onto firmware-v3 production pins..." | "K1 hardware maps the SB firmware onto firmware-v3 production pins..." | `<p>` prose |
| forensic-reconstruction.html:716 | `<time>first K1v2 upload</time>` | `<time>first K1 hardware upload</time>` | `<time>` element |
| forensic-reconstruction.html:718 | "<strong>The first K1v2 upload was recorded against explicit ESP32-S3 identity.</strong>" | "<strong>The first K1 hardware upload was recorded against explicit ESP32-S3 identity.</strong>" | `<strong>` prose |
| forensic-reconstruction.html:730 | "<strong>K1v2 boot exposed missing-hardware paths and serial/PSRAM issues.</strong>" | "<strong>K1 hardware boot exposed missing-hardware paths and serial/PSRAM issues.</strong>" | `<strong>` prose |
| forensic-reconstruction.html:731 | "...sweet-spot LED code still running after K1v2 disabled those pins." | "...sweet-spot LED code still running after K1 hardware disabled those pins." | `<p>` prose |
| forensic-reconstruction.html:743 (occurrence 1) | "K1v2 has no Rotate8 present..." | "K1 hardware has no Rotate8 present..." | `<p>` prose |
| forensic-reconstruction.html:743 (occurrence 2) | "...USB custom descriptors and MSC update mode are disabled for K1v2." | "...USB custom descriptors and MSC update mode are disabled for K1 hardware." | `<p>` prose |
| forensic-reconstruction.html:757 | "...firmware/tool changes were already present before report generation and represent the current K1v2 hardening state." | "...firmware/tool changes were already present before report generation and represent the current K1 hardware hardening state." | `<p>` prose |
| forensic-reconstruction.html:764 | `tools/compile-k1v2-arduino.sh` (inside `<pre><code>`) | `tools/compile-k1-arduino.sh` | Filename reference inside `<pre>` block (see preservation note) |
| forensic-reconstruction.html:781 | "Adds K1v2 capability flags and source-truth GPIO map." | "Adds K1 hardware capability flags and source-truth GPIO map." | `<td>` table cell |
| forensic-reconstruction.html:786 | "...aliases `<code>USBSerial</code>` to `<code>Serial</code>` for K1v2." | "...aliases `<code>USBSerial</code>` to `<code>Serial</code>` for K1 hardware." | `<td>` table cell |
| forensic-reconstruction.html:796 (occurrence 1) | "Compiles out MSC update mode for K1v2..." | "Compiles out MSC update mode for K1 hardware..." | `<td>` table cell |
| forensic-reconstruction.html:796 (occurrence 2) | "...and starts K1v2 USB earlier." | "...and starts K1 hardware USB earlier." | `<td>` table cell |
| forensic-reconstruction.html:800 | `<td><code>tools/compile-k1v2-arduino.sh</code></td>` | `<td><code>tools/compile-k1-arduino.sh</code></td>` | Filename reference inside `<code>` |
| forensic-reconstruction.html:801 | "Builds K1v2 with `<code>USBMode=hwcdc</code>`..." | "Builds K1 hardware with `<code>USBMode=hwcdc</code>`..." | `<td>` table cell |
| forensic-reconstruction.html:829 | "K1v2 USB strategy changed through several iterations..." | "K1 hardware USB strategy changed through several iterations..." | `<p>` prose |
| forensic-reconstruction.html:837 | "K1v2 upload and compile evidence do not prove 120 FPS or a 2 ms render ceiling." | "K1 hardware upload and compile evidence do not prove 120 FPS or a 2 ms render ceiling." | `<p>` prose |
| forensic-reconstruction.html:841 | "...while current `<code>tools/compile-k1v2-arduino.sh</code>` uses `<code>0/0</code>`." | "...while current `<code>tools/compile-k1-arduino.sh</code>` uses `<code>0/0</code>`." | Filename reference inside `<code>` |
| forensic-reconstruction.html:897 | "K1v2 GPIO map is present." | "K1 hardware GPIO map is present." | `<td>` table cell |
| forensic-reconstruction.html:901 | "K1v2 Rotate8 is disabled." | "K1 hardware Rotate8 is disabled." | `<td>` table cell |
| forensic-reconstruction.html:905 | "K1v2 sweet-spot LEDC paths are guarded." | "K1 hardware sweet-spot LEDC paths are guarded." | `<td>` table cell |
| forensic-reconstruction.html:909 | "K1v2 serial currently aliases `<code>USBSerial</code>` to `<code>Serial</code>`." | "K1 hardware serial currently aliases `<code>USBSerial</code>` to `<code>Serial</code>`." | `<td>` table cell |
| forensic-reconstruction.html:913 | "K1v2 compile wrapper has current flags." | "K1 hardware compile wrapper has current flags." | `<td>` table cell |
| forensic-reconstruction.html:914 | `<td><code>tools/compile-k1v2-arduino.sh:8-21</code></td>` | `<td><code>tools/compile-k1-arduino.sh:8-21</code></td>` | Filename + line range inside `<code>` |
| forensic-reconstruction.html:938 | "S2-S3/K1v2 migration timeline" | "S2-S3/K1 hardware migration timeline" | `<td>` table cell |
| forensic-reconstruction.html:939 | "...firmware-v3 K1v2 GPIO correction..." | "...firmware-v3 K1 hardware GPIO correction..." | `<td>` table cell |
| forensic-reconstruction.html:959 (occurrence 1) | "<strong>S2-S3/K1v2:</strong>" | "<strong>S2-S3/K1 hardware:</strong>" | `<strong>` prose |
| forensic-reconstruction.html:959 (occurrence 2) | "The K1v2 target is correctly identified and partially hardened." | "The K1 hardware target is correctly identified and partially hardened." | `<p>` prose |
| forensic-reconstruction.html:959 (occurrence 3) | "...compile, explicit K1v2 upload, serial boot capture..." | "...compile, explicit K1 hardware upload, serial boot capture..." | `<p>` prose |

Rewriteable occurrence count: 61 of 62.

---

## Hits Preserved Under Path A (commit-subject quotes / SHA-adjacent text)

Only one occurrence in the report is a literal quote of a historical git commit subject. Under Path A (forward-only purge), the historical commit subject is not rewritten in git, so the report's verbatim quote should also remain unchanged. Under Path B (full history rewrite), the commit subject itself would change and the report quote would need post-rewrite patching.

| File:Line | Current Text | Path A Action | Path B Action |
|-----------|--------------|----------------|----------------|
| forensic-reconstruction.html:307 | `<span><code>8b35022</code> - docs: record sb k1v2 upload evidence</span>` | preserve unchanged (verbatim historical commit subject for HEAD = `8b35022`) | rewrite during downstream SHA-remap pass; the SHA will also change |

Preserved occurrence count: 1 of 62.

Note: Lines 487 and 500 cite SHAs in the same paragraph as prose hits, but the "K1v2" text on those lines is editorial prose, NOT a verbatim commit subject quote. Those lines appear in the rewriteable table above. Only line 307 contains a literal commit-subject quote.

---

## SHA Citations Inventory (preserve under Path A; remap under Path B)

These commit SHAs are citation-evidence in the report. They must be preserved exactly. Under Path B, every SHA will change at history-rewrite time and a downstream remap pass would need to update all of these citations.

| File:Line | SHA | Context |
|-----------|-----|---------|
| forensic-reconstruction.html:307 | `8b35022` | HEAD meta strip; literal commit subject quote: "docs: record sb k1v2 upload evidence" |
| forensic-reconstruction.html:487 | `32cbadf` | "Commit `<code>32cbadf</code>` added generic ESP32-S3 compile prep." |
| forensic-reconstruction.html:487 | `f9f7278` | "Commit `<code>f9f7278</code>` documented the existing K1.Lightwave S3 port as a reference." |
| forensic-reconstruction.html:487 | `5a2d050` | "Commit `<code>5a2d050</code>` added `<code>SB_K1V2_HARDWARE</code>`." |
| forensic-reconstruction.html:500 | `8b35022` | "Commit `<code>8b35022</code>` records a K1v2 upload to explicit ESP32-S3 target identity..." |

Additional SHAs cited in the dispatcher prompt but NOT located inline in this HTML file as citation prose: `de4fc48`, `e78b6f6`, `039c78a`, `9f10f0b`, `1dca4cb`. (These may appear in other forensic artefacts under Lane 5 scope expansions; this file does not cite them by SHA in textual prose. Confirmed via `grep -E '[a-f0-9]{7}'` of the HTML for SHA-shaped tokens — only the five SHAs above appear as inline `<code>`-fenced citations on lines 307, 487, and 500.)

---

## Ambiguities Flagged for Captain Review

1. **Heading anchors / table-of-contents links.** Lines 346 (`<h3>K1v2</h3>`), 665 (`<h2>S2-S3/K1v2 Migration and Refactor Timeline</h2>`), and section headings on lines 6 and 294 use "K1v2" inside heading elements. The HTML uses NO explicit `id=` / `name=` attributes (grep confirmed: zero attribute references to k1v2 in any casing). Browser auto-generated fragment anchors are not used here. Risk under rename: **low** — no internal `<a href="#k1v2">` style links exist in the file. Captain may proceed with the heading rewrite without anchor breakage.

2. **Filename references inside `<pre>` block at line 764.** This block appears to be a `git status` style listing of currently-modified files. Renaming the filename in the report PRESUMES that lane(s) covering `tools/compile-k1v2-arduino.sh` will rename the file itself to `tools/compile-k1-arduino.sh`. If the file rename does not land, the report would falsely claim a path that does not exist on disk. **Decision needed:** Lane 5 should only execute the line-764 rewrite AFTER (or coordinated with) the tools-lane file rename.

3. **`SB_K1V2_HARDWARE` macro identifier at lines 487 and 706.** Rewriting these to `SB_K1_HARDWARE` in the HTML presumes the firmware-source lanes are renaming the macro. Same coordination concern as item 2. **Decision needed:** synchronise this rewrite with the firmware lane that owns `constants.h`.

4. **Tool filename references at lines 520, 764, 800, 841, and 914.** All five lines reference `compile-k1v2-arduino.sh` (line 914 includes a line-range suffix `:8-21`). After rename, line ranges must still resolve in the renamed file. Captain should verify the tools-lane line-range mapping survives the file rename.

5. **Casing variants.** Three casings exist: `K1v2` (~55 occurrences), `K1V2` (2 occurrences — macro identifier only, lines 487 and 706), `k1v2` (5 occurrences — commit-subject quote on 307, filename references on 520, 764, 800, 841, 914). Replacement rules are case-aware:
   - `K1v2` (prose) -> `K1 hardware`
   - `K1V2` (identifier `SB_K1V2_HARDWARE`) -> `K1_HARDWARE` (inside `SB_K1_HARDWARE`)
   - `k1v2` (filename) -> `k1` (inside `compile-k1-arduino.sh`)
   - `k1v2` (commit-subject quote, line 307) -> preserved unchanged

---

## Notes

- The report mode meta on line 311 states: "Read-only firmware archaeology. No firmware source changes made for this report." This meta statement is unaffected by the purge — leave as-is.
- The HEAD meta on lines 306-307 cites HEAD = `8b35022` with the verbatim commit subject. Under Path A this remains the historical truth. If Lane 5 ever produces an updated forensic HTML after the purge lands, the HEAD line will naturally update to the new HEAD commit at that point.
- Total textual occurrences: 62. Rewriteable: 61. Path-A-preserved: 1 (commit-subject quote on line 307).
- No HTML attribute references (`id=`, `class=`, `name=`, `href=`) contain "k1v2" in any casing. Confirmed by `grep -E 'id="[^"]*k1_?v2|class="[^"]*k1_?v2|href="[^"]*k1_?v2|name="[^"]*k1_?v2'` returning zero matches. Heading rename is anchor-safe.
- This file was authored READ-ONLY against the forensic HTML. No edits were performed on the HTML during Lane 5 enumeration.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:ssa-lane-5 | Created. Catalogued 62 K1v2 occurrences (61 rewriteable, 1 Path-A-preserved) across 51 lines of the SB Waveform/Bloom/S2-S3/K1v2 forensic reconstruction HTML. Inventoried five inline SHA citations and flagged five ambiguities for Captain review. |
