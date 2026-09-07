#pragma once

// Independent ST25R3916B identity probe. Main RPL pins only.
// Do not derive from generic k1_hardware (GPIO6/7 are LEDs there).

#ifndef K1_ST25_SCLK_PIN
#define K1_ST25_SCLK_PIN 7
#endif
#ifndef K1_ST25_MOSI_PIN
#define K1_ST25_MOSI_PIN 6
#endif
#ifndef K1_ST25_MISO_PIN
#define K1_ST25_MISO_PIN 5
#endif
#ifndef K1_ST25_CS_PIN
#define K1_ST25_CS_PIN 4
#endif
#ifndef K1_ST25_IRQ_PIN
#define K1_ST25_IRQ_PIN 2
#endif

#ifdef K1_ST25_PROBE_V1
void k1_st25_begin();
#endif
