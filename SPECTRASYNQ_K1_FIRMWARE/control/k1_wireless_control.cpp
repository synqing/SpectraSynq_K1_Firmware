#include "k1_wireless_control.h"

#include "k1_control_facade.h"

bool k1_wireless_control_is_allowed(const char* control) {
  return k1_control_is_allowed(control);
}

K1WirelessControlResult k1_wireless_control_apply(const K1WirelessControlRecord& record) {
  return k1_control_apply(record);
}

void k1_wireless_control_snapshot(K1WirelessControlState* state) {
  k1_control_snapshot(state);
}
