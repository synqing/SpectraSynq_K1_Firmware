---
name: k1-ap-websocket-stack
description: "Use when implementing or modifying WiFi configuration, network server, REST API, or WebSocket communication on any K1-family ESP32 device — enforces AP-ONLY architecture and WebSocket lifecycle discipline"
---

# K1 AP + WebSocket Stack

WiFi and network communication rules for K1-family ESP32 devices. These constraints are non-negotiable -- violating the AP-ONLY rule alone has wasted 6+ engineering sessions.

## AP-ONLY Iron Law (NON-NEGOTIABLE)

```
K1 boots as WiFi Access Point. Tab5 and iOS connect TO it. NEVER attempt STA mode.
```

**Any PR that adds STA connection logic MUST be rejected.** No exceptions, no "hybrid mode," no "fallback to STA."

### Root Cause Archive

STA mode was attempted across 6+ sessions. Every attempt failed:

| Disconnect Reason | Code | Outcome |
|---|---|---|
| `AUTH_EXPIRE` | reason 2 | Drops after seconds-minutes, unrecoverable without full reconnect |
| `AUTH_FAIL` | reason 202 | Rejected despite correct credentials; varies by AP vendor |
| `4WAY_HANDSHAKE_TIMEOUT` | reason 15 | Never completes; reconnect spin loop consumes 100% of WiFi task |

Mitigations attempted and failed: increased WPA2 timeout, static IP, channel locking, `esp_wifi_set_ps(WIFI_PS_NONE)`, listen interval tuning, reconnect backoff. **None resolved reliably.** Committing to AP-only eliminated the entire problem class.

### Why AP-Only Works

- K1 is the network authority -- no external infrastructure dependency
- AP ready within 200ms of `esp_wifi_start()` -- no DHCP race, no roaming, no channel scan
- Companion apps connect to a known SSID -- discovery is trivial

## AP Configuration Pattern

```c
wifi_config_t ap_config = {
    .ap = {
        .ssid = DEVICE_SSID,           // e.g., "LightwaveOS", "Emotiscope"
        .ssid_len = strlen(DEVICE_SSID),
        .channel = 6,                   // Fixed -- avoid auto for reliability
        .password = "",
        .max_connection = 4,
        .authmode = WIFI_AUTH_OPEN,
    },
};
ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
ESP_ERROR_CHECK(esp_wifi_start());
```

**mDNS** -- enables `<device>.local` resolution:

```c
ESP_ERROR_CHECK(mdns_init());
ESP_ERROR_CHECK(mdns_hostname_set(DEVICE_HOSTNAME));
mdns_service_add(NULL, "_http", "_tcp", 80, NULL, 0);
```

### Configuration Rules

- **SSID**: device-specific, human-readable (no MAC suffixes unless multi-unit coexistence)
- **Channel**: fixed integer (1, 6, or 11 for non-overlapping 2.4 GHz)
- **Max connections**: 4 (Tab5 + iOS + debug laptop + margin)
- **Auth**: typically open for local device control; WPA2-PSK if security required
- **Never store credentials in source** -- use Kconfig or NVS

## Server Stack Options

| Stack | Projects | Notes |
|---|---|---|
| **AsyncWebServer + AsyncWebSocket** | K1.LightwaveOS, Lightwave-Ledstrip | Arduino-ecosystem, event-driven, mature |
| **PsychicHttp** | Emotiscope.HIL | ESP-IDF native, lower overhead |

Both serve HTTP + WebSocket on same port (typically 80). Arduino = AsyncWebServer; ESP-IDF native = PsychicHttp.

## WebSocket Lifecycle

### Connection and Subscription

1. Client connects to `ws://<device>.local/ws`
2. Server sends initial state snapshot as JSON on `WS_EVT_CONNECT`
3. Client subscribes to data streams: `{"subscribe": ["audio_fft", "device_state"]}`
4. Server confirms: `{"subscribed": ["audio_fft", "device_state"]}`

Only subscribed streams are pushed -- prevents bandwidth saturation.

### Cleanup on Disconnect (CRITICAL)

On `WIFI_EVENT_AP_STADISCONNECTED`, **immediately** clean up all WebSocket state:
- Remove from all subscription lists
- Free per-client buffers
- Cancel pending outbound messages
- Log disconnect with client MAC

**If skipped:** stale entries accumulate, queues back up sending to dead sockets, eventual OOM or task starvation.

### Stale Connection Detection

- Server sends ping every 5-10 seconds; no pong within 3s = stale
- 2 consecutive missed pongs = force-close and clean up
- Alternative: application-level heartbeat if client library lacks ping/pong

## Rate Limiting

| Channel | Max Rate | Enforcement |
|---|---|---|
| HTTP requests | 20 req/sec per client | Token bucket; return 429 on exceed |
| WebSocket messages | 50 msg/sec per client | Drop oldest in queue; log warning |
| Binary frame streaming | Governed by frame budget | `[type:1][timestamp_ms:4][payload:N]` |

Binary header: byte 0 = type (uint8_t), bytes 1-4 = timestamp_ms (uint32_t LE), bytes 5-N = payload.

## REST API Conventions

**Response format** (all endpoints):

```json
{"success": true, "data": {}, "timestamp": 1710700800, "version": "1.0"}
```

**Error format**: `{"success": false, "error": "msg", "code": "INVALID_PARAMETER", "timestamp": N, "version": "1.0"}`

**URL structure**: version prefix `/api/v1/`, e.g., `/api/v1/device/state`, `/api/v1/effects/list`

### CORS Headers (REQUIRED)

Companion apps use WebView or different origins. Always set:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

Handle `OPTIONS` preflight explicitly. **Omitting CORS is a guaranteed bug** -- companion apps fail silently with no useful error in device logs.

## Thread Safety

WebSocket and HTTP handlers run on different RTOS tasks. Rules:

1. **Mutex-protect all shared state** between HTTP and WebSocket handlers
2. **Never block in a WebSocket callback** -- queue messages for a processing task if >1ms
3. **Use bounded timeout on `xQueueSend`** (not `portMAX_DELAY`) from network handlers -- drop rather than block
4. **ISR to WebSocket**: post via `xQueueSendFromISR`, let a task handle the WebSocket send

### Pattern: Non-Blocking WebSocket Handler

```c
static QueueHandle_t ws_cmd_queue;  // Created at init, size 16

void on_ws_message(AsyncWebSocketClient *client, uint8_t *data, size_t len) {
    ws_command_t cmd;
    if (parse_command(data, len, &cmd) == ESP_OK) {
        cmd.client_id = client->id();
        if (xQueueSend(ws_cmd_queue, &cmd, pdMS_TO_TICKS(5)) != pdTRUE) {
            ESP_LOGW(TAG, "WS command queue full, dropping message");
        }
    }
}
```

## Anti-Patterns (Will Be Rejected in Review)

| Anti-Pattern | Why It Fails |
|---|---|
| Adding STA connection logic | Wastes sessions; AUTH_EXPIRE/AUTH_FAIL/4WAY_HANDSHAKE never resolved despite 6+ attempts |
| Stale WebSocket connections after AP disconnect | Memory leak, queue backup, eventual OOM or task starvation |
| Unbounded queues for WebSocket messages | Heap exhaustion; use fixed-size queue with drop policy |
| CORS header omission | Companion apps fail silently; no error in device logs |
| Hardcoded WiFi credentials in source | Security violation; use Kconfig or NVS |
| Blocking in WebSocket callbacks | Blocks network task; watchdog timeout and device reset |
| Missing cleanup on client disconnect | Stale subscriptions; sends to dead sockets |
| `portMAX_DELAY` in network handler | One slow client blocks all network processing |

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-03-18 | agent:embedded-firmware-engineer | Created -- codified AP-ONLY WiFi + WebSocket patterns from 6 SpectraSynq K1-family projects |
