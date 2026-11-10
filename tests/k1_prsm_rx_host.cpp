/* Host test for the prepared-show serial receiver. Compiles the firmware's own
 * audio/k1_prsm.cpp, audio/k1_prsm_rx.cpp and audio/k1_authored_source.cpp: the
 * byte demultiplexer check_serial() calls is the code under test, not a copy.
 *
 * Usage: k1_prsm_rx_host [stream.prsm]
 * With a stream file (34-byte v1 frames) the packet-loss exposure runs on that
 * file as well as on the built-in synthetic stream. Prints one "name value"
 * line per measurement and "PASS k1_prsm_rx" at the end; exits 1 on the first
 * failed check. */

#include "k1_prsm.h"
#include "k1_prsm_rx.h"
#include "k1_authored_source.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

typedef std::vector<uint8_t> Bytes;

static void put_u16(uint8_t *p, uint16_t v) { p[0] = uint8_t(v); p[1] = uint8_t(v >> 8); }
static void put_u32(uint8_t *p, uint32_t v) { put_u16(p, uint16_t(v)); put_u16(p + 2, uint16_t(v >> 16)); }
static void put_u64(uint8_t *p, uint64_t v) { put_u32(p, uint32_t(v)); put_u32(p + 4, uint32_t(v >> 32)); }

static Bytes make_v1(uint8_t hz, uint32_t seq, uint64_t t_us, const uint16_t prim8[8]) {
  Bytes f(34);
  memcpy(f.data(), "PRSM", 4);
  f[4] = 1;
  f[5] = hz;
  put_u32(&f[6], seq);
  put_u64(&f[10], t_us);
  for (int i = 0; i < 8; i++) put_u16(&f[18 + 2 * i], prim8[i]);
  return f;
}

static Bytes make_v2(uint8_t hz, uint32_t seq, uint64_t t_us, const uint16_t prim8[8]) {
  Bytes f(39);
  memcpy(f.data(), "PRSM", 4);
  f[4] = 2;
  f[5] = 29;
  f[6] = hz;
  put_u32(&f[7], seq);
  put_u64(&f[11], t_us);
  for (int i = 0; i < 8; i++) put_u16(&f[19 + 2 * i], prim8[i]);
  put_u32(&f[35], k1_prsm_crc32(f.data(), 35));
  return f;
}

/* Deterministic stream whose bytes include every hotkey and ':' somewhere:
 * seq low byte sweeps 0..255, Prim8 values walk through printable pairs. */
static uint64_t tick_us(uint32_t i) { return (uint64_t(i) * 1000000u + 60u) / 120u; }
static std::vector<Bytes> synthetic_stream(uint32_t first_seq, uint32_t count, bool v2) {
  std::vector<Bytes> out;
  for (uint32_t k = 0; k < count; k++) {
    const uint32_t seq = first_seq + k;
    uint16_t p[8];
    for (int i = 0; i < 8; i++) {
      const uint8_t lo = uint8_t(0x20 + ((seq * 7u + uint32_t(i) * 13u) % 95u));
      const uint8_t hi = uint8_t(0x20 + ((seq * 11u + uint32_t(i) * 5u) % 95u));
      p[i] = uint16_t(lo | (hi << 8));
    }
    if (k % 5 == 0) p[0] = 20000; /* 0x20 0x4E: space, 'N' */
    if (k % 7 == 0) p[1] = 15000; /* 0x98 0x3A: ':' */
    out.push_back(v2 ? make_v2(120, seq, tick_us(seq), p) : make_v1(120, seq, tick_us(seq), p));
  }
  return out;
}

struct Tally {
  uint64_t frames = 0, hotkeys = 0, commands = 0, exits = 0, notices = 0, corrupt = 0;
  std::vector<uint32_t> seqs;
  std::string last_command;
  int first_hotkey = -1;
};

struct Truth {
  /* seq -> exact frame fields, for "is this applied frame one that was sent?" */
  std::vector<k1_prsm_frame_t> frames;
  uint32_t first_seq = 0;
  bool match(const k1_prsm_frame_t &f) const {
    const uint32_t idx = f.seq - first_seq;
    if (idx >= frames.size()) return false;
    const k1_prsm_frame_t &t = frames[idx];
    return t.hz == f.hz && t.seq == f.seq && t.t_us == f.t_us &&
           memcmp(t.prim8_u16, f.prim8_u16, sizeof(t.prim8_u16)) == 0;
  }
};

/* One call = one USB packet / host write: its bytes arrive together, then the
 * receive queue runs empty (check_serial() calls k1_prsm_rx_burst_end there). */
static void feed(k1_prsm_rx_t *rx, const uint8_t *data, size_t len, uint32_t now_ms,
                 Tally *t, const Truth *truth) {
  for (size_t i = 0; i <= len; i++) {
    k1_prsm_rx_event_t ev;
    if (i < len) k1_prsm_rx_push(rx, data[i], now_ms, &ev);
    else k1_prsm_rx_burst_end(rx, &ev);
    switch (ev.kind) {
      case K1_PRSM_RX_FRAME:
        t->frames++;
        t->seqs.push_back(ev.frame.seq);
        if (truth && !truth->match(ev.frame)) t->corrupt++;
        break;
      case K1_PRSM_RX_HOTKEY:
        if (t->first_hotkey < 0) t->first_hotkey = ev.byte;
        t->hotkeys++;
        break;
      case K1_PRSM_RX_COMMAND:
        t->commands++;
        t->last_command = ev.line;
        break;
      case K1_PRSM_RX_SESSION_EXIT: t->exits++; break;
      case K1_PRSM_RX_LOCKED_NOTICE: t->notices++; break;
      default: break;
    }
  }
}
static void feed(k1_prsm_rx_t *rx, const Bytes &b, uint32_t now_ms, Tally *t, const Truth *truth) {
  feed(rx, b.data(), b.size(), now_ms, t, truth);
}
static void feed(k1_prsm_rx_t *rx, const char *s, uint32_t now_ms, Tally *t) {
  feed(rx, reinterpret_cast<const uint8_t *>(s), strlen(s), now_ms, t, nullptr);
}

static int failures = 0;
static void check(bool ok, const char *what) {
  if (!ok) {
    std::fprintf(stderr, "FAIL %s\n", what);
    failures++;
  }
}

static Truth truth_of(const std::vector<Bytes> &frames) {
  Truth t;
  for (size_t i = 0; i < frames.size(); i++) {
    k1_prsm_frame_t f;
    const bool ok = frames[i][4] == 2 ? k1_prsm_parse_v2(frames[i].data(), 39, &f)
                                      : k1_prsm_parse(frames[i].data(), 34, &f);
    if (!ok) {
      std::fprintf(stderr, "FAIL truth frame %zu does not parse\n", i);
      failures++;
    }
    if (i == 0) t.first_seq = f.seq;
    t.frames.push_back(f);
  }
  return t;
}

/* USB packet loss, the Lane B model: one frame per packet, no host guard;
 * packet k keeps only its first i bytes, later packets arrive whole. Every
 * (k, i) is one event, fed to a fresh receiver from the start of the stream
 * (first frame, so "before the first accepted frame" is covered at k = 0). */
static void loss_exposure(const char *label, const std::vector<Bytes> &frames) {
  const Truth truth = truth_of(frames);
  const size_t flen = frames[0].size();
  const size_t tail = 70; /* packets replayed after the damaged one */
  uint64_t events = 0, hot = 0, cmd = 0, corrupt = 0, lost_extra = 0, max_lost = 0;
  for (size_t k = 0; k < frames.size(); k++) {
    for (size_t i = 0; i < flen; i++) {
      k1_prsm_rx_t rx;
      k1_prsm_rx_reset(&rx);
      Tally t;
      const size_t lead = k < 3 ? k : 3; /* a few whole frames first, when there are any */
      for (size_t j = k - lead; j < k; j++) feed(&rx, frames[j], 1000, &t, &truth);
      feed(&rx, frames[k].data(), i, 1000, &t, &truth);
      const size_t end = (k + 1 + tail < frames.size()) ? k + 1 + tail : frames.size();
      for (size_t j = k + 1; j < end; j++) feed(&rx, frames[j], 1000, &t, &truth);
      events++;
      hot += t.hotkeys;
      cmd += t.commands;
      corrupt += t.corrupt;
      const uint64_t sent = lead + (end - (k + 1));
      const uint64_t lost = sent - t.frames;
      if (lost > max_lost) max_lost = lost;
      lost_extra += lost;
    }
  }
  std::printf("%s_events %llu\n", label, (unsigned long long)events);
  std::printf("%s_hotkeys %llu\n", label, (unsigned long long)hot);
  std::printf("%s_commands %llu\n", label, (unsigned long long)cmd);
  std::printf("%s_corrupt_frames %llu\n", label, (unsigned long long)corrupt);
  std::printf("%s_whole_frames_lost_total %llu\n", label, (unsigned long long)lost_extra);
  std::printf("%s_whole_frames_lost_max_per_event %llu\n", label, (unsigned long long)max_lost);
  check(hot == 0, "loss exposure: a byte reached the hotkey path");
  check(cmd == 0, "loss exposure: a command line was executed");
  check(corrupt == 0, "loss exposure: a frame that was never sent was accepted");
  check(max_lost <= 2, "loss exposure: recovery took more than two frames");
}

static uint32_t xs = 0x9E3779B9u;
static uint8_t rnd8() {
  xs ^= xs << 13; xs ^= xs >> 17; xs ^= xs << 5;
  return uint8_t(xs >> 11);
}

int main(int argc, char **argv) {
  const uint16_t prim8[8] = {32768, 1000, 20000, 4000, 0, 0, 8000, 0};

  /* 1. Interactive text is unchanged. */
  {
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    feed(&rx, "h", 10, &t);
    check(t.hotkeys == 1 && t.first_hotkey == 'h', "interactive hotkey");
    feed(&rx, ":set_mode=3\r\n", 20, &t);
    check(t.commands == 1 && t.last_command == "set_mode=3", "interactive command line");
    feed(&rx, "\r\n;", 30, &t);
    check(t.hotkeys == 2 && t.commands == 1, "CR/LF ignored, next key is a hotkey");
    check(!rx.binary_session, "text never opens a binary session");
  }

  /* 2. A clean v1 stream: every frame, nothing else. */
  {
    const std::vector<Bytes> s = synthetic_stream(9000, 600, false);
    const Truth truth = truth_of(s);
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    for (const Bytes &f : s) feed(&rx, f, 100, &t, &truth);
    check(t.frames == 600 && t.corrupt == 0, "clean v1 stream delivers every frame");
    check(t.hotkeys == 0 && t.commands == 0, "clean v1 stream reaches nothing else");
    check(rx.binary_session, "first frame opens the binary session");
  }

  /* 2b. Frames whose last bytes look like the start of a header are whole
   *     frames and must arrive, back to back or alone. */
  {
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    uint16_t tail[8] = {1, 2, 3, 4, 5, 6, 0x5250 /* 'P','R' */, 0x4D53 /* 'S','M' */};
    Bytes two = make_v1(120, 1, tick_us(1), tail);
    tail[7] = 0x5000; /* ends in 'P' */
    const Bytes b = make_v1(120, 2, tick_us(2), tail);
    two.insert(two.end(), b.begin(), b.end());
    feed(&rx, two, 100, &t, nullptr);
    check(t.frames == 2 && t.seqs.size() == 2 && t.seqs[0] == 1 && t.seqs[1] == 2,
          "frames ending in header-like bytes arrive");
    check(t.hotkeys == 0 && t.commands == 0, "frames ending in header-like bytes leak nothing");
  }

  /* 3. Packet loss without any host guard (v1 and v2). */
  loss_exposure("loss_v1_synthetic", synthetic_stream(9000, 600, false));
  loss_exposure("loss_v2_synthetic", synthetic_stream(9000, 600, true));
  if (argc > 1) {
    FILE *fp = std::fopen(argv[1], "rb");
    if (!fp) { std::fprintf(stderr, "FAIL cannot open %s\n", argv[1]); return 1; }
    std::vector<Bytes> frames;
    Bytes f(34);
    while (std::fread(f.data(), 1, 34, fp) == 34) frames.push_back(f);
    std::fclose(fp);
    std::printf("stream_file_frames %zu\n", frames.size());
    loss_exposure("loss_stream_file", frames);
  }

  /* 4. A damaged first frame with no preamble: the header is consumed, the
   *    breaking byte opens the session, the rest is dropped. */
  {
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    Bytes bad = make_v1(120, 1, tick_us(1), prim8);
    bad[3] = 'N'; /* 'P','R','S','N': N is the noise-calibration arm key */
    feed(&rx, bad, 100, &t, nullptr);
    feed(&rx, "NY:save_show\nS!", 100, &t);
    check(t.hotkeys == 0 && t.commands == 0 && t.frames == 0, "bad-magic first frame leaks nothing");
    check(rx.binary_session, "bad-magic first frame opens the session");
  }

  /* 5. Random bytes and hostile text between frames. */
  {
    const std::vector<Bytes> s = synthetic_stream(100, 400, false);
    const Truth truth = truth_of(s);
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    Bytes nul(1, 0);
    feed(&rx, nul, 100, &t, nullptr); /* preamble byte: session open before any frame */
    uint64_t garbage = 0;
    for (size_t k = 0; k < s.size(); k++) {
      feed(&rx, s[k], 100, &t, &truth);
      Bytes junk(size_t(rnd8()) + 1);
      for (uint8_t &b : junk) {
        b = rnd8();
        if (b == 'P') b = 'p'; /* keep the junk from starting a frame header */
      }
      feed(&rx, junk, 100, &t, &truth);
      garbage += junk.size();
      feed(&rx, ":set_mode=5\nNY S!:factory_reset CONFIRM\r\n", 100, &t);
    }
    std::printf("garbage_bytes %llu\n", (unsigned long long)garbage);
    check(t.hotkeys == 0 && t.commands == 0, "garbage between frames reaches nothing");
    check(t.corrupt == 0, "garbage between frames never becomes a frame");
    check(t.frames == s.size(), "frames around the garbage all arrive");
    check(t.exits == 0, "garbage never ends the session");
  }

  /* 6. Leaving the session takes the exact line after the guard time. */
  {
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    feed(&rx, make_v1(120, 1, tick_us(1), prim8), 1000, &t, nullptr);
    feed(&rx, ":prsm_exit\n", 1000 + K1_PRSM_RX_EXIT_GUARD_MS - 1, &t);
    check(t.exits == 0 && rx.binary_session, "exit line inside the guard time is ignored");
    feed(&rx, ":build\n", 2000, &t);
    check(t.commands == 0 && t.exits == 0 && t.notices == 1, "other lines stay locked out, with a notice");
    feed(&rx, ":prsm_exit\n", 3000, &t);
    check(t.exits == 1 && !rx.binary_session, "exit line after the guard time ends the session");
    feed(&rx, ":build\n", 3001, &t);
    check(t.commands == 1 && t.last_command == "build", "commands work again after exit");
    feed(&rx, "h", 3002, &t);
    check(t.hotkeys == 1, "hotkeys work again after exit");
  }

  /* 7. A frame cut short at the end of a stream does not swallow the exit line. */
  {
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    const Bytes f = make_v1(120, 1, tick_us(1), prim8);
    feed(&rx, f, 1000, &t, nullptr);
    feed(&rx, f.data(), 20, 1008, &t, nullptr);
    feed(&rx, ":prsm_exit\n", 1500, &t);
    check(t.exits == 1 && t.frames == 1, "part-frame then pause then exit line");
  }

  /* 8. Pending command lines are never run by binary or stale input. */
  {
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    feed(&rx, ":set_mo", 100, &t);
    Bytes nul(1, 0);
    feed(&rx, nul, 100, &t, nullptr);
    feed(&rx, "de=1\n", 100, &t);
    check(t.commands == 0 && rx.binary_session, "binary byte in a command line discards it");

    k1_prsm_rx_reset(&rx);
    feed(&rx, ":set_mode=1", 100, &t);
    feed(&rx, "\n", 100 + K1_PRSM_RX_CMD_IDLE_MS + 1, &t);
    check(t.commands == 0 && !rx.command_mode, "a stale pending line is not run by a late newline");

    k1_prsm_rx_reset(&rx);
    std::string longline = ":" + std::string(200, 'a') + "\n";
    feed(&rx, longline.c_str(), 100, &t);
    // Stage F (10 Nov 2026): an over-long TEXT line runs nothing and creates no
    // hotkeys, but does not lock the port: the next line works.
    check(t.commands == 0 && t.hotkeys == 0 && !rx.binary_session, "over-long line is discarded, not run");
    feed(&rx, ":chroma=0.5\n", 100, &t);
    check(t.commands == 1 && t.hotkeys == 0, "the line after an over-long line runs");
  }

  /* 9. Version 2: length and CRC decide. */
  {
    k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
    Tally t;
    Bytes good = make_v2(120, 7, tick_us(7), prim8);
    feed(&rx, good, 100, &t, nullptr);
    check(t.frames == 1 && t.seqs[0] == 7, "v2 frame accepted");
    for (size_t bit = 6 * 8; bit < 39 * 8; bit++) {
      Bytes bad = good;
      bad[bit / 8] ^= uint8_t(1u << (bit % 8));
      k1_prsm_rx_reset(&rx);
      Tally u;
      feed(&rx, bad, 100, &u, nullptr);
      if (u.frames != 0 || u.hotkeys != 0 || u.commands != 0) {
        check(false, "v2 frame with one flipped bit was accepted or leaked");
        break;
      }
    }
    Bytes wrong_len = good;
    wrong_len[5] = 30;
    k1_prsm_rx_reset(&rx);
    Tally v;
    feed(&rx, wrong_len, 100, &v, nullptr);
    check(v.frames == 0 && v.hotkeys == 0 && rx.n.frames_bad >= 1, "v2 wrong length byte refused");
    Bytes v3 = good;
    v3[4] = 3;
    k1_prsm_rx_reset(&rx);
    Tally w;
    feed(&rx, v3, 100, &w, nullptr);
    check(w.frames == 0 && w.hotkeys == 0 && w.commands == 0, "unknown version refused without a leak");
  }

  /* 10. Applied-frame bookkeeping: duplicates dropped, seeks start an epoch. */
  {
    k1_authored_reset();
    k1_authored_status_t st;
    k1_prsm_frame_t f;
    k1_prsm_parse(make_v1(120, 100, tick_us(100), prim8).data(), 34, &f);
    check(k1_authored_on_frame(&f, 1000) == K1_AUTHORED_FRAME_APPLIED, "first frame applied");
    check(k1_authored_on_frame(&f, 1001) == K1_AUTHORED_FRAME_DUPLICATE, "same seq again is dropped");
    k1_prsm_parse(make_v1(120, 101, tick_us(101), prim8).data(), 34, &f);
    k1_authored_on_frame(&f, 1008);
    k1_prsm_parse(make_v1(120, 103, tick_us(103), prim8).data(), 34, &f);
    k1_authored_on_frame(&f, 1025);
    k1_authored_status(&st);
    check(st.epoch == 1 && st.seq_gaps == 1 && st.frames_applied == 3 && st.frames_duplicate == 1,
          "one missing frame stays inside the epoch");
    k1_prsm_parse(make_v1(120, 2500, tick_us(2500), prim8).data(), 34, &f);
    k1_authored_on_frame(&f, 1033);
    k1_authored_status(&st);
    check(st.epoch == 2, "sequence jump starts a new epoch");
    k1_prsm_parse(make_v1(120, 2501, tick_us(1200), prim8).data(), 34, &f);
    k1_authored_on_frame(&f, 1041);
    k1_authored_status(&st);
    check(st.epoch == 3 && st.applied_seq == 2501 && st.applied_t_us == tick_us(1200) && st.applied_ms == 1041,
          "contiguous seq with a show-time jump is a seek too");
    k1_prsm_parse(make_v1(10, 2502, tick_us(1201), prim8).data(), 34, &f);
    check(k1_authored_on_frame(&f, 1049) == K1_AUTHORED_FRAME_REJECTED, "hz out of range rejected");
    k1_authored_status(&st);
    check(st.frames_rejected == 1 && st.applied_seq == 2501, "a rejected frame is not applied");
  }

  if (failures) return 1;
  std::printf("PASS k1_prsm_rx\n");
  return 0;
}
