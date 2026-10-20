#pragma once
// Forced into fixture translation units with -include. Effect sources stay
// untouched; their millis() and micros() calls follow the admitted-sample clock.
#ifdef K1_EMU_FIXTURE
#include "k1_emu_fixture.h"
#define millis k1_emu_fixture_time_ms
#define micros k1_emu_fixture_time_us
#endif
