#include "diagnostic_capture.h"

#include <Arduino.h>
#include <string.h>
#include "esp_heap_caps.h"
#include "globals.h"

#if ENABLE_DIAG_CAPTURE
// Storage is PSRAM-backed so DIAG_CAPTURE_MAX_RECORDS can be raised (via a build flag on a
// NON-SHIPPING probe env) to a continuous multi-beat capture window without blowing internal
// SRAM. Allocated lazily on first start; a failed alloc fails SAFE (start returns false, no
// crash) per the buffered-capture playbook (firmware-telemetry-instrumentation §1).
static DiagRecordSlot* diag_slots = nullptr;
static bool diag_capture_ensure_alloc() {
  if (diag_slots != nullptr) return true;
  diag_slots = (DiagRecordSlot*)heap_caps_malloc(
      (size_t)DIAG_CAPTURE_MAX_RECORDS * sizeof(DiagRecordSlot),
      MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  return diag_slots != nullptr;
}
static portMUX_TYPE diag_capture_mux = portMUX_INITIALIZER_UNLOCKED;
static DiagCaptureStatus diag_status_state = {
  DIAG_CAPTURE_STOPPED,
  0,
  0,
  DIAG_CAPTURE_MAX_RECORDS,
  0,
  0,
  0,
  0,
  false,
};
#endif

const char* diag_capture_state_name(DiagCaptureState state) {
  switch (state) {
    case DIAG_CAPTURE_STOPPED: return "stopped";
    case DIAG_CAPTURE_CAPTURING: return "capturing";
    case DIAG_CAPTURE_FROZEN: return "frozen";
    case DIAG_CAPTURE_DRAINING: return "draining";
    default: return "unknown";
  }
}

const char* diag_kind_name(uint8_t kind) {
  switch (kind) {
    case DIAG_KIND_NONE: return "none";
    case DIAG_KIND_VPAB_METRICS: return "vpab_metrics";
    case DIAG_KIND_VPAB_BYTES: return "vpab_bytes";
    case DIAG_KIND_MARKER: return "marker";
    case DIAG_KIND_K1_PIN_EVIDENCE: return "k1_pin_evidence";
    case DIAG_KIND_RESERVED_AP: return "reserved_ap";
    case DIAG_KIND_RESERVED_PERF: return "reserved_perf";
    default: return "unknown";
  }
}

#if ENABLE_DIAG_CAPTURE
void diag_capture_reset() {
  portENTER_CRITICAL(&diag_capture_mux);
  diag_status_state.state = DIAG_CAPTURE_STOPPED;
  diag_status_state.seq = 0;
  diag_status_state.count = 0;
  diag_status_state.high_water = 0;
  diag_status_state.captured = 0;
  diag_status_state.dropped = 0;
  diag_status_state.corrupt = 0;
  diag_status_state.overflowed = false;
  portEXIT_CRITICAL(&diag_capture_mux);
}

bool diag_capture_start() {
  if (!diag_capture_ensure_alloc()) {
    return false;   // PSRAM buffer unavailable -> fail safe, do not capture
  }
  portENTER_CRITICAL(&diag_capture_mux);
  if (diag_status_state.state == DIAG_CAPTURE_DRAINING) {
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }
  diag_status_state.state = DIAG_CAPTURE_CAPTURING;
  portEXIT_CRITICAL(&diag_capture_mux);
  return true;
}

bool diag_capture_stop() {
  portENTER_CRITICAL(&diag_capture_mux);
  if (diag_status_state.state == DIAG_CAPTURE_DRAINING) {
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }
  diag_status_state.state = DIAG_CAPTURE_FROZEN;
  portEXIT_CRITICAL(&diag_capture_mux);
  return true;
}

bool diag_capture_begin_drain() {
  portENTER_CRITICAL(&diag_capture_mux);
  if (diag_status_state.state != DIAG_CAPTURE_FROZEN &&
      diag_status_state.state != DIAG_CAPTURE_STOPPED) {
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }
  diag_status_state.state = DIAG_CAPTURE_DRAINING;
  portEXIT_CRITICAL(&diag_capture_mux);
  return true;
}

void diag_capture_end_drain() {
  portENTER_CRITICAL(&diag_capture_mux);
  if (diag_status_state.state == DIAG_CAPTURE_DRAINING) {
    diag_status_state.state = DIAG_CAPTURE_FROZEN;
  }
  portEXIT_CRITICAL(&diag_capture_mux);
}

bool diag_capture_is_capturing() {
  portENTER_CRITICAL(&diag_capture_mux);
  bool capturing = diag_status_state.state == DIAG_CAPTURE_CAPTURING;
  portEXIT_CRITICAL(&diag_capture_mux);
  return capturing;
}

DiagCaptureStatus diag_capture_status() {
  portENTER_CRITICAL(&diag_capture_mux);
  DiagCaptureStatus snapshot = diag_status_state;
  portEXIT_CRITICAL(&diag_capture_mux);
  return snapshot;
}

bool diag_capture_can_push(uint16_t payload_bytes) {
  portENTER_CRITICAL(&diag_capture_mux);
  if (diag_status_state.state != DIAG_CAPTURE_CAPTURING) {
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }
  if (payload_bytes > DIAG_CAPTURE_MAX_PAYLOAD_BYTES ||
      diag_status_state.count >= DIAG_CAPTURE_MAX_RECORDS) {
    diag_status_state.dropped++;
    diag_status_state.overflowed = true;
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }
  portEXIT_CRITICAL(&diag_capture_mux);
  return true;
}

bool diag_capture_try_push(uint8_t kind, uint16_t flags, uint32_t frame, uint32_t t_us,
                           const void* payload, uint16_t payload_bytes) {
  if (diag_slots == nullptr) return false;
  portENTER_CRITICAL(&diag_capture_mux);
  if (diag_status_state.state != DIAG_CAPTURE_CAPTURING) {
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }
  if (payload_bytes > DIAG_CAPTURE_MAX_PAYLOAD_BYTES ||
      (payload_bytes > 0 && payload == nullptr)) {
    diag_status_state.dropped++;
    diag_status_state.overflowed = true;
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }
  if (diag_status_state.count >= DIAG_CAPTURE_MAX_RECORDS) {
    diag_status_state.dropped++;
    diag_status_state.overflowed = true;
    portEXIT_CRITICAL(&diag_capture_mux);
    return false;
  }

  DiagRecordSlot& slot = diag_slots[diag_status_state.count];
  slot.header.magic = DIAG_CAPTURE_MAGIC;
  slot.header.version = DIAG_CAPTURE_VERSION;
  slot.header.kind = kind;
  slot.header.payload_bytes = payload_bytes;
  slot.header.flags = flags;
  slot.header.seq = ++diag_status_state.seq;
  slot.header.frame = frame;
  slot.header.t_us = t_us;
  if (payload_bytes > 0) {
    memcpy(slot.payload, payload, payload_bytes);
  }

  diag_status_state.count++;
  diag_status_state.captured++;
  if (diag_status_state.count > diag_status_state.high_water) {
    diag_status_state.high_water = diag_status_state.count;
  }
  portEXIT_CRITICAL(&diag_capture_mux);
  return true;
}

uint16_t diag_capture_count() {
  portENTER_CRITICAL(&diag_capture_mux);
  uint16_t count = diag_status_state.count;
  portEXIT_CRITICAL(&diag_capture_mux);
  return count;
}

const DiagRecordSlot* diag_capture_record_at(uint16_t index) {
  if (diag_slots == nullptr) return nullptr;
  portENTER_CRITICAL(&diag_capture_mux);
  if (index >= diag_status_state.count) {
    portEXIT_CRITICAL(&diag_capture_mux);
    return nullptr;
  }
  const DiagRecordSlot* slot = &diag_slots[index];
  if (slot->header.magic != DIAG_CAPTURE_MAGIC ||
      slot->header.version != DIAG_CAPTURE_VERSION ||
      slot->header.payload_bytes > DIAG_CAPTURE_MAX_PAYLOAD_BYTES) {
    diag_status_state.corrupt++;
    portEXIT_CRITICAL(&diag_capture_mux);
    return nullptr;
  }
  portEXIT_CRITICAL(&diag_capture_mux);
  return slot;
}
#else
void diag_capture_reset() {}
bool diag_capture_start() { return false; }
bool diag_capture_stop() { return false; }
bool diag_capture_begin_drain() { return false; }
void diag_capture_end_drain() {}
bool diag_capture_is_capturing() { return false; }
DiagCaptureStatus diag_capture_status() {
  return { DIAG_CAPTURE_STOPPED, 0, 0, 0, 0, 0, 0, 0, false };
}
bool diag_capture_can_push(uint16_t) { return false; }
bool diag_capture_try_push(uint8_t, uint16_t, uint32_t, uint32_t, const void*, uint16_t) {
  return false;
}
uint16_t diag_capture_count() { return 0; }
const DiagRecordSlot* diag_capture_record_at(uint16_t) { return nullptr; }
#endif

void diag_capture_print_status() {
  DiagCaptureStatus st = diag_capture_status();
  USBSerial.println("sbr{{");
  USBSerial.print("DIAG: ");
  USBSerial.println(diag_capture_state_name(st.state));
  USBSerial.print("DIAG_RECORDS: count=");
  USBSerial.print(st.count);
  USBSerial.print(" capacity=");
  USBSerial.print(st.capacity);
  USBSerial.print(" high_water=");
  USBSerial.println(st.high_water);
  USBSerial.print("DIAG_COUNTERS: captured=");
  USBSerial.print(st.captured);
  USBSerial.print(" dropped=");
  USBSerial.print(st.dropped);
  USBSerial.print(" corrupt=");
  USBSerial.print(st.corrupt);
  USBSerial.print(" overflowed=");
  USBSerial.println(st.overflowed ? 1 : 0);
  USBSerial.print("DIAG_BYTES: payload_max=");
  USBSerial.print(DIAG_CAPTURE_MAX_PAYLOAD_BYTES);
  USBSerial.print(" storage=");
  USBSerial.println(uint32_t(sizeof(DiagRecordSlot)) * uint32_t(DIAG_CAPTURE_MAX_RECORDS));
  USBSerial.print("CAL_SOURCE: ");
  USBSerial.println(calibration_source_name());
  USBSerial.print("CAL_VALID: ");
  USBSerial.println(calibration_valid ? 1 : 0);
  USBSerial.print("CAL_PROFILE_LOADED: ");
  USBSerial.println(calibration_profile_loaded ? 1 : 0);
  USBSerial.println("}}");
}
