// Host driver for Gate-4 command channel primitives.

#include "k1_command_channels.h"

#include <stdio.h>
#include <string.h>

static int g_fail = 0;

static void fail(const char* name, const char* msg) {
  fprintf(stderr, "FAIL %s: %s\n", name, msg);
  g_fail = 1;
}

static int test_state_overwrite_complete_only() {
  const char* name = "state_overwrite_complete_only";
  k1_cmd_channels_reset();
  K1CmdStatePayload a = {}, b = {}, c = {}, got = {};
  memset(a.bytes, 0xA1, sizeof(a.bytes));
  memset(b.bytes, 0xB2, sizeof(b.bytes));
  memset(c.bytes, 0xC3, sizeof(c.bytes));
  k1_cmd_state_publish(a, 1);
  k1_cmd_state_publish(b, 2);
  k1_cmd_state_publish(c, 3);
  uint32_t gen = 0;
  if (!k1_cmd_state_acquire(&got, &gen) || gen != 3) {
    fail(name, "expected generation 3");
    return 1;
  }
  if (memcmp(got.bytes, c.bytes, sizeof(c.bytes)) != 0) {
    fail(name, "payload not complete C");
    return 1;
  }
  K1CmdChannelStats st;
  k1_cmd_channels_stats(&st);
  if (st.state_overwrite_count != 2) {
    fail(name, "overwrite count != 2");
    return 1;
  }
  printf("PASS %s\n", name);
  return 0;
}

static int test_scene_atomic() {
  const char* name = "scene_both_channels_same_generation";
  k1_cmd_channels_reset();
  K1CmdScene scene = {};
  scene.primary_mode = 3;
  scene.secondary_mode = 7;
  scene.crossfade_ms = 120;
  scene.generation = 9;
  k1_cmd_scene_publish(scene);
  K1CmdScene got = {};
  if (!k1_cmd_scene_acquire(&got)) {
    fail(name, "acquire failed");
    return 1;
  }
  if (got.primary_mode != 3 || got.secondary_mode != 7 || got.generation != 9) {
    fail(name, "scene fields split");
    return 1;
  }
  printf("PASS %s\n", name);
  return 0;
}

static int test_edge_at_most_once_and_full() {
  const char* name = "edge_at_most_once_and_full";
  k1_cmd_channels_reset();
  K1CmdEdge e = {};
  e.sequence = 1;
  e.opcode = 10;
  if (!k1_cmd_edge_push(e)) {
    fail(name, "first push failed");
    return 1;
  }
  if (k1_cmd_edge_push(e)) {
    fail(name, "duplicate accepted");
    return 1;
  }
  e.sequence = 0;
  if (k1_cmd_edge_push(e)) {
    fail(name, "regressed sequence accepted");
    return 1;
  }
  for (uint32_t i = 2; i <= K1_CMD_EDGE_CAPACITY + 2; i++) {
    e.sequence = i;
    (void)k1_cmd_edge_push(e);
  }
  K1CmdChannelStats st;
  k1_cmd_channels_stats(&st);
  if (st.edge_drop_count == 0 || st.edge_reject_count == 0) {
    fail(name, "full policy not visible");
    return 1;
  }
  K1CmdEdge got = {};
  if (!k1_cmd_edge_pop(&got) || got.sequence != 1) {
    fail(name, "pop order wrong");
    return 1;
  }
  if (k1_cmd_edge_pop(&got) && got.sequence == 1) {
    fail(name, "duplicate consume");
    return 1;
  }
  printf("PASS %s\n", name);
  return 0;
}

int main() {
  int rc = 0;
  rc |= test_state_overwrite_complete_only();
  rc |= test_scene_atomic();
  rc |= test_edge_at_most_once_and_full();
  if (rc == 0) printf("ALL_PASS\n");
  return rc || g_fail;
}
