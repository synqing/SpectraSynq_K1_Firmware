---
name: cowork-os-spectrasynq-k1
description: "Use when scoping any K1 × CoWork OS question — K1 firmware, K1 Visual Bible, SongAware DSP, SynqMatrix, effect QA pipelines. Resolves what CoWork OS can and cannot touch in the K1 product-truth stack and which Claude Code skills own which loops. K1 is entertainment technology (audio-reactive LGP lamp), not a smart-home / Matter / DLE / smart-bulb input — ecosystem signals are watchlist-only per `project_k1-positioning-entertainment-not-smart-bulb.md`. Composes cowork-os-safety + cowork-os-memory + cowork-os-workbench + cowork-os-providers under the live production-control-plane."
---

# CoWork OS — SpectraSynq K1 Operating Skill

## When to Use This Skill

Use when any of the following is on the table:

- a CoWork workflow that *might* touch K1 firmware, the archived Visual Bible (`/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/`), the live content-production pipeline (`/Users/spectrasynq/content-production-pipeline/blender/`), the archived marketing repo (`/Users/spectrasynq/SpectraSynq/archive/K1_Marketing.archived_2026-05-14/`), K1 production source, or signing keys
- review of a K1 LGP effect, SongAware Goertzel/beat path, SynqMatrix layout, register-map regression, or hardware bring-up
- "can CoWork do this for K1?" / "should CoWork own this K1 artifact?" / "drive ESP32 flashing from a CoWork workspace?"
- mounting the archived Visual Bible (`/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/`), the live content-production pipeline (`/Users/spectrasynq/content-production-pipeline/blender/`), or any other K1 product-truth source as a CoWork workspace
- K1 marketing copy / FAQ / pitch authored in a CoWork Document Workbench
- an MCP connector exposing K1 firmware build status, render-rig health, or SongAware test-fixture output to CoWork

This is the K1-vs-CoWork operating contract. K1 = ESP32-S3 dual-strip Light Guide Plate audio-reactive lamp + SongAware Goertzel/beat tracking + SynqMatrix engine + the K1 Visual Bible. K1 is entertainment technology — never a smart-home / Matter / DLE / smart-bulb input (see Anti-Patterns). Firmware build/flash/OTA, register verification, DSP correctness, render-path safety, and hardware bring-up live in Claude Code skills (`esp32-actor-model`, `k1-effect-development`, `k1-ap-websocket-stack`, `signal-processing-verification`, `dsp-performance-profiling`, `register-map-verification`, `peripheral-bus-debugging`, `hardware-bringup`, `firmware-crash-analysis`, `firmware-profiling`, `spectrasynq-audio-pipeline`, `m5rotate8-encoder-system`, `dsp-test-fixtures`, `audio-visualisation-debug`). CoWork OS has no equivalent substrate. This skill draws the line.

## What This Skill Does

Composition skill — applies four Tier A skills to a single workstream:

| Tier A skill | Draw from it for |
|---|---|
| `cowork-os-safety` | `production-control-plane.ts` verification (`COWORK_PRODUCTION_CONTROLS=1`, USD 1.00 / 100k-token default ceilings, `COWORK_PRODUCTION_ALLOWED_DOMAINS`); workspace permission defaults; Admin Policies; permission-mode matrix |
| `cowork-os-memory` | KG auto-extraction unguardedness (governance-sentinel-tracked); Subconscious / Heartbeat / Awareness env-disable inertness; mount policy |
| `cowork-os-workbench` | Workbench surface map; Computer Use blast radius; `media://`; permission template |
| `cowork-os-providers` | Anthropic + OpenAI + OpenRouter chain; production-control budget enforcement; SecureSettings |

If this skill restates Tier A mechanics, you are duplicating. Stop, link, move on.

## K1 Reality Check — CoWork OS Is Not a K1 Firmware Environment

The most expensive mistake on this surface is confusing CoWork OS for a K1 development substrate. It is not.

| K1 need | CoWork OS coverage |
|---|---|
| ESP32-S3 PlatformIO / ESP-IDF build | None |
| USB serial / JTAG flash / OTA push | None — sandbox-exec cannot tunnel USB; one mis-flash bricks a board |
| FastLED render path / LGP rendering | None — no render simulator, no LED preview, no LGP optics model |
| SongAware Goertzel + beat + tactus PLL | None — owned by `spectrasynq-audio-pipeline` + `signal-processing-verification` (Claude Code) |
| Register-map verification | None — owned by `register-map-verification` (Claude Code) |
| Crash dump / guru meditation / watchdog analysis | None — owned by `firmware-crash-analysis` (Claude Code) |
| Hardware bring-up | None — owned by `hardware-bringup` (Claude Code) |
| K-Cycles render orchestration | None — see Render-to-Content Observer department (`03_AGENT_DEPARTMENT_CHARTER.md`) |
| Visual Bible authority surface (archive `/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/`; live successor `/Users/spectrasynq/content-production-pipeline/blender/`) | Hostile — KG auto-extraction has no opt-out; never let CoWork own product truth |

Per `GAP_ANALYSIS.md` Gaps 1-3: hardware loops, device validation, and K-Cycles are N/A for CoWork OS. Anyone proposing CoWork as substrate is mis-scoping; route to Claude Code skills. CoWork OS is at most a coordination shell around K1 work — and even that role is bounded.

## Ship path required (Captain 2026-08-17)

Never tell Captain a K1 result does not mean ship / promote / close without the remaining numbered ship path in the same answer. Skill `/ship-path-required`.

## Where CoWork OS *Can* Help K1 (the Narrow Slice)

| Permitted job | CoWork primitive | Precondition |
|---|---|---|
| K1 marketing copy (DOCX) | Document Workbench | `COWORK_PRODUCTION_CONTROLS=1` verified per `cowork-os-providers` |
| K1 FE pitch / launch deck (PPTX) | Presentation Workbench | Same + `requireApprovalFor` on outbound delivery |
| Shot lists / render briefs / asset registers | Document Workbench + File Hub | Workspace permission default (no shell/network/delete) |
| "Three K1 hero layouts" concept iteration | Live Canvas + Build Mode | Concept only — never substitute for a K-Cycles render |
| K-Cycles output preview | `media://` token-gated (PNG/MP4/WebM, 1h TTL) | Workspace contains artifact; never auto-extract reference frames into KG |
| File provenance tags (`K1_Internal`, `K1_External`, `K1_Backer_Submissions`) | `FileProvenanceRegistry` | Always label on import |
| K1 marketing workspace permission profile (canonical live path `/Users/spectrasynq/content-production-pipeline/blender/`; legacy `~/K1_Marketing/` is archived at `/Users/spectrasynq/SpectraSynq/archive/K1_Marketing.archived_2026-05-14/` for evidence reads only) | `workspace_permission_rules` `{network:true, allowedDomains:[<social/CDN>], shell:false}` | Per-workspace grant; never extend across K1 workspaces |
| K1 firmware build-status MCP connector | `connectors/templates/mcp-connector/` scaffold | STUDY only — defer until post-FE Launch; one-way (rig writes → CoWork reads) |
| K1 effect-review task pipeline | Mission Control kanban (visualization) | Verdict from human + Claude Code skills, not CoWork LLM |

Every row inherits the safety floor from `cowork-os-safety`: `dangerous_only` permission mode, workspace `{read:true, write:true, delete:false, network:false, shell:false, unrestrictedFileAccess:false}`, Admin Policies `runtime.network.defaultAction:"deny"`, and live production-control-plane enforcement (`COWORK_PRODUCTION_CONTROLS=1` with USD 1.00 / 100k-token default ceilings — lower per task via `COWORK_PRODUCTION_MAX_COST_USD_PER_TASK` and `COWORK_PRODUCTION_MAX_TOKENS_PER_TASK`, scope outbound via `COWORK_PRODUCTION_ALLOWED_DOMAINS` per `02_PRODUCTION_GUARDRAILS.md` §Implemented Source Controls). If those are not in place, do not run paid K1 work in CoWork.

## Where CoWork OS *Cannot* Help K1 — Hard Exclusions

| Hard exclusion | Why (cite Tier A) |
|---|---|
| K1 firmware build / flash / OTA from any CoWork workspace | `cowork-os-safety` — Computer Use + `run_command` blast radius; sandbox cannot tunnel USB; SAFETY_RAILS 2.1 |
| K1 USB / JTAG / serial-port driving | Sandbox boundary does not cover USB |
| K-Cycles render orchestration | `cowork-os-workbench` — Live Canvas 5 MB cap; no native Blender adapter; Render-to-Content Observer is review-only per `03_AGENT_DEPARTMENT_CHARTER.md` |
| Visual Bible (archive `/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/`; live `/Users/spectrasynq/content-production-pipeline/blender/`) as CoWork-owned authority | `cowork-os-memory` — KG auto-extraction (`executor.ts:11607`) has no opt-out; governance-sentinel-tracked until upstream ships a gate |
| `~/.claude/memory/spectrasynq/` mirrored into a CoWork workspace | Same — stays canonical outside CoWork |
| SongAware DSP correctness verification | `signal-processing-verification` (Claude Code) owns it |
| Register-map / peripheral-bus / crash-dump analysis | Claude Code skill suite is authority |
| K1 signing certs / Apple developer keys / provisioning profiles in SecureSettings | `cowork-os-providers` / SAFETY_RAILS 2.2 — safeStorage not audited for production K1 signing |
| Computer Use to drive PlatformIO / IDF tooling | `cowork-os-workbench` — biggest single blast-radius primitive; default OFF |
| Auto-generated K1 hardware claims as authoritative | See Anti-Patterns |
| Matter / DLE / smart-home framing as K1 product-definition input | K1 is entertainment technology — ecosystem signals are watchlist-only per `project_k1-positioning-entertainment-not-smart-bulb.md` and `35_RESEARCH_DESK_MATTER_WATCHLIST_2026-05-17.md` |

## Composition Map

`cowork-os-spectrasynq-k1` ← `cowork-os-safety` + `cowork-os-memory` + `cowork-os-workbench` + `cowork-os-providers`. Read those four first. This skill resolves K1 application questions only — it does not restate the mechanics.

## K1 Visual Bible Guardian — Managed Agent Recipe

The safe pattern for surfacing Visual Bible reference into CoWork review without granting CoWork authority over the source.

| Field | Value |
|---|---|
| Surface (per `cowork-os-agent-teams`) | Managed Agent (versioned + ManagedSession) |
| Trigger | Reactive only — never AutomationProfile; never Heartbeat dispatcher |
| Workspace | `K1_Visual_Bible_Review` — separate from source repo; sandbox, not mirror |
| Permissions | `{read:true, write:false, delete:false, network:false, shell:false, unrestrictedFileAccess:false}` |
| Source mount | Read-only mount of *specific* reference frames per task; never bulk-mount the repo |
| KG auto-extraction | OFF for this workspace via mount-policy discipline + `<no-memory>` markers on every system prompt. No upstream env/source gate exists; log this workspace as `governance-sentinel-tracked` per `03_AGENT_DEPARTMENT_CHARTER.md` and `cowork-os-memory` R2 until upstream ships an opt-out mechanism. |
| Memory observation | OFF (`<no-memory>` marker on every system prompt) |
| Autonomy preset | `manual` — no auto-approve, not even `run_command` |
| `requireWorktree` | `true` |
| Outbound | None — Guardian writes review notes to the review workspace only |
| `founder_edge` | NEVER — `allowUserInput=false` makes Captain unreachable mid-flight |

Guardian reads and notes — does not publish. Ship approval flows through Captain + Claude Code (`forgecad-render-inspect`, `k1-effect-development`).

## K1 Effect Reviewer — Managed Agent Recipe

The safe pattern for CoWork review of an LED effect PR before it lands in K1 firmware.

| Field | Value |
|---|---|
| Surface | Managed Agent (versioned + ManagedSession) |
| Workspace | `K1_Effect_Review` — scoped to the firmware repo *worktree*, not the production checkout |
| Permissions | `{read:true, write:true, delete:false, network:false, shell:false, unrestrictedFileAccess:false}` — write scoped to review notes / PR comment drafts |
| Source scope | Single PR diff + `k1-effect-development` rules as context — checks centre-origin, no-heap, modifier-slot compliance, frame-rate-independent timing, palette-not-rainbow |
| KG auto-extraction | OFF (same mount-policy + `<no-memory>` posture as Guardian; governance-sentinel-tracked) |
| Autonomy preset | `manual` |
| Production push | NEVER — Reviewer drafts; merge stays with human + `k1-effect-development` |
| Cost ceiling | Per task: `COWORK_PRODUCTION_MAX_COST_USD_PER_TASK` (lower than the USD 1.00 default for review loops) and `COWORK_PRODUCTION_MAX_TOKENS_PER_TASK` (lower than the 100k default) per `02_PRODUCTION_GUARDRAILS.md` §Implemented Source Controls and `cowork-os-providers` |
| Heartbeat profile | `observer` only, if at all — never `operator` or `dispatcher` |
| `requireApprovalFor` | `["post message", "send email", "open pr", "merge", "push"]` |

Reviewer is a second pair of eyes against the rulebook. Not the rulebook, not the maintainer, does not ship.

## Safety Rails for K1 × CoWork Work

Inherit everything from `cowork-os-safety`. K1-specific non-negotiables (cross-ref `SAFETY_RAILS_FOR_SPECTRASYNQ.md` §§1-3):

1. K1 firmware production repos never CoWork-write-enabled — PRs and worktrees only; merge stays with Captain (Rules 1.1, 1.2).
2. The Visual Bible — both the archive at `/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/` (read-only evidence) and the live content-production pipeline at `/Users/spectrasynq/content-production-pipeline/blender/` — never bulk-mounted; per-task reference frames only, with `<no-memory>` markers and governance-sentinel-tracked logging until upstream ships a per-workspace KG opt-out (Rules 1.2, 3.2; `cowork-os-memory` R2).
3. K-Cycles renders never auto-generated without human-eye approval — Visual Bible = product truth (`GAP_ANALYSIS` Gap 3).
4. AI-summarised test-rig output is never authoritative for pass/fail — fixture raw output is (`GAP_ANALYSIS` Gap 2).
5. K1 signing keys / Apple developer credentials / provisioning profiles never enter CoWork's SecureSettings (Rule 2.2).
6. `~/.claude/memory/spectrasynq/`, the archived Visual Bible (`/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/`), and the live content-production pipeline (`/Users/spectrasynq/content-production-pipeline/blender/`) stay canonical outside CoWork — never CoWork-mirrored (Rules 1.3, 3.2).
7. Captain remains strategic authority for K1 product truth. CoWork can host a reactive Founder Office Operator twin for cognitive offload — never an outbound K1 authority surface.
8. `production-control-plane.ts` enforcement must be verified before any paid K1 work: `COWORK_PRODUCTION_CONTROLS=1`, ceilings set to the per-task limit appropriate for the K1 task (default USD 1.00 / 100k tokens per `02_PRODUCTION_GUARDRAILS.md`), `COWORK_PRODUCTION_ALLOWED_DOMAINS` scoping outbound to the providers the K1 task actually needs. Without these, a single K1 review loop can burn unbounded LLM spend.
9. K1 product-definition input never derives from Matter / DLE / Thread / HomeKit / Google Home / SmartThings / Alexa / smart-bulb ecosystem material. Those are watchlist-only per `project_k1-positioning-entertainment-not-smart-bulb.md`. K1 is entertainment technology; ecosystem evidence is for defensive awareness + future-interoperability-pressure monitoring, never for K1 spec, firmware roadmap, or product copy.

## Anti-Patterns / Non-Negotiables

| Anti-pattern | Why it fails |
|---|---|
| "Flash K1 from a CoWork shell task" | Sandbox cannot tunnel USB; Computer Use blast radius unacceptable (`GAP_ANALYSIS` Gap 1; `cowork-os-workbench` R1) |
| "Mount the Visual Bible archive (`/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/`) or the live content-production pipeline (`/Users/spectrasynq/content-production-pipeline/blender/`) so the agent has context" | KG auto-extraction has no opt-out; injects Visual Bible claims into every prompt (`cowork-os-memory` R2); governance-sentinel-tracked |
| "Have CoWork verify the SongAware beat detector is correct" | LLM cannot substitute for golden-reference F-measure; `signal-processing-verification` owns it |
| "Auto-summarise K1 thermal test results and call it pass/fail" | AI-summarised fixture output is never authoritative — raw output is (`GAP_ANALYSIS` Gap 2) |
| "Let the Reviewer post the PR comment automatically" | Reviewer is drafter, not publisher; `requireApprovalFor` covers outbound + git mutation |
| "Bypass Visual Bible golden-reference review with CoWork render-comparison" | Visual Bible is product truth; render diffs go to human + `forgecad-render-inspect` |
| "Import K1 firmware repo to use Document Workbench on the source" | Workbench is not for source code; `K1.SpectraSynq/` stays outside CoWork's workspace boundary (Rule 1.2) |
| "Use a Captain Proxy twin to reply to backer K1 firmware questions" | Captain Proxy AVOID per `cowork-os-agent-teams` — identity confusion |
| "Enable Computer Use so CoWork drives Blender for a K1 hero shot" | Render orchestration is N/A — Render-to-Content Observer is review-only per `03_AGENT_DEPARTMENT_CHARTER.md`; never driving Blender, K-Cycles runs, or Visual Bible mutation |
| "Production controls are on because the env vars are set in `.env.example`" | False — verify `COWORK_PRODUCTION_CONTROLS=1` is live in the running process and that ceilings + `COWORK_PRODUCTION_ALLOWED_DOMAINS` are set to the values the K1 task actually needs. KG auto-extraction has no env gate at all; workspace-mount discipline + `<no-memory>` markers + governance-sentinel-tracked logging are the only enforcement (`cowork-os-memory` R2; `02_PRODUCTION_GUARDRAILS.md` §Implemented Source Controls) |
| "Never frame K1 as Matter / DLE / smart-home / smart-bulb input. K1 is entertainment technology. Ecosystem signals are watchlist-only per `project_k1-positioning-entertainment-not-smart-bulb.md`." | Matter / DLE / Thread / HomeKit / Google Home / SmartThings / Alexa / smart-bulb comparisons are watchlist-only — never K1 product-definition input. Output sections like "Implication for K1 product definition" are forbidden; use "Ecosystem language tracking" / "Future interoperability pressure indicator" instead. Misclassifying K1's category risks SpectraSynq spending strategic attention on the wrong competitive frame. Cross-ref `35_RESEARCH_DESK_MATTER_WATCHLIST_2026-05-17.md`, `59_RESEARCH_DESK_MATTER_EFFECTS_CLUSTER_WATCHLIST_2026-05-18.md`, `60_RESEARCH_DESK_DLE_WATCHLIST_2026-05-18.md`. |

## Worked Example — K1 Effect QA Loop

End-to-end flow showing where CoWork fits and where it hands off.

1. Engineer opens a PR against `K1.SpectraSynq/` adding a new centre-origin effect.
2. CI runs Claude Code `k1-effect-development` checks in the firmware repo (centre-origin, no-heap, modifier-slot, palette-not-rainbow). Outside CoWork.
3. Mission Control INBOX receives "Review effect PR #N" — queue visualization, not authority.
4. `K1 Effect Reviewer` Managed Agent is dispatched. Workspace `K1_Effect_Review` opens a fresh worktree; permissions per template; `COWORK_PRODUCTION_CONTROLS=1` + per-task ceilings verified; KG auto-extraction governance-sentinel-tracked via mount-policy + `<no-memory>` discipline.
5. Reviewer reads the diff, surfaces violations against the `k1-effect-development` rulebook, drafts a PR comment in a Document Workbench artifact. *Does not post.*
6. Draft delivered to a private operator channel (Telegram private group or `#engineering-internal` Discord under channel-specialization per `cowork-os-channels`).
7. Captain (or delegate) posts the comment to the PR using their own credentials, final judgement applied. Comment is human-authored at the trust boundary.
8. Author iterates; loop repeats from step 4.
9. Merge authority into firmware main: human + Claude Code `k1-effect-development` + `signal-processing-verification` if audio-reactive. CoWork has no role at the merge gate.
10. Post-deploy validation (hardware-in-loop, register-map verification, render-path profiling) runs in Claude Code skills. CoWork is not in this loop.

Result: CoWork served as Reviewer-drafting + queue-visualization. Authority stayed with Captain + the firmware repo + Claude Code skills. No K1 product-truth claim by CoWork, no firmware flashed, no Visual Bible auto-extracted.

## Source References

- Synthesis: `SPECTRASYNQ_ADOPTION_MAP.md` §K1; `SAFETY_RAILS_FOR_SPECTRASYNQ.md` §§1-3; `GAP_ANALYSIS.md` Gaps 1-3
- Live doctrine: `SpectraSynq-Production-OS/02_PRODUCTION_GUARDRAILS.md`, `03_AGENT_DEPARTMENT_CHARTER.md`, `04_PILOT_LANE_BACKLOG.md`, `31_K1_PRODUCT_TRUTH_SESSION_PACKET_2026-05-17.md`, `35_RESEARCH_DESK_MATTER_WATCHLIST_2026-05-17.md`, `59_RESEARCH_DESK_MATTER_EFFECTS_CLUSTER_WATCHLIST_2026-05-18.md`, `60_RESEARCH_DESK_DLE_WATCHLIST_2026-05-18.md`
- Memory: `~/.claude/projects/-Users-spectrasynq-CoWork-OS/memory/project_k1-positioning-entertainment-not-smart-bulb.md`
- Source-control reference: `src/electron/production-control-plane.ts`
- Tier A composed: `cowork-os-safety`, `cowork-os-memory`, `cowork-os-workbench`, `cowork-os-providers`
- Adjacent Tier B: `cowork-os-spectrasynq-fe-launch`
- Claude Code authority (outside CoWork): `esp32-actor-model`, `esp32-render-path-safety`, `k1-effect-development`, `k1-ap-websocket-stack`, `register-map-verification`, `peripheral-bus-debugging`, `hardware-bringup`, `firmware-crash-analysis`, `firmware-profiling`, `signal-processing-verification`, `spectrasynq-audio-pipeline`, `m5rotate8-encoder-system`, `dsp-test-fixtures`, `dsp-performance-profiling`, `audio-visualisation-debug`, `forgecad-render-inspect`

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-17 | agent:wave-4-skill-author | Created — Tier B composition skill for K1 × CoWork OS. Composes safety + memory + workbench + providers. K1 Visual Bible Guardian + K1 Effect Reviewer recipes. K1 effect QA worked example. |
| 180526-1340 | agent:skill-refresh-ssa-spectrasynq-k1 | Refreshed per triage 180526-1310. Rotated patch references to production-control; ADDED K1-entertainment-tech anti-pattern row per memory file; preserved K1 reality-check + Visual Bible Guardian + Effect Reviewer recipes. |


---

> **Migration note — 2026-05-19.** Hardcoded dead-path references rewritten in this file per CONSOLIDATION_TRUTH.md (`/Users/spectrasynq/content-production-pipeline/blender/CONSOLIDATION_TRUTH.md`). Specifically: `~/K1_Visual_Bible/` and `/Users/spectrasynq/K1_Visual_Bible/` → archive at `/Users/spectrasynq/SpectraSynq/archive/K1_Visual_Bible.archived_2026-05-14/` (read-only evidence); `~/K1_Marketing/` and `/Users/spectrasynq/K1_Marketing/` → archive at `/Users/spectrasynq/SpectraSynq/archive/K1_Marketing.archived_2026-05-14/`; `~/SpectraSynq.LandingPage/` → archive at `/Users/spectrasynq/SpectraSynq/archive/SpectraSynq.LandingPage.archived_2026-05-14/`; the fictitious `/Users/spectrasynq/Workspace_Management/K1_Marketing` and `/Users/spectrasynq/Workspace_Management/K1_Renders` paths (which never existed) → canonical live workspace `/Users/spectrasynq/content-production-pipeline/blender/`. Backup retained at `~/.claude/backups/k1-visual-bible-sessions-2026-05-19/pre-cutover-2026-05-19/cowork-os/`.
