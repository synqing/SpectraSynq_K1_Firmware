# Lane 7 — Repo-root planning artefacts K1v2 purge

Scope: repo-root .md/.txt files (task_plan.md, findings.md, progress.md, README*, CHANGELOG*, etc.)
Total hits: 12

## Files Scanned

- `Benefits of Cochlear-Inspired AGC_Perceptually-Wei.md` (0 hits)
- `findings.md` (7 hits)
- `Integration.md` (0 hits)
- `Lightshow_Implementation_Plan.md` (0 hits)
- `progress.md` (2 hits)
- `README.md` (0 hits)
- `Sensory Bridge - Detail Code Analysis.md` (0 hits)
- `Sensory Bridge Firmware Architecture Analysis.md` (0 hits)
- `task_plan.md` (2 hits)

No CHANGELOG.md at repo root.

## Hits

| File:Line:Col | Current Text | Proposed Replacement | Category |
|---------------|--------------|---------------------|----------|
| progress.md:10:79 | `Received completed read-only SSA memos for Bloom/Waveform chronology, S2-S3/K1v2 chronology, committed artefact chronology, and dirty-tree/build evidence.` | `Received completed read-only SSA memos for Bloom/Waveform chronology, S2-S3/K1 hardware chronology, committed artefact chronology, and dirty-tree/build evidence.` | Prose — historical narrative |
| progress.md:11:68 | `` Cross-checked current source line ranges in `lightshow_modes.h`, K1v2 capability files, migration docs, config snapshot docs, and waveform-kill audit docs. `` | `` Cross-checked current source line ranges in `lightshow_modes.h`, K1 hardware capability files, migration docs, config snapshot docs, and waveform-kill audit docs. `` | Prose — historical narrative |
| findings.md:6:28 | `Current dirty tree after K1v2 LEDC/sweet-spot fix.` | `Current dirty tree after K1 hardware LEDC/sweet-spot fix.` | Prose — historical narrative |
| findings.md:8:62 | `` `claude-mem` observations for prior Bloom/Waveform repair, K1v2 GPIO/compile/upload work, serial strategy, Rotate8, LEDC, and PSRAM. `` | `` `claude-mem` observations for prior Bloom/Waveform repair, K1 hardware GPIO/compile/upload work, serial strategy, Rotate8, LEDC, and PSRAM. `` | Prose — historical narrative |
| findings.md:13:51 | `` `git status --short` showed current uncommitted K1v2 work in firmware files plus `tools/compile-k1v2-arduino.sh`. `` | `` `git status --short` showed current uncommitted K1 hardware work in firmware files plus `tools/compile-k1-arduino.sh`. `` | Prose (K1v2 prose) + Filename reference (`compile-k1v2-arduino.sh` → `compile-k1-arduino.sh`) |
| findings.md:14:167 | `Recent committed history contains secondary render isolation, p2p removal, recovery roadmap docs, perfect config snapshot, S3 compile prep, K1.Lightwave reference, K1v2 GPIO profile, and K1v2 upload evidence.` | `Recent committed history contains secondary render isolation, p2p removal, recovery roadmap docs, perfect config snapshot, S3 compile prep, K1.Lightwave reference, K1 hardware GPIO profile, and K1 hardware upload evidence.` | Prose — historical narrative (two occurrences on one line) |
| findings.md:15:55 | `Existing SSA outputs already contained useful prior K1v2 source-truth notes, but fresh read-only tasks were also queued on those same agents.` | `Existing SSA outputs already contained useful prior K1 hardware source-truth notes, but fresh read-only tasks were also queued on those same agents.` | Prose — historical narrative |
| findings.md:24:160 | `S2-S3 migration history split into: protected S2 content-capture boundary, generic S3 compile prep, K1.Lightwave reference detour, correction to firmware-v3 K1v2 GPIOs, K1v2 compile/upload evidence, and current dirty K1v2 hardening.` | `S2-S3 migration history split into: protected S2 content-capture boundary, generic S3 compile prep, K1.Lightwave reference detour, correction to firmware-v3 K1 hardware GPIOs, K1 hardware compile/upload evidence, and current dirty K1 hardware hardening.` | Prose — historical narrative (three occurrences on one line) |
| findings.md:25:17 | `Current dirty K1v2 hardening likely addresses absent Rotate8 and sweet-spot LEDC crash paths, but runtime proof remains incomplete for serial boot, PSRAM, I2S, LED output, and 120 FPS timing.` | `Current dirty K1 hardware hardening likely addresses absent Rotate8 and sweet-spot LEDC crash paths, but runtime proof remains incomplete for serial boot, PSRAM, I2S, LED output, and 120 FPS timing.` | Prose — historical narrative |
| findings.md:26:63 | `` `docs/s3-migration-prep.md` is stale against `tools/compile-k1v2-arduino.sh` for `LoopCore` / `EventsCore`. `` | `` `docs/s3-migration-prep.md` is stale against `tools/compile-k1-arduino.sh` for `LoopCore` / `EventsCore`. `` | Filename reference (`compile-k1v2-arduino.sh` → `compile-k1-arduino.sh`) |
| task_plan.md:5:119 | `Create a detailed forensic archaeology HTML reconstructing every known Waveform/Bloom repair attempt and the S2-to-S3/K1v2 migration/refactor work up to the current state.` | `Create a detailed forensic archaeology HTML reconstructing every known Waveform/Bloom repair attempt and the S2-to-S3/K1 hardware migration/refactor work up to the current state.` | Prose — historical narrative (goal statement) |
| task_plan.md:18:57 | `Completed - Pull memory and git chronology for S2-S3/K1v2 migration.` | `Completed - Pull memory and git chronology for S2-S3/K1 hardware migration.` | Prose — historical narrative (phase log) |

## File Renames Required

None. No root-level `.md` or `.txt` file contains `k1v2` in its filename.

(Note: the `tools/compile-k1v2-arduino.sh` filename reference IS quoted inside these root docs, but the actual file rename is out of scope for Lane 7 — it falls under the tools/ lane. The replacements above only update the in-prose REFERENCE to that filename so the planning artefacts read coherently after the tools/ lane completes its own rename.)

## Document Lifecycle Notes

`task_plan.md`, `findings.md`, and `progress.md` at repo root were authored for the 2026-05-23 forensic-archaeology task (per their own content). They are session-scoped Manus-style planning artefacts (planning-with-files pattern), not long-term doctrine. Captain decides which path:

- (a) **Rename in-place** with the K1v2 → K1 hardware purge applied above, leaving them at root. Lowest friction; preserves dirty-tree continuity for any in-flight follow-on edits.
- (b) **Move to `docs/forensics/2026-05-23-archaeology/`** alongside the generated HTML report (`docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html`). Cleanest; satisfies global Workspace Hygiene rules ("research outputs → `docs/`", session cleanup, no orphaned `.md` files at root).
- (c) **Delete** after the K1v2 purge completes and any follow-on edits have shipped. The HTML artefact at `docs/forensics/...` already preserves the synthesised conclusions.

Recommended default if Captain does not choose: **(b)** — preserves the audit trail without leaving root clutter, and the global CLAUDE.md explicitly directs research/analysis outputs into `docs/`. Apply the purge first, then move.

Recommended ordering, in either case: **apply the K1v2 → K1 hardware textual purge BEFORE renaming/moving/deleting** so the git history of the rename/move shows clean post-purge content.

## Ambiguities Flagged for Captain Review

1. **`K1.Lightwave reference` on `findings.md:14`** — adjacent to two K1v2 hits but is itself a distinct identifier (the K1.Lightwave reference port, per recent commit `f9f7278 docs: record existing k1 lightwave s3 port`). Left untouched in the proposed replacement. Confirm K1.Lightwave is NOT meant to be normalised to "K1 hardware" — it is a separate product/branch reference.

2. **`firmware-v3 K1v2 GPIOs` on `findings.md:24`** — this phrase describes a historical *correction commit* (per recent commit `5a2d050 chore: add sb k1v2 gpio build profile` — which Captain may or may not want to leave in its historical form). The proposed replacement (`firmware-v3 K1 hardware GPIOs`) preserves narrative meaning, but if Captain prefers strict historical fidelity (i.e., "the commit message at the time said K1v2"), this hit should be left as-is and instead annotated with a footnote. Flag.

3. **`task_plan.md:5` goal statement and `task_plan.md:18` phase log** — these describe completed historical work. If Captain wants the planning artefacts preserved as a *historical record* of how the task was originally framed (which used "K1v2"), these two lines are the strongest candidates for leaving untouched and annotating instead. If Captain wants forward-readable docs, apply the replacement as proposed.

4. **`progress.md:10` and `progress.md:11`** — same historical-record concern as (3). Same options apply.

5. **Two findings.md hits reference `compile-k1v2-arduino.sh` (lines 13 and 26)** — the proposed replacement assumes the tools/ lane will rename the file to `compile-k1-arduino.sh`. If the tools/ lane decides to keep the historical filename or pick a different name, these two replacements must be re-aligned with the tools/ lane's final decision. Lane 7 cannot resolve this independently.

## Notes

- `findings.md` AT REPO ROOT is the prior session's forensic findings file (Lane 7 scope). The `findings/` DIRECTORY (containing this output and lane-1/2/3 hits) is separate and was NOT scanned. Confirmed.
- No code-fenced identifier hits found at repo root (no `SB_K1V2_HARDWARE`-style symbols in any of the 9 scanned files). All hits are either prose narrative or filename references to `tools/compile-k1v2-arduino.sh`.
- All 12 hits are textual; no embedded HTML/JSON/YAML K1v2 references at repo root.
- READ-ONLY scan. No files in Lane 7 scope were modified.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:ssa-lane-7 | Created — repo-root planning-artefact K1v2 → K1 hardware purge sweep, 12 hits across findings.md / progress.md / task_plan.md, 0 file renames required at root. |
