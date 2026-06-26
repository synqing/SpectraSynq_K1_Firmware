---
name: cross-stack-integration-testing
description: "Use when verifying that firmware and software agree on protocol behaviour -- after protocol changes, before releases, or when a bug manifests only when both sides are connected."
---

# Cross-Stack Integration Testing

## Overview

Verify that firmware and software implementations agree on protocol behaviour. Unit tests on each side pass independently, but the system fails when connected -- this skill catches that class of bug.

**Core principle:** Protocol conformance is a property of the PAIR, not of either side alone.

**Announce at start:** "I'm using the cross-stack-integration-testing skill to verify protocol conformance between firmware and software."

## When to Use

**Mandatory:**
- After implementing a protocol change on both sides
- Before any release that includes cross-boundary changes
- After upgrading firmware or software version independently

**Recommended:**
- When a bug manifests only when firmware and software are connected
- Monthly hygiene check on protocol conformance
- After refactoring protocol handling on either side

## The Iron Law

```
NO RELEASE WITHOUT INTEGRATION EVIDENCE FROM BOTH SIDES
```

"Firmware tests pass" + "Software tests pass" is necessary but not sufficient. Integration tests must demonstrate the protocol contract holds.

## The Process

### Phase 1: Contract Extraction

Read the protocol specification (canonical source of truth):

```
docs/protocol/[PROTOCOL_SPEC].md
```

Extract:
- All message types (commands, responses, events, notifications)
- Field definitions for each message (name, type, byte offset, endianness)
- Value ranges and enum values
- State machine transitions (connection, pairing, data streaming, error recovery)
- Version negotiation sequence

Create a checklist of every protocol message.

### Phase 2: Gap Analysis

For each protocol message, verify test coverage on BOTH sides:

| Message | FW sends correctly? | SW parses correctly? | FW parses commands? | SW sends commands? |
|---------|--------------------|--------------------|--------------------|--------------------|
| [msg1]  | Y/N (test name)    | Y/N (test name)    | Y/N (test name)    | Y/N (test name)    |
| [msg2]  | ...                | ...                | ...                | ...                |

**Flag any message where either side is untested.** These are integration risk points.

### Phase 3: Integration Test Execution

Choose the appropriate mode:

**Mode A: Mock Integration (no hardware required)**

Software test suite runs against a firmware protocol simulator:
1. Record real firmware output (serial/BLE capture) or build simulator from spec
2. Software parses simulator output
3. Verify: correct state transitions, correct data rendering, correct commands sent back
4. Verify: graceful handling of disconnection mid-stream
5. Verify: version negotiation with older firmware versions

```bash
# Example test runner invocation
[SOFTWARE_DIR]/[TEST_COMMAND] --integration --mock-firmware
```

**Mode B: Hardware Integration (device required)**

Software connects to real firmware device:
1. Exercise every protocol message type
2. Verify: round-trip for each command/response pair
3. Verify: disconnection and reconnection recovery
4. Verify: version negotiation
5. Measure: latency for each message type

```bash
# Example: ensure device is connected, then run
[SOFTWARE_DIR]/[TEST_COMMAND] --integration --hardware
```

### Phase 4: Report

Structure the report as:

```
## Integration Test Report -- [DATE]

### Coverage
- Protocol messages tested: X/Y (Z%)
- Firmware-side gaps: [list untested messages]
- Software-side gaps: [list untested messages]

### Results
- Passed: X
- Failed: Y
- Skipped: Z (reason)

### Failures
For each failure:
- Message: [name]
- Expected: [per spec]
- Firmware produced: [actual bytes/values]
- Software received: [what it parsed]
- Root cause: [firmware encoding / software decoding / spec ambiguity]
- Fix required in: [firmware / software / spec]

### Recommendation
[Ship / Fix firmware / Fix software / Update spec / Block release]
```

## Integration with Superpowers

- **If a failure is found:** Transition to `/systematic-debugging` or `/cross-stack-debugging` (if the bug requires both sides running)
- **If tests are missing:** Transition to `/test-driven-development` to write the integration test
- **Before claiming done:** MUST use `/verification-before-completion` with evidence from the integration test run

## Red Flags

**Never:**
- Skip Phase 2 (gap analysis). Untested protocol messages are the highest-risk integration points.
- Claim "integration tested" based on Mode A alone when Mode B is available and the release ships hardware.
- Trust simulator output without periodically validating against real firmware captures.
- Skip disconnection/reconnection testing. This is where 50% of integration bugs live.

**Always:**
- Update the protocol spec if you find a discrepancy (spec is truth, not code)
- Test backward compatibility with at least one previous firmware version
- Report coverage percentage honestly -- gaps are information, not failure
