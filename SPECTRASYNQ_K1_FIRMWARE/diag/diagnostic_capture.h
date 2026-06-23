#ifndef DIAGNOSTIC_CAPTURE_H
#define DIAGNOSTIC_CAPTURE_H

#include <stddef.h>
#include <stdint.h>
#include "constants.h"

enum DiagCaptureState : uint8_t {
  DIAG_CAPTURE_STOPPED = 0,
  DIAG_CAPTURE_CAPTURING = 1,
  DIAG_CAPTURE_FROZEN = 2,
  DIAG_CAPTURE_DRAINING = 3,
};

enum DiagRecordKind : uint8_t {
  DIAG_KIND_NONE = 0,
  DIAG_KIND_VPAB_METRICS = 1,
  DIAG_KIND_VPAB_BYTES = 2,
  DIAG_KIND_MARKER = 3,
  DIAG_KIND_K1_PIN_EVIDENCE = 4,
  DIAG_KIND_RESERVED_AP = 16,
  DIAG_KIND_RESERVED_PERF = 17,
};

struct DiagRecordHeader {
  uint16_t magic;
  uint8_t version;
  uint8_t kind;
  uint16_t payload_bytes;
  uint16_t flags;
  uint32_t seq;
  uint32_t frame;
  uint32_t t_us;
};

struct DiagRecordSlot {
  DiagRecordHeader header;
  uint8_t payload[DIAG_CAPTURE_MAX_PAYLOAD_BYTES];
};

struct DiagCaptureStatus {
  DiagCaptureState state;
  uint32_t seq;
  uint16_t count;
  uint16_t capacity;
  uint16_t high_water;
  uint32_t captured;
  uint32_t dropped;
  uint32_t corrupt;
  bool overflowed;
};

void diag_capture_reset();
bool diag_capture_start();
bool diag_capture_stop();
bool diag_capture_begin_drain();
void diag_capture_end_drain();
bool diag_capture_is_capturing();
DiagCaptureStatus diag_capture_status();
bool diag_capture_can_push(uint16_t payload_bytes);
bool diag_capture_try_push(uint8_t kind, uint16_t flags, uint32_t frame, uint32_t t_us,
                           const void* payload, uint16_t payload_bytes);
uint16_t diag_capture_count();
const DiagRecordSlot* diag_capture_record_at(uint16_t index);
const char* diag_capture_state_name(DiagCaptureState state);
const char* diag_kind_name(uint8_t kind);
void diag_capture_print_status();

#endif
