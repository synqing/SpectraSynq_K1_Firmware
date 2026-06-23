#pragma once

#include <stddef.h>
#include <stdint.h>

#include "sb_wireless_control.h"

bool sb_k1_control_is_allowed(const char* control);
K1WirelessControlResult sb_k1_control_apply(const K1WirelessControlRecord& record);
void sb_k1_control_snapshot(K1WirelessControlState* state);
size_t sb_k1_control_capabilities_json(char* out, size_t out_len, uint8_t protocol_version);
