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

// Hardware present on I2S1 (ingress owner OR continuous shadow capture).
#define K1_PCM1808_PRESENT (K1_AUDIO_SOURCE_PCM1808 || K1_PCM1808_SHADOW)

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
#if !K1_AUDIO_SOURCE_USB && !K1_AUDIO_SOURCE_MIC && !K1_AUDIO_SOURCE_PCM1808
#error "No K1 audio source selected"
#endif
