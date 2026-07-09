#pragma once

#ifdef K1_WIRELESS_ENABLED

#include <stdint.h>

void k1_wireless_begin();
void k1_wireless_poll(uint32_t now_ms);
bool k1_wireless_is_ap_started();
uint8_t k1_wireless_client_count();

#endif  // K1_WIRELESS_ENABLED
