# Gate 2 DAG decision — negative matrix closes the experiment, not the gate

Date: 2026-08-15
Task: FRTOS-25
Scope: independent architecture/gate decision; no code, build, device or git action

## Decision

```text
G2_MATRIX_EXECUTION               = CLOSED_NEGATIVE
G2_CANDIDATE_SELECTION            = NO_SELECTION
G2_PRODUCTION_BEHAVIOUR_CHANGE    = NONE
G2_OPERATIONAL_ROLLBACK           = CROSS0_RETAINED
G2_SERVICE_CONTRACT               = OPEN_UNSATISFIED
G2_REQUIREMENTS_DECOMPOSITION     = REQUIRED
G3_ENTRY                          = BLOCKED
IMMEDIATE_CAPTAIN_DECISION        = NONE
TWO_UNIT_PRODUCT_AB_NOW           = NOT_REQUIRED
```

This is a more precise form of option **(b)**. The complete negative matrix closes the
bounded cross0/cross40/cross80 experiment and restores cross0 as the unchanged operational
baseline. It does **not** close Gate 2, because no sustainable GDFT service contract was
selected. Gate 3 remains dependency-blocked until Gate 2 is closed by one of the explicit
exit paths below.

Cross0 is a rollback state, not an accepted service contract. Treating restoration as
acceptance would convert a measured failure into a green gate without changing the
system or its requirements.

## Why the apparent plan tension resolves this way

The execution plan contains both statements:

1. when no candidate meets compute and product contracts, retain the current formula
   and reopen cadence/feature requirements
   (`EXECUTION_PLAN.md:377-390`); and
2. Gate 3 depends on Gate 2 (`EXECUTION_PLAN.md:392-394`).

The first statement defines the **failure disposition** of the Gate-2 behaviour-change
unit: do not promote a worse or unproven candidate; restore cross0; reopen the upstream
contract. It does not say that a known-unsustainable formula becomes the selected
service contract. The plan's systems ordering is explicit: select a sustainable spectral
contract before repairing generation ownership (`EXECUTION_PLAN.md:116-133`). Gate 1 is
equally explicit that an unsustainable service path may proceed **only** to Gate 2
(`EXECUTION_PLAN.md:356-375`).

Gate 3 also requires its copy/lock candidate to preserve service and freshness margins
(`EXECUTION_PLAN.md:411-417`). Those margins cannot meaningfully be declared preserved
as an admission success when the inherited service path already fails them. Allowing
Gate 3 now would add copy and lock cost to a path whose p99 is already over budget, then
make the causal comparison ambiguous.

The Gate-0 contract binds a 7,500 us arrival period and an AP-service p99 ceiling of
80% of arrival, or 6,000 us (`gate0/contract.json:21-26,44-55`). The corrected complete
matrix reports active-work p99 values of 7,571–11,820 us across all candidates and
fixtures; every candidate fails (`gate2-device-ab-inconclusive.md:44-63`). The independent
audit recomputed the same result and accepted `GATE2_SELECTION = BLOCKED_OPEN` and
`GATE3_ENTRY = BLOCKED_BY_GATE2`
(`gate2-device-independent-review.md:225-241`).

## Legal Gate-2 exit paths

Gate 2 may close through either path, but neither has occurred:

1. **Existing contract retained:** after a decomposition review, a new bounded service-
   demand candidate passes the frozen 6,000 us p99 requirement, bounded backlog/sample
   age, semantic regression and the applicable product contract.
2. **Requirements deliberately changed:** Captain authorises one concrete cadence or
   feature-contract revision. It lands as a separate contract commit, Gate 0 is fully
   requalified, and Gate 2 is rerun against the newly frozen contract. The Gate-0
   threshold rule expressly prohibits a production unit from editing its own acceptance
   criteria (`gate0/contract.json:57-63`).

The second path is not permission to hide the deficit through a larger hop, higher
priority or an ad hoc threshold relaxation. The execution plan explicitly rejects those
shortcuts (`EXECUTION_PLAN.md:388-390`). Any proposed requirement change must name the
product consequence and preserve the locked AP0/VP1 topology.

Because several candidates have already failed, the next engineering action is a
**decomposition review**, not another speculative crossover. The plan's bounded-retry
rule requires decomposition after repeated red evidence (`EXECUTION_PLAN.md:565-567`).
The review should attribute the remaining real-music p99 tail across GDFT and non-GDFT
AP work, then produce either a testable candidate under the frozen contract or a
specific product trade-off for Captain.

## Captain-owned decision boundary

No Captain decision is needed to interpret the current evidence: the frozen oracle
mechanically rejects all three candidates and blocks Gate 3.

Captain's smallest future decision is required only if engineering cannot produce a
compute-passing candidate under the existing contract. At that point the team must
present one concrete, evidence-backed cadence/feature trade-off for **accept or reject**.
Captain owns that product-definition change; he is not being asked to waive a red gate,
select an arbitrary crossover, or design the replacement algorithm.

## Two-unit product A/B relevance

The two-unit, simultaneous, multi-track, 30–60 minute procedure does not affect the
current Gate-2 decision. Compute and product acceptance are conjunctive. Since every
candidate already fails the compute contract, no perceptual result can promote one, and
spending another product session on these dominated candidates has no decision value.

Retain the corrected product procedure for the first behaviour-changing candidate that
passes compute and semantic admission. Cross0 needs no new product comparison merely to
serve as the unchanged rollback baseline. The Captain's inconclusive sequential test
remains correctly bounded and must not be reinterpreted as equivalence or preference
(`gate2-device-ab-inconclusive.md:74-87`).

## Final stamp

```text
MATRIX_COMPLETE                    = YES
MATRIX_RESULT                      = COMPLETE_NEGATIVE
CURRENT_FORMULA_RETAINED           = ROLLBACK_ONLY
SUSTAINABLE_SERVICE_SELECTED       = NO
GATE2_CLOSED                       = NO
GATE3_AUTHORISED                   = NO
NEXT_NODE                          = G2_DECOMPOSITION_AND_REQUIREMENTS_REOPEN
```

This preserves the plan's intended leverage order: service capacity first, coherent
publication second. It also avoids converting a well-measured failure into procedural
permission to advance.
