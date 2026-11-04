#pragma once

// Host-testable USB PCM byte assembler. No Arduino, no heap, no logging.
// Incoming USB Audio payloads are arbitrary lengths; a 16-bit sample may split
// across callbacks. A generation bump discards any partial byte.

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifndef K1_USB_PCM_FRAME_BYTES
#define K1_USB_PCM_FRAME_BYTES 192u
#endif

typedef void (*k1_usb_pcm_frame_cb)(const uint8_t frame[K1_USB_PCM_FRAME_BYTES], void *ctx);

struct K1UsbPcmAssembler {
  uint8_t buf[K1_USB_PCM_FRAME_BYTES];
  uint16_t filled;
  uint32_t generation;
  uint32_t frames_assembled;
  uint32_t bytes_received;
  uint32_t samples_received;
};

inline void k1_usb_pcm_assembler_init(K1UsbPcmAssembler *a) {
  memset(a, 0, sizeof(*a));
}

inline void k1_usb_pcm_assembler_reset(K1UsbPcmAssembler *a, uint32_t generation) {
  a->filled = 0;
  a->generation = generation;
}

inline void k1_usb_pcm_assembler_feed(K1UsbPcmAssembler *a, const uint8_t *data, uint16_t len,
                                      k1_usb_pcm_frame_cb cb, void *ctx) {
  if (data == nullptr && len != 0) {
    return;
  }
  a->bytes_received += len;
  a->samples_received += (uint32_t)(len / 2u);

  const uint8_t *src = data;
  uint16_t remain = len;
  while (remain > 0) {
    const uint16_t space = (uint16_t)(K1_USB_PCM_FRAME_BYTES - a->filled);
    const uint16_t take = remain < space ? remain : space;
    memcpy(a->buf + a->filled, src, take);
    a->filled = (uint16_t)(a->filled + take);
    src += take;
    remain = (uint16_t)(remain - take);
    if (a->filled == K1_USB_PCM_FRAME_BYTES) {
      a->frames_assembled++;
      if (cb != nullptr) {
        cb(a->buf, ctx);
      }
      a->filled = 0;
    }
  }
}
