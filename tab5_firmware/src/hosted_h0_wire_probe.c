// SPDX-License-Identifier: Apache-2.0
// H0 wire-contract probes (Captain 2026-08-07): wrap Hosted TX/RX/capability
// entry points against the prebuilt 2.0.13 archive. Linker flags:
//   -Wl,--wrap=esp_hosted_tx
//   -Wl,--wrap=process_capabilities
//   -Wl,--wrap=print_capabilities
//   -Wl,--wrap=serial_rx_handler

#include <stdint.h>
#include <string.h>

#include "esp_log.h"
#include "esp_hosted_interface.h"
#include "esp_hosted_header.h"

#ifndef TAB5_HCI_PATH_DIAG
#define TAB5_HCI_PATH_DIAG 0
#endif

static const char *TAG = "h0_wire";

/* Capability bits — match esp_hosted_transport_init.h ESP_CAPABILITIES. */
#define H0_WLAN_SDIO_SUPPORT   (1u << 0)
#define H0_BT_UART_SUPPORT     (1u << 1)
#define H0_BT_SDIO_SUPPORT     (1u << 2)
#define H0_BLE_ONLY_SUPPORT    (1u << 3)
#define H0_BR_EDR_ONLY_SUPPORT (1u << 4)
#define H0_WLAN_SPI_SUPPORT    (1u << 5)
#define H0_BT_SPI_SUPPORT      (1u << 6)
#define H0_CHECKSUM_ENABLED    (1u << 7)

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

/* RX counters (raw path before NimBLE): updated by wraps + vhci. */
volatile uint32_t g_h0_rx_if3;
volatile uint32_t g_h0_rx_if4;
volatile uint32_t g_h0_rx_if_other;
volatile uint32_t g_h0_rx_if_invalid;
volatile uint32_t g_h0_serial_rx_handler;
volatile uint32_t g_h0_hci_rx_handler;
volatile uint32_t g_h0_nimble_evt_cb;
volatile uint32_t g_h0_tx_hci;
volatile uint32_t g_h0_tx_serial;
volatile uint32_t g_h0_tx_other;
volatile uint32_t g_h0_cap_bitmap;
volatile uint8_t g_h0_cap_seen;

extern int __real_esp_hosted_tx(uint8_t iface_type, uint8_t iface_num,
                                uint8_t *buffer, uint16_t len,
                                uint8_t buff_zerocopy,
                                void (*free_buf_fun)(void *ptr));
extern void __real_process_capabilities(uint8_t cap);
extern void __real_print_capabilities(uint32_t cap);
extern int __real_serial_rx_handler(interface_buffer_handle_t *buf_handle);

#if TAB5_HCI_PATH_DIAG
static void h0_log_expected_header(uint8_t iface_type, uint8_t iface_num,
                                   const uint8_t *buffer, uint16_t len,
                                   uint8_t buff_zerocopy)
{
	/* Reconstruct Espressif SDIO TX packing (sdio_drv.c non-zerocopy HCI). */
	struct esp_payload_header h;
	uint16_t wire_len = len;
	uint8_t hci_pkt = 0;
	const uint8_t *wire_payload = buffer;
	uint8_t first[8] = {0};
	unsigned nfirst = 0;

	memset(&h, 0, sizeof(h));
	h.if_type = iface_type & 0x0f;
	h.if_num = iface_num & 0x0f;
	h.flags = 0;
	h.offset = (uint16_t)sizeof(struct esp_payload_header);
	h.seq_num = 0;
	h.checksum = 0;

	if (iface_type == (uint8_t)ESP_HCI_IF && !buff_zerocopy && buffer && len > 0) {
		hci_pkt = buffer[0];
		h.hci_pkt_type = hci_pkt;
		wire_len = (uint16_t)(len - 1);
		wire_payload = buffer + 1;
	}
	h.len = wire_len;

	if (wire_payload && wire_len > 0) {
		nfirst = wire_len < 8 ? wire_len : 8;
		memcpy(first, wire_payload, nfirst);
	}

	ESP_LOGI(TAG,
	         "pre-SDIO hdr if_type=%u if_num=%u hci_pkt_type=0x%02X len=%u "
	         "offset=%u flags=0x%02X seq_num=%u zcopy=%u "
	         "payload_first=%02X %02X %02X %02X %02X %02X %02X %02X (n=%u)",
	         (unsigned)h.if_type, (unsigned)h.if_num, (unsigned)h.hci_pkt_type,
	         (unsigned)h.len, (unsigned)h.offset, (unsigned)h.flags,
	         (unsigned)h.seq_num, (unsigned)buff_zerocopy,
	         first[0], first[1], first[2], first[3],
	         first[4], first[5], first[6], first[7], nfirst);

	if (iface_type == (uint8_t)ESP_HCI_IF && len >= 4 && buffer &&
	    buffer[0] == 0x01 && buffer[1] == 0x03 && buffer[2] == 0x0c &&
	    buffer[3] == 0x00) {
		const int ok_if = (iface_type == 4);
		const int ok_pkt = (hci_pkt == 0x01);
		const int ok_pl = (wire_len >= 3 && first[0] == 0x03 && first[1] == 0x0c &&
		                   first[2] == 0x00);
		ESP_LOGI(TAG,
		         "HCI Reset contract: if_type==4?%s hci_pkt==0x01?%s "
		         "payload==03 0C 00?%s  (expect PASS/PASS/PASS on 2.0.13)",
		         ok_if ? "YES" : "NO", ok_pkt ? "YES" : "NO",
		         ok_pl ? "YES" : "NO");
	}
}
#endif /* TAB5_HCI_PATH_DIAG */

int __wrap_esp_hosted_tx(uint8_t iface_type, uint8_t iface_num, uint8_t *buffer,
                         uint16_t len, uint8_t buff_zerocopy,
                         void (*free_buf_fun)(void *ptr))
{
	if (iface_type == (uint8_t)ESP_HCI_IF) {
		g_h0_tx_hci++;
	} else if (iface_type == (uint8_t)ESP_SERIAL_IF) {
		g_h0_tx_serial++;
	} else {
		g_h0_tx_other++;
	}

#if TAB5_HCI_PATH_DIAG
	ESP_LOGI(TAG,
	         "esp_hosted_tx ACTUAL if_type=%u (SERIAL=%u HCI=%u) if_num=%u "
	         "len=%u zcopy=%u",
	         (unsigned)iface_type, (unsigned)ESP_SERIAL_IF,
	         (unsigned)ESP_HCI_IF, (unsigned)iface_num, (unsigned)len,
	         (unsigned)buff_zerocopy);
	if (buffer && len > 0) {
		h0_log_expected_header(iface_type, iface_num, buffer, len, buff_zerocopy);
	}
#endif

	return __real_esp_hosted_tx(iface_type, iface_num, buffer, len, buff_zerocopy,
	                            free_buf_fun);
}

void __wrap_process_capabilities(uint8_t cap)
{
	g_h0_cap_bitmap = cap;
	g_h0_cap_seen = 1;
#if TAB5_HCI_PATH_DIAG
	ESP_LOGI(TAG,
	         "process_capabilities bitmap=0x%02X "
	         "WLAN_SDIO=%d BT_UART=%d BT_SDIO=%d BLE_ONLY=%d BR_EDR=%d "
	         "WLAN_SPI=%d BT_SPI=%d CHECKSUM=%d",
	         (unsigned)cap, !!(cap & H0_WLAN_SDIO_SUPPORT),
	         !!(cap & H0_BT_UART_SUPPORT), !!(cap & H0_BT_SDIO_SUPPORT),
	         !!(cap & H0_BLE_ONLY_SUPPORT), !!(cap & H0_BR_EDR_ONLY_SUPPORT),
	         !!(cap & H0_WLAN_SPI_SUPPORT), !!(cap & H0_BT_SPI_SUPPORT),
	         !!(cap & H0_CHECKSUM_ENABLED));
#endif
	__real_process_capabilities(cap);
}

void __wrap_print_capabilities(uint32_t cap)
{
#if TAB5_HCI_PATH_DIAG
	ESP_LOGI(TAG, "print_capabilities cap=0x%lx", (unsigned long)cap);
#endif
	__real_print_capabilities(cap);
}

int __wrap_serial_rx_handler(interface_buffer_handle_t *buf_handle)
{
	g_h0_serial_rx_handler++;
	if (buf_handle) {
		const uint8_t t = buf_handle->if_type;
		if (t == (uint8_t)ESP_SERIAL_IF) {
			g_h0_rx_if3++;
		} else if (t == (uint8_t)ESP_HCI_IF) {
			g_h0_rx_if4++;
		} else if (t == (uint8_t)ESP_INVALID_IF) {
			g_h0_rx_if_invalid++;
		} else {
			g_h0_rx_if_other++;
		}
#if TAB5_HCI_PATH_DIAG
		ESP_LOGI(TAG,
		         "serial_rx_handler if_type=%u len=%u (count_serial=%lu)",
		         (unsigned)t,
		         buf_handle->payload_len ? (unsigned)buf_handle->payload_len : 0,
		         (unsigned long)g_h0_serial_rx_handler);
#endif
	}
	return __real_serial_rx_handler(buf_handle);
}

void h0_wire_note_hci_rx(uint8_t if_type_hint)
{
	g_h0_hci_rx_handler++;
	if (if_type_hint == (uint8_t)ESP_HCI_IF) {
		g_h0_rx_if4++;
	} else if (if_type_hint == (uint8_t)ESP_SERIAL_IF) {
		g_h0_rx_if3++;
	} else if (if_type_hint == (uint8_t)ESP_INVALID_IF) {
		g_h0_rx_if_invalid++;
	} else {
		g_h0_rx_if_other++;
	}
}

void h0_wire_note_nimble_evt(void)
{
	g_h0_nimble_evt_cb++;
}

void h0_wire_log_counters(const char *where)
{
#if TAB5_HCI_PATH_DIAG
	ESP_LOGI(TAG,
	         "RX counters @%s: if3=%lu if4=%lu other=%lu invalid=%lu "
	         "serial_hdl=%lu hci_hdl=%lu nimble_evt=%lu | "
	         "TX hci=%lu serial=%lu other=%lu | cap_seen=%u cap=0x%02lX",
	         where ? where : "?", (unsigned long)g_h0_rx_if3,
	         (unsigned long)g_h0_rx_if4, (unsigned long)g_h0_rx_if_other,
	         (unsigned long)g_h0_rx_if_invalid,
	         (unsigned long)g_h0_serial_rx_handler,
	         (unsigned long)g_h0_hci_rx_handler,
	         (unsigned long)g_h0_nimble_evt_cb, (unsigned long)g_h0_tx_hci,
	         (unsigned long)g_h0_tx_serial, (unsigned long)g_h0_tx_other,
	         (unsigned)g_h0_cap_seen, (unsigned long)g_h0_cap_bitmap);
#else
	(void)where;
#endif
}
