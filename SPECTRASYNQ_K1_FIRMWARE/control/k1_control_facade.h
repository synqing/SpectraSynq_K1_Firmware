#pragma once

#include <stddef.h>
#include <stdint.h>

#include "k1_wireless_control.h"

bool k1_control_is_allowed(const char* control);
K1WirelessControlResult k1_control_apply(const K1WirelessControlRecord& record);
void k1_control_snapshot(K1WirelessControlState* state);
size_t k1_control_capabilities_json(char* out, size_t out_len, uint8_t protocol_version);
