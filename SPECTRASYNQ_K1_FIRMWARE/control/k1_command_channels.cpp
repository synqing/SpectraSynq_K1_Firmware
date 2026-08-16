#include "k1_command_channels.h"

#if defined(ARDUINO) && !defined(K1_CMD_HOST_TEST)
#include <Arduino.h>
static portMUX_TYPE k1_cmd_mux = portMUX_INITIALIZER_UNLOCKED;
#define K1_CMD_ENTER() portENTER_CRITICAL(&k1_cmd_mux)
#define K1_CMD_EXIT() portEXIT_CRITICAL(&k1_cmd_mux)
#else
#define K1_CMD_ENTER()                                                         \
  do {                                                                         \
  } while (0)
#define K1_CMD_EXIT()                                                          \
  do {                                                                         \
  } while (0)
#endif

static K1CmdStatePayload s_state;
static uint32_t s_state_generation = 0;
static bool s_state_valid = false;

static K1CmdScene s_scene;
static bool s_scene_valid = false;

static K1CmdEdge s_edges[K1_CMD_EDGE_CAPACITY];
static uint32_t s_edge_head = 0;
static uint32_t s_edge_tail = 0;
static uint32_t s_edge_count = 0;
static uint32_t s_edge_last_seq = 0;
static bool s_edge_have_seq = false;

static K1CmdChannelStats s_stats = {};

void k1_cmd_channels_reset(void) {
  K1_CMD_ENTER();
  memset(&s_state, 0, sizeof(s_state));
  s_state_generation = 0;
  s_state_valid = false;
  memset(&s_scene, 0, sizeof(s_scene));
  s_scene_valid = false;
  s_edge_head = s_edge_tail = s_edge_count = 0;
  s_edge_last_seq = 0;
  s_edge_have_seq = false;
  memset(&s_stats, 0, sizeof(s_stats));
  K1_CMD_EXIT();
}

void k1_cmd_channels_stats(K1CmdChannelStats* out) {
  if (out == nullptr) return;
  K1_CMD_ENTER();
  *out = s_stats;
  K1_CMD_EXIT();
}

void k1_cmd_state_publish(const K1CmdStatePayload& payload, uint32_t generation) {
  K1_CMD_ENTER();
  if (s_state_valid) {
    s_stats.state_overwrite_count++;
  }
  s_state = payload;                 // payload first
  s_state_generation = generation;   // generation last
  s_state_valid = true;
  K1_CMD_EXIT();
}

bool k1_cmd_state_acquire(K1CmdStatePayload* out, uint32_t* generation_out) {
  if (out == nullptr) return false;
  K1_CMD_ENTER();
  if (!s_state_valid) {
    K1_CMD_EXIT();
    return false;
  }
  *out = s_state;
  if (generation_out) *generation_out = s_state_generation;
  K1_CMD_EXIT();
  return true;
}

void k1_cmd_scene_publish(const K1CmdScene& scene) {
  K1_CMD_ENTER();
  s_scene = scene;
  s_scene.generation = scene.generation;
  s_scene_valid = true;
  s_stats.scene_generation = scene.generation;
  K1_CMD_EXIT();
}

bool k1_cmd_scene_acquire(K1CmdScene* out) {
  if (out == nullptr) return false;
  K1_CMD_ENTER();
  if (!s_scene_valid) {
    K1_CMD_EXIT();
    return false;
  }
  *out = s_scene;
  K1_CMD_EXIT();
  return true;
}

bool k1_cmd_edge_push(const K1CmdEdge& edge) {
  K1_CMD_ENTER();
  if (s_edge_have_seq && edge.sequence == s_edge_last_seq) {
    // Duplicate: at-most-once — reject without enqueue.
    s_stats.edge_reject_count++;
    K1_CMD_EXIT();
    return false;
  }
  if (s_edge_have_seq && edge.sequence < s_edge_last_seq) {
    s_stats.edge_reject_count++;
    K1_CMD_EXIT();
    return false;
  }
  if (s_edge_count >= K1_CMD_EDGE_CAPACITY) {
    s_stats.edge_drop_count++;
    s_stats.edge_reject_count++;
    K1_CMD_EXIT();
    return false;
  }
  s_edges[s_edge_tail] = edge;
  s_edge_tail = (s_edge_tail + 1) % K1_CMD_EDGE_CAPACITY;
  s_edge_count++;
  if (s_edge_count > s_stats.edge_queue_depth_max) {
    s_stats.edge_queue_depth_max = s_edge_count;
  }
  s_edge_last_seq = edge.sequence;
  s_edge_have_seq = true;
  K1_CMD_EXIT();
  return true;
}

bool k1_cmd_edge_pop(K1CmdEdge* out) {
  if (out == nullptr) return false;
  K1_CMD_ENTER();
  if (s_edge_count == 0) {
    K1_CMD_EXIT();
    return false;
  }
  *out = s_edges[s_edge_head];
  s_edge_head = (s_edge_head + 1) % K1_CMD_EDGE_CAPACITY;
  s_edge_count--;
  s_stats.edge_consume_count++;
  K1_CMD_EXIT();
  return true;
}
