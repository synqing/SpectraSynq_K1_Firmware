#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 34-byte PRSM FeatureFrame — layout verified against PRISM
 * k1_usb_uac_cdc_bridge/main/k1_feature_frame.h (transport reference only).
 * Product K1 copies the wire format, not the bridge renderer. */

#define K1_PRSM_PACKET_LEN 34
#define K1_PRSM_MAGIC_0 'P'
#define K1_PRSM_MAGIC_1 'R'
#define K1_PRSM_MAGIC_2 'S'
#define K1_PRSM_MAGIC_3 'M'
#define K1_PRSM_VERSION 1

typedef struct {
  uint8_t version;
  uint8_t hz;
  uint32_t seq;
  uint64_t t_us;
  uint16_t prim8_u16[8];
} k1_prsm_frame_t;

bool k1_prsm_parse(const uint8_t *buf, int len, k1_prsm_frame_t *out);

typedef enum {
  K1_PRSM_SCAN_NONE = 0,     /* byte is not part of a PRSM frame — hotkeys may have it */
  K1_PRSM_SCAN_CONSUMED,     /* byte consumed by hunter/filler; not a complete frame */
  K1_PRSM_SCAN_FRAME_OK,     /* complete valid frame in *out */
  K1_PRSM_SCAN_FRAME_BAD     /* magic matched but parse rejected; resynchronising */
} k1_prsm_scan_result_t;

typedef struct {
  uint8_t buf[K1_PRSM_PACKET_LEN];
  uint8_t fill;
} k1_prsm_scanner_t;

void k1_prsm_scanner_reset(k1_prsm_scanner_t *s);
k1_prsm_scan_result_t k1_prsm_scanner_push(k1_prsm_scanner_t *s, uint8_t byte,
                                           k1_prsm_frame_t *out);

#ifdef __cplusplus
}
#endif
