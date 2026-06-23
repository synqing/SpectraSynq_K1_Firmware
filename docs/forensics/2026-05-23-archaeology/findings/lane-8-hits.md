# Lane 8 — Audit + archive + vendored docs K1v2 purge

Scope: audit/**, fixed_firmware/**, archive/**, libraries/**/*.md (vendored docs only)
Total hits: 8
Directories present: audit/ (PRESENT), fixed_firmware/ (PRESENT, no hits), archive/ (ABSENT — directory does not exist), libraries/ (PRESENT, 18 .md files scanned, no hits)

## Hits

| File:Line | Current Text | Proposed Replacement | Category |
|-----------|--------------|---------------------|----------|
| audit/understanding/08_captain_preferences_and_feedback.md:61 | `5. **Confusing K1 vs K1v2 vs SB.** P57367: *"what are you uploading to? the k1v2 or the esp32s2?"* — when an agent is about to flash, it must name the target correctly. K1v9 hardware on this branch is the SB-derived ESP32-S2 board, not the K1v2 (which is a different platform under a different project tree).` | Rewrite prose narrative: replace each `K1v2` with `K1 hardware` EXCEPT the quoted Captain prompt `P57367: "what are you uploading to? the k1v2 or the esp32s2?"` which is a verbatim quotation and must be preserved as-is. Resulting passage: `5. **Confusing K1 vs K1 hardware vs SB.** P57367: *"what are you uploading to? the k1v2 or the esp32s2?"* — when an agent is about to flash, it must name the target correctly. K1v9 hardware on this branch is the SB-derived ESP32-S2 board, not the K1 hardware (which is a different platform under a different project tree).` | Prose / doc body (with embedded verbatim quote — AMBIGUITY: rewriting "K1 vs K1v2 vs SB" loses the contrast that was the whole point of the bullet) |
| audit/understanding/03_k1_hardware_lgp_topology.md:67 | `... — exactly the architecture obs #53230 confirms is ABSENT from K1v2 / firmware-v3 and was never built there.` | `... — exactly the architecture obs #53230 confirms is ABSENT from K1 hardware / firmware-v3 and was never built there.` | Prose / doc body — HISTORICAL NARRATIVE (audit memo comparing this branch to the separate K1v2 platform) |
| audit/understanding/03_k1_hardware_lgp_topology.md:110 | Table row: `\| K1v2 / firmware-v3 (in development) \| ESP32-S3 \| DESIGN INTENT same as SB v9 ... \| Built-in MEMS \| K1 successor \|` | `\| K1 hardware / firmware-v3 (in development) \| ESP32-S3 \| ... \| K1 successor \|` | Prose / doc body (table cell) — HISTORICAL NARRATIVE (comparison table of hardware generations) |
| audit/understanding/03_k1_hardware_lgp_topology.md:129 | Changelog row: `... and comparison to SB v1-v8 and K1v2/firmware-v3, and design implications ...` | `... and comparison to SB v1-v8 and K1 hardware/firmware-v3, and design implications ...` | Prose / doc body (changelog entry) — HISTORICAL NARRATIVE |
| audit/understanding/05_prephase1_effects_history.md:9 | `**Sources:** claude-mem observations (~25 IDs cited inline), inline header comments in ` ... `, and the K1v2 dual-VP critique pack at \`.planning/k1-vp-drift/A1..A7_CRITIQUE_*.md\`.` | `... and the K1 hardware dual-VP critique pack at \`.planning/k1-vp-drift/A1..A7_CRITIQUE_*.md\`.` | Prose / doc body — HISTORICAL NARRATIVE (sources block citing prior critique pack name) |
| audit/understanding/05_prephase1_effects_history.md:17 | `... The "year of changes" Captain references lives mostly *outside* this file — in the K1v2 firmware-v3 effect tree, the K1 visual bible, and SbK1*Effect reference ports — but every change that *did* land ...` | `... lives mostly *outside* this file — in the K1 hardware firmware-v3 effect tree, the K1 visual bible, and SbK1*Effect reference ports — ...` | Prose / doc body — HISTORICAL NARRATIVE (period-accurate description of where changes lived during the prior development arc) |
| audit/understanding/05_prephase1_effects_history.md:111 | `Heartbeat is a K1v2 dual-VP effect outside \`SPECTRASYNQ_K1_FIRMWARE/\`, but the critique informs SB effect design directly because Captain ordered an SB Bloom *direct port* into K1v2 (obs #53438) ...` | `Heartbeat is a K1 hardware dual-VP effect outside \`SPECTRASYNQ_K1_FIRMWARE/\`, but the critique informs SB effect design directly because Captain ordered an SB Bloom *direct port* into K1 hardware (obs #53438) ...` | Prose / doc body — HISTORICAL NARRATIVE (describing effect-port direction during the contemporaneous arc) |
| audit/understanding/05_prephase1_effects_history.md:131 | `Aggregating across observations #53361, #53386, #53407, #53423, #53438 (K1v2 Heartbeat arc) and #53394, #53405, #53406, #53436, #53449 (SB v9 arc):` | `Aggregating across observations #53361, ... #53438 (K1 hardware Heartbeat arc) and ... (SB v9 arc):` | Prose / doc body — HISTORICAL NARRATIVE (labels a named observation cluster as the "K1v2 Heartbeat arc") |

## File Renames Required

None. No .md filenames in scope contain `k1v2` or `k1_v2`.

## Historical-Preservation Candidates (HIGH-VOLUME FLAG)

**ALL 8 hits are historical-preservation candidates.** Every hit lives in `audit/understanding/` — these are SSA-authored audit memos dated 2026-05-20/21 whose explicit purpose is to document *how the K1v9/SB branch differs from the separate K1v2 (firmware-v3, ESP32-S3) platform*. The contrast K1 vs K1v2 vs SB is load-bearing for the document's correctness.

Per-hit historical-preservation rationale:

1. **08_captain_preferences_and_feedback.md:61** — Bullet 5's heading is literally `**Confusing K1 vs K1v2 vs SB.**`. The bullet explains a Captain-flagged pitfall where agents conflated the three platforms. Rewriting `K1v2` → `K1 hardware` collapses the "K1 vs K1 hardware vs SB" contrast into ambiguity and destroys the corrective intent of the bullet. The embedded verbatim Captain quotation `"what are you uploading to? the k1v2 or the esp32s2?"` (P57367) must remain verbatim regardless of the rewrite decision elsewhere.

2. **03_k1_hardware_lgp_topology.md:67, 110, 129** — Audit doc explicitly compares the K1/SB v9 hardware (this branch) against the separately-tree'd K1v2/firmware-v3 platform. The line-110 hardware-generations table row IS the row for the separate K1v2 platform (ESP32-S3, dual 160-LED, design intent same as SB v9). Rewriting it to `K1 hardware / firmware-v3` makes the table self-contradictory (this branch's K1 is ESP32-S2, not ESP32-S3).

3. **05_prephase1_effects_history.md:9, 17, 111, 131** — Audit doc describes the "K1v2 firmware-v3 effect tree" (a tree outside this branch) and the "K1v2 Heartbeat arc" (a named observation cluster). These are proper-noun references to a *separate codebase / observation arc* — not to this branch's hardware. Rewriting them to `K1 hardware` collapses two distinct platforms into one and breaks the audit's traceability into claude-mem observation IDs.

**Default proposal (per Captain directive that K1v2 must not appear in active surfaces):** rewrite as listed above.

**Strong dissent recommendation (Lane 8 author):** these audit memos qualify as period-accurate historical record, not active surface. The renaming would degrade their forensic value (they document the *exact* confusion the rename is intended to prevent on a go-forward basis). Suggested compromise: add a top-of-file note to each audit memo stating `Historical document — references to "K1v2" denote the contemporaneous name for the separate ESP32-S3 firmware-v3 platform tree, prior to the 2026-05-23 naming convention that purges "K1v2" from active surfaces.` and leave the body text intact. This preserves both the rename directive (active surfaces purged) and the audit forensic record (historical narrative intact).

## Ambiguities Flagged for Captain Review

1. **Verbatim Captain quotation embedded in prose** — audit/understanding/08_captain_preferences_and_feedback.md:61 contains the Captain prompt `P57367: "what are you uploading to? the k1v2 or the esp32s2?"`. Quoted user speech is not a doc-body voice and arguably should NEVER be silently rewritten. Default: preserve the quotation verbatim, rewrite only the surrounding narrative. Confirm.

2. **Heading-level self-reference collapse** — audit/understanding/08_captain_preferences_and_feedback.md:61 bullet heading reads `**Confusing K1 vs K1v2 vs SB.**`. A literal rewrite produces `**Confusing K1 vs K1 hardware vs SB.**` which is logically nonsensical (K1 == K1 hardware). Options: (a) preserve the K1v2 token in this single heading as the only way to preserve the three-platform contrast, (b) rewrite the heading to `**Confusing K1 (this branch) vs K1 hardware (separate platform) vs SB (upstream).**`, (c) accept the nonsense rewrite. Recommended (b).

3. **Hardware-generations comparison table** — audit/understanding/03_k1_hardware_lgp_topology.md:110 row identifies the separate ESP32-S3 platform. If rewritten to "K1 hardware" without further qualifier, the table now has two rows both labelled "K1 hardware" (this branch's ESP32-S2 row presumably exists above it). Requires either a clarifying suffix (e.g. `K1 hardware (ESP32-S3 successor variant)`) or table-level restructuring. Captain decision required on disambiguation strategy across all of `audit/understanding/`.

4. **Observation-arc proper-noun cluster** — `K1v2 Heartbeat arc` (05_prephase1_effects_history.md:131) is the canonical name for a specific claude-mem observation cluster (obs #53361/#53386/#53407/#53423/#53438). Renaming it changes a proper-noun handle to a generic one. If observations themselves still refer to "K1v2 Heartbeat arc", the audit doc's reference name should match the source. Confirm whether the observation-arc handle is also being renamed in claude-mem; if not, the audit reference name should remain `K1v2 Heartbeat arc` to preserve queryability.

## Notes

- `fixed_firmware/` exists (`CHANGES.md`, `README.txt`) but contains zero hits — no purge action required there.
- `archive/` does NOT exist at the repo root. No action.
- `libraries/` contains 18 vendored .md files (FastLED, FixedPoints, M5ROTATE8) with zero hits — vendored docs are clean.
- All 8 hits are concentrated in 3 files under `audit/understanding/` authored by SSA agents during the 2026-05-20/21 audit cycle. The "active surface vs archive" boundary judgment is the key question: SSA audit memos document *contemporaneous* engineering investigations and are written with reference to the historical state of the codebase. Captain has directed K1v2 to be purged from active surfaces — but if audit memos are considered active reference docs (read by future agents to understand the branch's history), the purge applies; if they are considered historical record (snapshot of what was understood on the date authored), preservation is appropriate. Default in this report: rewrite per directive, with explicit flag for Captain override.
- No code-fenced `SB_K1V2_HARDWARE` identifier appears in scope (no `.h`/`.cpp` in scope; only docs/memos).
- No filename-level rename candidates in scope.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:SSA-Lane-8 | Created. Read-only audit of audit/, fixed_firmware/, archive/ (absent), and libraries/**/*.md for K1v2 occurrences. 8 hits total, all in audit/understanding/, all flagged as historical-preservation candidates with strong dissent recommendation favouring header-note compromise over body rewrite. |
