# Lane 6 — .claude/ agent surfaces K1v2 purge

Scope: .claude/** (CLAUDE.md, skills/, hooks/, agents/ — excl. settings.local.json)
Total hits: 9

Surfaces present in scope:
- `.claude/CLAUDE.md` — project instructions (high-interest)
- `.claude/skills/sensorybridge-doctrine/SKILL.md` — doctrine bridge skill (high-interest, load-bearing)
- `.claude/hooks/` — NOT PRESENT
- `.claude/agents/` — NOT PRESENT
- `.claude/settings.json` — read-only, not searched per scope rule
- `.claude/settings.local.json` — excluded (potential secrets)

## Hits

| File:Line | Current Text | Proposed Replacement | Category |
|-----------|--------------|---------------------|----------|
| .claude/CLAUDE.md:1 | `# K1v2 / Sensory Bridge — Project Instructions` | `# Sensory Bridge core firmware on K1 hardware — Project Instructions` | Document title (prose) |
| .claude/CLAUDE.md:8 | `Before any non-trivial Sensory Bridge / K1v2 firmware refactor, AP/VP change, audio pipeline change, visual pipeline change, S2/S3 migration work, timing/performance change, or multi-file agentic edit:` | `Before any non-trivial Sensory Bridge core firmware refactor on K1 hardware, AP/VP change, audio pipeline change, visual pipeline change, S2/S3 migration work, timing/performance change, or multi-file agentic edit:` | Prose (rule preamble) — see Ambiguity #1 |
| .claude/CLAUDE.md:11 | `2. Treat the LightwaveOS_Official doctrine as reference doctrine, not local K1v2 historical truth.` | `2. Treat the LightwaveOS_Official doctrine as reference doctrine, not local K1 hardware historical truth.` | Prose (rule) |
| .claude/CLAUDE.md:12 | `3. Treat the K1v2 forensic reconstruction as the local fork evidence base for Bloom/Waveform/K1v2 migration state.` | `3. Treat the K1 hardware forensic reconstruction as the local fork evidence base for Bloom/Waveform/K1 hardware migration state.` | Prose (rule) — see Ambiguity #2 |
| .claude/skills/sensorybridge-doctrine/SKILL.md:3 | `description: Apply the LightwaveOS Sensory Bridge doctrine bridge and product north star before non-trivial Sensory Bridge / K1v2 firmware refactors, AP/VP changes, S2/S3 migration work, audio/visual pipeline changes, performance tuning, or multi-file agentic edits.` | `description: Apply the LightwaveOS Sensory Bridge doctrine bridge and product north star before non-trivial Sensory Bridge core firmware refactors on K1 hardware, AP/VP changes, S2/S3 migration work, audio/visual pipeline changes, performance tuning, or multi-file agentic edits.` | Skill frontmatter description |
| .claude/skills/sensorybridge-doctrine/SKILL.md:28 | `1. K1v2 current local source and local forensic report decide current fork state.` | `1. K1 hardware current local source and local forensic report decide current fork state.` | Skill prompt — priority-order rule (load-bearing) |
| .claude/skills/sensorybridge-doctrine/SKILL.md:32 | `5. If doctrine and local K1v2 evidence conflict, report the conflict instead of silently choosing one.` | `5. If doctrine and local K1 hardware evidence conflict, report the conflict instead of silently choosing one.` | Skill prompt — priority-order rule (load-bearing) |
| .claude/skills/sensorybridge-doctrine/SKILL.md:37 | `2. K1v2 local evidence touched.` | `2. K1 hardware local evidence touched.` | Skill output-schema section header |
| .claude/skills/sensorybridge-doctrine/SKILL.md:44 | `Do not re-mine Git history unless a claim lacks evidence in the doctrine, canonical audit, and K1v2 forensic report.` | `Do not re-mine Git history unless a claim lacks evidence in the doctrine, canonical audit, and K1 hardware forensic report.` | Skill prompt — guardrail rule |

## File Renames Required

None. No file or directory under `.claude/` (in scope) contains `k1v2` / `K1v2` / `k1_v2` in its name.

Verified:
- `.claude/CLAUDE.md` — no rename needed
- `.claude/skills/sensorybridge-doctrine/SKILL.md` — no rename needed
- `.claude/skills/sensorybridge-doctrine/` — no rename needed
- `.claude/hooks/`, `.claude/agents/` — not present, nothing to rename

## Skill Prompt Implications

The `sensorybridge-doctrine` SKILL.md is the load-bearing doctrine gate referenced by `.claude/CLAUDE.md` and by the user's `MEMORY.md` re-trigger rules. K1v2 appears in three structurally important locations within that skill's prompt:

1. **Frontmatter `description:` (line 3)** — this is the text the harness uses to surface the skill in `Available skills` listings and to trigger auto-suggestion. Changing "Sensory Bridge / K1v2 firmware refactors" to "Sensory Bridge core firmware refactors on K1 hardware" changes the *invocation surface* of the skill, not just its body. Captain should confirm the new phrasing matches the intended trigger semantics.

2. **Priority-order rule list (lines 28, 32)** — this list is the conflict-resolution hierarchy the skill enforces. "K1v2 current local source" and "local K1v2 evidence" are operative terms used downstream by any agent invoking `/sensorybridge-doctrine`. Renaming to "K1 hardware" is consistent with Captain's directive that this project is Sensory Bridge core firmware running on K1 hardware (not "K1v2 lane"). The semantic anchor remains "current local source" / "local evidence"; only the hardware label changes.

3. **Skill output schema (line 37)** — `2. K1v2 local evidence touched.` is a header in the *mandatory output template* the skill imposes on the calling agent. Every downstream agent that has ever run `/sensorybridge-doctrine` and emitted this section header will now emit `K1 hardware local evidence touched.` instead. Surface this so Captain knows the audit-trail string in past artifacts (`findings/`, `progress.md`, etc.) will diverge from the new template.

4. **Guardrail rule (line 44)** — `K1v2 forensic report` refers to the local forensic reconstruction file at `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html`. The filename itself does NOT contain `k1v2`, so renaming the in-prose reference to "K1 hardware forensic report" introduces no path drift. Safe to rename.

## Ambiguities Flagged for Captain Review

1. **CLAUDE.md:8 "Sensory Bridge / K1v2 firmware refactor" phrasing.** The current phrase reads as a compound: *Sensory Bridge OR K1v2 firmware refactor*. The proposed replacement "Sensory Bridge core firmware refactor on K1 hardware" collapses the slash construction. Captain may prefer one of:
   - (a) `Sensory Bridge core firmware refactor on K1 hardware` (proposed above — treats Sensory Bridge core firmware as the unified subject)
   - (b) `Sensory Bridge / K1 hardware firmware refactor` (mechanical replacement, preserves slash construction; reads as ambiguously parallel)
   - (c) `Sensory Bridge firmware refactor` (drops the K1 hardware qualifier entirely; relies on project identity to imply K1 hardware)

   Recommend (a) per Captain's 2026-05-23 directive that this project IS "Sensory Bridge core firmware on K1 hardware." Flagged because the same pattern recurs at SKILL.md:3.

2. **CLAUDE.md:12 has two K1v2 occurrences on the same line.** `Treat the K1v2 forensic reconstruction as the local fork evidence base for Bloom/Waveform/K1v2 migration state.` The second occurrence (`Bloom/Waveform/K1v2 migration state`) names a specific migration codepath. Captain may want the second one to be either:
   - (a) `Bloom/Waveform/K1 hardware migration state` (proposed above)
   - (b) `Bloom/Waveform/S2-to-S3 migration state` (more precise — it IS the S2-to-S3 hardware migration this evidence base captures)
   
   Recommend (a) for now to keep mechanical consistency; (b) is a semantic upgrade that should be done deliberately, not as part of a purge sweep.

3. **CLAUDE.md:1 title — "Sensory Bridge core firmware on K1 hardware".** The Lane 6 brief recommends this phrasing per Captain's directive. Confirmed by claude-mem observation #54226 (2026-05-23 7:01p) "Sensory Bridge Core Firmware on K1 Hardware — Project Identity Doctrine". Recommended as the canonical title.

## Notes

- `.claude/CLAUDE.md` and `.claude/skills/sensorybridge-doctrine/SKILL.md` are tightly coupled: the project CLAUDE.md tells agents to invoke the skill, and the skill enforces the doctrine gate. Both files should be updated in the same edit batch to avoid a window where the invocation surface and the skill body disagree on terminology.
- No K1v2 references exist in `.claude/hooks/` or `.claude/agents/` because those directories are not present in this project.
- `.claude/settings.json` was not read per scope rules (read-only OK but not modified, and not searched). If Captain wants to confirm no K1v2 references exist there, that requires a separate explicit instruction.
- All proposed replacements preserve the load-bearing semantics: the doctrine gate, priority-order list, output schema, and guardrail rule structure remain identical; only the hardware-label token changes from "K1v2" to "K1 hardware".
- No code-fenced identifiers (`SB_K1V2_HARDWARE` etc.) or filename references (`compile-k1v2-arduino.sh` etc.) were found inside the `.claude/` surface. All 9 hits are prose / instruction text.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:lane-6-sweep | Created. SSA Lane 6 sweep: 9 K1v2 hits across .claude/CLAUDE.md (4) and .claude/skills/sensorybridge-doctrine/SKILL.md (5). 0 file renames required. 3 ambiguities flagged. |
