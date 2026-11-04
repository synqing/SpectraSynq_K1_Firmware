#pragma once

// Static depth-4 drop-oldest PCM mailbox. Same code on device and host tests.
// Device wraps push/pop with a FreeRTOS critical section in the USB TU.

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "k1_usb_pcm_assembler.h"

#ifndef K1_USB_FRAME_QUEUE_DEPTH
#define K1_USB_FRAME_QUEUE_DEPTH 4u
#endif

struct K1UsbPcmFrame {
  uint8_t bytes[K1_USB_PCM_FRAME_BYTES];
  uint32_t sequence;
  uint32_t stream_generation;
  int64_t received_us;
};

struct K1UsbFrameMailbox {
  K1UsbPcmFrame slots[K1_USB_FRAME_QUEUE_DEPTH];
  uint8_t head;
  uint8_t count;
  uint32_t dropped_oldest;
  uint32_t enqueue_failures;
  uint32_t high_water;
  uint32_t next_sequence;
};

inline void k1_usb_mailbox_init(K1UsbFrameMailbox *q) {
  memset(q, 0, sizeof(*q));
}

inline uint8_t k1_usb_mailbox_count(const K1UsbFrameMailbox *q) { return q->count; }

inline bool k1_usb_mailbox_push_drop_oldest(K1UsbFrameMailbox *q, const K1UsbPcmFrame *frame) {
  if (frame == nullptr) {
    q->enqueue_failures++;
    return false;
  }
  if (q->count == K1_USB_FRAME_QUEUE_DEPTH) {
    q->head = (uint8_t)((q->head + 1u) % K1_USB_FRAME_QUEUE_DEPTH);
    q->count--;
    q->dropped_oldest++;
  }
  const uint8_t idx = (uint8_t)((q->head + q->count) % K1_USB_FRAME_QUEUE_DEPTH);
  q->slots[idx] = *frame;
  q->count++;
  if (q->count > q->high_water) {
    q->high_water = q->count;
  }
  return true;
}

inline bool k1_usb_mailbox_pop(K1UsbFrameMailbox *q, K1UsbPcmFrame *out) {
  if (q->count == 0 || out == nullptr) {
    return false;
  }
  *out = q->slots[q->head];
  q->head = (uint8_t)((q->head + 1u) % K1_USB_FRAME_QUEUE_DEPTH);
  q->count--;
  return true;
}
