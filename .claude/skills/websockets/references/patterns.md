# WebSocket Patterns Reference

## Contents
- Message JSON Schema
- Handshake Sequence
- Anti-Patterns
- Error Handling
- Integration with UI Layer

---

## Message JSON Schema

All messages are JSON objects with a `type` discriminator:

```json
// K1 → Tab5 capability advertisement
{ "type": "capabilities", "version": 2, "controls": [...] }

// Tab5 → K1 number control
{ "type": "control", "name": "brightness", "value": 0.75 }

// Tab5 → K1 text control
{ "type": "control", "name": "preset", "value": "fire" }

// Handshake hello
{ "type": "hello", "client": "tab5", "protocol_version": 2 }
```

All serialization uses ArduinoJson. Allocate `StaticJsonDocument` on the stack for outbound messages (size matched to expected payload). See the **python** skill for the Python-side schema mirror in the harness.

---

## Handshake Sequence

```
Tab5                     K1 Firmware
  |                           |
  |--- hello (v2) ----------->|
  |<-- capabilities ----------|
  |--- requestK1State() ----->|
  |<-- state -----------------|
  |      [CONNECTED+Ready]    |
  |--- sendK1NumberControl -->|
```

**NEVER send control messages before the Ready phase completes.** `K1WebSocketStatus::CONNECTED` alone is insufficient — the capabilities/state exchange must finish first. Check the internal handshake phase flag (private), or gate on `isConnected()` combined with a `capabilitiesReceived` flag if you need fine-grain control.

---

## Anti-Patterns

### WARNING: Calling `_ws.sendTXT()` Directly from UI Code

**The Problem:**
```cpp
// BAD — bypasses routing, skips serialization helpers, breaks test replay
_ws.sendTXT("{\"type\":\"control\",\"name\":\"mode\",\"value\":3}");
```

**Why This Breaks:**
1. String-literal JSON is not validated — a typo silently sends malformed messages.
2. Bypasses `K1SendResult` — callers lose ack tracking.
3. Test harness cannot intercept raw `sendTXT` calls; transcript replay breaks.

**The Fix:**
```cpp
// GOOD — use the typed API
g_wsClient.sendK1NumberControl("mode", 3.0f);
```

---

### WARNING: Reconnect Logic Outside `update()`

**The Problem:**
```cpp
// BAD — adds a second reconnect path; fights the built-in backoff
void myTask() {
    while (!g_wsClient.isConnected()) {
        g_wsClient.begin(host, port);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}
```

**Why This Breaks:**
1. Two reconnect paths race; one resets backoff state of the other.
2. `vTaskDelay` in the network task blocks `_ws.loop()`, dropping incoming frames.
3. Exponential backoff is already implemented — 1 s → 30 s. Don't replicate it.

**The Fix:** Call `g_wsClient.update()` once per loop iteration. The reconnect backoff runs automatically.

---

### WARNING: Blocking JSON Parse on the Network Task

**The Problem:**
```cpp
// BAD — large DynamicJsonDocument allocation on network task stack
DynamicJsonDocument doc(4096);
deserializeJson(doc, payload);
```

**Why This Breaks:**
1. ESP32-S3 network task stack is limited; heap allocation under interrupt-adjacent tasks causes fragmentation.
2. `DynamicJsonDocument` heap-allocates; prefer `StaticJsonDocument` sized to known schema.

**The Fix:**
```cpp
// GOOD — stack-allocated, sized to actual message
StaticJsonDocument<256> doc;
DeserializationError err = deserializeJson(doc, payload);
if (err) { /* log and return */ }
```

---

## Error Handling

```cpp
// In WebSocket event handler (existing pattern in K1WebSocketClient.cpp)
case WStype_ERROR:
    _status = K1WebSocketStatus::ERROR;
    _reconnectBackoff = min(_reconnectBackoff * 2, MAX_BACKOFF_MS);
    break;

case WStype_DISCONNECTED:
    _status = K1WebSocketStatus::DISCONNECTED;
    // update() will attempt reconnect after backoff
    break;
```

Log the `WStype` in all cases. Silent error swallowing makes offline debugging impossible — the `Tab5SerialHarness` needs error events to reproduce failure modes.

---

## Integration with UI Layer

`LightComposerUI` and `ConnectivityTab` read `g_wsClient.isConnected()` to render status. UI must NEVER call `sendK1*` directly in render paths — only in event callbacks (button press, encoder change). Render is called at display rate (~30 fps); injecting sends there creates message storms.

```cpp
// GOOD — send only on state change event
void onBrightnessEncoderChanged(int delta) {
    _brightness = clamp(_brightness + delta * 0.05f, 0.0f, 1.0f);
    if (g_wsClient.isConnected()) {
        g_wsClient.sendK1NumberControl("brightness", _brightness);
    }
}

// BAD — polled in render loop
void render() {
    g_wsClient.sendK1NumberControl("brightness", _brightness); // floods K1
}
```