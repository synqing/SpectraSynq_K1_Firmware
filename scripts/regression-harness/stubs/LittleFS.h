// LittleFS.h — HOST-ONLY in-memory filesystem stub (non-shipping).
//
// Lets host tests drive the REAL persistence loaders (persistence/bridge_fs.h
// load_config(), control/k1_show_state.cpp k1_show_state_load(), the preset
// slot file in control/k1_effect_queue.cpp) against byte-exact file images
// prepared by the test. Implements only the Arduino FS calls those loaders use.
// Absent from every PlatformIO environment.
#pragma once

#include "FS.h"
