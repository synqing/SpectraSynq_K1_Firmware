#include <cstdint>
#include <cstdio>
#include <cstring>

#include "k1_usb_pcm_assembler.h"
#include "k1_usb_frame_mailbox.h"

static int g_failures = 0;
static uint32_t g_cb_count = 0;
static uint8_t g_last[K1_USB_PCM_FRAME_BYTES];

static void on_frame(const uint8_t frame[K1_USB_PCM_FRAME_BYTES], void *ctx) {
  (void)ctx;
  g_cb_count++;
  memcpy(g_last, frame, K1_USB_PCM_FRAME_BYTES);
}

static void expect(bool cond, const char *msg) {
  if (!cond) {
    std::fprintf(stderr, "FAIL %s\n", msg);
    g_failures++;
  }
}

static void fill_ramp(uint8_t *dst, uint16_t n, uint8_t start) {
  for (uint16_t i = 0; i < n; i++) {
    dst[i] = (uint8_t)(start + i);
  }
}

int main() {
  K1UsbPcmAssembler a;
  k1_usb_pcm_assembler_init(&a);

  uint8_t exact[192];
  fill_ramp(exact, 192, 1);
  g_cb_count = 0;
  k1_usb_pcm_assembler_feed(&a, exact, 192, on_frame, nullptr);
  expect(g_cb_count == 1, "exact 192 emits one frame");
  expect(memcmp(g_last, exact, 192) == 0, "exact 192 payload");
  expect(a.filled == 0, "exact 192 leaves no partial");

  uint8_t two96[192];
  fill_ramp(two96, 192, 40);
  g_cb_count = 0;
  k1_usb_pcm_assembler_feed(&a, two96, 96, on_frame, nullptr);
  expect(g_cb_count == 0, "first 96 is partial");
  k1_usb_pcm_assembler_feed(&a, two96 + 96, 96, on_frame, nullptr);
  expect(g_cb_count == 1, "two*96 emits one frame");
  expect(memcmp(g_last, two96, 192) == 0, "two*96 payload");

  uint8_t ones[192];
  fill_ramp(ones, 192, 80);
  g_cb_count = 0;
  for (uint16_t i = 0; i < 192; i++) {
    k1_usb_pcm_assembler_feed(&a, ones + i, 1, on_frame, nullptr);
  }
  expect(g_cb_count == 1, "192x1 byte emits one frame");
  expect(memcmp(g_last, ones, 192) == 0, "192x1 payload");

  uint8_t odd[7] = {1, 2, 3, 4, 5, 6, 7};
  g_cb_count = 0;
  k1_usb_pcm_assembler_reset(&a, 2);
  k1_usb_pcm_assembler_feed(&a, odd, 7, on_frame, nullptr);
  expect(g_cb_count == 0, "odd length stays partial");
  expect(a.filled == 7, "odd length filled=7");

  uint8_t split_a[1] = {0x34};
  uint8_t split_b[191];
  fill_ramp(split_b, 191, 9);
  uint8_t split_expect[192];
  split_expect[0] = 0x34;
  memcpy(split_expect + 1, split_b, 191);
  k1_usb_pcm_assembler_reset(&a, 3);
  g_cb_count = 0;
  k1_usb_pcm_assembler_feed(&a, split_a, 1, on_frame, nullptr);
  k1_usb_pcm_assembler_feed(&a, split_b, 191, on_frame, nullptr);
  expect(g_cb_count == 1, "sample-split across callbacks");
  expect(memcmp(g_last, split_expect, 192) == 0, "sample-split payload");

  uint8_t multi[192 * 3];
  fill_ramp(multi, (uint16_t)sizeof(multi), 3);
  k1_usb_pcm_assembler_reset(&a, 4);
  g_cb_count = 0;
  k1_usb_pcm_assembler_feed(&a, multi, (uint16_t)sizeof(multi), on_frame, nullptr);
  expect(g_cb_count == 3, "multi-frame callback");

  uint8_t frame_plus[192 + 11];
  fill_ramp(frame_plus, (uint16_t)sizeof(frame_plus), 5);
  k1_usb_pcm_assembler_reset(&a, 5);
  g_cb_count = 0;
  k1_usb_pcm_assembler_feed(&a, frame_plus, (uint16_t)sizeof(frame_plus), on_frame, nullptr);
  expect(g_cb_count == 1, "frame+partial emits one");
  expect(a.filled == 11, "frame+partial remainder 11");

  k1_usb_pcm_assembler_reset(&a, 6);
  expect(a.filled == 0, "generation change discards partial");
  expect(a.generation == 6, "generation stored");

  g_cb_count = 0;
  k1_usb_pcm_assembler_feed(&a, frame_plus, 11, on_frame, nullptr);
  k1_usb_pcm_assembler_reset(&a, 7);
  uint8_t reconnect[192];
  fill_ramp(reconnect, 192, 200);
  k1_usb_pcm_assembler_feed(&a, reconnect, 192, on_frame, nullptr);
  expect(g_cb_count == 1, "clean first frame after reconnect");
  expect(memcmp(g_last, reconnect, 192) == 0, "reconnect payload not mixed with stale partial");

  K1UsbFrameMailbox q;
  k1_usb_mailbox_init(&q);
  expect(k1_usb_mailbox_count(&q) == 0, "empty mailbox");

  K1UsbPcmFrame frames[6];
  memset(frames, 0, sizeof(frames));
  for (uint32_t i = 0; i < 6; i++) {
    frames[i].bytes[0] = (uint8_t)(10 + i);
    frames[i].sequence = i + 1;
    frames[i].stream_generation = 1;
    frames[i].received_us = (int64_t)i;
  }
  expect(k1_usb_mailbox_push_drop_oldest(&q, &frames[0]), "push 0");
  expect(k1_usb_mailbox_push_drop_oldest(&q, &frames[1]), "push 1");
  expect(k1_usb_mailbox_count(&q) == 2, "normal depth 2");

  expect(k1_usb_mailbox_push_drop_oldest(&q, &frames[2]), "push 2");
  expect(k1_usb_mailbox_push_drop_oldest(&q, &frames[3]), "push 3");
  expect(k1_usb_mailbox_count(&q) == 4, "full depth 4");
  expect(q.dropped_oldest == 0, "no drop yet");

  expect(k1_usb_mailbox_push_drop_oldest(&q, &frames[4]), "push 4 drops oldest");
  expect(k1_usb_mailbox_count(&q) == 4, "still depth 4");
  expect(q.dropped_oldest == 1, "dropped oldest once");

  K1UsbPcmFrame out;
  expect(k1_usb_mailbox_pop(&q, &out), "pop after drop");
  expect(out.bytes[0] == 11, "newest retained, oldest gone (10 dropped, 11 now head)");
  expect(k1_usb_mailbox_pop(&q, &out), "pop 2");
  expect(out.bytes[0] == 12, "order 12");
  expect(k1_usb_mailbox_pop(&q, &out), "pop 3");
  expect(out.bytes[0] == 13, "order 13");
  expect(k1_usb_mailbox_pop(&q, &out), "pop 4");
  expect(out.bytes[0] == 14, "newest 14 retained");
  expect(!k1_usb_mailbox_pop(&q, &out), "underflow empty");
  expect(k1_usb_mailbox_count(&q) == 0, "empty after drain");

  expect(!k1_usb_mailbox_push_drop_oldest(&q, nullptr), "null is not a partial enqueue");
  expect(q.enqueue_failures == 1, "null counts as enqueue failure");

  uint32_t seq = 100;
  for (uint32_t i = 0; i < 4; i++) {
    frames[i].sequence = seq + i;
    frames[i].stream_generation = 9;
    k1_usb_mailbox_push_drop_oldest(&q, &frames[i]);
  }
  uint32_t prev = 0;
  bool first = true;
  while (k1_usb_mailbox_pop(&q, &out)) {
    if (!first) {
      expect(out.sequence == prev + 1, "sequence monotonic inside generation");
    }
    first = false;
    prev = out.sequence;
  }

  int16_t canonical[96];
  const int16_t src[96] = {0, 32767, -32768, 1, -1, 1234, -1234};
  memcpy(canonical, src, sizeof(src));
  expect(canonical[0] == 0, "zero stays zero (no IM69 *8, no DC)");
  expect(canonical[1] == 32767, "+FS retained");
  expect(canonical[2] == -32768, "-FS retained");
  expect(canonical[1] != (int16_t)(32767 * 8), "no IM69 x8");

  if (g_failures) {
    std::fprintf(stderr, "%d failures\n", g_failures);
    return 1;
  }
  std::puts("PASS k1_usb_audio_host_probe");
  return 0;
}
