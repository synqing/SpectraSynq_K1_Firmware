#pragma once

#include <stdint.h>
#include <stddef.h>
#include <string.h>

// Gate-4 transactional command channels (Candidate A primitives).

#ifndef K1_CMD_STATE_PAYLOAD_BYTES
#define K1_CMD_STATE_PAYLOAD_BYTES 64
#endif
#ifndef K1_CMD_EDGE_CAPACITY
#define K1_CMD_EDGE_CAPACITY 8
#endif

struct K1CmdStatePayload {
  uint8_t bytes[K1_CMD_STATE_PAYLOAD_BYTES];
};

struct K1CmdScene {
  uint8_t primary_mode;
  uint8_t secondary_mode;
  uint16_t crossfade_ms;
  uint32_t generation;
};

struct K1CmdEdge {
  uint32_t sequence;
  uint16_t opcode;
  uint16_t arg;
};

struct K1CmdChannelStats {
  uint32_t state_overwrite_count;
  uint32_t scene_generation;
  uint32_t edge_queue_depth_max;
  uint32_t edge_reject_count;
  uint32_t edge_drop_count;
  uint32_t edge_consume_count;
};

void k1_cmd_channels_reset(void);
void k1_cmd_channels_stats(K1CmdChannelStats* out);

// Complete desired state: depth-one latest-wins mailbox. Generation last.
void k1_cmd_state_publish(const K1CmdStatePayload& payload, uint32_t generation);
bool k1_cmd_state_acquire(K1CmdStatePayload* out, uint32_t* generation_out);

// Two-channel scene: both channels apply on the same VP frame or neither.
void k1_cmd_scene_publish(const K1CmdScene& scene);
bool k1_cmd_scene_acquire(K1CmdScene* out);

// Non-idempotent edge queue: at-most-once consume, visible full policy.
bool k1_cmd_edge_push(const K1CmdEdge& edge);   // false => rejected (full or regressed)
bool k1_cmd_edge_pop(K1CmdEdge* out);           // false => empty
