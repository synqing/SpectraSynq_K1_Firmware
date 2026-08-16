#pragma once

// Gate-1 scheduling trace integration only. Production builds expose no API and
// compile no call sites because K1_SCHEDULING_TRACE_V1 is non-shippable.
#ifdef K1_SCHEDULING_TRACE_V1

#include <stddef.h>
#include <stdint.h>

// Initialise the trace epoch before the bootstrap FastLED.show() creates and
// registers the two RMT channels. No capture is armed by this call.
void k1_scheduling_trace_initialise(void);

// Core-1 frame-boundary hook. It applies the finite prior-transfer lifetime
// barrier, consumes start/stop requests, and publishes complete identity for
// the next two RMT submissions. It never logs or allocates.
void k1_scheduling_trace_before_fastled_show(void);

// Typed serial command: :scheduling_trace=start|stop|status|dump.
bool k1_scheduling_trace_command(
    const char* command_type,
    const char* command_data);

#endif  // K1_SCHEDULING_TRACE_V1
