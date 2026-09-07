#pragma once

#include <stdint.h>

#include "k1_audio_source.h"

#ifndef K1_PCM1808_DIN_PIN
#define K1_PCM1808_DIN_PIN 10
#endif
#ifndef K1_PCM1808_BCLK_PIN
#define K1_PCM1808_BCLK_PIN 13
#endif
#ifndef K1_PCM1808_LRCK_PIN
#define K1_PCM1808_LRCK_PIN 14
#endif
#ifndef K1_PCM1808_NFC_CS_HOLD_PIN
#define K1_PCM1808_NFC_CS_HOLD_PIN 4
#endif

#if K1_AUDIO_SOURCE_PCM1808
void k1_pcm1808_begin();
void k1_pcm1808_take_canonical_samples(int16_t *out96, uint32_t t_now);
void k1_pcm1808_poll_telemetry(uint32_t t_now);
int k1_pcm1808_clock_gate_pass();
#ifdef K1_PCM1808_PROBE_V1
bool k1_pcm1808_dispatch(const char *command_type, char *command_data);
#endif
#endif
