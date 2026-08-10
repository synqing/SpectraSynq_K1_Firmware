/*
 * ESP-Hosted 2.0.13 payload header layout (common/esp_hosted_header.h).
 * Local copy for H0 wire-contract reconstruction — Arduino package omits it.
 */
#ifndef __ESP_HOSTED_HEADER__H
#define __ESP_HOSTED_HEADER__H

#include <stdint.h>

struct esp_payload_header {
	uint8_t          if_type:4;
	uint8_t          if_num:4;
	uint8_t          flags;
	uint16_t         len;
	uint16_t         offset;
	uint16_t         checksum;
	uint16_t         seq_num;
	uint8_t          throttle_cmd:2;
	uint8_t          reserved2:6;
	union {
		uint8_t      reserved3;
		uint8_t      hci_pkt_type;
		uint8_t      priv_pkt_type;
	};
} __attribute__((packed));

#define MORE_FRAGMENT (1 << 0)
#define H_ESP_PAYLOAD_HEADER_OFFSET sizeof(struct esp_payload_header)

#endif /* __ESP_HOSTED_HEADER__H */
