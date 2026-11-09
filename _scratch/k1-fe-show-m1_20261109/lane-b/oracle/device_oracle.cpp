/* Lane B differential oracle: feeds a prepared PRSM stream file through the REAL firmware
 * units (k1_prsm.cpp + k1_authored_source.cpp, snapshot of 407fdf6f in fw_407fdf6f/).
 *
 * Output: one JSON object on stdout:
 *   chunks:  per 34-byte chunk -> parse (k1_prsm_parse) and map (k1_authored_map_prim8) verdicts
 *   scan:    byte-scanner events (every non-CONSUMED result) as the device's check_serial sees them
 *   authored: for every FRAME_OK from the scanner, k1_authored_on_frame() is called with a synthetic
 *             arrival time (8 ms steps) and the state after the call is recorded.
 * No Arduino, no renderer. Pattern: tests/test_authored_ingress_native.py. */

#include "k1_prsm.h"
#include "k1_authored_source.h"

#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <vector>

static const char *scan_name(k1_prsm_scan_result_t r) {
  switch (r) {
    case K1_PRSM_SCAN_NONE: return "NONE";
    case K1_PRSM_SCAN_CONSUMED: return "CONSUMED";
    case K1_PRSM_SCAN_FRAME_OK: return "FRAME_OK";
    case K1_PRSM_SCAN_FRAME_BAD: return "FRAME_BAD";
  }
  return "?";
}

static const char *state_name(k1_authored_state_t s) {
  switch (s) {
    case K1_SRC_STANDALONE: return "STANDALONE";
    case K1_SRC_AUTHORED_ACQUIRE: return "AUTHORED_ACQUIRE";
    case K1_SRC_AUTHORED: return "AUTHORED";
    case K1_SRC_AUTHORED_DRAIN: return "AUTHORED_DRAIN";
    case K1_SRC_RECOVERY: return "RECOVERY";
  }
  return "?";
}

int main(int argc, char **argv) {
  if (argc != 2) {
    std::fprintf(stderr, "usage: device_oracle STREAM.prsm\n");
    return 3;
  }
  FILE *fp = std::fopen(argv[1], "rb");
  if (!fp) {
    std::perror("open");
    return 3;
  }
  std::vector<uint8_t> data;
  int c;
  while ((c = std::fgetc(fp)) != EOF) data.push_back(uint8_t(c));
  std::fclose(fp);

  std::printf("{\"bytes\":%zu,\"chunks\":[", data.size());
  const size_t n = data.size() / K1_PRSM_PACKET_LEN;
  for (size_t k = 0; k < n; k++) {
    k1_prsm_frame_t f = {};
    const bool parsed = k1_prsm_parse(&data[k * K1_PRSM_PACKET_LEN], K1_PRSM_PACKET_LEN, &f);
    k1_authored_intent_t intent;
    const bool mapped = parsed && k1_authored_map_prim8(&f, 0, &intent);
    std::printf("%s{\"k\":%zu,\"parse\":%d,\"map\":%d}", k ? "," : "", k, parsed ? 1 : 0,
                mapped ? 1 : 0);
  }
  std::printf("],\"scan\":[");

  k1_prsm_scanner_t sc;
  k1_prsm_scanner_reset(&sc);
  k1_authored_reset();
  bool first = true;
  std::vector<int> accepted_seq;
  uint32_t now_ms = 1000;
  for (size_t i = 0; i < data.size(); i++) {
    k1_prsm_frame_t f = {};
    const k1_prsm_scan_result_t r = k1_prsm_scanner_push(&sc, data[i], &f);
    if (r == K1_PRSM_SCAN_CONSUMED) continue;
    std::printf("%s{\"off\":%zu,\"r\":\"%s\",\"b\":%u", first ? "" : ",", i, scan_name(r),
                unsigned(data[i]));
    first = false;
    if (r == K1_PRSM_SCAN_FRAME_OK) {
      const k1_authored_state_t before = k1_authored_state();
      k1_authored_on_frame(&f, now_ms);
      const k1_authored_state_t after = k1_authored_state();
      /* A frame is "accepted" by the authored layer iff it was mapped; on reject the call
       * returns before touching state, so compare the latched seq/intent. */
      k1_authored_intent_t cur;
      const bool have = k1_authored_intent(&cur);
      const bool took = have && cur.seq == f.seq && cur.frame_ms == now_ms;
      std::printf(",\"hz\":%u,\"seq\":%" PRIu32 ",\"t_us\":%" PRIu64
                  ",\"authored_accept\":%d,\"state_before\":\"%s\",\"state_after\":\"%s\"",
                  unsigned(f.hz), f.seq, f.t_us, took ? 1 : 0, state_name(before),
                  state_name(after));
      now_ms += 8;
    }
    std::printf("}");
  }
  std::printf("],\"scanner_fill_at_eof\":%u", unsigned(sc.fill));

  /* Pass 3 — check_serial() byte demux, replicated control flow of serial_menu.cpp at 407fdf6f
   * (check_serial, lines 4123-4210): if !command_mode the REAL scanner runs first; a
   * non-NONE result consumes the byte; else ':' enters command mode, CR/LF is skipped,
   * immediate hotkeys dispatch. In command mode bytes go to command_buf until CR/LF or 127 bytes,
   * then parse_command(). The scanner object persists across command mode (static in
   * check_serial). Hotkey membership is NOT decided here; offsets/bytes are emitted. */
  {
    k1_prsm_scanner_t ds;
    k1_prsm_scanner_reset(&ds);
    bool command_mode = false;
    std::vector<uint8_t> cmd;
    std::printf(",\"demux\":{\"frames_ok\":[");
    bool f1 = true;
    std::vector<size_t> leak_off;
    std::vector<std::pair<size_t, std::vector<uint8_t>>> commands;
    std::vector<size_t> cmd_enter;
    for (size_t i = 0; i < data.size(); i++) {
      const uint8_t byte = data[i];
      if (!command_mode) {
        k1_prsm_frame_t f = {};
        const k1_prsm_scan_result_t r = k1_prsm_scanner_push(&ds, byte, &f);
        if (r != K1_PRSM_SCAN_NONE) {
          if (r == K1_PRSM_SCAN_FRAME_OK) {
            k1_authored_intent_t tmp;
            const bool mapped = k1_authored_map_prim8(&f, 0, &tmp);
            std::printf("%s{\"off\":%zu,\"seq\":%" PRIu32 ",\"t_us\":%" PRIu64 ",\"hz\":%u,"
                        "\"mapped\":%d,\"p\":[%u,%u,%u,%u,%u,%u,%u,%u]}",
                        f1 ? "" : ",", i, f.seq, f.t_us, unsigned(f.hz), mapped ? 1 : 0,
                        f.prim8_u16[0], f.prim8_u16[1], f.prim8_u16[2], f.prim8_u16[3],
                        f.prim8_u16[4], f.prim8_u16[5], f.prim8_u16[6], f.prim8_u16[7]);
            f1 = false;
          }
          continue;
        }
        if (byte == ':') {
          command_mode = true;
          cmd.clear();
          cmd_enter.push_back(i);
          continue;
        }
        if (byte == '\r' || byte == '\n') continue;
        leak_off.push_back(i); /* candidate immediate hotkey byte */
        continue;
      }
      if (byte == '\r' || byte == '\n') {
        if (!cmd.empty()) commands.push_back({i, cmd});
        cmd.clear();
        command_mode = false;
      } else {
        cmd.push_back(byte);
        if (cmd.size() >= 127) {
          commands.push_back({i, cmd});
          cmd.clear();
          command_mode = false;
        }
      }
    }
    std::printf("],\"leak_offsets\":[");
    for (size_t j = 0; j < leak_off.size(); j++)
      std::printf("%s%zu", j ? "," : "", leak_off[j]);
    std::printf("],\"command_mode_enter\":[");
    for (size_t j = 0; j < cmd_enter.size(); j++)
      std::printf("%s%zu", j ? "," : "", cmd_enter[j]);
    std::printf("],\"commands_parsed\":[");
    for (size_t j = 0; j < commands.size(); j++) {
      std::printf("%s{\"end_off\":%zu,\"len\":%zu}", j ? "," : "", commands[j].first,
                  commands[j].second.size());
    }
    std::printf("],\"command_mode_at_eof\":%d,\"pending_cmd_len\":%zu}", command_mode ? 1 : 0,
                cmd.size());
  }
  /* Freshness after stream end: tick at +50 and +51 ms after the last arrival. */
  const uint32_t last = now_ms - 8;
  k1_authored_tick(last + 50);
  const char *s50 = state_name(k1_authored_state());
  k1_authored_tick(last + 51);
  const char *s51 = state_name(k1_authored_state());
  k1_authored_tick(last + 52);
  const char *s52 = state_name(k1_authored_state());
  std::printf(",\"after_end\":{\"plus50\":\"%s\",\"plus51\":\"%s\",\"plus52\":\"%s\"}}\n", s50,
              s51, s52);
  return 0;
}
