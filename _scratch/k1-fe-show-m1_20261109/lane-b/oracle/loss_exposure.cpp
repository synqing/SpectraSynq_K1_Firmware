/* Lane B exhaustive USB-packet-loss exposure.
 * Model (HWCDC RX ISR drops the rest of a packet when rx_queue is full): the host writes one
 * packet per frame = [guard x 0x00][34-byte PRSM frame]. A loss event (k, i) keeps only the first
 * i bytes of packet k (i = 0 .. packet_len-1); packets k+1.. arrive intact. Bytes are fed through
 * the REAL firmware scanner/mapper (k1_prsm.cpp, k1_authored_source.cpp) inside a replica of the
 * check_serial() demux (serial_menu.cpp check_serial, 407fdf6f == ed0aa984) until resync: a packet
 * boundary with scanner fill 0 and command mode off, or 64 packets.
 *
 * usage: loss_exposure STREAM.prsm GUARD_BYTES  > events.jsonl
 * Prints one JSON line per event that is not clean (any byte not consumed by the scanner except
 * guard NULs, any ':' entry, any garbage frame accepted), then a final {"summary":...} line. */

#include "k1_prsm.h"
#include "k1_authored_source.h"

#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static std::string hexs(const std::vector<uint8_t> &v) {
  static const char *H = "0123456789abcdef";
  std::string s;
  for (uint8_t b : v) { s += H[b >> 4]; s += H[b & 15]; }
  return s;
}

int main(int argc, char **argv) {
  if (argc != 3) { std::fprintf(stderr, "usage: loss_exposure STREAM GUARD\n"); return 3; }
  FILE *fp = std::fopen(argv[1], "rb");
  if (!fp) { std::perror("open"); return 3; }
  std::vector<uint8_t> s;
  int c;
  while ((c = std::fgetc(fp)) != EOF) s.push_back(uint8_t(c));
  std::fclose(fp);
  const int guard = std::atoi(argv[2]);
  const size_t nfr = s.size() / K1_PRSM_PACKET_LEN;
  const int plen = guard + K1_PRSM_PACKET_LEN;
  std::vector<uint8_t> pk((size_t)plen);
  auto packet = [&](size_t k, std::vector<uint8_t> &out) {
    for (int j = 0; j < guard; j++) out[j] = 0;
    std::memcpy(&out[guard], &s[k * K1_PRSM_PACKET_LEN], K1_PRSM_PACKET_LEN);
  };
  k1_prsm_frame_t f0;
  k1_prsm_parse(&s[0], K1_PRSM_PACKET_LEN, &f0);
  const uint32_t seq0 = f0.seq;

  /* STEP mode (argv: STREAM GUARD step): induction step for arbitrary loss sequences. For every
   * scanner start fill f (0..33, stale = real frame prefix or 0xFF filler after magic), every
   * 10th packet q and every kept prefix length L (0..packet_len), command mode off at the start:
   * count bytes that are not consumed by the scanner (guard NULs excepted) and ':' entries. */
  if (getenv("LOSS_STEP")) {
    unsigned long runs = 0, bad = 0;
    for (int variant = 0; variant < 2; variant++)
      for (int f = 0; f < K1_PRSM_PACKET_LEN; f++)
        for (size_t q = 1; q < nfr; q += 10)
          for (int L = 0; L <= plen; L++) {
            runs++;
            k1_prsm_scanner_t sc;
            k1_prsm_scanner_reset(&sc);
            for (int j = 0; j < f; j++)
              sc.buf[j] = (j < 4) ? uint8_t("PRSM"[j])
                                  : (variant ? 0xFF : s[(q - 1) * K1_PRSM_PACKET_LEN + j]);
            sc.fill = uint8_t(f);
            packet(q, pk);
            int leaks = 0;
            for (int j = 0; j < L; j++) {
              k1_prsm_frame_t fr = {};
              if (k1_prsm_scanner_push(&sc, pk[j], &fr) != K1_PRSM_SCAN_NONE) continue;
              if (pk[j] == 0x00 && j < guard) continue;
              leaks++;
            }
            if (leaks) {
              if (bad < 5) std::printf("{\"step_fail\":{\"f\":%d,\"q\":%zu,\"L\":%d,\"leaks\":%d}}\n", f, q, L, leaks);
              bad++;
            }
          }
    std::printf("{\"step_summary\":{\"guard\":%d,\"runs\":%lu,\"runs_with_leaks\":%lu}}\n", guard, runs, bad);
    return 0;
  }

  unsigned long events = 0, dirty = 0, unresolved = 0;
  for (size_t k = 0; k + 1 < nfr; k++) {
    for (int i = 0; i < plen; i++) {
      events++;
      k1_prsm_scanner_t sc;
      k1_prsm_scanner_reset(&sc);
      bool cmd_mode = false;
      std::vector<uint8_t> cmd;
      std::string leaks;      /* [byte, packet_offset_from_loss] */
      std::string cmds;
      int enters = 0, garbage = 0, intact = 0;
      bool resynced = false;
      size_t pkts = 0;
      for (size_t q = k; q < nfr && pkts < 64; q++, pkts++) {
        packet(q, pk);
        const int n = (q == k) ? i : plen;
        for (int j = 0; j < n; j++) {
          const uint8_t b = pk[j];
          if (!cmd_mode) {
            k1_prsm_frame_t f = {};
            const k1_prsm_scan_result_t r = k1_prsm_scanner_push(&sc, b, &f);
            if (r != K1_PRSM_SCAN_NONE) {
              if (r == K1_PRSM_SCAN_FRAME_OK) {
                k1_authored_intent_t tmp;
                if (k1_authored_map_prim8(&f, 0, &tmp)) {
                  const uint32_t idx = f.seq - seq0;
                  k1_prsm_frame_t ref = {};
                  const bool known = idx < nfr &&
                      k1_prsm_parse(&s[idx * K1_PRSM_PACKET_LEN], K1_PRSM_PACKET_LEN, &ref) &&
                      ref.t_us == f.t_us && ref.hz == f.hz &&
                      std::memcmp(ref.prim8_u16, f.prim8_u16, sizeof f.prim8_u16) == 0;
                  if (known) intact++; else garbage++;
                }
              }
              continue;
            }
            if (b == ':') { cmd_mode = true; cmd.clear(); enters++; continue; }
            if (b == 0x00 && j < guard) continue;           /* guard NUL: inert by design */
            leaks += (leaks.empty() ? "" : ",") + std::string("[") + std::to_string(b) + "," +
                     std::to_string(pkts) + "]";
            continue;
          }
          if (b == '\r' || b == '\n') {
            if (!cmd.empty()) cmds += (cmds.empty() ? "\"" : ",\"") + hexs(cmd) + "\"";
            cmd.clear();
            cmd_mode = false;
          } else {
            cmd.push_back(b);
            if (cmd.size() >= 127) {
              cmds += (cmds.empty() ? "\"" : ",\"") + hexs(cmd) + "\"";
              cmd.clear();
              cmd_mode = false;
            }
          }
        }
        if (q > k && sc.fill == 0 && !cmd_mode) { resynced = true; pkts++; break; }
      }
      if (!resynced) unresolved++;
      if (!leaks.empty() || enters || garbage || !resynced) {
        dirty++;
        std::printf("{\"k\":%zu,\"i\":%d,\"leaks\":[%s],\"enters\":%d,\"cmds\":[%s],\"garbage\":%d,"
                    "\"intact\":%d,\"packets\":%zu,\"resynced\":%d,\"pending\":\"%s\"}\n",
                    k, i, leaks.c_str(), enters, cmds.c_str(), garbage, intact, pkts,
                    resynced ? 1 : 0, cmd_mode ? hexs(cmd).c_str() : "");
      }
    }
  }
  std::printf("{\"summary\":{\"frames\":%zu,\"guard\":%d,\"packet_len\":%d,\"events\":%lu,"
              "\"dirty_events\":%lu,\"unresolved_within_64_packets\":%lu}}\n",
              nfr, guard, plen, events, dirty, unresolved);
  return 0;
}
