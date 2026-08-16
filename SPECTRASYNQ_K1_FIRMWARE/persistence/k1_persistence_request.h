#pragma once

#include <stdint.h>

// Gate-7A: persistence request boundary with no filesystem calls.

#ifndef K1_PERSIST_QUEUE_CAPACITY
#define K1_PERSIST_QUEUE_CAPACITY 4
#endif

enum K1PersistOp : uint8_t {
  K1_PERSIST_OP_SAVE_CONFIG = 1,
  K1_PERSIST_OP_SAVE_PRESET = 2,
  K1_PERSIST_OP_SAVE_NOISE_CAL = 3,
};

struct K1PersistRequest {
  uint32_t sequence;
  K1PersistOp op;
  uint8_t idempotent;
  uint16_t arg;
};

struct K1PersistResult {
  uint32_t sequence;
  uint8_t ok;
  uint8_t error_code;
};

struct K1PersistStats {
  uint32_t queued;
  uint32_t coalesced;
  uint32_t rejected_full;
  uint32_t completed;
  uint32_t lost_result;
};

void k1_persist_reset(void);
void k1_persist_stats(K1PersistStats* out);
bool k1_persist_request_push(const K1PersistRequest& req);
bool k1_persist_request_pop(K1PersistRequest* out);
void k1_persist_result_publish(const K1PersistResult& result);
bool k1_persist_result_acquire(K1PersistResult* out);
// Host/service stub: drains one request into a synthetic result. No filesystem.
bool k1_persist_service_stub_once(void);
