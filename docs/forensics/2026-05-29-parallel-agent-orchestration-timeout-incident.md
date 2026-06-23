---
abstract: "Incident note and canonical resolution for parallel-agent orchestration stalls where load-bearing delegated research is waited on indefinitely or incorrectly treated as optional."
---

# Parallel-Agent Orchestration Timeout Incident

| Field | Value |
|---|---|
| Date | 2026-05-29 |
| Severity | SEV3 process failure |
| Affected surface | Agent orchestration, research/evaluation synthesis, Captain time |
| Status | Resolved by canonical rule update |

## Summary

[FACT] During K1 effect-roster evaluation work, the orchestrator dispatched two
read-only sub-agents for independent audit/design tasks and then waited too long
for their results instead of maintaining an explicit evidence barrier and
recovery path.

[FACT] The first attempted correction was also wrong: it framed late delegated
work as something the orchestrator could simply ignore and continue without.
Captain rejected that framing because the delegated tasks had been created for a
reason and could contain critical evidence for the final assessment.

[INFERENCE] The real failure mode was unmanaged dependency handling. The issue
was not parallelism itself. The issue was dispatching research/evaluation work
without a declared consumption contract, checkpoint cadence, and stalled-agent
recovery path.

## How It Happened

[FACT] The orchestrator identified two independent workstreams:

- source blast-radius audit for retiring/quarantining bad K1 light modes;
- replacement-effect concept design under K1 perceptual and firmware
  constraints.

[FACT] Both tasks were relevant to the final product assessment. They were not
mere optional curiosities.

[FACT] The orchestrator waited on the agents with a long blocking wait. When the
wait did not return useful results, the orchestrator attempted to continue by
treating the late results as optional.

[INFERENCE] This collapsed two different categories into one:

- optional acceleration work, where late output can be ignored safely;
- load-bearing evidence work, where late output must be consumed, replaced, or
  marked missing before final judgement.

## Why It Happened

[INFERENCE] The orchestration rule being followed was incomplete. It encouraged
parallel delegation for independent work and discouraged excessive waiting, but
it did not force a pre-dispatch declaration of:

- whether each sub-agent result was load-bearing or optional;
- what artefact was expected;
- when a checkpoint was due;
- who owns fallback if the task stalls;
- whether the final answer is allowed without that evidence.

[INFERENCE] Without those fields, the orchestrator had no correct decision
surface after timeout. Waiting indefinitely and ignoring late load-bearing work
both became plausible behaviours, even though both are wrong.

## Why It Continues To Happen

[INFERENCE] This failure repeats when "can run in parallel" is mistaken for "can
be omitted if inconvenient." Independent work can still be critical. Parallelism
removes sequencing constraints; it does not remove evidentiary dependencies.

[INFERENCE] It also repeats when sub-agent tasks do not write interim artefacts
or expose partial results. A long-running agent then becomes an opaque blocker
instead of a recoverable workstream.

[INFERENCE] Finally, it repeats when the final answer lacks an evidence ledger.
If the orchestrator does not list which delegated results were consumed, replaced,
or missing, it can accidentally present an under-evidenced judgement as complete.

## Canonical Resolution

[FACT] `AGENTS.md` and `.claude/CLAUDE.md` now contain a load-bearing
parallel-agent orchestration rule.

[FACT] The canonical rule is:

1. Do not dispatch a sub-agent without a consumption contract.
2. Classify every delegated task before launch as `load-bearing` or `optional`.
3. Treat delegated research, investigation, audit, or evaluation as load-bearing
   whenever the final judgement needs its evidence.
4. Never wait indefinitely.
5. Never silently downgrade late load-bearing work to optional.
6. If a load-bearing task misses its checkpoint, recover actively:
   - request a partial;
   - narrow the task;
   - reassign it;
   - complete an equivalent investigation locally;
   - or report the evidence as missing and reduce/escalate the claim.
7. Do not issue a final assessment that depends on delegated evidence until that
   evidence has been consumed, replaced, explicitly marked missing, or escalated
   as blocked.
8. Apply the stuck-agent retry policy. A silent or hung sidecar gets one bounded
   recovery attempt, not indefinite polling.

## Required Consumption Contract

Every delegated task must include this contract before launch:

```text
Delegation ID:
Role:
Task / evidence question:
Classification: load-bearing | optional
Classification rationale:
Expected output / minimum useful partial:
Source scope:
Write scope:
Checkpoint / timeout:
Bounded retry:
Fallback owner and action:
Final-answer dependency:
Escalation condition:
Consumption rule:
```

`optional` means the task could be deleted before launch without changing the
final answer's correctness, scope, confidence, or wording. If deleting the task
would weaken or narrow the judgement, the task is load-bearing. A load-bearing
task cannot be downgraded after launch because it is late, inconvenient, or
hung.

## Stuck-Agent Retry Policy

[FACT] A delegated task is `stuck` when any of these are true:

- the checkpoint/timeout in its consumption contract expires without a result;
- a wait returns no status twice for the same task;
- the agent produces no expected artefact and no useful partial;
- the agent is still running but the orchestrator cannot inspect progress.

[FACT] The canonical recovery sequence is:

1. **First miss:** request a partial result or narrow the task. Set one bounded
   retry window. The retry bound must be a concrete wall-clock or tool-call
   limit; default maximum is five minutes for interactive work unless Captain's
   deadline is stricter.
2. **Second miss:** stop treating that agent as a source of truth. Start the
   fallback owner immediately: replacement agent, local investigation, or a
   narrower equivalent task.
3. **Recovery completion:** consume the replacement evidence, or mark the
   evidence as missing and reduce/escalate the claim.
4. **No indefinite polling:** do not repeatedly wait on a silent sidecar while
   Captain is blocked.

[FACT] A hung load-bearing sidecar does not make its evidence optional. It makes
the evidence unresolved until the orchestrator replaces it or reports the gap.

[FACT] The parent deadline must reserve time for each stage:
`checkpoint + retry + fallback + synthesis`. If a first miss leaves no fallback
and synthesis buffer, skip the retry and start fallback immediately.

## Canonical State Machine

```text
PRE_DISPATCH
  -> RUNNING
  -> RECEIVED
  -> FIRST_MISS
  -> RETRY_WAIT
  -> RECEIVED
  -> SECOND_MISS
  -> FALLBACK_RUNNING
  -> REPLACED
  -> MISSING_OR_BLOCKED
  -> SYNTHESIS_LEDGER
```

| State | Required behaviour |
|---|---|
| `PRE_DISPATCH` | Contract exists and classification is declared |
| `RUNNING` | Poll only until the declared checkpoint |
| `FIRST_MISS` | Request useful partial or narrow the ask |
| `RETRY_WAIT` | One bounded retry; no "one more wait" loop |
| `SECOND_MISS` | Original sidecar stops being treated as truth source |
| `FALLBACK_RUNNING` | Replacement path must fit remaining parent deadline |
| `MISSING_OR_BLOCKED` | Reduce the claim or stop the judgement |
| `SYNTHESIS_LEDGER` | Record every load-bearing source and consumption result |

## Evidence Replacement And Partial Quality

[FACT] Replacement evidence is equivalent only if it answers the same evidence
question, covers the same declared scope, and has equal or higher authority. A
narrower replacement must narrow the final claim.

[FACT] A partial result only satisfies a load-bearing dependency if it directly
answers the declared evidence question or narrows the unresolved area. Status
chatter, plans, apologies, or generic progress reports do not count.

[FACT] Contradictory load-bearing evidence must be resolved, bounded, or
escalated. It must not be averaged away or hidden behind a generic caveat.

## Operator Update Protocol

Captain should see state transitions, not routine background chatter.

| Transition | Required operator update |
|---|---|
| Dispatch | Task, classification, expected artefact, checkpoint, fallback, final dependency |
| First missed checkpoint | Load-bearing evidence unresolved, partial/narrow request made, retry bound, held claim |
| Retry starts | Narrowed ask, due time, and next action if missed |
| Fallback starts | Original source no longer treated as truth, replacement path, evidence gap carried forward |
| Final synthesis | Delegation ledger with received/replaced/missing/blocked status and claim impact |

Proceed without asking Captain when the fallback is equivalent and stays within
the original scope. Emit `approval` when fallback requires broader scope,
hardware/device action, writes outside the approved lane, or more time than the
stated budget. Emit `review` when Captain must choose between a reduced
judgement and waiting. Emit `blocked` when load-bearing evidence cannot be
recovered and the final judgement depends on it. Emit `ready` only when synthesis
is complete and the ledger is honest.

## Delegation Ledger Requirement

Any final answer that used load-bearing parallel work must include a short ledger:

| Field | Meaning |
|---|---|
| ID | Stable delegated task ID |
| Task | Delegated evidence question |
| Classification | `load-bearing` or `optional` |
| Source | Agent ID/name or local fallback |
| Deadline | Checkpoint/timeout used |
| Status | `received`, `replaced`, `missing`, or `blocked` |
| Evidence / artefact | Link, summary, or `none` |
| Consumption | How the result affected the final judgement |

## SSA Review Findings

Five read-only SSAs were dispatched to canonise this policy. Their outputs were
load-bearing for this policy update and were consumed as follows:

| ID | Source | Assigned lane | Status | Consumption |
|---|---|---|---|---|
| `D1` | Fermat | Incident command and root-cause wording | received | Added unmanaged evidence-dependency failure, 5-whys framing, and "hung does not mean optional" rule |
| `D2` | Copernicus | Retry, timeout, and fallback state machine | received | Added state machine, parent deadline formula, and one-retry-then-fallback rule |
| `D3` | Pauli | Contract schema and delegation ledger | received | Expanded pre-dispatch contract, final ledger fields, and close states |
| `D4` | Chandrasekhar | Loophole audit | received | Tightened optional definition, no post-hoc downgrade, replacement equivalence, partial quality, and contradiction handling |
| `D5` | Boyle | Operator-facing update protocol | received | Added transition updates and PIP-40/review/approval/blocked/ready decision points |

## Operating Pattern

| Condition | Correct action |
|---|---|
| Optional task times out | Continue; state it was optional if relevant |
| Load-bearing task times out once | Request partial or narrow the ask |
| Load-bearing task times out twice | Abandon that source and reassign or complete equivalent work locally |
| Load-bearing evidence cannot be recovered | Mark the final claim as missing evidence or blocked |
| Final answer depends on missing delegated evidence | Do not make the claim |

## What This Prevents

[INFERENCE] This prevents two opposite failures:

- wasting Captain's time by waiting indefinitely on unmanaged agents;
- wasting Captain's time by ignoring critical delegated evidence and presenting
  an incomplete judgement.

## Changelog

| Date | Change |
|---|---|
| 2026-05-29 | Added incident note and canonical orchestration rule after Captain rejected both indefinite waiting and silent downgrade of load-bearing sidecar evidence. |
