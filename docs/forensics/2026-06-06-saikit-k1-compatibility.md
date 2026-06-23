---
abstract: "SummonAI Kit compatibility audit for SensoryBridge K1 agent artifacts. Saikit generated useful hook/slash/subagent scaffolding, but also overwrote tracked bespoke K1 skills with generic fallback skills. The protected K1 skills were restored, the hook now routes K1 prompts to the load-bearing skills, and a smoke test protects the route."
---

# SummonAI Kit K1 Compatibility Audit

Date: 2026-06-06

## Verdict

SummonAI Kit artifacts are useful only behind a K1 protection layer.

Raw generated fallback skills must not replace these tracked, hand-authored
skills:

- `.claude/skills/codex-offload/SKILL.md`
- `.claude/skills/k1-firmware-change-gate/SKILL.md`
- `.claude/skills/sensorybridge-doctrine/SKILL.md`
- `.claude/skills/ssa-management/SKILL.md`
- `.claude/skills/ssa-management/references/v-octave-near-disaster.md`

## Compatibility Fix

The Saikit prompt hook now routes:

- K1 firmware, AP, VP, render, audio, LED, serial, upload, tempo, beat,
  onset, chord, GDFT, I2S, and FastLED prompts to
  `k1-firmware-change-gate`
- SensoryBridge doctrine, perceptual impact, musical responsiveness, visual
  captivation, motion memory, colour clarity, dual-channel, and AP/VP refactor
  prompts to `sensorybridge-doctrine`
- subagent, SSA, fan-out, delegation, agent claim, and re-run prompts to
  `ssa-management`
- Codex exec, offload, heavy reading, bounded read, and context overflow prompts
  to `codex-offload`

The smoke harness is:

```bash
bash .claude/hooks/smoke-test-skill-instructions-hook.sh
```

Expected current result:

```text
PASS k1-firmware-routing
PASS firmware-upload-routing
PASS ssa-routing
PASS codex-offload-routing
```

## Slash Commands

The Saikit slash commands are acceptable only with the K1 protected-artifact
overlay now documented in:

- `.claude/commands/saikit-update.md`
- `.claude/commands/saikit-workflows.md`

After any Saikit update or workflow write that touches `.claude/`, restore or
verify the protected skill files and rerun the smoke harness.

## Generated Agent Assessment

Candidate keepers after frontmatter hardening:

- `code-reviewer`
- `debugger`
- `performance-engineer`
- `refactor-agent`
- `test-engineer`
- `product-strategist`

Conditional keeper:

- `marketing-strategist`, only for K1/Kickstarter copy work where product truth
  is explicitly grounded in `sensorybridge-doctrine`.

Do not stage the broad generated `.claude/skills/*` fallback dump unless each
skill is reviewed individually. The generated `references/patterns.md` and
`references/workflows.md` files for the protected K1 skills are generic filler
and are not part of the protected skill truth.

## Maintenance Rule

Saikit can refresh scaffolding. Git-tracked K1 doctrine decides whether the
refresh is admissible.
