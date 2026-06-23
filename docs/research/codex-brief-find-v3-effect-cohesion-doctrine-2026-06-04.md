---
abstract: "Codex task brief (2026-06-04): locate THE canonised firmware-v3 'effect cohesion / direction-of-travel / motion-logic' reference the Captain remembers from the K1 FE-Launch effect-fixing phase (~2026-03 to 2026-04), extract its verbatim conditions, and write a FOUND doc. Read-only on the v3 repo. Offloaded to Codex to preserve Claude budget."
---

# Codex task — find the firmware-v3 "effect cohesion / motion doctrine" reference

## Why this exists
The K1 is a music-reactive LED product (Light Guide Plate, 160 px, centre-origin). The active firmware is a Sensory-Bridge-derived fork; the **prior** main line is **firmware-v3** (`Lightwave-Ledstrip`). The Captain (founder) recalls a **canonised reference/ruleset** from the firmware-v3 days — created **~2 to 3 months ago (≈ 2026-03 to 2026-04)**, during the **"picking and fixing effects for the K1 FE Launch"** phase. In his words:

> An agent, working from my very exacting decomposition of what I saw in chaotic effects, **fingered the EXACT problem** — *one effect trying to do far too many things ends up doing nothing properly* — and **named the exact conditions that effects MUST conform to in order to appear cohesive (and visually impactful): how the direction of travel + motion logic MUST make sense.**

He is sure this was canonised into a document/ruleset. A *recent* (2026-06-02) `k1-motion-canon` skill is **NOT** it (too new). Find the **original v3-era** reference.

## Your task
1. **Identify THE reference** (the canonised cohesion / direction-of-travel / motion-logic ruleset) — and its companion docs.
2. **Extract the canonised conditions verbatim** (the rules an effect MUST conform to).
3. Write a FOUND report.

## Where to look (READ-ONLY)
Repo: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip` (work in `firmware-v3/`).
Use the full git history across ALL branches: `git -C <repo> log --all ...`, `git -C <repo> show <sha>:<path>`, `git -C <repo> grep`.

**Pre-located candidates (with add-dates) — start here, but do not assume one; confirm by reading + matching the Captain's description:**
- `2026-03-04` — `firmware-v3/docs/EFFECT_DEVELOPMENT_STANDARD.md` + `firmware-v3/docs/STIMULUS_CONTROL_CONTRACT.md` (commit `39d6dcee` "add effect development standard, stimulus contract, CI check"). **Top suspect** — "conditions effects MUST conform to," exactly 3 months ago.
- `2026-03-24` — commit `aed805bb` "rewrite 10 effects — direct audio, single smoothing, max follower" (the effect-fixing-for-cohesion pass; "single smoothing" ≈ one coherent behaviour).
- `2026-03-17` — `firmware-v3/docs/effects-catalog/PATTERN_TAXONOMY.md`.
- `2026-04-26` — `firmware-v3/docs/research/SB_ES_MOTION_MECHANICS_TAXONOMY_2026-04-26.md` + `..._BRAINSTORM_CATALOGUE_2026-04-26.md`.
- `2026-04-30` — `firmware-v3/docs/research/spazz_redesign_2026-04-30/SSA1_canonical_motion_doctrine.md` + `SSA4_working_lgp_motion_audit.md` ("spazz" = an over-loaded effect; this redesign packet is a strong match).
- direction-logic fix commits: `1d3dba28` "correct center-origin wave motion in 5 effects", `29ea5683` "direction bugs … LGP interference".
- Also check: `firmware-v3/docs/GOOD_LIGHT_SHOW_TAXONOMY.md`, `firmware-v3/docs/EFFECT_AUTHORING_STANDARD_V2.md`, `firmware-v3/docs/EFFECT_FRAMEWORK_STANDARD.md`.

Broaden via `git -C <repo> log --all -i --grep=cohes|--grep="direction"|--grep=motion|--grep="single"|--grep="too many"` if none of the above is the exact match. Claude-mem is likely NOT reachable from Codex — the git history + docs are authoritative; rely on them.

## Match criteria (the Captain's descriptors — the doc must hit these)
- States effects fail when one effect does **too many things** (loss of cohesion).
- Names **explicit conditions effects MUST conform to** to be cohesive + visually impactful.
- Governs **direction of travel** and **motion logic** ("must make sense").
- Born from **decomposition of real v3 effects** during the **FE-Launch effect-pick/fix** phase.
- Dated **~2026-03 to 2026-04**.

## Output
Write a report to: `/Users/spectrasynq/SensoryBridge-main 9/docs/research/2026-06-04-v3-effect-cohesion-doctrine-FOUND.md`, containing:
1. **THE reference** — exact path(s), first-commit sha + date, the work-phase context.
2. **The verbatim canonised conditions** — quote the actual rules (the direction-of-travel + motion-logic + cohesion + one-job conditions). This is the payload.
3. **Companion docs** that form the ruleset.
4. **Confidence** — which of the Captain's descriptors each candidate hits; rank if several plausible.
5. **Port note** — how these conditions map onto the current SensoryBridge fork (`SPECTRASYNQ_K1_FIRMWARE/`, `light_mode_*` effects, centre-origin 160px LGP) and where the current `docs/architecture/effect-decomposition/` guidebook + `k1-motion-canon` skill already encode (or miss) them.

## Constraints
Read-only on the v3 repo (no edits/commits there). British English. Anchor every claim (file:line / commit / doc§). If the top suspect isn't the match, say so and name the real one.
