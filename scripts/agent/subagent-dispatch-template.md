# Subagent Dispatch Contract

Fill this before dispatching any subagent. No dispatch without a complete contract.
This encodes the parallel-agent orchestration discipline from `.claude/CLAUDE.md`.

---

## Contract

```text
delegation_id:           <unique short id, e.g. im73d-audio-diff-001>
role:                    <what the subagent is, e.g. "DSP regression auditor">
task:                    <one-sentence evidence question or work item>
classification:          load-bearing | optional
expected_output:         <artefact the orchestrator will consume; minimum useful partial>
source_scope:            <paths the subagent may read>
write_scope:             <paths the subagent may write; "none" if read-only>
forbidden_actions:       <explicit no-list: upload, flash, erase, serial-write, commit, edit outside write_scope, ...>
checkpoint_timeout:      <wall-clock or tool-call bound, e.g. "5 min" or "20 tool calls">
launch_ack_timeout:      30 seconds (fixed; no retry after a blocked launch call)
bounded_retry:           <one bounded retry window if first checkpoint misses, e.g. "3 min, request partial">
fallback_owner:          <who runs if the subagent stalls: orchestrator-local | replacement agent | captain-escalation>
final_answer_dependency: <can the final answer ship without this evidence? yes | no | narrow-to-claim>
escalation_condition:    <when to stop retrying and escalate, e.g. "second missed checkpoint">
consumption_rule:        <how the orchestrator consumes the result: replace-evidence | narrow-claim | mark-missing | block-final>
```

## Classification rule

`optional` = the task could be deleted before launch without changing the final
answer's correctness, scope, confidence, or wording.

Anything else is `load-bearing`. A `load-bearing` task **cannot** be downgraded
after launch because it is late, inconvenient, or hung. If the final judgement
needs the evidence, it is load-bearing.

## Stuck-agent state machine

```
PRE_DISPATCH -> RUNNING -> RECEIVED
                       -> FIRST_MISS -> RETRY_WAIT -> RECEIVED
                                                 -> SECOND_MISS -> FALLBACK_RUNNING -> REPLACED
                                                                          -> MISSING_OR_BLOCKED
                       -> SYNTHESIS_LEDGER
```

Before `PRE_DISPATCH`, register the contract with
`scripts/agent/delegation_guard.py register`. Launch one agent at a time and run
`ack` immediately with the returned agent ID. The active cap is two and the
maximum checkpoint is 300 seconds. A launch call without acknowledgement after
30 seconds is `aborted`; do not issue another spawn attempt, and run the declared
fallback locally. The repository guard records and detects this condition but
cannot interrupt a collaboration API call that is already blocked.

- First miss: request a useful partial or narrow the task. One bounded retry.
- Second miss: stop treating the subagent as a source of truth. Start fallback.
- No indefinite polling. No "one more wait" loop.
- A hung load-bearing sidecar does not make its evidence optional. It makes the
  evidence unresolved until replaced or reported missing.

## Synthesis ledger (required in any final answer that used delegated evidence)

| delegation_id | task | classification | status | artefact | consumed-how |
|---------------|------|----------------|--------|----------|--------------|
|               |      |                |        |          |              |

Status ∈ `received | replaced | missing | blocked`. Missing evidence reduces or
removes the affected claim. Blocked evidence stops the affected judgement.
