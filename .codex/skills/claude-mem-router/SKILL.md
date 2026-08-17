---
name: claude-mem-router
description: Route to the right claude-mem / recall skill from the task scenario. Single entry point for mem-search, spec-recall, knowledge-agent, timeline-report, weekly-digests, smart-explore, learn-codebase, how-it-works, and memory-authority-gate. Use at session start, when resuming a lane, or whenever prior-session context / memory / "did we already" questions arise.
---

# Claude-Mem Router

**Core principle:** Don't memorize nine skills — match **scenario → one skill**, then stop. Over-invocation is a process bug (AGENT_OS §14).

This is the memory/recall counterpart to `/thinking-model-router`.

## Quick gate (run in order)

```
1. Is this about CURRENT lane / device / branch status?
   → /spec-recall  (on-disk first; memory is NOT authority)

2. Is memory empty, stale, offline, or contradicting launch docs?
   → /memory-authority-gate

3. Is the question about HOW the memory tool works?
   → /how-it-works

4. Else match the scenario table below → invoke ONE skill → act.
```

## Scenario → skill

| Scenario / user shape | Invoke | Do NOT |
|-----------------------|--------|--------|
| New session, context reset, "what's the active lane?" | `/spec-recall` | mem-search as current truth |
| Before firmware edit / flash / forensic work | `/spec-recall` then `/mem-search` | skip on-disk handover |
| "Did we already fix X?" / prior bug / failed attempt | `/mem-search` | timeline-report |
| Recurrence pattern / "how did we solve this last time?" | `/mem-search` (search→timeline→get_observations) | fetch all IDs unfiltered |
| Need code structure without reading whole files | `/smart-explore` | learn-codebase |
| Unfamiliar tree / empty memory seed / "prime the repo" | `/learn-codebase` | every session |
| Theme corpus Q&A ("everything about IM73D decisions") | `/knowledge-agent` | weekly-digests |
| One sweeping "Journey Into …" narrative | `/timeline-report` | weekly-digests |
| Week-by-week / serial chapters / "story by week" | `/weekly-digests` | timeline-report |
| "How does claude-mem work?" / injection / where data lives | `/how-it-works` | spec-recall |
| Withhold / "does not mean ship" / promote / close a gate | `/ship-path-required` **in the same answer** | ending on hold with no numbered path |
| Memory returns zero / worker unhealthy / contradicts Tier 0 | `/memory-authority-gate` | re-litigate from episodic memory |

## Default session ladder (K1)

Use this for normal firmware / forensic sessions — not for pure meta questions:

1. Bootstrap (`session-bootstrap.sh`) — must PASS  
2. `/spec-recall` — progress → handoff → spec-index → lane handover  
3. `/mem-search` — 2–4 **single-term** queries on the lane/effect (not compound AND/OR)  
4. Act from **git + on-disk + filtered observations**  
5. Record observations at start / green / blocker / decision / end (AGENT_OS §5)

Optional inserts:
- Symbol named in an observation → `/smart-explore` that symbol  
- Memory looks broken → `/memory-authority-gate` before trusting hits  
- Captain asks for history narrative → `/timeline-report` or `/weekly-digests` (pick by format)

## mem-search discipline (when that is the match)

```
search(query) → filter titles → timeline(anchor) → get_observations([ids])
```

- Project filter: use the name this repo's observations were stored under (often historical `SensoryBridge-main 9` — verify with a probe search if zero hits).  
- Prefer effect / subsystem names (`Dense Forge`, `IM73D`, `BLE remoted`), not port shorthand.  
- Never treat a hit as **current** worker/queue/device status without live re-check.

## Anti-patterns

- Invoking all memory skills "to be safe"  
- Using `/mem-search` as lane status (that's `/spec-recall`)  
- Running `/weekly-digests` or `/timeline-report` for a one-bug lookup  
- Running `/learn-codebase` every session  
- Averaging memory vs handoff when they disagree — **handoff wins for current state**

## Companion skills

| Skill | Role |
|-------|------|
| `/thinking-model-router` | Decision / debug / architecture mental models (orthogonal) |
| `/ssa-management` | How to consume subagent evidence (orthogonal) |
| `/discover-specialists` | Specialist fan-out when domain needs an agent, not memory |

## Refresh copies

```bash
bash scripts/install-claude-mem-skills.sh
```
