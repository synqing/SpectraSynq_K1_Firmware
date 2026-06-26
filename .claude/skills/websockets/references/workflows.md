# WebSocket Workflows Reference

## Contents
- Adding a New Message Type
- Debugging Reconnect Issues
- Testing with the Python Harness
- Offline / Disconnected Testing Checklist

---

## Adding a New Message Type

Copy this checklist and track progress:
- [ ] Define JSON schema: `type`, required fields, value ranges
- [ ] Add outbound method to `K1WebSocketClient.h/.cpp` (follow `sendK1NumberControl` signature)
- [ ] Register handler in `WsMessageRouter` for inbound direction
- [ ] Add `K1SendResult` check at every call site
- [ ] Add schema to Python harness mirror (`tools/tab5_k1_dashboard_harness.py`)
- [ ] Add replay fixture in `tests/fixtures/tab5/` for the new message
- [ ] Run `pytest tests/ -v` — all transcript replay tests must pass

Iterate until pass:
1. Add message type + handler
2. `pytest tests/test_tab5_dispatch_replay.py -v`
3. Fix any schema mismatch; repeat step 2

---

## Debugging Reconnect Issues

**Symptom:** Tab5 connects, handshake completes, then drops after N seconds.

1. Enable serial monitor: `pio device monitor` (115200 baud)
2. Look for `WStype_DISCONNECTED` log entries — note timestamp delta from last send
3. Check K1 firmware side: `WIFI_AP_ONLY` compile flag is NOT set (dual-mode shipped `ab8ef0ae`)
4. Verify backoff is not saturated at 30 s — if it is, the K1 AP may be changing SSID/channel

```bash
# Grep for backoff constant in source
grep -r "MAX_BACKOFF\|reconnect" sb-tab5-wireless-controller/src/network/
```

**Symptom:** Tab5 never reaches Ready phase (stuck at CONNECTING).

1. Check `network_config.h` for correct host/port
2. Verify K1 is broadcasting on expected SSID (AP mode) or is reachable (STA mode)
3. `requestK1Capabilities()` response timeout: if K1 firmware is on a branch without capability advertisement, handshake stalls — fall back to v1 path

---

## Testing with the Python Harness

The Python dashboard harness (`tools/tab5_k1_dashboard_harness.py`) provides a WebSocket server stub for host-side testing without hardware.

```bash
# Start the stub server (new code to add if not present — check tools/ first)
python tools/tab5_k1_dashboard_harness.py --port 8080

# Run harness-dependent tests
pytest tests/test_tab5_harness_strict_mode.py -v
pytest tests/test_tab5_dispatch_replay.py -v
```

See the **pytest** skill for test file organization and fixture conventions.
See the **python** skill for harness script patterns and async server setup.
See the **aiofiles** skill if the harness reads/writes transcript files asynchronously.
See the **click** skill for CLI argument parsing in harness tooling.

**Transcript replay pattern:**
1. Capture a live session transcript (JSON-lines, one message per line)
2. Save to `tests/fixtures/tab5/<scenario>.jsonl`
3. Replay via `test_tab5_harness_transcript_replay.py` — verifies dispatch routing deterministically

---

## Offline / Disconnected Testing Checklist

UI and control logic must degrade gracefully when WebSocket is down.

- [ ] All `sendK1*` call sites check `isConnected()` before sending
- [ ] UI status widget shows DISCONNECTED state (not frozen on last known state)
- [ ] Encoder / button inputs are buffered or silently dropped — NEVER panic/assert on send failure
- [ ] `K1SendResult.success == false` paths are handled (no UB on unacked requests)
- [ ] Reconnect eventually succeeds after K1 AP restarts — test by power-cycling K1 while Tab5 runs

Validate offline behaviour:
1. Flash Tab5, confirm connection in serial monitor
2. Power-cycle K1 (AP disappears)
3. Observe Tab5 serial: should log DISCONNECTED, then periodic reconnect attempts with backoff
4. Power K1 back on — Tab5 should reconnect and complete full handshake without reboot
5. Send a control message — confirm it reaches K1 (check K1 serial or effect response)