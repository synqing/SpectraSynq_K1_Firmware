/*
 * ESP-Hosted 2.0.13 wire ABI — interface type numbers.
 *
 * Arduino P4's shipped espressif__esp_hosted headers omit this file even though
 * transport_drv.h includes it. Values MUST match the prebuilt
 * libespressif__esp_hosted.a (2.0.13) and official common/esp_hosted_interface.h:
 *
 *   ESP_INVALID_IF=0, STA=1, AP=2, SERIAL=3, HCI=4, PRIV=5, …
 *
 * Do NOT use the classic (pre-INVALID) numbering where HCI was 3.
 */
#ifndef __ESP_HOSTED_INTERFACE_H__
#define __ESP_HOSTED_INTERFACE_H__

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
	ESP_INVALID_IF = 0,
	ESP_STA_IF,
	ESP_AP_IF,
	ESP_SERIAL_IF,
	ESP_HCI_IF,
	ESP_PRIV_IF,
	ESP_TEST_IF,
	ESP_ETH_IF,
	ESP_MAX_IF,
} esp_hosted_if_type_t;

#ifdef __cplusplus
}
#endif

#endif /* __ESP_HOSTED_INTERFACE_H__ */
