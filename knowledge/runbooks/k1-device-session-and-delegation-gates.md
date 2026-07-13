---
title: K1 Device Session and Delegation Gates
status: verified
last_verified: 2026-07-14
sources:
  - knowledge/decisions/k1-runtime-target-and-agent-launch-gates-2026-07-14.md
owner: knowledge-curator
---

# K1 Device Session and Delegation Gates

## Device operation

1. [FACT] Verify live branch, full HEAD, dirty state, device registry, and USB enumeration.
2. [FACT] Pin exactly one device with `k1_session_target.py pin`, including every required environment.
3. [FACT] Use explicit ports only. Auto-detection and stale defaults are prohibited.
4. [FACT] PlatformIO upload rechecks both persistent identity and session pin.
5. [FACT] After upload, hash the upload-produced binary and read runtime build environment and chip ID.
6. [FACT] After full erase, treat calibration and persisted state as invalid until deliberately re-established.
7. [FACT] Before measurement playback, require the capture harness runtime identity gate.

```bash
python3 scripts/regression-harness/device_novelty_buffer_capture.py \
  --track <absolute-track-path> --port /dev/cu.usbmodem1401 \
  --expected-chip-id B489A500 \
  --expected-build-env k1_bench_ap_frontend_probe \
  --duration-ms 120000 --capture-apcad-soak
```

## Delegation operation

1. [FACT] Fill `scripts/agent/subagent-dispatch-template.md` and register before calling the collaboration tool.
2. [FACT] Launch one at a time and immediately record the returned agent ID with `ack`.
3. [FACT] If acknowledgement is unavailable in 30 seconds, do not retry; close as `aborted` and execute the fallback locally.
4. [FACT] Never exceed two active delegations or a 300-second checkpoint.
5. [FACT] Close every delegation with evidence before increasing fan-out.

```bash
python3 scripts/agent/delegation_guard.py register \
  --id <id> --classification <load-bearing-or-optional> \
  --checkpoint-seconds 300 --artefact <result> --fallback orchestrator-local
python3 scripts/agent/delegation_guard.py ack --id <id> --agent-id <agent-id>
python3 scripts/agent/delegation_guard.py close --id <id> \
  --status received --evidence <artefact-or-summary>
```

[INFERENCE] After a blocked launch call, platform interruption and orchestrator-local execution are safer than repeated launches.
