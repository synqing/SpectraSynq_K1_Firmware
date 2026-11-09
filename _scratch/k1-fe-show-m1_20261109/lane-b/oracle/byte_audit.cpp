/* Lane B byte-routing audit engine.
 * Feeds a byte file through the REAL firmware scanner (k1_prsm.cpp) and authored mapper
 * (k1_authored_source.cpp) inside a replica of check_serial()'s demux
 * (serial_menu.cpp check_serial, lines 4123-4210 at 407fdf6f == ed0aa984, blob e99b8fb4).
 * The starting device state can be injected:
 *   --fill N --stale HEX   scanner holds N stale bytes (HEX = 2N hex chars)
 *   --cmd L                device is in ':' command mode with L pending bytes ('x')
 * Output: one JSON object (routing of every non-consumed byte, frames, commands executed). */

#include "k1_prsm.h"
#include "k1_authored_source.h"

#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static int hexval(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: byte_audit FILE [--fill N --stale HEX] [--cmd L]\n");
    return 3;
  }
  int fill = 0, cmd_pending = -1;
  std::vector<uint8_t> stale;
  for (int i = 2; i < argc; i++) {
    if (!std::strcmp(argv[i], "--fill") && i + 1 < argc) fill = std::atoi(argv[++i]);
    else if (!std::strcmp(argv[i], "--stale") && i + 1 < argc) {
      const char *h = argv[++i];
      for (size_t j = 0; h[j] && h[j + 1]; j += 2) stale.push_back(uint8_t(hexval(h[j]) * 16 + hexval(h[j + 1])));
    } else if (!std::strcmp(argv[i], "--cmd") && i + 1 < argc) cmd_pending = std::atoi(argv[++i]);
    else { std::fprintf(stderr, "bad arg %s\n", argv[i]); return 3; }
  }
  if (fill < 0 || fill >= K1_PRSM_PACKET_LEN || int(stale.size()) != fill) {
    std::fprintf(stderr, "fill must be 0..33 and --stale must carry exactly fill bytes\n");
    return 3;
  }
  FILE *fp = std::fopen(argv[1], "rb");
  if (!fp) { std::perror("open"); return 3; }
  std::vector<uint8_t> data;
  int c;
  while ((c = std::fgetc(fp)) != EOF) data.push_back(uint8_t(c));
  std::fclose(fp);

  k1_prsm_scanner_t sc;
  k1_prsm_scanner_reset(&sc);
  for (int j = 0; j < fill; j++) sc.buf[j] = stale[j];
  sc.fill = uint8_t(fill);
  bool command_mode = cmd_pending >= 0;
  std::string cmd(command_mode ? size_t(cmd_pending) : 0, 'x');

  std::printf("{\"bytes\":%zu,\"frames\":[", data.size());
  std::string none_s, enter_s, exec_s, bad_s, cmdbyte_s;
  bool ff = true;
  size_t cmd_bytes = 0;
  for (size_t i = 0; i < data.size(); i++) {
    const uint8_t b = data[i];
    if (!command_mode) {
      k1_prsm_frame_t f = {};
      const k1_prsm_scan_result_t r = k1_prsm_scanner_push(&sc, b, &f);
      if (r != K1_PRSM_SCAN_NONE) {
        if (r == K1_PRSM_SCAN_FRAME_OK) {
          k1_authored_intent_t tmp;
          const bool mapped = k1_authored_map_prim8(&f, 0, &tmp);
          std::printf("%s{\"off\":%zu,\"seq\":%" PRIu32 ",\"t_us\":%" PRIu64 ",\"hz\":%u,\"mapped\":%d,"
                      "\"p\":[%u,%u,%u,%u,%u,%u,%u,%u]}",
                      ff ? "" : ",", i, f.seq, f.t_us, unsigned(f.hz), mapped ? 1 : 0,
                      f.prim8_u16[0], f.prim8_u16[1], f.prim8_u16[2], f.prim8_u16[3],
                      f.prim8_u16[4], f.prim8_u16[5], f.prim8_u16[6], f.prim8_u16[7]);
          ff = false;
        } else if (r == K1_PRSM_SCAN_FRAME_BAD) {
          bad_s += (bad_s.empty() ? "" : ",") + std::to_string(i);
        }
        continue;
      }
      if (b == ':') {
        command_mode = true;
        cmd.clear();
        enter_s += (enter_s.empty() ? "" : ",") + std::to_string(i);
        continue;
      }
      /* CR/LF and every other byte: reported with its value; the Python side classifies
       * (CR/LF skipped by firmware; others go to serial_hotkey_is_immediate). */
      none_s += (none_s.empty() ? "" : ",") + std::string("[") + std::to_string(i) + "," +
                std::to_string(unsigned(b)) + "]";
      continue;
    }
    cmd_bytes++;
    cmdbyte_s += (cmdbyte_s.empty() ? "" : ",") + std::to_string(i);
    if (b == '\r' || b == '\n') {
      if (!cmd.empty()) {
        exec_s += (exec_s.empty() ? "" : ",") + std::string("{\"end_off\":") + std::to_string(i) +
                  ",\"len\":" + std::to_string(cmd.size()) + ",\"cstr_len\":" +
                  std::to_string(std::strlen(cmd.c_str())) + "}";
      }
      cmd.clear();
      command_mode = false;
    } else {
      cmd.push_back(char(b));
      if (cmd.size() >= 127) {
        exec_s += (exec_s.empty() ? "" : ",") + std::string("{\"end_off\":") + std::to_string(i) +
                  ",\"len\":127,\"cstr_len\":" + std::to_string(std::strlen(cmd.c_str())) + "}";
        cmd.clear();
        command_mode = false;
      }
    }
  }
  std::printf("],\"none\":[%s],\"frame_bad\":[%s],\"command_mode_enter\":[%s],"
              "\"command_mode_bytes\":[%s],\"commands_executed\":[%s],"
              "\"final\":{\"fill\":%u,\"command_mode\":%d,\"pending\":%zu}}\n",
              none_s.c_str(), bad_s.c_str(), enter_s.c_str(), cmdbyte_s.c_str(), exec_s.c_str(),
              unsigned(sc.fill), command_mode ? 1 : 0, cmd.size());
  (void)cmd_bytes;
  return 0;
}
