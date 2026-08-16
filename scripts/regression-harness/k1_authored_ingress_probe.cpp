/* Host probe for authored PRSM parse, magic-first scan, and source arbitration.
 * Compiles the real audio/k1_prsm.cpp + audio/k1_authored_source.cpp. */

#include "k1_prsm.h"
#include "k1_authored_source.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static void write_u32_le(uint8_t *p, uint32_t v) {
  p[0] = uint8_t(v);
  p[1] = uint8_t(v >> 8);
  p[2] = uint8_t(v >> 16);
  p[3] = uint8_t(v >> 24);
}

static void write_u64_le(uint8_t *p, uint64_t v) {
  write_u32_le(p, uint32_t(v));
  write_u32_le(p + 4, uint32_t(v >> 32));
}

static void write_u16_le(uint8_t *p, uint16_t v) {
  p[0] = uint8_t(v);
  p[1] = uint8_t(v >> 8);
}

static void make_prsm(uint8_t out[34], uint8_t hz, uint32_t seq, uint64_t t_us,
                      const uint16_t prim8[8]) {
  out[0] = 'P';
  out[1] = 'R';
  out[2] = 'S';
  out[3] = 'M';
  out[4] = 1;
  out[5] = hz;
  write_u32_le(out + 6, seq);
  write_u64_le(out + 10, t_us);
  for (int i = 0; i < 8; i++) write_u16_le(out + 18 + i * 2, prim8[i]);
}

static int fail(const char *msg) {
  std::fprintf(stderr, "FAIL %s\n", msg);
  return 1;
}

int main() {
  uint16_t prim8[8] = {32768, 1000, 20000, 4000, 0, 0, 8000, 0};
  uint8_t pkt[34];
  make_prsm(pkt, 120, 1, 1000, prim8);

  k1_prsm_frame_t parsed;
  if (!k1_prsm_parse(pkt, 34, &parsed)) return fail("parse_good");
  if (parsed.hz != 120 || parsed.seq != 1 || parsed.t_us != 1000) return fail("parse_fields");
  if (parsed.prim8_u16[0] != 32768 || parsed.prim8_u16[6] != 8000) return fail("parse_prim8");

  uint8_t bad[34];
  memcpy(bad, pkt, 34);
  bad[0] = 'X';
  if (k1_prsm_parse(bad, 34, &parsed)) return fail("parse_bad_magic");
  bad[0] = 'P';
  bad[4] = 2;
  if (k1_prsm_parse(bad, 34, &parsed)) return fail("parse_bad_version");

  k1_prsm_scanner_t sc;
  k1_prsm_scanner_reset(&sc);
  int frames = 0;
  int hotkey_leaks = 0;
  /* Prefix junk including P/R/S hotkeys, then a valid frame. */
  const uint8_t prefix[] = {'x', 'P', 'R', 'S', 'Q', 'P'};
  for (uint8_t b : prefix) {
    k1_prsm_frame_t f;
    k1_prsm_scan_result_t r = k1_prsm_scanner_push(&sc, b, &f);
    if (r == K1_PRSM_SCAN_NONE) hotkey_leaks++;
    if (r == K1_PRSM_SCAN_FRAME_OK) return fail("early_frame");
  }
  /* After lone P then R S Q, hunter should have reset; trailing P starts a frame. */
  for (int i = 1; i < 34; i++) {
    k1_prsm_frame_t f;
    k1_prsm_scan_result_t r = k1_prsm_scanner_push(&sc, pkt[i], &f);
    if (r == K1_PRSM_SCAN_NONE) return fail("scan_leak_inside_frame");
    if (r == K1_PRSM_SCAN_FRAME_OK) frames++;
  }
  if (frames != 1) return fail("scan_one_frame");
  if (hotkey_leaks < 1) return fail("junk_must_be_none");

  /* Intact PRSM must consume P/R/S — zero NONE results inside the packet. */
  k1_prsm_scanner_reset(&sc);
  int none_inside = 0;
  frames = 0;
  for (int i = 0; i < 34; i++) {
    k1_prsm_frame_t f;
    k1_prsm_scan_result_t r = k1_prsm_scanner_push(&sc, pkt[i], &f);
    if (r == K1_PRSM_SCAN_NONE) none_inside++;
    if (r == K1_PRSM_SCAN_FRAME_OK) frames++;
  }
  if (none_inside != 0) return fail("prsm_hotkey_collision");
  if (frames != 1) return fail("intact_frame");

  k1_authored_reset();
  if (k1_authored_state() != K1_SRC_STANDALONE) return fail("reset_standalone");
  if (k1_authored_suppresses_live_update()) return fail("reset_not_suppressed");

  k1_prsm_parse(pkt, 34, &parsed);
  k1_authored_on_frame(&parsed, 1000);
  if (!k1_authored_suppresses_live_update()) return fail("authored_suppress");
  if (k1_authored_state() != K1_SRC_AUTHORED) return fail("state_authored");

  k1_authored_intent_t intent;
  if (!k1_authored_intent(&intent)) return fail("intent_present");
  if (intent.spectral_energy < 0.49f || intent.spectral_energy > 0.51f) {
    return fail("pressure_map");
  }
  if (intent.low_energy <= 0.0f) return fail("mass_map");

  k1_authored_tick(1000 + 49);
  if (k1_authored_state() != K1_SRC_AUTHORED) return fail("fresh_49");
  k1_authored_tick(1000 + 51);
  if (k1_authored_state() != K1_SRC_RECOVERY) return fail("stale_51_recovery");
  k1_authored_tick(1000 + 52);
  if (k1_authored_state() != K1_SRC_STANDALONE) return fail("recovery_to_standalone");
  if (k1_authored_suppresses_live_update()) return fail("handback_live");

  /* Reject out-of-range hz — fail closed, do not map. */
  k1_authored_reset();
  make_prsm(pkt, 10, 1, 0, prim8);
  k1_prsm_parse(pkt, 34, &parsed);
  k1_authored_on_frame(&parsed, 50);
  if (k1_authored_state() != K1_SRC_STANDALONE) return fail("hz_reject");

  std::printf("PASS authored_ingress\n");
  std::printf("freshness_ms %u\n", K1_AUTHORED_FRESHNESS_MS);
  return 0;
}
