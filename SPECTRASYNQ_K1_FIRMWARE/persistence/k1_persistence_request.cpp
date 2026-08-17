#include "k1_persistence_request.h"

#include <string.h>

static K1PersistRequest s_q[K1_PERSIST_QUEUE_CAPACITY];
static uint32_t s_head = 0;
static uint32_t s_tail = 0;
static uint32_t s_count = 0;
static K1PersistResult s_result;
static bool s_result_valid = false;
static K1PersistStats s_stats = {};

void k1_persist_reset(void) {
  s_head = s_tail = s_count = 0;
  s_result_valid = false;
  memset(&s_stats, 0, sizeof(s_stats));
  memset(&s_result, 0, sizeof(s_result));
}

void k1_persist_stats(K1PersistStats* out) {
  if (out) *out = s_stats;
}

bool k1_persist_request_push(const K1PersistRequest& req) {
  if (req.idempotent) {
    for (uint32_t i = 0; i < s_count; i++) {
      uint32_t idx = (s_head + i) % K1_PERSIST_QUEUE_CAPACITY;
      if (s_q[idx].op == req.op && s_q[idx].idempotent) {
        s_q[idx] = req;  // coalesce
        s_stats.coalesced++;
        return true;
      }
    }
  }
  if (s_count >= K1_PERSIST_QUEUE_CAPACITY) {
    s_stats.rejected_full++;
    return false;
  }
  s_q[s_tail] = req;
  s_tail = (s_tail + 1) % K1_PERSIST_QUEUE_CAPACITY;
  s_count++;
  s_stats.queued++;
  return true;
}

bool k1_persist_request_pop(K1PersistRequest* out) {
  if (!out || s_count == 0) return false;
  *out = s_q[s_head];
  s_head = (s_head + 1) % K1_PERSIST_QUEUE_CAPACITY;
  s_count--;
  return true;
}

void k1_persist_result_publish(const K1PersistResult& result) {
  if (s_result_valid) {
    s_stats.lost_result++;
  }
  s_result = result;
  s_result_valid = true;
  s_stats.completed++;
}

bool k1_persist_result_acquire(K1PersistResult* out) {
  if (!out || !s_result_valid) return false;
  *out = s_result;
  s_result_valid = false;
  return true;
}

bool k1_persist_service_stub_once(void) {
  K1PersistRequest req;
  if (!k1_persist_request_pop(&req)) return false;
  K1PersistResult result = {};
  result.sequence = req.sequence;
  result.ok = 1;
  result.error_code = 0;
  k1_persist_result_publish(result);
  return true;
}
