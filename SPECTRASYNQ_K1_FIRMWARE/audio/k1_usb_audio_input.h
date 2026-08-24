#pragma once

#include <stdint.h>

#include "k1_audio_source.h"

#if K1_AUDIO_SOURCE_USB
void k1_usb_audio_start();
void k1_usb_audio_take_canonical_samples(int16_t *out96, uint32_t t_now);
void k1_usb_audio_poll_telemetry(uint32_t t_now);
#endif
