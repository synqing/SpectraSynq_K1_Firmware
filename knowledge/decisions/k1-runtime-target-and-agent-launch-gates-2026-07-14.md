---
title: K1 Runtime Target and Agent Launch Gates
status: verified
last_verified: 2026-07-14
sources:
  - docs/forensics/2026-07-14-bench-k1-targeting-and-agent-stall-incident.md
  - scripts/platformio/k1_session_target.py
  - scripts/agent/delegation_guard.py
owner: knowledge-curator
---

# K1 Runtime Target and Agent Launch Gates

## Decision

- [FACT] Every K1 upload and measurement requires `.devin/k1-session-target.json`.
- [FACT] The pin binds chip ID, USB serial, explicit ports, allowed environments, purpose, current HEAD, and a maximum four-hour expiry.
- [FACT] Persistent manifest authorisation remains necessary but is not sufficient for upload.
- [FACT] Measurement playback cannot start until runtime `BUILD` environment and `CHIP_ID` match.
- [FACT] Delegation fan-out is capped at two. Each launch is registered before dispatch, acknowledged within 30 seconds, and checkpointed within five minutes.
- [FACT] A missed acknowledgement or checkpoint blocks new delegation until explicitly closed.

## Rationale and boundary

[FACT] The incident proved that persistent USB identity can authorise a board that is nevertheless wrong for the mission, and that post-launch wait rules cannot protect a launch call that never returns.

[INFERENCE] Session intent must therefore be expiring machine-readable state, and fan-out may increase only after earlier launches are observable.

[FACT] These guards do not prove microphone placement, room silence, acoustic ground truth, or perceptual quality. The delegation ledger cannot pre-empt a platform call already blocked.

