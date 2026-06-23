#pragma once

#ifdef SB_K1_WIRELESS_ENABLED

#include <stdint.h>

void sb_k1_wireless_begin();
void sb_k1_wireless_poll(uint32_t now_ms);
bool sb_k1_wireless_is_ap_started();
uint8_t sb_k1_wireless_client_count();

#endif  // SB_K1_WIRELESS_ENABLED
