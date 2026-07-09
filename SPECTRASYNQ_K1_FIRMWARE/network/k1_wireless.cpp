#ifdef K1_WIRELESS_ENABLED

#include "k1_wireless.h"

#include <Arduino.h>
#include <WebSocketsServer.h>
#include <WiFi.h>
#include <ctype.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <stdlib.h>
#include <string.h>

#include "k1_control_facade.h"
#include "k1_wireless_control.h"

namespace {

constexpr const char* K1_AP_SSID = "LightwaveOS-AP";
constexpr const char* K1_AP_PASSWORD = "";
const IPAddress K1_AP_IP(192, 168, 4, 1);
const IPAddress K1_AP_GATEWAY(192, 168, 4, 1);
const IPAddress K1_AP_SUBNET(255, 255, 255, 0);
constexpr uint16_t K1_WS_PORT = 80;
constexpr uint8_t QUEUE_CAPACITY = 8;
constexpr size_t RX_LIMIT = 768;
constexpr size_t TX_LIMIT = 1024;
constexpr uint8_t K1_WS_PROTOCOL_V1 = 1;
constexpr uint8_t K1_WS_PROTOCOL_V2 = 2;
constexpr uint8_t MAX_REQUESTS_PER_AP_TICK = 4;
constexpr uint8_t MAX_FRAMES_PER_WS_TICK = 4;
constexpr uint32_t WS_TASK_DELAY_MS = 5;
constexpr uint32_t AP_IDLE_YIELD_INTERVAL_MS = 250;
constexpr UBaseType_t WS_TASK_PRIORITY = tskIDLE_PRIORITY + 1;

#ifndef K1_CONTROL_TOKEN
#define K1_CONTROL_TOKEN "k1-tab5"
#endif

#ifndef K1_WIRELESS_TASK_CORE
#ifdef K1_WS_TASK_CORE
#define K1_WIRELESS_TASK_CORE K1_WS_TASK_CORE
#else
#define K1_WIRELESS_TASK_CORE 0
#endif
#endif

#if defined(K1_LED_TASK_CORE) && (K1_WIRELESS_TASK_CORE == K1_LED_TASK_CORE)
#error "K1 wireless task must not run on the LED render core"
#endif

enum K1WirelessRequestKind : uint8_t {
  K1_REQUEST_NONE = 0,
  K1_REQUEST_HELLO,
  K1_REQUEST_CONTROL_SET,
  K1_REQUEST_STATE_GET,
  K1_REQUEST_CAPABILITIES_GET
};

struct K1WirelessRequest {
  K1WirelessRequestKind kind;
  uint8_t client_num;
  uint8_t protocol_version;
  uint32_t id;
  K1WirelessControlRecord record;
};

struct QueuedWirelessFrame {
  bool used;
  uint8_t client_num;
  char payload[TX_LIMIT];
};

WebSocketsServer g_ws(K1_WS_PORT, "/ws");
K1WirelessRequest g_request_queue[QUEUE_CAPACITY];
QueuedWirelessFrame g_frame_queue[QUEUE_CAPACITY];
uint8_t g_request_head = 0;
uint8_t g_request_tail = 0;
uint8_t g_request_count = 0;
uint8_t g_frame_head = 0;
uint8_t g_frame_tail = 0;
uint8_t g_frame_count = 0;
uint8_t g_reserved_frame_count = 0;
portMUX_TYPE g_queue_mux = portMUX_INITIALIZER_UNLOCKED;
TaskHandle_t g_ws_task_handle = nullptr;
volatile bool g_ap_started = false;
uint32_t g_last_ap_idle_yield_ms = 0;
uint32_t g_tx_drop_count = 0;
uint32_t g_last_client_request_id[QUEUE_CAPACITY] = {};

const char* skip_ws(const char* p) {
  while (*p && isspace(static_cast<unsigned char>(*p))) {
    ++p;
  }
  return p;
}

bool json_number_terminated(const char* p) {
  p = skip_ws(p);
  return *p == '\0' || *p == ',' || *p == '}';
}

bool looks_like_json_object(const char* json) {
  if (json == nullptr) {
    return false;
  }
  const char* start = skip_ws(json);
  if (*start != '{') {
    return false;
  }
  const char* end = start + strlen(start);
  while (end > start && isspace(static_cast<unsigned char>(end[-1]))) {
    --end;
  }
  return end > start && end[-1] == '}';
}

bool json_key_span_equals(const char* start, const char* end, const char* key) {
  if (start == nullptr || end == nullptr || key == nullptr || end < start) {
    return false;
  }
  const size_t span_len = size_t(end - start);
  return strlen(key) == span_len && strncmp(start, key, span_len) == 0;
}

uint8_t duplicate_json_key_count(const char* json, const char* key) {
  if (json == nullptr || key == nullptr) {
    return 0;
  }

  uint8_t count = 0;
  uint8_t depth = 0;
  bool in_string = false;
  bool candidate_key = false;
  bool expect_key = false;
  const char* string_start = nullptr;

  for (const char* p = json; *p; ++p) {
    if (in_string) {
      if (*p == '\\') {
        return UINT8_MAX;
      }
      if (*p == '"') {
        if (candidate_key && json_key_span_equals(string_start, p, key) && count < UINT8_MAX) {
          ++count;
        }
        in_string = false;
        candidate_key = false;
        string_start = nullptr;
        if (expect_key) {
          expect_key = false;
        }
      }
      continue;
    }

    if (*p == '"') {
      in_string = true;
      candidate_key = depth == 1 && expect_key;
      string_start = p + 1;
      continue;
    }
    if (*p == '{') {
      if (++depth != 1) {
        return UINT8_MAX;
      }
      expect_key = true;
      continue;
    }
    if (*p == '}') {
      if (depth == 0) {
        return UINT8_MAX;
      }
      --depth;
      continue;
    }
    if (*p == '[' || *p == ']') {
      return UINT8_MAX;
    }
    if (*p == ',' && depth == 1) {
      expect_key = true;
      continue;
    }
  }
  return count;
}

bool has_duplicate_json_protocol_keys(const char* json) {
  static constexpr const char* KEYS[] = {"type", "v", "id", "token", "control", "value"};
  for (const char* key : KEYS) {
    if (duplicate_json_key_count(json, key) > 1) {
      return true;
    }
  }
  return false;
}

const char* find_key(const char* json, const char* key) {
  char pattern[40];
  snprintf(pattern, sizeof(pattern), "\"%s\"", key);
  const char* p = strstr(json, pattern);
  if (p == nullptr) {
    return nullptr;
  }
  p += strlen(pattern);
  p = skip_ws(p);
  if (*p != ':') {
    return nullptr;
  }
  return skip_ws(p + 1);
}

bool read_json_string(const char* json, const char* key, char* out, size_t out_len) {
  const char* p = find_key(json, key);
  if (p == nullptr || *p != '"' || out_len == 0) {
    return false;
  }
  ++p;
  size_t i = 0;
  while (*p && *p != '"' && i + 1 < out_len) {
    if (*p == '\\') {
      return false;
    }
    out[i++] = *p++;
  }
  if (*p != '"') {
    return false;
  }
  out[i] = '\0';
  return true;
}

bool read_json_u32(const char* json, const char* key, uint32_t* out) {
  const char* p = find_key(json, key);
  if (p == nullptr || out == nullptr || *p == '"') {
    return false;
  }
  p = skip_ws(p);
  if (*p == '-' || *p == '+') {
    return false;
  }
  char* end = nullptr;
  unsigned long value = strtoul(p, &end, 10);
  if (end == p || value > UINT32_MAX || !json_number_terminated(end)) {
    return false;
  }
  *out = static_cast<uint32_t>(value);
  return true;
}

bool read_json_float(const char* json, const char* key, float* out) {
  const char* p = find_key(json, key);
  if (p == nullptr || out == nullptr || *p == '"') {
    return false;
  }
  char* end = nullptr;
  float value = strtof(p, &end);
  if (end == p || !json_number_terminated(end)) {
    return false;
  }
  *out = value;
  return true;
}

void queue_counts(uint8_t* requests, uint8_t* frames, uint32_t* tx_dropped) {
  portENTER_CRITICAL(&g_queue_mux);
  if (requests != nullptr) {
    *requests = g_request_count;
  }
  if (frames != nullptr) {
    *frames = g_frame_count;
  }
  if (tx_dropped != nullptr) {
    *tx_dropped = g_tx_drop_count;
  }
  portEXIT_CRITICAL(&g_queue_mux);
}

bool request_queue_has_pending() {
  bool pending = false;
  portENTER_CRITICAL(&g_queue_mux);
  pending = g_request_count > 0;
  portEXIT_CRITICAL(&g_queue_mux);
  return pending;
}

bool reserve_frame_capacity() {
  bool ok = false;
  portENTER_CRITICAL(&g_queue_mux);
  if (uint8_t(g_frame_count + g_reserved_frame_count) < QUEUE_CAPACITY) {
    ++g_reserved_frame_count;
    ok = true;
  }
  portEXIT_CRITICAL(&g_queue_mux);
  return ok;
}

void release_frame_reservation() {
  portENTER_CRITICAL(&g_queue_mux);
  if (g_reserved_frame_count > 0) {
    --g_reserved_frame_count;
  }
  portEXIT_CRITICAL(&g_queue_mux);
}

bool enqueue_frame_payload(uint8_t client_num, const char* payload, bool reserved = false) {
  if (payload == nullptr || payload[0] == '\0') {
    if (reserved) {
      release_frame_reservation();
    }
    return false;
  }

  bool ok = false;
  portENTER_CRITICAL(&g_queue_mux);
  const bool can_use_slot = reserved
    ? (g_reserved_frame_count > 0 && g_frame_count < QUEUE_CAPACITY)
    : (uint8_t(g_frame_count + g_reserved_frame_count) < QUEUE_CAPACITY);
  if (can_use_slot) {
    if (reserved && g_reserved_frame_count > 0) {
      --g_reserved_frame_count;
    }
    g_frame_queue[g_frame_tail].used = true;
    g_frame_queue[g_frame_tail].client_num = client_num;
    strlcpy(g_frame_queue[g_frame_tail].payload, payload, sizeof(g_frame_queue[g_frame_tail].payload));
    g_frame_tail = uint8_t((g_frame_tail + 1U) % QUEUE_CAPACITY);
    ++g_frame_count;
    ok = true;
  } else {
    if (reserved && g_reserved_frame_count > 0) {
      --g_reserved_frame_count;
    }
    ++g_tx_drop_count;
  }
  portEXIT_CRITICAL(&g_queue_mux);
  return ok;
}

bool dequeue_frame(QueuedWirelessFrame* out) {
  if (out == nullptr) {
    return false;
  }

  bool ok = false;
  portENTER_CRITICAL(&g_queue_mux);
  if (g_frame_count > 0) {
    *out = g_frame_queue[g_frame_head];
    g_frame_queue[g_frame_head].used = false;
    g_frame_queue[g_frame_head].payload[0] = '\0';
    g_frame_head = uint8_t((g_frame_head + 1U) % QUEUE_CAPACITY);
    --g_frame_count;
    ok = true;
  }
  portEXIT_CRITICAL(&g_queue_mux);
  return ok;
}

bool enqueue_request(const K1WirelessRequest& request) {
  bool ok = false;
  portENTER_CRITICAL(&g_queue_mux);
  if (g_request_count < QUEUE_CAPACITY) {
    g_request_queue[g_request_tail] = request;
    g_request_tail = uint8_t((g_request_tail + 1U) % QUEUE_CAPACITY);
    ++g_request_count;
    ok = true;
  }
  portEXIT_CRITICAL(&g_queue_mux);
  return ok;
}

bool dequeue_request(K1WirelessRequest* out) {
  if (out == nullptr) {
    return false;
  }

  bool ok = false;
  portENTER_CRITICAL(&g_queue_mux);
  if (g_request_count > 0) {
    *out = g_request_queue[g_request_head];
    memset(&g_request_queue[g_request_head], 0, sizeof(g_request_queue[g_request_head]));
    g_request_head = uint8_t((g_request_head + 1U) % QUEUE_CAPACITY);
    --g_request_count;
    ok = true;
  }
  portEXIT_CRITICAL(&g_queue_mux);
  return ok;
}

void reset_client_request_tracker(uint8_t client_num) {
  if (client_num >= QUEUE_CAPACITY) {
    return;
  }
  portENTER_CRITICAL(&g_queue_mux);
  g_last_client_request_id[client_num] = 0;
  portEXIT_CRITICAL(&g_queue_mux);
}

bool request_id_is_fresh(uint8_t client_num, uint32_t request_id) {
  if (request_id == 0 || client_num >= QUEUE_CAPACITY) {
    return true;
  }

  bool fresh = false;
  portENTER_CRITICAL(&g_queue_mux);
  fresh = request_id > g_last_client_request_id[client_num];
  portEXIT_CRITICAL(&g_queue_mux);
  return fresh;
}

void commit_client_request_id(uint8_t client_num, uint32_t request_id) {
  if (request_id == 0 || client_num >= QUEUE_CAPACITY) {
    return;
  }
  portENTER_CRITICAL(&g_queue_mux);
  if (request_id > g_last_client_request_id[client_num]) {
    g_last_client_request_id[client_num] = request_id;
  }
  portEXIT_CRITICAL(&g_queue_mux);
}

const char* protocol_error_message(const char* code) {
  if (strcmp(code, "size") == 0) return "Payload size out of range";
  if (strcmp(code, "json") == 0) return "Unsupported JSON payload";
  if (strcmp(code, "type") == 0) return "Unsupported request type";
  if (strcmp(code, "version") == 0) return "Unsupported protocol version";
  if (strcmp(code, "auth") == 0) return "Control token rejected";
  if (strcmp(code, "id") == 0) return "Request id required";
  if (strcmp(code, "control") == 0) return "Control path required";
  if (strcmp(code, "unsupported") == 0) return "Unsupported control";
  if (strcmp(code, "value") == 0) return "Value required";
  if (strcmp(code, "busy") == 0) return "K1 request queue full";
  if (strcmp(code, "replay") == 0) return "Stale or replayed request id";
  return "Protocol error";
}

bool queue_control_error(uint8_t client_num,
                         uint32_t id,
                         const char* control,
                         const char* code,
                         const char* message,
                         uint8_t protocol_version,
                         bool reserved = false) {
  char payload[TX_LIMIT];
  snprintf(payload, sizeof(payload),
           "{\"type\":\"k1.control.result\",\"v\":%u,\"id\":%lu,\"ok\":false,\"control\":\"%s\","
           "\"error\":{\"code\":\"%s\",\"message\":\"%s\"}}",
           unsigned(protocol_version),
           static_cast<unsigned long>(id),
           control ? control : "",
           code ? code : "error",
           message ? message : "Protocol error");
  return enqueue_frame_payload(client_num, payload, reserved);
}

bool queue_error(uint8_t client_num,
                 uint32_t id,
                 const char* code,
                 const char* message,
                 uint8_t protocol_version,
                 bool reserved = false) {
  char payload[TX_LIMIT];
  snprintf(payload, sizeof(payload),
           "{\"type\":\"k1.error\",\"v\":%u,\"id\":%lu,\"ok\":false,"
           "\"error\":{\"code\":\"%s\",\"message\":\"%s\"}}",
           unsigned(protocol_version),
           static_cast<unsigned long>(id),
           code ? code : "error",
           message ? message : "Protocol error");
  return enqueue_frame_payload(client_num, payload, reserved);
}

bool queue_control_result(uint8_t client_num,
                          const K1WirelessControlRecord& record,
                          const K1WirelessControlResult& result,
                          uint8_t protocol_version,
                          bool reserved = false) {
  char payload[TX_LIMIT];
  if (result.ok && result.value_kind == K1_WIRELESS_VALUE_TEXT) {
    snprintf(payload, sizeof(payload),
             "{\"type\":\"k1.control.result\",\"v\":%u,\"id\":%lu,\"ok\":true,\"control\":\"%s\","
             "\"value\":\"%s\",\"seq\":%lu}",
             unsigned(protocol_version),
             static_cast<unsigned long>(record.id),
             record.control,
             result.text_value,
             static_cast<unsigned long>(result.seq));
  } else if (result.ok && result.value_kind == K1_WIRELESS_VALUE_NUMBER) {
    snprintf(payload, sizeof(payload),
             "{\"type\":\"k1.control.result\",\"v\":%u,\"id\":%lu,\"ok\":true,\"control\":\"%s\","
             "\"value\":%.4f,\"seq\":%lu}",
             unsigned(protocol_version),
             static_cast<unsigned long>(record.id),
             record.control,
             double(result.number_value),
             static_cast<unsigned long>(result.seq));
  } else {
    return queue_control_error(client_num,
                               record.id,
                               record.control,
                               result.error_code,
                               result.error_message,
                               protocol_version,
                               reserved);
  }
  return enqueue_frame_payload(client_num, payload, reserved);
}

bool queue_hello(uint8_t client_num, uint32_t id, uint8_t protocol_version, bool reserved = false) {
  uint8_t request_count = 0;
  uint8_t frame_count = 0;
  uint32_t tx_dropped = 0;
  queue_counts(&request_count, &frame_count, &tx_dropped);

  char payload[TX_LIMIT];
  snprintf(payload, sizeof(payload),
           "{\"type\":\"k1.hello\",\"v\":%u,\"id\":%lu,\"ok\":true,\"device\":\"K1\","
           "\"mode\":\"ap\",\"token\":\"accepted\",\"limits\":{\"rx\":%u,\"tx\":%u,\"queue\":%u,"
           "\"perTick\":%u},\"queued\":{\"rx\":%u,\"tx\":%u,\"tx_dropped\":%lu}}",
           unsigned(protocol_version),
           static_cast<unsigned long>(id),
           unsigned(RX_LIMIT),
           unsigned(TX_LIMIT),
           unsigned(QUEUE_CAPACITY),
           unsigned(MAX_REQUESTS_PER_AP_TICK),
           unsigned(request_count),
           unsigned(frame_count),
           static_cast<unsigned long>(tx_dropped));
  return enqueue_frame_payload(client_num, payload, reserved);
}

bool queue_capabilities(uint8_t client_num, uint32_t id, uint8_t protocol_version, bool reserved = false) {
  char capabilities[TX_LIMIT - 96];
  (void)k1_control_capabilities_json(capabilities, sizeof(capabilities), protocol_version);

  char payload[TX_LIMIT];
  snprintf(payload, sizeof(payload),
           "{\"type\":\"k1.capabilities\",\"v\":%u,\"id\":%lu,\"ok\":true,\"capabilities\":%s}",
           unsigned(protocol_version),
           static_cast<unsigned long>(id),
           capabilities);
  return enqueue_frame_payload(client_num, payload, reserved);
}

bool queue_state(uint8_t client_num, uint32_t id, uint8_t protocol_version, bool reserved = false) {
  K1WirelessControlState state = {};
  k1_wireless_control_snapshot(&state);

  uint8_t request_count = 0;
  uint8_t frame_count = 0;
  uint32_t tx_dropped = 0;
  queue_counts(&request_count, &frame_count, &tx_dropped);

  char payload[TX_LIMIT];
  if (protocol_version >= K1_WS_PROTOCOL_V2) {
    snprintf(payload, sizeof(payload),
             "{\"type\":\"k1.state\",\"v\":%u,\"id\":%lu,\"ok\":true,\"seq\":%lu,"
             "\"clients\":%u,\"queued\":{\"rx\":%u,\"tx\":%u,\"tx_dropped\":%lu},"
             "\"primary\":{\"mode\":%u,\"palette\":%u,\"palette_mode\":%s,\"photons\":%.4f,"
             "\"chroma\":%.4f,\"mood\":%.4f,\"saturation\":%.4f,\"fps\":%.1f},"
             "\"secondary\":{\"enabled\":%s,\"mode\":%u,\"palette\":%u,\"palette_mode\":%s,"
             "\"photons\":%.4f,\"chroma\":%.4f,\"mood\":%.4f,\"saturation\":%.4f,\"fps\":%.1f},"
             "\"scene\":{\"smart\":\"%s\"},\"tempo\":{\"bpm\":%.1f,\"locked\":%s}}",
             unsigned(protocol_version),
             static_cast<unsigned long>(id),
             static_cast<unsigned long>(state.seq),
             unsigned(k1_wireless_client_count()),
             unsigned(request_count),
             unsigned(frame_count),
             static_cast<unsigned long>(tx_dropped),
             unsigned(state.primary_mode),
             unsigned(state.primary_palette),
             state.primary_palette_mode ? "true" : "false",
             double(state.primary_photons),
             double(state.primary_chroma),
             double(state.primary_mood),
             double(state.primary_saturation),
             double(state.primary_fps),
             state.secondary_enabled ? "true" : "false",
             unsigned(state.secondary_mode),
             unsigned(state.secondary_palette),
             state.secondary_palette_mode ? "true" : "false",
             double(state.secondary_photons),
             double(state.secondary_chroma),
             double(state.secondary_mood),
             double(state.secondary_saturation),
             double(state.secondary_fps),
             state.scene_smart,
             double(state.tempo_bpm),
             state.tempo_locked ? "true" : "false");
  } else {
    snprintf(payload, sizeof(payload),
             "{\"type\":\"k1.state\",\"v\":%u,\"id\":%lu,\"ok\":true,\"seq\":%lu,"
             "\"clients\":%u,\"queued\":{\"rx\":%u,\"tx\":%u,\"tx_dropped\":%lu},"
             "\"primary\":{\"mode\":%u,\"palette\":%u,\"photons\":%.4f,\"chroma\":%.4f,\"mood\":%.4f,\"fps\":%.1f},"
             "\"secondary\":{\"mode\":%u,\"palette\":%u,\"photons\":%.4f,\"chroma\":%.4f,\"mood\":%.4f,\"fps\":%.1f},"
             "\"scene\":{\"smart\":\"%s\"},\"tempo\":{\"bpm\":%.1f,\"locked\":%s}}",
             unsigned(protocol_version),
             static_cast<unsigned long>(id),
             static_cast<unsigned long>(state.seq),
             unsigned(k1_wireless_client_count()),
             unsigned(request_count),
             unsigned(frame_count),
             static_cast<unsigned long>(tx_dropped),
             unsigned(state.primary_mode),
             unsigned(state.primary_palette),
             double(state.primary_photons),
             double(state.primary_chroma),
             double(state.primary_mood),
             double(state.primary_fps),
             unsigned(state.secondary_mode),
             unsigned(state.secondary_palette),
             double(state.secondary_photons),
             double(state.secondary_chroma),
             double(state.secondary_mood),
             double(state.secondary_fps),
             state.scene_smart,
             double(state.tempo_bpm),
             state.tempo_locked ? "true" : "false");
  }
  return enqueue_frame_payload(client_num, payload, reserved);
}

bool parse_request_payload(const uint8_t* payload,
                           size_t length,
                           K1WirelessRequest* request,
                           char* error_code,
                           size_t error_code_len) {
  if (request == nullptr || error_code == nullptr || error_code_len == 0) {
    return false;
  }

  memset(request, 0, sizeof(*request));
  if (payload == nullptr || length == 0 || length > RX_LIMIT) {
    strlcpy(error_code, "size", error_code_len);
    return false;
  }
  if (memchr(payload, '\0', length) != nullptr) {
    strlcpy(error_code, "json", error_code_len);
    return false;
  }

  char json[RX_LIMIT + 1];
  memcpy(json, payload, length);
  json[length] = '\0';
  if (!looks_like_json_object(json) || has_duplicate_json_protocol_keys(json)) {
    strlcpy(error_code, "json", error_code_len);
    return false;
  }

  char type[24] = {};
  if (!read_json_string(json, "type", type, sizeof(type))) {
    strlcpy(error_code, "type", error_code_len);
    return false;
  }

  (void)read_json_u32(json, "id", &request->id);
  request->record.id = request->id;
  (void)read_json_string(json, "control", request->record.control, sizeof(request->record.control));

  uint32_t version = 0;
  if (!read_json_u32(json, "v", &version) ||
      (version != K1_WS_PROTOCOL_V1 && version != K1_WS_PROTOCOL_V2)) {
    strlcpy(error_code, "version", error_code_len);
    return false;
  }
  request->protocol_version = uint8_t(version);

  char token[40] = {};
  if (!read_json_string(json, "token", token, sizeof(token)) || strcmp(token, K1_CONTROL_TOKEN) != 0) {
    strlcpy(error_code, "auth", error_code_len);
    return false;
  }

  if (strcmp(type, "k1.hello") == 0) {
    request->kind = K1_REQUEST_HELLO;
    return true;
  }

  if (strcmp(type, "k1.state.get") == 0) {
    if (request->id == 0) {
      strlcpy(error_code, "id", error_code_len);
      return false;
    }
    request->kind = K1_REQUEST_STATE_GET;
    return true;
  }

  if (strcmp(type, "k1.capabilities.get") == 0) {
    if (request->id == 0) {
      strlcpy(error_code, "id", error_code_len);
      return false;
    }
    request->kind = K1_REQUEST_CAPABILITIES_GET;
    return true;
  }

  if (strcmp(type, "k1.control.set") != 0) {
    strlcpy(error_code, "type", error_code_len);
    return false;
  }

  request->kind = K1_REQUEST_CONTROL_SET;
  if (request->id == 0) {
    strlcpy(error_code, "id", error_code_len);
    return false;
  }
  if (request->record.control[0] == '\0') {
    strlcpy(error_code, "control", error_code_len);
    return false;
  }
  if (!k1_wireless_control_is_allowed(request->record.control)) {
    strlcpy(error_code, "unsupported", error_code_len);
    return false;
  }

  if (read_json_string(json, "value", request->record.text_value, sizeof(request->record.text_value))) {
    request->record.value_kind = K1_WIRELESS_VALUE_TEXT;
    return true;
  }

  if (read_json_float(json, "value", &request->record.number_value)) {
    request->record.value_kind = K1_WIRELESS_VALUE_NUMBER;
    return true;
  }

  strlcpy(error_code, "value", error_code_len);
  return false;
}

void handle_ws_event(uint8_t client_num, WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      reset_client_request_tracker(client_num);
      Serial.printf("[K1WS] client %u connected\n", client_num);
      break;
    case WStype_DISCONNECTED:
      reset_client_request_tracker(client_num);
      Serial.printf("[K1WS] client %u disconnected\n", client_num);
      break;
    case WStype_TEXT: {
      K1WirelessRequest request = {};
      char error_code[24] = {};
      if (!parse_request_payload(payload, length, &request, error_code, sizeof(error_code))) {
        const uint8_t response_version =
          request.protocol_version != 0 ? request.protocol_version : K1_WS_PROTOCOL_V1;
        Serial.printf("[K1WS] client %u protocol error %s len=%u\n",
                      client_num,
                      error_code,
                      unsigned(length));
        if (request.kind == K1_REQUEST_CONTROL_SET) {
          (void)queue_control_error(client_num,
                                    request.id,
                                    request.record.control,
                                    error_code,
                                    protocol_error_message(error_code),
                                    response_version);
        } else {
          (void)queue_error(client_num,
                            request.id,
                            error_code,
                            protocol_error_message(error_code),
                            response_version);
        }
        return;
      }
      if (!request_id_is_fresh(client_num, request.id)) {
        Serial.printf("[K1WS] client %u stale request id=%lu\n",
                      client_num,
                      static_cast<unsigned long>(request.id));
        if (request.kind == K1_REQUEST_CONTROL_SET) {
          (void)queue_control_error(client_num,
                                    request.id,
                                    request.record.control,
                                    "replay",
                                    protocol_error_message("replay"),
                                    request.protocol_version);
        } else {
          (void)queue_error(client_num,
                            request.id,
                            "replay",
                            protocol_error_message("replay"),
                            request.protocol_version);
        }
        return;
      }
      if (request.kind == K1_REQUEST_HELLO) {
        Serial.printf("[K1WS] client %u hello id=%lu\n",
                      client_num,
                      static_cast<unsigned long>(request.id));
        if (queue_hello(client_num, request.id, request.protocol_version)) {
          commit_client_request_id(client_num, request.id);
        }
        return;
      }
      request.client_num = client_num;
      if (request.kind == K1_REQUEST_STATE_GET) {
        Serial.printf("[K1WS] client %u state.get id=%lu\n",
                      client_num,
                      static_cast<unsigned long>(request.id));
      } else if (request.kind == K1_REQUEST_CAPABILITIES_GET) {
        Serial.printf("[K1WS] client %u capabilities.get id=%lu\n",
                      client_num,
                      static_cast<unsigned long>(request.id));
      } else if (request.kind == K1_REQUEST_CONTROL_SET) {
        Serial.printf("[K1WS] client %u control.set id=%lu control=%s\n",
                      client_num,
                      static_cast<unsigned long>(request.id),
                      request.record.control);
      }
      if (enqueue_request(request)) {
        commit_client_request_id(client_num, request.id);
      } else {
        if (request.kind == K1_REQUEST_CONTROL_SET) {
          (void)queue_control_error(client_num,
                                    request.id,
                                    request.record.control,
                                    "busy",
                                    protocol_error_message("busy"),
                                    request.protocol_version);
        } else {
          (void)queue_error(client_num,
                            request.id,
                            "busy",
                            protocol_error_message("busy"),
                            request.protocol_version);
        }
      }
      break;
    }
    default:
      break;
  }
}

void drain_outbound_frames() {
  QueuedWirelessFrame frame = {};
  uint8_t sent = 0;
  while (sent < MAX_FRAMES_PER_WS_TICK && dequeue_frame(&frame)) {
    if (!g_ws.sendTXT(frame.client_num, frame.payload)) {
      Serial.printf("[K1WS] client %u send failed\n", frame.client_num);
    }
    ++sent;
    delay(0);
  }
}

void k1_ws_task(void*) {
  for (;;) {
    if (g_ap_started) {
      g_ws.loop();
      drain_outbound_frames();
    }
    vTaskDelay(pdMS_TO_TICKS(WS_TASK_DELAY_MS));
  }
}

void yield_ap_idle_if_client_connected(uint32_t now_ms) {
  if (WiFi.softAPgetStationNum() == 0) {
    return;
  }
  if ((uint32_t)(now_ms - g_last_ap_idle_yield_ms) < AP_IDLE_YIELD_INTERVAL_MS) {
    return;
  }

  g_last_ap_idle_yield_ms = now_ms;
  vTaskDelay(1);
}

void print_ip_address(const IPAddress& ip) {
  Serial.printf("%u.%u.%u.%u", ip[0], ip[1], ip[2], ip[3]);
}

}  // namespace

void k1_wireless_begin() {
  if (g_ap_started) {
    return;
  }

  WiFi.persistent(false);
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(K1_AP_IP, K1_AP_GATEWAY, K1_AP_SUBNET);
  g_ap_started = WiFi.softAP(K1_AP_SSID, K1_AP_PASSWORD);
  if (g_ap_started) {
    g_ws.begin();
    g_ws.onEvent(handle_ws_event);
    if (g_ws_task_handle == nullptr) {
      BaseType_t task_result = xTaskCreatePinnedToCore(
        k1_ws_task,
        "k1_ws",
        6144,
        nullptr,
        WS_TASK_PRIORITY,
        &g_ws_task_handle,
        K1_WIRELESS_TASK_CORE);
      if (task_result != pdPASS) {
        g_ws_task_handle = nullptr;
        Serial.println("[K1WS] task start failed");
      }
    }
    Serial.print("[K1WS] AP ");
    Serial.print(K1_AP_SSID);
    Serial.print(" up at ");
    print_ip_address(WiFi.softAPIP());
    Serial.print(", ws://");
    print_ip_address(WiFi.softAPIP());
    Serial.println("/ws");
  } else {
    Serial.println("[K1WS] AP start failed");
  }
}

void k1_wireless_poll(uint32_t now_ms) {
  if (!g_ap_started) {
    return;
  }

  K1WirelessRequest request = {};
  uint8_t applied = 0;
  while (applied < MAX_REQUESTS_PER_AP_TICK && request_queue_has_pending()) {
    if (!reserve_frame_capacity()) {
      break;
    }
    if (!dequeue_request(&request)) {
      release_frame_reservation();
      break;
    }
    bool queued = false;
    if (request.kind == K1_REQUEST_CONTROL_SET) {
      K1WirelessControlResult result = k1_wireless_control_apply(request.record);
      queued = queue_control_result(request.client_num,
                                    request.record,
                                    result,
                                    request.protocol_version,
                                    true);
    } else if (request.kind == K1_REQUEST_STATE_GET) {
      queued = queue_state(request.client_num, request.id, request.protocol_version, true);
    } else if (request.kind == K1_REQUEST_CAPABILITIES_GET) {
      queued = queue_capabilities(request.client_num, request.id, request.protocol_version, true);
    } else {
      release_frame_reservation();
    }
    if (!queued) {
      Serial.printf("[K1WS] response queue full after request id=%lu kind=%u\n",
                    static_cast<unsigned long>(request.id),
                    unsigned(request.kind));
    }
    ++applied;
  }

  yield_ap_idle_if_client_connected(now_ms);
}

bool k1_wireless_is_ap_started() {
  return g_ap_started;
}

uint8_t k1_wireless_client_count() {
  if (!g_ap_started) {
    return 0;
  }
  return WiFi.softAPgetStationNum();
}

#endif  // K1_WIRELESS_ENABLED
