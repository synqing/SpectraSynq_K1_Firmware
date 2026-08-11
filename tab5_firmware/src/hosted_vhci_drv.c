// SPDX-License-Identifier: Apache-2.0
// Copyright 2015-2024 Espressif Systems (Shanghai) PTE LTD
// Adapted for Tab5 Deck16 P1: replace prebuilt hci_stub_drv with real VHCI.
//
// H0 (2026-08-07): ESP_HCI_IF MUST be 4 on Hosted 2.0.13 (SERIAL=3). Prior
// hardcoded ESP_HCI_IF=3 sent HCI on the control/serial IF — smoking gun.

#include <string.h>
#include <stdint.h>
#include <assert.h>

#include "sdkconfig.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_heap_caps.h"

#include "esp_hosted_interface.h"

static const char *TAG = "vhci_drv";

/* Gate H0: headers actually used by this TU must match 2.0.13 wire ABI. */
_Static_assert(ESP_SERIAL_IF == 3, "ESP_SERIAL_IF must be 3 (Hosted 2.0.13)");
_Static_assert(ESP_HCI_IF == 4, "ESP_HCI_IF must be 4 (Hosted 2.0.13)");
_Static_assert(ESP_INVALID_IF == 0, "ESP_INVALID_IF must be 0 (Hosted 2.0.13)");

// Matches host/utils/common.h layout used by the prebuilt hosted archive.
typedef struct {
  union {
    void *priv_buffer_handle;
  };
  uint8_t if_type;
  uint8_t if_num;
  uint8_t *payload;
  uint8_t flag;
  uint16_t payload_len;
  uint16_t seq_num;
  uint8_t payload_zcopy;
  void (*free_buf_handle)(void *buf_handle);
} interface_buffer_handle_t;

#define H_BUFF_NO_ZEROCOPY 0

extern int esp_hosted_tx(uint8_t iface_type, uint8_t iface_num,
                         uint8_t *buffer, uint16_t len, uint8_t buff_zerocopy,
                         void (*free_buf_fun)(void *ptr));

/* From hosted_h0_wire_probe.c */
void h0_wire_note_hci_rx(uint8_t if_type_hint);
void h0_wire_note_nimble_evt(void);
void h0_wire_log_counters(const char *where);

static void *vhci_alloc(size_t n)
{
  return heap_caps_aligned_alloc(64, n, MALLOC_CAP_INTERNAL | MALLOC_CAP_DMA | MALLOC_CAP_8BIT);
}

static void vhci_free(void *ptr)
{
  heap_caps_free(ptr);
}

#if defined(CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE) && defined(CONFIG_BT_NIMBLE_ENABLED)

#include "host/ble_hs_mbuf.h"
#include "os/os_mbuf.h"
#include "nimble/transport.h"
#include "nimble/transport/hci_h4.h"
#include "nimble/hci_common.h"
#include "esp_idf_version.h"

#ifndef TAB5_HCI_PATH_DIAG
#define TAB5_HCI_PATH_DIAG 0
#endif

#ifndef BLE_HCI_EVENT_HDR_LEN
#define BLE_HCI_EVENT_HDR_LEN 2
#endif

int hci_rx_handler(interface_buffer_handle_t *buf_handle)
{
  if (!buf_handle || !buf_handle->payload || buf_handle->payload_len == 0) {
    return ESP_FAIL;
  }

  const uint8_t if_type = buf_handle->if_type;
  h0_wire_note_hci_rx(if_type);

  uint8_t *data = buf_handle->payload;
  uint32_t len_total_read = buf_handle->payload_len;
  int rc;

#if defined(TAB5_HCI_PATH_DIAG) && (TAB5_HCI_PATH_DIAG)
  ESP_LOGI(TAG,
           "hci_rx_handler if_type=%u len=%u first=%02X %02X %02X %02X",
           (unsigned)if_type, (unsigned)len_total_read,
           data[0],
           len_total_read > 1 ? data[1] : 0,
           len_total_read > 2 ? data[2] : 0,
           len_total_read > 3 ? data[3] : 0);
#endif

  if (data[0] == HCI_H4_EVT) {
    uint8_t *evbuf;
    int totlen = BLE_HCI_EVENT_HDR_LEN + data[2];
#if defined(TAB5_HCI_PATH_DIAG) && (TAB5_HCI_PATH_DIAG)
    ESP_LOGI(TAG, "HCI RX EVT type=0x%02X plen=%u total=%u",
             data[1], (unsigned)data[2], (unsigned)len_total_read);
#endif
    if (totlen > UINT8_MAX + BLE_HCI_EVENT_HDR_LEN) {
      ESP_LOGE(TAG, "Rx: len[%d] > max INT, drop", totlen);
      return ESP_FAIL;
    }
    if (totlen > MYNEWT_VAL(BLE_TRANSPORT_EVT_SIZE)) {
      ESP_LOGE(TAG, "Rx: len[%d] > max BLE, drop", totlen);
      return ESP_FAIL;
    }
    if (data[1] == BLE_HCI_EVCODE_HW_ERROR) {
      ESP_LOGE(TAG, "Rx: HW_ERROR");
      return ESP_FAIL;
    }

    if ((data[1] == BLE_HCI_EVCODE_LE_META) &&
        (data[3] == BLE_HCI_LE_SUBEV_ADV_RPT || data[3] == BLE_HCI_LE_SUBEV_EXT_ADV_RPT)) {
      evbuf = ble_transport_alloc_evt(1);
      if (!evbuf) {
        ESP_LOGW(TAG, "Rx: drop ADV report (OOM)");
        return ESP_FAIL;
      }
    } else {
      evbuf = ble_transport_alloc_evt(0);
      if (!evbuf) {
        ESP_LOGE(TAG, "Rx: alloc_evt(0) failed");
        return ESP_FAIL;
      }
    }

    memset(evbuf, 0, totlen);
    memcpy(evbuf, &data[1], totlen);
    rc = ble_transport_to_hs_evt(evbuf);
    if (rc) {
      ESP_LOGE(TAG, "Rx: transport_to_hs_evt failed rc=%d", rc);
      return ESP_FAIL;
    }
    h0_wire_note_nimble_evt();
  } else if (data[0] == HCI_H4_ACL) {
    struct os_mbuf *m = ble_transport_alloc_acl_from_ll();
    if (!m) {
      ESP_LOGE(TAG, "Rx: alloc_acl_from_ll failed");
      return ESP_FAIL;
    }
    if ((rc = os_mbuf_append(m, &data[1], len_total_read - 1)) != 0) {
      ESP_LOGE(TAG, "Rx: os_mbuf_append failed rc=%d", rc);
      os_mbuf_free_chain(m);
      return ESP_FAIL;
    }
    ble_transport_to_hs_acl(m);
  }

  return ESP_OK;
}

void hci_drv_init(void)
{
  // VHCI: SDIO/Hosted transport carries HCI; nothing local to init.
}

void hci_drv_show_configuration(void)
{
  ESP_LOGI(TAG, "Host BT Support: Enabled");
  ESP_LOGI(TAG, "\tBT Transport Type: VHCI (Tab5 Deck16 P1)");
  /* Evaluated macros — not hand-written IF numbers. */
  ESP_LOGI(TAG, "ABI ESP_SERIAL_IF=%d ESP_HCI_IF=%d ESP_INVALID_IF=%d",
           (int)ESP_SERIAL_IF, (int)ESP_HCI_IF, (int)ESP_INVALID_IF);
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 3, 0)
void ble_transport_ll_init(void)
{
  // Transport is already brought up by hostedInitBLE() / ESP-Hosted SDIO.
}

void ble_transport_ll_deinit(void)
{
}
#endif

int ble_transport_to_ll_acl_impl(struct os_mbuf *om)
{
  int data_len = OS_MBUF_PKTLEN(om) + 1;
  uint8_t *data = vhci_alloc((size_t)data_len);
  int res;

  if (!data) {
    ESP_LOGE(TAG, "Tx ACL: malloc failed");
    res = ESP_FAIL;
    goto exit;
  }

  data[0] = HCI_H4_ACL;
  res = ble_hs_mbuf_to_flat(om, &data[1], OS_MBUF_PKTLEN(om), NULL);
  if (res) {
    ESP_LOGE(TAG, "Tx ACL: mbuf_to_flat failed %d", res);
    vhci_free(data);
    res = ESP_FAIL;
    goto exit;
  }

#if defined(TAB5_HCI_PATH_DIAG) && (TAB5_HCI_PATH_DIAG)
  ESP_LOGI(TAG, "HCI TX ACL → esp_hosted_tx(if_type=%u) len=%d",
           (unsigned)ESP_HCI_IF, data_len);
#endif
  res = esp_hosted_tx(ESP_HCI_IF, 0, data, (uint16_t)data_len, H_BUFF_NO_ZEROCOPY, vhci_free);

exit:
  os_mbuf_free_chain(om);
  return res;
}

int ble_transport_to_ll_cmd_impl(void *buf)
{
  int buf_len = 3 + ((uint8_t *)buf)[2] + 1;
  uint8_t *data = vhci_alloc((size_t)buf_len);
  int res;
  const uint8_t *hci = (const uint8_t *)buf;
  const uint16_t opcode = (uint16_t)hci[0] | ((uint16_t)hci[1] << 8);

#if defined(TAB5_HCI_PATH_DIAG) && (TAB5_HCI_PATH_DIAG)
  if (opcode == 0x0C03) {
    ESP_LOGI(TAG,
             "HCI TX Reset raw H4 stream 01 03 0C 00 → "
             "esp_hosted_tx(ACTUAL if_type=%u) SERIAL_IF=%u HCI_IF=%u len=%d",
             (unsigned)ESP_HCI_IF, (unsigned)ESP_SERIAL_IF,
             (unsigned)ESP_HCI_IF, buf_len);
  } else {
    ESP_LOGD(TAG, "HCI TX CMD opcode=0x%04X len=%d if_type=%u", opcode, buf_len,
             (unsigned)ESP_HCI_IF);
  }
#endif

  if (!data) {
    ESP_LOGE(TAG, "Tx CMD: malloc failed");
    res = ESP_FAIL;
    goto exit;
  }

  data[0] = HCI_H4_CMD;
  memcpy(&data[1], buf, (size_t)buf_len - 1);
  res = esp_hosted_tx(ESP_HCI_IF, 0, data, (uint16_t)buf_len, H_BUFF_NO_ZEROCOPY, vhci_free);

#if defined(TAB5_HCI_PATH_DIAG) && (TAB5_HCI_PATH_DIAG)
  if (opcode == 0x0C03) {
    ESP_LOGI(TAG, "HCI TX Reset esp_hosted_tx rc=%d (await NimBLE evt via hci_rx_handler)", res);
    h0_wire_log_counters("post_hci_reset_tx");
  }
#endif

exit:
  ble_transport_free(buf);
  return res;
}

#else /* !hosted NimBLE */

int hci_rx_handler(interface_buffer_handle_t *buf_handle)
{
  (void)buf_handle;
  return 0;
}

void hci_drv_init(void) {}

void hci_drv_show_configuration(void)
{
  ESP_LOGI(TAG, "Host BT Support: Disabled (stub)");
  ESP_LOGI(TAG, "ABI ESP_SERIAL_IF=%d ESP_HCI_IF=%d",
           (int)ESP_SERIAL_IF, (int)ESP_HCI_IF);
}

#endif /* CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE && CONFIG_BT_NIMBLE_ENABLED */
