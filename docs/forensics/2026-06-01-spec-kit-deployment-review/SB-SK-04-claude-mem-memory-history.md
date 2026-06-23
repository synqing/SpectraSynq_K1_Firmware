# SB-SK-04 - claude-mem and Local Memory History

## Scope

[FACT] Lane scope was read-only investigation for `/Users/spectrasynq/SensoryBridge-main 9`, local memory index `/Users/spectrasynq/.codex/memories/MEMORY.md`, repo-local `.claude` evidence, and claude-mem operational constraints. Target repo, memory store, databases, and services were not modified.

[FACT] The controller brief sets this lane inside the Spec Kit deployment swarm and requires outstanding tasks, future feature lanes, Spec Kit ordering, safety boundaries, exact citations, read-only target handling, and memory-derived labelling. Source truth order puts local memory after current repo and runtime evidence. Source: `00-swarm-brief.md:7-32`.

## Sources read

- `research/sensorybridge-spec-kit-deployment/00-swarm-brief.md:1-53`
- `/Users/spectrasynq/SensoryBridge-main 9/AGENTS.md:1-6`, `17-84`, `150-160`, `178-193`
- `/Users/spectrasynq/SensoryBridge-main 9/CLAUDE.md:1-13`
- `/Users/spectrasynq/SensoryBridge-main 9/.claude/CLAUDE.md:1-25`, `27-45`, `60-104`
- `/Users/spectrasynq/SensoryBridge-main 9/Lightwave-Ledstrip/AGENTS.md:19-21`
- `/Users/spectrasynq/SensoryBridge-main 9/Lightwave-Ledstrip/CLAUDE.md:118-134`, `656-660`
- `/Users/spectrasynq/.codex/memories/MEMORY.md:1-144`, `179-281`, `452-505`, `1028-1258`
- `/Users/spectrasynq/SensoryBridge-main 9/.specify/integrations/claude.manifest.json:1-16`
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:53`, `125-240`, `460-620`
- `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/2026-05-27-smart-director-edgemixer-onset-import-strategy.md:1-90`
- `/Users/spectrasynq/SensoryBridge-main 9/docs/superpowers/plans/2026-05-26-secondary-channel-release-roadmap-handover.md:117-133`
- Read-only command evidence: `git status --short --branch`, `git worktree list --porcelain`, repo file searches, `.claude/worktrees/*/.git` marker reads, and read-only `mcp__claude_mem.search` queries.

## Memory-derived feature/task lanes

[MEMORY-DERIVED, REVERIFIED IN REPO] Secondary-channel release recovery remains a concrete handoff lane: `RenderParams` containment, `ChannelEffectState`, then release feature recovery. Memory cites the corrected implementation-first handoff and concrete queue at `MEMORY.md:454-463` and `MEMORY.md:502`. Repo cross-check found the plan surfaces at `docs/superpowers/plans/2026-05-26-secondary-channel-release-roadmap-handover.md:117-133` and current source definitions at `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:125-240`.

[MEMORY-DERIVED, REVERIFIED IN REPO] Smart Director / EdgeMixer / Onset import strategy is a first-class future lane. Memory says to map donor systems before mutating `sb_hy.cpp`, prioritise live-demo value, add shared AP snapshot after `calculate_novelty(t_now)`, then isolate `Edgemixer-lite`, `Assist`, and `Onset/Beat` in SSA sandboxes. Source: `MEMORY.md:237-276`. Repo cross-check found the durable strategy doc and source integration points at `docs/forensics/2026-05-27-smart-director-edgemixer-onset-import-strategy.md:20-29`, `56-80`, and `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:471-478`, `583-620`.

[MEMORY-DERIVED, PARTLY REVERIFIED] Smart Visual Engine default-off safety and proof boundary remain active constraints. Memory says disabled smart features must be materially inert and static proof must cover new modules before relying on build/reviewer closure. Source: `MEMORY.md:210-235`. Repo cross-check found `tests/test_smart_visual_engine_static.py`, `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.*`, `scripts/regression-harness/smart_director_replay.py`, and `scripts/regression-harness/visual_hooks_replay.py`; detailed pass/fail status was not rerun in this read-only lane.

[MEMORY-DERIVED, NOT FULLY REVERIFIED] Waveform-Fast reference capture is a regression-gate lane, not a generic aesthetic note. Memory preserves the exact Bloom/Waveform-Fast setup and decay/trail complaint at `MEMORY.md:179-203`. The expected durable artefact `docs/forensics/2026-05-27-captain-reference-wavefast-bloom.md` was not found by repo file search, though runtime logs mentioning `secondary_status` and K1 reference effect config exist. Treat this lane as needing source/runtime artefact reconciliation before entering Spec Kit.

[MEMORY-DERIVED, REVERIFIED IN REPO] Config/state persistence is a safety lane. Memory warns that `CHROMA_PROFILE` shifted saved config layout and made flashing a device-state decision, not a routine code path. Source: `MEMORY.md:465-476`, `503-504`. Repo cross-check confirms `FIRMWARE_VERSION 40103` with an inline note about `CHROMA_PROFILE` config-field addition and stale `40102` blobs at `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:53`.

[MEMORY-DERIVED, NOT REVERIFIED BEYOND FILE PRESENCE] K1/S3 audio fault recovery remains a future lane: wrong I2S channel mode, SPH0645 sample-rate/format issues, S2-tuned scaling, persisted `DC_OFFSET=-32767`, and the chosen minimal direction of K1/S3-specific audio branch plus DC offset sanity clamp. Source: `MEMORY.md:1205-1233`. Repo has matching forensic audio docs under `docs/forensics/2026-05-23-sb-ap1-cal-state-investigation/`, but this lane did not re-read every cited audio file.

[MEMORY-DERIVED, NOT REVERIFIED] Historical SB versus active K1.Lightwave harvest map is read-only archaeology. Memory says historical SB is not a clean predecessor of active firmware-v3, and candidate harvests must be classified against centre-origin, AP-only, timing, and build-target constraints. Source: `MEMORY.md:1243-1268`.

[MEMORY-DERIVED, STRATEGY ONLY] SuperPixie only affects SensoryBridge strategy by reinforcing proof discipline and narrow profile-gated work: minimal real-firmware patches, compile proof separate from runtime proof, and strategic import candidates `SynqMatrix`, `EdgeMixer`, beat tracking from a recovered safe state. Source: `MEMORY.md:1-112`. This lane does not make SuperPixie an SB implementation dependency.

## Claude-mem operational constraints

[FACT] The repo-local nested Lightwave docs define current claude-mem routing as `mcp-search search -> timeline -> get_observations`, warn not to use stale `mem-search` names, and distinguish memory search from Smart Explore code navigation. Source: `Lightwave-Ledstrip/AGENTS.md:19-21`; `Lightwave-Ledstrip/CLAUDE.md:118-134`.

[FACT] Memory records the previous crash-loop root cause as `claude-mem` launching a `chroma-mcp` sidecar through `uv tool uvx --python 3.13 chroma-mcp==0.2.6 ... --data-dir /Users/spectrasynq/.claude-mem/chroma`, with poisoned Chroma store and `WorktreeAdoption` as a hidden secondary spawn path. Source: `MEMORY.md:114-144`.

[FACT] A read-only MCP surface existed in this session as `mcp__claude_mem.search`. I queried it narrowly for SensoryBridge feature handoff and Chroma crash terms; it returned no matching observations. I did not call `rebuild_corpus`, restart workers, query or mutate Chroma directly, or run memory maintenance.

[INFERENCE] Direct worker `GET /api/search` or SQLite FTS would be an acceptable fallback only if current worker health was known and MCP transport was closed, per `Lightwave-Ledstrip/CLAUDE.md:134` and `656-660`. Because the MCP search surface answered normally, this lane had no reason to touch worker endpoints or database files.

## Cross-check status against repo files

[FACT] Current target branch from `git status --short --branch` is `feat/gdft-harness...origin/feat/gdft-harness` with dirty `AGENTS.md` and `.claude/CLAUDE.md` plus untracked Spec Kit skills and `.specify/` files. The `AGENTS.md` current-known-base note says `refactor/main @ ed22d33` and explicitly says to verify live before acting; live HEAD from `git worktree list --porcelain` is `98d03af2226a5b74690bc57c0fd11c67a4a0b427`. Source: `AGENTS.md:178-186` plus command output.

[FACT] Repo-local `.claude/worktrees` exist for `agc-bypass`, `agent-a0b332d904b690d68`, `agent-a2df0c67d0041f2cd`, and `vp-product-baseline`. Their `.git` files point into `/Users/spectrasynq/SensoryBridge-main 9/.git/worktrees/...`; `git worktree list --porcelain` reports the two `agent-*` worktrees as locked by `claude agent ... (pid 59986)`.

[FACT] Spec Kit is installed for manual specification work only. Both `AGENTS.md` and root `CLAUDE.md` say repository instructions, source, runtime evidence, and hardware proof outrank generated Spec Kit artefacts, and forbid implementation, workflow automation, extension hooks, or task-to-issue sync without explicit Captain approval. Source: `AGENTS.md:188-193`; `CLAUDE.md:7-13`.

[FACT] `.specify/integrations/claude.manifest.json:1-16` records Claude integration version `0.8.19.dev0`, installed `2026-05-30T18:20:13.109228+00:00`, and installed generated speckit skills including `speckit-implement` and `speckit-taskstoissues`. File searches also found `.agents/skills/speckit-*` untracked.

[FACT] The AGENTS-required reference docs from the LightwaveOS-style instruction set are absent in this checkout; the existing strategy doc records `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`, `docs/protocol/k1-ws-contract.yaml`, and `docs/protocol/k1-rest-contract.yaml` as missing. Source: `docs/forensics/2026-05-27-smart-director-edgemixer-onset-import-strategy.md:31-42`.

## Spec Kit deployment implications

[INFERENCE] First Spec Kit candidates should be specification artefacts for lanes that already have source/runtime anchors and are not immediate hardware mutations: secondary-channel release recovery, Smart Director/EdgeMixer/Onset import sequencing, config persistence rules, and Waveform-Fast reference-capture reconciliation.

[INFERENCE] Spec Kit must carry evidence labels and gate language directly: memory-derived versus repo-verified, build/upload/runtime proof split, manual-only Spec Kit use, no task-to-issue sync, no generated hook execution, no service restarts, no memory maintenance, no calibration command, no firmware write without later explicit Captain approval.

[INFERENCE] Do not let Spec Kit convert memory notes into product truth. Any memory-derived lane entering `specs/` needs a source-truth section naming exact repo files, runtime logs, and unresolved gaps, with memory citations only as routing evidence.

[INFERENCE] The live branch/worktree state argues for a deployment preflight artefact before new specs: current branch, dirty tree, installed generated skills, locked `.claude/worktrees`, absent reference docs, and which generated surfaces are allowed only for manual specs.

## Stop conditions

- Stop if a lane requires firmware edits, build/upload, serial monitor, flash erase, calibration, runtime command writes, service restarts, Chroma rebuild, memory database maintenance, generated hook execution, workflow automation, or task-to-issue sync.
- Stop if memory and repo evidence conflict and no current source/runtime file resolves it.
- Stop if a Spec Kit artefact would encode a memory-derived claim as verified product truth.
- Stop if target hardware identity, board role, or protected capture-state status is needed but unavailable.
- Stop if `.claude` worktree locks indicate active Claude agents could be disturbed by cleanup, prune, or adoption activity.
