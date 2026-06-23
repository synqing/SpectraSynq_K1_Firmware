---
abstract: "P0 source-only governance preflight for using Spec Kit in SensoryBridge as a controlled specification, acceptance, and evidence-gating layer."
evidence_tier: "source-only"
proof_boundary: "source-only"
created: "2026-06-01"
status: "prepared"
---

# P0 Spec Kit Governance Preflight

## Changelog

| Date | Change | Proof boundary |
|---|---|---|
| 2026-06-01 | Initial governance preflight prepared from the committed deployment review packet and live repo inspection. | source-only |

## Scope

[FACT] This preflight governs Spec Kit use in `/Users/spectrasynq/SensoryBridge-main 9` before any feature spec is started. It is a documentation artefact only. It does not run Spec Kit commands, update `.specify`, change generated skills, mutate firmware source, build, upload, flash, open serial, calibrate, restart services, or maintain memory.

[FACT] The committed review packet says Spec Kit should be deployed as a controlled specification, acceptance, and evidence-contract layer, not as an implementation runner, issue-sync runner, workflow automation surface, or agent-context mutator. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:8-14`.

[FACT] The P0 backlog item is this governance preflight: freeze source-truth order, ignore unsafe generated surfaces, resolve placeholder constitution posture, and record dirty-tree baseline before feature specs. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:61-67`.

## Live Repo Snapshot

[FACT] Live branch before writing this file: `feat/gdft-harness`, tracking `origin/feat/gdft-harness`, `ahead 10`. Live HEAD before writing this file: `03adb3dae84cec3c25a9c175a116bd5791325232`. Source: local `git branch --show-current`, `git status --porcelain=v1 -b`, and `git rev-parse HEAD` command evidence from 2026-06-01.

[FACT] The review packet commit exists and is contained by the current branch: `1da151b9f08128cef371b660a099800af4ec3df4 docs: add SensoryBridge Spec Kit deployment review`. Source: local `git rev-parse --verify 1da151b^{commit}`, `git branch --contains 1da151b`, and `git show --stat 1da151b` command evidence from 2026-06-01.

[FACT] Dirty tree before this file was written was not clean. Existing dirt included modified `AGENTS.md` and `.claude/CLAUDE.md`; untracked root `CLAUDE.md`; untracked Spec Kit files under `.agents/skills/speckit-*`, `.claude/skills/speckit-*`, and `.specify/**`; untracked Smart Auto A/B logs, videos, frame directories, and runtime evidence under `docs/forensics/runtime-evidence/`; and an untracked parallel-agent incident doc. Source: local `git status --porcelain=v1 -b` command evidence from 2026-06-01.

[FACT] The `.specify/memory/constitution.md` file is still mostly placeholder text. Its product principles and governance section retain upstream placeholders, while only `Reasoning Protocol (Decision-Gate -> Mental-Model Bindings)` is marked as ratified. Source: `.specify/memory/constitution.md:1-41`, `.specify/memory/constitution.md:43-58`, and `.specify/memory/constitution.md:60-67`.

[FACT] `.specify/extensions.yml` has `auto_execute_hooks: false`; the only listed hooks are disabled optional `speckit.agent-context.update` hooks after specify and plan. Source: `.specify/extensions.yml:1-21`.

[FACT] `.specify/workflows/workflow-registry.json` has an empty workflow registry. Source: `.specify/workflows/workflow-registry.json:1-4`.

[FACT] `speckit-implement`, `speckit-taskstoissues`, and `speckit-agent-context-update` directories exist in both `.agents/skills/` and `.claude/skills/`, but their `SKILL.md` entrypoints were absent in live filesystem inspection before this file was written. Source: local `/usr/bin/find .agents/skills .claude/skills -maxdepth 2 -name SKILL.md -path '*speckit*' -print` and `/usr/bin/find ... -maxdepth 1 -type d -name 'speckit-*'` command evidence from 2026-06-01.

## Source-Truth Order

All Spec Kit artefacts in this repository must use this source-truth order:

1. [FACT] Captain's current instruction in the active conversation.
2. [FACT] Repo instructions: `AGENTS.md`, root `CLAUDE.md`, and `.claude/CLAUDE.md`. `AGENTS.md` says `.claude/CLAUDE.md` is canonical if they diverge. Source: `AGENTS.md:1-6`; `CLAUDE.md:1-13`.
3. [FACT] Current source files, checked-in runtime evidence, and local command evidence in this checkout.
4. [FACT] Git history and checked-in forensics docs, including the Spec Kit deployment review packet committed at `1da151b`.
5. [FACT] Local memory and claude-mem only as routing evidence unless reverified against current repo or runtime evidence. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/00-swarm-brief.md:25-32`; `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-04-claude-mem-memory-history.md:64-72`.
6. [FACT] Generated Spec Kit artefacts and generated skill guidance. These never outrank repo instructions, current source, runtime evidence, or hardware proof. Source: `AGENTS.md:188-193`; `CLAUDE.md:7-13`.

[FACT] The placeholder constitution is not a complete SensoryBridge constitution. Until Captain ratifies a full constitution update, only its Reasoning Protocol section is authoritative, and it augments rather than replaces `sensorybridge-doctrine` and `k1-firmware-change-gate`. Source: `.specify/memory/constitution.md:43-58`.

## Allowed Spec Kit Surfaces

Allowed surfaces are manual specification and analysis surfaces only. Each use still requires the active Captain task to name or clearly imply the relevant lane.

| Surface | Allowed use | Allowed writes | Required guard |
|---|---|---|---|
| `speckit-specify` | Create or update validation/evidence specs under `specs/`. | `specs/**/spec.md`, `specs/**/checklists/requirements.md`, and only the minimum generated feature pointer if the generated command is explicitly used. | Hooks must remain skipped/disabled. The prompt must carry this preflight's source-truth order, blocked surfaces, proof labels, and stop conditions. |
| `speckit-clarify` | Resolve underspecified spec decisions before planning. | Current `specs/**/spec.md` and existing requirements checklist state only. | Ask only material questions; do not convert strategic uncertainty into implementation. |
| `speckit-checklist` | Create requirements-quality checklists, not implementation test plans. | `specs/**/checklists/*.md`. | Checklist items test whether requirements are complete, clear, consistent, measurable, and traceable. Source: `.agents/skills/speckit-checklist/SKILL.md:11-30`, `.agents/skills/speckit-checklist/SKILL.md:132-183`. |
| guarded `speckit-plan` | Produce source-only/spec-only planning artefacts after a spec is accepted. | `specs/**/plan.md`, `specs/**/research.md`, `specs/**/data-model.md`, `specs/**/contracts/**`, and `specs/**/quickstart.md` when relevant. | Agent-context update must be explicitly skipped or separately approved. Generated guidance includes an agent-context update step. Source: `.agents/skills/speckit-plan/SKILL.md:54-68`, `.agents/skills/speckit-plan/SKILL.md:147-150`. |
| `speckit-tasks` | Generate dependency-ordered tasks after accepted spec and plan artefacts. | `specs/**/tasks.md`. | Every task must include `proof_boundary`, `hardware_touch_policy`, and explicit stop conditions. No generated issue sync. Source: `.agents/skills/speckit-tasks/SKILL.md:54-87`, `.agents/skills/speckit-tasks/SKILL.md:136-212`. |
| `speckit-analyze` | Read-only consistency review across spec, plan, and tasks. | None. | Output only analysis unless Captain explicitly approves remediation edits. Source: `.agents/skills/speckit-analyze/SKILL.md:54-63`, `.agents/skills/speckit-analyze/SKILL.md:164-205`. |

## Blocked Spec Kit Surfaces

These surfaces are blocked unless Captain gives a later explicit approval that names the exact surface and scope:

- `speckit-implement`, any implementation runner, or any generated task execution workflow.
- `speckit-taskstoissues`, task-to-issue sync, issue automation, or publication to remote systems.
- `speckit-agent-context-update` and any edit to `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, generated skill files, or `.specify` configuration by generated agent-context tooling.
- Extension hooks, even optional hooks, unless Captain explicitly approves a named hook execution. Current hooks are disabled and must remain inert by default. Source: `.specify/extensions.yml:1-21`.
- Workflow automation from `.specify/workflows/`. The registry is currently empty and should stay non-authoritative by default. Source: `.specify/workflows/workflow-registry.json:1-4`.
- `/speckit-constitution` or direct constitution replacement until Captain explicitly ratifies SensoryBridge product principles and governance text. The current constitution still contains placeholders. Source: `.specify/memory/constitution.md:1-41`, `.specify/memory/constitution.md:60-67`.
- Any Spec Kit flow that mutates firmware source, generated build configuration, scripts, hooks, memory stores, Chroma/claude-mem state, services, serial/device state, calibration state, flash contents, or remote systems.

## Required Labels

Every Spec Kit spec, plan, task, checklist, and analysis result must include these fields when relevant:

- `source_truth_status`: `repo-verified`, `runtime-verified`, `memory-derived`, or `unresolved`.
- `proof_boundary`: one of the labels below.
- `hardware_touch_policy`: `none`, `read-only-observe`, `identity-verified-runtime`, or `blocked-pending-Captain-approval`.
- `allowed_writes`: explicit paths or `none`.
- `blocked_surfaces`: generated commands or operational surfaces that must not run.
- `runtime_evidence_required`: exact serial, AP, VPAB/VPABB, trace-dev, video, or Captain-judgement evidence needed for promotion.
- `perception_gate`: perceived output, materiality threshold, collapse points, and stop criteria.
- `rollback_or_preservation_plan`: required when a lane could affect calibration, saved config, known-good dual-channel behaviour, palette ownership, or hardware state.

### `proof_boundary`

| Label | Meaning | Explicit non-claim |
|---|---|---|
| `spec-only` | Requirements, acceptance criteria, checklist, or decision scaffold only. | No current-source, build, upload, runtime, or visual claim. |
| `source-only` | Current files, docs, git, and checked-in evidence were inspected. | No compile, upload, runtime, or visual claim. |
| `compile-only` | A named build command passed, normally `pio run -e k1_hardware` for production K1 work. | No upload, runtime behaviour, or visual proof. |
| `upload-proof` | Firmware was uploaded to a verified hardware target. | No runtime behaviour or visual proof. |
| `runtime-proof` | Runtime serial/AP/VPAB/VPABB/trace evidence was captured on a verified target. | No product visual judgement unless separately labelled. |
| `visual-proof` | LGP video review, Captain A/B judgement, or equivalent visual evidence supports the claim. | No compile/upload/runtime claim unless separately evidenced. |

[FACT] Compile/upload cannot be treated as runtime proof; runtime proof needs matching serial, video, or timing evidence. Source: `AGENTS.md:82-84`; `.claude/CLAUDE.md:8-15`.

[FACT] Trace/harness instrumentation is non-shippable and must be labelled separately when used. Source: `AGENTS.md:30-47`; `.claude/CLAUDE.md:19-25`.

## Hardware-Touch Policy

Default `hardware_touch_policy` for Spec Kit governance and feature-spec work is `none`.

Hardware touch is blocked until a later Captain instruction explicitly approves the exact action and target. Hardware touch includes serial monitor access, firmware upload/flash, flash erase, device-write commands, runtime command writes, calibration commands, service restarts, and any action that can change target-device state.

Before any approved hardware touch, the agent must verify target identity by port plus stable hardware identity such as USB MAC, adapter serial, chip ID, board role, or another captured identity signal. A port name alone is insufficient. Source: `AGENTS.md:73-80`; `.claude/CLAUDE.md:33-45`.

Calibration commands that assume silence are never auto-fired. `start_noise_cal`, the `N`/`Y` calibration hotkey path, and equivalent calibration flows require Captain to confirm a silence window before execution. Source: `AGENTS.md:68-71`; `.claude/CLAUDE.md:27-31`.

AP-only is fixed. A Spec Kit artefact must stop if it proposes STA/network scope creep or treats AP-only as unresolved. Source: Captain active instruction for this task; `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:214-221`.

## Stop Conditions

Stop the Spec Kit flow and report `blocked` or `approval` if any of the following occurs:

- A generated command would mutate firmware, flash hardware, run serial commands, calibrate, erase flash, restart services, rebuild memory, execute hooks, sync tasks to issues, or update agent context without explicit Captain approval. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:267-277`.
- A spec cannot name the perceived product output and materiality threshold. Mechanism-only feature specs are not acceptable for this repo. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-05-system-design-perception-prioritisation.md:41-56`.
- Acceptance depends on ambiguous VPAB `render_us` semantics before the evidence contract resolves them. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:104-117`.
- A lane weakens centre-origin propagation, introduces rainbow or hue-wheel behaviour, adds heap allocation to render paths, enables STA/network scope creep, hides compile/upload/runtime/visual proof boundaries, or ships trace/harness-only code. Source: Captain active instruction for this task; `AGENTS.md:30-84`; `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:214-221`.
- Memory-derived evidence conflicts with current source/runtime evidence or would be encoded as verified product truth without repo/runtime verification. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-04-claude-mem-memory-history.md:64-80`.
- Calibration state is invalid or unknown before proof capture. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-05-system-design-perception-prioritisation.md:199-221`.
- Secondary-channel work risks overwriting the preserved known-good dual-channel look without an explicit recovery/profile plan. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-05-system-design-perception-prioritisation.md:223-245`.
- `.specify/extensions.yml` enables any hook, `.specify/workflows/` gains active workflows, or a generated skill asks to update agent context and Captain has not explicitly approved that exact action.
- The placeholder constitution is treated as a complete SensoryBridge constitution or as higher authority than `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, source, runtime evidence, or hardware proof.

## Next Start: Smart Auto Product Validation v1

Start this next as the first validation-only Spec Kit feature. Do not run implementation, build, upload, serial, calibration, capture, or hardware mutation while creating the spec.

Required start posture:

- `proof_boundary`: `spec-only` while drafting; `source-only` only for claims tied to current files, checked-in runtime evidence, or review packet citations.
- `hardware_touch_policy`: `none`.
- `source_truth_status`: use `repo-verified` for current files/evidence, `memory-derived` only for routing evidence, and `unresolved` for the final product verdict until visual evidence is reviewed.
- `allowed_writes`: `specs/001-smart-auto-product-validation-v1/spec.md`, `specs/001-smart-auto-product-validation-v1/checklists/requirements.md`, and any capture matrix/checklist under that same feature directory if Captain approves starting the Spec Kit feature. If using generated `/speckit-specify`, account for its feature-pointer write explicitly.
- `blocked_surfaces`: implementation, task-to-issue sync, hooks, agent-context update, hardware touch, calibration, service restarts, memory maintenance.

The spec must decide whether current Smart Auto v2 is visibly better than L1/manual baseline on the actual K1 LGP. Acceptance must include Captain/video A/B over at least two of three clip classes, no white/grey washout, no strobe or arbitrary thrash, no colour-clarity regression, manual-owner respect, no accepted evidence with over/dropped/overflowed frames, and separate labels for production scalar logs, harness captures, and human visual judgement. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:81-102`.

The spec must apply the ratified Reasoning Protocol for "Is Smart Auto v2 visibly better than baseline?": pre-register "better" per clip class, report calibrated confidence, treat VPAB as a map rather than the perceived result, and guard confirmation bias. Source: `.specify/memory/constitution.md:49-52`.

Stop Smart Auto spec work if it needs new hardware capture or target interaction before Captain explicitly approves that separate hardware-touch lane, or if it tries to treat ambiguous VPAB timing semantics as a hard pass/fail gate before the VPAB contract exists.

## Next Start: VPAB Render-Budget Semantics And Final-Byte Evidence Contract

Start this second, after the Smart Auto validation spec has been drafted or if Smart Auto acceptance needs a trusted timing/evidence contract before it can be closed. This is an evidence-contract spec first; parser/test work comes later.

Required start posture:

- `proof_boundary`: `source-only` for semantics derived from current files and checked-in evidence; `spec-only` for proposed taxonomy and acceptance rules until accepted.
- `hardware_touch_policy`: `none`.
- `allowed_writes`: `specs/002-vpab-render-budget-semantics/spec.md`, `specs/002-vpab-render-budget-semantics/checklists/requirements.md`, and contract/taxonomy docs under that same feature directory if Captain approves starting the Spec Kit feature.
- `blocked_surfaces`: parser implementation, firmware edits, builds, uploads, hardware capture, hooks, task-to-issue sync, agent-context update, service restarts, memory maintenance.

The spec must define `render_us`, `frame_us`, `show_us`, `over`, `dropped`, and `overflowed`; classify impossible samples, known harness artefacts, trace-dev artefacts, and real budget failures; and separate final-byte metrics from pre-output scalar churn. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/06-final-sensorybridge-spec-kit-deployment-review.md:104-117`; `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-05-system-design-perception-prioritisation.md:177-197`.

The spec must state when a timing row blocks feature promotion, when it is quarantined as an artefact, and what evidence class is required before Smart Auto, EdgeMixer, VME, or secondary work can cite it. Source: `docs/forensics/2026-06-01-spec-kit-deployment-review/SB-SK-05-system-design-perception-prioritisation.md:299-303`.

Stop VPAB spec work if it proposes trace/harness output as production proof, claims visual success from pre-output metrics alone, or requires parser/firmware implementation before Captain approves a separate implementation task.
