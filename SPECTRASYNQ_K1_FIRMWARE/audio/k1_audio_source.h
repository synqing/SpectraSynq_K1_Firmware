#pragma once

// Fail-closed audio ingress selectors. Production does not pass -DK1_AUDIO_SOURCE_MIC=1
// (that would change the shipping compiler command line). Defaults keep microphone
// authority. The USB probe env passes -DK1_AUDIO_SOURCE_USB=1 -DK1_AUDIO_SOURCE_MIC=0.

#ifndef K1_AUDIO_SOURCE_USB
#define K1_AUDIO_SOURCE_USB 0
#endif
#ifndef K1_AUDIO_SOURCE_MIC
#define K1_AUDIO_SOURCE_MIC 1
#endif
#ifndef K1_AUDIO_SOURCE_PCM1808
#define K1_AUDIO_SOURCE_PCM1808 0
#endif
#ifndef K1_PCM1808_SHADOW
#define K1_PCM1808_SHADOW 0
#endif
// FE board (k1_fe): microphone is the default AP source; the 3.5 mm jack hands
// ingress to the PCM1808 canonical path at runtime (system/k1_fe_board.h).
#ifndef K1_PCM1808_LINE_SWITCH
#define K1_PCM1808_LINE_SWITCH 0
#endif

// Hardware present on I2S1 (ingress owner, continuous shadow capture, or FE jack switch).
#define K1_PCM1808_PRESENT (K1_AUDIO_SOURCE_PCM1808 || K1_PCM1808_SHADOW || K1_PCM1808_LINE_SWITCH)
// The PCM1808 canonical 12.8 kHz / 96 hop can feed AP (always, or when the jack selects it).
#define K1_PCM1808_CANONICAL (K1_AUDIO_SOURCE_PCM1808 || K1_PCM1808_LINE_SWITCH)

#if K1_AUDIO_SOURCE_USB && K1_AUDIO_SOURCE_MIC
#error "K1 USB and microphone capture cannot both own ingress in this build"
#endif
#if K1_AUDIO_SOURCE_USB && K1_AUDIO_SOURCE_PCM1808
#error "K1 USB and PCM1808 capture cannot both own ingress in this build"
#endif
#if K1_AUDIO_SOURCE_MIC && K1_AUDIO_SOURCE_PCM1808
#error "K1 microphone and PCM1808 capture cannot both own ingress in this build"
#endif
#if K1_PCM1808_SHADOW && K1_AUDIO_SOURCE_PCM1808
#error "K1_PCM1808_SHADOW cannot share a build with PCM1808 ingress ownership"
#endif
#if K1_PCM1808_SHADOW && K1_AUDIO_SOURCE_USB
#error "K1 USB and PCM1808 shadow cannot both run in this build"
#endif
#if K1_PCM1808_SHADOW && !K1_AUDIO_SOURCE_MIC
#error "K1_PCM1808_SHADOW requires the microphone to remain the AP source"
#endif
#if K1_PCM1808_LINE_SWITCH && (!K1_AUDIO_SOURCE_MIC || K1_AUDIO_SOURCE_PCM1808 || K1_PCM1808_SHADOW || K1_AUDIO_SOURCE_USB)
#error "K1_PCM1808_LINE_SWITCH needs the microphone as default source and no other PCM/USB mode"
#endif
#if !K1_AUDIO_SOURCE_USB && !K1_AUDIO_SOURCE_MIC && !K1_AUDIO_SOURCE_PCM1808
#error "No K1 audio source selected"
#endif
