---
abstract: "ESP-IDF 5.4 / pioarduino S3 I2S RX overflow API: i2s_event_callbacks_t.on_recv_q_ovf, register before enable, ISR-only, event.size is overwritten buffer size. Exact lost-frame total remains UNKNOWN."
---

# P1 — installed I2S overflow callback (S3)

Header (Arduino-ESP32 libs, ESP32-S3):

`/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/include/esp_driver_i2s/include/driver/i2s_common.h`

`i2s_event_data_t` in sibling `driver/i2s_types.h`.

## Callback group (ISR)

```c
typedef struct {
    i2s_isr_callback_t on_recv;
    i2s_isr_callback_t on_recv_q_ovf;  /* buffer size that has been overwritten */
    i2s_isr_callback_t on_sent;
    i2s_isr_callback_t on_send_q_ovf;
} i2s_event_callbacks_t;
```

`i2s_isr_callback_t` returns `bool` (whether a high-priority task was woken).

## Event payload

```c
typedef struct {
    void  *data;     /* deprecated; NULL on overflow */
    void  *dma_buf;  /* NULL on on_recv_q_ovf */
    size_t size;     /* on overflow: buffer size that dropped / overwritten */
} i2s_event_data_t;
```

`size` is **one overwritten DMA buffer**, not a hardware lost-frame accumulator.

**Exact lost-frame count = UNKNOWN.** Firmware may report `dropped_frames_signaled = ovf_bytes / 6` as API-signaled, and must print `dropped_exact=UNKNOWN`.

## Register order

`i2s_channel_register_event_callback` is only legal in REGISTERED / READY — **before** `i2s_channel_enable`.

ISR: no printf, no heap, no SRC, no AP. Atomic increment only.

Re-run:

```bash
rg -n "on_recv_q_ovf|i2s_event_callbacks_t|i2s_channel_register_event_callback" \
  ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/include/esp_driver_i2s/include/driver/i2s_common.h
```

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | Quoted installed S3 I2S 5.4 headers. |
